from flask import flash, redirect, render_template, request, url_for
from notifications_python_client.errors import HTTPError

from app import current_service
from app.broadcast_areas.models import CustomBroadcastAreas
from app.main import main
from app.main.forms import (
    BroadcastAreaForm,
    BroadcastAreaFormWithSelectAll,
    BroadcastTemplateForm,
    ChooseCoordinateTypeForm,
    PostcodeForm,
    SearchByNameForm,
)
from app.models.broadcast_message import BroadcastMessage
from app.models.template import Template
from app.utils import service_has_permission
from app.utils.broadcast import (
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
from app.utils.user import user_has_permissions


@main.route("/services/<uuid:service_id>/write-new-broadcast", methods=["GET", "POST"])
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def write_new_broadcast(service_id):
    message_id = request.args.get("message_id")
    message = BroadcastMessage.from_id(message_id, service_id=current_service.id) if message_id else None
    template_id = request.args.get("template_id")
    template = Template.from_id(template_id, service_id=current_service.id) if template_id else None
    form = BroadcastTemplateForm()

    if form.validate_on_submit():
        if template_id:
            if template.areas:
                if type(template.areas) is CustomBroadcastAreas:
                    message = BroadcastMessage.create_from_custom_area(
                        service_id=current_service.id,
                        content=form.content.data,
                        reference=form.reference.data,
                        areas=template.areas,
                    )
                else:
                    message = BroadcastMessage.create_from_area(
                        service_id=current_service.id,
                        content=form.content.data,
                        reference=form.reference.data,
                        area_ids=template.area_ids,
                    )
        elif message_id:
            BroadcastMessage.update_from_content(
                service_id=current_service.id,
                message_id=message_id,
                content=form.content.data,
                reference=form.reference.data,
            )
        else:
            message = BroadcastMessage.create_from_content(
                service_id=current_service.id,
                content=form.content.data,
                reference=form.reference.data,
            )
        message_id = message.id
        return redirect(
            url_for(
                ".choose_extra_content"
                if current_service.broadcast_channel != "operator"
                else ".choose_broadcast_library",
                service_id=current_service.id,
                broadcast_message_id=message_id,
            )
        )

    if message_id:
        message = BroadcastMessage.from_id(
            message_id,
            service_id=current_service.id,
        )
        if message.status in ["draft", "returned"]:
            form.content.data = message.content
            form.reference.data = message.reference
        else:
            message = None

    return render_template(
        "views/broadcast/write-new-broadcast.html",
        message=message,
        form=form,
    )


@main.route("/services/<uuid:service_id>/new-broadcast/<uuid:template_id>")
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def broadcast(service_id, template_id):
    template = Template.from_id(template_id=template_id, service_id=service_id)
    if template.reference and template.content:
        if template.areas:
            # Make from area, reference and content
            # Redirect to extra content
            broadcast_message = (
                BroadcastMessage.create_from_custom_area(
                    service_id=service_id,
                    template_id=template_id,
                    areas=template.areas,
                    content=template.content,
                    reference=template.reference,
                )
                if type(template.areas) is CustomBroadcastAreas
                else BroadcastMessage.create_from_area(
                    service_id=service_id,
                    template_id=template_id,
                    area_ids=template.area_ids,
                    content=template.content,
                    reference=template.reference,
                )
            )
        else:
            # Make from just template and content
            # Redirect to extra content
            broadcast_message = BroadcastMessage.create_from_content(
                service_id=service_id, content=template.content, reference=template.reference
            )
            """If the current service is an operator service, user is redirected
            straight to choose area as extra_content attribute shouldn't be set for
            alerts created in operator services"""
        if current_service.broadcast_channel == "operator":
            return redirect_dependent_on_alert_area(template)
        else:
            return redirect(
                url_for(
                    ".choose_extra_content",
                    service_id=current_service.id,
                    broadcast_message_id=broadcast_message.id,
                )
            )
    elif template.areas:
        # Make from area only
        # Redirect to write content
        return redirect(
            url_for(
                ".write_new_broadcast",
                service_id=current_service.id,
                template_id=template.id,
            )
        )


@main.route("/services/<uuid:service_id>/<message_type>/<uuid:message_id>/areas")
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def preview_broadcast_areas(service_id, message_id, message_type):
    message = get_message_from_id(message_id, message_type)

    if message_type == "broadcast":
        if message.status != "returned":
            try:
                message.check_can_update_status("draft")
            except HTTPError as e:
                flash(e.message)
                return render_current_alert_page(
                    message,
                )

        if message.template_id and message.status not in ["draft", "returned"]:
            back_link = url_for(
                ".view_template",
                service_id=current_service.id,
                template_id=message.template_id,
            )
        elif message.status in ["draft", "returned"]:
            back_link = url_for(
                ".view_current_broadcast", service_id=current_service.id, broadcast_message_id=message_id
            )
        else:
            back_link = url_for(".write_new_broadcast", service_id=current_service.id, message_id=message_id)
    else:
        back_link = url_for(".write_new_broadcast", service_id=current_service.id, message_id=message_id)

    if message_type == "templates":
        back_link = request.referrer
        redirect_url = url_for(".view_template", service_id=current_service.id, template_id=message.id)
    elif message.duration:
        redirect_url = url_for(
            ".preview_broadcast_message",
            service_id=current_service.id,
            broadcast_message_id=message.id,
            message_type=message_type,
        )
    else:
        redirect_url = url_for(
            ".choose_broadcast_duration",
            service_id=current_service.id,
            broadcast_message_id=message.id,
            message_type=message_type,
        )

    return render_template(
        "views/broadcast/preview-areas.html",
        message=message,
        back_link=back_link,
        is_custom_broadcast=type(message.areas) is CustomBroadcastAreas,
        redirect_url=redirect_url,
        message_type=message_type,
    )


def get_message_from_id(message_id, message_type):
    message = None
    if message_type == "broadcast":
        message = BroadcastMessage.from_id(
            message_id,
            service_id=current_service.id,
        )
    elif message_type == "templates":
        message = Template.from_id(
            message_id,
            service_id=current_service.id,
        )
    return message


@main.route(
    "/services/<uuid:service_id>/<message_type>/<uuid:message_id>/libraries",
    methods=["GET", "POST"],
)
@main.route("/services/<uuid:service_id>/<message_type>/libraries", methods=["GET", "POST"])
def choose_broadcast_library(service_id, message_type, message_id=None):
    message = None
    is_custom_broadcast = False
    if message_id:
        message = get_message_from_id(message_id, message_type)
        is_custom_broadcast = type(message.areas) is CustomBroadcastAreas
        if is_custom_broadcast:
            message.clear_areas()
    return render_template(
        "views/broadcast/libraries.html",
        libraries=BroadcastMessage.libraries,
        message=message,
        custom_broadcast=is_custom_broadcast,
        back_link=request.referrer,
        message_type=message_type,
        message_id=message.id if message else None,
    )


@main.route(
    "/services/<uuid:service_id>/<message_type>/<uuid:message_id>/libraries/<library_slug>",
    methods=["GET", "POST"],
)
@main.route(
    "/services/<uuid:service_id>/<message_type>/libraries/<library_slug>",
    methods=["GET", "POST"],
)
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def choose_broadcast_area(service_id, library_slug, message_type, message_id=None):
    message = get_message_from_id(message_id, message_type) if message_id else None
    library = BroadcastMessage.libraries.get(library_slug)
    if library_slug == "coordinates":
        form = ChooseCoordinateTypeForm()
        if form.validate_on_submit():
            if message:
                url = url_for(
                    ".search_coordinates",
                    service_id=current_service.id,
                    message_id=message.id,
                    message_type=message_type,
                    coordinate_type=form.content.data,
                )
            else:
                url = url_for(
                    ".search_coordinates",
                    service_id=current_service.id,
                    message_type=message_type,
                    coordinate_type=form.content.data,
                )
            return redirect(url)

        return render_template(
            "views/broadcast/choose-coordinates-type.html",
            page_title="Choose coordinate type",
            form=form,
            back_link=url_for(
                ".choose_broadcast_library", service_id=service_id, message_id=message_id, message_type=message_type
            ),
        )
    elif library_slug == "postcodes":
        if message:
            url = url_for(
                ".search_postcodes",
                service_id=current_service.id,
                message_id=message.id,
                message_type=message_type,
            )
        else:
            url = url_for(".search_postcodes", service_id=current_service.id, message_type=message_type)
        return redirect(url)

    if library.is_group:
        return render_template(
            "views/broadcast/areas-with-sub-areas.html",
            search_form=SearchByNameForm(),
            show_search_form=(len(library) > 7),
            library=library,
            page_title=f"Choose a {library.name_singular.lower()}",
            message=message,
            message_type=message_type,
        )

    form = BroadcastAreaForm.from_library(library)
    if form.validate_on_submit():
        if message:
            message.replace_areas([*form.areas.data])
            return redirect(
                url_for(
                    ".preview_broadcast_areas",
                    service_id=current_service.id,
                    message_id=message.id,
                    message_type=message_type,
                )
            )
        elif message_type == "templates":
            message = Template.create_from_area(service_id=service_id, area_ids=[*form.areas.data])
            return redirect(
                url_for(
                    ".view_template",
                    service_id=current_service.id,
                    template_id=message.id,
                )
            )
    return render_template(
        "views/broadcast/areas.html",
        form=form,
        search_form=SearchByNameForm(),
        show_search_form=(len(form.areas.choices) > 7),
        page_title=f"Choose {library.name[0].lower()}{library.name[1:]}"
        if library.name != "REPPIR DEPZ sites"
        else "Choose REPPIR DEPZ sites",
        message=message,
        back_link=request.referrer,
        message_type=message_type,
    )


def _get_broadcast_sub_area_back_link(service_id, message_id, library_slug, message_type):
    if prev_area_slug := request.args.get("prev_area_slug"):
        return url_for(
            ".choose_broadcast_sub_area",
            service_id=service_id,
            message_id=message_id,
            library_slug=library_slug,
            area_slug=prev_area_slug,
            message_type=message_type,
        )
    else:
        return url_for(
            ".choose_broadcast_area",
            service_id=service_id,
            message_id=message_id,
            library_slug=library_slug,
            message_type=message_type,
        )


@main.route("/services/<uuid:service_id>/<message_type>/<uuid:message_id>/remove_custom/<postcode_slug>")
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def remove_postcode_area(service_id, message_id, postcode_slug, message_type):
    message = get_message_from_id(message_id=message_id, message_type=message_type)
    message = message.remove_area(postcode_slug)
    return redirect(
        url_for(
            ".choose_broadcast_library",
            service_id=current_service.id,
            message_id=message_id,
            library_slug="postcodes",
            message_type=message_type,
        )
    )


@main.route("/services/<uuid:service_id>/<message_type>/<uuid:message_id>/remove/")
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def remove_coordinate_area(service_id, message_id, message_type):
    message = get_message_from_id(message_id=message_id, message_type=message_type)
    message.clear_areas()
    return redirect(
        url_for(
            ".choose_broadcast_library", service_id=current_service.id, message_id=message.id, message_type=message_type
        )
    )


@main.route(
    "/services/<uuid:service_id>/<message_type>/libraries/postcodes",  # noqa: E501
    methods=["GET", "POST"],
)
@main.route(
    "/services/<uuid:service_id>/<message_type>/<uuid:message_id>/libraries/postcodes",  # noqa: E501
    methods=["GET", "POST"],
)
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def search_postcodes(service_id, message_type, message_id=None):
    message = get_message_from_id(message_id, message_type) if message_id else None
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
                if message and message_type == "broadcast":
                    message.add_custom_areas(circle_polygon, id=id)
                    return redirect(
                        url_for(
                            ".preview_broadcast_message" if message.duration else ".choose_broadcast_duration",
                            service_id=current_service.id,
                            broadcast_message_id=message.id,
                        ),
                    )
                elif message and message_type == "templates":
                    message.add_custom_areas(circle_polygon, id=id)
                    return redirect(
                        url_for(
                            ".view_template",
                            service_id=current_service.id,
                            template_id=message.id,
                        )
                    )
                else:
                    message = Template.create_with_custom_area(circle_polygon, id, service_id)
                    return redirect(
                        url_for(
                            ".view_template",
                            service_id=current_service.id,
                            template_id=message.id,
                        )
                    )
    return render_postcode_page(
        service_id,
        message_id,
        message,
        form,
        centroid,
        bleed,
        estimated_area,
        estimated_area_with_bleed,
        count_of_phones,
        count_of_phones_likely,
        message_type,
    )


@main.route(
    "/services/<uuid:service_id>/<message_type>/<uuid:message_id>/libraries/coordinates/<coordinate_type>/",  # noqa: E501
    methods=["GET", "POST"],
)
@main.route(
    "/services/<uuid:service_id>/<message_type>/libraries/coordinates/<coordinate_type>/",  # noqa: E501
    methods=["GET", "POST"],
)
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def search_coordinates(service_id, coordinate_type, message_type, message_id=None):
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
    message = get_message_from_id(message_id, message_type) if message_id else None
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
            if message and message_type == "broadcast":
                message.add_custom_areas(polygon, id=id)
                return redirect(
                    url_for(
                        ".preview_broadcast_message" if message.duration else ".choose_broadcast_duration",
                        service_id=current_service.id,
                        broadcast_message_id=message.id,
                    ),
                )
            elif message and message_type == "templates":
                message.add_custom_areas(polygon, id=id)
                return redirect(
                    url_for(
                        ".view_template",
                        service_id=current_service.id,
                        template_id=message.id,
                    )
                )
            else:
                message = Template.create_with_custom_area(polygon, id, service_id)
                return redirect(
                    url_for(
                        ".view_template",
                        service_id=current_service.id,
                        template_id=message.id,
                    )
                )
    return render_coordinates_page(
        service_id,
        message_id,
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
    "/services/<uuid:service_id>/<message_type>/<uuid:message_id>/libraries/<library_slug>/<area_slug>",
    methods=["GET", "POST"],
)
@main.route(
    "/services/<uuid:service_id>/<message_type>/libraries/<library_slug>/<area_slug>",
    methods=["GET", "POST"],
)
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def choose_broadcast_sub_area(service_id, message_type, library_slug, area_slug, message_id=None):
    message = get_message_from_id(message_id, message_type) if message_id else None
    if not BroadcastMessage.libraries.get_areas([area_slug]):
        return redirect(
            url_for(
                ".choose_broadcast_library",
                service_id=current_service.id,
                message_id=message.id,
                message_type=message_type,
                library_slug=library_slug,
            )
        )
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
        elif message_type == "templates":
            message = Template.create_from_area(service_id=service_id, area_ids=[*form.selected_areas])
        return redirect(
            url_for(
                ".preview_broadcast_areas",
                service_id=current_service.id,
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


@main.route("/services/<uuid:service_id>/<message_type>/<uuid:message_id>/remove/<area_slug>")
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def remove_broadcast_area(service_id, message_id, area_slug, message_type):
    message = get_message_from_id(message_id, message_type)
    message.remove_area(area_slug)
    if len(message.areas) == 0:
        return redirect(
            url_for(
                ".choose_broadcast_library",
                service_id=current_service.id,
                message_id=message_id,
                message_type=message_type,
            )
        )
    else:
        return redirect(
            url_for(
                ".preview_broadcast_areas",
                service_id=current_service.id,
                message_id=message_id,
                message_type=message_type,
            )
        )
