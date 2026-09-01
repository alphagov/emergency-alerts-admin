from math import isclose

import pytest
from emergency_alerts_utils.polygons import Polygons

from app.models.areas import Area
from tests.app.broadcast_areas.custom_polygons import MULTIPLE_ENGLAND
from tests.app.utils.test_broadcast import MockArea


def close_enough(a, b):
    return isclose(a, b, rel_tol=0.001)  # Within 0.1% difference


def test_has_polygons():
    england = MockArea({"name": "England"})
    england.polygons = Polygons(
        polygons=[[[longitude, latitude] for latitude, longitude in polygon] for polygon in MULTIPLE_ENGLAND]
    )

    assert len(england.polygons) == len(MULTIPLE_ENGLAND)

    assert england.polygons.as_coordinate_pairs_lat_long == MULTIPLE_ENGLAND


def test_polygons_are_enclosed():
    england = MockArea({"name": "England"})
    england.polygons = Polygons(
        polygons=[[[longitude, latitude] for latitude, longitude in polygon] for polygon in MULTIPLE_ENGLAND]
    )

    for polygon in england.polygons.as_coordinate_pairs_lat_long:
        assert polygon[0] != polygon[1] != polygon[2]
        assert polygon[0] == polygon[-1]


def test_lat_long_order():
    england = MockArea({"name": "England"})
    england.polygons = Polygons(
        polygons=[[[longitude, latitude] for latitude, longitude in polygon] for polygon in MULTIPLE_ENGLAND]
    )

    lat_long = england.polygons.as_coordinate_pairs_lat_long
    long_lat = england.polygons.as_coordinate_pairs_long_lat

    assert len(lat_long[0]) == len(long_lat[0]) == len(MULTIPLE_ENGLAND[0])  # Polygons in area
    assert len(lat_long[0][0]) == len(long_lat[0][0]) == 2  # Axes in coordinates
    assert lat_long[0][0] == list(reversed(long_lat[0][0]))


@pytest.mark.parametrize(
    ("estimated_area", "count_of_phones", "expected_bleed_in_m"),
    (
        (0, 1_000, 0),  # estimated_area of 0 results in bleed of 0
        (1_000, 0, 0),  # count_of_phones of 0 results in bleed of 0
        (1, 1, 5_000),  # bleed capped at 5_000
        (1, 1_000_000_000, 2_667.5),  # normally calculated result
    ),
)
def test_estimated_bleed(estimated_area, count_of_phones, expected_bleed_in_m):
    area = MockArea({"estimated_area": estimated_area})

    assert close_enough(
        Area.calculate_bleed(area.estimated_area, count_of_phones),
        expected_bleed_in_m,
    )
