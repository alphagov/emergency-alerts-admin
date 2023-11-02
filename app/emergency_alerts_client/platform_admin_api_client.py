from app.emergency_alerts_client import EmergencyAlertsAdminAPIClient


class AdminApiClient(EmergencyAlertsAdminAPIClient):
    """API client for looking up arbitrary API objects based on incomplete information, eg just a UUID"""

    def find_by_uuid(self, uuid_):
        return self.post(url="/platform-admin/find-by-uuid", data={"uuid": uuid_})


admin_api_client = AdminApiClient()
