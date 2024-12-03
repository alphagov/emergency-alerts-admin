import pytest
from flask import url_for
from freezegun import freeze_time
from notifications_python_client.errors import HTTPError

from tests import organisation_json, service_json
from tests.conftest import (
    ORGANISATION_ID,
    SERVICE_ONE_ID,
    create_active_user_with_permissions,
    create_platform_admin_user,
    normalize_spaces,
)


def test_organisation_page_shows_all_organisations(client_request, platform_admin_user, mocker):
    orgs = [
        {"id": "A3", "name": "Test 3", "active": True, "count_of_live_services": 0},
        {"id": "B1", "name": "Test 1", "active": True, "count_of_live_services": 1},
        {"id": "C2", "name": "Test 2", "active": False, "count_of_live_services": 2},
    ]

    get_organisations = mocker.patch("app.models.organisation.AllOrganisations.client_method", return_value=orgs)
    client_request.login(platform_admin_user)
    page = client_request.get(".organisations")

    assert normalize_spaces(page.select_one("h1").text) == "Organisations"

    assert [
        (
            normalize_spaces(link.text),
            normalize_spaces(hint.text),
            link["href"],
        )
        for link, hint in zip(
            page.select(".browse-list-item a"),
            page.select(".browse-list-item .browse-list-hint"),
        )
    ] == [
        ("Test 1", "1 live service", url_for("main.organisation_dashboard", org_id="B1")),
        ("Test 2", "2 live services", url_for("main.organisation_dashboard", org_id="C2")),
        ("Test 3", "0 live services", url_for("main.organisation_dashboard", org_id="A3")),
    ]

    archived = page.select_one(".table-field-status-default.heading-medium")
    assert normalize_spaces(archived.text) == "- archived"
    assert normalize_spaces(archived.parent.text) == "Test 2 - archived 2 live services"

    assert normalize_spaces(page.select_one("a.govuk-button--secondary").text) == "New organisation"
    get_organisations.assert_called_once_with()


def test_view_organisation_shows_the_correct_organisation(client_request, mocker):
    org = {"id": ORGANISATION_ID, "name": "Test 1", "active": True}
    mocker.patch("app.organisations_client.get_organisation", return_value=org)
    mocker.patch("app.organisations_client.get_organisation_services", return_value=[])

    page = client_request.get(
        ".organisation_dashboard",
        org_id=ORGANISATION_ID,
    )

    assert normalize_spaces(page.select_one("h1").text) == "All services"
    assert (
        normalize_spaces(page.select_one(".govuk-hint").text)
        == "Test 1 has no live services on GOV.UK Emergency Alerts"
    )
    assert not page.select("a[download]")


def test_page_to_create_new_organisation(
    client_request,
    platform_admin_user,
    mocker,
):
    client_request.login(platform_admin_user)
    page = client_request.get(".add_organisation")

    assert [(input["type"], input["name"], input.get("value")) for input in page.select("input")] == [
        ("text", "name", ""),
        ("radio", "organisation_type", "central"),
        ("radio", "organisation_type", "local"),
        ("radio", "organisation_type", "nhs_central"),
        ("radio", "organisation_type", "nhs_local"),
        ("radio", "organisation_type", "nhs_gp"),
        ("radio", "organisation_type", "emergency_service"),
        ("radio", "organisation_type", "school_or_college"),
        ("radio", "organisation_type", "other"),
        ("radio", "crown_status", "crown"),
        ("radio", "crown_status", "non-crown"),
        ("hidden", "csrf_token", mocker.ANY),
    ]


def test_create_new_organisation(
    client_request,
    platform_admin_user,
    mocker,
):
    mock_create_organisation = mocker.patch(
        "app.organisations_client.create_organisation",
        return_value=organisation_json(ORGANISATION_ID),
    )

    client_request.login(platform_admin_user)
    client_request.post(
        ".add_organisation",
        _data={
            "name": "new name",
            "organisation_type": "local",
            "crown_status": "non-crown",
        },
        _expected_redirect=url_for(
            "main.organisation_settings",
            org_id=ORGANISATION_ID,
        ),
    )

    mock_create_organisation.assert_called_once_with(
        name="new name",
        organisation_type="local",
        crown=False,
        agreement_signed=False,
    )


def test_create_new_organisation_validates(
    client_request,
    platform_admin_user,
    mocker,
):
    mock_create_organisation = mocker.patch("app.organisations_client.create_organisation")

    client_request.login(platform_admin_user)
    page = client_request.post(
        ".add_organisation",
        _expected_status=200,
    )
    assert [
        (error["data-error-label"], normalize_spaces(error.text)) for error in page.select(".govuk-error-message")
    ] == [
        ("name", "Error: Cannot be empty"),
        ("organisation_type", "Error: Select the type of organisation"),
        ("crown_status", "Error: Select whether this organisation is a crown body"),
    ]
    assert mock_create_organisation.called is False


@pytest.mark.parametrize(
    "name, error_message",
    [
        ("", "Cannot be empty"),
        ("a", "at least two alphanumeric characters"),
        ("a" * 256, "Organisation name must be 255 characters or fewer"),
    ],
)
def test_create_new_organisation_fails_with_incorrect_input(
    client_request,
    platform_admin_user,
    mocker,
    name,
    error_message,
):
    mock_create_organisation = mocker.patch("app.organisations_client.create_organisation")

    client_request.login(platform_admin_user)
    page = client_request.post(
        ".add_organisation",
        _data={
            "name": name,
            "organisation_type": "local",
            "crown_status": "non-crown",
        },
        _expected_status=200,
    )
    assert mock_create_organisation.called is False
    assert error_message in page.select_one(".govuk-error-message").text


def test_create_new_organisation_fails_with_duplicate_name(
    client_request,
    platform_admin_user,
    mocker,
):
    def _create(**_kwargs):
        json_mock = mocker.Mock(return_value={"message": "Organisation name already exists"})
        resp_mock = mocker.Mock(status_code=400, json=json_mock)
        http_error = HTTPError(response=resp_mock, message="Default message")
        raise http_error

    mocker.patch("app.organisations_client.create_organisation", side_effect=_create)

    client_request.login(platform_admin_user)
    page = client_request.post(
        ".add_organisation",
        _data={
            "name": "Existing org",
            "organisation_type": "local",
            "crown_status": "non-crown",
        },
        _expected_status=200,
    )

    error_message = "This organisation name is already in use"
    assert error_message in page.select_one(".govuk-error-message").text


@freeze_time("2020-02-20 20:20")
def test_organisation_services_shows_live_services_and_usage_with_count_of_1(
    client_request,
    mock_get_organisation,
    mocker,
    active_user_with_permissions,
    fake_uuid,
):
    mocker.patch(
        "app.organisations_client.get_organisation_services",
        return_value=[
            {
                "id": SERVICE_ONE_ID,
                "name": "Service 1",
            },
        ],
    )

    client_request.login(active_user_with_permissions)
    page = client_request.get(".organisation_dashboard", org_id=ORGANISATION_ID)

    usage_rows = page.select("main .organisation-service")

    assert len(usage_rows) == 1
    assert normalize_spaces(usage_rows[0].text) == "Service 1"


@freeze_time("2020-02-20 20:20")
def test_organisation_services_shows_search_bar(
    client_request,
    mock_get_organisation,
    mocker,
    active_user_with_permissions,
    fake_uuid,
):
    mocker.patch(
        "app.organisations_client.get_organisation_services",
        return_value=[{"id": "id-1", "name": "Service 1"}] * 8,
    )

    client_request.login(active_user_with_permissions)
    page = client_request.get(".organisation_dashboard", org_id=ORGANISATION_ID)

    services = page.select(".organisation-service")
    assert len(services) == 8

    assert page.select_one(".live-search")["data-targets"] == ".organisation-service"
    assert [normalize_spaces(service_name.text) for service_name in page.select(".live-search-relevant")] == [
        "Service 1",
        "Service 1",
        "Service 1",
        "Service 1",
        "Service 1",
        "Service 1",
        "Service 1",
        "Service 1",
    ]


@freeze_time("2020-02-20 20:20")
def test_organisation_services_hides_search_bar_for_7_or_fewer_services(
    client_request,
    mock_get_organisation,
    mocker,
    active_user_with_permissions,
    fake_uuid,
):
    mocker.patch(
        "app.organisations_client.get_organisation_services",
        return_value=[{"id": "id-1", "name": "Service 1"}] * 7,
    )

    client_request.login(active_user_with_permissions)
    page = client_request.get(".organisation_dashboard", org_id=ORGANISATION_ID)

    services = page.select(".organisation-service")
    assert len(services) == 7
    assert not page.select_one(".live-search")


def test_organisation_trial_mode_services_shows_all_non_live_services(
    client_request,
    platform_admin_user,
    mock_get_organisation,
    mocker,
    fake_uuid,
):
    mocker.patch(
        "app.organisations_client.get_organisation_services",
        return_value=[
            service_json(id_="1", name="1", restricted=False, active=True),  # live
            service_json(id_="2", name="2", restricted=True, active=True),  # trial
            service_json(id_="3", name="3", restricted=False, active=False),  # archived
        ],
    )

    client_request.login(platform_admin_user)
    page = client_request.get(".organisation_trial_mode_services", org_id=ORGANISATION_ID, _test_page_title=False)

    services = page.select(".browse-list-item")
    assert len(services) == 2

    assert normalize_spaces(services[0].text) == "2"
    assert normalize_spaces(services[1].text) == "3"
    assert services[0].find("a")["href"] == url_for("main.service_dashboard", service_id="2")
    assert services[1].find("a")["href"] == url_for("main.service_dashboard", service_id="3")


def test_organisation_trial_mode_services_doesnt_work_if_not_platform_admin(
    client_request,
    mock_get_organisation,
):
    client_request.get(".organisation_trial_mode_services", org_id=ORGANISATION_ID, _expected_status=403)


def test_manage_org_users_shows_correct_link_next_to_each_user(
    client_request,
    mock_get_organisation,
    mock_get_users_for_organisation,
    mock_get_invited_users_for_organisation,
):
    page = client_request.get(
        ".manage_org_users",
        org_id=ORGANISATION_ID,
    )

    # No banner confirming a user to be deleted shown
    assert not page.select_one(".banner-dangerous")

    users = page.select(".user-list-item")

    # The first user is an invited user, so has the link to cancel the invitation.
    # The second two users are active users, so have the link to be removed from the org
    assert (
        normalize_spaces(users[0].text)
        == "invited_user@test.gov.uk (invited) Cancel invitation for invited_user@test.gov.uk"
    )
    assert normalize_spaces(users[1].text) == "Test User 1 test@gov.uk Remove Test User 1 test@gov.uk"
    assert normalize_spaces(users[2].text) == "Test User 2 testt@gov.uk Remove Test User 2 testt@gov.uk"

    assert users[0].a["href"] == url_for(
        ".cancel_invited_org_user", org_id=ORGANISATION_ID, invited_user_id="73616d70-6c65-4f6f-b267-5f696e766974"
    )
    assert users[1].a["href"] == url_for(".edit_organisation_user", org_id=ORGANISATION_ID, user_id="1234")
    assert users[2].a["href"] == url_for(".edit_organisation_user", org_id=ORGANISATION_ID, user_id="5678")


def test_manage_org_users_shows_no_link_for_cancelled_users(
    client_request,
    mock_get_organisation,
    mock_get_users_for_organisation,
    sample_org_invite,
    mocker,
):
    sample_org_invite["status"] = "cancelled"
    mocker.patch("app.models.user.OrganisationInvitedUsers.client_method", return_value=[sample_org_invite])

    page = client_request.get(
        ".manage_org_users",
        org_id=ORGANISATION_ID,
    )
    users = page.select(".user-list-item")

    assert normalize_spaces(users[0].text) == "invited_user@test.gov.uk (cancelled invite)"
    assert not users[0].a


@pytest.mark.parametrize(
    "number_of_users",
    (
        pytest.param(7, marks=pytest.mark.xfail),
        pytest.param(8),
    ),
)
def test_manage_org_users_should_show_live_search_if_more_than_7_users(
    client_request,
    mocker,
    mock_get_organisation,
    active_user_with_permissions,
    number_of_users,
):
    mocker.patch(
        "app.models.user.OrganisationInvitedUsers.client_method",
        return_value=[],
    )
    mocker.patch(
        "app.models.user.OrganisationUsers.client_method",
        return_value=[active_user_with_permissions] * number_of_users,
    )

    page = client_request.get(
        ".manage_org_users",
        org_id=ORGANISATION_ID,
    )

    assert page.select_one("div[data-notify-module=live-search]")["data-targets"] == ".user-list-item"
    assert len(page.select(".user-list-item")) == number_of_users

    textbox = page.select_one("[data-notify-module=autofocus] .govuk-input")
    assert "value" not in textbox
    assert textbox["name"] == "search"
    # data-notify-module=autofocus is set on a containing element so it
    # shouldn’t also be set on the textbox itself
    assert "data-notify-module" not in textbox
    assert not page.select_one("[data-force-focus]")
    assert textbox["class"] == [
        "govuk-input",
        "govuk-!-width-full",
    ]
    assert normalize_spaces(page.select_one("label[for=search]").text) == "Search and filter by name or email address"


def test_edit_organisation_user_shows_the_delete_confirmation_banner(
    client_request,
    mock_get_organisation,
    mock_get_invites_for_organisation,
    mock_get_users_for_organisation,
    active_user_with_permissions,
):
    page = client_request.get(
        ".edit_organisation_user", org_id=ORGANISATION_ID, user_id=active_user_with_permissions["id"]
    )

    assert normalize_spaces(page.select_one("h1").text) == "Team members"

    banner = page.select_one(".banner-dangerous")
    assert "Are you sure you want to remove Test User?" in normalize_spaces(banner.contents[0])
    assert banner.form.attrs["action"] == url_for(
        "main.remove_user_from_organisation", org_id=ORGANISATION_ID, user_id=active_user_with_permissions["id"]
    )


def test_remove_user_from_organisation_makes_api_request_to_remove_user(
    client_request,
    mocker,
    mock_get_organisation,
    fake_uuid,
):
    mock_remove_user = mocker.patch("app.organisations_client.remove_user_from_organisation")

    client_request.post(
        ".remove_user_from_organisation",
        org_id=ORGANISATION_ID,
        user_id=fake_uuid,
        _expected_redirect=url_for(
            "main.show_accounts_or_dashboard",
        ),
    )

    mock_remove_user.assert_called_with(ORGANISATION_ID, fake_uuid)


def test_organisation_settings_platform_admin_only(client_request, mock_get_organisation, organisation_one):
    client_request.get(
        ".organisation_settings",
        org_id=organisation_one["id"],
        _expected_status=403,
    )


def test_organisation_settings_for_platform_admin(
    client_request,
    platform_admin_user,
    mock_get_organisation,
    organisation_one,
):
    expected_rows = [
        "Label Value Action",
        "Name Test organisation Change organisation name",
        "Sector Central government Change sector for the organisation",
        "Crown organisation Yes Change organisation crown status",
        "Notes None Change the notes for the organisation",
        "Known email domains None Change known email domains for the organisation",
    ]

    client_request.login(platform_admin_user)
    page = client_request.get(".organisation_settings", org_id=organisation_one["id"])

    assert page.select_one("h1").text == "Settings"
    rows = page.select("tr")
    assert len(rows) == len(expected_rows)
    for index, row in enumerate(expected_rows):
        assert row == " ".join(rows[index].text.split())
    mock_get_organisation.assert_called_with(organisation_one["id"])


def test_organisation_settings_shows_delete_link(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_organisation,
):
    client_request.login(platform_admin_user)
    page = client_request.get(".organisation_settings", org_id=organisation_one["id"])

    delete_link = page.select(".page-footer-link a")[0]
    assert normalize_spaces(delete_link.text) == "Delete this organisation"
    assert delete_link["href"] == url_for(
        "main.archive_organisation",
        org_id=organisation_one["id"],
    )


def test_organisation_settings_does_not_show_delete_link_for_archived_organisations(
    client_request,
    platform_admin_user,
    organisation_one,
    mocker,
):
    organisation_one["active"] = False
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    client_request.login(platform_admin_user)
    page = client_request.get(".organisation_settings", org_id=organisation_one["id"])

    assert not page.select(".page-footer-link a")


def test_archive_organisation_is_platform_admin_only(
    client_request,
    organisation_one,
    mock_get_organisation,
    mocker,
):
    client_request.get("main.archive_organisation", org_id=organisation_one["id"], _expected_status=403)


def test_archive_organisation_prompts_user(
    client_request,
    platform_admin_user,
    organisation_one,
    mocker,
):
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    client_request.login(platform_admin_user)
    delete_page = client_request.get(
        "main.archive_organisation",
        org_id=organisation_one["id"],
        _test_page_prefix="Are you sure you want to delete ‘organisation one’?",
    )
    assert normalize_spaces(delete_page.select_one(".banner-dangerous").text) == (
        "Are you sure you want to delete ‘organisation one’? There’s no way to undo this. Yes, delete"
    )


@pytest.mark.parametrize("method", ["get", "post"])
def test_archive_organisation_gives_403_for_inactive_orgs(
    client_request,
    platform_admin_user,
    organisation_one,
    mocker,
    method,
):
    organisation_one["active"] = False
    mocker.patch("app.organisations_client.get_organisation", return_value=organisation_one)

    client_request.login(platform_admin_user)

    getattr(client_request, method)("main.archive_organisation", org_id=organisation_one["id"], _expected_status=403)


def test_archive_organisation_after_confirmation(
    client_request,
    platform_admin_user,
    organisation_one,
    mocker,
    mock_get_organisation,
    mock_get_organisations,
    mock_get_organisations_and_services_for_user,
    mock_get_service_and_organisation_counts,
):
    mock_api = mocker.patch("app.organisations_client.post")

    client_request.login(platform_admin_user)
    page = client_request.post("main.archive_organisation", org_id=organisation_one["id"], _follow_redirects=True)
    mock_api.assert_called_once_with(url=f"/organisations/{organisation_one['id']}/archive", data=None)
    assert normalize_spaces(page.select_one("h1").text) == "Choose service"
    assert normalize_spaces(page.select_one(".banner-default-with-tick").text) == "‘Test organisation’ was deleted"


@pytest.mark.parametrize(
    "error_message",
    [
        "Cannot archive an organisation with services",
        "Cannot archive an organisation with team members or invited team members",
    ],
)
def test_archive_organisation_does_not_allow_orgs_with_team_members_or_services_to_be_archived(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_organisation,
    mock_get_users_for_organisation,
    mock_get_invited_users_for_organisation,
    mocker,
    error_message,
):
    mocker.patch(
        "app.organisations_client.archive_organisation",
        side_effect=HTTPError(
            response=mocker.Mock(status_code=400, json={"result": "error", "message": error_message}),
            message=error_message,
        ),
    )
    client_request.login(platform_admin_user)
    page = client_request.post(
        "main.archive_organisation",
        org_id=organisation_one["id"],
        _expected_status=200,
    )

    assert normalize_spaces(page.select_one("div.banner-dangerous").text) == error_message


@pytest.mark.parametrize(
    "endpoint, expected_options, expected_selected",
    (
        (
            ".edit_organisation_type",
            (
                {"value": "central", "label": "Central government"},
                {"value": "local", "label": "Local government"},
                {"value": "nhs_central", "label": "NHS – central government agency or public body"},
                {"value": "nhs_local", "label": "NHS Trust or Clinical Commissioning Group"},
                {"value": "nhs_gp", "label": "GP practice"},
                {"value": "emergency_service", "label": "Emergency service"},
                {"value": "school_or_college", "label": "School or college"},
                {"value": "other", "label": "Other"},
            ),
            "central",
        ),
        (
            ".edit_organisation_crown_status",
            (
                {"value": "crown", "label": "Yes"},
                {"value": "non-crown", "label": "No"},
                {"value": "unknown", "label": "Not sure"},
            ),
            "crown",
        ),
    ),
)
@pytest.mark.parametrize(
    "user",
    (
        pytest.param(
            create_platform_admin_user(),
        ),
        pytest.param(create_active_user_with_permissions(), marks=pytest.mark.xfail),
    ),
)
def test_view_organisation_settings(
    client_request,
    fake_uuid,
    organisation_one,
    mock_get_organisation,
    endpoint,
    expected_options,
    expected_selected,
    user,
):
    client_request.login(user)

    page = client_request.get(endpoint, org_id=organisation_one["id"])

    radios = page.select("input[type=radio]")

    for index, option in enumerate(expected_options):
        option_values = {
            "value": radios[index]["value"],
            "label": normalize_spaces(page.select_one("label[for={}]".format(radios[index]["id"])).text),
        }
        if "hint" in option:
            option_values["hint"] = normalize_spaces(
                page.select_one("label[for={}] + .govuk-hint".format(radios[index]["id"])).text
            )
        assert option_values == option

    if expected_selected:
        assert page.select_one("input[checked]")["value"] == expected_selected
    else:
        assert not page.select_one("input[checked]")


@pytest.mark.parametrize(
    "endpoint, post_data, expected_persisted",
    (
        (
            ".edit_organisation_type",
            {"organisation_type": "central"},
            {"organisation_type": "central"},
        ),
        (
            ".edit_organisation_type",
            {"organisation_type": "local"},
            {"organisation_type": "local"},
        ),
        (
            ".edit_organisation_type",
            {"organisation_type": "nhs_local"},
            {"organisation_type": "nhs_local"},
        ),
        (
            ".edit_organisation_crown_status",
            {"crown_status": "crown"},
            {"crown": True},
        ),
        (
            ".edit_organisation_crown_status",
            {"crown_status": "non-crown"},
            {"crown": False},
        ),
        (
            ".edit_organisation_crown_status",
            {"crown_status": "unknown"},
            {"crown": None},
        ),
    ),
)
@pytest.mark.parametrize(
    "user",
    (
        pytest.param(
            create_platform_admin_user(),
        ),
        pytest.param(create_active_user_with_permissions(), marks=pytest.mark.xfail),
    ),
)
def test_update_organisation_settings(
    mocker,
    client_request,
    fake_uuid,
    organisation_one,
    mock_get_organisation,
    mock_update_organisation,
    endpoint,
    post_data,
    expected_persisted,
    user,
):
    mocker.patch("app.organisations_client.get_organisation_services", return_value=[])
    client_request.login(user)

    client_request.post(
        endpoint,
        org_id=organisation_one["id"],
        _data=post_data,
        _expected_status=302,
        _expected_redirect=url_for(
            "main.organisation_settings",
            org_id=organisation_one["id"],
        ),
    )

    mock_update_organisation.assert_called_once_with(
        organisation_one["id"],
        **expected_persisted,
    )


def test_update_organisation_sector_sends_service_id_data_to_api_client(
    client_request,
    mock_get_organisation,
    organisation_one,
    mock_get_organisation_services,
    mock_update_organisation,
    platform_admin_user,
):
    client_request.login(platform_admin_user)

    client_request.post(
        "main.edit_organisation_type",
        org_id=organisation_one["id"],
        _data={"organisation_type": "central"},
        _expected_status=302,
        _expected_redirect=url_for(
            "main.organisation_settings",
            org_id=organisation_one["id"],
        ),
    )

    mock_update_organisation.assert_called_once_with(organisation_one["id"], organisation_type="central")


@pytest.mark.parametrize(
    "user",
    (
        pytest.param(
            create_platform_admin_user(),
        ),
        pytest.param(create_active_user_with_permissions(), marks=pytest.mark.xfail),
    ),
)
def test_view_organisation_domains(
    mocker,
    client_request,
    fake_uuid,
    user,
):
    client_request.login(user)

    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            org_id,
            "Org 1",
            domains=["example.gov.uk", "test.example.gov.uk"],
        ),
    )

    page = client_request.get(
        "main.edit_organisation_domains",
        org_id=ORGANISATION_ID,
    )

    assert [textbox.get("value") for textbox in page.select("input[type=text]")] == [
        "example.gov.uk",
        "test.example.gov.uk",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
    ]


@pytest.mark.parametrize(
    "post_data, expected_persisted",
    (
        (
            {
                "domains-0": "example.gov.uk",
                "domains-2": "example.gov.uk",
                "domains-3": "EXAMPLE.GOV.UK",
                "domains-5": "test.gov.uk",
            },
            {
                "domains": [
                    "example.gov.uk",
                    "test.gov.uk",
                ]
            },
        ),
        (
            {
                "domains-0": "",
                "domains-1": "",
                "domains-2": "",
            },
            {"domains": []},
        ),
    ),
)
@pytest.mark.parametrize(
    "user",
    (
        pytest.param(
            create_platform_admin_user(),
        ),
        pytest.param(create_active_user_with_permissions(), marks=pytest.mark.xfail),
    ),
)
def test_update_organisation_domains(
    client_request,
    fake_uuid,
    organisation_one,
    mock_get_organisation,
    mock_update_organisation,
    post_data,
    expected_persisted,
    user,
):
    client_request.login(user)

    client_request.post(
        "main.edit_organisation_domains",
        org_id=ORGANISATION_ID,
        _data=post_data,
        _expected_status=302,
        _expected_redirect=url_for(
            "main.organisation_settings",
            org_id=organisation_one["id"],
        ),
    )

    mock_update_organisation.assert_called_once_with(
        ORGANISATION_ID,
        **expected_persisted,
    )


def test_update_organisation_domains_when_domain_already_exists(
    mocker,
    client_request,
    fake_uuid,
    organisation_one,
    mock_get_organisation,
):
    user = create_platform_admin_user()
    client_request.login(user)

    mocker.patch(
        "app.organisations_client.update_organisation",
        side_effect=HTTPError(
            response=mocker.Mock(status_code=400, json={"result": "error", "message": "Domain already exists"}),
            message="Domain already exists",
        ),
    )

    response = client_request.post(
        "main.edit_organisation_domains",
        org_id=ORGANISATION_ID,
        _data={
            "domains": [
                "example.gov.uk",
            ]
        },
        _expected_status=200,
    )

    assert response.select_one("div.banner-dangerous").text.strip() == "This domain is already in use"


def test_update_organisation_domains_with_more_than_just_domain(
    mocker,
    client_request,
    fake_uuid,
):
    user = create_platform_admin_user()
    client_request.login(user)

    mocker.patch(
        "app.organisations_client.get_organisation",
        side_effect=lambda org_id: organisation_json(
            org_id,
            "Org 1",
            domains=["test.example.gov.uk"],
        ),
    )

    page = client_request.post(
        "main.edit_organisation_domains",
        org_id=ORGANISATION_ID,
        _data={
            "domains-0": "test@example.gov.uk",
            "domains-1": "example.gov.uk",
            "domains-2": "@example.gov.uk",
        },
        _expected_status=200,
    )

    assert normalize_spaces(page.select_one(".banner-dangerous").text) == (
        "There is a problem Item 1: Cannot contain @ Item 3: Cannot contain @"
    )

    assert [field["value"] for field in page.select("input[type=text][value]") if field["value"] != ""] == [
        "test@example.gov.uk",
        "example.gov.uk",
        "@example.gov.uk",
    ]


@pytest.mark.parametrize(
    "domain",
    (
        "nhs.net",
        "NHS.NET",
        "nhs.uk",
        pytest.param(
            "example.nhs.uk",
            marks=pytest.mark.xfail(reason="Subdomains still allowed"),
        ),
    ),
)
def test_update_organisation_domains_nhs_domains(
    client_request,
    mock_get_organisation,
    domain,
):
    user = create_platform_admin_user()
    client_request.login(user)

    page = client_request.post(
        "main.edit_organisation_domains",
        org_id=ORGANISATION_ID,
        _data={"domains-0": domain},
        _expected_status=200,
    )

    assert normalize_spaces(page.select_one(".banner-dangerous").text) == (
        f"There is a problem Item 1: Cannot be ‘{domain.lower()}’"
    )

    assert [field["value"] for field in page.select("input[type=text][value]") if field["value"] != ""] == [
        domain,
    ]


def test_update_organisation_name(
    client_request,
    platform_admin_user,
    fake_uuid,
    mock_get_organisation,
    mock_update_organisation,
):
    client_request.login(platform_admin_user)
    client_request.post(
        ".edit_organisation_name",
        org_id=fake_uuid,
        _data={"name": "TestNewOrgName"},
        _expected_redirect=url_for(
            ".organisation_settings",
            org_id=fake_uuid,
        ),
    )
    mock_update_organisation.assert_called_once_with(
        fake_uuid,
        name="TestNewOrgName",
    )


@pytest.mark.parametrize(
    "name, error_message",
    [
        ("", "Cannot be empty"),
        ("a", "at least two alphanumeric characters"),
        ("a" * 256, "Organisation name must be 255 characters or fewer"),
    ],
)
def test_update_organisation_with_incorrect_input(
    client_request, platform_admin_user, organisation_one, mock_get_organisation, name, error_message
):
    client_request.login(platform_admin_user)
    page = client_request.post(
        ".edit_organisation_name",
        org_id=organisation_one["id"],
        _data={"name": name},
        _expected_status=200,
    )
    assert error_message in page.select_one(".govuk-error-message").text


def test_update_organisation_with_non_unique_name(
    client_request,
    platform_admin_user,
    fake_uuid,
    mock_get_organisation,
    mocker,
):
    mocker.patch(
        "app.organisations_client.update_organisation",
        side_effect=HTTPError(
            response=mocker.Mock(
                status_code=400, json={"result": "error", "message": "Organisation name already exists"}
            ),
            message="Organisation name already exists",
        ),
    )
    client_request.login(platform_admin_user)
    page = client_request.post(
        ".edit_organisation_name",
        org_id=fake_uuid,
        _data={"name": "TestNewOrgName"},
        _expected_status=200,
    )

    assert "This organisation name is already in use" in page.select_one(".govuk-error-message").text


def test_view_edit_organisation_notes(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_organisation,
):
    client_request.login(platform_admin_user)
    page = client_request.get(
        "main.edit_organisation_notes",
        org_id=organisation_one["id"],
    )
    assert page.select_one("h1").text == "Edit organisation notes"
    assert page.select_one("label.form-label").text.strip() == "Notes"
    assert page.select_one("textarea").attrs["name"] == "notes"


def test_update_organisation_notes(
    client_request,
    platform_admin_user,
    organisation_one,
    mock_get_organisation,
    mock_update_organisation,
):
    client_request.login(platform_admin_user)
    client_request.post(
        "main.edit_organisation_notes",
        org_id=organisation_one["id"],
        _data={"notes": "Very fluffy"},
        _expected_redirect=url_for(
            "main.organisation_settings",
            org_id=organisation_one["id"],
        ),
    )
    mock_update_organisation.assert_called_with(organisation_one["id"], notes="Very fluffy")


def test_update_organisation_notes_errors_when_user_not_platform_admin(
    client_request,
    organisation_one,
    mock_get_organisation,
    mock_update_organisation,
):
    client_request.post(
        "main.edit_organisation_notes",
        org_id=organisation_one["id"],
        _data={"notes": "Very fluffy"},
        _expected_status=403,
    )


def test_update_organisation_notes_doesnt_call_api_when_notes_dont_change(
    client_request, platform_admin_user, organisation_one, mock_update_organisation, mocker
):
    mocker.patch(
        "app.organisations_client.get_organisation",
        return_value=organisation_json(id_=organisation_one["id"], name="Test Org", notes="Very fluffy"),
    )
    client_request.login(platform_admin_user)
    client_request.post(
        "main.edit_organisation_notes",
        org_id=organisation_one["id"],
        _data={"notes": "Very fluffy"},
        _expected_redirect=url_for(
            "main.organisation_settings",
            org_id=organisation_one["id"],
        ),
    )
    assert not mock_update_organisation.called
