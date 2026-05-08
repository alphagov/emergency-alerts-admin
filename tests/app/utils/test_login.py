import pytest
from flask import url_for
from freezegun import freeze_time

from app.models.user import User
from app.utils.login import (
    email_needs_revalidating,
    is_less_than_days_ago,
    redirect_when_logged_in,
)


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


@pytest.mark.parametrize(
    "next, allow_redirect",
    [
        ("foo", True),
        ("foo/bar", True),
        ("https://localhost/next", True),
        ("https://request-elsewhere/next", False),
        ("foo/bar\n", False),
        ("foo/bar\ncontent", False),
    ],
)
def test_redirect_when_logged_in(notify_admin, next, allow_redirect):
    with notify_admin.test_request_context(query_string={"next": next}):
        fallback_redirect_url = url_for("main.show_accounts_or_dashboard")

        response = redirect_when_logged_in(False)
        assert response.headers["Location"] == next if allow_redirect else fallback_redirect_url
