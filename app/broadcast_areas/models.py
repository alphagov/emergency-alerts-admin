import math
from abc import ABC, abstractmethod

from emergency_alerts_utils.formatters import formatted_list
from emergency_alerts_utils.polygons import Polygons
from emergency_alerts_utils.serialised_model import SerialisedModelCollection
from rtreelib import Rect
from werkzeug.utils import cached_property

from app.formatters import square_metres_to_square_miles
from app.models import SortingAndEqualityMixin

from .populations import CITY_OF_LONDON
from .repo import BroadcastAreasRepository, rtree_index


class GetItemByIdMixin:
    def get(self, id):
        for item in self:
            if item.id == id:
                return item
        raise KeyError(id)


class BaseBroadcastArea(ABC):
    @property
    @abstractmethod
    def simple_polygons(self):
        pass

    @property
    @abstractmethod
    def polygons(self):
        pass

    @property
    @abstractmethod
    def count_of_phones(self):
        pass

    @cached_property
    def simple_polygons_with_bleed(self):
        return self.simple_polygons.bleed_by(self.estimated_bleed_in_m)

    @cached_property
    def phone_density(self):
        if not self.simple_polygons.estimated_area:
            return 0
        return self.count_of_phones / square_metres_to_square_miles(self.simple_polygons.estimated_area)

    @property
    def estimated_bleed_in_m(self):
        """
        Estimates the amount of bleed based on the population of an
        area. Higher density areas tend to have short range masts, so
        the bleed is low (down to 500m). Lower density areas have longer
        range masts, so the typical bleed will be high (up to 5,000m).
        """
        if self.phone_density < 1:
            return Polygons.approx_bleed_in_m
        estimated_bleed = 5_900 - (math.log(self.phone_density, 10) * 1_250)
        return max(500, min(estimated_bleed, 5000))


class BroadcastArea(BaseBroadcastArea, SortingAndEqualityMixin):

    __sort_attribute__ = "name"

    def __init__(self, row):
        self.id, self.name, self._count_of_phones, self.library_id = row

    @cached_property
    def is_lower_tier_local_authority(self):
        return self.id.startswith("lad21-") and self.parent

    @cached_property
    def is_electoral_ward(self):
        return self.id.startswith("wd21-")

    @classmethod
    def from_row_with_simple_polygons(cls, row):
        instance = cls(row[:4])
        instance.simple_polygons = Polygons(
            row[4],
            utm_crs=row[5],
        )
        return instance

    @cached_property
    def polygons(self):
        polygons, utm_crs = BroadcastAreasRepository().get_polygons_for_area(self.id)
        return Polygons(polygons, utm_crs=utm_crs)

    @cached_property
    def simple_polygons(self):
        simple_polygons, utm_crs = BroadcastAreasRepository().get_simple_polygons_for_area(self.id)
        return Polygons(simple_polygons, utm_crs=utm_crs).utm_polygons

    @cached_property
    def sub_areas(self):
        return [BroadcastArea(row) for row in BroadcastAreasRepository().get_all_areas_for_group(self.id)]

    @property
    def count_of_phones(self):
        if self.id.endswith(CITY_OF_LONDON.WARDS):
            return CITY_OF_LONDON.DAYTIME_POPULATION * (
                self.polygons.estimated_area / CITY_OF_LONDON.AREA_SQUARE_METRES
            )
        if self.sub_areas:
            return sum(area.count_of_phones for area in self.sub_areas)
        # TODO: remove the `or 0` once missing data is fixed, see
        # https://www.pivotaltracker.com/story/show/174837293
        return self._count_of_phones or 0

    @cached_property
    def ancestors(self):
        return list(self._ancestors_iterator)

    @cached_property
    def parent(self):
        return next(iter(self.ancestors), None)

    @property
    def _ancestors_iterator(self):
        id = self.id

        while True:
            parent = BroadcastAreasRepository().get_parent_for_area(id)

            if not parent:
                return

            parent_broadcast_area = BroadcastArea(parent)
            yield parent_broadcast_area
            id = parent_broadcast_area.id


class CustomBroadcastArea(BaseBroadcastArea):
    def __init__(self, *, name, polygons=None):
        self.name = name
        self._polygons = polygons or []

    @classmethod
    def from_polygon_objects(cls, polygon_objects):
        instance = cls(name=None)
        instance.polygons = polygon_objects
        return instance

    @cached_property
    def polygons(self):
        return Polygons(
            # Polygons in the DB are stored with the coordinate pair
            # order flipped – this flips them back again
            [[[lat, long] for long, lat in polygon] for polygon in self._polygons]
        )

    simple_polygons = polygons

    @cached_property
    def overlapping_electoral_wards(self):
        return [area for area in self.nearby_electoral_wards if area.simple_polygons.intersects(self.polygons)]

    @cached_property
    def nearby_electoral_wards(self):
        if not self.polygons:
            return []
        return broadcast_area_libraries.get_areas_with_simple_polygons(
            [
                # We only index electoral wards in the RTree
                overlap.data
                for overlap in rtree_index.query(Rect(*self.simple_polygons.bounds))
            ]
        )

    @cached_property
    def count_of_phones(self):
        return sum(
            area.simple_polygons.ratio_of_intersection_with(self.polygons) * area.count_of_phones
            for area in self.nearby_electoral_wards
        )


class CustomBroadcastAreas(SerialisedModelCollection):
    model = CustomBroadcastArea

    def __init__(self, *, names, polygons):
        self.items = names
        self._polygons = polygons

    def __getitem__(self, index):
        return self.model(
            name=self.items[index],
            polygons=self._polygons if index == 0 else None,
        )


class BroadcastAreaLibrary(SerialisedModelCollection, SortingAndEqualityMixin, GetItemByIdMixin):

    model = BroadcastArea

    __sort_attribute__ = "name"

    def __init__(self, row):
        id, name, name_singular, is_group = row
        self.id = id
        self.name = name
        self.name_singular = name_singular
        self.is_group = bool(is_group)
        self.items = BroadcastAreasRepository().get_all_areas_for_library(self.id)

    def get_examples(self):
        # we show up to four things. three areas, then either a fourth area if there are exactly four, or "and X more".
        areas_to_show = sorted(area.name for area in self)[:4]

        count_of_areas_not_named = len(self.items) - 3
        # if there's exactly one area not named, there are exactly four - we should just show all four.
        if count_of_areas_not_named > 1:
            areas_to_show = areas_to_show[:3] + [f"{count_of_areas_not_named} more…"]

        return formatted_list(areas_to_show, before_each="", after_each="")


class BroadcastAreaLibraries(SerialisedModelCollection, GetItemByIdMixin):

    model = BroadcastAreaLibrary

    def __init__(self):
        self.items = BroadcastAreasRepository().get_libraries()

    def get_areas(self, area_ids):
        areas = BroadcastAreasRepository().get_areas(area_ids)
        return [BroadcastArea(area) for area in areas]

    def get_areas_with_simple_polygons(self, area_ids):
        areas = BroadcastAreasRepository().get_areas_with_simple_polygons(area_ids)
        return [BroadcastArea.from_row_with_simple_polygons(area) for area in areas]


broadcast_area_libraries = BroadcastAreaLibraries()
