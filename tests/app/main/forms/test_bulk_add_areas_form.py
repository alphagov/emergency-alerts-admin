import pytest

from app.main.forms import FloodWarningBulkAreasForm, LocalAuthorityBulkAreasForm

# FloodWarningBulkAreasForm & LocalAuthorityBulkAreasForm validation has moved to API,
# where error response is returned and displayed in Admin UI if posted input is invalid


@pytest.mark.parametrize(
    "post_data, expected_field_error, expected_form_error",
    (
        (
            "",
            ["This field is required"],
            ["Enter at least 1 Flood Warning TA code"],
        ),
    ),
)
def test_invalid_input_messages_for_flood_warning_areas_form(post_data, expected_field_error, expected_form_error):
    form = FloodWarningBulkAreasForm(areas=post_data)
    assert not form.validate()
    assert form.areas.errors == expected_field_error
    assert form.form_errors == expected_form_error


def test_valid_input_for_flood_warning_areas_form():
    form = FloodWarningBulkAreasForm(areas="Test Area")
    assert form.validate()


@pytest.mark.parametrize(
    "post_data, expected_field_error, expected_form_error",
    (
        (
            "",
            ["This field is required"],
            ["Enter at least 1 Local authority"],
        ),
    ),
)
def test_invalid_input_messages_for_local_authority_areas_form(post_data, expected_field_error, expected_form_error):
    form = LocalAuthorityBulkAreasForm(areas=post_data)
    assert not form.validate()
    assert form.areas.errors == expected_field_error
    assert form.form_errors == expected_form_error


def test_valid_input_for_local_authority_areas_form():
    form = LocalAuthorityBulkAreasForm(areas="Test Area")
    assert form.validate()
