from unittest.mock import call

import pytest

from app import organisations_client


@pytest.fixture(autouse=True)
def mock_notify_client_check_inactive_service(mocker):
    mocker.patch("app.notify_client.AdminAPIClient.check_inactive_service")


@pytest.mark.parametrize(
    "post_data, expected_cache_delete_calls",
    (
        (
            {"foo": "bar"},
            [
                call("organisations"),
                call("domains"),
            ],
        ),
        (
            {"name": "new name"},
            [
                call("organisation-6ce466d0-fd6a-11e5-82f5-e0accb9d11a6-name"),
                call("organisations"),
                call("domains"),
            ],
        ),
    ),
)
def test_update_organisation_when_not_updating_org_type(
    mocker,
    fake_uuid,
    post_data,
    expected_cache_delete_calls,
):
    mock_post = mocker.patch("app.notify_client.organisations_api_client.OrganisationsClient.post")

    organisations_client.update_organisation(fake_uuid, **post_data)

    mock_post.assert_called_with(url="/organisations/{}".format(fake_uuid), data=post_data)


def test_update_organisation_when_updating_org_type_and_org_has_services(mocker, fake_uuid):
    mock_post = mocker.patch("app.notify_client.organisations_api_client.OrganisationsClient.post")

    organisations_client.update_organisation(
        fake_uuid,
        organisation_type="central",
    )

    mock_post.assert_called_with(url="/organisations/{}".format(fake_uuid), data={"organisation_type": "central"})


def test_update_organisation_when_updating_org_type_but_org_has_no_services(mocker, fake_uuid):
    mock_post = mocker.patch("app.notify_client.organisations_api_client.OrganisationsClient.post")

    organisations_client.update_organisation(
        fake_uuid,
        organisation_type="central",
    )

    mock_post.assert_called_with(url="/organisations/{}".format(fake_uuid), data={"organisation_type": "central"})


@pytest.mark.parametrize("org_type", ["nhs_central", "nhs_local", "nhs_gp"])
def test_update_organisation_when_to_updating_to_an_nhs_org_type(mocker, org_type, fake_uuid):
    mock_post = mocker.patch("app.notify_client.organisations_api_client.OrganisationsClient.post")

    organisations_client.update_organisation(
        fake_uuid,
        organisation_type=org_type,
    )

    mock_post.assert_called_with(url=f"/organisations/{fake_uuid}", data={"organisation_type": org_type})


def test_remove_user_from_organisation_deletes_user_cache(mocker):
    mock_delete = mocker.patch("app.notify_client.organisations_api_client.OrganisationsClient.delete")

    org_id = "abcd-1234"
    user_id = "efgh-5678"

    organisations_client.remove_user_from_organisation(
        org_id=org_id,
        user_id=user_id,
    )

    mock_delete.assert_called_with(f"/organisations/{org_id}/users/{user_id}")


def test_archive_organisation(mocker):
    mock_post = mocker.patch("app.notify_client.organisations_api_client.OrganisationsClient.post")

    org_id = "abcd-1234"

    organisations_client.archive_organisation(org_id=org_id)

    mock_post.assert_called_with(url=f"/organisations/{org_id}/archive", data=None)
