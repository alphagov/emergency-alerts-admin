import json
import uuid
from functools import partial

import pytest
from flask import url_for
from freezegun import freeze_time

from tests import (
    NotifyBeautifulSoup,
    broadcast_message_json,
    broadcast_message_version_json,
    sample_uuid,
    user_json,
)
from tests.app.broadcast_areas.custom_polygons import (
    BD1_1EE,
    BD1_1EE_1,
    BD1_1EE_2,
    BD1_1EE_3,
    BRISTOL,
    BURFORD,
    CHELTENHAM,
    CUMBRIA_FLOOD_WARNING_AREA,
    HG3_2RL,
    MULTIPLE_ENGLAND,
    SKYE,
)
from tests.app.utils.test_broadcast import MockArea
from tests.conftest import (
    SERVICE_NO_BROADCAST,
    SERVICE_ONE_ID,
    SERVICE_TWO_ID,
    create_active_user_approve_broadcasts_permissions,
    create_active_user_create_broadcasts_permissions,
    create_active_user_view_permissions,
    create_platform_admin_user,
    normalize_spaces,
)
from tests.utils import xml_path

sample_uuid = sample_uuid()

sending_success_statuses = {
    "ee": {
        "alert": [
            {"created_at": "2020-02-22T23:23:23.000000", "status": "sending"},
            {
                "created_at": "2020-02-22T23:23:23.000000",
                "status": "returned-ack",
            },
        ],
        "cancel": [],
    }
}

sending_success_cancelled_statuses = {
    "ee": {
        "alert": [
            {"created_at": "2020-02-22T23:23:23.000000", "status": "sending"},
            {
                "created_at": "2020-02-22T23:23:23.000000",
                "status": "returned-ack",
            },
        ],
        "cancel": [
            {"created_at": "2020-02-22T23:24:24.000000", "status": "sending"},
            {
                "created_at": "2020-02-22T23:24:24.000000",
                "status": "returned-ack",
            },
        ],
    }
}

sending_failure_statuses = {
    "ee": {
        "alert": [
            {"created_at": "2020-02-22T23:23:23.000000", "status": "sending"},
            {
                "created_at": "2020-02-22T23:23:23.000000",
                "status": "returned-error",
            },
        ],
        "cancel": [],
    }
}


@pytest.mark.parametrize(
    "endpoint, extra_args, expected_get_status, expected_post_status",
    (
        (
            ".broadcast_dashboard",
            {},
            403,
            403,
        ),
        (
            ".broadcast_dashboard_updates",
            {},
            403,
            405,
        ),
        (
            ".broadcast_dashboard_previous",
            {},
            403,
            403,
        ),
        (
            ".new_broadcast",
            {},
            403,
            403,
        ),
        (
            ".write_new_broadcast",
            {},
            403,
            403,
        ),
        (
            ".broadcast",
            {"template_id": sample_uuid},
            403,
            405,
        ),
        (
            ".preview_areas",
            {
                "message_id": sample_uuid,
                "message_type": "broadcast",
            },
            403,
            405,
        ),
        (
            ".choose_library",
            {"message_id": sample_uuid, "message_type": "broadcast"},
            403,
            405,
        ),
        (
            ".choose_area",
            {"message_id": sample_uuid, "library_slug": "countries", "message_type": "broadcast"},
            403,
            403,
        ),
        (
            ".remove_area",
            {"message_id": sample_uuid, "area_slug": "E92000001", "message_type": "broadcast"},
            403,
            405,
        ),
        (
            ".choose_broadcast_duration",
            {"broadcast_message_id": sample_uuid},
            403,
            403,
        ),
        (
            ".preview_broadcast_message",
            {"broadcast_message_id": sample_uuid},
            403,
            403,
        ),
        (
            ".view_current_broadcast",
            {"broadcast_message_id": sample_uuid},
            403,
            403,
        ),
        (
            ".view_previous_broadcast",
            {"broadcast_message_id": sample_uuid},
            403,
            405,
        ),
        (
            ".view_previous_broadcast",
            {"broadcast_message_id": sample_uuid},
            403,
            405,
        ),
        (
            ".get_broadcast_geojson",
            {"broadcast_message_id": sample_uuid},
            403,
            405,
        ),
        (
            ".cancel_broadcast_message",
            {"broadcast_message_id": sample_uuid},
            403,
            403,
        ),
        (
            ".search_coordinates",
            {
                "message_id": sample_uuid,
                "coordinate_type": "latitude_longitude",
                "library_slug": "coordinates",
                "message_type": "broadcast",
            },
            403,
            403,
        ),
    ),
)
def test_broadcast_pages_403_without_permission(
    client_request, endpoint, extra_args, expected_get_status, expected_post_status, mock_get_broadcast_message_versions
):
    client_request.get(endpoint, service_id=SERVICE_NO_BROADCAST, _expected_status=expected_get_status, **extra_args)
    client_request.post(endpoint, service_id=SERVICE_NO_BROADCAST, _expected_status=expected_post_status, **extra_args)


@pytest.mark.parametrize("user_is_platform_admin", [True, False])
@pytest.mark.parametrize(
    "endpoint, extra_args, expected_get_status, expected_post_status",
    (
        (
            ".new_broadcast",
            {},
            403,
            403,
        ),
        (
            ".write_new_broadcast",
            {},
            403,
            403,
        ),
        (
            ".broadcast",
            {"template_id": sample_uuid},
            403,
            405,
        ),
        (
            ".preview_areas",
            {"message_id": sample_uuid, "message_type": "broadcast"},
            403,
            405,
        ),
        (
            ".choose_library",
            {"message_id": sample_uuid, "message_type": "broadcast"},
            403,
            405,
        ),
        (
            ".choose_area",
            {"message_id": sample_uuid, "library_slug": "countries", "message_type": "broadcast"},
            403,
            403,
        ),
        (
            ".remove_area",
            {"message_id": sample_uuid, "area_slug": "england", "message_type": "broadcast"},
            403,
            405,
        ),
        (
            ".preview_broadcast_message",
            {"broadcast_message_id": sample_uuid},
            403,
            403,
        ),
    ),
)
def test_broadcast_pages_403_for_user_without_permission(
    client_request,
    service_one,
    active_user_view_permissions,
    platform_admin_user_no_service_permissions,
    endpoint,
    extra_args,
    expected_get_status,
    expected_post_status,
    user_is_platform_admin,
    mock_get_broadcast_message,
    mock_get_broadcast_message_versions,
    mock_check_can_update_status,
    mock_create_broadcast_message,
):
    """
    Checks that users without permissions, including admin users, cannot create or edit broadcasts.
    """
    service_one["permissions"] += ["broadcast"]
    if user_is_platform_admin:
        client_request.login(platform_admin_user_no_service_permissions)
    else:
        client_request.login(active_user_view_permissions)
    client_request.get(endpoint, service_id=SERVICE_ONE_ID, _expected_status=expected_get_status, **extra_args)
    client_request.post(endpoint, service_id=SERVICE_ONE_ID, _expected_status=expected_post_status, **extra_args)


@pytest.mark.parametrize(
    "endpoint, endpoint_params, endpoint_data",
    (
        (".search_postcodes", {}, {"postcode": "BD1 1EE", "radius": "2", "continue": True}),
        (".choose_area", {"library_slug": "countries"}, {"postcode": "BD1 1EE", "radius": "2", "continue": True}),
        (
            ".choose_sub_area",
            {"library_slug": "local_authorities", "area_slug": "E10000016"},
            {"postcode": "BD1 1EE", "radius": "2", "continue": True},
        ),
    ),
)
def test_template_area_pages_error_for_user_with_only_create_broadcasts_permission(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
    mock_get_broadcast_message_versions,
    endpoint,
    endpoint_params,
    endpoint_data,
):
    """
    The endpoints/logic is shared for templates and broadcasts, but the permissions for each are
    defined separately.
    """

    client_request.login(active_user_create_broadcasts_permission)
    client_request.post(
        endpoint,
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="templates",
        **endpoint_params,
        _data=endpoint_data,
        _expected_status=403,
    )


@pytest.mark.parametrize(
    "endpoint, endpoint_params, endpoint_data",
    (
        (".search_postcodes", {}, {"postcode": "BD1 1EE", "radius": "2", "continue": True}),
        (".choose_area", {"library_slug": "countries"}, {"postcode": "BD1 1EE", "radius": "2", "continue": True}),
        (
            ".choose_sub_area",
            {"library_slug": "local_authorities", "area_slug": "E10000016"},
            {"postcode": "BD1 1EE", "radius": "2", "continue": True},
        ),
    ),
)
def test_broadcast_area_pages_error_for_user_with_only_manage_templates_permission(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    active_user_manage_template_permissions,
    mock_get_broadcast_message_versions,
    endpoint,
    endpoint_params,
    endpoint_data,
):
    """
    The endpoints/logic is shared for templates and broadcasts, but the permissions for each are
    defined separately.
    """

    client_request.login(active_user_manage_template_permissions)
    client_request.post(
        endpoint,
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
        **endpoint_params,
        _data=endpoint_data,
        _expected_status=403,
    )


@pytest.mark.parametrize(
    "user",
    [
        create_active_user_view_permissions(),
        create_platform_admin_user(),
        create_active_user_create_broadcasts_permissions(),
    ],
)
def test_user_cannot_accept_broadcast_without_permission(
    client_request,
    service_one,
    mock_get_broadcast_message,
    mock_check_can_update_status,
    mock_update_broadcast_message_status,
    user,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(user)

    client_request.post(
        ".approve_broadcast_message",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=sample_uuid,
        _expected_status=403,
    )


@pytest.mark.parametrize("user_is_platform_admin", [True, False])
def test_user_cannot_reject_broadcast_without_permission(
    client_request,
    service_one,
    active_user_view_permissions,
    platform_admin_user_no_service_permissions,
    user_is_platform_admin,
):
    service_one["permissions"] += ["broadcast"]
    if user_is_platform_admin:
        client_request.login(platform_admin_user_no_service_permissions)
    else:
        client_request.login(active_user_view_permissions)

    client_request.get(
        ".reject_broadcast_message",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=sample_uuid,
        _expected_status=403,
    )


def test_user_cannot_cancel_broadcast_without_permission(
    client_request,
    service_one,
    active_user_view_permissions,
):
    """
    separate test for cancel_broadcast endpoint, because admin users are allowed to cancel broadcasts
    """
    service_one["permissions"] += ["broadcast"]

    client_request.get(
        ".cancel_broadcast_message",
        service_id=SERVICE_ONE_ID,
        _expected_status=403,
        **{"broadcast_message_id": sample_uuid},
    )
    client_request.post(
        ".cancel_broadcast_message",
        service_id=SERVICE_ONE_ID,
        _expected_status=403,
        **{"broadcast_message_id": sample_uuid},
    )


def test_view_broadcast_page_displays_error_if_area_invalid(
    mocker,
    fake_uuid,
    service_one,
    client_request,
    mock_get_broadcast_message_versions,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
    mock_update_broadcast_message_status,
    mock_get_count_of_phones,
):
    mocker.patch(
        "app.areas_api_client.get_areas_by_ids",
        return_value=[
            {
                "id": "area-id",
                "name": "Invalid area",
            }
        ],
    )
    broadcast_message = broadcast_message_json(
        id_=fake_uuid,
        template_id=fake_uuid,
        created_by_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        starts_at="2020-02-20T20:20:20.000000",
        created_at="2020-02-20T20:20:20.000000",
        status="draft",
        areas={
            # The ring is not closed and is self-intersecting.
            "simple_polygons": [[[51.5310, -0.1580], [51.5310, -0.1570], [51.5310, -0.1580], [51.5310, -0.2]]],
            "names": ["Invalid area"],
            "ids": ["test"],
        },
    )

    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message,
    )
    service_one["permissions"] += ["broadcast"]

    client_request.login(create_active_user_create_broadcasts_permissions())

    page = client_request.get(
        ".view_current_broadcast",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )

    # Asserts that an error is displayed because the area is invalid
    assert normalize_spaces(page.select_one(".govuk-error-summary").text) == (
        "There is a problem The area used is invalid and the alert cannot be sent. If the alert"
        " was created through the API, report it to the alert creator. Otherwise report it "
        "to the Emergency Alerts team."
    )

    submitted_alert_page = client_request.post(
        ".submit_broadcast_message", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid, _expected_status=200
    )

    # Asserts that even when data is posted to submit broadcast, the page rendered displays
    # error because the area is invalid, and the broadcast status remains in draft

    assert normalize_spaces(submitted_alert_page.select_one(".govuk-error-summary").text) == (
        "There is a problem The area used is invalid and the alert cannot be sent. If the alert"
        " was created through the API, report it to the alert creator. Otherwise report it "
        "to the Emergency Alerts team."
    )

    assert mock_update_broadcast_message_status.called is False


@pytest.mark.parametrize(
    "endpoint, step_index, expected_link_text, expected_link_href",
    (
        (".broadcast_tour", 1, "Continue", partial(url_for, ".broadcast_tour", step_index=2)),
        (".broadcast_tour", 2, "Continue", partial(url_for, ".broadcast_tour", step_index=3)),
        (".broadcast_tour", 3, "Continue", partial(url_for, ".broadcast_tour", step_index=4)),
        (".broadcast_tour", 4, "Continue", partial(url_for, ".broadcast_tour", step_index=5)),
        (".broadcast_tour", 5, "Continue", partial(url_for, ".service_dashboard")),
        (".broadcast_tour", 6, "Continue", partial(url_for, ".service_dashboard")),
        (".broadcast_tour_live", 1, "Continue", partial(url_for, ".broadcast_tour_live", step_index=2)),
        (".broadcast_tour_live", 2, "Continue", partial(url_for, ".service_dashboard")),
    ),
)
def test_broadcast_tour_pages_have_continue_link(
    client_request,
    service_one,
    endpoint,
    step_index,
    expected_link_text,
    expected_link_href,
):
    service_one["permissions"] += ["broadcast"]
    page = client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        step_index=step_index,
    )
    link = page.select_one(".banner-tour a")
    assert normalize_spaces(link.text) == expected_link_text
    assert link["href"] == expected_link_href(service_id=SERVICE_ONE_ID)


@pytest.mark.parametrize(
    "endpoint, step_index",
    (
        pytest.param(".broadcast_tour", 1, marks=pytest.mark.xfail),
        pytest.param(".broadcast_tour", 2, marks=pytest.mark.xfail),
        pytest.param(".broadcast_tour", 3, marks=pytest.mark.xfail),
        pytest.param(".broadcast_tour", 4, marks=pytest.mark.xfail),
        (".broadcast_tour", 5),
        (".broadcast_tour", 6),
        (".broadcast_tour_live", 1),
        (".broadcast_tour_live", 2),
    ),
)
def test_some_broadcast_tour_pages_show_service_name(
    client_request,
    service_one,
    endpoint,
    step_index,
):
    service_one["permissions"] += ["broadcast"]
    page = client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        step_index=step_index,
    )
    assert normalize_spaces(page.select_one(".navigation-service").text).startswith("service one Training")


@pytest.mark.parametrize(
    "trial_mode, channel, allowed_broadcast_provider, selector, expected_text, expected_tagged_text",
    (
        (
            True,
            None,
            ["ee", "o2", "three", "vodafone"],
            ".navigation-service-type.navigation-service-type--training",
            "service one Training Switch service",
            "Training",
        ),
        (
            True,
            "test",
            ["ee", "o2", "three", "vodafone"],
            ".navigation-service-type.navigation-service-type--training",
            "service one Training Switch service",
            "Training",
        ),
        (
            False,
            "severe",
            ["ee", "o2", "three", "vodafone"],
            ".navigation-service-type.navigation-service-type--live",
            "service one Live Switch service",
            "Live",
        ),
        (
            False,
            "operator",
            ["ee", "o2", "three", "vodafone"],
            ".navigation-service-type.navigation-service-type--operator",
            "service one Operator Switch service",
            "Operator",
        ),
        (
            False,
            "operator",
            ["vodafone"],
            ".navigation-service-type.navigation-service-type--operator",
            "service one Operator (Vodafone) Switch service",
            "Operator (Vodafone)",
        ),
        (
            False,
            "test",
            ["ee", "o2", "three", "vodafone"],
            ".navigation-service-type.navigation-service-type--test",
            "service one Test Switch service",
            "Test",
        ),
        (
            False,
            "test",
            ["vodafone"],
            ".navigation-service-type.navigation-service-type--test",
            "service one Test (Vodafone) Switch service",
            "Test (Vodafone)",
        ),
        (
            False,
            "government",
            ["ee", "o2", "three", "vodafone"],
            ".navigation-service-type.navigation-service-type--government",
            "service one Government Switch service",
            "Government",
        ),
        (
            False,
            "government",
            ["vodafone"],
            ".navigation-service-type.navigation-service-type--government",
            "service one Government (Vodafone) Switch service",
            "Government (Vodafone)",
        ),
        (
            False,
            "severe",
            ["vodafone"],
            ".navigation-service-type.navigation-service-type--live",
            "service one Live (Vodafone) Switch service",
            "Live (Vodafone)",
        ),
    ),
)
def test_broadcast_service_shows_channel_settings(
    client_request,
    service_one,
    mock_get_no_broadcast_messages,
    trial_mode,
    allowed_broadcast_provider,
    channel,
    selector,
    expected_text,
    expected_tagged_text,
):
    service_one["allowed_broadcast_provider"] = allowed_broadcast_provider
    service_one["permissions"] += ["broadcast"]
    service_one["restricted"] = trial_mode
    service_one["broadcast_channel"] = channel
    page = client_request.get(
        ".broadcast_dashboard",
        service_id=SERVICE_ONE_ID,
    )
    assert normalize_spaces(page.select_one(".navigation-service").text) == (expected_text)
    assert normalize_spaces(page.select_one(".navigation-service").select_one(selector).text) == (expected_tagged_text)


@pytest.mark.parametrize(
    "endpoint, step_index",
    (
        (".broadcast_tour", 0),
        (".broadcast_tour", 7),
        (".broadcast_tour_live", 0),
        (".broadcast_tour_live", 3),
    ),
)
def test_broadcast_tour_page_404s_out_of_range(
    client_request,
    service_one,
    endpoint,
    step_index,
):
    service_one["permissions"] += ["broadcast"]
    client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        step_index=step_index,
        _expected_status=404,
    )


def test_dashboard_redirects_to_broadcast_dashboard(
    client_request,
    service_one,
):
    service_one["permissions"] += ["broadcast"]
    client_request.get(
        ".service_dashboard",
        service_id=SERVICE_ONE_ID,
        _expected_redirect=url_for(
            ".broadcast_dashboard",
            service_id=SERVICE_ONE_ID,
        ),
    )


def test_empty_broadcast_dashboard(
    client_request,
    service_one,
    mock_get_no_broadcast_messages,
):
    service_one["permissions"] += ["broadcast"]
    page = client_request.get(
        ".broadcast_dashboard",
        service_id=SERVICE_ONE_ID,
    )
    assert normalize_spaces(page.select_one("h1").text) == "Current alerts"
    assert [normalize_spaces(row.text) for row in page.select(".table-empty-message")] == [
        "You do not have any current alerts",
    ]


@pytest.mark.parametrize(
    "user",
    [
        create_active_user_approve_broadcasts_permissions(),
        create_active_user_create_broadcasts_permissions(),
    ],
)
@pytest.mark.parametrize(
    "mock_get_broadcast_messages,has_sending_error",
    [
        (None, False),
        ({"sending_error": True}, True),
    ],
    indirect=["mock_get_broadcast_messages"],
)
@freeze_time("2020-02-20 02:20")
def test_broadcast_dashboard(client_request, service_one, mock_get_broadcast_messages, has_sending_error, user, mocker):
    mocker.patch(
        "app.areas_api_client.get_areas_by_ids",
        return_value=[
            {
                "id": "england",
                "name": "England",
            },
            {
                "id": "scotland",
                "name": "Scotland",
            },
        ],
    )
    service_one["permissions"] += ["broadcast"]
    client_request.login(user)
    page = client_request.get(
        ".broadcast_dashboard",
        service_id=SERVICE_ONE_ID,
    )

    assert len(page.select(".ajax-block-container")) == len(page.select("h1")) == 1

    if has_sending_error:
        assert [normalize_spaces(row.text) for row in page.select(".ajax-block-container")[0].select(".file-list")] == [
            "Example template This is a test sending error live since today at 2:20am Area: England Scotland",
            "Half an hour ago This is a test Waiting for approval Area: England Scotland",
            "Example template This is a test draft",
            "Hour and a half ago This is a test Waiting for approval Area: England Scotland",
            "Example template This is a test sending error live since today at 1:20am Area: England Scotland",
        ]
    else:
        assert [normalize_spaces(row.text) for row in page.select(".ajax-block-container")[0].select(".file-list")] == [
            "Example template This is a test live since today at 2:20am Area: England Scotland",
            "Half an hour ago This is a test Waiting for approval Area: England Scotland",
            "Example template This is a test draft",
            "Hour and a half ago This is a test Waiting for approval Area: England Scotland",
            "Example template This is a test live since today at 1:20am Area: England Scotland",
        ]


@pytest.mark.parametrize(
    "user",
    [
        create_platform_admin_user(),
        create_active_user_view_permissions(),
        create_active_user_approve_broadcasts_permissions(),
    ],
)
@pytest.mark.parametrize(
    "endpoint",
    (
        ".broadcast_dashboard",
        ".broadcast_dashboard_previous",
        ".broadcast_dashboard_rejected",
    ),
)
def test_broadcast_dashboard_does_not_have_button_if_user_does_not_have_permission_to_create_broadcast(
    client_request,
    service_one,
    mock_get_broadcast_messages,
    mock_get_broadcast_message_provider_statuses,
    endpoint,
    user,
    mock_get_areas_by_ids,
):
    client_request.login(user)

    service_one["permissions"] += ["broadcast"]
    page = client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
    )
    assert not page.select("a.govuk-button")


@pytest.mark.parametrize(
    "endpoint",
    (
        ".broadcast_dashboard",
        ".broadcast_dashboard_previous",
        ".broadcast_dashboard_rejected",
    ),
)
def test_broadcast_dashboard_has_new_alert_button_if_user_has_permission_to_create_broadcasts(
    client_request,
    service_one,
    mock_get_broadcast_messages,
    mock_get_broadcast_message_provider_statuses,
    active_user_create_broadcasts_permission,
    endpoint,
    mock_get_areas_by_ids,
):
    client_request.login(active_user_create_broadcasts_permission)

    service_one["permissions"] += ["broadcast"]
    page = client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
    )
    button = page.select_one(".js-stick-at-bottom-when-scrolling a.govuk-button.govuk-button--secondary")
    assert normalize_spaces(button.text) == "Create new alert"
    assert button["href"] == url_for(
        "main.new_broadcast",
        service_id=SERVICE_ONE_ID,
    )


@freeze_time("2020-02-20 02:20")
def test_broadcast_dashboard_json(
    client_request,
    service_one,
    mock_get_broadcast_messages,
    mock_get_broadcast_message_provider_statuses,
    mock_get_areas_by_ids,
):
    service_one["permissions"] += ["broadcast"]

    response = client_request.get_response(
        ".broadcast_dashboard_updates",
        service_id=SERVICE_ONE_ID,
    )

    response_json = json.loads(response.get_data(as_text=True))
    response_html = NotifyBeautifulSoup(response_json["current_broadcasts"], "html.parser")
    broadcasts = normalize_spaces(response_html)

    assert response_json.keys() == {"current_broadcasts"}
    assert "Waiting for approval" in broadcasts
    assert "live since today at 2:20am" in broadcasts


@pytest.mark.parametrize(
    "user",
    [
        create_active_user_approve_broadcasts_permissions(),
        create_active_user_create_broadcasts_permissions(),
    ],
)
@freeze_time("2020-02-20 02:20")
def test_previous_broadcasts_page(
    client_request, service_one, mock_get_broadcast_messages, mock_get_broadcast_message_provider_statuses, user, mocker
):
    mocker.patch(
        "app.areas_api_client.get_areas_by_ids",
        return_value=[
            {
                "id": "england",
                "name": "England",
            },
            {
                "id": "scotland",
                "name": "Scotland",
            },
        ],
    )
    service_one["permissions"] += ["broadcast"]
    client_request.login(user)
    page = client_request.get(
        ".broadcast_dashboard_previous",
        service_id=SERVICE_ONE_ID,
    )

    assert normalize_spaces(page.select_one("main h1").text) == "Past alerts"
    assert len(page.select(".ajax-block-container")) == 1
    assert [normalize_spaces(row.text) for row in page.select(".ajax-block-container")[0].select(".file-list")] == [
        "Example template This is a test Yesterday at 2:20pm Area: England Scotland",
        "Example template This is a test Yesterday at 2:20am Area: England Scotland",
    ]


@pytest.mark.parametrize(
    "user",
    [
        create_active_user_approve_broadcasts_permissions(),
        create_active_user_create_broadcasts_permissions(),
    ],
)
@freeze_time("2020-02-20 02:20")
def test_rejected_broadcasts_page(
    client_request, service_one, mock_get_broadcast_messages, user, mock_get_areas_by_ids
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(user)
    page = client_request.get(
        ".broadcast_dashboard_rejected",
        service_id=SERVICE_ONE_ID,
    )

    assert normalize_spaces(page.select_one("main h1").text) == "Rejected alerts"
    assert len(page.select(".ajax-block-container")) == 1
    assert [normalize_spaces(row.text) for row in page.select(".ajax-block-container")[0].select(".file-list")] == [
        "Example template rejected today at 1:20:00am This is a test",
    ]


def test_new_broadcast_page(
    client_request,
    service_one,
    active_user_create_broadcasts_permission,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        ".new_broadcast",
        service_id=SERVICE_ONE_ID,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Create new alert"

    form = page.select_one("form")
    assert form["method"] == "post"
    assert "action" not in form

    assert [
        (
            choice.select_one("input")["name"],
            choice.select_one("input")["value"],
            normalize_spaces(choice.select_one("label").text),
        )
        for choice in form.select(".govuk-radios__item")
    ] == [
        ("content", "freeform", "Write your own message"),
        ("content", "template", "Use a template"),
    ]


@pytest.mark.parametrize(
    "value, expected_redirect_endpoint",
    (
        ("freeform", "main.write_new_broadcast"),
        ("template", "main.choose_template"),
    ),
)
def test_new_broadcast_page_redirects(
    client_request,
    service_one,
    active_user_create_broadcasts_permission,
    value,
    expected_redirect_endpoint,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    client_request.post(
        ".new_broadcast",
        service_id=SERVICE_ONE_ID,
        _data={
            "content": value,
        },
        _expected_redirect=url_for(
            expected_redirect_endpoint,
            service_id=SERVICE_ONE_ID,
        ),
    )


def test_write_new_broadcast_page(
    client_request,
    service_one,
    active_user_create_broadcasts_permission,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        ".write_new_broadcast",
        service_id=SERVICE_ONE_ID,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Write new alert"

    form = page.select_one("form")
    assert form["method"] == "post"
    assert "action" not in form

    assert normalize_spaces(page.select_one("label[for=reference]").text) == "Reference"
    assert page.select_one("input[type=text]")["name"] == "reference"

    assert normalize_spaces(page.select_one("label[for=content]").text) == "Alert message"
    assert page.select_one("textarea")["name"] == "content"
    assert page.select_one("textarea")["data-notify-module"] == "enhanced-textbox"
    assert page.select_one("textarea")["data-highlight-placeholders"] == "false"

    assert (page.select_one("[data-notify-module=update-status]")["data-updates-url"]) == url_for(
        ".count_content_length", service_id=SERVICE_ONE_ID, template_type="broadcast", field="content"
    )

    assert (
        (page.select_one("[data-notify-module=update-status]")["data-target"])
        == (page.select_one("textarea")["id"])
        == "content"
    )

    assert (page.select_one("[data-notify-module=update-status]")["aria-live"]) == "polite"


def test_write_new_broadcast_posts(
    client_request,
    service_one,
    mock_create_broadcast_message,
    fake_uuid,
    active_user_create_broadcasts_permission,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    client_request.post(
        ".write_new_broadcast",
        service_id=SERVICE_ONE_ID,
        _data={
            "reference": "My new alert",
            "content": "This is a test",
        },
        _expected_redirect=url_for(
            ".choose_extra_content",
            service_id=SERVICE_ONE_ID,
            broadcast_message_id=fake_uuid,
        ),
    )
    mock_create_broadcast_message.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        reference="My new alert",
        content="This is a test",
        template_id=None,
    )


@pytest.mark.parametrize(
    "content, expected_error_message",
    (
        ("", "Enter an alert message"),
        ("ŵ" * 616, "Content must be 615 characters or fewer because it contains ŵ"),
        ("w" * 1_396, "Content must be 1,395 characters or fewer"),
        ("hello ((name))", "You can’t use ((double brackets)) to personalise this message"),
    ),
)
def test_write_new_broadcast_bad_content(
    client_request,
    service_one,
    mock_create_broadcast_message,
    active_user_create_broadcasts_permission,
    content,
    expected_error_message,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.post(
        ".write_new_broadcast",
        service_id=SERVICE_ONE_ID,
        _data={
            "reference": "My new alert",
            "content": content,
        },
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one(".error-message").text) == (expected_error_message)
    assert mock_create_broadcast_message.called is False


@pytest.mark.parametrize(
    "content, expected_error_message",
    (
        ("", "Enter an alert message"),
        ("ŵ" * 616, "Content must be 615 characters or fewer because it contains ŵ"),
        ("w" * 1_396, "Content must be 1,395 characters or fewer"),
        ("hello ((name))", "You can’t use ((double brackets)) to personalise this message"),
    ),
)
def test_edit_broadcast_bad_content(
    client_request,
    service_one,
    mock_create_broadcast_message,
    active_user_create_broadcasts_permission,
    content,
    expected_error_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    mock_check_can_update_status,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
        ),
    )
    page = client_request.post(
        ".edit_broadcast",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _data={
            "reference": "My new alert",
            "content": content,
        },
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one(".error-message").text) == (expected_error_message)
    assert mock_update_broadcast_message.called is False


def test_choose_extra_content_page(
    client_request, service_one, active_user_create_broadcasts_permission, fake_uuid, mocker
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
        ),
    )
    page = client_request.get(
        ".choose_extra_content", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid, _test_page_title=False
    )

    assert (
        normalize_spaces(page.select_one("h1").text)
        == "Would you like to add additional information that will appear on gov.uk/alerts?"
    )

    form = page.select_one("form")
    assert form["method"] == "post"
    assert "action" not in form

    assert [
        (
            choice.select_one("input")["name"],
            choice.select_one("input")["value"],
            normalize_spaces(choice.select_one("label").text),
        )
        for choice in form.select(".govuk-radios__item")
    ] == [
        ("content", "yes", "Yes"),
        ("content", "no", "No"),
    ]


def test_add_extra_content_page(
    client_request, service_one, active_user_create_broadcasts_permission, fake_uuid, mocker
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
        ),
    )
    page = client_request.get(".add_extra_content", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid)

    assert normalize_spaces(page.select_one("h1").text) == "Add additional information"
    assert normalize_spaces(page.select_one("h1").text) == "Add additional information"

    form = page.select_one("form")
    assert form["method"] == "post"
    assert "action" not in form

    assert (
        normalize_spaces(page.select_one("label[for=extra_content]").text)
        == "Additional Information This might include evacuation procedures, Welsh translations "
        "or detailed information that's too long to include in the alert."
    )
    assert page.select_one("textarea")["data-notify-module"] == "enhanced-textbox"
    assert page.select_one("textarea")["data-highlight-placeholders"] == "false"

    assert (page.select_one("[data-notify-module=update-status]")["data-updates-url"]) == url_for(
        ".count_content_length", service_id=SERVICE_ONE_ID, template_type="broadcast", field="extra_content"
    )

    assert (
        (page.select_one("[data-notify-module=update-status]")["data-target"])
        == (page.select_one("textarea")["id"])
        == "extra_content"
    )

    assert (page.select_one("[data-notify-module=update-status]")["aria-live"]) == "polite"


def test_broadcast_page(
    client_request,
    service_one,
    fake_uuid,
    active_user_create_broadcasts_permission,
    mock_get_template_from_id,
    mocker,
    mock_get_areas_by_ids,
    mock_get_area_dict,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    mocker.patch(
        "app.broadcast_message_api_client.create_broadcast_message",
        return_value={"id": fake_uuid, "service_id": service_one, "template_id": fake_uuid, "areas": {}},
    )
    client_request.get(
        ".broadcast",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_redirect=url_for(".choose_extra_content", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid),
    )


@pytest.mark.parametrize(
    "areas_selected, areas_listed, count_of_phones, bleed, estimates",
    (
        (
            {
                "ids": ["E92000001"],
                "names": ["England"],
                "aggregate_names": ["England"],
                "simple_polygons": MULTIPLE_ENGLAND,
            },
            [
                "England Remove England",
            ],
            42_870_423,
            4_000,
            [
                "An area of 50,000 square miles Will get the alert",
                "An extra area of 2,000 square miles is Likely to get the alert",
                "More than 1 million phones estimated",
            ],
        ),
        (
            {
                "ids": ["bristol", "skye"],
                "names": ["Bristol", "Skye"],
                "aggregate_names": ["Bristol", "Skye"],
                "simple_polygons": [BRISTOL, SKYE],
            },
            [
                "Bristol Remove Bristol",
                "Skye Remove Skye",
            ],
            84_030,
            4,
            [
                "An area of 2,000 square miles Will get the alert",
                "An extra area of 400 square miles is Likely to get the alert",
                "Less than 1 million phones estimated",
            ],
        ),
        (
            {
                "ids": ["burford"],
                "names": ["Burford"],
                "aggregate_names": ["Burford"],
                "simple_polygons": [BURFORD],
            },
            [
                "Burford Remove Burford",
            ],
            31_143,
            500,
            [
                "An area of 100 square miles Will get the alert",
                "An extra area of 90 square miles is Likely to get the alert",
                "Less than 1 million phones estimated",
            ],
        ),
        (
            {
                "ids": ["cheltenham"],
                "names": ["Cheltenham"],
                "aggregate_names": ["Cheltenham"],
                "simple_polygons": [CHELTENHAM],
            },
            [
                "Cheltenham Remove Cheltenham",
            ],
            86_078,
            1_000,
            [
                "An area of 20 square miles Will get the alert",
                "An extra area of 20 square miles is Likely to get the alert",
                "Less than 1 million phones estimated",
            ],
        ),
    ),
)
def test_preview_areas_page(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    areas_selected,
    areas_listed,
    count_of_phones,
    bleed,
    estimates,
    active_user_create_broadcasts_permission,
    mock_get_broadcast_message_versions,
    mock_check_can_update_status,
):
    mocker.patch("app.broadcast_message_api_client.get_count_of_phones", return_value=count_of_phones)
    mocker.patch(
        "app.models.base_broadcast.Areas.get",
        return_value=[
            MockArea(
                {
                    "id": area_id,
                    "name": area_name,
                    "count_of_phones": count_of_phones,
                    "bleed": bleed,
                }
            )
            for area_id, area_name in zip(areas_selected["ids"], areas_selected["names"])
        ],
    )
    service_one["permissions"] += ["broadcast"]
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            areas=areas_selected,
        ),
    )
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        ".preview_areas",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
    )

    assert [normalize_spaces(item.text) for item in page.select("ul.area-list li.area-list-item")] == areas_listed

    assert len(page.select("#area-list-map")) == 1

    assert [normalize_spaces(item.text) for item in page.select(".area-list-key")] == estimates


def test_search_flood_warning_areas_page(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
    mock_get_flood_warning_area_library,
):
    mocker.patch("app.broadcast_message_api_client.get_count_of_phones", return_value=42.74975272772588)
    mocker.patch(
        "app.areas_api_client.get_areas_by_ids",
        return_value=[
            {
                "id": "011FWCN2M",
                "geographic_id": "011FWCN2M",
                "name": "Cumbria coast at Maryport harbour",
                "geography_type": "flood_warning_areas",
            }
        ],
    )
    service_one["permissions"] += ["broadcast"]
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            area_ids=["011FWCN2M"],
            areas={
                "ids": ["011FWCN2M"],
                "names": ["Cumbria coast at Maryport harbour"],
                "aggregate_names": ["Cumbria coast at Maryport harbour"],
                "simple_polygons": [CUMBRIA_FLOOD_WARNING_AREA],
            },
        ),
    )
    client_request.login(active_user_create_broadcasts_permission)

    page = client_request.get(
        ".search_flood_warning_areas",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
    )

    assert normalize_spaces(page.select_one("h1").text) == "Choose Flood Warning Target Areas (TA)"
    assert [normalize_spaces(item.text) for item in page.select("ul.area-list li.area-list-item")] == [
        "011FWCN2M: Cumbria coast at Maryport harbour Remove Cumbria coast at Maryport harbour"
    ]

    assert len(page.select("#area-list-map")) == 1

    assert [normalize_spaces(item.text) for item in page.select(".area-list-key")] == [
        "An area of 0 square miles Will get the alert",
        "An extra area of 10 square miles is Likely to get the alert",
        "Less than 1 million phones estimated",
    ]

    assert normalize_spaces(page.select(".govuk-button")[5].text) == "Add area"
    assert normalize_spaces(page.select(".govuk-button")[6].text) == "Remove Cumbria coast at Maryport harbour"
    assert normalize_spaces(page.select(".govuk-button")[7].text) == "Save and continue to preview"


def test_search_flood_warning_bulk_add_areas_page(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
    mock_get_count_of_phones,
    mock_get_libraries,
    mock_get_areas_by_ids,
):
    service_one["permissions"] += ["broadcast"]
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            area_ids=["011FWCN2M"],
            areas={
                "ids": ["011FWCN2M"],
                "names": ["Cumbria coast at Maryport harbour"],
                "aggregate_names": ["Cumbria coast at Maryport harbour"],
                "simple_polygons": [CUMBRIA_FLOOD_WARNING_AREA],
            },
        ),
    )
    client_request.login(active_user_create_broadcasts_permission)

    page = client_request.get(
        ".search_flood_warning_areas_as_a_list",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
    )

    assert normalize_spaces(page.select_one("h1").text) == "Enter Flood Warning Target Areas (TA) as a list"

    assert [normalize_spaces(item.text) for item in page.select(".govuk-hint")] == [
        "Emergency alerts can be sent to up to 25 target areas. "
        "Separate each TA code with a comma or write them on separate lines."
    ]
    assert page.select_one("textarea")["id"] == "areas"
    assert page.select_one("textarea")["rows"] == "10"
    assert normalize_spaces(page.select(".govuk-button")[5].text) == "Add areas"


def test_search_local_authority_bulk_add_areas_page(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
    mock_get_areas_by_ids,
    mock_get_count_of_phones,
):
    service_one["permissions"] += ["broadcast"]
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            area_ids=["E07000225"],
            areas={
                "ids": [""],
                "names": [""],
                "aggregate_names": [""],
                "simple_polygons": [],
            },
        ),
    )
    client_request.login(active_user_create_broadcasts_permission)

    page = client_request.get(
        ".search_local_authority_areas_as_a_list",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
    )

    assert normalize_spaces(page.select_one("h1").text) == "Enter local authorities as a list"

    assert [normalize_spaces(item.text) for item in page.select(".govuk-hint")] == [
        "Enter your list of local authorities as a list into the text box. "
        "You can have up to 25 local authorities as a list in one emergency alert. "
        "Your list of local authorities can be entered as one per new line."
    ]
    assert page.select_one("textarea")["id"] == "areas"
    assert page.select_one("textarea")["rows"] == "10"
    assert normalize_spaces(page.select(".govuk-button")[5].text) == "Add local authorities"


@pytest.mark.parametrize(
    "polygons, count_of_phones, expected_list_items",
    (
        (
            [
                [[1, 2], [3, 4], [5, 6]],
                [[7, 8], [9, 10], [11, 12]],
            ],
            0,
            [
                "An area of 300 square miles Will get the alert",
                "An extra area of 1,000 square miles is Likely to get the alert",
                "Unknown number of phones",
            ],
        ),
        (
            [BRISTOL],
            77000,
            [
                "An area of 4 square miles Will get the alert",
                "An extra area of 3 square miles is Likely to get the alert",
                "Less than 1 million phones estimated",
            ],
        ),
        (
            [SKYE],
            7030.187134868168,
            [
                "An area of 2,000 square miles Will get the alert",
                "An extra area of 500 square miles is Likely to get the alert",
                "Less than 1 million phones estimated",
            ],
        ),
    ),
)
def test_preview_areas_page_with_custom_polygons(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    polygons,
    count_of_phones,
    expected_list_items,
    active_user_create_broadcasts_permission,
    mock_check_can_update_status,
):
    mocker.patch("app.broadcast_message_api_client.get_count_of_phones", return_value=count_of_phones)
    service_one["permissions"] += ["broadcast"]
    mocker.patch(
        "app.models.areas.Areas.get",
        return_value=[
            MockArea({"id": "area-one", "name": "Area one"}),
            MockArea({"id": "area-two", "name": "Area two"}),
            MockArea({"id": "area-three", "name": "Area three"}),
        ],
    )
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            areas={
                "ids": ["area-one", "area-two", "area-three"],
                "names": ["Area one", "Area two", "Area three"],
                "simple_polygons": polygons,
            },
        ),
    )
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        ".preview_areas", service_id=SERVICE_ONE_ID, message_id=fake_uuid, message_type="broadcast"
    )

    assert [normalize_spaces(item.text) for item in page.select("ul.area-list li.area-list-item")] == [
        "Area one Remove Area one",
        "Area two Remove Area two",
        "Area three Remove Area three",
    ]

    assert len(page.select("#area-list-map")) == 1

    assert [normalize_spaces(item.text) for item in page.select(".area-list-key")] == expected_list_items


@pytest.mark.parametrize(
    "mock_areas, expected_list",
    (
        (
            [
                MockArea(
                    {
                        "id": "E92000001",
                        "name": "England",
                        "geography_type": "countries",
                    }
                ),
                MockArea(
                    {
                        "id": "S92000003",
                        "name": "Scotland",
                        "geography_type": "countries",
                    }
                ),
            ],
            [
                "Coordinates",
                "Countries",
                "Flood Warning Target Areas (TA code)",
                "Local authorities",
                "Postcode areas",
                "REPPIR DEPZ sites",
                "Test areas",
            ],
        ),
        (
            [
                MockArea(
                    {
                        "id": "E10000013",
                        "name": "Gloucestershire",
                    }
                ),
                MockArea(
                    {
                        "id": "E06000052",
                        "name": "Cornwall",
                    }
                ),
            ],
            [
                "Coordinates",
                "Countries",
                "Flood Warning Target Areas (TA code)",
                "Local authorities",
                "Postcode areas",
                "REPPIR DEPZ sites",
                "Test areas",
            ],
        ),
        (
            [
                MockArea(
                    {
                        "id": "E05010951",
                        "name": "Abbeymead",
                        "parent": "E07000081",
                        "geography_type": "local_authorities",
                    }
                ),
                MockArea(
                    {
                        "id": "S13003154",
                        "name": "Shetland Central",
                        "parent": "S12000027",
                        "geography_type": "local_authorities",
                    }
                ),
                MockArea(
                    {
                        "id": "E07000037",
                        "name": "High Peak",
                        "parent": "E10000007",
                        "geography_type": "local_authorities",
                    }
                ),
            ],
            [
                "Derbyshire",
                "Gloucester",
                "Gloucestershire",
                "Shetland Islands",
                "Coordinates",
                "Countries",
                "Flood Warning Target Areas (TA code)",
                "Local authorities",
                "Postcode areas",
                "REPPIR DEPZ sites",
                "Test areas",
            ],
        ),
    ),
)
def test_choose_library_page(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    active_user_create_broadcasts_permission,
    mock_areas,
    expected_list,
    mock_get_libraries,
    mock_get_library_example,
):
    parent_areas = {
        "E07000081": MockArea(
            {
                "id": "E07000081",
                "name": "Gloucester",
                "parent": "E10000013",
                "geography_type": "local_authorities",
            }
        ),
        "E10000013": MockArea(
            {
                "id": "E10000013",
                "name": "Gloucestershire",
                "geography_type": "local_authorities",
            }
        ),
        "S12000027": MockArea(
            {
                "id": "S12000027",
                "name": "Shetland Islands",
                "geography_type": "local_authorities",
            }
        ),
        "E10000007": MockArea(
            {
                "id": "E10000007",
                "name": "Derbyshire",
                "geography_type": "local_authorities",
            }
        ),
    }

    mocker.patch(
        "app.models.areas.Areas.get",
        return_value=mock_areas,
    )
    mocker.patch(
        "app.models.areas.Area.from_geographic_id",
        side_effect=parent_areas.__getitem__,
    )  # get parent area using geographic ID

    area_ids = [area.id for area in mock_areas]

    service_one["permissions"] += ["broadcast"]
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            area_ids=area_ids,
        ),
    )
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        ".choose_library",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
    )
    assert [normalize_spaces(title.text) for title in page.select("main a.govuk-link")] == expected_list

    assert normalize_spaces(page.select_one(".file-list-hint-large").text) == (
        "Use coordinates to create an alert area."
    )

    assert page.select_one("a.file-list-filename-large.govuk-link")["href"] == url_for(
        ".choose_area",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
        library_slug="coordinates",
    )


@pytest.mark.parametrize(
    "area_ids, expected_list",
    (
        (
            ["1km around the postcode BD1 1EE in Bradford"],
            [
                "Coordinates",
                "Countries",
                "Flood Warning Target Areas (TA code)",
                "Local authorities",
                "Postcode areas",
                "REPPIR DEPZ sites",
                "Test areas",
            ],
        ),
        (
            ["3km around the postcode BD1 1EE in Bradford"],
            [
                "Coordinates",
                "Countries",
                "Flood Warning Target Areas (TA code)",
                "Local authorities",
                "Postcode areas",
                "REPPIR DEPZ sites",
                "Test areas",
            ],
        ),
        (
            ["5km around the coordinates [54.0, -1.7] in Harrogate"],
            [
                "Coordinates",
                "Countries",
                "Flood Warning Target Areas (TA code)",
                "Local authorities",
                "Postcode areas",
                "REPPIR DEPZ sites",
                "Test areas",
            ],
        ),
    ),
)
def test_choose_library_page_with_custom_broadcast(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    active_user_create_broadcasts_permission,
    area_ids,
    expected_list,
    mock_get_libraries,
    mock_get_areas_by_ids,
    mock_get_library_example,
):
    service_one["permissions"] += ["broadcast"]
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            area_ids=area_ids,
        ),
    )
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        ".choose_library", service_id=SERVICE_ONE_ID, message_id=fake_uuid, message_type="broadcast"
    )
    assert [normalize_spaces(title.text) for title in page.select("main a.govuk-link")] == expected_list

    assert normalize_spaces(page.select(".file-list-hint-large")[0].text) == (
        "Use coordinates to create an alert area."
    )

    assert page.select_one("a.file-list-filename-large.govuk-link")["href"] == url_for(
        ".choose_area",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        library_slug="coordinates",
        message_type="broadcast",
    )


def test_suggested_area_has_correct_link(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    active_user_create_broadcasts_permission,
    mock_get_areas_by_ids,
    mock_get_library_example,
):
    mocker.patch(
        "app.models.areas.Area.from_geographic_id",
        return_value=MockArea(
            {
                "id": "E07000078",
                "name": "Cheltenham",
                "geography_type": "local_authorities",
            }
        ),
    )
    mocker.patch(
        "app.areas_api_client.get_libraries",
        return_value=[
            {
                "id": "wd25-lad25-local_authorities",
                "name": "Local authorities",
                "name_singular": "Local authority",
                "examples": [],
                "route": "local_authorities",
                "areas": [
                    MockArea(
                        {
                            "id": "E05015715",
                            "name": "Pitville",
                            "parent": "E07000078",
                        }
                    )
                ],
            },
        ],
    )
    mocker.patch(
        "app.areas_api_client.get_area",
        return_value={
            "id": "E05015715",
            "name": "Pitville",
            "parent": "E07000078",
        },
    )
    mocker.patch(
        "app.models.areas.Areas.get",
        return_value=[
            MockArea(
                {
                    "id": "E05015715",
                    "name": "Pitville",
                    "parent": "E07000078",
                    "geography_type": "local_authorities",
                }
            )
        ],
    )
    service_one["permissions"] += ["broadcast"]
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            area_ids=[
                "E05015715",  # Pitville, a ward of Cheltenham
            ],
        ),
    )
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        ".choose_library",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
        custom_broadcast=False,
    )
    link = page.select_one("main a.govuk-link")

    assert link.text == "Cheltenham"
    assert link["href"] == url_for(
        "main.choose_sub_area",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        library_slug="local_authorities",
        area_slug="E07000078",
        message_type="broadcast",
    )


@pytest.mark.parametrize(
    "library_slug, expected_page_title",
    (
        (
            "countries",
            "Choose countries",
        ),
        ("local_authorities", "Choose a local authority"),
        (
            "test",
            "Choose test areas",
        ),
        ("postcodes", "Choose alert area"),
        ("coordinates", "Choose coordinate type"),
    ),
)
def test_choose_area_page_titles(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    fake_uuid,
    active_user_create_broadcasts_permission,
    library_slug,
    expected_page_title,
    mock_get_libraries,
    mock_get_areas_by_ids,
    mock_get_areas_for_library,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        ".choose_area",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        library_slug=library_slug,
        message_type="broadcast",
        _follow_redirects=True,
    )
    assert normalize_spaces(page.select_one("h1").text) == expected_page_title


def test_choose_area_page(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    fake_uuid,
    active_user_create_broadcasts_permission,
    mock_get_libraries,
    mocker,
):
    mocker.patch(
        "app.areas_api_client.get_areas_for_library",
        return_value=[
            {
                "id": "E92000001",
                "geographic_id": "E92000001",
                "name": "England",
                "geography_type": "countries",
            },
            {
                "id": "N92000002",
                "geographic_id": "N92000002",
                "name": "Northern Ireland",
                "geography_type": "countries",
            },
            {
                "id": "S92000003",
                "geographic_id": "S92000003",
                "name": "Scotland",
                "geography_type": "countries",
            },
            {
                "id": "W92000004",
                "geographic_id": "W92000004",
                "name": "Wales",
                "geography_type": "countries",
            },
        ],
    )
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        ".choose_area",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
        library_slug="countries",
    )
    assert [
        (
            choice.select_one("input")["value"],
            normalize_spaces(choice.select_one("label").text),
        )
        for choice in page.select("form[method=post] .govuk-checkboxes__item")
    ] == [
        ("E92000001", "England"),
        ("N92000002", "Northern Ireland"),
        ("S92000003", "Scotland"),
        ("W92000004", "Wales"),
    ]


def test_choose_area_page_for_area_with_sub_areas(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    fake_uuid,
    active_user_create_broadcasts_permission,
    mock_get_libraries,
    mocker,
    mock_get_aberdeen_areas,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        ".choose_area",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
        library_slug="local_authorities",
    )
    assert normalize_spaces(page.select_one("h1").text) == "Choose a local authority"
    live_search = page.select_one("[data-notify-module=live-search]")
    assert live_search["data-targets"] == ".file-list-item"
    assert live_search.select_one("input")["type"] == "search"
    partial_url_for = partial(
        url_for,
        "main.choose_sub_area",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        library_slug="local_authorities",
        message_type="broadcast",
    )
    choices = [
        (
            choice.select_one("a.file-list-filename-large")["href"],
            normalize_spaces(choice.text),
        )
        for choice in page.select(".file-list-item")
    ]

    # First item, somewhere in Scotland
    assert choices[0] == (
        partial_url_for(area_slug="S12000033"),
        "Aberdeen City",
    )

    # Somewhere in England
    # ---
    # Note: we don't populate prev_area_slug query param, so the back link will come here rather than to a county page,
    # even though ashford belongs to kent
    assert choices[2] == (
        partial_url_for(area_slug="E07000223"),
        "Adur",
    )

    # Somewhere in Scotland
    assert choices[4] == (
        partial_url_for(area_slug="S12000041"),
        "Angus",
    )

    # Somewhere in Northern Ireland
    assert choices[5] == (
        partial_url_for(area_slug="N09000001"),
        "Antrim and Newtownabbey",
    )

    # Last item on the page
    assert choices[-1] == (
        partial_url_for(area_slug="E07000200"),
        "Babergh",
    )


def test_choose_sub_area_page_for_district_shows_checkboxes_for_wards(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    fake_uuid,
    active_user_create_broadcasts_permission,
    mocker,
):
    mocker.patch("app.areas_api_client.check_grandparent", return_value=False)
    mocker.patch(
        "app.areas_api_client.get_area",
        return_value={
            "id": "S12000033",
            "geographic_id": "S12000033",
            "name": "Aberdeen City",
            "geography_type": "local_authorities",
        },
    )
    mocker.patch(
        "app.areas_api_client.get_areas_for_parent",
        return_value=[
            {
                "id": "S13002845",
                "geographic_id": "S13002845",
                "name": "Airyhall/Broomhill/Garthdee",
                "parent": "S12000033",
                "geography_type": "local_authorities",
            },
            {
                "id": "S13002836",
                "geographic_id": "S13002836",
                "name": "Bridge of Don",
                "parent": "S12000033",
                "geography_type": "local_authorities",
            },
            {
                "id": "S13002835",
                "geographic_id": "S13002835",
                "name": "Dyce/Bucksburn/Danestone",
                "parent": "S12000033",
                "geography_type": "local_authorities",
            },
            {
                "id": "S13002837",
                "geographic_id": "S13002837",
                "name": "George Street/Harbour",
                "parent": "S12000033",
                "geography_type": "local_authorities",
            },
            {
                "id": "S13002838",
                "geographic_id": "S13002838",
                "name": "Hazlehead/Queens Cross",
                "parent": "S12000033",
                "geography_type": "local_authorities",
            },
            {
                "id": "S13002839",
                "geographic_id": "S13002839",
                "name": "Kincorth/Nigg/Cove",
                "parent": "S12000033",
                "geography_type": "local_authorities",
            },
            {
                "id": "S13002840",
                "geographic_id": "S13002840",
                "name": "Kingswells/Sheddocksley/Summerhill",
                "parent": "S12000033",
                "geography_type": "local_authorities",
            },
            {
                "id": "S13002841",
                "geographic_id": "S13002841",
                "name": "Lower Deeside",
                "parent": "S12000033",
                "geography_type": "local_authorities",
            },
            {
                "id": "S13002842",
                "geographic_id": "S13002842",
                "name": "Northfield/Mastrick North",
                "parent": "S12000033",
                "geography_type": "local_authorities",
            },
            {
                "id": "S13002843",
                "geographic_id": "S13002843",
                "name": "Tillydrone/Seaton/Old Aberdeen",
                "parent": "S12000033",
                "geography_type": "local_authorities",
            },
            {
                "id": "S13002846",
                "geographic_id": "S13002846",
                "name": "Torry/Ferryhill",
                "parent": "S12000033",
                "geography_type": "local_authorities",
            },
        ],
    )
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        "main.choose_sub_area",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        library_slug="local_authorities",
        area_slug="S12000033",
        message_type="broadcast",
    )
    assert normalize_spaces(page.select_one("h1").text) == "Choose an area of Aberdeen City"
    live_search = page.select_one("[data-notify-module=live-search]")
    assert live_search["data-targets"] == "#sub-areas .govuk-checkboxes__item"
    assert live_search.select_one("input")["type"] == "search"
    all_choices = [
        (
            choice.select_one("input")["value"],
            normalize_spaces(choice.select_one("label").text),
        )
        for choice in page.select("form[method=post] .govuk-checkboxes__item")
    ]
    sub_choices = [
        (
            choice.select_one("input")["value"],
            normalize_spaces(choice.select_one("label").text),
        )
        for choice in page.select("form[method=post] #sub-areas .govuk-checkboxes__item")
    ]
    assert all_choices[:3] == [
        ("y", "All of Aberdeen City"),
        ("S13002845", "Airyhall/Broomhill/Garthdee"),
        ("S13002836", "Bridge of Don"),
    ]
    assert sub_choices[:3] == [
        ("S13002845", "Airyhall/Broomhill/Garthdee"),
        ("S13002836", "Bridge of Don"),
        ("S13002835", "Dyce/Bucksburn/Danestone"),
    ]
    assert (
        all_choices[-1:]
        == sub_choices[-1:]
        == [
            ("S13002846", "Torry/Ferryhill"),
        ]
    )


@pytest.mark.parametrize(
    "prev_area_slug, expected_back_link_url, expected_back_link_extra_kwargs",
    [
        ("E10000016", "main.choose_sub_area", {"area_slug": "E10000016"}),  # Kent
        (None, ".choose_area", {}),
    ],
)
def test_choose_sub_area_page_for_district_has_back_link(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    active_user_create_broadcasts_permission,
    prev_area_slug,
    expected_back_link_url,
    expected_back_link_extra_kwargs,
    mocker,
    mock_get_areas_for_parent,
    mock_check_grandparent,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    mocker.patch(
        "app.areas_api_client.get_area",
        return_value={
            "id": "ashdord_id",
            "name": "Ashford",
        },
    )
    mocker.patch(
        "app.models.base_broadcast.Areas.get",
        return_value=[
            MockArea({"id": "E07000105", "name": "Ashford", "parent": "E10000016"}),
            MockArea({"id": "E10000016", "name": "Kent", "parent": None}),
        ],
    )
    page = client_request.get(
        "main.choose_sub_area",
        service_id=SERVICE_ONE_ID,
        message_id=str(uuid.UUID(int=0)),
        library_slug="local_authorities",
        area_slug="E07000105",  # Ashford
        message_type="broadcast",
        prev_area_slug=prev_area_slug,
    )
    assert normalize_spaces(page.select_one("h1").text) == "Choose an area of Ashford"
    back_link = page.select_one(".govuk-back-link")
    assert back_link["href"] == url_for(
        expected_back_link_url,
        service_id=SERVICE_ONE_ID,
        message_id=str(uuid.UUID(int=0)),
        library_slug="local_authorities",
        message_type="broadcast",
        **expected_back_link_extra_kwargs,
    )


def test_write_new_broadcast_does_update_when_broadcast_exists(
    mocker,
    client_request,
    service_one,
    active_user_create_broadcasts_permission,
    mock_create_broadcast_message,
    mock_update_broadcast_message,
    mock_check_can_update_status,
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=str(uuid.UUID(int=0)),
            service_id=SERVICE_ONE_ID,
            created_by_id=active_user_create_broadcasts_permission["id"],
            finishes_at=None,
            status="draft",
        ),
    )
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    client_request.get("main.write_new_broadcast", service_id=SERVICE_ONE_ID, message_id=str(uuid.UUID(int=0)))

    client_request.post(
        ".write_new_broadcast",
        service_id=SERVICE_ONE_ID,
        message_id=str(uuid.UUID(int=0)),
        _data={
            "reference": "Emergency broadcast",
            "content": "Broadcast content",
        },
    )

    assert not mock_create_broadcast_message.called
    assert mock_update_broadcast_message.called


@pytest.mark.parametrize(
    "expected_back_link_url, expected_back_link_extra_kwargs",
    [
        (".write_new_broadcast", {}),
    ],
)
def test_preview_areas_has_back_link_with_uuid(
    mocker,
    client_request,
    service_one,
    active_user_create_broadcasts_permission,
    expected_back_link_url,
    expected_back_link_extra_kwargs,
    mock_check_can_update_status,
    mock_get_count_of_phones,
    mock_get_areas_by_ids,
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=str(uuid.UUID(int=0)),
            service_id=SERVICE_ONE_ID,
            created_by_id=active_user_create_broadcasts_permission["id"],
            finishes_at=None,
            status="pending-approval",
        ),
    )
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        "main.preview_areas", service_id=SERVICE_ONE_ID, message_id=uuid.UUID(int=0), message_type="broadcast"
    )
    assert normalize_spaces(page.select_one("h1").text) == "Confirm the area for the alert"
    back_link = page.select_one(".govuk-back-link")
    assert back_link["href"] == url_for(
        expected_back_link_url,
        service_id=SERVICE_ONE_ID,
        message_id=str(uuid.UUID(int=0)),
        **expected_back_link_extra_kwargs,
    )


def test_write_new_broadcast_content_from_uuid_is_displayed_before_live(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    active_user_create_broadcasts_permission,
    mock_check_can_update_status,
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            reference="Emergency broadcast",
            content="Emergency broadcast content",
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
        ),
    )
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        "main.write_new_broadcast", service_id=SERVICE_ONE_ID, message_id=fake_uuid, follow_redirects=True
    )
    assert normalize_spaces(page.select_one("h1").text) == "Edit alert"
    assert normalize_spaces(page.select_one("textarea").text) == "Emergency broadcast content"


def test_write_new_broadcast_only_displays_from_this_service(
    mocker,
    client_request,
    service_one,
    service_two,
    active_user_create_broadcasts_permission,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        "main.write_new_broadcast",
        service_id=SERVICE_TWO_ID,
        broadcast_message_id=str(uuid.UUID(int=0)),
        _expected_status=403,
    )
    assert normalize_spaces(page.select_one("h1").text) == "You’re not allowed to see this page"


def test_write_new_broadcast_does_not_display_alerts_in_broadcast(
    mocker,
    client_request,
    service_one,
    mock_get_live_broadcast_message,
    fake_uuid,
    active_user_create_broadcasts_permission,
    mock_check_can_update_status,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get("main.write_new_broadcast", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid)
    assert normalize_spaces(page.select_one("input").text) == ""


def test_choose_sub_area_page_for_county_shows_links_for_districts(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    fake_uuid,
    active_user_create_broadcasts_permission,
    mock_check_grandparent,
    mock_get_libraries,
    mocker,
):
    mocker.patch(
        "app.areas_api_client.get_area",
        return_value={
            "id": "E10000016",
            "geographic_id": "E10000016",
            "name": "Kent",
            "parent": None,
            "geography_type": "local_authorities",
        },
    )
    mocker.patch(
        "app.areas_api_client.get_areas_for_parent",
        return_value=[
            {
                "id": "E07000105",
                "geographic_id": "E07000105",
                "name": "Ashford",
                "parent": "E10000016",
                "geography_type": "local_authorities",
            },
            {
                "id": "E07000106",
                "geographic_id": "E07000106",
                "name": "Canterbury",
                "parent": "E10000016",
                "geography_type": "local_authorities",
            },
            {
                "id": "E07000107",
                "geographic_id": "E07000107",
                "name": "Dartford",
                "parent": "E10000016",
                "geography_type": "local_authorities",
            },
            {
                "id": "E07000108",
                "geographic_id": "E07000108",
                "name": "Dover",
                "parent": "E10000016",
                "geography_type": "local_authorities",
            },
            {
                "id": "E07000109",
                "geographic_id": "E07000109",
                "name": "Gravesham",
                "parent": "E10000016",
                "geography_type": "local_authorities",
            },
            {
                "id": "E07000110",
                "geographic_id": "E07000110",
                "name": "Maidstone",
                "parent": "E10000016",
                "geography_type": "local_authorities",
            },
            {
                "id": "E07000111",
                "geographic_id": "E07000111",
                "name": "Sevenoaks",
                "parent": "E10000016",
                "geography_type": "local_authorities",
            },
            {
                "id": "E07000112",
                "geographic_id": "E07000112",
                "name": "Folkestone and Hythe",
                "parent": "E10000016",
                "geography_type": "local_authorities",
            },
            {
                "id": "E07000113",
                "geographic_id": "E07000113",
                "name": "Swale",
                "parent": "E10000016",
                "geography_type": "local_authorities",
            },
            {
                "id": "E07000114",
                "geographic_id": "E07000114",
                "name": "Thanet",
                "parent": "E10000016",
                "geography_type": "local_authorities",
            },
            {
                "id": "E07000115",
                "geographic_id": "E07000115",
                "name": "Tonbridge and Malling",
                "parent": "E10000016",
                "geography_type": "local_authorities",
            },
            {
                "id": "E07000116",
                "geographic_id": "E07000116",
                "name": "Tunbridge Wells",
                "parent": "E10000016",
                "geography_type": "local_authorities",
            },
        ],
    )
    service_one["permissions"] += ["broadcast"]

    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        "main.choose_sub_area",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        library_slug="local_authorities",
        area_slug="E10000016",  # Kent
        message_type="broadcast",
    )
    assert normalize_spaces(page.select_one("h1").text) == "Choose an area of Kent"
    live_search = page.select_one("[data-notify-module=live-search]")
    assert live_search["data-targets"] == ".file-list-item"
    assert live_search.select_one("input")["type"] == "search"
    all_choices_checkbox = [
        (
            choice.select_one("input")["value"],
            normalize_spaces(choice.select_one("label").text),
        )
        for choice in page.select("form[method=post] .govuk-checkboxes__item")
    ]
    districts = [
        (
            district["href"],
            district.text,
        )
        for district in page.select("form[method=post] a")
    ]
    assert all_choices_checkbox == [
        ("y", "All of Kent"),
    ]
    assert len(districts) == 12
    assert districts[0][0] == url_for(
        "main.choose_sub_area",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
        library_slug="local_authorities",
        area_slug="E07000105",
        prev_area_slug="E10000016",  # Kent
    )
    assert districts[0][1] == "Ashford"
    assert districts[-1][0] == url_for(
        "main.choose_sub_area",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        library_slug="local_authorities",
        area_slug="E07000116",
        prev_area_slug="E10000016",  # Kent
        message_type="broadcast",
    )
    assert districts[-1][1] == "Tunbridge Wells"


def test_add_broadcast_area(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
    mock_get_libraries,
    mock_add_areas,
):
    mocker.patch(
        "app.areas_api_client.get_areas_for_library",
        return_value=[
            {"id": "E92000001", "name": "England"},
            {"id": "N92000002", "name": "Northern Ireland"},
            {"id": "S92000003", "name": "Scotland"},
            {"id": "W92000004", "name": "Wales"},
        ],
    )
    service_one["permissions"] += ["broadcast"]
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            area_ids=["E92000001", "W92000004"],
            areas={
                "ids": ["E92000001", "W92000004"],
                "names": ["England", "Wales"],
                "simple_polygons": [],
            },
        ),
    )

    client_request.login(active_user_create_broadcasts_permission)
    client_request.post(
        ".choose_area",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
        library_slug="countries",
        _data={"areas": ["E92000001", "W92000004"]},
    )
    mock_add_areas.assert_called_once_with(
        fake_uuid, SERVICE_ONE_ID, ["E92000001", "W92000004"], "broadcast", "countries"
    )


def test_add_flood_warning_area(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
    mock_get_count_of_phones,
    mock_get_flood_warning_area_library,
    mock_add_areas,
):
    service_one["permissions"] += ["broadcast"]
    areas = [
        {
            "id": "011FWCN2M",
            "name": "Cumbria coast at Maryport harbour",
            "geography_type": "flood_warning_areas",
            "geographic_id": "011FWCN2M",
        }
    ]
    mocker.patch(
        "app.areas_api_client.get_areas_by_names",
        return_value=areas,
    )
    mocker.patch(
        "app.areas_api_client.get_areas_by_ids",
        return_value=areas,
    )
    # Initial GET request should have empty broadcast_message
    empty_broadcast_message = broadcast_message_json(
        id_=fake_uuid,
        template_id=fake_uuid,
        created_by_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        status="draft",
        area_ids=[],
        areas={
            "ids": [],
            "names": [],
            "simple_polygons": [],
        },
    )

    updated_broadcast_message = broadcast_message_json(
        id_=fake_uuid,
        template_id=fake_uuid,
        created_by_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        status="draft",
        area_ids=["011FWCN2M"],
        areas={
            "ids": ["011FWCN2M"],
            "names": ["Cumbria coast at Maryport harbour"],
            "aggregate_names": ["Cumbria coast at Maryport harbour"],
            "simple_polygons": [CUMBRIA_FLOOD_WARNING_AREA],
        },
    )

    mock_add_areas.return_value = updated_broadcast_message

    mock_get_broadcast_message = mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        side_effect=[
            empty_broadcast_message,
            updated_broadcast_message,
        ],
    )
    client_request.login(active_user_create_broadcasts_permission)

    page = client_request.get(
        ".search_flood_warning_areas",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
    )

    assert normalize_spaces(page.select_one("h1").text) == "Choose Flood Warning Target Areas (TA)"
    assert not page.select("ul.area-list li.area-list-item")

    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.post(
        ".search_flood_warning_areas",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
        _data={"flood_warning_area": "011FWCN2M", "add_area_button": ""},
        _follow_redirects=True,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Choose Flood Warning Target Areas (TA)"
    assert [normalize_spaces(item.text) for item in page.select("ul.area-list li.area-list-item")] == [
        "011FWCN2M: Cumbria coast at Maryport harbour Remove Cumbria coast at Maryport harbour"
    ]

    assert mock_get_broadcast_message.call_count == 2
    mock_add_areas.assert_called_once_with(
        fake_uuid,
        SERVICE_ONE_ID,
        ["011FWCN2M"],
        "broadcast",
        "flood_warning_areas",
    )


@pytest.mark.parametrize(
    "delimiter",
    ((","), ("\n")),
)
def test_add_flood_warning_areas_in_bulk_with_delimiters(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
    delimiter,
    mock_get_count_of_phones,
    mock_get_libraries,
    mock_get_flood_warning_area_library,
    mock_add_areas,
):
    service_one["permissions"] += ["broadcast"]

    client_request.login(active_user_create_broadcasts_permission)
    areas = [
        {
            "id": "011FWBWH",
            "name": "Whitehaven Sea Lock failure, town centre and North Shore Rd",
            "geography_type": "flood_warning_areas",
            "geographic_id": "011FWBWH",
        },
        {
            "id": "011FWCN1A",
            "name": (
                "Cumbrian coastline from Gretna to Silloth including Port Carlisle, " "Skinburness and Rockcliffe"
            ),
            "geography_type": "flood_warning_areas",
            "geographic_id": "011FWCN1A",
        },
        {
            "id": "011FWCN1B",
            "name": ("Cumbrian coastline from Gretna to Silloth, between Longtown and " "Skinburness"),
            "geography_type": "flood_warning_areas",
            "geographic_id": "011FWCN1B",
        },
    ]

    mocker.patch(
        "app.areas_api_client.get_areas_by_names",
        return_value=areas,
    )
    mocker.patch(
        "app.areas_api_client.get_areas_by_ids",
        return_value=areas,
    )

    # Initial GET request should have empty broadcast_message
    empty_broadcast_message = broadcast_message_json(
        id_=fake_uuid,
        template_id=fake_uuid,
        created_by_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        status="draft",
        area_ids=[],
        areas={
            "ids": [],
            "names": [],
            "simple_polygons": [],
        },
    )

    updated_broadcast_message = broadcast_message_json(
        id_=fake_uuid,
        template_id=fake_uuid,
        created_by_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        status="draft",
        area_ids=["011FWBWH", "011FWCN1A", "011FWCN1B"],
        areas={
            "ids": ["011FWBWH", "011FWCN1A", "011FWCN1B"],
            "names": [
                "Whitehaven Sea Lock failure, town centre and North Shore Rd",
                ("Cumbrian coastline from Gretna to Silloth including Port Carlisle, " "Skinburness and Rockcliffe"),
                ("Cumbrian coastline from Gretna to Silloth, between Longtown and " "Skinburness"),
            ],
            "simple_polygons": [],
        },
    )

    mock_get_broadcast_message = mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        side_effect=[
            empty_broadcast_message,
            empty_broadcast_message,
            updated_broadcast_message,  # Once areas added
        ],
    )

    page = client_request.get(
        ".search_flood_warning_areas_as_a_list",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
    )

    assert normalize_spaces(page.select_one("h1").text) == "Enter Flood Warning Target Areas (TA) as a list"

    areas = ["011FWBWH", "011FWCN1A", "011FWCN1B"]
    areas_as_string = delimiter.join(areas)

    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.post(
        ".search_flood_warning_areas_as_a_list",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
        _data={"areas": [areas_as_string]},
        _follow_redirects=True,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Choose Flood Warning Target Areas (TA)"
    assert [normalize_spaces(item.text) for item in page.select("ul.area-list li.area-list-item")] == [
        "011FWBWH: Whitehaven Sea Lock failure, town centre and North Shore Rd Remove Whitehaven "
        "Sea Lock failure, town centre and North Shore Rd",
        "011FWCN1A: Cumbrian coastline from Gretna to Silloth including Port Carlisle, Skinburness "
        "and Rockcliffe Remove Cumbrian coastline from Gretna to Silloth including Port Carlisle, "
        "Skinburness and Rockcliffe",
        (
            "011FWCN1B: Cumbrian coastline from Gretna to Silloth, between Longtown and Skinburness Remove "
            "Cumbrian coastline from Gretna to Silloth, between Longtown and Skinburness"
        ),
    ]

    assert mock_get_broadcast_message.call_count == 3
    assert mock_add_areas.called


def test_add_local_authority_areas_in_bulk_with_newline_delimiter(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
    mock_get_broadcast_message_versions,
    mock_check_can_update_status,
    mock_get_count_of_phones,
    mock_add_areas,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    areas = [
        {"id": "devon", "name": "Devon"},
        {"id": "isles_of_scilly", "name": "Isles of Scilly"},
    ]

    mocker.patch(
        "app.areas_api_client.get_areas_by_names",
        return_value=areas,
    )
    mocker.patch(
        "app.areas_api_client.get_areas_by_ids",
        return_value=areas,
    )

    # Initial GET request should have empty broadcast_message
    empty_broadcast_message = broadcast_message_json(
        id_=fake_uuid,
        template_id=fake_uuid,
        created_by_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        status="draft",
        area_ids=[],
        areas={
            "ids": [],
            "names": [],
            "simple_polygons": [],
        },
    )

    updated_broadcast_message = broadcast_message_json(
        id_=fake_uuid,
        template_id=fake_uuid,
        created_by_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        status="draft",
        area_ids=["devon", "isles_of_scilly"],
        areas={
            "ids": ["devon", "isles_of_scilly"],
            "names": ["Devon", "Isles of Scilly"],
            "simple_polygons": [],
        },
    )

    mock_get_broadcast_message = mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        side_effect=[
            empty_broadcast_message,
            empty_broadcast_message,
            updated_broadcast_message,  # Once areas added
        ],
    )

    page = client_request.get(
        ".search_local_authority_areas_as_a_list",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
    )

    assert normalize_spaces(page.select_one("h1").text) == "Enter local authorities as a list"

    page = client_request.post(
        ".search_local_authority_areas_as_a_list",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
        _data={"areas": "Devon\nIsles of Scilly"},
        _follow_redirects=True,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Confirm the area for the alert"
    assert [normalize_spaces(item.text) for item in page.select("ul.area-list li.area-list-item")] == [
        "Devon Remove Devon",
        "Isles of Scilly Remove Isles of Scilly",
    ]

    assert mock_get_broadcast_message.call_count == 3
    mock_add_areas.assert_called_once_with(fake_uuid, SERVICE_ONE_ID, areas, "broadcast", None)


def test_remove_flood_warning_area(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
    mock_get_count_of_phones,
    mock_get_flood_warning_area_library,
):
    area = {
        "id": "011FWCN2M",
        "name": "Cumbria coast at Maryport harbour",
        "geography_type": "flood_warning_areas",
        "geographic_id": "011FWCN2M",
    }

    mocker.patch(
        "app.areas_api_client.get_areas_by_ids",
        side_effect=[
            [area],  # Initial page render
            [],  # The area has been removed
        ],
    )

    service_one["permissions"] += ["broadcast"]
    broadcast_message_with_area = broadcast_message_json(
        id_=fake_uuid,
        template_id=fake_uuid,
        created_by_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        status="draft",
        area_ids=["011FWCN2M"],
        areas={
            "ids": ["011FWCN2M"],
            "names": ["Cumbria coast at Maryport harbour"],
            "aggregate_names": ["Cumbria coast at Maryport harbour"],
            "simple_polygons": [CUMBRIA_FLOOD_WARNING_AREA],
        },
    )
    broadcast_message_without_area = broadcast_message_json(
        id_=fake_uuid,
        template_id=fake_uuid,
        created_by_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        status="draft",
        area_ids=[],
        areas={
            "ids": [],
            "names": [],
            "aggregate_names": [],
            "simple_polygons": [],
        },
    )

    mock_get_broadcast_message = mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        side_effect=[
            broadcast_message_with_area,
            broadcast_message_without_area,
        ],
    )
    mock_remove_area = mocker.patch("app.areas_api_client.remove_area", return_value=broadcast_message_without_area)
    client_request.login(active_user_create_broadcasts_permission)

    page = client_request.get(
        ".search_flood_warning_areas",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
    )

    assert normalize_spaces(page.select_one("h1").text) == "Choose Flood Warning Target Areas (TA)"
    assert [normalize_spaces(item.text) for item in page.select("ul.area-list li.area-list-item")] == [
        "011FWCN2M: Cumbria coast at Maryport harbour Remove Cumbria coast at Maryport harbour"
    ]

    client_request.get(
        ".remove_area",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        area_slug="011FWCN2M",
        message_type="broadcast",
        _expected_redirect=url_for(
            ".choose_library", service_id=SERVICE_ONE_ID, message_id=fake_uuid, message_type="broadcast"
        ),  # Redirects to library page as the broadcast has no area
    )

    assert mock_get_broadcast_message.call_count == 2
    mock_remove_area.assert_called_once_with(fake_uuid, SERVICE_ONE_ID, "011FWCN2M", "broadcast")


def test_error_if_flood_warning_code_bulk_input_input_empty(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    active_user_create_broadcasts_permission,
    mock_add_areas,
    mock_get_libraries,
    mock_get_areas_by_ids,
    mock_get_count_of_phones,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)

    page = client_request.post(
        ".search_flood_warning_areas_as_a_list",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
        _data={"areas": []},
        _follow_redirects=True,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Enter Flood Warning Target Areas (TA) as a list"
    assert not page.select("ul.area-list li.area-list-item")
    assert normalize_spaces(page.select_one(".govuk-error-message").text) == "Error: This field is required"
    assert (
        normalize_spaces(page.select_one(".govuk-error-summary").text)
        == "There is a problem Enter at least 1 Flood Warning TA code"
    )
    assert not mock_add_areas.called


def test_error_if_flood_warning_code_bulk_input_invalid(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
    mock_get_flood_warning_area_library,
    mock_add_areas_returns_error_for_invalid_input,
    mock_get_libraries,
):
    mock_add_areas_returns_error_for_invalid_input.side_effect = type(
        "MockAreaError",
        (Exception,),
        {"message": "Flood Warning TA code not found"},
    )()
    service_one["permissions"] += ["broadcast"]
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            area_ids=[],
            areas={
                "ids": [],
                "names": [],
                "simple_polygons": [],
            },
        ),
    )
    client_request.login(active_user_create_broadcasts_permission)

    page = client_request.get(
        ".search_flood_warning_areas_as_a_list",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
    )

    assert normalize_spaces(page.select_one("h1").text) == "Enter Flood Warning Target Areas (TA) as a list"
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.post(
        ".search_flood_warning_areas_as_a_list",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
        _data={"areas": ["test"]},
        _follow_redirects=True,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Enter Flood Warning Target Areas (TA) as a list"
    assert not page.select("ul.area-list li.area-list-item")
    assert normalize_spaces(page.select_one(".govuk-error-message").text) == "Error: Flood Warning TA code not found"
    assert (
        normalize_spaces(page.select_one(".govuk-error-summary").text)
        == "There is a problem Flood Warning TA code not found"
    )


def test_error_if_local_authority_bulk_input_invalid(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
    mock_get_areas_by_names_returns_error_for_invalid_input,
    mock_add_areas,
):
    mock_get_areas_by_names_returns_error_for_invalid_input.side_effect = type(
        "MockAreaError",
        (Exception,),
        {"message": "Local authority 'test' not found'"},
    )()
    service_one["permissions"] += ["broadcast"]
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            area_ids=[],
            created_at="2020-02-20T10:20:20.000000",
            areas={
                "ids": [],
                "names": [],
                "simple_polygons": [],
            },
        ),
    )
    client_request.login(active_user_create_broadcasts_permission)

    page = client_request.get(
        ".search_local_authority_areas_as_a_list",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
    )

    assert normalize_spaces(page.select_one("h1").text) == "Enter local authorities as a list"

    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.post(
        ".search_local_authority_areas_as_a_list",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
        _data={"areas": ["test"]},
        _follow_redirects=True,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Enter local authorities as a list"
    assert not page.select("ul.area-list li.area-list-item")
    assert normalize_spaces(page.select_one(".govuk-error-message").text) == "Error: Local authority 'test' not found'"
    assert normalize_spaces(page.select_one(".govuk-error-summary").text) == (
        "There is a problem Local authority not found"
    )
    assert not mock_add_areas.called


def test_error_if_local_authority_input_empty(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
):
    service_one["permissions"] += ["broadcast"]
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            area_ids=[],
            areas={
                "ids": [],
                "names": [],
                "simple_polygons": [],
            },
        ),
    )
    client_request.login(active_user_create_broadcasts_permission)

    page = client_request.get(
        ".search_local_authority_areas_as_a_list",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
    )

    assert normalize_spaces(page.select_one("h1").text) == "Enter local authorities as a list"

    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.post(
        ".search_local_authority_areas_as_a_list",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
        _data={"areas": []},
        _follow_redirects=True,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Enter local authorities as a list"
    assert not page.select("ul.area-list li.area-list-item")
    assert normalize_spaces(page.select_one(".govuk-error-message").text) == "Error: This field is required"
    assert normalize_spaces(page.select_one(".govuk-error-summary").text) == (
        "There is a problem Enter at least 1 Local authority"
    )
    assert not mock_update_broadcast_message.called


@pytest.mark.parametrize(
    "post_data, update_broadcast_data",
    (
        (
            {"postcode": "BD1 1EE", "radius": "2", "radius_btn": True},
            {
                "areas": {
                    "ids": ["2km around the postcode BD1 1EE in Bradford"],
                    "names": ["2km around the postcode BD1 1EE in Bradford"],
                    "aggregate_names": ["2km around the postcode BD1 1EE in Bradford"],
                    "simple_polygons": [BD1_1EE_2],
                }
            },
        ),
        (
            {"postcode": "BD1 1EE", "radius": "3", "radius_btn": True},
            {
                "areas": {
                    "ids": ["3km around the postcode BD1 1EE in Bradford"],
                    "names": ["3km around the postcode BD1 1EE in Bradford"],
                    "aggregate_names": ["3km around the postcode BD1 1EE in Bradford"],
                    "simple_polygons": [BD1_1EE_3],
                }
            },
        ),
    ),
)
def test_create_postcode_area(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
    post_data,
    update_broadcast_data,
    mock_get_count_of_phones,
):
    service_one["permissions"] += ["broadcast"]
    mock_get_broadcast_message = mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            areas={
                "ids": ["1km around the postcode BD1 1EE in Bradford"],
                "simple_polygons": [BD1_1EE_2],
                "names": ["1km around the postcode BD1 1EE in Bradford"],
            },
        ),
    )

    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.post(
        ".search_postcodes",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        library_slug="postcodes",
        message_type="broadcast",
        _data=post_data,
        _follow_redirects=True,
    )

    form = page.select_one("form")
    postcode_value = form.select_one("#postcode")["value"]
    radius_value = form.select_one("#radius")["value"]
    assert normalize_spaces(form.select_one("button").text) == "Search for areas"
    assert postcode_value == post_data["postcode"]
    assert radius_value == post_data["radius"]
    assert mock_get_broadcast_message.call_count == 1


@pytest.mark.parametrize(
    "post_data, update_broadcast_data",
    (
        (
            {"postcode": "BD1 1EE", "radius": "2", "continue": True},
            {
                "areas": {
                    "ids": ["2km around the postcode BD1 1EE in Bradford"],
                    "names": ["2km around the postcode BD1 1EE in Bradford"],
                    "aggregate_names": ["2km around the postcode BD1 1EE in Bradford"],
                    "simple_polygons": [BD1_1EE_2],
                }
            },
        ),
        (
            {"postcode": "BD1 1EE", "radius": "3", "continue": True},
            {
                "areas": {
                    "ids": ["3km around the postcode BD1 1EE in Bradford"],
                    "names": ["3km around the postcode BD1 1EE in Bradford"],
                    "aggregate_names": ["3km around the postcode BD1 1EE in Bradford"],
                    "simple_polygons": [BD1_1EE_3],
                }
            },
        ),
    ),
)
def test_add_postcode_area_to_broadcast(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
    post_data,
    update_broadcast_data,
    mock_get_broadcast_message_versions,
    mock_create_postcode_area,
    mock_add_postcode_area,
    mock_get_postcode_centroid,
    mock_get_areas_by_ids,
    mock_get_latest_edit_reason,
    mock_get_broadcast_returned_for_edit_reasons,
):
    mocker.patch("app.broadcast_message_api_client.get_count_of_phones", return_value=1_000_000)
    service_one["permissions"] += ["broadcast"]
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            created_at="2020-02-20T10:20:20.000000",
            areas={
                "ids": ["1km around the postcode BD1 1EE in Bradford"],
                "simple_polygons": [BD1_1EE_1],
                "names": ["1km around the postcode BD1 1EE in Bradford"],
            },
        ),
    )

    client_request.login(active_user_create_broadcasts_permission)
    client_request.post(
        ".search_postcodes",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        library_slug="postcodes",
        message_type="broadcast",
        _data=post_data,
        _follow_redirects=True,
    )

    assert mock_create_postcode_area.called
    mock_add_postcode_area.assert_called_once_with(
        fake_uuid,
        SERVICE_ONE_ID,
        post_data["postcode"],
        float(post_data["radius"]),
        "broadcast",
    )


@pytest.mark.parametrize(
    "post_data, update_broadcast_data",
    (
        (
            {"first_coordinate": "54", "second_coordinate": "-1.7", "radius": "5", "radius_btn": True},
            {
                "areas": {
                    "ids": ["5km around 54.0 latitude, -1.7 longitude, in Harrogate"],
                    "names": ["5km around 54.0 latitude, -1.7 longitude, in Harrogate"],
                    "aggregate_names": ["5km around 54.0 latitude, -1.7 longitude, in Harrogate"],
                    "simple_polygons": [HG3_2RL],
                }
            },
        ),
        (
            {"first_coordinate": "53.793", "second_coordinate": "-1.75", "radius": "3", "radius_btn": True},
            {
                "areas": {
                    "ids": ["3km around 53.793 latitude, -1.75 longitude, in Bradford"],
                    "names": ["3km around 53.793 latitude, -1.75 longitude, in Bradford"],
                    "aggregate_names": ["3km around 53.793 latitude, -1.75 longitude, in Bradford"],
                    "simple_polygons": [BD1_1EE],
                }
            },
        ),
    ),
)
def test_create_latitude_longitude_coordinate_area(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
    post_data,
    update_broadcast_data,
    mock_check_coordinates_valid,
    mock_create_coordinate_area,
):
    mocker.patch("app.broadcast_message_api_client.get_count_of_phones", return_value=1_000_000)
    service_one["permissions"] += ["broadcast"]
    mock_get_broadcast_message = mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            areas={
                "ids": [],
                "simple_polygons": [],
                "names": [],
            },
        ),
    )
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.post(
        ".search_coordinates",
        message_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        coordinate_type="latitude_longitude",
        message_type="broadcast",
        _data=post_data,
        _follow_redirects=True,
    )

    form = page.select_one("form")
    first_coordinate = form.select_one("#first_coordinate")["value"]
    second_coordinate = form.select_one("#second_coordinate")["value"]
    radius_value = form.select_one("#radius")["value"]
    assert normalize_spaces(form.select_one("button").text) == "Search"
    assert first_coordinate == post_data["first_coordinate"]
    assert second_coordinate == post_data["second_coordinate"]
    assert radius_value == post_data["radius"]
    assert mock_get_broadcast_message.call_count == 1
    assert mock_create_coordinate_area.called


@pytest.mark.parametrize(
    "post_data, update_broadcast_data",
    (
        (
            {"first_coordinate": "54", "second_coordinate": "-1.7", "radius": "5", "continue": True},
            {
                "areas": {
                    "ids": ["5km around 54.0 latitude, -1.7 longitude in North Yorkshire"],
                    "names": ["5km around 54.0 latitude, -1.7 longitude in North Yorkshire"],
                    "aggregate_names": ["5km around 54.0 latitude, -1.7 longitude in North Yorkshire"],
                    "simple_polygons": [HG3_2RL],
                }
            },
        ),
        (
            {"first_coordinate": "53.793", "second_coordinate": "-1.75", "radius": "3", "continue": True},
            {
                "areas": {
                    "ids": ["3km around 53.793 latitude, -1.75 longitude in Bradford"],
                    "names": ["3km around 53.793 latitude, -1.75 longitude in Bradford"],
                    "aggregate_names": ["3km around 53.793 latitude, -1.75 longitude in Bradford"],
                    "simple_polygons": [BD1_1EE],
                }
            },
        ),
    ),
)
def test_add_latitude_longitude_coordinate_area_to_broadcast(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
    post_data,
    update_broadcast_data,
    mock_get_broadcast_message_versions,
    mock_check_coordinates_valid,
    mock_create_coordinate_area,
    mock_add_coordinate_area,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
):
    mocker.patch("app.broadcast_message_api_client.get_count_of_phones", return_value=1_000_000)
    service_one["permissions"] += ["broadcast"]
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            created_at="2020-02-20T10:20:20.000000",
            status="draft",
            areas={
                "ids": [],
                "simple_polygons": [],
                "names": [],
            },
        ),
    )
    client_request.login(active_user_create_broadcasts_permission)
    client_request.post(
        ".search_coordinates",
        message_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        coordinate_type="latitude_longitude",
        message_type="broadcast",
        _data=post_data,
        _follow_redirects=True,
    )

    mock_add_coordinate_area.assert_called_once_with(
        fake_uuid,
        SERVICE_ONE_ID,
        float(post_data["first_coordinate"]),
        float(post_data["second_coordinate"]),
        float(post_data["radius"]),
        "latitude_longitude",
        "broadcast",
    )


@pytest.mark.parametrize(
    "post_data, update_broadcast_data",
    (
        (
            {
                "first_coordinate": "419763",
                "second_coordinate": "456038",
                "radius": "5",
                "radius_btn": True,
            },
            {
                "areas": {
                    "ids": ["5km around the easting of 419763.0 and the northing of 456038.0 in North Yorkshire"],
                    "names": ["5km around the easting of 419763.0 and the northing of 456038.0 in North Yorkshire"],
                    "aggregate_names": [
                        "5km around the easting of 419763.0 and the northing of 456038.0 in North Yorkshire"
                    ],
                    "simple_polygons": [],
                }
            },
        ),
        (
            {"first_coordinate": "416567", "second_coordinate": "432994", "radius": "3", "radius_btn": True},
            {
                "areas": {
                    "ids": ["3km around the easting of 416567.0 and the northing of 432994.0 in Bradford"],
                    "names": ["3km around the easting of 416567.0 and the northing of 432994.0 in Bradford"],
                    "aggregate_names": ["3km around the easting of 416567.0 and the northing of 432994.0 in Bradford"],
                    "simple_polygons": [BD1_1EE],
                }
            },
        ),
    ),
)
def test_create_easting_northing_coordinate_area(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
    post_data,
    update_broadcast_data,
    mock_get_count_of_phones,
    mock_check_coordinates_valid,
    mock_create_coordinate_area,
):
    service_one["permissions"] += ["broadcast"]
    mock_get_broadcast_message = mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            areas={
                "ids": [],
                "simple_polygons": [],
                "names": [],
            },
        ),
    )

    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.post(
        ".search_coordinates",
        message_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        coordinate_type="easting_northing",
        message_type="broadcast",
        _data=post_data,
        _follow_redirects=True,
    )
    form = page.select_one("form")
    first_coordinate = form.select_one("#first_coordinate")["value"]
    second_coordinate = form.select_one("#second_coordinate")["value"]
    radius_value = form.select_one("#radius")["value"]
    assert normalize_spaces(form.select_one("button").text) == "Search"
    assert first_coordinate == post_data["first_coordinate"]
    assert second_coordinate == post_data["second_coordinate"]
    assert radius_value == post_data["radius"]
    assert mock_get_broadcast_message.call_count == 1


@pytest.mark.parametrize(
    "post_data, update_broadcast_data",
    (
        (
            {"first_coordinate": "419763", "second_coordinate": "456038", "radius": "5", "continue": True},
            {
                "areas": {
                    "ids": ["5km around the easting of 419763 and the northing of 456038 in North Yorkshire"],
                    "names": ["5km around the easting of 419763 and the northing of 456038 in North Yorkshire"],
                    "aggregate_names": [
                        "5km around the easting of 419763 and the northing of 456038 in North Yorkshire"
                    ],
                    "simple_polygons": [HG3_2RL],
                }
            },
        ),
        (
            {"first_coordinate": "416567", "second_coordinate": "432994", "radius": "3", "continue": True},
            {
                "areas": {
                    "ids": ["3km around the easting of 416567 and the northing of 432994 in Bradford"],
                    "names": ["3km around the easting of 416567 and the northing of 432994 in Bradford"],
                    "aggregate_names": ["3km around the easting of 416567 and the northing of 432994 in Bradford"],
                    "simple_polygons": [BD1_1EE],
                }
            },
        ),
    ),
)
def test_add_easting_northing_coordinate_area_to_broadcast(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
    post_data,
    update_broadcast_data,
    mock_get_broadcast_message_versions,
    mock_get_count_of_phones,
    mock_check_coordinates_valid,
    mock_create_coordinate_area,
    mock_add_coordinate_area,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
):
    service_one["permissions"] += ["broadcast"]
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            areas={
                "ids": [],
                "simple_polygons": [],
                "names": [],
            },
            created_at="2020-02-20T10:20:20.000000",
        ),
    )

    client_request.login(active_user_create_broadcasts_permission)
    client_request.post(
        ".search_coordinates",
        message_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        coordinate_type="easting_northing",
        message_type="broadcast",
        _data=post_data,
        _follow_redirects=True,
    )
    mock_add_coordinate_area.assert_called_once_with(
        fake_uuid,
        SERVICE_ONE_ID,
        float(post_data["first_coordinate"]),
        float(post_data["second_coordinate"]),
        float(post_data["radius"]),
        "easting_northing",
        "broadcast",
    )


@pytest.mark.parametrize(
    "post_data, expected_errors",
    (
        (
            {"postcode": "RG12 8SP", "radius": "5", "radius_btn": True},
            ["Enter a postcode within the UK"],
        ),
        (
            {"postcode": "BD1 1EP", "radius": "1", "radius_btn": True},
            ["Enter a postcode within the UK"],
        ),
    ),
)
def test_valid_format_postcode_not_in_db_form_error(
    client_request,
    service_one,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
    post_data,
    expected_errors,
    mock_update_broadcast_message,
):
    service_one["permissions"] += ["broadcast"]
    mock_get_broadcast_message = mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            areas={
                "ids": [],
                "simple_polygons": [],
                "names": [],
            },
        ),
    )

    client_request.login(active_user_create_broadcasts_permission)

    page = client_request.post(
        ".search_postcodes",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        library_slug="postcodes",
        message_type="broadcast",
        _data=post_data,
        _follow_redirects=True,
    )
    form = page.select_one("form")
    error_list = [
        normalize_spaces([error])
        for error in page.select(".govuk-error-summary__list a")
        if normalize_spaces([error]) != ""
    ]
    assert error_list == expected_errors
    assert normalize_spaces(form.select_one("button").text) == "Search for areas"
    assert mock_get_broadcast_message.call_count == 1


@pytest.mark.parametrize(
    "post_data, expected_area_ids",
    (
        (
            {"select_all": "y", "areas": ["S13002845"]},
            # The selected district is ignored is ignored because the user chose ‘Select all…’
            ["S12000033"],
        ),
        (
            {"areas": ["S13002845", "S13002836"]},
            ["S13002845", "S13002836"],
        ),
    ),
)
def test_add_broadcast_sub_area_district_view(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_add_areas,
    fake_uuid,
    post_data,
    expected_area_ids,
    active_user_create_broadcasts_permission,
    mock_get_area,
    mock_check_grandparent,
    mocker,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    mocker.patch(
        "app.areas_api_client.get_area",
        return_value={
            "id": "S12000033",
            "name": "Aberdeen City",
        },
    )
    mocker.patch(
        "app.areas_api_client.get_areas_for_parent",
        # child areas of Aberdeen City
        return_value=[
            {
                "id": "S13002845",
                "name": "Airyhall/Broomhill/Garthdee",
            },
            {
                "id": "S13002836",
                "name": "Bridge of Don",
            },
        ],
    )
    client_request.post(
        ".choose_sub_area",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        library_slug="local_authorities",
        area_slug="E10000016",
        message_type="broadcast",
        _data=post_data,
        _expected_redirect=url_for(
            ".preview_areas",
            service_id=SERVICE_ONE_ID,
            message_id=fake_uuid,
            message_type="broadcast",
        ),
    )

    mock_add_areas.assert_called_once_with(
        fake_uuid,
        SERVICE_ONE_ID,
        expected_area_ids,
        "broadcast",
        None,
    )


def test_add_broadcast_sub_area_county_view(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    fake_uuid,
    active_user_create_broadcasts_permission,
    mock_add_areas,
    mock_get_areas_for_parent,
    mock_check_grandparent,
    mocker,
):
    service_one["permissions"] += ["broadcast"]
    mocker.patch(
        "app.areas_api_client.get_area",
        return_value={"id": "E10000016", "name": "Kent"},
    )
    mock_add_areas.return_value = broadcast_message_json(
        id_=fake_uuid,
        template_id=fake_uuid,
        created_by_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        status="draft",
        areas={
            "ids": ["E92000001", "S92000003"],
            "names": ["England", "Scotland"],
            "aggregate_names": ["England", "Scotland"],
            "simple_polygons": [],
        },
    )

    client_request.login(active_user_create_broadcasts_permission)
    client_request.post(
        ".choose_sub_area",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        library_slug="local_authorities",
        area_slug="E10000016",
        message_type="broadcast",
        _data={"select_all": "y"},
    )

    mock_add_areas.assert_called_once_with(fake_uuid, SERVICE_ONE_ID, ["E10000016"], "broadcast", None)


def test_remove_area_page(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    fake_uuid,
    active_user_create_broadcasts_permission,
    mock_remove_area,
    mock_get_areas_by_ids,
):
    service_one["permissions"] += ["broadcast"]

    mock_remove_area.return_value = broadcast_message_json(
        id_=fake_uuid,
        template_id=fake_uuid,
        created_by_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        status="draft",
        areas={
            "ids": ["E92000001"],
            "names": ["England"],
            "aggregate_names": ["England"],
            "simple_polygons": [MULTIPLE_ENGLAND],
        },
    )

    client_request.login(active_user_create_broadcasts_permission)
    client_request.get(
        ".remove_area",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        area_slug="E92000001",
        message_type="broadcast",
        _expected_redirect=url_for(
            ".preview_areas",
            service_id=SERVICE_ONE_ID,
            message_id=fake_uuid,
            message_type="broadcast",
        ),
    )

    mock_remove_area.assert_called_once_with(
        fake_uuid,
        SERVICE_ONE_ID,
        "E92000001",
        "broadcast",
    )


def test_remove_postcode_area(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
    mock_remove_area,
):
    service_one["permissions"] += ["broadcast"]
    mock_get_broadcast_message = mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            areas={
                "ids": ["1km around the postcode BD1 1EE in Bradford"],
                "names": ["BDE 1EE-1"],
                "simple_polygons": [BD1_1EE_1],
            },
        ),
    )

    client_request.login(active_user_create_broadcasts_permission)
    client_request.get(
        ".remove_area",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        message_type="broadcast",
        area_slug="1km around the postcode BD1 1EE in Bradford",
        _expected_redirect=url_for(
            ".choose_library", service_id=SERVICE_ONE_ID, message_id=fake_uuid, message_type="broadcast"
        ),
    )
    mock_get_broadcast_message.assert_called_once_with(service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid)
    mock_remove_area.assert_called_once_with(
        fake_uuid,
        SERVICE_ONE_ID,
        "1km around the postcode BD1 1EE in Bradford",
        "broadcast",
    )


def test_remove_coordinate_area(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
    mock_remove_area,
):
    service_one["permissions"] += ["broadcast"]
    mock_get_broadcast_message = mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            areas={
                "ids": ["5km around 54.0 latitude, -1.7 longitude, in Harrogate"],
                "names": ["5km around 54.0 latitude, -1.7 longitude, in Harrogate"],
                "aggregate_names": ["5km around 54.0 latitude, -1.7 longitude, in Harrogate"],
                "simple_polygons": [HG3_2RL],
            },
        ),
    )

    client_request.login(active_user_create_broadcasts_permission)
    client_request.get(
        ".remove_area",
        service_id=SERVICE_ONE_ID,
        message_id=fake_uuid,
        area_slug="5km around 54.0 latitude, -1.7 longitude, in Harrogate",
        message_type="broadcast",
        _expected_redirect=url_for(
            ".choose_library", service_id=SERVICE_ONE_ID, message_id=fake_uuid, message_type="broadcast"
        ),
    )
    mock_get_broadcast_message.assert_called_once_with(service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid)
    mock_remove_area.assert_called_once_with(
        fake_uuid,
        SERVICE_ONE_ID,
        "5km around 54.0 latitude, -1.7 longitude, in Harrogate",
        "broadcast",
    )


def test_choose_broadcast_duration_page(
    client_request,
    service_one,
    active_user_create_broadcasts_permission,
    mock_get_draft_broadcast_message,
    fake_uuid,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        ".choose_broadcast_duration",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Alert Duration"

    form = page.select_one("form")
    assert form["method"] == "post"
    assert "action" not in form

    assert form.select("input#hours") is not None
    assert form.select("input#minutes") is not None


def test_choose_broadcast_duration(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    active_user_create_broadcasts_permission,
):
    service_one["permissions"] += ["broadcast"]

    client_request.login(active_user_create_broadcasts_permission)
    client_request.post(
        ".choose_broadcast_duration",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _data={"duration": "PT30M"},
        _expected_status=200,
    )


def test_preview_broadcast_message_page(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    fake_uuid,
    active_user_create_broadcasts_permission,
    mock_get_broadcast_message_versions,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mocker,
):
    mocker.patch(
        "app.areas_api_client.get_areas_by_ids",
        return_value=[
            {
                "id": "england",
                "name": "England",
            },
            {
                "id": "scotland",
                "name": "Scotland",
            },
        ],
    )
    mocker.patch("app.broadcast_message_api_client.get_count_of_phones", return_value=46909327.34961163)
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        ".preview_broadcast_message",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )

    assert [normalize_spaces(area.text) for area in page.select(".area-list-item.area-list-item--unremoveable")] == [
        "England",
        "Scotland",
    ]

    assert normalize_spaces(page.select_one("p.duration-preview").text) == "22 hours, 30 minutes"

    assert normalize_spaces(page.select_one("h2.broadcast-message-heading").text) == "Emergency alert"

    assert normalize_spaces(page.select_one(".broadcast-message-wrapper").text) == "Emergency alert This is a test"

    assert [normalize_spaces(p.text) for p in page.select(".govuk-summary-list__key")] == [
        "Reference",
        "Alert message",
        "Additional Information",
        "Area",
        "Alert duration",
        "Phone estimate",
        "Downloads",
    ]
    assert [normalize_spaces(p.text) for p in page.select(".govuk-summary-list__value")] == [
        "Example template",
        "Emergency alert This is a test",
        "",
        "England Scotland Use the arrow keys to move the map. "
        + "Use the buttons to zoom the map in or out View larger map",
        "22 hours, 30 minutes",
        "More than 1 million phones estimated",
        "Download geoJSON Download CAP XML Download IBAG XML",
    ]

    form = page.select_one("form")
    assert form["method"] == "post"
    assert "action" not in form


def test_start_broadcasting(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message_status,
    fake_uuid,
    active_user_create_broadcasts_permission,
    mock_check_can_update_status,
    mock_get_areas_by_ids,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    client_request.post(
        ".preview_broadcast_message",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _expected_redirect=url_for(
            "main.view_current_broadcast",
            service_id=SERVICE_ONE_ID,
            broadcast_message_id=fake_uuid,
        ),
    )
    mock_update_broadcast_message_status.assert_called_once_with(
        "pending-approval",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )


@pytest.mark.parametrize(
    "endpoint, created_by_api, extra_fields, mock_get_broadcast_message_provider_statuses, "
    + "operator_statuses_text, expected_paragraphs",
    (
        (
            ".view_current_broadcast",
            False,
            {
                "status": "broadcasting",
                "finishes_at": "2020-02-23T23:23:23.000000",
                "created_by": "Alice",
                "approved_by": "Bob",
            },
            sending_success_statuses,
            "Operator Statuses Operator Alert Status EE Sent today at 11:23:23pm O2 Three Vodafone",
            [
                "live since 20 February at 8:20pm Stop sending",
                "More than 1 million phones estimated",
                "Broadcasting stops tomorrow at 11:23:23pm.",
                "Created by Alice on 20 February at 10:20:20am.",
                "Submitted by Test User 2 on 20 February at 8:20:20pm.",
                "Returned by Test User on 20 February at 8:25:20pm.",
                "Submitted by Test User 2 on 20 February at 9:00:00pm.",
                "Approved by Bob on 20 February at 9:00:00pm.",
            ],
        ),
        (
            ".view_current_broadcast",
            False,
            {
                "status": "broadcasting",
                "finishes_at": "2020-02-23T23:23:23.000000",
                "created_by": "Alice",
                "approved_by": "Bob",
            },
            sending_failure_statuses,
            "Operator Statuses Operator Alert Status EE Sending, last attempted today at 11:23:23pm O2 Three Vodafone",
            [
                "sending error live since 20 February at 8:20pm Stop sending",
                "More than 1 million phones estimated",
                "Broadcasting stops tomorrow at 11:23:23pm.",
                "Created by Alice on 20 February at 10:20:20am.",
                "Submitted by Test User 2 on 20 February at 8:20:20pm.",
                "Returned by Test User on 20 February at 8:25:20pm.",
                "Submitted by Test User 2 on 20 February at 9:00:00pm.",
                "Approved by Bob on 20 February at 9:00:00pm.",
            ],
        ),
        (
            ".view_current_broadcast",
            True,
            {"status": "broadcasting", "finishes_at": "2020-02-23T23:23:23.000000", "approved_by": "Alice"},
            sending_success_statuses,
            "Operator Statuses Operator Alert Status EE Sent today at 11:23:23pm O2 Three Vodafone",
            [
                "live since 20 February at 8:20pm Stop sending",
                "More than 1 million phones estimated",
                "Broadcasting stops tomorrow at 11:23:23pm.",
                "Created from an API call on 20 February at 10:20:20am.",
                "Submitted by Test User 2 on 20 February at 8:20:20pm.",
                "Returned by Test User on 20 February at 8:25:20pm.",
                "Submitted by Test User 2 on 20 February at 9:00:00pm.",
                "Approved by Alice on 20 February at 9:00:00pm.",
            ],
        ),
        (
            ".view_previous_broadcast",
            False,
            {
                "status": "broadcasting",
                "finishes_at": "2020-02-22T22:20:20.000000",  # 2 mins before now()
                "created_by": "Alice",
                "approved_by": "Bob",
            },
            sending_success_statuses,
            "Operator Statuses Operator Alert Status EE Sent today at 11:23:23pm O2 Three Vodafone",
            [
                "Sent on 20 February at 8:20:20pm.",
                "More than 1 million phones estimated",
                "Created by Alice on 20 February at 10:20:20am.",
                "Submitted by Test User 2 on 20 February at 8:20:20pm.",
                "Returned by Test User on 20 February at 8:25:20pm.",
                "Submitted by Test User 2 on 20 February at 9:00:00pm.",
                "Approved by Bob on 20 February at 9:00:00pm.",
                "Finished broadcasting today at 10:20:20pm.",
            ],
        ),
        (
            ".view_previous_broadcast",
            False,
            {
                "status": "broadcasting",
                "finishes_at": "2020-02-22T22:20:20.000000",  # 2 mins before now()
                "created_by": "Alice",
                "approved_by": "Bob",
            },
            sending_failure_statuses,
            "Operator Statuses Operator Alert Status EE Sending, last attempted today at 11:23:23pm O2 Three Vodafone",
            [
                "sending error Sent on 20 February at 8:20:20pm.",
                "More than 1 million phones estimated",
                "Created by Alice on 20 February at 10:20:20am.",
                "Submitted by Test User 2 on 20 February at 8:20:20pm.",
                "Returned by Test User on 20 February at 8:25:20pm.",
                "Submitted by Test User 2 on 20 February at 9:00:00pm.",
                "Approved by Bob on 20 February at 9:00:00pm.",
                "Finished broadcasting today at 10:20:20pm.",
            ],
        ),
        (
            ".view_previous_broadcast",
            True,
            {
                "status": "broadcasting",
                "finishes_at": "2020-02-22T22:20:20.000000",  # 2 mins before now()
                "approved_by": "Alice",
            },
            sending_success_statuses,
            "Operator Statuses Operator Alert Status EE Sent today at 11:23:23pm O2 Three Vodafone",
            [
                "Sent on 20 February at 8:20:20pm.",
                "More than 1 million phones estimated",
                "Created from an API call on 20 February at 10:20:20am.",
                "Submitted by Test User 2 on 20 February at 8:20:20pm.",
                "Returned by Test User on 20 February at 8:25:20pm.",
                "Submitted by Test User 2 on 20 February at 9:00:00pm.",
                "Approved by Alice on 20 February at 9:00:00pm.",
                "Finished broadcasting today at 10:20:20pm.",
            ],
        ),
        (
            ".view_previous_broadcast",
            False,
            {
                "status": "completed",
                "finishes_at": "2020-02-21T21:21:21.000000",
                "created_by": "Alice",
                "approved_by": "Bob",
            },
            sending_success_statuses,
            "Operator Statuses Operator Alert Status EE Sent today at 11:23:23pm O2 Three Vodafone",
            [
                "Sent on 20 February at 8:20:20pm.",
                "More than 1 million phones estimated",
                "Created by Alice on 20 February at 10:20:20am.",
                "Submitted by Test User 2 on 20 February at 8:20:20pm.",
                "Returned by Test User on 20 February at 8:25:20pm.",
                "Submitted by Test User 2 on 20 February at 9:00:00pm.",
                "Approved by Bob on 20 February at 9:00:00pm.",
                "Finished broadcasting yesterday at 9:21:21pm.",
            ],
        ),
        (
            ".view_previous_broadcast",
            False,
            {
                "status": "cancelled",
                "cancelled_by_id": sample_uuid,
                "cancelled_at": "2020-02-21T21:21:21.000000",
                "created_by": "Alice",
                "approved_by": "Bob",
                "cancelled_by": "Carol",
            },
            sending_success_cancelled_statuses,
            "Operator Statuses Operator Alert Status Cancellation Status EE Sent today at 11:23:23pm "
            + "Sent today at 11:24:24pm O2 Three Vodafone",
            [
                "Sent on 20 February at 8:20:20pm.",
                "More than 1 million phones estimated",
                "Created by Alice on 20 February at 10:20:20am.",
                "Submitted by Test User 2 on 20 February at 8:20:20pm.",
                "Returned by Test User on 20 February at 8:25:20pm.",
                "Submitted by Test User 2 on 20 February at 9:00:00pm.",
                "Approved by Bob on 20 February at 9:00:00pm.",
                "Stopped by Carol yesterday at 9:21:21pm.",
            ],
        ),
        (
            ".view_previous_broadcast",
            False,
            {
                "status": "cancelled",
                "cancelled_at": "2020-02-21T21:21:21.000000",
                "created_by": "Alice",
                "approved_by": "Bob",
                "cancelled_by_id": None,
            },
            sending_success_cancelled_statuses,
            "Operator Statuses Operator Alert Status Cancellation Status EE Sent today at 11:23:23pm "
            + "Sent today at 11:24:24pm O2 Three Vodafone",
            [
                "Sent on 20 February at 8:20:20pm.",
                "More than 1 million phones estimated",
                "Created by Alice on 20 February at 10:20:20am.",
                "Submitted by Test User 2 on 20 February at 8:20:20pm.",
                "Returned by Test User on 20 February at 8:25:20pm.",
                "Submitted by Test User 2 on 20 February at 9:00:00pm.",
                "Approved by Bob on 20 February at 9:00:00pm.",
                "Stopped by an API call yesterday at 9:21:21pm.",
            ],
        ),
    ),
    indirect=["mock_get_broadcast_message_provider_statuses"],
)
@freeze_time("2020-02-22T22:22:22.000000")
def test_view_broadcast_message_page(
    mocker,
    client_request,
    service_one,
    active_user_view_permissions,
    fake_uuid,
    endpoint,
    created_by_api,
    extra_fields,
    expected_paragraphs,
    mock_get_broadcast_message_versions,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
    operator_statuses_text,
    mock_get_areas_by_ids,
):
    mocker.patch("app.broadcast_message_api_client.get_count_of_phones", return_value=1_000_000)
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=None if created_by_api else fake_uuid,
            approved_by_id=fake_uuid,
            starts_at="2020-02-20T20:20:20.000000",
            created_at="2020-02-20T10:20:20.000000",
            submitted_at="2020-02-20T21:00:00.000000",
            approved_at="2020-02-20T21:00:00.000000",
            submitted_by="Test User 2",
            **extra_fields,
        ),
    )
    service_one["permissions"] += ["broadcast"]

    client_request.login(active_user_view_permissions)

    page = client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )

    assert [normalize_spaces(p.text) for p in page.select("main p.govuk-body")] == expected_paragraphs

    assert normalize_spaces(page.select("table")[0].text) == operator_statuses_text


@pytest.mark.parametrize(
    "endpoint, created_by_api, extra_fields, expected_paragraphs",
    (
        (
            ".view_rejected_broadcast",
            False,
            {
                "status": "rejected",
                "created_at": "2020-02-20T19:20:20.000000",
                "updated_at": "2020-02-20T20:40:20.000000",
                "submitted_at": "2020-02-21T21:21:21.000000",
                "rejected_at": "2020-02-21T21:21:21.000000",
                "submitted_by": "Test User 3",
            },
            [
                "Rejected yesterday at 9:21:21pm by Carol.",
                "More than 1 million phones estimated",
                "Created by Alice on 20 February at 7:20:20pm.",
                "Submitted by Test User 2 on 20 February at 8:20:20pm.",
                "Returned by Test User on 20 February at 8:25:20pm.",
                "Submitted by Test User 3 on 21 February at 9:21:21pm.",
                "Rejected by Carol on 21 February at 9:21:21pm.",
            ],
        ),
    ),
)
@freeze_time("2020-02-22T22:22:22.000000")
def test_view_rejected_broadcast_message_page(
    mocker,
    client_request,
    service_one,
    active_user_view_permissions,
    fake_uuid,
    endpoint,
    created_by_api,
    extra_fields,
    expected_paragraphs,
    mock_get_broadcast_message_versions,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_areas_by_ids,
):
    mocker.patch("app.broadcast_message_api_client.get_count_of_phones", return_value=1_000_000)
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=None if created_by_api else fake_uuid,
            approved_by_id=fake_uuid,
            created_by="Alice",
            rejected_by="Carol",
            starts_at="2020-02-20T20:20:20.000000",
            **extra_fields,
        ),
    )
    service_one["permissions"] += ["broadcast"]

    client_request.login(active_user_view_permissions)

    mocker.patch(
        "app.user_api_client.get_user",
        side_effect=[
            user_json(name="Alice"),
            user_json(name="Bob"),
            user_json(name="Carol"),
        ],
    )

    page = client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )

    assert [normalize_spaces(p.text) for p in page.select("main p.govuk-body")] == expected_paragraphs
    assert not page.select("table")  # No operator statuses table


@pytest.mark.parametrize(
    "endpoint",
    (
        ".view_current_broadcast",
        ".view_previous_broadcast",
        ".view_rejected_broadcast",
    ),
)
@pytest.mark.parametrize(
    "status, expected_highlighted_navigation_item, expected_back_link_endpoint",
    (
        (
            "pending-approval",
            "Current alerts",
            ".broadcast_dashboard",
        ),
        (
            "broadcasting",
            "Current alerts",
            ".broadcast_dashboard",
        ),
        (
            "completed",
            "Past alerts",
            ".broadcast_dashboard_previous",
        ),
        (
            "cancelled",
            "Past alerts",
            ".broadcast_dashboard_previous",
        ),
        (
            "rejected",
            "Rejected alerts",
            ".broadcast_dashboard_rejected",
        ),
    ),
)
@freeze_time("2020-02-22T22:22:22.000000")
def test_view_broadcast_message_shows_correct_highlighted_navigation(
    mocker,
    client_request,
    service_one,
    active_user_approve_broadcasts_permission,
    fake_uuid,
    endpoint,
    status,
    expected_highlighted_navigation_item,
    expected_back_link_endpoint,
    mock_get_broadcast_message_versions,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
    mock_get_areas_by_ids,
):
    mocker.patch("app.broadcast_message_api_client.get_count_of_phones", return_value=1_000_000)
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            approved_by_id=fake_uuid,
            starts_at="2020-02-20T20:20:20.000000",
            approved_at="2020-02-20T21:00:00.000000",
            finishes_at="2021-12-21T21:21:21.000000",
            cancelled_at="2021-01-01T01:01:01.000000",
            rejected_at="2021-01-01T01:01:01.000000",
            created_at="2021-01-01T00:01:01.000000",
            status=status,
        ),
    )
    service_one["permissions"] += ["broadcast"]

    client_request.login(active_user_approve_broadcasts_permission)
    page = client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _follow_redirects=True,
        _test_page_title=False,
    )

    assert normalize_spaces(page.select_one(".navigation .selected").text) == (expected_highlighted_navigation_item)

    assert page.select_one(".govuk-back-link")["href"] == url_for(
        expected_back_link_endpoint,
        service_id=SERVICE_ONE_ID,
    )


def test_view_pending_broadcast(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    active_user_approve_broadcasts_permission,
    mock_get_broadcast_message_versions,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_count_of_phones,
    mock_get_areas_by_ids,
):
    broadcast_creator = create_active_user_create_broadcasts_permissions(with_unique_id=True)
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=broadcast_creator["id"],
            created_by="Test User Create Broadcasts Permission",
            finishes_at=None,
            status="pending-approval",
            created_at="2021-01-01T00:01:01.000000",
        ),
    )
    client_request.login(active_user_approve_broadcasts_permission)
    mocker.patch(
        "app.user_api_client.get_user",
        return_value=broadcast_creator,
    )
    service_one["permissions"] += ["broadcast"]

    page = client_request.get(
        ".view_current_broadcast",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _test_page_title=False,
    )

    assert (normalize_spaces(page.select_one(".banner").text)) == (
        "Test User Create Broadcasts Permission wants to broadcast Example template "
        "No phones will get this alert. "
        "Start broadcasting now "
        "Return this alert for edit "
        "Give a reason for returning the alert to draft "
        "Provide details of why you're returning the alert to draft, including how it can be improved. "
        'For example, "The alert message has spelling mistakes". '
        "Return alert for edit "
        "Reject this alert "
        "Give a reason for rejecting the alert "
        "Provide details of why you are rejecting the alert. "
        'For example, "The emergency has passed". '
        "Reject alert"
    )
    assert not page.select(".banner input[type=checkbox]")
    assert not page.select("table")  # No operator statuses table

    approval_form = page.select_one("form#approve")
    assert approval_form["method"] == "post"
    assert "action" not in approval_form
    assert approval_form.select_one("button")

    rejection_form = page.select_one("form#reject")
    button = rejection_form.select_one("button.govuk-button.govuk-button--warning")
    assert normalize_spaces(button.text) == "Reject alert"


@pytest.mark.parametrize(
    "extra_broadcast_json_fields, expected_banner_text",
    (
        (
            {"reference": "ABC123"},
            (
                "Test User Create Broadcasts Permission wants to broadcast ABC123 "
                "No phones will get this alert. "
                "Start broadcasting now "
                "Return this alert for edit "
                "Give a reason for returning the alert to draft "
                "Provide details of why you're returning the alert to draft, including how it can be improved. "
                'For example, "The alert message has spelling mistakes". '
                "Return alert for edit "
                "Reject this alert "
                "Give a reason for rejecting the alert "
                "Provide details of why you are rejecting the alert. "
                'For example, "The emergency has passed". '
                "Reject alert"
            ),
        ),
        (
            {"cap_event": "Severe flood warning", "reference": "ABC123"},
            (
                "Test User Create Broadcasts Permission wants to broadcast Severe flood warning "
                "No phones will get this alert. "
                "Start broadcasting now "
                "Return this alert for edit "
                "Give a reason for returning the alert to draft "
                "Provide details of why you're returning the alert to draft, including how it can be improved. "
                'For example, "The alert message has spelling mistakes". '
                "Return alert for edit "
                "Reject this alert "
                "Give a reason for rejecting the alert "
                "Provide details of why you are rejecting the alert. "
                'For example, "The emergency has passed". '
                "Reject alert"
            ),
        ),
    ),
)
def test_view_pending_broadcast_without_template(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    active_user_approve_broadcasts_permission,
    extra_broadcast_json_fields,
    expected_banner_text,
    mock_get_broadcast_message_versions,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
    mock_get_count_of_phones,
    mock_get_areas_by_ids,
):
    broadcast_creator = create_active_user_create_broadcasts_permissions(with_unique_id=True)
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=None,
            created_by_id=broadcast_creator["id"],
            created_by="Test User Create Broadcasts Permission",
            finishes_at=None,
            status="pending-approval",
            content="Uh-oh",
            created_at="2020-02-23T20:23:23.000000",
            **extra_broadcast_json_fields,
        ),
    )
    client_request.login(active_user_approve_broadcasts_permission)
    mocker.patch(
        "app.user_api_client.get_user",
        return_value=broadcast_creator,
    )
    service_one["permissions"] += ["broadcast"]

    page = client_request.get(
        ".view_current_broadcast",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _test_page_title=False,
    )

    assert (normalize_spaces(page.select_one(".banner").text)) == expected_banner_text

    assert (normalize_spaces(page.select_one(".broadcast-message-wrapper").text)) == "Emergency alert Uh-oh"


def test_view_pending_broadcast_from_api_call(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    active_user_approve_broadcasts_permission,
    mock_get_broadcast_message_versions,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
    mock_get_count_of_phones,
    mock_get_areas_by_ids,
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=None,
            created_by_id=None,  # No user created this broadcast
            finishes_at=None,
            status="pending-approval",
            reference="abc123",
            content="Uh-oh",
            created_at="2020-02-23T20:23:23.000000",
        ),
    )
    service_one["permissions"] += ["broadcast"]

    client_request.login(active_user_approve_broadcasts_permission)
    page = client_request.get(
        ".view_current_broadcast",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _test_page_title=False,
    )

    assert (normalize_spaces(page.select_one(".banner").text)) == (
        "An API call wants to broadcast abc123 No phones will get this alert. "
        "Start broadcasting now "
        "Return this alert for edit "
        "Give a reason for returning the alert to draft "
        "Provide details of why you're returning the alert to draft, including how it can be improved. "
        'For example, "The alert message has spelling mistakes". '
        "Return alert for edit "
        "Reject this alert "
        "Give a reason for rejecting the alert "
        "Provide details of why you are rejecting the alert. "
        'For example, "The emergency has passed". '
        "Reject alert"
    )
    assert (normalize_spaces(page.select_one(".broadcast-message-wrapper").text)) == "Emergency alert Uh-oh"


@pytest.mark.parametrize(
    "channel, expected_label_text",
    (
        ("test", "I understand this will alert anyone who has switched on the test channel"),
        ("operator", "I understand this will alert anyone who has switched on the operator channel"),
        ("severe", "I understand this will alert millions of people"),
        ("government", "I understand this will alert millions of people, even if they’ve opted out"),
    ),
)
def test_checkbox_to_confirm_non_training_broadcasts(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    active_user_approve_broadcasts_permission,
    channel,
    expected_label_text,
    mock_get_broadcast_message_versions,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
    mock_get_areas_by_ids,
):
    mocker.patch("app.broadcast_message_api_client.get_count_of_phones", return_value=1_000_000)
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=None,
            created_by_id=None,
            status="pending-approval",
            created_at="2020-02-23T20:23:23.000000",
        ),
    )
    service_one["permissions"] += ["broadcast"]
    service_one["restricted"] = False
    service_one["allowed_broadcast_provider"] = "all"
    service_one["broadcast_channel"] = channel

    client_request.login(active_user_approve_broadcasts_permission)
    page = client_request.get(
        ".view_current_broadcast",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _test_page_title=False,
    )

    label = page.select_one("form#approve label")
    assert label["for"] == "confirm"
    assert (normalize_spaces(label.text)) == expected_label_text
    assert page.select_one("form#approve input[type=checkbox]")["name"] == "confirm"
    assert page.select_one("form#approve input[type=checkbox]")["value"] == "y"

    rejection_form = page.select_one("form#reject")
    button = rejection_form.select_one("button.govuk-button.govuk-button--warning")
    assert normalize_spaces(button.text) == "Reject alert"


def test_confirm_approve_non_training_broadcasts_errors_if_not_ticked(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    mock_update_broadcast_message,
    mock_update_broadcast_message_status,
    active_user_approve_broadcasts_permission,
    mock_get_broadcast_message_versions,
    mock_check_can_update_status,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
    mock_get_count_of_phones,
    mock_get_areas_by_ids,
):
    page = mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=None,
            created_by_id=None,
            status="pending-approval",
            created_at="2020-02-23T20:23:23.000000",
        ),
    )
    service_one["permissions"] += ["broadcast"]
    service_one["restricted"] = False
    service_one["allowed_broadcast_provider"] = "all"
    service_one["broadcast_channel"] = "severe"

    client_request.login(active_user_approve_broadcasts_permission)
    page = client_request.post(
        ".approve_broadcast_message",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _data={},
        _expected_status=200,
    )
    error_message = page.select_one("form#approve .govuk-error-message")
    assert error_message
    assert error_message["id"] == "confirm-error"
    assert normalize_spaces(error_message.text) == "Error: You need to confirm that you understand"

    assert mock_update_broadcast_message.called is False
    assert mock_update_broadcast_message_status.called is False


@freeze_time("2020-02-22T22:22:22.000000")
def test_can_approve_own_broadcast_in_training_mode(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    active_user_approve_broadcasts_permission,
    mock_get_broadcast_message_versions,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
    mock_get_count_of_phones,
    mock_get_areas_by_ids,
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            finishes_at="2020-02-23T23:23:23.000000",
            status="pending-approval",
            created_at="2020-02-23T23:23:23.000000",
        ),
    )
    client_request.login(active_user_approve_broadcasts_permission)
    service_one["permissions"] += ["broadcast"]

    page = client_request.get(
        ".view_current_broadcast",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _test_page_title=False,
    )

    assert (normalize_spaces(page.select_one(".banner h1").text)) == "Example template is waiting for approval"
    assert (normalize_spaces(page.select_one(".banner p").text)) == (
        "When you use a live account you’ll need another member of your team to approve your alert."
    )
    assert (normalize_spaces(page.select_one(".banner details summary").text)) == "Approve your own alert"
    assert (normalize_spaces(page.select_one(".banner details ").text)) == (
        "Approve your own alert "
        "Because you’re in training mode you can approve your own "
        "alerts, to see how it works. "
        "No real alerts will be broadcast to anyone’s phone. "
        "Start broadcasting now"
    )

    form = page.select_one(".banner details form")
    assert form["method"] == "post"
    assert "action" not in form
    assert normalize_spaces(form.select_one("button").text) == "Start broadcasting now"
    assert normalize_spaces(page.select(".govuk-button")[6].text) == "Return alert for edit"
    assert normalize_spaces(page.select(".govuk-button")[7].text) == "Reject alert"


@freeze_time("2020-02-22T22:22:22.000000")
@pytest.mark.parametrize(
    "user",
    [
        create_active_user_approve_broadcasts_permissions(),
        create_active_user_create_broadcasts_permissions(),
    ],
)
def test_can_approve_own_broadcast_if_service_is_live_and_user_didnt_submit_alert(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    user,
    mock_get_broadcast_message_versions,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
    mock_get_count_of_phones,
    mock_get_areas_by_ids,
):
    service_one["restricted"] = False
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            finishes_at="2020-02-23T23:23:23.000000",
            status="pending-approval",
            created_by="Test",
            reference="Example template",
            created_at="2020-02-23T20:23:23.000000",
        ),
    )
    client_request.login(user)
    service_one["permissions"] += ["broadcast"]

    page = client_request.get(
        ".view_current_broadcast",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _test_page_title=False,
    )

    assert (normalize_spaces(page.select_one(".banner h1").text)) == "Test wants to broadcast Example template"
    form = page.select("form")
    assert form
    assert normalize_spaces(page.select(".govuk-button")[5].text) == "Start broadcasting now"
    assert normalize_spaces(page.select(".govuk-button")[6].text) == "Return alert for edit"
    assert normalize_spaces(page.select(".govuk-button")[7].text) == "Reject alert"


@freeze_time("2020-02-22T22:22:22.000000")
@pytest.mark.parametrize(
    "user",
    [
        create_active_user_approve_broadcasts_permissions(),
        create_active_user_create_broadcasts_permissions(),
    ],
)
def test_cannot_approve_own_broadcast_if_service_is_live_and_user_submitted_alert(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    user,
    mock_get_broadcast_message_versions,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
    mock_get_count_of_phones,
    mock_get_areas_by_ids,
):
    service_one["restricted"] = False
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            finishes_at="2020-02-23T23:23:23.000000",
            status="pending-approval",
            created_by="Test",
            submitted_by_id=fake_uuid,
            created_at="2020-02-23T20:23:23.000000",
        ),
    )
    client_request.login(user)
    service_one["permissions"] += ["broadcast"]

    page = client_request.get(
        ".view_current_broadcast",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _test_page_title=False,
    )

    assert (normalize_spaces(page.select_one(".banner h1").text)) == "Example template is waiting for approval"
    assert (normalize_spaces(page.select_one(".banner p").text)) == (
        "You need another member of your team to approve your alert."
    )

    button = page.select_one(".banner button.govuk-button.govuk-button--warning")
    assert button.text == "Discard this alert"
    form = button.parent.parent
    assert form["action"] == url_for(
        ".discard_broadcast_message",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )


@freeze_time("2020-02-22T22:22:22.000000")
@pytest.mark.parametrize("user_is_platform_admin", [True, False])
def test_view_only_user_cant_approve_broadcast_created_by_someone_else(
    mocker,
    client_request,
    service_one,
    active_user_create_broadcasts_permission,
    active_user_view_permissions,
    platform_admin_user_no_service_permissions,
    fake_uuid,
    user_is_platform_admin,
    mock_get_broadcast_message_versions,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
    mock_get_count_of_phones,
    mock_get_areas_by_ids,
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            finishes_at="2020-02-23T23:23:23.000000",
            status="pending-approval",
            created_at="2020-02-23T20:23:23.000000",
        ),
    )

    service_one["permissions"] += ["broadcast"]

    page = client_request.get(
        ".view_current_broadcast",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _test_page_title=False,
    )

    assert (normalize_spaces(page.select_one(".banner").text)) == (
        "This alert is waiting for approval You don’t have permission to approve alerts."
    )

    assert not page.select_one("form")
    assert not page.select_one(".banner a")


def test_view_only_user_cant_approve_broadcasts_they_created(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    active_user_create_broadcasts_permission,
    active_user_view_permissions,
    mock_get_broadcast_message_versions,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
    mock_get_count_of_phones,
    mock_get_areas_by_ids,
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            finishes_at="2020-02-23T23:23:23.000000",
            status="pending-approval",
            created_at="2020-02-23T20:23:23.000000",
        ),
    )
    client_request.login(active_user_view_permissions)

    service_one["permissions"] += ["broadcast"]
    service_one["restriced"] = False

    page = client_request.get(
        ".view_current_broadcast",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _test_page_title=False,
    )

    assert (normalize_spaces(page.select_one(".banner").text)) == (
        "This alert is waiting for approval You don’t have permission to approve alerts."
    )

    assert not page.select_one("form")
    assert not page.select_one(".banner a")


@pytest.mark.parametrize(
    "is_service_training_mode,banner_text",
    [
        (
            True,
            (
                "This alert is waiting for approval "
                "Another member of your team needs to approve this alert. "
                "This service is in training mode. No real alerts will be sent. "
                "Discard this alert"
            ),
        ),
        (
            False,
            (
                "This alert is waiting for approval "
                "Another member of your team needs to approve this alert. "
                "Discard this alert"
            ),
        ),
    ],
)
def test_user_without_approve_permission_cant_approve_broadcast_created_by_someone_else(
    mocker,
    client_request,
    service_one,
    active_user_create_broadcasts_permission,
    fake_uuid,
    is_service_training_mode,
    banner_text,
    mock_get_broadcast_message_versions,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
    mock_get_areas_by_ids,
):
    mocker.patch("app.broadcast_message_api_client.get_count_of_phones", return_value=1_000_000)
    current_user = create_active_user_create_broadcasts_permissions(with_unique_id=True)
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            finishes_at="2020-02-23T23:23:23.000000",
            status="pending-approval",
            created_at="2020-02-23T20:23:23.000000",
        ),
    )
    client_request.login(current_user)
    mocker.patch(
        "app.user_api_client.get_user",
        return_value=active_user_create_broadcasts_permission,
    )
    service_one["permissions"] += ["broadcast"]
    service_one["restricted"] = is_service_training_mode

    page = client_request.get(
        ".view_current_broadcast",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _test_page_title=False,
    )

    assert (normalize_spaces(page.select_one(".banner").text)) == banner_text
    button = page.select_one(".banner button.govuk-button.govuk-button--warning")
    assert button.text == "Discard this alert"
    form = button.parent.parent
    assert form["action"] == url_for(
        ".discard_broadcast_message",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )


def test_user_without_approve_permission_cant_approve_broadcast_they_created(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    active_user_create_broadcasts_permission,
    mock_get_broadcast_message_versions,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
    mock_get_count_of_phones,
    mock_get_areas_by_ids,
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=active_user_create_broadcasts_permission["id"],
            finishes_at=None,
            status="pending-approval",
            created_at="2020-02-23T20:23:23.000000",
        ),
    )
    client_request.login(active_user_create_broadcasts_permission)
    service_one["permissions"] += ["broadcast"]

    page = client_request.get(
        ".view_current_broadcast",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _test_page_title=False,
    )

    assert (normalize_spaces(page.select_one(".banner").text)) == (
        "Example template is waiting for approval "
        "You need another member of your team to approve this alert. "
        "This service is in training mode. No real alerts will be sent. "
        "Discard this alert"
    )
    assert not page.select(".banner input[type=checkbox]")

    button = page.select_one(".banner button.govuk-button.govuk-button--warning")
    assert button.text == "Discard this alert"
    form = button.parent.parent
    assert form["action"] == url_for(
        ".discard_broadcast_message",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )


@pytest.mark.parametrize(
    "channel, duration, expected_finishes_at",
    (
        ("operator", 1800, "2020-02-22T22:52:22+00:00"),  # 30 mins later
        ("test", 10800, "2020-02-23T01:22:22+00:00"),  # 3 hours later
        ("severe", 21600, "2020-02-23T04:22:22+00:00"),  # 6 hours later
        ("government", 79200, "2020-02-23T20:22:22+00:00"),  # 22 hours later
        (None, 0, "2020-02-23T20:52:22+00:00"),  # Training mode
    ),
)
@pytest.mark.parametrize(
    "trial_mode, initial_status, post_data, expected_approval, expected_redirect",
    (
        (
            True,
            "draft",
            {},
            False,
            partial(
                url_for,
                ".view_current_broadcast",
                broadcast_message_id=sample_uuid,
            ),
        ),
        (
            True,
            "pending-approval",
            {},
            True,
            partial(
                url_for,
                ".broadcast_tour",
                step_index=6,
            ),
        ),
        (
            False,
            "pending-approval",
            {"confirm": "y"},
            True,
            partial(
                url_for,
                ".view_current_broadcast",
                broadcast_message_id=sample_uuid,
            ),
        ),
        (
            True,
            "rejected",
            {},
            False,
            partial(
                url_for,
                ".view_current_broadcast",
                broadcast_message_id=sample_uuid,
            ),
        ),
        (
            True,
            "broadcasting",
            {},
            False,
            partial(
                url_for,
                ".view_current_broadcast",
                broadcast_message_id=sample_uuid,
            ),
        ),
        (
            True,
            "cancelled",
            {},
            False,
            partial(
                url_for,
                ".view_current_broadcast",
                broadcast_message_id=sample_uuid,
            ),
        ),
    ),
)
@freeze_time("2020-02-22T22:22:22.000000")
def test_confirm_approve_broadcast(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    mock_update_broadcast_message,
    mock_update_broadcast_message_status,
    active_user_approve_broadcasts_permission,
    initial_status,
    post_data,
    expected_approval,
    trial_mode,
    expected_redirect,
    channel,
    duration,
    expected_finishes_at,
    mock_get_broadcast_message_versions,
    mock_check_can_update_status,
    mock_get_areas_by_ids,
):
    mocker.patch("app.broadcast_message_api_client.get_count_of_phones", return_value=1_000_000)
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            duration=duration,
            finishes_at="2020-02-23T20:52:22.000000",
            status=initial_status,
        ),
    )
    service_one["restricted"] = trial_mode
    service_one["permissions"] += ["broadcast"]
    service_one["broadcast_channel"] = channel

    client_request.login(active_user_approve_broadcasts_permission)
    client_request.post(
        ".approve_broadcast_message",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _expected_redirect=expected_redirect(
            service_id=SERVICE_ONE_ID,
        ),
        _data=post_data,
    )

    if expected_approval:
        mock_update_broadcast_message.assert_called_once_with(
            service_id=SERVICE_ONE_ID,
            broadcast_message_id=fake_uuid,
            data={
                "starts_at": "2020-02-22T22:22:22+00:00",
                "finishes_at": expected_finishes_at,
            },
        )
        mock_update_broadcast_message_status.assert_called_once_with(
            "broadcasting",
            service_id=SERVICE_ONE_ID,
            broadcast_message_id=fake_uuid,
        )
    else:
        assert mock_update_broadcast_message.called is False
        assert mock_update_broadcast_message_status.called is False


@pytest.mark.parametrize("trial_mode", (True, False))
@pytest.mark.parametrize(
    "initial_status",
    (
        ("draft",),
        ("pending-approval",),
        ("rejected",),
        ("broadcasting",),
        ("draft",),
    ),
)
@freeze_time("2020-02-22T22:22:22.000000")
def test_cannot_approve_broadcast_if_transition_not_allowed(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    mock_update_broadcast_message,
    mock_update_broadcast_message_status,
    active_user_approve_broadcasts_permission,
    initial_status,
    trial_mode,
    mock_get_broadcast_message_versions,
    mock_check_can_update_status_returns_http_error,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_areas_by_ids,
):
    mocker.patch("app.broadcast_message_api_client.get_count_of_phones", return_value=1_000_000)
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            status=initial_status,
            finishes_at="2020-02-23T23:23:23.000000",
            starts_at="2020-02-23T23:13:23.000000",
        ),
    )
    service_one["restricted"] = trial_mode
    service_one["permissions"] += ["broadcast"]

    client_request.login(active_user_approve_broadcasts_permission)

    page = client_request.post(
        ".approve_broadcast_message",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _expected_status=200,
        _data={},
    )

    assert mock_update_broadcast_message.called is False
    assert mock_update_broadcast_message_status.called is False
    assert normalize_spaces(page.select_one(".banner-dangerous").text) == (
        "This alert is live, it cannot be edited or submitted again."
    )


@pytest.mark.parametrize(
    "user",
    (create_active_user_approve_broadcasts_permissions(),),
)
@freeze_time("2020-02-22T22:22:22.000000")
def test_reject_broadcast_displays_error_when_no_reason_provided(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    mock_update_broadcast_message,
    mock_update_broadcast_message_status_with_reason,
    user,
    mock_get_broadcast_message_versions,
    mock_check_can_update_status,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
    mock_get_count_of_phones,
    mock_get_areas_by_ids,
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            finishes_at="2020-02-23T23:23:23.000000",
            status="pending-approval",
            created_at="2020-02-23T20:23:23.000000",
        ),
    )
    service_one["permissions"] += ["broadcast"]

    client_request.login(user)
    page = client_request.post(
        ".reject_broadcast_message",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _expected_status=200,
        _data={"rejection_reason": ""},
    )

    assert (
        normalize_spaces(page.select_one(".govuk-error-message").text)
        == "Error: Enter the reason for rejecting the alert"
    )

    assert mock_update_broadcast_message.called is False
    assert mock_update_broadcast_message_status_with_reason.called is False


@pytest.mark.parametrize(
    "user",
    (create_active_user_approve_broadcasts_permissions(),),
)
@freeze_time("2020-02-22T22:22:22.000000")
def test_return_broadcast_for_edit_displays_error_when_no_reason_provided(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    mock_update_broadcast_message,
    mock_update_broadcast_message_status_with_reason,
    user,
    mock_get_broadcast_message_versions,
    mock_check_can_update_status,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
    mock_get_count_of_phones,
    mock_get_areas_by_ids,
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            finishes_at="2020-02-23T23:23:23.000000",
            status="pending-approval",
            created_at="2020-02-23T20:23:23.000000",
        ),
    )
    service_one["permissions"] += ["broadcast"]

    client_request.login(user)
    page = client_request.post(
        ".return_broadcast_for_edit",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _expected_status=200,
        _data={"return_for_edit_reason": ""},
    )

    assert (
        normalize_spaces(page.select_one(".govuk-error-message").text)
        == "Error: Enter the reason for returning the alert for edit"
    )

    assert mock_update_broadcast_message.called is False


@pytest.mark.parametrize(
    "user",
    (create_active_user_approve_broadcasts_permissions(),),
)
@freeze_time("2020-02-22T22:22:22.000000")
def test_can_return_broadcast_for_edit(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    mock_return_broadcast_message_for_edit_with_reason,
    mock_update_broadcast_message_status_with_reason,
    user,
    mock_get_broadcast_message_versions,
    mock_check_can_update_status,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
    mock_get_count_of_phones,
    mock_get_areas_by_ids,
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            finishes_at="2020-02-23T23:23:23.000000",
            status="pending-approval",
            created_at="2020-02-23T20:23:23.000000",
        ),
    )
    service_one["permissions"] += ["broadcast"]

    client_request.login(user)
    client_request.post(
        ".return_broadcast_for_edit",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _expected_status=200,
        _data={"return_for_edit_reason": "test reason"},
    )

    assert mock_return_broadcast_message_for_edit_with_reason.called is True


@pytest.mark.parametrize(
    "user",
    (create_active_user_create_broadcasts_permissions(),),
)
@freeze_time("2020-02-22T22:22:22.000000")
def test_discard_broadcast(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    mock_update_broadcast_message,
    mock_update_broadcast_message_status_with_reason,
    user,
    mock_get_broadcast_message_versions,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
    mock_get_count_of_phones,
    mock_get_areas_by_ids,
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            finishes_at="2020-02-23T23:23:23.000000",
            status="pending-approval",
            created_at="2020-02-23T20:23:23.000000",
        ),
    )
    service_one["permissions"] += ["broadcast"]

    client_request.login(user)
    page = client_request.post(
        ".reject_broadcast_message", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid, _expected_status=200
    )
    button = page.select_one(".banner button.govuk-button.govuk-button--warning")
    assert button.text == "Discard this alert"
    form = button.parent.parent
    assert form["action"] == url_for(
        ".discard_broadcast_message",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )

    assert mock_update_broadcast_message.called is False
    assert mock_update_broadcast_message_status_with_reason.called is False


@pytest.mark.parametrize(
    "user",
    (create_active_user_approve_broadcasts_permissions(),),
)
@freeze_time("2020-02-22T22:22:22.000000")
def test_cannot_reject_broadcast_if_transition_not_allowed(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    mock_update_broadcast_message,
    mock_update_broadcast_message_status_with_reason,
    user,
    mock_get_broadcast_message_versions,
    mock_check_can_update_status_returns_http_error,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
    mock_get_count_of_phones,
    mock_get_areas_by_ids,
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            finishes_at="2020-02-23T23:23:23.000000",
            status="pending-approval",
            created_at="2020-02-23T22:23:23.000000",
        ),
    )
    service_one["permissions"] += ["broadcast"]

    client_request.login(user)
    page = client_request.post(
        ".reject_broadcast_message",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _expected_status=200,
        _data={"rejection_reason": ""},
    )

    assert mock_update_broadcast_message.called is False
    assert mock_update_broadcast_message_status_with_reason.called is False
    assert normalize_spaces(page.select_one(".banner-dangerous").text) == (
        "This alert has been rejected, it cannot be edited or resubmitted for approval."
    )


@pytest.mark.parametrize(
    "user",
    (create_active_user_create_broadcasts_permissions(),),
)
@freeze_time("2020-02-22T22:22:22.000000")
def test_cannot_discard_broadcast_if_transition_not_allowed(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    mock_update_broadcast_message,
    mock_update_broadcast_message_status_with_reason,
    user,
    mock_get_broadcast_message_versions,
    mock_check_can_update_status_returns_http_error,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
    mock_get_count_of_phones,
    mock_get_areas_by_ids,
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            finishes_at="2020-02-23T23:23:23.000000",
            status="pending-approval",
            created_at="2020-02-23T20:23:23.000000",
        ),
    )
    service_one["permissions"] += ["broadcast"]

    client_request.login(user)
    page = client_request.post(
        ".reject_broadcast_message", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid, _expected_status=200
    )

    assert mock_update_broadcast_message.called is False
    assert mock_update_broadcast_message_status_with_reason.called is False
    assert normalize_spaces(page.select_one(".banner-dangerous").text) == (
        "This alert has been rejected, it cannot be edited or resubmitted for approval."
    )


@pytest.mark.parametrize(
    "user",
    (
        create_active_user_create_broadcasts_permissions(),
        create_active_user_approve_broadcasts_permissions(),
    ),
)
@freeze_time("2020-02-22T22:22:22.000000")
def test_reject_broadcast_with_reason(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    mock_update_broadcast_message,
    mock_update_broadcast_message_status_with_reason,
    user,
    mock_get_broadcast_message_versions,
    mock_check_can_update_status,
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            finishes_at="2020-02-23T23:23:23.000000",
            status="pending-approval",
        ),
    )
    service_one["permissions"] += ["broadcast"]

    client_request.login(user)
    client_request.post(
        ".reject_broadcast_message",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _expected_redirect=url_for(
            ".broadcast_dashboard",
            service_id=SERVICE_ONE_ID,
        ),
        _data={"rejection_reason": "TEST"},
    )

    assert mock_update_broadcast_message.called is False
    assert mock_update_broadcast_message_status_with_reason.called

    mock_update_broadcast_message_status_with_reason.assert_called_once_with(
        "rejected", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid, rejection_reason="TEST"
    )


@pytest.mark.parametrize(
    "user",
    [
        create_active_user_create_broadcasts_permissions(),
        create_active_user_approve_broadcasts_permissions(),
    ],
)
@pytest.mark.parametrize(
    "initial_status",
    (
        "draft",
        "rejected",
        "broadcasting",
        "cancelled",
    ),
)
@freeze_time("2020-02-22T22:22:22.000000")
def test_cant_reject_broadcast_in_wrong_state(
    mocker,
    client_request,
    service_one,
    mock_get_template,
    fake_uuid,
    mock_update_broadcast_message,
    mock_update_broadcast_message_status,
    user,
    initial_status,
    mock_get_broadcast_message_versions,
    mock_check_can_update_status,
    mock_get_broadcast_message,
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            finishes_at="2020-02-23T23:23:23.000000",
            status=initial_status,
        ),
    )
    service_one["permissions"] += ["broadcast"]

    client_request.login(user)
    client_request.get(
        ".reject_broadcast_message",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _expected_redirect=url_for(
            ".view_current_broadcast",
            service_id=SERVICE_ONE_ID,
            broadcast_message_id=fake_uuid,
        ),
    )

    assert mock_update_broadcast_message.called is False
    assert mock_update_broadcast_message_status.called is False


def test_submit_broadcast_changes_status(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    mock_update_broadcast_message,
    mock_get_broadcast_message_versions,
    mock_update_broadcast_message_status,
    mock_check_can_update_status,
    mock_get_areas_by_ids,
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            finishes_at="2020-02-23T23:23:23.000000",
            status="draft",
        ),
    )
    service_one["permissions"] += ["broadcast"]

    client_request.login(create_active_user_create_broadcasts_permissions())
    client_request.post(
        ".submit_broadcast_message",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _expected_redirect=url_for(
            ".view_current_broadcast",
            broadcast_message_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
        ),
    )

    mock_update_broadcast_message_status.assert_called_once_with(
        "pending-approval",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )


def test_cannot_submit_if_transition_not_allowed(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    mock_update_broadcast_message,
    mock_get_broadcast_message_versions,
    mock_update_broadcast_message_status,
    mock_check_can_update_status_returns_http_error,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
    mock_get_count_of_phones,
    mock_get_areas_by_ids,
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            finishes_at="2020-02-23T23:23:23.000000",
            updated_at="2020-02-23T23:00:00.000000",
            created_at="2020-02-23T20:00:00.000000",
        ),
    )
    service_one["permissions"] += ["broadcast"]

    client_request.login(create_active_user_create_broadcasts_permissions())

    page = client_request.post(
        ".submit_broadcast_message", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid, _expected_status=200
    )

    assert mock_update_broadcast_message_status.called is False
    assert normalize_spaces(page.select_one(".banner-dangerous").text) == (
        "This alert is pending approval, it cannot be edited or submitted again."
    )


def test_view_broadcast_versions_returns_versions(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    mock_update_broadcast_message,
    mock_update_broadcast_message_status_with_reason,
    mock_get_broadcast_message_versions,
    mock_check_can_update_status,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_version_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            created_by_id=fake_uuid,
            status="draft",
        ),
    )
    service_one["permissions"] += ["broadcast"]

    client_request.login(create_active_user_create_broadcasts_permissions())

    page = client_request.post(
        ".view_broadcast_versions", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid, _expected_status=200
    )

    assert normalize_spaces(page.select_one("h1").text) == "Previous versions"
    assert [
        normalize_spaces(row.text)
        for row in page.select(".govuk-grid-column-three-quarters")[0].select(".message-name")
    ] == [
        "Test version broadcast",
        "Test version broadcast",
    ]
    assert [
        normalize_spaces(row.text)
        for row in page.select(".govuk-grid-column-three-quarters")[0].select(".area-list-item")
    ] == [
        "England",
        "England",
    ]


@pytest.mark.parametrize(
    "endpoint",
    (".view_current_broadcast",),
)
def test_can_view_current_page_for_draft(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    fake_uuid,
    endpoint,
    mock_get_broadcast_message_versions,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
    mock_get_count_of_phones,
    mock_get_areas_by_ids,
):
    service_one["permissions"] += ["broadcast"]
    client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )


@pytest.mark.parametrize(
    "endpoint",
    (".view_previous_broadcast",),
)
def test_view_previous_page_for_draft_redirects_to_current(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    fake_uuid,
    endpoint,
    mock_get_broadcast_message_versions,
):
    service_one["permissions"] += ["broadcast"]
    client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _expected_redirect=url_for(
            ".view_current_broadcast",
            service_id=SERVICE_ONE_ID,
            broadcast_message_id=fake_uuid,
        ),
    )


@pytest.mark.parametrize(
    "user",
    (
        create_active_user_create_broadcasts_permissions(),
        create_active_user_approve_broadcasts_permissions(),
        create_platform_admin_user(),
    ),
)
def test_cancel_broadcast(
    client_request,
    service_one,
    mock_get_live_broadcast_message,
    mock_update_broadcast_message_status,
    fake_uuid,
    user,
    mock_get_broadcast_message_versions,
    mock_check_can_update_status,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
    mock_get_count_of_phones,
    mock_get_areas_by_ids,
):
    """
    users with 'create/approve_broadcasts' permissions and platform admins should be able to cancel broadcasts.
    """
    service_one["permissions"] += ["broadcast"]

    client_request.login(user)
    page = client_request.get(
        ".cancel_broadcast_message",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _test_page_prefix="Are you sure you want to stop this broadcast now?",
    )
    assert normalize_spaces(page.select_one(".banner-dangerous").text) == (
        "Are you sure you want to stop this broadcast now? Yes, stop broadcasting"
    )
    form = page.select_one("form")
    assert form["method"] == "post"
    assert "action" not in form
    assert normalize_spaces(form.select_one("button").text) == "Yes, stop broadcasting"
    assert mock_update_broadcast_message_status.called is False
    assert (
        url_for(
            ".cancel_broadcast_message",
            service_id=SERVICE_ONE_ID,
            broadcast_message_id=fake_uuid,
        )
        not in page
    )


@pytest.mark.parametrize(
    "user",
    (
        create_active_user_create_broadcasts_permissions(),
        create_active_user_approve_broadcasts_permissions(),
        create_platform_admin_user(),
    ),
)
def test_cannot_cancel_broadcast_if_transition_not_allowed(
    client_request,
    service_one,
    mock_get_live_broadcast_message,
    mock_update_broadcast_message_status,
    fake_uuid,
    user,
    mock_get_broadcast_message_versions,
    mock_check_can_update_status_returns_http_error,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
    mock_get_count_of_phones,
    mock_get_areas_by_ids,
):
    service_one["permissions"] += ["broadcast"]

    client_request.login(user)
    page = client_request.get(
        ".cancel_broadcast_message", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid, _expected_status=200
    )

    assert mock_update_broadcast_message_status.called is False
    assert normalize_spaces(page.select_one(".banner-dangerous").text) == (
        "This alert has already been broadcast, it cannot be edited or resubmitted for approval."
    )


@pytest.mark.parametrize(
    "user",
    [
        create_platform_admin_user(),
        create_active_user_create_broadcasts_permissions(),
        create_active_user_approve_broadcasts_permissions(),
    ],
)
def test_confirm_cancel_broadcast(
    client_request,
    service_one,
    mock_get_live_broadcast_message,
    mock_update_broadcast_message_status,
    mock_check_can_update_status,
    fake_uuid,
    user,
):
    """
    Platform admins and users with any of the broadcast permissions can cancel broadcasts.
    """
    service_one["permissions"] += ["broadcast"]

    client_request.login(user)

    client_request.post(
        ".cancel_broadcast_message",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _expected_redirect=url_for(
            ".view_previous_broadcast",
            service_id=SERVICE_ONE_ID,
            broadcast_message_id=fake_uuid,
        ),
    )
    mock_update_broadcast_message_status.assert_called_once_with(
        "cancelled",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )


@pytest.mark.parametrize("method", ("post", "get"))
def test_cant_cancel_broadcast_in_a_different_state(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message_status,
    fake_uuid,
    active_user_create_broadcasts_permission,
    method,
    mock_check_can_update_status,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    getattr(client_request, method)(
        ".cancel_broadcast_message",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _expected_redirect=url_for(
            ".view_current_broadcast",
            service_id=SERVICE_ONE_ID,
            broadcast_message_id=fake_uuid,
        ),
    )
    assert mock_update_broadcast_message_status.called is False


def test_edit_broadcast_page(
    client_request,
    service_one,
    active_user_create_broadcasts_permission,
    mocker,
    fake_uuid,
    mock_check_can_update_status,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)

    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            reference="Test Edit Alert",
            content="This is a test for edit_broadcast",
        ),
    )
    page = client_request.get(".edit_broadcast", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid)

    assert normalize_spaces(page.select_one("h1").text) == "Edit alert"

    form = page.select_one("form")
    assert form["method"] == "post"
    assert "action" not in form

    assert normalize_spaces(page.select_one("label[for=reference]").text) == "Reference"
    assert page.select_one("input[type=text]")["name"] == "reference"

    assert normalize_spaces(page.select_one("label[for=content]").text) == "Alert message"
    assert normalize_spaces(page.select_one("textarea").text) == "This is a test for edit_broadcast"
    assert page.select_one("textarea")["name"] == "content"
    assert page.select_one("textarea")["data-notify-module"] == "enhanced-textbox"
    assert page.select_one("textarea")["data-highlight-placeholders"] == "false"

    assert (page.select_one("[data-notify-module=update-status]")["data-updates-url"]) == url_for(
        ".count_content_length", service_id=SERVICE_ONE_ID, template_type="broadcast", field="content"
    )

    assert (
        (page.select_one("[data-notify-module=update-status]")["data-target"])
        == (page.select_one("textarea")["id"])
        == "content"
    )

    assert (page.select_one("[data-notify-module=update-status]")["aria-live"]) == "polite"


def test_edit_broadcast_page_displays_overwrite_banner(
    client_request,
    service_one,
    active_user_create_broadcasts_permission,
    mocker,
    fake_uuid,
    mock_check_can_update_status,
):
    """
    Checks that if user submits edit_broadcast form data and the initial content for the form
    is different to what is stored for the broadcast_message, then a banner is displayed
    asking user if they want to overwrite that change or keep the change.
    In this test the data hasn't changed for the alert, but its simulated by changing
    the initial data for the form, so the banner is rendered.
    """
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)

    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            reference="Test Edit Alert",
            content="This is a test for edit_broadcast",
        ),
    )
    # Initial render of the edit page
    page = client_request.get(".edit_broadcast", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid)

    assert normalize_spaces(page.select_one("h1").text) == "Edit alert"
    assert normalize_spaces(page.select_one("textarea").text) == "This is a test for edit_broadcast"

    # Data posted to edit_broadcast where initial data changed to simulate actual broadcast_message changed
    page2 = client_request.post(
        ".edit_broadcast",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _data={
            "reference": "Emergency broadcast",
            "content": "Broadcast content",
            "initial_name": "Something different",
            "initial_content": "Something different",
        },
        _follow_redirects=True,
    )
    # Asserting that banners displayed to make user aware that change has been made to message that they're editing
    assert [normalize_spaces(item.text) for item in page2.select(".banner-dangerous")][0] == (
        "A user has made changes to the alert reference. Would you like to overwrite "
        + "their change? Yes, overwrite No, keep this change"
    )

    assert [normalize_spaces(item.text) for item in page2.select(".banner-dangerous")][1] == (
        "A user has made changes to the alert message. Would you like to overwrite "
        + "their change? Yes, overwrite No, keep this change"
    )


def test_edit_broadcast_clicking_overwrite_in_banner_closes_banner(
    client_request,
    service_one,
    active_user_create_broadcasts_permission,
    mocker,
    fake_uuid,
    mock_check_can_update_status,
    mock_update_broadcast_message,
    mock_get_broadcast_message_versions,
):
    """
    Checks that when the "User has made changes..." banner is displayed, clicking the "Yes, overwrite" button
    in the banner closes it.
    """
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)

    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            reference="Test Edit Alert",
            content="This is a test for edit_broadcast",
        ),
    )
    # Initial render of edit_broadcast page
    page = client_request.get(".edit_broadcast", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid)

    assert normalize_spaces(page.select_one("h1").text) == "Edit alert"
    assert normalize_spaces(page.select_one("textarea").text) == "This is a test for edit_broadcast"

    # Data posted to edit_broadcast where initial_name changed to simulate actual broadcast_message reference changed
    page2 = client_request.post(
        ".edit_broadcast",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _data={
            "reference": "Emergency broadcast overwritten",
            "content": "This is a test for edit_broadcast",
            "initial_name": "Something different",
            "initial_content": "This is a test for edit_broadcast",
        },
        _expected_status=200,
    )

    """
    Asserts that because initial_name different to current broadcast reference,
    the banner is displayed to say that the reference has been changed whilst page has been open
    """
    assert [normalize_spaces(item.text) for item in page2.select(".banner-dangerous")] == [
        "A user has made changes to the alert reference. Would you like to overwrite "
        + "their change? Yes, overwrite No, keep this change"
    ]

    """
    Data posted to edit_broadcast includes overwrite-reference which is present when "Yes, overwrite" button
    has been clicked.
    """
    page3 = client_request.post(
        ".edit_broadcast",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _data={
            "reference": "Emergency broadcast overwritten",
            "content": "This is a test for edit_broadcast",
            "initial_name": "Something different",
            "initial_content": "This is a test for edit_broadcast",
            "overwrite-reference": "",
        },
        _expected_status=200,
    )
    # Asserts that because the "Yes, overwrite" button has been clicked, the banner is closed
    assert not page3.select(".banner-dangerous")


def test_edit_broadcast_overwrite_updates_message_content(
    client_request,
    service_one,
    active_user_create_broadcasts_permission,
    mocker,
    fake_uuid,
    mock_check_can_update_status,
    mock_update_broadcast_message,
    mock_get_broadcast_message_versions,
    mock_get_areas_by_ids,
):
    """
    Checks that when "overwrite_content" is set to "y" in data posted to edit_broadcast, the data is updated.
    "overwrite_content" is a boolean, hidden field in BroadcastTemplate form and is 'checked' when user clicks
    "Yes, overwrite" button and then submits the form.
    """
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)

    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            reference="Test Edit Alert",
            content="This is a test for edit_broadcast",
        ),
    )
    # Initial render of edit_broadcast page
    page = client_request.get(".edit_broadcast", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid)

    assert normalize_spaces(page.select_one("h1").text) == "Edit alert"
    assert normalize_spaces(page.select_one("textarea").text) == "This is a test for edit_broadcast"

    """
    Data posted to edit_broadcast includes overwrite_content which is present when "Yes, overwrite" button
    has been clicked and user has submitted the form.
    """
    client_request.post(
        ".edit_broadcast",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _data={
            "reference": "Test Edit Alert",
            "content": "Broadcast content",
            "initial_name": "Test Edit Alert",
            "overwrite_content": "y",
        },
        _follow_redirects=True,
    )

    # Asserts that update_broadcast_message called with only content as only content changed
    mock_update_broadcast_message.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        data={
            "content": "Broadcast content",
        },
    )


def test_edit_broadcast_keep_message_keeps_message_reference(
    client_request,
    service_one,
    active_user_create_broadcasts_permission,
    mocker,
    fake_uuid,
    mock_check_can_update_status,
    mock_update_broadcast_message,
    mock_get_broadcast_message_versions,
):
    """
    Checks that when the "User has made changes..." banner is displayed, clicking the "No, keep this change" button
    in the banner closes it and the form fields are populated with changed broadcast_message data.
    """
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)

    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            reference="Test Edit Alert",
            content="This is a test for edit_broadcast",
        ),
    )
    # Initial render of edit_broadcast page
    page = client_request.get(".edit_broadcast", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid)
    assert page.select_one("input[name='reference']")["value"] == "Test Edit Alert"

    # Posting new reference
    page2 = client_request.post(
        ".edit_broadcast",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _data={
            "reference": "Test Edit Alert NEW",
            "content": "This is a test for edit_broadcast",
            "initial_name": "Something different",  # Simulates alert changed in the background
            "initial_content": "This is a test for edit_broadcast",
        },
        _expected_status=200,
    )
    # Assert reference field data has changed
    assert page2.select_one("input[name='reference']")["value"] == "Test Edit Alert NEW"

    assert [normalize_spaces(item.text) for item in page2.select(".banner-dangerous")] == [
        "A user has made changes to the alert reference. Would you like to overwrite "
        + "their change? Yes, overwrite No, keep this change"
    ]

    # Posting new reference with keep-reference button clicked to close banner
    page3 = client_request.post(
        ".edit_broadcast",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _data={
            "reference": "Test Edit Alert NEW",
            "content": "This is a test for edit_broadcast",
            "initial_name": "Test Edit Alert",  # Simulates alert changed in the background
            "initial_content": "This is a test for edit_broadcast",
            "keep-reference": "",
        },
        _follow_redirects=True,
    )

    # Asserts that the banner is closed and the reference field data has been reverted back to stored reference
    assert not page3.select(".banner-dangerous")
    assert page.select_one("input[name='reference']")["value"] == "Test Edit Alert"


def test_edit_broadcast_updates_message(
    client_request,
    service_one,
    active_user_create_broadcasts_permission,
    mocker,
    fake_uuid,
    mock_check_can_update_status,
    mock_update_broadcast_message,
    mock_get_broadcast_message_versions,
    mock_get_areas_by_ids,
):
    """
    Checks that when data is posted to edit_broadcast and no changes have been made to broadcast_message
    i.e. initial form data matches the stored broadcast_message, then any data submitted updates the
    broadcast_message.
    """
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)

    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            reference="Test Edit Alert",
            content="This is a test for edit_broadcast",
        ),
    )
    # Initial render of edit_broadcast page
    client_request.get(".edit_broadcast", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid)

    # Updated data posted but initial content matches current broadcast_message
    client_request.post(
        ".edit_broadcast",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _data={
            "reference": "Test Edit Alert NEW",
            "content": "This is a test for edit_broadcast",
            "initial_name": "Test Edit Alert",
            "initial_content": "This is a test for edit_broadcast",
        },
        _follow_redirects=True,
    )

    mock_update_broadcast_message.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        data={
            "reference": "Test Edit Alert NEW",
        },
    )


def test_add_extra_content_updates_message(
    client_request,
    service_one,
    active_user_create_broadcasts_permission,
    mocker,
    fake_uuid,
    mock_check_can_update_status,
    mock_update_broadcast_message,
    mock_get_broadcast_message_versions,
    mock_get_areas_by_ids,
):
    """
    Checks that when data is posted to add_extra_content and no changes have been made to broadcast_message
    i.e. initial form data matches the stored broadcast_message, then any data submitted updates the
    broadcast_message.
    """
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)

    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            extra_content="Test Extra Content",
        ),
    )
    # Initial render of the page
    client_request.get(".add_extra_content", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid)

    # Updated data posted but initial content matches current broadcast_message
    client_request.post(
        ".add_extra_content",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _data={
            "extra_content": "Test Edit Alert NEW",
            "initial_extra_content": "Test Extra Content",
        },
        _follow_redirects=True,
    )

    mock_update_broadcast_message.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        data={
            "extra_content": "Test Edit Alert NEW",
        },
    )


def test_add_extra_content_secondary_removes_extra_content(
    client_request,
    service_one,
    active_user_create_broadcasts_permission,
    mocker,
    fake_uuid,
    mock_check_can_update_status,
    mock_update_broadcast_message,
    mock_get_broadcast_message_versions,
):
    """
    Checks that when the secondary ('no longer required') button is clicked, that the extra content is removed.
    """
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)

    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            extra_content="Test Extra Content",
        ),
    )
    # Initial render of the page
    client_request.get(".add_extra_content", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid)

    # Simulate clicking the secondary button named remove-extra-content
    client_request.post(
        ".add_extra_content",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _data={
            "extra_content": "Test Extra Content",
            "initial_extra_content": "Test Extra Content",
            "remove-extra-content": "anything",
        },
        _expected_redirect=url_for(
            ".view_current_broadcast", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid
        ),
    )

    mock_update_broadcast_message.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        data={
            "extra_content": "",
        },
    )


def test_add_extra_content_keep_message_keeps_original_extra_content(
    client_request,
    service_one,
    active_user_create_broadcasts_permission,
    mocker,
    fake_uuid,
    mock_check_can_update_status,
    mock_update_broadcast_message,
    mock_get_broadcast_message_versions,
):
    """
    Checks that when the "User has made changes..." banner is displayed, clicking the "No, keep this change" button
    in the banner closes it and the form fields are populated with changed broadcast_message data.
    """
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)

    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            extra_content="Test Extra Content",
        ),
    )
    # Initial render of add_extra_content page
    page = client_request.get(".add_extra_content", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid)
    assert normalize_spaces(page.select_one("textarea").text) == "Test Extra Content"
    # Posting new reference
    page2 = client_request.post(
        ".add_extra_content",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _data={
            "extra_content": "Test Extra Content NEW",
            "initial_extra_content": "Something different",  # Simulates alert changed in the background
        },
        _expected_status=200,
    )

    assert [normalize_spaces(item.text) for item in page2.select(".banner-dangerous")] == [
        "A user has made changes to the alert's additional information. Would you like to "
        + "overwrite their change? Yes, overwrite No, keep this change"
    ]

    # Posting new reference with keep-extra-content button clicked to close banner
    page3 = client_request.post(
        ".add_extra_content",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _data={
            "extra_content": "Test Extra Content NEW",
            "initial_extra_content": "Test Extra Content NEW",  # Simulates alert changed in the background
            "keep-extra-content": "",
        },
        _follow_redirects=True,
    )

    # Asserts that the banner is closed and the reference field data has been reverted back to stored reference
    assert not page3.select(".banner-dangerous")
    assert normalize_spaces(page.select_one("textarea").text) == "Test Extra Content"
    assert mock_update_broadcast_message.called is False


def test_add_extra_content_overwrite_change_overwrites_extra_content(
    client_request,
    service_one,
    active_user_create_broadcasts_permission,
    mocker,
    fake_uuid,
    mock_check_can_update_status,
    mock_update_broadcast_message,
    mock_get_broadcast_message_versions,
    mock_get_areas_by_ids,
):
    """
    Checks that when "overwrite_extra_content" is set to "y" in data posted to add_extra_content, the data is updated.
    "overwrite_extra_content" is a boolean, hidden field in AddExtraContent form and is 'checked' when user clicks
    "Yes, overwrite" button and then submits the form.
    """
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)

    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            extra_content="Test Extra Content",
        ),
    )
    # Initial render of add_extra_content page
    page = client_request.get(".add_extra_content", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid)

    assert normalize_spaces(page.select_one("h1").text) == "Edit additional information"
    assert normalize_spaces(page.select_one("textarea").text) == "Test Extra Content"

    """
    Data posted to add_extra_content includes overwrite_extra_content which is present when "Yes, overwrite" button
    has been clicked and user has submitted the form.
    """
    client_request.post(
        ".add_extra_content",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _data={
            "extra_content": "Test Extra Content NEW",
            "initial_extra_content": "Test Extra Content",
            "overwrite_extra_content": "y",
        },
        _follow_redirects=True,
    )

    # Asserts that update_broadcast_message called with extra_content data
    mock_update_broadcast_message.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        data={
            "extra_content": "Test Extra Content NEW",
        },
    )


def test_view_draft_broadcast_message_page(
    mocker,
    client_request,
    service_one,
    active_user_view_permissions,
    fake_uuid,
    mock_get_broadcast_message_versions,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_broadcast_message_provider_statuses,
):
    mocker.patch(
        "app.models.base_broadcast.Areas.get",
        return_value=[
            MockArea(
                {
                    "id": "E92000001",
                    "name": "England",
                }
            ),
            MockArea(
                {
                    "id": "E92000001",
                    "name": "Scotland",
                }
            ),
        ],
    )
    mocker.patch("app.broadcast_message_api_client.get_count_of_phones", return_value=1_000_000)
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            approved_by_id=fake_uuid,
            starts_at="2020-02-20T20:20:20.000000",
            created_at="2020-02-20T20:20:20.000000",
            content="Hello",
            extra_content="Test Extra Content",
            reference="Test Template Reference",
            duration=10_800,
            areas={
                "ids": ["E92000001", "S92000003"],
                "names": ["England", "Scotland"],
                "simple_polygons": MULTIPLE_ENGLAND,
                "aggregate_names": [],
            },
        ),
    )
    service_one["permissions"] += ["broadcast"]

    client_request.login(active_user_view_permissions)

    page = client_request.get(
        ".view_current_broadcast",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )

    assert not page.select_one(".banner")
    assert [normalize_spaces(p.text) for p in page.select(".govuk-summary-list__key")] == [
        "Reference",
        "Alert message",
        "Additional Information",
        "Area",
        "Alert duration",
        "Phone estimate",
        "Downloads",
    ]
    assert [normalize_spaces(p.text) for p in page.select(".govuk-summary-list__value")] == [
        "Test Template Reference",
        "Emergency alert Hello",
        "Test Extra Content",
        "England Scotland Use the arrow keys to move the map. "
        + "Use the buttons to zoom the map in or out View larger map",
        "3 hours",
        "More than 1 million phones estimated",
        "Download geoJSON Download CAP XML Download IBAG XML",
    ]


def test_can_get_geojson_simple(
    mocker,
    client_request,
    service_one,
    active_user_view_permissions,
    fake_uuid,
    mock_get_broadcast_message_versions,
    mock_get_areas_by_ids,
):
    mock_area = MockArea(
        {
            "id": "E92000001",
            "name": "Bristol Name",
            "geometry_wkt": "".join(
                ["POLYGON ((-0.1400 51.5150,-0.1400 51.4950,-0.1000", " 51.4950,-0.1000 51.5150,-0.1400 51.5150))"]
            ),
        }
    )
    mock_area.polygons = mocker.Mock(
        as_wgs84_coordinates=[
            [
                [-2.6216, 51.4371],
                [-2.575, 51.4371],
                [-2.575, 51.4668],
                [-2.6216, 51.4668],
                [-2.6216, 51.4371],
            ]
        ]
    )

    mocker.patch(
        "app.models.base_broadcast.Areas.get",
        return_value=[mock_area],
    )
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            approved_by_id=fake_uuid,
            starts_at="2020-02-20T20:20:20.000000",
            reference="Test name",
            content="Hello",
            duration=10_800,
            areas={
                "ids": ["Bristol ID"],
                "simple_polygons": [BRISTOL],
                # We want the name in the JSON so make them different to the IDs for asserting
                "names": ["Bristol Name"],
            },
        ),
    )
    service_one["permissions"] += ["broadcast"]

    client_request.login(active_user_view_permissions)
    json_response = client_request.get_response(
        ".get_broadcast_geojson",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )

    assert json_response.content_type == "application/geo+json"
    assert json_response.headers.get("Content-Disposition") == f"attachment;filename=Test name-{fake_uuid}.geojson"
    json_contents = json.loads(json_response.text)

    assert json_contents == {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-2.6216, 51.4371],
                            [-2.575, 51.4371],
                            [-2.575, 51.4668],
                            [-2.6216, 51.4668],
                            [-2.6216, 51.4371],
                        ]
                    ],
                },
                "properties": {"name": "Bristol Name"},
            }
        ],
    }


def test_can_get_unsigned_cap_xml(
    mocker,
    client_request,
    service_one,
    active_user_view_permissions,
    fake_uuid,
    mock_get_broadcast_message_versions,
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            approved_by_id=fake_uuid,
            starts_at="2020-02-20T20:20:20.000000Z",
            finishes_at="2020-02-20T23:20:20.000000Z",
            duration=10_800,
            reference="Test name",
            content="Test content",
            areas={
                "ids": ["Bristol", "Skye"],
                "simple_polygons": [BRISTOL, SKYE],
                "names": ["Bristol", "Skye"],
            },
        ),
    )
    # This nets us an 'Alert' msgType:
    service_one["broadcast_channel"] = "severe"
    service_one["permissions"] += ["broadcast"]

    client_request.login(active_user_view_permissions)
    xml_response = client_request.get_response(
        ".get_broadcast_unsigned_xml",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        xml_type="cap",
    )

    assert xml_response.content_type == "application/xml; charset=utf-8"
    assert xml_response.headers.get("Content-Disposition") == f"attachment;filename=Test name-{fake_uuid}.cap.xml"

    assert xml_path(
        xml_response.text,
        "/cap:alert/cap:identifier//text()",
    ) == [fake_uuid]

    assert xml_path(
        xml_response.text,
        "/cap:alert/cap:status//text()",
    ) == ["Actual"]

    assert xml_path(
        xml_response.text,
        "/cap:alert/cap:sent//text()",
    ) == ["2020-02-20T20:20:20-00:00"]

    assert xml_path(
        xml_response.text,
        "/cap:alert/cap:info/cap:language//text()",
    ) == ["en-GB"]

    assert xml_path(
        xml_response.text,
        "/cap:alert/cap:info/cap:expires//text()",
    ) == ["2020-02-20T23:20:20-00:00"]

    assert xml_path(
        xml_response.text,
        "/cap:alert/cap:info/cap:headline//text()",
    ) == ["GOV.UK Emergency Alert"]

    assert xml_path(
        xml_response.text,
        "/cap:alert/cap:info/cap:description//text()",
    ) == ["Test content"]

    assert xml_path(
        xml_response.text,
        "/cap:alert/cap:info/cap:area/cap:areaDesc//text()",
    ) == ["area-1", "area-2"]

    assert xml_path(
        xml_response.text,
        "/cap:alert/cap:info/cap:area/cap:polygon//text()",
    ) == [
        "51.4371,-2.6216 51.4371,-2.575 51.4668,-2.575 51.4668,-2.6216 51.4371,-2.6216",
        "57.1004,-6.828 57.1004,-5.7733 57.7334,-5.7733 57.7334,-6.828 57.1004,-6.828",
    ]

    assert xml_path(
        xml_response.text,
        "/cap:alert/cap:info/cap:event//text()",
    ) == ["Alert"]

    assert xml_path(
        xml_response.text,
        "/cap:alert/cap:info/cap:urgency//text()",
    ) == ["Expected"]

    assert xml_path(
        xml_response.text,
        "/cap:alert/cap:info/cap:severity//text()",
    ) == ["Severe"]

    assert xml_path(
        xml_response.text,
        "/cap:alert/cap:info/cap:certainty//text()",
    ) == ["Likely"]


def test_can_get_unsigned_ibag_xml(
    mocker,
    client_request,
    service_one,
    active_user_view_permissions,
    fake_uuid,
    mock_get_broadcast_message_versions,
    mock_get_areas_by_ids,
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            approved_by_id=fake_uuid,
            starts_at="2020-02-20T20:20:20.000000Z",
            finishes_at="2020-02-20T23:20:20.000000Z",
            duration=10_800,
            reference="Test name",
            content="Test content",
            areas={
                "ids": ["Bristol", "Skye"],
                "simple_polygons": [BRISTOL, SKYE],
                "names": ["Bristol", "Skye"],
            },
        ),
    )
    # This nets us an 'Alert' msgType:
    service_one["broadcast_channel"] = "severe"
    service_one["permissions"] += ["broadcast"]

    client_request.login(active_user_view_permissions)
    xml_response = client_request.get_response(
        ".get_broadcast_unsigned_xml", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid, xml_type="ibag"
    )

    assert xml_response.content_type == "application/xml; charset=utf-8"
    assert xml_response.headers.get("Content-Disposition") == f"attachment;filename=Test name-{fake_uuid}.ibag.xml"

    assert xml_path(
        xml_response.text,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_sending_gateway_id//text()",
        "ibag",
    ) == ["broadcasts@notifications.service.gov.uk"]

    assert xml_path(
        xml_response.text,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_message_number//text()",
        "ibag",
    ) == ["00000001"]

    assert xml_path(
        xml_response.text,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_sender//text()",
        "ibag",
    ) == ["broadcasts@notifications.service.gov.uk"]

    assert xml_path(
        xml_response.text,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_sent_date_time//text()",
        "ibag",
    ) == ["2020-02-20T20:20:20-00:00"]

    assert xml_path(
        xml_response.text,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_status//text()",
        "ibag",
    ) == ["Actual"]

    assert xml_path(
        xml_response.text,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_message_type//text()",
        "ibag",
    ) == ["Alert"]

    assert xml_path(
        xml_response.text,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_cap_alert_uri//text()",
        "ibag",
    ) == ["https://www.gov.uk/alerts"]

    assert xml_path(
        xml_response.text,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_alert_info/ibag:IBAG_text_language//text()",
        "ibag",
    ) == ["English"]

    assert xml_path(
        xml_response.text,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_alert_info/ibag:IBAG_expires_date_time//text()",
        "ibag",
    ) == ["2020-02-20T23:20:20-00:00"]

    assert xml_path(
        xml_response.text,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_alert_info/ibag:IBAG_text_alert_message//text()",
        "ibag",
    ) == ["Test content"]

    assert xml_path(
        xml_response.text,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_alert_info/ibag:IBAG_text_alert_message_length//text()",
        "ibag",
    ) == [str(len("Test content"))]

    assert xml_path(
        xml_response.text,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_alert_info/ibag:IBAG_Alert_Area[1]/ibag:IBAG_area_description//text()",
        "ibag",
    ) == ["area-1"]

    assert xml_path(
        xml_response.text,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_alert_info/ibag:IBAG_Alert_Area[1]/ibag:IBAG_polygon//text()",
        "ibag",
    ) == ["51.4371,-2.6216 51.4371,-2.575 51.4668,-2.575 51.4668,-2.6216 51.4371,-2.6216"]

    assert xml_path(
        xml_response.text,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_alert_info/ibag:IBAG_Alert_Area[2]/ibag:IBAG_area_description//text()",
        "ibag",
    ) == ["area-2"]

    assert xml_path(
        xml_response.text,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_alert_info/ibag:IBAG_Alert_Area[2]/ibag:IBAG_polygon//text()",
        "ibag",
    ) == ["57.1004,-6.828 57.1004,-5.7733 57.7334,-5.7733 57.7334,-6.828 57.1004,-6.828"]

    assert xml_path(
        xml_response.text,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_alert_info/ibag:IBAG_channel_category//text()",
        "ibag",
    ) == [
        "4378-CAT3-ENGLISH"
    ]  # Severe alert

    assert xml_path(
        xml_response.text,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_alert_info/ibag:IBAG_severity//text()",
        "ibag",
    ) == ["Severe"]

    assert xml_path(
        xml_response.text,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_alert_info/ibag:IBAG_urgency//text()",
        "ibag",
    ) == ["Expected"]

    assert xml_path(
        xml_response.text,
        "/ibag:IBAG_Alert_Attributes/ibag:IBAG_alert_info/ibag:IBAG_certainty//text()",
        "ibag",
    ) == ["Likely"]


def test_send_summary_email_section_not_visible_with_no_contacts(
    mocker,
    client_request,
    service_one,
    active_user_create_broadcasts_permission,
    fake_uuid,
    mock_get_broadcast_message_versions,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_count_of_phones,
    mock_get_areas_by_ids,
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            approved_by_id=fake_uuid,
            starts_at="2020-02-20T20:20:20.000000",
            created_at="2020-02-20T20:20:20.000000",
            content="Hello",
            extra_content="Test Extra Content",
            reference="Test Template Reference",
            duration=10_800,
        ),
    )

    client_request.login(active_user_create_broadcasts_permission)

    page = client_request.get(
        ".view_current_broadcast",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )

    keys = [normalize_spaces(p.text) for p in page.select(".govuk-summary-list__key")]
    assert "Send summary email" not in keys


def test_send_summary_email_section_not_visible_with_no_perms(
    mocker,
    client_request,
    service_one,
    active_user_view_permissions,
    fake_uuid,
    mock_get_broadcast_message_versions,
    mock_get_broadcast_returned_for_edit_reasons,
    mock_get_latest_edit_reason,
    mock_get_count_of_phones,
    mock_get_areas_by_ids,
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            created_at="2020-02-20T20:20:20.000000",
            content="Hello",
            extra_content="Test Extra Content",
            reference="Test Template Reference",
            duration=10_800,
        ),
    )

    service_one["alert_notification_addresses"] += ["test@test1.com"]

    client_request.login(active_user_view_permissions)

    page = client_request.get(
        ".view_current_broadcast",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )

    keys = [normalize_spaces(p.text) for p in page.select(".govuk-summary-list__key")]
    assert "Send summary email" not in keys


def test_send_summary_email(
    mocker, client_request, service_one, active_user_create_broadcasts_permission, fake_uuid, mock_get_areas_by_ids
):
    mocker.patch("app.broadcast_message_api_client.get_count_of_phones", return_value=1_000_000)
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            approved_by_id=fake_uuid,
            starts_at="2020-02-20T20:20:20.000000",
            created_at="2020-02-20T20:20:20.000000",
            content="Hello",
            extra_content="Test Extra Content",
            reference="Test Template Reference",
            duration=10_800,
        ),
    )

    client_request.login(active_user_create_broadcasts_permission)

    page = client_request.get(
        ".alert_summary_email",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Send summary email"
    assert page.select_one("textarea")["name"] == "alert_summary"
    assert page.select_one("textarea")["id"] == "alert_summary"
    assert page.select_one("textarea")["data-notify-module"] == "enhanced-textbox"
    assert page.select_one("textarea")["data-highlight-placeholders"] == "false"

    paras = page.select("p.govuk-body")
    for para in paras:
        if "Alert Message" in para.get_text():
            assert "Hello" in para.get_text()
        if "Phone Estimate" in para.get_text():
            assert "More than 1 million phones estimated" in para.get_text()
        if "Additional Info" in para.get_text():
            assert "Test Extra Content" in para.get_text()
        if "Alert duration" in para.get_text():
            assert "3 hours" in para.get_text()

    assert normalize_spaces(page.select(".govuk-button")[5].text) == "Send Email"


def test_send_summary_email_no_perms(
    mocker,
    client_request,
    service_one,
    active_user_view_permissions,
    fake_uuid,
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            approved_by_id=fake_uuid,
            starts_at="2020-02-20T20:20:20.000000",
            created_at="2020-02-20T20:20:20.000000",
            content="Hello",
            extra_content="Test Extra Content",
            reference="Test Template Reference",
            duration=10_800,
        ),
    )

    client_request.login(active_user_view_permissions)

    client_request.get(
        ".alert_summary_email",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _expected_status=403,
    )
