#!/usr/bin/env python
#
# django-codenerix
#
# Codenerix GNU
#
# Project URL : http://www.codenerix.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import functools
from collections.abc import Callable, Collection
from importlib import import_module
from typing import TYPE_CHECKING, Any

import debug_toolbar
from django import VERSION
from django.conf import settings

if TYPE_CHECKING:
    # Type-only: keep settings-time imports of this module minimal
    from django.http import HttpRequest, HttpResponseBase

# Sentinel in DEBUG_ALLOWED_IPS meaning "any client address". It can never be
# a real REMOTE_ADDR, so it cannot collide with a listed client.
DEBUG_ANY_IP = "0.0.0.0"

# Settings removed in 6.0.0, mapped to what replaces them
_REMOVED_SETTINGS = {
    "DEBUG_TOOLBAR_ALLOWED_IPS": "DEBUG_ALLOWED_IPS",
    "DEBUG_TOOLBAR_REQUIRE_SUPERUSER": "DEBUG_REQUIRE_SUPERUSER",
    "DEBUG_TOOLBAR_PRODUCTION": "autoload(..., DEBUG_PRODUCTION=...)",
}

# Matched by dotted path: settings-time code cannot import project middlewares
_TOOLBAR_MIDDLEWARES = ("debug_toolbar.middleware.DebugToolbarMiddleware",)
_PROFILER_MIDDLEWARE = "codenerix.debug_middleware.ProfilerMiddleware"
_PROFILER_MIDDLEWARES = (
    "pyinstrument.middleware.ProfilerMiddleware",
    _PROFILER_MIDDLEWARE,
)
# Stock page cache middlewares and the codenerix subclasses that skip the
# cache for debug requests; autoload() swaps one for the other
_PAGE_CACHE_REPLACEMENTS = {
    "django.middleware.cache.UpdateCacheMiddleware": (
        "codenerix.debug_middleware.UpdateCacheMiddleware"
    ),
    "django.middleware.cache.CacheMiddleware": "codenerix.debug_middleware.CacheMiddleware",
    "django.middleware.cache.FetchFromCacheMiddleware": (
        "codenerix.debug_middleware.FetchFromCacheMiddleware"
    ),
}
_CONTENT_ENCODING_MIDDLEWARES = ("django.middleware.gzip.GZipMiddleware",)
_DEBUG_REQUEST_ATTR = "_codenerix_debug_request"

# System check ids, one per kind of problem, so each can be silenced on its own
E_ACCESS = "codenerix.E001"  # removed, malformed or public access settings
E_ORDER = "codenerix.E002"  # debug tool behind the page cache
E_CACHE = "codenerix.E003"  # page cache that debug requests would not bypass
E_CALLBACK = "codenerix.E004"  # toolbar callback that ignores DEBUG_ALLOWED_IPS
E_DUPLICATE = "codenerix.E005"  # more than one middleware of a debug tool


def debug_access_checks() -> list[tuple[str, str]]:
    """Return every problem found in the debug access settings, as (check id, message).

    Reported at startup by the codenerix system check. The gates fail closed on
    them: is_debug_request() on the access settings, and each tool on the
    placement of its own middleware.
    """
    checks = [(E_ACCESS, error) for error in _access_errors()]
    for family in (_TOOLBAR_MIDDLEWARES, _PROFILER_MIDDLEWARES):
        checks += [check for check in _middleware_errors(family) if check not in checks]
    checks += [(E_CALLBACK, error) for error in _toolbar_callback_errors()]
    return checks


def debug_access_errors() -> list[str]:
    """The messages of debug_access_checks(), without their check ids."""
    return [message for _, message in debug_access_checks()]


def _access_errors() -> list[str]:
    errors = [
        f"{old} was removed in django-codenerix 6.0.0; use {new}."
        for old, new in _REMOVED_SETTINGS.items()
        if hasattr(settings, old)
    ]
    allowed = getattr(settings, "DEBUG_ALLOWED_IPS", ())
    # A bare string would turn the membership test into a substring match
    if isinstance(allowed, str) or not isinstance(allowed, Collection):
        errors.append("DEBUG_ALLOWED_IPS must be a list, tuple or set of IP strings.")
    elif DEBUG_ANY_IP in allowed and not settings.DEBUG and not _require_superuser():
        errors.append(
            f"DEBUG_ALLOWED_IPS contains {DEBUG_ANY_IP!r} with DEBUG=False and "
            "DEBUG_REQUIRE_SUPERUSER=False: the debug tools would be public. "
            "List the client IPs instead.",
        )
    return errors


@functools.cache
def _page_cache_kind(path: str) -> tuple[bool, str] | None:
    """Classify a MIDDLEWARE entry as a page cache middleware.

    Returns None for anything else, or (bypassed, codenerix path): whether
    debug requests skip it, and the codenerix.debug_middleware class it is or
    should derive from. Imports project middlewares, so it is only called at
    check and request time, never while settings load.
    """
    if path in _PAGE_CACHE_REPLACEMENTS:
        return False, _PAGE_CACHE_REPLACEMENTS[path]
    if path in _PAGE_CACHE_REPLACEMENTS.values():
        return True, path
    if path in (*_TOOLBAR_MIDDLEWARES, *_PROFILER_MIDDLEWARES, *_CONTENT_ENCODING_MIDDLEWARES):
        return None
    from django.middleware import cache
    from django.utils.module_loading import import_string

    try:
        middleware = import_string(path)
    except Exception:  # noqa: BLE001
        # Not ours to report: Django fails on it when it loads MIDDLEWARE
        return None
    if not isinstance(middleware, type):
        return None
    update = issubclass(middleware, cache.UpdateCacheMiddleware)
    fetch = issubclass(middleware, cache.FetchFromCacheMiddleware)
    if update and fetch:
        stock = "django.middleware.cache.CacheMiddleware"
    elif update:
        stock = "django.middleware.cache.UpdateCacheMiddleware"
    elif fetch:
        stock = "django.middleware.cache.FetchFromCacheMiddleware"
    else:
        return None
    replacement = _PAGE_CACHE_REPLACEMENTS[stock]
    # By dotted path: importing codenerix.debug_middleware here would be a cyclic import.
    # The combined codenerix class also bypasses for each half of the pair
    bypassing = (
        import_string(replacement),
        import_string(_PAGE_CACHE_REPLACEMENTS["django.middleware.cache.CacheMiddleware"]),
    )
    return issubclass(middleware, bypassing), replacement


def _both_or_all(paths: list[str]) -> str:
    if len(paths) == 2:
        return f"{paths[0]} and {paths[1]} are both"
    return f"{', '.join(paths)} are all"


def _middleware_errors(family: tuple[str, ...]) -> list[tuple[str, str]]:
    middleware: list[str] = list(getattr(settings, "MIDDLEWARE", None) or ())
    tools = [i for i, path in enumerate(middleware) if path in family]
    if not tools:
        return []
    errors = []
    if len(tools) > 1:
        # e.g. pyinstrument's middleware listed after autoload() added the codenerix one
        errors.append(
            (
                E_DUPLICATE,
                f"{_both_or_all([middleware[i] for i in tools])} in MIDDLEWARE: they would "
                "run on the same request. Keep only one.",
            ),
        )
    kinds = {path: _page_cache_kind(path) for path in middleware}
    cache = [i for i, path in enumerate(middleware) if kinds[path] is not None]
    if cache and max(tools) > min(cache):
        errors.append(
            (
                E_ORDER,
                f"{middleware[max(tools)]} comes after {middleware[min(cache)]} in MIDDLEWARE: "
                "the page cache would store its output and serve it to every client. "
                "Move it before the page cache middlewares.",
            ),
        )
    errors += [(E_CACHE, error) for error in _page_cache_errors(middleware, kinds)]
    return errors


def _page_cache_errors(
    middleware: list[str],
    kinds: dict[str, tuple[bool, str] | None],
) -> list[str]:
    errors = []
    for path, kind in kinds.items():
        if kind is None or kind[0]:
            continue
        replacement = kind[1]
        if path not in _PAGE_CACHE_REPLACEMENTS:
            errors.append(
                f"{path} subclasses Django's page cache middleware but not {replacement}: "
                "debug requests would be served from and stored in the page cache. "
                f"Derive it from {replacement}.",
            )
        elif replacement in middleware:
            # Typical cause: an "if <stock path> not in MIDDLEWARE" guard run after autoload()
            errors.append(
                f"{path} and {replacement} are both in MIDDLEWARE: {path} was added "
                "again after autoload() replaced it, so the page cache runs twice and debug "
                "requests would be served from and stored in it. Code that checks MIDDLEWARE "
                f"for {path} after calling autoload() must also accept {replacement}.",
            )
        else:
            errors.append(
                f"{path} in MIDDLEWARE together with debug tools: debug requests would be "
                "served from and stored in the page cache. Add the page cache middlewares "
                f"before calling autoload(), or use {replacement}.",
            )
    return errors


def _toolbar_callback_errors() -> list[str]:
    middleware = getattr(settings, "MIDDLEWARE", None) or ()
    if not any(path in _TOOLBAR_MIDDLEWARES for path in middleware):
        return []
    config = getattr(settings, "DEBUG_TOOLBAR_CONFIG", None) or {}
    callback = config.get("SHOW_TOOLBAR_CALLBACK")
    if callback in (DEBUG_TOOLBAR_DEFAULT_CONFIG["SHOW_TOOLBAR_CALLBACK"], show_toolbar):
        return []
    return [
        "DEBUG_TOOLBAR_CONFIG['SHOW_TOOLBAR_CALLBACK'] is not codenerix.debug.show_toolbar: "
        "the toolbar ignores DEBUG_ALLOWED_IPS. Set DEBUG_TOOLBAR_CONFIG = "
        "DEBUG_TOOLBAR_DEFAULT_CONFIG.",
    ]


def _insert_debug_middlewares(
    middleware: list[str] | tuple[str, ...],
    debug_middlewares: list[str],
) -> list[str] | tuple[str, ...]:
    # As early as possible, but after anything that encodes the response body
    # (django-debug-toolbar installation docs); early also keeps it outside the page cache
    encoders = [i for i, path in enumerate(middleware) if path in _CONTENT_ENCODING_MIDDLEWARES]
    position = encoders[-1] + 1 if encoders else 0
    if isinstance(middleware, tuple):
        return (*middleware[:position], *debug_middlewares, *middleware[position:])
    middleware[position:position] = debug_middlewares
    return middleware


def _replace_page_cache_middlewares(
    middleware: list[str] | tuple[str, ...],
) -> list[str] | tuple[str, ...]:
    replaced = [_PAGE_CACHE_REPLACEMENTS.get(path, path) for path in middleware]
    if isinstance(middleware, tuple):
        return tuple(replaced)
    middleware[:] = replaced
    return middleware


def _require_superuser() -> bool:
    return bool(getattr(settings, "DEBUG_REQUIRE_SUPERUSER", True))


def _session_user(request: HttpRequest) -> Any:
    """Read the logged-in user from the session cookie, without changing the session.

    Debug middlewares run before SessionMiddleware and AuthenticationMiddleware,
    so request.user does not exist yet. django.contrib.auth.get_user() is not
    used: on a fallback or stale session hash it cycles or flushes the session
    in the store, which would log the real request out.

    Loading the session has the side effects SessionMiddleware has on the same
    request: the file backend deletes and recreates an expired or undecodable
    session file, cached_db fills the cache on a miss; db and signed_cookies
    write nothing. Stricter than get_user(): a user object without
    get_session_auth_hash() is rejected, and a SESSION_ENGINE that cannot be
    imported means nobody.

    For an allowed IP carrying a session cookie, SessionMiddleware loads the
    session again later. Deliberately not shared: handing this user to
    AuthenticationMiddleware would skip get_user()'s rotation and flush.
    """
    from django.apps import apps

    if not apps.is_installed("django.contrib.auth"):
        return None
    session_key = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
    if not session_key:
        return None
    from django.contrib.auth import (
        BACKEND_SESSION_KEY,
        HASH_SESSION_KEY,
        SESSION_KEY,
        get_user_model,
        load_backend,
    )
    from django.utils.crypto import constant_time_compare

    try:
        session_store = import_module(settings.SESSION_ENGINE).SessionStore
    except (ImportError, AttributeError):
        # Fail closed: without SessionMiddleware nothing else trips on a broken engine
        return None
    session = session_store(session_key)
    try:
        user_id = get_user_model()._meta.pk.to_python(session[SESSION_KEY])
        backend_path = session[BACKEND_SESSION_KEY]
        session_hash = session[HASH_SESSION_KEY]
    except KeyError:
        return None
    if backend_path not in settings.AUTHENTICATION_BACKENDS:
        return None
    user = load_backend(backend_path).get_user(user_id)
    if user is None or not hasattr(user, "get_session_auth_hash"):
        return None
    # Current secret only: a fallback hash needs a session rotation we must not do here
    if not constant_time_compare(session_hash, user.get_session_auth_hash()):
        return None
    return user


def _client_allowed(request: HttpRequest) -> bool:
    if _access_errors():
        # Fail closed; the system check reports the misconfiguration
        return False
    allowed = getattr(settings, "DEBUG_ALLOWED_IPS", ())
    if DEBUG_ANY_IP not in allowed and request.META.get("REMOTE_ADDR") not in allowed:
        return False
    if not _require_superuser():
        return True
    user = getattr(request, "user", None)
    if user is None:
        user = _session_user(request)
    return bool(user is not None and user.is_authenticated and user.is_superuser)


def is_debug_request(request: HttpRequest) -> bool:
    """Whether this request may see debug tools output.

    Driven by DEBUG_ALLOWED_IPS (default: nobody; "0.0.0.0" means any client)
    and DEBUG_REQUIRE_SUPERUSER (default True). Settings are read per request,
    so projects may define them anywhere in their settings module. The result
    is memoised on the request, so every debug middleware and the page cache
    bypass agree on it.

    The superuser is read from the session cookie: a user authenticated later
    in the chain (a token or OTP middleware setting request.user) never passes.
    """
    decision = getattr(request, _DEBUG_REQUEST_ATTR, None)
    if decision is None:
        decision = _client_allowed(request)
        setattr(request, _DEBUG_REQUEST_ATTR, decision)
    return decision


def _profile_requested(request: HttpRequest) -> bool:
    middleware = getattr(settings, "MIDDLEWARE", None) or ()
    if not any(path in _PROFILER_MIDDLEWARES for path in middleware):
        return False
    return getattr(settings, "PYINSTRUMENT_URL_ARGUMENT", "profile") in request.GET


def show_toolbar(request: HttpRequest) -> bool:
    """SHOW_TOOLBAR_CALLBACK: is_debug_request(), unless the toolbar is misplaced.

    The toolbar also stands aside on pyinstrument's ?profile requests: the
    profile replaces the response, and the toolbar's own cost would only skew it.
    """
    if _middleware_errors(_TOOLBAR_MIDDLEWARES):
        # Fail closed; the system check reports the misconfiguration
        return False
    if _profile_requested(request):
        return False
    return is_debug_request(request)


def show_pyinstrument(request: HttpRequest) -> bool:
    """PYINSTRUMENT_SHOW_CALLBACK: is_debug_request(), unless the profiler is misplaced.

    codenerix.debug_middleware.ProfilerMiddleware applies it on its own; set it
    as PYINSTRUMENT_SHOW_CALLBACK when using pyinstrument's middleware directly.
    On URLs that end in a slash, ?profile needs it too (/page/?profile): without
    it the profile is that of CommonMiddleware's redirect, not of the view.
    """
    if _middleware_errors(_PROFILER_MIDDLEWARES):
        # Fail closed; the system check reports the misconfiguration
        return False
    return is_debug_request(request)


# Full set of built-in panels, in upstream order. Requires
# django-debug-toolbar >= 7.1 (TasksPanel landed there); older releases raise
# ImportError on the panels they do not ship.
DEBUG_TOOLBAR_DEFAULT_PANELS = (
    "debug_toolbar.panels.history.HistoryPanel",
    "debug_toolbar.panels.versions.VersionsPanel",
    "debug_toolbar.panels.timer.TimerPanel",
    "debug_toolbar.panels.settings.SettingsPanel",
    "debug_toolbar.panels.headers.HeadersPanel",
    "debug_toolbar.panels.request.RequestPanel",
    "debug_toolbar.panels.sql.SQLPanel",
    "debug_toolbar.panels.staticfiles.StaticFilesPanel",
    "debug_toolbar.panels.templates.TemplatesPanel",
    "debug_toolbar.panels.alerts.AlertsPanel",
    "debug_toolbar.panels.cache.CachePanel",
    "debug_toolbar.panels.signals.SignalsPanel",
    "debug_toolbar.panels.tasks.TasksPanel",
    "debug_toolbar.panels.community.CommunityPanel",
    # Deprecated since 6.2 in favour of HistoryPanel, but still part of the
    # upstream default set. Sits in DISABLE_PANELS, so it is never instantiated
    # and emits no warning unless a project enables it. Drop it when upstream does.
    "debug_toolbar.panels.redirects.RedirectsPanel",
    # Not deprecated, only disabled by default via DISABLE_PANELS: profiling
    # every request is expensive.
    "debug_toolbar.panels.profiling.ProfilingPanel",
)
DEBUG_TOOLBAR_DEFAULT_CONFIG = {
    # Toolbar options
    "RESULTS_CACHE_SIZE": 100,
    "SHOW_COLLAPSED": True,
    # Panel options
    "SQL_WARNING_THRESHOLD": 100,  # milliseconds
    # Visibility rules (DEBUG_ALLOWED_IPS, DEBUG_REQUIRE_SUPERUSER)
    "SHOW_TOOLBAR_CALLBACK": "codenerix.debug.show_toolbar",
}


# Autoload
def autoload(
    INSTALLED_APPS,  # noqa: N803
    MIDDLEWARE,
    DEBUG=False,
    SPAGHETTI=False,
    ROSETTA=False,
    ADMINSITE=False,
    DEBUG_TOOLBAR=False,
    DEBUG_PANEL=False,
    SNIPPET_SCREAM=False,
    GRAPH_MODELS=False,
    CODENERIX_DISABLE_LOG=False,
    DEBUG_PYINSTRUMENT=False,
    DEBUG_PRODUCTION: bool = False,
):
    EXTRA_MIDDLEWARES = []  # noqa: N806
    # Outermost first: [profiler, toolbar, ...]
    debug_middlewares: list[str] = []
    # Production use is opt-in; per-request visibility is then up to is_debug_request
    debug_tools = DEBUG or DEBUG_PRODUCTION
    if DEBUG and SPAGHETTI:
        INSTALLED_APPS += ("django_spaghetti",)
    if DEBUG and ROSETTA:
        INSTALLED_APPS += ("rosetta",)
    if "django.contrib.admin" not in INSTALLED_APPS and not CODENERIX_DISABLE_LOG:
        INSTALLED_APPS += ("django.contrib.admin",)
    if DEBUG and ADMINSITE and not CODENERIX_DISABLE_LOG:
        EXTRA_MIDDLEWARES.append(
            "django.contrib.messages.middleware.MessageMiddleware",
        )
    # Raised only where they used to take effect, which already failed at startup
    if DEBUG_TOOLBAR and debug_tools and DEBUG_PANEL:
        raise ValueError(
            "autoload(DEBUG_PANEL=True) is no longer supported: django-debug-panel does not "
            "import on Django 2.0 or later. Use DEBUG_PANEL=False.",
        )
    if DEBUG and SNIPPET_SCREAM:
        raise ValueError(
            "autoload(SNIPPET_SCREAM=True) is no longer supported: django-snippetscream does "
            "not import on Python 3. Use SNIPPET_SCREAM=False, or DEBUG_PYINSTRUMENT.",
        )
    if DEBUG_TOOLBAR and debug_tools:
        INSTALLED_APPS += ("debug_toolbar",)
        debug_middlewares.append("debug_toolbar.middleware.DebugToolbarMiddleware")
    if DEBUG and GRAPH_MODELS:
        INSTALLED_APPS += ("django_extensions",)
    profiler = DEBUG_PYINSTRUMENT and debug_tools
    # A pyinstrument middleware already in MIDDLEWARE is kept instead
    if profiler and not set(_PROFILER_MIDDLEWARES) & set(MIDDLEWARE):
        # Outside the toolbar, which stands aside on ?profile requests (show_toolbar)
        debug_middlewares.insert(0, _PROFILER_MIDDLEWARE)

    # Attach new middlewares
    existing = set(MIDDLEWARE)
    extra = [middleware for middleware in EXTRA_MIDDLEWARES if middleware not in existing]
    if isinstance(MIDDLEWARE, tuple):
        MIDDLEWARE += tuple(extra)
    else:
        MIDDLEWARE += extra
    # Not appended: behind the page cache their output would be cached for everyone
    new_debug = [middleware for middleware in debug_middlewares if middleware not in existing]
    if new_debug:
        MIDDLEWARE = _insert_debug_middlewares(MIDDLEWARE, new_debug)  # noqa: N806
    if debug_middlewares or profiler:
        # Debug requests must neither read nor fill the page cache
        MIDDLEWARE = _replace_page_cache_middlewares(MIDDLEWARE)  # noqa: N806

    # Return final results
    return (INSTALLED_APPS, MIDDLEWARE)


def _debug_only(view: Callable[..., HttpResponseBase]) -> Callable[..., HttpResponseBase]:
    """Serve view only to requests is_debug_request() accepts; 404 for anyone else."""
    from django.http import Http404
    from django.views.decorators.cache import never_cache

    @functools.wraps(view)
    def gated(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        if not is_debug_request(request):
            raise Http404
        return view(request, *args, **kwargs)

    # Kept out of the page cache, which autoload() leaves stock when no debug tool is on
    return never_cache(gated)


# Autourl
def autourl(
    URLPATTERNS,  # noqa: N803
    DEBUG,
    ROSETTA,
    ADMINSITE,
    SPAGHETTI,
    DEBUG_TOOLBAR=False,
    DEBUG_PANEL=False,
):
    from django.conf.urls import include
    from django.urls import re_path

    del DEBUG_PANEL  # Not used

    if ROSETTA:
        URLPATTERNS += [re_path(r"^rosetta/", include("rosetta.urls"))]

    if ADMINSITE:
        from django.contrib import admin

        if VERSION[0] < 2 and ADMINSITE:
            URLPATTERNS += [re_path(r"^admin/", include(admin.site.urls))]  # pyright: ignore[reportArgumentType]
        else:
            from django.urls import path

            URLPATTERNS += [
                path(
                    "admin/",
                    admin.site.urls,
                ),
            ]
    if DEBUG and SPAGHETTI:
        from django.urls import path
        from django.utils.module_loading import import_string

        # Same route and namespace as django_spaghetti.urls, behind the debug gate
        plate = import_string("django_spaghetti.views.plate")
        spaghetti = ([path("", _debug_only(plate), name="plate")], "spaghetti")
        URLPATTERNS += [re_path(r"^plate/", include(spaghetti))]
    # Follow what autoload() installed instead of re-deriving it from DEBUG
    if DEBUG_TOOLBAR and "debug_toolbar" in settings.INSTALLED_APPS:
        URLPATTERNS += [re_path(r"^__debug__/", include(debug_toolbar.urls))]
    return URLPATTERNS


# Codenerix STATIC
def codenerix_statics(DEBUG, STATIC_URL="/static/"):  # noqa: N803
    # Backward compatibility for older configurations (CODENERIXSOURCE is
    # deprecated from now!)
    if isinstance(STATIC_URL, bool):
        DEBUG = STATIC_URL  # noqa: N806
        STATIC_URL = "/static/"  # noqa: N806

    locales = '\
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.ar.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.bg.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.ca.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.cs.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.da.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.de.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.ee.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.el.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.es.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.fi.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.fr.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.he.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.hr.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.hu.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.id.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.is.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.it.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.ja.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.ko.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.lt.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.lv.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.ms.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.nb.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.nl.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.no.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.pl.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.pt-BR.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.pt.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.ro.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.rs.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.rs-latin.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.ru.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.sk.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.sl.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.sv.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.sw.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.th.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.tr.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.ua.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.uk.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.zh-CN.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/locales/bootstrap-datetimepicker.zh-TW.js"></script> '  # noqa: E501

    CODENERIX_CSS_DEBUG = (
        ' \
    <link href="{STATIC_URL}codenerix/lib/bootstrap/css/bootstrap.css" rel="stylesheet"> \
    <link href="{STATIC_URL}djangular/css/styles.css" rel="stylesheet"> \
    <link href="{STATIC_URL}djangular/css/bootstrap3.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-bootstrap-colorpicker/css/colorpicker.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-daterangepicker/daterangepicker-bs3.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-ui/select.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-material/angular-material.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-loading-bar/loading-bar.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/css/bootstrap-datetimepicker.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/nspopover/nspopover.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/css/base.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/css/lists.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/bootstrap-vertical-grid.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/fontawesome/css/font-awesome.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/fontawesome-animation/font-awesome-animation.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/textAngular/textAngular.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-quill/quill.snow.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-hotkeys/hotkeys.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/bootstrap-switch/bootstrap-switch.css" rel="stylesheet"> \
    '
        + ""
    )  # noqa: N806  # noqa: E501

    CODENERIX_CSS_MIN = (
        ' \
    <link href="{STATIC_URL}codenerix/lib/bootstrap/css/bootstrap.min.css" rel="stylesheet"> \
    <link href="{STATIC_URL}djangular/css/styles.css" rel="stylesheet"> \
    <link href="{STATIC_URL}djangular/css/bootstrap3.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-bootstrap-colorpicker/css/colorpicker.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-daterangepicker/daterangepicker-bs3.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-ui/select.min.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-material/angular-material.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-loading-bar/loading-bar.min.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/css/bootstrap-datetimepicker.min.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/nspopover/nspopover.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/css/base.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/css/lists.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/bootstrap-vertical-grid.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/fontawesome/css/font-awesome.min.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/fontawesome-animation/font-awesome-animation.min.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/textAngular/textAngular.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-quill/quill.snow.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/angular-hotkeys/hotkeys.min.css" rel="stylesheet"> \
    <link href="{STATIC_URL}codenerix/lib/bootstrap-switch/bootstrap-switch.min.css" rel="stylesheet"> \
    '
        + ""
    )  # noqa: N806  # noqa: E501

    CODENERIX_JS_DEBUG = (
        ' \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/jquery/jquery.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/moment/moment.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap/js/bootstrap.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-dropdowns-functions.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-animate.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-aria.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-messages.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-ui/ui-bootstrap-tpls.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-ui/angular-ui-router.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-ui/select.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-ui/datetimepicker.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-resource.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-cookies.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-sanitize.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-touch.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-material/angular-material.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}djangular/js/django-angular.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-loading-bar/loading-bar.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/bootstrap-datetimepicker.js"></script> \
\
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-bootstrap-colorpicker/js/bootstrap-colorpicker-module.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-daterangepicker/daterangepicker.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-daterangepicker/angular-daterangepicker.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-checklist-model.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/color-contrast.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/nspopover/nspopover.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/notifyjs/notify.js"></script> \
    <script type="text/javascript" src="https://www.google.com/recaptcha/api.js?onload=vcRecaptchaApiLoaded&render=explicit" async defer></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-recaptcha/angular-recaptcha.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-base64-upload.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/file_validation.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/js/codenerix.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/js/notify.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/js/filters.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/js/inotify.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/textAngular/textAngular-rangy.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/textAngular/textAngular-sanitize.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/textAngular/textAngular.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-quill/quill.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-quill/ng-quill.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-hotkeys/hotkeys.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-switch/bootstrap-switch.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-bootstrap-switch/angular-bootstrap-switch.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-qr/qrcode.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-qr/angular-qr.js"></script> \
    '
        + locales
    )  # noqa: N806  # noqa: E501

    CODENERIX_JS_MIN = (
        ' \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/jquery/jquery.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/moment/moment.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap/js/bootstrap.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-dropdowns-functions.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-animate.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-aria.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-messages.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-ui/ui-bootstrap-tpls.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-ui/angular-ui-router.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-ui/select.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-ui/datetimepicker.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-resource.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-cookies.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-sanitize.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular/angular-touch.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-material/angular-material.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}djangular/js/django-angular.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-loading-bar/loading-bar.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-datetimepicker/js/bootstrap-datetimepicker.js"></script> <!-- .min.js FAILS! --> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-bootstrap-colorpicker/js/bootstrap-colorpicker-module.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-daterangepicker/daterangepicker.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-daterangepicker/angular-daterangepicker.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-checklist-model.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/color-contrast.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/nspopover/nspopover.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/notifyjs/notify.min.js"></script> \
    <script type="text/javascript" src="https://www.google.com/recaptcha/api.js?onload=vcRecaptchaApiLoaded&render=explicit" async defer></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-recaptcha/angular-recaptcha.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-base64-upload.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/file_validation.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/js/codenerix.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/js/notify.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/js/filters.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/js/inotify.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/textAngular/textAngular-rangy.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/textAngular/textAngular-sanitize.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/textAngular/textAngular.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-quill/quill.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-quill/ng-quill.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-hotkeys/hotkeys.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/bootstrap-switch/bootstrap-switch.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-bootstrap-switch/angular-bootstrap-switch.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-qr/qrcode.min.js"></script> \
    <script type="text/javascript" src="{STATIC_URL}codenerix/lib/angular-qr/angular-qr.min.js"></script> \
    '  # noqa: E501
        + locales
    )  # noqa: N806

    # Load CODENERIX CSS
    if DEBUG:
        CODENERIX_CSS = CODENERIX_CSS_DEBUG  # noqa: N806
    else:
        CODENERIX_CSS = CODENERIX_CSS_MIN  # noqa: N806
    # Load CODENERIX JS
    if DEBUG:
        CODENERIX_JS = CODENERIX_JS_DEBUG  # noqa: N806
    else:
        CODENERIX_JS = CODENERIX_JS_MIN  # noqa: N806
    return (
        CODENERIX_CSS.format(STATIC_URL=STATIC_URL),
        CODENERIX_JS.format(STATIC_URL=STATIC_URL),
    )
