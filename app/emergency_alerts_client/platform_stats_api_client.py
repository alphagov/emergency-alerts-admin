from app.emergency_alerts_client import EmergencyAlertsAdminAPIClient


class PlatformStatsAPIClient(EmergencyAlertsAdminAPIClient):
    def get_aggregate_platform_stats(self, params_dict=None):
        return self.get("/platform-stats", params=params_dict)


platform_stats_api_client = PlatformStatsAPIClient()
