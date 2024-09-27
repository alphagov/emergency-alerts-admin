import json

import pytest


@pytest.mark.parametrize(
    "submitted_content, expected_content_sent",
    [
        (
            {
                "type": "some-violation",
                "url": "https://gov.uk",
                "user_agent": "some-browser",
                "body": '{"key1":"value1","key2":"value2"}',
            },
            {
                "type": "some-violation",
                "url": "https://gov.uk",
                "user_agent": "some-browser",
                "body": '{"key1":"value1","key2":"value2"}',
            },
        ),
        (
            {
                "type": "some-violation",
                "url": "https://gov.uk",
                "user_agent": "some-browser",
                "body": '{"key1":"value1","key2":"value2"}',
                "another_key": "another-value",
            },
            {
                "type": "some-violation",
                "url": "https://gov.uk",
                "user_agent": "some-browser",
                "body": '{"key1":"value1","key2":"value2"}',
            },
        ),
    ],
)
def test_endpoint_is_called_with_filtered_content(client_request, mocker, submitted_content, expected_content_sent):
    client_request.logout()  # Should work unauthenticated

    mock_send_report_to_slack = mocker.patch(
        "app.main.views.reports.reports_api_client.post_report",
        autospec=True,
    )

    client_request.post(
        "main.reports",
        _data=json.dumps(submitted_content),
        _content_type="application/reports+json",
        _expected_status=200,
    )

    sorted_expected_content_sent = dict(sorted(expected_content_sent.items()))
    mock_send_report_to_slack.assert_called_once_with(data=json.dumps(sorted_expected_content_sent))


def test_endpoint_requires_report_keys(client_request):
    invalid_request_content = {"type": "some-violation", "url": "https://gov.uk", "user_agent": "some-browser"}
    response = client_request.post(
        "main.reports",
        _data=json.dumps(invalid_request_content),
        _content_type="application/reports+json",
        _expected_status=400,
    )

    assert (
        "The request did not conform to the schema for reports. "
        "The request must include a 'type', the 'url', the 'user_agent', and the report 'body'."
    ) in response.text


def test_endpoint_only_allows_reports_type(client_request, mocker):
    request = {}

    client_request.post(
        "main.reports", _data=json.dumps(request), _content_type="application/json", _expected_status=400
    )
