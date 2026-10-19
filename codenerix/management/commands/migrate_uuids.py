import os
import shutil

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.models import ForeignKey, UUIDField


class Command(BaseCommand):
    help = "Migrate UUID columns between CHAR(32) (hex) and CHAR(36) (dashed) formats."

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
            help="Execute even if the database's data directory has less free "
            "space than the estimated size of the table rebuilds.",
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
        *args,
        **options,
    ):
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
            self.stdout.write(
                self.style.ERROR(
                    "Error: This command is only designed for MySQL/MariaDB.",
                ),
            )
            return

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

        # Scan models
        all_models = apps.get_models()
        operations = []

        with connection.cursor() as cursor:
            for model in all_models:
                table_name = (
                    model._meta.db_table  # pylint: disable=protected-access
                )

                for field in (
                    model._meta.get_fields()  # pylint: disable=protected-access # noqa: E501
                ):
                    # Identify UUID fields (PKs, direct fields or FKs to UUIDs)
                    if not hasattr(field, "column"):
                        continue

                    is_candidate = False
                    if isinstance(field, UUIDField):
                        is_candidate = True
                    elif isinstance(field, ForeignKey) and isinstance(
                        field.target_field,
                        UUIDField,
                    ):
                        is_candidate = True

                    if is_candidate:
                        # Inspect current schema
                        cursor.execute(
                            """
                            SELECT COLUMN_TYPE, CHARACTER_MAXIMUM_LENGTH
                            FROM information_schema.COLUMNS
                            WHERE TABLE_SCHEMA = DATABASE()
                              AND TABLE_NAME = %s
                              AND COLUMN_NAME = %s
                        """,
                            [table_name, field.column],  # pyright: ignore[reportAttributeAccessIssue]
                        )

                        result = cursor.fetchone()
                        if not result:
                            continue

                        _, current_length = result

                        # Logic to decide if migration is needed
                        if current_length != target_length:
                            operations.append(
                                {
                                    "model": model.__name__,
                                    "table": table_name,
                                    "column": field.column,  # pyright: ignore[reportAttributeAccessIssue]
                                    "current": current_length,
                                    "target": target_length,
                                    "null": field.null,
                                },
                            )

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

        copy_bulk = self.check_resources(
            sorted({op["table"] for op in operations}),
            execute_mode and not options["skip_space_check"],
            options["disable_copy_bulk"],
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
            self.stdout.write(
                f"Plan: {op['model']} -> {table}.{col} ({op['current']} -> {op['target']})",
            )

            # A. Alter Table Structure
            sql_commands.append(
                f"ALTER TABLE `{table}` MODIFY `{col}` CHAR({target_length}) {null_stmt};",
            )

            # B. Convert Data
            if target_length == 36:
                # Convert 32 hex to 36 dashed (Format: 8-4-4-4-12)
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
                    WHERE CHAR_LENGTH(`{col}`) = 32;
                """,
                )
            elif target_length == 32:
                # Convert 36 dashed to 32 hex (Remove dashes)
                sql_commands.append(
                    f"""
                    UPDATE `{table}`
                    SET `{col}` = REPLACE(`{col}`, '-', '')
                    WHERE CHAR_LENGTH(`{col}`) = 36;
                """,
                )

        # Re-enable Foreign Keys
        sql_commands.append("SET FOREIGN_KEY_CHECKS=1;")

        # 4. Execution or Preview
        if dry_run:
            self.stdout.write(
                self.style.MIGRATE_HEADING("\n--- SQL PREVIEW (Dry Run) ---"),
            )
            self.stdout.write(
                "These commands will NOT be executed unless you use --execute",
            )
            for sql in sql_commands:
                # Clean formatting for printing
                clean_sql = " ".join(sql.split())
                print(f"{clean_sql}")
            self.stdout.write(
                self.style.WARNING("\nDone. No changes were applied."),
            )
        else:
            self.stdout.write(
                self.style.MIGRATE_HEADING("\n--- EXECUTING MIGRATION ---"),
            )
            # Only switched off when it is ON: nothing to restore otherwise
            restore_copy_bulk = options["disable_copy_bulk"] and copy_bulk == "ON"
            if restore_copy_bulk:
                self.set_copy_bulk("OFF")
            try:
                with connection.cursor() as cursor:
                    # Execute mostly atomically? MySQL DDL causes implicit
                    # commit, so we execute statement by statement
                    for sql in sql_commands:
                        cursor.execute(sql)
                self.stdout.write(
                    self.style.SUCCESS("Migration completed successfully."),
                )
            except Exception as e:  # pylint: disable=broad-except
                self.stdout.write(
                    self.style.ERROR(
                        f"CRITICAL ERROR executing migration: {e}",
                    ),
                )
                self.stdout.write(
                    "Note: Some ALTER statements might have succeeded before the error.",
                )
                # Note: Due to MySQL implicit commits on DDL, rollback might
                # not be fully possible if it failed halfway through an ALTER
            finally:
                if restore_copy_bulk:
                    self.set_copy_bulk("ON")

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
            return
        self.stdout.write(f"{statement} done.")

    def check_resources(
        self,
        tables: list[str],
        refuse_without_space: bool,
        disable_copy_bulk: bool,
    ) -> str | None:
        """Estimate the disk the table rebuilds need and compare it with what is
        free, when the server's directories are on this host. Returns the value
        of innodb_alter_copy_bulk, or None where the variable does not exist.

        ALTER ... MODIFY runs with ALGORITHM=COPY: each table is copied next to
        the original in the data directory, so the run needs about the sum of
        the table sizes there (conservative: the copies are sequential and each
        original is freed afterwards). With innodb_alter_copy_bulk=ON (MariaDB
        11.x default) the copy also builds the indexes through a merge-sort file
        in innodb_tmpdir (tmpdir by default) that grows with the table being
        rebuilt: on a tmpfs /tmp it fills up and the ALTER aborts.
        """
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT TABLE_NAME, TABLE_ROWS, DATA_LENGTH + INDEX_LENGTH
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN %s
                """,
                [tuple(tables)],
            )
            sizes = {name: (rows or 0, size or 0) for name, rows, size in cursor.fetchall()}
            cursor.execute("SELECT @@datadir, @@tmpdir")
            datadir, tmpdir = cursor.fetchone()
            cursor.execute("SHOW VARIABLES LIKE 'innodb_alter_copy_bulk'")
            bulk = cursor.fetchone()
            bulk_on = bulk is not None and str(bulk[1]).upper() == "ON"
            if bulk_on:
                cursor.execute("SHOW VARIABLES LIKE 'innodb_tmpdir'")
                innodb_tmpdir = cursor.fetchone()
                if innodb_tmpdir is not None and innodb_tmpdir[1]:
                    tmpdir = innodb_tmpdir[1]

        total = 0
        largest = 0
        for table in tables:
            rows, size = sizes.get(table, (0, 0))
            total += size
            largest = max(largest, size)
            self.stdout.write(f"Size: {table}: ~{rows} rows, {self.human(size)}")
        self.stdout.write(f"Estimated space needed for the rebuilds: {self.human(total)}")

        self.check_free_space("data directory", datadir, total, refuse_without_space, "")
        if bulk_on and disable_copy_bulk:
            self.stdout.write(
                "innodb_alter_copy_bulk is ON: --disable-copy-bulk switches it off for the "
                "rebuilds (SET GLOBAL, needs SUPER) and restores it afterwards.",
            )
        elif bulk_on:
            self.stdout.write(
                "innodb_alter_copy_bulk is ON: each rebuild also writes a merge-sort file of "
                f"about the table size in {tmpdir}.",
            )
            self.check_free_space(
                "temporary directory",
                tmpdir,
                largest,
                refuse_without_space,
                " Or switch innodb_alter_copy_bulk off for the rebuilds, so the copy inserts "
                "row by row with no merge file: --disable-copy-bulk if the database user has "
                "SUPER, else SET GLOBAL innodb_alter_copy_bulk=OFF by hand before --execute "
                "(and =ON afterwards).",
            )
        return None if bulk is None else str(bulk[1]).upper()

    def check_free_space(
        self,
        what: str,
        directory: str,
        needed: int,
        refuse: bool,
        workaround: str,
    ) -> None:
        if not os.path.isdir(directory):
            self.stdout.write(
                self.style.WARNING(
                    f"Cannot check free space: {what} {directory} is not on this host. "
                    f"Check that it has {self.human(needed)} free before running with --execute.",
                ),
            )
            return
        free = shutil.disk_usage(directory).free
        self.stdout.write(f"Free space in {directory}: {self.human(free)}")
        if free >= needed:
            return
        message = (
            f"Not enough free space in {what} {directory}: {self.human(free)} free, "
            f"{self.human(needed)} needed. Free some space, or run with --skip-space-check "
            f"to proceed anyway.{workaround}"
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
