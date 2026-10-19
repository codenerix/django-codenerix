"""The debug gate shared by every debug tool: pyinstrument placement and gating,
the page cache bypass for debug requests, and the superuser check that runs
before SessionMiddleware and AuthenticationMiddleware."""

from collections.abc import Iterator
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import caches
from django.http import HttpRequest, JsonResponse
from django.middleware import cache as django_cache
from django.test import Client, RequestFactory, override_settings
from django.urls import URLPattern, URLResolver, path

from codenerix import debug_middleware
from codenerix.checks import check_debug_access
from codenerix.debug import autoload, show_pyinstrument, show_toolbar

MY_IP = "203.0.113.7"
OTHER_IP = "198.51.100.9"

PROFILER_MW = "codenerix.debug_middleware.ProfilerMiddleware"
UPSTREAM_PROFILER_MW = "pyinstrument.middleware.ProfilerMiddleware"
TOOLBAR_MW = "debug_toolbar.middleware.DebugToolbarMiddleware"
UPDATE_CACHE_MW = "django.middleware.cache.UpdateCacheMiddleware"
FETCH_CACHE_MW = "django.middleware.cache.FetchFromCacheMiddleware"
CACHE_MW = "django.middleware.cache.CacheMiddleware"
CDNX_UPDATE_CACHE_MW = "codenerix.debug_middleware.UpdateCacheMiddleware"
CDNX_FETCH_CACHE_MW = "codenerix.debug_middleware.FetchFromCacheMiddleware"
CDNX_CACHE_MW = "codenerix.debug_middleware.CacheMiddleware"
COMMON_MW = "django.middleware.common.CommonMiddleware"
GZIP_MW = "django.middleware.gzip.GZipMiddleware"
SESSION_MW = "django.contrib.sessions.middleware.SessionMiddleware"
AUTH_MW = "django.contrib.auth.middleware.AuthenticationMiddleware"
PAGE_CACHE = [UPDATE_CACHE_MW, COMMON_MW, FETCH_CACHE_MW]
CDNX_PAGE_CACHE = [CDNX_UPDATE_CACHE_MW, COMMON_MW, CDNX_FETCH_CACHE_MW]

# Marker of pyinstrument's HTML renderer output
PROFILE_MARKER = b"pyinstrument"


def _request(ip: str, query: str = "") -> HttpRequest:
    return RequestFactory().get(f"/{query}", REMOTE_ADDR=ip)


# --- Placement ----------------------------------------------------------------


@pytest.mark.parametrize("container", [list, tuple])
def test_autoload_puts_profiler_before_page_cache(container: type) -> None:
    middleware = autoload((), container(PAGE_CACHE), DEBUG=True, DEBUG_PYINSTRUMENT=True)[1]
    assert type(middleware) is container
    assert list(middleware) == [PROFILER_MW, *CDNX_PAGE_CACHE]


def test_autoload_profiler_production_is_opt_in() -> None:
    assert autoload((), list(PAGE_CACHE), DEBUG_PYINSTRUMENT=True)[1] == PAGE_CACHE
    middleware = autoload((), list(PAGE_CACHE), DEBUG_PYINSTRUMENT=True, DEBUG_PRODUCTION=True)[1]
    assert middleware == [PROFILER_MW, *CDNX_PAGE_CACHE]


def test_autoload_puts_profiler_outside_toolbar_and_after_gzip() -> None:
    middleware = autoload(
        (),
        [GZIP_MW, *PAGE_CACHE],
        DEBUG_TOOLBAR=True,
        DEBUG_PYINSTRUMENT=True,
        DEBUG_PRODUCTION=True,
    )[1]
    assert middleware == [GZIP_MW, PROFILER_MW, TOOLBAR_MW, *CDNX_PAGE_CACHE]


@pytest.mark.parametrize("existing", [PROFILER_MW, UPSTREAM_PROFILER_MW])
def test_autoload_keeps_existing_profiler_position(existing: str) -> None:
    middleware = autoload((), [*PAGE_CACHE, existing], DEBUG=True, DEBUG_PYINSTRUMENT=True)[1]
    # Kept where the project put it; the system check reports it behind the cache
    assert middleware == [*CDNX_PAGE_CACHE, existing]


def test_autoload_replaces_combined_cache_middleware() -> None:
    middleware = autoload((), [CACHE_MW], DEBUG=True, DEBUG_PYINSTRUMENT=True)[1]
    assert middleware == [PROFILER_MW, CDNX_CACHE_MW]


def test_autoload_without_debug_tools_keeps_stock_cache() -> None:
    assert autoload((), list(PAGE_CACHE), DEBUG=True)[1] == PAGE_CACHE


# --- Gating -------------------------------------------------------------------


@override_settings(DEBUG=True, DEBUG_ALLOWED_IPS=[MY_IP], DEBUG_REQUIRE_SUPERUSER=False)
def test_profiler_listed_ip_only() -> None:
    assert show_pyinstrument(_request(MY_IP)) is True
    assert show_pyinstrument(_request(OTHER_IP)) is False


@override_settings(DEBUG=True, INTERNAL_IPS=[MY_IP], DEBUG_REQUIRE_SUPERUSER=False)
def test_profiler_unset_allows_nobody() -> None:
    assert show_pyinstrument(_request(MY_IP)) is False


@override_settings(DEBUG=False, DEBUG_ALLOWED_IPS=[MY_IP])
def test_profiler_superuser_required_by_default() -> None:
    # No session cookie and no request.user: nobody to check, so closed
    assert show_pyinstrument(_request(MY_IP)) is False


@pytest.mark.parametrize("profiler", [PROFILER_MW, UPSTREAM_PROFILER_MW])
@pytest.mark.parametrize("cache", [PAGE_CACHE, CDNX_PAGE_CACHE])
def test_profiler_behind_page_cache_fails_closed_and_is_reported(
    profiler: str,
    cache: list[str],
) -> None:
    with override_settings(
        DEBUG=True,
        DEBUG_ALLOWED_IPS=[MY_IP],
        DEBUG_REQUIRE_SUPERUSER=False,
        MIDDLEWARE=[*cache, profiler],
    ):
        assert show_pyinstrument(_request(MY_IP)) is False
        messages = check_debug_access(None)
        # The stock pair is also reported as not bypassed (E003)
        expected = {"codenerix.E002"} | ({"codenerix.E003"} if cache == PAGE_CACHE else set())
        assert {e.id for e in messages} == expected
        assert any(f"{profiler} comes after" in e.msg for e in messages)


def _stock_cache_messages(middleware: list[str]) -> list[str]:
    with override_settings(
        DEBUG=True,
        DEBUG_ALLOWED_IPS=[MY_IP],
        DEBUG_REQUIRE_SUPERUSER=False,
        MIDDLEWARE=middleware,
    ):
        assert show_pyinstrument(_request(MY_IP)) is False
        # Placement messages start with the tool path; these start with the cache path
        return [e.msg for e in check_debug_access(None) if e.msg.startswith(UPDATE_CACHE_MW)]


def test_page_cache_added_after_autoload_is_reported() -> None:
    (message,) = _stock_cache_messages([PROFILER_MW, *PAGE_CACHE])
    assert "before calling autoload()" in message


def test_page_cache_added_again_after_autoload_is_reported() -> None:
    # Settings that run "if <stock path> not in MIDDLEWARE: insert" after autoload()
    middleware = autoload((), list(PAGE_CACHE), DEBUG=True, DEBUG_PYINSTRUMENT=True)[1]
    middleware = [UPDATE_CACHE_MW, *middleware, FETCH_CACHE_MW]
    (message,) = _stock_cache_messages(middleware)
    assert f"{UPDATE_CACHE_MW} and {CDNX_UPDATE_CACHE_MW} are both in MIDDLEWARE" in message
    assert "added again after autoload()" in message


def test_every_duplicated_stock_path_is_named() -> None:
    middleware = autoload((), list(PAGE_CACHE), DEBUG=True, DEBUG_PYINSTRUMENT=True)[1]
    middleware = [UPDATE_CACHE_MW, *middleware, FETCH_CACHE_MW]
    with override_settings(
        DEBUG=True,
        DEBUG_ALLOWED_IPS=[MY_IP],
        DEBUG_REQUIRE_SUPERUSER=False,
        MIDDLEWARE=middleware,
    ):
        messages = [e.msg for e in check_debug_access(None) if e.id == "codenerix.E003"]
    assert any(m.startswith(f"{UPDATE_CACHE_MW} and {CDNX_UPDATE_CACHE_MW}") for m in messages)
    assert any(m.startswith(f"{FETCH_CACHE_MW} and {CDNX_FETCH_CACHE_MW}") for m in messages)


# --- Project subclasses of the page cache middlewares --------------------------


class ProjectUpdateCache(django_cache.UpdateCacheMiddleware):
    pass


class ProjectFetchCache(django_cache.FetchFromCacheMiddleware):
    pass


class ProjectCache(django_cache.CacheMiddleware):
    pass


class ProjectBypassedUpdateCache(debug_middleware.UpdateCacheMiddleware):
    pass


class ProjectBypassedFetchCache(debug_middleware.FetchFromCacheMiddleware):
    pass


class ProjectBypassedBothHalves(
    debug_middleware.UpdateCacheMiddleware,
    debug_middleware.FetchFromCacheMiddleware,
    django_cache.CacheMiddleware,
):
    pass


PROJECT_UPDATE_MW = f"{__name__}.ProjectUpdateCache"
PROJECT_FETCH_MW = f"{__name__}.ProjectFetchCache"
PROJECT_CACHE_MW = f"{__name__}.ProjectCache"
PROJECT_PAGE_CACHE = [PROJECT_UPDATE_MW, COMMON_MW, PROJECT_FETCH_MW]
BYPASSED_PAGE_CACHE = [
    f"{__name__}.ProjectBypassedUpdateCache",
    COMMON_MW,
    f"{__name__}.ProjectBypassedFetchCache",
]


def _gate_settings(middleware: list[str]) -> Any:
    return override_settings(
        DEBUG=True,
        DEBUG_ALLOWED_IPS=[MY_IP],
        DEBUG_REQUIRE_SUPERUSER=False,
        MIDDLEWARE=middleware,
    )


@pytest.mark.parametrize(
    ("cache", "expected"),
    [
        (
            PROJECT_PAGE_CACHE,
            {PROJECT_UPDATE_MW: CDNX_UPDATE_CACHE_MW, PROJECT_FETCH_MW: CDNX_FETCH_CACHE_MW},
        ),
        ([PROJECT_CACHE_MW], {PROJECT_CACHE_MW: CDNX_CACHE_MW}),
    ],
    ids=["split", "combined"],
)
def test_unbypassed_cache_subclass_fails_closed_and_is_reported(
    cache: list[str],
    expected: dict[str, str],
) -> None:
    middleware = autoload((), list(cache), DEBUG=True, DEBUG_PYINSTRUMENT=True)[1]
    with _gate_settings(middleware):
        assert show_pyinstrument(_request(MY_IP)) is False
        messages = [e.msg for e in check_debug_access(None) if e.id == "codenerix.E003"]
    for subclass, replacement in expected.items():
        assert any(
            m.startswith(
                f"{subclass} subclasses Django's page cache middleware but not {replacement}"
            )
            for m in messages
        )


def test_bypassed_cache_subclass_is_allowed() -> None:
    with _gate_settings([PROFILER_MW, *BYPASSED_PAGE_CACHE]):
        assert show_pyinstrument(_request(MY_IP)) is True
        assert check_debug_access(None) == []


def test_subclass_of_both_codenerix_halves_is_allowed() -> None:
    # Bypasses both halves without deriving from codenerix CacheMiddleware
    with _gate_settings([PROFILER_MW, f"{__name__}.ProjectBypassedBothHalves"]):
        assert show_pyinstrument(_request(MY_IP)) is True
        assert check_debug_access(None) == []


def test_profiler_behind_cache_subclass_is_reported() -> None:
    with _gate_settings([*BYPASSED_PAGE_CACHE, PROFILER_MW]):
        assert show_pyinstrument(_request(MY_IP)) is False
        (check,) = check_debug_access(None)
    assert check.id == "codenerix.E002"
    assert check.msg.startswith(f"{PROFILER_MW} comes after {BYPASSED_PAGE_CACHE[0]}")


# --- More than one middleware of a kind ----------------------------------------


@pytest.mark.parametrize(
    "profilers",
    [[UPSTREAM_PROFILER_MW, PROFILER_MW], [PROFILER_MW, PROFILER_MW]],
    ids=["upstream-and-codenerix", "listed-twice"],
)
def test_duplicated_profiler_fails_closed_and_is_reported(profilers: list[str]) -> None:
    with _gate_settings([*profilers, *CDNX_PAGE_CACHE]):
        assert show_pyinstrument(_request(MY_IP, "?profile")) is False
        (check,) = check_debug_access(None)
    assert check.id == "codenerix.E005"
    assert check.msg.startswith(f"{profilers[0]} and {profilers[1]} are both in MIDDLEWARE")


@override_settings(
    DEBUG=True,
    DEBUG_ALLOWED_IPS=[MY_IP],
    DEBUG_REQUIRE_SUPERUSER=False,
    DEBUG_TOOLBAR_CONFIG={"SHOW_TOOLBAR_CALLBACK": "codenerix.debug.show_toolbar"},
    MIDDLEWARE=[TOOLBAR_MW, *CDNX_PAGE_CACHE, PROFILER_MW],
)
def test_misplaced_profiler_does_not_close_the_toolbar() -> None:
    assert show_toolbar(_request(MY_IP)) is True
    assert show_pyinstrument(_request(MY_IP)) is False


@override_settings(
    DEBUG=True,
    DEBUG_ALLOWED_IPS=[MY_IP],
    DEBUG_REQUIRE_SUPERUSER=False,
    MIDDLEWARE=[PROFILER_MW, TOOLBAR_MW, *CDNX_PAGE_CACHE],
)
def test_toolbar_stands_aside_on_profile_requests() -> None:
    assert show_toolbar(_request(MY_IP, "?profile")) is False
    assert show_pyinstrument(_request(MY_IP, "?profile")) is True
    assert show_toolbar(_request(MY_IP)) is True


@override_settings(
    DEBUG=True,
    DEBUG_ALLOWED_IPS=[MY_IP],
    DEBUG_REQUIRE_SUPERUSER=False,
    MIDDLEWARE=[TOOLBAR_MW, *CDNX_PAGE_CACHE],
)
def test_toolbar_ignores_profile_argument_without_profiler() -> None:
    assert show_toolbar(_request(MY_IP, "?profile")) is True


@override_settings(
    DEBUG=True,
    DEBUG_ALLOWED_IPS=[MY_IP],
    DEBUG_REQUIRE_SUPERUSER=False,
    MIDDLEWARE=[TOOLBAR_MW, *CDNX_PAGE_CACHE],
)
def test_toolbar_without_codenerix_callback_is_reported() -> None:
    # DEBUG_TOOLBAR_CONFIG unset: upstream's callback would ignore DEBUG_ALLOWED_IPS
    messages = check_debug_access(None)
    assert [e.id for e in messages] == ["codenerix.E004"]
    assert "SHOW_TOOLBAR_CALLBACK" in messages[0].msg


# --- End to end: profiles never reach the page cache --------------------------


def _json_view(request: HttpRequest) -> JsonResponse:
    user = getattr(request, "user", None)
    return JsonResponse({"user": user.get_username() if user is not None else None})


# ROOT_URLCONF for the end-to-end tests
urlpatterns: list[URLPattern | URLResolver] = [path("json/", _json_view)]

JSON_BODY = b'{"user": null}'


def _cached_site(middleware: Any, **settings: Any) -> Any:
    return override_settings(
        MIDDLEWARE=middleware,
        ROOT_URLCONF=__name__,
        DEBUG_ALLOWED_IPS=[MY_IP],
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "codenerix-debug-gate-e2e",
            },
        },
        CACHE_MIDDLEWARE_SECONDS=600,
        **settings,
    )


@pytest.fixture(autouse=True)
def _clear_page_cache() -> Iterator[None]:
    yield
    with override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "codenerix-debug-gate-e2e",
            },
        },
    ):
        caches["default"].clear()


@pytest.mark.parametrize(
    "mode",
    [{"DEBUG": True}, {"DEBUG_PRODUCTION": True}],
    ids=["debug", "production"],
)
@pytest.mark.parametrize("cache", [PAGE_CACHE, [CACHE_MW]], ids=["split", "combined"])
def test_profile_never_reaches_page_cache(mode: dict[str, bool], cache: list[str]) -> None:
    middleware = autoload((), list(cache), DEBUG_PYINSTRUMENT=True, **mode)[1]
    with _cached_site(middleware, DEBUG=mode.get("DEBUG", False), DEBUG_REQUIRE_SUPERUSER=False):
        mine = Client(REMOTE_ADDR=MY_IP).get("/json/?profile")
        # Guard against a vacuous pass: the profiler must really run for the allowed IP
        assert PROFILE_MARKER in mine.content
        assert "no-store" in mine.headers.get("Cache-Control", "")

        other = Client(REMOTE_ADDR=OTHER_IP).get("/json/?profile")
        assert other.content == JSON_BODY

        other = Client(REMOTE_ADDR=OTHER_IP).get("/json/?profile")
        assert "Age" in other.headers  # served from the page cache, still clean
        assert other.content == JSON_BODY

        # The allowed IP is never served from the cache: it gets a fresh profile
        mine = Client(REMOTE_ADDR=MY_IP).get("/json/?profile")
        assert "Age" not in mine.headers
        assert PROFILE_MARKER in mine.content


def test_duplicated_profiler_does_not_crash() -> None:
    # pyinstrument's own middleware listed by the project next to the codenerix one
    middleware = [
        UPSTREAM_PROFILER_MW,
        *autoload((), list(PAGE_CACHE), DEBUG=True, DEBUG_PYINSTRUMENT=True)[1],
    ]
    with _cached_site(
        middleware,
        DEBUG=True,
        DEBUG_REQUIRE_SUPERUSER=False,
        PYINSTRUMENT_SHOW_CALLBACK="codenerix.debug.show_pyinstrument",
    ):
        for ip in (MY_IP, OTHER_IP):
            response = Client(REMOTE_ADDR=ip).get("/json/?profile")
            assert response.status_code == 200
            assert PROFILE_MARKER not in response.content


# --- Superuser from the session, before SessionMiddleware ---------------------

SESSION_SITE = [UPDATE_CACHE_MW, SESSION_MW, AUTH_MW, FETCH_CACHE_MW]


def _login(is_superuser: bool) -> tuple[Client, Any]:
    user = get_user_model().objects.create_user(
        username="admin" if is_superuser else "staff",
        password="pw",  # noqa: S106 - test-only
        is_superuser=is_superuser,
    )
    client = Client(REMOTE_ADDR=MY_IP)
    client.force_login(user)
    return client, user


@pytest.mark.django_db
@pytest.mark.parametrize(("is_superuser", "profiled"), [(True, True), (False, False)])
def test_superuser_resolved_from_session(is_superuser: bool, profiled: bool) -> None:
    middleware = autoload((), list(SESSION_SITE), DEBUG=True, DEBUG_PYINSTRUMENT=True)[1]
    assert middleware[0] == PROFILER_MW
    with _cached_site(middleware, DEBUG=True):
        client, _ = _login(is_superuser)
        response = client.get("/json/?profile")
        assert (PROFILE_MARKER in response.content) is profiled


@pytest.mark.django_db
def test_anonymous_is_not_profiled() -> None:
    middleware = autoload((), list(SESSION_SITE), DEBUG=True, DEBUG_PYINSTRUMENT=True)[1]
    with _cached_site(middleware, DEBUG=True):
        response = Client(REMOTE_ADDR=MY_IP).get("/json/?profile")
        assert PROFILE_MARKER not in response.content


def test_broken_session_engine_fails_closed() -> None:
    # No SessionMiddleware, so Django itself never imports the engine
    middleware = autoload((), list(PAGE_CACHE), DEBUG=True, DEBUG_PYINSTRUMENT=True)[1]
    with _cached_site(middleware, DEBUG=True, SESSION_ENGINE="codenerix.tests.no_such_engine"):
        client = Client(REMOTE_ADDR=MY_IP)
        client.cookies["sessionid"] = "any-session-key"
        response = client.get("/json/?profile")
        assert response.status_code == 200
        assert PROFILE_MARKER not in response.content


@pytest.mark.django_db
def test_stale_session_hash_is_rejected_without_logging_out() -> None:
    middleware = autoload((), list(SESSION_SITE), DEBUG=True, DEBUG_PYINSTRUMENT=True)[1]
    old_key = "codenerix-old-secret-key"
    with _cached_site(middleware, DEBUG=True, SECRET_KEY=old_key):
        client, _ = _login(is_superuser=True)
    # Rotated secret: the session hash only verifies against the fallback key
    with _cached_site(
        middleware,
        DEBUG=True,
        SECRET_KEY="codenerix-new-secret-key",
        SECRET_KEY_FALLBACKS=[old_key],
    ):
        response = client.get("/json/?profile")
        # The gate does not rotate sessions, so it fails closed on a fallback hash...
        assert PROFILE_MARKER not in response.content
        # ...and leaves the session for Django, which keeps the user logged in
        assert response.json() == {"user": "admin"}
        assert client.get("/json/").json() == {"user": "admin"}
