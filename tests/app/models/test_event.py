import pytest

from app.models.event import ServiceEvent
from tests.conftest import sample_uuid


@pytest.mark.parametrize(
    "key, value_from, value_to, expected",
    (
        ("restricted", True, False, "Made this service live"),
        ("restricted", False, True, "Put this service back into trial mode"),
        ("active", False, True, "Unsuspended this service"),
        ("active", True, False, "Deleted this service"),
        ("name", "Old", "New", "Renamed this service from ‘Old’ to ‘New’"),
        ("permissions", ["a", "b", "c"], ["a", "b", "c", "d"], "Added ‘d’ to this service’s permissions"),
        ("permissions", ["a", "b", "c"], ["a", "b"], "Removed ‘c’ from this service’s permissions"),
        (
            "permissions",
            ["a", "b", "c"],
            ["c", "d", "e"],
            "Removed ‘a’ and ‘b’ from this service’s permissions, added ‘d’ and ‘e’",
        ),
        ("service_callback_api", "foo", "bar", "Updated the callback for delivery receipts"),
    ),
)
def test_service_event(
    key,
    value_from,
    value_to,
    expected,
):
    event = ServiceEvent(
        {
            "created_at": "foo",
            "updated_at": "bar",
            "created_by_id": sample_uuid(),
        },
        key,
        value_from,
        value_to,
    )
    assert event.relevant is True
    assert str(event) == expected
