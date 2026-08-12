import pytest

from app.notify_client.broadcast_message_api_client import BroadcastMessageAPIClient


def test_create_broadcast_message(mocker):
    client = BroadcastMessageAPIClient()
    mocker.patch("app.notify_client.current_user", id="1")
    mock_post = mocker.patch("app.notify_client.broadcast_message_api_client.BroadcastMessageAPIClient.post")
    client.create_broadcast_message(
        service_id="12345",
        template_id="67890",
        content=None,
        reference=None,
    )
    mock_post.assert_called_once_with(
        "/service/12345/broadcast-message",
        data={
            "service_id": "12345",
            "template_id": "67890",
            "personalisation": {},
            "created_by": "1",
        },
    )


def test_get_broadcast_messages(mocker):
    client = BroadcastMessageAPIClient()
    mock_get = mocker.patch("app.notify_client.broadcast_message_api_client.BroadcastMessageAPIClient.get")
    client.get_broadcast_messages("12345")
    mock_get.assert_called_once_with(
        "/service/12345/broadcast-message/messages",
    )


def test_get_broadcast_message(mocker):
    client = BroadcastMessageAPIClient()
    mocker.patch("app.notify_client.current_user", id="1")
    mock_get = mocker.patch(
        "app.notify_client.broadcast_message_api_client.BroadcastMessageAPIClient.get",
        return_value={"abc": "def"},
    )
    client.get_broadcast_message(service_id="12345", broadcast_message_id="67890")
    mock_get.assert_called_once_with(
        "/service/12345/broadcast-message/message=67890",
    )


def test_update_broadcast_message(mocker):
    client = BroadcastMessageAPIClient()
    mocker.patch("app.notify_client.current_user", id="1")
    mock_post = mocker.patch("app.notify_client.broadcast_message_api_client.BroadcastMessageAPIClient.post")
    client.update_broadcast_message(
        service_id="12345",
        broadcast_message_id="67890",
        data={"abc": "def"},
    )
    mock_post.assert_called_once_with(
        "/service/12345/broadcast-message/67890",
        data={"abc": "def", "created_by": "1"},
    )


def test_update_broadcast_message_status(mocker):
    client = BroadcastMessageAPIClient()
    mocker.patch("app.notify_client.current_user", id="1")
    mock_post = mocker.patch("app.notify_client.broadcast_message_api_client.BroadcastMessageAPIClient.post")
    client.update_broadcast_message_status(
        "cancelled",
        service_id="12345",
        broadcast_message_id="67890",
    )
    mock_post.assert_called_once_with(
        "/service/12345/broadcast-message/67890/status",
        data={"created_by": "1", "status": "cancelled"},
    )


def test_reject_broadcast_message_status(mocker):
    client = BroadcastMessageAPIClient()
    mocker.patch("app.notify_client.current_user", id="1")
    mock_post = mocker.patch("app.notify_client.broadcast_message_api_client.BroadcastMessageAPIClient.post")
    client.update_broadcast_message_status(
        "cancelled",
        service_id="12345",
        broadcast_message_id="67890",
    )
    mock_post.assert_called_once_with(
        "/service/12345/broadcast-message/67890/status",
        data={"created_by": "1", "status": "cancelled"},
    )


def test_reject_broadcast_message_status_with_rejection_reason(mocker):
    client = BroadcastMessageAPIClient()
    mocker.patch("app.notify_client.current_user", id="1")
    mock_post = mocker.patch("app.notify_client.broadcast_message_api_client.BroadcastMessageAPIClient.post")
    client.update_broadcast_message_status_with_reason(
        "cancelled",
        service_id="12345",
        broadcast_message_id="67890",
        rejection_reason="This is a test rejection reason.",
    )
    mock_post.assert_called_once_with(
        "/service/12345/broadcast-message/67890/status-with-reason",
        data={"created_by": "1", "status": "cancelled", "rejection_reason": "This is a test rejection reason."},
    )


@pytest.mark.parametrize(
    "wkt_value",
    [
        # No WKT → should not appear in payload
        None,
        # Simple polygon
        "POLYGON ((-0.1400 51.5150,-0.1400 51.4950,-0.1000 51.4950,-0.1000 51.5150,-0.1400 51.5150))",
        # Multipolygon wrapper
        "MULTIPOLYGON (((-0.1400 51.5150,-0.1400 51.4950,-0.1000 51.4950,-0.1000 51.5150,-0.1400 51.5150)))",
    ],
)
def test_send_alert_summary_email(mocker, wkt_value):
    client = BroadcastMessageAPIClient()
    mocker.patch("app.notify_client.current_user", id="1")
    mock_post = mocker.patch("app.notify_client.broadcast_message_api_client.BroadcastMessageAPIClient.post")

    geojson = {"type": "Point", "coordinates": [0, 0]}
    cap_xml = "<cap/>"
    ibag_xml = "<ibag/>"

    client.send_alert_summary_email(
        service_id="12345",
        broadcast_message_id="67890",
        geojson=geojson,
        cap_xml=cap_xml,
        ibag_xml=ibag_xml,
        alert_summary="summary",
        phone_estimate="less than 1 million",
        duration="30 minutes",
        wkt=wkt_value,
    )

    mock_post.assert_called_once_with(
        "/service/12345/broadcast-message/67890/alert-summary-email",
        data={
            "geojson": geojson,
            "cap_xml": cap_xml,
            "ibag_xml": ibag_xml,
            "alert_summary": "summary",
            "phone_estimate": "less than 1 million",
            "duration": "30 minutes",
            **({"wkt": wkt_value} if wkt_value else {}),
            "created_by": "1",
        },
    )
