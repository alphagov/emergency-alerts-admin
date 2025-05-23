from flask import abort
from notifications_python_client.errors import HTTPError

from app.notify_client import AdminAPIClient
from app.utils.user_permissions import translate_permissions_from_ui_to_db

ALLOWED_ATTRIBUTES = {
    "name",
    "email_address",
    "mobile_number",
    "auth_type",
    "updated_by",
    "current_session_id",
    "email_access_validated_at",
}


class UserApiClient(AdminAPIClient):
    def init_app(self, app):
        super().init_app(app)
        self.admin_url = app.config["ADMIN_EXTERNAL_URL"]

    def register_user(self, name, email_address, mobile_number, password, auth_type):
        data = {
            "name": name,
            "email_address": email_address,
            "mobile_number": mobile_number,
            "password": password,
            "auth_type": auth_type,
        }
        user_data = self.post("/user", data)
        return user_data["data"]

    def get_user(self, user_id):
        return self._get_user(user_id)["data"]

    def _get_user(self, user_id):
        return self.get("/user/{}".format(user_id))

    def get_user_by_email(self, email_address):
        try:
            user_data = self.post("/user/email", data={"email": email_address})
            return user_data["data"]
        except HTTPError as e:
            if e.status_code == 404:
                return None
            elif e.status_code == 429:
                abort(429)
            raise e

    def check_user_exists(self, email_address):
        return self.post("/user/email-in-use", data={"email": email_address})

    def get_user_by_email_if_exists(self, email_address):
        """Returns user from database if they exist there already, but unlike get_user_by_email
        if user doesn't exist, no failed login attempt is recorded as this is for inviting users"""
        return self.post("/user/email-or-none", data={"email": email_address})["data"]

    def get_user_by_email_or_none(self, email_address):
        try:
            return self.get_user_by_email(email_address)
        except HTTPError as e:
            if e.status_code == 404:
                return None
            elif e.status_code == 429:
                abort(429)
            raise e

    def update_user_attribute(self, user_id, **kwargs):
        data = dict(kwargs)
        disallowed_attributes = set(data.keys()) - ALLOWED_ATTRIBUTES
        if disallowed_attributes:
            raise TypeError("Not allowed to update user attributes: {}".format(", ".join(disallowed_attributes)))

        url = "/user/{}/update".format(user_id)
        user_data = self.post(url, data=data)
        return user_data["data"]

    def archive_user(self, user_id):
        return self.post("/user/{}/archive".format(user_id), data=None)

    def reset_failed_login_count(self, user_id):
        url = "/user/{}/reset-failed-login-count".format(user_id)
        user_data = self.post(url, data={})
        return user_data["data"]

    def update_password(self, user_id, password):
        data = {"_password": password}
        url = "/user/{}/update-password".format(user_id)
        user_data = self.post(url, data=data)
        return user_data["data"]

    def check_password_is_valid(self, user_id, password):
        endpoint = f"/user/{user_id}/check-password-validity"
        data = {
            "_password": password,
        }

        self.post(endpoint, data=data)

    def verify_password(self, user_id, password):
        try:
            url = "/user/{}/verify/password".format(user_id)
            data = {"password": password}
            self.post(url, data=data)
            return True
        except HTTPError as e:
            if e.status_code == 400 or e.status_code == 404:
                return False
            elif e.status_code == 429:
                abort(429)

    def send_verify_code(self, user_id, code_type, to, next_string=None):
        data = {"to": to}
        if next_string:
            data["next"] = next_string
        if code_type == "email":
            data["email_auth_link_host"] = self.admin_url
        endpoint = "/user/{0}/{1}-code".format(user_id, code_type)
        self.post(endpoint, data=data)

    def send_verify_code_to_new_auth(self, user_id, code_type, to, next_string=None):
        data = {"to": to}
        if next_string:
            data["next"] = next_string
        if code_type == "email":
            data["email_auth_link_host"] = self.admin_url
        endpoint = "/user/{0}/{1}-code-new-auth".format(user_id, code_type)
        self.post(endpoint, data=data)

    def send_verify_email(self, user_id, to):
        data = {
            "to": to,
            "admin_base_url": self.admin_url,
        }
        endpoint = "/user/{0}/email-verification".format(user_id)
        self.post(endpoint, data=data)

    def send_already_registered_email(self, user_id, to):
        data = {"email": to}
        endpoint = "/user/{0}/email-already-registered".format(user_id)
        self.post(endpoint, data=data)

    def check_verify_code(self, user_id, code, code_type):
        data = {"code_type": code_type, "code": code}
        endpoint = "/user/{}/verify/code".format(user_id)
        try:
            self.post(endpoint, data=data)
            return True, ""
        except HTTPError as e:
            if e.status_code == 400 or e.status_code == 404:
                return False, e.message
            elif e.status_code == 429:
                abort(429)
            raise e

    def complete_webauthn_login_attempt(self, user_id, is_successful, webauthn_credential_id):
        data = {"successful": is_successful, "webauthn_credential_id": webauthn_credential_id}
        endpoint = f"/user/{user_id}/complete/webauthn-login"
        try:
            self.post(endpoint, data=data)
            return True, ""
        except HTTPError as e:
            if e.status_code == 403:
                return False, e.message
            raise e

    def get_users_for_service(self, service_id):
        endpoint = "/service/{}/users".format(service_id)
        return self.get(endpoint)["data"]

    def get_users_for_organisation(self, org_id):
        endpoint = "/organisations/{}/users".format(org_id)
        return self.get(endpoint)["data"]

    def add_user_to_service(self, service_id, user_id, permissions, folder_permissions):
        # permissions passed in are the combined UI permissions, not DB permissions
        endpoint = "/service/{}/users/{}".format(service_id, user_id)
        data = {
            "permissions": [{"permission": x} for x in translate_permissions_from_ui_to_db(permissions)],
            "folder_permissions": folder_permissions,
        }

        self.post(endpoint, data=data)

    def add_user_to_organisation(self, org_id, user_id):
        resp = self.post("/organisations/{}/users/{}".format(org_id, user_id), data={})
        return resp["data"]

    def set_user_permissions(self, user_id, service_id, permissions, folder_permissions=None):
        # permissions passed in are the combined UI permissions, not DB permissions
        data = {
            "permissions": [{"permission": x} for x in translate_permissions_from_ui_to_db(permissions)],
        }

        if folder_permissions is not None:
            data["folder_permissions"] = folder_permissions

        endpoint = "/user/{}/service/{}/permission".format(user_id, service_id)
        self.post(endpoint, data=data)

    def send_reset_password_url(self, email_address, next_string=None):
        endpoint = "/user/reset-password"
        data = {
            "email": email_address,
            "admin_base_url": self.admin_url,
        }
        if next_string:
            data["next"] = next_string
        self.post(endpoint, data=data)

    def find_users_by_full_or_partial_email(self, email_address):
        endpoint = "/user/find-users-by-email"
        data = {"email": email_address}
        users = self.post(endpoint, data=data)
        return users

    def activate_user(self, user_id):
        return self.post("/user/{}/activate".format(user_id), data=None)

    def send_change_email_verification(self, user_id, new_email):
        endpoint = "/user/{}/change-email-verification".format(user_id)
        data = {"email": new_email}
        try:
            self.post(endpoint, data)
        except HTTPError as e:
            raise e

    def get_organisations_and_services_for_user(self, user_id):
        endpoint = "/user/{}/organisations-and-services".format(user_id)
        return self.get(endpoint)

    def get_webauthn_credentials_for_user(self, user_id):
        endpoint = f"/user/{user_id}/webauthn"

        return self.get(endpoint)["data"]

    def get_webauthn_credentials_count(self, user_id):
        endpoint = f"/user/{user_id}/webauthn/check-credentials"
        return int(self.get(endpoint)["data"])

    def create_webauthn_credential_for_user(self, user_id, credential):
        endpoint = f"/user/{user_id}/webauthn"

        return self.post(endpoint, data=credential.serialize())

    def update_webauthn_credential_name_for_user(self, *, user_id, credential_id, new_name_for_credential):
        endpoint = f"/user/{user_id}/webauthn/{credential_id}"

        return self.post(endpoint, data={"name": new_name_for_credential})

    def delete_webauthn_credential_for_user(self, *, user_id, credential_id):
        endpoint = f"/user/{user_id}/webauthn/{credential_id}"

        return self.delete(endpoint)

    def elevate_admin_next_login(self, user_id, approved_by_id):
        endpoint = f"/user/{user_id}/elevate"

        return self.post(endpoint, data={"approved_by": str(approved_by_id)})

    def redeem_admin_elevation(self, user_id):
        endpoint = f"/user/{user_id}/redeem-elevation"

        return self.post(endpoint, data={})


user_api_client = UserApiClient()
