"""GenList selects the foreign keys its columns walk, rows and values unchanged.

A list over django.contrib.admin's LogEntry with a many-to-many column
(user__groups) and a method column (get_change_message): either one made the
list builder drop its select_related, so every row fetched its user and its
content type on its own.
"""

import json
from collections.abc import Iterator
from typing import Any

import pytest
from django.apps import apps
from django.contrib.admin.models import ADDITION, LogEntry
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType
from django.db import connection, models
from django.test import RequestFactory, override_settings
from django.test.utils import CaptureQueriesContext

# codenerix.views reads STATIC_URL while its classes are created, as in
# test_haystack_checks.py; ALL_PAGESALLOWED and MEDIA_URL are read per request
LIST_SETTINGS = {"STATIC_URL": "/static/", "ALL_PAGESALLOWED": True, "MEDIA_URL": "/media/"}
with override_settings(**LIST_SETTINGS):
    from codenerix import views
    from codenerix.views import GenList


class LogList(GenList):
    model = LogEntry

    def __fields__(self, info: Any) -> list[tuple[str, str]]:
        return [
            ("object_repr", "Object"),
            ("user__username", "User name"),
            ("user__groups", "Groups"),
            ("content_type__app_label", "App"),
            ("user", "User"),
            ("get_change_message", "Message"),
        ]


def _entries(n: int) -> None:
    group = Group.objects.create(name="g1")
    users = ContentType.objects.get_for_model(User)
    for i in range(n):
        user = User.objects.create(username=f"u{i}", is_superuser=True, is_staff=True)
        user.groups.add(group)
        LogEntry.objects.create(
            user=user,
            # The last row has no content type: a nullable foreign key
            content_type=None if i == n - 1 else users,
            object_id=str(i),
            object_repr=f"o{i}",
            action_flag=ADDITION,
            change_message="m",
        )


def _body() -> tuple[list[dict[str, Any]], int]:
    request = RequestFactory().get(
        "/", {"json": json.dumps({"rowsperpage": "All"})}, HTTP_X_REST="1"
    )
    request.user = User.objects.get(username="u0")
    with override_settings(**LIST_SETTINGS), CaptureQueriesContext(connection) as queries:
        response = LogList.as_view()(request)
    assert response.status_code == 200
    return json.loads(response.content)["table"]["body"], len(queries)


@pytest.mark.django_db
def test_rows_and_values() -> None:
    _entries(3)
    body, _ = _body()
    assert body == [
        {
            "pk": i + 1,
            "object_repr": f"o{i}",
            "user__username": f"u{i}",
            "user__groups": ["g1"],
            "content_type__app_label": None if i == 2 else "auth",
            "user": f"u{i}",
            "get_change_message": "m",
        }
        for i in range(3)
    ]


@pytest.mark.django_db
@pytest.mark.parametrize(("few", "many"), [(2, 5)])
def test_one_query_per_extra_row(few: int, many: int) -> None:
    # Per row only the many-to-many is left (no prefetch); user and content
    # type come with the row
    _entries(few)
    _, small = _body()
    LogEntry.objects.all().delete()
    User.objects.all().delete()
    Group.objects.all().delete()
    _entries(many)
    _, large = _body()
    assert (large - small) / (many - few) == 1


# Own models for what LogEntry lacks: a one-to-one chain, deeper foreign key
# chains and querysets narrowed with only() or values() by the list's hooks


def _make_models() -> dict[str, Any]:
    def model(model_name: str, **fields: Any) -> Any:
        attrs = {
            "__module__": __name__,
            "Meta": type("Meta", (), {"app_label": "codenerix"}),
            **fields,
        }
        return type(f"ListQ{model_name}", (models.Model,), attrs)

    country = model("Country", name=models.CharField(max_length=20))
    city = model(
        "City",
        name=models.CharField(max_length=20),
        country=models.ForeignKey(country, on_delete=models.CASCADE),
    )
    person = model(
        "Person",
        name=models.CharField(max_length=20),
        city=models.ForeignKey(city, null=True, on_delete=models.CASCADE),
    )
    detail = model(
        "Detail",
        nick=models.CharField(max_length=20),
        person=models.OneToOneField(person, on_delete=models.CASCADE),
    )

    def label(self: Any) -> str:
        return self.text.upper()

    note = model(
        "Note",
        text=models.CharField(max_length=20),
        author=models.ForeignKey(person, null=True, on_delete=models.CASCADE),
        detail=models.OneToOneField(detail, null=True, on_delete=models.CASCADE),
        label=label,
    )
    return {"country": country, "city": city, "person": person, "detail": detail, "note": note}


@pytest.fixture
def qmodels() -> Iterator[dict[str, Any]]:
    built = _make_models()
    try:
        yield built
    finally:
        # Keep them out of apps.get_models() for the rest of the suite
        for m in built.values():
            del apps.all_models["codenerix"][m._meta.model_name]
        apps.clear_cache()


@pytest.fixture
def qdata(qmodels: dict[str, Any]) -> Iterator[dict[str, Any]]:
    order = ["country", "city", "person", "detail", "note"]
    with connection.schema_editor() as editor:
        for name in order:
            editor.create_model(qmodels[name])
    try:
        yield qmodels
    finally:
        with connection.schema_editor() as editor:
            for name in reversed(order):
                editor.delete_model(qmodels[name])


def _notes(m: dict[str, Any], n: int) -> None:
    country = m["country"].objects.create(name="Spain")
    city = m["city"].objects.create(name="Malaga", country=country)
    for i in range(n):
        person = m["person"].objects.create(name=f"p{i}", city=None if i == 1 else city)
        detail = m["detail"].objects.create(nick=f"n{i}", person=person)
        # One note without author and one without detail: nullable joins
        m["note"].objects.create(
            text=f"t{i}",
            author=None if i == 2 else person,
            detail=None if i == 3 else detail,
        )


NOTE_FIELDS = [
    "text",
    "label",
    "who:author__name",
    "author__city__country__name",
    "detail__nick",
    "detail__person__name",
]


def _note_list(model: Any, fields: list[str], **attrs: Any) -> type:
    def __fields__(self: Any, info: Any) -> list[tuple[str, str]]:
        return [(f, f) for f in fields]

    return type("NoteList", (GenList,), {"model": model, "__fields__": __fields__, **attrs})


def _call(view: type) -> tuple[int, Any, int]:
    if not User.objects.filter(username="adm").exists():
        User.objects.create(username="adm", is_superuser=True, is_staff=True)
    request = RequestFactory().get(
        "/", {"json": json.dumps({"rowsperpage": "All"})}, HTTP_X_REST="1"
    )
    request.user = User.objects.get(username="adm")
    with override_settings(**LIST_SETTINGS), CaptureQueriesContext(connection) as queries:
        response = view.as_view()(request)
    body = json.loads(response.content)["table"]["body"] if response.status_code == 200 else None
    return response.status_code, body, len(queries)


def _branchless(monkeypatch: pytest.MonkeyPatch, view: type) -> tuple[int, Any, int]:
    """The same list with the to-one selection switched off (78e380e behaviour)."""
    with monkeypatch.context() as patch:
        patch.setattr(views, "_select_to_one", lambda queryset, *a, **k: queryset)
        return _call(view)


def test_to_one_paths_follow_one_to_ones_aliases_and_stop_at_other_fields(
    qmodels: dict[str, Any],
) -> None:
    note = qmodels["note"]
    assert views._to_one_paths(note, NOTE_FIELDS) == [
        "author",
        "author__city__country",
        "detail",
        "detail__person",
    ]
    # The chain ends at the first part that is not a forward to-one relation
    assert views._to_one_paths(note, ["author__name__city"]) == ["author"]


@pytest.mark.django_db
def test_select_to_one_leaves_other_querysets_alone(qmodels: dict[str, Any]) -> None:
    note = qmodels["note"]
    rules = ["text", "author__name"]
    plain = note.objects.all()
    for queryset in (
        note.objects.values("text"),
        note.objects.values_list("text"),
        note.objects.only("text"),
        note.objects.defer("text"),
        note.objects.order_by().union(note.objects.order_by()),
        [],
    ):
        assert views._select_to_one(queryset, note, rules, found=False, haystack=False) is queryset
    assert views._select_to_one(plain, note, rules, found=True, haystack=False) is plain
    assert views._select_to_one(plain, note, rules, found=False, haystack=True) is plain
    # No to-one path: select_related() without arguments would join every foreign key
    assert (
        views._select_to_one(plain, note, ["text", "label"], found=False, haystack=False) is plain
    )
    selected = views._select_to_one(plain, note, rules, found=False, haystack=False)
    assert selected.query.select_related == {"author": {}}


@pytest.mark.django_db(transaction=True)
def test_one_to_one_and_alias_columns(
    qdata: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    _notes(qdata, 2)
    status, body, few = _call(_note_list(qdata["note"], NOTE_FIELDS))
    assert status == 200
    assert (status, body) == _branchless(monkeypatch, _note_list(qdata["note"], NOTE_FIELDS))[:2]
    qdata["note"].objects.all().delete()
    _notes(qdata, 5)
    status, body, many = _call(_note_list(qdata["note"], NOTE_FIELDS))
    assert (status, body) == _branchless(monkeypatch, _note_list(qdata["note"], NOTE_FIELDS))[:2]
    # Every column walks to-one relations only: no query per row
    assert many == few


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("hook", ["class_only", "custom_only", "class_values", "custom_union"])
def test_hooks_that_narrow_the_queryset(
    qdata: dict[str, Any], monkeypatch: pytest.MonkeyPatch, hook: str
) -> None:
    note = qdata["note"]
    _notes(qdata, 4)
    attrs: dict[str, Any] = {
        "class_only": {"queryset": note.objects.only("text")},
        "custom_only": {"custom_queryset": lambda self, queryset, info: queryset.only("text")},
        "class_values": {"queryset": note.objects.values("text", "author__name")},
        # order_by() cleared on both members (SQLite refuses ORDER BY in them),
        # the union ordered as a whole so the paginator gets a stable order
        "custom_union": {
            "custom_queryset": lambda self, queryset, info: (
                queryset.order_by().union(note.objects.order_by()).order_by("id")
            ),
        },
    }[hook]
    view = _note_list(note, ["text", "label", "author__name", "author__city__name"], **attrs)
    status, body, _ = _call(view)
    assert status == 200
    assert (status, body) == _branchless(monkeypatch, view)[:2]
