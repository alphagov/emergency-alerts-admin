from typing import TypedDict

from flask_login import current_user

from app.notify_client import AdminAPIClient


class PendingActionResponse(TypedDict):
    pending: list[dict]
    # UUID -> Object:
    services: dict[str, dict]
    users: dict[str, dict]


class AdminActionsApiClient(AdminAPIClient):
    def create_admin_action(self, action_obj):
        """Caution: You may wish to use utils/admin_action.create_or_replace_admin_action"""
        return self.post(url="/admin-action", data=action_obj)

    def get_pending_admin_actions(self) -> PendingActionResponse:
        return self.get(url="/admin-action/pending")

    def get_admin_action_by_id(self, action_id: str):
        return self.get(url="/admin-action/{}".format(action_id))

    def review_admin_action(self, action_id: str, status: str):
        data = {
            "reviewed_by": current_user.id,
            "status": status,
        }
        return self.post(url="/admin-action/{}/review".format(action_id), data=data)


admin_actions_api_client = AdminActionsApiClient()
