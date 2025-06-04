from app.notify_client import AdminAPIClient, _attach_current_user


class TemplateAPIClient(AdminAPIClient):
    def create_service_template(self, name, type_, content, service_id, parent_folder_id=None, areas=None):
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
            data["parent_folder_id"] = parent_folder_id
        if areas:
            data["areas"] = areas
        data = _attach_current_user(data)
        endpoint = "/service/{0}/template".format(service_id)
        return self.post(endpoint, data)

    def update_service_template(self, id_, name, type_, content, service_id, areas=None):
        """
        Update a service template.
        """
        data = {
            "id": id_,
            "name": name,
            "template_type": type_,
            "content": content,
            "service": service_id,
            "areas": areas or [],
        }
        data = _attach_current_user(data)
        endpoint = "/service/{0}/template/{1}".format(service_id, id_)
        return self.post(endpoint, data)

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
                if (not template_type or template.template_type == template_type)
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


template_api_client = TemplateAPIClient()
