from datetime import datetime, timedelta, timezone
from typing import Collection

from emergency_alerts_utils.xml.broadcast import generate_xml_body
from emergency_alerts_utils.xml.cap import convert_utc_datetime_to_cap_standard_string
from emergency_alerts_utils.xml.common import HEADLINE
from flask import redirect, render_template, request, url_for
from postcode_validator.uk.uk_postcode_validator import UKPostcode
from shapely import wkt
from shapely.ops import unary_union

from app import current_service, current_user
from app.config import BroadcastProvider, Config
from app.formatters import (
    format_mobile_networks,
    format_provider_status_with_human_time,
)
from app.main.forms import (
    ConfirmBroadcastForm,
    EastingNorthingCoordinatesForm,
    LatitudeLongitudeCoordinatesForm,
    RejectionReasonForm,
    ReturnForEditForm,
)
from app.models.areas import Area
from app.models.broadcast_message import BroadcastMessage
from app.notify_client.areas_api_client import areas_api_client
from app.utils.datetime import fromisoformat_allow_z_tz

INVALID_AREA_ERROR_TEXT = (
    "The area used is invalid and the alert cannot be sent. If the alert "
    "was created through the API, report it to the alert creator. Otherwise report "
    "it to the Emergency Alerts team."
)


def create_postcode_db_id(form):
    if form.pre_validate(form):
        return str(UKPostcode(form.data["postcode"]).postcode)


def create_custom_area_polygon(form, postcode):
    centroid = None
    radius = float(form.data["radius"]) if form.data["radius"] else 0
    try:
        centroid = areas_api_client.get_postcode_centroid(postcode)
        centroid = wkt.loads(centroid)
        data = areas_api_client.create_postcode_area(postcode, radius)
    except Exception:
        form.postcode.process_errors.append("Enter a postcode within the UK")
    return centroid, data.get("circle"), data.get("id")


def parse_coordinate_form_data(form):
    first_coordinate = float(form.data["first_coordinate"] or 0)
    second_coordinate = float(form.data["second_coordinate"] or 0)
    radius = float(form.data["radius"]) if form.data["radius"] else 0
    return first_coordinate, second_coordinate, radius


def all_fields_empty(request, form):
    return request.method == "POST" and not form.data["postcode"] and form.data["radius"] is None


def postcode_entered(request, form):
    return (
        request.method == "POST"
        and form.data["postcode"]
        and form.data["radius"] is None
        and form.radius.raw_data == [""]
    )


def postcode_and_radius_entered(request, form):
    return (
        request.method == "POST" and form.postcode and (form.data["radius"] is not None or form.radius.raw_data != [""])
    )


def continue_button_clicked(request):
    return request.form.get("continue")


def render_postcode_page(
    service_id,
    message,
    form,
    centroid,
    bleed,
    estimated_area,
    estimated_area_with_bleed,
    count_of_phones,
    message_type,
    template_folder_id=None,
):
    message_id = message.id if message else None
    return render_template(
        "views/broadcast/search-postcodes.html",
        broadcast_message=message,
        message=message,
        page_title="Choose alert area" if message_type == "broadcast" else "Choose template area",
        form=form,
        bleed=bleed or None,
        back_link=url_for(".choose_library", service_id=service_id, message_id=message_id, message_type=message_type),
        estimated_area=estimated_area,
        estimated_area_with_bleed=estimated_area_with_bleed,
        count_of_phones=count_of_phones,
        centroid=[centroid.y, centroid.x] if centroid else None,
        template_folder_id=template_folder_id,
    )


def select_coordinate_form(coordinate_type):
    if coordinate_type == "latitude_longitude":
        form = LatitudeLongitudeCoordinatesForm()
    elif coordinate_type == "easting_northing":
        form = EastingNorthingCoordinatesForm()
    return form


def all_coordinate_form_fields_empty(request, form):
    return (
        request.method == "POST"
        and form.data["radius"] is None
        and (form.data["first_coordinate"] is None or form.data["second_coordinate"] is None)
    )


def coordinates_entered_but_no_radius(request, form):
    return (
        request.method == "POST"
        and form.data["radius"] is None
        and form.radius.raw_data == [""]
        and form.pre_validate(form)
    )


def coordinates_and_radius_entered(request, form):
    return (
        request.method == "POST"
        and (form.data["radius"] is not None or form.radius.raw_data != [""])
        and form.first_coordinate is not None
        and form.second_coordinate is not None
    )


def render_coordinates_page(
    service_id,
    coordinate_type,
    bleed,
    estimated_area,
    estimated_area_with_bleed,
    count_of_phones,
    marker,
    message,
    form,
    message_type,
    template_folder_id=None,
):
    message_id = message.id if message else None
    return render_template(
        "views/broadcast/search-coordinates.html",
        page_title="Choose alert area" if message_type == "broadcast" else "Choose template area",
        message=message,
        back_link=url_for(
            ".choose_area",
            service_id=service_id,
            library_slug="coordinates",
            message_id=message_id,
            message_type=message_type,
            template_folder_id=template_folder_id,
        ),
        form=form,
        coordinate_type=coordinate_type,
        marker=marker,
        bleed=bleed,
        estimated_area=estimated_area,
        estimated_area_with_bleed=estimated_area_with_bleed,
        count_of_phones=count_of_phones,
        centroid=marker,
    )


def validate_form_based_on_fields_entered(request, form):
    if request.form.get("radius_btn"):
        form.validate_on_submit()
    elif request.form.get("search_btn"):
        form.pre_validate(form)


def adding_invalid_coords_errors_to_form(coordinate_type, form):
    if coordinate_type == "latitude_longitude":
        form.first_coordinate.process_errors.append("The latitude and longitude must be within the UK")
        form.second_coordinate.process_errors.append("The latitude and longitude must be within the UK")
    elif coordinate_type == "easting_northing":
        form.first_coordinate.process_errors.append("The easting and northing must be within the UK")
        form.second_coordinate.process_errors.append("The easting and northing must be within the UK")


def format_area_name(area_name):
    if area_name.endswith(", City of"):
        return f"City of {area_name[:-9]}"
    elif area_name.endswith(", County of"):
        return f"County of {area_name[:-11]}"
    else:
        return area_name


def format_areas_list(areas_list):
    return [format_area_name(area) if isinstance(area, str) else format_area_name(area.name) for area in areas_list]


def format_areas_list_with_parent(areas_list):
    formatted = []
    for area in areas_list:
        # Strings: keep existing behaviour
        if isinstance(area, str):
            formatted.append(format_area_name(area))
            continue

        # Electoral ward: parent → child
        if getattr(area, "is_electoral_ward", False):
            parent = format_area_name(area.parent.name)
            child = format_area_name(area.name)
            formatted.append(f"{parent} -> {child}")
        else:
            formatted.append(format_area_name(area.name))

    return formatted


def create_map_label(areas):
    label = ""
    if len(areas) == 1:
        label = f"Map of the United Kingdom, showing the area for {areas[0]}"
    elif len(areas) > 1:
        label = "Map of the United Kingdom, showing the areas for " + (", ").join(areas[:-1]) + " and " + areas[-1]
    return label


def stringify_areas(areas):
    areas_string = ""
    if len(areas) == 1:
        areas_string = areas[0]
    elif len(areas) > 1:
        areas_string = (", ").join(areas[:-1]) + " and " + areas[-1]
    return areas_string


def render_current_alert_page(
    broadcast_message,
    rejection_form=None,
    return_for_edit_form=None,
    confirm_broadcast_form=None,
    back_link_url=".broadcast_dashboard",
    hide_stop_link=False,
    errors=None,
):
    broadcast_provider_status_rows = None
    broadcast_provider_sending_error = False

    # Only query for alerts which have been sent
    if broadcast_message.status in {"broadcasting", "completed", "cancelled"}:
        broadcast_provider_statuses = broadcast_message.get_broadcast_provider_statuses()
        broadcast_provider_contains_cancellation = provider_statuses_contains_cancellation_events(
            broadcast_provider_statuses
        )
        # We loop the static providers here as we always want a row for every MNO - but immediately after hitting
        # broadcast it's unlikely the job(s) to send the alert have even been picked up yet to record a
        # broadcast_event at all.
        broadcast_provider_status_rows = [
            _get_mno_status_row(
                mno.name,
                broadcast_provider_statuses.get(mno.name, {"alert": [], "cancel": []}),
                broadcast_provider_contains_cancellation,
            )
            for mno in BroadcastProvider.PROVIDERS
        ]
        broadcast_provider_sending_error = provider_statuses_contains_fail_to_send(broadcast_provider_statuses)

    return render_template(
        "views/broadcast/view-message.html",
        broadcast_message=broadcast_message,
        rejection_form=RejectionReasonForm() if rejection_form is None else rejection_form,
        return_for_edit_form=ReturnForEditForm() if return_for_edit_form is None else return_for_edit_form,
        form=(
            ConfirmBroadcastForm(
                service_is_live=current_service.live,
                channel=current_service.broadcast_channel,
                max_phones=broadcast_message.count_of_phones,
            )
            if confirm_broadcast_form is None
            else confirm_broadcast_form
        ),
        areas=format_areas_list(broadcast_message.areas),
        back_link=url_for(
            back_link_url,
            service_id=current_service.id,
        ),
        hide_stop_link=hide_stop_link,
        broadcast_message_version_count=broadcast_message.get_count_of_versions(),
        last_updated_time=(
            broadcast_message.get_latest_version().get("created_at") if broadcast_message.get_latest_version() else None
        ),
        edit_reasons=broadcast_message.get_returned_for_edit_reasons(),
        returned_for_edit_by=broadcast_message.get_latest_returned_for_edit_reason().get("created_by_id"),
        broadcast_provider_status_rows=broadcast_provider_status_rows,
        broadcast_provider_sending_error=broadcast_provider_sending_error,
        errors=errors,
        message=broadcast_message,  # Required parameter for map javascripts
    )


def render_edit_alert_page(broadcast_message, form):
    return render_template(
        "views/broadcast/write-new-broadcast.html",
        broadcast_message=broadcast_message,
        form=form,
        changes=get_changed_alert_form_data(broadcast_message, form),
    )


def render_preview_alert_page(broadcast_message, areas, errors=None):
    return render_template(
        "views/broadcast/preview-message.html",
        broadcast_message=broadcast_message,
        message=broadcast_message,
        areas=areas,
        back_link=request.referrer,
        label=create_map_label(areas),
        areas_string=stringify_areas(areas),
        broadcast_message_version_count=broadcast_message.get_count_of_versions(),
        last_updated_time=(
            broadcast_message.get_latest_version().get("created_at") if broadcast_message.get_latest_version() else None
        ),
        returned_for_edit_by=broadcast_message.get_latest_returned_for_edit_reason().get("created_by_id"),
        errors=errors,
    )


def keep_alert_content_button_clicked():
    return request.method == "POST" and request.form.get("keep-message") is not None


def keep_alert_reference_button_clicked():
    return request.method == "POST" and request.form.get("keep-reference") is not None


def overwrite_content_button_clicked():
    return request.method == "POST" and request.form.get("overwrite-message") is not None


def overwrite_reference_button_clicked():
    return request.method == "POST" and request.form.get("overwrite-reference") is not None


def get_changed_alert_form_data(broadcast_message, form):
    """
    Compares stored alert reference and content with the initial form data, stored when page rendered.
    If the overwrite_{field} field is True, i.e. overwrite button has been clicked for that field
    then changes to that field are not stored and considered as we're overwriting the data for that field.
    """
    changes = {}
    if broadcast_message.reference != form.initial_name.data and not form.overwrite_name.data:
        changes["reference"] = {"updated_by": broadcast_message.updated_by or "A user"}
    if broadcast_message.content != form.initial_content.data and not form.overwrite_content.data:
        changes["message"] = {"updated_by": broadcast_message.updated_by or "A user"}
    return changes


def get_changed_extra_content_form_data(form, broadcast_message):
    """
    Compares stored extra_content with the initial form extra_content data, stored when page rendered.
    If the overwrite_extra_content field is True, i.e. overwrite button has been clicked for that field
    then changes to that field are not stored and considered as we're overwriting the data for that field.
    """
    changes = {}
    if broadcast_message.extra_content != form.initial_extra_content.data and not form.overwrite_extra_content.data:
        changes["updated_by"] = broadcast_message.updated_by or "A user"
    return changes


def update_broadcast_message_using_changed_data(broadcast_message_id, form):
    BroadcastMessage.update_from_content(
        service_id=current_service.id,
        message_id=broadcast_message_id,
        content=form.content.data if form.initial_content.data != form.content.data else None,
        reference=form.reference.data if form.initial_name.data != form.reference.data else None,
    )


def get_alert_redirect_url(broadcast_message):
    redirect_url = ""
    if broadcast_message.areas:
        if broadcast_message.duration:
            redirect_url = url_for(
                ".preview_broadcast_message",
                service_id=current_service.id,
                broadcast_message_id=broadcast_message.id,
            )
        else:
            redirect_url = url_for(
                ".choose_broadcast_duration",
                service_id=current_service.id,
                broadcast_message_id=broadcast_message.id,
            )
    else:
        redirect_url = url_for(
            ".choose_library",
            service_id=current_service.id,
            message_id=broadcast_message.id,
            message_type="broadcast",
        )

    return redirect_url


def redirect_if_operator_service(broadcast_message_id):
    # Redirects to the current broadcast view if the current service is an operator service.
    # Returns a redirect response if the service is an operator service, otherwise None.
    if not current_service.alerts_can_have_extra_content:
        return redirect(
            url_for(
                ".view_current_broadcast",
                service_id=current_service.id,
                broadcast_message_id=broadcast_message_id,
            )
        )
    return None


def check_for_missing_fields(broadcast_message):
    errors = []
    edit_url = url_for(
        ".edit_broadcast",
        service_id=current_service.id,
        broadcast_message_id=broadcast_message.id,
    )
    if not broadcast_message.reference:
        errors.append({"html": f"""<a href="{edit_url}">Add alert reference</a>"""})
    if not broadcast_message.content:
        errors.append({"html": f"""<a href="{edit_url}">Add alert message</a>"""})
    if not broadcast_message.areas:
        area_url = url_for(
            ".choose_library",
            service_id=current_service.id,
            message_id=broadcast_message.id,
            message_type="broadcast",
        )
        errors.append({"html": f"""<a href="{area_url}">Add alert area</a>"""})
    return errors


def provider_statuses_contains_fail_to_send(provider_statuses):
    for mno in provider_statuses:
        alert_statuses = provider_statuses[mno].get("alert", [])
        if len(alert_statuses) > 0:
            latest_alert_status = alert_statuses[-1]
            if latest_alert_status["status"] in {"returned-error", "returned-error-retry-exhausted"}:
                return True

    return False


def provider_statuses_contains_cancellation_events(provider_statuses):
    for mno in provider_statuses:
        cancel_statuses = provider_statuses[mno].get("cancel", [])
        if len(cancel_statuses) > 0:
            return True

    return False


def _get_back_link_from_view_broadcast_endpoint():
    return {
        "main.view_current_broadcast": ".broadcast_dashboard",
        "main.view_previous_broadcast": ".broadcast_dashboard_previous",
        "main.view_rejected_broadcast": ".broadcast_dashboard_rejected",
        "main.approve_broadcast_message": ".broadcast_dashboard",
        "main.reject_broadcast_message": ".broadcast_dashboard",
        "main.return_broadcast_for_edit": ".broadcast_dashboard",
        "main.discard_broadcast_message": ".broadcast_dashboard",
    }[request.endpoint]


def _get_broadcast_sub_area_back_link(service_id, message_id, library_slug, message_type):
    if prev_area_slug := request.args.get("prev_area_slug"):
        return url_for(
            ".choose_sub_area",
            service_id=service_id,
            message_id=message_id,
            library_slug=library_slug,
            area_slug=prev_area_slug,
            message_type=message_type,
        )
    else:
        return url_for(
            ".choose_area",
            service_id=service_id,
            message_id=message_id,
            library_slug=library_slug,
            message_type=message_type,
        )


def _get_choose_library_back_link(
    service_id,
    message_type,
    message_id=None,
    template_folder_id=None,
):
    if message_type == "broadcast":
        return url_for(
            ".choose_extra_content" if current_service.alerts_can_have_extra_content else ".write_new_broadcast",
            service_id=service_id,
            broadcast_message_id=message_id,
        )
    else:
        if not message_id:
            return url_for(
                ".choose_template_fields",
                service_id=service_id,
                template_folder_id=template_folder_id,
            )
        else:
            return request.referrer


def _get_mno_status_row(mno, mno_statuses, include_cancellation_status):
    """
    Get a row ready to pass to the govukTable macro.
    MNO | Alert Status | Cancellation Status
    """
    alert_row_text = ""
    if len(mno_statuses.get("alert", [])) > 0:
        latest_alert_status = mno_statuses.get("alert", [])[-1]
        alert_row_text = format_provider_status_with_human_time(
            latest_alert_status["status"], latest_alert_status["created_at"]
        )

    cancelled_row_text = ""
    if include_cancellation_status and len(mno_statuses.get("cancel", [])) > 0:
        latest_cancel_status = mno_statuses.get("cancel", [])[-1]
        cancelled_row_text = format_provider_status_with_human_time(
            latest_cancel_status["status"], latest_cancel_status["created_at"]
        )

    mno_capitalised = format_mobile_networks(mno)
    result = [{"text": mno_capitalised}, {"text": alert_row_text}]
    if include_cancellation_status:
        result.append({"text": cancelled_row_text})

    return result


def has_permission_for_message_type(service_id: str, message_type: str) -> bool:
    if message_type == "broadcast":
        return current_user.has_permission_for_service(service_id, "create_broadcasts")
    elif message_type == "templates":
        return current_user.has_permission_for_service(service_id, "manage_templates")
    else:
        raise RuntimeError("No known message_type " + message_type)


def generate_geojson(broadcast_message):
    areas: Collection[Area] = broadcast_message.areas
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    # geoJSON spec uses WGS84: https://datatracker.ietf.org/doc/html/rfc7946#section-4
                    "coordinates": area.polygons.as_wgs84_coordinates,
                },
                "properties": {"name": area.__dict__.get("name")},
            }
            for area in areas
        ],
    }
    return geojson


def generate_wkt(broadcast_message):
    areas = broadcast_message.areas

    # No areas return None
    if not areas:
        return None

    geoms = []

    # Iterate through all areas in broadcast message and combine them
    for area in areas:
        wkt_str = area.as_wkt_geometry

        geoms.append(wkt.loads(wkt_str))

    # No valid geometries return None
    if not geoms:
        return None

    merged = unary_union(geoms)
    return merged.wkt


def generate_unsigned_xml(broadcast_message, xml_type):
    is_cap_format = True
    if xml_type == "ibag":
        is_cap_format = False

    areas: Collection[Area] = broadcast_message.areas

    all_area_coordinates = []
    for area in areas:
        # An area in a broadcast_message can have multiple polygons (e.g. islands), so we need
        # to process each one and add it to the 'general' set of areas in the 'event' as used
        # by the XML logic.
        coordinate_pairs = area.polygons.as_coordinate_pairs_lat_long
        for coordinate_pair in coordinate_pairs:
            all_area_coordinates.append({"polygon": coordinate_pair})

    # When in training mode default to 'test' channel if channel is not set.
    # Prevents 500 error in utils.xml.common.validate_channel call later on.
    # XML will never be sent in training mode, but this function is still called when
    # downloading XML or sending summary emails.
    channel = current_service.broadcast_channel
    if channel is None and current_service.trial_mode:
        channel = "test"

    event = {
        # In a signed CAP message the identifier refers to a BroadcastProviderMessage which is unique per MNO
        # We don't have such a thing here so we just use the overall BroadcastMessage
        "identifier": broadcast_message.id,
        "message_type": "alert",
        "message_format": "cap" if is_cap_format else "ibag",
        "message_number": "00000001",  # Only relevant for IBAG, and is made up here
        "headline": HEADLINE,
        "description": broadcast_message.content,
        "language": "en-GB" if is_cap_format else "English",
        "areas": all_area_coordinates,
        "channel": channel,
        # starts_at and finishes_at can be None if it's a draft/awaiting approval, so we just use now
        # sent and expires expect a string in 'CAP' format (see convert_utc_... method's description)
        "sent": (
            convert_utc_datetime_to_cap_standard_string(
                fromisoformat_allow_z_tz(broadcast_message.starts_at)
                if broadcast_message.starts_at
                else datetime.now(timezone.utc)
            )
        ),
        "expires": (
            convert_utc_datetime_to_cap_standard_string(
                fromisoformat_allow_z_tz(broadcast_message.finishes_at)
                if broadcast_message.finishes_at
                else datetime.now(timezone.utc)
                + timedelta(seconds=_get_broadcast_duration(broadcast_message.broadcast_duration))
            )
        ),
    }

    cap_xml = generate_xml_body(event)
    return cap_xml


def _get_broadcast_duration(broadcast_duration):
    if broadcast_duration is not None:
        return int(broadcast_duration)

    if current_service.broadcast_channel in ["test", "operator"]:
        return Config.DEFAULT_DURATION_PERIODS.get("training", 30)
    else:
        return Config.DEFAULT_DURATION_PERIODS.get("live", 1350)


def create_area_from_wkt(circle_wkt):
    area = Area.from_wkt(circle_wkt)
    bleed = area.bleed
    estimated_area = area.estimated_area
    estimated_area_with_bleed = area.estimated_area_with_bleed
    count_of_phones = area.count_of_phones
    return bleed, estimated_area, estimated_area_with_bleed, count_of_phones
