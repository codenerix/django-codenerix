"""Visibility rules of codenerix.debug.show_toolbar and its activation helpers."""

from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest
from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.test import Client, RequestFactory, override_settings
from django.urls import URLPattern, URLResolver, include, path
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

TOOLBAR_MW = "debug_toolbar.middleware.DebugToolbarMiddleware"
PANEL_MW = "debug_panel.middleware.DebugPanelMiddleware"
UPDATE_CACHE_MW = "django.middleware.cache.UpdateCacheMiddleware"
FETCH_CACHE_MW = "django.middleware.cache.FetchFromCacheMiddleware"
COMMON_MW = "django.middleware.common.CommonMiddleware"
GZIP_MW = "django.middleware.gzip.GZipMiddleware"
PAGE_CACHE = [UPDATE_CACHE_MW, COMMON_MW, FETCH_CACHE_MW]

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


def _production_middleware(middleware: Any, **kwargs: bool) -> Any:
    return autoload(
        (),
        middleware,
        DEBUG_TOOLBAR=True,
        DEBUG_TOOLBAR_PRODUCTION=True,
        **kwargs,
    )[1]


@pytest.mark.parametrize("container", [list, tuple])
def test_autoload_puts_toolbar_before_page_cache(container: type) -> None:
    middleware = _production_middleware(container(PAGE_CACHE))
    assert type(middleware) is container
    assert list(middleware) == [TOOLBAR_MW, *PAGE_CACHE]


def test_autoload_places_debug_panel_like_the_toolbar() -> None:
    middleware = _production_middleware(list(PAGE_CACHE), DEBUG_PANEL=True)
    assert middleware == [PANEL_MW, *PAGE_CACHE]


def test_autoload_puts_toolbar_after_content_encoding() -> None:
    middleware = _production_middleware([GZIP_MW, *PAGE_CACHE])
    assert middleware == [GZIP_MW, TOOLBAR_MW, *PAGE_CACHE]


def test_autoload_keeps_existing_toolbar_position() -> None:
    assert _production_middleware([*PAGE_CACHE, TOOLBAR_MW]) == [*PAGE_CACHE, TOOLBAR_MW]


def test_autoload_without_toolbar_leaves_middleware_unchanged() -> None:
    assert autoload((), list(PAGE_CACHE), DEBUG=False, DEBUG_TOOLBAR=True)[1] == PAGE_CACHE
    assert autoload((), list(PAGE_CACHE), DEBUG=True)[1] == PAGE_CACHE


def test_autoload_still_appends_other_extras() -> None:
    _, middleware = autoload(
        (),
        [COMMON_MW],
        DEBUG=True,
        DEBUG_TOOLBAR=True,
        ADMINSITE=True,
        DEBUG_PYINSTRUMENT=True,
    )
    assert middleware == [
        TOOLBAR_MW,
        COMMON_MW,
        "django.contrib.messages.middleware.MessageMiddleware",
        "pyinstrument.middleware.ProfilerMiddleware",
    ]


@pytest.mark.parametrize(
    "middleware",
    [
        [*PAGE_CACHE, TOOLBAR_MW],
        [UPDATE_CACHE_MW, TOOLBAR_MW, COMMON_MW, FETCH_CACHE_MW],
        # Django's recommended order with GZip: autoload() cannot satisfy both rules
        _production_middleware([UPDATE_CACHE_MW, GZIP_MW, COMMON_MW, FETCH_CACHE_MW]),
    ],
)
@pytest.mark.parametrize(
    "access",
    [
        {"INTERNAL_IPS": [MY_IP]},
        {"DEBUG_TOOLBAR_ALLOWED_IPS": [MY_IP]},
    ],
)
def test_toolbar_behind_page_cache_fails_closed_and_is_reported(
    middleware: list[str],
    access: dict[str, list[str]],
) -> None:
    with override_settings(DEBUG=True, MIDDLEWARE=middleware, **access):
        assert show_toolbar(_request(MY_IP)) is False
        assert [e.id for e in check_debug_toolbar_access(None)] == ["codenerix.E001"]


@override_settings(
    DEBUG=True, DEBUG_TOOLBAR_ALLOWED_IPS=[MY_IP], MIDDLEWARE=[TOOLBAR_MW, *PAGE_CACHE]
)
def test_toolbar_before_page_cache_is_allowed() -> None:
    assert show_toolbar(_request(MY_IP)) is True
    assert check_debug_toolbar_access(None) == []


# --- End to end: toolbar output must never reach the page cache ---------------


def _json_view(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"ok": True})


def _html_view(request: HttpRequest) -> HttpResponse:
    return HttpResponse("<html><body><p>page</p></body></html>")


# ROOT_URLCONF for the end-to-end test; filled once the toolbar app is installed
urlpatterns: list[URLPattern | URLResolver] = []


@pytest.fixture
def cached_site_with_toolbar() -> Iterator[None]:
    middleware = _production_middleware(list(PAGE_CACHE))
    with override_settings(STATIC_URL="/static/"):
        with override_settings(
            INSTALLED_APPS=_TOOLBAR_APPS,
            MIDDLEWARE=middleware,
            ROOT_URLCONF=__name__,
            DEBUG=False,
            DEBUG_TOOLBAR_ALLOWED_IPS=[MY_IP],
            DEBUG_TOOLBAR_REQUIRE_SUPERUSER=False,
            DEBUG_TOOLBAR_CONFIG=DEBUG_TOOLBAR_DEFAULT_CONFIG,
            CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
            CACHE_MIDDLEWARE_SECONDS=600,
            TEMPLATES=[
                {"BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True},
            ],
        ):
            # Only importable once the toolbar app is installed (its models load on import)
            from debug_toolbar.middleware import show_toolbar_func_or_path

            # The toolbar memoises the callback; another test may have resolved it already
            show_toolbar_func_or_path.cache_clear()
            urlpatterns[:] = [
                path("json/", _json_view),
                path("html/", _html_view),
                path("__debug__/", include("debug_toolbar.urls")),
            ]
            try:
                yield
            finally:
                urlpatterns.clear()
                show_toolbar_func_or_path.cache_clear()


@pytest.mark.parametrize(
    ("url", "body"),
    [
        ("/json/", b'{"ok": true}'),
        ("/html/", b"<html><body><p>page</p></body></html>"),
    ],
)
@pytest.mark.usefixtures("cached_site_with_toolbar")
def test_toolbar_output_never_reaches_page_cache(url: str, body: bytes) -> None:
    mine = Client(REMOTE_ADDR=MY_IP).get(url)
    # Guard against a vacuous pass: the toolbar must really run for the allowed IP
    assert "djdt-request-id" in mine.headers

    other = Client(REMOTE_ADDR=OTHER_IP).get(url)
    assert "Age" in other.headers  # served from the page cache
    assert "djdt-request-id" not in other.headers
    assert "Server-Timing" not in other.headers
    assert other.content == body


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
