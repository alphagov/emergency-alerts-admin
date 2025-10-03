import pytest
from werkzeug.datastructures import MultiDict

from app.main.forms import ChooseDurationForm


@pytest.mark.parametrize(
    "channel, hours, minutes",
    (
        ("severe", 1, 1),
        ("test", 1, 1),
        ("operator", 1, 1),
    ),
)
def test_choose_valid_duration(channel, hours, minutes):
    formdata = MultiDict({"hours": str(hours), "minutes": str(minutes)})
    form = ChooseDurationForm(channel, duration=None, formdata=formdata)
    form.hours.raw_data = str(hours)
    form.minutes.raw_data = str(minutes)
    assert form.validate()


@pytest.mark.parametrize(
    "channel",
    (
        "severe",
        "test",
        "operator",
    ),
)
def test_choose_duration_no_duration_displays_error(channel):
    formdata = MultiDict({"hours": "0", "minutes": "0"})
    form = ChooseDurationForm(channel, duration=None, formdata=formdata)
    form.validate()
    assert form.hours.errors == []
    assert form.minutes.errors == ["Duration must be at least 5 minutes"]


@pytest.mark.parametrize(
    "channel, hours, minutes, expected_hours_error, expected_minutes_error",
    (
        ("severe", 22, 31, [], ["Maximum duration is 22 hours, 30 minutes"]),
        ("test", 5, 0, ["Duration must not be greater than 4 hours"], []),
        ("operator", 4, 1, [], ["Duration must not be greater than 4 hours"]),
    ),
)
def test_choose_duration_too_long_displays_error(channel, hours, minutes, expected_hours_error, expected_minutes_error):
    formdata = MultiDict({"hours": str(hours), "minutes": str(minutes)})
    form = ChooseDurationForm(channel, duration=None, formdata=formdata)
    form.validate()
    assert form.hours.errors == expected_hours_error
    assert form.minutes.errors == expected_minutes_error
