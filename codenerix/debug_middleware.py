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

"""Middlewares installed by codenerix.debug.autoload() for the debug tools.

Kept apart from codenerix.debug, which settings modules import before Django
is set up.
"""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.middleware import cache
from django.utils.cache import add_never_cache_headers
from pyinstrument import middleware as pyinstrument_middleware

from codenerix.debug import is_debug_request, show_pyinstrument


class ProfilerMiddleware(pyinstrument_middleware.ProfilerMiddleware):
    """pyinstrument's middleware gated by show_pyinstrument().

    Enforced here rather than through PYINSTRUMENT_SHOW_CALLBACK, which a
    project may forget to set (pyinstrument then profiles for anyone). A
    project callback, if set, still applies on top.
    """

    def process_request(self, request: HttpRequest) -> None:
        if show_pyinstrument(request):
            super().process_request(request)

    def process_response(
        self,
        request: HttpRequest,
        response: HttpResponseBase,
    ) -> HttpResponseBase:
        result = super().process_response(request, response)
        if result is not response:
            # The profile page is built after the page cache ran: keep HTTP caches off it too
            add_never_cache_headers(result)
        return result


class _SkipFetchForDebug(cache.FetchFromCacheMiddleware):
    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        if is_debug_request(request):
            # A hit would bypass the debug tools; a miss must not be stored either
            request._cache_update_cache = False  # type: ignore[attr-defined]
            return None
        return super().process_request(request)


class _SkipUpdateForDebug(cache.UpdateCacheMiddleware):
    # Signature as django-stubs declares it on UpdateCacheMiddleware
    def process_response(
        self,
        request: HttpRequest,
        response: HttpResponseBase | str,
    ) -> HttpResponseBase | str:
        if is_debug_request(request):
            if isinstance(response, HttpResponseBase):
                # Instrumented output must not land in browser or shared HTTP caches either
                add_never_cache_headers(response)
            return response
        return super().process_response(request, response)


class UpdateCacheMiddleware(_SkipUpdateForDebug):
    """Django's UpdateCacheMiddleware, skipped for debug requests."""


class FetchFromCacheMiddleware(_SkipFetchForDebug):
    """Django's FetchFromCacheMiddleware, skipped for debug requests."""


class CacheMiddleware(_SkipUpdateForDebug, _SkipFetchForDebug, cache.CacheMiddleware):
    """Django's CacheMiddleware, skipped for debug requests."""
