import uuid
from unittest.mock import ANY

import pytest
from flask import g, session, url_for

from app.event_handlers import (
    create_add_user_to_service_event,
    create_archive_service_event,
    create_archive_user_event,
    create_broadcast_account_type_change_event,
    create_email_change_event,
    create_mobile_number_change_event,
    create_remove_user_from_service_event,
    create_set_user_permissions_event,
    on_session_protected,
    on_user_logged_in,
)
from app.models.user import User
from tests.conftest import SERVICE_ONE_ID, set_config


def event_dict(**extra):
    return {
        "browser_fingerprint": {"browser": ANY, "version": ANY, "platform": ANY, "user_agent_string": ""},
        "ip_address": ANY,
        **extra,
    }


def test_on_user_logged_in_calls_events_api(client_request, api_user_active, mock_events):
    on_user_logged_in("_notify_admin", User(api_user_active))

    mock_events.assert_called_with("sucessful_login", event_dict(user_id=str(api_user_active["id"])))


def test_create_email_change_event_calls_events_api(client_request, mock_events):
    kwargs = {
        "user_id": str(uuid.uuid4()),
        "updated_by_id": str(uuid.uuid4()),
        "original_email_address": "original@example.com",
        "new_email_address": "new@example.com",
    }

    create_email_change_event(**kwargs)
    mock_events.assert_called_with("update_user_email", event_dict(**kwargs))


def test_create_add_user_to_service_event_calls_events_api(client_request, mock_events):
    kwargs = {
        "user_id": str(uuid.uuid4()),
        "invited_by_id": str(uuid.uuid4()),
        "service_id": str(uuid.uuid4()),
        "ui_permissions": {"manage_templates"},
    }

    create_add_user_to_service_event(**kwargs)
    mock_events.assert_called_with("add_user_to_service", event_dict(**kwargs))


def test_create_remove_user_from_service_event_calls_events_api(client_request, mock_events):
    kwargs = {"user_id": str(uuid.uuid4()), "removed_by_id": str(uuid.uuid4()), "service_id": str(uuid.uuid4())}

    create_remove_user_from_service_event(**kwargs)
    mock_events.assert_called_with("remove_user_from_service", event_dict(**kwargs))


def test_create_mobile_number_change_event_calls_events_api(client_request, mock_events):
    kwargs = {
        "user_id": str(uuid.uuid4()),
        "updated_by_id": str(uuid.uuid4()),
        "original_mobile_number": "07700900000",
        "new_mobile_number": "07700900999",
    }

    create_mobile_number_change_event(**kwargs)
    mock_events.assert_called_with("update_user_mobile_number", event_dict(**kwargs))


def test_create_archive_user_event_calls_events_api(client_request, mock_events):
    kwargs = {"user_id": str(uuid.uuid4()), "user_email_address": "user@gov.uk", "archived_by_id": str(uuid.uuid4())}

    create_archive_user_event(**kwargs)
    mock_events.assert_called_with("archive_user", event_dict(**kwargs))


def test_create_broadcast_account_type_change_event(client_request, mock_events):
    kwargs = {
        "service_id": str(uuid.uuid4()),
        "changed_by_id": str(uuid.uuid4()),
        "service_mode": "training",
        "broadcast_channel": "severe",
        "provider_restriction": None,
    }

    create_broadcast_account_type_change_event(**kwargs)
    mock_events.assert_called_with("change_broadcast_account_type", event_dict(**kwargs))


def test_archive_service(client_request, mock_events):
    kwargs = {"service_id": str(uuid.uuid4()), "archived_by_id": str(uuid.uuid4())}

    create_archive_service_event(**kwargs)
    mock_events.assert_called_with("archive_service", event_dict(**kwargs))


def test_set_user_permissions(client_request, mock_events):
    kwargs = {
        "user_id": str(uuid.uuid4()),
        "service_id": str(uuid.uuid4()),
        "original_ui_permissions": set("manage_templates"),
        "new_ui_permissions": set("view_activity"),
        "set_by_id": str(uuid.uuid4()),
    }

    create_set_user_permissions_event(**kwargs)
    mock_events.assert_called_with("set_user_permissions", event_dict(**kwargs))


@pytest.mark.parametrize(
    "session_protection, request_identifier, expected_signed_out",
    (
        ("strong", "identifier-at-sign-in", False),
        ("strong", "identifier-from-a-different-ip-address-or-browser", True),
        ("basic", "identifier-from-a-different-ip-address-or-browser", False),
        (None, "identifier-from-a-different-ip-address-or-browser", False),
    ),
)
def test_session_protection(
    notify_admin,
    client_request,
    mock_get_service,
    mocker,
    session_protection,
    request_identifier,
    expected_signed_out,
):
    with client_request.session_transaction() as session:
        session["_id"] = "identifier-at-sign-in"
    mocker.patch.object(notify_admin.login_manager, "_session_identifier_generator", return_value=request_identifier)
    # Test client requests share the test's app context, so would otherwise reuse the user logged in by the
    # client_request fixture rather than loading (and checking) them from the session like a real request would
    g.pop("_login_user", None)

    with set_config(notify_admin, "SESSION_PROTECTION", session_protection):
        client_request.get(
            "main.service_dashboard",
            service_id=SERVICE_ONE_ID,
            _expected_redirect=(
                url_for("main.sign_in", next=f"/services/{SERVICE_ONE_ID}")
                if expected_signed_out
                else url_for("main.broadcast_dashboard", service_id=SERVICE_ONE_ID)
            ),
        )

    with client_request.session_transaction() as session:
        if expected_signed_out:
            assert not session
        else:
            assert session["_user_id"]


def test_on_session_protected_does_not_clear_session_without_logged_in_user(notify_admin):
    with set_config(notify_admin, "SESSION_PROTECTION", "strong"), notify_admin.test_request_context():
        session["user_details"] = {"email": "test@example.com"}

        on_session_protected(notify_admin)

        assert session == {"user_details": {"email": "test@example.com"}}
