import math
from unittest.mock import patch

import pytest
from shapely import Point

from app.main.forms import (
    EastingNorthingCoordinatesForm,
    LatitudeLongitudeCoordinatesForm,
    PostcodeForm,
)
from app.models.broadcast_message import BroadcastMessage
from app.utils.broadcast import (
    adding_invalid_coords_errors_to_form,
    check_coordinates_valid_for_enclosed_polygons,
    create_circle,
    create_coordinate_area,
    create_coordinate_area_slug,
    create_custom_area_polygon,
    create_postcode_area_slug,
    create_postcode_db_id,
    extract_attributes_from_custom_area,
    format_area_name,
    format_areas_list,
    get_centroid,
    get_centroid_if_postcode_in_db,
    normalising_point,
    parse_coordinate_form_data,
)
from tests.app.broadcast_areas.custom_polygons import (
    BD1_1EE_1,
    custom_craven_area,
    custom_westminster_area,
)


@pytest.mark.parametrize(
    "coordinate_type, first_coordinate, second_coordinate, radius",
    [
        ("latitude_longitude", 54, -2, 10),
        ("latitude_longitude", 54, -2, 12),
        ("easting_northing", 530111, 170000, 12),
        ("easting_northing", 530111, 179963, 1),
        ("easting_northing", 341216, 1006204.592, 23),  # EAS-2567: Long values end up as scientific notation
    ],
)
def test_create_coordinate_area_slug(coordinate_type, first_coordinate, second_coordinate, radius):
    if coordinate_type == "latitude_longitude":
        assert (
            create_coordinate_area_slug(coordinate_type, first_coordinate, second_coordinate, radius)
            == f"{radius}km around {first_coordinate} latitude, {second_coordinate} longitude"
        )
    elif coordinate_type == "easting_northing":
        assert (
            create_coordinate_area_slug(coordinate_type, first_coordinate, second_coordinate, radius)
            == f"{radius}km around the easting of {first_coordinate} and the northing of {second_coordinate}"
        )


@pytest.mark.parametrize(
    "coordinate_type, first_coordinate, second_coordinate, radius",
    [("latitude_longitude", 54, -2, 1), ("easting_northing", 530111, 179963, 1)],
)
def test_create_coordinate_area(coordinate_type, first_coordinate, second_coordinate, radius):
    if coordinate_type == "latitude_longitude":
        actual = create_coordinate_area(first_coordinate, second_coordinate, radius, coordinate_type)
        for coords1, coords2 in zip(actual, custom_craven_area):
            assert all(abs(a - b) < math.exp(1e-12) for a, b in zip(coords1, coords2))
    elif coordinate_type == "easting_northing":
        actual = create_coordinate_area(first_coordinate, second_coordinate, radius, coordinate_type)
        for coords1, coords2 in zip(actual, custom_westminster_area):
            assert all(abs(a - b) < math.exp(1e-12) for a, b in zip(coords1, coords2))


@pytest.mark.parametrize(
    "first_coordinate, second_coordinate, expected, coordinate_type",
    [
        (54, -2, True, "latitude_longitude"),
        (57, -3, True, "latitude_longitude"),
        (50.69, -1.23, True, "latitude_longitude"),
        (0, -2, False, "latitude_longitude"),
        (29.79, -3.57, False, "latitude_longitude"),
        (45, -2, False, "easting_northing"),
        (0, 0, False, "easting_northing"),
        (29.79, -3.57, False, "easting_northing"),
        (530111, 179963, True, "easting_northing"),
        (520000, 170000, True, "easting_northing"),
        (540000, 170000, True, "easting_northing"),
    ],
)
def test_check_coordinates_valid_for_enclosed_polygons(first_coordinate, second_coordinate, expected, coordinate_type):
    assert (
        check_coordinates_valid_for_enclosed_polygons(
            BroadcastMessage, first_coordinate, second_coordinate, coordinate_type
        )
    ) == expected


@pytest.mark.parametrize(
    "coordinate_type, first_coordinate, second_coordinate, expected",
    [
        ("latitude_longitude", 54, -2, [-2.0, 54.0]),
        ("easting_northing", 530111, 170000, [-0.13043144039058444, 51.414098034396865]),
    ],
)
def test_normalising_point(coordinate_type, first_coordinate, second_coordinate, expected):
    assert normalising_point(first_coordinate, second_coordinate, coordinate_type).x == expected[0]
    assert normalising_point(first_coordinate, second_coordinate, coordinate_type).y == expected[1]


def test_extract_attributes_from_custom_area():
    expected_attributes = (
        2627.25959347374,
        3134370.3703178177,
        41279574.21508839,
        500,
        4000,
    )
    assert extract_attributes_from_custom_area(custom_craven_area) == pytest.approx(expected_attributes, 1e-12)


@pytest.mark.parametrize(
    "postcode",
    ["RG12 8SN", "BD1 1EE", "AB10 1AL"],
)
def test_create_postcode_db_id(postcode):
    form = PostcodeForm()
    form.postcode.data = postcode
    form.radius.data = 5
    assert create_postcode_db_id(form) == f"postcodes-{postcode}"


def test_create_custom_area_polygon():
    form = PostcodeForm()
    form.postcode.data = "BD1 1EE"
    form.radius.data = 1
    centroid, custom_polygon = create_custom_area_polygon(BroadcastMessage, form, "postcodes-BD1 1EE")
    assert centroid.x == -1.7516431369765788
    assert centroid.y == 53.79363450437661
    for coords1, coords2 in zip(custom_polygon, BD1_1EE_1):
        assert all(abs(a - b) < math.exp(1e-12) for a, b in zip(coords1, coords2))

    centroid, custom_polygon = create_custom_area_polygon(BroadcastMessage, form, "postcodes-BD1 1EP")
    assert centroid is None
    assert custom_polygon is None


@pytest.mark.parametrize(
    "postcode, radius",
    [("RG12 8SN", 2), ("BD1 1EE", 10), ("AB10 1AL", 30)],
)
def test_create_postcode_area_slug(radius, postcode):
    form = PostcodeForm()
    form.postcode.data = postcode
    form.radius.data = radius
    assert create_postcode_area_slug(form) == f"{radius}km around the postcode {postcode}"


@pytest.mark.parametrize(
    "id, expected",
    [
        ("postcodes-BD1 1EE", [-1.7516431369765788, 53.79363450437661]),
        ("ctry19-E92000001", [-1.4660743481578784, 52.59949456672687]),
    ],
)
def test_get_centroid(id, expected):
    area = BroadcastMessage.libraries.get_areas([id])[0]
    assert get_centroid(area).x == expected[0]
    assert get_centroid(area).y == expected[1]


def test_create_circle():
    actual = create_circle(Point(-1.7516431369765788, 53.79363450437661), 1)
    for coords1, coords2 in zip(actual, BD1_1EE_1):
        assert all(abs(a - b) < math.exp(1e-12) for a, b in zip(coords1, coords2))


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
    "postcode, expected_centroid",
    [
        ("postcodes-BD1 1EE", [-1.7516431369765788, 53.79363450437661]),
        ("postcodes-BD1 1EP", None),
    ],
)
def test_get_centroid_if_postcode_in_db(postcode, expected_centroid):
    form = PostcodeForm()
    centroid = get_centroid_if_postcode_in_db(postcode, form)
    if expected_centroid is not None:
        assert centroid.x == expected_centroid[0]
        assert centroid.y == expected_centroid[1]


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


class MockCustomBroadcastArea:
    def __init__(self, name):
        self.name = name


class MockCustomBroadcastAreas:
    def __init__(self, items):
        self.items = items

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)


def test_format_areas_list_single_custom_area():
    with patch("app.utils.broadcast.CustomBroadcastArea", MockCustomBroadcastArea):
        custom_area = MockCustomBroadcastArea("Bristol, City of")
        assert format_areas_list(custom_area) == ["City of Bristol"]


def test_format_areas_list_multiple_areas():
    with patch("app.utils.broadcast.CustomBroadcastAreas", MockCustomBroadcastAreas):
        custom_area1 = "Manchester, City of"
        custom_area2 = "Yorkshire, County of"
        custom_areas_list = MockCustomBroadcastAreas([custom_area1, custom_area2])

        assert format_areas_list(custom_areas_list) == ["City of Manchester", "County of Yorkshire"]


def test_format_areas_list_regular_list():
    areas_list = ["London", "Lancaster, City of", "Oxfordshire, County of"]
    assert format_areas_list(areas_list) == ["London", "City of Lancaster", "County of Oxfordshire"]
