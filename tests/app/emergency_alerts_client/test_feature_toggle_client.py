from app.emergency_alerts_client.feature_toggle_api_client import FeatureToggleApiClient


def test_feature_toggle_client_calls_correct_api_endpoint(mocker):
    client = FeatureToggleApiClient()
    mock_get = mocker.patch.object(client, "get", return_value={})

    client.get_feature_toggle(feature_toggle_name="foo")
    mock_get.assert_called_once_with("/feature-toggle", params={"feature_toggle_name": "foo"})
