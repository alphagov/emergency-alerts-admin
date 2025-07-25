import copy
import json
import os
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from functools import partial
from unittest.mock import Mock, PropertyMock
from uuid import UUID, uuid4

import pytest
from emergency_alerts_utils.url_safe_token import generate_token
from flask import Flask, Response, url_for
from notifications_python_client.errors import HTTPError

from app import create_app, webauthn_server

from . import (
    NotifyBeautifulSoup,
    TestClient,
    api_key_json,
    assert_url_expected,
    broadcast_message_edit_reason_json,
    broadcast_message_json,
    broadcast_message_version_json,
    generate_uuid,
    invite_json,
    org_invite_json,
    organisation_json,
    sample_uuid,
    service_json,
    template_json,
    template_version_json,
    user_json,
)


class ElementNotFound(Exception):
    pass


@pytest.fixture(scope="module")
def notify_admin_without_context():
    """
    You probably won't need to use this fixture, unless you need to use the flask.appcontext_pushed hook. Possibly if
    you're patching something on `g`. https://flask.palletsprojects.com/en/1.1.x/testing/#faking-resources-and-context
    """
    app = Flask("app")
    create_app(app)
    app.test_client_class = TestClient

    return app


@pytest.fixture(scope="module")
def notify_admin(notify_admin_without_context):
    with notify_admin_without_context.app_context():
        yield notify_admin_without_context


@pytest.fixture(scope="function")
def service_one(api_user_active):
    return service_json(SERVICE_ONE_ID, "service one", [api_user_active["id"]])


@pytest.fixture(scope="function")
def service_two(api_user_active):
    return service_json(SERVICE_TWO_ID, "service two", [api_user_active["id"]])


@pytest.fixture(scope="function")
def mock_add_sms_sender(mocker):
    def _add_sms_sender(service_id, sms_sender, is_default=False):
        return

    return mocker.patch("app.service_api_client.add_sms_sender", side_effect=_add_sms_sender)


@pytest.fixture(scope="function")
def mock_update_sms_sender(mocker):
    def _update_sms_sender(service_id, sms_sender_id, sms_sender=None, active=None, is_default=False):
        return

    return mocker.patch("app.service_api_client.update_sms_sender", side_effect=_update_sms_sender)


@pytest.fixture(scope="function")
def fake_uuid():
    return sample_uuid()


@pytest.fixture(scope="function")
def mock_get_service(mocker, api_user_active):
    def _get(service_id):
        service = service_json(service_id, users=[api_user_active["id"]])
        return {"data": service}

    return mocker.patch("app.service_api_client.get_service", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_service_statistics(mocker, api_user_active):
    def _get(service_id, limit_days=None):
        return {
            "email": {"requested": 0, "delivered": 0, "failed": 0},
            "sms": {"requested": 0, "delivered": 0, "failed": 0},
            "letter": {"requested": 0, "delivered": 0, "failed": 0},
        }

    return mocker.patch("app.service_api_client.get_service_statistics", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_detailed_services(mocker, fake_uuid):
    service_one = service_json(
        id_=SERVICE_ONE_ID,
        name="service_one",
        users=[fake_uuid],
        active=True,
        restricted=False,
    )
    service_two = service_json(
        id_=fake_uuid,
        name="service_two",
        users=[fake_uuid],
        active=True,
        restricted=True,
    )
    service_one["statistics"] = {
        "email": {"requested": 0, "delivered": 0, "failed": 0},
        "sms": {"requested": 0, "delivered": 0, "failed": 0},
        "letter": {"requested": 0, "delivered": 0, "failed": 0},
    }
    service_two["statistics"] = {
        "email": {"requested": 0, "delivered": 0, "failed": 0},
        "sms": {"requested": 0, "delivered": 0, "failed": 0},
        "letter": {"requested": 0, "delivered": 0, "failed": 0},
    }
    services = {"data": [service_one, service_two]}

    return mocker.patch("app.service_api_client.get_services", return_value=services)


@pytest.fixture(scope="function")
def mock_get_live_service(mocker, api_user_active):
    def _get(service_id):
        service = service_json(service_id, users=[api_user_active["id"]], restricted=False)
        return {"data": service}

    return mocker.patch("app.service_api_client.get_service", side_effect=_get)


@pytest.fixture(scope="function")
def mock_create_service(mocker):
    def _create(
        service_name,
        organisation_type,
        restricted,
        user_id,
    ):
        service = service_json(101, service_name, [user_id], restricted=restricted)
        return service["id"]

    return mocker.patch("app.service_api_client.create_service", side_effect=_create)


@pytest.fixture(scope="function")
def mock_update_service(mocker):
    def _update(service_id, **kwargs):
        service = service_json(
            service_id,
            **{key: kwargs[key] for key in kwargs if key in ["name", "users", "active", "restricted", "permissions"]},
        )
        return {"data": service}

    return mocker.patch("app.service_api_client.update_service", side_effect=_update, autospec=True)


@pytest.fixture(scope="function")
def mock_update_service_raise_httperror_duplicate_name(mocker):
    def _update(service_id, **kwargs):
        json_mock = Mock(return_value={"message": {"name": ["Duplicate service name '{}'".format(kwargs.get("name"))]}})
        resp_mock = Mock(status_code=400, json=json_mock)
        http_error = HTTPError(response=resp_mock, message="Default message")
        raise http_error

    return mocker.patch("app.service_api_client.update_service", side_effect=_update)


SERVICE_ONE_ID = "596364a0-858e-42c8-9062-a8fe822260eb"
SERVICE_TWO_ID = "147ad62a-2951-4fa1-9ca0-093cd1a52c52"
SERVICE_NO_BROADCAST = "a45678a8-4ca5-4814-a3eb-5b47eb35805f"
ORGANISATION_ID = "c011fa40-4cbe-4524-b415-dde2f421bd9c"
ORGANISATION_TWO_ID = "d9b5be73-0b36-4210-9d89-8f1a5c2fef26"
TEMPLATE_ONE_ID = "b22d7d94-2197-4a7d-a8e7-fd5f9770bf48"
USER_ONE_ID = "7b395b52-c6c1-469c-9d61-54166461c1ab"


@pytest.fixture(scope="function")
def mock_get_services(mocker, active_user_with_permissions):
    def _get_services(params_dict=None):
        service_one = service_json(
            SERVICE_ONE_ID, "service_one", [active_user_with_permissions["id"]], 1000, True, False
        )
        service_two = service_json(
            SERVICE_TWO_ID, "service_two", [active_user_with_permissions["id"]], 1000, True, False
        )
        return {"data": [service_one, service_two]}

    return mocker.patch("app.service_api_client.get_services", side_effect=_get_services)


@pytest.fixture(scope="function")
def mock_get_services_with_no_services(mocker):
    def _get_services(params_dict=None):
        return {"data": []}

    return mocker.patch("app.service_api_client.get_services", side_effect=_get_services)


@pytest.fixture(scope="function")
def mock_get_services_with_one_service(mocker, api_user_active):
    def _get_services(params_dict=None):
        return {"data": [service_json(SERVICE_ONE_ID, "service_one", [api_user_active["id"]], 1000, True, True)]}

    return mocker.patch("app.service_api_client.get_services", side_effect=_get_services)


@pytest.fixture(scope="function")
def mock_get_service_template(mocker):
    def _get(service_id, template_id, version=None):
        template = template_json(
            service_id, template_id, "Sample Template", "broadcast", "Template <em>content</em> with & entity"
        )
        if version:
            template.update({"version": version})
        return {"data": template}

    return mocker.patch("app.service_api_client.get_service_template", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_deleted_template(mocker):
    def _get(service_id, template_id, version=None):
        template = template_json(
            service_id,
            template_id,
            "Test alert",
            "broadcast",
            "This is a test",
            archived=True,
        )
        if version:
            template.update({"version": version})
        return {"data": template}

    return mocker.patch("app.service_api_client.get_service_template", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_template_version(mocker, api_user_active):
    def _get(service_id, template_id, version):
        template_version = template_version_json(service_id, template_id, api_user_active, version=version)
        return {"data": template_version}

    return mocker.patch("app.service_api_client.get_service_template", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_template_versions(mocker, api_user_active):
    def _get(service_id, template_id):
        template_version = template_version_json(service_id, template_id, api_user_active, version=1)
        return {"data": [template_version]}

    return mocker.patch("app.service_api_client.get_service_template_versions", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_empty_service_template_with_optional_placeholder(mocker):
    def _get(service_id, template_id, version=None):
        template = template_json(
            service_id, template_id, name="Optional content", content="((show_placeholder??Some content))"
        )
        return {"data": template}

    return mocker.patch("app.service_api_client.get_service_template", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_broadcast_template(mocker):
    def _get(service_id, template_id, version=None):
        template = template_json(
            service_id,
            template_id,
            "Test alert",
            "broadcast",
            "This is a test",
        )
        if version:
            template.update({"version": version})
        return {"data": template}

    return mocker.patch("app.service_api_client.get_service_template", side_effect=_get)


@pytest.fixture(scope="function")
def mock_create_service_template(mocker, fake_uuid):
    def _create(name, type_, content, service, parent_folder_id=None):
        template = template_json(fake_uuid, name, type_, content, service, parent_folder_id)
        return {"data": template}

    return mocker.patch("app.service_api_client.create_service_template", side_effect=_create)


@pytest.fixture(scope="function")
def mock_update_service_template(mocker):
    def _update(id_, name, type_, content, service):
        template = template_json(service, id_, name, type_, content)
        return {"data": template}

    return mocker.patch("app.service_api_client.update_service_template", side_effect=_update)


@pytest.fixture(scope="function")
def mock_create_service_template_content_too_big(mocker):
    def _create(name, type_, content, service, parent_folder_id=None):
        json_mock = Mock(
            return_value={
                "message": {"content": ["Content has a character count greater than the limit of 459"]},
                "result": "error",
            }
        )
        resp_mock = Mock(status_code=400, json=json_mock)
        http_error = HTTPError(
            response=resp_mock, message={"content": ["Content has a character count greater than the limit of 459"]}
        )
        raise http_error

    return mocker.patch("app.service_api_client.create_service_template", side_effect=_create)


@pytest.fixture(scope="function")
def mock_update_service_template_400_content_too_big(mocker):
    def _update(id_, name, type_, content, service):
        json_mock = Mock(
            return_value={
                "message": {"content": ["Content has a character count greater than the limit of 459"]},
                "result": "error",
            }
        )
        resp_mock = Mock(status_code=400, json=json_mock)
        http_error = HTTPError(
            response=resp_mock, message={"content": ["Content has a character count greater than the limit of 459"]}
        )
        raise http_error

    return mocker.patch("app.service_api_client.update_service_template", side_effect=_update)


def create_service_templates(service_id, number_of_templates=6):
    service_templates = []

    for num in range(1, number_of_templates + 1):
        template_type = "broadcast"
        service_templates.append(
            template_json(
                service_id,
                TEMPLATE_ONE_ID if num == 1 else str(generate_uuid()),
                "{}_template_{}".format(template_type, str(num)),
                template_type,
                "{} template {} content".format(template_type, str(num)),
            )
        )

    return {"data": service_templates}


def _template(template_type, name, parent=None, template_id=None):
    return {
        "id": template_id or str(uuid4()),
        "name": name,
        "template_type": template_type,
        "folder": parent,
        "content": "Broadcast template",
    }


@pytest.fixture(scope="function")
def mock_get_service_templates(mocker):
    def _create(service_id):
        return create_service_templates(service_id)

    return mocker.patch("app.service_api_client.get_service_templates", side_effect=_create)


@pytest.fixture(scope="function")
def mock_get_more_service_templates_than_can_fit_onscreen(mocker):
    def _create(service_id):
        return create_service_templates(service_id, number_of_templates=20)

    return mocker.patch("app.service_api_client.get_service_templates", side_effect=_create)


@pytest.fixture(scope="function")
def mock_get_service_templates_when_no_templates_exist(mocker):
    def _create(service_id):
        return {"data": []}

    return mocker.patch("app.service_api_client.get_service_templates", side_effect=_create)


@pytest.fixture(scope="function")
def mock_get_service_templates_with_only_one_template(mocker):
    def _get(service_id):
        return {
            "data": [
                template_json(
                    service_id, generate_uuid(), "broadcast_template_one", "broadcast", "broadcast template one content"
                )
            ]
        }

    return mocker.patch("app.service_api_client.get_service_templates", side_effect=_get)


@pytest.fixture(scope="function")
def mock_delete_service_template(mocker):
    def _delete(service_id, template_id):
        template = template_json(service_id, template_id, "Template to delete", "sms", "content to be deleted")
        return {"data": template}

    return mocker.patch("app.service_api_client.delete_service_template", side_effect=_delete)


@pytest.fixture(scope="function")
def mock_redact_template(mocker):
    return mocker.patch("app.service_api_client.redact_service_template")


@pytest.fixture(scope="function")
def mock_update_service_template_sender(mocker):
    def _update(service_id, template_id, reply_to):
        return

    return mocker.patch("app.service_api_client.update_service_template_sender", side_effect=_update)


@pytest.fixture(scope="function")
def api_user_pending(fake_uuid):
    return create_user(id=fake_uuid, state="pending")


@pytest.fixture(scope="function")
def platform_admin_user(fake_uuid):
    return create_platform_admin_user(
        permissions={
            SERVICE_ONE_ID: [
                "manage_users",
                "manage_templates",
                "manage_settings",
                "manage_api_keys",
                "view_activity",
            ]
        }
    )


@pytest.fixture(scope="function")
def platform_admin_capable_user(platform_admin_user):
    platform_admin_user["platform_admin_active"] = False
    return platform_admin_user


@pytest.fixture(scope="function")
def platform_admin_user_no_service_permissions():
    """
    this fixture is for situations where we want to test that platform admin can access
    an endpoint even though they have no explicit permissions for that service.
    """
    return create_platform_admin_user()


@pytest.fixture(scope="function")
def api_user_active():
    return create_api_user_active()


@pytest.fixture(scope="function")
def api_user_active_email_auth(fake_uuid):
    return create_user(id=fake_uuid, auth_type="email_auth")


@pytest.fixture(scope="function")
def active_user_with_permissions_no_mobile(fake_uuid):
    return create_service_one_admin(
        id=fake_uuid,
        mobile_number=None,
    )


@pytest.fixture(scope="function")
def api_nongov_user_active(fake_uuid):
    return create_service_one_admin(
        id=fake_uuid,
        email_address="someuser@example.com",
    )


@pytest.fixture(scope="function")
def active_user_with_permissions(fake_uuid):
    return create_active_user_with_permissions()


@pytest.fixture(scope="function")
def active_new_user_with_permissions(fake_uuid):
    return create_active_new_user_view_permissions()


@pytest.fixture(scope="function")
def active_user_create_broadcasts_permission():
    return create_active_user_create_broadcasts_permissions()


@pytest.fixture(scope="function")
def active_user_approve_broadcasts_permission():
    return create_active_user_approve_broadcasts_permissions()


@pytest.fixture(scope="function")
def active_user_with_permission_to_two_services(fake_uuid):
    permissions = [
        "manage_users",
        "manage_templates",
        "manage_settings",
        "manage_api_keys",
        "view_activity",
    ]

    return create_user(
        id=fake_uuid,
        permissions={
            SERVICE_ONE_ID: permissions,
            SERVICE_TWO_ID: permissions,
        },
        organisations=[ORGANISATION_ID],
        services=[SERVICE_ONE_ID, SERVICE_TWO_ID],
    )


@pytest.fixture(scope="function")
def active_user_with_permission_to_other_service(active_user_with_permission_to_two_services):
    active_user_with_permission_to_two_services["permissions"].pop(SERVICE_ONE_ID)
    active_user_with_permission_to_two_services["services"].pop(0)
    active_user_with_permission_to_two_services["name"] = "Service Two User"
    active_user_with_permission_to_two_services["email_address"] = "service-two-user@test.gov.uk"
    return active_user_with_permission_to_two_services


@pytest.fixture
def active_user_view_permissions():
    return create_active_user_view_permissions()


@pytest.fixture
def active_user_no_settings_permission():
    return create_active_user_no_settings_permission()


@pytest.fixture(scope="function")
def api_user_locked(fake_uuid):
    return create_user(
        id=fake_uuid,
        failed_login_count=5,
        password_changed_at=None,
    )


@pytest.fixture(scope="function")
def api_user_request_password_reset(fake_uuid):
    return create_user(
        id=fake_uuid,
        failed_login_count=5,
    )


@pytest.fixture(scope="function")
def api_user_changed_password(fake_uuid):
    return create_user(
        id=fake_uuid,
        failed_login_count=5,
        password_changed_at=str(datetime.now(timezone.utc) + timedelta(minutes=1)),
    )


@pytest.fixture(scope="function")
def mock_send_change_email_verification(mocker):
    return mocker.patch("app.user_api_client.send_change_email_verification")


@pytest.fixture(scope="function")
def mock_register_user(mocker, api_user_pending):
    def _register(name, email_address, mobile_number, password, auth_type):
        api_user_pending["name"] = name
        api_user_pending["email_address"] = email_address
        api_user_pending["mobile_number"] = mobile_number
        api_user_pending["password"] = password
        api_user_pending["auth_type"] = auth_type
        return api_user_pending

    return mocker.patch("app.user_api_client.register_user", side_effect=_register)


@pytest.fixture(scope="function")
def login_non_govuser(client_request, api_user_active):
    api_user_active["email_address"] = "someuser@example.com"

    client_request.login(api_user_active)


@pytest.fixture(scope="function")
def mock_get_user(mocker, api_user_active):
    def _get_user(id_):
        api_user_active["id"] = id_
        return api_user_active

    return mocker.patch("app.user_api_client.get_user", side_effect=_get_user)


@pytest.fixture(scope="function")
def mock_get_locked_user(mocker, api_user_locked):
    def _get_user(id_):
        api_user_locked["id"] = id_
        return api_user_locked

    return mocker.patch("app.user_api_client.get_user", side_effect=_get_user)


@pytest.fixture(scope="function")
def mock_get_user_pending(mocker, api_user_pending):
    return mocker.patch("app.user_api_client.get_user", return_value=api_user_pending)


@pytest.fixture(scope="function")
def mock_get_user_by_email(mocker, api_user_active):
    def _get_user(email_address):
        api_user_active["email_address"] = email_address
        return api_user_active

    return mocker.patch("app.user_api_client.get_user_by_email", side_effect=_get_user)


@pytest.fixture(scope="function")
def mock_already_registered(mocker):
    def _is_already_registered(email_address):
        return True

    return mocker.patch("app.models.user.User.already_registered", side_effect=_is_already_registered)


@pytest.fixture(scope="function")
def mock_not_already_registered(mocker):
    def _is_already_registered(email_address):
        return False

    return mocker.patch("app.models.user.User.already_registered", side_effect=_is_already_registered)


@pytest.fixture(scope="function")
def mock_check_password(mocker):
    def _is_valid(pwd):
        return True

    return mocker.patch("app.models.user.User.already_registered", side_effect=_is_valid)


@pytest.fixture(scope="function")
def mock_dont_get_user_by_email(mocker):
    def _get_user(email_address):
        return None

    return mocker.patch("app.user_api_client.get_user_by_email", side_effect=_get_user, autospec=True)


@pytest.fixture(scope="function")
def mock_get_user_by_email_request_password_reset(mocker, api_user_request_password_reset):
    return mocker.patch("app.user_api_client.get_user_by_email", return_value=api_user_request_password_reset)


@pytest.fixture(scope="function")
def mock_get_user_by_email_user_changed_password(mocker, api_user_changed_password):
    return mocker.patch("app.user_api_client.get_user_by_email", return_value=api_user_changed_password)


@pytest.fixture(scope="function")
def mock_get_user_by_email_locked(mocker, api_user_locked):
    return mocker.patch("app.user_api_client.get_user_by_email", return_value=api_user_locked)


@pytest.fixture(scope="function")
def mock_get_user_by_email_pending(mocker, api_user_pending):
    return mocker.patch("app.user_api_client.get_user_by_email", return_value=api_user_pending)


@pytest.fixture(scope="function")
def mock_get_user_by_email_not_found(mocker, api_user_active):
    def _get_user(email):
        json_mock = Mock(return_value={"message": "Not found", "result": "error"})
        resp_mock = Mock(status_code=404, json=json_mock)
        http_error = HTTPError(response=resp_mock, message="Default message")
        raise http_error

    return mocker.patch("app.user_api_client.get_user_by_email", side_effect=_get_user)


@pytest.fixture(scope="function")
def mock_verify_password(mocker):
    def _verify_password(user, password):
        return True

    return mocker.patch("app.user_api_client.verify_password", side_effect=_verify_password)


@pytest.fixture(scope="function")
def mock_update_user_password(mocker, api_user_active):
    def _update(user_id, password):
        api_user_active["id"] = user_id
        return api_user_active

    return mocker.patch("app.user_api_client.update_password", side_effect=_update)


@pytest.fixture(scope="function")
def mock_update_user_attribute(mocker, api_user_active):
    def _update(user_id, **kwargs):
        api_user_active["id"] = user_id
        return api_user_active

    return mocker.patch("app.user_api_client.update_user_attribute", side_effect=_update)


@pytest.fixture
def mock_activate_user(mocker, api_user_active):
    def _activate(user_id):
        api_user_active["id"] = user_id
        return {"data": api_user_active}

    return mocker.patch("app.user_api_client.activate_user", side_effect=_activate)


@pytest.fixture(scope="function")
def mock_email_is_not_already_in_use(mocker):
    return mocker.patch("app.user_api_client.get_user_by_email_or_none", return_value=None)


@pytest.fixture(scope="function")
def mock_check_user_exists_for_nonexistent_user(mocker):
    return mocker.patch("app.user_api_client.check_user_exists", return_value=False)


@pytest.fixture(scope="function")
def mock_check_user_exists_for_existing_user(mocker):
    return mocker.patch("app.user_api_client.check_user_exists", return_value=True)


@pytest.fixture(scope="function")
def mock_revoke_api_key(mocker):
    def _revoke(service_id, key_id):
        return {}

    return mocker.patch("app.api_key_api_client.revoke_api_key", side_effect=_revoke)


@pytest.fixture(scope="function")
def mock_get_api_keys(mocker, fake_uuid):
    def _get_keys(service_id, key_id=None):
        keys = {
            "apiKeys": [
                api_key_json(
                    id_=fake_uuid,
                    name="some key name",
                ),
                api_key_json(id_="1234567", name="another key name", expiry_date=str(date.fromtimestamp(0))),
            ]
        }
        return keys

    return mocker.patch("app.api_key_api_client.get_api_keys", side_effect=_get_keys)


@pytest.fixture(scope="function")
def mock_get_no_api_keys(mocker):
    def _get_keys(service_id):
        keys = {"apiKeys": []}
        return keys

    return mocker.patch("app.api_key_api_client.get_api_keys", side_effect=_get_keys)


@pytest.fixture(scope="function")
def mock_login(mocker, mock_get_user, mock_update_user_attribute, mock_events):
    def _verify_code(user_id, code, code_type):
        return True, ""

    def _no_services(params_dict=None):
        return {"data": []}

    return (
        mocker.patch("app.user_api_client.check_verify_code", side_effect=_verify_code),
        mocker.patch("app.service_api_client.get_services", side_effect=_no_services),
    )


@pytest.fixture(scope="function")
def mock_send_verify_code(mocker):
    return mocker.patch("app.user_api_client.send_verify_code")


@pytest.fixture(scope="function")
def mock_send_verify_email(mocker):
    return mocker.patch("app.user_api_client.send_verify_email")


@pytest.fixture(scope="function")
def mock_check_verify_code(mocker):
    def _verify(user_id, code, code_type):
        return True, ""

    return mocker.patch("app.user_api_client.check_verify_code", side_effect=_verify)


@pytest.fixture(scope="function")
def mock_check_verify_code_code_not_found(mocker):
    def _verify(user_id, code, code_type):
        return False, "Code not found"

    return mocker.patch("app.user_api_client.check_verify_code", side_effect=_verify)


@pytest.fixture(scope="function")
def mock_check_verify_code_code_expired(mocker):
    def _verify(user_id, code, code_type):
        return False, "Code has expired"

    return mocker.patch("app.user_api_client.check_verify_code", side_effect=_verify)


@pytest.fixture(scope="function")
def mock_has_permissions(mocker):
    def _has_permission(*permissions, restrict_admin_usage=False, allow_org_user=False):
        return True

    return mocker.patch("app.models.user.User.has_permissions", side_effect=_has_permission)


@pytest.fixture(scope="function")
def mock_get_users_by_service(mocker):
    def _get_users_for_service(service_id):
        return [
            create_service_one_admin(
                id=sample_uuid(),
                logged_in_at=None,
                mobile_number="+447700900986",
                email_address="notify@digital.cabinet-office.gov.uk",
            )
        ]

    # You shouldn’t be calling the user API client directly, so it’s the
    # instance on the model that’s mocked here
    return mocker.patch("app.models.user.Users.client_method", side_effect=_get_users_for_service)


@pytest.fixture(scope="function")
def sample_invite(mocker, service_one):
    id_ = USER_ONE_ID
    from_user = service_one["users"][0]
    email_address = "invited_user@test.gov.uk"
    service_id = service_one["id"]
    permissions = "view_activity,manage_settings,manage_users,manage_api_keys"
    created_at = str(datetime.now(timezone.utc))
    auth_type = "sms_auth"
    folder_permissions = []

    return invite_json(
        id_, from_user, service_id, email_address, permissions, created_at, "pending", auth_type, folder_permissions
    )


@pytest.fixture(scope="function")
def mock_create_invite(mocker, sample_invite):
    def _create_invite(from_user, service_id, email_address, permissions, folder_permissions):
        sample_invite["from_user"] = from_user
        sample_invite["service"] = service_id
        sample_invite["email_address"] = email_address
        sample_invite["status"] = "pending"
        sample_invite["permissions"] = permissions
        sample_invite["folder_permissions"] = folder_permissions
        return sample_invite

    return mocker.patch("app.invite_api_client.create_invite", side_effect=_create_invite)


@pytest.fixture(scope="function")
def mock_get_invites_for_service(mocker, service_one, sample_invite):
    def _get_invites(service_id):
        data = []
        for i in range(0, 5):
            invite = copy.copy(sample_invite)
            invite["email_address"] = "user_{}@testnotify.gov.uk".format(i)
            data.append(invite)
        return data

    return mocker.patch("app.models.user.InvitedUsers.client_method", side_effect=_get_invites)


@pytest.fixture(scope="function")
def mock_get_invites_without_manage_permission(mocker, service_one, sample_invite):
    def _get_invites(service_id):
        return [
            invite_json(
                id_=str(sample_uuid()),
                from_user=service_one["users"][0],
                email_address="invited_user@test.gov.uk",
                service_id=service_one["id"],
                permissions="view_activity,create_broadcasts,manage_api_keys",
                created_at=str(datetime.now(timezone.utc)),
                auth_type="sms_auth",
                folder_permissions=[],
                status="pending",
            )
        ]

    return mocker.patch("app.models.user.InvitedUsers.client_method", side_effect=_get_invites)


@pytest.fixture(scope="function")
def mock_accept_invite(mocker, sample_invite):
    def _accept(service_id, invite_id):
        return sample_invite

    return mocker.patch("app.invite_api_client.accept_invite", side_effect=_accept)


@pytest.fixture(scope="function")
def mock_add_user_to_service(mocker, service_one, api_user_active):
    def _add_user(service_id, user_id, permissions, folder_permissions):
        return

    return mocker.patch("app.user_api_client.add_user_to_service", side_effect=_add_user)


@pytest.fixture(scope="function")
def mock_set_user_permissions(mocker):
    return mocker.patch("app.user_api_client.set_user_permissions", return_value=None)


@pytest.fixture(scope="function")
def mock_remove_user_from_service(mocker):
    return mocker.patch("app.service_api_client.remove_user_from_service", return_value=None)


@pytest.fixture(scope="function")
def mock_get_template_statistics(mocker, service_one, fake_uuid):
    template = template_json(service_one["id"], fake_uuid, "Test template", "sms", "Something very interesting")
    data = {
        "count": 1,
        "template_name": template["name"],
        "template_type": template["template_type"],
        "template_id": template["id"],
        "is_precompiled_letter": False,
        "status": "delivered",
    }

    def _get_stats(service_id, limit_days=None):
        return [data]

    return mocker.patch("app.template_statistics_client.get_template_statistics_for_service", side_effect=_get_stats)


@pytest.fixture(scope="function")
def mock_get_monthly_template_usage(mocker, service_one, fake_uuid):
    def _stats(service_id, year):
        return [
            {"template_id": fake_uuid, "month": 4, "year": year, "count": 2, "name": "My first template", "type": "sms"}
        ]

    return mocker.patch("app.template_statistics_client.get_monthly_template_usage_for_service", side_effect=_stats)


@pytest.fixture(scope="function")
def mock_get_monthly_notification_stats(mocker, service_one, fake_uuid):
    def _stats(service_id, year):
        return {
            "data": {
                datetime.now(timezone.utc).strftime("%Y-%m"): {
                    "email": {
                        "sending": 1,
                        "delivered": 1,
                    },
                    "sms": {
                        "sending": 1,
                        "delivered": 1,
                    },
                    "letter": {
                        "sending": 1,
                        "delivered": 1,
                    },
                }
            }
        }

    return mocker.patch("app.service_api_client.get_monthly_notification_stats", side_effect=_stats)


@pytest.fixture(scope="function")
def mock_events(mocker):
    def _create_event(event_type, event_data):
        return {"some": "data"}

    return mocker.patch("app.events_api_client.create_event", side_effect=_create_event)


@pytest.fixture(scope="function")
def mock_send_already_registered_email(mocker):
    return mocker.patch("app.user_api_client.send_already_registered_email")


@pytest.fixture(scope="function")
def mock_get_guest_list(mocker):
    def _get_guest_list(service_id):
        return {"email_addresses": ["test@example.com"], "phone_numbers": ["07900900000"]}

    return mocker.patch("app.service_api_client.get_guest_list", side_effect=_get_guest_list)


@pytest.fixture(scope="function")
def mock_update_guest_list(mocker):
    return mocker.patch("app.service_api_client.update_guest_list")


@pytest.fixture(scope="function")
def mock_reset_failed_login_count(mocker):
    return mocker.patch("app.user_api_client.reset_failed_login_count")


@pytest.fixture(scope="function")
def _client(notify_admin):
    """
    Do not use this fixture directly – use `client_request` instead
    """
    with notify_admin.test_request_context(), notify_admin.test_client() as client:
        yield client


@pytest.fixture(scope="function")
def _logged_in_client(_client, active_user_with_permissions, mocker, service_one, mock_login):
    """
    Do not use this fixture directly – use `client_request` instead
    """
    _client.login(active_user_with_permissions, mocker, service_one)
    yield _client


@pytest.fixture
def os_environ():
    """
    clear os.environ, and restore it after the test runs
    """
    # for use whenever you expect code to edit environment variables
    old_env = os.environ.copy()
    os.environ.clear()
    yield
    for k, v in old_env.items():
        os.environ[k] = v


@pytest.fixture  # noqa (C901 too complex)
def client_request(_logged_in_client, mocker, service_one):  # noqa (C901 too complex)
    mocker.patch("app.feature_toggle_api_client.get_feature_toggle", return_value={})

    def block_method(object, method_name, preferred_method_name):
        def blocked_method(*args, **kwargs):
            raise AttributeError(
                f"Don’t use {object.__class__.__name__}.{method_name}"
                f" – try {object.__class__.__name__}.{preferred_method_name} instead"
            )

        setattr(object, method_name, blocked_method)

    class ClientRequest:
        @staticmethod
        @contextmanager
        def session_transaction():
            with _logged_in_client.session_transaction() as session:
                yield session

        @staticmethod
        def login(user, service=service_one):
            _logged_in_client.login(user, mocker, service)

        @staticmethod
        def logout():
            _logged_in_client.logout(None)

        @staticmethod
        def get(
            endpoint,
            _expected_status=200,
            _follow_redirects=False,
            _expected_redirect=None,
            _test_page_title=True,
            _test_page_prefix=None,
            _test_for_elements_without_class=True,
            _optional_args="",
            **endpoint_kwargs,
        ):
            return ClientRequest.get_url(
                url_for(endpoint, **(endpoint_kwargs or {})) + _optional_args,
                _expected_status=_expected_status,
                _follow_redirects=_follow_redirects,
                _expected_redirect=_expected_redirect,
                _test_page_title=_test_page_title,
                _test_page_prefix=_test_page_prefix,
                _test_for_elements_without_class=_test_for_elements_without_class,
            )

        @staticmethod
        def get_url(
            url,
            _expected_status=200,
            _follow_redirects=False,
            _expected_redirect=None,
            _test_page_title=True,
            _test_page_prefix=None,
            _test_for_elements_without_class=True,
            **endpoint_kwargs,
        ):
            resp = _logged_in_client.get(
                url,
                follow_redirects=_follow_redirects,
            )

            if _expected_redirect and _expected_status == 200:
                _expected_status = 302

            assert resp.status_code == _expected_status, resp.location

            if _expected_redirect:
                assert resp.location == _expected_redirect

            page = NotifyBeautifulSoup(resp.data.decode("utf-8"), "html.parser")

            if _test_page_title:
                # Page should have one H1
                if _test_page_prefix:
                    page_title = normalize_spaces(page.select_one("title").text)
                    assert normalize_spaces(page_title).startswith(
                        f"{_test_page_prefix}"
                    ), f"Page {url} title '{page_title}' does not start with prefix '{_test_page_prefix}'"
                else:
                    assert len(page.select("h1")) == 1
                    page_title, h1 = (normalize_spaces(page.select_one(selector).text) for selector in ("title", "h1"))
                    assert normalize_spaces(page_title).startswith(
                        h1
                    ), f"Page {url} title '{page_title}' does not start with H1 '{h1}'"

            if _test_for_elements_without_class and _expected_status not in (301, 302):
                for tag, hint in (
                    ("p", "govuk-body"),
                    ("a", "govuk-link govuk-link--no-visited-state"),
                ):
                    element = page.select_one(f"{tag}:not([class])")
                    if (
                        element
                        and not element.has_attr("style")  # Elements with inline CSS are exempt
                        and element.text.strip()  # Empty elements are exempt
                    ):
                        raise AssertionError(
                            f"Found a <{tag}> without a class attribute:\n"
                            f"    {element}\n"
                            f"\n"
                            f'(you probably want to add class="{hint}")'
                        )
            return page

        @staticmethod
        def post(
            endpoint,
            _data=None,
            _expected_status=None,
            _follow_redirects=False,
            _expected_redirect=None,
            _content_type=None,
            **endpoint_kwargs,
        ):
            return ClientRequest.post_url(
                url_for(endpoint, **(endpoint_kwargs or {})),
                _data=_data,
                _expected_status=_expected_status,
                _follow_redirects=_follow_redirects,
                _expected_redirect=_expected_redirect,
                _content_type=_content_type,
            )

        @staticmethod
        def post_url(
            url,
            _data=None,
            _expected_status=None,
            _follow_redirects=False,
            _expected_redirect=None,
            _content_type=None,
        ):
            if _expected_status is None:
                _expected_status = 200 if _follow_redirects else 302
            post_kwargs = {}
            if _content_type:
                post_kwargs.update(content_type=_content_type)
            resp = _logged_in_client.post(url, data=_data, follow_redirects=_follow_redirects, **post_kwargs)
            assert resp.status_code == _expected_status
            if _expected_redirect:
                assert_url_expected(resp.location, _expected_redirect)

            return NotifyBeautifulSoup(resp.data.decode("utf-8"), "html.parser")

        @staticmethod
        def get_response(endpoint, _expected_status=200, _optional_args="", **endpoint_kwargs):
            return ClientRequest.get_response_from_url(
                url_for(endpoint, **(endpoint_kwargs or {})) + _optional_args,
                _expected_status=_expected_status,
            )

        @staticmethod
        def get_response_from_url(
            url,
            _expected_status=200,
        ):
            resp = _logged_in_client.get(url)
            assert resp.status_code == _expected_status
            return resp

        @staticmethod
        def post_response(
            endpoint, _data=None, _expected_status=302, _optional_args="", _content_type=None, **endpoint_kwargs
        ):
            return ClientRequest.post_response_from_url(
                url_for(endpoint, **(endpoint_kwargs or {})) + _optional_args,
                _data=_data,
                _content_type=_content_type,
                _expected_status=_expected_status,
            )

        @staticmethod
        def post_response_from_url(
            url,
            _data=None,
            _expected_status=302,
            _content_type=None,
        ):
            post_kwargs = {}
            if _content_type:
                post_kwargs.update(content_type=_content_type)
            resp = _logged_in_client.post(url, data=_data, **post_kwargs)
            assert resp.status_code == _expected_status
            return resp

    return ClientRequest


def normalize_spaces(input):
    if isinstance(input, str):
        return " ".join(input.split())
    return normalize_spaces(" ".join(item.text for item in input))


@pytest.fixture(scope="function")
def mock_get_service_data_retention(mocker):
    data = {
        "id": str(sample_uuid()),
        "service_id": str(sample_uuid()),
        "service_name": "service name",
        "notification_type": "email",
        "days_of_retention": 7,
        "created_at": datetime.now(),
        "updated_at": None,
    }
    return mocker.patch("app.service_api_client.get_service_data_retention", return_value=[data])


@pytest.fixture(scope="function")
def mock_create_service_data_retention(mocker):
    return mocker.patch("app.service_api_client.create_service_data_retention")


@pytest.fixture(scope="function")
def mock_update_service_data_retention(mocker):
    return mocker.patch("app.service_api_client.update_service_data_retention")


@contextmanager
def set_config(app, name, value):
    old_val = app.config.get(name)
    app.config[name] = value
    yield
    app.config[name] = old_val


@contextmanager
def set_config_values(app, dict):
    old_values = {}

    for key in dict:
        old_values[key] = app.config.get(key)
        app.config[key] = dict[key]

    yield

    for key in dict:
        app.config[key] = old_values[key]


@pytest.fixture
def webauthn_dev_server(notify_admin, mocker):
    overrides = {
        "HOST": "local",
        "ADMIN_BASE_URL": "https://webauthn.io",
        "ADMIN_EXTERNAL_URL": "https://webauthn.io",
    }

    with set_config_values(notify_admin, overrides):
        webauthn_server.init_app(notify_admin)
        yield

    webauthn_server.init_app(notify_admin)


@pytest.fixture(scope="function")
def valid_token(notify_admin, fake_uuid):
    return generate_token(
        json.dumps({"user_id": fake_uuid, "secret_code": "my secret"}),
        notify_admin.config["SECRET_KEY"],
        notify_admin.config["DANGEROUS_SALT"],
    )


@pytest.fixture(scope="function")
def mock_get_valid_service_inbound_api(mocker):
    def _get(service_id, inbound_api_id):
        return {
            "created_at": "2017-12-04T10:52:55.289026Z",
            "updated_by_id": fake_uuid,
            "id": inbound_api_id,
            "url": "https://hello3.gov.uk",
            "service_id": service_id,
            "updated_at": "2017-12-04T11:28:42.575153Z",
        }

    return mocker.patch("app.service_api_client.get_service_inbound_api", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_valid_service_callback_api(mocker):
    def _get(service_id, callback_api_id):
        return {
            "created_at": "2017-12-04T10:52:55.289026Z",
            "updated_by_id": fake_uuid,
            "id": callback_api_id,
            "url": "https://hello2.gov.uk",
            "service_id": service_id,
            "updated_at": "2017-12-04T11:28:42.575153Z",
        }

    return mocker.patch("app.service_api_client.get_service_callback_api", side_effect=_get)


@pytest.fixture(scope="function")
def mock_get_empty_service_inbound_api(mocker):
    return mocker.patch(
        "app.service_api_client.get_service_inbound_api",
        side_effect=lambda service_id, callback_api_id: None,
    )


@pytest.fixture(scope="function")
def mock_get_empty_service_callback_api(mocker):
    return mocker.patch(
        "app.service_api_client.get_service_callback_api",
        side_effect=lambda service_id, callback_api_id: None,
    )


@pytest.fixture(scope="function")
def mock_create_service_inbound_api(mocker):
    def _create_service_inbound_api(service_id, url, bearer_token, user_id):
        return

    return mocker.patch("app.service_api_client.create_service_inbound_api", side_effect=_create_service_inbound_api)


@pytest.fixture(scope="function")
def mock_update_service_inbound_api(mocker):
    def _update_service_inbound_api(service_id, url, bearer_token, user_id, inbound_api_id):
        return

    return mocker.patch("app.service_api_client.update_service_inbound_api", side_effect=_update_service_inbound_api)


@pytest.fixture(scope="function")
def mock_create_service_callback_api(mocker):
    def _create_service_callback_api(service_id, url, bearer_token, user_id):
        return

    return mocker.patch("app.service_api_client.create_service_callback_api", side_effect=_create_service_callback_api)


@pytest.fixture(scope="function")
def mock_update_service_callback_api(mocker):
    def _update_service_callback_api(service_id, url, bearer_token, user_id, callback_api_id):
        return

    return mocker.patch("app.service_api_client.update_service_callback_api", side_effect=_update_service_callback_api)


@pytest.fixture(scope="function")
def organisation_one(api_user_active):
    return organisation_json(ORGANISATION_ID, "organisation one", [api_user_active["id"]])


@pytest.fixture(scope="function")
def mock_get_organisations(mocker):
    def _get_organisations():
        return [
            organisation_json("7aa5d4e9-4385-4488-a489-07812ba13383", "Org 1"),
            organisation_json("7aa5d4e9-4385-4488-a489-07812ba13384", "Org 2"),
            organisation_json("7aa5d4e9-4385-4488-a489-07812ba13385", "Org 3"),
        ]

    mocker.patch(
        "app.models.organisation.AllOrganisations.client_method",
        side_effect=_get_organisations,
    )

    return mocker.patch(
        "app.notify_client.organisations_api_client.organisations_client.get_organisations",
        side_effect=_get_organisations,
    )


@pytest.fixture(scope="function")
def mock_get_organisations_with_unusual_domains(mocker):
    def _get_organisations():
        return [
            organisation_json(
                "7aa5d4e9-4385-4488-a489-07812ba13383",
                "Org 1",
                domains=[
                    "ldquo.net",
                    "rdquo.net",
                    "lsquo.net",
                    "rsquo.net",
                ],
            ),
        ]

    return mocker.patch("app.organisations_client.get_organisations", side_effect=_get_organisations)


@pytest.fixture(scope="function")
def mock_get_organisation(mocker):
    def _get_organisation(org_id):
        return organisation_json(
            org_id,
            {
                "o1": "Org 1",
                "o2": "Org 2",
                "o3": "Org 3",
            }.get(org_id, "Test organisation"),
        )

    return mocker.patch("app.organisations_client.get_organisation", side_effect=_get_organisation)


@pytest.fixture(scope="function")
def mock_get_organisation_by_domain(mocker):
    def _get_organisation_by_domain(domain):
        return organisation_json(ORGANISATION_ID)

    return mocker.patch(
        "app.organisations_client.get_organisation_by_domain",
        side_effect=_get_organisation_by_domain,
    )


@pytest.fixture(scope="function")
def mock_get_no_organisation_by_domain(mocker):
    return mocker.patch(
        "app.organisations_client.get_organisation_by_domain",
        return_value=None,
    )


@pytest.fixture(scope="function")
def mock_get_service_organisation(
    mocker,
    mock_get_organisation,
):
    return mocker.patch(
        "app.models.service.Service.organisation_id",
        new_callable=PropertyMock,
        return_value=ORGANISATION_ID,
    )


@pytest.fixture(scope="function")
def mock_update_service_organisation(mocker):
    def _update_service_organisation(service_id, org_id):
        return

    return mocker.patch(
        "app.organisations_client.update_service_organisation", side_effect=_update_service_organisation
    )


def _get_organisation_services(organisation_id):
    if organisation_id == "o1":
        return [
            service_json("12345", "service one", restricted=False),
            service_json("67890", "service two"),
            service_json("abcde", "service three"),
        ]
    if organisation_id == "o2":
        return [
            service_json("12345", "service one (org 2)", restricted=False),
            service_json("67890", "service two (org 2)", restricted=False),
            service_json("abcde", "service three"),
        ]
    return [
        service_json("12345", "service one"),
        service_json("67890", "service two"),
        service_json(SERVICE_ONE_ID, "service one", [sample_uuid()]),
    ]


@pytest.fixture(scope="function")
def mock_get_organisation_services(mocker, api_user_active):
    return mocker.patch("app.organisations_client.get_organisation_services", side_effect=_get_organisation_services)


@pytest.fixture(scope="function")
def mock_get_users_for_organisation(mocker):
    def _get_users_for_organisation(org_id):
        return [
            user_json(id_="1234", name="Test User 1"),
            user_json(id_="5678", name="Test User 2", email_address="testt@gov.uk"),
        ]

    return mocker.patch("app.models.user.OrganisationUsers.client_method", side_effect=_get_users_for_organisation)


@pytest.fixture(scope="function")
def mock_get_invited_users_for_organisation(mocker, sample_org_invite):
    def _get_invited_invited_users_for_organisation(org_id):
        return [sample_org_invite]

    return mocker.patch(
        "app.models.user.OrganisationInvitedUsers.client_method",
        side_effect=_get_invited_invited_users_for_organisation,
    )


@pytest.fixture(scope="function")
def sample_org_invite(mocker, organisation_one):
    id_ = str(UUID(bytes=b"sample_org_invit", version=4))
    invited_by = organisation_one["users"][0]
    email_address = "invited_user@test.gov.uk"
    organisation = organisation_one["id"]
    created_at = str(datetime.now(timezone.utc))
    status = "pending"

    return org_invite_json(id_, invited_by, organisation, email_address, created_at, status)


@pytest.fixture(scope="function")
def mock_get_invites_for_organisation(mocker, sample_org_invite):
    def _get_org_invites(org_id):
        data = []
        for i in range(0, 5):
            invite = copy.copy(sample_org_invite)
            invite["email_address"] = "user_{}@testnotify.gov.uk".format(i)
            data.append(invite)
        return data

    return mocker.patch("app.models.user.OrganisationInvitedUsers.client_method", side_effect=_get_org_invites)


@pytest.fixture(scope="function")
def mock_check_org_invite_token(mocker, sample_org_invite):
    def _check_org_token(token):
        return sample_org_invite

    return mocker.patch("app.org_invite_api_client.check_token", side_effect=_check_org_token)


@pytest.fixture(scope="function")
def mock_check_org_cancelled_invite_token(mocker, sample_org_invite):
    def _check_org_token(token):
        sample_org_invite["status"] = "cancelled"
        return sample_org_invite

    return mocker.patch("app.org_invite_api_client.check_token", side_effect=_check_org_token)


@pytest.fixture(scope="function")
def mock_check_org_accepted_invite_token(mocker, sample_org_invite):
    sample_org_invite["status"] = "accepted"

    def _check_org_token(token):
        return sample_org_invite

    return mocker.patch("app.org_invite_api_client.check_token", return_value=sample_org_invite)


@pytest.fixture(scope="function")
def mock_accept_org_invite(mocker, sample_org_invite):
    def _accept(organisation_id, invite_id):
        return sample_org_invite

    return mocker.patch("app.org_invite_api_client.accept_invite", side_effect=_accept)


@pytest.fixture(scope="function")
def mock_add_user_to_organisation(mocker, organisation_one, api_user_active):
    def _add_user(organisation_id, user_id):
        return api_user_active

    return mocker.patch("app.user_api_client.add_user_to_organisation", side_effect=_add_user)


@pytest.fixture(scope="function")
def mock_update_organisation(mocker):
    def _update_org(org, **kwargs):
        return

    return mocker.patch("app.organisations_client.update_organisation", side_effect=_update_org)


@pytest.fixture
def mock_get_organisations_and_services_for_user(mocker, organisation_one, api_user_active):
    def _get_orgs_and_services(user_id):
        return {"organisations": [], "services": []}

    return mocker.patch(
        "app.user_api_client.get_organisations_and_services_for_user", side_effect=_get_orgs_and_services
    )


@pytest.fixture
def mock_get_non_empty_organisations_and_services_for_user(mocker, organisation_one, api_user_active):
    def _make_services(name, trial_mode=False):
        return [
            {
                "name": "{} {}".format(name, i),
                "id": SERVICE_TWO_ID,
                "restricted": trial_mode,
                "organisation": None,
            }
            for i in range(1, 3)
        ]

    def _get_orgs_and_services(user_id):
        return {
            "organisations": [
                {
                    "name": "Org 1",
                    "id": "o1",
                    "count_of_live_services": 1,
                },
                {
                    "name": "Org 2",
                    "id": "o2",
                    "count_of_live_services": 2,
                },
                {
                    "name": "Org 3",
                    "id": "o3",
                    "count_of_live_services": 0,
                },
            ],
            "services": (
                _get_organisation_services("o1") + _get_organisation_services("o2") + _make_services("Service")
            ),
        }

    return mocker.patch(
        "app.user_api_client.get_organisations_and_services_for_user", side_effect=_get_orgs_and_services
    )


@pytest.fixture
def mock_get_just_services_for_user(mocker, organisation_one, api_user_active):
    def _make_services(name, trial_mode=False):
        return [
            {
                "name": "{} {}".format(name, i + 1),
                "id": id,
                "restricted": trial_mode,
                "organisation": None,
            }
            for i, id in enumerate([SERVICE_TWO_ID, SERVICE_ONE_ID])
        ]

    def _get_orgs_and_services(user_id):
        return {
            "organisations": [],
            "services": _make_services("Service"),
        }

    return mocker.patch(
        "app.user_api_client.get_organisations_and_services_for_user", side_effect=_get_orgs_and_services
    )


@pytest.fixture
def mock_get_empty_organisations_and_one_service_for_user(mocker, organisation_one, api_user_active):
    def _get_orgs_and_services(user_id):
        return {
            "organisations": [],
            "services": [
                {
                    "name": "Only service",
                    "id": SERVICE_TWO_ID,
                    "restricted": True,
                }
            ],
        }

    return mocker.patch(
        "app.user_api_client.get_organisations_and_services_for_user", side_effect=_get_orgs_and_services
    )


@pytest.fixture
def mock_create_event(mocker):
    """
    This should be used whenever your code is calling `flask_login.login_user`
    """

    def _add_event(event_type, event_data):
        return

    return mocker.patch("app.events_api_client.create_event", side_effect=_add_event)


def url_for_endpoint_with_token(endpoint, token, next=None):
    token = token.replace("%2E", ".")
    return url_for(endpoint, token=token, next=next)


@pytest.fixture
def mock_get_template_folders(mocker):
    return mocker.patch("app.template_folder_api_client.get_template_folders", return_value=[])


@pytest.fixture
def mock_move_to_template_folder(mocker):
    return mocker.patch("app.template_folder_api_client.move_to_folder")


@pytest.fixture
def mock_create_template_folder(mocker):
    return mocker.patch("app.template_folder_api_client.create_template_folder", return_value=sample_uuid())


@pytest.fixture(scope="function")
def mock_get_service_and_organisation_counts(mocker):
    return mocker.patch(
        "app.status_api_client.get_count_of_live_services_and_organisations",
        return_value={
            "organisations": 111,
            "services": 9999,
        },
    )


@pytest.fixture(scope="function")
def mock_get_service_history(mocker):
    return mocker.patch(
        "app.service_api_client.get_service_history",
        return_value={
            "service_history": [
                {
                    "name": "Example service",
                    "created_at": "2010-10-10T01:01:01.000000Z",
                    "updated_at": None,
                    "created_by_id": uuid4(),
                },
                {
                    "name": "Before lunch",
                    "created_at": "2010-10-10T01:01:01.000000Z",
                    "updated_at": "2012-12-12T12:12:12.000000Z",
                    "created_by_id": sample_uuid(),
                },
                {
                    "name": "After lunch",
                    "created_at": "2010-10-10T01:01:01.000000Z",
                    "updated_at": "2012-12-12T13:13:13.000000Z",
                    "created_by_id": sample_uuid(),
                },
            ],
            "api_key_history": [
                {
                    "name": "Good key",
                    "updated_at": None,
                    "created_at": "2010-10-10T10:10:10.000000Z",
                    "created_by_id": sample_uuid(),
                },
                {
                    "name": "Bad key",
                    "updated_at": "2012-11-11T12:12:12.000000Z",
                    "created_at": "2011-11-11T11:11:11.000000Z",
                    "created_by_id": sample_uuid(),
                },
                {
                    "name": "Bad key",
                    "updated_at": None,
                    "created_at": "2011-11-11T11:11:11.000000Z",
                    "created_by_id": sample_uuid(),
                },
                {
                    "name": "Key event returned in non-chronological order",
                    "updated_at": None,
                    "created_at": "2010-10-10T09:09:09.000000Z",
                    "created_by_id": sample_uuid(),
                },
            ],
            "events": [],
        },
    )


def create_api_user_active(with_unique_id=False):
    return create_user(
        id=str(uuid4()) if with_unique_id else sample_uuid(),
    )


def create_active_user_empty_permissions(with_unique_id=False):
    return create_service_one_user(
        id=str(uuid4()) if with_unique_id else sample_uuid(),
        name="Test User With Empty Permissions",
    )


def create_active_user_with_permissions(with_unique_id=False):
    return create_service_one_admin(
        id=str(uuid4()) if with_unique_id else sample_uuid(),
    )


def create_active_user_view_permissions(with_unique_id=False):
    return create_service_one_user(
        id=str(uuid4()) if with_unique_id else sample_uuid(),
        name="Test User With Permissions",
        permissions={SERVICE_ONE_ID: ["view_activity"]},
    )


def create_active_new_user_view_permissions(with_unique_id=False):
    return create_service_one_user(
        id=str(uuid4()) if with_unique_id else sample_uuid(),
        name="Test User With Permissions",
        permissions={SERVICE_ONE_ID: ["view_activity"]},
        email_address="new.user@user.gov.uk",
    )


def create_active_user_create_broadcasts_permissions(with_unique_id=False):
    return create_service_one_user(
        id=str(uuid4()) if with_unique_id else sample_uuid(),
        name="Test User Create Broadcasts Permission",
        permissions={
            SERVICE_ONE_ID: [
                "create_broadcasts",
                "reject_broadcasts",
                "cancel_broadcasts",
                "view_activity",  # added automatically by API
            ]
        },
        auth_type="webauthn_auth",
    )


def create_active_user_approve_broadcasts_permissions(with_unique_id=False):
    return create_service_one_user(
        id=str(uuid4()) if with_unique_id else sample_uuid(),
        name="Test User Approve Broadcasts Permission",
        permissions={
            SERVICE_ONE_ID: [
                "approve_broadcasts",
                "reject_broadcasts",
                "cancel_broadcasts",
                "view_activity",  # added automatically by API
            ]
        },
        auth_type="webauthn_auth",
    )


def create_active_user_no_api_key_permission(with_unique_id=False):
    return create_service_one_user(
        id=str(uuid4()) if with_unique_id else sample_uuid(),
        name="Test User With Permissions",
        permissions={
            SERVICE_ONE_ID: [
                "manage_templates",
                "manage_settings",
                "manage_users",
                "view_activity",
            ]
        },
    )


def create_active_user_no_settings_permission(with_unique_id=False):
    return create_service_one_user(
        id=str(uuid4()) if with_unique_id else sample_uuid(),
        name="Test User With Permissions",
        permissions={
            SERVICE_ONE_ID: [
                "manage_templates",
                "manage_api_keys",
                "view_activity",
            ]
        },
    )


def create_active_user_manage_template_permissions(with_unique_id=False):
    return create_service_one_user(
        id=str(uuid4()) if with_unique_id else sample_uuid(),
        name="Test User With Permissions",
        permissions={
            SERVICE_ONE_ID: [
                "manage_templates",
                "view_activity",
            ]
        },
    )


def create_platform_admin_user(with_unique_id=False, auth_type="webauthn_auth", permissions=None):
    return create_user(
        id=str(uuid4()) if with_unique_id else sample_uuid(),
        name="Platform admin user",
        email_address="platform@admin.gov.uk",
        permissions=permissions or {},
        platform_admin_capable=True,
        platform_admin_active=True,
        auth_type=auth_type,
        can_use_webauthn=True,
    )


def create_service_one_admin(**overrides):
    user_data = {
        "permissions": {
            SERVICE_ONE_ID: [
                "manage_users",
                "manage_templates",
                "manage_settings",
                "manage_api_keys",
                "view_activity",
            ]
        },
    }
    user_data.update(overrides)
    return create_service_one_user(**user_data)


def create_service_one_user(**overrides):
    user_data = {
        "organisations": [ORGANISATION_ID],
        "services": [SERVICE_ONE_ID],
    }
    user_data.update(overrides)
    return create_user(**user_data)


def create_user(**overrides):
    user_data = {
        "name": "Test User",
        "password": "somepassword",
        "email_address": "test@user.gov.uk",
        "mobile_number": "07700 900762",
        "state": "active",
        "failed_login_count": 0,
        "permissions": {},
        "platform_admin_capable": False,
        "platform_admin_redemption": None,
        # This is not a part of the database user object, but for tests can be used to elevate:
        "platform_admin_active": False,
        "auth_type": "sms_auth",
        "password_changed_at": str(datetime.now(timezone.utc)),
        "services": [],
        "organisations": [],
        "current_session_id": None,
        "logged_in_at": None,
        "email_access_validated_at": str(datetime.now(timezone.utc)),
        "can_use_webauthn": False,
    }
    user_data.update(overrides)
    return user_data


def create_reply_to_email_address(
    id_="1234", service_id="abcd", email_address="test@example.com", is_default=True, created_at=None, updated_at=None
):
    return {
        "id": id_,
        "service_id": service_id,
        "email_address": email_address,
        "is_default": is_default,
        "created_at": created_at,
        "updated_at": updated_at,
    }


def create_multiple_email_reply_to_addresses(service_id="abcd"):
    return [
        {
            "id": "1234",
            "service_id": service_id,
            "email_address": "test@example.com",
            "is_default": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
        },
        {
            "id": "5678",
            "service_id": service_id,
            "email_address": "test2@example.com",
            "is_default": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
        },
        {
            "id": "9457",
            "service_id": service_id,
            "email_address": "test3@example.com",
            "is_default": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
        },
    ]


def create_sms_sender(
    id_="1234",
    service_id="abcd",
    sms_sender="GOVUK",
    is_default=True,
    created_at=None,
    updated_at=None,
):
    return {
        "id": id_,
        "service_id": service_id,
        "sms_sender": sms_sender,
        "is_default": is_default,
        "created_at": created_at,
        "updated_at": updated_at,
    }


def create_multiple_sms_senders(service_id="abcd"):
    return [
        {
            "id": "1234",
            "service_id": service_id,
            "sms_sender": "Example",
            "is_default": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
        },
        {
            "id": "5678",
            "service_id": service_id,
            "sms_sender": "Example 2",
            "is_default": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
        },
        {
            "id": "9457",
            "service_id": service_id,
            "sms_sender": "Example 3",
            "is_default": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
        },
    ]


def create_letter_contact_block(
    id_="1234",
    service_id="abcd",
    contact_block="1 Example Street",
    is_default=True,
    created_at=None,
    updated_at=None,
):
    return {
        "id": id_,
        "service_id": service_id,
        "contact_block": contact_block,
        "is_default": is_default,
        "created_at": created_at,
        "updated_at": updated_at,
    }


def create_multiple_letter_contact_blocks(service_id="abcd"):
    return [
        {
            "id": "1234",
            "service_id": service_id,
            "contact_block": "1 Example Street",
            "is_default": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
        },
        {
            "id": "5678",
            "service_id": service_id,
            "contact_block": "2 Example Street",
            "is_default": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
        },
        {
            "id": "9457",
            "service_id": service_id,
            "contact_block": "foo\n\n<bar>\n\nbaz",
            "is_default": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
        },
    ]


def create_folder(id):
    return {"id": id, "parent_id": None, "name": "My folder"}


def create_template(
    service_id=SERVICE_ONE_ID,
    template_id=None,
    template_type="broadcast",
    name="sample template",
    content="Template content",
    folder=None,
):
    return template_json(
        service_id=service_id,
        id_=template_id or str(generate_uuid()),
        name=name,
        type_=template_type,
        content=content,
        folder=folder,
    )


@pytest.fixture(scope="function")
def mock_create_broadcast_message(
    mocker,
    fake_uuid,
):
    def _create(
        *,
        service_id,
        template_id,
        content,
        reference,
    ):
        return {
            "id": fake_uuid,
        }

    return mocker.patch(
        "app.broadcast_message_api_client.create_broadcast_message",
        side_effect=_create,
    )


@pytest.fixture(scope="function")
def mock_get_draft_broadcast_message(
    mocker,
    fake_uuid,
):
    def _get(*, service_id, broadcast_message_id):
        return broadcast_message_json(
            id_=broadcast_message_id,
            service_id=service_id,
            template_id=fake_uuid,
            status="draft",
            created_by_id=fake_uuid,
            created_at=datetime.now(),
        )

    return mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        side_effect=_get,
    )


@pytest.fixture(scope="function")
def mock_get_live_broadcast_message(
    mocker,
    fake_uuid,
):
    def _get(*, service_id, broadcast_message_id):
        return broadcast_message_json(
            id_=broadcast_message_id,
            service_id=service_id,
            template_id=fake_uuid,
            status="broadcasting",
            created_by_id=fake_uuid,
            starts_at=datetime.now().isoformat(),
            finishes_at=(datetime.now() + timedelta(hours=24)).isoformat(),
            created_at=datetime.now().isoformat(),
            approved_at=datetime.now().isoformat(),
        )

    return mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        side_effect=_get,
    )


@pytest.fixture(scope="function")
def mock_get_no_broadcast_messages(
    mocker,
    fake_uuid,
):
    return mocker.patch(
        "app.models.broadcast_message.BroadcastMessages.client_method",
        return_value=[
            broadcast_message_json(
                id_=fake_uuid,
                service_id=SERVICE_ONE_ID,
                template_id=fake_uuid,
                status="rejected",  # rejected broadcasts aren’t shown on the dashboard
                created_by_id=fake_uuid,
            ),
        ],
    )


@pytest.fixture(scope="function")
def mock_get_broadcast_messages(
    mocker,
    fake_uuid,
):
    def _get(service_id):
        partial_json = partial(
            broadcast_message_json,
            service_id=service_id,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
        )
        return [
            partial_json(
                id_=uuid4(),
                status="draft",
                updated_at=(datetime.now(timezone.utc) - timedelta(hours=1, minutes=30)).isoformat(),
            ),
            partial_json(
                id_=uuid4(),
                status="pending-approval",
                updated_at=(datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat(),
                template_name="Half an hour ago",
                finishes_at=None,
            ),
            partial_json(
                id_=uuid4(),
                status="pending-approval",
                updated_at=(datetime.now(timezone.utc) - timedelta(hours=1, minutes=30)).isoformat(),
                template_name="Hour and a half ago",
                finishes_at=None,
            ),
            partial_json(
                id_=uuid4(),
                status="broadcasting",
                updated_at=(datetime.now(timezone.utc)).isoformat(),
                starts_at=(datetime.now(timezone.utc)).isoformat(),
                finishes_at=(datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
            ),
            partial_json(
                id_=uuid4(),
                status="broadcasting",
                updated_at=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
                starts_at=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
                finishes_at=(datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
            ),
            partial_json(
                id_=uuid4(),
                status="completed",
                starts_at=(datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(),
                finishes_at=(datetime.now(timezone.utc) - timedelta(hours=6)).isoformat(),
            ),
            partial_json(
                id_=uuid4(),
                status="cancelled",
                starts_at=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                finishes_at=(datetime.now(timezone.utc) - timedelta(days=100)).isoformat(),
                cancelled_at=(datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
            ),
            partial_json(
                id_=uuid4(),
                status="rejected",
                updated_at=(datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            ),
        ]

    return mocker.patch(
        "app.models.broadcast_message.BroadcastMessages.client_method",
        side_effect=_get,
    )


@pytest.fixture(scope="function")
def mock_get_broadcast_message_versions(mocker):
    partial_json = partial(
        broadcast_message_version_json,
        service_id=SERVICE_ONE_ID,
        id_=fake_uuid,
        created_by_id=fake_uuid,
        reference="Test version broadcast",
    )
    return mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message_versions",
        return_value=[
            partial_json(
                version=1,
            ),
            partial_json(version=2),
        ],
    )


@pytest.fixture(scope="function")
def mock_get_broadcast_returned_for_edit_reasons(mocker):
    broadcast_message_edit_reason_partial = partial(
        broadcast_message_edit_reason_json,
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        id=fake_uuid,
        created_by_id=fake_uuid,
        created_by="Test User",
        submitted_by="Test User 2",
        submitted_by_id=fake_uuid,
        submitted_at="2020-02-20T20:20:20.000000",
    )
    return mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_returned_for_edit_reasons",
        return_value=[
            broadcast_message_edit_reason_partial(edit_reason="Hello", created_at="2020-02-20T20:25:20.000000"),
        ],
    )


@pytest.fixture(scope="function")
def mock_get_latest_edit_reason(mocker):
    broadcast_message_edit_reason_partial = partial(
        broadcast_message_edit_reason_json,
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        id=fake_uuid,
        created_by_id=fake_uuid,
        created_by="Test User",
        submitted_by="Test User 2",
        submitted_by_id=fake_uuid,
        submitted_at="2020-02-20T20:20:20.000000",
    )
    return mocker.patch(
        "app.broadcast_message_api_client.get_latest_returned_for_edit_reason",
        return_value=broadcast_message_edit_reason_partial(
            edit_reason="TESTING", created_at="2020-02-20T20:20:20.000000"
        ),
    )


@pytest.fixture(scope="function")
def mock_update_broadcast_message(
    mocker,
    fake_uuid,
):
    def _update(*, service_id, broadcast_message_id, data):
        pass

    return mocker.patch(
        "app.broadcast_message_api_client.update_broadcast_message",
        side_effect=_update,
    )


@pytest.fixture(scope="function")
def mock_return_broadcast_message_for_edit_with_reason(
    mocker,
    fake_uuid,
):
    def _update(*, service_id, broadcast_message_id, edit_reason):
        pass

    return mocker.patch(
        "app.broadcast_message_api_client.return_broadcast_message_for_edit_with_reason",
        side_effect=_update,
    )


@pytest.fixture(scope="function")
def mock_check_can_update_status(mocker):
    return mocker.patch("app.broadcast_message_api_client.check_broadcast_status_transition_allowed")


@pytest.fixture(scope="function")
def mock_check_can_update_status_returns_http_error(mocker):
    """
    This fixture is different to actual client method in that the status passed in is the new status
    and the error message here is dependent on new status only.
    For the actual method, the message is dependent on the existing status of the broadcast message
    i.e. the error message for when 'pending-approval' is passed in is reflective of whether or not
    the current broadcast message can transition to 'pending-approval'.
    For example, if the current broadcast message status is 'rejected' and the method is called to
    update the status to 'pending-approval' the message returned will be "his alert has been rejected,
    it cannot be edited or resubmitted for approval.".
    In the interests of mocking the method and the resulting error handling, the below messages are returned
    for each new_status, passed in by function called, irresepctive of existing status.
    """

    def _get(status, broadcast_message_id, service_id):
        if status == "pending-approval":
            message = "This alert is pending approval, it cannot be edited or submitted again."
        elif status == "rejected":
            message = "This alert has been rejected, it cannot be edited or resubmitted for approval."
        elif status == "broadcasting":
            message = "This alert is live, it cannot be edited or submitted again."
        elif status == "cancelled":
            message = "This alert has already been broadcast, it cannot be edited or resubmitted for approval."
        raise HTTPError(
            Response(status=400),
            message,
        )

    return mocker.patch("app.broadcast_message_api_client.check_broadcast_status_transition_allowed", side_effect=_get)


@pytest.fixture(scope="function")
def mock_update_broadcast_message_status(
    mocker,
    fake_uuid,
):
    def _update(status, *, service_id, broadcast_message_id):
        pass

    return mocker.patch(
        "app.broadcast_message_api_client.update_broadcast_message_status",
        side_effect=_update,
    )


@pytest.fixture(scope="function")
def mock_update_broadcast_message_status_with_reason(
    mocker,
    fake_uuid,
):
    def _update(status, *, service_id, broadcast_message_id, rejection_reason):
        pass

    return mocker.patch(
        "app.broadcast_message_api_client.update_broadcast_message_status_with_reason",
        side_effect=_update,
    )


@pytest.fixture
def mock_get_invited_user_by_id(mocker, sample_invite):
    def _get(invited_user_id):
        return sample_invite

    return mocker.patch(
        "app.invite_api_client.get_invited_user",
        side_effect=_get,
    )


@pytest.fixture
def mock_get_invited_org_user_by_id(mocker, sample_org_invite):
    def _get(invited_org_user_id):
        return sample_org_invite

    return mocker.patch(
        "app.org_invite_api_client.get_invited_user",
        side_effect=_get,
    )


@pytest.fixture
def mock_get_pending_admin_actions(mocker):
    return mocker.patch(
        "app.admin_actions_api_client.get_pending_admin_actions",
        return_value={"pending": [], "services": {}, "users": {}},
    )


@pytest.fixture
def webauthn_credential():
    return {
        "id": str(uuid4()),
        "name": "Test credential",
        "credential_data": "WJ8AAAAAAAAAAAAAAAAAAAAAAECKU1ppjl9gmhHWyDkgHsUvZmhr6oF3/lD3llzLE2SaOSgOGIsIuAQqgp8JQSUu3r/oOaP8RS44dlQjrH+ALfYtpQECAyYgASFYIDGeoB8RJc5iMpRzZYAK5dndyHQkfFXRUWutPKPKMgdcIlggWfHwfzsvhsClHgz6E9xX58d6EQ55b4oLJ3Qf5YZjyzo=",  # noqa
        "registration_response": "anything",
        "created_at": "2017-10-18T16:57:14.154185Z",
        "logged_in_at": "2017-10-19T00:00:00.000000Z",
    }


@pytest.fixture
def webauthn_credential_2():
    return {
        "id": str(uuid4()),
        "name": "Another test credential",
        "credential_data": "WJ0AAAAAAAAAAAAAAAAAAAAAAECKU1jppl9mhgHWyDkgHsUvZmhr6oF3/lD3llzLE2SaOSgOGIsIuAQqgp8JQSUu3r/oOaP8RS44dlQjrH+ALfYtpAECAyYhWCAxnqAfESXOYjKUc2WACuXZ3ch0JHxV0VFrrTyjyjIHXCJYIFnx8L4H87bApR4M+hPcV+fHehEOeW+KCyd0H+WGY8s6",  # noqa
        "registration_response": "stuff",
        "created_at": "2021-05-14T16:57:14.154185Z",
        "logged_in_at": None,
    }


@pytest.fixture
def mock_admin_action_notification(mocker):
    return mocker.patch("app.utils.admin_action.send_notifications", return_value=None)
