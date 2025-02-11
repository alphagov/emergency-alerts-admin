from typing import TypedDict

from app.notify_client import AdminAPIClient


class PendingActionResponse(TypedDict):
    pending: list[dict]
    # UUID -> Object:
    services: dict[str, dict]
    organizations: dict[str, dict]
    users: dict[str, dict]


class AdminActionsClient(AdminAPIClient):
    def get_pending_admin_actions(self) -> PendingActionResponse:
        return self.get(url="/admin-action/pending")


admin_actions_api_client = AdminActionsClient()
