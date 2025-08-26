import math

from app.models.template import Template
from tests import template_json
from tests.app.broadcast_areas.custom_polygons import BD1_1EE, ENGLAND
from tests.conftest import SERVICE_ONE_ID


def test_create_template_from_content(mocker, fake_uuid, mock_create_template):
    Template.create(service_id=SERVICE_ONE_ID, reference="Test Reference", content="Test Content")
    mock_create_template.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        reference="Test Reference",
        content="Test Content",
        template_folder_id=None,
        areas=None,
    )


def test_create_template_with_custom_area(mocker, fake_uuid, mock_create_template):
    area_data = {
        "areas": {
            "ids": ["2km around the postcode BD1 1EE in Bradford"],
            "names": ["2km around the postcode BD1 1EE in Bradford"],
            "aggregate_names": ["2km around the postcode BD1 1EE in Bradford"],
            "simple_polygons": [BD1_1EE],
        }
    }
    Template.create_with_custom_area(BD1_1EE, "2km around the postcode BD1 1EE", SERVICE_ONE_ID)
    mock_create_template.assert_called_once()
    assert mock_create_template._mock_call_args[1]["areas"]["names"] == area_data["areas"]["names"]
    assert mock_create_template._mock_call_args[1]["areas"]["ids"] == area_data["areas"]["ids"]
    assert mock_create_template._mock_call_args[1]["areas"]["aggregate_names"] == area_data["areas"]["aggregate_names"]

    actual_polygons = mock_create_template._mock_call_args[1]["areas"]["simple_polygons"]
    expected_polygons = area_data["areas"]["simple_polygons"]

    for coords1, coords2 in zip(actual_polygons, expected_polygons):
        for coord1, coord2 in zip(coords1, coords2):
            assert all(abs(a - b) < math.exp(1e-12) for a, b in zip(coord1, coord2))


def test_create_template_from_area(mocker, fake_uuid, mock_create_template):
    Template.create_from_area(service_id=SERVICE_ONE_ID, area_ids=["ctry19-E92000001"])
    mock_create_template.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        areas={
            "ids": ["ctry19-E92000001"],
            "simple_polygons": [ENGLAND],
            "names": ["England"],
            "aggregate_names": ["England"],
        },
        template_folder_id=None,
    )


def test_update_template_from_content(mocker, fake_uuid, mock_update_template):
    Template.update_from_content(
        service_id=SERVICE_ONE_ID, template_id=fake_uuid, content="Test New Content", reference="Test New Reference"
    )
    mock_update_template.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        id_=fake_uuid,
        data={"reference": "Test New Reference", "content": "Test New Content"},
    )


def test_get_template_from_id(mocker, fake_uuid, mock_get_template_from_id):
    Template.from_id(template_id=fake_uuid, service_id=SERVICE_ONE_ID)
    mock_get_template_from_id.assert_called_once_with(template_id=fake_uuid, service_id=SERVICE_ONE_ID)


def test_add_custom_areas_to_template(mocker, fake_uuid, mock_update_template):
    template = Template(template_json(SERVICE_ONE_ID, fake_uuid, areas={}))
    template.add_custom_areas(BD1_1EE, id="2km around the postcode BD1 1EE")
    mock_update_template.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        id_=fake_uuid,
        data={
            "areas": {
                "ids": ["2km around the postcode BD1 1EE in Bradford"],
                "names": ["2km around the postcode BD1 1EE in Bradford"],
                "aggregate_names": ["2km around the postcode BD1 1EE in Bradford"],
                "simple_polygons": [BD1_1EE],
            },
        },
    )


def test_get_template_version(mocker, fake_uuid, mock_get_template_version):
    template = Template(
        template_json(
            SERVICE_ONE_ID,
            fake_uuid,
        ),
    )
    template.get_template_version(service_id=SERVICE_ONE_ID, version=2)
    mock_get_template_version.assert_called_once_with(SERVICE_ONE_ID, template.id, 2)


def test_get_template_versions(mocker, fake_uuid, mock_get_template_versions):
    template = Template(
        template_json(
            SERVICE_ONE_ID,
            fake_uuid,
        ),
    )
    template.get_template_versions(service_id=SERVICE_ONE_ID)
    mock_get_template_versions.assert_called_once_with(SERVICE_ONE_ID, template.id)
