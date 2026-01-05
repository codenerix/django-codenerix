from django.apps import apps  # type: ignore # pylint: disable=import-error
from django.core.management.base import (  # type: ignore # pylint: disable=import-error # noqa: E501
    BaseCommand,
)
from django.db import connection  # type: ignore # pylint: disable=import-error
from django.db.models import (  # type: ignore # pylint: disable=import-error # noqa: E501
    ForeignKey,
    UUIDField,
)


class Command(BaseCommand):
    help = (
        "Migrate UUID columns between CHAR(32) (hex) and "
        "CHAR(36) (dashed) formats."
    )

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
                    "MODE: EXECUTE (Destructive). Changes WILL be "
                    "applied to the database.",
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

        # Scan models
        all_models = apps.get_models()
        operations = []

        with connection.cursor() as cursor:
            for model in all_models:
                table_name = (
                    model._meta.db_table  # pylint: disable=protected-access
                )

                for (
                    field
                ) in (
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
                            [table_name, field.column],
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
                                    "column": field.column,
                                    "current": current_length,
                                    "target": target_length,
                                    "null": field.null,
                                },
                            )

        if not operations:
            self.stdout.write(
                self.style.SUCCESS(
                    "All UUID fields are already "
                    f"compliant with CHAR({target_length}).",
                ),
            )
            return

        self.stdout.write(
            self.style.WARNING(
                f"\nFound {len(operations)} columns that need migration.",
            ),
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
                f"Plan: {op['model']} -> {table}.{col} "
                f"({op['current']} -> {op['target']})",
            )

            # A. Alter Table Structure
            sql_commands.append(
                f"ALTER TABLE `{table}` MODIFY `{col}` "
                f"CHAR({target_length}) {null_stmt};",
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
            try:
                with connection.cursor() as cursor:
                    # Execute mostly atomically? MySQL DDL causes implicit
                    # commit, so we execute statement by statement
                    for sql in sql_commands:
                        cursor.execute(sql)
                self.stdout.write(
                    self.style.SUCCESS("Migration completed successfully."),
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"CRITICAL ERROR executing migration: {e}",
                    ),
                )
                self.stdout.write(
                    "Note: Some ALTER statements might have "
                    "succeeded before the error.",
                )
                # Note: Due to MySQL implicit commits on DDL, rollback might
                # not be fully possible if it failed halfway through an ALTER
