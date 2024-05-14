from functools import partial

import pytest
from bs4 import BeautifulSoup
from flask import url_for
from freezegun import freeze_time

from tests.conftest import SERVICE_ONE_ID, normalize_spaces


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
        ("register", {}),
        ("features_email", {}),
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
        "pricing",
        "terms",
        "roadmap",
        "features",
        "documentation",
        "security",
        "message_status",
        "features_email",
        "features_sms",
        "features_letters",
        "how_to_pay",
        "get_started",
        "guidance_index",
        "create_and_send_messages",
        "edit_and_format_messages",
        "send_files_by_email",
        "upload_a_letter",
        "who_can_use_notify",
        "billing_details",
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


def test_guidance_pages_link_to_service_pages_when_signed_in(
    client_request,
):
    request = partial(client_request.get, "main.edit_and_format_messages")
    selector = ".govuk-list--number li a"

    # Check the page loads when user is signed in
    page = request()
    assert page.select_one(selector)["href"] == url_for(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
    )

    # Check it still works when they don’t have a recent service
    with client_request.session_transaction() as session:
        session["service_id"] = None
    page = request()
    assert not page.select_one(selector)

    # Check it still works when they sign out
    client_request.logout()
    with client_request.session_transaction() as session:
        session["service_id"] = None
        session["user_id"] = None
    page = request()
    assert not page.select_one(selector)


@pytest.mark.parametrize(
    "view, expected_view",
    [
        ("information_risk_management", "security"),
        ("old_integration_testing", "integration_testing"),
        ("old_roadmap", "roadmap"),
        ("information_risk_management", "security"),
        ("old_terms", "terms"),
        ("information_security", "using_emergency_alerts"),
        ("old_using_notify", "using_emergency_alerts"),
        ("delivery_and_failure", "message_status"),
        ("callbacks", "documentation"),
        ("who_its_for", "who_can_use_notify"),
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


def test_message_status_page_contains_message_status_ids(client_request):
    # The 'email-statuses' and 'sms-statuses' id are linked to when we display a message status,
    # so this test ensures we don't accidentally remove them
    page = client_request.get("main.message_status")

    assert page.select_one("#email-statuses")
    assert page.select_one("#text-message-statuses")


def test_message_status_page_contains_link_to_support(client_request):
    page = client_request.get("main.message_status")
    sms_status_table = page.select_one("#text-message-statuses").findNext("tbody")

    temp_fail_details_cell = sms_status_table.select_one("tr:nth-child(4) > td:nth-child(2)")
    assert temp_fail_details_cell.select_one("a")["href"] == url_for("main.support")


def test_old_using_notify_page(client_request):
    client_request.get("main.using_emergency_alerts", _expected_status=410)


def test_old_integration_testing_page(
    client_request,
):
    page = client_request.get(
        "main.integration_testing",
        _expected_status=410,
    )
    assert normalize_spaces(page.select_one(".govuk-grid-row").text) == (
        "Integration testing "
        "This information has moved. "
        "Refer to the documentation for the client library you are using."
    )
    assert page.select_one(".govuk-grid-row a")["href"] == url_for("main.documentation")


def test_terms_page_has_correct_content(client_request):
    terms_page = client_request.get("main.terms")
    assert normalize_spaces(terms_page.select("main p")[0].text) == (
        "These terms apply to your use of GOV.UK Emergency Alerts."
    )


def test_css_is_served_from_correct_path(client_request):
    page = client_request.get("main.documentation")  # easy static page

    for index, link in enumerate(page.select("link[rel=stylesheet]")):
        assert link["href"].startswith(
            [
                "https://static.example.com/stylesheets/main.css?",
                "https://static.example.com/stylesheets/print.css?",
            ][index]
        )


def test_resources_that_use_asset_path_variable_have_correct_path(client_request):
    page = client_request.get("main.documentation")  # easy static page

    favicon = page.select_one('link[type="image/x-icon"]')

    assert favicon.attrs["href"].startswith("https://static.example.com/images/favicon.ico")


def test_letter_spec_redirect(client_request):
    client_request.get(
        "main.letter_spec",
        _expected_status=302,
        _expected_redirect=(
            "https://docs.notifications.service.gov.uk" "/documentation/images/notify-pdf-letter-spec-v2.4.pdf"
        ),
    )


def test_letter_spec_redirect_with_non_logged_in_user(client_request):
    client_request.logout()
    client_request.get(
        "main.letter_spec",
        _expected_status=302,
        _expected_redirect=(
            "https://docs.notifications.service.gov.uk" "/documentation/images/notify-pdf-letter-spec-v2.4.pdf"
        ),
    )
