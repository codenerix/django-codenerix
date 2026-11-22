"""clean_caches tries every memcached entry and fails when any flush fails."""

import subprocess
from typing import Any

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

MEMCACHE = "django.core.cache.backends.memcached.PyMemcacheCache"
CACHES = {
    "default": {"BACKEND": MEMCACHE, "LOCATION": "10.0.0.1:11211"},
    "other": {"BACKEND": MEMCACHE, "LOCATION": "10.0.0.2"},
    "local": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}


def _fake_nc(monkeypatch: pytest.MonkeyPatch, outcome: dict[str, Any]) -> list[str]:
    """Answer nc per host: an exit status, or an exception to raise."""
    hosts: list[str] = []

    def run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        host = cmd[4]
        hosts.append(host)
        result = outcome.get(host, 0)
        if isinstance(result, type) and issubclass(result, Exception):
            raise result(cmd[0])
        return subprocess.CompletedProcess(cmd, result, stdout="OK\n")

    monkeypatch.setattr(subprocess, "run", run)
    return hosts


@override_settings(CACHES=CACHES)
def test_all_flushed(monkeypatch: pytest.MonkeyPatch) -> None:
    hosts = _fake_nc(monkeypatch, {})
    call_command("clean_caches")
    assert hosts == ["10.0.0.1", "10.0.0.2"]


@override_settings(CACHES=CACHES)
def test_failed_flush_fails_after_trying_every_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    hosts = _fake_nc(monkeypatch, {"10.0.0.1": 1})
    with pytest.raises(CommandError, match=r"Could not flush: default$"):
        call_command("clean_caches")
    assert hosts == ["10.0.0.1", "10.0.0.2"]


@override_settings(CACHES=CACHES)
def test_missing_nc_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_nc(monkeypatch, {"10.0.0.1": FileNotFoundError, "10.0.0.2": FileNotFoundError})
    with pytest.raises(CommandError, match=r"Could not flush: default, other$"):
        call_command("clean_caches")


@override_settings(CACHES={"local": CACHES["local"]})
def test_no_memcached_runs_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    hosts = _fake_nc(monkeypatch, {})
    call_command("clean_caches")
    assert hosts == []
