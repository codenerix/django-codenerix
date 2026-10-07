"""OTPAuth emits one fail2ban-friendly log line per failed attempt, and nothing else."""

import logging

import pyotp
import pytest
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.test import RequestFactory, override_settings

from codenerix.authbackend import OTPAuth

LOGGER = "codenerix.auth.otp"
CLIENT_IP = "203.0.113.7"
PASSWORD = "correct-horse-battery"
OTP_KEY = pyotp.random_base32(32)

pytestmark = pytest.mark.django_db


@pytest.fixture
def user() -> User:
    # OTPAuth reads the TOTP key from first_name
    return User.objects.create_user(username="alice", password=PASSWORD, first_name=OTP_KEY)


def _request(ip: str = CLIENT_IP) -> HttpRequest:
    return RequestFactory().post("/", REMOTE_ADDR=ip)


def _lines(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.name == LOGGER]


def _auth(request: HttpRequest | None, **kwargs: str) -> User | None:
    return OTPAuth().authenticate(request, **kwargs)


@pytest.mark.parametrize(
    "credentials",
    [
        {"username": "alice", "password": "wrong", "authtoken": "000000"},
        {"username": "nobody", "password": PASSWORD, "authtoken": "000000"},
        {"username": "alice", "password": PASSWORD, "authtoken": "not-a-code"},
    ],
    ids=["bad-password", "unknown-user", "bad-otp"],
)
def test_failure_is_logged_once(
    user: User,
    credentials: dict[str, str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING, logger=LOGGER)
    assert _auth(_request(), **credentials) is None
    assert _lines(caplog) == [f"OTPAuth failure ip={CLIENT_IP}"]


def test_user_without_otp_key_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    User.objects.create_user(username="bob", password=PASSWORD)
    caplog.set_level(logging.WARNING, logger=LOGGER)
    assert _auth(_request(), username="bob", password=PASSWORD, authtoken="000000") is None
    assert _lines(caplog) == [f"OTPAuth failure ip={CLIENT_IP}"]


def test_success_is_not_logged(user: User, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING, logger=LOGGER)
    token = pyotp.TOTP(OTP_KEY).now()
    assert _auth(_request(), username="alice", password=PASSWORD, authtoken=token) == user
    assert _lines(caplog) == []


def test_missing_parameters_are_not_logged(user: User, caplog: pytest.LogCaptureFixture) -> None:
    # Plain password logins reach every backend; they are not OTP attempts
    caplog.set_level(logging.WARNING, logger=LOGGER)
    assert _auth(_request(), username="alice", password="wrong") is None
    assert _lines(caplog) == []


@override_settings(OTP_BYMAIL=True)
def test_otp_request_is_not_logged_but_bad_password_is(
    user: User,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING, logger=LOGGER)
    assert _auth(_request(), username="alice", password=PASSWORD, authtoken="REQUEST_OTP") is None
    assert _lines(caplog) == []

    assert _auth(_request(), username="alice", password="wrong", authtoken="REQUEST_OTP") is None
    assert _lines(caplog) == [f"OTPAuth failure ip={CLIENT_IP}"]


def test_ipv6_is_normalised(user: User, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING, logger=LOGGER)
    _auth(_request("2001:DB8:0:0::1"), username="alice", password="wrong", authtoken="0")
    assert _lines(caplog) == ["OTPAuth failure ip=2001:db8::1"]


@pytest.mark.parametrize(
    "remote_addr",
    ["", "not-an-ip", f"{CLIENT_IP}\nOTPAuth failure ip=198.51.100.9"],
    ids=["empty", "garbage", "injected-line"],
)
def test_unusable_address_is_not_logged(
    user: User,
    remote_addr: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.WARNING, logger=LOGGER)
    _auth(_request(remote_addr), username="alice", password="wrong", authtoken="0")
    assert _lines(caplog) == []


def test_username_never_reaches_the_line(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING, logger=LOGGER)
    forged = "x\nOTPAuth failure ip=198.51.100.9"
    _auth(_request(), username=forged, password="wrong", authtoken="0")
    assert _lines(caplog) == [f"OTPAuth failure ip={CLIENT_IP}"]


def test_no_request_is_not_logged(user: User, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING, logger=LOGGER)
    assert _auth(None, username="alice", password="wrong", authtoken="0") is None
    assert _lines(caplog) == []
