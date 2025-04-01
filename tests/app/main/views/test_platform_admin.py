import datetime
import uuid
from functools import partial
from unittest.mock import ANY

import pytest
from flask import session, url_for
from flask_login import current_user
from freezegun import freeze_time

from tests import service_json
from tests.conftest import SERVICE_ONE_ID, SERVICE_TWO_ID, normalize_spaces


@pytest.mark.parametrize(
    "endpoint",
    [
        "main.platform_admin",
        "main.live_services",
        "main.trial_services",
    ],
)
def test_should_redirect_if_not_logged_in(client_request, endpoint):
    client_request.logout()
    client_request.get(
        endpoint,
        _expected_redirect=url_for("main.sign_in", next=url_for(endpoint)),
    )


@pytest.mark.parametrize(
    "endpoint",
    [
        "main.platform_admin",
        "main.platform_admin_search",
        "main.live_services",
        "main.trial_services",
    ],
)
def test_should_403_if_not_platform_admin(
    client_request,
    endpoint,
):
    client_request.get(endpoint, _expected_status=403)


@pytest.mark.parametrize(
    "endpoint, expected_h1, expected_services_shown",
    [
        ("main.live_services", "Live services", 1),
        ("main.trial_services", "Trial mode services", 1),
    ],
)
def test_should_render_platform_admin_page(
    client_request, platform_admin_user, mock_get_detailed_services, endpoint, expected_h1, expected_services_shown
):
    client_request.login(platform_admin_user)
    page = client_request.get(endpoint)
    assert normalize_spaces(page.select("h1")) == expected_h1
    mock_get_detailed_services.assert_called_once_with({"include_from_test_key": True, "only_active": False})


@pytest.mark.parametrize(
    "endpoint",
    [
        "main.live_services",
        "main.trial_services",
    ],
)
@pytest.mark.parametrize(
    "partial_url_for, inc",
    [
        (partial(url_for), True),
        (partial(url_for, include_from_test_key="y", start_date="", end_date=""), True),
        (partial(url_for, start_date="", end_date=""), False),
    ],
)
def test_live_trial_services_toggle_including_from_test_key(
    partial_url_for, client_request, platform_admin_user, mock_get_detailed_services, endpoint, inc
):
    client_request.login(platform_admin_user)
    client_request.get_url(partial_url_for(endpoint))
    mock_get_detailed_services.assert_called_once_with(
        {
            "only_active": False,
            "include_from_test_key": inc,
        }
    )


@pytest.mark.parametrize("endpoint", ["main.live_services", "main.trial_services"])
def test_live_trial_services_with_date_filter(
    client_request, platform_admin_user, mock_get_detailed_services, endpoint
):
    client_request.login(platform_admin_user)
    page = client_request.get(
        endpoint,
        start_date="2016-12-20",
        end_date="2016-12-28",
    )

    assert "Platform admin" in page.text
    mock_get_detailed_services.assert_called_once_with(
        {
            "include_from_test_key": False,
            "end_date": datetime.date(2016, 12, 28),
            "start_date": datetime.date(2016, 12, 20),
            "only_active": False,
        }
    )


@pytest.mark.parametrize(
    "endpoint, restricted", [("main.live_services", False), ("main.trial_services", True)], ids=["live", "trial"]
)
def test_should_show_archived_services_last(
    endpoint,
    client_request,
    platform_admin_user,
    mock_get_detailed_services,
    restricted,
):
    services = [
        service_json(name="C", restricted=restricted, active=False, created_at="2002-02-02 12:00:00"),
        service_json(name="B", restricted=restricted, active=True, created_at="2001-01-01 12:00:00"),
        service_json(name="A", restricted=restricted, active=True, created_at="2003-03-03 12:00:00"),
    ]

    mock_get_detailed_services.return_value = {"data": services}
    client_request.login(platform_admin_user)
    page = client_request.get(endpoint)

    mock_get_detailed_services.assert_called_once_with({"include_from_test_key": True, "only_active": ANY})

    list_body = page.select_one("nav.browse-list")
    services = list(list_body.select("li.browse-list-item"))
    assert len(services) == 3
    assert normalize_spaces(services[0].text) == "A"
    assert normalize_spaces(services[1].text) == "B"
    assert normalize_spaces(services[2].text) == "C Archived"


@pytest.mark.parametrize("endpoint, restricted", [("main.trial_services", True), ("main.live_services", False)])
def test_should_order_services_by_usage_with_inactive_last(
    endpoint,
    restricted,
    client_request,
    platform_admin_user,
    mock_get_detailed_services,
    fake_uuid,
):
    services = [
        service_json(fake_uuid, "My Service 1", [], restricted=restricted),
        service_json(fake_uuid, "My Service 2", [], restricted=restricted),
        service_json(fake_uuid, "My Service 3", [], restricted=restricted, active=False),
    ]

    mock_get_detailed_services.return_value = {"data": services}
    client_request.login(platform_admin_user)
    page = client_request.get(endpoint)

    mock_get_detailed_services.assert_called_once_with({"include_from_test_key": True, "only_active": ANY})

    list_body = page.select_one("nav.browse-list")
    services = list(list_body.select("li.browse-list-item"))
    assert len(services) == 3
    assert normalize_spaces(services[0].text) == "My Service 2"
    assert normalize_spaces(services[1].text) == "My Service 1"
    assert normalize_spaces(services[2].text) == "My Service 3 Archived"


class TestPlatformAdminSearch:
    def test_page_requires_platform_admin(self, client_request):
        client_request.get(".platform_admin_search", _expected_status=403)

    def test_page_loads(self, client_request, platform_admin_user):
        client_request.login(platform_admin_user)
        client_request.get(".platform_admin_search")

    def test_can_search_for_user(
        self, mocker, client_request, platform_admin_user, active_user_create_broadcasts_permission
    ):
        mocker.patch(
            "app.main.views.platform_admin.user_api_client.find_users_by_full_or_partial_email",
            return_value={"data": [active_user_create_broadcasts_permission]},
        )
        mocker.patch(
            "app.main.views.platform_admin.service_api_client.find_services_by_name",
            return_value={"data": []},
        )
        mocker.patch("app.main.views.platform_admin.get_url_for_notify_record", return_value=None)
        client_request.login(platform_admin_user)

        response = client_request.post(".platform_admin_search", _data={"search": "caseworker"}, _expected_status=200)

        assert normalize_spaces(response.select(".govuk-tabs ul")[0]) == "Users (1)"

        found_user_links = response.select(".govuk-tabs ul")[1].select("a")
        assert found_user_links[0].text == "test@user.gov.uk"
        assert found_user_links[0].get("href") == "/users/6ce466d0-fd6a-11e5-82f5-e0accb9d11a6"

    def test_can_search_for_services(self, mocker, client_request, platform_admin_user, service_one, service_two):
        mocker.patch(
            "app.main.views.platform_admin.user_api_client.find_users_by_full_or_partial_email",
            return_value={"data": []},
        )
        mocker.patch(
            "app.main.views.platform_admin.service_api_client.find_services_by_name",
            return_value={"data": [service_one, service_two]},
        )
        mocker.patch("app.main.views.platform_admin.get_url_for_notify_record", return_value=None)
        client_request.login(platform_admin_user)

        response = client_request.post(".platform_admin_search", _data={"search": "service"}, _expected_status=200)

        assert normalize_spaces(response.select(".govuk-tabs ul")[0]) == "Services (2)"

        found_service_links = response.select(".govuk-tabs ul")[1].select("a")
        assert found_service_links[0].text == "service one"
        assert found_service_links[0].get("href") == "/services/596364a0-858e-42c8-9062-a8fe822260eb"
        assert found_service_links[1].text == "service two"
        assert found_service_links[1].get("href") == "/services/147ad62a-2951-4fa1-9ca0-093cd1a52c52"

    def test_shows_results_from_all_categories(
        self,
        mocker,
        client_request,
        platform_admin_user,
        active_user_create_broadcasts_permission,
        service_one,
        service_two,
    ):
        mocker.patch(
            "app.main.views.platform_admin.user_api_client.find_users_by_full_or_partial_email",
            return_value={"data": [active_user_create_broadcasts_permission]},
        )
        mocker.patch(
            "app.main.views.platform_admin.service_api_client.find_services_by_name",
            return_value={"data": [service_one, service_two]},
        )
        mocker.patch("app.main.views.platform_admin.get_url_for_notify_record", return_value=None)
        client_request.login(platform_admin_user)

        response = client_request.post(".platform_admin_search", _data={"search": "service"}, _expected_status=200)

        assert normalize_spaces(response.select(".govuk-tabs ul")[0]) == "Users (1) Services (2)"

        found_user_links = response.select(".govuk-tabs ul")[1].select("a")
        assert found_user_links[0].text == "test@user.gov.uk"
        assert found_user_links[0].get("href") == "/users/6ce466d0-fd6a-11e5-82f5-e0accb9d11a6"

        found_service_links = response.select(".govuk-tabs ul")[2].select("a")
        assert found_service_links[0].text == "service one"
        assert found_service_links[0].get("href") == "/services/596364a0-858e-42c8-9062-a8fe822260eb"
        assert found_service_links[1].text == "service two"
        assert found_service_links[1].get("href") == "/services/147ad62a-2951-4fa1-9ca0-093cd1a52c52"


class TestPlatformAdminActions:
    def test_admin_actions_is_platform_admin_only(self, client_request):
        client_request.get("main.admin_actions", _expected_status=403)

    def test_lists_api_key_actions(
        self,
        client_request,
        platform_admin_user,
        mocker,
        fake_uuid,
    ):
        mock_get_pending_actions = mocker.patch(
            "app.admin_actions_api_client.get_pending_admin_actions",
            return_value={
                "pending": [
                    {
                        "service_id": SERVICE_ONE_ID,
                        "created_by": fake_uuid,
                        "created_at": "2025-02-14T12:34:56",
                        "action_type": "create_api_key",
                        "action_data": {
                            "key_type": "normal",
                            "key_name": "Test Key",
                        },
                    },
                    {
                        "service_id": SERVICE_TWO_ID,
                        "created_by": fake_uuid,
                        "created_at": "2025-02-14T12:34:56",
                        "action_type": "create_api_key",
                        "action_data": {
                            "key_type": "team",
                            "key_name": "Test Key",
                        },
                    },
                ],
                "users": {fake_uuid: {"name": "Test", "email_address": "test@test.gov.uk"}},
                "services": {
                    SERVICE_ONE_ID: {"name": "Test Live Service", "active": True, "restricted": False},
                    SERVICE_TWO_ID: {"name": "Test Service 2", "active": True, "restricted": True},
                },
            },
        )

        client_request.login(platform_admin_user)
        page = client_request.get("main.admin_actions")
        elements = page.select("main .govuk-grid-row")

        assert len(elements) == 2
        assert "Create API key for live service Test Live Service" in normalize_spaces(elements[0].text)
        assert "Key type: Live" in normalize_spaces(elements[0].text)
        assert "Create API key for service Test Service 2" in normalize_spaces(elements[1].text)
        assert "Key type: Team and guest" in normalize_spaces(elements[1].text)

        mock_get_pending_actions.assert_called_once()

    def test_lists_invite_actions(
        self,
        client_request,
        platform_admin_user,
        mocker,
        fake_uuid,
    ):
        mock_get_pending_actions = mocker.patch(
            "app.admin_actions_api_client.get_pending_admin_actions",
            return_value={
                "pending": [
                    {
                        "service_id": SERVICE_ONE_ID,
                        "created_by": fake_uuid,
                        "created_at": "2025-02-14T12:34:56",
                        "action_type": "invite_user",
                        "action_data": {
                            "email_address": "testing@test.gov.uk",
                            "permissions": [
                                "create_broadcasts",
                                "approve_broadcasts",
                                "manage_templates",
                                "view_activity",
                            ],
                            "login_authentication": "sms_auth",
                            "folder_permissions": [],
                        },
                    },
                ],
                "users": {fake_uuid: {"name": "Test", "email_address": "test@test.gov.uk"}},
                "services": {
                    SERVICE_ONE_ID: {"name": "Test Live Service", "active": True, "restricted": False},
                },
            },
        )

        client_request.login(platform_admin_user)
        page = client_request.get("main.admin_actions")
        elements = page.select("main .govuk-grid-row")

        assert len(elements) == 1
        assert "Invite user testing@test.gov.uk to live service Test Live Service" in normalize_spaces(elements[0].text)
        assert "Create new alerts" in normalize_spaces(elements[0].text)
        assert "Approve alerts" in normalize_spaces(elements[0].text)
        assert "Add and edit templates" in normalize_spaces(elements[0].text)

        mock_get_pending_actions.assert_called_once()

    def test_lists_edit_permission_actions(
        self,
        client_request,
        platform_admin_user,
        mocker,
        fake_uuid,
    ):
        edited_user_uuid = str(uuid.uuid4())
        mock_get_pending_actions = mocker.patch(
            "app.admin_actions_api_client.get_pending_admin_actions",
            return_value={
                "pending": [
                    {
                        "service_id": SERVICE_ONE_ID,
                        "created_by": fake_uuid,
                        "created_at": "2025-02-14T12:34:56",
                        "action_type": "edit_permissions",
                        "action_data": {
                            "user_id": edited_user_uuid,
                            "existing_permissions": [],
                            "permissions": [
                                "create_broadcasts",
                                "approve_broadcasts",
                                "manage_templates",
                                "view_activity",
                            ],
                            "folder_permissions": [],
                        },
                    },
                ],
                "users": {
                    fake_uuid: {"name": "Test", "email_address": "test@test.gov.uk"},
                    edited_user_uuid: {"name": "Test 2", "email_address": "testing@test.gov.uk"},
                },
                "services": {
                    SERVICE_ONE_ID: {"name": "Test Live Service", "active": True, "restricted": False},
                },
            },
        )

        client_request.login(platform_admin_user)
        page = client_request.get("main.admin_actions")
        elements = page.select("main .govuk-grid-row")

        assert len(elements) == 1
        assert "Edit testing@test.gov.uk's permissions to live service Test Live Service" in normalize_spaces(
            elements[0].text
        )
        assert "Create new alerts" in normalize_spaces(elements[0].text)
        assert "Approve alerts" in normalize_spaces(elements[0].text)
        assert "Add and edit templates" in normalize_spaces(elements[0].text)

        mock_get_pending_actions.assert_called_once()

    def test_lists_elevate_user_actions(
        self,
        client_request,
        platform_admin_user,
        mocker,
        fake_uuid,
    ):
        mock_get_pending_actions = mocker.patch(
            "app.admin_actions_api_client.get_pending_admin_actions",
            return_value={
                "pending": [
                    {
                        "service_id": None,
                        "created_by": fake_uuid,
                        "created_at": "2025-02-14T12:34:56",
                        "action_type": "elevate_platform_admin",
                        "action_data": {},
                    },
                ],
                "users": {
                    fake_uuid: {"name": "Test", "email_address": "test@test.gov.uk"},
                },
                "services": {},
            },
        )

        client_request.login(platform_admin_user)
        page = client_request.get("main.admin_actions")
        elements = page.select("main .govuk-grid-row")

        assert len(elements) == 1
        assert "Elevate to full platform admin" in normalize_spaces(elements[0].text)

        mock_get_pending_actions.assert_called_once()

    @staticmethod
    def sample_pending_action(fake_uuid, user_id):
        return {
            "id": fake_uuid,
            "service_id": SERVICE_ONE_ID,
            "created_by": user_id,
            "created_at": "2025-02-14T12:34:56",
            "action_type": "create_api_key",
            "action_data": {"key_name": "Test", "key_type": "team"},
            "status": "pending",
        }

    def test_cannot_approve_own_action(
        self,
        client_request,
        platform_admin_user,
        fake_uuid,
        mocker,
    ):
        pending_action = self.sample_pending_action(fake_uuid, platform_admin_user["id"])
        mocker.patch(
            "app.admin_actions_api_client.get_pending_admin_actions",
            return_value={
                "pending": [pending_action],
                "users": {
                    platform_admin_user["id"]: {"name": "Test", "email_address": "test@test.gov.uk"},
                },
                "services": {
                    SERVICE_ONE_ID: {"name": "Test Live Service", "active": True, "restricted": False},
                },
            },
        )
        mocker.patch(
            "app.admin_actions_api_client.get_admin_action_by_id",
            return_value=pending_action,
        )
        client_request.login(platform_admin_user)

        # Is the approve button disabled?
        page = client_request.get("main.admin_actions")
        approve_button = page.select_one("button[data-button-type=approve]")
        assert "disabled" in approve_button.attrs

        # Do we enforce reject it even if they enable the button?
        mock_review_admin_action = mocker.patch("app.admin_actions_api_client.review_admin_action", return_value=None)
        page = client_request.post(
            "main.review_admin_action", action_id=fake_uuid, new_status="approved", _follow_redirects=True
        )
        assert "You cannot approve your own admin approvals" in page.select_one(".banner-dangerous").text

        mock_review_admin_action.assert_not_called()

    def test_can_approve_others_actions(
        self,
        client_request,
        platform_admin_user,
        fake_uuid,
        mocker,
    ):
        random_user_uuid = str(uuid.uuid4())
        pending_action = self.sample_pending_action(fake_uuid, random_user_uuid)  # Not created by the admin
        mocker.patch(
            "app.admin_actions_api_client.get_pending_admin_actions",
            return_value={
                "pending": [pending_action],
                "users": {
                    random_user_uuid: {"name": "Test", "email_address": "test@test.gov.uk"},
                },
                "services": {
                    SERVICE_ONE_ID: {"name": "Test Live Service", "active": True, "restricted": False},
                },
            },
        )
        mocker.patch(
            "app.admin_actions_api_client.get_admin_action_by_id",
            return_value=pending_action,
        )
        client_request.login(platform_admin_user)

        # Is the approve button enabled?
        page = client_request.get("main.admin_actions")
        approve_button = page.select_one("button[data-button-type=approve]")
        assert "disabled" not in approve_button.attrs

        # Does the endpoint allow it through too?
        mock_review_admin_action = mocker.patch("app.admin_actions_api_client.review_admin_action", return_value=None)
        mock_api_key_create = mocker.patch("app.api_key_api_client.create_api_key", return_value="test")
        page = client_request.post(
            "main.review_admin_action", action_id=fake_uuid, new_status="approved", _follow_redirects=True
        )

        mock_review_admin_action.assert_called_once_with(fake_uuid, "approved")
        mock_api_key_create.assert_called_once_with(
            service_id=SERVICE_ONE_ID,
            key_name="Test",
            key_type="team",
        )

    @pytest.mark.parametrize("is_own_action", (True, False))
    def test_admins_can_reject_all_actions(
        self,
        client_request,
        platform_admin_user,
        mocker,
        is_own_action,
    ):
        action_id = str(uuid.uuid4())  # Reused for both action and creator
        mocker.patch(
            "app.admin_actions_api_client.get_pending_admin_actions",
            return_value={"pending": []},  # For the followed redirect before asserting
        )
        mocker.patch(
            "app.admin_actions_api_client.get_admin_action_by_id",
            return_value=self.sample_pending_action(
                action_id,
                (platform_admin_user["id"] if is_own_action else action_id),
            ),
        )
        mock_review_admin_action = mocker.patch("app.admin_actions_api_client.review_admin_action", return_value=None)

        client_request.login(platform_admin_user)
        client_request.post(
            "main.review_admin_action", action_id=action_id, new_status="rejected", _follow_redirects=True
        )

        mock_review_admin_action.assert_called_once_with(action_id, "rejected")

    def test_approving_creates_api_key(
        self,
        client_request,
        platform_admin_user,
        mocker,
        mock_get_service,
    ):
        action_id = str(uuid.uuid4())  # Reused for both action and creator ID
        mocker.patch(
            "app.admin_actions_api_client.get_admin_action_by_id",
            return_value={
                "id": action_id,
                "service_id": SERVICE_ONE_ID,
                "created_by": action_id,  # Test user is not the creator
                "created_at": "2025-02-14T12:34:56",
                "action_type": "create_api_key",
                "action_data": {
                    "key_type": "test",
                    "key_name": "Test Key",
                },
                "status": "pending",
            },
        )
        mock_review_admin_action = mocker.patch("app.admin_actions_api_client.review_admin_action", return_value=None)
        mock_api_key_create = mocker.patch("app.api_key_api_client.create_api_key", return_value="key-secret")

        client_request.login(platform_admin_user)
        page = client_request.post(
            "main.review_admin_action",
            action_id=action_id,
            new_status="approved",
            _expected_status=200,  # POSTs expect a redirect, but for API keys we want the secret to be a once only
        )

        mock_review_admin_action.assert_called_once_with(action_id, "approved")
        mock_api_key_create.assert_called_once_with(
            service_id=SERVICE_ONE_ID,
            key_name="Test Key",
            key_type="test",
        )

        clipboard = page.select_one(".copy-to-clipboard__value")
        assert "key-secret" in clipboard.text

    def test_approving_creates_user_invite(
        self,
        client_request,
        platform_admin_user,
        mocker,
    ):
        action_or_creator_id = str(uuid.uuid4())
        mocker.patch(
            "app.admin_actions_api_client.get_admin_action_by_id",
            return_value={
                "id": action_or_creator_id,
                "service_id": SERVICE_ONE_ID,
                "created_by": action_or_creator_id,
                "created_at": "2025-02-14T12:34:56",
                "action_type": "invite_user",
                "action_data": {
                    "email_address": "testing@test.gov.uk",
                    "permissions": [
                        "create_broadcasts",
                    ],
                    "login_authentication": "sms_auth",
                    "folder_permissions": [],
                },
                "status": "pending",
            },
        )
        mock_review_admin_action = mocker.patch("app.admin_actions_api_client.review_admin_action", return_value=None)
        mock_user_invite = mocker.patch(
            "app.invite_api_client.create_invite",
            return_value={"from_user": action_or_creator_id},
        )

        client_request.login(platform_admin_user)
        client_request.post(
            "main.review_admin_action",
            action_id=action_or_creator_id,
            new_status="approved",
            _expected_redirect=url_for(".manage_users", service_id=SERVICE_ONE_ID),
        )

        mock_review_admin_action.assert_called_once_with(action_or_creator_id, "approved")
        mock_user_invite.assert_called_once_with(
            action_or_creator_id,
            SERVICE_ONE_ID,
            "testing@test.gov.uk",
            [
                "create_broadcasts",
            ],
            "sms_auth",
            [],
        )

    def test_approving_edits_user_permissions(
        self,
        client_request,
        platform_admin_user,
        mocker,
    ):
        action_or_creator_id = str(uuid.uuid4())
        edited_user_id = str(uuid.uuid4())

        mocker.patch(
            "app.admin_actions_api_client.get_admin_action_by_id",
            return_value={
                "id": action_or_creator_id,
                "service_id": SERVICE_ONE_ID,
                "created_by": action_or_creator_id,  # Test user is not the creator
                "created_at": "2025-02-14T12:34:56",
                "action_type": "edit_permissions",
                "action_data": {
                    "user_id": edited_user_id,
                    "existing_permissions": [],
                    "permissions": [
                        "create_broadcasts",
                    ],
                    "folder_permissions": [],
                },
                "status": "pending",
            },
        )
        mock_review_admin_action = mocker.patch("app.admin_actions_api_client.review_admin_action", return_value=None)
        mock_edit_permissions = mocker.patch(
            "app.user_api_client.set_user_permissions",
            return_value=None,
        )

        client_request.login(platform_admin_user)
        # For User.from_id to work, .login patches it to our platform admin user
        mocker.patch(
            "app.user_api_client.get_user",
            return_value={"id": edited_user_id, "platform_admin": False, "email_address": "testing@gov.uk"},
        )
        client_request.post(
            "main.review_admin_action",
            action_id=action_or_creator_id,
            new_status="approved",
            _expected_redirect=url_for(".manage_users", service_id=SERVICE_ONE_ID),
        )

        mock_review_admin_action.assert_called_once_with(action_or_creator_id, "approved")
        mock_edit_permissions.assert_called_once_with(
            edited_user_id,
            SERVICE_ONE_ID,
            permissions=[
                "create_broadcasts",
            ],
            folder_permissions=[],
        )

    def test_approving_marks_admin_for_elevation_redemption(
        self,
        client_request,
        platform_admin_user,
        mocker,
    ):
        action_or_creator_id = str(uuid.uuid4())

        mocker.patch(
            "app.admin_actions_api_client.get_admin_action_by_id",
            return_value={
                "id": action_or_creator_id,
                "service_id": None,
                "created_by": action_or_creator_id,  # Test user is not the creator
                "created_at": "2025-02-14T12:34:56",
                "action_type": "elevate_platform_admin",
                "action_data": {},
                "status": "pending",
            },
        )
        mock_review_admin_action = mocker.patch("app.admin_actions_api_client.review_admin_action", return_value=None)
        mock_elevate_admin = mocker.patch(
            "app.user_api_client.elevate_admin_next_login",
            return_value=None,
        )

        client_request.login(platform_admin_user)
        client_request.post(
            "main.review_admin_action",
            action_id=action_or_creator_id,
            new_status="approved",
            _expected_redirect=url_for(".admin_actions"),
        )

        mock_review_admin_action.assert_called_once_with(action_or_creator_id, "approved")
        mock_elevate_admin.assert_called_once_with(action_or_creator_id, platform_admin_user["id"])


class TestPlatformAdminElevation:
    def test_platform_admin_capable_can_request_elevation(self, client_request, platform_admin_capable_user, mocker):
        client_request.login(platform_admin_capable_user)
        assert not current_user.platform_admin

        mock_create_admin_action = mocker.patch("app.admin_actions_api_client.create_admin_action", return_value=None)
        mocker.patch(
            "app.admin_actions_api_client.get_pending_admin_actions",
            return_value={"pending": []},
        )

        page = client_request.get(
            "main.platform_admin_request_elevation",
        )
        assert normalize_spaces(page.select_one("h1").text) == "Request Platform Admin Elevation"

        page = client_request.post(
            "main.platform_admin_request_elevation", _expected_redirect=url_for("main.admin_actions")
        )

        flashes = session.get("_flashes")
        assert len(flashes) == 1
        assert flashes[0][1] == "An admin approval has been created"
        mock_create_admin_action.assert_called_once_with(
            {
                "created_by": str(platform_admin_capable_user["id"]),
                "action_type": "elevate_platform_admin",
                "action_data": {},
            }
        )

    @freeze_time("2015-01-01 11:00:00")
    def test_pending_elevation_can_become_active_platform_admin(
        self,
        client_request,
        platform_admin_user,
        mocker,
    ):
        # Make the admin elevation pending
        platform_admin_user["platform_admin_active"] = False
        platform_admin_user["platform_admin_capable"] = True
        platform_admin_user["platform_admin_redemption"] = datetime.datetime(2025, 1, 1, 12, 0, 0)
        assert not session.get("platform_admin_active")
        assert not current_user.platform_admin

        client_request.login(platform_admin_user)
        # Should allow viewing the elevation prompt page:
        client_request.get(
            "main.platform_admin_elevation",
        )

        mocker.patch(
            "app.user_api_client.redeem_admin_elevation",
        )
        client_request.post(
            "main.platform_admin_elevation",
        )

        assert session.get("platform_admin_active")
        assert current_user.platform_admin

    @pytest.mark.parametrize(
        "platform_admin_capable, platform_admin_redemption",
        [
            (True, None),
            (True, datetime.datetime(2025, 1, 1, 10, 0, 0)),  # Expired an hour ago
            (False, datetime.datetime(2025, 1, 1, 12, 0, 0)),
        ],
    )
    @freeze_time("2025-01-01 11:00:00")
    def test_invalid_elevation_cannot_become_active_platform_admin(
        self,
        client_request,
        platform_admin_user,
        platform_admin_redemption,
        platform_admin_capable,
    ):
        platform_admin_user["platform_admin_active"] = False
        platform_admin_user["platform_admin_capable"] = platform_admin_capable
        platform_admin_user["platform_admin_redemption"] = platform_admin_redemption
        assert not current_user.platform_admin

        client_request.login(platform_admin_user)
        client_request.get(
            "main.platform_admin_elevation",
            _expected_status=403,
        )
        client_request.post(
            "main.platform_admin_elevation",
            _expected_status=403,
        )

        assert not current_user.platform_admin
