import uuid

import pytest
from ordered_set import OrderedSet

from app.notify_client.template_folder_api_client import TemplateFolderAPIClient


@pytest.mark.parametrize("parent_id", [uuid.uuid4(), None])
def test_create_template_folder_calls_correct_api_endpoint(mocker, parent_id):
    some_service_id = uuid.uuid4()
    expected_url = "/service/{}/template-folder".format(some_service_id)
    data = {"name": "foo", "parent_id": parent_id}

    client = TemplateFolderAPIClient()

    mock_post = mocker.patch("app.notify_client.template_folder_api_client.TemplateFolderAPIClient.post")

    client.create_template_folder(some_service_id, name="foo", parent_id=parent_id)

    mock_post.assert_called_once_with(expected_url, data)


def test_get_template_folders_calls_correct_api_endpoint(mocker):
    mock_api_get = mocker.patch("app.notify_client.AdminAPIClient.get", return_value={"template_folders": {"a": "b"}})

    some_service_id = uuid.uuid4()
    expected_url = "/service/{}/template-folder".format(some_service_id)

    client = TemplateFolderAPIClient()

    ret = client.get_template_folders(some_service_id)

    assert ret == {"a": "b"}

    mock_api_get.assert_called_once_with(expected_url)


def test_move_templates_and_folders(mocker):
    mock_api_post = mocker.patch("app.notify_client.AdminAPIClient.post")

    some_service_id = uuid.uuid4()
    some_folder_id = uuid.uuid4()

    TemplateFolderAPIClient().move_to_folder(
        some_service_id,
        some_folder_id,
        template_ids=OrderedSet(("a", "b", "c")),
        folder_ids=OrderedSet(("1", "2", "3")),
    )

    mock_api_post.assert_called_once_with(
        "/service/{}/template-folder/{}/contents".format(some_service_id, some_folder_id),
        {
            "folders": ["1", "2", "3"],
            "templates": ["a", "b", "c"],
        },
    )


def test_move_templates_and_folders_to_root(mocker):
    mock_api_post = mocker.patch("app.notify_client.AdminAPIClient.post")

    some_service_id = uuid.uuid4()

    TemplateFolderAPIClient().move_to_folder(
        some_service_id,
        None,
        template_ids=OrderedSet(("a", "b", "c")),
        folder_ids=OrderedSet(("1", "2", "3")),
    )

    mock_api_post.assert_called_once_with(
        "/service/{}/template-folder/contents".format(some_service_id),
        {
            "folders": ["1", "2", "3"],
            "templates": ["a", "b", "c"],
        },
    )


def test_update_template_folder_calls_correct_api_endpoint(mocker):
    some_service_id = uuid.uuid4()
    template_folder_id = uuid.uuid4()
    expected_url = "/service/{}/template-folder/{}".format(some_service_id, template_folder_id)
    data = {"name": "foo", "users_with_permission": ["some_id"]}

    client = TemplateFolderAPIClient()

    mock_post = mocker.patch("app.notify_client.template_folder_api_client.TemplateFolderAPIClient.post")

    client.update_template_folder(some_service_id, template_folder_id, name="foo", users_with_permission=["some_id"])

    mock_post.assert_called_once_with(expected_url, data)


def test_delete_template_folder_calls_correct_api_endpoint(mocker):
    some_service_id = uuid.uuid4()
    template_folder_id = uuid.uuid4()
    expected_url = "/service/{}/template-folder/{}".format(some_service_id, template_folder_id)

    client = TemplateFolderAPIClient()

    mock_delete = mocker.patch("app.notify_client.template_folder_api_client.TemplateFolderAPIClient.delete")

    client.delete_template_folder(some_service_id, template_folder_id)

    mock_delete.assert_called_once_with(expected_url, {})
