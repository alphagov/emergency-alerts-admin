import math

from emergency_alerts_utils.polygons import Polygons
from emergency_alerts_utils.serialised_model import SerialisedModelCollection
from shapely import wkt
from werkzeug.utils import cached_property

from app.models import ModelList
from app.notify_client.areas_api_client import areas_api_client
from app.notify_client.broadcast_message_api_client import broadcast_message_api_client


class Area:
    """
    Represents a single area within a broadcast library.
    """

    def __init__(self, data):
        self.id = data.get("id")
        # `geographic_id` is the area's GSS Code / ONS ID
        self.geographic_id = data.get("geographic_id")
        self.name = data.get("name")
        self.parent = data.get("parent")
        self.geography_type = data.get("geography_type")
        self.geometry_wkt = data.get("geometry_wkt")

        # Not returned from API but created with `from_wkt` method and used
        # for rendering areas on custom area pages
        self.count_of_phones = data.get("count_of_phones")
        self.estimated_area = data.get("estimated_area")
        self.estimated_area_with_bleed = data.get("estimated_area_with_bleed")
        self.bleed = data.get("bleed")

    @cached_property
    def polygons(self):
        if self.geography_type in ["coordinates", "postcodes"]:
            # No geometry_wkt returned as not predefined
            polygon_wkt = areas_api_client.get_polygons(self.id)
        else:
            polygon_wkt = self.geometry_wkt

        if not polygon_wkt:
            return None

        geom = wkt.loads(polygon_wkt)
        geometries = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]

        return Polygons(
            polygons=[
                [[coordinate[0], coordinate[1]] for coordinate in polygon.exterior.coords] for polygon in geometries
            ]
        )

    @classmethod
    def from_id(cls, id):
        return cls(areas_api_client.get_area(id))

    @classmethod
    def from_geographic_id(cls, geographic_id):
        """Returns an Area object, from geographic_id"""
        return cls(areas_api_client.get_area_by_geographic_id(geographic_id))

    @classmethod
    def from_wkt(cls, polygon_wkt, name=None):
        """
        Create an Area object from a WKT polygon.
        This isn't posted to API - just created so you can access bleed,
        estimated_area, etc for custom polygons (postcodes/coordinates)
        """

        # WKT string loaded and shapely geometry returned,
        # then the exterior coordinates of the polygon become the coords
        # necessary for Polygons object
        geom = wkt.loads(polygon_wkt)
        coords = list(geom.exterior.coords)
        polygon_coords = [[coord[0], coord[1]] for coord in coords]
        polygons = Polygons(polygons=[polygon_coords])

        estimated_area = polygons.estimated_area
        count_of_phones = broadcast_message_api_client.get_count_of_phones(polygon_wkt) or 0
        bleed = cls.calculate_bleed(estimated_area, count_of_phones)
        estimated_area_with_bleed = polygons.bleed_by(bleed).estimated_area

        return cls(
            {
                "id": None,
                "geographic_id": None,
                "name": name,
                "parent": None,
                "geography_type": "custom",
                "count_of_phones": count_of_phones,
                "estimated_area": estimated_area,
                "estimated_area_with_bleed": estimated_area_with_bleed,
                "bleed": bleed,
            }
        )

    @classmethod
    def calculate_bleed(cls, estimated_area, count_of_phones):
        """
        Estimates the amount of bleed based on the population of an
        area. Higher density areas tend to have short range masts, so
        the bleed is low (down to 500m). Lower density areas have longer
        range masts, so the typical bleed will be high (up to 5,000m).
        """
        if count_of_phones <= 0 or estimated_area <= 0:
            return 0

        phone_density = count_of_phones / (estimated_area * 3.86e-7)  # Square metres to square miles
        estimated_bleed = 5_900 - (math.log(phone_density, 10) * 1_250)
        return max(500, min(estimated_bleed, 5000))

    def get_sub_areas(self):
        """Returns all sub areas for a parent"""
        raw_areas = areas_api_client.get_areas_for_parent(self.geographic_id)
        return [Area(area_data) for area_data in raw_areas]

    def is_grandparent(self):
        """Returns whether or not an area is a grandparent,
        i.e. it is the parent geography of an area that is also a parent geography"""
        return areas_api_client.check_grandparent(self.id)


class Areas(ModelList):
    model = Area
    client_method = areas_api_client.get_all_areas

    def get(self, area_ids, area_names):
        """
        Return a list of Area objects for the given IDs/names.
        """
        raw_areas = areas_api_client.get_areas_by_ids(area_ids, area_names)
        return [Area(area_data) for area_data in raw_areas]


class BroadcastAreaLibrary(SerialisedModelCollection):
    model = Area

    def __init__(self, data):
        self.id = data.get("id")
        self.name = data.get("name")
        # `name_singular` is how single areas are referred
        # to in the application .i.e. local authority
        self.name_singular = data.get("name_singular")
        # `examples` stores the hint text displayed for each library
        self.examples = data.get("examples")
        self.route = data.get("route")

        super().__init__([])

    @cached_property
    def is_group(self):
        """Returns whether or not the library has areas that are parents,
        i.e. their ID is the parent_geography_id of another area"""
        return self.route in ["local_authorities"]

    def get_areas(self):
        """
        Returns list of Area objects for library's areas
        """
        raw_areas = areas_api_client.get_areas_for_library(self.route)
        return [Area(area_data) for area_data in raw_areas]


class BroadcastAreaLibraries(ModelList):
    model = BroadcastAreaLibrary

    def client_method(self):
        libraries = areas_api_client.get_libraries()

        # Hard-coded additional library element for coordinates as this isn't stored in DB
        libraries.append(
            {
                "id": "coordinates",
                "name": "Coordinates",
                "name_singular": "Coordinates",
                "examples": [],
                "route": "coordinates",
                "areas": [],
            }
        )

        return libraries

    def get(self, library_route):
        """
        Return the BroadcastAreaLibrary with the given id (slug),
        or raise KeyError if not found.
        """
        for library in self:
            if library.route == library_route:
                return library
        raise KeyError(f"Library with route '{library_route}' not found")


broadcast_area_libraries = BroadcastAreaLibraries()
