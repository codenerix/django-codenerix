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

import sys
from collections.abc import Iterator, Sequence
from importlib.util import find_spec
from typing import Any

from django.apps import AppConfig
from django.conf import settings
from django.core.checks import CheckMessage, Error
from django.urls import URLPattern, URLResolver, get_resolver

from codenerix.debug import debug_access_checks

E_HAYSTACK_MISSING = "codenerix.E006"  # routed view with haystack = True, extra not installed
E_HAYSTACK_CONTRIB = "codenerix.E007"  # HAYSTACK_CONNECTIONS engine under the removed contrib
E_OTP_WINDOW = "codenerix.E008"  # OTP_VALID_WINDOW that is not a non-negative integer

REMOVED_CONTRIB = "codenerix.contrib."


def check_debug_access(
    app_configs: Sequence[AppConfig] | None,
    **kwargs: Any,
) -> list[CheckMessage]:
    """Report unsafe, malformed or removed debug access settings (E001), debug
    tools placed behind the page cache middlewares (E002), a page cache that
    debug requests would not bypass (E003), a toolbar callback that ignores
    DEBUG_ALLOWED_IPS (E004) and more than one middleware of a debug tool (E005).

    The debug gates already fail closed on these; this makes the cause visible
    on runserver and on any management command (e.g. `manage.py check --deploy`).
    """
    return [Error(message, id=check_id) for check_id, message in debug_access_checks()]


def _haystack_installed() -> bool:
    # find_spec, not an import: the check must not load the package
    return find_spec("haystack") is not None


def _routed_view_classes(patterns: Sequence[URLPattern | URLResolver]) -> Iterator[type]:
    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            yield from _routed_view_classes(pattern.url_patterns)
            continue
        view_class = getattr(pattern.callback, "view_class", None)
        if isinstance(view_class, type):
            yield view_class


def _haystack_view_errors() -> list[str]:
    """Routed GenList subclasses with haystack = True while django-haystack is
    not importable: get_queryset() raises ImproperlyConfigured on their first
    request, which nothing reported before."""
    if _haystack_installed():
        return []
    try:
        patterns = get_resolver().url_patterns
    except Exception:  # noqa: BLE001
        # A URLconf that does not import is reported by Django's own urls.* checks
        return []
    # Not imported here: codenerix.views reads STATIC_URL at import and would stop every
    # management command of a project that leaves it unset. Resolving the URLconf imported
    # every routed view, so if no view module loaded it, no routed view derives from GenList
    views = sys.modules.get("codenerix.views")
    if views is None:
        return []
    GenList = views.GenList  # noqa: N806
    seen: set[type] = set()
    errors = []
    for view_class in _routed_view_classes(patterns):
        if view_class in seen or not issubclass(view_class, GenList):
            continue
        seen.add(view_class)
        if getattr(view_class, "haystack", False):
            errors.append(
                f"{view_class.__module__}.{view_class.__qualname__}.haystack is True but "
                "django-haystack is not installed: its first request would fail. Install "
                "django-codenerix[haystack], or set haystack = False.",
            )
    return errors


def _haystack_engine_errors() -> list[str]:
    """HAYSTACK_CONNECTIONS engines under codenerix.contrib, removed in 6.2.0:
    with django-haystack installed, check passes and the first search (or every
    save, with a realtime signal processor) raises ModuleNotFoundError."""
    connections = getattr(settings, "HAYSTACK_CONNECTIONS", None)
    if not isinstance(connections, dict):
        return []
    errors = []
    for alias, config in connections.items():
        engine = config.get("ENGINE") if isinstance(config, dict) else None
        if isinstance(engine, str) and engine.startswith(REMOVED_CONTRIB):
            errors.append(
                f"HAYSTACK_CONNECTIONS[{alias!r}]['ENGINE'] is {engine}: codenerix.contrib was "
                "removed in django-codenerix 6.2.0, so the engine cannot be imported. Copy the "
                "engine class into the project, or use "
                "haystack.backends.elasticsearch7_backend.Elasticsearch7SearchEngine, whose "
                "client the project must now install itself (elasticsearch>=7,<8).",
            )
    return errors


def check_haystack(
    app_configs: Sequence[AppConfig] | None,
    **kwargs: Any,
) -> list[CheckMessage]:
    """Report at check time the haystack configurations that 6.2.0 left to fail
    on the first request: a routed view with haystack = True without the extra
    (E006) and a HAYSTACK_CONNECTIONS engine under the removed codenerix.contrib
    (E007). A missing "haystack" app with the package absent cannot be a check:
    Django stops while populating INSTALLED_APPS, before any check runs. E006
    probes the package with find_spec, without importing it, so an installed but
    broken django-haystack passes here and fails on the view's first request.
    """
    errors: list[CheckMessage] = [
        Error(message, id=E_HAYSTACK_MISSING) for message in _haystack_view_errors()
    ]
    errors += [Error(message, id=E_HAYSTACK_CONTRIB) for message in _haystack_engine_errors()]
    return errors


def otp_valid_window(value: object) -> int | None:
    """OTP_VALID_WINDOW as OTPAuth uses it: a non-negative integer, else None."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def check_otp_valid_window(
    app_configs: Sequence[AppConfig] | None,
    **kwargs: Any,
) -> list[CheckMessage]:
    """Report an OTP_VALID_WINDOW that is not a non-negative integer (E008): a
    string from an environment variable used to raise TypeError at login, and a
    negative value refused every code. OTPAuth falls back to 0 meanwhile."""
    value = getattr(settings, "OTP_VALID_WINDOW", 1)
    if otp_valid_window(value) is not None:
        return []
    return [
        Error(
            f"OTP_VALID_WINDOW is {value!r}: it must be a non-negative integer (steps of 30 s "
            "accepted on each side of the current one). OTPAuth falls back to 0, the current "
            "step only.",
            id=E_OTP_WINDOW,
        ),
    ]
