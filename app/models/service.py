from emergency_alerts_utils.serialised_model import SerialisedModelCollection
from flask import abort
from werkzeug.utils import cached_property

from app.models import JSONModel
from app.models.organisation import Organisation
from app.models.template import Template
from app.models.user import InvitedUsers, PendingUsers, User, Users
from app.notify_client.api_key_api_client import api_key_api_client
from app.notify_client.invite_api_client import invite_api_client
from app.notify_client.organisations_api_client import organisations_client
from app.notify_client.service_api_client import service_api_client
from app.notify_client.template_api_client import template_api_client
from app.notify_client.template_folder_api_client import template_folder_api_client


class Service(JSONModel):
    ALLOWED_PROPERTIES = {
        "active",
        "allowed_broadcast_provider",
        "broadcast_channel",
        "id",
        "name",
        "notes",
        "service_callback_api",
    }

    __sort_attribute__ = "name"

    TEMPLATE_TYPES = ("broadcast",)

    ALL_PERMISSIONS = TEMPLATE_TYPES + (
        "edit_folder_permissions",
        "email_auth",
        "broadcast",
    )

    @classmethod
    def from_id(cls, service_id):
        return cls(service_api_client.get_service(service_id)["data"])

    @property
    def permissions(self):
        return self._dict.get("permissions", self.TEMPLATE_TYPES)

    def update(self, **kwargs):
        return service_api_client.update_service(self.id, **kwargs)

    def update_status(self, live):
        return service_api_client.update_status(self.id, live=live)

    def switch_permission(self, permission):
        return self.force_permission(
            permission,
            on=not self.has_permission(permission),
        )

    def force_permission(self, permission, on=False):
        permissions, permission = set(self.permissions), {permission}

        return self.update_permissions(
            permissions | permission if on else permissions - permission,
        )

    def update_permissions(self, permissions):
        return self.update(permissions=list(permissions))

    @property
    def trial_mode(self):
        return self._dict["restricted"]

    @property
    def live(self):
        return not self.trial_mode

    def has_permission(self, permission):
        if permission not in self.ALL_PERMISSIONS:
            raise KeyError(f"{permission} is not a service permission")
        return permission in self.permissions

    @cached_property
    def invited_users(self):
        return InvitedUsers(self.id)

    @cached_property
    def pending_users(self):
        return PendingUsers(self.id)

    def invite_pending_for(self, email_address):
        return email_address.lower() in (invited_user.email_address.lower() for invited_user in self.pending_users)

    @cached_property
    def active_users(self):
        return Users(self.id)

    @cached_property
    def team_members(self):
        return self.invited_users + self.active_users

    @cached_property
    def has_team_members(self):
        return (
            len([user for user in self.team_members if user.has_permission_for_service(self.id, "manage_service")]) > 1
        )

    def cancel_invite(self, invited_user_id):
        if str(invited_user_id) not in {user.id for user in self.invited_users}:
            abort(404)

        return invite_api_client.cancel_invited_user(
            service_id=self.id,
            invited_user_id=str(invited_user_id),
        )

    def get_team_member(self, user_id):
        if str(user_id) not in {user.id for user in self.active_users}:
            abort(404)

        return User.from_id(user_id)

    @cached_property
    def all_templates(self):
        templates = template_api_client.get_templates(self.id)["data"]

        return [template for template in templates if template["template_type"] in self.available_template_types]

    @cached_property
    def all_template_ids(self):
        return {template["id"] for template in self.all_templates}

    def get_template_folder_with_user_permission_or_403(self, folder_id, user):
        template_folder = self.get_template_folder(folder_id)

        if not user.has_template_folder_permission(template_folder):
            abort(403)

        return template_folder

    def get_template_with_user_permission_or_403(self, template_id, user):
        template = Template.from_id(template_id, service_id=self.id)

        self.get_template_folder_with_user_permission_or_403(template.folder, user)

        return template

    @property
    def available_template_types(self):
        return list(filter(self.has_permission, self.TEMPLATE_TYPES))

    @property
    def has_templates(self):
        return bool(self.all_templates)

    def has_folders(self):
        return bool(self.all_template_folders)

    def has_templates_of_type(self, template_type):
        return any(template for template in self.all_templates if template["template_type"] == template_type)

    @cached_property
    def organisation(self):
        return Organisation.from_id(self.organisation_id)

    @property
    def organisation_id(self):
        return self._dict["organisation"]

    @property
    def organisation_type(self):
        return self.organisation.organisation_type or self._dict["organisation_type"]

    @property
    def organisation_name(self):
        if not self.organisation_id:
            return None
        return organisations_client.get_organisation_name(self.organisation_id)

    @property
    def organisation_type_label(self):
        return Organisation.TYPE_LABELS.get(self.organisation_type)

    @property
    def is_nhs(self):
        return self.organisation_type in Organisation.NHS_TYPES

    @cached_property
    def all_template_folders(self):
        return sorted(
            template_folder_api_client.get_template_folders(self.id),
            key=lambda folder: folder["name"].lower(),
        )

    @cached_property
    def all_template_folder_ids(self):
        return {folder["id"] for folder in self.all_template_folders}

    def get_template_folder(self, folder_id):
        if folder_id is None:
            return {
                "id": None,
                "name": "Templates",
                "parent_id": None,
            }
        return self._get_by_id(self.all_template_folders, folder_id)

    def get_template_folder_path(self, template_folder_id):
        folder = self.get_template_folder(template_folder_id)

        if folder["id"] is None:
            return [folder]

        return self.get_template_folder_path(folder["parent_id"]) + [self.get_template_folder(folder["id"])]

    def get_template_path(self, template):
        template_dict = template.__dict__
        template_dict["name"] = template.reference
        return self.get_template_folder_path(template.folder) + [
            template_dict,
        ]

    @property
    def count_of_templates_and_folders(self):
        return len(self.all_templates + self.all_template_folders)

    def move_to_folder(self, ids_to_move, move_to):
        ids_to_move = set(ids_to_move)

        template_folder_api_client.move_to_folder(
            service_id=self.id,
            folder_id=move_to,
            template_ids=ids_to_move & self.all_template_ids,
            folder_ids=ids_to_move & self.all_template_folder_ids,
        )

    @cached_property
    def api_keys(self):
        return sorted(
            api_key_api_client.get_api_keys(self.id)["apiKeys"],
            key=lambda key: key["name"].lower(),
        )

    def get_api_key(self, id):
        return self._get_by_id(self.api_keys, id)

    @property
    def able_to_accept_agreement(self):
        return self.organisation.agreement_signed is not None or self.organisation_type in {
            Organisation.TYPE_NHS_GP,
            Organisation.TYPE_NHS_LOCAL,
        }


class Services(SerialisedModelCollection):
    model = Service
