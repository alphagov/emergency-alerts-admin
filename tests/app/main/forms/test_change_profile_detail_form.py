import pytest

from app.main.forms import ChangeEmailForm, ChangeMobileNumberForm, ChangeNameForm


def test_empty_email_address_error_message(client_request, mock_already_registered, mock_get_organisations):
    form = ChangeEmailForm(mock_already_registered)
    form.email_address.data = ""
    assert not form.validate()
    assert form.errors == {"email_address": ["Enter a valid email address"]}


def test_already_used_email_address_error_message(client_request, mock_already_registered, mock_get_organisations):
    form = ChangeEmailForm(mock_already_registered)
    form.email_address.data = "test@digital.cabinet-office.gov.uk"
    assert not form.validate()
    assert form.errors == {"email_address": ["The email address is already in use"]}


@pytest.mark.parametrize(
    "mobile_number, expected_error", (("", "Enter a valid mobile number"), ("+441234123412", "Not a UK mobile number"))
)
def test_invalid_mobile_number_error_message(
    mobile_number,
    expected_error,
    client_request,
):
    form = ChangeMobileNumberForm(mobile_number=mobile_number)
    assert not form.validate()
    assert form.errors == {"mobile_number": [expected_error]}


@pytest.mark.parametrize(
    "name, expected_error", (("", "Enter a name"), ("Test User", "Name must be different to current name"))
)
def test_invalid_name_error_message(
    name,
    expected_error,
    client_request,
):
    form = ChangeNameForm(
        new_name=name,
    )
    assert not form.validate()
    assert form.errors == {"new_name": [expected_error]}


def test_change_name_form_valid(
    client_request,
):
    form = ChangeNameForm(
        new_name="Test",
    )
    assert form.validate()


def test_change_email_address_form_valid(client_request, mock_not_already_registered, mock_get_organisations):
    form = ChangeEmailForm(mock_not_already_registered)
    form.email_address.data = "test@digital.cabinet-office.gov.uk"
    assert form.validate()


def test_change_mobile_number_form_valid(
    client_request,
):
    form = ChangeMobileNumberForm(mobile_number="+447700900986")
    assert form.validate()
