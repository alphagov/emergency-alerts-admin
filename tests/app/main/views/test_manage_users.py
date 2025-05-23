import copy
import uuid

import pytest
from flask import url_for

import app
from app.models.user import User
from app.utils.user import is_gov_user
from tests.conftest import (
    ORGANISATION_ID,
    SERVICE_ONE_ID,
    USER_ONE_ID,
    create_active_user_empty_permissions,
    create_active_user_manage_template_permissions,
    create_active_user_view_permissions,
    create_active_user_with_permissions,
    normalize_spaces,
    sample_uuid,
)


@pytest.mark.parametrize(
    "user, expected_self_text, expected_coworker_text",
    [
        (
            create_active_user_with_permissions(),
            ("Test User (you) " "Can Add and edit templates " "Cannot Create new alerts " "Cannot Approve alerts"),
            (
                "ZZZZZZZZ zzzzzzz@example.gov.uk "
                "Cannot Add and edit templates "
                "Cannot Create new alerts "
                "Cannot Approve alerts "
                "Change details for ZZZZZZZZ zzzzzzz@example.gov.uk"
            ),
        ),
        (
            create_active_user_empty_permissions(),
            (
                "Test User With Empty Permissions (you) "
                "Cannot Add and edit templates "
                "Cannot Create new alerts "
                "Cannot Approve alerts"
            ),
            (
                "ZZZZZZZZ zzzzzzz@example.gov.uk "
                "Cannot Add and edit templates "
                "Cannot Create new alerts "
                "Cannot Approve alerts"
            ),
        ),
        (
            create_active_user_view_permissions(),
            (
                "Test User With Permissions (you) "
                "Cannot Add and edit templates "
                "Cannot Create new alerts "
                "Cannot Approve alerts"
            ),
            (
                "ZZZZZZZZ zzzzzzz@example.gov.uk "
                "Cannot Add and edit templates "
                "Cannot Create new alerts "
                "Cannot Approve alerts"
            ),
        ),
        (
            create_active_user_manage_template_permissions(),
            (
                "Test User With Permissions (you) "
                "Can Add and edit templates "
                "Cannot Create new alerts "
                "Cannot Approve alerts"
            ),
            (
                "ZZZZZZZZ zzzzzzz@example.gov.uk "
                "Cannot Add and edit templates "
                "Cannot Create new alerts "
                "Cannot Approve alerts"
            ),
        ),
        (
            create_active_user_manage_template_permissions(),
            (
                "Test User With Permissions (you) "
                "Can Add and edit templates "
                "Cannot Create new alerts "
                "Cannot Approve alerts"
            ),
            (
                "ZZZZZZZZ zzzzzzz@example.gov.uk "
                "Cannot Add and edit templates "
                "Cannot Create new alerts "
                "Cannot Approve alerts"
            ),
        ),
    ],
)
def test_should_show_overview_page(
    client_request,
    mocker,
    mock_get_invites_for_service,
    mock_get_template_folders,
    service_one,
    user,
    expected_self_text,
    expected_coworker_text,
    active_user_view_permissions,
):
    current_user = user
    other_user = copy.deepcopy(active_user_view_permissions)
    other_user["email_address"] = "zzzzzzz@example.gov.uk"
    other_user["name"] = "ZZZZZZZZ"
    other_user["id"] = "zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz"

    mock_get_users = mocker.patch(
        "app.models.user.Users.client_method",
        return_value=[
            current_user,
            other_user,
        ],
    )

    client_request.login(current_user)
    page = client_request.get("main.manage_users", service_id=SERVICE_ONE_ID)

    assert normalize_spaces(page.select_one("h1").text) == "Team members"
    assert normalize_spaces(page.select(".user-list-item")[0].text) == expected_self_text
    # [1:5] are invited users
    assert normalize_spaces(page.select(".user-list-item")[6].text) == expected_coworker_text
    mock_get_users.assert_called_once_with(SERVICE_ONE_ID)


@pytest.mark.parametrize(
    "state",
    (
        "active",
        "pending",
    ),
)
def test_should_show_change_details_link(
    client_request,
    mocker,
    mock_get_invites_for_service,
    mock_get_template_folders,
    service_one,
    active_user_with_permissions,
    active_user_create_broadcasts_permission,
    state,
):
    current_user = active_user_with_permissions

    other_user = active_user_create_broadcasts_permission
    other_user["id"] = uuid.uuid4()
    other_user["email_address"] = "zzzzzzz@example.gov.uk"
    other_user["state"] = state

    mocker.patch("app.user_api_client.get_user", return_value=current_user)
    mocker.patch(
        "app.models.user.Users.client_method",
        return_value=[
            current_user,
            other_user,
        ],
    )

    page = client_request.get("main.manage_users", service_id=SERVICE_ONE_ID)
    link = page.select(".user-list-item")[-1].select_one("a")

    assert normalize_spaces(link.text) == (
        "Change details for Test User " "Create Broadcasts Permission zzzzzzz@example.gov.uk"
    )
    assert link["href"] == url_for(
        ".edit_user_permissions",
        service_id=SERVICE_ONE_ID,
        user_id=other_user["id"],
    )


@pytest.mark.parametrize(
    "number_of_users",
    (
        pytest.param(7, marks=pytest.mark.xfail),
        pytest.param(8),
    ),
)
def test_should_show_live_search_if_more_than_7_users(
    client_request,
    mocker,
    mock_get_invites_for_service,
    mock_get_template_folders,
    active_user_with_permissions,
    active_user_view_permissions,
    number_of_users,
):
    mocker.patch("app.user_api_client.get_user", return_value=active_user_with_permissions)
    mocker.patch("app.models.user.InvitedUsers.client_method", return_value=[])
    mocker.patch("app.models.user.Users.client_method", return_value=[active_user_with_permissions] * number_of_users)

    page = client_request.get("main.manage_users", service_id=SERVICE_ONE_ID)

    assert page.select_one("div[data-notify-module=live-search]")["data-targets"] == ".user-list-item"
    assert len(page.select(".user-list-item")) == number_of_users

    textbox = page.select_one(".govuk-input")
    assert "value" not in textbox
    assert textbox["name"] == "search"
    # data-notify-module=autofocus is set on a containing element so it
    # shouldn’t also be set on the textbox itself
    assert "data-notify-module" not in textbox
    assert not page.select_one("[data-force-focus]")
    assert textbox["class"] == [
        "govuk-input",
        "govuk-!-width-full",
    ]
    assert normalize_spaces(page.select_one("label[for=search]").text) == "Search and filter by name or email address"


def test_should_show_other_user_on_overview_page(
    client_request,
    mocker,
    mock_get_invites_for_service,
    mock_get_template_folders,
    service_one,
    active_user_view_permissions,
    active_new_user_with_permissions,
):
    service_one["permissions"].append("caseworking")
    current_user = active_user_view_permissions

    other_user = active_new_user_with_permissions
    other_user["id"] = uuid.uuid4()
    other_user["email_address"] = "zzzzzzz@example.gov.uk"

    mocker.patch(
        "app.models.user.Users.client_method",
        return_value=[
            current_user,
            other_user,
        ],
    )

    client_request.login(current_user)
    page = client_request.get("main.manage_users", service_id=SERVICE_ONE_ID)

    assert normalize_spaces(page.select_one("h1").text) == "Team members"
    assert normalize_spaces(page.select(".user-list-item")[0].text) == (
        "Test User With Permissions (you) "
        "Cannot Add and edit templates "
        "Cannot Create new alerts "
        "Cannot Approve alerts"
    )
    assert normalize_spaces(page.select(".user-list-item")[6].text) == (
        "Test User With Permissions "
        "zzzzzzz@example.gov.uk "
        "Cannot Add and edit templates "
        "Cannot Create new alerts "
        "Cannot Approve alerts"
    )


def test_should_show_overview_page_for_broadcast_service(
    client_request,
    mocker,
    mock_get_invites_for_service,
    mock_get_template_folders,
    service_one,
    active_user_view_permissions,
    active_user_create_broadcasts_permission,
    active_user_approve_broadcasts_permission,
):
    service_one["permissions"].append("broadcast")
    mocker.patch(
        "app.models.user.Users.client_method",
        return_value=[
            active_user_create_broadcasts_permission,
            active_user_approve_broadcasts_permission,
            active_user_view_permissions,
        ],
    )
    page = client_request.get("main.manage_users", service_id=SERVICE_ONE_ID)
    assert normalize_spaces(page.select(".user-list-item")[0].text) == (
        "Test User Create Broadcasts Permission (you) "
        "Cannot Add and edit templates "
        "Can Create new alerts "
        "Cannot Approve alerts"
    )
    assert normalize_spaces(page.select(".user-list-item")[1].text) == (
        "Test User Approve Broadcasts Permission (you) "
        "Cannot Add and edit templates "
        "Cannot Create new alerts "
        "Can Approve alerts"
    )
    assert normalize_spaces(page.select(".user-list-item")[2].text) == (
        "Test User With Permissions (you) "
        "Cannot Add and edit templates "
        "Cannot Create new alerts "
        "Cannot Approve alerts"
    )


@pytest.mark.parametrize(
    "endpoint, extra_args",
    [
        (
            "main.edit_user_permissions",
            {"user_id": sample_uuid()},
        ),
        (
            "main.invite_user",
            {},
        ),
    ],
)
def test_broadcast_service_only_shows_relevant_permissions(
    client_request,
    service_one,
    mock_get_users_by_service,
    mock_get_template_folders,
    endpoint,
    extra_args,
):
    service_one["permissions"] = ["broadcast"]
    page = client_request.get(endpoint, service_id=SERVICE_ONE_ID, **extra_args)
    assert [(field["name"], field["value"]) for field in page.select("input[type=checkbox]")] == [
        ("permissions_field", "manage_templates"),
        ("permissions_field", "create_broadcasts"),
        ("permissions_field", "approve_broadcasts"),
    ]


@pytest.mark.parametrize("service_has_email_auth, displays_auth_type", [(True, True), (False, False)])
def test_manage_users_page_shows_member_auth_type_if_service_has_email_auth_activated(
    client_request,
    service_has_email_auth,
    service_one,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_get_template_folders,
    displays_auth_type,
):
    if service_has_email_auth:
        service_one["permissions"].append("email_auth")
    page = client_request.get("main.manage_users", service_id=service_one["id"])
    assert bool(page.select_one(".tick-cross-list-hint")) == displays_auth_type


@pytest.mark.parametrize(
    "endpoint, extra_args, expected_checkboxes",
    [
        (
            "main.edit_user_permissions",
            {"user_id": sample_uuid()},
            [
                ("manage_templates", True),
                ("create_broadcasts", False),
                ("approve_broadcasts", False),
            ],
        ),
        (
            "main.invite_user",
            {},
            [
                ("manage_templates", False),
                ("create_broadcasts", False),
                ("approve_broadcasts", False),
            ],
        ),
    ],
)
def test_should_show_page_for_one_user(
    client_request,
    mock_get_users_by_service,
    mock_get_template_folders,
    endpoint,
    extra_args,
    expected_checkboxes,
):
    page = client_request.get(endpoint, service_id=SERVICE_ONE_ID, **extra_args)
    checkboxes = page.select("input[type=checkbox]")

    assert len(checkboxes) == 3

    for index, expected in enumerate(expected_checkboxes):
        expected_input_value, expected_checked = expected
        assert checkboxes[index]["name"] == "permissions_field"
        assert checkboxes[index]["value"] == expected_input_value
        assert checkboxes[index].has_attr("checked") == expected_checked


def test_invite_user_has_correct_email_field(
    client_request,
    mock_get_users_by_service,
    mock_get_template_folders,
):
    email_field = client_request.get("main.invite_user", service_id=SERVICE_ONE_ID).select_one("#email_address")
    assert email_field["spellcheck"] == "false"
    assert "autocomplete" not in email_field


def test_should_not_show_page_for_non_team_member(
    client_request,
    mock_get_users_by_service,
):
    client_request.get(
        "main.edit_user_permissions",
        service_id=SERVICE_ONE_ID,
        user_id=USER_ONE_ID,
        _expected_status=404,
    )


@pytest.mark.parametrize(
    "existing_permissions, submitted_permissions, expected_sent_permissions, requires_admin_action",
    [
        (
            set(),
            {
                "create_broadcasts",
            },
            {
                "view_activity",
                "create_broadcasts",
            },
            True,
        ),
        (
            set(),
            {
                "approve_broadcasts",
            },
            {
                "view_activity",
                "approve_broadcasts",
            },
            True,
        ),
        (
            set(),
            {
                "create_broadcasts",
                "approve_broadcasts",
            },
            {
                "view_activity",
                "create_broadcasts",
                "approve_broadcasts",
            },
            True,
        ),
        (
            set(),
            {"manage_templates"},  # Not sensitive
            {
                "view_activity",
                "manage_templates",
            },
            False,
        ),
        # Removing permissions should never require admin action:
        (
            {"manage_templates", "view_activity"},
            set(),
            {
                "view_activity",
            },
            False,
        ),
        (
            {
                "create_broadcasts",
                "approve_broadcasts",
                "manage_templates",
            },
            {"manage_templates"},
            {
                "view_activity",
                "manage_templates",
            },
            False,
        ),
        (
            {
                "create_broadcasts",
                "approve_broadcasts",
            },
            set(),
            {
                "view_activity",
            },
            False,
        ),
    ],
)
def test_edit_user_permissions_for_broadcast_service(
    client_request,
    service_one,
    mocker,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_set_user_permissions,
    mock_get_template_folders,
    mock_get_pending_admin_actions,
    mock_admin_action_notification,
    fake_uuid,
    existing_permissions,
    submitted_permissions,
    expected_sent_permissions,
    requires_admin_action,
):
    mocker.patch(
        "app.models.user.User.permissions_for_service",
        side_effect=[
            {"manage_service"},  # To allow the endpoint to run initially
            # Called by the form, endpoint for existing perms, and then the User class:
            existing_permissions,
            existing_permissions,
            existing_permissions,
        ],
    )
    mocker.patch("app.admin_actions_api_client.create_admin_action", return_value=None)
    service_one["permissions"] = ["broadcast"]

    client_request.post(
        "main.edit_user_permissions",
        service_id=SERVICE_ONE_ID,
        user_id=fake_uuid,
        _data=dict(email_address="test@example.com", permissions_field=list(submitted_permissions)),
        _expected_status=302,
        _expected_redirect=url_for(
            "main.manage_users",
            service_id=SERVICE_ONE_ID,
        ),
    )

    if requires_admin_action:
        # One or more added permissions are sensitive
        app.admin_actions_api_client.create_admin_action.assert_called_once_with(
            {
                "service_id": SERVICE_ONE_ID,
                "created_by": fake_uuid,
                "action_type": "edit_permissions",
                "action_data": {
                    "user_id": fake_uuid,
                    "existing_permissions": existing_permissions,
                    "permissions": expected_sent_permissions,
                    "folder_permissions": [],
                },
            }
        )
        mock_admin_action_notification.assert_called_once()
        mock_set_user_permissions.assert_not_called()
    else:
        # The added permissions are not sensitive
        mock_set_user_permissions.assert_called_with(
            fake_uuid, SERVICE_ONE_ID, permissions=expected_sent_permissions, folder_permissions=[]
        )
        mock_admin_action_notification.assert_not_called()
        app.admin_actions_api_client.create_admin_action.assert_not_called()


def test_edit_user_folder_permissions(
    client_request,
    mocker,
    service_one,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_set_user_permissions,
    mock_get_template_folders,
    fake_uuid,
):
    mock_get_template_folders.return_value = [
        {"id": "folder-id-1", "name": "folder_one", "parent_id": None, "users_with_permission": []},
        {"id": "folder-id-2", "name": "folder_one", "parent_id": None, "users_with_permission": []},
        {"id": "folder-id-3", "name": "folder_one", "parent_id": "folder-id-1", "users_with_permission": []},
    ]

    page = client_request.get(
        "main.edit_user_permissions",
        service_id=SERVICE_ONE_ID,
        user_id=fake_uuid,
    )
    assert [item["value"] for item in page.select("input[name=folder_permissions]")] == [
        "folder-id-1",
        "folder-id-3",
        "folder-id-2",
    ]

    client_request.post(
        "main.edit_user_permissions",
        service_id=SERVICE_ONE_ID,
        user_id=fake_uuid,
        _data=dict(folder_permissions=["folder-id-1", "folder-id-3"]),
        _expected_status=302,
        _expected_redirect=url_for(
            "main.manage_users",
            service_id=SERVICE_ONE_ID,
        ),
    )
    mock_set_user_permissions.assert_called_with(
        fake_uuid, SERVICE_ONE_ID, permissions={"view_activity"}, folder_permissions=["folder-id-1", "folder-id-3"]
    )


def test_cant_edit_user_folder_permissions_for_platform_admin_users(
    client_request,
    mocker,
    service_one,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_set_user_permissions,
    mock_get_template_folders,
    platform_admin_user,
):
    service_one["permissions"] = ["edit_folder_permissions"]
    mocker.patch("app.user_api_client.get_user", return_value=platform_admin_user)
    mock_get_template_folders.return_value = [
        {"id": "folder-id-1", "name": "folder_one", "parent_id": None, "users_with_permission": []},
        {"id": "folder-id-2", "name": "folder_one", "parent_id": None, "users_with_permission": []},
        {"id": "folder-id-3", "name": "folder_one", "parent_id": "folder-id-1", "users_with_permission": []},
    ]
    page = client_request.get(
        "main.edit_user_permissions",
        service_id=SERVICE_ONE_ID,
        user_id=platform_admin_user["id"],
    )
    assert normalize_spaces(page.select("main p")[0].text) == "platform@admin.gov.uk Change email address"
    assert normalize_spaces(page.select("main p")[2].text) == "Platform admin users can access all template folders."
    assert page.select("input[name=folder_permissions]") == []
    client_request.post(
        "main.edit_user_permissions",
        service_id=SERVICE_ONE_ID,
        user_id=platform_admin_user["id"],
        _data={},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.manage_users",
            service_id=SERVICE_ONE_ID,
        ),
    )
    mock_set_user_permissions.assert_called_with(
        platform_admin_user["id"],
        SERVICE_ONE_ID,
        permissions={
            "manage_api_keys",
            "manage_service",
            "manage_templates",
            "view_activity",
        },
        folder_permissions=None,
    )


def test_cant_edit_non_member_user_permissions(
    client_request,
    mocker,
    mock_get_users_by_service,
    mock_set_user_permissions,
):
    client_request.post(
        "main.edit_user_permissions",
        service_id=SERVICE_ONE_ID,
        user_id=USER_ONE_ID,
        _data={
            "email_address": "test@example.com",
            "manage_service": "y",
        },
        _expected_status=404,
    )
    assert mock_set_user_permissions.called is False


def test_edit_user_permissions_including_authentication_with_email_auth_service(
    client_request,
    service_one,
    active_user_with_permissions,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_set_user_permissions,
    mock_update_user_attribute,
    mock_get_template_folders,
):
    active_user_with_permissions["auth_type"] = "email_auth"
    service_one["permissions"].append("email_auth")

    client_request.post(
        "main.edit_user_permissions",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
        _data={
            "email_address": active_user_with_permissions["email_address"],
            "permissions_field": [
                "manage_templates",
            ],
            "login_authentication": "sms_auth",
        },
        _expected_status=302,
        _expected_redirect=url_for(
            "main.manage_users",
            service_id=SERVICE_ONE_ID,
        ),
    )

    mock_set_user_permissions.assert_called_with(
        str(active_user_with_permissions["id"]),
        SERVICE_ONE_ID,
        permissions={
            "view_activity",
            "manage_templates",
        },
        folder_permissions=[],
    )
    mock_update_user_attribute.assert_called_with(str(active_user_with_permissions["id"]), auth_type="sms_auth")


def test_edit_user_permissions_hides_authentication_for_webauthn_user(
    client_request,
    service_one,
    mock_get_users_by_service,
    mock_get_template_folders,
    active_user_with_permissions,
):
    active_user_with_permissions["auth_type"] = "webauthn_auth"
    service_one["permissions"].append("email_auth")

    page = client_request.get(
        "main.edit_user_permissions",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
    )

    assert page.select_one("#login_authentication") is None


@pytest.mark.parametrize("new_auth_type", ["sms_auth", "email_auth"])
def test_edit_user_permissions_preserves_auth_type_for_webauthn_user(
    client_request,
    service_one,
    active_user_with_permissions,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_set_user_permissions,
    mock_update_user_attribute,
    mock_get_template_folders,
    new_auth_type,
):
    active_user_with_permissions["auth_type"] = "webauthn_auth"
    service_one["permissions"].append("email_auth")

    client_request.post(
        "main.edit_user_permissions",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
        _data={
            "email_address": active_user_with_permissions["email_address"],
            "permissions_field": [],
            "login_authentication": new_auth_type,
        },
        _expected_status=302,
    )

    mock_set_user_permissions.assert_called_with(
        str(active_user_with_permissions["id"]),
        SERVICE_ONE_ID,
        permissions={"view_activity"},
        folder_permissions=[],
    )
    mock_update_user_attribute.assert_not_called()


def test_should_show_page_for_inviting_user(
    client_request,
    mock_get_template_folders,
):
    page = client_request.get(
        "main.invite_user",
        service_id=SERVICE_ONE_ID,
    )

    assert "Invite a team member" in page.select_one("h1").text.strip()
    assert not page.select_one("div.checkboxes-nested")


def test_should_show_page_for_inviting_user_with_email_prefilled(
    client_request,
    mocker,
    service_one,
    mock_get_template_folders,
    fake_uuid,
    active_user_with_permissions,
    active_user_with_permission_to_other_service,
    mock_get_organisation_by_domain,
    mock_get_invites_for_service,
    sample_invite,
):
    service_one["organisation"] = ORGANISATION_ID

    client_request.login(active_user_with_permissions)
    mocker.patch(
        "app.user_api_client.get_user",
        return_value=active_user_with_permission_to_other_service,
    )
    mocker.patch("app.models.user.PendingUsers.client_method", return_value=[sample_invite])
    page = client_request.get(
        "main.invite_user",
        service_id=SERVICE_ONE_ID,
        user_id=fake_uuid,
        # We have the user’s name in the H1 but don’t want it duplicated
        # in the page title
        _test_page_title=False,
    )
    assert normalize_spaces(page.select_one("title").text).startswith("Invite a team member")
    assert normalize_spaces(page.select_one("h1").text) == "Invite Service Two User"
    assert normalize_spaces(page.select_one("main .govuk-body").text) == "service-two-user@test.gov.uk"
    assert not page.select("input#email_address") or page.select("input[type=email]")


def test_should_show_page_if_prefilled_user_is_already_a_team_member(
    mocker,
    client_request,
    mock_get_template_folders,
    fake_uuid,
    active_user_with_permissions,
    active_user_create_broadcasts_permission,
):
    mocker.patch(
        "app.models.user.user_api_client.get_user",
        side_effect=[
            # First call is to get the current user
            active_user_with_permissions,
            # Second call gets the user to invite
            active_user_create_broadcasts_permission,
        ],
    )
    page = client_request.get(
        "main.invite_user",
        service_id=SERVICE_ONE_ID,
        user_id=fake_uuid,
    )

    assert normalize_spaces(page.select_one("title").text).startswith("This person is already a team member")
    assert normalize_spaces(page.select_one("h1").text) == "This person is already a team member"
    assert normalize_spaces(page.select_one("main .govuk-body").text) == (
        "Test User is already member of ‘service one’."
    )
    assert not page.select("form")


def test_should_show_page_if_prefilled_user_is_already_invited(
    mocker,
    client_request,
    mock_get_template_folders,
    fake_uuid,
    active_user_with_permissions,
    active_user_with_permission_to_other_service,
    mock_get_invites_for_service,
):
    active_user_with_permission_to_other_service["email_address"] = "user_1@testnotify.gov.uk"
    client_request.login(active_user_with_permissions)
    mocker.patch(
        "app.models.user.user_api_client.get_user",
        return_value=active_user_with_permission_to_other_service,
    )
    mocker.patch("app.models.service.Service.invite_pending_for", return_value=True)
    page = client_request.get(
        "main.invite_user",
        service_id=SERVICE_ONE_ID,
        user_id=fake_uuid,
    )

    assert normalize_spaces(page.select_one("title").text).startswith("This person has already received an invite")
    assert normalize_spaces(page.select_one("h1").text) == "This person has already received an invite"
    assert normalize_spaces(page.select_one("main .govuk-body").text) == (
        "Service Two User has not accepted their invitation to " "‘service one’ yet. You do not need to do anything."
    )
    assert not page.select("form")


def test_should_show_folder_permission_form_if_service_has_folder_permissions_enabled(
    client_request, mock_get_template_folders, service_one
):
    mock_get_template_folders.return_value = [
        {"id": "folder-id-1", "name": "folder_one", "parent_id": None, "users_with_permission": []},
        {"id": "folder-id-2", "name": "folder_two", "parent_id": None, "users_with_permission": []},
        {"id": "folder-id-3", "name": "folder_three", "parent_id": "folder-id-1", "users_with_permission": []},
    ]
    page = client_request.get(
        "main.invite_user",
        service_id=SERVICE_ONE_ID,
    )

    assert "Invite a team member" in page.select_one("h1").text.strip()

    folder_checkboxes = page.select_one("div.selection-wrapper").select("li")
    assert len(folder_checkboxes) == 3


@pytest.mark.parametrize("email_address, gov_user", [("test@example.gov.uk", True), ("test@example.com", False)])
def test_invite_user(
    client_request,
    active_user_with_permissions,
    mocker,
    sample_invite,
    email_address,
    gov_user,
    mock_get_template_folders,
    mock_get_organisations,
):
    sample_invite["email_address"] = email_address
    assert is_gov_user(email_address) == gov_user

    mocker.patch("app.models.user.InvitedUsers.client_method", return_value=[sample_invite])
    mocker.patch("app.models.user.Users.client_method", return_value=[active_user_with_permissions])
    mocker.patch("app.invite_api_client.create_invite", return_value=sample_invite)
    mocker.patch("app.models.user.User.from_email_address_invited", return_value=None)
    mocker.patch("app.models.user.User.belongs_to_service", return_value=gov_user)
    mocker.patch("app.models.service.Service.invite_pending_for", return_value=False)

    page = client_request.post(
        "main.invite_user",
        service_id=SERVICE_ONE_ID,
        _data={
            "email_address": email_address,
            "permissions_field": [
                "view_activity",
                "manage_templates",
                "manage_service",
                "manage_api_keys",
            ],
        },
        _follow_redirects=True,
    )
    if gov_user:
        assert page.select_one("h1").string.strip() == "Team members"

        flash_banner = page.select_one("div.banner-default-with-tick").string.strip()
        assert flash_banner == f"Invite sent to {email_address}"

        expected_permissions = {
            "manage_templates",
            "view_activity",
        }
        app.invite_api_client.create_invite.assert_called_once_with(
            sample_invite["from_user"], sample_invite["service"], email_address, expected_permissions, "sms_auth", []
        )
    else:
        assert page.select_one("h1").string.strip() == "Invite a team member"
        assert "Enter a public sector email address" in page.select_one("p.govuk-error-message").text


def test_invite_user_when_email_address_is_prefilled(
    client_request,
    service_one,
    active_user_with_permissions,
    active_user_with_permission_to_other_service,
    fake_uuid,
    mocker,
    sample_invite,
    mock_get_template_folders,
    mock_get_invites_for_service,
    mock_get_organisation_by_domain,
):
    service_one["organisation"] = ORGANISATION_ID
    client_request.login(active_user_with_permissions)
    mocker.patch(
        "app.models.user.user_api_client.get_user",
        return_value=active_user_with_permission_to_other_service,
    )
    mocker.patch("app.invite_api_client.create_invite", return_value=sample_invite)
    mocker.patch("app.models.user.PendingUsers.client_method", return_value=[sample_invite])
    client_request.post(
        "main.invite_user",
        service_id=SERVICE_ONE_ID,
        user_id=fake_uuid,
        _data={
            # No posted email address
            "permissions_field": ["view_activity"],
        },
    )

    app.invite_api_client.create_invite.assert_called_once_with(
        active_user_with_permissions["id"],
        SERVICE_ONE_ID,
        active_user_with_permission_to_other_service["email_address"],
        {"view_activity"},
        "sms_auth",
        [],
    )


@pytest.mark.parametrize("auth_type", ["sms_auth", "email_auth"])
@pytest.mark.parametrize(
    "email_address, gov_user",
    [
        ("test@example.gov.uk", True),
        ("test@example.com", False),
    ],
)
def test_invite_user_with_email_auth_service(
    client_request,
    service_one,
    active_user_with_permissions,
    sample_invite,
    email_address,
    gov_user,
    mocker,
    auth_type,
    mock_get_organisations,
    mock_get_template_folders,
):
    service_one["permissions"].append("email_auth")
    sample_invite["email_address"] = "test@example.gov.uk"

    assert is_gov_user(email_address) is gov_user
    mocker.patch("app.models.user.InvitedUsers.client_method", return_value=[sample_invite])
    mocker.patch("app.models.user.Users.client_method", return_value=[active_user_with_permissions])
    mocker.patch("app.invite_api_client.create_invite", return_value=sample_invite)
    mocker.patch("app.models.user.User.from_email_address_invited", return_value=None)
    mocker.patch("app.models.service.Service.invite_pending_for", return_value=False)

    page = client_request.post(
        "main.invite_user",
        service_id=SERVICE_ONE_ID,
        _data={
            "email_address": email_address,
            "permissions_field": [
                "view_activity",
                "manage_templates",
                "manage_service",
                "manage_api_keys",
            ],
            "login_authentication": auth_type,
        },
        _follow_redirects=True,
        _expected_status=200,
    )

    if gov_user:
        assert page.select_one("h1").string.strip() == "Team members"
        flash_banner = page.select_one("div.banner-default-with-tick").string.strip()
        assert flash_banner == "Invite sent to test@example.gov.uk"

        expected_permissions = {
            "manage_templates",
            "view_activity",
        }

        app.invite_api_client.create_invite.assert_called_once_with(
            sample_invite["from_user"], sample_invite["service"], email_address, expected_permissions, "email_auth", []
        )
    else:
        assert page.select_one("h1").string.strip() == "Invite a team member"
        assert normalize_spaces(page.select_one(".govuk-error-message").text).startswith(
            "Error: Enter a public sector email address"
        )


@pytest.mark.parametrize(
    "post_data, expected_permissions, requires_admin_action",
    (
        (
            {
                "permissions_field": [
                    "view_activity",
                    "manage_templates",
                ]
            },
            {
                "view_activity",
                "manage_templates",
            },
            False,
        ),
        (
            {
                "permissions_field": [
                    "view_activity",
                    "manage_api_keys",
                    "foo",
                ]
            },
            {
                "view_activity",
            },
            False,
        ),
        # These below permissions are sensitive and require an admin approval
        (
            {
                "permissions_field": [
                    "view_activity",
                    "create_broadcasts",
                ]
            },
            {
                "view_activity",
                "create_broadcasts",
            },
            True,
        ),
        (
            {
                "permissions_field": [
                    "view_activity",
                    "approve_broadcasts",
                    "foo",
                ]
            },
            {
                "view_activity",
                "approve_broadcasts",
            },
            True,
        ),
    ),
)
def test_invite_user_to_broadcast_service(
    client_request,
    service_one,
    active_new_user_with_permissions,
    mocker,
    sample_invite,
    mock_get_template_folders,
    mock_get_organisations,
    mock_get_pending_admin_actions,
    mock_admin_action_notification,
    post_data,
    expected_permissions,
    requires_admin_action,
):
    mocker.patch("app.models.user.User.from_email_address_invited", return_value=User(active_new_user_with_permissions))
    mocker.patch("app.models.user.PendingUsers.client_method", return_value=[sample_invite])
    mocker.patch("app.invite_api_client.create_invite", return_value=sample_invite)
    mocker.patch("app.admin_actions_api_client.create_admin_action", return_value=None)
    mocker.patch("app.models.user.User.belongs_to_service", return_value=False)

    post_data["email_address"] = "new.user@user.gov.uk"
    client_request.post(
        "main.invite_user",
        service_id=SERVICE_ONE_ID,
        _expected_status=302,
        _data=post_data,
    )

    if requires_admin_action:
        # One or more of the permissions above are sensitive and require approval
        app.invite_api_client.create_invite.assert_not_called()

        app.admin_actions_api_client.create_admin_action.assert_called_once_with(
            {
                "service_id": SERVICE_ONE_ID,
                "created_by": sample_invite["from_user"],
                "action_type": "invite_user",
                "action_data": {
                    "email_address": "new.user@user.gov.uk",
                    "permissions": expected_permissions,
                    "login_authentication": "sms_auth",
                    "folder_permissions": [],
                },
            }
        )

    else:
        # The permissions above are not 'privileged' and do not require admin approval
        app.invite_api_client.create_invite.assert_called_once_with(
            sample_invite["from_user"],
            sample_invite["service"],
            "new.user@user.gov.uk",
            expected_permissions,
            "sms_auth",
            [],
        )
        app.admin_actions_api_client.create_admin_action.assert_not_called()


def test_invite_non_govt_user_to_broadcast_service_fails_validation(
    client_request,
    service_one,
    active_user_with_permissions,
    mocker,
    sample_invite,
    mock_get_template_folders,
    mock_get_organisations,
):
    mocker.patch("app.models.user.User.from_email_address_invited", return_value=None)
    mocker.patch("app.invite_api_client.create_invite", return_value=sample_invite)
    mocker.patch("app.models.service.Service.invite_pending_for", return_value=False)
    post_data = {
        "permissions_field": [
            "manage_templates",
            "manage_service",
        ],
        "email_address": "random@example.com",
    }
    page = client_request.post("main.invite_user", service_id=SERVICE_ONE_ID, _data=post_data, _expected_status=200)
    assert app.invite_api_client.create_invite.called is False
    assert "Enter a public sector email address" in page.select_one(".govuk-error-message").text


def test_cancel_invited_user_cancels_user_invitations(
    client_request,
    mock_get_invites_for_service,
    sample_invite,
    active_user_with_permissions,
    mock_get_users_by_service,
    mock_get_template_folders,
    mocker,
):
    mock_cancel = mocker.patch("app.invite_api_client.cancel_invited_user")
    mocker.patch("app.invite_api_client.get_invited_user_for_service", return_value=sample_invite)

    page = client_request.get(
        "main.cancel_invited_user",
        service_id=SERVICE_ONE_ID,
        invited_user_id=sample_invite["id"],
        _follow_redirects=True,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Team members"
    flash_banner = normalize_spaces(page.select_one("div.banner-default-with-tick").text)
    assert flash_banner == f"Invitation cancelled for {sample_invite['email_address']}"
    mock_cancel.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        invited_user_id=sample_invite["id"],
    )


def test_cancel_invited_user_doesnt_work_if_user_not_invited_to_this_service(
    client_request,
    mock_get_invites_for_service,
    mocker,
):
    mock_cancel = mocker.patch("app.invite_api_client.cancel_invited_user")
    client_request.get(
        "main.cancel_invited_user",
        service_id=SERVICE_ONE_ID,
        invited_user_id=sample_uuid(),
        _expected_status=404,
    )
    assert mock_cancel.called is False


@pytest.mark.parametrize(
    "invite_status, expected_text",
    [
        (
            "pending",
            (
                "invited_user@test.gov.uk (invited) "
                "Cannot Add and edit templates "
                "Cannot Create new alerts "
                "Cannot Approve alerts "
                "Cancel invitation for invited_user@test.gov.uk"
            ),
        ),
        (
            "cancelled",
            (
                "invited_user@test.gov.uk (cancelled invite) "
                # all permissions are greyed out
                "Cannot Add and edit templates "
                "Cannot Create new alerts "
                "Cannot Approve alerts"
            ),
        ),
    ],
)
def test_manage_users_shows_invited_user(
    client_request,
    mocker,
    active_user_with_permissions,
    mock_get_template_folders,
    sample_invite,
    invite_status,
    expected_text,
):
    sample_invite["status"] = invite_status
    mocker.patch("app.models.user.InvitedUsers.client_method", return_value=[sample_invite])
    mocker.patch("app.models.user.Users.client_method", return_value=[active_user_with_permissions])

    page = client_request.get("main.manage_users", service_id=SERVICE_ONE_ID)
    assert page.select_one("h1").string.strip() == "Team members"
    assert normalize_spaces(page.select(".user-list-item")[0].text) == expected_text


def test_manage_users_does_not_show_accepted_invite(
    client_request,
    mocker,
    active_user_with_permissions,
    sample_invite,
    mock_get_template_folders,
):
    invited_user_id = uuid.uuid4()
    sample_invite["id"] = invited_user_id
    sample_invite["status"] = "accepted"
    mocker.patch("app.models.user.InvitedUsers.client_method", return_value=[sample_invite])
    mocker.patch("app.models.user.Users.client_method", return_value=[active_user_with_permissions])

    page = client_request.get("main.manage_users", service_id=SERVICE_ONE_ID)

    assert page.select_one("h1").string.strip() == "Team members"
    user_lists = page.select("div.user-list")
    assert len(user_lists) == 1
    assert "invited_user@test.gov.uk" not in page.text


def test_user_cant_invite_themselves(
    client_request,
    mocker,
    active_user_with_permissions,
    mock_create_invite,
    mock_get_template_folders,
):
    mocker.patch("app.models.user.User.from_email_address_invited", return_value=User(active_user_with_permissions))
    mocker.patch("app.models.user.User.belongs_to_service", return_value=True)
    mocker.patch("app.models.service.Service.invite_pending_for", return_value=False)

    page = client_request.post(
        "main.invite_user",
        service_id=SERVICE_ONE_ID,
        _data={
            "email_address": active_user_with_permissions["email_address"],
            "permissions_field": ["manage_service", "manage_api_keys"],
        },
        _follow_redirects=True,
        _expected_status=200,
    )
    assert page.select_one("h1").string.strip() == "This person is already a team member"
    assert not mock_create_invite.called


@pytest.mark.parametrize(
    "email_address",
    (
        "test@user.gov.uk",
        "TEST@user.gov.uk",
        "test@USER.gov.uk",
        "test+test@user.gov.uk",
        "te.st@user.gov.uk",
    ),
)
def test_broadcast_user_cant_invite_themselves_or_their_aliases(
    client_request,
    service_one,
    mocker,
    active_user_with_permissions,
    mock_create_invite,
    mock_get_template_folders,
    email_address,
):
    mocker.patch("app.models.user.User.from_email_address_invited", return_value=User(active_user_with_permissions))
    mocker.patch("app.models.user.User.belongs_to_service", return_value=True)
    mocker.patch("app.models.service.Service.invite_pending_for", return_value=False)

    page = client_request.post(
        "main.invite_user",
        service_id=SERVICE_ONE_ID,
        _data={"email_address": email_address, "permissions_field": []},
        _expected_status=200,
    )

    assert normalize_spaces(page.select_one("main h1").text) == ("This person is already a team member")
    assert mock_create_invite.called is False


def test_platform_admin_cant_invite_themselves_to_broadcast_services(
    client_request,
    service_one,
    mocker,
    platform_admin_user,
    mock_create_invite,
    mock_get_template_folders,
):
    mocker.patch("app.models.user.User.from_email_address_invited", return_value=User(platform_admin_user))
    mocker.patch("app.models.user.User.belongs_to_service", return_value=True)
    mocker.patch("app.models.service.Service.invite_pending_for", return_value=False)

    client_request.login(platform_admin_user)
    page = client_request.post(
        "main.invite_user",
        service_id=SERVICE_ONE_ID,
        _data={"email_address": platform_admin_user["email_address"], "permissions_field": []},
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one("main h1").text) == ("This person is already a team member")
    assert mock_create_invite.called is False


def test_no_permission_manage_users_page(
    client_request,
    service_one,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_get_template_folders,
    api_user_active,
    mocker,
):
    resp_text = client_request.get("main.manage_users", service_id=service_one["id"])
    assert url_for(".invite_user", service_id=service_one["id"]) not in resp_text
    assert "Edit permission" not in resp_text
    assert "Team members" not in resp_text


@pytest.mark.parametrize(
    "folders_user_can_see, expected_message",
    [
        (3, "Can see all folders"),
        (2, "Can see 2 folders"),
        (1, "Can see 1 folder"),
        (0, "Cannot see any folders"),
    ],
)
def test_manage_user_page_shows_how_many_folders_user_can_view(
    client_request,
    service_one,
    mock_get_template_folders,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    api_user_active,
    folders_user_can_see,
    expected_message,
):
    service_one["permissions"] = ["edit_folder_permissions"]
    mock_get_template_folders.return_value = [
        {"id": "folder-id-1", "name": "f1", "parent_id": None, "users_with_permission": []},
        {"id": "folder-id-2", "name": "f2", "parent_id": None, "users_with_permission": []},
        {"id": "folder-id-3", "name": "f3", "parent_id": None, "users_with_permission": []},
    ]
    for i in range(folders_user_can_see):
        mock_get_template_folders.return_value[i]["users_with_permission"].append(api_user_active["id"])

    page = client_request.get("main.manage_users", service_id=service_one["id"])

    user_div = page.select_one("h2[title='notify@digital.cabinet-office.gov.uk']").parent
    assert user_div.select_one(".tick-cross-list-hint:last-child").text.strip() == expected_message


def test_manage_user_page_doesnt_show_folder_hint_if_service_has_no_folders(
    client_request,
    service_one,
    mock_get_template_folders,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    api_user_active,
):
    service_one["permissions"] = ["edit_folder_permissions"]
    mock_get_template_folders.return_value = []

    page = client_request.get("main.manage_users", service_id=service_one["id"])

    user_div = page.select_one("h2[title='notify@digital.cabinet-office.gov.uk']").parent
    assert user_div.find(".tick-cross-list-hint:last-child") is None


def test_manage_user_page_doesnt_show_folder_hint_if_service_cant_edit_folder_permissions(
    client_request,
    service_one,
    mock_get_template_folders,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    api_user_active,
):
    service_one["permissions"] = []
    mock_get_template_folders.return_value = [
        {"id": "folder-id-1", "name": "f1", "parent_id": None, "users_with_permission": [api_user_active["id"]]},
    ]

    page = client_request.get("main.manage_users", service_id=service_one["id"])

    user_div = page.select_one("h2[title='notify@digital.cabinet-office.gov.uk']").parent
    assert user_div.find(".tick-cross-list-hint:last-child") is None


def test_remove_user_from_service(
    client_request, active_user_with_permissions, api_user_active, service_one, mock_remove_user_from_service, mocker
):
    mock_event_handler = mocker.patch("app.main.views.manage_users.create_remove_user_from_service_event")

    client_request.post(
        "main.remove_user_from_service",
        service_id=service_one["id"],
        user_id=active_user_with_permissions["id"],
        _expected_redirect=url_for("main.manage_users", service_id=service_one["id"]),
    )
    mock_remove_user_from_service.assert_called_once_with(service_one["id"], str(active_user_with_permissions["id"]))

    mock_event_handler.assert_called_once_with(
        user_id=active_user_with_permissions["id"],
        removed_by_id=api_user_active["id"],
        service_id=service_one["id"],
    )


def test_can_invite_user_as_platform_admin(
    client_request,
    service_one,
    platform_admin_user,
    active_user_with_permissions,
    mock_get_invites_for_service,
    mock_get_template_folders,
    mocker,
):
    mocker.patch("app.models.user.Users.client_method", return_value=[active_user_with_permissions])

    page = client_request.get(
        "main.manage_users",
        service_id=SERVICE_ONE_ID,
    )
    assert url_for(".invite_user", service_id=service_one["id"]) in str(page)


def test_edit_user_email_page(
    client_request, active_user_with_permissions, service_one, mock_get_users_by_service, mocker
):
    user = active_user_with_permissions
    mocker.patch("app.user_api_client.get_user", return_value=user)

    page = client_request.get("main.edit_user_email", service_id=service_one["id"], user_id=sample_uuid())

    assert page.select_one("h1").text == "Change team member’s email address"
    assert page.select("p[id=user_name]")[0].text == "This will change the email address for {}.".format(user["name"])
    assert page.select("input[type=email]")[0].attrs["value"] == user["email_address"]
    assert normalize_spaces(page.select("form button")[0].text) == "Save"


def test_edit_user_email_page_404_for_non_team_member(
    client_request,
    mock_get_users_by_service,
):
    client_request.get(
        "main.edit_user_email",
        service_id=SERVICE_ONE_ID,
        user_id=USER_ONE_ID,
        _expected_status=404,
    )


def test_edit_user_email_redirects_to_confirmation(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
    mock_check_user_exists_for_nonexistent_user,
):
    client_request.post(
        "main.edit_user_email",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
        _expected_status=302,
        _expected_redirect=url_for(
            "main.confirm_edit_user_email",
            service_id=SERVICE_ONE_ID,
            user_id=active_user_with_permissions["id"],
        ),
    )
    with client_request.session_transaction() as session:
        assert session["team_member_email_change-{}".format(active_user_with_permissions["id"])] == "test@user.gov.uk"


def test_edit_user_email_without_changing_renders_form_error(
    client_request,
    active_user_with_permissions,
    mock_get_user_by_email,
    mock_get_users_by_service,
    mock_update_user_attribute,
):
    page = client_request.post(
        "main.edit_user_email",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
        _data={"email_address": active_user_with_permissions["email_address"]},
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one(".govuk-error-message").text) == (
        "Error: Email address must be different to current email address"
    )
    assert mock_update_user_attribute.called is False


@pytest.mark.parametrize("original_email_address", ["test@gov.uk", "test@example.com"])
def test_edit_user_email_can_change_any_email_address_to_a_gov_email_address(
    client_request,
    active_user_with_permissions,
    mock_check_user_exists_for_nonexistent_user,
    mock_get_users_by_service,
    mock_update_user_attribute,
    mock_get_organisations,
    original_email_address,
):
    active_user_with_permissions["email_address"] = original_email_address

    client_request.post(
        "main.edit_user_email",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
        _data={"email_address": "new-email-address@gov.uk"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.confirm_edit_user_email",
            service_id=SERVICE_ONE_ID,
            user_id=active_user_with_permissions["id"],
        ),
    )


def test_edit_user_email_can_change_a_non_gov_email_address_to_another_non_gov_email_address(
    client_request,
    active_user_with_permissions,
    mock_check_user_exists_for_nonexistent_user,
    mock_get_users_by_service,
    mock_update_user_attribute,
    mock_get_organisations,
):
    active_user_with_permissions["email_address"] = "old@example.com"

    client_request.post(
        "main.edit_user_email",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
        _data={"email_address": "new@example.com"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.confirm_edit_user_email",
            service_id=SERVICE_ONE_ID,
            user_id=active_user_with_permissions["id"],
        ),
    )


def test_edit_user_email_cannot_change_a_gov_email_address_to_a_non_gov_email_address(
    client_request,
    active_user_with_permissions,
    mock_get_user_by_email_not_found,
    mock_get_users_by_service,
    mock_update_user_attribute,
    mock_get_organisations,
):
    page = client_request.post(
        "main.edit_user_email",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
        _data={"email_address": "new_email@example.com"},
        _expected_status=200,
    )
    assert "Enter a public sector email address" in page.select_one(".govuk-error-message").text
    with client_request.session_transaction() as session:
        assert "team_member_email_change-{}".format(active_user_with_permissions["id"]) not in session


def test_confirm_edit_user_email_page(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
    mock_get_user,
):
    new_email = "new_email@gov.uk"
    with client_request.session_transaction() as session:
        session["team_member_email_change-{}".format(active_user_with_permissions["id"])] = new_email

    page = client_request.get(
        "main.confirm_edit_user_email",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
    )

    assert "Confirm change of email address" in page.text
    for text in [
        "New email address:",
        new_email,
        "We will send {} an email to tell them about the change.".format(active_user_with_permissions["name"]),
    ]:
        assert text in page.text
    assert "Confirm" in page.text


def test_confirm_edit_user_email_page_redirects_if_session_empty(
    client_request,
    mock_get_users_by_service,
    active_user_with_permissions,
):
    page = client_request.get(
        "main.confirm_edit_user_email",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
        _follow_redirects=True,
    )
    assert "Confirm change of email address" not in page.text


def test_confirm_edit_user_email_page_404s_for_non_team_member(
    client_request,
    mock_get_users_by_service,
):
    client_request.get(
        "main.confirm_edit_user_email",
        service_id=SERVICE_ONE_ID,
        user_id=USER_ONE_ID,
        _expected_status=404,
    )


def test_confirm_edit_user_email_changes_user_email(
    client_request,
    active_user_with_permissions,
    api_user_active,
    service_one,
    mocker,
    mock_update_user_attribute,
):
    # We want active_user_with_permissions (the current user) to update the email address for api_user_active
    # By default both users would have the same id, so we change the id of api_user_active
    api_user_active["id"] = str(uuid.uuid4())
    mocker.patch("app.models.user.Users.client_method", return_value=[api_user_active, active_user_with_permissions])
    # get_user gets called twice - first to check if current user can see the page, then to see if the team member
    # whose email address we're changing belongs to the service
    mocker.patch("app.user_api_client.get_user", side_effect=[active_user_with_permissions, api_user_active])
    mock_event_handler = mocker.patch("app.main.views.manage_users.create_email_change_event")

    new_email = "new_email@gov.uk"
    with client_request.session_transaction() as session:
        session["team_member_email_change-{}".format(api_user_active["id"])] = new_email

    client_request.post(
        "main.confirm_edit_user_email",
        service_id=service_one["id"],
        user_id=api_user_active["id"],
        _expected_status=302,
        _expected_redirect=url_for(
            "main.manage_users",
            service_id=SERVICE_ONE_ID,
        ),
    )

    mock_update_user_attribute.assert_called_once_with(
        api_user_active["id"], email_address=new_email, updated_by=active_user_with_permissions["id"]
    )
    mock_event_handler.assert_called_once_with(
        user_id=api_user_active["id"],
        updated_by_id=active_user_with_permissions["id"],
        original_email_address=api_user_active["email_address"],
        new_email_address=new_email,
    )


def test_confirm_edit_user_email_doesnt_change_user_email_for_non_team_member(
    client_request,
    mock_get_users_by_service,
):
    with client_request.session_transaction() as session:
        session["team_member_email_change"] = "new_email@gov.uk"
    client_request.post(
        "main.confirm_edit_user_email",
        service_id=SERVICE_ONE_ID,
        user_id=USER_ONE_ID,
        _expected_status=404,
    )


def test_edit_user_permissions_page_displays_redacted_mobile_number_and_change_link(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
    mock_get_template_folders,
    service_one,
    mocker,
):
    page = client_request.get(
        "main.edit_user_permissions",
        service_id=service_one["id"],
        user_id=active_user_with_permissions["id"],
    )

    assert active_user_with_permissions["name"] in page.select_one("h1").text
    mobile_number_paragraph = page.select("p[id=user_mobile_number]")[0]
    assert "0770 •  •  •  • 762" in mobile_number_paragraph.text
    change_link = mobile_number_paragraph.findChild()
    assert change_link.attrs["href"] == "/services/{}/users/{}/edit-mobile-number".format(
        service_one["id"], active_user_with_permissions["id"]
    )


def test_edit_user_permissions_with_delete_query_shows_banner(
    client_request, active_user_with_permissions, mock_get_users_by_service, mock_get_template_folders, service_one
):
    page = client_request.get(
        "main.edit_user_permissions",
        service_id=service_one["id"],
        user_id=active_user_with_permissions["id"],
        delete=1,
        _test_page_prefix="Are you sure you want to remove Test User?",
    )

    banner = page.select_one("div.banner-dangerous")
    assert banner.contents[0].strip() == "Are you sure you want to remove Test User?"
    assert banner.form.attrs["action"] == url_for(
        "main.remove_user_from_service", service_id=service_one["id"], user_id=active_user_with_permissions["id"]
    )


def test_edit_user_mobile_number_page(
    client_request, active_user_with_permissions, mock_get_users_by_service, service_one, mocker
):
    page = client_request.get(
        "main.edit_user_mobile_number",
        service_id=service_one["id"],
        user_id=active_user_with_permissions["id"],
    )

    assert page.select_one("h1").text == "Change team member’s mobile number"
    assert page.select("p[id=user_name]")[0].text == "This will change the mobile number for {}.".format(
        active_user_with_permissions["name"]
    )
    assert page.select("input[name=mobile_number]")[0].attrs["value"] == "0770••••762"
    assert normalize_spaces(page.select("form button")[0].text) == "Save"


def test_edit_user_mobile_number_redirects_to_confirmation(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
):
    client_request.post(
        "main.edit_user_mobile_number",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
        _data={"mobile_number": "07554080636"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.confirm_edit_user_mobile_number",
            service_id=SERVICE_ONE_ID,
            user_id=active_user_with_permissions["id"],
        ),
    )


def test_edit_user_mobile_number_renders_form_error(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
    mock_update_user_attribute,
    service_one,
    mocker,
    mock_get_user,
):
    page = client_request.post(
        "main.edit_user_mobile_number",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
        _data={"mobile_number": "0770••••762"},
        _expected_status=200,
    )

    assert normalize_spaces(page.select_one(".govuk-error-message").text) == (
        "Error: Mobile number must be different to current mobile number"
    )
    assert mock_update_user_attribute.called is False


def test_confirm_edit_user_mobile_number_page(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
    service_one,
    mocker,
    mock_get_user,
):
    new_number = "07554080636"
    with client_request.session_transaction() as session:
        session["team_member_mobile_change"] = new_number
    page = client_request.get(
        "main.confirm_edit_user_mobile_number",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
    )

    assert "Confirm change of mobile number" in page.text
    for text in [
        "New mobile number:",
        new_number,
        "We will send {} a text message to tell them about the change.".format(active_user_with_permissions["name"]),
    ]:
        assert text in page.text
    assert "Confirm" in page.text


def test_confirm_edit_user_mobile_number_page_redirects_if_session_empty(
    client_request,
    active_user_with_permissions,
    mock_get_users_by_service,
    service_one,
    mocker,
    mock_get_user,
):
    page = client_request.get(
        "main.confirm_edit_user_mobile_number",
        service_id=SERVICE_ONE_ID,
        user_id=active_user_with_permissions["id"],
        _expected_status=302,
    )
    assert "Confirm change of mobile number" not in page.text


def test_confirm_edit_user_mobile_number_changes_user_mobile_number(
    client_request, active_user_with_permissions, api_user_active, service_one, mocker, mock_update_user_attribute
):
    # We want active_user_with_permissions (the current user) to update the mobile number for api_user_active
    # By default both users would have the same id, so we change the id of api_user_active
    api_user_active["id"] = str(uuid.uuid4())

    mocker.patch("app.models.user.Users.client_method", return_value=[api_user_active, active_user_with_permissions])
    # get_user gets called twice - first to check if current user can see the page, then to see if the team member
    # whose mobile number we're changing belongs to the service
    mocker.patch("app.user_api_client.get_user", side_effect=[active_user_with_permissions, api_user_active])
    mock_event_handler = mocker.patch("app.main.views.manage_users.create_mobile_number_change_event")

    new_number = "07554080636"
    with client_request.session_transaction() as session:
        session["team_member_mobile_change"] = new_number

    client_request.post(
        "main.confirm_edit_user_mobile_number",
        service_id=SERVICE_ONE_ID,
        user_id=api_user_active["id"],
        _expected_status=302,
        _expected_redirect=url_for(
            "main.manage_users",
            service_id=SERVICE_ONE_ID,
        ),
    )
    mock_update_user_attribute.assert_called_once_with(
        api_user_active["id"], mobile_number=new_number, updated_by=active_user_with_permissions["id"]
    )
    mock_event_handler.assert_called_once_with(
        user_id=api_user_active["id"],
        updated_by_id=active_user_with_permissions["id"],
        original_mobile_number=api_user_active["mobile_number"],
        new_mobile_number=new_number,
    )


def test_confirm_edit_user_mobile_number_doesnt_change_user_mobile_for_non_team_member(
    client_request,
    mock_get_users_by_service,
):
    with client_request.session_transaction() as session:
        session["team_member_mobile_change"] = "07554080636"
    client_request.post(
        "main.confirm_edit_user_mobile_number",
        service_id=SERVICE_ONE_ID,
        user_id=USER_ONE_ID,
        _expected_status=404,
    )
