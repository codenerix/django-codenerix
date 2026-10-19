"""migrate_uuids refuses the target that would break UUID lookups or writes on
the connected database: 36 where Django stores 32 hex characters (MySQL,
MariaDB < 10.7) and 32 where it stores dashed values (MariaDB >= 10.7)."""

from io import StringIO
from types import SimpleNamespace
from typing import Any

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import UUIDField

from codenerix.management.commands import migrate_uuids

MARIADB = "11.8.6-MariaDB-ubu2404"
MYSQL = "8.0.21"


class _Server:
    """What the fake database answers: the version, the current length of the
    UUID columns found (None: no column, every field skipped), the table sizes,
    the data directory and the innodb_alter_copy_bulk variable (None: absent)."""

    def __init__(
        self,
        version: str,
        column_length: int | None = None,
        sizes: dict[str, tuple[int, int]] | None = None,
        datadir: str = "/nonexistent/datadir",
        tmpdir: str = "/nonexistent/tmpdir",
        innodb_tmpdir: str = "",
        bulk: str | None = None,
    ) -> None:
        self.version = version
        self.column_length = column_length
        self.sizes = sizes or {}
        self.datadir = datadir
        self.tmpdir = tmpdir
        self.innodb_tmpdir = innodb_tmpdir
        self.bulk = bulk
        self.log: list[str] = []
        # Statements containing this text raise, like a privilege or a DDL error would
        self.fail_on: str | None = None


class _Cursor:
    """Records every statement and answers the command's probes."""

    def __init__(self, server: _Server) -> None:
        self.server = server
        self._last = ""

    def __enter__(self) -> "_Cursor":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def execute(self, sql: str, params: Any = None) -> None:
        self._last = " ".join(sql.split())
        self.server.log.append(self._last)
        if self.server.fail_on and self.server.fail_on in self._last:
            raise RuntimeError(f"(1227, 'Access denied') on {self._last}")

    def fetchone(self) -> tuple[Any, ...] | None:
        if "VERSION()" in self._last:
            return (self.server.version,)
        if "information_schema.COLUMNS" in self._last:
            if self.server.column_length is None:
                return None
            return (f"char({self.server.column_length})", self.server.column_length)
        if "@@datadir" in self._last:
            return (self.server.datadir, self.server.tmpdir)
        if "innodb_tmpdir" in self._last:
            return ("innodb_tmpdir", self.server.innodb_tmpdir)
        if "innodb_alter_copy_bulk" in self._last:
            return (
                None if self.server.bulk is None else ("innodb_alter_copy_bulk", self.server.bulk)
            )
        return None

    def fetchall(self) -> list[tuple[Any, ...]]:
        if "information_schema.TABLES" in self._last:
            return [(name, rows, size) for name, (rows, size) in self.server.sizes.items()]
        return []


@pytest.fixture
def statements(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    state: dict[str, Any] = {}

    def connect(version: str, native: bool, **server: Any) -> _Server:
        db = _Server(version, **server)
        connection = SimpleNamespace(
            vendor="mysql",
            features=SimpleNamespace(has_native_uuid_field=native),
            cursor=lambda: _Cursor(db),
        )
        monkeypatch.setattr(migrate_uuids, "connection", connection)
        state["log"] = db.log
        return db

    state["connect"] = connect
    return state


def _run(
    target: int,
    *,
    execute: bool = False,
    skip_space_check: bool = False,
    disable_copy_bulk: bool = False,
) -> str:
    out = StringIO()
    args = ["--target", str(target)]
    if execute:
        args.append("--execute")
    if skip_space_check:
        args.append("--skip-space-check")
    if disable_copy_bulk:
        args.append("--disable-copy-bulk")
    call_command("migrate_uuids", *args, stdout=out)
    return out.getvalue()


def _alters(log: list[str]) -> list[str]:
    return [sql for sql in log if sql.startswith(("ALTER", "UPDATE"))]


@pytest.mark.parametrize("execute", [False, True], ids=["dry-run", "execute"])
def test_target_36_is_refused_where_django_writes_hex(
    statements: dict[str, Any],
    execute: bool,
) -> None:
    statements["connect"](MYSQL, native=False)
    with pytest.raises(CommandError, match=r"--target 36 refused on MySQL \(8\.0\.21\)"):
        _run(36, execute=execute)
    # Nothing but the version probe reached the database
    assert statements["log"] == ["SELECT VERSION()"]


def test_target_32_is_refused_where_django_writes_dashed(statements: dict[str, Any]) -> None:
    statements["connect"](MARIADB, native=True)
    with pytest.raises(CommandError, match=r"--target 32 refused on MariaDB"):
        _run(32, execute=True)
    assert statements["log"] == ["SELECT VERSION()"]


def test_target_36_runs_on_native_uuid_databases(statements: dict[str, Any]) -> None:
    statements["connect"](MARIADB, native=True)
    assert "already compliant with CHAR(36)" in _run(36)


def test_target_32_runs_where_django_writes_hex(statements: dict[str, Any]) -> None:
    statements["connect"](MYSQL, native=False)
    assert "already compliant with CHAR(32)" in _run(32)


# --- Space estimate and free-space check ---------------------------------------

GIB = 1024**3
SIZES = {"people_behaviour": (1_000_000, 20 * GIB), "codenerix_email_emailmessage": (1, 6 * GIB)}


def _uuid_model(name: str, table: str) -> type:
    # The test settings install no model with a UUIDField: a stand-in with a real
    # field, so the command plans the two tables of SIZES
    field = UUIDField(null=False)
    field.set_attributes_from_name("uuid")
    meta = SimpleNamespace(db_table=table, get_fields=lambda: [field])
    return type(name, (), {"_meta": meta})


@pytest.fixture
def planned(statements: dict[str, Any], tmp_path: Any, monkeypatch: Any) -> dict[str, Any]:
    """A MariaDB with every UUID column still at char(32) and a local data directory."""
    models = [
        _uuid_model(name, table)
        for name, table in (
            ("Behaviour", "people_behaviour"),
            ("EmailMessage", "codenerix_email_emailmessage"),
        )
    ]
    monkeypatch.setattr(migrate_uuids, "apps", SimpleNamespace(get_models=lambda: models))
    datadir, tmpdir = tmp_path / "mysql", tmp_path / "tmp"
    datadir.mkdir()
    tmpdir.mkdir()
    statements["datadir"], statements["tmpdir"] = str(datadir), str(tmpdir)
    statements["connect_planned"] = lambda **kw: statements["connect"](
        MARIADB,
        native=True,
        **{
            "column_length": 32,
            "datadir": str(datadir),
            "tmpdir": str(tmpdir),
            "sizes": SIZES,
            **kw,
        },
    )

    def free_space(datadir_free: int, tmpdir_free: int = 100 * GIB) -> None:
        by_dir = {str(datadir): datadir_free, str(tmpdir): tmpdir_free}
        monkeypatch.setattr(
            migrate_uuids.shutil,
            "disk_usage",
            lambda path: SimpleNamespace(free=by_dir[str(path)]),
        )

    statements["free_space"] = free_space
    statements["disk_usage"] = lambda fn: monkeypatch.setattr(
        migrate_uuids.shutil, "disk_usage", fn
    )
    return statements


def test_estimate_is_printed_in_dry_run(planned: dict[str, Any]) -> None:
    planned["free_space"](100 * GIB)
    db = planned["connect_planned"]()
    out = _run(36)
    assert "Size: people_behaviour: ~1000000 rows, 20.0 GiB" in out
    assert "Estimated space needed for the rebuilds: 26.0 GiB" in out
    assert f"Free space in {planned['datadir']}: 100.0 GiB" in out
    assert "innodb_alter_copy_bulk" not in out
    assert _alters(db.log) == []


def test_execute_is_refused_without_free_space(planned: dict[str, Any]) -> None:
    planned["free_space"](10 * GIB)
    db = planned["connect_planned"]()
    with pytest.raises(CommandError, match=r"10\.0 GiB free, 26\.0 GiB needed"):
        _run(36, execute=True)
    assert _alters(db.log) == []


def test_dry_run_only_warns_without_free_space(planned: dict[str, Any]) -> None:
    planned["free_space"](10 * GIB)
    planned["connect_planned"]()
    assert "Not enough free space" in _run(36)


def test_skip_space_check_executes_anyway(planned: dict[str, Any]) -> None:
    planned["free_space"](10 * GIB)
    db = planned["connect_planned"]()
    out = _run(36, execute=True, skip_space_check=True)
    assert "Not enough free space" in out
    assert "Migration completed successfully." in out
    assert _alters(db.log)


def test_remote_datadir_is_reported_not_checked(planned: dict[str, Any]) -> None:
    db = planned["connect_planned"](datadir="/no/such/dir")
    out = _run(36, execute=True)
    assert "Cannot check free space: data directory /no/such/dir is not on this host" in out
    assert "26.0 GiB free before running" in out
    assert _alters(db.log)


@pytest.mark.parametrize("bulk", ["OFF", None], ids=["off", "absent"])
def test_bulk_off_or_absent_checks_only_the_data_directory(
    planned: dict[str, Any],
    bulk: str | None,
) -> None:
    planned["free_space"](100 * GIB, tmpdir_free=0)
    planned["connect_planned"](bulk=bulk)
    out = _run(36, execute=True)
    assert "innodb_alter_copy_bulk" not in out
    assert planned["tmpdir"] not in out


def test_bulk_on_with_room_in_tmpdir_only_informs(planned: dict[str, Any]) -> None:
    planned["free_space"](100 * GIB, tmpdir_free=20 * GIB)  # the largest table is 20 GiB
    planned["connect_planned"](bulk="ON")
    out = _run(36, execute=True)
    assert f"merge-sort file of about the table size in {planned['tmpdir']}" in out
    assert f"Free space in {planned['tmpdir']}: 20.0 GiB" in out
    assert "Not enough" not in out
    assert "Migration completed successfully." in out


def test_bulk_on_without_room_in_tmpdir_is_refused(planned: dict[str, Any]) -> None:
    # carmen, 2026-10-19: /tmp is a tmpfs, the 26 GB email table filled it at 7.6 GB
    planned["free_space"](100 * GIB, tmpdir_free=7 * GIB)
    db = planned["connect_planned"](bulk="ON")
    with pytest.raises(CommandError) as excinfo:
        _run(36, execute=True)
    message = str(excinfo.value)
    assert f"temporary directory {planned['tmpdir']}: 7.0 GiB free, 20.0 GiB needed" in message
    assert "SET GLOBAL innodb_alter_copy_bulk=OFF" in message
    assert _alters(db.log) == []


def test_bulk_on_without_room_in_tmpdir_only_warns_in_dry_run(planned: dict[str, Any]) -> None:
    planned["free_space"](100 * GIB, tmpdir_free=7 * GIB)
    planned["connect_planned"](bulk="ON")
    out = _run(36)
    assert "SET GLOBAL innodb_alter_copy_bulk=OFF" in out


def test_innodb_tmpdir_takes_precedence(planned: dict[str, Any], tmp_path: Any) -> None:
    other = tmp_path / "innodb"
    other.mkdir()
    planned["free_space"](100 * GIB, tmpdir_free=0)
    planned["connect_planned"](bulk="ON", innodb_tmpdir=str(other))
    asked: list[str] = []

    def disk_usage(path: str) -> Any:
        asked.append(str(path))
        return SimpleNamespace(free=100 * GIB)

    planned["disk_usage"](disk_usage)
    assert "Not enough" not in _run(36, execute=True)
    assert asked == [planned["datadir"], str(other)]


# --- --disable-copy-bulk --------------------------------------------------------

SET_OFF = "SET GLOBAL innodb_alter_copy_bulk=OFF"
SET_ON = "SET GLOBAL innodb_alter_copy_bulk=ON"


def _globals(log: list[str]) -> list[str]:
    return [sql for sql in log if sql.startswith("SET GLOBAL")]


def test_disable_copy_bulk_wraps_the_rebuilds(planned: dict[str, Any]) -> None:
    planned["free_space"](100 * GIB, tmpdir_free=0)  # tmpdir no longer matters
    db = planned["connect_planned"](bulk="ON")
    out = _run(36, execute=True, disable_copy_bulk=True)
    assert "--disable-copy-bulk switches it off for the rebuilds" in out
    assert "Not enough" not in out
    assert f"{SET_OFF} done." in out and f"{SET_ON} done." in out
    assert "Migration completed successfully." in out
    first_alter = db.log.index(_alters(db.log)[0])
    last_alter = db.log.index(_alters(db.log)[-1])
    assert db.log.index(SET_OFF) < first_alter < last_alter < db.log.index(SET_ON)


def test_disable_copy_bulk_restores_after_a_failed_statement(planned: dict[str, Any]) -> None:
    planned["free_space"](100 * GIB)
    db = planned["connect_planned"](bulk="ON")
    db.fail_on = "ALTER TABLE `people_behaviour`"
    out = _run(36, execute=True, disable_copy_bulk=True)
    assert "CRITICAL ERROR executing migration" in out
    assert _globals(db.log) == [SET_OFF, SET_ON]


def test_disable_copy_bulk_without_privilege_executes_nothing(planned: dict[str, Any]) -> None:
    planned["free_space"](100 * GIB)
    db = planned["connect_planned"](bulk="ON")
    db.fail_on = "SET GLOBAL"
    with pytest.raises(CommandError, match=r"lacks the privilege \(SUPER\)") as excinfo:
        _run(36, execute=True, disable_copy_bulk=True)
    assert 'sudo mariadb -e "SET GLOBAL innodb_alter_copy_bulk=OFF"' in str(excinfo.value)
    assert _alters(db.log) == []
    assert _globals(db.log) == [SET_OFF]


def test_disable_copy_bulk_reports_a_failed_restore(planned: dict[str, Any]) -> None:
    planned["free_space"](100 * GIB)
    db = planned["connect_planned"](bulk="ON")
    db.fail_on = SET_ON
    out = _run(36, execute=True, disable_copy_bulk=True)
    assert "Migration completed successfully." in out
    assert "innodb_alter_copy_bulk is still OFF for every session" in out
    assert 'sudo mariadb -e "SET GLOBAL innodb_alter_copy_bulk=ON"' in out


@pytest.mark.parametrize("bulk", ["OFF", None], ids=["already-off", "absent"])
def test_disable_copy_bulk_sends_nothing_when_not_on(
    planned: dict[str, Any],
    bulk: str | None,
) -> None:
    planned["free_space"](100 * GIB)
    db = planned["connect_planned"](bulk=bulk)
    assert "Migration completed successfully." in _run(36, execute=True, disable_copy_bulk=True)
    assert _globals(db.log) == []


def test_disable_copy_bulk_in_dry_run_changes_nothing(planned: dict[str, Any]) -> None:
    planned["free_space"](100 * GIB, tmpdir_free=0)
    db = planned["connect_planned"](bulk="ON")
    out = _run(36, disable_copy_bulk=True)
    assert "--disable-copy-bulk switches it off for the rebuilds" in out
    assert "Not enough" not in out
    assert _globals(db.log) == [] and _alters(db.log) == []


def test_tmpdir_message_names_the_flag(planned: dict[str, Any]) -> None:
    planned["free_space"](100 * GIB, tmpdir_free=7 * GIB)
    planned["connect_planned"](bulk="ON")
    assert "--disable-copy-bulk if the database user has SUPER" in _run(36)
