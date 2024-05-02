import pytest

from app.main.forms import CartesianCoordinatesForm, DecimalCoordinatesForm


def check_coordinate_exists(form):
    form.form_errors.append("Invalid coordinates.")


@pytest.mark.parametrize(
    "post_data, expected_error",
    (
        (
            [91, 181, 2],
            {
                "first_coordinate": ["Enter a Latitude between -90 and 90."],
                "second_coordinate": ["Enter a Longitude between -180 and 180."],
            },
        ),
        (
            [-91, -181, 2],
            {
                "first_coordinate": ["Enter a Latitude between -90 and 90."],
                "second_coordinate": ["Enter a Longitude between -180 and 180."],
            },
        ),
        (
            [90, 180, 0],
            {"radius": ["Enter a radius."]},
        ),
        (
            [90, 180, 0.05],
            {"radius": ["Enter a radius between 0.1km and 38.0km."]},
        ),
        (
            [90, 180, 2.555],
            {"radius": ["Enter a value with 2 decimal places"]},
        ),
    ),
)
def test_invalid_input_messages_for_decimal_coordinates(post_data, expected_error):
    form = DecimalCoordinatesForm(first_coordinate=post_data[0], second_coordinate=post_data[1], radius=post_data[2])
    assert not form.validate()
    assert form.errors == expected_error


@pytest.mark.parametrize(
    "post_data, expected_error",
    (
        (
            [480000, 2, 0],
            {"radius": ["Enter a radius."]},
        ),
        (
            [480000, 2, 0.05],
            {"radius": ["Enter a radius between 0.1km and 38.0km."]},
        ),
        (
            [480000, 2, 2.555],
            {"radius": ["Enter a value with 2 decimal places"]},
        ),
    ),
)
def test_invalid_input_messages_for_cartesian_coordinates(post_data, expected_error):
    form = CartesianCoordinatesForm(first_coordinate=post_data[0], second_coordinate=post_data[1], radius=post_data[2])
    assert not form.validate()
    assert form.errors == expected_error


def test_non_UK_decimal_coordinates_message():
    form = DecimalCoordinatesForm(first_coordinate=80, second_coordinate=80, radius=2)
    check_coordinate_exists(form)
    assert form.validate()
    assert not form.post_validate()


def test_non_UK_cartesian_coordinates_message():
    form = CartesianCoordinatesForm(first_coordinate=300000, second_coordinate=2, radius=2)
    check_coordinate_exists(form)
    assert form.validate()
    assert not form.post_validate()
