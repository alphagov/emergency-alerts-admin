import itertools
from datetime import datetime, timedelta, timezone

from emergency_alerts_utils.polygons import Polygons
from emergency_alerts_utils.template import BroadcastPreviewTemplate
from flask import current_app
from ordered_set import OrderedSet
from werkzeug.utils import cached_property

from app.broadcast_areas.models import (
    CustomBroadcastArea,
    CustomBroadcastAreas,
    broadcast_area_libraries,
)
from app.broadcast_areas.utils import aggregate_areas, generate_aggregate_names
from app.formatters import round_to_significant_figures
from app.models import JSONModel, ModelList
from app.notify_client.broadcast_message_api_client import broadcast_message_api_client

ESTIMATED_AREA_OF_LARGEST_UK_COUNTY = broadcast_area_libraries.get_areas(["lad23-E06000065"])[  # North Yorkshire
    0
].polygons.estimated_area


class BroadcastMessage(JSONModel):
    ALLOWED_PROPERTIES = {
        "id",
        "service_id",
        "template_id",
        "content",
        "service_id",
        "created_by",
        "personalisation",
        "duration",
        "starts_at",
        "finishes_at",
        "created_at",
        "approved_at",
        "cancelled_at",
        "updated_at",
        "rejected_at",
        "created_by_id",
        "approved_by_id",
        "cancelled_by_id",
        "rejected_by_id",
        "rejection_reason",
        "rejected_by",
        "created_by",
        "approved_by",
        "cancelled_by",
        "rejected_by_api_key_id",
        "submitted_by_id",
        "submitted_by",
        "submitted_at",
        "updated_by",
        "edit_reason",
        "extra_content",
    }

    libraries = broadcast_area_libraries

    __sort_attribute__ = None  # Class defines its own sorting behaviour

    def __lt__(self, other):
        if self.starts_at and other.starts_at:
            return self.starts_at < other.starts_at
        if self.starts_at and not other.starts_at:
            return True
        if not self.starts_at and other.starts_at:
            return False
        if self.updated_at and not other.updated_at:
            return self.updated_at < other.created_at
        if not self.updated_at and other.updated_at:
            return self.created_at < other.updated_at
        if not self.updated_at and not other.updated_at:
            return self.created_at < other.created_at
        return self.updated_at < other.updated_at

    @classmethod
    def create(cls, *, service_id, template_id):
        return cls(
            broadcast_message_api_client.create_broadcast_message(
                service_id=service_id,
                template_id=template_id,
                content=None,
                reference=None,
            )
        )

    @classmethod
    def create_from_content(cls, *, service_id, content, reference):
        return cls(
            broadcast_message_api_client.create_broadcast_message(
                service_id=service_id,
                template_id=None,
                content=content,
                reference=reference,
            )
        )

    @classmethod
    def update_from_content(cls, *, service_id, broadcast_message_id, content=None, reference=None):
        broadcast_message_api_client.update_broadcast_message(
            service_id=service_id,
            broadcast_message_id=broadcast_message_id,
            data=({"reference": reference} if reference else {}) | ({"content": content} if content else {}),
        )

    @classmethod
    def add_extra_content(cls, *, service_id, broadcast_message_id, extra_content):
        broadcast_message_api_client.update_broadcast_message(
            service_id=service_id, broadcast_message_id=broadcast_message_id, data=({"extra_content": extra_content})
        )

    @classmethod
    def remove_extra_content(cls, *, service_id, broadcast_message_id):
        broadcast_message_api_client.update_broadcast_message(
            service_id=service_id, broadcast_message_id=broadcast_message_id, data=({"extra_content": ""})
        )

    @classmethod
    def update_duration(cls, *, service_id, broadcast_message_id, duration):
        broadcast_message_api_client.update_broadcast_message(
            service_id=service_id,
            broadcast_message_id=broadcast_message_id,
            data={
                "duration": duration,
            },
        )

    @classmethod
    def from_id(cls, broadcast_message_id, *, service_id):
        return cls(
            broadcast_message_api_client.get_broadcast_message(
                service_id=service_id,
                broadcast_message_id=broadcast_message_id,
            )
        )

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

    @cached_property
    def polygons(self):
        return self.get_polygons_from_areas(area_attribute="polygons")

    @cached_property
    def simple_polygons(self):
        return self.get_polygons_from_areas(area_attribute="simple_polygons")

    @cached_property
    def simple_polygons_with_bleed(self):
        return self.get_polygons_from_areas(area_attribute="simple_polygons_with_bleed")

    @property
    def reference(self):
        if self.template_id and not self._dict["reference"]:
            return self._dict["template_name"]
        return self._dict["cap_event"] or self._dict["reference"]

    @property
    def template(self):
        return BroadcastPreviewTemplate(
            {
                "template_type": BroadcastPreviewTemplate.template_type,
                "name": self.reference,
                "content": self.content,
            }
        )

    @property
    def status(self):
        if (
            self._dict["status"]
            and self._dict["status"] == "broadcasting"
            and self.finishes_at < datetime.now(timezone.utc).isoformat()
        ):
            return "completed"
        return self._dict["status"]

    @property
    def broadcast_duration(self):
        return self._dict["duration"]

    @cached_property
    def count_of_phones(self):
        return round_to_significant_figures(sum(area.count_of_phones for area in self.areas), 1)

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
            data = {"areas": areas}

            self.area_ids = [id]
            broadcast_message_api_client.update_broadcast_message(
                broadcast_message_id=self.id, service_id=self.service_id, data=data
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

    def _set_status_to(self, status):
        broadcast_message_api_client.update_broadcast_message_status(
            status,
            broadcast_message_id=self.id,
            service_id=self.service_id,
        )

    def check_can_update_status(self, status):
        broadcast_message_api_client.check_broadcast_status_transition_allowed(
            status,
            broadcast_message_id=self.id,
            service_id=self.service_id,
        )

    def _update_areas(self, force_override=False):
        aggregate_names = generate_aggregate_names(self.areas)
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

    def _update(self, **kwargs):
        broadcast_message_api_client.update_broadcast_message(
            service_id=self.service_id,
            broadcast_message_id=self.id,
            data=kwargs,
        )

    def request_approval(self):
        self._set_status_to("pending-approval")

    def approve_broadcast(self, channel):
        if self.duration == 0 or self.duration is None:
            if channel in {"test", "operator"}:
                ttl = timedelta(hours=4, minutes=0)
            else:
                ttl = timedelta(hours=22, minutes=30)
        else:
            ttl = timedelta(seconds=self.duration)

        self._update(
            starts_at=datetime.now(timezone.utc).isoformat(),
            finishes_at=(datetime.now(timezone.utc) + ttl).isoformat(),
        )
        self._set_status_to("broadcasting")

    def reject_broadcast(self):
        self._set_status_to("rejected")

    def reject_broadcast_with_reason(self, rejection_reason):
        broadcast_message_api_client.update_broadcast_message_status_with_reason(
            "rejected", broadcast_message_id=self.id, service_id=self.service_id, rejection_reason=rejection_reason
        )

    def return_broadcast_message_for_edit(self, return_for_edit_reason):
        broadcast_message_api_client.return_broadcast_message_for_edit_with_reason(
            broadcast_message_id=self.id,
            service_id=self.service_id,
            edit_reason=return_for_edit_reason,
        )

    def cancel_broadcast(self):
        self._set_status_to("cancelled")

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

    def get_versions(self):
        return broadcast_message_api_client.get_broadcast_message_versions(self.service_id, self.id)

    def get_count_of_versions(self):
        return len(self.get_versions())

    def get_latest_version(self):
        versions = broadcast_message_api_client.get_broadcast_message_versions(self.service_id, self.id)
        return versions[0] if len(versions) > 0 else None

    def get_returned_for_edit_reasons(self):
        """Returns a list of 'edit_reason' records - these consist of the reason that alert has been returned,
        who submitted the alert for approval and who returned (as well as other attributes that we don't currently use)
        """
        return broadcast_message_api_client.get_broadcast_returned_for_edit_reasons(self.service_id, self.id)

    def get_latest_returned_for_edit_reason(self):
        """Returns latest edit_reason record submitted to the broadcast_message_edit_reasons
        table for the broadcast_message_id"""
        return broadcast_message_api_client.get_latest_returned_for_edit_reason(self.service_id, self.id)


class BroadcastMessages(ModelList):
    model = BroadcastMessage
    client_method = broadcast_message_api_client.get_broadcast_messages

    def with_status(self, *statuses):
        return [broadcast for broadcast in self if broadcast.status in statuses]
