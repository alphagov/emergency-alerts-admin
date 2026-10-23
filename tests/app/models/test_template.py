import pytest

from app.models.template import Template
from tests import template_json
from tests.conftest import SERVICE_ONE_ID


def test_create_template_from_content(mocker, fake_uuid, mock_create_template):
    Template.create(service_id=SERVICE_ONE_ID, reference="Test Reference", content="Test Content")
    mock_create_template.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        reference="Test Reference",
        content="Test Content",
        template_folder_id=None,
        areas=[],
    )


@pytest.mark.parametrize(
    ("area_ids", "areas"),
    [
        (
            ["E92000001"],
            {
                "E92000001": {
                    "id": "fake area ID",
                    "geographic_id": "E92000001",
                    "name": "England",
                    "parent": None,
                    "geography_type": "country",
                }
            },
        ),
        (
            ["2km around the postcode BD1 1EE in Bradford"],
            {
                "2km around the postcode BD1 1EE in Bradford": {
                    "id": "2km around the postcode BD1 1EE in Bradford",
                    "geographic_id": None,
                    "name": "2km around the postcode BD1 1EE in Bradford",
                    "parent": None,
                    "geography_type": "custom",
                }
            },
        ),
        (
            ["5km around 54.0 latitude, -1.7 longitude, in Harrogate"],
            {
                "5km around 54.0 latitude, -1.7 longitude, in Harrogate": {
                    "id": "5km around 54.0 latitude, -1.7 longitude, in Harrogate",
                    "geographic_id": None,
                    "name": "5km around 54.0 latitude, -1.7 longitude, in Harrogate",
                    "parent": None,
                    "geography_type": "custom",
                }
            },
        ),
    ],
)
def test_create_template_from_area(
    mocker,
    fake_uuid,
    mock_create_template,
    area_ids,
    areas,
):
    mock_get_area_dict = mocker.patch(
        "app.models.template.areas_api_client.get_area_dict",
        return_value=areas,
    )

    Template.create_from_area(
        service_id=SERVICE_ONE_ID,
        area_ids=area_ids,
    )

    mock_get_area_dict.assert_called_once_with(area_ids)
    mock_create_template.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        areas=areas,
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


def test_add_postcode_area_to_template(mocker, fake_uuid):
    template = Template(template_json(SERVICE_ONE_ID, fake_uuid, areas={}))

    mock_add_postcode_area = mocker.patch(
        "app.models.base_broadcast.areas_api_client.add_postcode_area",
        return_value=template._dict,
    )

    template.add_postcode_area(
        template.id,
        template.service_id,
        postcode="BD1 1EE",
        radius=2.0,
        message_type="templates",
    )

    mock_add_postcode_area.assert_called_once_with(
        fake_uuid,
        SERVICE_ONE_ID,
        "BD1 1EE",
        2.0,
        "templates",
    )


def test_add_coordinate_area_to_template(mocker, fake_uuid):
    template = Template(template_json(SERVICE_ONE_ID, fake_uuid, areas={}))

    mock_add_coordinate_area = mocker.patch(
        "app.models.base_broadcast.areas_api_client.add_coordinate_area",
        return_value=template._dict,
    )

    template.add_coordinate_area(
        template.id,
        template.service_id,
        first_coordinate=54.0,
        second_coordinate=-1.7,
        radius=5.0,
        coordinate_type="latitude_longitude",
        message_type="templates",
    )

    mock_add_coordinate_area.assert_called_once_with(
        fake_uuid,
        SERVICE_ONE_ID,
        54.0,
        -1.7,
        5.0,
        "latitude_longitude",
        "templates",
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
