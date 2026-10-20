import os
import re
import shutil
import socket
from typing import Any

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connection
from django.db.models import ForeignKey, UUIDField

HEX32 = "^[0-9a-fA-F]{32}$"
DASHED36 = "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
# Merge files of a bulk index build and the binary log of the UPDATE phase were measured at
# 1.6x to 2.46x the table (CDNX-6.2-FOLLOWUP REVIEWs, BECAS-HYG-010 REVIEWs): 2.5x covers both,
# with a thin margin. ROW_FORMAT=COMPRESSED tables exceed it on their size on disk, so they
# are scaled to their uncompressed size first (see Command.compression_scale)
SPACE_FACTOR = 2.5
SET_SQL_MODE = "SET SESSION sql_mode = %s"
# The narrowest UUID value: a row cannot take less, which exposes a stale size
UUID_BYTES = 32


def _filename(name: str) -> str:
    """How InnoDB spells a schema or table name in its tablespace list: ASCII characters
    other than letters, digits and "_" become "@" and four hex digits ("a-b" -> "a@002db").
    Non-ASCII names are encoded differently: they miss the lookup and keep the estimate."""
    return "".join(
        c if c.isascii() and (c.isalnum() or c == "_") else f"@{ord(c):04x}" for c in name
    )


def _device(path: str) -> int:
    """Filesystem id of a directory, so requirements on the same filesystem add up."""
    return os.stat(path).st_dev


class Command(BaseCommand):
    help = "Migrate UUID columns between CHAR(32) (hex) and CHAR(36) (dashed) formats."
    # Set by set_copy_bulk() when the global could not be put back: the run then exits 1
    restore_failed = False

    def add_arguments(self, parser):
        parser.add_argument(
            "--target",
            type=int,
            choices=[32, 36],
            default=36,
            help="Target length for UUID columns: 36 (dashed, standard) or "
            "32 (hex, compact). Default is 36.",
        )
        parser.add_argument(
            "--skip-space-check",
            action="store_true",
            help="Execute even if a directory of the database server has less free "
            "space than the estimate for the rebuilds and the UPDATE phase, when the "
            "server is on another host and its free space cannot be checked, or when "
            "the table statistics are stale.",
        )
        parser.add_argument(
            "--disable-copy-bulk",
            action="store_true",
            help="With --execute, run SET GLOBAL innodb_alter_copy_bulk=OFF (MariaDB, "
            "needs SUPER) before the table rebuilds and restore the previous value "
            "afterwards, so no merge-sort file is written in tmpdir.",
        )
        parser.add_argument(
            "--execute",
            action="store_true",
            help="DANGER: Actually execute the SQL queries against the "
            "database. If omitted, runs in DRY-RUN mode.",
        )

    def handle(  # pylint: disable=unused-argument,too-many-branches,too-many-locals,too-many-statements # noqa: E501
        self,
        *args: Any,
        **options: Any,
    ) -> None:
        target_length = options["target"]
        execute_mode = options["execute"]
        dry_run = not execute_mode

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"--- UUID Migration Tool (Target: CHAR({target_length})) ---",
            ),
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "MODE: DRY-RUN (Safe). No changes will be applied.",
                ),
            )
            self.stdout.write(
                self.style.WARNING(
                    "To apply changes, run again with '--execute'.",
                ),
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    "MODE: EXECUTE (Destructive). Changes WILL be applied to the database.",
                ),
            )

        if connection.vendor != "mysql":
            raise CommandError("This command is only designed for MySQL/MariaDB.")

        # Detect DB Version
        with connection.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0].lower()
            is_mariadb = "mariadb" in version
            db_type = "MariaDB" if is_mariadb else "MySQL"
            self.stdout.write(f"Detected Database: {db_type} ({version})")

        # Django's own criterion (MariaDB >= 10.7): where it writes dashed UUIDs the
        # columns must be CHAR(36), elsewhere it writes 32 hex characters. The wrong
        # target makes every lookup miss or every write fail with "Data too long"
        native = connection.features.has_native_uuid_field
        if target_length == 36 and not native:
            raise CommandError(
                f"--target 36 refused on {db_type} ({version}): Django stores UUIDs as 32 hex "
                "characters on this database, so dashed values would never match a lookup. "
                "Use --target 32 here; --target 36 is for MariaDB >= 10.7.",
            )
        if target_length == 32 and native:
            raise CommandError(
                f"--target 32 refused on {db_type} ({version}): Django stores UUIDs as 36 "
                "dashed characters on this database, so every write would fail with "
                "'Data too long'. Use --target 36 here; --target 32 is for MySQL and "
                "MariaDB < 10.7.",
            )

        columns = self.scan_columns(target_length)
        for col in columns:
            if col["malformed"]:
                # A planned column with such values blocks --execute: say so in the dry run
                refusal = " --execute refuses to run until they are fixed." if col["action"] else ""
                self.stdout.write(
                    self.style.WARNING(
                        f"{col['table']}.{col['column']}: {col['malformed']} values are neither "
                        "32 hex characters nor a dashed UUID: Django cannot read them, and this "
                        f"command does not convert them.{refusal}",
                    ),
                )
        operations = [col for col in columns if col["action"]]

        if not operations:
            self.stdout.write(
                self.style.SUCCESS(
                    f"All UUID fields are already compliant with CHAR({target_length}).",
                ),
            )
            return

        self.stdout.write(
            self.style.WARNING(
                f"\nFound {len(operations)} columns that need migration.",
            ),
        )
        malformed = [f"{op['table']}.{op['column']}" for op in operations if op["malformed"]]
        if malformed and execute_mode:
            raise CommandError(
                f"Refusing to execute: {', '.join(malformed)} hold values that are neither 32 hex "
                "characters nor a dashed UUID. Fix or remove them first; the conversion would "
                "leave them unreadable, or truncate them.",
            )

        counted: dict[str, int] = {}
        for op in operations:
            counted[op["table"]] = max(counted.get(op["table"], 0), op["rows"])
        copy_bulk = self.check_resources(
            sorted({op["table"] for op in operations if op["action"] == "alter"}),
            sorted({op["table"] for op in operations}),
            execute_mode and not options["skip_space_check"],
            options["disable_copy_bulk"],
            options["skip_space_check"],
            counted,
        )

        # SQL Generation
        sql_commands = []

        # Disable Foreign Keys constraints to allow altering types safely
        sql_commands.append("SET FOREIGN_KEY_CHECKS=0;")

        for op in operations:
            table = op["table"]
            col = op["column"]
            null_stmt = "NULL" if op["null"] else "NOT NULL"

            # Print the plan regardless of mode
            if op["action"] == "alter":
                self.stdout.write(
                    f"Plan: {op['model']} -> {table}.{col} ({op['current']} -> {target_length})",
                )
            else:
                self.stdout.write(
                    f"Plan: {op['model']} -> {table}.{col} (already CHAR({target_length}), "
                    f"{op['pending']} values still in the old format: half converted)",
                )

            alter = f"ALTER TABLE `{table}` MODIFY `{col}` CHAR({target_length}) {null_stmt};"
            if target_length == 36:
                # Widen first, then convert 32 hex to 36 dashed (Format: 8-4-4-4-12)
                if op["action"] == "alter":
                    sql_commands.append(alter)
                sql_commands.append(
                    f"""
                    UPDATE `{table}`
                    SET `{col}` = CONCAT(
                        SUBSTR(`{col}`, 1, 8), '-',
                        SUBSTR(`{col}`, 9, 4), '-',
                        SUBSTR(`{col}`, 13, 4), '-',
                        SUBSTR(`{col}`, 17, 4), '-',
                        SUBSTR(`{col}`, 21)
                    )
                    WHERE `{col}` REGEXP '{HEX32}';
                """,
                )
            elif target_length == 32:
                # Remove the dashes while the column is still wide, then narrow it:
                # narrowing first truncates every dashed value (or fails with 1265 in
                # strict mode) before the UPDATE can run
                sql_commands.append(
                    f"""
                    UPDATE `{table}`
                    SET `{col}` = REPLACE(`{col}`, '-', '')
                    WHERE `{col}` REGEXP '{DASHED36}';
                """,
                )
                if op["action"] == "alter":
                    sql_commands.append(alter)

        # Re-enable Foreign Keys: run in a finally on --execute, so a failed statement
        # cannot leave the session (reused by a caller of call_command) with them off
        fk_on = "SET FOREIGN_KEY_CHECKS=1;"

        # 4. Execution or Preview
        if dry_run:
            self.stdout.write(
                self.style.MIGRATE_HEADING("\n--- SQL PREVIEW (Dry Run) ---"),
            )
            self.stdout.write(
                "These commands will NOT be executed unless you use --execute",
            )
            self.stdout.write(
                "With --execute they run with STRICT_ALL_TABLES added to the session sql_mode.",
            )
            for sql in [*sql_commands, fk_on]:
                # Clean formatting for printing
                clean_sql = " ".join(sql.split())
                print(f"{clean_sql}")
            self.stdout.write(
                self.style.WARNING("\nDone. No changes were applied."),
            )
            return

        self.stdout.write(
            self.style.MIGRATE_HEADING("\n--- EXECUTING MIGRATION ---"),
        )
        # Only switched off when it is ON: nothing to restore otherwise
        restore_copy_bulk = options["disable_copy_bulk"] and copy_bulk == "ON"
        if restore_copy_bulk:
            self.set_copy_bulk("OFF")
        self.restore_failed = False
        failure: tuple[str, Exception | KeyboardInterrupt] | None = None
        restore_errors: list[str] = []
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT @@SESSION.sql_mode")
                sql_mode = cursor.fetchone()[0]
                # A value that does not fit must stop the run, not be truncated, also on a
                # server configured without strict mode
                cursor.execute(
                    SET_SQL_MODE,
                    [",".join(filter(None, [sql_mode, "STRICT_ALL_TABLES"]))],
                )
                try:
                    # MySQL DDL commits implicitly, so statement by statement
                    for sql in sql_commands:
                        try:
                            cursor.execute(sql)
                        # Ctrl-C reaches Python only once the server has finished the
                        # statement in progress: report it like a failure, not a traceback
                        except (Exception, KeyboardInterrupt) as e:  # pylint: disable=broad-except
                            failure = (" ".join(sql.split()), e)
                            break
                finally:
                    # Each restore on its own: one failing must not skip the other
                    restores = (
                        (fk_on, None, fk_on.rstrip(";")),
                        (SET_SQL_MODE, [sql_mode], f"SET SESSION sql_mode = '{sql_mode}'"),
                    )
                    for statement, params, shown in restores:
                        try:
                            cursor.execute(statement, params)
                        except Exception as e:  # pylint: disable=broad-except
                            restore_errors.append(f"{shown}: {e}")
        finally:
            if restore_errors or (
                failure is not None and isinstance(failure[1], KeyboardInterrupt)
            ):
                # The session may be out of sync or left half restored: drop it, so the
                # global restore, the report and any later caller get a fresh one
                connection.close()
            if restore_copy_bulk:
                self.set_copy_bulk("ON")

        for error_text in restore_errors:
            self.stdout.write(self.style.ERROR(f"Could not restore the session: {error_text}"))
        if failure is not None:
            statement, error = failure
            interrupted = isinstance(error, KeyboardInterrupt)
            if interrupted:
                self.stdout.write(self.style.ERROR(f"Interrupted while running: {statement}"))
                self.stdout.write(
                    "The server finishes a statement it has started, so this one may have "
                    "completed: the state below says where the run stopped.",
                )
            else:
                self.stdout.write(self.style.ERROR(f"CRITICAL ERROR executing migration: {error}"))
                self.stdout.write(f"Failed statement: {statement}")
            self.report_state(target_length)
            # A cut ALTER or UPDATE leaves the statistics behind the data
            self.stdout.write(
                "If the next run reports stale statistics, run ANALYZE TABLE on the tables "
                "listed as not or half converted first.",
            )
            raise CommandError(
                f"Migration {'interrupted' if interrupted else 'failed'}; the columns listed as "
                "not or half converted are still pending. "
                f"{'Run' if interrupted else 'Fix the cause and run'} the command again: it "
                "resumes them.",
            ) from error
        if restore_errors:
            raise CommandError(
                "Migration completed, but the session could not be restored (see above); the "
                "connection was closed.",
            )
        if self.restore_failed:
            raise CommandError(
                "Migration completed, but innodb_alter_copy_bulk could not be restored (see "
                "above).",
            )
        self.stdout.write(
            self.style.SUCCESS("Migration completed successfully."),
        )

    def report_state(self, target_length: int) -> None:
        """Where a failed or interrupted run stopped, column by column."""
        self.stdout.write("State of every UUID column now:")
        try:
            columns = self.scan_columns(target_length)
        except Exception as e:  # pylint: disable=broad-except
            # A dead connection must not hide the failure reported above
            self.stdout.write(self.style.ERROR(f"  could not read the column state: {e}"))
            return
        for col in columns:
            if col["action"] == "alter":
                state = f"not converted (CHAR({col['current']}))"
            elif col["action"] == "update":
                state = f"half converted ({col['pending']} values in the old format)"
            else:
                state = "converted"
            self.stdout.write(f"  {col['table']}.{col['column']}: {state}")

    def scan_columns(self, target_length: int) -> list[dict[str, Any]]:
        """Every UUID column with its type and what its values look like.

        action is "alter" when the column type has the wrong length, "update" when the
        type is right but values in the old format remain (a run cut after the ALTER),
        None when nothing is left to do. A native uuid column (MariaDB >= 10.7) is
        compliant for --target 36.
        """
        columns = []
        seen: set[tuple[str, str]] = set()
        with connection.cursor() as cursor:
            for model in apps.get_models():
                table_name = model._meta.db_table  # pylint: disable=protected-access
                for field in model._meta.get_fields():  # pylint: disable=protected-access
                    # Identify UUID fields (PKs, direct fields or FKs to UUIDs)
                    if not hasattr(field, "column"):
                        continue
                    if not (
                        isinstance(field, UUIDField)
                        or (
                            isinstance(field, ForeignKey)
                            and isinstance(field.target_field, UUIDField)
                        )
                    ):
                        continue
                    column = str(field.column)  # pyright: ignore[reportAttributeAccessIssue]
                    # Unmanaged models mapped to the same table would plan it twice
                    if (table_name, column) in seen:
                        continue
                    seen.add((table_name, column))
                    cursor.execute(
                        """
                        SELECT DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
                        FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA = DATABASE()
                          AND TABLE_NAME = %s
                          AND COLUMN_NAME = %s
                    """,
                        [table_name, column],
                    )
                    result = cursor.fetchone()
                    if not result:
                        continue
                    data_type, current_length = result
                    if str(data_type).lower() == "uuid":
                        # The type Django itself creates: values are always valid UUIDs
                        continue
                    cursor.execute(
                        f"SELECT COUNT(`{column}`), "
                        f"COALESCE(SUM(`{column}` REGEXP '{HEX32}'), 0), "
                        f"COALESCE(SUM(`{column}` REGEXP '{DASHED36}'), 0) "
                        f"FROM `{table_name}`",
                    )
                    values, hex32, dashed = (int(n) for n in cursor.fetchone())
                    pending = hex32 if target_length == 36 else dashed
                    if current_length != target_length:
                        action = "alter"
                    elif pending:
                        action = "update"
                    else:
                        action = None
                    columns.append(
                        {
                            "model": model.__name__,
                            "table": table_name,
                            "column": column,
                            "current": current_length,
                            "null": field.null,
                            "pending": pending,
                            "malformed": values - hex32 - dashed,
                            # A lower bound of the table's rows, to spot stale statistics
                            "rows": values,
                            "action": action,
                        },
                    )
        return columns

    def set_copy_bulk(self, value: str) -> None:
        """SET GLOBAL innodb_alter_copy_bulk: it has no session scope, so this
        affects every session of the server until it is set back, and a process
        killed before the restore leaves it as it is (the change is not
        persisted: a server restart resets it)."""
        statement = f"SET GLOBAL innodb_alter_copy_bulk={value}"
        try:
            with connection.cursor() as cursor:
                cursor.execute(statement)
        except Exception as e:  # noqa: BLE001 - any driver error; the cause is in the message
            manual = f'sudo mariadb -e "{statement}"'
            if value == "OFF":
                raise CommandError(
                    f"{statement} failed ({e}): the database user lacks the privilege "
                    f"(SUPER). Run it by hand before --execute, e.g. {manual}, and "
                    "SET GLOBAL innodb_alter_copy_bulk=ON afterwards.",
                ) from e
            self.stdout.write(
                self.style.ERROR(
                    f"{statement} failed ({e}): innodb_alter_copy_bulk is still OFF for every "
                    f"session of the server. Restore it by hand: {manual}",
                ),
            )
            self.restore_failed = True
            return
        self.stdout.write(f"{statement} done.")

    def server_is_local(self, hostname: str) -> bool:
        """Whether the server's directories are this host's: a socket or loopback
        connection to a server reporting this host's name. A path that merely exists
        here is no proof (another machine, a container, a mount namespace)."""
        host = str(connection.settings_dict.get("HOST") or "")
        if not (host == "" or host.startswith("/") or host in ("localhost", "127.0.0.1", "::1")):
            return False
        return (
            str(hostname).split(".", maxsplit=1)[0]
            == socket.gethostname().split(".", maxsplit=1)[0]
        )

    def check_resources(
        self,
        rebuilt: list[str],
        updated: list[str],
        refuse_without_space: bool,
        disable_copy_bulk: bool,
        skip_space_check: bool = False,
        counted: dict[str, int] | None = None,
    ) -> str | None:
        """Estimate the disk the run needs per directory of the server and compare
        it with what is free, when those directories are on this host. Returns the
        value of innodb_alter_copy_bulk, or None where the variable does not exist.

        - Data directory: ALTER ... MODIFY runs with ALGORITHM=COPY and copies each
          rebuilt table next to the original: the sum of those tables (the copies are
          sequential, so this is conservative).
        - Temporary directory (every one of a colon-separated tmpdir): with
          innodb_alter_copy_bulk=ON (MariaDB 10.11.9, 11.4.3 and later) the copy builds
          the indexes through merge-sort files there, SPACE_FACTOR times the largest
          rebuilt table; with a ROW binary log the UPDATE phase spills its transaction
          cache there too, SPACE_FACTOR times the largest updated table.
        - Binary log directory: with a ROW binary log, SPACE_FACTOR times the sum of
          the updated tables.
        Directories on the same filesystem add their requirements up. A table's size is
        its tablespace file when readable (current after an import), else the estimate of
        information_schema.TABLES, refused under --execute when it is stale; a
        ROW_FORMAT=COMPRESSED table counts uncompressed for merge files and binary log.
        """
        tables = sorted(set(rebuilt) | set(updated))
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT TABLE_NAME, TABLE_ROWS, DATA_LENGTH + INDEX_LENGTH, ROW_FORMAT,
                       CREATE_OPTIONS
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN %s
                """,
                [tuple(tables)],
            )
            stats = {
                str(name): (int(rows or 0), int(size or 0), str(fmt or ""), str(opts or ""))
                for name, rows, size, fmt, opts in cursor.fetchall()
            }
            cursor.execute(
                "SHOW VARIABLES WHERE Variable_name IN ('datadir', 'tmpdir', 'hostname', "
                "'log_bin', 'log_bin_basename', 'binlog_format', 'innodb_alter_copy_bulk', "
                "'innodb_page_size')",
            )
            variables = {str(name): str(value) for name, value in cursor.fetchall()}
        files = self.file_sizes(tables)
        page_size = int(variables.get("innodb_page_size") or 16384)

        # On-disk size (what the copy in the data directory takes) and the uncompressed
        # size (what the merge files and the binary log are proportional to)
        sizes: dict[str, int] = {}
        expanded: dict[str, int] = {}
        stale: list[tuple[str, str]] = []
        for table in tables:
            rows, estimate, row_format, create_options = stats.get(table, (0, 0, "", ""))
            sizes[table] = max(estimate, files.get(table, 0))
            scale = self.compression_scale(row_format, create_options, page_size)
            expanded[table] = int(sizes[table] * scale)
            line = f"Size: {table}: ~{rows} rows, {self.human(sizes[table])}"
            if scale > 1:
                line += (
                    f" (ROW_FORMAT=COMPRESSED: counted as {self.human(expanded[table])} for "
                    "merge files and the binary log)"
                )
            self.stdout.write(line)
            # Without the file size, figures far below the rows just counted mean an import
            # not yet analyzed. MariaDB keeps TABLE_ROWS current while DATA_LENGTH waits for
            # ANALYZE (seen on 11.8.6), so the size is checked too: a row holds its UUID
            rows_counted = (counted or {}).get(table, 0)
            if table not in files and (
                2 * rows < rows_counted or estimate < UUID_BYTES * rows_counted
            ):
                stale.append(
                    (
                        table,
                        f"{table} ({self.human(estimate)} and ~{rows} rows reported, "
                        f"{rows_counted} rows counted)",
                    ),
                )
        row_binlog = variables.get("log_bin", "").upper() in ("ON", "1") and (
            variables.get("binlog_format", "").upper() == "ROW"
        )
        # A size only matters where it feeds a requirement: a rebuild, or the binary log
        # of an UPDATE in ROW format. Otherwise asking for ANALYZE would only block a resume
        measured = set(rebuilt) | (set(updated) if row_binlog else set())
        if any(table not in files for table in measured):
            self.stdout.write(
                "Sizes without a tablespace file size (it needs the PROCESS privilege) are "
                "InnoDB estimates; right after an import they can be far too low: run "
                "ANALYZE TABLE on these tables first.",
            )
        relevant = [text for table, text in stale if table in measured]
        if relevant:
            message = (
                f"Stale statistics: {', '.join(relevant)}. Sizes that low cannot check the disk. "
                "Run ANALYZE TABLE on these tables first, or run with --skip-space-check to "
                "proceed anyway."
            )
            if refuse_without_space:
                raise CommandError(message)
            self.stdout.write(self.style.WARNING(message))
        rebuilt_sizes = [sizes[table] for table in rebuilt]
        rebuilt_expanded = [expanded[table] for table in rebuilt]
        updated_sizes = [expanded[table] for table in updated]
        self.stdout.write(
            f"Estimated space needed for the rebuilds: {self.human(sum(rebuilt_sizes))}",
        )

        bulk = variables.get("innodb_alter_copy_bulk")
        # Only an ALTER builds indexes: with half-converted columns alone the variable is moot
        bulk_on = bool(rebuilt) and bulk is not None and bulk.upper() in ("ON", "1")
        # (what, directory, bytes needed); entries sharing a key take the largest
        needs: list[tuple[str, str, int]] = [
            ("data directory", variables.get("datadir", ""), sum(rebuilt_sizes)),
        ]
        tmp_need = 0
        if bulk_on and disable_copy_bulk:
            self.stdout.write(
                "innodb_alter_copy_bulk is ON: --disable-copy-bulk switches it off for the "
                "rebuilds (SET GLOBAL, needs SUPER) and restores it afterwards.",
            )
        elif bulk_on:
            self.stdout.write(
                "innodb_alter_copy_bulk is ON: each rebuild also writes merge-sort files of "
                f"up to {SPACE_FACTOR}x the table in tmpdir.",
            )
            tmp_need = int(SPACE_FACTOR * max(rebuilt_expanded, default=0))
        if row_binlog:
            self.stdout.write(
                "Binary log is ON in ROW format: the UPDATE phase logs every converted row "
                f"(up to {SPACE_FACTOR}x the table) and spills its transaction cache to tmpdir.",
            )
            tmp_need = max(tmp_need, int(SPACE_FACTOR * max(updated_sizes, default=0)))
            needs.append(
                (
                    "binary log directory",
                    os.path.dirname(variables.get("log_bin_basename", "")),
                    int(SPACE_FACTOR * sum(updated_sizes)),
                ),
            )
        if tmp_need:
            needs += [
                ("temporary directory", path, tmp_need)
                for path in variables.get("tmpdir", "").split(":")
                if path
            ]

        workaround = (
            " Or switch innodb_alter_copy_bulk off for the rebuilds, so the copy inserts "
            "row by row with no merge files: --disable-copy-bulk if the database user has "
            "SUPER, else SET GLOBAL innodb_alter_copy_bulk=OFF by hand before --execute "
            "(and =ON afterwards)."
            if bulk_on and not disable_copy_bulk
            else ""
        )
        needs = [need for need in needs if need[2] > 0]
        if not self.server_is_local(variables.get("hostname", "")):
            server = variables.get("hostname", "?")
            unchecked = "; ".join(
                f"{what} {directory}: {self.human(needed)}" for what, directory, needed in needs
            )
            # What cannot be measured is not assumed to fit: a full disk mid-run on a
            # remote server fails the same way as on this one. No bulk workaround here:
            # switching it off leaves the data directory need, so only the flag lifts this
            if needs and refuse_without_space:
                raise CommandError(
                    f"Cannot check free space: the database server ({server}) is not this "
                    f"host. Check by hand the free space it needs ({unchecked}), then run "
                    "again with --skip-space-check.",
                )
            # Asking for the flag the user already gave would be noise
            requirement = (
                ""
                if skip_space_check
                else "; --execute on another host requires --skip-space-check"
            )
            for what, directory, needed in needs:
                self.stdout.write(
                    self.style.WARNING(
                        f"Cannot check free space: the database server ({server}) is not this "
                        f"host. Check that its {what} {directory} has {self.human(needed)} "
                        f"free{requirement}.",
                    ),
                )
            return "ON" if bulk_on else None

        groups: dict[int, dict[str, tuple[str, int]]] = {}
        for what, directory, needed in needs:
            if not os.path.isdir(directory):
                self.stdout.write(
                    self.style.WARNING(
                        f"Cannot check free space: {what} {directory} not found on this host. "
                        f"Check that it has {self.human(needed)} free before running with "
                        "--execute.",
                    ),
                )
                continue
            group = groups.setdefault(_device(directory), {})
            known = group.get(what)
            if known is None or needed > known[1]:
                group[what] = (directory, needed)
        for group in groups.values():
            self.check_free_space(group, refuse_without_space, workaround)
        return "ON" if bulk_on else None

    def file_sizes(self, tables: list[str]) -> dict[str, int]:
        """Size of each table's tablespace file, current even right after an import,
        unlike the statistics of information_schema.TABLES. Empty without the PROCESS
        privilege the view needs, and for tables outside a file of their own."""
        # Attribute of Django's MySQL backend only, which handle() has already required
        mariadb = getattr(connection, "mysql_is_mariadb", False)
        view = "INNODB_SYS_TABLESPACES" if mariadb else "INNODB_TABLESPACES"
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT DATABASE()")
                schema = str(cursor.fetchone()[0])
                # MariaDB lists encoded names, MySQL 8.0 plain ones (REVIEW 4): ask for both
                names = {f"{_filename(schema)}/{_filename(table)}": table for table in tables}
                names.update({f"{schema}/{table}": table for table in tables})
                cursor.execute(
                    f"SELECT NAME, FILE_SIZE FROM information_schema.{view} WHERE NAME IN %s",
                    [tuple(names)],
                )
                return {
                    names[str(name)]: int(size or 0)
                    for name, size in cursor.fetchall()
                    if str(name) in names
                }
        except DatabaseError:
            return {}

    @staticmethod
    def compression_scale(row_format: str, create_options: str, page_size: int) -> float:
        """How much larger than on disk the rows of a table are once uncompressed.

        ROW_FORMAT=COMPRESSED packs each page into KEY_BLOCK_SIZE (half a page unless
        given), while merge files and the binary log hold the rows uncompressed: on
        10.11.14 and 11.8.6, with a highly compressible 200-character text per row, they
        reached 4.2x (default), 8.4x (4K) and 18.4x (1K) the size on disk, and 1.1x to
        2.1x once scaled by page size / KEY_BLOCK_SIZE; less compressible rows stay lower.
        """
        compressed = row_format.lower() == "compressed" or (
            "row_format=compressed" in create_options.lower()
        )
        if not compressed:
            return 1.0
        match = re.search(r"key_block_size=(\d+)", create_options, re.IGNORECASE)
        block = int(match.group(1)) * 1024 if match and int(match.group(1)) else page_size // 2
        return max(1.0, page_size / block)

    def check_free_space(
        self,
        group: dict[str, tuple[str, int]],
        refuse: bool,
        workaround: str,
    ) -> None:
        """One filesystem: the requirements of every directory on it add up."""
        directory = next(iter(group.values()))[0]
        needed = sum(need for _, need in group.values())
        free = shutil.disk_usage(directory).free
        self.stdout.write(f"Free space in {directory}: {self.human(free)}")
        if free >= needed:
            return
        where = " and ".join(f"{what} {path}" for what, (path, _) in group.items())
        shared = " (same filesystem)" if len(group) > 1 else ""
        message = (
            f"Not enough free space in {where}{shared}: {self.human(free)} free, "
            f"{self.human(needed)} needed. Free some space, or run with --skip-space-check "
            f"to proceed anyway.{workaround if 'temporary' in where else ''}"
        )
        if refuse:
            raise CommandError(message)
        self.stdout.write(self.style.WARNING(message))

    @staticmethod
    def human(size: int) -> str:
        value = float(size)
        for unit in ("B", "KiB", "MiB", "GiB"):
            if value < 1024:
                return f"{value:.1f} {unit}"
            value /= 1024
        return f"{value:.1f} TiB"
