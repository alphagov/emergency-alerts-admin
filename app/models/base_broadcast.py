from flask import current_app
from ordered_set import OrderedSet
from werkzeug.utils import cached_property

from app.broadcast_areas.models import (
    CustomBroadcastArea,
    CustomBroadcastAreas,
    broadcast_area_libraries,
)
from app.broadcast_areas.utils import (
    aggregate_areas,
    generate_aggregate_names,
    get_polygons_from_areas,
)
from app.formatters import round_to_significant_figures
from app.models import JSONModel

ESTIMATED_AREA_OF_LARGEST_UK_COUNTY = broadcast_area_libraries.get_areas(["lad23-E06000065"])[  # North Yorkshire
    0
].polygons.estimated_area


class BaseBroadcast(JSONModel):
    libraries = broadcast_area_libraries

    __sort_attribute__ = None  # Class defines its own sorting behaviour

    @cached_property
    def areas(self):
        if "ids" in self._dict["areas"]:
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
                    f"BroadcastMessage has {len(self.area_ids)} area IDs "
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

    @property
    def has_flood_warning_target_areas(self):
        if type(self.areas) is CustomBroadcastAreas:
            return False
        return any(
            # Returns True if any of the message areas have an ID
            # that means its a Flood Warning Target Area, otherwise False
            (area.id.startswith("Flood_Warning_Target_Areas-") for area in self.areas)
        )

    @cached_property
    def polygons(self):
        return get_polygons_from_areas(self.areas, area_attribute="polygons")

    @cached_property
    def simple_polygons(self):
        return get_polygons_from_areas(self.areas, area_attribute="simple_polygons")

    @cached_property
    def simple_polygons_with_bleed(self):
        return get_polygons_from_areas(self.areas, area_attribute="simple_polygons_with_bleed")

    @cached_property
    def count_of_phones(self):
        return round_to_significant_figures(sum(area.count_of_phones for area in self.areas), 1)

    @cached_property
    def estimated_count_of_phones(self):
        return round_to_significant_figures(sum(area.estimated_count_of_phones for area in self.areas), 1)

    @cached_property
    def count_of_phones_likely(self):
        estimated_area = self.simple_polygons.estimated_area
        count_of_phones = self.count_of_phones

        def naive_estimate():
            return count_of_phones * (self.simple_polygons_with_bleed.estimated_area / estimated_area)

        def intersecting_estimate():
            return CustomBroadcastArea.from_polygon_objects(self.simple_polygons_with_bleed).count_of_phones

        if estimated_area <= ESTIMATED_AREA_OF_LARGEST_UK_COUNTY:
            # For smaller areas, where the computation can be done in
            # a second or less (approximately) calculate the number of
            # phones based on the ammount of overlap with areas for
            # which we have population data
            count = intersecting_estimate()

            # This serves as a guardrail in case our bleed area yields smaller figures
            # - which can happen because the calculations for the base polygon and the bleed
            # area are different.
            if count < count_of_phones:
                count = naive_estimate()
        else:
            # For large areas, use a naïve but computationally less
            # expensive way of counting the number of phones in the
            # bleed area
            count = naive_estimate()

        return round_to_significant_figures(count, 1)

    def get_areas(self, area_ids):
        return broadcast_area_libraries.get_areas(area_ids)

    def add_areas(self, *new_area_ids):
        self.area_ids = list(OrderedSet(self.area_ids + list(new_area_ids)))
        self._update_areas()

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
        aggregated_areas = aggregate_areas(self.areas)
        aggregate_names = generate_aggregate_names(aggregated_areas)
        areas = {
            "ids": self.area_ids,
            "names": [area.name for area in self.areas],
            "aggregate_names": aggregate_names,
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
