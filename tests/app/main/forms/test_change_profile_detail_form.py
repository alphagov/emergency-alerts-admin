from app.main.forms import ChangeEmailForm, ChangeMobileNumberForm, ChangeNameForm


def test_invalid_name_error_message(
    client_request,
):
    form = ChangeNameForm(
        new_name="",
    )
    assert not form.validate()


def test_invalid_email_address_error_message(client_request, mock_already_registered, mock_get_organisations):
    form = ChangeEmailForm("leyla.yaltiligil@digital.cabinet-office.gov.uk")
    assert not form.validate()


def test_invalid_mobile_number_error_message(
    client_request,
):
    form = ChangeMobileNumberForm(mobile_number="")
    assert not form.validate()
