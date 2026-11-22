"""Tests for codenerix.helpers.

get_client_ip() only ever reads ``request.META``, so the tests build a tiny
stand-in instead of a real ``HttpRequest``.  RequestFactory would inject its
own ``REMOTE_ADDR`` default, which is exactly the value several of these cases
need to be absent, so an explicit META dict keeps each scenario unambiguous.
"""

import base64
import datetime
import json
import re
import uuid
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.test import override_settings

from codenerix.helpers import OBJ_TO_HTML_VIEWS, get_client_ip, obj_to_html

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


class _Markup:
    """Object whose text needs escaping."""

    def __str__(self):
        return "<b>&"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # yattag only takes str, int and float: anything else used to raise TypeError
        (Decimal("100.00"), "100.00"),
        (uuid.UUID(int=1), "00000000-0000-0000-0000-000000000001"),
        (datetime.date(2026, 1, 1), "2026-01-01"),
        (datetime.datetime(2026, 1, 1, 2, 3), "2026-01-01 02:03:00"),
        (datetime.time(1, 2), "01:02:00"),
        (b"x", "b'x'"),
        (_Markup(), "&lt;b&gt;&amp;"),
        # Types yattag already took render as before
        (7, ">7<"),
        (1.5, ">1.5<"),
        (True, ">True<"),
        ("plain text", ">plain text<"),
    ],
)
def test_obj_to_html_renders_any_type_as_text(value, expected):
    kind, html = obj_to_html(value)
    assert kind == "OBJ"
    assert expected in html


@pytest.mark.parametrize("wrap", [True, False])
@pytest.mark.parametrize("value", ["plain text", {"a": [1, {"b": Decimal("2.50")}]}])
def test_obj_to_html_closes_every_tag_it_opens(value, wrap):
    _, html = obj_to_html(value, wrap=wrap)
    assert html.startswith("<html><body>")
    assert html.endswith("</div></body></html>" if wrap else "</body></html>")
    for name in ("html", "body", "div", "ul", "li"):
        assert html.count(f"<{name}>") + html.count(f"<{name} ") == html.count(f"</{name}>")


def _payload(html):
    """Decode the data-payload attribute of the viewer."""
    encoded = re.search(r'data-payload="([^"]+)"', html).group(1)
    return json.loads(base64.b64decode(encoded).decode("utf-8"))


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # Captured from 6.3.6, before views existed
        (
            {"a": [1, None]},
            '<html><body><div style="word-break: break-all; overflow-wrap: break-word;">'
            "<ul><li><strong>a: </strong><ul><li>1</li><li>None</li></ul></li></ul>"
            "</div></body></html>",
        ),
        (
            '{"k": "v"}',
            '<html><body><div style="word-break: break-all; overflow-wrap: break-word;">'
            "<ul><li><strong>k: </strong>v</li></ul></div></body></html>",
        ),
    ],
)
def test_obj_to_html_simple_view_keeps_classic_output(value, expected):
    _, html = obj_to_html(value, views=("simple",))
    assert html == expected


def test_obj_to_html_offers_every_view_by_default_in_order():
    kind, html = obj_to_html({"a": 1})
    assert kind == "OBJ"
    assert "codenerix-obj-viewer" in html
    views = re.search(r'data-views="([^"]+)"', html).group(1)
    assert tuple(views.split(",")) == OBJ_TO_HTML_VIEWS
    assert OBJ_TO_HTML_VIEWS[0] == "tree"
    assert OBJ_TO_HTML_VIEWS[-1] == "simple"


def test_obj_to_html_keeps_the_requested_views_order():
    _, html = obj_to_html({"a": 1}, views=["flat", "tree"])
    assert 'data-views="flat,tree"' in html


@pytest.mark.parametrize("views", [[], ["tree", "nope"], ["tree", "flat", "tree"]])
def test_obj_to_html_rejects_unknown_empty_or_repeated_views(views):
    with pytest.raises(ValueError):
        obj_to_html({"a": 1}, views=views)


def test_obj_to_html_viewer_keeps_simple_rendering_as_fallback():
    _, simple = obj_to_html({"a": [1, 2]}, views=("simple",))
    _, viewer = obj_to_html({"a": [1, 2]})
    inner = "<ul><li><strong>a: </strong><ul><li>1</li><li>2</li></ul></li></ul>"
    assert inner in simple
    assert inner in viewer


def test_obj_to_html_payload_roundtrips_unicode_and_odd_types():
    value = {
        "name": "Málaga",
        "price": Decimal("142.50"),
        "id": uuid.UUID(int=1),
        "day": datetime.date(2026, 1, 1),
        "pair": (1, 2),
        "set": {"b", "a"},
        3: float("nan"),
    }
    payload = _payload(obj_to_html(value)[1])
    assert payload["kind"] == "OBJ"
    assert payload["raw"] is None
    assert payload["data"] == {
        "name": "Málaga",
        "price": "142.50",
        "id": "00000000-0000-0000-0000-000000000001",
        "day": "2026-01-01",
        "pair": [1, 2],
        "set": ["a", "b"],
        "3": "nan",
    }
    assert payload["labels"]["tree"]


def test_obj_to_html_payload_turns_xml_into_a_tree():
    xml = '<Res v="2"><Status>OK</Status><Room n="1"/><Room n="2">x</Room></Res>'
    kind, html = obj_to_html(xml)
    payload = _payload(html)
    assert kind == "XML"
    assert payload["raw"] == xml
    assert payload["data"] == {
        "Res": {
            "@v": "2",
            "Status": {"#text": "OK"},
            "Room": [{"@n": "1"}, {"@n": "2", "#text": "x"}],
        },
    }


def test_obj_to_html_payload_respects_depth_for_nested_strings():
    value = '{"inner": "{\\"x\\": 1}"}'
    assert _payload(obj_to_html(value)[1])["data"] == {"inner": '{"x": 1}'}
    assert _payload(obj_to_html(value, depth=2)[1])["data"] == {"inner": {"x": 1}}


def test_obj_to_html_viewer_hides_angular_expressions():
    # The fallback is never compiled and the data travels base64-encoded, so
    # no "{{" may reach the markup outside the payload
    _, html = obj_to_html({"evil": "{{constructor.constructor('x')()}}"})
    markup = re.sub(r'data-payload="[^"]+"', "", html)
    assert "{{" not in re.sub(r"<ul>.*</ul>", "", markup)
    assert _payload(html)["data"]["evil"].startswith("{{")


def test_obj_to_html_payload_carries_lone_surrogates_as_ascii() -> None:
    # A lone surrogate is a valid Python str but cannot be encoded to UTF-8:
    # 6.4.0 raised UnicodeEncodeError here, 6.3.6 returned the HTML
    value = json.loads('{"a": "\\ud800", "b": "M\\u00e1laga"}')
    _, html = obj_to_html(value)
    match = re.search(r'data-payload="([^"]+)"', html)
    assert match is not None
    assert base64.b64decode(match.group(1)).isascii()
    assert _payload(html)["data"] == value


def test_obj_to_html_viewer_element_is_not_bindable() -> None:
    # Without the directive registered, AngularJS must leave the fallback alone
    _, html = obj_to_html({"a": 1})
    assert '<div codenerix-obj-viewer="" ng-non-bindable="" data-views=' in html


class _ClickTags(HTMLParser):
    """Collect the tag of every element with ng-click, and every input."""

    def __init__(self) -> None:
        super().__init__()
        self.clickable: list[str] = []
        self.inputs: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        names = dict(attrs)
        if "ng-click" in names:
            self.clickable.append(tag)
        if tag == "input":
            self.inputs.append(names)


def test_obj_viewer_partial_is_keyboard_reachable() -> None:
    # Buttons get Enter and Space from the browser; any other element with a
    # click handler would need its own keyboard handler
    partial = Path(__file__).parent.parent / "static/codenerix/partials/obj_viewer.html"
    tags = _ClickTags()
    tags.feed(partial.read_text(encoding="utf-8"))
    assert len(tags.clickable) == 16
    assert set(tags.clickable) == {"button"}
    assert all(i.get("aria-label") or i.get("title") for i in tags.inputs)


def test_obj_to_html_viewer_css_resets_buttons() -> None:
    _, html = obj_to_html({"a": 1})
    assert ".cdnx-objviewer .cdnx-ov-btn{border:0;margin:0;cursor:pointer}" in html
    assert (
        ".cdnx-objviewer .cdnx-ov-btn:not(.label){background:transparent;"
        "padding:0;font:inherit;color:inherit;text-align:inherit}"
    ) in html


@pytest.mark.parametrize(
    ("wrap", "klass"),
    [(True, "cdnx-objviewer cdnx-ov-wrap"), (False, "cdnx-objviewer")],
)
def test_obj_to_html_viewer_wrap_class(wrap: bool, klass: str) -> None:
    _, html = obj_to_html({"a": 1}, wrap=wrap)
    assert f'class="{klass}"' in html


def test_obj_to_html_payload_sorts_frozensets_like_sets() -> None:
    payload = _payload(obj_to_html({"f": frozenset({"b", "a"})})[1])
    assert payload["data"] == {"f": ["a", "b"]}


def test_obj_to_html_payload_xml_text_is_stripped_joined_and_keeps_cdata() -> None:
    # Whitespace-only nodes between tags are dropped, other text is stripped
    # and joined with one space, CDATA counts as text
    xml = "<m>  a  <b>x</b>\n c <![CDATA[<d>]]> <e/>\n</m>"
    data = _payload(obj_to_html(xml)[1])["data"]
    assert data == {"m": {"b": {"#text": "x"}, "e": {}, "#text": "a c <d>"}}
