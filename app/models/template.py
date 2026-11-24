from flask import abort
from flask_login import current_user

from app import current_service
from app.models.base_broadcast import BaseBroadcast
from app.notify_client.areas_api_client import areas_api_client
from app.notify_client.template_api_client import template_api_client


class Template(BaseBroadcast):
    ALLOWED_PROPERTIES = {
        "id",
        "content",
        "name",
        "folder",
        "service",
        "version",
        "template_type",
        "updated_at",
        "reference",
        "created_by",
        "created_at",
        "archived",
    }

    def __init__(self, _dict):
        super().__init__(_dict)

    @property
    def service_id(self):
        return self.service

    @classmethod
    def create(cls, *, service_id, reference=None, content=None, template_folder_id=None, areas=None):
        return cls(
            template_api_client.create_template(
                service_id=service_id,
                reference=reference,
                content=content,
                template_folder_id=template_folder_id,
                areas=areas or [],
            )
        )

    @classmethod
    def create_from_area(cls, service_id, template_folder_id=None, area_ids=None):
        areas_dict = areas_api_client.get_area_dict(area_ids)
        return cls(
            template_api_client.create_template(
                service_id=service_id,
                template_folder_id=template_folder_id,
                areas=areas_dict,
            )
        )

    @classmethod
    def update_from_content(cls, *, service_id, template_id, content=None, reference=None):
        template_api_client.update_template(
            service_id=service_id,
            id_=template_id,
            data=({"reference": reference} if reference else {}) | ({"content": content} if content else {}),
        )

    @classmethod
    def from_id(cls, template_id, *, service_id):
        return cls(
            template_api_client.get_template(
                service_id=service_id,
                template_id=template_id,
            )["data"]
        )

    @classmethod
    def from_id_or_403(cls, template_id, *, service_id):
        if not current_user.has_permissions("manage_templates"):
            abort(403)

        template = cls(
            template_api_client.get_template(
                service_id=service_id,
                template_id=template_id,
            )["data"]
        )
        # Checks user has parent folder access also
        current_service.get_template_with_user_permission_or_403(template_id, current_user)

        return template

    def _update(self, **kwargs):
        template_api_client.update_template(
            id_=self.id,
            data=kwargs,
            service_id=self.service,
        )

    def get_template_version(self, service_id, version):
        return template_api_client.get_template(service_id, self.id, version)["data"]

    def get_template_versions(self, service_id):
        return template_api_client.get_template_versions(service_id, self.id)["data"]
