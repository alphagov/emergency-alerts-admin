import json
from unittest.mock import ANY

import pytest
from flask import url_for
from freezegun import freeze_time

from tests import NotifyBeautifulSoup, template_json, validate_route_permission
from tests.app.main.views.test_template_folders import (
    PARENT_FOLDER_ID,
    _folder,
    _template,
)
from tests.conftest import (
    SERVICE_ONE_ID,
    TEMPLATE_ONE_ID,
    ElementNotFound,
    create_active_user_view_permissions,
    normalize_spaces,
)


@pytest.mark.parametrize(
    "permissions, expected_message",
    (
        (["email"], "You need a template before you can send emails, text messages or letters."),
        (["sms"], "You need a template before you can send emails, text messages or letters."),
        (["letter"], "You need a template before you can send emails, text messages or letters."),
        (["email", "sms", "letter"], "You need a template before you can send emails, text messages or letters."),
        (["broadcast"], "You haven’t added any templates yet."),
    ),
)
def test_should_show_empty_page_when_no_templates(
    client_request,
    service_one,
    mock_get_service_templates_when_no_templates_exist,
    mock_get_template_folders,
    mock_get_no_api_keys,
    permissions,
    expected_message,
):
    service_one["permissions"] = permissions

    page = client_request.get(
        "main.choose_template",
        service_id=service_one["id"],
    )

    assert normalize_spaces(page.select_one("h1").text) == "Templates"
    assert normalize_spaces(page.select_one("main p").text) == (expected_message)
    assert page.select_one("#add_new_folder_form")
    assert page.select_one("#add_new_template_form")


def test_should_show_add_template_form_if_service_has_folder_permission(
    client_request,
    service_one,
    mock_get_service_templates_when_no_templates_exist,
    mock_get_template_folders,
    mock_get_no_api_keys,
):
    page = client_request.get(
        "main.choose_template",
        service_id=service_one["id"],
    )

    assert normalize_spaces(page.select_one("h1").text) == "Templates"
    assert normalize_spaces(page.select_one("main p").text) == ("You haven’t added any templates yet.")
    assert [(item["name"], item["value"]) for item in page.select("[type=radio]")] == [
        ("add_template_by_template_type", "broadcast"),
    ]
    assert not page.select("main a")


@pytest.mark.parametrize(
    "user, expected_page_title, extra_args, expected_nav_links, expected_templates",
    [
        (
            create_active_user_view_permissions(),
            "Templates",
            {},
            ["Broadcast"],
            [
                "broadcast_template_1",
                "broadcast_template_2",
                "broadcast_template_3",
                "broadcast_template_4",
                "broadcast_template_5",
                "broadcast_template_6",
            ],
        ),
        (
            create_active_user_view_permissions(),
            "Templates",
            {"template_type": "broadcast"},
            ["Broadcast"],
            [
                "broadcast_template_1",
                "broadcast_template_2",
                "broadcast_template_3",
                "broadcast_template_4",
                "broadcast_template_5",
                "broadcast_template_6",
            ],
        ),
    ],
)
def test_should_show_page_for_choosing_a_template(
    client_request,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_get_no_api_keys,
    extra_args,
    expected_nav_links,
    expected_templates,
    service_one,
    mocker,
    user,
    expected_page_title,
):
    client_request.login(user)

    page = client_request.get("main.choose_template", service_id=service_one["id"], **extra_args)

    assert normalize_spaces(page.select_one("h1").text) == expected_page_title

    template_links = page.select("#template-list .govuk-label a, .template-list-item a")

    assert len(template_links) == len(expected_templates)

    for index, expected_template in enumerate(expected_templates):
        assert template_links[index].text.strip() == expected_template

    mock_get_service_templates.assert_called_once_with(SERVICE_ONE_ID)
    mock_get_template_folders.assert_called_once_with(SERVICE_ONE_ID)


def test_should_show_page_of_broadcast_templates(
    mocker,
    client_request,
    service_one,
    fake_uuid,
    mock_get_template_folders,
    mock_get_no_api_keys,
):
    service_one["permissions"] += ["broadcast"]
    mocker.patch(
        "app.service_api_client.get_service_templates",
        return_value={
            "data": [
                template_json(
                    SERVICE_ONE_ID,
                    fake_uuid,
                    type_="broadcast",
                    name="A",
                    content="a" * 40,
                ),
                template_json(
                    SERVICE_ONE_ID,
                    fake_uuid,
                    type_="broadcast",
                    name="B",
                    content="b" * 42,
                ),
                template_json(
                    SERVICE_ONE_ID,
                    fake_uuid,
                    type_="broadcast",
                    name="C",
                    content="c" * 43,
                ),
                template_json(
                    SERVICE_ONE_ID,
                    fake_uuid,
                    type_="broadcast",
                    name="D",
                    # This should be truncated at 40 chars, then have the
                    # trailing space stripped
                    content=("d" * 39) + " " + ("d" * 40),
                ),
            ]
        },
    )
    page = client_request.get(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
    )
    assert [
        (
            normalize_spaces(template.select_one(".govuk-link").text),
            normalize_spaces(template.select_one(".govuk-hint").text),
        )
        for template in page.select(".template-list-item")
    ] == [
        (
            "A",
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        ),
        (
            "B",
            "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        ),
        (
            "C",
            "cccccccccccccccccccccccccccccccccccccccc…",
        ),
        (
            "D",
            "ddddddddddddddddddddddddddddddddddddddd…",
        ),
    ]


def test_choose_template_can_pass_through_an_initial_state_to_templates_and_folders_selection_form(
    client_request,
    mock_get_template_folders,
    mock_get_service_templates,
    mock_get_no_api_keys,
):
    page = client_request.get("main.choose_template", service_id=SERVICE_ONE_ID, initial_state="add-new-template")

    templates_and_folders_form = page.select_one("form")
    assert templates_and_folders_form["data-prev-state"] == "add-new-template"


def test_should_not_show_template_nav_if_only_one_type_of_template(
    client_request,
    mock_get_template_folders,
    mock_get_service_templates_with_only_one_template,
    mock_get_no_api_keys,
):
    page = client_request.get(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
    )

    assert not page.select(".pill")


def test_should_not_show_live_search_if_list_of_templates_fits_onscreen(
    client_request,
    mock_get_template_folders,
    mock_get_service_templates,
    mock_get_no_api_keys,
):
    page = client_request.get(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
    )

    assert not page.select(".live-search")


def test_should_show_live_search_if_list_of_templates_taller_than_screen(
    client_request,
    mock_get_template_folders,
    mock_get_more_service_templates_than_can_fit_onscreen,
    mock_get_no_api_keys,
):
    page = client_request.get(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
    )
    search = page.select_one(".live-search")

    assert search["data-notify-module"] == "live-search"
    assert search["data-targets"] == "#template-list .template-list-item"
    assert normalize_spaces(search.select_one("label").text) == "Search and filter by name"

    assert len(page.select(search["data-targets"])) == len(page.select("#template-list .govuk-label")) == 20


def test_should_label_search_by_id_for_services_with_api_keys(
    client_request,
    mock_get_template_folders,
    mock_get_more_service_templates_than_can_fit_onscreen,
    mock_get_api_keys,
):
    page = client_request.get(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
    )
    assert normalize_spaces(page.select_one(".live-search label").text) == "Search and filter by name or ID"


def test_should_show_live_search_if_service_has_lots_of_folders(
    client_request,
    mock_get_template_folders,
    mock_get_service_templates,  # returns 4 templates
    mock_get_no_api_keys,
):
    mock_get_template_folders.return_value = [
        _folder("one", PARENT_FOLDER_ID),
        _folder("two", None, parent=PARENT_FOLDER_ID),
        _folder("three", None, parent=PARENT_FOLDER_ID),
        _folder("four", None, parent=PARENT_FOLDER_ID),
    ]

    page = client_request.get(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
    )

    count_of_templates_and_folders = len(page.select("#template-list .govuk-label"))
    count_of_folders = len(page.select(".template-list-folder:first-of-type"))
    count_of_templates = count_of_templates_and_folders - count_of_folders

    assert len(page.select(".live-search")) == 1
    assert count_of_folders == 4
    assert count_of_templates == 6


def test_should_show_new_template_choices_if_service_has_folder_permission(
    client_request,
    service_one,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_get_no_api_keys,
):
    page = client_request.get(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
    )

    if not page.select("#add_new_template_form"):
        raise ElementNotFound()

    assert normalize_spaces(page.select_one("#add_new_template_form fieldset legend").text) == "New template"
    assert [choice["value"] for choice in page.select("#add_new_template_form input[type=radio]")] == [
        "broadcast",
        "copy-existing",
    ]
    assert [normalize_spaces(choice.text) for choice in page.select("#add_new_template_form label")] == [
        "Broadcast",
        "Copy an existing template",
    ]


def test_should_add_data_attributes_for_broadcast_service(
    client_request,
    service_one,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_get_no_api_keys,
):
    page = client_request.get(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
    )

    if not page.select("#add_new_template_form"):
        raise ElementNotFound()

    assert page.select_one("#add_new_template_form").attrs["data-channel"] == "broadcast"
    assert page.select_one("#add_new_template_form").attrs["data-service"] == SERVICE_ONE_ID


def test_should_show_page_for_one_template(
    client_request,
    mock_get_service_template,
    fake_uuid,
):
    template_id = fake_uuid
    page = client_request.get(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=template_id,
    )

    back_link = page.select_one(".govuk-back-link")
    assert back_link["href"] == url_for(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=template_id,
    )

    assert page.select_one("input[type=text]")["value"] == "Sample Template"
    assert "Template &lt;em&gt;content&lt;/em&gt; with &amp; entity" in str(page.select_one("textarea"))
    assert page.select_one("textarea")["data-notify-module"] == "enhanced-textbox"

    assert (
        (page.select_one("[data-notify-module=update-status]")["data-target"])
        == (page.select_one("textarea")["id"])
        == "template_content"
    )

    assert (page.select_one("[data-notify-module=update-status]")["data-updates-url"]) == url_for(
        ".count_content_length",
        service_id=SERVICE_ONE_ID,
        template_type="broadcast",
    )

    assert (page.select_one("[data-notify-module=update-status]")["aria-live"]) == "polite"

    mock_get_service_template.assert_called_with(SERVICE_ONE_ID, template_id, None)


def test_broadcast_template_doesnt_highlight_placeholders_but_does_count_characters(
    client_request,
    service_one,
    mock_get_broadcast_template,
    fake_uuid,
):
    service_one["permissions"] += ["broadcast"]
    page = client_request.get(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )
    assert page.select_one("textarea")["data-notify-module"] == "enhanced-textbox"
    assert page.select_one("textarea")["data-highlight-placeholders"] == "false"

    assert (
        (page.select_one("[data-notify-module=update-status]")["data-target"])
        == (page.select_one("textarea")["id"])
        == "template_content"
    )

    assert (page.select_one("[data-notify-module=update-status]")["data-updates-url"]) == url_for(
        ".count_content_length",
        service_id=SERVICE_ONE_ID,
        template_type="broadcast",
    )

    assert (page.select_one("[data-notify-module=update-status]")["aria-live"]) == "polite"


@pytest.mark.parametrize(
    "permissions, links_to_be_shown, permissions_warning_to_be_shown",
    [
        (["view_activity"], [], "If you need to send this broadcast or edit this template, contact your manager."),
        (
            ["manage_api_keys"],
            [],
            None,
        ),
        (
            ["manage_templates"],
            [
                (".edit_service_template", "Edit this template"),
            ],
            None,
        ),
    ],
)
def test_should_be_able_to_view_a_template_with_links(
    client_request,
    mock_get_service_template,
    mock_get_template_folders,
    active_user_with_permissions,
    fake_uuid,
    permissions,
    links_to_be_shown,
    permissions_warning_to_be_shown,
):
    active_user_with_permissions["permissions"][SERVICE_ONE_ID] = permissions + ["view_activity"]
    client_request.login(active_user_with_permissions)

    page = client_request.get(
        ".view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )

    assert normalize_spaces(page.select_one("h1").text) == "Template"
    assert normalize_spaces(page.select_one("title").text) == (
        "Sample Template – Templates – service one – GOV.UK Emergency Alerts"
    )

    assert [(link["href"], normalize_spaces(link.text)) for link in page.select(".pill-separate-item")] == [
        (
            url_for(
                endpoint,
                service_id=SERVICE_ONE_ID,
                template_id=fake_uuid,
            ),
            text,
        )
        for endpoint, text in links_to_be_shown
    ]
    if permissions_warning_to_be_shown is not None:
        assert normalize_spaces(page.select_one("main p").text) == (
            permissions_warning_to_be_shown or "To: phone number"
        )


def test_view_broadcast_template(
    client_request,
    service_one,
    mock_get_broadcast_template,
    mock_get_template_folders,
    fake_uuid,
    active_user_create_broadcasts_permission,
):
    active_user_create_broadcasts_permission["permissions"][SERVICE_ONE_ID].append("manage_templates")
    client_request.login(active_user_create_broadcasts_permission)
    page = client_request.get(
        ".view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )

    assert [(link.text.strip(), link["href"]) for link in page.select(".pill-separate-item")] == [
        (
            "Get ready to send",
            url_for(
                ".broadcast",
                service_id=SERVICE_ONE_ID,
                template_id=fake_uuid,
            ),
        ),
        (
            "Edit this template",
            url_for(
                ".edit_service_template",
                service_id=SERVICE_ONE_ID,
                template_id=fake_uuid,
            ),
        ),
    ]

    assert (
        (normalize_spaces(page.select_one(".template-container").text))
        == (normalize_spaces(page.select_one(".broadcast-message-wrapper").text))
        == "Emergency alert This is a test"
    )


def test_should_hide_template_id_for_broadcast_templates(
    client_request,
    mock_get_broadcast_template,
    mock_get_template_folders,
    fake_uuid,
):
    page = client_request.get(
        ".view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )
    assert not page.select(".copy-to-clipboard__value")


@pytest.mark.parametrize(
    "service_permissions, data, expected_error",
    (
        (
            ["letter"],
            {
                "operation": "add-new-template",
                "add_template_by_template_type": "broadcast",
            },
            "Sending broadcasts has been disabled for your service.",
        ),
    ),
)
def test_should_not_allow_creation_of_template_through_form_without_correct_permission(
    client_request,
    service_one,
    mock_get_service_templates,
    mock_get_template_folders,
    service_permissions,
    data,
    expected_error,
    fake_uuid,
):
    service_one["permissions"] = service_permissions
    page = client_request.post(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
        _data=data,
        _follow_redirects=True,
        _expected_status=403,
    )
    assert normalize_spaces(page.select("main p")[0].text) == expected_error
    assert page.select_one(".govuk-back-link").text.strip() == "Back"
    assert page.select(".govuk-back-link")[0]["href"] == url_for(
        ".choose_template",
        service_id=SERVICE_ONE_ID,
    )


@pytest.mark.parametrize("method", ("get", "post"))
@pytest.mark.parametrize(
    "type_of_template, expected_error",
    [
        ("broadcast", "Sending broadcasts has been disabled for your service."),
    ],
)
def test_should_not_allow_creation_of_a_template_without_correct_permission(
    client_request,
    service_one,
    mocker,
    method,
    type_of_template,
    expected_error,
):
    service_one["permissions"] = []

    page = getattr(client_request, method)(
        ".add_service_template",
        service_id=SERVICE_ONE_ID,
        template_type=type_of_template,
        _follow_redirects=True,
        _expected_status=403,
    )
    assert page.select("main p")[0].text.strip() == expected_error
    assert page.select_one(".govuk-back-link").text.strip() == "Back"
    assert page.select(".govuk-back-link")[0]["href"] == url_for(
        ".choose_template",
        service_id=service_one["id"],
    )


def test_should_redirect_when_saving_a_template(
    client_request,
    mock_get_service_template,
    mock_get_api_keys,
    mock_update_service_template,
    fake_uuid,
):
    name = "new name"
    content = "template <em>content</em> with & entity"
    client_request.post(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={
            "id": fake_uuid,
            "name": name,
            "template_content": content,
            "template_type": "broadcast",
            "service": SERVICE_ONE_ID,
        },
        _expected_status=302,
        _expected_redirect=url_for(
            ".view_template",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
        ),
    )
    mock_update_service_template.assert_called_with(
        fake_uuid,
        name,
        "broadcast",
        content,
        SERVICE_ONE_ID,
    )


def test_should_not_allow_template_edits_without_correct_permission(
    client_request,
    mock_get_service_template,
    service_one,
    fake_uuid,
):
    service_one["permissions"] = ["email"]

    page = client_request.get(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _follow_redirects=True,
        _expected_status=403,
    )

    assert page.select("main p")[0].text.strip() == "Sending broadcasts has been disabled for your service."
    assert page.select_one(".govuk-back-link").text.strip() == "Back"
    assert page.select(".govuk-back-link")[0]["href"] == url_for(
        ".view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
    )


@pytest.mark.parametrize(
    "content, expected_error",
    (
        (("ŴŶ" * 308), "Content must be 615 characters or fewer because it contains Ŵ and Ŷ"),
        (("ab" * 698), "Content must be 1,395 characters or fewer"),
    ),
)
def test_should_not_create_too_big_template_for_broadcasts(
    client_request,
    service_one,
    content,
    expected_error,
):
    service_one["permissions"] = ["broadcast"]
    page = client_request.post(
        ".add_service_template",
        service_id=SERVICE_ONE_ID,
        template_type="broadcast",
        _data={
            "name": "New name",
            "template_content": content,
            "template_type": "broadcast",
            "service": SERVICE_ONE_ID,
        },
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one(".error-message").text) == expected_error


def test_should_show_delete_template_page_with_escaped_template_name(client_request, mocker, fake_uuid):
    template = template_json(SERVICE_ONE_ID, fake_uuid, name="<script>evil</script>")

    mocker.patch("app.service_api_client.get_service_template", return_value={"data": template})

    page = client_request.get(
        ".delete_service_template", service_id=SERVICE_ONE_ID, template_id=fake_uuid, _test_page_title=False
    )
    banner = page.select_one(".banner-dangerous")
    assert banner.select("script") == []


@pytest.mark.parametrize("parent", (PARENT_FOLDER_ID, None))
def test_should_redirect_when_deleting_a_template(
    mocker,
    client_request,
    mock_delete_service_template,
    mock_get_template_folders,
    parent,
):
    mock_get_template_folders.return_value = [
        {"id": PARENT_FOLDER_ID, "name": "Folder", "parent": None, "users_with_permission": [ANY]}
    ]
    mock_get_service_template = mocker.patch(
        "app.service_api_client.get_service_template",
        return_value={
            "data": _template(
                "sms",
                "Hello",
                parent=parent,
            )
        },
    )

    client_request.post(
        ".delete_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=TEMPLATE_ONE_ID,
        _expected_status=302,
        _expected_redirect=url_for(
            ".choose_template",
            service_id=SERVICE_ONE_ID,
            template_folder_id=parent,
        ),
    )

    mock_get_service_template.assert_called_with(SERVICE_ONE_ID, TEMPLATE_ONE_ID, None)
    mock_delete_service_template.assert_called_with(SERVICE_ONE_ID, TEMPLATE_ONE_ID)


@freeze_time("2016-01-01T15:00")
def test_should_show_page_for_a_deleted_template(
    client_request,
    mock_get_template_folders,
    mock_get_deleted_template,
    mock_get_user,
    mock_get_user_by_email,
    mock_has_permissions,
    fake_uuid,
):
    template_id = fake_uuid
    page = client_request.get(
        ".view_template",
        service_id=SERVICE_ONE_ID,
        template_id=template_id,
        _test_page_title=False,
    )

    content = str(page)
    assert url_for("main.edit_service_template", service_id=SERVICE_ONE_ID, template_id=fake_uuid) not in content
    assert page.select("p.hint")[0].text.strip() == "This template was deleted today at 3:00pm."
    assert "Delete this template" not in page.select_one("main").text

    mock_get_deleted_template.assert_called_with(SERVICE_ONE_ID, template_id, None)


@pytest.mark.parametrize(
    "route", ["main.add_service_template", "main.edit_service_template", "main.delete_service_template"]
)
def test_route_permissions(
    route,
    mocker,
    notify_admin,
    client_request,
    api_user_active,
    service_one,
    mock_get_service_template,
    mock_get_template_folders,
    fake_uuid,
):
    validate_route_permission(
        mocker,
        notify_admin,
        "GET",
        200,
        url_for(route, service_id=service_one["id"], template_type="broadcast", template_id=fake_uuid),
        ["manage_templates"],
        api_user_active,
        service_one,
    )


def test_route_permissions_for_choose_template(
    mocker,
    notify_admin,
    client_request,
    api_user_active,
    mock_get_template_folders,
    service_one,
    mock_get_service_templates,
    mock_get_no_api_keys,
):
    validate_route_permission(
        mocker,
        notify_admin,
        "GET",
        200,
        url_for(
            "main.choose_template",
            service_id=service_one["id"],
        ),
        [],
        api_user_active,
        service_one,
    )


@pytest.mark.parametrize(
    "route", ["main.add_service_template", "main.edit_service_template", "main.delete_service_template"]
)
def test_route_invalid_permissions(
    route,
    mocker,
    notify_admin,
    client_request,
    api_user_active,
    service_one,
    mock_get_service_template,
    fake_uuid,
):
    validate_route_permission(
        mocker,
        notify_admin,
        "GET",
        403,
        url_for(route, service_id=service_one["id"], template_type="broadcast", template_id=fake_uuid),
        ["view_activity"],
        api_user_active,
        service_one,
    )


def test_add_template_page_furniture(
    client_request,
):
    page = client_request.get(
        ".add_service_template",
        service_id=SERVICE_ONE_ID,
        template_type="broadcast",
    )
    assert normalize_spaces(page.select_one("h1").text) == "New template"

    back_link = page.select_one(".govuk-back-link")
    assert back_link["href"] == url_for("main.choose_template", service_id=SERVICE_ONE_ID, template_folder_id=None)


def test_should_not_create_sms_or_broadcast_template_with_emoji(
    client_request,
    mock_create_service_template,
):
    page = client_request.post(
        ".add_service_template",
        service_id=SERVICE_ONE_ID,
        template_type="broadcast",
        _data={
            "name": "new name",
            "template_content": "here are some noodles 🍜",
            "template_type": "broadcast",
            "service": SERVICE_ONE_ID,
        },
        _expected_status=200,
    )
    assert "You cannot use 🍜 in broadcasts." in page.text
    assert mock_create_service_template.called is False


def test_should_not_update_broadcast_template_with_emoji(
    client_request,
    mock_get_service_template,
    mock_update_service_template,
    fake_uuid,
):
    page = client_request.post(
        ".edit_service_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _data={
            "id": fake_uuid,
            "name": "new name",
            "template_content": "here's a burger 🍔",
            "service": SERVICE_ONE_ID,
            "template_type": "broadcast",
        },
        _expected_status=200,
    )
    assert "You cannot use 🍔 in broadcasts." in page.text
    assert mock_update_service_template.called is False


def test_should_create_broadcast_template_without_downgrading_unicode_characters(
    client_request,
    mock_create_service_template,
):
    msg = "here:\tare some “fancy quotes” and non\u200Bbreaking\u200Bspaces"

    client_request.post(
        ".add_service_template",
        service_id=SERVICE_ONE_ID,
        template_type="broadcast",
        _data={
            "name": "new name",
            "template_content": msg,
            "template_type": "broadcast",
            "service": SERVICE_ONE_ID,
        },
        expected_status=302,
    )

    mock_create_service_template.assert_called_with(
        ANY,  # name
        ANY,  # type
        msg,  # content
        ANY,  # service_id
        ANY,  # parent_folder_id
    )


def test_should_not_show_redaction_stuff_for_broadcasts(
    client_request,
    fake_uuid,
    mock_get_broadcast_template,
    mock_get_template_folders,
):
    page = client_request.get(
        "main.view_template",
        service_id=SERVICE_ONE_ID,
        template_id=fake_uuid,
        _test_page_title=False,
    )

    assert page.select(".hint") == []
    assert "personalisation" not in " ".join(link.text.lower() for link in page.select("a"))


@pytest.mark.parametrize(
    "template_content",
    (
        "This is a ((test))",
        "This ((unsure??might)) be a test",
        pytest.param("This is a test", marks=pytest.mark.xfail),
    ),
)
@pytest.mark.parametrize(
    "template_type",
    (
        "broadcast",
        pytest.param("sms", marks=pytest.mark.xfail),
    ),
)
def test_should_not_create_broadcast_template_with_placeholders(
    client_request,
    service_one,
    mock_create_service_template,
    mock_update_service_template,
    template_content,
    template_type,
):
    service_one["permissions"] += [template_type]
    page = client_request.post(
        ".add_service_template",
        service_id=SERVICE_ONE_ID,
        template_type=template_type,
        _data={
            "name": "new name",
            "template_content": template_content,
            "service": SERVICE_ONE_ID,
        },
        _expected_status=200,
    )
    assert normalize_spaces(page.select_one(".error-message").text) == (
        "You can’t use ((double brackets)) to personalise this message"
    )
    assert mock_create_service_template.called is False


@pytest.mark.parametrize(
    "template_type, content, expected_message, expected_class",
    (
        (
            "broadcast",
            "",
            "You have 1,395 characters remaining",
            None,
        ),
        (
            "broadcast",
            "a",
            "You have 1,394 characters remaining",
            None,
        ),
        (
            "broadcast",
            "a" * 1395,
            "You have 0 characters remaining",
            None,
        ),
        (
            "broadcast",
            "a" * 1396,
            "You have 1 character too many",
            "govuk-error-message",
        ),
        (
            "broadcast",
            "a" * 1397,
            "You have 2 characters too many",
            "govuk-error-message",
        ),
        (
            "broadcast",
            "Ẅ" * 615,
            "You have 0 characters remaining",
            None,
        ),
        (
            "broadcast",
            "Ẅ" * 616,
            "You have 1 character too many",
            "govuk-error-message",
        ),
    ),
)
def test_content_count_json_endpoint(
    client_request,
    service_one,
    template_type,
    content,
    expected_message,
    expected_class,
):
    response = client_request.post_response(
        "main.count_content_length",
        service_id=SERVICE_ONE_ID,
        template_type=template_type,
        _data={
            "template_content": content,
        },
        _expected_status=200,
    )

    html = json.loads(response.get_data(as_text=True))["html"]
    snippet = NotifyBeautifulSoup(html, "html.parser").select_one("span")

    assert normalize_spaces(snippet.text) == expected_message

    if snippet.has_attr("class"):
        assert snippet["class"] == [expected_class]
    else:
        assert expected_class is None


@pytest.mark.parametrize(
    "template_type",
    (
        "email",
        "letter",
        "banana",
    ),
)
def test_content_count_json_endpoint_for_unsupported_template_types(
    client_request,
    template_type,
):
    client_request.post(
        "main.count_content_length",
        service_id=SERVICE_ONE_ID,
        template_type=template_type,
        content="foo",
        _expected_status=404,
    )
