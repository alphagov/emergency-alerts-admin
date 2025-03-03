import json
import math
import uuid
from collections import namedtuple
from functools import partial

import pytest
from flask import url_for
from freezegun import freeze_time

from tests import NotifyBeautifulSoup, broadcast_message_json, sample_uuid, user_json
from tests.app.broadcast_areas.custom_polygons import (
    BD1_1EE,
    BD1_1EE_1,
    BD1_1EE_2,
    BD1_1EE_3,
    BRISTOL,
    HG3_2RL,
    SKYE,
)
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

sample_uuid = sample_uuid()


@pytest.mark.parametrize(
    "endpoint, extra_args, expected_get_status, expected_post_status",
    (
        (
            ".broadcast_dashboard",
            {},
            403,
            405,
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
            405,
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
            ".preview_broadcast_areas",
            {"broadcast_message_id": sample_uuid},
            403,
            405,
        ),
        (
            ".choose_broadcast_library",
            {"broadcast_message_id": sample_uuid},
            403,
            405,
        ),
        (
            ".choose_broadcast_area",
            {"broadcast_message_id": sample_uuid, "library_slug": "countries"},
            403,
            403,
        ),
        (
            ".remove_broadcast_area",
            {"broadcast_message_id": sample_uuid, "area_slug": "countries-E92000001"},
            403,
            405,
        ),
        (
            ".remove_postcode_area",
            {
                "broadcast_message_id": sample_uuid,
                "postcode_slug": "1km around the postcode BD1 1EE in Bradford",
            },
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
            ".cancel_broadcast_message",
            {"broadcast_message_id": sample_uuid},
            403,
            403,
        ),
        (
            ".search_coordinates",
            {
                "broadcast_message_id": sample_uuid,
                "coordinate_type": "latitude_longitude",
                "library_slug": "coordinates",
            },
            403,
            403,
        ),
    ),
)
def test_broadcast_pages_403_without_permission(
    client_request,
    endpoint,
    extra_args,
    expected_get_status,
    expected_post_status,
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
            ".preview_broadcast_areas",
            {"broadcast_message_id": sample_uuid},
            403,
            405,
        ),
        (
            ".choose_broadcast_library",
            {"broadcast_message_id": sample_uuid},
            403,
            405,
        ),
        (
            ".choose_broadcast_area",
            {"broadcast_message_id": sample_uuid, "library_slug": "countries"},
            403,
            403,
        ),
        (
            ".remove_broadcast_area",
            {"broadcast_message_id": sample_uuid, "area_slug": "england"},
            403,
            405,
        ),
        (
            ".remove_postcode_area",
            {
                "broadcast_message_id": sample_uuid,
                "postcode_slug": "1km around the postcode BD1 1EE in Bradford",
            },
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
            "all",
            ".navigation-service-type.navigation-service-type--training",
            "service one Training Switch service",
            "Training",
        ),
        (
            True,
            "test",
            "all",
            ".navigation-service-type.navigation-service-type--training",
            "service one Training Switch service",
            "Training",
        ),
        (
            False,
            "severe",
            "all",
            ".navigation-service-type.navigation-service-type--live",
            "service one Live Switch service",
            "Live",
        ),
        (
            False,
            "operator",
            "all",
            ".navigation-service-type.navigation-service-type--operator",
            "service one Operator Switch service",
            "Operator",
        ),
        (
            False,
            "operator",
            "vodafone",
            ".navigation-service-type.navigation-service-type--operator",
            "service one Operator (Vodafone) Switch service",
            "Operator (Vodafone)",
        ),
        (
            False,
            "test",
            "all",
            ".navigation-service-type.navigation-service-type--test",
            "service one Test Switch service",
            "Test",
        ),
        (
            False,
            "test",
            "vodafone",
            ".navigation-service-type.navigation-service-type--test",
            "service one Test (Vodafone) Switch service",
            "Test (Vodafone)",
        ),
        (
            False,
            "government",
            "all",
            ".navigation-service-type.navigation-service-type--government",
            "service one Government Switch service",
            "Government",
        ),
        (
            False,
            "government",
            "vodafone",
            ".navigation-service-type.navigation-service-type--government",
            "service one Government (Vodafone) Switch service",
            "Government (Vodafone)",
        ),
        (
            False,
            "severe",
            "vodafone",
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
    ),


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
@freeze_time("2020-02-20 02:20")
def test_broadcast_dashboard(
    client_request,
    service_one,
    mock_get_broadcast_messages,
    user,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(user)
    page = client_request.get(
        ".broadcast_dashboard",
        service_id=SERVICE_ONE_ID,
    )

    assert len(page.select(".ajax-block-container")) == len(page.select("h1")) == 1

    assert [normalize_spaces(row.text) for row in page.select(".ajax-block-container")[0].select(".file-list")] == [
        "Half an hour ago This is a test Waiting for approval Area: England Scotland",
        "Hour and a half ago This is a test Waiting for approval Area: England Scotland",
        "Example template This is a test live since today at 2:20am Area: England Scotland",
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
    endpoint,
    user,
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
    active_user_create_broadcasts_permission,
    endpoint,
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
    client_request,
    service_one,
    mock_get_broadcast_messages,
    user,
):
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
    client_request,
    service_one,
    mock_get_broadcast_messages,
    user,
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
        "Example template rejected today at 1:20am This is a test",
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

    assert normalize_spaces(page.select_one("label[for=name]").text) == "Reference"
    assert page.select_one("input[type=text]")["name"] == "name"

    assert normalize_spaces(page.select_one("label[for=template_content]").text) == "Alert message"
    assert page.select_one("textarea")["name"] == "template_content"
    assert page.select_one("textarea")["data-notify-module"] == "enhanced-textbox"
    assert page.select_one("textarea")["data-highlight-placeholders"] == "false"

    assert (page.select_one("[data-notify-module=update-status]")["data-updates-url"]) == url_for(
        ".count_content_length",
        service_id=SERVICE_ONE_ID,
        template_type="broadcast",
    )

    assert (
        (page.select_one("[data-notify-module=update-status]")["data-target"])
        == (page.select_one("textarea")["id"])
        == "template_content"
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
            "name": "My new alert",
            "template_content": "This is a test",
        },
        _expected_redirect=url_for(
            ".choose_broadcast_library",
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
            "name": "My new alert",
            "template_content": content,
        },
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one(".error-message").text) == (expected_error_message)
    assert mock_create_broadcast_message.called is False


def test_broadcast_page(
    client_request,
    service_one,
    fake_uuid,
    mock_create_broadcast_message,
    active_user_create_broadcasts_permission,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    client_request.get(
        ".broadcast",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _expected_redirect=url_for(
            ".choose_broadcast_library",
            service_id=SERVICE_ONE_ID,
            broadcast_message_id=fake_uuid,
        ),
    ),


@pytest.mark.parametrize(
    "areas_selected, areas_listed, estimates",
    (
        (
            [
                "ctry19-E92000001",
                "ctry19-S92000003",
            ],
            [
                "England Remove England",
                "Scotland Remove Scotland",
            ],
            [
                "An area of 100,000 square miles Will get the alert",
                "An extra area of 6,000 square miles is Likely to get the alert",
                "40,000,000 phones estimated",
            ],
        ),
        (
            [
                "wd23-E05014242",
                "wd23-E05014243",
            ],
            [
                "Penrith North Remove Penrith North",
                "Penrith South Remove Penrith South",
            ],
            [
                "An area of 10 square miles Will get the alert",
                "An extra area of 30 square miles is Likely to get the alert",
                "10,000 phones estimated",
            ],
        ),
        (
            [
                "lad23-E09000019",
            ],
            [
                "Islington Remove Islington",
            ],
            [
                "An area of 6 square miles Will get the alert",
                "An extra area of 4 square miles is Likely to get the alert",
                "200,000 to 500,000 phones",
            ],
        ),
        (
            [
                "ctyua23-E10000019",
            ],
            [
                "Lincolnshire Remove Lincolnshire",
            ],
            [
                "An area of 2,000 square miles Will get the alert",
                "An extra area of 500 square miles is Likely to get the alert",
                "500,000 to 600,000 phones",
            ],
        ),
        (
            ["ctyua23-E10000019", "lad23-E06000065"],
            [
                "Lincolnshire Remove Lincolnshire",
                "North Yorkshire Remove North Yorkshire",
            ],
            [
                "An area of 6,000 square miles Will get the alert",
                "An extra area of 1,000 square miles is Likely to get the alert",
                "1,000,000 phones estimated",
            ],
        ),
        (
            [
                "pfa23-E23000035",
            ],
            [
                "Devon & Cornwall Remove Devon & Cornwall",
            ],
            [
                "An area of 4,000 square miles Will get the alert",
                "An extra area of 800 square miles is Likely to get the alert",
                "1,000,000 phones estimated",
            ],
        ),
        (
            [
                "pfa23-LONDON",
            ],
            [
                "London (Metropolitan & City of London) Remove London (Metropolitan & City of London)",
            ],
            [
                "An area of 600 square miles Will get the alert",
                "An extra area of 70 square miles is Likely to get the alert",
                "6,000,000 phones estimated",
            ],
        ),
    ),
)
def test_preview_broadcast_areas_page(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    areas_selected,
    areas_listed,
    estimates,
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
            area_ids=areas_selected,
        ),
    )
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        ".preview_broadcast_areas",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )

    assert [normalize_spaces(item.text) for item in page.select("ul.area-list li.area-list-item")] == areas_listed

    assert len(page.select("#area-list-map")) == 1

    assert [normalize_spaces(item.text) for item in page.select(".area-list-key")] == estimates


@pytest.mark.parametrize(
    "polygons, expected_list_items",
    (
        (
            [
                [[1, 2], [3, 4], [5, 6]],
                [[7, 8], [9, 10], [11, 12]],
            ],
            [
                "An area of 800 square miles Will get the alert",
                "An extra area of 2,000 square miles is Likely to get the alert",
                "Unknown number of phones",
            ],
        ),
        (
            [BRISTOL],
            [
                "An area of 4 square miles Will get the alert",
                "An extra area of 3 square miles is Likely to get the alert",
                "70,000 to 100,000 phones",
            ],
        ),
        (
            [SKYE],
            [
                "An area of 2,000 square miles Will get the alert",
                "An extra area of 600 square miles is Likely to get the alert",
                "7,000 phones estimated",
            ],
        ),
        (
            [BD1_1EE_1],
            [
                "An area of 1 square miles Will get the alert",
                "An extra area of 3 square miles is Likely to get the alert",
                "10,000 to 50,000 phones",
            ],
        ),
        (
            [BD1_1EE_2],
            [
                "An area of 5 square miles Will get the alert",
                "An extra area of 5 square miles is Likely to get the alert",
                "50,000 to 100,000 phones",
            ],
        ),
        (
            [BD1_1EE_3],
            [
                "An area of 10 square miles Will get the alert",
                "An extra area of 7 square miles is Likely to get the alert",
                "100,000 to 200,000 phones",
            ],
        ),
        (
            [BD1_1EE],
            [
                "An area of 10 square miles Will get the alert",
                "An extra area of 7 square miles is Likely to get the alert",
                "100,000 to 200,000 phones",
            ],
        ),
        (
            [HG3_2RL],
            [
                "An area of 30 square miles Will get the alert",
                "An extra area of 60 square miles is Likely to get the alert",
                "2,000 to 10,000 phones",
            ],
        ),
    ),
)
def test_preview_broadcast_areas_page_with_custom_polygons(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    polygons,
    expected_list_items,
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
            areas={
                "names": ["Area one", "Area two", "Area three"],
                "simple_polygons": polygons,
            },
        ),
    )
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        ".preview_broadcast_areas",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )

    assert [normalize_spaces(item.text) for item in page.select("ul.area-list li.area-list-item")] == [
        "Area one Remove Area one",
        "Area two Remove Area two",
        "Area three Remove Area three",
    ]

    assert len(page.select("#area-list-map")) == 1

    assert [normalize_spaces(item.text) for item in page.select(".area-list-key")] == expected_list_items


@pytest.mark.parametrize(
    "area_ids, expected_list",
    (
        (
            [
                # Countries have no parent areas
                "ctry19-E92000001",
                "ctry19-S92000003",
            ],
            [
                "Countries",
                "Local authorities",
                "Police forces in England and Wales",
                "Test areas",
            ],
        ),
        (
            [
                # If you’ve chosen the whole of a county or unitary authority
                # there’s no reason to  also pick districts of it
                "ctyua23-E10000013",  # Gloucestershire, a county
                "lad23-E06000052",  # Cornwall, a unitary authority
            ],
            [
                "Countries",
                "Local authorities",
                "Police forces in England and Wales",
                "Test areas",
            ],
        ),
        (
            [
                "wd23-E05004299",  # Pitville, in Cheltenham, in Gloucestershire
                "wd23-E05004290",  # Benhall and the Reddings, in Cheltenham, in Gloucestershire
                "wd23-E05010951",  # Abbeymead, in Gloucester, in Gloucestershire
                "wd23-S13003154",  # Shetland Central, in Shetland Isles
                "lad23-E07000037",  # High Peak, a district in Derbyshire
            ],
            [
                "Cheltenham",
                "Derbyshire",
                "Gloucester",
                "Gloucestershire",
                "Shetland Islands",
                # ---
                "Countries",
                "Local authorities",
                "Police forces in England and Wales",
                "Test areas",
            ],
        ),
    ),
)
def test_choose_broadcast_library_page(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    active_user_create_broadcasts_permission,
    area_ids,
    expected_list,
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
        ".choose_broadcast_library",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )
    assert [normalize_spaces(title.text) for title in page.select("main a.govuk-link")] == expected_list

    assert normalize_spaces(page.select(".file-list-hint-large")[0].text) == (
        "England, Northern Ireland, Scotland and Wales"
    )

    assert page.select_one("a.file-list-filename-large.govuk-link")["href"] == url_for(
        ".choose_broadcast_area",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug="ctry19",
    )


@pytest.mark.parametrize(
    "area_ids, expected_list",
    (
        (
            ["1km around the postcode BD1 1EE in Bradford"],
            [
                "Coordinates",
                "Countries",
                "Local authorities",
                "Police forces in England and Wales",
                "Postcode areas",
                "Test areas",
            ],
        ),
        (
            ["3km around the postcode BD1 1EE in Bradford"],
            [
                "Coordinates",
                "Countries",
                "Local authorities",
                "Police forces in England and Wales",
                "Postcode areas",
                "Test areas",
            ],
        ),
        (
            ["5km around the coordinates [54.0, -1.7] in Harrogate"],
            [
                "Coordinates",
                "Countries",
                "Local authorities",
                "Police forces in England and Wales",
                "Postcode areas",
                "Test areas",
            ],
        ),
    ),
)
def test_choose_broadcast_library_page_with_custom_broadcast(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    active_user_create_broadcasts_permission,
    area_ids,
    expected_list,
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
        ".choose_broadcast_library",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )
    assert [normalize_spaces(title.text) for title in page.select("main a.govuk-link")] == expected_list

    assert normalize_spaces(page.select(".file-list-hint-large")[0].text) == (
        "Use coordinates to create an alert area."
    )

    assert page.select_one("a.file-list-filename-large.govuk-link")["href"] == url_for(
        ".choose_broadcast_area",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug="coordinates",
    )


def test_suggested_area_has_correct_link(
    mocker,
    client_request,
    service_one,
    fake_uuid,
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
            area_ids=[
                "wd23-E05004299",  # Pitville, a ward of Cheltenham
            ],
        ),
    )
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        ".choose_broadcast_library", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid, custom_broadcast=False
    )
    link = page.select_one("main a.govuk-link")

    assert link.text == "Cheltenham"
    assert link["href"] == url_for(
        "main.choose_broadcast_sub_area",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug="wd23-lad23-ctyua23",
        area_slug="lad23-E07000078",
    )


@pytest.mark.parametrize(
    "library_slug, expected_page_title",
    (
        (
            "ctry19",
            "Choose countries",
        ),
        ("wd23-lad23-ctyua23", "Choose a local authority"),
        ("pfa23", "Choose police forces in England and Wales"),
        (
            "test",
            "Choose test areas",
        ),
        ("postcodes", "Choose alert area"),
        ("coordinates", "Choose coordinate type"),
    ),
)
def test_choose_broadcast_area_page_titles(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    fake_uuid,
    active_user_create_broadcasts_permission,
    library_slug,
    expected_page_title,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        ".choose_broadcast_area",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug=library_slug,
        _follow_redirects=True,
    )
    assert normalize_spaces(page.select_one("h1").text) == expected_page_title


def test_choose_broadcast_area_page(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    fake_uuid,
    active_user_create_broadcasts_permission,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        ".choose_broadcast_area",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug="ctry19",
    )
    assert [
        (
            choice.select_one("input")["value"],
            normalize_spaces(choice.select_one("label").text),
        )
        for choice in page.select("form[method=post] .govuk-checkboxes__item")
    ] == [
        ("ctry19-E92000001", "England"),
        ("ctry19-N92000002", "Northern Ireland"),
        ("ctry19-S92000003", "Scotland"),
        ("ctry19-W92000004", "Wales"),
    ]


def test_choose_broadcast_area_page_for_area_with_sub_areas(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    fake_uuid,
    active_user_create_broadcasts_permission,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        ".choose_broadcast_area",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug="wd23-lad23-ctyua23",
    )
    assert normalize_spaces(page.select_one("h1").text) == "Choose a local authority"
    live_search = page.select_one("[data-notify-module=live-search]")
    assert live_search["data-targets"] == ".file-list-item"
    assert live_search.select_one("input")["type"] == "search"
    partial_url_for = partial(
        url_for,
        "main.choose_broadcast_sub_area",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug="wd23-lad23-ctyua23",
    )
    choices = [
        (
            choice.select_one("a.file-list-filename-large")["href"],
            normalize_spaces(choice.text),
        )
        for choice in page.select(".file-list-item")
    ]
    assert len(choices) == 382

    # First item, somewhere in Scotland
    assert choices[0] == (
        partial_url_for(area_slug="lad23-S12000033"),
        "Aberdeen City",
    )

    # Somewhere in England
    # ---
    # Note: we don't populate prev_area_slug query param, so the back link will come here rather than to a county page,
    # even though ashford belongs to kent
    assert choices[12] == (
        partial_url_for(area_slug="lad23-E07000200"),
        "Babergh",
    )

    # Somewhere in Wales
    assert choices[219] == (
        partial_url_for(area_slug="lad23-W06000022"),
        "Newport",
    )

    # Somewhere in Northern Ireland
    assert choices[21] == (
        partial_url_for(area_slug="lad23-N09000003"),
        "Belfast",
    )

    # Last item on the page
    assert choices[-1] == (
        partial_url_for(area_slug="lad23-E06000014"),
        "York",
    )


def test_choose_broadcast_sub_area_page_for_district_shows_checkboxes_for_wards(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    fake_uuid,
    active_user_create_broadcasts_permission,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        "main.choose_broadcast_sub_area",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug="wd23-lad23-ctyua23",
        area_slug="lad23-S12000033",
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
        ("wd23-S13002845", "Airyhall/Broomhill/Garthdee"),
        ("wd23-S13002836", "Bridge of Don"),
    ]
    assert sub_choices[:3] == [
        ("wd23-S13002845", "Airyhall/Broomhill/Garthdee"),
        ("wd23-S13002836", "Bridge of Don"),
        ("wd23-S13002835", "Dyce/Bucksburn/Danestone"),
    ]
    assert (
        all_choices[-1:]
        == sub_choices[-1:]
        == [
            ("wd23-S13002846", "Torry/Ferryhill"),
        ]
    )


@pytest.mark.parametrize(
    "prev_area_slug, expected_back_link_url, expected_back_link_extra_kwargs",
    [
        ("ctyua23-E10000016", "main.choose_broadcast_sub_area", {"area_slug": "ctyua23-E10000016"}),  # Kent
        (None, ".choose_broadcast_area", {}),
    ],
)
def test_choose_broadcast_sub_area_page_for_district_has_back_link(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    active_user_create_broadcasts_permission,
    prev_area_slug,
    expected_back_link_url,
    expected_back_link_extra_kwargs,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        "main.choose_broadcast_sub_area",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=str(uuid.UUID(int=0)),
        library_slug="wd23-lad23-ctyua23",
        area_slug="lad23-E07000105",  # Ashford
        prev_area_slug=prev_area_slug,
    )
    assert normalize_spaces(page.select_one("h1").text) == "Choose an area of Ashford"
    back_link = page.select_one(".govuk-back-link")
    assert back_link["href"] == url_for(
        expected_back_link_url,
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=str(uuid.UUID(int=0)),
        library_slug="wd23-lad23-ctyua23",
        **expected_back_link_extra_kwargs,
    )


def test_write_new_broadcast_does_update_when_broadcast_exists(
    mocker,
    client_request,
    service_one,
    active_user_create_broadcasts_permission,
    mock_create_broadcast_message,
    mock_update_broadcast_message,
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
    client_request.get(
        "main.write_new_broadcast", service_id=SERVICE_ONE_ID, broadcast_message_id=str(uuid.UUID(int=0))
    )

    client_request.post(
        ".write_new_broadcast",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=str(uuid.UUID(int=0)),
        _data={
            "name": "Emergency broadcast",
            "template_content": "Broadcast content",
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
def test_preview_broadcast_areas_has_back_link_with_uuid(
    mocker,
    client_request,
    service_one,
    active_user_create_broadcasts_permission,
    expected_back_link_url,
    expected_back_link_extra_kwargs,
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
        "main.preview_broadcast_areas", service_id=SERVICE_ONE_ID, broadcast_message_id=str(uuid.UUID(int=0))
    )
    assert normalize_spaces(page.select_one("h1").text) == "Confirm the area for the alert"
    back_link = page.select_one(".govuk-back-link")
    assert back_link["href"] == url_for(
        expected_back_link_url,
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=str(uuid.UUID(int=0)),
        **expected_back_link_extra_kwargs,
    )


def test_write_new_broadcast_content_from_uuid_is_displayed_before_live(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    active_user_create_broadcasts_permission,
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
    page = client_request.get("main.write_new_broadcast", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid)

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
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get("main.write_new_broadcast", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid)
    assert normalize_spaces(page.select_one("input").text) == ""


def test_choose_broadcast_sub_area_page_for_county_shows_links_for_districts(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    fake_uuid,
    active_user_create_broadcasts_permission,
):
    service_one["permissions"] += ["broadcast"]

    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        "main.choose_broadcast_sub_area",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug="wd23-lad23-ctyua23",
        area_slug="ctyua23-E10000016",  # Kent
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
        "main.choose_broadcast_sub_area",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug="wd23-lad23-ctyua23",
        area_slug="lad23-E07000105",
        prev_area_slug="ctyua23-E10000016",  # Kent
    )
    assert districts[0][1] == "Ashford"
    assert districts[-1][0] == url_for(
        "main.choose_broadcast_sub_area",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug="wd23-lad23-ctyua23",
        area_slug="lad23-E07000116",
        prev_area_slug="ctyua23-E10000016",  # Kent
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
):
    service_one["permissions"] += ["broadcast"]
    polygon_class = namedtuple("polygon_class", ["as_coordinate_pairs_lat_long"])
    coordinates = [[50.1, 0.1], [50.2, 0.2], [50.3, 0.2]]
    polygons = polygon_class(as_coordinate_pairs_lat_long=coordinates)
    mock_get_polygons_from_areas = mocker.patch(
        "app.models.broadcast_message.BroadcastMessage.get_polygons_from_areas",
        return_value=polygons,
    )
    mock_get_broadcast_message = mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            template_id=fake_uuid,
            created_by_id=fake_uuid,
            service_id=SERVICE_ONE_ID,
            status="draft",
            area_ids=["ctry19-E92000001", "ctry19-W92000004"],
            areas={
                "ids": ["ctry19-E92000001", "ctry19-W92000004"],
                "names": ["England", "Wales"],
                "simple_polygons": [polygons],
            },
        ),
    )

    client_request.login(active_user_create_broadcasts_permission)
    client_request.post(
        ".choose_broadcast_area",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug="ctry19",
        _data={"areas": ["ctry19-E92000001", "ctry19-W92000004"]},
    )
    mock_get_polygons_from_areas.assert_called_once_with(area_attribute="simple_polygons")
    mock_get_broadcast_message.assert_called_once_with(service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid)

    mock_update_broadcast_message.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        data={
            "areas": {
                "ids": ["ctry19-E92000001", "ctry19-W92000004"],
                "names": ["England", "Wales"],
                "aggregate_names": ["England", "Wales"],
                "simple_polygons": coordinates,
            }
        },
    )


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
                "simple_polygons": [BD1_1EE_1],
                "names": ["1km around the postcode BD1 1EE in Bradford"],
            },
        ),
    )

    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.post(
        ".search_postcodes",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug="postcodes",
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
            {"postcode": "BD1 1EE", "radius": "2", "preview": True},
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
            {"postcode": "BD1 1EE", "radius": "3", "preview": True},
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
                "simple_polygons": [BD1_1EE_1],
                "names": ["1km around the postcode BD1 1EE in Bradford"],
            },
        ),
    )

    client_request.login(active_user_create_broadcasts_permission)
    client_request.post(
        ".search_postcodes",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug="postcodes",
        _data=post_data,
        _follow_redirects=True,
    )
    mock_update_broadcast_message.assert_called_once()
    assert (
        mock_update_broadcast_message._mock_call_args[1]["data"]["areas"]["names"]
        == update_broadcast_data["areas"]["names"]
    )
    assert (
        mock_update_broadcast_message._mock_call_args[1]["data"]["areas"]["ids"]
        == update_broadcast_data["areas"]["ids"]
    )
    assert (
        mock_update_broadcast_message._mock_call_args[1]["data"]["areas"]["aggregate_names"]
        == update_broadcast_data["areas"]["aggregate_names"]
    )

    actual_polygons = mock_update_broadcast_message._mock_call_args[1]["data"]["areas"]["simple_polygons"]
    expected_polygons = update_broadcast_data["areas"]["simple_polygons"]

    for coords1, coords2 in zip(actual_polygons, expected_polygons):
        for coord1, coord2 in zip(coords1, coords2):
            assert all(abs(a - b) < math.exp(1e-12) for a, b in zip(coord1, coord2))

    assert mock_get_broadcast_message.call_count == 2


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
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug="coordinates",
        coordinate_type="latitude_longitude",
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
            {"first_coordinate": "54", "second_coordinate": "-1.7", "radius": "5", "preview": True},
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
            {"first_coordinate": "53.793", "second_coordinate": "-1.75", "radius": "3", "preview": True},
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
    client_request.post(
        ".search_coordinates",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug="coordinates",
        coordinate_type="latitude_longitude",
        _data=post_data,
        _follow_redirects=True,
    )

    mock_update_broadcast_message.assert_called_once()
    assert (
        mock_update_broadcast_message._mock_call_args[1]["data"]["areas"]["names"]
        == update_broadcast_data["areas"]["names"]
    )
    assert (
        mock_update_broadcast_message._mock_call_args[1]["data"]["areas"]["ids"]
        == update_broadcast_data["areas"]["ids"]
    )
    assert (
        mock_update_broadcast_message._mock_call_args[1]["data"]["areas"]["aggregate_names"]
        == update_broadcast_data["areas"]["aggregate_names"]
    )

    actual_polygons = mock_update_broadcast_message._mock_call_args[1]["data"]["areas"]["simple_polygons"]
    expected_polygons = update_broadcast_data["areas"]["simple_polygons"]

    for coords1, coords2 in zip(actual_polygons, expected_polygons):
        for coord1, coord2 in zip(coords1, coords2):
            assert all(abs(a - b) < math.exp(1e-12) for a, b in zip(coord1, coord2))

    assert mock_get_broadcast_message.call_count == 2


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
        broadcast_message_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        library_slug="coordinates",
        coordinate_type="easting_northing",
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
            {"first_coordinate": "419763", "second_coordinate": "456038", "radius": "5", "preview": True},
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
            {"first_coordinate": "416567", "second_coordinate": "432994", "radius": "3", "preview": True},
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
    client_request.post(
        ".search_coordinates",
        broadcast_message_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        library_slug="coordinates",
        coordinate_type="easting_northing",
        _data=post_data,
        _follow_redirects=True,
    )
    mock_update_broadcast_message.assert_called_once()

    assert (
        mock_update_broadcast_message._mock_call_args[1]["data"]["areas"]["names"]
        == update_broadcast_data["areas"]["names"]
    )
    assert (
        mock_update_broadcast_message._mock_call_args[1]["data"]["areas"]["ids"]
        == update_broadcast_data["areas"]["ids"]
    )
    assert (
        mock_update_broadcast_message._mock_call_args[1]["data"]["areas"]["aggregate_names"]
        == update_broadcast_data["areas"]["aggregate_names"]
    )

    actual_polygons = mock_update_broadcast_message._mock_call_args[1]["data"]["areas"]["simple_polygons"]
    expected_polygons = update_broadcast_data["areas"]["simple_polygons"]

    for coords1, coords2 in zip(actual_polygons, expected_polygons):
        for coord1, coord2 in zip(coords1, coords2):
            assert all(abs(a - b) < math.exp(1e-12) for a, b in zip(coord1, coord2))
    assert mock_get_broadcast_message.call_count == 2


@pytest.mark.parametrize(
    "post_data, expected_error",
    (
        (
            {"first_coordinate": "419763.0000000", "second_coordinate": "456038", "radius": "5"},
            ["Enter a value with 6 decimal places"],
        ),
        (
            {"first_coordinate": "419763", "second_coordinate": "456038", "radius": "5.555"},
            ["Enter a value with 2 decimal places"],
        ),
        (
            {
                "first_coordinate": "419763.0000000",
                "second_coordinate": "456038",
                "radius": "5.555",
            },
            ["Enter a value with 6 decimal places", "Enter a value with 2 decimal places"],
        ),
        (
            {"first_coordinate": "", "second_coordinate": "", "radius": "", "radius_btn": True},
            ["The easting and northing must be within the UK", "Enter a radius between 0.1km and 38.0km"],
        ),
        (
            {"first_coordinate": "", "second_coordinate": "", "radius": "", "search_btn": True},
            [
                "The easting and northing must be within the UK",
            ],
        ),
    ),
)
def test_easting_northing_coordinate_area_form_errors(
    client_request,
    service_one,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
    post_data,
    expected_error,
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
        broadcast_message_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        library_slug="coordinates",
        coordinate_type="easting_northing",
        _data=post_data,
        _follow_redirects=True,
    )

    form = page.select_one("form")
    error_list = [
        normalize_spaces([error])
        for error in page.select(".govuk-error-summary__list a")
        if normalize_spaces([error]) != ""
    ]
    assert error_list == expected_error
    assert normalize_spaces(form.select_one("button").text) == "Search"
    assert mock_get_broadcast_message.call_count == 1


@pytest.mark.parametrize(
    "post_data, expected_error",
    (
        (
            {"first_coordinate": "54.0000000", "second_coordinate": "-2", "radius": "5"},
            ["Enter a value with 6 decimal places"],
        ),
        (
            {"first_coordinate": "54", "second_coordinate": "-2", "radius": "5.555"},
            ["Enter a value with 2 decimal places"],
        ),
        (
            {
                "first_coordinate": "54.0000000",
                "second_coordinate": "-2",
                "radius": "5.555",
            },
            ["Enter a value with 6 decimal places", "Enter a value with 2 decimal places"],
        ),
        (
            {"first_coordinate": "", "second_coordinate": "", "radius": "", "radius_btn": True},
            ["The latitude and longitude must be within the UK", "Enter a radius between 0.1km and 38.0km"],
        ),
        (
            {"first_coordinate": "", "second_coordinate": "", "radius": "", "search_btn": True},
            ["The latitude and longitude must be within the UK"],
        ),
    ),
)
def test_latitude_longitude_coordinate_area_form_errors(
    client_request,
    service_one,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
    post_data,
    expected_error,
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
        broadcast_message_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        library_slug="coordinates",
        coordinate_type="latitude_longitude",
        _data=post_data,
        _follow_redirects=True,
    )

    form = page.select_one("form")
    error_list = [
        normalize_spaces([error])
        for error in page.select(".govuk-error-summary__list a")
        if normalize_spaces([error]) != ""
    ]
    assert error_list == expected_error
    assert normalize_spaces(form.select_one("button").text) == "Search"
    assert mock_get_broadcast_message.call_count == 1


@pytest.mark.parametrize(
    "post_data, coordinate_type, expected_error",
    (
        (
            {"first_coordinate": "0", "second_coordinate": "", "radius": "0"},
            "latitude_longitude",
            ["The latitude and longitude must be within the UK", "Enter a radius between 0.1km and 38.0km"],
        ),
        (
            {"first_coordinate": "0", "second_coordinate": "-10", "radius": "0"},
            "latitude_longitude",
            ["The latitude and longitude must be within the UK", "Enter a radius between 0.1km and 38.0km"],
        ),
        (
            {"first_coordinate": "0", "second_coordinate": "-10", "radius": "/"},
            "latitude_longitude",
            ["The latitude and longitude must be within the UK", "Enter a radius between 0.1km and 38.0km"],
        ),
        (
            {"first_coordinate": "0", "second_coordinate": "-10", "radius": "/"},
            "easting_northing",
            ["The easting and northing must be within the UK", "Enter a radius between 0.1km and 38.0km"],
        ),
    ),
)
def test_latitude_longitude_coordinate_area_form_error_with_invalid_coords(
    client_request,
    service_one,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
    post_data,
    coordinate_type,
    expected_error,
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
        ".search_coordinates",
        broadcast_message_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        library_slug="coordinates",
        coordinate_type=coordinate_type,
        _data=post_data,
        _follow_redirects=True,
    )

    form = page.select_one("form")
    error_list = [
        normalize_spaces([error])
        for error in page.select(".govuk-error-summary__list a")
        if normalize_spaces([error]) != ""
    ]
    assert error_list == expected_error
    assert normalize_spaces(form.select_one("button").text) == "Search"
    assert mock_get_broadcast_message.call_count == 1


@pytest.mark.parametrize(
    "post_data, coordinate_type, expected_error",
    (
        (
            {"first_coordinate": "0", "second_coordinate": "0", "radius": "5"},
            "latitude_longitude",
            [
                "The latitude and longitude must be within the UK",
            ],
        ),
        (
            {"first_coordinate": "50", "second_coordinate": "-2", "radius": "5"},
            "latitude_longitude",
            [
                "The latitude and longitude must be within the UK",
            ],
        ),
        (
            {"first_coordinate": "50", "second_coordinate": "50", "radius": "5"},
            "latitude_longitude",
            [
                "The latitude and longitude must be within the UK",
            ],
        ),
        (
            {"first_coordinate": "0", "second_coordinate": "0", "radius": "5"},
            "easting_northing",
            [
                "The easting and northing must be within the UK",
            ],
        ),
        (
            {"first_coordinate": "170000", "second_coordinate": "170000", "radius": "5"},
            "easting_northing",
            [
                "The easting and northing must be within the UK",
            ],
        ),
    ),
)
def test_non_uk_coordinate_area_form_errors(
    client_request,
    service_one,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
    post_data,
    coordinate_type,
    expected_error,
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
        ".search_coordinates",
        broadcast_message_id=fake_uuid,
        service_id=SERVICE_ONE_ID,
        library_slug="coordinates",
        coordinate_type=coordinate_type,
        _data=post_data,
        _follow_redirects=True,
    )
    form = page.select_one("form")
    error_list = [
        normalize_spaces([error])
        for error in page.select(".govuk-error-summary__list a")
        if normalize_spaces([error]) != ""
    ]
    assert error_list == expected_error
    assert normalize_spaces(form.select_one("button").text) == "Search"
    assert mock_get_broadcast_message.call_count == 1


@pytest.mark.parametrize(
    "post_data, expected_errors",
    (
        (
            {"postcode": "", "radius": "", "search_btn": True},
            ["Enter a postcode within the UK"],
        ),
        (
            {"postcode": "", "radius": "", "radius_btn": True},
            ["Enter a postcode within the UK", "Enter a radius between 0.1km and 38.0km"],
        ),
        (
            {"postcode": "TEST", "radius": "10"},
            ["Enter a postcode within the UK"],
        ),
        (
            {"postcode": "", "radius": "10"},
            ["Enter a postcode within the UK"],
        ),
        (
            {"postcode": "BD1 1EP", "radius": ""},
            ["Enter a postcode within the UK"],
        ),
    ),
)
def test_incorrect_input_postcode_form_errors(
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
        broadcast_message_id=fake_uuid,
        library_slug="postcodes",
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
        broadcast_message_id=fake_uuid,
        library_slug="postcodes",
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
    "post_data, expected_data",
    (
        (
            {"select_all": "y", "areas": ["wd23-S13002845"]},
            {
                # wd23-S13002845 is ignored because the user chose ‘Select all…’
                "ids": ["lad23-S12000033"],
                "names": ["Aberdeen City"],
                "aggregate_names": ["Aberdeen City"],
            },
        ),
        (
            {"areas": ["wd23-S13002845", "wd23-S13002836"]},
            {
                "ids": ["wd23-S13002845", "wd23-S13002836"],
                "names": ["Bridge of Don", "Airyhall/Broomhill/Garthdee"],
                "aggregate_names": ["Aberdeen City"],
            },
        ),
    ),
)
def test_add_broadcast_sub_area_district_view(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    post_data,
    expected_data,
    mocker,
    active_user_create_broadcasts_permission,
):
    service_one["permissions"] += ["broadcast"]
    polygon_class = namedtuple("polygon_class", ["as_coordinate_pairs_lat_long"])
    coordinates = [[50.1, 0.1], [50.2, 0.2], [50.3, 0.2]]
    polygons = polygon_class(as_coordinate_pairs_lat_long=coordinates)
    mock_get_polygons_from_areas = mocker.patch(
        "app.models.broadcast_message.BroadcastMessage.get_polygons_from_areas",
        return_value=polygons,
    )

    client_request.login(active_user_create_broadcasts_permission)
    client_request.post(
        ".choose_broadcast_sub_area",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug="wd23-lad23-ctyua23",
        area_slug="lad23-S12000033",
        _data=post_data,
    )

    # These two areas are on the broadcast already
    expected_data["ids"] = ["ctry19-E92000001", "ctry19-S92000003"] + expected_data["ids"]
    expected_data["names"] = ["England", "Scotland"] + expected_data["names"]
    expected_data["aggregate_names"] = sorted(["England", "Scotland"] + expected_data["aggregate_names"])

    mock_get_polygons_from_areas.assert_called_once_with(area_attribute="simple_polygons")
    mock_update_broadcast_message.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        data={
            "areas": {
                "simple_polygons": coordinates,
                **expected_data,
            }
        },
    )


def test_add_broadcast_sub_area_county_view(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
):
    service_one["permissions"] += ["broadcast"]
    polygon_class = namedtuple("polygon_class", ["as_coordinate_pairs_lat_long"])
    coordinates = [[50.1, 0.1], [50.2, 0.2], [50.3, 0.2]]
    polygons = polygon_class(as_coordinate_pairs_lat_long=coordinates)
    mock_get_polygons_from_areas = mocker.patch(
        "app.models.broadcast_message.BroadcastMessage.get_polygons_from_areas",
        return_value=polygons,
    )

    client_request.login(active_user_create_broadcasts_permission)
    client_request.post(
        ".choose_broadcast_sub_area",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        library_slug="wd23-lad23-ctyua23",
        area_slug="ctyua23-E10000016",  # Kent
        _data={"select_all": "y"},
    )
    mock_get_polygons_from_areas.assert_called_once_with(area_attribute="simple_polygons")
    mock_update_broadcast_message.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        data={
            "areas": {
                "simple_polygons": coordinates,
                "ids": [
                    # These two areas are on the broadcast already
                    "ctry19-E92000001",
                    "ctry19-S92000003",
                ]
                + ["ctyua23-E10000016"],
                "names": ["England", "Scotland", "Kent"],
                "aggregate_names": ["England", "Kent", "Scotland"],
            }
        },
    )


def test_remove_broadcast_area_page(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
):
    service_one["permissions"] += ["broadcast"]
    polygon_class = namedtuple("polygon_class", ["as_coordinate_pairs_lat_long"])
    coordinates = [[50.1, 0.1], [50.2, 0.2], [50.3, 0.2]]
    polygons = polygon_class(as_coordinate_pairs_lat_long=coordinates)
    mock_get_polygons_from_areas = mocker.patch(
        "app.models.broadcast_message.BroadcastMessage.get_polygons_from_areas",
        return_value=polygons,
    )

    client_request.login(active_user_create_broadcasts_permission)
    client_request.get(
        ".remove_broadcast_area",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        area_slug="ctry19-E92000001",
        _expected_redirect=url_for(
            ".preview_broadcast_areas",
            service_id=SERVICE_ONE_ID,
            broadcast_message_id=fake_uuid,
        ),
    )
    mock_get_polygons_from_areas.assert_called_once_with(area_attribute="simple_polygons")
    mock_update_broadcast_message.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        data={
            "areas": {
                "simple_polygons": coordinates,
                "names": ["Scotland"],
                "aggregate_names": ["Scotland"],
                "ids": ["ctry19-S92000003"],
            },
        },
    )


def test_remove_postcode_area(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    mock_update_broadcast_message,
    fake_uuid,
    mocker,
    active_user_create_broadcasts_permission,
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
        ".remove_postcode_area",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        postcode_slug="1km around the postcode BD1 1EE in Bradford",
        _expected_redirect=url_for(
            ".choose_broadcast_area",
            service_id=SERVICE_ONE_ID,
            broadcast_message_id=fake_uuid,
            library_slug="postcodes",
        ),
    )
    mock_get_broadcast_message.assert_called_once_with(service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid)
    mock_update_broadcast_message.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        data={
            "areas": {
                "ids": [],
                "names": [],
                "aggregate_names": [],
                "simple_polygons": [],
            }
        },
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

    assert normalize_spaces(page.select_one("h1").text) == "Choose alert duration"

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
        ("content", "PT30M", "30 minutes"),
        ("content", "PT3H", "3 hours"),
        ("content", "PT6H", "6 hours"),
        ("content", "PT22H", "22 hours"),
    ]


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
):
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

    assert page.select_one("p.duration-preview").text == "Duration: 0 seconds"

    assert normalize_spaces(page.select_one("h2.broadcast-message-heading").text) == "Emergency alert"

    assert normalize_spaces(page.select_one(".broadcast-message-wrapper").text) == "Emergency alert This is a test"

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
    ),
    mock_update_broadcast_message_status.assert_called_once_with(
        "pending-approval",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )


@pytest.mark.parametrize(
    "endpoint, created_by_api, extra_fields, expected_paragraphs",
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
            [
                "live since 20 February at 8:20pm Stop sending",
                "Created by Alice and approved by Bob.",
                "Broadcasting stops tomorrow at 11:23pm.",
            ],
        ),
        (
            ".view_current_broadcast",
            True,
            {"status": "broadcasting", "finishes_at": "2020-02-23T23:23:23.000000", "approved_by": "Alice"},
            [
                "live since 20 February at 8:20pm Stop sending",
                "Created from an API call and approved by Alice.",
                "Broadcasting stops tomorrow at 11:23pm.",
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
            [
                "Sent on 20 February at 8:20pm.",
                "Created by Alice and approved by Bob.",
                "Finished broadcasting today at 10:20pm.",
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
            [
                "Sent on 20 February at 8:20pm.",
                "Created from an API call and approved by Alice.",
                "Finished broadcasting today at 10:20pm.",
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
            [
                "Sent on 20 February at 8:20pm.",
                "Created by Alice and approved by Bob.",
                "Finished broadcasting yesterday at 9:21pm.",
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
            [
                "Sent on 20 February at 8:20pm.",
                "Created by Alice and approved by Bob.",
                "Stopped by Carol yesterday at 9:21pm.",
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
            [
                "Sent on 20 February at 8:20pm.",
                "Created by Alice and approved by Bob.",
                "Stopped by an API call yesterday at 9:21pm.",
            ],
        ),
    ),
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
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=None if created_by_api else fake_uuid,
            approved_by_id=fake_uuid,
            starts_at="2020-02-20T20:20:20.000000",
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


@pytest.mark.parametrize(
    "endpoint, created_by_api, extra_fields, expected_paragraphs",
    (
        (
            ".view_rejected_broadcast",
            False,
            {
                "status": "rejected",
                "updated_at": "2020-02-21T21:21:21.000000",
            },
            [
                "Rejected yesterday at 9:21pm by Carol.",
                "Created by Alice and approved by Bob.",
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
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
            created_by_id=None if created_by_api else fake_uuid,
            approved_by_id=fake_uuid,
            created_by="Alice",
            approved_by="Bob",
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
            finishes_at="2021-12-21T21:21:21.000000",
            cancelled_at="2021-01-01T01:01:01.000000",
            updated_at="2021-01-01T01:01:01.000000",
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
        "Reject this alert "
        "Give a reason for rejecting the alert "
        "Detailed reason for rejecting the alert, including how it may be reworked. "
        'For example, "The alert message has spelling mistakes". '
        "Reject alert"
    )
    assert not page.select(".banner input[type=checkbox]")

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
                "Reject this alert "
                "Give a reason for rejecting the alert "
                "Detailed reason for rejecting the alert, including how it may be reworked. "
                'For example, "The alert message has spelling mistakes". '
                "Reject alert"
            ),
        ),
        (
            {"cap_event": "Severe flood warning", "reference": "ABC123"},
            (
                "Test User Create Broadcasts Permission wants to broadcast Severe flood warning "
                "No phones will get this alert. "
                "Start broadcasting now "
                "Reject this alert "
                "Give a reason for rejecting the alert "
                "Detailed reason for rejecting the alert, including how it may be reworked. "
                'For example, "The alert message has spelling mistakes". '
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
        "An API call wants to broadcast abc123 "
        "No phones will get this alert. "
        "Start broadcasting now "
        "Reject this alert "
        "Give a reason for rejecting the alert "
        "Detailed reason for rejecting the alert, including how it may be reworked. "
        'For example, "The alert message has spelling mistakes". '
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
):
    mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=None,
            created_by_id=None,
            status="pending-approval",
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
):
    page = mocker.patch(
        "app.broadcast_message_api_client.get_broadcast_message",
        return_value=broadcast_message_json(
            id_=fake_uuid,
            service_id=SERVICE_ONE_ID,
            template_id=None,
            created_by_id=None,
            status="pending-approval",
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

    button = page.select_one(".banner button.govuk-button.govuk-button--warning")
    assert (normalize_spaces(button.text)) == "Reject alert"


@freeze_time("2020-02-22T22:22:22.000000")
@pytest.mark.parametrize(
    "user",
    [
        create_active_user_approve_broadcasts_permissions(),
        create_active_user_create_broadcasts_permissions(),
    ],
)
def test_cant_approve_own_broadcast_if_service_is_live(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    user,
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
    assert not page.select("form")

    link = page.select_one(".banner a.govuk-link.govuk-link--destructive")
    assert link.text == "Discard this alert"
    assert link["href"] == url_for(
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
                "Reject this alert"
            ),
        ),
        (
            False,
            (
                "This alert is waiting for approval "
                "Another member of your team needs to approve this alert. "
                "Reject this alert"
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
):
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
    assert not page.select_one("form")
    link = page.select_one(".banner a")
    assert link["href"] == url_for(
        ".reject_broadcast_message", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid
    )


def test_user_without_approve_permission_cant_approve_broadcast_they_created(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    active_user_create_broadcasts_permission,
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

    link = page.select_one("a.govuk-link.govuk-link--destructive")
    assert link.text == "Discard this alert"
    assert link["href"] == url_for(
        ".discard_broadcast_message",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )


@pytest.mark.parametrize(
    "channel, duration, expected_finishes_at",
    (
        ("operator", 1800, "2020-02-22T22:52:22"),  # 30 mins later
        ("test", 10800, "2020-02-23T01:22:22"),  # 3 hours later
        ("severe", 21600, "2020-02-23T04:22:22"),  # 6 hours later
        ("government", 79200, "2020-02-23T20:22:22"),  # 22 hours later
        (None, 0, "2020-02-23T20:52:22"),  # Training mode
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
):
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
                "starts_at": "2020-02-22T22:22:22",
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
    page = client_request.post(
        ".reject_broadcast_message", service_id=SERVICE_ONE_ID, broadcast_message_id=fake_uuid, _expected_status=200
    )
    link = page.select_one(".banner a.govuk-link.govuk-link--destructive")
    assert link.text == "Discard this alert"
    assert link["href"] == url_for(
        ".discard_broadcast_message",
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
    )

    assert mock_update_broadcast_message.called is False
    assert mock_update_broadcast_message_status_with_reason.called is False


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
    mock_get_broadcast_template,
    fake_uuid,
    mock_update_broadcast_message,
    mock_update_broadcast_message_status,
    user,
    initial_status,
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


@pytest.mark.parametrize(
    "endpoint",
    (
        ".view_current_broadcast",
        ".view_previous_broadcast",
    ),
)
def test_no_view_page_for_draft(
    client_request,
    service_one,
    mock_get_draft_broadcast_message,
    fake_uuid,
    endpoint,
):
    service_one["permissions"] += ["broadcast"]
    client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
        broadcast_message_id=fake_uuid,
        _expected_status=404,
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
