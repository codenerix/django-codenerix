"""The current request is visible during the request only."""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory

from codenerix import middleware as codenerix_middleware
from codenerix.middleware import (
    CurrentRequestMiddleware,
    CurrentUserMiddleware,
    get_current_request,
    get_current_user,
)


@pytest.fixture(autouse=True)
def _no_current_request() -> None:
    # Start outside any request, whatever ran before in this thread
    codenerix_middleware._thread_locals_request.value = None


def _request() -> HttpRequest:
    request = RequestFactory().get("/")
    request.user = AnonymousUser()
    return request


@pytest.mark.parametrize("middleware", [CurrentRequestMiddleware, CurrentUserMiddleware])
def test_request_seen_during_the_view_and_cleared_after(
    middleware: type[CurrentRequestMiddleware],
) -> None:
    seen: list[object] = []

    def view(request: HttpRequest) -> HttpResponse:
        seen.append(get_current_request())
        seen.append(get_current_user())
        return HttpResponse("ok")

    request = _request()
    middleware(view)(request)
    assert seen == [request, request.user]
    assert get_current_request() is None
    assert get_current_user() is None


def test_cleared_when_the_view_raises() -> None:
    def view(request: HttpRequest) -> HttpResponse:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        CurrentRequestMiddleware(view)(_request())
    assert get_current_request() is None


def test_nested_request_restores_the_outer_one() -> None:
    outer, inner = _request(), _request()
    seen: list[object] = []

    def inner_view(request: HttpRequest) -> HttpResponse:
        seen.append(get_current_request())
        return HttpResponse("inner")

    def outer_view(request: HttpRequest) -> HttpResponse:
        CurrentRequestMiddleware(inner_view)(inner)
        seen.append(get_current_request())
        return HttpResponse("outer")

    CurrentRequestMiddleware(outer_view)(outer)
    assert seen == [inner, outer]
    assert get_current_request() is None
