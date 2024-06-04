import pyproj
from flask import render_template, url_for
from postcode_validator.uk.uk_postcode_validator import UKPostcode
from shapely import Point
from shapely.geometry import Polygon
from shapely.ops import unary_union

from app.broadcast_areas.models import CustomBroadcastArea
from app.formatters import round_to_significant_figures
from app.main.forms import (
    EastingNorthingCoordinatesForm,
    LatitudeLongitudeCoordinatesForm,
    PostcodeForm,
)
from app.models.broadcast_message import BroadcastMessage


def create_coordinate_area_slug(coordinate_type, first_coordinate, second_coordinate, radius):
    radius_min_sig_figs = "{:g}".format(radius)
    id = f"{radius_min_sig_figs}km around "
    if coordinate_type == "latitude_longitude":
        id = f"{id}{first_coordinate} latitude, {second_coordinate} longitude"
    elif coordinate_type == "easting_northing":
        first_coordinate = "{:g}".format((first_coordinate))
        second_coordinate = "{:g}".format(second_coordinate)
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


def check_coordinates_valid_for_enclosed_polygons(message, lat, lng, type):
    in_polygon = []
    buffer = 0.5  # in kilometres
    uk_countries = message.libraries.get_areas(
        [
            "ctry19-E92000001",
            "ctry19-N92000002",
            "ctry19-S92000003",
            "ctry19-W92000004",
        ]
    )
    test_areas = message.libraries.get_areas(
        [
            "test-santa-claus-village-rovaniemi-a",
            "test-santa-claus-village-rovaniemi-b",
            "test-santa-claus-village-rovaniemi-c",
            "test-santa-claus-village-rovaniemi-d",
        ]
    )
    # instead need to add buffer to each polygon and combine
    polygons_to_check = [uk_countries, test_areas]
    for group in polygons_to_check:
        polygons = []
        for area in group:
            polygons.extend([Polygon(p).buffer(buffer) for p in area.polygons.polygons])
        combined_polygon = unary_union(polygons)
        shapely_polygon = Polygon(combined_polygon)
        normalized_center = normalising_point(lat, lng, type)
        in_polygon.append(shapely_polygon.contains(normalized_center))
        # geojson = json.dumps(mapping(shapely_polygon))
        # with open('countries.geojson', 'w') as f:
        #     f.write(geojson)
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


def create_custom_area_polygon(BroadcastMessage, form: PostcodeForm, postcode):
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


def preview_button_clicked(request):
    return request.form.get("preview")


def render_postcode_page(
    service_id,
    broadcast_message_id,
    broadcast_message,
    form,
    centroid,
    bleed,
    estimated_area,
    estimated_area_with_bleed,
    count_of_phones,
    count_of_phones_likely,
):
    return render_template(
        "views/broadcast/search-postcodes.html",
        broadcast_message=broadcast_message,
        page_title="Choose alert area",
        form=form,
        bleed=bleed or None,
        back_link=url_for(
            ".choose_broadcast_library", service_id=service_id, broadcast_message_id=broadcast_message_id
        ),
        estimated_area=estimated_area,
        estimated_area_with_bleed=estimated_area_with_bleed,
        count_of_phones=count_of_phones,
        count_of_phones_likely=count_of_phones_likely,
        centroid=[centroid.y, centroid.x] if centroid else None,
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
    broadcast_message_id,
    coordinate_type,
    bleed,
    estimated_area,
    estimated_area_with_bleed,
    count_of_phones,
    count_of_phones_likely,
    marker,
    broadcast_message,
    form,
):
    return render_template(
        "views/broadcast/search-coordinates.html",
        page_title="Choose a coordinate area",
        broadcast_message=broadcast_message,
        back_link=url_for(
            ".choose_broadcast_area",
            service_id=service_id,
            broadcast_message_id=broadcast_message_id,
            library_slug="coordinates",
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
