import math

from emergency_alerts_utils.polygons import Polygons
from shapely import Polygon
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
        Returns list of Area objects for areas in `areas` in broadcast dictionary
        """
        areas_data = self._dict.get("areas") or {}
        area_ids = areas_data.get("ids")

        try:
            areas = Areas().get(area_ids, areas_data.get("names"))
            self.get_areas_by_id_failed = False
            return areas
        except Exception:
            # If error returned by API, setting this results
            # in has_valid_area method returning False
            self.get_areas_by_id_failed = True
            return []

    @property
    def area_ids(self):
        """Returns list of IDs for areas in broadcast"""
        return [area.id for area in self.areas]

    @property
    def area_names(self):
        """Returns list of names for areas in broadcast"""
        if self.areas:
            return [area.name for area in self.areas]
        if self._dict.get("areas"):
            return self._dict.get("areas").get("names")

    @property
    def ancestor_areas(self):
        """Returns unique parent Areas, including all ancestor levels."""

        parent_ids = set()
        ancestors = []
        for area in self.areas:
            parent = area

            # Continue while the current area has a parent
            while parent.parent:
                # Get the geographic ID of the current area's parent
                parent_id = parent.parent

                if parent_id in parent_ids:
                    break

                parent_ids.add(parent_id)

                # Load the parent Area object using its geographic ID
                parent = Area.from_geographic_id(parent_id)

                ancestors.append(parent)

        # Return all ancestors sorted alphabetically by area name
        return sorted(ancestors, key=lambda area: area.name)

    @cached_property
    def count_of_phones(self):
        """Returns the `count_of_phones` sourced via API client method, or 0"""
        if not self.has_valid_area:
            return 0
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

    @property
    def has_valid_area(self):
        areas_data = self._dict.get("areas") or {}
        raw_polygons = areas_data.get("simple_polygons") or []

        if getattr(self, "get_areas_by_id_failed", True):
            return False

        if not raw_polygons:
            return True  # no Area still returns valid

        for coordinates in raw_polygons:
            if coordinates[0] != coordinates[-1]:
                # Polygon isn't closed
                return False

        # returns True only if the all polygons are valid
        return all(Polygon(coordinates).is_valid for coordinates in raw_polygons)

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
        if self.count_of_phones <= 0 or self.estimated_area <= 0:
            return 0
        phone_density = self.count_of_phones / (self.estimated_area * 3.86e-7)  # Square metres to square miles
        estimated_bleed = 5_900 - (math.log10(phone_density) * 1_250)
        return max(500, min(estimated_bleed, 5000))
