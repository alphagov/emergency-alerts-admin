from app.notify_client import AdminAPIClient, _attach_current_user


class ApiKeyApiClient(AdminAPIClient):
    def get_api_keys(self, service_id):
        return self.get(url="/service/{}/api-keys".format(service_id))

    def create_api_key(self, service_id, key_name, key_type):
        data = {"name": key_name, "key_type": key_type}
        data = _attach_current_user(data)
        key = self.post(url="/service/{}/api-key".format(service_id), data=data)
        return key["data"]

    def revoke_api_key(self, service_id, key_id):
        data = _attach_current_user({})
        return self.post(url="/service/{0}/api-key/revoke/{1}".format(service_id, key_id), data=data)


api_key_api_client = ApiKeyApiClient()
