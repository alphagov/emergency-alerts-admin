import pytest

from app.main.forms import PostcodeForm


def check_postcode_exists(form):
    form.form_errors.append("Postcode not found. Enter a valid postcode.")


@pytest.mark.parametrize(
    "post_data, expected_error",
    (
        (
            ["", "2"],
            {"postcode": ["Enter a valid postcode."]},
        ),
        (
            ["BD1 1EE", ""],
            {"radius": ["Enter a valid radius."]},
        ),
        (
            ["", ""],
            {"postcode": ["Enter a valid postcode."], "radius": ["Enter a valid radius."]},
        ),
    ),
)
def test_invalid_input_messages(post_data, expected_error):
    form = PostcodeForm(postcode=post_data[0], radius=post_data[1])
    assert not form.validate()
    assert form.errors == expected_error


def test_nonexistent_postcode_message():
    form = PostcodeForm(postcode="TEST", radius="2")
    check_postcode_exists(form)
    assert form.validate()
    assert not form.post_validate()
