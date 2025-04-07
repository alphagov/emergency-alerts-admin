import uuid

import pytest

from app.utils.admin_action import create_or_replace_admin_action
from tests.conftest import SERVICE_ONE_ID


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
                    "user_id": SERVICE_ONE_ID,
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
                        "user_id": SERVICE_ONE_ID,
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
                    "user_id": SERVICE_ONE_ID,
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
