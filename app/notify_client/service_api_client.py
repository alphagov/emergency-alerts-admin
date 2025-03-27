from datetime import datetime

from app.notify_client import AdminAPIClient, _attach_current_user


class ServiceAPIClient(AdminAPIClient):
    def create_service(
        self,
        service_name,
        organisation_type,
        restricted,
        user_id,
    ):
        """
        Create a service and return the json.
        """
        data = {
            "name": service_name,
            "organisation_type": organisation_type,
            "active": True,
            "restricted": restricted,
            "user_id": user_id,
        }
        data = _attach_current_user(data)
        return self.post("/service", data)["data"]["id"]

    def get_service(self, service_id):
        """
        Retrieve a service.
        """
        return self.get("/service/{0}".format(service_id))

    def get_service_statistics(self, service_id, limit_days=None):
        return self.get("/service/{0}/statistics".format(service_id), params={"limit_days": limit_days})["data"]

    def get_services(self, params_dict=None):
        """
        Retrieve a list of services.
        """
        return self.get("/service", params=params_dict)

    def find_services_by_name(self, service_name):
        return self.get("/service/find-services-by-name", params={"service_name": service_name})

    def get_live_services_data(self, params_dict=None):
        """
        Retrieve a list of live services data with contact names and notification counts.
        """
        return self.get("/service/live-services-data", params=params_dict)

    def get_active_services(self, params_dict=None):
        """
        Retrieve a list of active services.
        """
        params_dict["only_active"] = True
        return self.get_services(params_dict)

    def update_service(self, service_id, **kwargs):
        """
        Update a service.
        """
        data = _attach_current_user(kwargs)
        disallowed_attributes = set(data.keys()) - {
            "active",
            "created_by",
            "name",
            "notes",
            "organisation_type",
            "permissions",
            "restricted",
        }
        if disallowed_attributes:
            raise TypeError("Not allowed to update service attributes: {}".format(", ".join(disallowed_attributes)))

        endpoint = "/service/{0}".format(service_id)
        return self.post(endpoint, data)

    def update_status(self, service_id, live):
        return self.update_service(
            service_id,
            restricted=(not live),
            go_live_at=str(datetime.utcnow()) if live else None,
        )

    # This method is not cached because it calls through to one which is
    def update_service_with_properties(self, service_id, properties):
        return self.update_service(service_id, **properties)

    def archive_service(self, service_id):
        return self.post("/service/{}/archive".format(service_id), data=None)

    def remove_user_from_service(self, service_id, user_id):
        """
        Remove a user from a service
        """
        endpoint = "/service/{service_id}/users/{user_id}".format(service_id=service_id, user_id=user_id)
        data = _attach_current_user({})
        return self.delete(endpoint, data)

    def create_service_template(self, name, type_, content, service_id, parent_folder_id=None):
        """
        Create a service template.
        """
        data = {
            "name": name,
            "template_type": type_,
            "content": content,
            "service": service_id,
        }
        if parent_folder_id:
            data.update({"parent_folder_id": parent_folder_id})
        data = _attach_current_user(data)
        endpoint = "/service/{0}/template".format(service_id)
        return self.post(endpoint, data)

    def update_service_template(self, id_, name, type_, content, service_id):
        """
        Update a service template.
        """
        data = {"id": id_, "name": name, "template_type": type_, "content": content, "service": service_id}
        data = _attach_current_user(data)
        endpoint = "/service/{0}/template/{1}".format(service_id, id_)
        return self.post(endpoint, data)

    def redact_service_template(self, service_id, id_):
        return self.post(
            "/service/{}/template/{}".format(service_id, id_),
            _attach_current_user({"redact_personalisation": True}),
        )

    def update_service_template_sender(self, service_id, template_id, reply_to):
        data = {
            "reply_to": reply_to,
        }
        data = _attach_current_user(data)
        return self.post("/service/{0}/template/{1}".format(service_id, template_id), data)

    def get_service_template(self, service_id, template_id, version=None):
        """
        Retrieve a service template.
        """
        endpoint = "/service/{service_id}/template/{template_id}".format(service_id=service_id, template_id=template_id)
        if version:
            endpoint = "{base}/version/{version}".format(base=endpoint, version=version)
        return self.get(endpoint)

    def get_service_template_versions(self, service_id, template_id):
        """
        Retrieve a list of versions for a template
        """
        endpoint = "/service/{service_id}/template/{template_id}/versions".format(
            service_id=service_id, template_id=template_id
        )
        return self.get(endpoint)

    def get_precompiled_template(self, service_id):
        """
        Returns the precompiled template for a service, creating it if it doesn't already exist
        """
        return self.get("/service/{}/template/precompiled".format(service_id))

    def get_service_templates(self, service_id):
        """
        Retrieve all templates for service.
        """
        endpoint = "/service/{service_id}/template?detailed=False".format(service_id=service_id)
        return self.get(endpoint)

    # This doesn’t need caching because it calls through to a method which is cached
    def count_service_templates(self, service_id, template_type=None):
        return len(
            [
                template
                for template in self.get_service_templates(service_id)["data"]
                if (not template_type or template["template_type"] == template_type)
            ]
        )

    def delete_service_template(self, service_id, template_id):
        """
        Set a service template's archived flag to True
        """
        endpoint = "/service/{0}/template/{1}".format(service_id, template_id)
        data = {"archived": True}
        data = _attach_current_user(data)
        return self.post(endpoint, data=data)

    # Temp access of service history data. Includes service and api key history
    def get_service_history(self, service_id):
        return self.get("/service/{0}/history".format(service_id))["data"]

    def get_service_service_history(self, service_id):
        return self.get_service_history(service_id)["service_history"]

    def get_service_api_key_history(self, service_id):
        return self.get_service_history(service_id)["api_key_history"]

    def get_monthly_notification_stats(self, service_id, year):
        return self.get(url="/service/{}/notifications/monthly?year={}".format(service_id, year))

    def get_guest_list(self, service_id):
        return self.get(url="/service/{}/guest-list".format(service_id))

    def update_guest_list(self, service_id, data):
        return self.put(url="/service/{}/guest-list".format(service_id), data=data)

    def create_service_inbound_api(self, service_id, url, bearer_token, user_id):
        data = {"url": url, "bearer_token": bearer_token, "updated_by_id": user_id}
        return self.post("/service/{}/inbound-api".format(service_id), data)

    def update_service_inbound_api(self, service_id, url, bearer_token, user_id, inbound_api_id):
        data = {"url": url, "updated_by_id": user_id}
        if bearer_token:
            data["bearer_token"] = bearer_token
        return self.post("/service/{}/inbound-api/{}".format(service_id, inbound_api_id), data)

    def get_service_inbound_api(self, service_id, inbound_sms_api_id):
        return self.get("/service/{}/inbound-api/{}".format(service_id, inbound_sms_api_id))["data"]

    def delete_service_inbound_api(self, service_id, callback_api_id):
        return self.delete("/service/{}/inbound-api/{}".format(service_id, callback_api_id))

    def get_reply_to_email_addresses(self, service_id):
        return self.get("/service/{}/email-reply-to".format(service_id))

    def get_reply_to_email_address(self, service_id, reply_to_email_id):
        return self.get("/service/{}/email-reply-to/{}".format(service_id, reply_to_email_id))

    def verify_reply_to_email_address(self, service_id, email_address):
        return self.post("/service/{}/email-reply-to/verify".format(service_id), data={"email": email_address})

    def add_reply_to_email_address(self, service_id, email_address, is_default=False):
        return self.post(
            "/service/{}/email-reply-to".format(service_id),
            data={"email_address": email_address, "is_default": is_default},
        )

    def update_reply_to_email_address(self, service_id, reply_to_email_id, email_address, is_default=False):
        return self.post(
            "/service/{}/email-reply-to/{}".format(
                service_id,
                reply_to_email_id,
            ),
            data={"email_address": email_address, "is_default": is_default},
        )

    def get_service_callback_api(self, service_id, callback_api_id):
        return self.get("/service/{}/delivery-receipt-api/{}".format(service_id, callback_api_id))["data"]

    def update_service_callback_api(self, service_id, url, bearer_token, user_id, callback_api_id):
        data = {"url": url, "updated_by_id": user_id}
        if bearer_token:
            data["bearer_token"] = bearer_token
        return self.post("/service/{}/delivery-receipt-api/{}".format(service_id, callback_api_id), data)

    def delete_service_callback_api(self, service_id, callback_api_id):
        return self.delete("/service/{}/delivery-receipt-api/{}".format(service_id, callback_api_id))

    def create_service_callback_api(self, service_id, url, bearer_token, user_id):
        data = {"url": url, "bearer_token": bearer_token, "updated_by_id": user_id}
        return self.post("/service/{}/delivery-receipt-api".format(service_id), data)

    def create_service_data_retention(self, service_id, notification_type, days_of_retention):
        data = {"notification_type": notification_type, "days_of_retention": days_of_retention}

        return self.post("/service/{}/data-retention".format(service_id), data)

    def update_service_data_retention(self, service_id, data_retention_id, days_of_retention):
        data = {"days_of_retention": days_of_retention}
        return self.post("/service/{}/data-retention/{}".format(service_id, data_retention_id), data)

    def get_service_data_retention(self, service_id):
        return self.get("/service/{}/data-retention".format(service_id))

    def set_service_broadcast_settings(self, service_id, service_mode, broadcast_channel, provider_restriction):
        """
        service_mode is one of "training" or "live"
        broadcast channel is one of "operator", "test", "severe", "government"
        provider_restriction is one of "all", "three", "o2", "vodafone", "ee"

        NEW:
        provider_restriction is either "all" or a list of between 1 and 3 providers
        e.g. ["o2", "vodafone", "ee"], ["o2"], ["vodafone", "three"]

        """
        data = {
            "service_mode": service_mode,
            "broadcast_channel": broadcast_channel,
            "provider_restriction": provider_restriction,
        }

        return self.post("/service/{}/set-as-broadcast-service".format(service_id), data)

    @classmethod
    def parse_edit_service_http_error(cls, http_error):
        """Inspect the HTTPError from a create_service/update_service call and return a human-friendly error message"""
        if http_error.message.get("name"):
            return "This service name is already in use"

        return None


service_api_client = ServiceAPIClient()
