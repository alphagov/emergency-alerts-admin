from flask import flash, redirect, render_template, request, url_for
from notifications_python_client.errors import HTTPError

from app.broadcast_areas.models import CustomBroadcastAreas
from app.main import main
from app.main.forms import (
    BroadcastAreaForm,
    BroadcastAreaFormWithSelectAll,
    ChooseCoordinateTypeForm,
    FloodWarningForm,
    PostcodeForm,
    SearchByNameForm,
)
from app.main.views.broadcast import create_new_broadcast, update_broadcast
from app.main.views.templates import write_new_broadcast_from_template
from app.models.broadcast_message import BroadcastMessage
from app.models.template import Template
from app.utils import service_has_permission
from app.utils.broadcast import (
    _get_broadcast_sub_area_back_link,
    _get_choose_library_back_link,
    adding_invalid_coords_errors_to_form,
    all_coordinate_form_fields_empty,
    all_fields_empty,
    check_coordinates_valid_for_enclosed_polygons,
    continue_button_clicked,
    coordinates_and_radius_entered,
    coordinates_entered_but_no_radius,
    create_coordinate_area,
    create_coordinate_area_slug,
    create_custom_area_polygon,
    create_postcode_area_slug,
    create_postcode_db_id,
    extract_attributes_from_custom_area,
    get_centroid_if_postcode_in_db,
    get_message_type,
    normalising_point,
    parse_coordinate_form_data,
    postcode_and_radius_entered,
    postcode_entered,
    redirect_dependent_on_alert_area,
    render_coordinates_page,
    render_current_alert_page,
    render_postcode_page,
    select_coordinate_form,
    validate_form_based_on_fields_entered,
)
from app.utils.user import user_has_any_permissions


@main.route("/services/<uuid:service_id>/write-new-broadcast", methods=["GET", "POST"])
@service_has_permission("broadcast")
@user_has_any_permissions(["create_broadcasts", "manage_templates"], restrict_admin_usage=True)
def write_new_broadcast(service_id):
    # If message_id in request then pre-populate with any existing data
    message_id = request.args.get("message_id")

    # Likewise, if template_id in request then Template has already been created & can add
    # reference and content here
    template_id = request.args.get("template_id")

    if message_id:
        return update_broadcast(service_id=service_id, message_id=message_id)
    elif template_id:
        return write_new_broadcast_from_template(service_id=service_id, template_id=template_id)
    else:
        return create_new_broadcast(service_id)


@main.route(
    "/services/<uuid:service_id>/<message_type>/<uuid:message_id>/libraries",
)
@main.route(
    "/services/<uuid:service_id>/<message_type>/libraries",
)
@service_has_permission("broadcast")
@user_has_any_permissions(["create_broadcasts", "manage_templates"], restrict_admin_usage=True)
def choose_library(service_id, message_type, message_id=None):
    template_folder_id = request.args.get("template_folder_id")
    Message = get_message_type(message_type)
    has_flood_warning_areas = False
    if message_id:
        message = Message.from_id_or_403(message_id, service_id=service_id)
        is_custom_broadcast = type(message.areas) is CustomBroadcastAreas
        if not is_custom_broadcast:
            # Checking whether or not alert has flood warning areas as they will be
            # treated as custom areas on libraries page
            has_flood_warning_areas = any(area.is_flood_warning_target_area for area in message.areas)
        if is_custom_broadcast or has_flood_warning_areas:
            # If alert has custom area or flood warning area, alert area is cleared as
            # they cannot be combined with other library areas
            message.clear_areas()
    else:
        message = None
        is_custom_broadcast = False
    return render_template(
        "views/broadcast/libraries.html",
        libraries=BroadcastMessage.libraries,
        message=message,
        custom_broadcast=is_custom_broadcast,
        back_link=_get_choose_library_back_link(
            service_id, message_type, template_folder_id=template_folder_id, message_id=message_id
        ),
        message_type=message_type,
        message_id=message_id,
        template_folder_id=template_folder_id,
        has_flood_warning_areas=has_flood_warning_areas,
    )


@main.route(
    "/services/<uuid:service_id>/<message_type>/<uuid:message_id>/libraries/<library_slug>",
    methods=["GET", "POST"],
)
@main.route(
    "/services/<uuid:service_id>/<message_type>/libraries/<library_slug>",
    methods=["GET", "POST"],
)
@service_has_permission("broadcast")
@user_has_any_permissions(["create_broadcasts", "manage_templates"], restrict_admin_usage=True)
def choose_area(
    service_id,
    library_slug,
    message_type,
    message_id=None,
):
    template_folder_id = request.args.get("template_folder_id")
    Message = get_message_type(message_type)
    message = Message.from_id_or_403(message_id, service_id=service_id) if message_id else None
    library = BroadcastMessage.libraries.get(library_slug)

    def redirect_for_library_page(url, service_id, message_type, message_id, template_folder_id):
        return redirect(
            url_for(
                url,
                service_id=service_id,
                message_id=message_id,
                message_type=message_type,
                template_folder_id=template_folder_id,
            )
        )

    if library_slug == "coordinates":
        form = ChooseCoordinateTypeForm()
        if form.validate_on_submit():
            return redirect(
                url_for(
                    ".search_coordinates",
                    service_id=service_id,
                    message_id=message_id,
                    coordinate_type=form.content.data,
                    message_type=message_type,
                    template_folder_id=template_folder_id,
                )
            )

        return render_template(
            "views/broadcast/choose-coordinates-type.html",
            page_title="Choose coordinate type",
            form=form,
            back_link=url_for(
                ".choose_library",
                service_id=service_id,
                message_id=message_id,
                message_type=message_type,
                template_folder_id=template_folder_id,
            ),
        )

    elif library_slug == "postcodes":
        url = ".search_postcodes"
        return redirect_for_library_page(url, service_id, message_type, message_id, template_folder_id)

    if library_slug == "Flood_Warning_Target_Areas":
        url = ".search_flood_warning_areas"
        return redirect_for_library_page(url, service_id, message_type, message_id, template_folder_id)

    if library.is_group:
        return render_template(
            "views/broadcast/areas-with-sub-areas.html",
            search_form=SearchByNameForm(),
            show_search_form=(len(library) > 7),
            library=library,
            page_title=f"Choose a {library.name_singular.lower()}",
            message=message,
            message_type=message_type,
            template_folder_id=template_folder_id,
        )

    form = BroadcastAreaForm.from_library(library)
    if form.validate_on_submit():
        if message:
            message.replace_areas([*form.areas.data])
        else:
            message = Message.create_from_area(
                service_id=service_id, area_ids=[*form.areas.data], template_folder_id=template_folder_id
            )
        return redirect(
            url_for(
                ".preview_areas",
                service_id=service_id,
                message_id=message.id,
                message_type=message_type,
                template_folder_id=template_folder_id,
            )
        )
    return render_template(
        "views/broadcast/areas.html",
        form=form,
        search_form=SearchByNameForm(),
        show_search_form=(len(form.areas.choices) > 7),
        page_title=(
            f"Choose {library.name[0].lower()}{library.name[1:]}"
            if library.name != "REPPIR DEPZ sites"
            else "Choose REPPIR DEPZ sites"
        ),
        message=message,
        back_link=url_for(
            ".choose_library",
            service_id=service_id,
            message_id=message_id,
            message_type=message_type,
            template_folder_id=template_folder_id,
        ),
        message_type=message_type,
        template_folder_id=template_folder_id,
    )


@main.route(
    "/services/<uuid:service_id>/<message_type>/<uuid:message_id>/libraries/<library_slug>/<area_slug>",  # noqa: E501
    methods=["GET", "POST"],
)
@main.route(
    "/services/<uuid:service_id>/<message_type>/libraries/<library_slug>/<area_slug>",  # noqa: E501
    methods=["GET", "POST"],
)
@service_has_permission("broadcast")
@user_has_any_permissions(["create_broadcasts", "manage_templates"], restrict_admin_usage=True)
def choose_sub_area(service_id, message_type, library_slug, area_slug, message_id=None):
    template_folder_id = request.args.get("template_folder_id")
    Message = get_message_type(message_type)
    message = Message.from_id_or_403(message_id, service_id=service_id) if message_id else None
    area = BroadcastMessage.libraries.get_areas([area_slug])[0]
    back_link = _get_broadcast_sub_area_back_link(service_id, message_id, library_slug, message_type)
    is_county = any(sub_area.sub_areas for sub_area in area.sub_areas)

    form = BroadcastAreaFormWithSelectAll.from_library(
        [] if is_county else area.sub_areas,
        select_all_choice=(area.id, f"All of {area.name}"),
    )
    if form.validate_on_submit():
        if message:
            message.replace_areas([*form.selected_areas])
        else:
            message = Message.create_from_area(
                service_id=service_id, area_ids=[*form.selected_areas], template_folder_id=template_folder_id
            )
        return redirect(
            url_for(
                ".preview_areas",
                service_id=service_id,
                message_id=message.id,
                message_type=message_type,
            )
        )

    if is_county:
        # area = county. sub_areas = districts. they have wards, so link to individual district pages
        return render_template(
            "views/broadcast/counties.html",
            form=form,
            search_form=SearchByNameForm(),
            show_search_form=(len(area.sub_areas) > 7),
            library_slug=library_slug,
            page_title=f"Choose an area of {area.name}",
            message=message,
            county=area,
            back_link=back_link,
            message_type=message_type,
        )

    return render_template(
        "views/broadcast/sub-areas.html",
        form=form,
        search_form=SearchByNameForm(),
        show_search_form=(len(form.areas.choices) > 7),
        library_slug=library_slug,
        page_title=f"Choose an area of {area.name}",
        message=message,
        back_link=back_link,
    )


@main.route("/services/<uuid:service_id>/<message_type>/<uuid:message_id>/areas")
@service_has_permission("broadcast")
@user_has_any_permissions(["create_broadcasts", "manage_templates"], restrict_admin_usage=True)
def preview_areas(service_id, message_id, message_type):
    is_custom = False
    has_flood_warning_areas = False
    Message = get_message_type(message_type)
    message = Message.from_id_or_403(message_id, service_id=service_id) if message_id else None
    if Message:
        is_custom = type(message.areas) is CustomBroadcastAreas
        if not is_custom:
            # Checking whether or not the alert has flood warning areas,
            # as this will determine content on rendered page
            has_flood_warning_areas = any(area.is_flood_warning_target_area for area in message.areas)
    if Message is BroadcastMessage:
        if message.status != "returned":
            try:
                message.check_can_update_status("draft")
            except HTTPError as e:
                flash(e.message)
                return render_current_alert_page(
                    message,
                )

        if message.duration:
            redirect_url = url_for(".preview_broadcast_message", service_id=service_id, broadcast_message_id=message_id)
        else:
            redirect_url = url_for(".choose_broadcast_duration", service_id=service_id, broadcast_message_id=message_id)
    else:
        redirect_url = url_for(".view_template", service_id=service_id, template_id=message_id)
    return render_template(
        "views/broadcast/preview-areas.html",
        message=message,
        back_link=request.referrer,
        is_custom_broadcast=is_custom,
        redirect_url=redirect_url,  # The url for when 'Save and continue' button clicked
        message_type=message_type,
        has_flood_warning_areas=has_flood_warning_areas,
    )


@main.route(
    "/services/<uuid:service_id>/<message_type>/libraries/postcodes",
    methods=["GET", "POST"],
)
@main.route(
    "/services/<uuid:service_id>/<message_type>/<uuid:message_id>/libraries/postcodes",
    methods=["GET", "POST"],
)
@service_has_permission("broadcast")
@user_has_any_permissions(["create_broadcasts", "manage_templates"], restrict_admin_usage=True)
def search_postcodes(service_id, message_type, message_id=None):
    template_folder_id = request.args.get("template_folder_id")
    Message = get_message_type(message_type)
    message = Message.from_id_or_403(message_id, service_id=service_id) if message_id else None
    form = PostcodeForm()
    # Initialising variables here that may be assigned values, to be then passed into jinja template.
    centroid, bleed, estimated_area, estimated_area_with_bleed, count_of_phones, count_of_phones_likely = (
        None,
        None,
        None,
        None,
        None,
        None,
    )

    if all_fields_empty(request, form):
        """
        If no input fields have values then the request will use the button clicked
        to determine which fields to validate.
        """
        validate_form_based_on_fields_entered(request, form)
    elif postcode_entered(request, form):
        """
        Clears any areas in broadcast message, then creates the ID to search for in SQLite database,
        if query returns IndexError, the postcode isn't in the database and thus error is appended to
        postcode field and displayed on the page.
        """
        postcode = create_postcode_db_id(form)
        centroid = get_centroid_if_postcode_in_db(postcode, form)
        form.pre_validate(form)  # Validating the postcode field
    elif postcode_and_radius_entered(request, form):
        """
        If postcode and radius entered, that are validated successfully,
        custom polygon is created using radius and centroid.
        """
        postcode = create_postcode_db_id(form)
        form.pre_validate(form)
        centroid, circle_polygon = create_custom_area_polygon(form, postcode)
        if form.validate_on_submit():
            """
            If postcode is in database, i.e. creating the Polygon didn't return IndexError,
            then a dummy CustomBroadcastArea is created and used for the attributes that
            are required for the Leaflet map, key, number of phones to display etc.
            """
            (
                bleed,
                estimated_area,
                estimated_area_with_bleed,
                count_of_phones,
                count_of_phones_likely,
            ) = extract_attributes_from_custom_area(circle_polygon)
            id = create_postcode_area_slug(form)
            if continue_button_clicked(request):
                """
                If 'Continue' button is clicked, area is added to Broadcast Message
                and message is updated.
                """
                if message:
                    message.add_custom_areas(circle_polygon, id=id)
                elif Message is Template:
                    message = Message.create_with_custom_area(
                        circle_polygon, id, service_id, template_folder_id=template_folder_id
                    )
                if Message is BroadcastMessage:
                    return redirect(
                        url_for(
                            ".preview_broadcast_message" if message.duration else ".choose_broadcast_duration",
                            service_id=service_id,
                            broadcast_message_id=message.id,
                        ),
                    )
                else:
                    return redirect(
                        url_for(
                            ".view_template",
                            service_id=service_id,
                            template_id=message.id,
                        )
                    )
    return render_postcode_page(
        service_id,
        message,
        form,
        centroid,
        bleed,
        estimated_area,
        estimated_area_with_bleed,
        count_of_phones,
        count_of_phones_likely,
        message_type,
        template_folder_id,
    )


@main.route(
    "/services/<uuid:service_id>/<message_type>/<uuid:message_id>/libraries/coordinates/<coordinate_type>/",  # noqa: E501
    methods=["GET", "POST"],
)
@main.route(
    "/services/<uuid:service_id>/<message_type>/libraries/coordinates/<coordinate_type>/",  # noqa: E501
    methods=["GET", "POST"],
)
@service_has_permission("broadcast")
@user_has_any_permissions(["create_broadcasts", "manage_templates"], restrict_admin_usage=True)
def search_coordinates(service_id, coordinate_type, message_type, message_id=None):
    template_folder_id = request.args.get("template_folder_id")
    Message = get_message_type(message_type)
    message = Message.from_id_or_403(message_id, service_id=service_id) if message_id else None
    (
        polygon,
        bleed,
        estimated_area,
        estimated_area_with_bleed,
        count_of_phones,
        count_of_phones_likely,
        marker,
    ) = (
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    )
    form = select_coordinate_form(coordinate_type)

    if all_coordinate_form_fields_empty(request, form):
        """
        If no input fields have values then the request will use the button clicked
        to determine which fields to validate.
        """
        validate_form_based_on_fields_entered(request, form)
    elif coordinates_entered_but_no_radius(request, form):
        """
        If only coordinates are entered then they're checked to determine if within
        either UK or test area. If they are within test or UK, the coordinate point is created
        and converted accordingly into latitude, longitude format to be passed into jinja
        and displayed in Leaflet map.
        Otherwise, an error is displayed on the page.
        """
        first_coordinate = float(form.data["first_coordinate"])
        second_coordinate = float(form.data["second_coordinate"])
        if check_coordinates_valid_for_enclosed_polygons(
            first_coordinate,
            second_coordinate,
            coordinate_type,
        ):
            Point = normalising_point(first_coordinate, second_coordinate, coordinate_type)
            marker = [Point.y, Point.x]
        else:
            adding_invalid_coords_errors_to_form(coordinate_type, form)
        form.pre_validate(form)  # To validate the fields don't have any errors
    elif coordinates_and_radius_entered(request, form):
        """
        If both radius and coordinates entered, then coordinates are checked to determine if within
        either UK or test area. If they are within test or UK, polygon is created using coordinates and
        radius. Then a CustomBroadcastArea is created and used for the attributes that
        are required for the Leaflet map, key, number of phones to display etc.
        """
        first_coordinate, second_coordinate, radius = parse_coordinate_form_data(form)
        if check_coordinates_valid_for_enclosed_polygons(
            first_coordinate,
            second_coordinate,
            coordinate_type,
        ):
            marker = [first_coordinate, second_coordinate]
            if form.validate_on_submit():
                if polygon := create_coordinate_area(
                    first_coordinate,
                    second_coordinate,
                    radius,
                    coordinate_type,
                ):
                    id = create_coordinate_area_slug(coordinate_type, first_coordinate, second_coordinate, radius)
                    (
                        bleed,
                        estimated_area,
                        estimated_area_with_bleed,
                        count_of_phones,
                        count_of_phones_likely,
                    ) = extract_attributes_from_custom_area(polygon)
        else:
            adding_invalid_coords_errors_to_form(coordinate_type, form)
            form.validate_on_submit()
        if continue_button_clicked(request):
            """
            If 'Preview alert' button is clicked, area is added to Broadcast Message
            and message is updated.
            """
            if message:
                message.add_custom_areas(polygon, id=id)
            elif Message is Template:
                message = Message.create_with_custom_area(
                    polygon, id, service_id, template_folder_id=template_folder_id
                )
            if Message is BroadcastMessage:
                return redirect(
                    url_for(
                        ".preview_broadcast_message" if message.duration else ".choose_broadcast_duration",
                        service_id=service_id,
                        broadcast_message_id=message.id,
                    ),
                )
            else:
                return redirect(
                    url_for(
                        ".view_template",
                        service_id=service_id,
                        template_id=message.id,
                    )
                )
    return render_coordinates_page(
        service_id,
        coordinate_type,
        bleed,
        estimated_area,
        estimated_area_with_bleed,
        count_of_phones,
        count_of_phones_likely,
        marker,
        message,
        form,
        message_type,
    )


@main.route(
    "/services/<uuid:service_id>/<message_type>/<uuid:message_id>/libraries/flood_warning_areas/",
    methods=["GET", "POST"],
)
@main.route(
    "/services/<uuid:service_id>/<message_type>/libraries/flood_warning_areas/",
    methods=["GET", "POST"],
)
@service_has_permission("broadcast")
@user_has_any_permissions(["create_broadcasts", "manage_templates"], restrict_admin_usage=True)
def search_flood_warning_areas(service_id, message_id, message_type):
    template_folder_id = request.args.get("template_folder_id")
    Message = get_message_type(message_type)
    message = Message.from_id_or_403(message_id, service_id=service_id) if message_id else None
    library = BroadcastMessage.libraries.get("Flood_Warning_Target_Areas")
    form = FloodWarningForm()

    def render_search_flood_warning_areas_page():
        # Added this as an inner function here as it's only used within this
        # function and removes repeated code
        return render_template(
            "views/broadcast/search-flood-warning-areas.html",
            broadcast_message=message,
            page_title="Choose Flood Warning Target Areas (TA)",
            form=form,
            back_link=url_for(
                ".choose_library", service_id=service_id, message_id=message_id, message_type=message_type
            ),
            template_folder_id=template_folder_id,
            message=message,
            message_type=message_type,
            redirect_url=redirect_dependent_on_alert_area(message),
        )

    if form.validate_on_submit():
        area_id = f"Flood_Warning_Target_Areas-{form.flood_warning_area.data}"
        if area_id not in library.item_ids:
            form.flood_warning_area.errors.append("Flood Warning TA Code not found")
            return render_search_flood_warning_areas_page()
        elif area_id in message.area_ids:
            form.flood_warning_area.errors.append("Flood Warning TA Code already selected")
            return render_search_flood_warning_areas_page()
        if message:
            message.add_areas(area_id)
        else:
            message = Message.create_from_area(
                service_id=service_id,
                area_ids=[area_id],
                template_folder_id=template_folder_id,
            )
        form.flood_warning_area.data = ""  # clear the form field on page after area added
    return render_search_flood_warning_areas_page()


@main.route("/services/<uuid:service_id>/<message_type>/<uuid:message_id>/remove/<area_slug>")
@service_has_permission("broadcast")
@user_has_any_permissions(["create_broadcasts", "manage_templates"], restrict_admin_usage=True)
def remove_area(service_id, message_id, area_slug, message_type):
    redirect_to_flood_warning_page = bool(request.args.get("redirect_to_flood_warning_page"))
    Message = get_message_type(message_type)
    message = Message.from_id_or_403(message_id, service_id=service_id) if message_id else None
    message.remove_area(area_slug)
    if redirect_to_flood_warning_page:
        url = ".search_flood_warning_areas"
    elif len(message.areas) == 0:
        url = ".choose_library"
    else:
        url = ".preview_areas"
    return redirect(
        url_for(
            url,
            service_id=service_id,
            message_id=message_id,
            message_type=message_type,
        )
    )


@main.route("/services/<uuid:service_id>/<message_type>/<uuid:message_id>/remove/")
@service_has_permission("broadcast")
@user_has_any_permissions(["create_broadcasts", "manage_templates"], restrict_admin_usage=True)
def remove_custom_area(service_id, message_id, message_type):
    Message = get_message_type(message_type)
    message = Message.from_id_or_403(message_id, service_id=service_id) if message_id else None
    message.clear_areas()
    return redirect(
        url_for(
            ".choose_library",
            service_id=service_id,
            message_id=message_id,
            message_type=message_type,
        )
    )
