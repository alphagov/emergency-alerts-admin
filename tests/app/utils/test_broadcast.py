import pytest

from app.main.forms import (
    EastingNorthingCoordinatesForm,
    LatitudeLongitudeCoordinatesForm,
    PostcodeForm,
)
from app.utils.broadcast import (
    adding_invalid_coords_errors_to_form,
    create_postcode_db_id,
    format_area_name,
    format_areas_list,
    format_areas_list_with_parent,
    parse_coordinate_form_data,
)
from tests import MockArea


@pytest.mark.parametrize(
    "postcode",
    ["RG12 8SN", "BD1 1EE", "AB10 1AL"],
)
def test_create_postcode_db_id(postcode):
    form = PostcodeForm()
    form.postcode.data = postcode
    form.radius.data = 5
    assert create_postcode_db_id(form) == postcode


@pytest.mark.parametrize(
    "coordinate_type, first_coordinate, second_coordinate, radius",
    [
        ("latitude_longitude", 54, -2, 10),
        ("latitude_longitude", 54, -2, 12),
        ("easting_northing", 530111, 170000, 12),
        ("easting_northing", 530111, 179963, 1),
        ("easting_northing", 0, 0, 0),
    ],
)
def test_parse_coordinate_form_data(coordinate_type, first_coordinate, second_coordinate, radius):
    if coordinate_type == "latitude_longitude":
        form = LatitudeLongitudeCoordinatesForm()
        form.first_coordinate.data = first_coordinate
        form.second_coordinate.data = second_coordinate
        form.radius.data = radius
    elif coordinate_type == "easting_northing":
        form = EastingNorthingCoordinatesForm()
        form.first_coordinate.data = first_coordinate
        form.second_coordinate.data = second_coordinate
        form.radius.data = radius
    assert parse_coordinate_form_data(form) == (float(first_coordinate), float(second_coordinate), float(radius))


def test_adding_invalid_coords_errors_to_form():
    adding_invalid_coords_errors_to_form("latitude_longitude", LatitudeLongitudeCoordinatesForm())
    assert not LatitudeLongitudeCoordinatesForm().validate_on_submit()
    adding_invalid_coords_errors_to_form("easting_northing", EastingNorthingCoordinatesForm())
    assert not EastingNorthingCoordinatesForm().validate_on_submit()


@pytest.mark.parametrize(
    "area_name, expected_output",
    [
        ("Manchester, City of", "City of Manchester"),
        ("Yorkshire, County of", "County of Yorkshire"),
        ("London", "London"),
        ("Lancaster, City of", "City of Lancaster"),
        ("Oxfordshire, County of", "County of Oxfordshire"),
    ],
)
def test_format_area_name(area_name, expected_output):
    assert format_area_name(area_name) == expected_output


def test_format_areas_list_multiple_areas():
    areas = [
        MockArea({"name": "Manchester, City of"}),
        MockArea({"name": "Yorkshire, County of"}),
    ]

    assert format_areas_list(areas) == [
        "City of Manchester",
        "County of Yorkshire",
    ]


def test_format_areas_list_regular_list():
    areas = [
        "London",
        "Lancaster, City of",
        "Oxfordshire, County of",
    ]

    assert format_areas_list(areas) == [
        "London",
        "City of Lancaster",
        "County of Oxfordshire",
    ]


def test_format_areas_list_with_parent_regular_list():
    areas = [
        "London",
        "Lancaster, City of",
        "Oxfordshire, County of",
    ]

    assert format_areas_list_with_parent(areas) == [
        "London",
        "City of Lancaster",
        "County of Oxfordshire",
    ]


def test_format_areas_list_with_parent_electoral_ward():
    parent = MockArea({"name": "Bristol West"})
    ward = MockArea(
        {
            "name": "Clifton",
            "parent": parent,
        }
    )
    ward.is_electoral_ward = True

    assert format_areas_list_with_parent([ward]) == [
        "Bristol West -> Clifton",
    ]


def test_format_areas_list_with_parent_mixed_list():
    parent = MockArea({"name": "Bristol West"})
    ward = MockArea(
        {
            "name": "Clifton",
            "parent": parent,
        }
    )
    ward.is_electoral_ward = True

    non_ward = MockArea({"name": "Somerset"})

    assert format_areas_list_with_parent(
        [
            "London",
            ward,
            non_ward,
        ]
    ) == [
        "London",
        "Bristol West -> Clifton",
        "Somerset",
    ]


def test_format_areas_list_with_parent_missing_is_electoral_ward_attribute():
    area = MockArea({"name": "Somerset"})

    assert format_areas_list_with_parent([area]) == ["Somerset"]
