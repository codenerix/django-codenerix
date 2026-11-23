"""The LDAP backend imports ldap3 only when used; its behaviour is pinned.

The pinning tests replace ldap3.Server and ldap3.Connection on the ldap3
module itself, which the backend reads at call time whether it imported ldap3
at module level (6.4.0) or lazily, so the same tests pin both.
"""

import os
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest
from django.contrib.auth.models import Group, User
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from codenerix.authbackend import ActiveDirectoryGroupMembershipSSLBackend

# ldap3 is imported here on purpose, its pyasn1 deprecations are not ours
pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")

ROOT = Path(__file__).resolve().parents[2]
AD = {
    "AD_NT4_DOMAIN": "corp.example.com",
    "AD_MAP_FIELDS": {"email": "mail", "first_name": "givenName"},
}


def _run(code: str, tmp_path: Path, settings_body: str) -> str:
    (tmp_path / "lazy_settings.py").write_text(textwrap.dedent(settings_body))
    env = dict(os.environ, DJANGO_SETTINGS_MODULE="lazy_settings", PYTHONPATH=str(tmp_path))
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_importing_authbackend_does_not_load_ldap3(tmp_path: Path) -> None:
    # A fresh interpreter: in this one another test may have loaded ldap3
    out = _run(
        """
        import sys
        import django
        django.setup()
        import codenerix.authbackend
        print("ldap3" in sys.modules)
        """,
        tmp_path,
        "from codenerix.tests.settings import *\n",
    )
    assert out == "False"


def test_start_up_with_otp_and_token_middlewares_does_not_load_ldap3(tmp_path: Path) -> None:
    out = _run(
        """
        import sys
        import django
        django.setup()
        from django.core.handlers.wsgi import WSGIHandler
        WSGIHandler()  # builds the middleware chain, importing codenerix.authbackend
        import codenerix.views
        print("codenerix.authbackend" in sys.modules, "ldap3" in sys.modules)
        """,
        tmp_path,
        """
        from codenerix.tests.settings import *
        STATIC_URL = "/static/"
        MIDDLEWARE = [
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "codenerix.authbackend.TokenAuthMiddleware",
            "codenerix.authbackend.OTPAuthMiddleware",
            "codenerix.middleware.CurrentUserMiddleware",
        ]
        AUTHENTICATION_BACKENDS = [
            "codenerix.authbackend.TokenAuth",
            "codenerix.authbackend.OTPAuth",
            "django.contrib.auth.backends.ModelBackend",
        ]
        """,
    )
    assert out == "True False"


def test_missing_ldap3_names_the_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "ldap3", None)
    with (
        override_settings(**AD),
        pytest.raises(ImproperlyConfigured, match=r"django-codenerix\[ldap\]"),
    ):
        ActiveDirectoryGroupMembershipSSLBackend().ldap_link("ann", "secret")


class _Entry:
    def __init__(self, **attrs: Any) -> None:
        self.__dict__.update(attrs)


class _FakeLdap:
    """Record Server and Connection calls; a Connection may raise instead."""

    def __init__(
        self, raises: type[Exception] | None = None, entries: list[_Entry] | None = None
    ) -> None:
        self.raises = raises
        self.entries = entries or []
        self.servers: list[tuple[str, dict[str, Any]]] = []
        self.connections: list[dict[str, Any]] = []
        self.searches: list[dict[str, Any]] = []

    def server(self, url: str, **kwargs: Any) -> str:
        self.servers.append((url, kwargs))
        return url

    def connection(self, server: str, **kwargs: Any) -> Any:
        self.connections.append(kwargs)
        if self.raises is not None:
            raise self.raises("refused")
        fake = self

        class _Conn:
            entries = fake.entries

            def search(self, **kw: Any) -> None:
                fake.searches.append(kw)

        return _Conn()


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch) -> _FakeLdap:
    import ldap3

    ldap = _FakeLdap()
    monkeypatch.setattr(ldap3, "Server", ldap.server)
    monkeypatch.setattr(ldap3, "Connection", ldap.connection)
    return ldap


@override_settings(**AD)
def test_plain_link_arguments(fake: _FakeLdap) -> None:
    import ldap3

    assert ActiveDirectoryGroupMembershipSSLBackend().ldap_link("ann", "secret")
    assert fake.servers == [
        ("ldap://CORP.EXAMPLE.COM:389", {"allowed_referral_hosts": [("*", True)]})
    ]
    assert fake.connections == [
        {
            "user": "CORP.EXAMPLE.COM\\ann",
            "password": "secret",
            "raise_exceptions": True,
            "authentication": ldap3.NTLM,
            "auto_bind": ldap3.AUTO_BIND_NO_TLS,
        },
    ]


@override_settings(**AD, AD_SSL=True, AD_CERT_FILE="/nonexistent/cert.pem", AD_LDAP_PORT=6360)
def test_ssl_link_arguments(fake: _FakeLdap) -> None:
    import ssl

    import ldap3

    assert ActiveDirectoryGroupMembershipSSLBackend().ldap_link("ann", "secret")
    ((url, ser),) = fake.servers
    assert url == "ldaps://CORP.EXAMPLE.COM:6360"
    assert ser["use_ssl"] is True
    assert isinstance(ser["tls"], ldap3.Tls)
    assert ser["tls"].validate == ssl.CERT_REQUIRED
    assert fake.connections[0]["auto_bind"] == ldap3.AUTO_BIND_TLS_BEFORE_BIND


@override_settings(**AD)
def test_no_password_never_connects(fake: _FakeLdap) -> None:
    assert ActiveDirectoryGroupMembershipSSLBackend().ldap_link("ann", "") is False
    assert fake.servers == []


@pytest.mark.django_db
@override_settings(**AD)
def test_successful_login_creates_and_synchronises_the_user(fake: _FakeLdap) -> None:
    import ldap3

    Group.objects.create(name="Staff")
    fake.entries = [
        _Entry(
            mail="ann@example.com",
            givenName="Ann",
            memberOf=[
                "CN=Domain Admins,CN=Users,DC=corp,DC=example,DC=com",
                "CN=Staff,OU=Groups,DC=corp,DC=example,DC=com",
                "CN=Missing,DC=corp,DC=example,DC=com",
            ],
        ),
    ]
    user = ActiveDirectoryGroupMembershipSSLBackend().authenticate(
        None, username="ann", password="secret"
    )
    assert user is not None
    user = User.objects.get(username="ann")
    assert (user.email, user.first_name, user.last_name) == ("ann@example.com", "Ann", "")
    assert user.is_active and user.is_staff and user.is_superuser
    assert user.check_password("secret")
    assert list(user.groups.values_list("name", flat=True)) == ["Staff"]
    assert fake.searches[0]["search_filter"] == "(sAMAccountName=ann)"
    assert fake.searches[0]["search_base"] == "dc=corp,dc=example,dc=com"
    assert fake.searches[0]["search_scope"] == ldap3.SUBTREE


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("error", "lock", "answer", "active"),
    [
        ("LDAPSocketOpenError", False, None, True),
        ("LDAPSocketOpenError", True, None, False),
        ("LDAPException", False, False, False),
    ],
)
def test_refused_link_and_user_lock(
    fake: _FakeLdap, error: str, lock: bool, answer: object, active: bool
) -> None:
    from ldap3.core import exceptions

    fake.raises = getattr(exceptions, error)
    User.objects.create(username="ann", is_active=True)
    backend = ActiveDirectoryGroupMembershipSSLBackend()
    with override_settings(**AD, AD_LOCK_UNAUTHORIZED=lock):
        assert backend.ldap_link("ann", "secret") is answer
        assert backend.authenticate(None, username="ann", password="secret") is None
    assert User.objects.get(username="ann").is_active is active
