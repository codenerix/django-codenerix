"""Change log of GenLog / GenLogFull with values bson's json_util cannot encode.

GenLogFull stores ``(old, new)`` per changed field. The old value used to go
into the log unchecked, so changing a Decimal, date, time or UUID field made
``save()`` raise TypeError/ValueError before the row was written.
"""

import datetime
import json
import uuid
from decimal import Decimal

import pytest
from django.apps import apps
from django.db import connection, models

from codenerix.models import GenLog, GenLogFull, Log

INITIAL = {
    "amount": Decimal("100.00"),
    "day": datetime.date(2026, 1, 1),
    "hour": datetime.time(1, 2),
    "ref": uuid.UUID(int=1),
}

CHANGES = [
    ("amount", Decimal("200.00"), "100.00", "200.00"),
    ("day", datetime.date(2026, 2, 2), "2026-01-01", "2026-02-02"),
    ("hour", datetime.time(3, 4), "01:02:00", "03:04:00"),
    ("ref", uuid.UUID(int=2), str(uuid.UUID(int=1)), str(uuid.UUID(int=2))),
    # New value encodable (None), old one not: the old one must be checked too
    ("amount", None, "100.00", None),
]


def _make_model(base):
    """Concrete model on ``base``. GenLog.save() looks its class up in the
    global app registry, so isolate_apps() cannot be used: the fixture
    unregisters it instead."""

    class Meta(base.Meta):
        app_label = "codenerix"

    def __fields__(self, info):
        return []

    attrs = {
        "__module__": __name__,
        "Meta": Meta,
        "__fields__": __fields__,
        "amount": models.DecimalField(max_digits=10, decimal_places=2, null=True),
        "day": models.DateField(),
        "hour": models.TimeField(),
        "ref": models.UUIDField(),
    }
    return type(f"LogValues{base.__name__}", (base,), attrs)


@pytest.fixture(params=[GenLog, GenLogFull], ids=["GenLog", "GenLogFull"])
def model(request):
    model = _make_model(request.param)
    try:
        with connection.schema_editor() as editor:
            editor.create_model(model)
        try:
            yield model
        finally:
            with connection.schema_editor() as editor:
                editor.delete_model(model)
    finally:
        # Keep it out of apps.get_models() for the rest of the suite
        del apps.all_models["codenerix"][model._meta.model_name]
        apps.clear_cache()


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(("attr", "new", "old_logged", "new_logged"), CHANGES)
def test_change_is_logged(model, attr, new, old_logged, new_logged):
    obj = model.objects.create(**INITIAL)
    setattr(obj, attr, new)
    obj.save()

    obj.refresh_from_db()
    assert getattr(obj, attr) == new

    change = json.loads(Log.objects.order_by("-pk").first().change_json)
    expected = [old_logged, new_logged] if model.CodenerixMeta.log_full else new_logged
    assert change == {attr: expected}
