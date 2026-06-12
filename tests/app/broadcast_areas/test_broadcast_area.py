from math import isclose

import pytest

from app.broadcast_areas.models import (
    BroadcastAreasRepository,
    broadcast_area_libraries,
)
from app.broadcast_areas.populations import (
    estimate_number_of_smartphones_for_population,
)


def close_enough(a, b):
    return isclose(a, b, rel_tol=0.001)  # Within 0.1% difference


def test_loads_libraries():
    assert [(library.id, library.name, library.is_group) for library in sorted(broadcast_area_libraries)] == [
        (
            "coordinates",
            "Coordinates",
            False,
        ),
        (
            "ctry19",
            "Countries",
            False,
        ),
        ("Flood_Warning_Target_Areas", "Flood Warning Target Areas", False),
        (
            "wd25-lad25-ctyua25",
            "Local authorities",
            True,
        ),
        (
            "postcodes",
            "Postcode areas",
            False,
        ),
        (
            "REPPIR_DEPZ_sites",
            "REPPIR DEPZ sites",
            False,
        ),
        (
            "test",
            "Test areas",
            False,
        ),
    ]


def test_loads_areas_from_library():
    assert [(area.id, area.name) for area in sorted(broadcast_area_libraries.get("ctry19"))] == [
        ("ctry19-E92000001", "England"),
        ("ctry19-N92000002", "Northern Ireland"),
        ("ctry19-S92000003", "Scotland"),
        ("ctry19-W92000004", "Wales"),
    ]


def test_examples():
    countries = broadcast_area_libraries.get("ctry19").get_examples()
    assert countries == "England, Northern Ireland, Scotland and Wales"

    wards = broadcast_area_libraries.get("wd25-lad25-ctyua25").get_examples()
    assert wards == "Aberdeen City, Aberdeenshire, Adur and 379 more…"


@pytest.mark.parametrize(
    "id",
    (
        "ctry19-E92000001",
        "ctry19-N92000002",
        "ctry19-S92000003",
        "ctry19-W92000004",
        pytest.param("mercia", marks=pytest.mark.xfail(raises=KeyError)),
    ),
)
def test_loads_areas_from_libraries(id):
    assert (broadcast_area_libraries.get("ctry19").get(id)) == (broadcast_area_libraries.get_areas([id])[0])


def test_get_names_of_areas():
    areas = broadcast_area_libraries.get_areas(
        [
            "ctry19-W92000004",
            "lad25-W06000014",
            "ctry19-E92000001",
        ]
    )
    assert [area.name for area in sorted(areas)] == [
        "England",
        "Vale of Glamorgan",
        "Wales",
    ]


def test_has_polygons():
    england = broadcast_area_libraries.get_areas(["ctry19-E92000001"])[0]
    scotland = broadcast_area_libraries.get_areas(["ctry19-S92000003"])[0]

    assert len(england.polygons) == 35
    assert len(scotland.polygons) == 195

    assert england.polygons.as_coordinate_pairs_lat_long[0][0] == [
        55.81108,
        -2.03436,  # https://goo.gl/maps/HMFHGogohXdh9ggo8
    ]


def test_polygons_are_enclosed():
    england = broadcast_area_libraries.get("ctry19").get("ctry19-E92000001")

    first_polygon = england.polygons.as_coordinate_pairs_lat_long[0]
    assert first_polygon[0] != first_polygon[1] != first_polygon[2]
    assert first_polygon[0] == first_polygon[-1]


def test_lat_long_order():
    england = broadcast_area_libraries.get_areas(["ctry19-E92000001"])[0]

    lat_long = england.polygons.as_coordinate_pairs_lat_long
    long_lat = england.polygons.as_coordinate_pairs_long_lat

    assert len(lat_long[0]) == len(long_lat[0]) == 2082  # Coordinates in polygon
    assert len(lat_long[0][0]) == len(long_lat[0][0]) == 2  # Axes in coordinates
    assert lat_long[0][0] == list(reversed(long_lat[0][0]))


def test_includes_electoral_wards():
    areas = broadcast_area_libraries.get_areas(["wd25-E05009289"])
    assert len(areas) == 1


def test_electoral_wards_are_groupable_cardiff():
    areas = broadcast_area_libraries.get_areas(["lad25-W06000015"])
    assert len(areas) == 1
    cardiff = areas[0]
    assert len(cardiff.sub_areas) == 28


def test_electoral_wards_are_groupable_ealing():
    areas = broadcast_area_libraries.get_areas(["lad25-E09000009"])
    assert len(areas) == 1
    ealing = areas[0]
    assert len(ealing.sub_areas) == 24


def test_repository_has_all_libraries():
    repo = BroadcastAreasRepository()
    libraries = repo.get_libraries()

    assert len(libraries) == 6
    assert [
        ("Flood Warning Target Areas", "Flood Warning Target Area"),
        ("REPPIR DEPZ sites", "REPPIR DEPZ site"),
        ("Countries", "country"),
        ("Postcode areas", "postcode area"),
        ("Test areas", "test area"),
        ("Local authorities", "local authority"),
    ] == [(name, name_singular) for _, name, name_singular, _is_group in libraries]


@pytest.mark.parametrize(
    "population, expected_estimate",
    (
        # Upper and lower bounds of each age range
        (
            [(0, 100)],
            50,
        ),
        ([(16, 100)], 100),
        (
            [(24, 100)],
            100,
        ),
        (
            [(25, 100)],
            97,
        ),
        (
            [(34, 100)],
            97,
        ),
        ([(35, 100)], 91),
        (
            [(44, 100)],
            91,
        ),
        ([(45, 100)], 88),
        (
            [(54, 100)],
            88,
        ),
        ([(55, 100)], 73),
        (
            [(64, 100)],
            73,
        ),
        ([(65, 100)], 40),
        (
            [(999, 100)],
            40,
        ),
        # Multiple different ages in a single popualtion
        ([(16, 100), (54, 100)], 188),
        ([(1, 1000), (66, 100)], 540),
    ),
)
def test_estimate_number_of_smartphones_for_population(
    population,
    expected_estimate,
):
    assert estimate_number_of_smartphones_for_population(population) == expected_estimate


@pytest.mark.parametrize(
    "area, count_of_phones, expected_phones_per_square_mile",
    (
        (
            # Islington (most dense in UK)
            "lad25-E09000019",
            188563.04338646453,
            31_296,
        ),
        (
            # Cordwainer Ward (City of London)
            # This is higher than Islington because we inflate the
            # popualtion to account for daytime workers
            "wd25-E05009300",
            0,
            392_753,
        ),
        (
            # Crewe East
            "wd25-E05008621",
            13135.044539755492,
            3_865,
        ),
        (
            # Derringham (East Yorkshire)
            "wd25-E05011530",
            8941.705074095897,
            9_363,
        ),
        (
            # Highland (least dense in UK)
            "lad25-S12000017",
            170606.22907047928,
            14.4,
        ),
    ),
)
def test_phone_density(area, expected_phones_per_square_mile, count_of_phones, mocker):
    mocker.patch("app.broadcast_message_api_client.get_count_of_phones", return_value=count_of_phones)
    assert close_enough(
        broadcast_area_libraries.get_areas([area])[0].phone_density,
        expected_phones_per_square_mile,
    )


@pytest.mark.parametrize(
    "area, count_of_phones, expected_bleed_in_m",
    (
        (
            # Islington (most dense in UK)
            "lad25-E09000019",
            188563.04338646453,
            500,
        ),
        (
            # Cordwainer Ward (City of London)
            # Special case because of inflated daytime population
            "wd25-E05009300",
            11619.627517184586,
            500,
        ),
        (
            # Crewe East
            "wd25-E05008621",
            13135.044539755492,
            1_416,
        ),
        (
            # Ramsbottom
            "wd25-E05014163",
            8955.83823065393,
            1_882,
        ),
        (
            # Highland (least dense in UK)
            "lad25-S12000017",
            170606.22907047928,
            4_452,
        ),
        (
            # No population data available
            "test-santa-claus-village-rovaniemi-a",
            0,
            1_500,
        ),
        (
            # No population data available
            "REPPIR_DEPZ_sites-awe_aldermaston",
            3492.7064930129995,
            2_595,
        ),
        (
            # No population data available
            "Flood_Warning_Target_Areas-011FWBWH",
            94.55460828006048,
            1_632,
        ),
    ),
)
def test_estimated_bleed(area, expected_bleed_in_m, count_of_phones, mocker):
    mocker.patch("app.broadcast_message_api_client.get_count_of_phones", return_value=count_of_phones)
    assert close_enough(
        broadcast_area_libraries.get_areas([area])[0].estimated_bleed_in_m,
        expected_bleed_in_m,
    )
