"""Visibility rules of codenerix.debug.show_toolbar and its activation helpers."""

from types import SimpleNamespace

import pytest
from django.conf import settings
from django.http import HttpRequest
from django.test import RequestFactory, override_settings
from django.utils.module_loading import import_string

from codenerix.checks import check_debug_toolbar_access
from codenerix.debug import (
    DEBUG_TOOLBAR_DEFAULT_CONFIG,
    autoload,
    autourl,
    show_toolbar,
)

MY_IP = "203.0.113.7"
OTHER_IP = "198.51.100.9"

# Same nesting rationale as in test_debug_toolbar.py: the toolbar app's ready()
# reads STATIC_URL, which must already be set when the registry repopulates.
_TOOLBAR_APPS = [
    *settings.INSTALLED_APPS,
    "django.contrib.staticfiles",
    "debug_toolbar",
]


def _request(ip: str, superuser: bool | None = None) -> HttpRequest:
    request = RequestFactory().get("/", REMOTE_ADDR=ip)
    if superuser is not None:
        # Stand-in for request.user; avoids touching the database
        request.user = SimpleNamespace(is_authenticated=True, is_superuser=superuser)  # type: ignore[assignment]
    return request


# --- DEBUG_TOOLBAR_ALLOWED_IPS unset: upstream behaviour, unchanged -----------


@override_settings(DEBUG=False, INTERNAL_IPS=[MY_IP])
def test_unset_delegates_upstream_debug_off() -> None:
    assert show_toolbar(_request(MY_IP)) is False


@override_settings(DEBUG=True, INTERNAL_IPS=[MY_IP])
def test_unset_delegates_upstream_debug_on() -> None:
    assert show_toolbar(_request(MY_IP)) is True
    assert show_toolbar(_request(OTHER_IP)) is False


# --- DEBUG=True: IP only by default ------------------------------------------


@override_settings(DEBUG=True, DEBUG_TOOLBAR_ALLOWED_IPS=[MY_IP])
def test_debug_listed_ip_only() -> None:
    assert show_toolbar(_request(MY_IP)) is True
    assert show_toolbar(_request(OTHER_IP)) is False


@override_settings(DEBUG=True, DEBUG_TOOLBAR_ALLOWED_IPS=["0.0.0.0"])
def test_debug_any_ip() -> None:
    assert show_toolbar(_request(OTHER_IP)) is True


# --- DEBUG=False: IP + superuser by default ----------------------------------


@override_settings(DEBUG=False, DEBUG_TOOLBAR_ALLOWED_IPS=[MY_IP])
def test_production_requires_superuser() -> None:
    assert show_toolbar(_request(MY_IP)) is False
    assert show_toolbar(_request(MY_IP, superuser=False)) is False
    assert show_toolbar(_request(MY_IP, superuser=True)) is True
    assert show_toolbar(_request(OTHER_IP, superuser=True)) is False


@override_settings(
    DEBUG=False,
    DEBUG_TOOLBAR_ALLOWED_IPS=[MY_IP],
    DEBUG_TOOLBAR_REQUIRE_SUPERUSER=False,
)
def test_production_ip_only_when_opted_out() -> None:
    assert show_toolbar(_request(MY_IP)) is True
    assert show_toolbar(_request(OTHER_IP)) is False


@override_settings(
    DEBUG=False,
    DEBUG_TOOLBAR_ALLOWED_IPS=["0.0.0.0"],
    DEBUG_TOOLBAR_REQUIRE_SUPERUSER=False,
)
def test_public_toolbar_fails_closed_and_is_reported() -> None:
    assert show_toolbar(_request(MY_IP, superuser=True)) is False
    assert [e.id for e in check_debug_toolbar_access(None)] == ["codenerix.E001"]


@override_settings(DEBUG=False, DEBUG_TOOLBAR_ALLOWED_IPS=["0.0.0.0"])
def test_production_any_ip_with_superuser_is_allowed() -> None:
    assert show_toolbar(_request(OTHER_IP, superuser=True)) is True
    assert check_debug_toolbar_access(None) == []


@pytest.mark.parametrize("value", [MY_IP, 42])
def test_malformed_setting_fails_closed_and_is_reported(value: object) -> None:
    with override_settings(DEBUG=True, DEBUG_TOOLBAR_ALLOWED_IPS=value):
        # A bare string must not degrade into a substring match
        assert show_toolbar(_request(MY_IP)) is False
        assert [e.id for e in check_debug_toolbar_access(None)] == ["codenerix.E001"]


# --- Wiring -------------------------------------------------------------------


def test_default_config_points_at_show_toolbar() -> None:
    assert import_string(DEBUG_TOOLBAR_DEFAULT_CONFIG["SHOW_TOOLBAR_CALLBACK"]) is show_toolbar


def test_autoload_production_is_opt_in() -> None:
    apps, middleware = autoload((), [], DEBUG=False, DEBUG_TOOLBAR=True)
    assert "debug_toolbar" not in apps
    assert middleware == []

    apps, middleware = autoload(
        (),
        [],
        DEBUG=False,
        DEBUG_TOOLBAR=True,
        DEBUG_TOOLBAR_PRODUCTION=True,
    )
    assert "debug_toolbar" in apps
    assert "debug_toolbar.middleware.DebugToolbarMiddleware" in middleware


def test_autourl_follows_installed_apps() -> None:
    def mounted() -> bool:
        patterns = autourl(
            [], DEBUG=False, ROSETTA=False, ADMINSITE=False, SPAGHETTI=False, DEBUG_TOOLBAR=True
        )
        return any(str(p.pattern) == "^__debug__/" for p in patterns)

    assert mounted() is False
    with override_settings(STATIC_URL="/static/"):
        with override_settings(INSTALLED_APPS=_TOOLBAR_APPS):
            assert mounted() is True
