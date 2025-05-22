from datetime import datetime, timedelta, timezone

import pytest

from app.utils.datetime import fromisoformat_allow_z_tz


@pytest.mark.parametrize(
    ["datetime_str", "datetime_obj"],
    [
        ("2025-04-01T13:08:56.787717Z", datetime(2025, 4, 1, 13, 8, 56, 787717, timezone.utc)),
        ("2020-02-20T20:20:20.000000+01:00", datetime(2020, 2, 20, 20, 20, 20, 0, timezone(timedelta(0, 3600)))),
    ],
)
def test_datetime_can_have_trailing_z(datetime_str, datetime_obj):
    assert fromisoformat_allow_z_tz(datetime_str) == datetime_obj
