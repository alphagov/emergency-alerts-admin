from app.notify_client import NotifyAdminAPIClient


class FeatureToggleApiClient(NotifyAdminAPIClient):
    def find_feature_toggle_by_name(self, feature_toggle_name):
        return self.get("/feature-toggle", params={"feature_toggle_name": feature_toggle_name})


feature_toggle_api_client = FeatureToggleApiClient()
