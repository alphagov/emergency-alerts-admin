from app.emergency_alerts_client import EmergencyAlertsAdminAPIClient


class UploadApiClient(EmergencyAlertsAdminAPIClient):
    def get_letters_by_service_and_print_day(
        self,
        service_id,
        *,
        letter_print_day,
        page=1,
    ):
        return self.get(url=f"/service/{service_id}/upload/uploaded-letters/{letter_print_day}?page={page}")


upload_api_client = UploadApiClient()
