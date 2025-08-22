from app.models.template import Template
from tests import template_json
from tests.app.broadcast_areas.custom_polygons import BD1_1EE
from tests.conftest import SERVICE_ONE_ID


def test_create_template(mocker, fake_uuid):
    mock_create = mocker.patch(
        "app.models.template.template_api_client.create_template",
        return_value=template_json(
            SERVICE_ONE_ID,
            fake_uuid,
        ),
    )
    Template.create(service_id=SERVICE_ONE_ID)
    mock_create.assert_called_once()


def test_create_template_with_custom_area(mocker, fake_uuid):
    mock_create = mocker.patch(
        "app.models.template.template_api_client.create_template",
        return_value=template_json(
            SERVICE_ONE_ID,
            fake_uuid,
        ),
    )
    Template.create_with_custom_area(BD1_1EE, fake_uuid, SERVICE_ONE_ID)
    mock_create.assert_called_once()


def test_create_template_from_area(mocker, fake_uuid):
    mock_create = mocker.patch(
        "app.models.template.template_api_client.create_template",
        return_value=template_json(
            SERVICE_ONE_ID,
            fake_uuid,
        ),
    )
    mock_libraries = mocker.patch("app.models.template.BroadcastAreaLibraries")
    mocker.patch("app.models.template.aggregate_areas", return_value=["agg-area"])
    mocker.patch("app.models.template.generate_aggregate_names", return_value=["agg-name"])
    mock_libraries.return_value.get_areas.return_value = [
        type(
            "Area",
            (),
            {"name": "AreaName", "simple_polygons": type("Polygons", (), {"as_coordinate_pairs_lat_long": "coords"})()},
        )()
    ]
    template = Template.create_from_area(service_id=SERVICE_ONE_ID, area_ids=["area-id"])
    mock_create.assert_called_once()
    assert isinstance(template, Template)


def test_update_template_from_content(mocker, fake_uuid):
    mock_update = mocker.patch("app.models.template.template_api_client.update_template")
    Template.update_from_content(
        service_id=SERVICE_ONE_ID, template_id=fake_uuid, content="new content", reference="new-ref"
    )
    mock_update.assert_called_once()
    args, kwargs = mock_update.call_args
    assert kwargs["service_id"] == SERVICE_ONE_ID
    assert kwargs["id_"] == fake_uuid
    assert "content" in kwargs["data"]
    assert "reference" in kwargs["data"]


def test_get_template_from_id(mocker, fake_uuid):
    mock_get = mocker.patch(
        "app.models.template.template_api_client.get_template",
        return_value={
            "data": template_json(
                SERVICE_ONE_ID,
                fake_uuid,
            ),
        },
    )
    template = Template.from_id(fake_uuid, service_id=SERVICE_ONE_ID)
    mock_get.assert_called_once()
    assert isinstance(template, Template)
    assert template.id == fake_uuid


def test_update_template(mocker, fake_uuid):
    template = Template(
        template_json(
            SERVICE_ONE_ID,
            fake_uuid,
        ),
    )
    mock_update = mocker.patch("app.models.template.template_api_client.update_template")
    template._update(content="updated")
    mock_update.assert_called_once()
    args, kwargs = mock_update.call_args
    assert kwargs["id_"] == template.id
    assert kwargs["service_id"] == template.service
    assert kwargs["data"]["content"] == "updated"


def test_add_custom_areas_to_template(mocker, fake_uuid):
    template = Template(template_json(SERVICE_ONE_ID, fake_uuid, areas={}))
    mock_update = mocker.patch("app.models.template.template_api_client.update_template")
    mocker.patch.object(Template, "add_local_authority_to_slug", return_value="custom-id")
    template.area_ids = []
    template.add_custom_areas("polygon", id="custom-id")
    mock_update.assert_called_once()
    args, kwargs = mock_update.call_args
    assert kwargs["id_"] == template.id
    assert kwargs["service_id"] == template.service
    assert "areas" in kwargs["data"]


def test_get_template_version(mocker, fake_uuid):
    mock_get = mocker.patch(
        "app.models.template.template_api_client.get_template",
        return_value={
            "data": template_json(
                SERVICE_ONE_ID,
                fake_uuid,
            ),
        },
    )
    template = Template(
        template_json(
            SERVICE_ONE_ID,
            fake_uuid,
        ),
    )
    data = template.get_template_version(service_id=SERVICE_ONE_ID, version=2)
    mock_get.assert_called_once_with(SERVICE_ONE_ID, template.id, 2)
    assert data["id"] == fake_uuid


def test_get_template_versions(mocker, fake_uuid):
    mock_get = mocker.patch(
        "app.models.template.template_api_client.get_template_versions",
        return_value={
            "data": [
                template_json(
                    SERVICE_ONE_ID,
                    fake_uuid,
                ),
            ]
        },
    )
    template = Template(
        template_json(
            SERVICE_ONE_ID,
            fake_uuid,
        ),
    )
    template.get_template_versions(service_id=SERVICE_ONE_ID)
    mock_get.assert_called_once_with(SERVICE_ONE_ID, template.id)
