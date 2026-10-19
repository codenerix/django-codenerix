"""OTPAuth accepts a correct TOTP code typed across the 30 s step boundary."""

import datetime
from types import SimpleNamespace

import pyotp
import pytest
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.test import RequestFactory, override_settings

from codenerix.authbackend import OTPAuth
from codenerix.checks import check_otp_valid_window

PASSWORD = "correct-horse-battery"
OTP_KEY = pyotp.random_base32(32)
# 2026-01-01 12:00:00 UTC, a multiple of 30: second 0 of a step, so the
# previous step ended one second earlier. Kept as an epoch because pyotp's
# at() tests isinstance against the (patched) datetime module.
STEP_START = 1767268800

pytestmark = pytest.mark.django_db


@pytest.fixture
def user() -> User:
    # OTPAuth reads the TOTP key from first_name
    return User.objects.create_user(username="alice", password=PASSWORD, first_name=OTP_KEY)


class _Clock(datetime.datetime):
    """pyotp's clock pinned at second 0 of a step while the code is verified."""

    @classmethod
    def now(cls, tz: datetime.tzinfo | None = None) -> "_Clock":
        return cls.fromtimestamp(STEP_START, tz=tz)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> None:
    # Only pyotp's view of the datetime module is replaced, not the module itself
    monkeypatch.setattr(pyotp.totp, "datetime", SimpleNamespace(datetime=_Clock))


def _code_at(seconds_before_step: int) -> str:
    return pyotp.TOTP(OTP_KEY).at(STEP_START - seconds_before_step)


def _auth(token: str) -> User | None:
    request: HttpRequest = RequestFactory().post("/", REMOTE_ADDR="203.0.113.7")
    return OTPAuth().authenticate(request, username="alice", password=PASSWORD, authtoken=token)


def test_code_from_the_previous_step_is_accepted(user: User, clock: None) -> None:
    # Generated one second before the boundary, submitted one second after it
    assert _auth(_code_at(1)) == user


def test_code_from_the_next_step_is_accepted(user: User, clock: None) -> None:
    # A client clock one step ahead of the server
    assert _auth(_code_at(-30)) == user


def test_code_two_steps_old_is_refused(user: User, clock: None) -> None:
    assert _auth(_code_at(31)) is None


@override_settings(OTP_VALID_WINDOW=0)
def test_window_zero_refuses_the_previous_step(user: User, clock: None) -> None:
    # The 6.2.0 behaviour, kept available for deployments that want it
    assert _auth(_code_at(1)) is None
    assert _auth(_code_at(0)) == user


@pytest.mark.parametrize(
    "value",
    ["1", 1.5, -1, True, None],
    ids=["string", "float", "negative", "bool", "none"],
)
def test_invalid_window_is_reported(value: object) -> None:
    with override_settings(OTP_VALID_WINDOW=value):
        (error,) = check_otp_valid_window(None)
    assert error.id == "codenerix.E008"
    assert error.msg.startswith(f"OTP_VALID_WINDOW is {value!r}: it must be a non-negative integer")


@pytest.mark.parametrize("value", [0, 1, 2])
def test_valid_window_is_not_reported(value: int) -> None:
    with override_settings(OTP_VALID_WINDOW=value):
        assert check_otp_valid_window(None) == []


@override_settings(OTP_VALID_WINDOW="1")
def test_invalid_window_fails_closed_at_login(user: User, clock: None) -> None:
    # A string from an environment variable used to raise TypeError inside pyotp
    assert _auth(_code_at(1)) is None
    assert _auth(_code_at(0)) == user
