"""Visibility rules of codenerix.debug.show_toolbar and its activation helpers.

The gate shared with the profiler and the page cache bypass is covered in
test_debug_gate.py.
"""

import sys
from collections.abc import Iterator
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from django.conf import settings
from django.core.cache import caches
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.test import Client, RequestFactory, override_settings
from django.urls import URLPattern, URLResolver, include, path, reverse
from django.utils.module_loading import import_string

from codenerix.checks import check_debug_access
from codenerix.debug import (
    DEBUG_TOOLBAR_DEFAULT_CONFIG,
    autoload,
    autourl,
    show_toolbar,
)

MY_IP = "203.0.113.7"
OTHER_IP = "198.51.100.9"

TOOLBAR_MW = "debug_toolbar.middleware.DebugToolbarMiddleware"
UPDATE_CACHE_MW = "django.middleware.cache.UpdateCacheMiddleware"
FETCH_CACHE_MW = "django.middleware.cache.FetchFromCacheMiddleware"
COMMON_MW = "django.middleware.common.CommonMiddleware"
GZIP_MW = "django.middleware.gzip.GZipMiddleware"
CDNX_UPDATE_CACHE_MW = "codenerix.debug_middleware.UpdateCacheMiddleware"
CDNX_FETCH_CACHE_MW = "codenerix.debug_middleware.FetchFromCacheMiddleware"
PAGE_CACHE = [UPDATE_CACHE_MW, COMMON_MW, FETCH_CACHE_MW]
# What autoload() turns PAGE_CACHE into once a debug tool is installed
CDNX_PAGE_CACHE = [CDNX_UPDATE_CACHE_MW, COMMON_MW, CDNX_FETCH_CACHE_MW]

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


# --- DEBUG_ALLOWED_IPS unset: nobody, whatever INTERNAL_IPS says ---------------


@pytest.mark.parametrize("debug", [True, False])
def test_unset_allows_nobody(debug: bool) -> None:
    with override_settings(DEBUG=debug, INTERNAL_IPS=[MY_IP], DEBUG_REQUIRE_SUPERUSER=False):
        assert show_toolbar(_request(MY_IP)) is False


# --- IP list ------------------------------------------------------------------


@override_settings(DEBUG=True, DEBUG_ALLOWED_IPS=[MY_IP], DEBUG_REQUIRE_SUPERUSER=False)
def test_listed_ip_only() -> None:
    assert show_toolbar(_request(MY_IP)) is True
    assert show_toolbar(_request(OTHER_IP)) is False


@override_settings(DEBUG=True, DEBUG_ALLOWED_IPS=["0.0.0.0"], DEBUG_REQUIRE_SUPERUSER=False)
def test_debug_any_ip() -> None:
    assert show_toolbar(_request(OTHER_IP)) is True
    assert check_debug_access(None) == []


# --- Superuser required by default, with DEBUG or not -------------------------


@pytest.mark.parametrize("debug", [True, False])
def test_superuser_required_by_default(debug: bool) -> None:
    with override_settings(DEBUG=debug, DEBUG_ALLOWED_IPS=[MY_IP]):
        assert show_toolbar(_request(MY_IP, superuser=False)) is False
        assert show_toolbar(_request(MY_IP, superuser=True)) is True
        assert show_toolbar(_request(OTHER_IP, superuser=True)) is False


@override_settings(DEBUG=False, DEBUG_ALLOWED_IPS=[MY_IP], DEBUG_REQUIRE_SUPERUSER=False)
def test_production_ip_only_when_opted_out() -> None:
    assert show_toolbar(_request(MY_IP)) is True
    assert show_toolbar(_request(OTHER_IP)) is False
    assert check_debug_access(None) == []


@override_settings(
    DEBUG=False,
    DEBUG_ALLOWED_IPS=["0.0.0.0"],
    DEBUG_REQUIRE_SUPERUSER=False,
)
def test_public_toolbar_fails_closed_and_is_reported() -> None:
    assert show_toolbar(_request(MY_IP, superuser=True)) is False
    assert [e.id for e in check_debug_access(None)] == ["codenerix.E001"]


@override_settings(DEBUG=False, DEBUG_ALLOWED_IPS=["0.0.0.0"])
def test_production_any_ip_with_superuser_is_allowed() -> None:
    assert show_toolbar(_request(OTHER_IP, superuser=True)) is True
    assert check_debug_access(None) == []


@pytest.mark.parametrize("value", [MY_IP, 42])
def test_malformed_setting_fails_closed_and_is_reported(value: object) -> None:
    with override_settings(DEBUG=True, DEBUG_ALLOWED_IPS=value, DEBUG_REQUIRE_SUPERUSER=False):
        # A bare string must not degrade into a substring match
        assert show_toolbar(_request(MY_IP)) is False
        assert [e.id for e in check_debug_access(None)] == ["codenerix.E001"]


@pytest.mark.parametrize(
    "removed",
    [
        {"DEBUG_TOOLBAR_ALLOWED_IPS": [MY_IP]},
        {"DEBUG_TOOLBAR_REQUIRE_SUPERUSER": False},
        {"DEBUG_TOOLBAR_PRODUCTION": True},
    ],
)
def test_removed_settings_fail_closed_and_are_reported(removed: dict[str, object]) -> None:
    with override_settings(
        DEBUG=True, DEBUG_ALLOWED_IPS=[MY_IP], DEBUG_REQUIRE_SUPERUSER=False, **removed
    ):
        assert show_toolbar(_request(MY_IP)) is False
        assert [e.id for e in check_debug_access(None)] == ["codenerix.E001"]


def test_autoload_rejects_removed_keyword() -> None:
    with pytest.raises(TypeError):
        autoload((), [], DEBUG_TOOLBAR=True, DEBUG_TOOLBAR_PRODUCTION=True)  # type: ignore[call-arg]


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
        DEBUG_PRODUCTION=True,
    )
    assert "debug_toolbar" in apps
    assert "debug_toolbar.middleware.DebugToolbarMiddleware" in middleware


def _production_middleware(middleware: Any, **kwargs: bool) -> Any:
    return autoload(
        (),
        middleware,
        DEBUG_TOOLBAR=True,
        DEBUG_PRODUCTION=True,
        **kwargs,
    )[1]


@pytest.mark.parametrize("container", [list, tuple])
def test_autoload_puts_toolbar_before_page_cache(container: type) -> None:
    middleware = _production_middleware(container(PAGE_CACHE))
    assert type(middleware) is container
    assert list(middleware) == [TOOLBAR_MW, *CDNX_PAGE_CACHE]


@pytest.mark.parametrize(
    "dead",
    [
        {"DEBUG_TOOLBAR": True, "DEBUG_PANEL": True},
        {"SNIPPET_SCREAM": True},
    ],
    ids=["debug_panel", "snippetscream"],
)
def test_autoload_rejects_dead_packages(dead: dict[str, bool]) -> None:
    # Neither package imports on supported Django / Python: startup failed anyway
    with pytest.raises(ValueError, match="no longer supported"):
        autoload((), list(PAGE_CACHE), DEBUG=True, **dead)


def test_autoload_ignores_dead_packages_where_they_never_applied() -> None:
    # Same conditions as before: without DEBUG (and the toolbar) they never took effect
    assert autoload((), list(PAGE_CACHE), DEBUG_PANEL=True, SNIPPET_SCREAM=True)[1] == PAGE_CACHE
    middleware = _production_middleware(list(PAGE_CACHE), DEBUG_PANEL=False)
    assert middleware == [TOOLBAR_MW, *CDNX_PAGE_CACHE]


def test_autoload_puts_toolbar_after_content_encoding() -> None:
    middleware = _production_middleware([GZIP_MW, *PAGE_CACHE])
    assert middleware == [GZIP_MW, TOOLBAR_MW, *CDNX_PAGE_CACHE]


def test_autoload_keeps_existing_toolbar_position() -> None:
    assert _production_middleware([*PAGE_CACHE, TOOLBAR_MW]) == [*CDNX_PAGE_CACHE, TOOLBAR_MW]


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
        "codenerix.debug_middleware.ProfilerMiddleware",
        TOOLBAR_MW,
        COMMON_MW,
        "django.contrib.messages.middleware.MessageMiddleware",
    ]


@pytest.mark.parametrize(
    "middleware",
    [
        [*PAGE_CACHE, TOOLBAR_MW],
        [UPDATE_CACHE_MW, TOOLBAR_MW, COMMON_MW, FETCH_CACHE_MW],
        [CDNX_UPDATE_CACHE_MW, TOOLBAR_MW, COMMON_MW, CDNX_FETCH_CACHE_MW],
        # Page cache added after autoload(): stock paths, not bypassed for debug requests
        [TOOLBAR_MW, *PAGE_CACHE],
        # Django's recommended order with GZip: autoload() cannot satisfy both rules
        _production_middleware([UPDATE_CACHE_MW, GZIP_MW, COMMON_MW, FETCH_CACHE_MW]),
    ],
)
@pytest.mark.parametrize(
    "access",
    [
        {"DEBUG_ALLOWED_IPS": [MY_IP]},
        {"DEBUG_ALLOWED_IPS": ["0.0.0.0"]},
    ],
)
def test_toolbar_behind_page_cache_fails_closed_and_is_reported(
    middleware: list[str],
    access: dict[str, list[str]],
) -> None:
    with override_settings(
        DEBUG=True,
        MIDDLEWARE=middleware,
        DEBUG_REQUIRE_SUPERUSER=False,
        DEBUG_TOOLBAR_CONFIG=DEBUG_TOOLBAR_DEFAULT_CONFIG,
        **access,
    ):
        assert show_toolbar(_request(MY_IP)) is False
        # Order (E002) and unbypassed cache (E003) are separate checks
        ids = {e.id for e in check_debug_access(None)}
        assert ids
        assert ids <= {"codenerix.E002", "codenerix.E003"}


@override_settings(
    DEBUG=True,
    DEBUG_ALLOWED_IPS=[MY_IP],
    DEBUG_REQUIRE_SUPERUSER=False,
    DEBUG_TOOLBAR_CONFIG=DEBUG_TOOLBAR_DEFAULT_CONFIG,
    MIDDLEWARE=[TOOLBAR_MW, *CDNX_PAGE_CACHE],
)
def test_toolbar_before_page_cache_is_allowed() -> None:
    assert show_toolbar(_request(MY_IP)) is True
    assert check_debug_access(None) == []


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
            DEBUG_ALLOWED_IPS=[MY_IP],
            DEBUG_REQUIRE_SUPERUSER=False,
            DEBUG_TOOLBAR_CONFIG=DEBUG_TOOLBAR_DEFAULT_CONFIG,
            CACHES={
                "default": {
                    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                    "LOCATION": "codenerix-toolbar-e2e",
                },
            },
            CACHE_MIDDLEWARE_SECONDS=600,
            TEMPLATES=[
                {"BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True},
            ],
        ):
            # Only importable once the toolbar app is installed (its models load on import)
            from debug_toolbar.middleware import show_toolbar_func_or_path

            # The toolbar memoises the callback; another test may have resolved it already
            show_toolbar_func_or_path.cache_clear()
            caches["default"].clear()
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


# Injected by the toolbar into HTML pages that have a </body>
TOOLBAR_MARKUP = b'id="djDebug"'


@pytest.mark.parametrize(
    ("url", "body", "markup"),
    [
        ("/json/", b'{"ok": true}', False),
        ("/html/", b"<html><body><p>page</p></body></html>", True),
    ],
)
@pytest.mark.usefixtures("cached_site_with_toolbar")
def test_toolbar_output_never_reaches_page_cache(url: str, body: bytes, markup: bool) -> None:
    mine = Client(REMOTE_ADDR=MY_IP).get(url)
    # Guard against a vacuous pass: the toolbar must really run for the allowed IP
    assert "djdt-request-id" in mine.headers
    assert (TOOLBAR_MARKUP in mine.content) is markup
    # Debug responses are kept out of browser and shared HTTP caches too
    assert "no-store" in mine.headers["Cache-Control"]

    # Nothing was stored for the debug request: this one is a miss that fills the cache
    other = Client(REMOTE_ADDR=OTHER_IP).get(url)
    assert "Age" not in other.headers
    assert "djdt-request-id" not in other.headers
    assert other.content == body

    # A debug request is never served from the page cache: it would show only the cache GET
    mine = Client(REMOTE_ADDR=MY_IP).get(url)
    assert "Age" not in mine.headers
    assert "djdt-request-id" in mine.headers

    other = Client(REMOTE_ADDR=OTHER_IP).get(url)
    assert "Age" in other.headers  # served from the page cache
    assert "djdt-request-id" not in other.headers
    assert "Server-Timing" not in other.headers
    assert other.content == body


@pytest.mark.usefixtures("cached_site_with_toolbar")
def test_toolbar_endpoints_never_reach_page_cache() -> None:
    # render_panel answers a cookie-less 200 JSON: cacheable unless the bypass applies
    request_id = Client(REMOTE_ADDR=MY_IP).get("/html/").headers["djdt-request-id"]
    url = f"/__debug__/render_panel/?request_id={request_id}&panel_id=HeadersPanel"

    mine = Client(REMOTE_ADDR=MY_IP).get(url)
    assert mine.status_code == 200
    # Guard against a vacuous pass: the panel content, not the "not available" stub
    assert "HTTP_REMOTE_ADDR" in mine.json()["content"] or MY_IP in mine.json()["content"]
    assert "no-store" in mine.headers["Cache-Control"]

    other = Client(REMOTE_ADDR=OTHER_IP).get(url)
    assert other.status_code == 404
    assert "Age" not in other.headers

    mine = Client(REMOTE_ADDR=MY_IP).get(url)
    assert "Age" not in mine.headers


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


# --- django_spaghetti's /plate/ behind the debug gate --------------------------

PLATE_BODY = b"plate"


def _plate(request: HttpRequest) -> HttpResponse:
    return HttpResponse(PLATE_BODY)


@pytest.fixture
def spaghetti_site(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    # Stand-in for django_spaghetti.views: only autourl()'s wiring is under test
    monkeypatch.setitem(sys.modules, "django_spaghetti", ModuleType("django_spaghetti"))
    views = ModuleType("django_spaghetti.views")
    views.plate = _plate  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "django_spaghetti.views", views)
    with override_settings(
        MIDDLEWARE=list(PAGE_CACHE),
        ROOT_URLCONF=__name__,
        DEBUG=True,
        DEBUG_ALLOWED_IPS=[MY_IP],
        DEBUG_REQUIRE_SUPERUSER=False,
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "codenerix-plate-e2e",
            },
        },
        CACHE_MIDDLEWARE_SECONDS=600,
    ):
        caches["default"].clear()
        urlpatterns[:] = autourl([], DEBUG=True, ROSETTA=False, ADMINSITE=False, SPAGHETTI=True)
        try:
            yield
        finally:
            urlpatterns.clear()


@pytest.mark.usefixtures("spaghetti_site")
def test_plate_is_behind_the_debug_gate() -> None:
    assert reverse("spaghetti:plate") == "/plate/"

    mine = Client(REMOTE_ADDR=MY_IP).get("/plate/")
    assert mine.status_code == 200
    assert mine.content == PLATE_BODY
    # Stock page cache (no debug tool installed): kept out of it by the headers
    assert "no-store" in mine.headers["Cache-Control"]

    other = Client(REMOTE_ADDR=OTHER_IP).get("/plate/")
    assert other.status_code == 404
    assert "Age" not in other.headers
