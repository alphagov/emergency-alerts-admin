import pytest

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
    form = ChooseDurationForm(channel, duration=None)
    form.hours.raw_data = str(hours)
    form.minutes.raw_data = str(minutes)
    assert form.validate()


@pytest.mark.parametrize(
    "channel",
    (
        ("severe"),
        ("test"),
        ("operator"),
    ),
)
def test_choose_duration_no_duration_displays_error(channel):
    form = ChooseDurationForm(channel, duration=None)
    form.hours.raw_data = 0
    form.minutes.raw_data = 0
    form.validate()
    assert form.hours.errors == []
    assert form.minutes.errors == ["Duration must be at least 5 minutes"]


@pytest.mark.parametrize(
    "channel, hours, minutes",
    (
        ("severe", 22, 31),
        ("test", 5, 0),
        ("operator", 1, 1),
    ),
)
def test_choose_duration_too_long_displays_error(channel, hours, minutes):
    form = ChooseDurationForm(channel, duration=None)
    form.hours.raw_data = 0
    form.minutes.raw_data = 0
    assert form.validate()
