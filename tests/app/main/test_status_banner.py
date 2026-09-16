from unittest.mock import patch

from app.utils.labels import LABELS


@patch("app.feature_toggle_api_client.get_feature_toggle")
def test_service_not_live_banner_displayed(
    mock_get_feature_toggle,
    client_request,
):
    mock_get_feature_toggle.return_value = {
        "is_enabled": True,
        "display_html": "Service not production",
    }

    client_request.logout()
    page = client_request.get("main.sign_in")

    assert "Service not production" in page.text


@patch("app.feature_toggle_api_client.get_feature_toggle")
def test_service_not_live_banner_not_displayed(
    mock_get_feature_toggle,
    client_request,
):
    mock_get_feature_toggle.return_value = {
        "is_enabled": False,
        "display_html": "Service not production",
    }

    client_request.logout()
    page = client_request.get("main.sign_in")

    assert "Service not production" not in page.text


@patch("app.feature_toggle_api_client.get_feature_toggle")
def test_training_banner_not_displayed(
    mock_get_feature_toggle,
    client_request,
    mocker,
):
    mock_get_feature_toggle.return_value = {
        "is_enabled": False,
        "display_html": "Service not production",
    }

    mocker.patch(
        "app.current_service",
        mocker.Mock(trial_mode=False),
    )

    page = client_request.get(".support")

    assert "Service not production" not in page.text
    assert LABELS.service.training_service_status not in page.text


@patch("app.feature_toggle_api_client.get_feature_toggle")
def test_training_banner_displayed(
    mock_get_feature_toggle,
    client_request,
    mocker,
):
    mock_get_feature_toggle.return_value = {
        "is_enabled": False,
        "display_html": "Service not production",
    }

    mocker.patch(
        "app.current_service",
        mocker.Mock(trial_mode=True),
    )

    page = client_request.get(".support")

    assert "Service not production" not in page.text
    assert LABELS.service.training_service_status in page.text
