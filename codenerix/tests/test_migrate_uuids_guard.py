"""migrate_uuids against a fake MySQL/MariaDB connection: target guards, the
data-aware plan, exit codes, the strict session sql_mode, the resource check
and --disable-copy-bulk."""

import re
import socket
from io import StringIO
from types import SimpleNamespace
from typing import Any

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError
from django.db.models import UUIDField

from codenerix.management.commands import migrate_uuids

MARIADB = "11.8.6-MariaDB-ubu2404"
MYSQL = "8.0.21"
GIB = 1024**3
SET_OFF = "SET GLOBAL innodb_alter_copy_bulk=OFF"
SET_ON = "SET GLOBAL innodb_alter_copy_bulk=ON"


class _Server:
    """What the fake database answers.

    columns: table -> (DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, non-null values,
    32-hex values, dashed values), or (DATA_TYPE, length, [the values]) to have the
    counts computed from the REGEXPs the command sends; sizes: table -> (rows, bytes);
    formats: table -> (ROW_FORMAT, CREATE_OPTIONS); files: table -> tablespace file
    size, None for a user without PROCESS; variables: what SHOW VARIABLES holds."""

    def __init__(
        self,
        version: str,
        columns: dict[str, tuple[Any, ...]],
        sizes: dict[str, tuple[int, int]],
        variables: dict[str, str],
    ) -> None:
        self.version = version
        self.columns = columns
        self.sizes = sizes
        self.formats: dict[str, tuple[str, str]] = {}
        self.files: dict[str, int] | None = None
        self.encoded_names = True
        self.variables = variables
        self.sql_mode = "NO_ENGINE_SUBSTITUTION"
        self.log: list[str] = []
        self.params: list[Any] = []
        # Statements containing any of these texts raise, like a privilege or a DDL error
        self.fail_on: str | tuple[str, ...] | None = None
        # A statement containing this text raises KeyboardInterrupt once it has run, as
        # Ctrl-C reaches Python when the server returns
        self.interrupt_on: str | None = None


class _Cursor:
    def __init__(self, server: _Server) -> None:
        self.server = server
        self._last = ""
        self._params: Any = None

    def __enter__(self) -> "_Cursor":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def execute(self, sql: str, params: Any = None) -> None:
        self._last = " ".join(sql.split())
        self._params = params
        self.server.log.append(self._last)
        self.server.params.append(params)
        fail_on = self.server.fail_on
        texts = (fail_on,) if isinstance(fail_on, str) else (fail_on or ())
        # Matched against the parameters too, to fail one of two statements with equal SQL
        if any(text in f"{self._last} {params!r}" for text in texts):
            raise RuntimeError(f"(1227, 'Access denied') on {self._last}")
        if self.server.interrupt_on and self.server.interrupt_on in self._last:
            raise KeyboardInterrupt
        if "TABLESPACES" in self._last and self.server.files is None:
            raise DatabaseError("(1227, 'Access denied; you need the PROCESS privilege')")

    def fetchone(self) -> tuple[Any, ...] | None:
        if "VERSION()" in self._last:
            return (self.server.version,)
        if "information_schema.COLUMNS" in self._last:
            spec = self.server.columns.get(self._params[0])
            return None if spec is None else spec[:2]
        if self._last.startswith("SELECT COUNT("):
            table = self._last.rsplit("FROM `", 1)[1].rstrip("`")
            spec = self.server.columns[table]
            if len(spec) == 5:
                return spec[2:]
            # Values given: classify them with the patterns of the query itself. Python's "$"
            # accepts a trailing newline, as MariaDB's and MySQL's do (REVIEW 4)
            patterns = re.findall(r"REGEXP '([^']*)'", self._last)
            values = [v for v in spec[2] if v is not None]
            return (len(values), *(sum(bool(re.search(p, v)) for v in values) for p in patterns))
        if self._last == "SELECT DATABASE()":
            return ("testdb",)
        if "@@SESSION.sql_mode" in self._last:
            return (self.server.sql_mode,)
        # The queries of 6.3.1, so the negative control fails on behaviour, not on the fake
        if self._last == "SELECT @@datadir, @@tmpdir":
            return (self.server.variables["datadir"], self.server.variables["tmpdir"])
        if self._last.startswith("SHOW VARIABLES LIKE"):
            name = self._last.split("'")[1]
            value = self.server.variables.get(name)
            return None if value is None else (name, value)
        return None

    def fetchall(self) -> list[tuple[Any, ...]]:
        if "information_schema.TABLES" in self._last:
            wanted = self._params[0]
            # 6.3.2 asked for three columns: answered too, so its negative control fails on
            # behaviour, not on the fake
            extra = "ROW_FORMAT" in self._last
            return [
                (t, rows, size, *(self.server.formats.get(t, ("Dynamic", "")) if extra else ()))
                for t, (rows, size) in self.server.sizes.items()
                if t in wanted
            ]
        if "TABLESPACES" in self._last:
            wanted = self._params[0]
            files = self.server.files or {}
            # MariaDB lists encoded names, MySQL 8.0 plain ones
            spell = migrate_uuids._filename if self.server.encoded_names else str
            names = {f"testdb/{spell(t)}": size for t, size in files.items()}
            return [(name, size) for name, size in names.items() if name in wanted]
        if self._last.startswith("SHOW VARIABLES WHERE"):
            # Only the names the query asks for, as the server does
            names = re.findall(r"'([^']+)'", self._last.split(" IN ", 1)[1])
            return [(k, v) for k, v in self.server.variables.items() if k in names]
        if self._last.startswith("SHOW VARIABLES"):
            return list(self.server.variables.items())
        return []


def _uuid_model(name: str, table: str) -> type:
    # The test settings install no model with a UUIDField: a stand-in with a real field
    field = UUIDField(null=False)
    field.set_attributes_from_name("uuid")
    meta = SimpleNamespace(db_table=table, get_fields=lambda: [field])
    return type(name, (), {"_meta": meta})


BEHAVIOUR = ("Behaviour", "people_behaviour")
EMAIL = ("EmailMessage", "codenerix_email_emailmessage")
SIZES = {"people_behaviour": (1_000_000, 20 * GIB), "codenerix_email_emailmessage": (10, 6 * GIB)}


def _hex(n: int = 10) -> tuple[str, int, int, int, int]:
    return ("char", 32, n, n, 0)


def _dashed(n: int = 10, length: int = 36) -> tuple[str, int, int, int, int]:
    return ("char", length, n, 0, n)


@pytest.fixture
def db(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> dict[str, Any]:
    """Builds a fake server; by default MariaDB >= 10.7, both tables still char(32)
    hex, a local server with datadir and tmpdir on different filesystems."""
    state: dict[str, Any] = {}
    datadir, tmpdir, binlog = tmp_path / "mysql", tmp_path / "tmp", tmp_path / "binlog"
    for path in (datadir, tmpdir, binlog):
        path.mkdir()
    state.update(datadir=str(datadir), tmpdir=str(tmpdir), binlog=str(binlog))
    devices = {str(datadir): 1, str(tmpdir): 2, str(binlog): 3}
    free = {str(datadir): 100 * GIB, str(tmpdir): 100 * GIB, str(binlog): 100 * GIB}
    state.update(devices=devices, free=free, asked=[])

    def disk_usage(path: str) -> Any:
        state["asked"].append(str(path))
        return SimpleNamespace(free=free[str(path)])

    monkeypatch.setattr(migrate_uuids.shutil, "disk_usage", disk_usage)
    # raising=False: the negative control against 6.3.1, which has no _device, still runs
    monkeypatch.setattr(migrate_uuids, "_device", lambda path: devices[str(path)], raising=False)

    def connect(
        version: str = MARIADB,
        native: bool = True,
        columns: dict[str, tuple[Any, ...]] | None = None,
        models: tuple[tuple[str, str], ...] = (BEHAVIOUR, EMAIL),
        host: str = "",
        **variables: str,
    ) -> _Server:
        base = {
            "datadir": str(datadir),
            "tmpdir": str(tmpdir),
            "hostname": socket.gethostname(),
            "log_bin": "OFF",
        }
        base.update(variables)
        server = _Server(
            version,
            columns if columns is not None else {t: _hex() for _, t in models},
            SIZES,
            {k: v for k, v in base.items() if v is not None},
        )
        monkeypatch.setattr(
            migrate_uuids,
            "apps",
            SimpleNamespace(get_models=lambda: [_uuid_model(n, t) for n, t in models]),
        )
        monkeypatch.setattr(
            migrate_uuids,
            "connection",
            SimpleNamespace(
                vendor="mysql",
                features=SimpleNamespace(has_native_uuid_field=native),
                cursor=lambda: _Cursor(server),
                settings_dict={"HOST": host},
                mysql_is_mariadb="MariaDB" in version,
                close=lambda: server.log.append("CLOSE"),
            ),
        )
        state["server"] = server
        return server

    state["connect"] = connect
    return state


def _run(target: int = 36, *flags: str) -> str:
    out = StringIO()
    call_command("migrate_uuids", "--target", str(target), *flags, stdout=out)
    return out.getvalue()


def _writes(log: list[str]) -> list[str]:
    return [sql for sql in log if sql.startswith(("ALTER", "UPDATE"))]


def _globals(log: list[str]) -> list[str]:
    return [sql for sql in log if sql.startswith("SET GLOBAL")]


def _order(log: list[str], table: str) -> list[str]:
    return [sql.split()[0] for sql in _writes(log) if f"`{table}`" in sql]


# --- Target guards ---------------------------------------------------------------


@pytest.mark.parametrize("flags", [(), ("--execute",)], ids=["dry-run", "execute"])
def test_target_36_is_refused_where_django_writes_hex(db: dict[str, Any], flags: tuple) -> None:
    server = db["connect"](MYSQL, native=False)
    with pytest.raises(CommandError, match=r"--target 36 refused on MySQL \(8\.0\.21\)"):
        _run(36, *flags)
    # Nothing but the version probe reached the database
    assert server.log == ["SELECT VERSION()"]


def test_target_32_is_refused_where_django_writes_dashed(db: dict[str, Any]) -> None:
    server = db["connect"]()
    with pytest.raises(CommandError, match=r"--target 32 refused on MariaDB"):
        _run(32, "--execute")
    assert server.log == ["SELECT VERSION()"]


def test_other_database_vendors_exit_1(db: dict[str, Any], monkeypatch: Any) -> None:
    db["connect"]()
    monkeypatch.setattr(migrate_uuids.connection, "vendor", "sqlite")
    with pytest.raises(CommandError, match="only designed for MySQL/MariaDB"):
        _run(36)


# --- What the scan plans ---------------------------------------------------------


def test_compliant_tables_plan_nothing(db: dict[str, Any]) -> None:
    db["connect"](columns={t: _dashed() for t in SIZES})
    assert "already compliant with CHAR(36)" in _run(36)


def test_native_uuid_columns_are_compliant(db: dict[str, Any]) -> None:
    server = db["connect"](columns={t: ("uuid", None, 10, 0, 10) for t in SIZES})
    assert "already compliant with CHAR(36)" in _run(36)
    # No value scan either: the native type only holds valid UUIDs
    assert not [sql for sql in server.log if sql.startswith("SELECT COUNT(")]


def test_half_converted_column_gets_only_the_update(db: dict[str, Any]) -> None:
    # A run cut after the ALTER: char(36) holding hex values, which 6.3.1 called compliant
    server = db["connect"](
        columns={
            "people_behaviour": ("char", 36, 10, 4, 6),
            "codenerix_email_emailmessage": _dashed(),
        },
    )
    out = _run(36, "--execute")
    assert "already CHAR(36), 4 values still in the old format: half converted" in out
    assert _order(server.log, "people_behaviour") == ["UPDATE"]
    assert _order(server.log, "codenerix_email_emailmessage") == []
    assert "Migration completed successfully." in out


def test_updates_match_the_format_not_the_length(db: dict[str, Any]) -> None:
    server = db["connect"]()
    _run(36, "--execute")
    updates = [sql for sql in server.log if sql.startswith("UPDATE")]
    assert updates and all(f"REGEXP '{migrate_uuids.HEX32}'" in sql for sql in updates)


def test_malformed_values_refuse_execute(db: dict[str, Any]) -> None:
    # 10 values, 7 hex, 0 dashed: 3 are neither (e.g. '', 'abc', a dashed UUID cut to 32)
    server = db["connect"](
        columns={"people_behaviour": ("char", 32, 10, 7, 0), "codenerix_email_emailmessage": _hex()}
    )
    with pytest.raises(CommandError, match=r"Refusing to execute: people_behaviour\.uuid"):
        _run(36, "--execute")
    assert _writes(server.log) == []


def test_malformed_values_are_listed_in_dry_run(db: dict[str, Any]) -> None:
    db["connect"](
        columns={"people_behaviour": ("char", 32, 10, 7, 0), "codenerix_email_emailmessage": _hex()}
    )
    out = _run(36)
    assert "people_behaviour.uuid: 3 values are neither 32 hex characters nor a dashed UUID" in out
    # The dry run warns that --execute will not run, not only that the values stay as they are
    assert "--execute refuses to run until they are fixed." in out
    assert "No changes were applied" in out


def test_malformed_values_in_a_compliant_column_only_warn(db: dict[str, Any]) -> None:
    db["connect"](
        columns={
            "people_behaviour": ("char", 36, 10, 0, 9),
            "codenerix_email_emailmessage": _dashed(),
        }
    )
    out = _run(36, "--execute")
    assert "1 values are neither" in out
    assert "--execute refuses" not in out
    assert "already compliant with CHAR(36)" in out


def test_a_table_mapped_by_two_models_is_planned_once(db: dict[str, Any]) -> None:
    server = db["connect"](models=(BEHAVIOUR, ("BehaviourMirror", "people_behaviour")))
    _run(36, "--execute")
    assert _order(server.log, "people_behaviour") == ["ALTER", "UPDATE"]


def test_target_32_removes_the_dashes_before_narrowing(db: dict[str, Any]) -> None:
    # MySQL 8.0, 2026-10-19: narrowing first truncated every dashed value (non-strict) or
    # failed with 1265 (strict) before the UPDATE ran
    server = db["connect"](MYSQL, native=False, columns={t: _dashed() for t in SIZES})
    assert "Migration completed successfully." in _run(32, "--execute")
    for table in SIZES:
        assert _order(server.log, table) == ["UPDATE", "ALTER"]


def test_target_36_widens_before_adding_the_dashes(db: dict[str, Any]) -> None:
    server = db["connect"]()
    assert "Migration completed successfully." in _run(36, "--execute")
    for table in SIZES:
        assert _order(server.log, table) == ["ALTER", "UPDATE"]


# --- Strict session sql_mode and exit codes -----------------------------------------


def test_execute_runs_with_a_strict_session_and_restores_it(db: dict[str, Any]) -> None:
    server = db["connect"]()
    _run(36, "--execute")
    sets = [
        (sql, params)
        for sql, params in zip(server.log, server.params, strict=True)
        if sql.startswith("SET SESSION sql_mode")
    ]
    assert sets == [
        ("SET SESSION sql_mode = %s", ["NO_ENGINE_SUBSTITUTION,STRICT_ALL_TABLES"]),
        ("SET SESSION sql_mode = %s", ["NO_ENGINE_SUBSTITUTION"]),
    ]
    first_set = server.log.index("SET SESSION sql_mode = %s")
    assert first_set < server.log.index(_writes(server.log)[0])


def test_failed_statement_exits_1_and_reports_every_column(db: dict[str, Any]) -> None:
    server = db["connect"]()
    server.fail_on = "ALTER TABLE `codenerix_email_emailmessage`"
    out = StringIO()
    with pytest.raises(CommandError, match="Migration failed"):
        call_command("migrate_uuids", "--target", "36", "--execute", stdout=out)
    text = out.getvalue()
    assert "CRITICAL ERROR executing migration" in text
    assert "Failed statement: ALTER TABLE `codenerix_email_emailmessage` MODIFY" in text
    assert "State of every UUID column now:" in text
    # The session sql_mode is put back even after the failure
    assert server.log.count("SET SESSION sql_mode = %s") == 2
    assert server.params[
        len(server.log) - 1 - server.log[::-1].index("SET SESSION sql_mode = %s")
    ] == [
        "NO_ENGINE_SUBSTITUTION",
    ]


def test_foreign_key_checks_are_restored_after_a_failed_statement(db: dict[str, Any]) -> None:
    # The session may be reused by whoever called call_command: checks off would stay off
    server = db["connect"]()
    server.fail_on = "ALTER TABLE `codenerix_email_emailmessage`"
    with pytest.raises(CommandError, match="Migration failed"):
        _run(36, "--execute")
    failed = next(
        i for i, sql in enumerate(server.log) if sql.startswith("ALTER TABLE `codenerix_email")
    )
    assert "SET FOREIGN_KEY_CHECKS=1;" in server.log[failed + 1 :]


def test_foreign_key_checks_are_restored_once_after_success(db: dict[str, Any]) -> None:
    server = db["connect"]()
    _run(36, "--execute")
    assert server.log.count("SET FOREIGN_KEY_CHECKS=1;") == 1
    assert server.log.index("SET FOREIGN_KEY_CHECKS=1;") > server.log.index(_writes(server.log)[-1])


def test_dry_run_previews_the_foreign_key_restore(db: dict[str, Any], capsys: Any) -> None:
    server = db["connect"]()
    _run(36)
    # The preview goes through print(), not the command's stdout
    assert capsys.readouterr().out.splitlines()[-1] == "SET FOREIGN_KEY_CHECKS=1;"
    assert "SET FOREIGN_KEY_CHECKS" not in " ".join(server.log)


# --- Resource check --------------------------------------------------------------


def test_estimate_is_printed_in_dry_run(db: dict[str, Any]) -> None:
    server = db["connect"]()
    out = _run(36)
    assert "Size: people_behaviour: ~1000000 rows, 20.0 GiB" in out
    assert "Estimated space needed for the rebuilds: 26.0 GiB" in out
    assert f"Free space in {db['datadir']}: 100.0 GiB" in out
    assert "run ANALYZE TABLE on these tables first" in out
    assert "innodb_alter_copy_bulk" not in out
    assert _writes(server.log) == []


def test_execute_is_refused_without_free_space(db: dict[str, Any]) -> None:
    db["free"][db["datadir"]] = 10 * GIB
    server = db["connect"]()
    with pytest.raises(CommandError, match=r"10\.0 GiB free, 26\.0 GiB needed"):
        _run(36, "--execute")
    assert _writes(server.log) == []


def test_dry_run_only_warns_without_free_space(db: dict[str, Any]) -> None:
    db["free"][db["datadir"]] = 10 * GIB
    db["connect"]()
    assert "Not enough free space" in _run(36)


def test_skip_space_check_executes_anyway(db: dict[str, Any]) -> None:
    db["free"][db["datadir"]] = 10 * GIB
    server = db["connect"]()
    out = _run(36, "--execute", "--skip-space-check")
    assert "Not enough free space" in out
    assert "Migration completed successfully." in out
    assert _writes(server.log)


def test_half_converted_tables_need_no_rebuild_space(db: dict[str, Any]) -> None:
    db["connect"](
        columns={"people_behaviour": ("char", 36, 10, 4, 6), "codenerix_email_emailmessage": _hex()}
    )
    assert "Estimated space needed for the rebuilds: 6.0 GiB" in _run(36)


@pytest.mark.parametrize(
    ("host", "hostname"),
    [("db.example.org", None), ("", "another-machine")],
    ids=["tcp-to-another-host", "same-path-other-server"],
)
def test_server_on_another_host_refuses_execute(
    db: dict[str, Any],
    host: str,
    hostname: str | None,
) -> None:
    # A directory that exists here proves nothing about the server's filesystem, and what
    # cannot be measured is not assumed to fit
    extra = {"hostname": hostname} if hostname else {}
    server = db["connect"](host=host, innodb_alter_copy_bulk="ON", **extra)
    with pytest.raises(CommandError, match=r"is not this host.*--skip-space-check") as refused:
        _run(36, "--execute")
    # Switching bulk off would not lift this refusal, so it is not offered as a way out
    assert "--disable-copy-bulk" not in str(refused.value)
    assert db["asked"] == []
    assert _writes(server.log) == []


def test_server_on_another_host_only_warns_in_dry_run(db: dict[str, Any]) -> None:
    db["connect"](host="db.example.org")
    out = _run(36)
    assert "is not this host" in out
    assert "--execute on another host requires --skip-space-check." in out
    assert db["asked"] == []


def test_server_on_another_host_dry_run_with_the_flag_does_not_ask_for_it(
    db: dict[str, Any],
) -> None:
    db["connect"](host="db.example.org")
    out = _run(36, "--skip-space-check")
    assert "is not this host" in out
    assert "requires --skip-space-check" not in out


def test_server_on_another_host_executes_with_skip_space_check(db: dict[str, Any]) -> None:
    server = db["connect"](host="db.example.org")
    out = _run(36, "--execute", "--skip-space-check")
    assert "is not this host" in out
    assert "requires --skip-space-check" not in out
    assert db["asked"] == []
    assert "Migration completed successfully." in out
    assert _writes(server.log)


def test_server_on_another_host_with_nothing_to_rebuild_executes(db: dict[str, Any]) -> None:
    # Half-converted columns only, no binary log: no space is needed, so nothing to check
    server = db["connect"](
        host="db.example.org",
        columns={
            "people_behaviour": ("char", 36, 10, 4, 6),
            "codenerix_email_emailmessage": _dashed(),
        },
    )
    assert "Migration completed successfully." in _run(36, "--execute")
    assert _order(server.log, "people_behaviour") == ["UPDATE"]


def test_bulk_tmpdir_needs_the_factor_times_the_largest_table(db: dict[str, Any]) -> None:
    db["free"][db["tmpdir"]] = 49 * GIB  # largest rebuilt table 20 GiB: 50 GiB needed
    server = db["connect"](innodb_alter_copy_bulk="ON")
    with pytest.raises(CommandError) as excinfo:
        _run(36, "--execute")
    message = str(excinfo.value)
    assert f"temporary directory {db['tmpdir']}: 49.0 GiB free, 50.0 GiB needed" in message
    assert "--disable-copy-bulk if the database user has SUPER" in message
    assert _writes(server.log) == []


def test_bulk_tmpdir_with_room_only_informs(db: dict[str, Any]) -> None:
    db["free"][db["tmpdir"]] = 50 * GIB
    db["connect"](innodb_alter_copy_bulk="ON")
    out = _run(36, "--execute")
    assert f"up to {migrate_uuids.SPACE_FACTOR}x the table in tmpdir" in out
    assert "Migration completed successfully." in out


def test_innodb_tmpdir_is_not_read(db: dict[str, Any]) -> None:
    # The merge files go to tmpdir anyway (MariaDB 10.11, REVIEW F2b)
    server = db["connect"](innodb_alter_copy_bulk="ON", innodb_tmpdir="/somewhere/roomy")
    _run(36)
    assert not any("innodb_tmpdir" in sql for sql in server.log)
    assert db["tmpdir"] in db["asked"]


def test_every_directory_of_a_tmpdir_list_is_checked(db: dict[str, Any], tmp_path: Any) -> None:
    second = tmp_path / "tmp2"
    second.mkdir()
    db["devices"][str(second)] = 4
    db["free"][str(second)] = 1 * GIB
    db["connect"](innodb_alter_copy_bulk="ON", tmpdir=f"{db['tmpdir']}:{second}")
    out = _run(36)
    assert f"Free space in {db['tmpdir']}" in out
    assert f"Not enough free space in temporary directory {second}" in out


def test_row_binlog_counts_the_update_phase(db: dict[str, Any]) -> None:
    # 26 GiB updated: 65 GiB of binary log; largest 20 GiB: 50 GiB of transaction cache
    db["free"][db["binlog"]] = 64 * GIB
    db["connect"](log_bin="ON", binlog_format="ROW", log_bin_basename=f"{db['binlog']}/mysql-bin")
    out = _run(36)
    assert "Binary log is ON in ROW format" in out
    assert f"binary log directory {db['binlog']}: 64.0 GiB free, 65.0 GiB needed" in out
    assert f"Free space in {db['tmpdir']}: 100.0 GiB" in out


def test_statement_binlog_adds_nothing(db: dict[str, Any]) -> None:
    db["connect"](log_bin="ON", binlog_format="STATEMENT", log_bin_basename=f"{db['binlog']}/b")
    out = _run(36)
    assert "Binary log" not in out
    assert db["binlog"] not in db["asked"]


def test_directories_on_one_filesystem_add_up(db: dict[str, Any]) -> None:
    # datadir 26 GiB + tmpdir 50 GiB on the same filesystem with 70 GiB free
    db["devices"][db["tmpdir"]] = db["devices"][db["datadir"]]
    db["free"][db["datadir"]] = 70 * GIB
    db["connect"](innodb_alter_copy_bulk="ON")
    out = _run(36)
    assert "(same filesystem): 70.0 GiB free, 76.0 GiB needed" in out


# --- --disable-copy-bulk ------------------------------------------------------------


def test_disable_copy_bulk_wraps_the_rebuilds(db: dict[str, Any]) -> None:
    db["free"][db["tmpdir"]] = 0  # tmpdir no longer matters
    server = db["connect"](innodb_alter_copy_bulk="ON")
    out = _run(36, "--execute", "--disable-copy-bulk")
    assert "--disable-copy-bulk switches it off for the rebuilds" in out
    assert "Not enough" not in out
    assert f"{SET_OFF} done." in out and f"{SET_ON} done." in out
    writes = _writes(server.log)
    assert server.log.index(SET_OFF) < server.log.index(writes[0])
    assert server.log.index(writes[-1]) < server.log.index(SET_ON)


def test_disable_copy_bulk_restores_after_a_failed_statement(db: dict[str, Any]) -> None:
    server = db["connect"](innodb_alter_copy_bulk="ON")
    server.fail_on = "ALTER TABLE `people_behaviour`"
    with pytest.raises(CommandError, match="Migration failed"):
        _run(36, "--execute", "--disable-copy-bulk")
    assert _globals(server.log) == [SET_OFF, SET_ON]


def test_disable_copy_bulk_without_privilege_executes_nothing(db: dict[str, Any]) -> None:
    server = db["connect"](innodb_alter_copy_bulk="ON")
    server.fail_on = "SET GLOBAL"
    with pytest.raises(CommandError, match=r"lacks the privilege \(SUPER\)") as excinfo:
        _run(36, "--execute", "--disable-copy-bulk")
    assert 'sudo mariadb -e "SET GLOBAL innodb_alter_copy_bulk=OFF"' in str(excinfo.value)
    assert _writes(server.log) == []
    assert _globals(server.log) == [SET_OFF]


def test_disable_copy_bulk_failed_restore_exits_1(db: dict[str, Any]) -> None:
    server = db["connect"](innodb_alter_copy_bulk="ON")
    server.fail_on = SET_ON
    out = StringIO()
    with pytest.raises(CommandError, match="could not be restored"):
        call_command(
            "migrate_uuids",
            "--target",
            "36",
            "--execute",
            "--disable-copy-bulk",
            stdout=out,
        )
    assert "innodb_alter_copy_bulk is still OFF for every session" in out.getvalue()
    assert _writes(server.log)


@pytest.mark.parametrize("bulk", ["OFF", None], ids=["already-off", "absent"])
def test_disable_copy_bulk_sends_nothing_when_not_on(db: dict[str, Any], bulk: str | None) -> None:
    server = db["connect"](innodb_alter_copy_bulk=bulk)
    assert "Migration completed successfully." in _run(36, "--execute", "--disable-copy-bulk")
    assert _globals(server.log) == []


def test_disable_copy_bulk_in_dry_run_changes_nothing(db: dict[str, Any]) -> None:
    db["free"][db["tmpdir"]] = 0
    server = db["connect"](innodb_alter_copy_bulk="ON")
    out = _run(36, "--disable-copy-bulk")
    assert "--disable-copy-bulk switches it off for the rebuilds" in out
    assert "Not enough" not in out
    assert _globals(server.log) == [] and _writes(server.log) == []


def test_bulk_is_left_alone_without_rebuilds(db: dict[str, Any]) -> None:
    # Only half-converted columns: UPDATEs, no ALTER, so no merge files and no SET GLOBAL
    db["free"][db["tmpdir"]] = 0
    server = db["connect"](
        columns={t: ("char", 36, 10, 4, 6) for t in SIZES},
        innodb_alter_copy_bulk="ON",
    )
    out = _run(36, "--execute", "--disable-copy-bulk")
    assert "innodb_alter_copy_bulk" not in out
    assert _globals(server.log) == []
    assert "Migration completed successfully." in out


# --- Ctrl-C and restore failures (6.3.3) ---------------------------------------------


def test_ctrl_c_reports_where_the_run_stopped(db: dict[str, Any]) -> None:
    # Measured on 11.8.6: Ctrl-C during an ALTER surfaces when the server has finished it
    server = db["connect"](innodb_alter_copy_bulk="ON")
    server.interrupt_on = "ALTER TABLE `codenerix_email_emailmessage`"
    out = StringIO()
    with pytest.raises(CommandError, match="Migration interrupted"):
        call_command(
            "migrate_uuids", "--target", "36", "--execute", "--disable-copy-bulk", stdout=out
        )
    text = out.getvalue()
    assert "Interrupted while running: ALTER TABLE `codenerix_email_emailmessage`" in text
    assert "this one may have completed" in text
    assert "State of every UUID column now:" in text
    # Restores first, then a fresh connection for the global restore and the report
    close = server.log.index("CLOSE")
    assert "SET FOREIGN_KEY_CHECKS=1;" in server.log[:close]
    assert server.log[:close].count("SET SESSION sql_mode = %s") == 2
    assert server.log.index(SET_ON) > close


def test_failed_fk_restore_does_not_skip_the_sql_mode_restore(db: dict[str, Any]) -> None:
    server = db["connect"]()
    server.fail_on = ("ALTER TABLE `codenerix_email_emailmessage`", "SET FOREIGN_KEY_CHECKS=1")
    out = StringIO()
    with pytest.raises(CommandError, match="Migration failed"):
        call_command("migrate_uuids", "--target", "36", "--execute", stdout=out)
    text = out.getvalue()
    # The driver's "(code, 'message')" as it is, without a second pair of parentheses
    assert "Could not restore the session: SET FOREIGN_KEY_CHECKS=1: (1227, " in text
    assert "Failed statement: ALTER TABLE `codenerix_email_emailmessage`" in text
    fk = server.log.index("SET FOREIGN_KEY_CHECKS=1;")
    assert server.log[fk + 1] == "SET SESSION sql_mode = %s"
    assert "CLOSE" in server.log[fk:]


def test_failed_restore_after_success_exits_1(db: dict[str, Any]) -> None:
    server = db["connect"]()
    # Only the restore: the first SET carries STRICT_ALL_TABLES in its parameters
    server.fail_on = "SET SESSION sql_mode = %s ['NO_ENGINE_SUBSTITUTION']"
    out = StringIO()
    with pytest.raises(CommandError, match="the session could not be restored"):
        call_command("migrate_uuids", "--target", "36", "--execute", stdout=out)
    text = out.getvalue()
    # The value restored, not the query placeholder (REVIEW 4 m-5)
    assert "Could not restore the session: SET SESSION sql_mode = 'NO_ENGINE_SUBSTITUTION'" in text
    assert "Could not restore the session: SET SESSION sql_mode = %s" not in text
    assert _writes(server.log)
    assert server.log[-1] == "CLOSE"


def test_report_survives_a_dead_connection(
    db: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    db["connect"]().fail_on = "ALTER TABLE `codenerix_email_emailmessage`"
    scans = {"n": 0}
    original = migrate_uuids.Command.scan_columns

    def scan(command: Any, target_length: int) -> list[dict[str, Any]]:
        scans["n"] += 1
        if scans["n"] > 1:
            raise RuntimeError("(2006, 'Server has gone away')")
        return original(command, target_length)

    monkeypatch.setattr(migrate_uuids.Command, "scan_columns", scan)
    out = StringIO()
    with pytest.raises(CommandError, match="Migration failed"):
        call_command("migrate_uuids", "--target", "36", "--execute", stdout=out)
    text = out.getvalue()
    assert "Failed statement: ALTER TABLE `codenerix_email_emailmessage`" in text
    assert "could not read the column state: (2006, 'Server has gone away')" in text


# --- Sizes: tablespace files, stale statistics, compressed tables (6.3.3) -------------


def test_stale_statistics_refuse_execute(db: dict[str, Any]) -> None:
    # Right after an import: 2 rows and 16 KiB reported for a table where 10 were counted
    server = db["connect"]()
    server.sizes = {"people_behaviour": (2, 16 * 1024), "codenerix_email_emailmessage": (10, GIB)}
    with pytest.raises(
        CommandError,
        match=r"people_behaviour \(16\.0 KiB and ~2 rows reported, 10 rows counted\)",
    ):
        _run(36, "--execute")
    assert _writes(server.log) == []


def test_stale_size_with_current_rows_refuses(db: dict[str, Any]) -> None:
    # MariaDB 11.8.6 after a bulk insert with STATS_AUTO_RECALC=0: 300000 rows, 32 KiB
    server = db["connect"](columns={t: _hex(300_000) for t in SIZES})
    server.sizes = {
        "people_behaviour": (300_000, 32 * 1024),
        "codenerix_email_emailmessage": (10, GIB),
    }
    with pytest.raises(CommandError, match=r"people_behaviour \(32\.0 KiB and ~300000 rows"):
        _run(36, "--execute")
    assert _writes(server.log) == []


def test_stale_statistics_only_warn_in_dry_run_and_skip_proceeds(db: dict[str, Any]) -> None:
    server = db["connect"]()
    server.sizes = {"people_behaviour": (2, 16 * 1024), "codenerix_email_emailmessage": (10, GIB)}
    assert "Run ANALYZE TABLE on these tables first, or run with --skip-space-check" in _run(36)
    out = _run(36, "--execute", "--skip-space-check")
    assert "Migration completed successfully." in out


def test_stale_statistics_refuse_on_a_remote_server_too(db: dict[str, Any]) -> None:
    # REVIEW 3 m-4: tiny stale sizes used to need nothing, so the remote refusal never fired
    server = db["connect"](host="db.example.org")
    server.sizes = {"people_behaviour": (0, 0), "codenerix_email_emailmessage": (0, 0)}
    with pytest.raises(CommandError, match="Stale statistics: codenerix_email_emailmessage"):
        _run(36, "--execute")
    assert _writes(server.log) == []


def test_file_sizes_replace_stale_statistics(db: dict[str, Any]) -> None:
    server = db["connect"]()
    server.sizes = {"people_behaviour": (2, 16 * 1024), "codenerix_email_emailmessage": (10, GIB)}
    server.files = {"people_behaviour": 30 * GIB, "codenerix_email_emailmessage": 6 * GIB}
    out = _run(36)
    assert "Size: people_behaviour: ~2 rows, 30.0 GiB" in out
    assert "Estimated space needed for the rebuilds: 36.0 GiB" in out
    assert "Stale statistics" not in out
    assert "PROCESS privilege" not in out


def test_without_process_the_estimates_are_used(db: dict[str, Any]) -> None:
    server = db["connect"]()
    out = _run(36)
    assert any("TABLESPACES" in sql for sql in server.log)
    assert "Estimated space needed for the rebuilds: 26.0 GiB" in out
    assert "it needs the PROCESS privilege" in out


def test_tablespace_names_are_encoded_like_innodb() -> None:
    assert migrate_uuids._filename("people_behaviour") == "people_behaviour"
    assert migrate_uuids._filename("cd-nx") == "cd@002dnx"
    assert migrate_uuids._filename("a b.c") == "a@0020b@002ec"


@pytest.mark.parametrize(
    ("row_format", "options", "page", "scale"),
    [
        ("Dynamic", "", 16384, 1.0),
        ("Compressed", "row_format=COMPRESSED", 16384, 2.0),
        ("Compressed", "row_format=COMPRESSED key_block_size=4", 16384, 4.0),
        ("Compressed", "ROW_FORMAT=COMPRESSED KEY_BLOCK_SIZE=1", 16384, 16.0),
        ("Compressed", "row_format=COMPRESSED key_block_size=16", 16384, 1.0),
        ("Compressed", "row_format=COMPRESSED", 8192, 2.0),
    ],
)
def test_compression_scale(row_format: str, options: str, page: int, scale: float) -> None:
    assert migrate_uuids.Command.compression_scale(row_format, options, page) == scale


def test_compressed_table_scales_the_merge_files_not_the_copy(db: dict[str, Any]) -> None:
    # 20 GiB on disk, default KEY_BLOCK_SIZE: 40 GiB uncompressed, so 100 GiB of merge files
    db["free"][db["tmpdir"]] = 99 * GIB
    server = db["connect"](innodb_alter_copy_bulk="ON")
    server.formats = {"people_behaviour": ("Compressed", "row_format=COMPRESSED")}
    out = _run(36)
    assert "ROW_FORMAT=COMPRESSED: counted as 40.0 GiB" in out
    assert "Estimated space needed for the rebuilds: 26.0 GiB" in out
    assert f"temporary directory {db['tmpdir']}: 99.0 GiB free, 100.0 GiB needed" in out


def test_compressed_table_scales_the_binary_log(db: dict[str, Any]) -> None:
    # (40 + 6) GiB uncompressed updated: 115 GiB of binary log
    db["free"][db["binlog"]] = 114 * GIB
    server = db["connect"](
        log_bin="ON", binlog_format="ROW", log_bin_basename=f"{db['binlog']}/mysql-bin"
    )
    server.formats = {"people_behaviour": ("Compressed", "row_format=COMPRESSED")}
    out = _run(36)
    assert f"binary log directory {db['binlog']}: 114.0 GiB free, 115.0 GiB needed" in out


# --- Fake fidelity (REVIEW 2 M-7) ------------------------------------------------------


def test_values_are_classified_by_the_query_patterns(db: dict[str, Any]) -> None:
    hexed = "9b2f6c1e4d3a4f8b9c7d1e2f3a4b5c6d"
    values = [
        hexed,
        hexed.upper(),
        "9b2f6c1e-4d3a-4f8b-9c7d-1e2f3a4b5c6d",
        "",
        "abc",
        hexed + "\n",
        None,
    ]
    db["connect"](
        columns={"people_behaviour": ("char", 32, values), "codenerix_email_emailmessage": _hex()}
    )
    out = _run(36)
    # Upper-case hex is hex, and so is a value with a trailing newline: MariaDB's and
    # MySQL's "$" accept it (REVIEW 4 m-3); the empty string and "abc" are neither
    assert "people_behaviour.uuid: 2 values are neither" in out


def test_show_variables_answers_only_what_is_asked(db: dict[str, Any]) -> None:
    server = db["connect"](innodb_tmpdir="/elsewhere", log_bin="ON", binlog_format="ROW")
    cursor = _Cursor(server)
    cursor.execute("SHOW VARIABLES WHERE Variable_name IN ('tmpdir', 'log_bin')")
    assert dict(cursor.fetchall()) == {"tmpdir": db["tmpdir"], "log_bin": "ON"}


# --- REVIEW 4 follow-up ----------------------------------------------------------------


def test_stale_statistics_do_not_block_an_update_only_resume(db: dict[str, Any]) -> None:
    # After a cut run: half converted, nothing rebuilt, no ROW binary log: no size is used
    server = db["connect"](columns={t: ("char", 36, 10, 4, 6) for t in SIZES})
    server.sizes = {"people_behaviour": (0, 0), "codenerix_email_emailmessage": (0, 0)}
    out = _run(36, "--execute")
    assert "Stale statistics" not in out
    # No size is used, so no advice to analyze either (REVIEW 5 n-2)
    assert "it needs the PROCESS privilege" not in out
    assert "Migration completed successfully." in out


def test_stale_statistics_still_refuse_an_update_with_a_row_binlog(db: dict[str, Any]) -> None:
    server = db["connect"](
        columns={t: ("char", 36, 10, 4, 6) for t in SIZES},
        log_bin="ON",
        binlog_format="ROW",
        log_bin_basename=f"{db['binlog']}/mysql-bin",
    )
    server.sizes = {"people_behaviour": (0, 0), "codenerix_email_emailmessage": (0, 0)}
    with pytest.raises(CommandError, match="Stale statistics"):
        _run(36, "--execute")
    assert _writes(server.log) == []


def test_failure_report_points_to_analyze_table(db: dict[str, Any]) -> None:
    db["connect"]().fail_on = "ALTER TABLE `codenerix_email_emailmessage`"
    out = StringIO()
    with pytest.raises(CommandError, match="Migration failed"):
        call_command("migrate_uuids", "--target", "36", "--execute", stdout=out)
    assert "run ANALYZE TABLE on the tables listed as not or half converted" in out.getvalue()


ODD = ("Odd", "odd-table")


@pytest.mark.parametrize("encoded", [True, False], ids=["mariadb-encoded", "mysql-plain"])
def test_file_sizes_found_under_either_spelling(db: dict[str, Any], encoded: bool) -> None:
    server = db["connect"](models=(ODD,))
    server.sizes = {"odd-table": (10, GIB)}
    server.files = {"odd-table": 3 * GIB}
    server.encoded_names = encoded
    assert "Size: odd-table: ~10 rows, 3.0 GiB" in _run(36)
