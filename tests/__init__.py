import uuid
from datetime import datetime, timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import freezegun
import pytest
from bs4 import BeautifulSoup
from flask import session as flask_session
from flask import url_for
from flask.testing import FlaskClient
from flask_login import login_user

from app.models.user import User

# Add itsdangerous to the libraries which freezegun ignores to avoid errors.
# In tests where we freeze time, the code in the test function will get the frozen time but the
# fixtures will be using the current time. This causes itsdangerous to raise an exception - when
# the session is decoded it appears to be created in the future.
freezegun.configure(extend_ignore_list=["itsdangerous"])


class TestClient(FlaskClient):
    def login(self, user, mocker=None, service=None):
        # Skipping authentication here and just log them in
        model_user = User(user)
        with self.session_transaction() as session:
            session["current_session_id"] = model_user.current_session_id
            session["user_id"] = model_user.id
        if mocker:
            mocker.patch("app.feature_toggle_api_client.get_feature_toggle", return_value={})
            mocker.patch("app.user_api_client.get_user", return_value=user)
        if mocker and service:
            with self.session_transaction() as session:
                session["service_id"] = service["id"]
            mocker.patch("app.service_api_client.get_service", return_value={"data": service})

        with patch("app.events_api_client.create_event"):
            login_user(model_user)
        with self.session_transaction() as test_session:
            for key, value in flask_session.items():
                test_session[key] = value

    def logout(self, user):
        self.get(url_for("main.sign_out"))


class NotifyBeautifulSoup(BeautifulSoup):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.override_method("find", "select_one")
        self.override_method("find_all", "select")

    def override_method(self, method_name, preferred_method_name):
        def overridden_method(*args, **kwargs):
            raise AttributeError(
                f"Don’t use BeautifulSoup.{method_name} – try BeautifulSoup.{preferred_method_name} instead"
            )

        setattr(self, method_name, overridden_method)


def sample_uuid():
    return "6ce466d0-fd6a-11e5-82f5-e0accb9d11a6"


def generate_uuid():
    return uuid.uuid4()


def created_by_json(id_, name="", email_address=""):
    return {"id": id_, "name": name, "email_address": email_address}


def user_json(
    id_="1234",
    name="Test User",
    email_address="test@gov.uk",
    mobile_number="+447700900986",
    password_changed_at=None,
    permissions=None,
    auth_type="sms_auth",
    failed_login_count=0,
    logged_in_at=None,
    state="active",
    platform_admin=False,
    current_session_id="1234",
    organisations=None,
    services=None,
):
    if permissions is None:
        permissions = {
            str(generate_uuid()): [
                "view_activity",
                "send_texts",
                "send_emails",
                "send_letters",
                "manage_users",
                "manage_templates",
                "manage_settings",
                "manage_api_keys",
            ]
        }

    if services is None:
        services = [str(service_id) for service_id in permissions.keys()]

    return {
        "id": id_,
        "name": name,
        "email_address": email_address,
        "mobile_number": mobile_number,
        "password_changed_at": password_changed_at,
        "permissions": permissions,
        "auth_type": auth_type,
        "failed_login_count": failed_login_count,
        "logged_in_at": logged_in_at or datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f"),
        "state": state,
        "platform_admin": platform_admin,
        "current_session_id": current_session_id,
        "organisations": organisations or [],
        "services": services,
    }


def invited_user(
    _id="1234",
    service=None,
    from_user="1234",
    email_address="testinviteduser@gov.uk",
    permissions=None,
    status="pending",
    created_at=None,
    auth_type="sms_auth",
    organisation=None,
):
    data = {
        "id": _id,
        "from_user": from_user,
        "email_address": email_address,
        "status": status,
        "created_at": created_at or datetime.utcnow(),
        "auth_type": auth_type,
    }
    if service:
        data["service"] = service
    if permissions:
        data["permissions"] = permissions
    if organisation:
        data["organisation"] = organisation

    return data


def service_json(
    id_="1234",
    name="Test Service",
    users=None,
    message_limit=1000,
    active=True,
    restricted=True,
    email_from=None,
    reply_to_email_address=None,
    sms_sender="GOVUK",
    research_mode=False,
    branding="govuk",
    created_at=None,
    letter_contact_block=None,
    inbound_api=None,
    service_callback_api=None,
    permissions=None,
    organisation_type="central",
    prefix_sms=True,
    contact_link=None,
    organisation_id=None,
    rate_limit=3000,
    notes=None,
    billing_contact_email_addresses=None,
    billing_contact_names=None,
    billing_reference=None,
    purchase_order_number=None,
    broadcast_channel=None,
    allowed_broadcast_provider=None,
):
    if users is None:
        users = []
    if permissions is None:
        permissions = ["email", "sms", "broadcast"]
    if service_callback_api is None:
        service_callback_api = []
    if inbound_api is None:
        inbound_api = []
    return {
        "id": id_,
        "name": name,
        "users": users,
        "message_limit": message_limit,
        "rate_limit": rate_limit,
        "active": active,
        "restricted": restricted,
        "email_from": email_from,
        "reply_to_email_address": reply_to_email_address,
        "sms_sender": sms_sender,
        "research_mode": research_mode,
        "organisation_type": organisation_type,
        "branding": branding,
        "created_at": created_at or str(datetime.utcnow()),
        "letter_contact_block": letter_contact_block,
        "permissions": permissions,
        "inbound_api": inbound_api,
        "service_callback_api": service_callback_api,
        "prefix_sms": prefix_sms,
        "contact_link": contact_link,
        "volume_email": 111111,
        "volume_sms": 222222,
        "volume_letter": 333333,
        "consent_to_research": True,
        "count_as_live": True,
        "organisation": organisation_id,
        "notes": notes,
        "billing_contact_email_addresses": billing_contact_email_addresses,
        "billing_contact_names": billing_contact_names,
        "billing_reference": billing_reference,
        "purchase_order_number": purchase_order_number,
        "broadcast_channel": broadcast_channel,
        "allowed_broadcast_provider": allowed_broadcast_provider,
    }


def organisation_json(
    id_="1234",
    name=False,
    users=None,
    active=True,
    created_at=None,
    services=None,
    domains=None,
    crown=True,
    agreement_signed=False,
    agreement_signed_version=None,
    agreement_signed_by_id=None,
    agreement_signed_on_behalf_of_name=None,
    agreement_signed_on_behalf_of_email_address=None,
    organisation_type="central",
    request_to_go_live_notes=None,
    notes=None,
    billing_contact_email_addresses=None,
    billing_contact_names=None,
    billing_reference=None,
    purchase_order_number=None,
):
    if users is None:
        users = []
    if services is None:
        services = []
    return {
        "id": id_,
        "name": "Test Organisation" if name is False else name,
        "active": active,
        "users": users,
        "created_at": created_at or str(datetime.utcnow()),
        "organisation_type": organisation_type,
        "crown": crown,
        "agreement_signed": agreement_signed,
        "agreement_signed_at": None,
        "agreement_signed_by_id": agreement_signed_by_id,
        "agreement_signed_version": agreement_signed_version,
        "agreement_signed_on_behalf_of_name": agreement_signed_on_behalf_of_name,
        "agreement_signed_on_behalf_of_email_address": agreement_signed_on_behalf_of_email_address,
        "domains": domains or [],
        "request_to_go_live_notes": request_to_go_live_notes,
        "count_of_live_services": len(services),
        "notes": notes,
        "billing_contact_email_addresses": billing_contact_email_addresses,
        "billing_contact_names": billing_contact_names,
        "billing_reference": billing_reference,
        "purchase_order_number": purchase_order_number,
    }


def template_json(
    service_id,
    id_,
    name="sample template",
    type_=None,
    content=None,
    subject=None,
    version=1,
    archived=False,
    process_type="normal",
    redact_personalisation=None,
    service_letter_contact=None,
    reply_to=None,
    reply_to_text=None,
    is_precompiled_letter=False,
    postage=None,
    folder=None,
):
    template = {
        "id": id_,
        "name": name,
        "template_type": type_ or "sms",
        "content": content,
        "service": service_id,
        "version": version,
        "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f"),
        "archived": archived,
        "process_type": process_type,
        "service_letter_contact": service_letter_contact,
        "reply_to": reply_to,
        "reply_to_text": reply_to_text,
        "is_precompiled_letter": is_precompiled_letter,
        "folder": folder,
        "postage": postage,
    }
    if content is None:
        template["content"] = "template content"
    if subject is None and type_ != "sms":
        template["subject"] = "template subject"
    if subject is not None:
        template["subject"] = subject
    if redact_personalisation is not None:
        template["redact_personalisation"] = redact_personalisation
    return template


def template_version_json(service_id, id_, created_by, version=1, created_at=None, **kwargs):
    template = template_json(service_id, id_, **kwargs)
    template["created_by"] = created_by_json(
        created_by["id"],
        created_by["name"],
        created_by["email_address"],
    )
    if created_at is None:
        created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")
    template["created_at"] = created_at
    template["version"] = version
    return template


def api_key_json(id_, name, expiry_date=None):
    return {"id": id_, "name": name, "expiry_date": expiry_date}


def invite_json(
    id_, from_user, service_id, email_address, permissions, created_at, status, auth_type, folder_permissions
):
    return {
        "id": id_,
        "from_user": from_user,
        "service": service_id,
        "email_address": email_address,
        "status": status,
        "permissions": permissions,
        "created_at": created_at,
        "auth_type": auth_type,
        "folder_permissions": folder_permissions,
    }


def org_invite_json(id_, invited_by, org_id, email_address, created_at, status):
    return {
        "id": id_,
        "invited_by": invited_by,
        "organisation": org_id,
        "email_address": email_address,
        "status": status,
        "created_at": created_at,
    }


def inbound_sms_json():
    return {
        "has_next": True,
        "data": [
            {
                "user_number": phone_number,
                "notify_number": "07900000002",
                "content": f"message-{index + 1}",
                "created_at": (datetime.utcnow() - timedelta(minutes=60 * hours_ago, seconds=index)).isoformat(),
                "id": sample_uuid(),
            }
            for index, hours_ago, phone_number in (
                (0, 1, "447900900000"),
                (1, 1, "07900900000"),
                (2, 1, "07900900000"),
                (3, 3, "07900900002"),
                (4, 5, "33(0)1 12345678"),  # France
                (5, 7, "1-202-555-0104"),  # USA in one format
                (6, 9, "+12025550104"),  # USA in another format
                (7, 9, "+68212345"),  # Cook Islands
            )
        ],
    }


TEST_USER_EMAIL = "test@user.gov.uk"


def create_test_api_user(state, permissions=None):
    user_data = {
        "id": 1,
        "name": "Test User",
        "password": "somepassword",
        "email_address": TEST_USER_EMAIL,
        "mobile_number": "+441234123412",
        "state": state,
        "permissions": permissions or {},
    }
    return user_data


def validate_route_permission(
    mocker, notify_admin, method, response_code, route, permissions, usr, service, session=None
):
    usr["permissions"][str(service["id"])] = permissions
    usr["services"] = [service["id"]]
    mocker.patch("app.feature_toggle_api_client.get_feature_toggle", return_value={})
    mocker.patch("app.user_api_client.check_verify_code", return_value=(True, ""))
    mocker.patch("app.service_api_client.get_services", return_value={"data": []})
    mocker.patch("app.service_api_client.update_service", return_value=service)
    mocker.patch("app.service_api_client.update_service_with_properties", return_value=service)
    mocker.patch("app.user_api_client.get_user", return_value=usr)
    mocker.patch("app.user_api_client.get_user_by_email", return_value=usr)
    mocker.patch("app.service_api_client.get_service", return_value={"data": service})
    mocker.patch("app.models.user.Users.client_method", return_value=[usr])
    with notify_admin.test_request_context():
        with notify_admin.test_client() as client:
            client.login(usr)
            if session:
                with client.session_transaction() as session_:
                    for k, v in session.items():
                        session_[k] = v
            resp = None
            if method == "GET":
                resp = client.get(route)
            elif method == "POST":
                resp = client.post(route)
            else:
                pytest.fail("Invalid method call {}".format(method))
            if resp.status_code != response_code:
                pytest.fail("Invalid permissions set for endpoint {}".format(route))
    return resp


def validate_route_permission_with_client(mocker, client, method, response_code, route, permissions, usr, service):
    usr["permissions"][str(service["id"])] = permissions
    mocker.patch("app.feature_toggle_api_client.get_feature_toggle", return_value={})
    mocker.patch("app.user_api_client.check_verify_code", return_value=(True, ""))
    mocker.patch("app.service_api_client.get_services", return_value={"data": []})
    mocker.patch("app.service_api_client.update_service", return_value=service)
    mocker.patch("app.service_api_client.update_service_with_properties", return_value=service)
    mocker.patch("app.user_api_client.get_user", return_value=usr)
    mocker.patch("app.user_api_client.get_user_by_email", return_value=usr)
    mocker.patch("app.service_api_client.get_service", return_value={"data": service})
    mocker.patch("app.user_api_client.get_users_for_service", return_value=[usr])
    client.login(usr)
    resp = None
    if method == "GET":
        resp = client.get_response_from_url(route, _expected_status=response_code)
    elif method == "POST":
        resp = client.post_response_from_url(route, _expected_status=response_code)
    else:
        pytest.fail("Invalid method call {}".format(method))
    if resp.status_code != response_code:
        pytest.fail("Invalid permissions set for endpoint {}".format(route))
    return resp


def assert_url_expected(actual, expected):
    actual_parts = urlparse(actual)
    expected_parts = urlparse(expected)
    for attribute in actual_parts._fields:
        if attribute == "query":
            # query string ordering can be non-deterministic
            # so we need to parse it first, which gives us a
            # dictionary of keys and values, not a
            # serialized string
            assert parse_qs(expected_parts.query) == parse_qs(actual_parts.query)
        else:
            assert getattr(actual_parts, attribute) == getattr(expected_parts, attribute), (
                "Expected redirect: {}\nActual redirect: {}"
            ).format(expected, actual)


def find_element_by_tag_and_partial_text(page, tag, string):
    return [e for e in page.select(tag) if string in e.text][0]


def broadcast_message_json(
    *,
    id_=None,
    service_id=None,
    template_id=None,
    status="draft",
    created_by_id=None,
    duration=0,
    starts_at=None,
    finishes_at=None,
    cancelled_at=None,
    updated_at=None,
    approved_by_id=None,
    cancelled_by_id=None,
    areas=None,
    area_ids=None,
    simple_polygons=None,
    content=None,
    reference=None,
    cap_event=None,
    template_name="Example template",
    created_by=None,
    approved_by=None,
    rejected_by=None,
    cancelled_by=None,
):
    return {
        "id": id_,
        "service_id": service_id,
        "template_id": template_id,
        "template_version": 123,
        "template_name": template_name,
        "content": content or "This is a test",
        "reference": reference,
        "cap_event": cap_event,
        "personalisation": {},
        "areas": areas
        or {
            "ids": area_ids or ["ctry19-E92000001", "ctry19-S92000003"],
            "simple_polygons": simple_polygons or [],
        },
        "status": status,
        "duration": duration,
        "starts_at": starts_at,
        "finishes_at": finishes_at,
        "created_at": None,
        "approved_at": None,
        "cancelled_at": cancelled_at,
        "updated_at": updated_at,
        "created_by_id": created_by_id,
        "approved_by_id": approved_by_id,
        "cancelled_by_id": cancelled_by_id,
        "created_by": created_by,
        "approved_by": approved_by,
        "rejected_by": rejected_by,
        "cancelled_by": cancelled_by,
    }
