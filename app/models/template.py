from app.broadcast_areas.models import (
    BroadcastAreaLibraries,
    CustomBroadcastArea,
    broadcast_area_libraries,
)
from app.broadcast_areas.utils import aggregate_areas, generate_aggregate_names
from app.models.base_broadcast import BaseBroadcast
from app.notify_client.template_api_client import template_api_client

ESTIMATED_AREA_OF_LARGEST_UK_COUNTY = broadcast_area_libraries.get_areas(["lad23-E06000065"])[  # North Yorkshire
    0
].polygons.estimated_area


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
    def create_with_custom_area(cls, circle_polygon, area_id, service_id, template_folder_id=None):
        """Creates a broadcast template with a custom area defined by polygons."""
        simple_polygons = [circle_polygon]
        area_to_get_params = CustomBroadcastArea(name="", polygons=simple_polygons)
        id_with_local_authority = cls.add_local_authority_to_slug(cls, area_id, area_to_get_params)
        areas = {
            "ids": [id_with_local_authority],
            "names": [id_with_local_authority],
            "aggregate_names": [id_with_local_authority],
            "simple_polygons": simple_polygons,
        }
        return cls(
            template_api_client.create_template(
                service_id=service_id,
                template_folder_id=template_folder_id,
                areas=areas,
            )
        )

    @classmethod
    def create_from_area(cls, service_id, template_folder_id=None, area_ids=None):
        areas = BroadcastAreaLibraries().get_areas(area_ids)
        aggregated_areas = aggregate_areas(areas)
        aggregate_names = generate_aggregate_names(aggregated_areas)
        areas = {
            "ids": area_ids,
            "names": [area.name for area in areas],
            "aggregate_names": aggregate_names,
            "simple_polygons": [area.simple_polygons.as_coordinate_pairs_lat_long for area in areas],
        }
        return cls(
            template_api_client.create_template(
                service_id=service_id,
                template_folder_id=template_folder_id,
                areas=areas,
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

    def _update(self, **kwargs):
        template_api_client.update_template(
            id_=self.id,
            data=kwargs,
            service_id=self.service,
        )

    def add_custom_areas(self, *circle_polygon, id):
        simple_polygons = list(circle_polygon)
        area_to_get_params = CustomBroadcastArea(name="", polygons=simple_polygons)
        id = self.add_local_authority_to_slug(id, area_to_get_params)
        if id not in self.area_ids:
            areas = {
                "ids": [id],
                "names": [id],
                "aggregate_names": [id],
                "simple_polygons": simple_polygons,
            }
            data = {"areas": areas}

            self.area_ids = [id]
            template_api_client.update_template(id_=self.id, service_id=self.service, data=data)

    def get_template_version(self, service_id, version):
        return template_api_client.get_template(service_id, self.id, version)["data"]

    def get_template_versions(self, service_id):
        return template_api_client.get_template_versions(service_id, self.id)["data"]
