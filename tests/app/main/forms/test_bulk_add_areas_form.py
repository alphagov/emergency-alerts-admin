import pytest

from app.main.forms import FloodWarningBulkAreasForm, LocalAuthorityBulkAreasForm

library_ids = [
    "Flood_Warning_Target_Areas-011FWBWH",
    "Flood_Warning_Target_Areas-011FWCN1A",
    "Flood_Warning_Target_Areas-011FWCN1B",
    "Flood_Warning_Target_Areas-011FWCN2A",
]

library_areas_lookup_dict = {
    "adur": "lad25-E07000223",
    "arun": "lad25-E07000224",
    "chichester": "lad25-E07000225",
    "crawley": "lad25-E07000226",
    "horsham": "lad25-E07000227",
    "mid sussex": "lad25-E07000228",
    "worthing": "lad25-E07000229",
    "bromsgrove": "lad25-E07000234",
}


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
def test_invalid_input_messages_for_flood_warning_areas_form(post_data, expected_field_error, expected_form_error):
    form = FloodWarningBulkAreasForm(library_ids=library_ids, areas=post_data)
    assert not form.validate()
    assert form.areas.errors == expected_field_error
    assert form.form_errors == expected_form_error


def test_valid_input_for_flood_warning_areas_form():
    form = FloodWarningBulkAreasForm(library_ids=library_ids, areas="011FWCN1A")
    assert form.validate()


@pytest.mark.parametrize(
    "post_data, expected_field_error, expected_form_error",
    (
        (
            "",
            ["This field is required"],
            ["Enter at least 1 local authority"],
        ),
        (
            "Adu\nAdur",
            ["Local authority 'Adu' not found"],
            ["Local authority not found"],
        ),
        (
            "Adur\nAdur",
            ["Local authority 'Adur' currently appears in the list more than once"],
            ["All local authorities must be unique"],
        ),
        (
            "Adu",
            ["Local authority 'Adu' not found"],
            ["Local authority not found"],
        ),
    ),
)
def test_invalid_input_messages_for_local_authority_areas_form(post_data, expected_field_error, expected_form_error):
    form = LocalAuthorityBulkAreasForm(library_ids=library_areas_lookup_dict, areas=post_data)
    assert not form.validate()
    assert form.areas.errors == expected_field_error
    assert form.form_errors == expected_form_error


def test_valid_input_for_local_authority_areas_form():
    form = LocalAuthorityBulkAreasForm(library_ids=library_areas_lookup_dict, areas="adur")
    assert form.validate()
