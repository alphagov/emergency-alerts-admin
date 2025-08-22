import pytest

from app.notify_client.template_api_client import TemplateAPIClient
from tests.app.notify_client.test_service_api_client import FAKE_TEMPLATE_ID
from tests.conftest import SERVICE_ONE_ID


@pytest.mark.parametrize(
    "template_data, extra_args, expected_count",
    (
        (
            [],
            {},
            0,
        ),
        (
            [],
            {"template_type": "broadcast"},
            0,
        ),
        (
            [
                {"template_type": "broadcast"},
            ],
            {},
            1,
        ),
        (
            [
                {"template_type": "broadcast"},
            ],
            {"template_type": "broadcast"},
            1,
        ),
        (
            [
                {"template_type": "broadcast"},
                {"template_type": "broadcast"},
            ],
            {},
            2,
        ),
        (
            [
                {"template_type": "broadcast"},
                {"template_type": "broadcast"},
            ],
            {"template_type": "broadcast"},
            2,
        ),
        (
            [
                {"template_type": "broadcast"},
                {"template_type": "broadcast"},
                {"template_type": "broadcast"},
            ],
            {},
            3,
        ),
        (
            [
                {"template_type": "broadcast"},
                {"template_type": "broadcast"},
                {"template_type": "broadcast"},
            ],
            {"template_type": "broadcast"},
            3,
        ),
    ),
)
def test_client_returns_count_of_service_templates(
    notify_admin,
    mocker,
    template_data,
    extra_args,
    expected_count,
):
    mocker.patch("app.notify_client.current_user", id="1")
    mocker.patch(
        "app.notify_client.template_api_client.TemplateAPIClient.get_templates",
        return_value={"data": template_data},
    )
    client = TemplateAPIClient()
    assert client.count_templates(service_id=SERVICE_ONE_ID) == expected_count


def test_client_gets_template(mocker, fake_uuid):
    mock_get = mocker.patch(
        "app.notify_client.template_api_client.TemplateAPIClient.get",
        return_value={
            "data": {"id": fake_uuid},
        },
    )
    TemplateAPIClient().get_template(SERVICE_ONE_ID, fake_uuid)
    mock_get.assert_called_once_with(
        "/service/{service_id}/template/{template_id}".format(service_id=SERVICE_ONE_ID, template_id=fake_uuid)
    )


def test_client_gets_multiple_templates(mocker, fake_uuid):
    mock_get = mocker.patch(
        "app.notify_client.template_api_client.TemplateAPIClient.get",
        return_value={
            "data": [
                {"id": fake_uuid},
                {"id": fake_uuid},
            ]
        },
    )
    templates = TemplateAPIClient().get_templates(SERVICE_ONE_ID)
    mock_get.assert_called_once_with("/service/{service_id}/template?detailed=False".format(service_id=SERVICE_ONE_ID))
    assert len(templates["data"]) == 2
    assert templates["data"][1]["id"] == fake_uuid


def test_client_posts_archived_true_when_deleting_template(mocker):
    mocker.patch("app.notify_client.current_user", id="1")
    expected_data = {"archived": True, "created_by": "1"}
    expected_url = f"/service/{SERVICE_ONE_ID}/template/{FAKE_TEMPLATE_ID}"

    mock_post = mocker.patch("app.notify_client.template_api_client.TemplateAPIClient.post")
    mocker.patch(
        "app.notify_client.template_api_client.TemplateAPIClient.get",
        return_value={"data": {"id": str(FAKE_TEMPLATE_ID)}},
    )
    TemplateAPIClient().delete_template(SERVICE_ONE_ID, FAKE_TEMPLATE_ID)
    mock_post.assert_called_once_with(expected_url, data=expected_data)


def test_client_gets_template_versions(mocker, fake_uuid):
    mocker.patch("app.notify_client.current_user", id="1")
    mock_get = mocker.patch(
        "app.notify_client.template_api_client.TemplateAPIClient.get",
        return_value={
            "data": [
                {"id": fake_uuid},
                {"id": fake_uuid},
            ]
        },
    )
    templates = TemplateAPIClient().get_template_versions(SERVICE_ONE_ID, fake_uuid)
    mock_get.assert_called_once_with(
        "/service/{service_id}/template/{template_id}/versions".format(service_id=SERVICE_ONE_ID, template_id=fake_uuid)
    )
    assert len(templates["data"]) == 2
    assert templates["data"][1]["id"] == fake_uuid


def test_client_posts_data_when_updating_template(mocker, fake_uuid):
    mocker.patch("app.notify_client.current_user", id="1")
    mock_post = mocker.patch("app.notify_client.template_api_client.TemplateAPIClient.post")
    TemplateAPIClient().update_template(
        id_=fake_uuid, service_id=SERVICE_ONE_ID, data={"reference": "New template reference"}
    )
    mock_post.assert_called_once_with(
        "/service/{0}/template/{1}".format(SERVICE_ONE_ID, fake_uuid),
        {"created_by": "1", "reference": "New template reference"},
    )


def test_client_posts_data_when_creating_template(mocker):
    mocker.patch("app.notify_client.current_user", id="1")
    mock_post = mocker.patch("app.notify_client.template_api_client.TemplateAPIClient.post")
    TemplateAPIClient().create_template(SERVICE_ONE_ID, reference="Template Reference", content="Template Content")
    mock_post.assert_called_once_with(
        "/service/{0}/template".format(SERVICE_ONE_ID),
        {
            "created_by": "1",
            "reference": "Template Reference",
            "template_type": "broadcast",
            "content": "Template Content",
            "service": "596364a0-858e-42c8-9062-a8fe822260eb",
        },
    )
