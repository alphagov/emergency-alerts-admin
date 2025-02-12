from typing import Iterable

from flask import flash, redirect, url_for

from app.models.user import InvitedUser

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

    action_type = action_obj["action_type"]

    if action_type == ADMIN_INVITE_USER:
        InvitedUser.create(
            action_obj["created_by"],
            action_obj["service_id"],
            action_obj["action_data"]["email_address"],
            action_obj["action_data"]["permissions"],
            action_obj["action_data"]["login_authentication"],
            action_obj["action_data"]["folder_permissions"],
        )
        flash("Sent invite to user " + action_obj["action_data"]["email_address"], "default_with_tick")
        return redirect(url_for(".manage_users", service_id=action_obj["service_id"]))
    else:
        raise Exception("Unknown admin action " + action_type)


def permissions_require_admin_action(new_permissions: Iterable[str]):
    return bool(set(new_permissions) & set(ADMIN_APPROVAL_PERMISSIONS))
