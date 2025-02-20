import datetime
from functools import partial
from unittest.mock import ANY

import pytest
from flask import url_for

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
    def test_should_not_allow_normal_user_to_list_actions(self, client_request):
        client_request.get("main.admin_actions", _expected_status=403)

    def test_should_list_api_key_actions(
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
                "users": {str(fake_uuid): {"name": "Test", "email_address": "test@test.gov.uk"}},
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

    def test_should_display_invite_actions(
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
                "users": {str(fake_uuid): {"name": "Test", "email_address": "test@test.gov.uk"}},
                "services": {
                    SERVICE_ONE_ID: {"name": "Test Live Service", "active": True, "restricted": False},
                    # SERVICE_TWO_ID: {"name": "Test Service 2", "active": True, "restricted": True},
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
