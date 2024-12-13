import pytest

from app.main.forms import get_placeholder_form_instance


def test_form_class_not_mutated(notify_admin):
    with notify_admin.test_request_context(method="POST", data={"placeholder_value": ""}):
        form1 = get_placeholder_form_instance("name", {}, "sms")
        form2 = get_placeholder_form_instance("city", {}, "sms")

        assert not form1.validate_on_submit()
        assert not form2.validate_on_submit()

        assert str(form1.placeholder_value.label) == '<label for="placeholder_value">name</label>'
        assert str(form2.placeholder_value.label) == '<label for="placeholder_value">city</label>'


@pytest.mark.parametrize(
    "placeholder_name, template_type, value, expected_error",
    [
        ("email address", "email", "", "Cannot be empty"),
        ("email address", "email", "12345", "Enter a valid email address"),
        ("email address", "email", "“bad”@email-address.com", "Enter a valid email address"),
        ("email address", "email", "test@example.com", None),
        ("email address", "email", "test@example.gov.uk", None),
        ("phone number", "sms", "", "Cannot be empty"),
        ("phone number", "sms", "+1-2345-678890", "Not a UK mobile number"),
        ("phone number", "sms", "07900900123", None),
        ("phone number", "sms", "+44(0)7900 900-123", None),
        ("anything else", "sms", "", "Cannot be empty"),
        ("anything else", "email", "", "Cannot be empty"),
    ],
)
def test_validates_recipients(
    notify_admin,
    placeholder_name,
    template_type,
    value,
    expected_error,
):
    with notify_admin.test_request_context(method="POST", data={"placeholder_value": value}):
        form = get_placeholder_form_instance(
            placeholder_name,
            {},
            template_type,
        )

        if expected_error:
            assert not form.validate_on_submit()
            assert form.placeholder_value.errors[0] == expected_error
        else:
            assert form.validate_on_submit()
