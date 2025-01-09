from functools import partial

import pytest
from bs4 import BeautifulSoup
from flask import url_for
from freezegun import freeze_time


def test_non_logged_in_user_redirects_to_sign_in(
    client_request,
    mock_get_service_and_organisation_counts,
):
    client_request.logout()

    client_request.get(
        "main.index",
        _expected_status=302,
    )


def test_logged_in_user_redirects_to_choose_account(
    client_request,
    api_user_active,
    mock_get_user,
    mock_get_user_by_email,
    mock_login,
):
    client_request.get(
        "main.index",
        _expected_status=302,
    )
    client_request.get(
        "main.sign_in", _expected_status=302, _expected_redirect=url_for("main.show_accounts_or_dashboard")
    )


def test_robots(client_request):
    client_request.get_url("/robots.txt", _expected_status=200, _test_page_title=False)


@pytest.mark.parametrize(
    "endpoint, kwargs",
    (
        ("sign_in", {}),
        ("support", {}),
        ("support_public", {}),
        ("triage", {}),
        ("feedback", {"ticket_type": "ask-question-give-feedback"}),
        ("feedback", {"ticket_type": "general"}),
        ("feedback", {"ticket_type": "report-problem"}),
        ("bat_phone", {}),
        ("thanks", {}),
        pytest.param("index", {}, marks=pytest.mark.xfail(raises=AssertionError)),
    ),
)
@freeze_time("2012-12-12 12:12")  # So we don’t go out of business hours
def test_hiding_pages_from_search_engines(
    client_request,
    mock_get_service_and_organisation_counts,
    endpoint,
    kwargs,
):
    client_request.logout()
    response = client_request.get_response(f"main.{endpoint}", **kwargs)
    assert "X-Robots-Tag" in response.headers
    assert response.headers["X-Robots-Tag"] == "noindex"

    page = BeautifulSoup(response.data.decode("utf-8"), "html.parser")
    assert page.select_one("meta[name=robots]")["content"] == "noindex"


@pytest.mark.parametrize(
    "view",
    [
        "cookies",
        "privacy",
        "terms",
        "security",
    ],
)
def test_static_pages(
    client_request,
    mock_get_organisation_by_domain,
    view,
):
    request = partial(client_request.get, "main.{}".format(view))

    # Check the page loads when user is signed in
    page = request()
    assert not page.select_one("meta[name=description]")

    # Check it still works when they don’t have a recent service
    with client_request.session_transaction() as session:
        session["service_id"] = None
    request()

    # Check it still works when they sign out
    client_request.logout()
    with client_request.session_transaction() as session:
        session["service_id"] = None
        session["user_id"] = None
    request()


@pytest.mark.parametrize(
    "view, expected_view",
    [
        ("information_risk_management", "security"),
        ("information_risk_management", "security"),
        ("old_terms", "terms"),
    ],
)
def test_old_static_pages_redirect(client_request, view, expected_view):
    client_request.logout()
    client_request.get(
        "main.{}".format(view),
        _expected_status=301,
        _expected_redirect=url_for(
            "main.{}".format(expected_view),
        ),
    )
