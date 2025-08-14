import pyproj
from flask import redirect, render_template, request, url_for
from postcode_validator.uk.uk_postcode_validator import UKPostcode
from shapely import Point
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union

from app import current_service
from app.broadcast_areas.models import CustomBroadcastArea, CustomBroadcastAreas
from app.formatters import format_number_no_scientific, round_to_significant_figures
from app.main.forms import (
    ConfirmBroadcastForm,
    EastingNorthingCoordinatesForm,
    LatitudeLongitudeCoordinatesForm,
    PostcodeForm,
    RejectionReasonForm,
    ReturnForEditForm,
)
from app.models.broadcast_message import BroadcastMessage


def create_coordinate_area_slug(coordinate_type, first_coordinate, second_coordinate, radius):
    radius_min_sig_figs = format_number_no_scientific(radius)
    id = f"{radius_min_sig_figs}km around "
    if coordinate_type == "latitude_longitude":
        id = f"{id}{first_coordinate} latitude, {second_coordinate} longitude"
    elif coordinate_type == "easting_northing":
        first_coordinate = format_number_no_scientific(first_coordinate)
        second_coordinate = format_number_no_scientific(second_coordinate)
        id = f"{id}the easting of {first_coordinate} and the northing of {second_coordinate}"
    return id


def create_coordinate_area(lat, lng, radius, type):
    radius *= 1000
    if type == "easting_northing":
        crs_4326 = pyproj.CRS("EPSG:4326")
        crs_normalized = pyproj.CRS("EPSG:27700")
        transformer_inverse = pyproj.Transformer.from_crs(crs_normalized, crs_4326)
        normalized_center = Point(lat, lng)
    elif type == "latitude_longitude":
        crs_4326 = pyproj.CRS("EPSG:4326")
        crs_normalized = pyproj.CRS(proj="aeqd", datum="WGS84", lat_0=lat, lon_0=lng)
        transformer = pyproj.Transformer.from_crs(crs_4326, crs_normalized)
        transformer_inverse = pyproj.Transformer.from_crs(crs_normalized, crs_4326)
        normalized_center = Point(transformer.transform(lat, lng))
    circle = normalized_center.buffer(radius)
    xx, yy = circle.exterior.coords.xy
    xx_wgs84, yy_wgs84 = transformer_inverse.transform(xx, yy)
    return [[lat, lon] for lat, lon in zip(xx_wgs84, yy_wgs84)]


def check_coordinates_valid_for_enclosed_polygons(lat, lng, type):
    in_polygon = []
    uk_countries = BroadcastMessage.libraries.get_areas(
        [
            "ctry19-E92000001",
            "ctry19-N92000002",
            "ctry19-S92000003",
            "ctry19-W92000004",
        ]
    )
    test_areas = BroadcastMessage.libraries.get_areas(
        [
            "test-santa-claus-village-rovaniemi-a",
            "test-santa-claus-village-rovaniemi-b",
            "test-santa-claus-village-rovaniemi-c",
            "test-santa-claus-village-rovaniemi-d",
        ]
    )
    polygons_to_check = [uk_countries, test_areas]
    for group in polygons_to_check:
        polygons = []
        for area in group:
            # Extending polygons list by a list of polygons from those areas, with a buffer of 0.25 degrees
            polygons.extend([Polygon(p).buffer(0.25) for p in area.polygons.polygons])
        combined_polygon = unary_union(polygons)  # Calculating unary union of buffered polygons
        if isinstance(combined_polygon, MultiPolygon):
            shapely_polygon = MultiPolygon(combined_polygon)
        else:
            shapely_polygon = Polygon(combined_polygon)
        normalized_center = normalising_point(lat, lng, type)
        in_polygon.append(shapely_polygon.contains(normalized_center))
    return any(in_polygon)


def normalising_point(lat, lng, type):
    if type == "easting_northing":
        crs_4326 = pyproj.CRS("EPSG:4326")
        crs_normalized = pyproj.CRS("EPSG:27700")
        transformer_inverse = pyproj.Transformer.from_crs(crs_normalized, crs_4326)
        lat, lng = transformer_inverse.transform(lat, lng)
        normalized_center = Point(lng, lat)
    elif type == "latitude_longitude":
        normalized_center = Point(lng, lat)
    return normalized_center


def extract_attributes_from_custom_area(polygons):
    custom_area = CustomBroadcastArea(name="", polygons=[polygons])
    bleed = custom_area.estimated_bleed_in_m
    estimated_area = custom_area.simple_polygons.estimated_area
    estimated_area_with_bleed = custom_area.simple_polygons_with_bleed.estimated_area
    count_of_phones = round_to_significant_figures(custom_area.count_of_phones, 1)
    count_of_phones_likely = round_to_significant_figures(
        CustomBroadcastArea.from_polygon_objects(custom_area.simple_polygons_with_bleed).count_of_phones,
        1,
    )
    return bleed, estimated_area, estimated_area_with_bleed, count_of_phones, count_of_phones_likely


def create_postcode_db_id(form):
    if form.pre_validate(form):
        postcode_formatted = UKPostcode(form.data["postcode"]).postcode
        postcode = f"postcodes-{postcode_formatted}"
        return postcode


def create_custom_area_polygon(form: PostcodeForm, postcode):
    centroid = None
    circle_polygon = None
    radius = float(form.data["radius"]) if form.data["radius"] else 0
    try:
        area = BroadcastMessage.libraries.get_areas([postcode])[0]
        centroid = get_centroid(area)
        circle_polygon = create_circle(centroid, radius * 1000)
    except IndexError:
        form.postcode.process_errors.append("Enter a postcode within the UK")
    return centroid, circle_polygon


def create_postcode_area_slug(form):
    postcode_formatted = UKPostcode(form.data["postcode"]).postcode
    radius_to_min_sig_figs = "{:g}".format(float(form.data["radius"]))
    return f"{radius_to_min_sig_figs}km around the postcode {postcode_formatted}"


def get_centroid(area):
    polygons = area.polygons[0]
    return Polygon(polygons).centroid


def create_circle(center, radius):
    crs_4326 = pyproj.CRS("EPSG:4326")
    crs_normalized = pyproj.CRS(proj="aeqd", datum="WGS84", lat_0=center.y, lon_0=center.x)

    transformer = pyproj.Transformer.from_crs(crs_4326, crs_normalized)
    transformer_inverse = pyproj.Transformer.from_crs(crs_normalized, crs_4326)

    normalized_center = Point(transformer.transform(center.y, center.x))
    circle = normalized_center.buffer(radius)
    xx, yy = circle.exterior.coords.xy
    xx_wgs84, yy_wgs84 = transformer_inverse.transform(xx, yy)
    return [[lat, lon] for lat, lon in zip(xx_wgs84, yy_wgs84)]


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
    message_id,
    broadcast_message,
    form,
    centroid,
    bleed,
    estimated_area,
    estimated_area_with_bleed,
    count_of_phones,
    count_of_phones_likely,
    message_type,
    template_folder_id,
):
    return render_template(
        "views/broadcast/search-postcodes.html",
        broadcast_message=broadcast_message,
        page_title="Choose alert area" if message_type == "broadcast" else "Choose template area",
        form=form,
        bleed=bleed or None,
        back_link=url_for(
            ".choose_broadcast_library", service_id=service_id, message_id=message_id, message_type=message_type
        ),
        estimated_area=estimated_area,
        estimated_area_with_bleed=estimated_area_with_bleed,
        count_of_phones=count_of_phones,
        count_of_phones_likely=count_of_phones_likely,
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
    message_id,
    coordinate_type,
    bleed,
    estimated_area,
    estimated_area_with_bleed,
    count_of_phones,
    count_of_phones_likely,
    marker,
    broadcast_message,
    form,
    message_type,
    template_folder_id,
):
    return render_template(
        "views/broadcast/search-coordinates.html",
        page_title="Choose alert area" if message_type == "broadcast" else "Choose template area",
        message=broadcast_message,
        back_link=url_for(
            ".choose_broadcast_area",
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
        count_of_phones_likely=count_of_phones_likely,
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


def get_centroid_if_postcode_in_db(postcode, form):
    try:
        area = BroadcastMessage.libraries.get_areas([postcode])[0]
    except IndexError:
        form.postcode.process_errors.append("Enter a postcode within the UK")
    else:
        return get_centroid(area)


def format_area_name(area_name):
    if area_name.endswith(", City of"):
        return f"City of {area_name[:-9]}"
    elif area_name.endswith(", County of"):
        return f"County of {area_name[:-11]}"
    else:
        return area_name


def format_areas_list(areas_list):
    if isinstance(areas_list, CustomBroadcastArea):
        return [format_area_name(areas_list.name)]
    elif isinstance(areas_list, CustomBroadcastAreas):
        return [format_area_name(area) for area in areas_list.items]
    else:
        return [format_area_name(area) if isinstance(area, str) else format_area_name(area.name) for area in areas_list]


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
    print(current_service.id, broadcast_message.id)
    return render_template(
        "views/broadcast/view-message.html",
        broadcast_message=broadcast_message,
        rejection_form=RejectionReasonForm() if rejection_form is None else rejection_form,
        return_for_edit_form=ReturnForEditForm() if return_for_edit_form is None else return_for_edit_form,
        form=ConfirmBroadcastForm(
            service_is_live=current_service.live,
            channel=current_service.broadcast_channel,
            max_phones=broadcast_message.count_of_phones_likely,
        )
        if confirm_broadcast_form is None
        else confirm_broadcast_form,
        is_custom_broadcast=type(broadcast_message.areas) is CustomBroadcastAreas,
        areas=format_areas_list(broadcast_message.areas),
        back_link=url_for(
            back_link_url,
            service_id=current_service.id,
        ),
        hide_stop_link=hide_stop_link,
        broadcast_message_version_count=broadcast_message.get_count_of_versions(),
        last_updated_time=broadcast_message.get_latest_version().get("created_at")
        if broadcast_message.get_latest_version()
        else None,
        edit_reasons=broadcast_message.get_returned_for_edit_reasons(),
        returned_for_edit_by=broadcast_message.get_latest_returned_for_edit_reason().get("created_by_id"),
        errors=errors,
        message=broadcast_message,  # Required parameter for map javascripts
    )


def render_edit_alert_page(broadcast_message, form):
    return render_template(
        "views/broadcast/write-new-broadcast.html",
        message=broadcast_message,
        form=form,
        changes=get_changed_alert_form_data(broadcast_message, form),
    )


def render_preview_alert_page(broadcast_message, is_custom_broadcast, areas, errors=None):
    return render_template(
        "views/broadcast/preview-message.html",
        broadcast_message=broadcast_message,
        message=broadcast_message,
        custom_broadcast=is_custom_broadcast,
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


def redirect_dependent_on_alert_area(broadcast_message):
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
            ".choose_broadcast_library",
            service_id=current_service.id,
            message_id=broadcast_message.id,
            message_type="broadcast",
        )

    return redirect(redirect_url)


def redirect_if_operator_service(broadcast_message_id):
    # Redirects to the current broadcast view if the current service is an operator service.
    # Returns a redirect response if the service is an operator service, otherwise None.
    if current_service.broadcast_channel == "operator":
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
        ".write_new_broadcast",
        service_id=current_service.id,
        broadcast_message_id=broadcast_message.id,
    )
    if not broadcast_message.reference:
        errors.append({"html": f"""<a href="{edit_url}">Add alert reference</a>"""})
    if not broadcast_message.content:
        errors.append({"html": f"""<a href="{edit_url}">Add alert message</a>"""})
    if not broadcast_message.areas:
        area_url = url_for(
            ".choose_broadcast_library",
            service_id=current_service.id,
            message_id=broadcast_message.id,
            message_type="broadcast",
        )
        errors.append({"html": f"""<a href="{area_url}">Add alert area</a>"""})
    return errors
