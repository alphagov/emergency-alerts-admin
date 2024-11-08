import datetime
from functools import partial
from unittest.mock import ANY, call

import pytest
from flask import url_for

from tests import service_json
from tests.conftest import normalize_spaces


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


@pytest.mark.parametrize("endpoint", ["main.live_services", "main.trial_services"], ids=["live", "trial"])
def test_should_show_archived_services_last(
    endpoint,
    client_request,
    platform_admin_user,
    mock_get_detailed_services,
):
    services = [
        service_json(name="C", active=False, created_at="2002-02-02 12:00:00"),
        service_json(name="B", active=True, created_at="2001-01-01 12:00:00"),
        service_json(name="A", active=True, created_at="2003-03-03 12:00:00"),
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


@pytest.mark.parametrize("endpoint", ["main.trial_services", "main.live_services"])
def test_should_order_services_by_usage_with_inactive_last(
    endpoint,
    client_request,
    platform_admin_user,
    mock_get_detailed_services,
    fake_uuid,
):
    services = [
        service_json(fake_uuid, "My Service 1", []),
        service_json(fake_uuid, "My Service 2", []),
        service_json(fake_uuid, "My Service 3", [], active=False),
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


def test_clear_cache_shows_form(
    client_request,
    platform_admin_user,
    mocker,
):
    redis = mocker.patch("app.main.views.platform_admin.redis_client")
    client_request.login(platform_admin_user)

    page = client_request.get("main.clear_cache")

    assert not redis.delete_by_pattern.called
    radios = {el["value"] for el in page.select("input[type=checkbox]")}

    assert radios == {"user", "service", "template", "organisation", "broadcast"}


@pytest.mark.parametrize(
    "model_type, expected_calls, expected_confirmation",
    (
        (
            "template",
            [
                call("service-????????-????-????-????-????????????-templates"),
                call(
                    "service-????????-????-????-????-????????????-template-????????-????-????-????-????????????-version-*"  # noqa
                ),
                call(
                    "service-????????-????-????-????-????????????-template-????????-????-????-????-????????????-versions"  # noqa
                ),
            ],
            "Removed 6 objects across 3 key formats for template",
        ),
        (
            ["service", "organisation"],
            [
                call("has_jobs-????????-????-????-????-????????????"),
                call("service-????????-????-????-????-????????????"),
                call("service-????????-????-????-????-????????????-templates"),
                call("service-????????-????-????-????-????????????-data-retention"),
                call("service-????????-????-????-????-????????????-template-folders"),
                call("organisations"),
                call("domains"),
                call("live-service-and-organisation-counts"),
                call("organisation-????????-????-????-????-????????????-name"),
            ],
            "Removed 18 objects across 9 key formats for service, organisation",
        ),
        (
            "broadcast",
            [
                call(
                    "service-????????-????-????-????-????????????-broadcast-message-????????-????-????-????-????????????"  # noqa
                ),
            ],
            "Removed 2 objects across 1 key formats for broadcast",
        ),
    ),
)
def test_clear_cache_submits_and_tells_you_how_many_things_were_deleted(
    client_request,
    platform_admin_user,
    mocker,
    model_type,
    expected_calls,
    expected_confirmation,
):
    redis = mocker.patch("app.main.views.platform_admin.redis_client")
    redis.delete_by_pattern.return_value = 2
    client_request.login(platform_admin_user)

    page = client_request.post("main.clear_cache", _data={"model_type": model_type}, _expected_status=200)

    assert redis.delete_by_pattern.call_args_list == expected_calls

    flash_banner = page.select_one("div.banner-default")
    assert flash_banner.text.strip() == expected_confirmation


def test_clear_cache_requires_option(
    client_request,
    platform_admin_user,
    mocker,
):
    redis = mocker.patch("app.main.views.platform_admin.redis_client")
    client_request.login(platform_admin_user)

    page = client_request.post("main.clear_cache", _data={}, _expected_status=200)

    assert normalize_spaces(page.select_one(".govuk-error-message").text) == "Error: Select at least one option"
    assert not redis.delete_by_pattern.called


class TestPlatformAdminSearch:
    def test_page_requires_platform_admin(self, client_request):
        client_request.get(".platform_admin_search", _expected_status=403)

    def test_page_loads(self, client_request, platform_admin_user):
        client_request.login(platform_admin_user)
        client_request.get(".platform_admin_search")

    def test_can_search_for_user(self, mocker, client_request, platform_admin_user, active_caseworking_user):
        mocker.patch(
            "app.main.views.platform_admin.user_api_client.find_users_by_full_or_partial_email",
            return_value={"data": [active_caseworking_user]},
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
        assert found_user_links[0].text == "caseworker@example.gov.uk"
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
        self, mocker, client_request, platform_admin_user, active_caseworking_user, service_one, service_two
    ):
        mocker.patch(
            "app.main.views.platform_admin.user_api_client.find_users_by_full_or_partial_email",
            return_value={"data": [active_caseworking_user]},
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
        assert found_user_links[0].text == "caseworker@example.gov.uk"
        assert found_user_links[0].get("href") == "/users/6ce466d0-fd6a-11e5-82f5-e0accb9d11a6"

        found_service_links = response.select(".govuk-tabs ul")[2].select("a")
        assert found_service_links[0].text == "service one"
        assert found_service_links[0].get("href") == "/services/596364a0-858e-42c8-9062-a8fe822260eb"
        assert found_service_links[1].text == "service two"
        assert found_service_links[1].get("href") == "/services/147ad62a-2951-4fa1-9ca0-093cd1a52c52"
