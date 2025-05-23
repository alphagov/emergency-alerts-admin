from datetime import datetime
from typing import Iterable

from emergency_alerts_utils.admin_action import (
    ADMIN_CREATE_API_KEY,
    ADMIN_EDIT_PERMISSIONS,
    ADMIN_ELEVATE_USER,
    ADMIN_INVITE_USER,
    ADMIN_SENSITIVE_PERMISSIONS,
    ADMIN_STATUS_APPROVED,
    ADMIN_STATUS_INVALIDATED,
    ADMIN_STATUS_PENDING,
    ADMIN_STATUS_REJECTED,
    ADMIN_ZENDESK_OFFICE_HOURS_END,
    ADMIN_ZENDESK_OFFICE_HOURS_START,
    ADMIN_ZENDESK_OFFICE_HOURS_TIMEZONE,
    ADMIN_ZENDESK_PRIORITY_APPROVE,
    ADMIN_ZENDESK_PRIORITY_ELEVATED,
    ADMIN_ZENDESK_PRIORITY_REQUEST,
)
from emergency_alerts_utils.api_key import KEY_TYPE_NORMAL
from emergency_alerts_utils.clients.slack.slack_client import SlackClient, SlackMessage
from emergency_alerts_utils.clients.zendesk.zendesk_client import EASSupportTicket
from flask import abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app import current_service
from app.extensions import zendesk_client
from app.formatters import email_safe
from app.models.service import Service
from app.models.user import InvitedUser, User
from app.notify_client.admin_actions_api_client import admin_actions_api_client
from app.notify_client.api_key_api_client import api_key_api_client
from app.notify_client.user_api_client import user_api_client
from app.utils.user_permissions import broadcast_permission_options, permission_options

slack_client = SlackClient()


def process_admin_action(action_obj):
    """
    Process an admin action - i.e, it's been approved and we now need to actuate the relevant API to fulfil it
    """

    # See the JSON schema in admin_action in the API:
    action_type = action_obj["action_type"]
    action_data = action_obj["action_data"]
    service_id = action_obj["service_id"]

    if action_type == ADMIN_INVITE_USER:
        InvitedUser.create(
            action_obj["created_by"],
            service_id,
            action_data["email_address"],
            action_data["permissions"],
            action_data["login_authentication"],
            action_data["folder_permissions"],
        )
        flash("Sent invite to user " + action_data["email_address"], "default_with_tick")
        return redirect(url_for(".manage_users", service_id=service_id))
    elif action_type == ADMIN_EDIT_PERMISSIONS:
        user = User.from_id(action_data["user_id"])
        user.set_permissions(
            service_id,
            permissions=action_data["permissions"],
            folder_permissions=action_data["folder_permissions"],
            set_by_id=current_user.id,
        )
        flash("Updated permissions for " + user.email_address, "default_with_tick")
        return redirect(url_for(".manage_users", service_id=service_id))
    elif action_type == ADMIN_CREATE_API_KEY:
        service = Service.from_id(service_id)
        if service.trial_mode and action_data["key_type"] == KEY_TYPE_NORMAL:
            abort(400)
        secret = api_key_api_client.create_api_key(
            service_id=service_id, key_name=action_data["key_name"], key_type=action_data["key_type"]
        )
        # The template uses has_permissions and requires the service ID to be in the request args
        request.view_args["service_id"] = service_id
        return render_template(
            "views/api/keys/show.html",
            secret=secret,
            service_id=service_id,
            key_name=email_safe(action_data["key_name"], whitespace="_"),
        )
    elif action_type == ADMIN_ELEVATE_USER:
        user_api_client.elevate_admin_next_login(action_obj["created_by"], current_user.id)
        flash("The user is approved to become a full platform admin for the next session", "default_with_tick")
        return redirect(url_for(".admin_actions"))
    else:
        raise Exception("Unknown admin action " + action_type)


def permissions_require_admin_action(new_permissions: Iterable[str]):
    return bool(set(new_permissions) & set(ADMIN_SENSITIVE_PERMISSIONS))


def create_or_replace_admin_action(proposed_action_obj):
    """
    Create an admin action, replacing (or doing nothing if identical) any existing admin actions for a given subject.
    It will also send a notification to Slack.
    E.g. editing a user but with a different set of permissions to a previous pending admin action.
    """

    pending_admin_actions = admin_actions_api_client.get_pending_admin_actions()["pending"]

    for pending_action in pending_admin_actions:
        if _admin_action_is_similar(proposed_action_obj, pending_action):
            # Invalidate the existing one
            admin_actions_api_client.review_admin_action(
                pending_action["id"],
                ADMIN_STATUS_INVALIDATED,
            )

    admin_actions_api_client.create_admin_action(proposed_action_obj)
    send_notifications(ADMIN_STATUS_PENDING, proposed_action_obj, current_service)


def _admin_action_is_similar(action_obj1, action_obj2):
    """
    Similar being related to the same subject, e.g. inviting the same user to the same service.
    """
    # service_id is optional
    if action_obj1.get("service_id") != action_obj2.get("service_id"):
        return False

    if action_obj1["action_type"] != action_obj2["action_type"]:
        return False

    if action_obj1["action_type"] == ADMIN_INVITE_USER:
        return action_obj1["action_data"]["email_address"] == action_obj2["action_data"]["email_address"]
    elif action_obj1["action_type"] == ADMIN_EDIT_PERMISSIONS:
        return action_obj1["action_data"]["user_id"] == action_obj2["action_data"]["user_id"]
    elif action_obj1["action_type"] == ADMIN_CREATE_API_KEY:
        return action_obj1["action_data"]["key_name"] == action_obj2["action_data"]["key_name"]
    elif action_obj1["action_type"] == ADMIN_ELEVATE_USER:
        return action_obj1["created_by"] == action_obj2["created_by"]
    else:
        return False  # Unknown action_type


def send_notifications(new_status, action_obj, action_service: Service):
    creator_user = User.from_id(action_obj["created_by"])
    _send_slack_notification(new_status, action_obj, action_service, creator_user)

    # If we're out of hours and this concerns an admin elevation (request or approval)
    # then we'll create a Zendesk ticket too. Elevating itself is handled elsewhere.
    if action_obj["action_type"] == ADMIN_ELEVATE_USER and _should_send_zendesk_ticket():
        _send_admin_elevation_zendesk_notification(new_status, creator_user)


def _send_slack_notification(new_status, action_obj, action_service: Service, creator_user: User):
    message_title = None
    message_type = None
    message_markdown_parts = [
        _get_action_description_markdown(action_obj, action_service),
        f"_Created by `{creator_user.email_address}`_",
    ]

    if new_status == ADMIN_STATUS_PENDING:
        message_title = "New Admin Approval Request"
        message_type = "info"  # Yellow SlackMessage
    elif new_status == ADMIN_STATUS_APPROVED:
        message_title = "Admin Action Approved"
        message_type = "success"  # Green SlackMessage
        message_markdown_parts.append(f":green_tick: Approved by `{current_user.email_address}`")
    elif new_status == ADMIN_STATUS_REJECTED:
        message_title = "Admin Action Rejected"
        message_type = "error"  # Red SlackMessage
        message_markdown_parts.append(f":red-x-mark: Rejected by `{current_user.email_address}`")

    message = SlackMessage(
        None,  # Filled in later
        message_title,
        message_type,
        message_markdown_parts,
    )
    return _send_slack_message(message)


def _send_admin_elevation_zendesk_notification(new_status, creator_user: User):
    comment = f"{creator_user.email_address} requested to become a platform admin"
    priority = ADMIN_ZENDESK_PRIORITY_REQUEST

    # We add the approval onto initial the comment.
    # We don't know here if the original request was out of hours and thus went to Zendesk
    # or just the approval was out of hours.
    if new_status == ADMIN_STATUS_APPROVED:
        comment = comment + f"\nApproved by {current_user.email_address}"
        priority = ADMIN_ZENDESK_PRIORITY_APPROVE

    _create_or_upgrade_zendesk_ticket(priority, comment, creator_user.email_address)


def send_elevated_notifications():
    """Send a notification that the current user has elevated to full platform admin status."""
    _send_elevated_slack_notification()

    if _should_send_zendesk_ticket():
        _send_elevation_zendesk_notification()


def _send_elevated_slack_notification():
    message = SlackMessage(
        None,  # Filled in later
        "Platform Admin Elevated",
        "success",  # Green SlackMessage
        [f"`{current_user.email_address}` has elevated to become a full platform admin for their session"],
    )
    return _send_slack_message(message)


def _send_elevation_zendesk_notification():
    # Only expected to be called out of hours
    _create_or_upgrade_zendesk_ticket(
        ADMIN_ZENDESK_PRIORITY_ELEVATED,
        f"{current_user.email_address} has elevated to full platform admin",
        current_user.email_address,
    )


def _send_slack_message(message: SlackMessage):
    webhook_url = current_app.config.get("SLACK_WEBHOOK_ADMIN_ACTIVITY", "")
    message.webhook_url = webhook_url
    current_app.logger.info("Sending SlackMessage", message.__dict__)

    if not webhook_url.startswith("https://"):
        # Local environments aren't hooked up to Slack.
        # Hosted development environments also aren't, and Terraform defaults to 'dummy' (not a URL but also not blank)
        return

    try:
        slack_client.send_message_to_slack(message)
    except Exception as e:
        current_app.logger.error("Could not post to Slack", e)


def _create_or_upgrade_zendesk_ticket(priority: str, comment: str, relevant_admin_email: str):
    """Create a new Zendesk ticket, or if there's one open for the email, update the priority and add a comment."""
    existing_ticket_id = zendesk_client.get_open_admin_zendesk_ticket_id_for_email(relevant_admin_email)
    if existing_ticket_id is not None:
        zendesk_client.update_ticket_priority_with_comment(existing_ticket_id, priority, comment)
    else:
        ticket = EASSupportTicket(
            subject="Out of Hours Admin Activity",
            message=comment,
            ticket_type=EASSupportTicket.TYPE_INCIDENT,
            p1=True,
            custom_priority=priority,
            user_email=relevant_admin_email,
        )
        zendesk_client.send_ticket_to_zendesk(ticket)


def _should_send_zendesk_ticket():
    if current_app.config["ADMIN_ACTIVITY_ZENDESK_ENABLED"]:
        if _is_out_of_office_hours():
            return True

    return False


def _get_action_description_markdown(action_obj, action_service: Service):
    action_type = action_obj["action_type"]
    action_data = action_obj["action_data"]
    markdown = f"(Unknown action type: {action_type})"

    permission_labels = dict(permission_options + broadcast_permission_options)
    if action_type == ADMIN_INVITE_USER:
        markdown = (
            f'Invite user `{action_data["email_address"]}` to '
            + f'{"*live* " if action_service.live else ""}service `{action_service.name}`.'
            + "\n\n"
            + "With permissions:"
            + "".join("\n- " + permission_labels[x] for x in action_data["permissions"])
        )
    elif action_type == ADMIN_EDIT_PERMISSIONS:
        user = User.from_id(action_data["user_id"])
        markdown = (
            f"Edit user `{user.email_address}`'s permissions in "
            + f'{"*live* " if action_service.live else ""}service `{action_service.name}`.'
            + "\n\nWith permissions:"
            + "".join("\n- " + permission_labels[x] for x in action_data["permissions"])
        )
    elif action_type == ADMIN_CREATE_API_KEY:
        markdown = (
            f'Create {action_data["key_type"]} API key `{action_data["key_name"]}` in '
            + f'{"*live* " if action_service.live else ""}service `{action_service.name}`.'
        )
    elif action_type == ADMIN_ELEVATE_USER:
        markdown = "Elevate themselves to become a full platform admin\n_(This request will automatically expire)_"

    return markdown


def _is_out_of_office_hours():
    now = datetime.now(ADMIN_ZENDESK_OFFICE_HOURS_TIMEZONE)
    # datetime hour is zero-indexed but our constants are 1-indexed to make sense to humans
    if now.hour >= ADMIN_ZENDESK_OFFICE_HOURS_END:
        return True
    if now.hour < ADMIN_ZENDESK_OFFICE_HOURS_START:
        return True
    return False
