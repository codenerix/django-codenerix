"""Minimal Django settings for running the test suite.

This module exists solely so pytest (via pytest-django) and the static
analysers can resolve a DJANGO_SETTINGS_MODULE. It is intentionally minimal:
just enough INSTALLED_APPS for codenerix models to load.
"""

SECRET_KEY = "codenerix-test-secret-key"  # noqa: S105 - test-only, not a secret

USE_TZ = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    # codenerix/models.py imports django.contrib.admin.models (ADDITION/CHANGE/
    # DELETION), so the admin app must be installed for that model module to load.
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.messages",
    "codenerix",
]

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
