from datetime import datetime, timezone

from emergency_alerts_utils.timezones import utc_string_to_aware_gmt_datetime
from flask import abort, request, session
from flask_login import AnonymousUserMixin, UserMixin, login_user, logout_user
from notifications_python_client.errors import HTTPError
from werkzeug.utils import cached_property

from app.event_handlers import (
    create_add_user_to_service_event,
    create_set_user_permissions_event,
)
from app.models import JSONModel, ModelList
from app.models.organisation import Organisation, Organisations
from app.models.webauthn_credential import WebAuthnCredentials
from app.notify_client import InviteTokenError
from app.notify_client.invite_api_client import invite_api_client
from app.notify_client.org_invite_api_client import org_invite_api_client
from app.notify_client.user_api_client import user_api_client
from app.utils.user import is_gov_user
from app.utils.user_permissions import (
    all_ui_permissions,
    translate_permissions_from_db_to_ui,
)


def _get_service_id_from_view_args():
    return str(request.view_args.get("service_id", "")) or None


def _get_org_id_from_view_args():
    return str(request.view_args.get("org_id", "")) or None


class BaseUser(JSONModel):
    __sort_attribute__ = "email_address"


class User(BaseUser, UserMixin):
    MAX_FAILED_LOGIN_COUNT = 10

    ALLOWED_PROPERTIES = {
        "can_use_webauthn",
        "id",
        "name",
        "email_address",
        "auth_type",
        "current_session_id",
        "failed_login_count",
        "email_access_validated_at",
        "logged_in_at",
        "mobile_number",
        "password_changed_at",
        "platform_admin_active",
        "platform_admin_capable",
        "platform_admin_redemption",
        "permissions",
        "state",
    }

    # As a default
    platform_admin_active = False

    def __init__(self, _dict):
        super().__init__(_dict)
        self.permissions = _dict.get("permissions", {})

    @classmethod
    def from_id(cls, user_id):
        return cls(user_api_client.get_user(user_id))

    @classmethod
    def from_email_address(cls, email_address):
        return cls(user_api_client.get_user_by_email(email_address))

    @classmethod
    def from_email_address_or_none(cls, email_address):
        response = user_api_client.get_user_by_email_or_none(email_address)
        if response:
            return cls(response)
        return None

    @classmethod
    def from_email_address_invited(cls, email_address):
        response = user_api_client.get_user_by_email_if_exists(email_address)
        if response:
            return cls(response)
        return None

    @staticmethod
    def already_registered(email_address):
        return bool(user_api_client.check_user_exists(email_address))

    @classmethod
    def from_email_address_and_password_or_none(cls, email_address, password):
        user = cls.from_email_address_or_none(email_address)
        if not user:
            return None
        if user.locked:
            return None
        if not user_api_client.verify_password(user.id, password):
            return None
        return user

    @property
    def permissions(self):
        return self._permissions

    @permissions.setter
    def permissions(self, permissions_by_service):
        """
        Permissions is a dict {'service_id': ['permission a', 'permission b', 'permission c']}
        """
        self._permissions = {
            service: translate_permissions_from_db_to_ui(permissions)
            for service, permissions in permissions_by_service.items()
        }

    def update(self, **kwargs):
        response = user_api_client.update_user_attribute(self.id, **kwargs)
        self.__init__(response)

    def update_password(self, password):
        response = user_api_client.update_password(self.id, password)
        self.__init__(response)

    def update_email_access_validated_at(self):
        self.update(email_access_validated_at=datetime.now(timezone.utc).isoformat())

    def password_changed_more_recently_than(self, datetime_string):
        if not self.password_changed_at:
            return False
        return utc_string_to_aware_gmt_datetime(self.password_changed_at) > utc_string_to_aware_gmt_datetime(
            datetime_string
        )

    def set_permissions(self, service_id, permissions, folder_permissions, set_by_id):
        user_api_client.set_user_permissions(
            self.id,
            service_id,
            permissions=permissions,
            folder_permissions=folder_permissions,
        )
        create_set_user_permissions_event(
            user_id=self.id,
            service_id=service_id,
            original_ui_permissions=self.permissions_for_service(service_id),
            new_ui_permissions=permissions,
            set_by_id=set_by_id,
        )

    def logged_in_elsewhere(self):
        return session.get("current_session_id") != self.current_session_id

    def activate(self):
        if self.is_pending:
            user_data = user_api_client.activate_user(self.id)
            return self.__class__(user_data["data"])
        else:
            return self

    def login(self):
        login_user(self)
        session["user_id"] = self.id

    def send_login_code(self):
        if self.email_auth:
            user_api_client.send_verify_code(self.id, "email", None, request.args.get("next"))
        if self.sms_auth:
            user_api_client.send_verify_code(self.id, "sms", self.mobile_number)

    def sign_out(self):
        session.clear()
        # Update the db so the server also knows the user is logged out.
        self.update(current_session_id=None)
        logout_user()

    @property
    def sms_auth(self):
        return self.auth_type == "sms_auth"

    @property
    def email_auth(self):
        return self.auth_type == "email_auth"

    @property
    def webauthn_auth(self):
        return self.auth_type == "webauthn_auth"

    def reset_failed_login_count(self):
        user_api_client.reset_failed_login_count(self.id)

    @property
    def is_active(self):
        return self.state == "active"

    @property
    def is_pending(self):
        return self.state == "pending"

    @property
    def is_gov_user(self):
        return is_gov_user(self.email_address)

    @property
    def is_authenticated(self):
        return not self.logged_in_elsewhere() and super(User, self).is_authenticated

    @property
    def platform_admin(self):
        """Whether the user is currently a platform admin (i.e. elevated), not just capable of being one"""
        return self.platform_admin_active and not session.get("disable_platform_admin_view", False)

    @property
    def has_pending_platform_admin_elevation(self):
        if self.platform_admin_redemption is None or not self.platform_admin_capable:
            return False

        redemption = utc_string_to_aware_gmt_datetime(self.platform_admin_redemption)
        return redemption > datetime.now(timezone.utc)

    def has_permissions(self, *permissions, restrict_admin_usage=False, allow_org_user=False):
        unknown_permissions = set(permissions) - all_ui_permissions
        if unknown_permissions:
            raise TypeError("{} are not valid permissions".format(list(unknown_permissions)))

        # Service id is always set on the request for service specific views.
        service_id = _get_service_id_from_view_args()
        org_id = _get_org_id_from_view_args()

        if not service_id and not org_id:
            # we shouldn't have any pages that require permissions, but don't specify a service or organisation.
            # use @user_is_platform_admin for platform admin only pages
            raise NotImplementedError

        # platform admins should be able to do most things (except eg send messages, or create api keys)
        if self.platform_admin and not restrict_admin_usage:
            return True

        if org_id:
            return self.belongs_to_organisation(org_id)

        if not permissions and self.belongs_to_service(service_id):
            return True

        if any(self.permissions_for_service(service_id) & set(permissions)):
            return True

        from app.models.service import Service

        return allow_org_user and self.belongs_to_organisation(Service.from_id(service_id).organisation_id)

    def permissions_for_service(self, service_id):
        return self._permissions.get(service_id, set())

    def has_permission_for_service(self, service_id, permission):
        return permission in self._permissions.get(service_id, [])

    def has_template_folder_permission(self, template_folder, service=None):
        if self.platform_admin:
            return True

        # Top-level templates are always visible
        if template_folder is None or template_folder["id"] is None:
            return True

        return self.id in template_folder.get("users_with_permission", [])

    def template_folders_for_service(self, service=None):
        """
        Returns list of template folders that a user can view for a given service
        """
        return [
            template_folder
            for template_folder in service.all_template_folders
            if self.id in template_folder.get("users_with_permission", [])
        ]

    def belongs_to_service(self, service_id):
        return service_id in self.service_ids

    def belongs_to_service_or_403(self, service_id):
        if not self.belongs_to_service(service_id):
            abort(403)

    def belongs_to_organisation(self, organisation_id):
        return str(organisation_id) in self.organisation_ids

    @property
    def locked(self):
        return self.failed_login_count >= self.MAX_FAILED_LOGIN_COUNT

    @property
    def email_domain(self):
        return self.email_address.split("@")[-1]

    @cached_property
    def orgs_and_services(self):
        return user_api_client.get_organisations_and_services_for_user(self.id)

    @property
    def services(self):
        from app.models.service import Services

        return Services(self.orgs_and_services["services"])

    @property
    def services_with_organisation(self):
        return [service for service in self.services if self.belongs_to_organisation(service.organisation_id)]

    @property
    def service_ids(self):
        return self._dict["services"]

    @property
    def trial_mode_services(self):
        return [service for service in self.services if service.trial_mode]

    @property
    def live_services(self):
        return [service for service in self.services if service.live]

    @property
    def organisations(self):
        return Organisations(self.orgs_and_services["organisations"])

    @property
    def organisation_ids(self):
        return self._dict["organisations"]

    @cached_property
    def default_organisation(self):
        return Organisation.from_domain(self.email_domain)

    @property
    def default_organisation_type(self):
        if self.default_organisation:
            return self.default_organisation.organisation_type
        if self.has_nhs_email_address:
            return "nhs"
        return None

    @property
    def has_access_to_live_and_trial_mode_services(self):
        return (self.organisations or self.live_services) and (self.trial_mode_services)

    @property
    def has_nhs_email_address(self):
        return self.email_address.lower().endswith(
            (
                "@nhs.uk",
                ".nhs.uk",
                "@nhs.net",
                ".nhs.net",
            )
        )

    @property
    def webauthn_credentials(self):
        return WebAuthnCredentials(self.id)

    def create_webauthn_credential(self, credential):
        user_api_client.create_webauthn_credential_for_user(self.id, credential)

    def serialize(self):
        dct = {
            "id": self.id,
            "name": self.name,
            "email_address": self.email_address,
            "mobile_number": self.mobile_number,
            "password_changed_at": self.password_changed_at,
            "state": self.state,
            "failed_login_count": self.failed_login_count,
            "permissions": [x for x in self._permissions],
            "organisations": self.organisation_ids,
            "current_session_id": self.current_session_id,
        }
        if hasattr(self, "_password"):
            dct["password"] = self._password
        return dct

    @classmethod
    def register(
        cls,
        name,
        email_address,
        mobile_number,
        password,
        auth_type,
    ):
        return cls(
            user_api_client.register_user(
                name,
                email_address,
                mobile_number or None,
                password,
                auth_type,
            )
        )

    def set_password(self, pwd):
        self._password = pwd

    def send_verify_email(self):
        user_api_client.send_verify_email(self.id, self.email_address)

    def send_verify_code(self, to=None):
        user_api_client.send_verify_code(self.id, "sms", to or self.mobile_number)

    def send_verify_code_to_new_auth(self, to):
        user_api_client.send_verify_code_to_new_auth(self.id, "sms", to)

    def send_already_registered_email(self):
        user_api_client.send_already_registered_email(self.id, self.email_address)

    def refresh_session_id(self):
        self.current_session_id = user_api_client.get_user(self.id).get("current_session_id")
        session["current_session_id"] = self.current_session_id

    def add_to_service(self, service_id, permissions, folder_permissions, invited_by_id):
        try:
            user_api_client.add_user_to_service(
                service_id,
                self.id,
                permissions,
                folder_permissions,
            )
            create_add_user_to_service_event(
                user_id=self.id,
                invited_by_id=invited_by_id,
                service_id=service_id,
                ui_permissions=permissions,
            )
        except HTTPError as exception:
            if exception.status_code == 400 and "already part of service" in exception.message:
                pass
            else:
                raise exception

    def add_to_organisation(self, organisation_id):
        user_api_client.add_user_to_organisation(
            organisation_id,
            self.id,
        )

    def complete_webauthn_login_attempt(self, is_successful=True, webauthn_credential_id=None):
        return user_api_client.complete_webauthn_login_attempt(self.id, is_successful, webauthn_credential_id)

    def is_editable_by(self, other_user):
        if other_user == self:
            return False
        if self.is_active or self.is_pending:
            return True
        return False


class InvitedUser(BaseUser):
    ALLOWED_PROPERTIES = {
        "id",
        "service",
        "email_address",
        "permissions",
        "status",
        "created_at",
        "auth_type",
        "folder_permissions",
    }

    def __init__(self, _dict):
        super().__init__(_dict)
        self.permissions = _dict.get("permissions") or []
        self._from_user = _dict["from_user"]

    @classmethod
    def create(
        cls,
        invite_from_id,
        service_id,
        email_address,
        permissions,
        auth_type,
        folder_permissions,
    ):
        return cls(
            invite_api_client.create_invite(
                invite_from_id,
                service_id,
                email_address,
                permissions,
                auth_type,
                folder_permissions,
            )
        )

    @classmethod
    def by_id_and_service_id(cls, service_id, invited_user_id):
        return cls(invite_api_client.get_invited_user_for_service(service_id, invited_user_id))

    @classmethod
    def by_id(cls, invited_user_id):
        return cls(invite_api_client.get_invited_user(invited_user_id))

    def accept_invite(self):
        invite_api_client.accept_invite(self.service, self.id)

    @property
    def permissions(self):
        return self._permissions

    @permissions.setter
    def permissions(self, permissions):
        if isinstance(permissions, list):
            self._permissions = permissions
        else:
            self._permissions = permissions.split(",")
        self._permissions = translate_permissions_from_db_to_ui(self.permissions)

    @property
    def from_user(self):
        return User.from_id(self._from_user)

    @property
    def sms_auth(self):
        return self.auth_type == "sms_auth"

    @property
    def email_auth(self):
        return self.auth_type == "email_auth"

    @classmethod
    def from_token(cls, token):
        try:
            return cls(invite_api_client.check_token(token))
        except HTTPError as exception:
            if exception.status_code == 400 and "invitation" in exception.message:
                raise InviteTokenError(exception.message["invitation"])
            else:
                raise exception

    @classmethod
    def from_session(cls):
        invited_user_id = session.get("invited_user_id")
        return cls.by_id(invited_user_id) if invited_user_id else None

    def has_permissions(self, *permissions):
        if self.status == "cancelled":
            return False
        return set(self.permissions) > set(permissions)

    def has_permission_for_service(self, service_id, permission):
        if self.status == "cancelled":
            return False
        return self.service == service_id and permission in self.permissions

    def __eq__(self, other):
        return (self.id, self.service, self._from_user, self.email_address, self.auth_type, self.status) == (
            other.id,
            other.service,
            other._from_user,
            other.email_address,
            other.auth_type,
            other.status,
        )

    def serialize(self, permissions_as_string=False):
        data = {
            "id": self.id,
            "service": self.service,
            "from_user": self._from_user,
            "email_address": self.email_address,
            "status": self.status,
            "created_at": str(self.created_at),
            "auth_type": self.auth_type,
            "folder_permissions": self.folder_permissions,
        }
        if permissions_as_string:
            data["permissions"] = ",".join(self.permissions)
        else:
            data["permissions"] = sorted(self.permissions)
        return data

    def template_folders_for_service(self, service=None):
        # only used on the manage users page to display the count, so okay to not be fully fledged for now
        return [{"id": x} for x in self.folder_permissions]

    def is_editable_by(self, other):
        return False


class InvitedOrgUser(BaseUser):
    ALLOWED_PROPERTIES = {
        "id",
        "organisation",
        "email_address",
        "status",
        "created_at",
    }

    def __init__(self, _dict):
        super().__init__(_dict)
        self._invited_by = _dict["invited_by"]

    def __eq__(self, other):
        return (self.id, self.organisation, self._invited_by, self.email_address, self.status) == (
            other.id,
            other.organisation,
            other._invited_by,
            other.email_address,
            other.status,
        )

    @classmethod
    def create(cls, invite_from_id, org_id, email_address):
        return cls(org_invite_api_client.create_invite(invite_from_id, org_id, email_address))

    @classmethod
    def from_session(cls):
        invited_org_user_id = session.get("invited_org_user_id")
        return cls.by_id(invited_org_user_id) if invited_org_user_id else None

    @classmethod
    def by_id_and_org_id(cls, org_id, invited_user_id):
        return cls(org_invite_api_client.get_invited_user_for_org(org_id, invited_user_id))

    @classmethod
    def by_id(cls, invited_user_id):
        return cls(org_invite_api_client.get_invited_user(invited_user_id))

    def serialize(self, permissions_as_string=False):
        data = {
            "id": self.id,
            "organisation": self.organisation,
            "invited_by": self._invited_by,
            "email_address": self.email_address,
            "status": self.status,
            "created_at": str(self.created_at),
        }
        return data

    @property
    def invited_by(self):
        return User.from_id(self._invited_by)

    @classmethod
    def from_token(cls, token):
        try:
            return cls(org_invite_api_client.check_token(token))
        except HTTPError as exception:
            if exception.status_code == 400 and "invitation" in exception.message:
                raise InviteTokenError(exception.message["invitation"])
            else:
                raise exception

    def accept_invite(self):
        org_invite_api_client.accept_invite(self.organisation, self.id)


class AnonymousUser(AnonymousUserMixin):
    # set the anonymous user so that if a new browser hits us we don't error http://stackoverflow.com/a/19275188

    def logged_in_elsewhere(self):
        return False

    @property
    def default_organisation(self):
        return Organisation(None)


class Users(ModelList):
    client_method = user_api_client.get_users_for_service
    model = User

    def get_name_from_id(self, id):
        for user in self:
            if user.id == id:
                return user.name
        # The user may not exist in the list of users for this service if they are
        # a platform admin or if they have since left the team. In this case, we fall
        # back to getting the user from the API
        user = User.from_id(id)
        if user and user.name:
            return user.name
        return "Unknown"


class OrganisationUsers(Users):
    client_method = user_api_client.get_users_for_organisation


class InvitedUsers(Users):
    client_method = invite_api_client.get_invites_for_service
    model = InvitedUser

    def __init__(self, service_id):
        self.items = [user for user in self.client_method(service_id) if user["status"] != "accepted"]


class PendingUsers(Users):
    client_method = invite_api_client.get_invites_for_service
    model = InvitedUser

    def __init__(self, service_id):
        self.items = [user for user in self.client_method(service_id) if user["status"] == "pending"]


class OrganisationInvitedUsers(InvitedUsers):
    client_method = org_invite_api_client.get_invites_for_organisation
    model = InvitedOrgUser
