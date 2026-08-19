import math

from emergency_alerts_utils.polygons import Polygons
from werkzeug.utils import cached_property

from app.models import JSONModel
from app.models.areas import Area, Areas, broadcast_area_libraries
from app.notify_client.areas_api_client import areas_api_client
from app.notify_client.broadcast_message_api_client import broadcast_message_api_client


class BaseBroadcast(JSONModel):
    libraries = broadcast_area_libraries

    __sort_attribute__ = None  # Class defines its own sorting behaviour

    @cached_property
    def areas(self):
        """
        Returns list of Area objects for areas in `areas` in brodacast dictionary
        """
        areas_data = self._dict.get("areas", {})
        if "ids" in areas_data:
            areas = Areas()
            return areas.get(areas_data["ids"], areas_data.get("names"))
        return []

    @property
    def area_ids(self):
        """Returns list of IDs for areas in broadcast"""
        return [area.id for area in self.areas]

    @property
    def area_names(self):
        """Returns list of names for areas in broadcast"""
        return [area.name for area in self.areas]

    @property
    def ancestor_areas(self):
        """Returns list of unique parent Areas for Areas"""
        existing_parent_ids = set()
        ancestors = []
        for area in self.areas:
            if not area.parent:
                continue
            if area.parent in existing_parent_ids:
                continue
            existing_parent_ids.add(area.parent)
            ancestors.append(Area.from_geographic_id(area.parent))
        return ancestors

    @cached_property
    def count_of_phones(self):
        """Returns the `count_of_phones` sourced via API client method, or 0"""
        response = broadcast_message_api_client.get_count_of_phones(self.simple_polygons.as_wkt)
        return response or 0

    @cached_property
    def estimated_area(self):
        return self.simple_polygons.estimated_area

    @cached_property
    def estimated_area_with_bleed(self):
        return self.simple_polygons_with_bleed.estimated_area

    @cached_property
    def simple_polygons(self):
        areas_data = self._dict.get("areas") or {}
        raw_polygons = areas_data.get("simple_polygons") or []
        # Coordinates are reversed as utils' Polygons class works in long, lat - not lat, long
        reversed_coords = [[[coord[1], coord[0]] for coord in polygon] for polygon in raw_polygons]
        return Polygons(polygons=reversed_coords)

    @cached_property
    def simple_polygons_with_bleed(self):
        if self.count_of_phones == 0 or not self.estimated_area:
            # Use utils' approximate bleed distance when data is missing
            return self.simple_polygons.bleed_by(Polygons.approx_bleed_in_m)

        bleed = self.calculate_bleed()
        return self.simple_polygons.bleed_by(bleed)

    @classmethod
    def add_areas(cls, id, service_id, new_area_ids, message_type="broadcast", type_name=None):
        return cls(areas_api_client.add_areas(id, service_id, new_area_ids, message_type, type_name))

    @classmethod
    def add_postcode_area(cls, id, service_id, postcode, radius, message_type):
        return cls(areas_api_client.add_postcode_area(id, service_id, postcode, radius, message_type))

    @classmethod
    def add_coordinate_area(
        cls, id, service_id, first_coordinate, second_coordinate, radius, coordinate_type, message_type
    ):
        return cls(
            areas_api_client.add_coordinate_area(
                id, service_id, first_coordinate, second_coordinate, radius, coordinate_type, message_type
            )
        )

    @classmethod
    def remove_area(cls, message_id, service_id, area_id, message_type):
        return cls(areas_api_client.remove_area(message_id, service_id, area_id, message_type))

    def calculate_bleed(self):
        """
        Estimates the amount of bleed based on the population of an
        area. Higher density areas tend to have short range masts, so
        the bleed is low (down to 500m). Lower density areas have longer
        range masts, so the typical bleed will be high (up to 5,000m).
        """
        phone_density = self.count_of_phones / (self.estimated_area) * 3.86e-7  # Square metres to square miles
        estimated_bleed = 5_900 - (math.log(phone_density, 10) * 1_250)
        return max(500, min(estimated_bleed, 5000))
