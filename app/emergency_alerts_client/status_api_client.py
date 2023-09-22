from app.emergency_alerts_client import EmergencyAlertsAdminAPIClient, cache


class StatusApiClient(EmergencyAlertsAdminAPIClient):
    def get_status(self, *params):
        return self.get(url="/_api_status", *params)

    @cache.set("live-service-and-organisation-counts", ttl_in_seconds=3600)
    def get_count_of_live_services_and_organisations(self):
        return self.get(url="/_api_status/live-service-and-organisation-counts")


status_api_client = StatusApiClient()
