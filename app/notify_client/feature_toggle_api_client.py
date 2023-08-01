from app.notify_client import NotifyAdminAPIClient


class FeatureToggleApiClient(NotifyAdminAPIClient):
    def get_feature_toggle(self, feature_toggle_name):
        return self.get("/feature-toggle", params={"feature_toggle_name": feature_toggle_name})


feature_toggle_api_client = FeatureToggleApiClient()
