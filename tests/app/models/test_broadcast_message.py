import pytest

from app.broadcast_areas.models import CustomBroadcastAreas
from app.models.broadcast_message import BroadcastMessage
from tests import broadcast_message_json
from tests.app.broadcast_areas.custom_polygons import (
    BD1_1EE_1,
    MULTIPLE_ENGLAND,
    custom_essex_bleed_area,
)


@pytest.mark.parametrize(
    "areas, expected_area_ids", [({"simple_polygons": []}, []), ({"ids": ["123"], "simple_polygons": []}, ["123"])]
)
def test_area_ids(
    areas,
    expected_area_ids,
):
    broadcast_message = BroadcastMessage(broadcast_message_json(areas=areas))

    assert broadcast_message.area_ids == expected_area_ids


def test_simple_polygons():
    broadcast_message = BroadcastMessage(
        broadcast_message_json(
            area_ids=[
                # Hackney Central
                "wd23-E05009372",
                # Hackney Wick
                "wd23-E05009374",
            ],
        )
    )

    assert [
        [len(polygon) for polygon in broadcast_message.polygons.as_coordinate_pairs_lat_long],
        [len(polygon) for polygon in broadcast_message.simple_polygons.as_coordinate_pairs_lat_long],
    ] == [
        # One polygon for each area
        [27, 31],
        # Because the areas are close to each other, the simplification
        # and unioning process results in a single polygon with fewer
        # total coordinates
        [57],
    ]


def test_content_comes_from_attribute_not_template():
    broadcast_message = BroadcastMessage(broadcast_message_json())
    assert broadcast_message.content == "This is a test"


@pytest.mark.parametrize(
    ("areas", "expected_length"),
    [
        ({"ids": []}, 0),
        ({"ids": ["wd23-E05009372"]}, 1),
        ({"no data": "just created"}, 0),
        ({"names": ["somewhere"], "simple_polygons": [[[3.5, 1.5]]]}, 1),
    ],
)
def test_areas(areas, expected_length):
    broadcast_message = BroadcastMessage(broadcast_message_json(areas=areas))

    assert len(list(broadcast_message.areas)) == expected_length


def test_areas_treats_missing_ids_as_custom_broadcast(notify_admin):
    broadcast_message = BroadcastMessage(
        broadcast_message_json(
            areas={
                "ids": [
                    "wd20-E05009372",
                    "something else",
                ],
                # although the IDs may no longer be usable, we can
                # expect the broadcast to have names and polygons,
                # which is enough to show the user something
                "names": ["wd20 name", "something else name"],
                "simple_polygons": [[[1, 2]]],
            }
        )
    )

    assert len(list(broadcast_message.areas)) == 2
    assert type(broadcast_message.areas) is CustomBroadcastAreas


def test_broadcast_message_bleed_phones_is_not_less_than_base_estimate(notify_admin):
    broadcast_message = BroadcastMessage(
        broadcast_message_json(
            areas={
                "ids": [
                    "ctyua23-E10000012",
                ],
                "names": ["Essex"],
                "simple_polygons": [custom_essex_bleed_area],
            }
        )
    )

    assert broadcast_message.count_of_phones_likely >= broadcast_message.count_of_phones


@pytest.mark.parametrize(
    "area_ids, approx_bounds",
    (
        (
            [
                "ctry19-N92000002",  # Northern Ireland (UTM zone 29N)
                "ctry19-W92000004",  # Wales (UTM zone 30N)
            ],
            [-8.2, 51.5, -2.1, 55.1],
        ),
        (
            [
                "lad23-E06000031",  # Peterborough (UTM zone 30N)
                "lad23-E07000146",  # Kings Lyn and West Norfolk (UTM zone 31N)
            ],
            [-0.5, 52.5, 0.8, 53.0],
        ),
        (
            [
                "wd23-E05009372",  # Hackney Central (UTM zone 30N)
                "wd23-E05009374",  # Hackney Wick (UTM zone 30N)
            ],
            [-0.1, 51.5, -0.0, 51.6],
        ),
        (
            [
                "wd23-E05009372",  # Hackney Central (UTM zone 30N)
                "test-santa-claus-village-rovaniemi-a",  # (UTM zone 35N)
            ],
            [-0.1, 51.5, 25.9, 66.6],
        ),
    ),
)
def test_combining_multiple_areas_keeps_same_bounds(area_ids, approx_bounds):
    broadcast_message = BroadcastMessage(broadcast_message_json(areas={"ids": area_ids}))

    assert (
        [round(coordinate, 1) for coordinate in broadcast_message.polygons.bounds]
        == [round(coordinate, 1) for coordinate in broadcast_message.simple_polygons.bounds]
        == (approx_bounds)
    )


def test_create_from_area(mocker, service_one, fake_uuid, mock_create_broadcast_message):
    # Asserts that once create_from_area class method called, the mocked API
    # client method (broadcast_message_api_client.create_broadcast_message) is called
    # with expected arguments
    BroadcastMessage.create_from_area(
        service_id=service_one,
        area_ids=["ctry19-E92000001"],
        template_id="template_id",
        content="Test content",
        reference="Test Reference",
    )
    mock_create_broadcast_message.assert_called_once_with(
        service_id=service_one,
        reference="Test Reference",
        content="Test content",
        areas={
            "ids": ["ctry19-E92000001"],
            "simple_polygons": MULTIPLE_ENGLAND,
            "names": ["England"],
            "aggregate_names": ["England"],
        },
        template_id="template_id",
    )


def test_create_from_custom_area(mocker, service_one, fake_uuid, mock_create_broadcast_message):
    # Asserts that once class method create_from_custom_area called, the mocked API
    # client method (broadcast_message_api_client.create_broadcast_message) is called
    # with expected arguments
    custom_area = CustomBroadcastAreas(names=["1km around the postcode BD1 1EE in Bradford"], polygons=[BD1_1EE_1])
    BroadcastMessage.create_from_custom_area(
        service_id=service_one,
        areas=custom_area,
        template_id="template_id",
        content="Test content",
        reference="Test Reference",
    )
    mock_create_broadcast_message.assert_called_once_with(
        service_id=service_one,
        reference="Test Reference",
        content="Test content",
        areas={
            "ids": ["1km around the postcode BD1 1EE in Bradford"],
            "simple_polygons": [BD1_1EE_1],
            "names": ["1km around the postcode BD1 1EE in Bradford"],
            "aggregate_names": ["1km around the postcode BD1 1EE in Bradford"],
        },
        template_id="template_id",
    )


def test_invalid_area_returns_is_valid_False():
    invalid_polygon = [[51.5310, -0.1580], [51.5310, -0.1570], [51.5310, -0.1580], [51.5310, -0.2]]
    custom_areas = CustomBroadcastAreas(names="invalid area", polygons=[invalid_polygon])
    assert custom_areas.is_valid_area() is False


def test_create_from_content(mocker, service_one, fake_uuid, mock_create_broadcast_message):
    # Asserts that once class method create_from_content called, the mocked API
    # client method (broadcast_message_api_client.create_broadcast_message) is called
    # with expected arguments
    BroadcastMessage.create_from_content(
        service_id=service_one,
        content="Test content",
        reference="Test Reference",
    )
    mock_create_broadcast_message.assert_called_once_with(
        service_id=service_one, reference="Test Reference", content="Test content", template_id=None
    )


def test_update_from_content(mocker, service_one, fake_uuid, mock_update_broadcast_message):
    # Asserts that once class method update_from_content called, the mocked API
    # client method (broadcast_message_api_client.update_broadcast_message) is called
    # with expected arguments
    BroadcastMessage.update_from_content(
        service_id=service_one,
        message_id=fake_uuid,
        content="Updated content",
        reference="Test reference",
    )
    mock_update_broadcast_message.assert_called_once_with(
        service_id=service_one,
        broadcast_message_id=fake_uuid,
        data={
            "reference": "Test reference",
            "content": "Updated content",
        },
    )
