from app.emergency_alerts_client import EmergencyAlertsAdminAPIClient


class FeatureToggleApiClient(EmergencyAlertsAdminAPIClient):
    def get_feature_toggle(self, feature_toggle_name):
        return self.get("/feature-toggle", params={"feature_toggle_name": feature_toggle_name})


feature_toggle_api_client = FeatureToggleApiClient()
