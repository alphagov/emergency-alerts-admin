from typing import Iterable

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.models.service import Service
from app.models.user import InvitedUser, User
from app.notify_client.api_key_api_client import KEY_TYPE_NORMAL, api_key_api_client

# Tasks which require another platform/org admin to approve before being actioned
ADMIN_INVITE_USER = "invite_user"  # Only if the user has sensitive permissions
ADMIN_INVITE_USER_ORG = "invite_user_org"
ADMIN_EDIT_PERMISSIONS = "edit_permissions"  # Only if adding permissions, removal does not need approval
ADMIN_CREATE_API_KEY = "create_api_key"

ADMIN_ACTION_LIST = [
    ADMIN_INVITE_USER,
    ADMIN_INVITE_USER_ORG,
    ADMIN_EDIT_PERMISSIONS,
    ADMIN_CREATE_API_KEY,
]

ADMIN_STATUS_PENDING = "pending"
ADMIN_STATUS_APPROVED = "approved"
ADMIN_STATUS_REJECTED = "rejected"

ADMIN_STATUS_LIST = [
    ADMIN_STATUS_PENDING,
    ADMIN_STATUS_APPROVED,
    ADMIN_STATUS_REJECTED,
]

# Permissions which require approval from an additional admin before being added
ADMIN_APPROVAL_PERMISSIONS = ["create_broadcasts", "approve_broadcasts"]


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
        # The template uses has_permissions, but this requires the service ID to be in the request args
        request.view_args["service_id"] = service_id
        return render_template(
            "views/api/keys/show.html",
            secret=secret,
            service_id=service_id,
            key_name=action_data["key_name"],
        )
    else:
        raise Exception("Unknown admin action " + action_type)


def permissions_require_admin_action(new_permissions: Iterable[str]):
    return bool(set(new_permissions) & set(ADMIN_APPROVAL_PERMISSIONS))
