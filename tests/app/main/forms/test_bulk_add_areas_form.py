import pytest

from app.main.forms import FloodWarningBulkAreasForm

library_ids = [
    "Flood_Warning_Target_Areas-011FWBWH",
    "Flood_Warning_Target_Areas-011FWCN1A",
    "Flood_Warning_Target_Areas-011FWCN1B",
    "Flood_Warning_Target_Areas-011FWCN2A",
]


@pytest.mark.parametrize(
    "post_data, expected_field_error, expected_form_error",
    (
        (
            "",
            ["This field is required"],
            ["Enter at least 1 Flood Warning TA code"],
        ),
        (
            "011FWBWH,011FWBWH",
            ["Flood Warning TA code '011FWBWH' currently appears in the list more than once"],
            ["All Flood Warning TA codes must be unique"],
        ),
        (
            "011FWBW",
            ["Flood Warning TA code '011FWBW' not found"],
            ["Flood Warning TA code not found"],
        ),
    ),
)
def test_invalid_input_messages(post_data, expected_field_error, expected_form_error):
    form = FloodWarningBulkAreasForm(library_ids=library_ids, areas=post_data)
    assert not form.validate()
    assert form.areas.errors == expected_field_error
    assert form.form_errors == expected_form_error


def test_valid_input():
    form = FloodWarningBulkAreasForm(library_ids=library_ids, areas="011FWCN1A")
    assert form.validate()
