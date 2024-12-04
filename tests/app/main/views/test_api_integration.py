from unittest.mock import call

import pytest
from flask import url_for

from tests import validate_route_permission
from tests.conftest import SERVICE_ONE_ID, normalize_spaces


def test_should_show_empty_api_keys_page(
    client_request,
    api_user_active,
    mock_login,
    mock_get_no_api_keys,
    mock_get_service,
    mock_has_permissions,
):
    client_request.login(api_user_active)
    page = client_request.get("main.api_keys", service_id=SERVICE_ONE_ID)

    assert "You have not created any API keys yet" in page.text
    assert "Create an API key" in page.text
    mock_get_no_api_keys.assert_called_once_with(SERVICE_ONE_ID)


def test_should_show_api_keys_page(
    client_request,
    mock_get_api_keys,
    fake_uuid,
):
    page = client_request.get("main.api_keys", service_id=SERVICE_ONE_ID)
    rows = [normalize_spaces(row.text) for row in page.select("main tr")]
    revoke_link = page.select_one("main tr a.govuk-link.govuk-link--destructive")

    assert rows[0] == "API keys Action"
    assert rows[1] == "another key name Revoked 1 January at 1:00am"
    assert rows[2] == "some key name Revoke some key name"

    assert normalize_spaces(revoke_link.text) == "Revoke some key name"
    assert revoke_link["href"] == url_for(
        "main.revoke_api_key",
        service_id=SERVICE_ONE_ID,
        key_id=fake_uuid,
    )

    mock_get_api_keys.assert_called_once_with(SERVICE_ONE_ID)


@pytest.mark.parametrize(
    "restricted, expected_options",
    [
        (
            True,
            [
                ("Live – sends to anyone", "Not available because your service is in training mode"),
                "Team and guest list – limits who you can send to",
                "Test – pretends to send messages",
            ],
        ),
        (
            False,
            [
                "Live – sends to anyone",
                "Team and guest list – limits who you can send to",
                "Test – pretends to send messages",
            ],
        ),
        (
            False,
            [
                "Live – sends to anyone",
                "Team and guest list – limits who you can send to",
                "Test – pretends to send messages",
            ],
        ),
    ],
)
def test_should_show_create_api_key_page(
    client_request,
    mocker,
    api_user_active,
    mock_get_api_keys,
    restricted,
    expected_options,
    service_one,
):
    service_one["restricted"] = restricted
    mocker.patch("app.service_api_client.get_service", return_value={"data": service_one})
    page = client_request.get("main.create_api_key", service_id=SERVICE_ONE_ID)

    for index, option in enumerate(expected_options):
        item = page.select(".govuk-radios__item")[index]
        if type(option) is tuple:
            assert normalize_spaces(item.select_one(".govuk-label").text) == option[0]
            assert normalize_spaces(item.select_one(".govuk-hint").text) == option[1]
        else:
            assert normalize_spaces(item.select_one(".govuk-label").text) == option


def test_should_create_api_key_with_type_normal(
    client_request,
    api_user_active,
    mock_login,
    mock_get_api_keys,
    mock_get_live_service,
    mock_has_permissions,
    fake_uuid,
    mocker,
):
    post = mocker.patch("app.notify_client.api_key_api_client.ApiKeyApiClient.post", return_value={"data": fake_uuid})

    page = client_request.post(
        "main.create_api_key",
        service_id=SERVICE_ONE_ID,
        _data={"key_name": "Some default key name 1/2", "key_type": "normal"},
        _expected_status=200,
    )

    assert page.select_one("span.copy-to-clipboard__value").text == (
        # The text should be exactly this, with no leading or trailing whitespace
        f"some_default_key_name_12-{SERVICE_ONE_ID}-{fake_uuid}"
    )

    post.assert_called_once_with(
        url="/service/{}/api-key".format(SERVICE_ONE_ID),
        data={"name": "Some default key name 1/2", "key_type": "normal", "created_by": api_user_active["id"]},
    )


def test_cant_create_normal_api_key_in_trial_mode(
    client_request,
    api_user_active,
    mock_login,
    mock_get_api_keys,
    mock_get_service,
    mock_has_permissions,
    fake_uuid,
    mocker,
):
    mock_post = mocker.patch("app.notify_client.api_key_api_client.ApiKeyApiClient.post")

    client_request.post(
        "main.create_api_key",
        service_id=SERVICE_ONE_ID,
        _data={"key_name": "some default key name", "key_type": "normal"},
        _expected_status=400,
    )
    assert mock_post.called is False


def test_should_show_confirm_revoke_api_key(
    client_request,
    mock_get_api_keys,
    fake_uuid,
):
    page = client_request.get(
        "main.revoke_api_key",
        service_id=SERVICE_ONE_ID,
        key_id=fake_uuid,
        _test_page_title=False,
    )
    assert normalize_spaces(page.select(".banner-dangerous")[0].text) == (
        "Are you sure you want to revoke ‘some key name’? "
        "You will not be able to use this API key to connect to GOV.UK Notify. "
        "Yes, revoke this API key"
    )
    assert mock_get_api_keys.call_args_list == [
        call("596364a0-858e-42c8-9062-a8fe822260eb"),
    ]


def test_should_404_for_api_key_that_doesnt_exist(
    client_request,
    mock_get_api_keys,
):
    client_request.get(
        "main.revoke_api_key",
        service_id=SERVICE_ONE_ID,
        key_id="key-doesn’t-exist",
        _expected_status=404,
    )


def test_should_redirect_after_revoking_api_key(
    client_request,
    api_user_active,
    mock_login,
    mock_revoke_api_key,
    mock_get_api_keys,
    mock_get_service,
    mock_has_permissions,
    fake_uuid,
):
    client_request.post(
        "main.revoke_api_key",
        service_id=SERVICE_ONE_ID,
        key_id=fake_uuid,
        _expected_status=302,
        _expected_redirect=url_for(
            ".api_keys",
            service_id=SERVICE_ONE_ID,
        ),
    )
    mock_revoke_api_key.assert_called_once_with(service_id=SERVICE_ONE_ID, key_id=fake_uuid)
    mock_get_api_keys.assert_called_once_with(
        SERVICE_ONE_ID,
    )


@pytest.mark.parametrize("route", ["main.api_keys", "main.create_api_key", "main.revoke_api_key"])
def test_route_permissions(
    mocker,
    notify_admin,
    fake_uuid,
    api_user_active,
    service_one,
    mock_get_api_keys,
    route,
):
    with notify_admin.test_request_context():
        validate_route_permission(
            mocker,
            notify_admin,
            "GET",
            200,
            url_for(route, service_id=service_one["id"], key_id=fake_uuid),
            ["manage_api_keys"],
            api_user_active,
            service_one,
        )


@pytest.mark.parametrize("route", ["main.api_keys", "main.create_api_key", "main.revoke_api_key"])
def test_route_invalid_permissions(
    mocker,
    notify_admin,
    fake_uuid,
    api_user_active,
    service_one,
    mock_get_api_keys,
    route,
):
    with notify_admin.test_request_context():
        validate_route_permission(
            mocker,
            notify_admin,
            "GET",
            403,
            url_for(route, service_id=service_one["id"], key_id=fake_uuid),
            ["view_activity"],
            api_user_active,
            service_one,
        )
