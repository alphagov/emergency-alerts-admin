import itertools

from emergency_alerts_utils.polygons import Polygons
from flask import abort, current_app
from orderedset import OrderedSet
from werkzeug.utils import cached_property

from app.broadcast_areas.models import (
    CustomBroadcastArea,
    CustomBroadcastAreas,
    broadcast_area_libraries,
)
from app.broadcast_areas.utils import aggregate_areas
from app.models import JSONModel
from app.notify_client.template_api_client import template_api_client


class Template(JSONModel):
    ALLOWED_PROPERTIES = {
        "id",
        "content",
        "name",
        "folder",
        "service",
        "version",
        "template_type",
        "updated_at",
    }

    libraries = broadcast_area_libraries

    __sort_attribute__ = None  # Class defines its own sorting behaviour

    @classmethod
    def from_id(cls, template_id, service_id):
        return cls(template_api_client.get_service_template(service_id, template_id)["data"])

    def get_template_with_user_permission_or_403(self, service_id, template_id, user):
        template = self.get_service_template(service_id, template_id)
        self.get_template_folder_with_user_permission_or_403(self.folder, user)
        return template

    def get_template_folder_with_user_permission_or_403(self, folder_id, user):
        template_folder = self.get_template_folder(folder_id)

        if not user.has_template_folder_permission(template_folder):
            abort(403)

        return template_folder

    def get_versions(self, service_id, template_id):
        return template_api_client.get_service_template_versions(service_id, template_id)

    @classmethod
    def create(cls, name, content, service_id, parent_folder_id=None, areas=None):
        return cls(
            template_api_client.create_service_template(
                name=name,
                type_="broadcast",
                content=content,
                parent_folder_id=parent_folder_id,
                service_id=service_id,
                areas=areas,
            )["data"]
        )

    @cached_property
    def areas(self):
        if self._dict["areas"] and "ids" in self._dict["areas"]:
            library_areas = self.get_areas(self.area_ids)

            if len(library_areas) == len(self.area_ids):
                return library_areas
            else:
                # it's possible an old broadcast may refer to areas that
                # are no longer part of our area libraries; in this case
                # we should just treat the whole thing as a custom broadcast,
                # which isn't great as our code doesn't support editing its
                # areas, but we don't expect this to happen often
                current_app.logger.warn(
                    f"Template has {len(self.area_ids)} area IDs "
                    f"but {len(library_areas)} found in the library. Treating "
                    f"{self.id} as a custom broadcast."
                )

        polygons = self._dict["areas"].get("simple_polygons", [])

        if polygons:
            return CustomBroadcastAreas(
                names=self._dict["areas"]["names"],
                polygons=polygons,
            )

        return []

    @property
    def area_ids(self):
        return self._dict["areas"].get("ids", [])

    @area_ids.setter
    def area_ids(self, value):
        self._dict["areas"]["ids"] = value

    @property
    def ancestor_areas(self):
        return sorted(set(self._ancestor_areas_iterator))

    @property
    def _ancestor_areas_iterator(self):
        for area in self.areas:
            for ancestor in area.ancestors:
                yield ancestor

    @cached_property
    def polygons(self):
        return self.get_polygons_from_areas(area_attribute="polygons")

    @cached_property
    def simple_polygons(self):
        return self.get_polygons_from_areas(area_attribute="simple_polygons")

    @cached_property
    def simple_polygons_with_bleed(self):
        return self.get_polygons_from_areas(area_attribute="simple_polygons_with_bleed")

    def get_areas(self, area_ids):
        return broadcast_area_libraries.get_areas(area_ids)

    def get_polygons_from_areas(self, area_attribute):
        areas_polygons = [getattr(area, area_attribute) for area in self.areas]
        coordinate_reference_systems = {polygons.utm_crs for polygons in areas_polygons}

        if len(coordinate_reference_systems) == 1:
            # All our polygons are defined in the same coordinate
            # reference system so we just have to flatten the list and
            # say which coordinate reference system we are using
            polygons = Polygons(
                list(itertools.chain(*areas_polygons)),
                utm_crs=next(iter(coordinate_reference_systems)),
            )
        else:
            # Our polygons are in different coordinate reference systems
            # We need to convert them back to degrees and make a new
            # instance of `Polygons` which will determine a common
            # coordinate reference system
            polygons = Polygons(
                list(itertools.chain(*(area_polygon.as_wgs84_coordinates for area_polygon in areas_polygons)))
            )

        if area_attribute != "polygons" and len(self.areas) > 1:
            # We’re combining simplified polygons from multiple areas so we
            # need to re-simplify the combined polygons to keep the point
            # count down
            return polygons.smooth.simplify
        return polygons

    def add_areas(self, *new_area_ids):
        self.area_ids = list(OrderedSet(self.area_ids + list(new_area_ids)))
        self._update_areas()

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
            self.areas = areas
            self.area_ids = [id]
            template_api_client.update_service_template(self.id, self.__dict__, self.service)

    @classmethod
    def create_with_custom_area(cls, circle_polygon, area_id, name, content, service_id, parent_folder_id=None):
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
        return cls.create(
            name=name,
            content=content,
            service_id=service_id,
            parent_folder_id=parent_folder_id,
            areas=areas,
        )

    def add_local_authority_to_slug(self, id, area_to_get_params):
        if not (local_authority := area_to_get_params.local_authority):
            return id
        if local_authority.endswith(", City of"):
            return f"{id} in City of {local_authority[:-9]}"
        elif local_authority.endswith(", County of"):
            return f"{id} in County of {local_authority[:-11]}"
        else:
            return f"{id} in {local_authority}"

    def remove_area(self, area_id):
        self.area_ids = list(set(self._dict["areas"]["ids"]) - {area_id})
        self._update_areas()

    def replace_areas(self, new_area_ids):
        """
        Created this to ensure that if areas are added, that are in the libraries,
        they will overwrite the custom area if added afterwards.
        """
        area_ids = (
            list(set(self._dict["areas"]["ids"]) & {area.id for area in self.get_areas(self.area_ids)})
            if self.area_ids
            else []
        )
        self.area_ids = list(OrderedSet(area_ids + list(new_area_ids)))
        self._update_areas()

    def _update_areas(self, force_override=False):
        areas = {
            "ids": self.area_ids,
            "names": [area.name for area in self.areas],
            "aggregate_names": [area.name for area in aggregate_areas(self.areas)],
            "simple_polygons": self.simple_polygons.as_coordinate_pairs_lat_long,
        }

        data = {"areas": areas}

        # TEMPORARY: while we migrate to a new format for "areas"
        """
            The following link is a ticket to ensure tracking of whether this temporary fix is still required
            https://gds-ea.atlassian.net/browse/EAS-2037?atlOrigin=eyJpIjoiOWY2OWQ5ZTcwNjU4NDNkZWFjYzE1NDg0NGMwOTgyOTciLCJwIjoiaiJ9
        """

        if force_override:
            data["force_override"] = True

        self._update(**data)

    def _update_custom_areas(self, force_override=False):
        areas = {
            "ids": self.area_ids,
            "names": [area.name for area in self.areas],
            "aggregate_names": [area.name for area in aggregate_areas(self.areas)],
            "simple_polygons": self.simple_polygons.as_coordinate_pairs_lat_long,
        }

        data = {"areas": areas}

        # TEMPORARY: while we migrate to a new format for "areas"
        """
            The following link is a ticket to ensure tracking of whether this temporary fix is still required
            https://gds-ea.atlassian.net/browse/EAS-2037?atlOrigin=eyJpIjoiOWY2OWQ5ZTcwNjU4NDNkZWFjYzE1NDg0NGMwOTgyOTciLCJwIjoiaiJ9
        """

        if force_override:
            data["force_override"] = True

        self._update(**data)

    def _update(self):
        template_api_client.update_service_template(self.id, self.__dict__, self.service)

    def clear_areas(self, force_override=False):
        self.area_ids.clear()
        areas = {
            "ids": [],
            "names": [],
            "aggregate_names": [],
            "simple_polygons": [],
        }

        data = {"areas": areas}

        # TEMPORARY: while we migrate to a new format for "areas"
        """
            The following link is a ticket to ensure tracking of whether this temporary fix is still required
            https://gds-ea.atlassian.net/browse/EAS-2037?atlOrigin=eyJpIjoiOWY2OWQ5ZTcwNjU4NDNkZWFjYzE1NDg0NGMwOTgyOTciLCJwIjoiaiJ9
        """

        if force_override:
            data["force_override"] = True

        self._update(**data)

    def delete_template(self, service_id, template_id):
        return template_api_client.delete_service_template(service_id, template_id)
