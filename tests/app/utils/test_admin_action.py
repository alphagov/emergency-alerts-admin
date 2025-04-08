import uuid

import pytest

from app.models.service import Service
from app.utils.admin_action import (
    create_or_replace_admin_action,
    send_slack_notification,
)
from tests.conftest import SERVICE_ONE_ID, USER_ONE_ID, set_config


@pytest.mark.parametrize(
    "existing_actions, proposed_action_obj, expect_invalidation",
    [
        # User invites
        (
            [],
            {
                "service_id": SERVICE_ONE_ID,
                "action_type": "invite_user",
                "action_data": {
                    "email_address": "test@test.com",
                    "permissions": ["create_broadcasts"],
                    "login_authentication": "email_auth",
                    "folder_permissions": [str(uuid.uuid4())],
                },
            },
            False,
        ),
        (
            [
                [
                    {
                        "id": str(uuid.uuid4()),
                        "service_id": SERVICE_ONE_ID,
                        "action_type": "invite_user",
                        "action_data": {
                            "email_address": "test@test.com",
                            "permissions": ["create_broadcasts"],
                            "login_authentication": "email_auth",
                            "folder_permissions": [str(uuid.uuid4())],
                        },
                    }
                ],
                {
                    "service_id": SERVICE_ONE_ID,
                    "action_type": "invite_user",
                    "action_data": {
                        "email_address": "test@test.com",
                        "permissions": ["approve_broadcasts"],
                        "login_authentication": "email_auth",
                        "folder_permissions": [str(uuid.uuid4())],
                    },
                },
                True,
            ]
        ),
        (
            [
                [
                    {
                        "id": str(uuid.uuid4()),
                        "service_id": SERVICE_ONE_ID,
                        "action_type": "invite_user",
                        "action_data": {
                            "email_address": "test@test.com",
                            "permissions": ["create_broadcasts"],
                            "login_authentication": "email_auth",
                            "folder_permissions": [str(uuid.uuid4())],
                        },
                    }
                ],
                {
                    "service_id": SERVICE_ONE_ID,
                    "action_type": "invite_user",
                    "action_data": {
                        "email_address": "test2@test.com",
                        "permissions": ["approve_broadcasts"],
                        "login_authentication": "email_auth",
                        "folder_permissions": [str(uuid.uuid4())],
                    },
                },
                False,  # Different email
            ]
        ),
        # Edit permissions
        (
            [],
            {
                "service_id": SERVICE_ONE_ID,
                "action_type": "edit_permissions",
                "action_data": {
                    "user_id": USER_ONE_ID,
                    "existing_permissions": ["create_broadcasts"],
                    "permissions": ["create_broadcasts", "approve_broadcasts"],
                    "folder_permissions": [str(uuid.uuid4())],
                },
            },
            False,
        ),
        (
            [
                {
                    "id": str(uuid.uuid4()),
                    "service_id": SERVICE_ONE_ID,
                    "action_type": "edit_permissions",
                    "action_data": {
                        "user_id": USER_ONE_ID,
                        "existing_permissions": ["create_broadcasts"],
                        "permissions": ["create_broadcasts", "approve_broadcasts"],
                        "folder_permissions": [str(uuid.uuid4())],
                    },
                }
            ],
            {
                "service_id": SERVICE_ONE_ID,
                "action_type": "edit_permissions",
                "action_data": {
                    "user_id": USER_ONE_ID,
                    "existing_permissions": ["create_broadcasts"],
                    "permissions": ["create_broadcasts", "approve_broadcasts", "manage_templates"],
                    "folder_permissions": [str(uuid.uuid4())],
                },
            },
            True,
        ),
        # API keys
        (
            [],
            {
                "service_id": SERVICE_ONE_ID,
                "action_type": "create_api_key",
                "action_data": {
                    "key_type": "normal",
                    "key_name": "New Key",
                },
            },
            False,
        ),
        (
            [
                {
                    "id": str(uuid.uuid4()),
                    "service_id": SERVICE_ONE_ID,
                    "action_type": "create_api_key",
                    "action_data": {
                        "key_type": "normal",
                        "key_name": "New Key",
                    },
                }
            ],
            {
                "service_id": SERVICE_ONE_ID,
                "action_type": "create_api_key",
                "action_data": {
                    "key_type": "team",
                    "key_name": "New Key",
                },
            },
            True,
        ),
        # Elevation
        (
            [
                {
                    "id": str(uuid.uuid4()),
                    "created_by": SERVICE_ONE_ID,
                    "action_type": "elevate_platform_admin",
                    "action_data": {},
                }
            ],
            {
                "created_by": SERVICE_ONE_ID,
                "action_type": "elevate_platform_admin",
                "action_data": {},
            },
            True,
        ),
    ],
)
def test_similar_admin_actions_are_invalidated(
    mocker, mock_admin_action_notification, existing_actions, proposed_action_obj, expect_invalidation
):
    mocker.patch("app.admin_actions_api_client.get_pending_admin_actions", return_value={"pending": existing_actions})
    creator = mocker.patch("app.admin_actions_api_client.create_admin_action", return_value=None)
    reviewer = mocker.patch("app.admin_actions_api_client.review_admin_action", return_value=None)

    create_or_replace_admin_action(proposed_action_obj)

    creator.assert_called_once_with(proposed_action_obj)
    if expect_invalidation:
        reviewer.assert_called_once_with(existing_actions[0]["id"], "invalidated")
    else:
        reviewer.assert_not_called()


@pytest.mark.parametrize(
    "action_obj, expected_markdown",
    [
        (
            {
                "service_id": SERVICE_ONE_ID,
                "created_by": USER_ONE_ID,
                "action_type": "invite_user",
                "action_data": {
                    "email_address": "test@test.com",
                    "permissions": ["create_broadcasts"],
                    "login_authentication": "email_auth",
                    "folder_permissions": [str(uuid.uuid4())],
                },
            },
            """Invite user `test@test.com` to service `service one`.

With permissions:
- Create new alerts""",
        ),
        (
            {
                "service_id": SERVICE_ONE_ID,
                "created_by": USER_ONE_ID,
                "action_type": "create_api_key",
                "action_data": {
                    "key_type": "normal",
                    "key_name": "New Key",
                },
            },
            "Create normal API key `New Key` in service `service one`.",
        ),
        (
            {
                "service_id": SERVICE_ONE_ID,
                "created_by": USER_ONE_ID,
                "action_type": "edit_permissions",
                "action_data": {
                    "user_id": USER_ONE_ID,
                    "existing_permissions": ["create_broadcasts"],
                    "permissions": ["create_broadcasts", "approve_broadcasts", "manage_templates"],
                    "folder_permissions": [str(uuid.uuid4())],
                },
            },
            """Edit user `platform@admin.gov.uk`'s permissions in service `service one`.

With permissions:
- Create new alerts
- Approve alerts
- Add and edit templates""",
        ),
        (
            {
                "created_by": SERVICE_ONE_ID,
                "action_type": "elevate_platform_admin",
                "action_data": {},
            },
            """Elevate themselves to become a full platform admin
_(This request will automatically expire)_""",
        ),
    ],
)
def test_slack_notification_message(
    action_obj, expected_markdown, mocker, mock_get_user, service_one, notify_admin, client_request, platform_admin_user
):
    sender = mocker.patch("emergency_alerts_utils.clients.slack.slack_client.SlackClient.send_message_to_slack")
    service = Service(service_one)

    with set_config(notify_admin, "SLACK_WEBHOOK_ADMIN_ACTIVITY", "https://test"):
        # Uses current_user so we need a 'logged in' user and a request context:
        client_request.login(platform_admin_user)
        with notify_admin.test_request_context(method="POST"):
            send_slack_notification("approved", action_obj, service)

    sender.assert_called_once()
    slack_message = sender.call_args[0][0]
    slack_message_properties = slack_message.__dict__

    assert slack_message_properties["markdown_sections"][0] == expected_markdown
    assert slack_message_properties["markdown_sections"][1] == "_Created by `platform@admin.gov.uk`_"
    assert slack_message_properties["markdown_sections"][2] == ":green_tick: Approved by `platform@admin.gov.uk`"
