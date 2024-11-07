import functools

import pytest
from flask import url_for

from app.main.views.service_settings import PLATFORM_ADMIN_SERVICE_PERMISSIONS
from tests.conftest import normalize_spaces


@pytest.fixture
def get_service_settings_page(
    client_request,
    platform_admin_user,
    service_one,
    mock_get_organisation,
    mock_get_service_data_retention,
):
    client_request.login(platform_admin_user)
    return functools.partial(client_request.get, "main.service_settings", service_id=service_one["id"])


def test_service_set_permission_requires_platform_admin(
    mocker,
    client_request,
    service_one,
):
    client_request.post(
        "main.service_set_permission",
        service_id=service_one["id"],
        permission="email_auth",
        _data={"enabled": "True"},
        _expected_status=403,
    )


def test_service_set_permission_does_not_exist_for_broadcast_permission(
    mocker,
    client_request,
    platform_admin_user,
    service_one,
):
    client_request.login(platform_admin_user)
    client_request.get(
        "main.service_set_permission", service_id=service_one["id"], permission="broadcast", _expected_status=404
    )


@pytest.mark.parametrize(
    "initial_permissions, permission, form_data, expected_update",
    [
        (
            [],
            "email_auth",
            "True",
            ["email_auth"],
        ),
        (
            ["email_auth"],
            "email_auth",
            "False",
            [],
        ),
    ],
)
def test_service_set_permission(
    mocker,
    client_request,
    platform_admin_user,
    service_one,
    mock_update_service_organisation,
    permission,
    initial_permissions,
    form_data,
    expected_update,
):
    service_one["permissions"] = initial_permissions
    mock_update_service = mocker.patch("app.service_api_client.update_service")
    client_request.login(platform_admin_user)
    client_request.post(
        "main.service_set_permission",
        service_id=service_one["id"],
        permission=permission,
        _data={"enabled": form_data},
        _expected_redirect=url_for(
            "main.service_settings",
            service_id=service_one["id"],
        ),
    )

    assert mock_update_service.call_args[0][0] == service_one["id"]
    new_permissions = mock_update_service.call_args[1]["permissions"]
    assert len(new_permissions) == len(set(new_permissions))
    assert set(new_permissions) == set(expected_update)


@pytest.mark.parametrize(
    "endpoint, index, text", [(".archive_service", 0, "Delete this service"), (".history", 1, "Service history")]
)
def test_service_setting_links_displayed_for_active_services(
    get_service_settings_page,
    service_one,
    endpoint,
    index,
    text,
):
    link_url = url_for(endpoint, service_id=service_one["id"])
    page = get_service_settings_page()
    link = page.select(".page-footer-link a")[index]
    assert normalize_spaces(link.text) == text
    assert link["href"] == link_url


def test_service_settings_links_for_archived_service(
    get_service_settings_page,
    service_one,
):
    service_one.update({"active": False})
    page = get_service_settings_page()
    links = page.select("a")

    # There should be a link to the service history page
    assert len([link for link in links if link.get("href") == url_for(".history", service_id=service_one["id"])]) == 1

    # There shouldn't be a link to the archive/delete service page.
    assert (
        len([link for link in links if link.get("href") == url_for(".archive_service", service_id=service_one["id"])])
        == 0
    )


def test_normal_user_doesnt_see_any_platform_admin_settings(
    client_request,
    service_one,
    mock_get_organisation,
    mock_get_service_data_retention,
):
    page = client_request.get("main.service_settings", service_id=service_one["id"])
    platform_admin_settings = [permission["title"] for permission in PLATFORM_ADMIN_SERVICE_PERMISSIONS.values()]

    for permission in platform_admin_settings:
        assert permission not in page
