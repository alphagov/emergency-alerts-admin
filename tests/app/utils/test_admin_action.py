import uuid

import pytest
from emergency_alerts_utils.clients.zendesk.zendesk_client import EASSupportTicket
from freezegun import freeze_time

from app.models.service import Service
from app.utils.admin_action import (
    _create_or_upgrade_zendesk_ticket,
    _is_out_of_office_hours,
    create_or_replace_admin_action,
    send_elevation_notifications,
    send_notifications,
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
            send_notifications("approved", action_obj, service)

    sender.assert_called_once()
    slack_message = sender.call_args[0][0]
    slack_message_properties = slack_message.__dict__

    assert slack_message_properties["markdown_sections"][0] == expected_markdown
    assert slack_message_properties["markdown_sections"][1] == "_Created by `platform@admin.gov.uk`_"
    assert slack_message_properties["markdown_sections"][2] == ":green_tick: Approved by `platform@admin.gov.uk`"


@pytest.mark.parametrize("is_out_of_hours", [False, True])
def test_elevation_notifications_message(
    mocker, mock_get_user, notify_admin, client_request, platform_admin_user, is_out_of_hours
):
    slack_sender = mocker.patch("emergency_alerts_utils.clients.slack.slack_client.SlackClient.send_message_to_slack")
    zendesk_sender = mocker.patch(
        "emergency_alerts_utils.clients.zendesk.zendesk_client.ZendeskClient.send_ticket_to_zendesk"
    )

    with freeze_time("2020-11-11T01:00:00Z" if is_out_of_hours else "2020-11-11T12:00:00Z"):
        with set_config(notify_admin, "SLACK_WEBHOOK_ADMIN_ACTIVITY", "https://test"):
            # Uses current_user so we need a 'logged in' user and a request context:
            client_request.login(platform_admin_user)
            with notify_admin.test_request_context(method="POST"):
                send_elevation_notifications()

    slack_sender.assert_called_once()
    slack_message = slack_sender.call_args[0][0]
    slack_message_properties = slack_message.__dict__

    assert (
        slack_message_properties["markdown_sections"][0]
        == "`platform@admin.gov.uk` has elevated to become a full platform admin for their session"
    )

    if is_out_of_hours:
        zendesk_sender.assert_not_called()
    else:
        zendesk_sender.assert_called_once()
        zendesk_ticket_json = zendesk_sender.call_args[0][0]
        assert zendesk_ticket_json == {"id": "yes"}


def test_create_or_upgrade_zendesk_ticket_creates(mocker):
    zendesk_get = mocker.patch(
        "emergency_alerts_utils.clients.zendesk.zendesk_client"
        + ".ZendeskClient.get_open_admin_zendesk_ticket_id_for_email",
        return_value=None,
    )
    zendesk_sender = mocker.patch(
        "emergency_alerts_utils.clients.zendesk.zendesk_client.ZendeskClient.send_ticket_to_zendesk"
    )

    email = "test@digital.cabinet-office.gov.uk"
    _create_or_upgrade_zendesk_ticket("urgent", "test", email)

    zendesk_get.assert_called_once_with(email)
    zendesk_sender.assert_called_once()
    assert (
        zendesk_sender.call_args[0][0].__dict__
        == EASSupportTicket(
            subject="Out of Hours Admin Activity",
            message="test",
            ticket_type=EASSupportTicket.TYPE_INCIDENT,
            p1=True,
            user_email=email,
        ).__dict__
    )


def test_create_or_upgrade_zendesk_ticket_updates_if_exists(mocker):
    zendesk_get = mocker.patch(
        "emergency_alerts_utils.clients.zendesk.zendesk_client"
        + ".ZendeskClient.get_open_admin_zendesk_ticket_id_for_email",
        return_value=123,
    )
    zendesk_update = mocker.patch(
        "emergency_alerts_utils.clients.zendesk.zendesk_client.ZendeskClient.update_ticket_priority_with_comment"
    )
    zendesk_sender = mocker.patch(
        "emergency_alerts_utils.clients.zendesk.zendesk_client.ZendeskClient.send_ticket_to_zendesk"
    )

    email = "test@digital.cabinet-office.gov.uk"
    _create_or_upgrade_zendesk_ticket("urgent", "test", email)

    zendesk_get.assert_called_once_with(email)
    zendesk_update.assert_called_once_with(123, "urgent", "test")
    zendesk_sender.assert_not_called()


@pytest.mark.parametrize(
    "datetime_utc, expected_out_of_hours",
    [
        # Winter time
        ("2020-11-11T06:59:00Z", True),
        ("2020-11-11T07:00:00Z", True),
        ("2020-11-11T07:59:00Z", True),
        ("2020-11-11T08:00:00Z", False),
        ("2020-11-11T08:01:00Z", False),
        ("2020-11-11T17:59:00Z", False),
        ("2020-11-11T18:00:00Z", True),
        ("2020-11-11T18:01:00Z", True),
        ("2020-11-11T19:00:00Z", True),
        # Summer time: these times will have one hour added on locally due to DST
        # as it's parsed with the Europe/London timezone
        ("2020-05-05T06:59:00Z", True),
        ("2020-05-05T07:00:00Z", False),
        ("2020-05-05T07:59:00Z", False),
        ("2020-05-05T08:00:00Z", False),
        ("2020-05-05T08:01:00Z", False),
        ("2020-05-05T16:59:00Z", False),
        ("2020-05-05T17:00:00Z", True),
        ("2020-05-05T18:00:00Z", True),
        ("2020-05-05T19:00:00Z", True),
    ],
)
def test_is_out_of_office_hours(datetime_utc, expected_out_of_hours):
    with freeze_time(datetime_utc):
        assert _is_out_of_office_hours() == expected_out_of_hours
