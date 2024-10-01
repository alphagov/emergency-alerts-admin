import pytest
from flask import url_for

from tests.conftest import SERVICE_ONE_ID, create_active_user_view_permissions


@pytest.mark.parametrize(
    "user",
    (create_active_user_view_permissions(),),
)
def test_redirect_from_old_dashboard(
    client_request,
    user,
    mocker,
):
    mocker.patch("app.user_api_client.get_user", return_value=user)
    expected_location = "/services/{}".format(SERVICE_ONE_ID)

    client_request.get_url(
        "/services/{}/dashboard".format(SERVICE_ONE_ID),
        _expected_redirect=expected_location,
    )

    assert expected_location == url_for("main.service_dashboard", service_id=SERVICE_ONE_ID)


@pytest.mark.parametrize(
    "user",
    (create_active_user_view_permissions(),),
)
def test_redirect_from_service_dashboard_to_broadcast_dashboard(
    client_request,
    user,
    mocker,
):
    mocker.patch("app.user_api_client.get_user", return_value=user)
    expected_redirect = "/services/{}/current-alerts".format(SERVICE_ONE_ID)

    client_request.get_url(
        "/services/{}".format(SERVICE_ONE_ID),
        _expected_redirect=expected_redirect,
    )

    assert expected_redirect == url_for("main.broadcast_dashboard", service_id=SERVICE_ONE_ID)
