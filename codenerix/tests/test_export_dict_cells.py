"""Dict cells in the five GenList exports go through DjangoJSONEncoder.

6.3.5 made every export encode a dict cell with DjangoJSONEncoder, so a dict
holding a Decimal, a date or a UUID no longer fails; nothing exercised those
branches. Each test builds the smallest answer the export methods read.
"""

import csv
import datetime
import io
import json
import uuid
from decimal import Decimal
from typing import Any

import bson
from django.test import override_settings
from openpyxl import load_workbook

# codenerix.views reads STATIC_URL while its classes are created, as in
# test_haystack_checks.py
with override_settings(STATIC_URL="/static/"):
    from codenerix.views import GenList

CELL = {
    "price": Decimal("1.50"),
    "day": datetime.date(2026, 1, 2),
    "id": uuid.UUID(int=1),
}
# What DjangoJSONEncoder makes of CELL; plain json.dumps() raises on it
ENCODED = '{"price": "1.50", "day": "2026-01-02", "id": "00000000-0000-0000-0000-000000000001"}'


def _view() -> GenList:
    view = GenList()
    view.language = "en"
    return view


def _answer() -> dict[str, Any]:
    return {
        "meta": {"export_name": "list"},
        "table": {
            "head": {"columns": [{"name": "Data", "id": "data", "type": "JSONField"}]},
            "body": [{"data": CELL}],
        },
    }


def test_csv_export_encodes_dict_cell() -> None:
    body = _view().response_to_csv(_answer()).content.decode("utf-8")
    assert list(csv.reader(io.StringIO(body), delimiter=";")) == [["Data"], [ENCODED]]


def test_xls_export_encodes_dict_cell() -> None:
    content = _view().response_to_xls(_answer()).content
    sheet = load_workbook(io.BytesIO(content)).active
    assert sheet is not None
    assert [cell.value for cell in sheet[2]] == [ENCODED]


def test_json_export_encodes_dict_cell() -> None:
    data = json.loads(_view().response_to_json(_answer()).content)
    assert data["body"] == [[ENCODED]]


def test_jsonl_export_encodes_dict_cell() -> None:
    body = _view().response_to_jsonl(_answer()).content.decode("utf-8")
    assert [json.loads(line) for line in body.splitlines()] == [{"data": ENCODED}]


def test_bson_export_encodes_dict_cell() -> None:
    data = bson.decode(_view().response_to_bson(_answer()).content)
    assert data["body"] == [[ENCODED]]
