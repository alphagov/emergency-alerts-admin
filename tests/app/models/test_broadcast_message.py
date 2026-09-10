from unittest.mock import patch

import pytest

from app.notify_client.areas_api_client import AreasAPIClient
from tests.app.broadcast_areas.custom_polygons import BRISTOL
from tests.app.utils.test_broadcast import MockArea

with patch.object(AreasAPIClient, "get_libraries", return_value=[]):
    from app.models.broadcast_message import BroadcastMessage

from tests import broadcast_message_json


@pytest.mark.parametrize(
    ("areas", "mock_areas", "expected_area_ids"),
    [
        (
            {"simple_polygons": []},
            [],
            [],
        ),
        (
            {"ids": ["123"], "simple_polygons": []},
            [MockArea({"id": "123", "name": "Test area", "parent": None})],
            ["123"],
        ),
    ],
)
def test_area_ids(areas, mock_areas, expected_area_ids, mocker):
    mocker.patch(
        "app.models.base_broadcast.Areas.get",
        return_value=mock_areas,
    )

    broadcast_message = BroadcastMessage(broadcast_message_json(areas=areas))

    assert broadcast_message.area_ids == expected_area_ids


def test_simple_polygons():
    broadcast_message = BroadcastMessage(
        broadcast_message_json(
            areas={
                "ids": ["bristol"],
                "names": ["Bristol"],
                "simple_polygons": [BRISTOL],
            },
        )
    )

    assert broadcast_message.simple_polygons.as_coordinate_pairs_lat_long == [BRISTOL]


def test_content_comes_from_attribute_not_template():
    broadcast_message = BroadcastMessage(broadcast_message_json())
    assert broadcast_message.content == "This is a test"


@pytest.mark.parametrize(
    ("areas", "mock_areas", "expected_length"),
    [
        ({"ids": []}, [], 0),
        (
            {"ids": ["wd25-E05009372"]},
            [
                MockArea(
                    {
                        "id": "wd25-E05009372",
                        "name": "Hackney Central",
                        "parent": None,
                    }
                )
            ],
            1,
        ),
        ({"no data": "just created"}, [], 0),
        (
            {"ids": ["somewhere"], "simple_polygons": [[[3.5, 1.5]]]},
            [
                MockArea(
                    {
                        "id": "somewhere",
                        "name": "Somewhere",
                        "parent": None,
                    }
                )
            ],
            1,
        ),
    ],
)
def test_areas(areas, mock_areas, expected_length, mocker):
    mocker.patch(
        "app.models.base_broadcast.Areas.get",
        return_value=mock_areas,
    )

    broadcast_message = BroadcastMessage(broadcast_message_json(areas=areas))

    assert len(list(broadcast_message.areas)) == expected_length


def test_create_from_area(mocker, service_one, fake_uuid, mock_create_broadcast_message, mock_get_areas_by_ids):
    # Asserts that once create_from_area class method called, the mocked API
    # client method (broadcast_message_api_client.create_broadcast_message) is called
    # with expected arguments
    mocker.patch(
        "app.models.areas.areas_api_client.get_area_dict",
        return_value={
            "E92000001": {
                "id": "E92000001",
                "geographic_id": "E92000001",
                "name": "England",
                "parent": None,
                "geography_type": "country",
            }
        },
    )

    BroadcastMessage.create_from_area(
        service_id=service_one,
        area_ids=["E92000001"],
        template_id="template_id",
        content="Test content",
        reference="Test Reference",
    )
    mock_create_broadcast_message.assert_called_once_with(
        service_id=service_one,
        reference="Test Reference",
        content="Test content",
        areas={
            "E92000001": {
                "id": "E92000001",
                "geographic_id": "E92000001",
                "name": "England",
                "parent": None,
                "geography_type": "country",
            }
        },
        template_id="template_id",
    )


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
