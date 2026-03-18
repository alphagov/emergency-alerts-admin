from unittest.mock import ANY

import pytest
from flask import url_for

from app.models.user import User
from tests.conftest import normalize_spaces


@pytest.mark.parametrize(
    "email_address, expected_value",
    [
        ("first.last@example.com", "First Last"),
        ("first.middle.last@example.com", "First Middle Last"),
        ("first.m.last@example.com", "First Last"),
        ("first.last-last@example.com", "First Last-Last"),
        ("first.o'last@example.com", "First O’Last"),
        ("first.last+testing@example.com", "First Last"),
        ("first.last+testing+testing@example.com", "First Last"),
        ("first.last6@example.com", "First Last"),
        ("first.last.212@example.com", "First Last"),
        ("first.2.last@example.com", "First Last"),
        ("first.2b.last@example.com", "First Last"),
        ("first.1.2.3.last@example.com", "First Last"),
        ("first.last.1.2.3@example.com", "First Last"),
        # Instances where we can’t make a good-enough guess:
        ("example123@example.com", ""),
        ("f.last@example.com", ""),
        ("f.m.last@example.com", ""),
    ],
)
def test_shows_name_on_registration_page_from_invite(
    client_request,
    fake_uuid,
    email_address,
    expected_value,
    sample_invite,
    mock_get_invited_user_by_id,
):
    sample_invite["email_address"] = email_address
    with client_request.session_transaction() as session:
        session["invited_user_id"] = sample_invite

    page = client_request.get("main.register_from_invite")
    assert page.select_one("input[name=name]").get("value") == expected_value


def test_shows_hidden_email_address_on_registration_page_from_invite(
    client_request,
    fake_uuid,
    sample_invite,
    mock_get_invited_user_by_id,
):
    with client_request.session_transaction() as session:
        session["invited_user_id"] = sample_invite

    page = client_request.get("main.register_from_invite")
    assert normalize_spaces(page.select_one("main p").text) == (
        "Your account will be created with this email address: invited_user@test.gov.uk"
    )
    hidden_input = page.select_one("form .govuk-visually-hidden input")
    for attr, value in (
        ("type", "email"),
        ("name", "username"),
        ("id", "username"),
        ("value", "invited_user@test.gov.uk"),
        ("disabled", "disabled"),
        ("tabindex", "-1"),
        ("aria-hidden", "true"),
        ("autocomplete", "username"),
    ):
        assert hidden_input[attr] == value


@pytest.mark.parametrize(
    "extra_data",
    (
        {},
        # The username field is present in the page but the POST request
        # should ignore it
        {"username": "invited@user.com"},
        {"username": "anythingelse@example.com"},
    ),
)
def test_register_from_invite(
    client_request,
    fake_uuid,
    mock_email_is_not_already_in_use,
    mock_register_user,
    mock_send_verify_code,
    mock_accept_invite,
    mock_get_invited_user_by_id,
    sample_invite,
    extra_data,
):
    client_request.logout()
    with client_request.session_transaction() as session:
        session["invited_user_id"] = sample_invite["id"]
    client_request.post(
        "main.register_from_invite",
        _data=dict(
            name="Registered in another Browser",
            email_address=sample_invite["email_address"],
            mobile_number="+4407700900460",
            service=sample_invite["service"],
            password="somreallyhardthingtoguess",
            auth_type="sms_auth",
            **extra_data
        ),
        _expected_redirect=url_for("main.verify"),
    )
    mock_register_user.assert_called_once_with(
        "Registered in another Browser",
        sample_invite["email_address"],
        "+4407700900460",
        "somreallyhardthingtoguess",
        "sms_auth",
    )
    mock_get_invited_user_by_id.assert_called_once_with(sample_invite["id"])


def test_register_from_invite_when_user_registers_in_another_browser(
    client_request,
    api_user_active,
    mock_get_user_by_email,
    mock_accept_invite,
    mock_get_invited_user_by_id,
    sample_invite,
):
    client_request.logout()
    sample_invite["email_address"] = api_user_active["email_address"]
    with client_request.session_transaction() as session:
        session["invited_user_id"] = sample_invite["id"]
    client_request.post(
        "main.register_from_invite",
        _data={
            "name": "Registered in another Browser",
            "email_address": api_user_active["email_address"],
            "mobile_number": api_user_active["mobile_number"],
            "service": sample_invite["service"],
            "password": "somreallyhardthingtoguess",
            "auth_type": "sms_auth",
        },
        _expected_redirect=url_for("main.verify"),
    )


@pytest.mark.parametrize("invite_email_address", ["gov-user@gov.uk", "non-gov-user@example.com"])
def test_register_from_email_auth_invite(
    client_request,
    sample_invite,
    mock_email_is_not_already_in_use,
    mock_register_user,
    mock_get_user,
    mock_send_verify_email,
    mock_send_verify_code,
    mock_accept_invite,
    mock_create_event,
    mock_add_user_to_service,
    mock_get_service,
    mock_get_invited_user_by_id,
    invite_email_address,
    service_one,
    fake_uuid,
    mocker,
):
    client_request.logout()
    mock_login_user = mocker.patch("app.models.user.login_user")
    sample_invite["auth_type"] = "email_auth"
    sample_invite["email_address"] = invite_email_address
    with client_request.session_transaction() as session:
        session["invited_user_id"] = sample_invite["id"]
        # Prove that the user isn’t already signed in
        assert "user_id" not in session

    data = {
        "name": "invited user",
        "email_address": sample_invite["email_address"],
        "mobile_number": "07700900001",
        "password": "FSLKAJHFNvdzxgfyst",
        "service": sample_invite["service"],
        "auth_type": "email_auth",
    }

    client_request.post(
        "main.register_from_invite",
        _data=data,
        _expected_redirect=url_for(
            "main.broadcast_tour",
            service_id=sample_invite["service"],
            step_index=1,
        ),
    )

    # doesn't send any 2fa code
    assert not mock_send_verify_email.called
    assert not mock_send_verify_code.called
    # creates user with email_auth set
    mock_register_user.assert_called_once_with(
        data["name"], data["email_address"], data["mobile_number"], data["password"], data["auth_type"]
    )
    # this is actually called twice, at the beginning of the function and then by the activate_user function
    mock_get_invited_user_by_id.assert_called_with(sample_invite["id"])
    mock_accept_invite.assert_called_once_with(sample_invite["service"], sample_invite["id"])

    # just logs them in
    mock_login_user.assert_called_once_with(
        User({"id": fake_uuid, "platform_admin": False})  # This ID matches the return value of mock_register_user
    )
    mock_add_user_to_service.assert_called_once_with(
        sample_invite["service"],
        fake_uuid,  # This ID matches the return value of mock_register_user
        {"manage_api_keys", "manage_service", "view_activity"},
        [],
    )

    with client_request.session_transaction() as session:
        # The user is signed in
        assert "user_id" in session
        # user already added to the service at this point, so check
        # invited_user_id has been removed from session
        assert "invited_user_id" not in session


def test_can_register_email_auth_without_phone_number(
    client_request,
    sample_invite,
    mock_email_is_not_already_in_use,
    mock_register_user,
    mock_get_user,
    mock_send_verify_email,
    mock_send_verify_code,
    mock_accept_invite,
    mock_create_event,
    mock_add_user_to_service,
    mock_get_service,
    mock_get_invited_user_by_id,
):
    client_request.logout()
    sample_invite["auth_type"] = "email_auth"
    with client_request.session_transaction() as session:
        session["invited_user_id"] = sample_invite["id"]

    data = {
        "name": "invited user",
        "email_address": sample_invite["email_address"],
        "mobile_number": "",
        "password": "FSLKAJHFNvdzxgfyst",
        "service": sample_invite["service"],
        "auth_type": "email_auth",
    }

    client_request.post(
        "main.register_from_invite",
        _data=data,
        _expected_redirect=url_for(
            "main.broadcast_tour",
            service_id=sample_invite["service"],
            step_index=1,
        ),
    )

    mock_register_user.assert_called_once_with(ANY, ANY, None, ANY, ANY)  # mobile_number


def test_register_from_invite_form_doesnt_show_mobile_number_field_if_email_auth(
    client_request,
    sample_invite,
    mock_get_invited_user_by_id,
):
    client_request.logout()
    sample_invite["auth_type"] = "email_auth"
    with client_request.session_transaction() as session:
        session["invited_user_id"] = sample_invite["id"]

    page = client_request.get("main.register_from_invite")

    assert page.select_one("input[name=auth_type]")["value"] == "email_auth"
    assert page.select_one("input[name=mobile_number]") is None
