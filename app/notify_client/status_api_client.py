from app.notify_client import AdminAPIClient


class StatusApiClient(AdminAPIClient):
    def get_status(self, *params):
        return self.get(url="/_api_status", *params)

    def get_count_of_live_services_and_organisations(self):
        return self.get(url="/_api_status/live-service-and-organisation-counts")


status_api_client = StatusApiClient()
