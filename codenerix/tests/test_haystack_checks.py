"""System checks for the haystack configurations that 6.2.0 left to fail on the
first request: a routed view with haystack = True without the extra (E006) and
a HAYSTACK_CONNECTIONS engine under the removed codenerix.contrib (E007)."""

import importlib.util
import subprocess
import sys
import textwrap
from collections.abc import Iterator
from pathlib import Path

import pytest
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import clear_url_caches, include, path
from django.views.generic import TemplateView

from codenerix import checks
from codenerix.checks import check_haystack

# codenerix.views reads STATIC_URL while its classes are created, and the test
# settings leave it unset on purpose (see test_debug_toolbar.py)
with override_settings(STATIC_URL="/static/"):
    from codenerix.views import GenList

E006 = "codenerix.E006"
E007 = "codenerix.E007"
CONTRIB_ENGINE = "codenerix.contrib.haystack_engines.AsciifoldingElasticSearchEngine"
SIMPLE_ENGINE = "haystack.backends.simple_backend.SimpleEngine"


class PlainList(GenList):
    model = User


class SearchList(GenList):
    model = User
    haystack = True


class NotCodenerix(TemplateView):
    # A non-codenerix view with the same attribute must not be reported
    haystack = True


nested = [path("search/", SearchList.as_view(), name="search")]
urlpatterns = [
    path("plain/", PlainList.as_view(), name="plain"),
    path("nested/", include(nested)),
    path("other/", NotCodenerix.as_view(), name="other"),
    path("again/", SearchList.as_view(), name="again"),
]


@pytest.fixture
def routed() -> Iterator[None]:
    with override_settings(ROOT_URLCONF=__name__):
        clear_url_caches()
        yield
    clear_url_caches()


@pytest.fixture
def haystack_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checks, "_haystack_installed", lambda: False)


@pytest.fixture
def haystack_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checks, "_haystack_installed", lambda: True)


def _ids(errors: list) -> list[str]:
    return [e.id for e in errors]


def test_routed_haystack_view_without_the_extra_is_reported(
    routed: None,
    haystack_absent: None,
) -> None:
    (error,) = check_haystack(None)
    assert error.id == E006
    # Reported once although it is routed twice; the plain and non-codenerix views are not
    assert error.msg.startswith(f"{__name__}.SearchList.haystack is True")
    assert "django-codenerix[haystack]" in error.msg


def test_routed_haystack_view_with_the_extra_passes(routed: None, haystack_present: None) -> None:
    assert check_haystack(None) == []


@pytest.mark.parametrize(
    "urlconf",
    ["django.contrib.auth.urls", "codenerix.tests.no_such_urlconf"],
    ids=["no-codenerix-views", "urlconf-does-not-import"],
)
def test_unrouted_haystack_view_is_not_reported(haystack_absent: None, urlconf: str) -> None:
    # SearchList exists but is not routed, so nothing can fail at request time; a URLconf
    # that does not import is left to Django's own urls.* checks
    with override_settings(ROOT_URLCONF=urlconf):
        clear_url_caches()
        assert check_haystack(None) == []
    clear_url_caches()


def test_haystack_availability_is_probed_without_importing() -> None:
    # Holds whether or not the venv has the optional extra: uv run does not remove
    # packages left over from before 6.2.0, so django-haystack may still be there
    was_loaded = "haystack" in sys.modules
    assert checks._haystack_installed() is (importlib.util.find_spec("haystack") is not None)
    assert ("haystack" in sys.modules) is was_loaded


@override_settings(HAYSTACK_CONNECTIONS={"default": {"ENGINE": CONTRIB_ENGINE}})
def test_removed_contrib_engine_is_reported(haystack_present: None) -> None:
    (error,) = check_haystack(None)
    assert error.id == E007
    assert error.msg.startswith(f"HAYSTACK_CONNECTIONS['default']['ENGINE'] is {CONTRIB_ENGINE}")


@override_settings(
    HAYSTACK_CONNECTIONS={
        "default": {"ENGINE": SIMPLE_ENGINE},
        "odd": "not a dict",
    },
)
def test_other_engines_pass(haystack_present: None) -> None:
    assert check_haystack(None) == []


@override_settings(HAYSTACK_CONNECTIONS={"default": {"ENGINE": CONTRIB_ENGINE}})
def test_both_problems_are_reported_together(routed: None, haystack_absent: None) -> None:
    assert _ids(check_haystack(None)) == [E006, E007]


def test_check_never_imports_codenerix_views(
    routed: None,
    haystack_absent: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Stands for a project whose URLconf loaded no codenerix view: the check must not
    # import codenerix.views itself (it reads STATIC_URL at import)
    monkeypatch.delitem(sys.modules, "codenerix.views")
    assert check_haystack(None) == []
    assert "codenerix.views" not in sys.modules


def test_manage_py_check_without_static_url(tmp_path: Path) -> None:
    # A fresh interpreter: codenerix.views must not be loaded by anything but the check
    (tmp_path / "f1_settings.py").write_text(
        textwrap.dedent(
            """
            SECRET_KEY = "x"
            ROOT_URLCONF = "f1_urls"
            DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
            INSTALLED_APPS = [
                "django.contrib.contenttypes", "django.contrib.auth", "django.contrib.admin",
                "django.contrib.sessions", "django.contrib.messages", "codenerix",
            ]
            # STATIC_URL left unset on purpose (Django's default is None)
            SILENCED_SYSTEM_CHECKS = ["admin.E403", "admin.E408", "admin.E409", "admin.E410"]
            """,
        ),
    )
    (tmp_path / "f1_urls.py").write_text(
        "from django.urls import path\n"
        "from django.views.generic import TemplateView\n"
        'urlpatterns = [path("", TemplateView.as_view(template_name="x.html"))]\n',
    )
    script = textwrap.dedent(
        """
        import os, sys
        sys.modules["haystack"] = None  # find_spec() -> None: E006 runs even if it is installed
        os.environ["DJANGO_SETTINGS_MODULE"] = "f1_settings"
        import django
        django.setup()
        from django.core.management import call_command
        call_command("check")
        print("codenerix.views loaded:", "codenerix.views" in sys.modules)
        """,
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env={"PYTHONPATH": str(tmp_path), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "System check identified no issues" in result.stdout
    assert "codenerix.views loaded: False" in result.stdout
