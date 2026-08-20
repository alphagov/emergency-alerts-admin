from unittest.mock import Mock

import pytest
from wtforms import ValidationError

from app.main.validators import (
    BlockedEmailDomain,
    CharactersNotAllowed,
    MustContainAlphanumericCharacters,
    NoCommasInPlaceHolders,
    NoDuplicates,
    OnlySMSCharacters,
    StringsNotAllowed,
    ValidGovEmail,
)


def _gen_mock_field(x):
    return Mock(data=x)


@pytest.mark.parametrize(
    "email",
    [
        "test@gov.uk",
        "test@GOV.UK",
        "test@gov.uK",
        "test@test.test.gov.uk",
        "test@test.gov.uk",
        "test@nhs.uk",
        "test@gov.nhs.uk",
        "test@nhs.net",
        "test@gov.nhs.net",
        "test@nhs.scot",
        "test@police.uk",
        "test@gov.police.uk",
        "test@GOV.PoliCe.uk",
        "test@cjsm.net",
        "test@example.ac.uk",
        "test@example.sch.uk",
    ],
)
def test_valid_list_of_white_list_email_domains(
    client_request,
    email,
):
    email_domain_validators = ValidGovEmail()
    email_domain_validators(None, _gen_mock_field(email))


@pytest.mark.parametrize(
    "email",
    [
        "test@ukgov.uk",
        "test@gov.uk.uk",
        "test@gov.test.uk",
        "test@ukmod.uk",
        "test@mod.uk.uk",
        "test@mod.test.uk",
        "test@ukddc-mod.org",
        "test@ddc-mod.org.uk",
        "test@ddc-mod.uk.org",
        "test@ukgov.scot",
        "test@gov.scot.uk",
        "test@gov.test.scot",
        "test@ukparliament.uk",
        "test@parliament.uk.uk",
        "test@parliament.test.uk",
        "test@uknhs.uk",
        "test@nhs.uk.uk",
        "test@uknhs.net",
        "test@nhs.net.uk",
        "test@nhs.test.net",
        "test@ukpolice.uk",
        "test@police.uk.uk",
        "test@police.test.uk",
        "test@ucds.com",
        "test@123bl.uk",
    ],
)
def test_invalid_list_of_white_list_email_domains(
    client_request,
    email,
    mock_get_organisations,
):
    email_domain_validators = ValidGovEmail()
    with pytest.raises(ValidationError):
        email_domain_validators(None, _gen_mock_field(email))


@pytest.mark.parametrize(
    "email",
    [
        "test@gov.uk",
        "test@GOV.UK",
        "test@gov.uK",
        "test@test.test.gov.uk",
        "test@test.gov.uk",
        "test@nhs.uk",
        "test@gov.nhs.uk",
        "test@nhs.net",
        "test@gov.nhs.net",
        "test@nhs.scot",
        "test@police.uk",
        "test@gov.police.uk",
        "test@GOV.PoliCe.uk",
        "test@cjsm.net",
        "test@example.ac.uk",
        "test@example.sch.uk",
    ],
)
def test_valid_list_of_black_list_email_domains(
    client_request,
    email,
):
    email_domain_validators = BlockedEmailDomain()
    email_domain_validators(None, _gen_mock_field(email))


@pytest.mark.parametrize(
    "email",
    [
        "test@gmail.com",
        "test@googlemail.com",
        "test@outlook.com",
        "test@hotmail.com",
        "test@live.com",
        "test@msn.com",
        "test@yahoo.com",
        "test@ymail.com",
        "test@icloud.com",
        "test@me.com",
        "test@mac.com",
        "test@protonmail.com",
        "test@proton.me",
        "test@gmx.com",
        "test@gmx.co.uk",
        "test@mail.com",
        "test@zoho.com",
        "test@fastmail.com",
        "test@tutanota.com",
        "test@mailinator.com",
        "test@tempmail.com",
        "test@10minutemail.com",
        "test@guerrillamail.com",
        "test@trashmail.com",
        "test@dispostable.com",
        "test@fakeinbox.com",
        "test@getnada.com",
        "test@maildrop.cc",
        "test@pm.me",
        "test@cock.li",
        "test@riseup.net",
    ],
)
def test_invalid_list_of_black_list_email_domains(
    client_request,
    email,
    mock_get_organisations,
):
    email_domain_validators = BlockedEmailDomain()
    with pytest.raises(ValidationError):
        email_domain_validators(None, _gen_mock_field(email))


def test_for_commas_in_placeholders(
    client_request,
):
    with pytest.raises(ValidationError) as error:
        NoCommasInPlaceHolders()(None, _gen_mock_field("Hello ((name,date))"))
    assert str(error.value) == "You cannot put commas between double brackets"
    NoCommasInPlaceHolders()(None, _gen_mock_field("Hello ((name))"))


@pytest.mark.parametrize("msg", ["The quick brown fox", "Thé “quick” bröwn fox\u200b"])
def test_sms_character_validation(client_request, msg):
    OnlySMSCharacters(template_type="sms")(None, _gen_mock_field(msg))


@pytest.mark.parametrize(
    "data, err_msg",
    [
        (
            "∆ abc 📲 def 📵 ghi",
            "You cannot use ∆, 📲 or 📵 in broadcasts. They will not show up properly on everyone’s phones.",
        ),
        ("📵", "You cannot use 📵 in broadcasts. It will not show up properly on everyone’s phones."),
    ],
)
def test_non_sms_character_validation(data, err_msg, client_request):
    with pytest.raises(ValidationError) as error:
        OnlySMSCharacters(template_type="broadcast")(None, _gen_mock_field(data))

    assert str(error.value) == err_msg


@pytest.mark.parametrize("string", [".", "A.", ".8...."])
def test_if_string_does_not_contain_alphanumeric_characters_raises(string):
    with pytest.raises(ValidationError) as error:
        MustContainAlphanumericCharacters()(None, _gen_mock_field(string))

    assert str(error.value) == "Must include at least two alphanumeric characters"


@pytest.mark.parametrize("string", [".A8", "AB.", ".42...."])
def test_if_string_contains_alphanumeric_characters_does_not_raise(string):
    MustContainAlphanumericCharacters()(None, _gen_mock_field(string))


def test_string_cannot_contain_characters():
    with pytest.raises(ValidationError) as error:
        CharactersNotAllowed("abcdef")(None, _gen_mock_field("abc"))

    assert str(error.value) == "Cannot contain a, b or c"


def test_string_cannot_contain_characters_with_custom_error_message():
    with pytest.raises(ValidationError) as error:
        CharactersNotAllowed("abcdef", message="Cannot use first 3 letters of the alphabet")(
            None, _gen_mock_field("abc")
        )

    assert str(error.value) == "Cannot use first 3 letters of the alphabet"


@pytest.mark.parametrize(
    "field_value, expected_error",
    (
        ("abc", "Cannot be ‘abc’"),
        ("ABC", "Cannot be ‘abc’"),
        ("123", "Cannot be ‘123’"),
        pytest.param(
            "abc123",
            "Cannot be ‘abc’",
            marks=pytest.mark.xfail(reason="Shouldn’t match on substrings"),
        ),
    ),
)
def test_string_cannot_contain_string(field_value, expected_error):
    with pytest.raises(ValidationError) as error:
        StringsNotAllowed("abc", "123")(None, _gen_mock_field(field_value))

    assert str(error.value) == expected_error


@pytest.mark.parametrize(
    "field_value, expected_error",
    (
        ("abc", "Cannot contain ‘abc’"),
        ("ABC", "Cannot contain ‘abc’"),
        ("123", "Cannot contain ‘123’"),
        ("abc123", "Cannot contain ‘abc’"),
    ),
)
def test_string_cannot_contain_substrings(field_value, expected_error):
    with pytest.raises(ValidationError) as error:
        StringsNotAllowed("abc", "123", match_on_substrings=True)(None, _gen_mock_field(field_value))

    assert str(error.value) == expected_error


def test_string_cannot_contain_string_with_custom_error_message():
    with pytest.raises(ValidationError) as error:
        StringsNotAllowed("abc", "123", message="No sequences please")(None, _gen_mock_field("abc"))

    assert str(error.value) == "No sequences please"


class _Field:
    def __init__(self, name, data):
        self.name = name
        self.data = data
        self.errors = []


class _Form:
    def __init__(self, fieldlist_name, fields):
        setattr(self, fieldlist_name, fields)


@pytest.mark.parametrize(
    "values",
    [
        ["a@example.com", "b@example.com", "c@example.com"],
        ["one", "two", "three"],
    ],
)
def test_no_duplicate_allows_unique_values(values):
    fields = [
        _Field("emails-0", values[0]),
        _Field("emails-1", values[1]),
        _Field("emails-2", values[2]),
    ]
    form = _Form("emails", fields)

    validator = NoDuplicates()

    # Should not raise
    for field in fields:
        validator(form, field)


@pytest.mark.parametrize(
    "values, index",
    [
        (["a@example.com", "a@example.com", ""], 1),
        (["x", "y", "x"], 2),
    ],
)
def test_duplicate_raises_validation_error(values, index):
    fields = [
        _Field("emails-0", values[0]),
        _Field("emails-1", values[1]),
        _Field("emails-2", values[2]),
    ]
    form = _Form("emails", fields)

    validator = NoDuplicates()

    with pytest.raises(ValidationError) as error:
        validator(form, fields[index])

    assert str(error.value) == "Duplicate email entered"
    assert fields[index].errors == ["Duplicate email entered"]


def test_non_plural_prefix_kept_as_is():
    fields = [
        _Field("code-0", "123"),
        _Field("code-1", "123"),
    ]
    form = _Form("code", fields)

    validator = NoDuplicates()

    with pytest.raises(ValidationError) as error:
        validator(form, fields[1])

    assert str(error.value) == "Duplicate code entered"
