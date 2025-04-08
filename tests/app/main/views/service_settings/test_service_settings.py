from uuid import uuid4

import pytest
from flask import url_for

import app
from tests import organisation_json, service_json, validate_route_permission
from tests.conftest import (
    ORGANISATION_ID,
    SERVICE_ONE_ID,
    create_active_user_no_settings_permission,
    create_active_user_with_permissions,
    create_platform_admin_user,
    normalize_spaces,
)

FAKE_TEMPLATE_ID = uuid4()


@pytest.mark.parametrize(
    "user, expected_rows",
    [
        (
            create_active_user_with_permissions(),
            [
                "Label Value Action",
                "Service name Test Service Change service name",
                "Sign-in method Text message code Change sign-in method",
            ],
        ),
        (
            create_platform_admin_user(),
            [
                "Label Value Action",
                "Service name Test Service Change service name",
                "Sign-in method Text message code Change sign-in method",
                "Label Value Action",
                "Notes None Change the notes for the service",
                "Email authentication Off Change your settings for Email authentication",
                "Emergency alerts Off Change your settings for emergency alerts",
            ],
        ),
    ],
)
def test_should_show_overview(
    client_request,
    mocker,
    api_user_active,
    user,
    expected_rows,
):
    service_one = service_json(
        SERVICE_ONE_ID,
        users=[api_user_active["id"]],
        permissions=["sms", "email"],
        organisation_id=ORGANISATION_ID,
        contact_link="contact_us@gov.uk",
    )
    mocker.patch("app.service_api_client.get_service", return_value={"data": service_one})

    client_request.login(user, service_one)
    page = client_request.get("main.service_settings", service_id=SERVICE_ONE_ID)

    assert page.select_one("h1").text == "Settings"
    rows = page.select("tr")
    assert len(rows) == len(expected_rows)
    for index, row in enumerate(expected_rows):
        assert row == " ".join(rows[index].text.split())
    app.service_api_client.get_service.assert_called_with(SERVICE_ONE_ID)


def test_platform_admin_sees_only_relevant_settings_for_broadcast_service(
    client_request,
    mocker,
    api_user_active,
):
    service_one = service_json(
        SERVICE_ONE_ID,
        users=[api_user_active["id"]],
        permissions=["broadcast"],
        restricted=True,
        organisation_id=ORGANISATION_ID,
        contact_link="contact_us@gov.uk",
    )
    mocker.patch("app.service_api_client.get_service", return_value={"data": service_one})

    client_request.login(create_platform_admin_user(), service_one)
    page = client_request.get("main.service_settings", service_id=SERVICE_ONE_ID)

    assert page.select_one("h1").text == "Settings"
    rows = page.select("tr")

    expected_rows = [
        "Label Value Action",
        "Service name Test Service Change service name",
        "Sign-in method Text message code Change sign-in method",
        "Label Value Action",
        "Notes None Change the notes for the service",
        "Email authentication Off Change your settings for Email authentication",
        "Emergency alerts Off Change your settings for emergency alerts",
    ]

    assert len(rows) == len(expected_rows)
    for index, row in enumerate(expected_rows):
        assert row == " ".join(rows[index].text.split())
    app.service_api_client.get_service.assert_called_with(SERVICE_ONE_ID)


@pytest.mark.parametrize(
    "has_broadcast_permission,service_mode,broadcast_channel,allowed_broadcast_provider,expected_text",
    [
        (False, "training", None, ["ee", "o2", "three", "vodafone"], "Off"),
        (False, "live", None, ["ee", "o2", "three", "vodafone"], "Off"),
        (True, "training", "test", ["ee", "o2", "three", "vodafone"], "Training"),
        (True, "live", "test", ["ee"], "Test (EE)"),
        (True, "live", "test", ["three"], "Test (Three)"),
        (True, "live", "test", ["ee", "o2", "three", "vodafone"], "Test"),
        (True, "live", "severe", ["ee", "o2", "three", "vodafone"], "Live"),
        (True, "live", "severe", ["three"], "Live (Three)"),
        (True, "live", "government", ["ee", "o2", "three", "vodafone"], "Government"),
        (True, "live", "government", ["three"], "Government (Three)"),
    ],
)
def test_platform_admin_sees_correct_description_of_broadcast_service_setting(
    client_request,
    mocker,
    api_user_active,
    has_broadcast_permission,
    service_mode,
    broadcast_channel,
    allowed_broadcast_provider,
    expected_text,
):
    service_one = service_json(
        SERVICE_ONE_ID,
        users=[api_user_active["id"]],
        permissions=["broadcast"] if has_broadcast_permission else ["email"],
        organisation_id=ORGANISATION_ID,
        restricted=True if service_mode == "training" else False,
        broadcast_channel=broadcast_channel,
        allowed_broadcast_provider=allowed_broadcast_provider,
    )
    mocker.patch("app.service_api_client.get_service", return_value={"data": service_one})

    client_request.login(create_platform_admin_user(), service_one)
    page = client_request.get("main.service_settings", service_id=SERVICE_ONE_ID)

    broadcast_setting_row = page.select("tr")[-1]
    assert normalize_spaces(broadcast_setting_row.select("td")[0].text) == "Emergency alerts"
    broadcast_setting_description = broadcast_setting_row.select("td")[1].text
    assert normalize_spaces(broadcast_setting_description) == expected_text


@pytest.mark.parametrize(
    "permissions, expected_rows",
    [
        (
            ["broadcast"],
            [
                "Service name service one Change service name",
                "Sign-in method Text message code Change sign-in method",
            ],
        ),
    ],
)
def test_should_show_overview_for_service_with_more_things_set(
    client_request,
    active_user_with_permissions,
    mocker,
    service_one,
    permissions,
    expected_rows,
):
    client_request.login(active_user_with_permissions)
    service_one["permissions"] = permissions
    page = client_request.get("main.service_settings", service_id=service_one["id"])
    for index, row in enumerate(expected_rows):
        assert row == " ".join(page.select("tr")[index + 1].text.split())


def test_should_show_service_name(
    client_request,
):
    page = client_request.get("main.service_name_change", service_id=SERVICE_ONE_ID)
    assert page.select_one("h1").text == "Change your service name"
    assert page.select_one("input", attrs={"type": "text"})["value"] == "service one"
    assert (
        page.select_one("main p").text
        == "Your service name should tell users what the message is about as well as who it’s from."
    )
    app.service_api_client.get_service.assert_called_with(SERVICE_ONE_ID)


def test_should_show_different_change_service_name_page_for_local_services(
    client_request,
    service_one,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation_by_domain",
        return_value=organisation_json(organisation_type="local"),
    )
    service_one["organisation_type"] = "local"
    page = client_request.get("main.service_name_change", service_id=SERVICE_ONE_ID)
    assert page.select_one("h1").text == "Change your service name"
    assert page.select_one("input", attrs={"type": "text"})["value"] == "service one"
    assert page.select_one("main .govuk-body").text.strip() == (
        "Your service name should tell users what the message is about as well as who it’s from. For example:"
    )
    # when no organisation on the service object, default org for the user is used for hint
    assert "School admissions - Test Org" in page.select_one("ul.govuk-list.govuk-list--bullet").text

    app.service_api_client.get_service.assert_called_with(SERVICE_ONE_ID)


def test_should_show_service_org_in_hint_on_change_service_name_page_for_local_services_if_service_has_org(
    client_request,
    service_one,
    mocker,
):
    mocker.patch(
        "app.organisations_client.get_organisation_by_domain",
        return_value=organisation_json(organisation_type="local"),
    )
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(organisation_type="local", name="Local Authority"),
    )
    service_one["organisation_type"] = "local"
    service_one["organisation"] = "1234"
    page = client_request.get("main.service_name_change", service_id=SERVICE_ONE_ID)
    # when there is organisation on the service object, it is used for hint text instead of user default org
    assert "School admissions - Local Authority" in page.select_one("ul.govuk-list.govuk-list--bullet").text


def test_should_show_service_name_with_no_prefixing(
    client_request,
    service_one,
):
    page = client_request.get("main.service_name_change", service_id=SERVICE_ONE_ID)
    assert page.select_one("h1").text == "Change your service name"
    assert (
        page.select_one("main p").text
        == "Your service name should tell users what the message is about as well as who it’s from."
    )


@pytest.mark.parametrize(
    "name, error_message",
    [
        ("", "Cannot be empty"),
        (".", "Must include at least two alphanumeric characters"),
        ("a" * 256, "Service name must be 255 characters or fewer"),
    ],
)
def test_service_name_change_fails_if_new_name_fails_validation(
    client_request,
    mock_update_service,
    name,
    error_message,
):
    page = client_request.post(
        "main.service_name_change",
        service_id=SERVICE_ONE_ID,
        _data={"name": name},
        _expected_status=200,
    )
    assert not mock_update_service.called
    assert error_message in page.select_one(".govuk-error-message").text


@pytest.mark.parametrize(
    "user, expected_response",
    [
        (
            create_active_user_with_permissions(),
            200,
        ),
        (
            create_active_user_no_settings_permission(),
            403,
        ),
    ],
)
def test_show_restricted_service(
    client_request,
    user,
    expected_response,
):
    client_request.login(user)
    page = client_request.get("main.service_settings", service_id=SERVICE_ONE_ID, _expected_response=expected_response)

    if expected_response == 200:
        assert page.select_one("main h1").text == "Settings"


def test_broadcast_service_in_training_mode_doesnt_show_trial_mode_content(
    client_request,
    service_one,
):
    service_one["permissions"] = "broadcast"
    page = client_request.get(
        "main.service_settings",
        service_id=SERVICE_ONE_ID,
    )

    assert "Your service is in trial mode" not in page.select("main")[0].text
    assert "To remove these restrictions, you can send us a request to go live" not in page.select("main")[0].text
    assert not page.select_one("main ul")


def test_show_live_service(
    client_request,
    mock_get_live_service,
):
    page = client_request.get(
        "main.service_settings",
        service_id=SERVICE_ONE_ID,
    )
    assert page.select_one("h1").text.strip() == "Settings"
    assert "Your service is in trial mode" not in page.text


def test_should_not_allow_duplicate_service_names(
    client_request,
    mock_update_service_raise_httperror_duplicate_name,
    service_one,
):
    page = client_request.post(
        "main.service_name_change",
        service_id=SERVICE_ONE_ID,
        _data={"name": "SErvICE TWO"},
        _expected_status=200,
    )

    assert "This service name is already in use" in page.text


def test_should_redirect_after_service_name_change(
    client_request,
    mock_update_service,
):
    client_request.post(
        "main.service_name_change",
        service_id=SERVICE_ONE_ID,
        _data={"name": "New Name"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.service_settings",
            service_id=SERVICE_ONE_ID,
        ),
    )

    mock_update_service.assert_called_once_with(
        SERVICE_ONE_ID,
        name="New Name",
    )


@pytest.mark.parametrize(
    "route",
    [
        "main.service_settings",
        "main.service_name_change",
        "main.archive_service",
    ],
)
def test_route_permissions(
    mocker,
    notify_admin,
    client_request,
    api_user_active,
    service_one,
    mock_get_invites_for_service,
    route,
    mock_get_service_templates,
):
    validate_route_permission(
        mocker,
        notify_admin,
        "GET",
        200,
        url_for(route, service_id=service_one["id"]),
        ["manage_service"],
        api_user_active,
        service_one,
        session={"service_name_change": "New Service Name"},
    )


@pytest.mark.parametrize(
    "route",
    [
        "main.service_settings",
        "main.service_name_change",
        "main.archive_service",
    ],
)
def test_route_invalid_permissions(
    mocker,
    notify_admin,
    client_request,
    api_user_active,
    service_one,
    route,
    mock_get_service_templates,
    mock_get_invites_for_service,
):
    validate_route_permission(
        mocker,
        notify_admin,
        "GET",
        403,
        url_for(route, service_id=service_one["id"]),
        ["blah"],
        api_user_active,
        service_one,
    )


@pytest.mark.parametrize(
    "route",
    [
        "main.service_settings",
        "main.service_name_change",
    ],
)
def test_route_for_platform_admin(
    mocker,
    notify_admin,
    client_request,
    platform_admin_user,
    service_one,
    route,
    mock_get_service_templates,
    mock_get_invites_for_service,
):
    validate_route_permission(
        mocker,
        notify_admin,
        "GET",
        200,
        url_for(route, service_id=service_one["id"]),
        [],
        platform_admin_user,
        service_one,
        session={"service_name_change": "New Service Name"},
    )


@pytest.mark.parametrize("method", ["get"])
@pytest.mark.parametrize(
    "endpoint",
    [
        "main.service_settings",
        "main.api_keys",
    ],
)
def test_organisation_type_pages_are_platform_admin_only(
    client_request,
    active_user_create_broadcasts_permission,
    method,
    endpoint,
):
    client_request.login(active_user_create_broadcasts_permission)
    getattr(client_request, method)(
        endpoint,
        service_id=SERVICE_ONE_ID,
        _expected_status=403,
        _test_page_title=False,
    )


@pytest.mark.parametrize(
    "user, is_trial_service",
    (
        [create_platform_admin_user(), True],
        [create_platform_admin_user(), False],
        [create_active_user_with_permissions(), True],
        pytest.param(create_active_user_with_permissions(), False, marks=pytest.mark.xfail),
        pytest.param(create_active_user_no_settings_permission(), True, marks=pytest.mark.xfail),
    ),
)
def test_archive_service_after_confirm(
    client_request,
    mocker,
    mock_get_organisations,
    mock_get_service_and_organisation_counts,
    mock_get_organisations_and_services_for_user,
    mock_get_users_by_service,
    mock_get_service_templates,
    service_one,
    user,
    is_trial_service,
):
    service_one["restricted"] = is_trial_service
    mock_api = mocker.patch("app.service_api_client.post")
    mock_event = mocker.patch("app.main.views.service_settings.create_archive_service_event")

    client_request.login(user)
    page = client_request.post(
        "main.archive_service",
        service_id=SERVICE_ONE_ID,
        _follow_redirects=True,
    )

    mock_api.assert_called_once_with("/service/{}/archive".format(SERVICE_ONE_ID), data=None)
    mock_event.assert_called_once_with(service_id=SERVICE_ONE_ID, archived_by_id=user["id"])

    assert normalize_spaces(page.select_one("h1").text) == "Choose service"
    assert normalize_spaces(page.select_one(".banner-default-with-tick").text) == "‘service one’ was deleted"


@pytest.mark.parametrize(
    "user, is_trial_service",
    (
        [create_platform_admin_user(), True],
        [create_platform_admin_user(), False],
        [create_active_user_with_permissions(), True],
        pytest.param(create_active_user_with_permissions(), False, marks=pytest.mark.xfail),
        pytest.param(create_active_user_no_settings_permission(), True, marks=pytest.mark.xfail),
    ),
)
def test_archive_service_prompts_user(
    client_request,
    mocker,
    service_one,
    user,
    is_trial_service,
):
    mock_api = mocker.patch("app.service_api_client.post")
    service_one["restricted"] = is_trial_service
    client_request.login(user)

    settings_page = client_request.get(
        "main.archive_service",
        service_id=SERVICE_ONE_ID,
        _test_page_prefix="Are you sure you want to delete ‘service one’?",
    )
    delete_link = settings_page.select(".page-footer-link a")[0]
    assert normalize_spaces(delete_link.text) == "Delete this service"
    assert delete_link["href"] == url_for(
        "main.archive_service",
        service_id=SERVICE_ONE_ID,
    )

    delete_page = client_request.get(
        "main.archive_service",
        service_id=SERVICE_ONE_ID,
        _test_page_prefix="Are you sure you want to delete ‘service one’?",
    )
    assert normalize_spaces(delete_page.select_one(".banner-dangerous").text) == (
        "Are you sure you want to delete ‘service one’? There’s no way to undo this. Yes, delete"
    )
    assert mock_api.called is False


def test_cant_archive_inactive_service(
    client_request,
    platform_admin_user,
    service_one,
):
    service_one["active"] = False

    client_request.login(platform_admin_user)
    page = client_request.get(
        "main.service_settings",
        service_id=service_one["id"],
    )

    assert "Delete service" not in {a.text for a in page.select("a.button")}


@pytest.mark.parametrize(
    "endpoint, permissions, expected_p",
    [
        ("main.service_set_auth_type", [], "Text message code"),
        ("main.service_set_auth_type", ["email_auth"], "Email link or text message code"),
    ],
)
def test_invitation_pages(
    client_request,
    service_one,
    endpoint,
    permissions,
    expected_p,
):
    service_one["permissions"] = permissions
    page = client_request.get(
        endpoint,
        service_id=SERVICE_ONE_ID,
    )

    assert normalize_spaces(page.select("main p")[0].text) == expected_p


def test_select_organisation(
    client_request, platform_admin_user, service_one, mock_get_organisation, mock_get_organisations
):
    client_request.login(platform_admin_user)
    page = client_request.get(
        ".link_service_to_organisation",
        service_id=service_one["id"],
    )

    assert len(page.select(".govuk-radios__item")) == 3
    for i in range(0, 3):
        assert normalize_spaces(page.select(".govuk-radios__item label")[i].text) == "Org {}".format(i + 1)


def test_select_organisation_shows_message_if_no_orgs(
    client_request, platform_admin_user, service_one, mock_get_organisation, mocker
):
    mocker.patch("app.organisations_client.get_organisations", return_value=[])

    client_request.login(platform_admin_user)
    page = client_request.get(
        ".link_service_to_organisation",
        service_id=service_one["id"],
    )

    assert normalize_spaces(page.select_one("main p").text) == "No organisations"
    assert not page.select_one("main button")


def test_update_service_organisation(
    client_request,
    platform_admin_user,
    service_one,
    mock_get_organisation,
    mock_get_organisations,
    mock_update_service_organisation,
):
    client_request.login(platform_admin_user)
    client_request.post(
        ".link_service_to_organisation",
        service_id=service_one["id"],
        _data={"organisations": "7aa5d4e9-4385-4488-a489-07812ba13384"},
    )
    mock_update_service_organisation.assert_called_once_with(service_one["id"], "7aa5d4e9-4385-4488-a489-07812ba13384")


def test_update_service_organisation_does_not_update_if_same_value(
    client_request,
    platform_admin_user,
    service_one,
    mock_get_organisation,
    mock_get_organisations,
    mock_update_service_organisation,
):
    org_id = "7aa5d4e9-4385-4488-a489-07812ba13383"
    service_one["organisation"] = org_id
    client_request.login(platform_admin_user)
    client_request.post(
        ".link_service_to_organisation",
        service_id=service_one["id"],
        _data={"organisations": org_id},
    )
    assert mock_update_service_organisation.called is False


def test_service_settings_links_to_edit_service_notes_page_for_platform_admins(
    mocker,
    service_one,
    client_request,
    platform_admin_user,
):
    client_request.login(platform_admin_user)
    page = client_request.get(
        ".service_settings",
        service_id=SERVICE_ONE_ID,
    )
    assert len(page.select(f'a[href="/services/{SERVICE_ONE_ID}/notes"]')) == 1


def test_view_edit_service_notes(
    client_request,
    platform_admin_user,
    service_one,
):
    client_request.login(platform_admin_user)
    page = client_request.get(
        "main.edit_service_notes",
        service_id=SERVICE_ONE_ID,
    )
    assert page.select_one("h1").text == "Edit service notes"
    assert page.select_one("label.form-label").text.strip() == "Notes"
    assert page.select_one("textarea").attrs["name"] == "notes"


def test_update_service_notes(client_request, platform_admin_user, service_one, mock_update_service):
    client_request.login(platform_admin_user)
    client_request.post(
        "main.edit_service_notes",
        service_id=SERVICE_ONE_ID,
        _data={"notes": "Very fluffy"},
        _expected_redirect=url_for(
            "main.service_settings",
            service_id=SERVICE_ONE_ID,
        ),
    )
    mock_update_service.assert_called_with(SERVICE_ONE_ID, notes="Very fluffy")


def test_service_set_broadcast_channel(
    client_request,
    platform_admin_user,
):
    client_request.login(platform_admin_user)
    page = client_request.get(
        "main.service_set_broadcast_channel",
        service_id=SERVICE_ONE_ID,
    )

    assert page.select_one("h1").text.strip() == "Emergency alerts settings"

    assert [normalize_spaces(label) for label in page.select("label.govuk-radios__label")] == [
        "Training mode",
        "Operator channel",
        "Test channel",
        "Live channel",
        "Government channel",
    ]

    assert page.select_one(".govuk-back-link")["href"] == url_for(
        "main.service_settings",
        service_id=SERVICE_ONE_ID,
    )


@pytest.mark.parametrize(
    "service_mode,broadcast_channel,allowed_broadcast_provider,expected_text,expected_value",
    [
        (
            "training",
            "test",
            "all",
            "Training mode",
            "training",
        ),
        (
            "live",
            "government",
            "all",
            "Government channel",
            "government",
        ),
    ],
)
def test_service_set_broadcast_channel_has_radio_selected_for_broadcast_service(
    client_request,
    platform_admin_user,
    mocker,
    service_mode,
    broadcast_channel,
    allowed_broadcast_provider,
    expected_text,
    expected_value,
):
    service_one = service_json(
        SERVICE_ONE_ID,
        permissions=["broadcast"],
        restricted=True if service_mode == "training" else False,
        broadcast_channel=broadcast_channel,
        allowed_broadcast_provider=allowed_broadcast_provider,
    )
    mocker.patch("app.service_api_client.get_service", return_value={"data": service_one})

    client_request.login(platform_admin_user, service_one)
    page = client_request.get(
        "main.service_set_broadcast_channel",
        service_id=SERVICE_ONE_ID,
    )

    selected_radios = page.select("input[checked]")
    assert len(selected_radios) == 1

    selected_radio = selected_radios[0]
    assert selected_radio.get("value") == expected_value
    selected_label = selected_radio.find_next_sibling("label")
    assert selected_label.text.strip() == expected_text


@pytest.mark.parametrize(
    "channel,expected_redirect_endpoint,extra_args",
    [
        (
            "training",
            ".service_confirm_broadcast_account_type",
            {"account_type": "training-test-all"},
        ),
        (
            "operator",
            ".service_set_broadcast_network",
            {"broadcast_channel": "operator"},
        ),
        (
            "test",
            ".service_set_broadcast_network",
            {"broadcast_channel": "test"},
        ),
        (
            "severe",
            ".service_set_broadcast_network",
            {"broadcast_channel": "severe"},
        ),
        (
            "government",
            ".service_set_broadcast_network",
            {"broadcast_channel": "government"},
        ),
    ],
)
def test_service_set_broadcast_channel_redirects(
    client_request,
    platform_admin_user,
    mocker,
    channel,
    expected_redirect_endpoint,
    extra_args,
):
    client_request.login(platform_admin_user)
    client_request.post(
        "main.service_set_broadcast_channel",
        service_id=SERVICE_ONE_ID,
        _data={
            "channel": channel,
        },
        _expected_redirect=url_for(
            expected_redirect_endpoint,
            service_id=SERVICE_ONE_ID,
            **extra_args,
        ),
    )


@pytest.mark.parametrize(
    "service_mode,broadcast_channel,allowed_broadcast_provider,expected_selected",
    [
        (
            "live",
            "severe",
            ["all"],
            [
                ("All mobile networks", "all"),
            ],
        ),
        (
            "live",
            "test",
            ["ee"],
            [
                ("EE", "ee"),
            ],
        ),
    ],
)
def test_service_set_broadcast_network_has_radio_selected(
    client_request,
    platform_admin_user,
    mocker,
    service_mode,
    broadcast_channel,
    allowed_broadcast_provider,
    expected_selected,
):
    client_request.login(platform_admin_user)
    service_one = service_json(
        SERVICE_ONE_ID,
        permissions=["broadcast"],
        restricted=False if service_mode == "live" else True,
        broadcast_channel=broadcast_channel,
        allowed_broadcast_provider=allowed_broadcast_provider,
    )
    mocker.patch("app.service_api_client.get_service", return_value={"data": service_one})
    mocker.patch(
        "app.service_api_client.get_broadcast_providers",
        return_value={"data": [{"provider": p} for p in allowed_broadcast_provider]},
    )

    page = client_request.get(
        "main.service_set_broadcast_network",
        service_id=SERVICE_ONE_ID,
        broadcast_channel=broadcast_channel,
    )

    assert [
        (
            normalize_spaces(checkbox.find_next_sibling("label").text),
            checkbox["value"],
        )
        for checkbox in page.select("input[checked]")
    ] == expected_selected


@pytest.mark.parametrize(
    "broadcast_channel, data, expected_result",
    (
        ("severe", {"networks": ["all"]}, "live-severe-ee-o2-three-vodafone"),
        ("government", {"networks": ["all"]}, "live-government-ee-o2-three-vodafone"),
        ("government", {"networks": ["ee", "o2", "three", "vodafone"]}, "live-government-ee-o2-three-vodafone"),
        ("operator", {"networks": ["all"]}, "live-operator-ee-o2-three-vodafone"),
        ("operator", {"networks": ["ee", "o2", "three", "vodafone"]}, "live-operator-ee-o2-three-vodafone"),
        ("test", {"networks": ["all"]}, "live-test-ee-o2-three-vodafone"),
        ("test", {"networks": ["o2"]}, "live-test-o2"),
        ("test", {"networks": ["ee"]}, "live-test-ee"),
        ("test", {"networks": ["three"]}, "live-test-three"),
        ("test", {"networks": ["vodafone"]}, "live-test-vodafone"),
        ("government", {"networks": ["vodafone"]}, "live-government-vodafone"),
        ("severe", {"networks": ["vodafone"]}, "live-severe-vodafone"),
        ("severe", {"networks": ["ee", "vodafone"]}, "live-severe-ee-vodafone"),
        ("severe", {"networks": ["o2", "three"]}, "live-severe-o2-three"),
    ),
)
def test_service_set_broadcast_network(
    client_request,
    platform_admin_user,
    mocker,
    broadcast_channel,
    data,
    expected_result,
):
    mocker.patch(
        "app.service_api_client.get_broadcast_providers",
        return_value={"data": []},
    )

    client_request.login(platform_admin_user)
    client_request.post(
        "main.service_set_broadcast_network",
        service_id=SERVICE_ONE_ID,
        broadcast_channel=broadcast_channel,
        _data=data,
        _expected_status=302,
        _expected_redirect=url_for(
            "main.service_confirm_broadcast_account_type",
            service_id=SERVICE_ONE_ID,
            account_type=expected_result,
        ),
    )


@pytest.mark.parametrize("broadcast_channel", ["government", "severe", "test", "operator"])
def test_service_set_broadcast_network_makes_you_choose(client_request, platform_admin_user, mocker, broadcast_channel):
    data = []  # no network selected
    mocker.patch(
        "app.service_api_client.get_broadcast_providers",
        return_value={"data": data},
    )

    client_request.login(platform_admin_user)
    page = client_request.post(
        "main.service_set_broadcast_network",
        service_id=SERVICE_ONE_ID,
        broadcast_channel=broadcast_channel,
        _data=data,
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one(".govuk-error-message").text) == "Error: Select a mobile network"


@pytest.mark.parametrize(
    "value, expected_paragraphs",
    [
        (
            "training-test-all",
            [
                "Training",
                "No phones will receive alerts sent from this service.",
            ],
        ),
        (
            "live-operator-ee-o2-three-vodafone",
            [
                "Operator",
                "Members of the public who have switched on the operator "
                "channel on their phones will receive alerts sent from "
                "this service.",
            ],
        ),
        (
            "live-test-ee",
            [
                "Test (EE)",
                "Members of the public who have switched on the test "
                "channel on their phones will receive alerts sent from "
                "this service.",
            ],
        ),
        (
            "live-test-o2",
            [
                "Test (O2)",
                "Members of the public who have switched on the test "
                "channel on their phones will receive alerts sent from "
                "this service.",
            ],
        ),
        (
            "live-test-three",
            [
                "Test (Three)",
                "Members of the public who have switched on the test "
                "channel on their phones will receive alerts sent from "
                "this service.",
            ],
        ),
        (
            "live-test-vodafone",
            [
                "Test (Vodafone)",
                "Members of the public who have switched on the test "
                "channel on their phones will receive alerts sent from "
                "this service.",
            ],
        ),
        (
            "live-test-ee-o2-three-vodafone",
            [
                "Test",
                "Members of the public who have switched on the test "
                "channel on their phones will receive alerts sent from "
                "this service.",
            ],
        ),
        (
            "live-severe-ee-o2-three-vodafone",
            [
                "Live",
                "Members of the public will receive alerts sent from this service.",
            ],
        ),
        (
            "live-severe-vodafone",
            [
                "Live (Vodafone)",
                "Members of the public will receive alerts sent from this service.",
            ],
        ),
        (
            "live-government-ee-o2-three-vodafone",
            [
                "Government",
                "Members of the public will receive alerts sent from this service, even if they’ve opted out.",
            ],
        ),
        (
            "live-government-vodafone",
            [
                "Government (Vodafone)",
                "Members of the public will receive alerts sent from this service, even if they’ve opted out.",
            ],
        ),
    ],
)
def test_service_confirm_broadcast_account_type_confirmation_page(
    client_request,
    platform_admin_user,
    value,
    expected_paragraphs,
):
    client_request.login(platform_admin_user)
    page = client_request.get(
        "main.service_confirm_broadcast_account_type",
        service_id=SERVICE_ONE_ID,
        account_type=value,
    )
    assert [normalize_spaces(p.text) for p in page.select("main p")] == expected_paragraphs + [
        "Changing service mode from Training to one of the live channels will remove all team member permissions."
    ]


@pytest.mark.parametrize(
    "value,service_mode,broadcast_channel,allowed_broadcast_provider",
    [
        ("training-test-all", "training", "test", ["all"]),
        ("live-operator-o2", "live", "operator", ["o2"]),
        ("live-test-vodafone", "live", "test", ["vodafone"]),
        ("live-severe-all", "live", "severe", ["all"]),
        ("live-government-all", "live", "government", ["all"]),
    ],
)
def test_service_confirm_broadcast_account_type_posts_data_to_api_and_redirects(
    client_request,
    platform_admin_user,
    mocker,
    value,
    service_mode,
    broadcast_channel,
    allowed_broadcast_provider,
    fake_uuid,
    mock_get_users_by_service,
):
    set_service_broadcast_settings_mock = mocker.patch("app.service_api_client.set_service_broadcast_settings")
    mock_event_handler = mocker.patch("app.main.views.service_settings.create_broadcast_account_type_change_event")

    client_request.login(platform_admin_user)
    client_request.post(
        "main.service_confirm_broadcast_account_type",
        service_id=SERVICE_ONE_ID,
        account_type=value,
        _expected_redirect=url_for(
            "main.service_settings",
            service_id=SERVICE_ONE_ID,
        ),
    )
    set_service_broadcast_settings_mock.assert_called_once_with(
        SERVICE_ONE_ID,
        service_mode=service_mode,
        broadcast_channel=broadcast_channel,
        provider_restriction=allowed_broadcast_provider,
    )
    mock_event_handler.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        changed_by_id=fake_uuid,
        service_mode=service_mode,
        broadcast_channel=broadcast_channel,
        provider_restriction=allowed_broadcast_provider,
    )


@pytest.mark.parametrize("account_type", ("foo-test-ee", "live-foo-all", "live-government-foo"))
def test_service_confirm_broadcast_account_type_errors_for_unknown_type(
    client_request,
    platform_admin_user,
    mocker,
    account_type,
):
    set_service_broadcast_settings_mock = mocker.patch("app.service_api_client.set_service_broadcast_settings")
    mock_event_handler = mocker.patch("app.main.views.service_settings.create_broadcast_account_type_change_event")

    client_request.login(platform_admin_user)
    client_request.post(
        "main.service_confirm_broadcast_account_type",
        service_id=SERVICE_ONE_ID,
        account_type=account_type,
        _expected_status=404,
    )
    assert not set_service_broadcast_settings_mock.called
    assert not mock_event_handler.called


def test_service_set_broadcast_channel_makes_you_choose(
    client_request,
    platform_admin_user,
):
    client_request.login(platform_admin_user)
    _ = client_request.post(
        "main.service_set_broadcast_channel",
        service_id=SERVICE_ONE_ID,
        _expected_status=302,
        _expected_redirect=url_for(
            ".service_confirm_broadcast_account_type",
            service_id=SERVICE_ONE_ID,
            account_type="training-test-all",
        ),
    )
