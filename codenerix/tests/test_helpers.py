"""Tests for codenerix.helpers.

get_client_ip() only ever reads ``request.META``, so the tests build a tiny
stand-in instead of a real ``HttpRequest``.  RequestFactory would inject its
own ``REMOTE_ADDR`` default, which is exactly the value several of these cases
need to be absent, so an explicit META dict keeps each scenario unambiguous.
"""

from types import SimpleNamespace

import pytest
from django.test import override_settings

from codenerix.helpers import get_client_ip

CLIENT = "203.0.113.9"
EDGE = "198.51.100.7"
SPOOFED = "6.6.6.6"


def req(**meta):
    """Minimal request stand-in carrying only META."""
    return SimpleNamespace(META=meta)


@pytest.mark.parametrize(
    ("name", "meta", "trusted_proxies", "expected"),
    [
        (
            # uwsgi_params passes REMOTE_ADDR and no proxy headers at all.
            "direct-uwsgi",
            {"REMOTE_ADDR": CLIENT},
            1,
            CLIENT,
        ),
        (
            # nginx proxy_params, single hop, honest client.
            "single-hop-honest",
            {"REMOTE_ADDR": "", "HTTP_X_REAL_IP": CLIENT, "HTTP_X_FORWARDED_FOR": CLIENT},
            1,
            CLIENT,
        ),
        (
            # The regression this change exists for: the client prepends a
            # forged entry, nginx appends the real peer, and the rightmost
            # entry is the only trustworthy one.
            "single-hop-spoofed-xff",
            {
                "REMOTE_ADDR": "",
                "HTTP_X_REAL_IP": CLIENT,
                "HTTP_X_FORWARDED_FOR": f"{SPOOFED}, {CLIENT}",
            },
            1,
            CLIENT,
        ),
        (
            # X-Real-IP is the fallback when no XFF reaches the app.
            "real-ip-only",
            {"REMOTE_ADDR": "", "HTTP_X_REAL_IP": CLIENT},
            1,
            CLIENT,
        ),
        (
            # CDN + nginx with the default of one trusted hop: the app sees
            # the CDN edge.  Documented on purpose, this is the case that
            # needs CODENERIX_TRUSTED_PROXIES raising to 2.
            "cdn-default-hops",
            {
                "REMOTE_ADDR": "",
                "HTTP_X_REAL_IP": EDGE,
                "HTTP_X_FORWARDED_FOR": f"{CLIENT}, {EDGE}",
            },
            1,
            EDGE,
        ),
        (
            # Same deployment, hops declared correctly.
            "cdn-two-hops",
            {
                "REMOTE_ADDR": "",
                "HTTP_X_REAL_IP": EDGE,
                "HTTP_X_FORWARDED_FOR": f"{CLIENT}, {EDGE}",
            },
            2,
            CLIENT,
        ),
        (
            # Zero trusted proxies distrusts every header. Must not raise.
            "no-trusted-proxies",
            {
                "REMOTE_ADDR": CLIENT,
                "HTTP_X_REAL_IP": SPOOFED,
                "HTTP_X_FORWARDED_FOR": f"{SPOOFED}, 7.7.7.7, 8.8.8.8",
            },
            0,
            CLIENT,
        ),
        (
            # More declared hops than entries present: fall back to the
            # leftmost rather than walking off the list.
            "more-hops-than-entries",
            {"REMOTE_ADDR": "", "HTTP_X_FORWARDED_FOR": f"{CLIENT}, {EDGE}"},
            9,
            CLIENT,
        ),
        (
            # Whitespace and empty entries must not shift the count.
            "messy-xff",
            {"REMOTE_ADDR": "", "HTTP_X_FORWARDED_FOR": f"  {SPOOFED} , , {CLIENT}  "},
            1,
            CLIENT,
        ),
        (
            # Nothing at all to go on.
            "nothing",
            {},
            1,
            None,
        ),
    ],
)
def test_get_client_ip(name, meta, trusted_proxies, expected):
    assert get_client_ip(req(**meta), trusted_proxies=trusted_proxies) == expected


def test_defaults_to_one_trusted_proxy_without_setting():
    """With no setting defined the default is a single reverse proxy."""
    meta = {"REMOTE_ADDR": "", "HTTP_X_FORWARDED_FOR": f"{SPOOFED}, {CLIENT}"}
    assert get_client_ip(req(**meta)) == CLIENT


@override_settings(CODENERIX_TRUSTED_PROXIES=2)
def test_reads_trusted_proxies_from_settings():
    """The hop count is picked up from CODENERIX_TRUSTED_PROXIES."""
    meta = {"REMOTE_ADDR": "", "HTTP_X_FORWARDED_FOR": f"{CLIENT}, {EDGE}"}
    assert get_client_ip(req(**meta)) == CLIENT


@override_settings(CODENERIX_TRUSTED_PROXIES=0)
def test_setting_zero_ignores_proxy_headers():
    """CODENERIX_TRUSTED_PROXIES = 0 works as a kill switch and never raises."""
    meta = {"REMOTE_ADDR": CLIENT, "HTTP_X_FORWARDED_FOR": f"{SPOOFED}, 7.7.7.7"}
    assert get_client_ip(req(**meta)) == CLIENT


def test_explicit_argument_overrides_setting():
    """The keyword argument wins over the setting."""
    meta = {"REMOTE_ADDR": "", "HTTP_X_FORWARDED_FOR": f"{CLIENT}, {EDGE}"}
    with override_settings(CODENERIX_TRUSTED_PROXIES=1):
        assert get_client_ip(req(**meta), trusted_proxies=2) == CLIENT
