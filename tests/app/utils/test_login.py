import pytest
from freezegun import freeze_time

from app.models.user import User
from app.utils.login import email_needs_revalidating, is_less_than_days_ago


@freeze_time("2020-11-27T12:00:00")
@pytest.mark.parametrize(
    ("email_access_validated_at", "expected_result"),
    (
        ("2020-10-01T11:35:21.726132Z", False),
        ("2020-07-23T11:35:21.726132Z", True),
    ),
)
def test_email_needs_revalidating(
    api_user_active,
    email_access_validated_at,
    expected_result,
):
    api_user_active["email_access_validated_at"] = email_access_validated_at
    assert email_needs_revalidating(User(api_user_active)) == expected_result


@pytest.mark.parametrize(
    "date_from_db, expected_result",
    [
        ("2019-11-17T11:35:21.726132Z", True),
        ("2019-11-16T11:35:21.726132Z", False),
        ("2019-11-16T11:35:21+0000", False),
    ],
)
@freeze_time("2020-02-14T12:00:00")
def test_is_less_than_days_ago(date_from_db, expected_result):
    assert is_less_than_days_ago(date_from_db, 90) == expected_result
