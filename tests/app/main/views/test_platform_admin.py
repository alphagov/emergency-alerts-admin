import datetime
from functools import partial
from unittest.mock import ANY, call

import pytest
from flask import url_for

from app.main.views.platform_admin import (
    create_global_stats,
    format_stats_by_service,
    get_tech_failure_status_box_data,
    is_over_threshold,
    sum_service_usage,
)
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
    mock_get_detailed_services.assert_called_once_with(
        {"detailed": True, "include_from_test_key": True, "only_active": False}
    )


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
            "detailed": True,
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
            "detailed": True,
            "only_active": False,
        }
    )


def test_create_global_stats_sets_failure_rates(fake_uuid):
    services = [service_json(fake_uuid, "a", []), service_json(fake_uuid, "b", [])]
    services[0]["statistics"] = create_stats(
        emails_requested=1,
        emails_delivered=1,
        emails_failed=0,
    )
    services[1]["statistics"] = create_stats(
        emails_requested=2,
        emails_delivered=1,
        emails_failed=1,
    )

    stats = create_global_stats(services)
    assert stats == {
        "email": {"delivered": 2, "failed": 1, "requested": 3, "failure_rate": "33.3"},
        "sms": {"delivered": 0, "failed": 0, "requested": 0, "failure_rate": "0"},
        "letter": {"delivered": 0, "failed": 0, "requested": 0, "failure_rate": "0"},
    }


def create_stats(
    emails_requested=0,
    emails_delivered=0,
    emails_failed=0,
    sms_requested=0,
    sms_delivered=0,
    sms_failed=0,
    letters_requested=0,
    letters_delivered=0,
    letters_failed=0,
):
    return {
        "sms": {
            "requested": sms_requested,
            "delivered": sms_delivered,
            "failed": sms_failed,
        },
        "email": {
            "requested": emails_requested,
            "delivered": emails_delivered,
            "failed": emails_failed,
        },
        "letter": {
            "requested": letters_requested,
            "delivered": letters_delivered,
            "failed": letters_failed,
        },
    }


def test_format_stats_by_service_returns_correct_values(fake_uuid):
    services = [service_json(fake_uuid, "a", [])]
    services[0]["statistics"] = create_stats(
        emails_requested=10,
        emails_delivered=3,
        emails_failed=5,
        sms_requested=50,
        sms_delivered=7,
        sms_failed=11,
        letters_requested=40,
        letters_delivered=20,
        letters_failed=7,
    )

    ret = list(format_stats_by_service(services))
    assert len(ret) == 1

    assert ret[0]["stats"]["email"]["requested"] == 10
    assert ret[0]["stats"]["email"]["delivered"] == 3
    assert ret[0]["stats"]["email"]["failed"] == 5

    assert ret[0]["stats"]["sms"]["requested"] == 50
    assert ret[0]["stats"]["sms"]["delivered"] == 7
    assert ret[0]["stats"]["sms"]["failed"] == 11

    assert ret[0]["stats"]["letter"]["requested"] == 40
    assert ret[0]["stats"]["letter"]["delivered"] == 20
    assert ret[0]["stats"]["letter"]["failed"] == 7


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
    services[0]["statistics"] = create_stats()
    services[1]["statistics"] = create_stats()
    services[2]["statistics"] = create_stats()

    mock_get_detailed_services.return_value = {"data": services}
    client_request.login(platform_admin_user)
    page = client_request.get(endpoint)

    mock_get_detailed_services.assert_called_once_with(
        {"detailed": True, "include_from_test_key": True, "only_active": ANY}
    )

    list_body = page.select_one("nav.browse-list")
    services = list(list_body.select("li.browse-list-item"))
    assert len(services) == 3
    assert normalize_spaces(services[0].text) == "A"
    assert normalize_spaces(services[1].text) == "B"
    assert normalize_spaces(services[2].text) == "C Archived"


@pytest.mark.parametrize(
    "endpoint, restricted, research_mode", [("main.trial_services", True, False), ("main.live_services", False, False)]
)
def test_should_order_services_by_usage_with_inactive_last(
    endpoint,
    restricted,
    research_mode,
    client_request,
    platform_admin_user,
    mock_get_detailed_services,
    fake_uuid,
):
    services = [
        service_json(fake_uuid, "My Service 1", [], restricted=restricted, research_mode=research_mode),
        service_json(fake_uuid, "My Service 2", [], restricted=restricted, research_mode=research_mode),
        service_json(fake_uuid, "My Service 3", [], restricted=restricted, research_mode=research_mode, active=False),
    ]
    services[0]["statistics"] = create_stats(
        emails_requested=100, emails_delivered=25, emails_failed=25, sms_requested=100, sms_delivered=25, sms_failed=25
    )

    services[1]["statistics"] = create_stats(
        emails_requested=200, emails_delivered=50, emails_failed=50, sms_requested=200, sms_delivered=50, sms_failed=50
    )

    services[2]["statistics"] = create_stats(
        emails_requested=200, emails_delivered=50, emails_failed=50, sms_requested=200, sms_delivered=50, sms_failed=50
    )

    mock_get_detailed_services.return_value = {"data": services}
    client_request.login(platform_admin_user)
    page = client_request.get(endpoint)

    mock_get_detailed_services.assert_called_once_with(
        {"detailed": True, "include_from_test_key": True, "only_active": ANY}
    )

    list_body = page.select_one("nav.browse-list")
    services = list(list_body.select("li.browse-list-item"))
    assert len(services) == 3
    assert normalize_spaces(services[0].text) == "My Service 2"
    assert normalize_spaces(services[1].text) == "My Service 1"
    assert normalize_spaces(services[2].text) == "My Service 3 Archived"


def test_sum_service_usage_is_sum_of_all_activity(fake_uuid):
    service = service_json(fake_uuid, "My Service 1")
    service["statistics"] = create_stats(
        emails_requested=100, emails_delivered=25, emails_failed=25, sms_requested=100, sms_delivered=25, sms_failed=25
    )
    assert sum_service_usage(service) == 200


def test_sum_service_usage_with_zeros(fake_uuid):
    service = service_json(fake_uuid, "My Service 1")
    service["statistics"] = create_stats(
        emails_requested=0, emails_delivered=0, emails_failed=25, sms_requested=0, sms_delivered=0, sms_failed=0
    )
    assert sum_service_usage(service) == 0


@pytest.mark.parametrize(
    "number, total, threshold, result",
    [
        (0, 0, 0, False),
        (1, 1, 0, True),
        (2, 3, 66, True),
        (2, 3, 67, False),
    ],
)
def test_is_over_threshold(number, total, threshold, result):
    assert is_over_threshold(number, total, threshold) is result


def test_get_tech_failure_status_box_data_removes_percentage_data():
    stats = {
        "failures": {"permanent-failure": 0, "technical-failure": 0, "temporary-failure": 1, "virus-scan-failed": 0},
        "test-key": 0,
        "total": 5589,
    }
    tech_failure_data = get_tech_failure_status_box_data(stats)

    assert "percentage" not in tech_failure_data


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
