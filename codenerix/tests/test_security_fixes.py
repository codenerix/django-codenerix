"""OTPAuthMiddleware `next` validation and GenList `pages_to_bring` bounds."""

import pytest
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from codenerix import authbackend

LOGIN_REDIRECT = "/after-login/"

# redirect() tries reverse() first, which needs a URLconf; an empty one will do
urlpatterns: list[object] = []


def _middleware_response(monkeypatch: pytest.MonkeyPatch, next_url: str, secure: bool = False):
    # A successful token login, without touching the database or sessions
    monkeypatch.setattr(authbackend, "authenticate", lambda request, **kwargs: object())
    monkeypatch.setattr(authbackend, "login", lambda request, user: None)
    request = RequestFactory().get(
        "/",
        {"authtoken": "123456", "username": "alice", "password": "pw", "next": next_url},
        secure=secure,
    )
    middleware = authbackend.OTPAuthMiddleware(lambda request: HttpResponse("view"))
    return middleware(request)


@override_settings(
    LOGIN_REDIRECT_URL=LOGIN_REDIRECT,
    ALLOWED_HOSTS=["testserver"],
    ROOT_URLCONF=__name__,
)
@pytest.mark.parametrize(
    ("next_url", "expected"),
    [
        ("/inside/page/", "/inside/page/"),
        ("http://testserver/inside/", "http://testserver/inside/"),
        ("https://evil.example/phish", LOGIN_REDIRECT),
        ("//evil.example/phish", LOGIN_REDIRECT),
        ("javascript:alert(1)", LOGIN_REDIRECT),
    ],
    ids=["relative", "same-host", "offsite", "scheme-relative", "javascript"],
)
def test_next_is_only_followed_on_this_host(
    monkeypatch: pytest.MonkeyPatch,
    next_url: str,
    expected: str,
) -> None:
    response = _middleware_response(monkeypatch, next_url)
    assert response.status_code == 302
    assert response["Location"] == expected


@override_settings(
    LOGIN_REDIRECT_URL=LOGIN_REDIRECT,
    ALLOWED_HOSTS=["testserver"],
    ROOT_URLCONF=__name__,
)
def test_https_request_does_not_follow_http_next(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _middleware_response(monkeypatch, "http://testserver/inside/", secure=True)
    assert response["Location"] == LOGIN_REDIRECT


def _bounded_pages_to_bring():
    # codenerix.views reads settings.STATIC_URL at import time, and STATIC_URL
    # must stay out of codenerix.tests.settings (see test_debug_toolbar.py)
    with override_settings(STATIC_URL="/static/"):
        from codenerix.views import bounded_pages_to_bring

    return bounded_pages_to_bring


@pytest.mark.parametrize(
    ("value", "total_pages", "expected"),
    [
        (1, 10, 1),
        (3, 10, 3),
        ("2", 10, 2),
        (10**9, 10, 10),
        (0, 10, 1),
        (-5, 10, 1),
        ("abc", 10, 1),
        (None, 10, 1),
        (4, 0, 1),
    ],
)
def test_bounded_pages_to_bring(value: object, total_pages: int, expected: int) -> None:
    assert _bounded_pages_to_bring()(value, total_pages) == expected
