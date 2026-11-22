"""manage.py touch runs collectstatic and clean with the running interpreter."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from django.core.management import call_command
from django.test import override_settings


def test_subcommands_use_the_running_interpreter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    appdir = tmp_path / "proj"
    appdir.mkdir()
    wsgi = appdir / "wsgi.py"
    wsgi.write_text("")
    os.utime(wsgi, (1, 1))
    calls: list[list[str]] = []

    def run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="")

    monkeypatch.setattr(subprocess, "run", run)
    with override_settings(ROOT_URLCONF="proj.urls", BASE_DIR=str(tmp_path)):
        call_command("touch")
    assert calls == [
        [sys.executable, f"{appdir}/manage", "collectstatic", "--noinput"],
        [sys.executable, f"{appdir}/manage", "clean"],
    ]
    assert wsgi.stat().st_mtime > 1
