from unittest.mock import ANY

import pytest
from emergency_alerts_utils.clients.zendesk.zendesk_client import EASSupportTicket
from flask import url_for

from tests.conftest import SERVICE_ONE_ID, normalize_spaces


def no_redirect():
    return lambda: None


def test_passed_non_logged_in_user_details_through_flow(client_request, mocker):
    client_request.logout()
    mock_create_ticket = mocker.spy(EASSupportTicket, "__init__")
    mock_send_ticket_to_zendesk = mocker.patch(
        "app.main.views.feedback.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
    )

    data = {"feedback": "blah", "name": "Anne Example", "email_address": "anne@example.com"}

    client_request.post(
        "main.support",
        _data=data,
        _expected_redirect=url_for(
            "main.thanks",
        ),
    )

    mock_create_ticket.assert_called_once_with(
        ANY,
        subject="Emergency Alerts feedback",
        message="blah\n",
        ticket_type="question",
        p1=False,
        user_name="Anne Example",
        user_email="anne@example.com",
        org_id=None,
        org_type=None,
        service_id=None,
    )
    mock_send_ticket_to_zendesk.assert_called_once()


@pytest.mark.parametrize(
    "data", [{"feedback": "blah"}, {"feedback": "blah", "name": "Ignored", "email_address": "ignored@email.com"}]
)
def test_passes_logged_in_user_details_through_flow(
    client_request,
    mock_get_non_empty_organisations_and_services_for_user,
    mocker,
    data,
):
    mock_create_ticket = mocker.spy(EASSupportTicket, "__init__")
    mock_send_ticket_to_zendesk = mocker.patch(
        "app.main.views.feedback.zendesk_client.send_ticket_to_zendesk",
        autospec=True,
    )

    client_request.post(
        "main.support",
        _data=data,
        _expected_status=302,
        _expected_redirect=url_for(
            "main.thanks",
        ),
    )
    mock_create_ticket.assert_called_once_with(
        ANY,
        subject="Emergency Alerts feedback",
        message=ANY,
        ticket_type="question",
        p1=False,
        user_name="Test User",
        user_email="test@user.gov.uk",
        org_id=None,
        org_type="central",
        service_id=SERVICE_ONE_ID,
    )

    assert mock_create_ticket.call_args[1]["message"] == "\n".join(
        [
            "blah",
            'Service: "service one"',
            url_for(
                "main.service_dashboard",
                service_id=SERVICE_ONE_ID,
                _external=True,
            ),
            "",
        ]
    )
    mock_send_ticket_to_zendesk.assert_called_once()


def test_email_address_must_be_valid_if_provided_to_support_form(
    client_request,
    mocker,
):
    client_request.logout()
    page = client_request.post(
        "main.support",
        _data={
            "feedback": "blah",
            "email_address": "not valid",
        },
        _expected_status=200,
    )

    assert normalize_spaces(page.select_one(".govuk-error-message").text) == "Error: Enter a valid email address"


def test_thanks(
    client_request,
    mocker,
    api_user_active,
    mock_get_user,
):
    page = client_request.get(
        "main.thanks",
    )
    assert (
        normalize_spaces(page.select_one("main").find("p").text)
        == "We'll aim to read and reply to your message in the next working day."
    )
