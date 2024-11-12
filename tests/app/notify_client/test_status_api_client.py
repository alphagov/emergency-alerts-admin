from app.notify_client.status_api_client import StatusApiClient


def test_get_count_of_live_services_and_organisations(mocker):
    client = StatusApiClient()
    mock = mocker.patch.object(client, "get", return_value={})

    client.get_count_of_live_services_and_organisations()

    mock.assert_called_once_with(url="/_api_status/live-service-and-organisation-counts")
