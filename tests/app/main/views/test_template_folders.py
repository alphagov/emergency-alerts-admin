import uuid

import pytest
from flask import abort, url_for
from notifications_python_client.errors import HTTPError

from app.models.template import Template
from app.models.user import User
from tests import sample_uuid, template_json
from tests.conftest import (
    SERVICE_ONE_ID,
    TEMPLATE_ONE_ID,
    _template,
    create_active_new_user_view_permissions,
    create_active_user_view_permissions,
    create_active_user_with_permissions,
    create_template,
    normalize_spaces,
)

ROOT_FOLDER_ID = "__NONE__"
PARENT_FOLDER_ID = "7e979e79-d970-43a5-ac69-b625a8d147b0"
CHILD_FOLDER_ID = "92ee1ee0-e4ee-4dcc-b1a7-a5da9ebcfa2b"
GRANDCHILD_FOLDER_ID = "fafe723f-1d39-4a10-865f-e551e03d8886"
FOLDER_TWO_ID = "bbbb222b-2b22-2b22-222b-b222b22b2222"
FOLDER_B_ID = "dddb222b-2b22-2b22-222b-b222b22b6789"
FOLDER_C_ID = "ccbb222b-2b22-2b22-222b-b222b22b2345"


def _folder(name, folder_id=None, parent=None, users_with_permission=None):
    return {
        "name": name,
        "id": folder_id or str(uuid.uuid4()),
        "parent_id": parent,
        "users_with_permission": users_with_permission if users_with_permission is not None else [sample_uuid()],
    }


@pytest.mark.parametrize(
    (
        "expected_title_tag,"
        "expected_page_title,"
        "expected_parent_link_args,"
        "extra_args,"
        "expected_nav_links,"
        "expected_items, "
        "expected_displayed_items, "
        "expected_searchable_text, "
        "expected_empty_message "
    ),
    [
        (
            "Templates – service one – GOV.UK Emergency Alerts",
            ["Templates"],
            [],
            {"template_type": "broadcast"},
            ["Broadcast"],
            [
                "folder_one folder_one 1 folder",
                "folder_one folder_one_one folder_one folder_one_one 1 template, 1 folder",
                (
                    "folder_one folder_one_one folder_one_one_one "
                    "folder_one folder_one_one folder_one_one_one "
                    "1 template"
                ),
                (
                    "folder_one folder_one_one folder_one_one_one broadcast_template_nested_two "
                    "folder_one folder_one_one folder_one_one_one broadcast_template_nested_two "
                    "Broadcast template"
                ),
                (
                    "folder_one folder_one_one broadcast_template_nested_one "
                    "folder_one folder_one_one broadcast_template_nested_one "
                    "Broadcast template"
                ),
                "broadcast_template_one broadcast_template_one Broadcast template",
                "broadcast_template_two broadcast_template_two Broadcast template",
            ],
            [
                "folder_one folder_one 1 folder",
                "broadcast_template_one broadcast_template_one Broadcast template",
                "broadcast_template_two broadcast_template_two Broadcast template",
            ],
            [
                "folder_one",
                "folder_one_one",
                "folder_one_one_one",
                "broadcast_template_nested_two",
                "broadcast_template_nested_one",
                "broadcast_template_one",
                "broadcast_template_two",
            ],
            None,
        ),
        (
            "folder_one – Templates – service one – GOV.UK Emergency Alerts",
            ["Templates", "folder_one"],
            [{"template_type": "all"}],
            {"template_folder_id": PARENT_FOLDER_ID},
            ["Broadcast"],
            [
                "folder_one_one folder_one_one 1 template, 1 folder",
                "folder_one_one folder_one_one_one folder_one_one folder_one_one_one 1 template",
                (
                    "folder_one_one folder_one_one_one broadcast_template_nested_two "
                    "folder_one_one folder_one_one_one broadcast_template_nested_two "
                    "Broadcast template"
                ),
                (
                    "folder_one_one broadcast_template_nested_one "
                    "folder_one_one broadcast_template_nested_one "
                    "Broadcast template"
                ),
                "folder_one_two folder_one_two Empty",
            ],
            [
                "folder_one_one folder_one_one 1 template, 1 folder",
                "folder_one_two folder_one_two Empty",
            ],
            [
                "folder_one_one",
                "folder_one_one_one",
                "broadcast_template_nested_two",
                "broadcast_template_nested_one",
                "folder_one_two",
            ],
            None,
        ),
        (
            "folder_one – Templates – service one – GOV.UK Emergency Alerts",
            ["Templates", "folder_one"],
            [{"template_type": "broadcast"}],
            {"template_type": "broadcast", "template_folder_id": PARENT_FOLDER_ID},
            ["Broadcast"],
            [
                "folder_one_one folder_one_one 1 template, 1 folder",
                "folder_one_one folder_one_one_one folder_one_one folder_one_one_one 1 template",
                (
                    "folder_one_one folder_one_one_one broadcast_template_nested_two "
                    "folder_one_one folder_one_one_one broadcast_template_nested_two "
                    "Broadcast template"
                ),
                (
                    "folder_one_one broadcast_template_nested_one "
                    "folder_one_one broadcast_template_nested_one "
                    "Broadcast template"
                ),
            ],
            [
                "folder_one_one folder_one_one 1 template, 1 folder",
            ],
            [
                "folder_one_one",
                "folder_one_one_one",
                "broadcast_template_nested_two",
                "broadcast_template_nested_one",
            ],
            None,
        ),
        (
            "folder_one – Templates – service one – GOV.UK Emergency Alerts",
            ["Templates", "folder_one"],
            [{"template_type": "broadcast"}],
            {"template_type": "broadcast", "template_folder_id": PARENT_FOLDER_ID},
            ["Broadcast"],
            [],
            [],
            [],
            "There are no broadcast templates in this folder",
        ),
        (
            "folder_one_one – folder_one – Templates – service one – GOV.UK Emergency Alerts",
            ["Templates", "folder_one", "folder_one_one"],
            [
                {"template_type": "all"},
                {"template_type": "all", "template_folder_id": PARENT_FOLDER_ID},
            ],
            {"template_folder_id": CHILD_FOLDER_ID},
            ["Broadcast"],
            [
                "folder_one_one_one folder_one_one_one 1 template",
                (
                    "folder_one_one_one broadcast_template_nested_two "
                    "folder_one_one_one broadcast_template_nested_two "
                    "Broadcast template"
                ),
                "broadcast_template_nested_one broadcast_template_nested_one Broadcast template",
            ],
            [
                "folder_one_one_one folder_one_one_one 1 template",
                "broadcast_template_nested_one broadcast_template_nested_one Broadcast template",
            ],
            [
                "folder_one_one_one",
                "broadcast_template_nested_two",
                "broadcast_template_nested_one",
            ],
            None,
        ),
        (
            "folder_one_one_one – folder_one_one – folder_one – Templates – service one – GOV.UK Emergency Alerts",
            ["Templates", "folder_one", "folder_one_one", "folder_one_one_one"],
            [
                {"template_type": "all"},
                {"template_type": "all", "template_folder_id": PARENT_FOLDER_ID},
                {"template_type": "all", "template_folder_id": CHILD_FOLDER_ID},
            ],
            {"template_folder_id": GRANDCHILD_FOLDER_ID},
            ["Broadcast"],
            ["broadcast_template_nested_two broadcast_template_nested_two Broadcast template"],
            ["broadcast_template_nested_two broadcast_template_nested_two Broadcast template"],
            ["broadcast_template_nested_two"],
            None,
        ),
        (
            "folder_one_one_one – folder_one_one – folder_one – Templates – service one – GOV.UK Emergency Alerts",
            ["Templates", "folder_one", "folder_one_one", "folder_one_one_one"],
            [
                {"template_type": "broadcast"},
                {"template_type": "broadcast", "template_folder_id": PARENT_FOLDER_ID},
                {"template_type": "broadcast", "template_folder_id": CHILD_FOLDER_ID},
            ],
            {
                "template_type": "broadcast",
                "template_folder_id": GRANDCHILD_FOLDER_ID,
            },
            ["Broadcast"],
            ["broadcast_template_nested_two broadcast_template_nested_two Broadcast template"],
            ["broadcast_template_nested_two broadcast_template_nested_two Broadcast template"],
            ["broadcast_template_nested_two"],
            None,
        ),
        (
            "folder_one_one_one – folder_one_one – folder_one – Templates – service one – GOV.UK Emergency Alerts",
            ["Templates", "folder_one", "folder_one_one", "folder_one_one_one"],
            [
                {"template_type": "all"},
                {"template_type": "all", "template_folder_id": PARENT_FOLDER_ID},
                {"template_type": "all", "template_folder_id": CHILD_FOLDER_ID},
            ],
            {
                "template_type": "all",
                "template_folder_id": GRANDCHILD_FOLDER_ID,
            },
            ["Broadcast"],
            ["broadcast_template_nested_two broadcast_template_nested_two Broadcast template"],
            ["broadcast_template_nested_two broadcast_template_nested_two Broadcast template"],
            ["broadcast_template_nested_two"],
            None,
        ),
        (
            "folder_two – Templates – service one – GOV.UK Emergency Alerts",
            ["Templates", "folder_two"],
            [{"template_type": "all"}],
            {"template_folder_id": FOLDER_TWO_ID},
            ["Broadcast"],
            [],
            [],
            [],
            "This folder is empty",
        ),
        (
            "folder_two – Templates – service one – GOV.UK Emergency Alerts",
            ["Templates", "folder_two"],
            [{"template_type": "broadcast"}],
            {"template_folder_id": FOLDER_TWO_ID, "template_type": "broadcast"},
            ["Broadcast"],
            [],
            [],
            [],
            "This folder is empty",
        ),
    ],
)
def test_should_show_templates_folder_page(
    client_request,
    mock_get_template_folders,
    mock_get_no_api_keys,
    service_one,
    mocker,
    expected_title_tag,
    expected_page_title,
    expected_parent_link_args,
    extra_args,
    expected_nav_links,
    expected_items,
    expected_displayed_items,
    expected_searchable_text,
    expected_empty_message,
):
    mock_get_template_folders.return_value = [
        _folder("folder_two", FOLDER_TWO_ID),
        _folder("folder_one", PARENT_FOLDER_ID),
        _folder("folder_one_two", parent=PARENT_FOLDER_ID),
        _folder("folder_one_one", CHILD_FOLDER_ID, parent=PARENT_FOLDER_ID),
        _folder("folder_one_one_one", GRANDCHILD_FOLDER_ID, parent=CHILD_FOLDER_ID),
    ]
    mock_template_data = (
        []
        if len(expected_items) == 0
        else [
            _template("broadcast", "broadcast_template_one"),
            _template("broadcast", "broadcast_template_two"),
            _template("broadcast", "broadcast_template_nested_one", parent=CHILD_FOLDER_ID),
            _template("broadcast", "broadcast_template_nested_two", parent=GRANDCHILD_FOLDER_ID),
        ]
    )
    mock_get_templates = mocker.patch(
        "app.template_api_client.get_templates",
        return_value={"data": mock_template_data},
    )

    page = client_request.get("main.choose_template", service_id=SERVICE_ONE_ID, _test_page_title=False, **extra_args)

    assert [item.text.strip() for item in page.select(".govuk-breadcrumbs__list-item")] == expected_page_title
    assert normalize_spaces(page.select_one("title").text) == expected_title_tag

    assert len(page.select(".govuk-breadcrumbs__list-item a")) == len(expected_parent_link_args)

    for index, parent_link in enumerate(page.select(".govuk-breadcrumbs__list-item a")):
        assert parent_link["href"] == url_for(
            "main.choose_template", service_id=SERVICE_ONE_ID, **expected_parent_link_args[index]
        )

    all_page_items = page.select(".template-list-item")
    all_page_items_styled_with_checkboxes = page.select(".template-list-item.govuk-checkboxes__item")

    assert len(all_page_items) == len(all_page_items_styled_with_checkboxes)

    checkboxes = page.select("input[name=templates_and_folders]")
    unique_checkbox_values = set(item["value"] for item in checkboxes)
    assert len(all_page_items) == len(expected_items)
    assert len(checkboxes) == len(expected_items)
    assert len(unique_checkbox_values) == len(expected_items)

    for index, expected_item in enumerate(expected_items):
        assert normalize_spaces(all_page_items[index].text) == expected_item

    displayed_page_items = page.select(".template-list-item:not(.template-list-item-hidden-by-default)")
    assert len(displayed_page_items) == len(expected_displayed_items)

    for index, expected_item in enumerate(expected_displayed_items):
        assert "/" not in expected_item
        assert normalize_spaces(displayed_page_items[index].text) == expected_item

    all_searchable_text = page.select("#template-list .template-list-item .live-search-relevant")
    assert len(all_searchable_text) == len(expected_searchable_text)

    for index, expected_item in enumerate(expected_searchable_text):
        assert normalize_spaces(all_searchable_text[index].text) == expected_item

    if expected_empty_message:
        assert normalize_spaces(page.select_one(".template-list-empty").text) == (expected_empty_message)
    else:
        assert not page.select(".template-list-empty")

    mock_get_templates.assert_called_once_with(SERVICE_ONE_ID)


def test_template_id_is_searchable_for_services_with_api_keys(
    client_request, mock_get_template_folders, mock_get_api_keys, service_one, mocker
):
    mock_get_template_folders.return_value = [
        _folder("folder one", PARENT_FOLDER_ID),
    ]
    template_1 = _template("broadcast", "template one")
    template_2 = _template("broadcast", "template two", parent=PARENT_FOLDER_ID)
    mocker.patch(
        "app.template_api_client.get_templates",
        return_value={
            "data": [
                template_1,
                template_2,
            ]
        },
    )

    page = client_request.get(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
        _test_page_title=False,
    )

    assert [
        normalize_spaces(item.text)
        for item in page.select(
            # Elements which the live search will filter by
            ".template-list-item .live-search-relevant"
        )
    ] == [
        "folder one",
        f'{template_2["id"]} template two',
        f'{template_1["id"]} template one',
    ]

    assert [
        normalize_spaces(item.text)
        for item in page.select(
            # Elements the user will see when first loading the page
            ".template-list-item:not(.template-list-item-hidden-by-default)"
        )
    ] == [
        "folder one folder one 1 template",
        f'template one {template_1["id"]} template one Broadcast template',
    ]

    assert [
        normalize_spaces(item.text)
        for item in page.select(
            # Text which should be hidden from all users
            r".template-list-item .govuk-\!-display-none"
        )
    ] == [
        template_2["id"],
        template_1["id"],
    ]

    mock_get_api_keys.assert_called_once_with(SERVICE_ONE_ID)


def test_can_create_email_template_with_parent_folder(
    client_request, mock_get_templates, mock_get_template_from_id, fake_uuid, mocker
):
    template = template_json(SERVICE_ONE_ID, fake_uuid, reference="Template", folder=PARENT_FOLDER_ID)
    mock_create_template = mocker.patch("app.models.template.Template.create", return_value=Template(template))
    data = {
        "reference": "new name",
        "content": "Broadcast template content",
        "template_type": "broadcast",
        "service": SERVICE_ONE_ID,
        "parent_folder_id": PARENT_FOLDER_ID,
    }
    client_request.post(
        ".add_service_template",
        service_id=SERVICE_ONE_ID,
        template_type="broadcast",
        template_folder_id=PARENT_FOLDER_ID,
        _data=data,
        _expected_redirect=url_for(
            "main.view_template",
            service_id=SERVICE_ONE_ID,
            template_id=fake_uuid,
        ),
    )
    mock_create_template.assert_called_once_with(
        reference=data["reference"],
        content=data["content"],
        service_id=SERVICE_ONE_ID,
        template_folder_id=data["parent_folder_id"],
    )


def test_get_manage_folder_page(
    client_request, active_user_with_permissions, service_one, mock_get_template_folders, mocker
):
    folder_id = str(uuid.uuid4())
    mock_get_template_folders.return_value = [
        _folder("folder_two", folder_id, None, [active_user_with_permissions["id"]]),
    ]
    mocker.patch(
        "app.models.user.Users.client_method",
        return_value=[active_user_with_permissions],
    )
    page = client_request.get(
        "main.manage_template_folder",
        service_id=service_one["id"],
        template_folder_id=folder_id,
        _test_page_title=False,
    )
    assert (
        normalize_spaces(page.select_one("title").text)
        == "folder_two – Templates – service one – GOV.UK Emergency Alerts"
    )
    assert page.select_one("input[name=name]")["value"] == "folder_two"
    delete_link = page.select_one("a.govuk-link--destructive")
    assert normalize_spaces(delete_link.text) == "Delete this folder"
    expected_delete_url = "/services/{}/templates/folders/{}/delete".format(service_one["id"], folder_id)
    assert expected_delete_url in delete_link["href"]


def test_get_manage_folder_viewing_permissions_for_users(
    client_request,
    active_user_with_permissions,
    service_one,
    mock_get_template_folders,
    mock_get_users_by_service,
    mocker,
):
    folder_id = str(uuid.uuid4())
    team_member = create_active_user_view_permissions(with_unique_id=True)
    team_member_2 = create_active_user_view_permissions(with_unique_id=True)

    mock_get_template_folders.return_value = [
        _folder("folder_two", folder_id, None, [active_user_with_permissions["id"], team_member_2["id"]]),
    ]
    mocker.patch(
        "app.models.user.Users.client_method",
        return_value=[active_user_with_permissions, team_member, team_member_2],
    )

    page = client_request.get(
        "main.manage_template_folder",
        service_id=service_one["id"],
        template_folder_id=folder_id,
        _test_page_title=False,
    )
    assert (
        normalize_spaces(page.select_one("title").text)
        == "folder_two – Templates – service one – GOV.UK Emergency Alerts"
    )
    form_labels = page.select("legend.govuk-fieldset__legend")
    assert normalize_spaces(form_labels[0].text) == "Team members who can see this folder"
    checkboxes = page.select("input[name=users_with_permission]")

    assert len(checkboxes) == 2
    assert checkboxes[0]["value"] == team_member["id"]
    assert "checked" not in checkboxes[0].attrs

    assert checkboxes[1]["value"] == team_member_2["id"]
    assert "checked" in checkboxes[1].attrs

    assert "Test User" in page.select_one("label[for=users_with_permission-1]").text


def test_get_manage_folder_viewing_permissions_for_users_not_visible_when_no_manage_settings_permission(
    client_request, active_user_with_permissions, service_one, mock_get_template_folders, mocker
):
    active_user_with_permissions["permissions"][SERVICE_ONE_ID] = [
        "manage_templates",
        "manage_api_keys",
        "view_activity",
    ]
    folder_id = str(uuid.uuid4())
    team_member = create_active_user_view_permissions(with_unique_id=True)
    team_member_2 = create_active_user_view_permissions(with_unique_id=True)
    service_one["permissions"] += ["edit_folder_permissions"]
    mock_get_template_folders.return_value = [
        {
            "id": folder_id,
            "name": "folder_two",
            "parent_id": None,
            "users_with_permission": [active_user_with_permissions["id"], team_member_2["id"]],
        },
    ]
    mocker.patch(
        "app.models.user.Users.client_method",
        return_value=[team_member, team_member_2],
    )

    client_request.login(active_user_with_permissions)
    page = client_request.get(
        "main.manage_template_folder",
        service_id=service_one["id"],
        template_folder_id=folder_id,
        _test_page_title=False,
    )
    assert (
        normalize_spaces(page.select_one("title").text)
        == "folder_two – Templates – service one – GOV.UK Emergency Alerts"
    )
    form_labels = page.select("legend[class=form-label]")
    assert len(form_labels) == 0
    checkboxes = page.select("input[name=users_with_permission]")
    assert len(checkboxes) == 0


def test_get_manage_folder_viewing_permissions_for_users_not_visible_for_services_with_one_user(
    client_request, active_user_with_permissions, service_one, mock_get_template_folders, mocker
):
    folder_id = str(uuid.uuid4())
    service_one["permissions"] += ["edit_folder_permissions"]
    mock_get_template_folders.return_value = [
        {
            "id": folder_id,
            "name": "folder_two",
            "parent_id": None,
            "users_with_permission": [active_user_with_permissions["id"]],
        },
    ]
    mocker.patch(
        "app.models.user.Users.client_method",
        return_value=[active_user_with_permissions],
    )

    page = client_request.get(
        "main.manage_template_folder",
        service_id=service_one["id"],
        template_folder_id=folder_id,
        _test_page_title=False,
    )
    assert (
        normalize_spaces(page.select_one("title").text)
        == "folder_two – Templates – service one – GOV.UK Emergency Alerts"
    )
    form_labels = page.select("legend[class=form-label]")
    assert len(form_labels) == 0


def test_manage_folder_page_404s(client_request, service_one, mock_get_template_folders):
    client_request.get(
        "main.manage_template_folder",
        service_id=service_one["id"],
        template_folder_id=str(uuid.uuid4()),
        _expected_status=404,
    )


def test_get_manage_folder_page_no_permissions(
    client_request,
    active_user_view_permissions,
):
    client_request.login(active_user_view_permissions)
    client_request.get(
        "main.manage_template_folder",
        service_id=SERVICE_ONE_ID,
        template_folder_id=PARENT_FOLDER_ID,
        _expected_status=403,
    )


@pytest.mark.parametrize(
    "endpoint",
    [
        "main.manage_template_folder",
        "main.delete_template_folder",
    ],
)
def test_user_access_denied_to_template_folder_actions_without_folder_permission(
    client_request, active_user_with_permissions, service_one, mock_get_template_folders, mocker, endpoint
):
    mock = mocker.patch(
        "app.models.service.Service.get_template_folder_with_user_permission_or_403",
        side_effect=lambda *args: abort(403),
    )

    folder_id = str(uuid.uuid4())
    client_request.get(
        endpoint,
        service_id=service_one["id"],
        template_folder_id=folder_id,
        _expected_status=403,
        _test_page_title=False,
    )

    mock.assert_called_once_with(folder_id, User(active_user_with_permissions))


@pytest.mark.parametrize(
    "endpoint",
    [
        "main.confirm_redact_template",
        "main.delete_service_template",
        "main.edit_service_template",
    ],
)
def test_user_access_denied_to_template_actions_without_folder_permission(
    client_request, active_user_with_permissions, service_one, mocker, endpoint
):
    mock = mocker.patch(
        "app.models.service.Service.get_template_with_user_permission_or_403", side_effect=lambda *args: abort(403)
    )

    template_id = str(uuid.uuid4())
    client_request.get(
        endpoint,
        service_id=service_one["id"],
        template_id=template_id,
        _expected_status=403,
        _test_page_title=False,
    )

    mock.assert_called_once_with(template_id, User(active_user_with_permissions))


def test_rename_folder(client_request, active_user_with_permissions, service_one, mock_get_template_folders, mocker):
    mock_update = mocker.patch("app.template_folder_api_client.update_template_folder")
    folder_id = str(uuid.uuid4())
    mock_get_template_folders.return_value = [
        _folder("folder_two", folder_id, None, [active_user_with_permissions["id"]])
    ]
    mocker.patch(
        "app.models.user.Users.client_method",
        return_value=[active_user_with_permissions],
    )

    client_request.post(
        "main.manage_template_folder",
        service_id=service_one["id"],
        template_folder_id=folder_id,
        _data={"name": "new beautiful name", "users_with_permission": []},
        _expected_redirect=url_for(
            "main.choose_template",
            service_id=service_one["id"],
            template_folder_id=folder_id,
        ),
    )

    mock_update.assert_called_once_with(
        service_one["id"], folder_id, name="new beautiful name", users_with_permission=None
    )


def test_manage_folder_users(
    client_request, active_user_with_permissions, service_one, mock_get_template_folders, mocker
):
    team_member = create_active_user_view_permissions(with_unique_id=True)
    mock_update = mocker.patch("app.template_folder_api_client.update_template_folder")
    folder_id = str(uuid.uuid4())
    mock_get_template_folders.return_value = [
        _folder("folder_two", folder_id, None, [active_user_with_permissions["id"], team_member["id"]])
    ]
    mocker.patch(
        "app.models.user.Users.client_method",
        return_value=[active_user_with_permissions, team_member],
    )

    client_request.post(
        "main.manage_template_folder",
        service_id=service_one["id"],
        template_folder_id=folder_id,
        _data={"name": "new beautiful name", "users_with_permission": []},
        _expected_redirect=url_for(
            "main.choose_template",
            service_id=service_one["id"],
            template_folder_id=folder_id,
        ),
    )

    mock_update.assert_called_once_with(
        service_one["id"],
        folder_id,
        name="new beautiful name",
        users_with_permission=[active_user_with_permissions["id"]],
    )


def test_manage_folder_users_doesnt_change_permissions_current_user_cannot_manage_users(
    client_request, active_user_with_permissions, service_one, mock_get_template_folders, mocker
):
    active_user_with_permissions["permissions"][SERVICE_ONE_ID] = [
        "manage_templates",
        "manage_api_keys",
        "view_activity",
    ]
    team_member = create_active_user_view_permissions(with_unique_id=True)
    mock_update = mocker.patch("app.template_folder_api_client.update_template_folder")
    folder_id = str(uuid.uuid4())
    mock_get_template_folders.return_value = [
        {
            "id": folder_id,
            "name": "folder_two",
            "parent_id": None,
            "users_with_permission": [active_user_with_permissions["id"], team_member["id"]],
        }
    ]
    mocker.patch(
        "app.models.user.Users.client_method",
        return_value=[team_member],
    )

    client_request.login(active_user_with_permissions)
    client_request.post(
        "main.manage_template_folder",
        service_id=service_one["id"],
        template_folder_id=folder_id,
        _data={"name": "new beautiful name", "users_with_permission": []},
        _expected_redirect=url_for(
            "main.choose_template",
            service_id=service_one["id"],
            template_folder_id=folder_id,
        ),
    )

    mock_update.assert_called_once_with(
        service_one["id"], folder_id, name="new beautiful name", users_with_permission=None
    )


def test_delete_template_folder_should_request_confirmation(
    client_request, service_one, mocker, mock_get_service_templates_when_no_templates_exist, mock_get_templates
):
    mocker.patch("app.models.service.Service.active_users", [])
    folder_id = str(uuid.uuid4())
    mocker.patch(
        "app.template_folder_api_client.get_template_folders",
        return_value=[
            _folder("sacrifice", folder_id, None),
        ],
    )
    page = client_request.get(
        "main.delete_template_folder",
        service_id=service_one["id"],
        template_folder_id=folder_id,
        _test_page_title=False,
    )
    assert normalize_spaces(page.select_one(".banner-dangerous").text) == (
        "Are you sure you want to delete the ‘sacrifice’ folder? Yes, delete"
    )

    assert len(page.select("main form")) == 2
    assert len(page.select("main button")) == 2

    assert "action" not in page.select("main form")[0]
    assert normalize_spaces(page.select("main form button")[0].text) == "Yes, delete"

    assert page.select("main form")[1]["action"] == url_for(
        "main.manage_template_folder",
        service_id=service_one["id"],
        template_folder_id=folder_id,
    )
    assert normalize_spaces(page.select("main form button")[1].text) == "Save"


def test_delete_template_folder_should_detect_non_empty_folder_on_get(
    client_request, service_one, mock_get_template_folders, mocker, mock_get_templates, mock_get_user
):
    folder_id = str(uuid.uuid4())
    mock_get_template_folders.side_effect = [[_folder("can't touch me", folder_id, None)], []]
    mocker.patch("app.template_api_client.get_templates", return_value={"data": [create_template(folder=folder_id)]})
    client_request.get(
        "main.delete_template_folder",
        service_id=service_one["id"],
        template_folder_id=folder_id,
        _expected_redirect=url_for(
            "main.choose_template",
            template_type="all",
            service_id=service_one["id"],
            template_folder_id=folder_id,
        ),
        _expected_status=302,
    )


@pytest.mark.parametrize(
    "parent_folder_id",
    (
        None,
        PARENT_FOLDER_ID,
    ),
)
def test_delete_folder(
    client_request,
    service_one,
    mock_get_template_folders,
    mocker,
    parent_folder_id,
    mock_get_service_templates_when_no_templates_exist,
    mock_get_templates,
):
    mock_delete = mocker.patch("app.template_folder_api_client.delete_template_folder")
    folder_id = str(uuid.uuid4())
    mock_get_template_folders.side_effect = [
        [
            _folder("sacrifice", folder_id, parent_folder_id),
        ],
        [],
    ]

    client_request.post(
        "main.delete_template_folder",
        service_id=service_one["id"],
        template_folder_id=folder_id,
        _expected_redirect=url_for(
            "main.choose_template",
            service_id=service_one["id"],
            template_folder_id=parent_folder_id,
        ),
    )

    mock_delete.assert_called_once_with(service_one["id"], folder_id)


@pytest.mark.parametrize(
    "user",
    [
        pytest.param(create_active_user_with_permissions()),
        pytest.param(create_active_user_view_permissions(), marks=pytest.mark.xfail(raises=AssertionError)),
    ],
)
def test_should_show_checkboxes_for_selecting_templates(
    client_request,
    mocker,
    service_one,
    mock_get_templates,
    mock_get_template_folders,
    mock_get_no_api_keys,
    user,
):
    client_request.login(user)

    page = client_request.get(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
    )
    checkboxes = page.select("input[name=templates_and_folders]")

    assert len(checkboxes) == 6

    assert checkboxes[0]["value"] == TEMPLATE_ONE_ID
    assert checkboxes[0]["id"] == "templates-or-folder-{}".format(TEMPLATE_ONE_ID)

    for index in (1, 2, 3):
        assert checkboxes[index]["value"] != TEMPLATE_ONE_ID
        assert TEMPLATE_ONE_ID not in checkboxes[index]["id"]


@pytest.mark.parametrize(
    "user",
    [
        create_active_user_view_permissions(),
        create_active_new_user_view_permissions(),
        pytest.param(
            create_active_user_with_permissions(),
            marks=pytest.mark.xfail(raises=AssertionError),
        ),
    ],
)
def test_should_not_show_radios_and_buttons_for_move_destination_if_incorrect_permissions(
    client_request,
    mocker,
    service_one,
    mock_get_templates,
    mock_get_template_folders,
    mock_get_no_api_keys,
    user,
):
    client_request.login(user)

    page = client_request.get(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
    )
    radios = page.select("input[type=radio]")
    radio_div = page.select("div#move_to_folder_radios")
    assert radios == page.select("input[name=move_to]")

    assert not radios
    assert not radio_div
    assert not page.select("button[name=operation]")


def test_should_show_radios_and_buttons_for_move_destination_if_correct_permissions(
    client_request,
    mocker,
    service_one,
    mock_get_templates,
    mock_get_template_folders,
    mock_get_no_api_keys,
    fake_uuid,
    active_user_with_permissions,
):
    client_request.login(active_user_with_permissions)

    FOLDER_TWO_ID = str(uuid.uuid4())
    FOLDER_ONE_TWO_ID = str(uuid.uuid4())
    mock_get_template_folders.return_value = [
        _folder("folder_one", PARENT_FOLDER_ID, None),
        _folder("folder_two", FOLDER_TWO_ID, None),
        _folder("folder_one_one", CHILD_FOLDER_ID, PARENT_FOLDER_ID),
        _folder("folder_one_two", FOLDER_ONE_TWO_ID, PARENT_FOLDER_ID),
    ]
    page = client_request.get(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
    )
    radios = page.select("#move_to_folder_radios input[type=radio]")
    radio_div = page.select_one("div#move_to_folder_radios")
    assert radios == page.select("input[name=move_to]")

    assert [x["value"] for x in radios] == [
        ROOT_FOLDER_ID,
        PARENT_FOLDER_ID,
        CHILD_FOLDER_ID,
        FOLDER_ONE_TWO_ID,
        FOLDER_TWO_ID,
    ]
    assert [x.text.strip() for x in radio_div.select("label")] == [
        "Templates",
        "folder_one",
        "folder_one_one",
        "folder_one_two",
        "folder_two",
    ]
    assert set(x["value"] for x in page.select("button[name=operation]")) == {
        "unknown",
        "move-to-existing-folder",
        "move-to-new-folder",
        "add-new-folder",
        "add-new-template",
    }


def test_move_to_shouldnt_select_a_folder_by_default(
    client_request,
    mocker,
    service_one,
    mock_get_templates,
    mock_get_template_folders,
    mock_get_no_api_keys,
    fake_uuid,
    active_user_with_permissions,
):
    client_request.login(active_user_with_permissions)

    FOLDER_TWO_ID = str(uuid.uuid4())
    mock_get_template_folders.return_value = [
        _folder("folder_one", PARENT_FOLDER_ID, None),
        _folder("folder_two", FOLDER_TWO_ID, None),
    ]
    page = client_request.get(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
    )
    checked_radio = page.select("input[name=move_to][checked=checked]")
    assert checked_radio == []


def test_should_be_able_to_move_to_existing_folder(
    client_request,
    service_one,
    mock_get_templates,
    mock_get_template_folders,
    mock_move_to_template_folder,
):
    FOLDER_TWO_ID = str(uuid.uuid4())
    mock_get_template_folders.return_value = [
        _folder("folder_one", PARENT_FOLDER_ID, None),
        _folder("folder_two", FOLDER_TWO_ID, None),
    ]
    client_request.post(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
        _data={
            "operation": "move-to-existing-folder",
            "move_to": PARENT_FOLDER_ID,
            "templates_and_folders": [
                FOLDER_TWO_ID,
                TEMPLATE_ONE_ID,
            ],
        },
        _expected_status=302,
        _expected_redirect=url_for(
            "main.choose_template",
            service_id=SERVICE_ONE_ID,
            _external=True,
        ),
    )
    mock_move_to_template_folder.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        folder_id=PARENT_FOLDER_ID,
        folder_ids={FOLDER_TWO_ID},
        template_ids={TEMPLATE_ONE_ID},
    )


@pytest.mark.parametrize(
    "user, expected_status, expected_called",
    [
        (create_active_user_view_permissions(), 403, False),
        (create_active_user_with_permissions(), 302, True),
    ],
)
def test_should_not_be_able_to_move_to_existing_folder_if_dont_have_permission(
    client_request,
    service_one,
    fake_uuid,
    mock_get_templates,
    mock_get_template_folders,
    mock_move_to_template_folder,
    user,
    expected_status,
    expected_called,
):
    client_request.login(user)
    FOLDER_TWO_ID = str(uuid.uuid4())
    mock_get_template_folders.return_value = [
        _folder("folder_one", PARENT_FOLDER_ID, None),
        _folder("folder_two", FOLDER_TWO_ID, None),
    ]
    client_request.post(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
        _data={
            "operation": "move-to-existing-folder",
            "move_to": PARENT_FOLDER_ID,
            "templates_and_folders": [
                FOLDER_TWO_ID,
                TEMPLATE_ONE_ID,
            ],
        },
        _expected_status=expected_status,
    )
    assert mock_move_to_template_folder.called is expected_called


def test_move_folder_form_shows_current_folder_hint_when_in_a_folder(
    client_request,
    service_one,
    mock_get_templates,
    mock_get_template_folders,
    mock_get_no_api_keys,
):
    mock_get_template_folders.return_value = [
        _folder("parent_folder", PARENT_FOLDER_ID, None),
        _folder("child_folder", CHILD_FOLDER_ID, PARENT_FOLDER_ID),
    ]
    page = client_request.get(
        "main.choose_template", service_id=SERVICE_ONE_ID, template_folder_id=PARENT_FOLDER_ID, _test_page_title=False
    )

    assert page.select(f'input[name=move_to][value="{PARENT_FOLDER_ID}"]')

    move_form_labels = page.select("div#move_to_folder_radios label")

    assert len(move_form_labels) == 3
    assert normalize_spaces(move_form_labels[0].text) == "Templates"
    assert normalize_spaces(move_form_labels[1].text) == "parent_folder current folder"
    assert normalize_spaces(move_form_labels[2].text) == "child_folder"


def test_move_folder_form_does_not_show_current_folder_hint_at_the_top_level(
    client_request,
    service_one,
    mock_get_templates,
    mock_get_template_folders,
    mock_get_no_api_keys,
):
    mock_get_template_folders.return_value = [
        _folder("parent_folder", PARENT_FOLDER_ID, None),
        _folder("child_folder", CHILD_FOLDER_ID, PARENT_FOLDER_ID),
    ]
    page = client_request.get("main.choose_template", service_id=SERVICE_ONE_ID, _test_page_title=False)

    assert page.select(f'input[name=move_to][value="{PARENT_FOLDER_ID}"]')

    move_form_labels = page.select("div#move_to_folder_radios label")

    assert len(move_form_labels) == 3
    assert normalize_spaces(move_form_labels[0].text) == "Templates"
    assert normalize_spaces(move_form_labels[1].text) == "parent_folder"
    assert normalize_spaces(move_form_labels[2].text) == "child_folder"


def test_should_be_able_to_move_a_sub_item(
    client_request,
    service_one,
    fake_uuid,
    mock_get_templates,
    mock_get_template_folders,
    mock_move_to_template_folder,
):
    GRANDCHILD_FOLDER_ID = str(uuid.uuid4())
    mock_get_template_folders.return_value = [
        _folder("folder_one", PARENT_FOLDER_ID, None),
        _folder("folder_one_one", CHILD_FOLDER_ID, PARENT_FOLDER_ID),
        _folder("folder_one_one_one", GRANDCHILD_FOLDER_ID, CHILD_FOLDER_ID),
    ]
    client_request.post(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
        template_folder_id=PARENT_FOLDER_ID,
        _data={
            "operation": "move-to-existing-folder",
            "move_to": ROOT_FOLDER_ID,
            "templates_and_folders": [GRANDCHILD_FOLDER_ID],
        },
        _expected_status=302,
    )
    mock_move_to_template_folder.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        folder_id=None,
        folder_ids={GRANDCHILD_FOLDER_ID},
        template_ids=set(),
    )


@pytest.mark.parametrize(
    "data",
    [
        # move to existing, but add new folder name given
        {
            "operation": "move-to-existing-folder",
            "templates_and_folders": [],
            "add_new_folder_name": "foo",
            "move_to": PARENT_FOLDER_ID,
        },
        # move to existing, but move to new folder name given
        {
            "operation": "move-to-existing-folder",
            "templates_and_folders": [TEMPLATE_ONE_ID],
            "move_to_new_folder_name": "foo",
            "move_to": PARENT_FOLDER_ID,
        },
        # move to existing, but no templates to move
        {
            "operation": "move-to-existing-folder",
            "templates_and_folders": [],
            "move_to_new_folder_name": "",
            "move_to": PARENT_FOLDER_ID,
        },
        # move to new, but nothing selected to move
        {
            "operation": "move-to-new-folder",
            "templates_and_folders": [],
            "move_to_new_folder_name": "foo",
            "move_to": None,
        },
        # add a new template, but also select move destination
        {
            "operation": "add-new-template",
            "templates_and_folders": [],
            "move_to_new_folder_name": "",
            "move_to": PARENT_FOLDER_ID,
            "add_template_by_template_type": "broadcast",
        },
        # add a new template, but also move to root folder
        {
            "operation": "add-new-template",
            "templates_and_folders": [],
            "move_to_new_folder_name": "",
            "move_to": ROOT_FOLDER_ID,
            "add_template_by_template_type": "broadcast",
        },
        # add a new template, but don't select anything
        {
            "operation": "add-new-template",
        },
    ],
)
def test_no_action_if_user_fills_in_ambiguous_fields(
    client_request,
    service_one,
    mock_get_templates,
    mock_get_template_folders,
    mock_move_to_template_folder,
    mock_create_template_folder,
    mock_get_no_api_keys,
    data,
):
    mock_get_template_folders.return_value = [
        _folder("parent_folder", PARENT_FOLDER_ID, None),
        _folder("folder_two", FOLDER_TWO_ID, None),
    ]

    page = client_request.post(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
        _data=data,
        _expected_status=200,
        _expected_redirect=None,
    )

    assert mock_move_to_template_folder.called is False
    assert mock_create_template_folder.called is False

    assert page.select_one("button[value={}]".format(data["operation"]))

    assert [
        "broadcast",
        "copy-existing",
    ] == [radio["value"] for radio in page.select("#add_new_template_form input[type=radio]")]

    assert [
        ROOT_FOLDER_ID,
        FOLDER_TWO_ID,
        PARENT_FOLDER_ID,
    ] == [radio["value"] for radio in page.select("#move_to_folder_radios input[type=radio]")]


def test_new_folder_is_created_if_only_new_folder_is_filled_out(
    client_request,
    service_one,
    mock_get_templates,
    mock_get_template_folders,
    mock_move_to_template_folder,
    mock_create_template_folder,
):
    data = {"move_to_new_folder_name": "", "add_new_folder_name": "new folder", "operation": "add-new-folder"}

    client_request.post(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
        _data=data,
        _expected_status=302,
        _expected_redirect=url_for(
            "main.choose_template",
            service_id=service_one["id"],
            template_folder_id=None,
            _external=True,
        ),
    )

    assert mock_move_to_template_folder.called is False
    mock_create_template_folder.assert_called_once_with(SERVICE_ONE_ID, name="new folder", parent_id=None)


def test_should_be_able_to_move_to_new_folder(
    client_request,
    service_one,
    mock_get_templates,
    mock_get_template_folders,
    mock_move_to_template_folder,
    mock_create_template_folder,
):
    new_folder_id = mock_create_template_folder.return_value
    FOLDER_TWO_ID = str(uuid.uuid4())
    mock_get_template_folders.return_value = [
        _folder("parent_folder", PARENT_FOLDER_ID, None),
        _folder("folder_two", FOLDER_TWO_ID, None),
    ]

    client_request.post(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
        template_folder_id=None,
        _data={
            "operation": "move-to-new-folder",
            "move_to_new_folder_name": "new folder",
            "templates_and_folders": [
                FOLDER_TWO_ID,
                TEMPLATE_ONE_ID,
            ],
        },
        _expected_status=302,
        _expected_redirect=url_for("main.choose_template", service_id=SERVICE_ONE_ID, _external=True),
    )

    mock_create_template_folder.assert_called_once_with(SERVICE_ONE_ID, name="new folder", parent_id=None)
    mock_move_to_template_folder.assert_called_once_with(
        service_id=SERVICE_ONE_ID,
        folder_id=new_folder_id,
        folder_ids={FOLDER_TWO_ID},
        template_ids={TEMPLATE_ONE_ID},
    )


def test_radio_button_with_no_value_shows_custom_error_message(
    client_request,
    service_one,
    mock_get_templates,
    mock_get_template_folders,
    mock_move_to_template_folder,
    mock_create_template_folder,
    mock_get_no_api_keys,
):
    page = client_request.post(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
        _data={"operation": "add-new-template"},
        _expected_status=200,
        _expected_redirect=None,
    )

    assert mock_move_to_template_folder.called is False
    assert mock_create_template_folder.called is False

    assert page.select_one("span.error-message").text.strip() == "Select the type of template you want to add"


@pytest.mark.parametrize(
    "data, error_msg",
    [
        # nothing selected when moving
        (
            {"operation": "move-to-new-folder", "templates_and_folders": [], "move_to_new_folder_name": "foo"},
            "Select at least one template or folder",
        ),
        (
            {"operation": "move-to-existing-folder", "templates_and_folders": [], "move_to": PARENT_FOLDER_ID},
            "Select at least one template or folder",
        ),
        # api error (eg moving folder to itself)
        (
            {
                "operation": "move-to-existing-folder",
                "templates_and_folders": [FOLDER_TWO_ID],
                "move_to": FOLDER_TWO_ID,
            },
            "Some api error msg",
        ),
    ],
)
def test_show_custom_error_message(
    client_request,
    service_one,
    mock_get_templates,
    mock_get_template_folders,
    mock_move_to_template_folder,
    mock_create_template_folder,
    mock_get_no_api_keys,
    data,
    error_msg,
):
    mock_get_template_folders.return_value = [
        _folder("folder_one", PARENT_FOLDER_ID, None),
        _folder("folder_two", FOLDER_TWO_ID, None),
    ]
    mock_move_to_template_folder.side_effect = HTTPError(message="Some api error msg")

    page = client_request.post(
        "main.choose_template",
        service_id=SERVICE_ONE_ID,
        _data=data,
        _expected_status=200,
        _expected_redirect=None,
    )

    assert page.select_one("div.banner-dangerous").text.strip() == error_msg


@pytest.mark.parametrize(
    "extra_args,expected_displayed_items, expected_items, expected_empty_message ",
    [
        (
            {},
            [
                ["folder_A", "folder_A", "1 template, 2 folders"],
                ["folder_E folder_F folder_G", "folder_E", "folder_F", "folder_G", "1 template"],
                ["broadcast_template_root", "broadcast_template_root", "Broadcast template"],
            ],
            [
                ["folder_A", "folder_A", "1 template, 2 folders"],
                ["folder_A folder_C", "folder_A", "folder_C", "Empty"],
                ["folder_A folder_D", "folder_A", "folder_D", "Empty"],
                ["folder_A broadcast_template_A", "folder_A", "broadcast_template_A", "Broadcast template"],
                ["folder_E folder_F folder_G", "folder_E", "folder_F", "folder_G", "1 template"],
                [
                    "folder_E folder_F folder_G broadcast_template_G",
                    "folder_E",
                    "folder_F",
                    "folder_G",
                    "broadcast_template_G",
                    "Broadcast template",
                ],
                ["broadcast_template_root", "broadcast_template_root", "Broadcast template"],
            ],
            None,
        ),
        (
            {"template_type": "broadcast"},
            [
                ["folder_A", "folder_A", "1 template"],
                ["folder_E folder_F folder_G", "folder_E", "folder_F", "folder_G", "1 template"],
                ["broadcast_template_root", "broadcast_template_root", "Broadcast template"],
            ],
            [
                ["folder_A", "folder_A", "1 template"],
                ["folder_A broadcast_template_A", "folder_A", "broadcast_template_A", "Broadcast template"],
                ["folder_E folder_F folder_G", "folder_E", "folder_F", "folder_G", "1 template"],
                [
                    "folder_E folder_F folder_G broadcast_template_G",
                    "folder_E",
                    "folder_F",
                    "folder_G",
                    "broadcast_template_G",
                    "Broadcast template",
                ],
                ["broadcast_template_root", "broadcast_template_root", "Broadcast template"],
            ],
            None,
        ),
        (
            {
                "template_type": "broadcast",
                "template_folder_id": FOLDER_C_ID,
            },
            [],
            [],
            "This folder is empty",
        ),
        (
            {"template_folder_id": CHILD_FOLDER_ID},
            [],
            [],
            "This folder is empty",
        ),
        (
            {"template_folder_id": CHILD_FOLDER_ID, "template_type": "broadcast"},
            [],
            [],
            "This folder is empty",
        ),
    ],
)
def test_should_filter_templates_folder_page_based_on_user_permissions(
    client_request,
    mock_get_template_folders,
    mock_get_no_api_keys,
    service_one,
    mocker,
    active_user_with_permissions,
    extra_args,
    expected_displayed_items,
    expected_items,
    expected_empty_message,
    mock_get_templates,
):
    mock_get_template_folders.return_value = [
        _folder("folder_A", FOLDER_TWO_ID, None, [active_user_with_permissions["id"]]),
        _folder("folder_B", FOLDER_B_ID, FOLDER_TWO_ID, []),
        _folder("folder_C", FOLDER_C_ID, FOLDER_TWO_ID, [active_user_with_permissions["id"]]),
        _folder("folder_D", None, FOLDER_TWO_ID, [active_user_with_permissions["id"]]),
        _folder("folder_E", PARENT_FOLDER_ID, users_with_permission=[]),
        _folder("folder_F", CHILD_FOLDER_ID, PARENT_FOLDER_ID, []),
        _folder("folder_G", GRANDCHILD_FOLDER_ID, CHILD_FOLDER_ID, [active_user_with_permissions["id"]]),
    ]
    mocker.patch(
        "app.template_api_client.get_templates",
        return_value={
            "data": [
                _template("broadcast", "broadcast_template_root"),
                _template("broadcast", "broadcast_template_A", parent=FOLDER_TWO_ID),
                _template("broadcast", "broadcast_template_B", parent=FOLDER_B_ID),
                _template("broadcast", "broadcast_template_G", parent=GRANDCHILD_FOLDER_ID),
                _template("broadcast", "broadcast_template_F", parent=CHILD_FOLDER_ID),
            ]
        },
    )

    page = client_request.get("main.choose_template", service_id=SERVICE_ONE_ID, _test_page_title=False, **extra_args)

    displayed_page_items = page.select(".template-list-item:not(.template-list-item-hidden-by-default)")
    assert [
        [i.strip() for i in e.text.split("\n") if i.strip()] for e in displayed_page_items
    ] == expected_displayed_items

    all_page_items = page.select(".template-list-item")
    assert [[i.strip() for i in e.text.split("\n") if i.strip()] for e in all_page_items] == expected_items

    if expected_empty_message:
        assert normalize_spaces(page.select_one(".template-list-empty").text) == (expected_empty_message)
    else:
        assert not page.select(".template-list-empty")
