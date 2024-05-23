import pytest

from app.main.forms import PostcodeForm


def check_postcode_exists(form):
    form.form_errors.append("Enter a postcode within the UK")


def no_local_authority_found(form):
    form.postcode.process_errors.append("No local authority found for the postcode entered. Enter a different postcode")


@pytest.mark.parametrize(
    "post_data, expected_error",
    (
        (
            ["", 2],
            {"postcode": ["Enter a postcode within the UK"]},
        ),
        (
            ["BD1 1EE", 0],
            {"radius": ["Enter a radius between 0.1km and 38.0km"]},
        ),
        (
            ["", 0],
            {"postcode": ["Enter a postcode within the UK"], "radius": ["Enter a radius between 0.1km and 38.0km"]},
        ),
        (
            ["BD1 1EE", 38.2],
            {"radius": ["Enter a radius between 0.1km and 38.0km"]},
        ),
        (
            ["BD1 1EE", 0.05],
            {"radius": ["Enter a radius between 0.1km and 38.0km"]},
        ),
        (
            ["", 0.05],
            {"postcode": ["Enter a postcode within the UK"], "radius": ["Enter a radius between 0.1km and 38.0km"]},
        ),
        (
            ["BD1 1EE", 12.345],
            {"radius": ["Enter a value with 2 decimal places"]},
        ),
    ),
)
def test_invalid_input_messages(post_data, expected_error):
    form = PostcodeForm(postcode=post_data[0], radius=post_data[1])
    assert not form.validate()
    assert form.errors == expected_error


def test_nonexistent_postcode_message():
    form = PostcodeForm(postcode="TE10 1TE", radius=2)
    check_postcode_exists(form)
    assert form.validate()
    assert form.errors


def test_no_local_authority_found_error():
    form = PostcodeForm(postcode="TE10 1TE", radius=2)
    no_local_authority_found(form)
    assert not form.validate()
    assert form.errors
