from notifications_python_client.errors import HTTPError

from app.notify_client import AdminAPIClient, _attach_current_user


class BroadcastMessageAPIClient(AdminAPIClient):
    def create_broadcast_message(
        self,
        *,
        service_id,
        template_id,
        content,
        reference,
    ):
        data = {
            "service_id": service_id,
            "personalisation": {},
        }
        if template_id:
            data.update(template_id=template_id)
        if content:
            data.update(content=content)
        if reference:
            data.update(reference=reference)

        data = _attach_current_user(data)

        broadcast_message = self.post(
            f"/service/{service_id}/broadcast-message",
            data=data,
        )

        return broadcast_message

    def get_broadcast_messages(self, service_id):
        return self.get(f"/service/{service_id}/broadcast-message/messages")["broadcast_messages"]

    def get_broadcast_message(self, *, service_id, broadcast_message_id):
        return self.get(f"/service/{service_id}/broadcast-message/message={broadcast_message_id}")

    def update_broadcast_message(self, *, service_id, broadcast_message_id, data):
        self.post(
            f"/service/{service_id}/broadcast-message/{broadcast_message_id}",
            data=_attach_current_user(data),
        )

    def update_broadcast_message_status(self, status, *, service_id, broadcast_message_id):
        data = _attach_current_user(
            {
                "status": status,
            }
        )
        self.post(
            f"/service/{service_id}/broadcast-message/{broadcast_message_id}/status",
            data=data,
        )

    def update_broadcast_message_status_with_reason(
        self, status, *, service_id, broadcast_message_id, rejection_reason
    ):
        data = _attach_current_user(
            {
                "status": status,
                **({"rejection_reason": rejection_reason} if rejection_reason else {}),
            }
        )
        try:
            self.post(
                f"/service/{service_id}/broadcast-message/{broadcast_message_id}/status-with-reason",
                data=data,
            )
        except HTTPError as e:
            if e.status_code == 400:
                raise e

    def return_broadcast_message_for_edit_with_reason(self, *, service_id, broadcast_message_id, edit_reason):
        data = _attach_current_user(
            {
                "edit_reason": edit_reason,
            }
        )
        try:
            self.post(
                f"/service/{service_id}/broadcast-message/{broadcast_message_id}/return-for-edit",
                data=data,
            )
        except HTTPError as e:
            if e.status_code == 400:
                raise e

    def get_broadcast_message_versions(self, service_id, broadcast_message_id):
        """
        Retrieve a list of versions for a broadcast message
        """
        return self.get(f"/service/{service_id}/broadcast-message-history/{broadcast_message_id}/versions")

    def get_broadcast_message_version(self, service_id, broadcast_message_id, version):
        """
        Retrieve a specific version of a broadcast message
        """
        return self.get(f"/service/{service_id}/broadcast-message-history/{broadcast_message_id}/version/{version}")

    def check_broadcast_status_transition_allowed(self, new_status, *, service_id, broadcast_message_id):
        data = _attach_current_user(
            {
                "status": new_status,
            }
        )
        return self.post(f"/service/{service_id}/broadcast-message/{broadcast_message_id}/check-status", data=data)

    def get_latest_broadcast_message_returned_for_edit_reason(self, service_id, broadcast_message_id):
        """
        Retrieve a list of ...
        """
        return self.get(
            f"/service/{service_id}/broadcast-message-edit-reasons/{broadcast_message_id}/latest-edit-reason"
        ).get("edit_reason")


broadcast_message_api_client = BroadcastMessageAPIClient()
