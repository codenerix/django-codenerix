"""Guard the debug toolbar defaults against upstream drift.

``codenerix.debug`` ships an explicit copy of django-debug-toolbar's default
panel list. New upstream panels (Alerts in 4.4.3, Community in 6.1, Tasks in
7.1) would otherwise go unnoticed until somebody diffed the two lists by hand.
These tests fail the moment that copy stops matching the installed toolbar.
"""

# debug_toolbar.settings is not a documented public API. If upstream renames
# these constants the import fails loudly, which is the point: the guard must
# never silently stop guarding.
from debug_toolbar.settings import CONFIG_DEFAULTS, PANELS_DEFAULTS
from django.conf import settings
from django.test import override_settings
from django.utils.module_loading import import_string

from codenerix.debug import (
    DEBUG_TOOLBAR_DEFAULT_CONFIG,
    DEBUG_TOOLBAR_DEFAULT_PANELS,
)

# Importing the panel modules pulls debug_toolbar.models.HistoryEntry, which
# needs the app registered. Scoped to this test so the rest of the suite keeps
# running without the toolbar installed. STATIC_URL cannot be overridden here:
# override_settings repopulates the app registry before applying the overrides,
# so the staticfiles panel's ready() would read it as None. It lives in the
# test settings module instead.
_TOOLBAR_APPS = [
    *settings.INSTALLED_APPS,
    "django.contrib.staticfiles",
    "debug_toolbar",
]


def test_default_panels_match_upstream() -> None:
    """The panel tuple must stay a verbatim copy of the upstream default."""
    ours = list(DEBUG_TOOLBAR_DEFAULT_PANELS)
    upstream = list(PANELS_DEFAULTS)
    assert ours == upstream, (
        f"missing: {sorted(set(upstream) - set(ours))}, "
        f"extra: {sorted(set(ours) - set(upstream))}, "
        f"same set but reordered: {set(ours) == set(upstream)}"
    )


@override_settings(INSTALLED_APPS=_TOOLBAR_APPS)
def test_default_panels_are_importable() -> None:
    """Every dotted path must resolve against the installed toolbar."""
    for panel in DEBUG_TOOLBAR_DEFAULT_PANELS:
        import_string(panel)


def test_default_config_keys_are_known() -> None:
    """Reject config keys the installed toolbar no longer recognises."""
    unknown = sorted(set(DEBUG_TOOLBAR_DEFAULT_CONFIG) - set(CONFIG_DEFAULTS))
    assert not unknown, f"unknown DEBUG_TOOLBAR_CONFIG keys: {unknown}"
