import pytest

from app.main.forms import RegisterUserForm


@pytest.mark.parametrize("password", ["govuknotify", "11111111", "kittykat", "blackbox"])
def test_should_raise_validation_error_for_password(
    client_request,
    mock_get_user_by_email,
    password,
):
    form = RegisterUserForm()
    form.name.data = "test"
    form.email_address.data = "teset@example.gov.uk"
    form.mobile_number.data = "441231231231"
    form.new_password.data = password

    form.validate()
    assert "Choose a password that’s harder to guess" in form.errors["new_password"]


@pytest.mark.parametrize("password", ["govuknotif1", "1111112!", "lowentropy"])
def test_should_raise_low_entropy_validation_error_for_password(
    client_request,
    mock_get_user_by_email,
    password,
):
    form = RegisterUserForm()
    form.name.data = "test"
    form.email_address.data = "teset@example.gov.uk"
    form.mobile_number.data = "441231231231"
    form.new_password.data = password

    form.validate()
    assert (
        "Your password is not strong enough. To make it stronger, you can: "
        "<ul class='govuk-error-message govuk-list govuk-list--bullet'>"
        "<li>Increase the length of your password.</li>"
        "<li>Use a mix of upper and lower case letters, numbers, and special characters.</li>"
        "</ul>" in form.errors["new_password"]
    )


def test_valid_email_not_in_valid_domains(
    client_request,
    mock_get_organisations,
):
    form = RegisterUserForm(email_address="test@test.com", mobile_number="441231231231")
    assert not form.validate()
    assert "Enter a public sector email address" in form.errors["email_address"][0]


def test_valid_email_in_valid_domains(
    client_request,
):
    form = RegisterUserForm(
        name="test", email_address="test@my.gov.uk", mobile_number="4407888999111", new_password="an uncommon password"
    )
    form.validate()
    assert form.errors == {}


def test_invalid_email_address_error_message(
    client_request,
    mock_get_organisations,
):
    form = RegisterUserForm(name="test", email_address="test.com", mobile_number="4407888999111", password="1234567890")
    assert not form.validate()

    form = RegisterUserForm(name="test", email_address="test.com", mobile_number="4407888999111", password="1234567890")
    assert not form.validate()
