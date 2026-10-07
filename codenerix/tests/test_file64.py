"""file64 must only read files that live (lexically) under its base directory."""

import base64
from pathlib import Path

import pytest
from django.core.exceptions import SuspiciousFileOperation

from codenerix.templatetags.codenerix_special import file64

CONTENT = b"\x89PNG fake image bytes"


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """<tmp>/base/{img.png, sub/deep.png, link.png -> ../outside.png} + <tmp>/outside.png."""
    base = tmp_path / "base"
    (base / "sub").mkdir(parents=True)
    (base / "img.png").write_bytes(CONTENT)
    (base / "sub" / "deep.png").write_bytes(CONTENT)
    (tmp_path / "outside.png").write_bytes(CONTENT)
    (tmp_path / "base2").mkdir()
    (tmp_path / "base2" / "x.png").write_bytes(CONTENT)
    (base / "link.png").symlink_to(tmp_path / "outside.png")
    return base


EXPECTED = base64.b64encode(CONTENT).decode()


@pytest.mark.parametrize(
    "path",
    ["img.png", "sub/deep.png", "/img.png", "sub/../img.png", "link.png"],
    ids=["plain", "subdir", "leading-slash", "dotdot-inside", "symlink-out"],
)
def test_paths_inside_base_are_read(tree: Path, path: str) -> None:
    assert file64(path, str(tree)) == EXPECTED


def test_trailing_slash_on_base_is_accepted(tree: Path) -> None:
    assert file64("img.png", f"{tree}/") == EXPECTED


@pytest.mark.parametrize(
    "path",
    ["../outside.png", "sub/../../outside.png", "/../outside.png", "../base2/x.png"],
    ids=["parent", "nested-parent", "slash-parent", "sibling-prefix"],
)
def test_paths_outside_base_are_rejected(tree: Path, path: str) -> None:
    with pytest.raises(SuspiciousFileOperation):
        file64(path, str(tree))


def test_missing_file_still_raises_oserror(tree: Path) -> None:
    with pytest.raises(OSError, match="File not found"):
        file64("missing.png", str(tree))
