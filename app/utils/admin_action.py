from typing import Iterable

from emergency_alerts_utils.admin_action import (
    ADMIN_CREATE_API_KEY,
    ADMIN_EDIT_PERMISSIONS,
    ADMIN_ELEVATE_USER,
    ADMIN_INVITE_USER,
    ADMIN_SENSITIVE_PERMISSIONS,
    ADMIN_STATUS_INVALIDATED,
)
from emergency_alerts_utils.api_key import KEY_TYPE_NORMAL
from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.formatters import email_safe
from app.models.service import Service
from app.models.user import InvitedUser, User
from app.notify_client.admin_actions_api_client import admin_actions_api_client
from app.notify_client.api_key_api_client import api_key_api_client
from app.notify_client.user_api_client import user_api_client


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

    return admin_actions_api_client.create_admin_action(proposed_action_obj)


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
