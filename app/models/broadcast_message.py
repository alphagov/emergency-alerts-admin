from datetime import datetime, timedelta, timezone

from emergency_alerts_utils.template import BroadcastPreviewTemplate
from flask import abort
from flask_login import current_user
from ordered_set import OrderedSet

from app.broadcast_areas.models import BroadcastAreaLibraries, CustomBroadcastArea
from app.broadcast_areas.utils import aggregate_areas, generate_aggregate_names
from app.models import ModelList
from app.models.base_broadcast import BaseBroadcast
from app.notify_client.broadcast_message_api_client import broadcast_message_api_client


class BroadcastMessage(BaseBroadcast):
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

    def __init__(self, _dict):
        super().__init__(_dict)

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
    def create_from_area(cls, service_id, area_ids, template_id=None, content="", reference=""):
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
            broadcast_message_api_client.create_broadcast_message(
                service_id=service_id, template_id=template_id, content=content, reference=reference, areas=areas
            )
        )

    @classmethod
    def create_from_custom_area(cls, service_id, areas, template_id=None, content="", reference=""):
        areas = {
            "ids": areas.items,
            "names": areas.items,
            "aggregate_names": areas.items,
            "simple_polygons": areas._polygons,
        }
        return cls(
            broadcast_message_api_client.create_broadcast_message(
                service_id=service_id,
                template_id=template_id,
                content=content,
                reference=reference,
                areas=areas,
            )
        )

    @classmethod
    def update_from_content(cls, *, service_id, message_id, content=None, reference=None):
        broadcast_message_api_client.update_broadcast_message(
            service_id=service_id,
            broadcast_message_id=message_id,
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

    @classmethod
    def from_id_or_403(cls, broadcast_message_id, *, service_id):
        if not current_user.has_permissions("create_broadcasts", restrict_admin_usage=True):
            abort(403)
        return cls(
            broadcast_message_api_client.get_broadcast_message(
                service_id=service_id,
                broadcast_message_id=broadcast_message_id,
            )
        )

    @property
    def reference(self):
        if self.template_id and not self._dict["reference"]:
            return self._dict["reference"]
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

    def remove_area(self, area_id):
        self.area_ids = list(set(self._dict["areas"]["ids"]) - {area_id})
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
