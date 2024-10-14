import json

from app.notify_client import NotifyAdminAPIClient


class SecurityReportApiClient(NotifyAdminAPIClient):
    def post_report(self, data):
        return self.post("/reports", json.loads(data))


reports_api_client = SecurityReportApiClient()
