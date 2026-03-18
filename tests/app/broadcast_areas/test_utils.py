import pytest

from app.broadcast_areas.models import BroadcastAreaLibraries
from app.broadcast_areas.utils import (
    aggregate_areas,
    create_areas_dict,
    get_polygons_from_areas,
)
from app.models.broadcast_message import BroadcastMessage
from tests import broadcast_message_json
from tests.app.broadcast_areas.custom_polygons import (
    ABERDEEN_CITY,
    BRISTOL,
    BURFORD,
    CHELTENHAM,
    CHELTENHAM_AND_GLOUCESTER,
    MULTIPLE_ENGLAND,
    SANTA_A,
    SEVERN_ESTUARY,
    SKYE,
)


@pytest.mark.parametrize(
    ("area_ids", "expected_area_names"),
    [
        (
            [
                "wd23-E05009336",  # Whitechapel, Tower Hamlets (electoral ward)
                "wd23-E05009372",  # Hackney Central, Hackney (electoral ward)
                "wd23-E05009374",  # Hackney Wick, Hackney (electoral ward)
            ],
            [
                "Hackney",  # in Greater London* (DB doesn't know this)
                "Tower Hamlets",  # in Greater London*
            ],
        ),
        (
            [
                "wd23-E05004294",  # Hester’s Way, Cheltenham (electoral ward)
                "wd23-E05010981",  # Painswick & Upton, Stroud (electoral ward)
            ],
            [
                "Cheltenham",  # in Gloucestershire (upper tier authority)
                "Stroud",  # in Gloucestershire
            ],
        ),
        (
            [
                "wd23-E05004294",  # Hester’s Way, Cheltenham (electoral ward)
                "wd23-E05009372",  # Hackney Central (electoral ward)
            ],
            [
                "Cheltenham",  # in Gloucestershire (upper tier authority)
                "Hackney",  # in Greater London* (DB doesn't know this)
            ],
        ),
        (
            [
                "wd23-E05004294",  # Hester’s Way, Cheltenham (electoral ward)
                "wd23-E05010981",  # Painswick & Upton, Stroud (electoral ward)
                "wd23-E05009372",  # Hackney Central, Hackney (electoral ward)
            ],
            [
                "Gloucestershire",  # upper tier authority
                "Hackney",  # in Greater London* (DB doesn't know this)
            ],
        ),
        (
            [
                "lad23-E07000037",  # High Peak (lower tier authority)
            ],
            [
                "High Peak",  # in Derbyshire (upper tier authority)
            ],
        ),
        (
            [
                "lad23-E07000037",  # High Peak (lower tier authority)
                "lad23-E07000035",  # Derbyshire Dales (lower tier authority)
            ],
            [
                "Derbyshire Dales",  # in Derbyshire (upper tier authority)
                "High Peak",  # in Derbyshire
            ],
        ),
        (
            [
                "lad23-E07000037",  # High Peak (lower tier authority)
                "lad23-E07000035",  # Derbyshire Dales (lower tier authority)
                "ctyua23-E10000028",  # Staffordshire (upper tier authority)
            ],
            [
                "Derbyshire",  # upper tier authority
                "Staffordshire",
            ],
        ),
        (
            [
                "ctry19-E92000001",  # England
            ],
            [
                "England",
            ],
        ),
    ],
)
def test_aggregate_areas(
    area_ids,
    expected_area_names,
):
    broadcast_message = BroadcastMessage(broadcast_message_json(area_ids=area_ids))

    assert [area.name for area in aggregate_areas(broadcast_message.areas)] == expected_area_names


@pytest.mark.parametrize(
    ("simple_polygons", "expected_area_names"),
    [
        (
            [SKYE],
            [
                # Area covers a single unitary authority
                "Highland",
            ],
        ),
        (
            [BRISTOL],
            [
                # Area covers a single unitary authority
                "Bristol, City of",
            ],
        ),
        (
            [SEVERN_ESTUARY],
            [
                # Area covers various lower-tier authorities
                # with more than three in Gloucestershire so
                # we aggregate them into that
                "Bristol, City of",
                "Gloucestershire",
                "Monmouthshire",
                "Newport",
                "North Somerset",
                "South Gloucestershire",
            ],
        ),
        (
            [CHELTENHAM],
            [
                # Area covers three lower-tier authorities
                # in Gloucestershire (upper tier authority)
                "Cheltenham",
                "Cotswold",
                "Tewkesbury",
            ],
        ),
        (
            [CHELTENHAM_AND_GLOUCESTER],
            [
                # Area covers more than 3 lower-tier authorities
                # in Gloucestershire so we aggregate them
                "Gloucestershire",
            ],
        ),
        (
            [BURFORD],
            [
                # Area covers one lower-tier authority in
                # Gloucestershire and one in Oxfordshire (both
                # upper tier authorities)
                "Cotswold",
                "West Oxfordshire",
            ],
        ),
        (
            [CHELTENHAM_AND_GLOUCESTER, BURFORD],
            [
                # Area covers many lower-tier authorities
                # in Gloucestershire but only one in Oxfordshire
                "Gloucestershire",
                "West Oxfordshire",
            ],
        ),
        (
            [SANTA_A],
            [
                # Does not overlap with the UK
            ],
        ),
    ],
)
def test_aggregate_areas_for_custom_polygons(
    simple_polygons,
    expected_area_names,
):
    broadcast_message = BroadcastMessage(
        broadcast_message_json(
            areas={"names": [f"polygon {i}" for i, _ in enumerate(simple_polygons)], "simple_polygons": simple_polygons}
        )
    )

    assert [area.name for area in aggregate_areas(broadcast_message.areas)] == expected_area_names


@pytest.mark.parametrize(
    ("area_ids", "expected_dict"),
    [
        (
            ["ctry19-E92000001"],
            {
                "aggregate_names": ["England"],
                "ids": ["ctry19-E92000001"],
                "names": ["England"],
                "simple_polygons": MULTIPLE_ENGLAND,
            },
        ),
        (
            ["lad23-S12000033"],
            {
                "aggregate_names": ["Aberdeen City"],
                "ids": ["lad23-S12000033"],
                "names": ["Aberdeen City"],
                "simple_polygons": [ABERDEEN_CITY],
            },
        ),
        ([], {"aggregate_names": [], "ids": [], "names": [], "simple_polygons": []}),
    ],
)
def test_create_areas_dict(area_ids, expected_dict):
    areas = BroadcastAreaLibraries().get_areas(area_ids)
    created_dict = create_areas_dict(areas)
    assert created_dict == expected_dict


@pytest.mark.parametrize(
    ("area_ids", "area_attribute", "expected_polygons"),
    [
        (["ctry19-E92000001"], "simple_polygons", MULTIPLE_ENGLAND),
        (["lad23-S12000033"], "simple_polygons", [ABERDEEN_CITY]),
        ([], "simple_polygons", []),
        (["nonexistent_area_id"], "simple_polygons", []),
    ],
)
def test_get_polygons_from_areas(area_ids, area_attribute, expected_polygons):
    areas = BroadcastAreaLibraries().get_areas(area_ids)
    assert get_polygons_from_areas(areas, area_attribute).as_coordinate_pairs_lat_long == expected_polygons
