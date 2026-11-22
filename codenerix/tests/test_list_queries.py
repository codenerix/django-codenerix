"""GenList selects the foreign keys its columns walk, rows and values unchanged.

A list over django.contrib.admin's LogEntry with a many-to-many column
(user__groups) and a method column (get_change_message): either one made the
list builder drop its select_related, so every row fetched its user and its
content type on its own.
"""

import json
from typing import Any

import pytest
from django.contrib.admin.models import ADDITION, LogEntry
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import RequestFactory, override_settings
from django.test.utils import CaptureQueriesContext

# codenerix.views reads STATIC_URL while its classes are created, as in
# test_haystack_checks.py; ALL_PAGESALLOWED and MEDIA_URL are read per request
LIST_SETTINGS = {"STATIC_URL": "/static/", "ALL_PAGESALLOWED": True, "MEDIA_URL": "/media/"}
with override_settings(**LIST_SETTINGS):
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
