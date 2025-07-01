import json
from datetime import datetime, timedelta, timezone
from typing import Collection

from emergency_alerts_utils.template import BroadcastPreviewTemplate
from emergency_alerts_utils.xml.broadcast import generate_xml_body
from emergency_alerts_utils.xml.cap import convert_utc_datetime_to_cap_standard_string
from emergency_alerts_utils.xml.common import HEADLINE
from flask import (
    Response,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from notifications_python_client.errors import HTTPError

from app import current_service
from app.broadcast_areas.models import BaseBroadcastArea, CustomBroadcastAreas
from app.main import main
from app.main.forms import (
    AddExtraContentForm,
    BroadcastAreaForm,
    BroadcastAreaFormWithSelectAll,
    BroadcastTemplateForm,
    ChooseCoordinateTypeForm,
    ChooseDurationForm,
    ChooseExtraContentForm,
    ConfirmBroadcastForm,
    NewBroadcastForm,
    PostcodeForm,
    RejectionReasonForm,
    ReturnForEditForm,
    SearchByNameForm,
)
from app.models.broadcast_message import BroadcastMessage, BroadcastMessages
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
    create_map_label,
    create_postcode_area_slug,
    create_postcode_db_id,
    extract_attributes_from_custom_area,
    format_areas_list,
    get_centroid_if_postcode_in_db,
    get_changed_alert_form_data,
    keep_alert_content_button_clicked,
    keep_alert_reference_button_clicked,
    normalising_point,
    overwrite_content_button_clicked,
    overwrite_reference_button_clicked,
    parse_coordinate_form_data,
    postcode_and_radius_entered,
    postcode_entered,
    redirect_dependent_on_alert_area,
    render_coordinates_page,
    render_current_alert_page,
    render_edit_alert_page,
    render_postcode_page,
    select_coordinate_form,
    stringify_areas,
    update_broadcast_message_using_changed_data,
    validate_form_based_on_fields_entered,
)
from app.utils.datetime import fromisoformat_allow_z_tz
from app.utils.user import user_has_permissions


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


@main.route("/services/<uuid:service_id>/broadcast-tour/<int:step_index>")
@user_has_permissions()
@service_has_permission("broadcast")
def broadcast_tour(service_id, step_index):
    if step_index not in (1, 2, 3, 4, 5, 6):
        abort(404)
    return render_template(f"views/broadcast/tour/{step_index}.html")


@main.route("/services/<uuid:service_id>/broadcast-tour/live/<int:step_index>")
@user_has_permissions()
@service_has_permission("broadcast")
def broadcast_tour_live(service_id, step_index):
    if step_index not in (1, 2):
        abort(404)
    return render_template(f"views/broadcast/tour/live/{step_index}.html")


@main.route("/services/<uuid:service_id>/current-alerts")
@user_has_permissions()
@service_has_permission("broadcast")
def broadcast_dashboard(service_id):
    return render_template(
        "views/broadcast/dashboard.html",
        partials=get_broadcast_dashboard_partials(current_service.id),
    )


@main.route("/services/<uuid:service_id>/past-alerts")
@user_has_permissions()
@service_has_permission("broadcast")
def broadcast_dashboard_previous(service_id):
    return render_template(
        "views/broadcast/previous-broadcasts.html",
        broadcasts=BroadcastMessages(service_id).with_status(
            "cancelled",
            "completed",
        ),
        page_title="Past alerts",
        empty_message="You do not have any past alerts",
        view_broadcast_endpoint=".view_previous_broadcast",
        reverse_chronological_sort=True,
    )


@main.route("/services/<uuid:service_id>/rejected-alerts")
@user_has_permissions()
@service_has_permission("broadcast")
def broadcast_dashboard_rejected(service_id):
    return render_template(
        "views/broadcast/previous-broadcasts.html",
        broadcasts=BroadcastMessages(service_id).with_status(
            "rejected",
        ),
        page_title="Rejected alerts",
        empty_message="You do not have any rejected alerts",
        view_broadcast_endpoint=".view_rejected_broadcast",
        reverse_chronological_sort=True,
    )


@main.route("/services/<uuid:service_id>/broadcast-dashboard.json")
@user_has_permissions()
@service_has_permission("broadcast")
def broadcast_dashboard_updates(service_id):
    return jsonify(get_broadcast_dashboard_partials(current_service.id))


def get_broadcast_dashboard_partials(service_id):
    broadcast_messages = BroadcastMessages(service_id)
    return dict(
        current_broadcasts=render_template(
            "views/broadcast/partials/dashboard-table.html",
            broadcasts=broadcast_messages.with_status("pending-approval", "broadcasting", "draft", "returned"),
            empty_message="You do not have any current alerts",
            view_broadcast_endpoint=".view_current_broadcast",
            reverse_chronological_sort=False,  # Keep order that API returns - by status then alphabetically
        ),
    )


@main.route("/services/<uuid:service_id>/new-broadcast", methods=["GET", "POST"])
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def new_broadcast(service_id):
    form = NewBroadcastForm()

    if form.validate_on_submit():
        if form.use_template:
            return redirect(
                url_for(
                    ".choose_template",
                    service_id=current_service.id,
                )
            )
        return redirect(
            url_for(
                ".write_new_broadcast",
                service_id=current_service.id,
            )
        )

    return render_template(
        "views/broadcast/new-broadcast.html",
        form=form,
    )


@main.route(
    "/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/choose-extra-content", methods=["GET", "POST"]
)
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def choose_extra_content(service_id, broadcast_message_id):
    form = ChooseExtraContentForm()

    if form.validate_on_submit():
        if str(form.data["content"]) == "yes":
            return redirect(
                url_for(".add_extra_content", service_id=current_service.id, broadcast_message_id=broadcast_message_id)
            )
        else:
            url_for(
                ".choose_broadcast_library",
                service_id=current_service.id,
                broadcast_message_id=broadcast_message_id,
            )

    return render_template(
        "views/broadcast/choose-extra-content.html",
        form=form,
    )


@main.route(
    "/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/add-extra-content", methods=["GET", "POST"]
)
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def add_extra_content(service_id, broadcast_message_id):
    form = AddExtraContentForm()

    broadcast_message = (
        BroadcastMessage.from_id(broadcast_message_id, service_id=current_service.id) if broadcast_message_id else None
    )

    if form.validate_on_submit():
        broadcast_message.add_extra_content(
            service_id=current_service.id,
            broadcast_message_id=broadcast_message_id,
            extra_content=form.extra_content.data,
        )
        return redirect_dependent_on_alert_area(broadcast_message)

    if broadcast_message.status in ["draft", "returned"] and broadcast_message.extra_content:
        form.extra_content.data = broadcast_message.extra_content

    return render_template(
        "views/broadcast/add-extra-content.html",
        broadcast_message=broadcast_message,
        form=form,
    )


@main.route("/services/<uuid:service_id>/write-new-broadcast", methods=["GET", "POST"])
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def write_new_broadcast(service_id):
    broadcast_message_id = request.args.get("broadcast_message_id")
    broadcast_message = (
        BroadcastMessage.from_id(broadcast_message_id, service_id=current_service.id) if broadcast_message_id else None
    )
    form = BroadcastTemplateForm()

    if form.validate_on_submit():
        if broadcast_message_id:
            BroadcastMessage.update_from_content(
                service_id=current_service.id,
                broadcast_message_id=broadcast_message_id,
                content=form.template_content.data,
                reference=form.name.data,
            )
        else:
            broadcast_message = BroadcastMessage.create_from_content(
                service_id=current_service.id,
                content=form.template_content.data,
                reference=form.name.data,
            )
        broadcast_message_id = broadcast_message.id
        return redirect(
            url_for(
                ".choose_extra_content",
                service_id=current_service.id,
                broadcast_message_id=broadcast_message_id,
            )
        )

    if broadcast_message_id:
        broadcast_message = BroadcastMessage.from_id(
            broadcast_message_id,
            service_id=current_service.id,
        )
        if broadcast_message.status in ["draft", "returned"]:
            form.template_content.data = broadcast_message.content
            form.name.data = broadcast_message.reference
        else:
            broadcast_message = None

    return render_template(
        "views/broadcast/write-new-broadcast.html",
        broadcast_message=broadcast_message,
        form=form,
    )


@main.route("/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/edit", methods=["GET", "POST"])
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def edit_broadcast(service_id, broadcast_message_id):
    broadcast_message = BroadcastMessage.from_id(broadcast_message_id, service_id=current_service.id)

    # If alert cannot move into draft status from its original status, an error is rendered on page
    if broadcast_message.status != "returned":
        try:
            broadcast_message.check_can_update_status("draft")
        except HTTPError as e:
            flash(e.message)
            return render_current_alert_page(
                broadcast_message,
            )

    if request.method == "GET":
        # When the page loads initially, the fields are populated with alerts current data
        form = BroadcastTemplateForm(template_content=broadcast_message.content, name=broadcast_message.reference)
        form.initial_name.data = broadcast_message.reference
        form.initial_content.data = broadcast_message.content
    elif overwrite_reference_button_clicked():
        """
        When the button to overwrite the current reference data is clicked, the overwrite field is set
        to True, so the banner won't be displayed again as user has confirmed that they know the data is
        different and should be overwritten.
        The reference field is populated with "name" data posted from the request, and the page is re-rendered to
        reflect this.
        """
        form = BroadcastTemplateForm()
        form.overwrite_name.data = True
        form.name.data = request.form.get("name")
        return render_edit_alert_page(broadcast_message, form)
    elif overwrite_content_button_clicked():
        """
        When the button to overwrite the current message data is clicked, the overwrite field is set
        to True, so the banner won't be displayed again for message as user has confirmed that they know the data is
        different and should be overwritten.
        The message field is populated with "template-content" data posted from the request, and the page is
        re-rendered to reflect this.
        """
        form = BroadcastTemplateForm()
        form.overwrite_content.data = True
        form.template_content.data = request.form.get("template_content")
        return render_edit_alert_page(broadcast_message, form)
    elif keep_alert_reference_button_clicked():
        """
        When the button to keep the alert's current reference is clicked, the initial name field
        and the new name field are set to alert's current reference value and the page is re-rendered.
        """
        form = BroadcastTemplateForm()
        form.name.data = broadcast_message.reference
        form.initial_name.data = broadcast_message.reference
        return render_edit_alert_page(broadcast_message, form)

    elif keep_alert_content_button_clicked():
        """
        When the button to keep the alert's current message is clicked, the initial content field
        and the new template-content field are set to alert's current value and the page is re-rendered.
        """
        form = BroadcastTemplateForm()
        form.template_content.data = broadcast_message.content
        form.initial_content.data = broadcast_message.content
        return render_edit_alert_page(broadcast_message, form)

    else:
        form = BroadcastTemplateForm(
            name=request.form.get("name"), template_content=request.form.get("template_content")
        )

    if form.validate_on_submit():
        """
        Once form validated and submitted, check that the data stored in db matches form's initial data,
        and pass any changed data to template to display banners to indicate that alert has been updated
        while page open.
        """
        if changes := get_changed_alert_form_data(broadcast_message, form):
            return render_template(
                "views/broadcast/write-new-broadcast.html",
                broadcast_message=broadcast_message,
                form=form,
                changes=changes,
            )
        # Updates the initial data fields to ensure only changed data posted to API
        form.initial_name.data = broadcast_message.reference
        form.initial_content.data = broadcast_message.content
        update_broadcast_message_using_changed_data(broadcast_message_id, form)
        return redirect_dependent_on_alert_area(broadcast_message)

    return render_edit_alert_page(broadcast_message, form)


@main.route("/services/<uuid:service_id>/new-broadcast/<uuid:template_id>")
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def broadcast(service_id, template_id):
    return redirect(
        url_for(
            ".choose_extra_content",
            service_id=current_service.id,
            broadcast_message_id=BroadcastMessage.create(
                service_id=service_id,
                template_id=template_id,
            ).id,
        )
    )


@main.route("/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/areas")
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def preview_broadcast_areas(service_id, broadcast_message_id):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )

    if broadcast_message.status != "returned":
        try:
            broadcast_message.check_can_update_status("draft")
        except HTTPError as e:
            flash(e.message)
            return render_current_alert_page(
                broadcast_message,
            )

    if broadcast_message.template_id and broadcast_message.status not in ["draft", "returned"]:
        back_link = url_for(
            ".view_template",
            service_id=current_service.id,
            template_id=broadcast_message.template_id,
        )
    elif broadcast_message.status in ["draft", "returned"]:
        back_link = url_for(
            ".view_current_broadcast", service_id=current_service.id, broadcast_message_id=broadcast_message_id
        )
    else:
        back_link = url_for(
            ".write_new_broadcast", service_id=current_service.id, broadcast_message_id=broadcast_message_id
        )

    return render_template(
        "views/broadcast/preview-areas.html",
        broadcast_message=broadcast_message,
        back_link=back_link,
        is_custom_broadcast=type(broadcast_message.areas) is CustomBroadcastAreas,
    )


@main.route("/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/libraries")
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def choose_broadcast_library(service_id, broadcast_message_id):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )
    is_custom_broadcast = type(broadcast_message.areas) is CustomBroadcastAreas
    if is_custom_broadcast:
        broadcast_message.clear_areas()
    return render_template(
        "views/broadcast/libraries.html",
        libraries=BroadcastMessage.libraries,
        broadcast_message=broadcast_message,
        custom_broadcast=is_custom_broadcast,
    )


@main.route(
    "/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/libraries/<library_slug>",
    methods=["GET", "POST"],
)
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def choose_broadcast_area(service_id, broadcast_message_id, library_slug):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )
    library = BroadcastMessage.libraries.get(library_slug)

    if library_slug == "coordinates":
        form = ChooseCoordinateTypeForm()
        if form.validate_on_submit():
            return redirect(
                url_for(
                    ".search_coordinates",
                    service_id=current_service.id,
                    broadcast_message_id=broadcast_message.id,
                    library_slug="coordinates",
                    coordinate_type=form.content.data,
                )
            )

        return render_template(
            "views/broadcast/choose-coordinates-type.html",
            page_title="Choose coordinate type",
            form=form,
            back_link=url_for(
                ".choose_broadcast_library", service_id=service_id, broadcast_message_id=broadcast_message_id
            ),
        )
    elif library_slug == "postcodes":
        return redirect(
            url_for(
                ".search_postcodes",
                service_id=current_service.id,
                broadcast_message_id=broadcast_message.id,
                library_slug="postcodes",
            )
        )

    if library.is_group:
        return render_template(
            "views/broadcast/areas-with-sub-areas.html",
            search_form=SearchByNameForm(),
            show_search_form=(len(library) > 7),
            library=library,
            page_title=f"Choose a {library.name_singular.lower()}",
            broadcast_message=broadcast_message,
        )

    form = BroadcastAreaForm.from_library(library)
    if form.validate_on_submit():
        broadcast_message.replace_areas([*form.areas.data])
        return redirect(
            url_for(
                ".preview_broadcast_areas",
                service_id=current_service.id,
                broadcast_message_id=broadcast_message.id,
            )
        )
    return render_template(
        "views/broadcast/areas.html",
        form=form,
        search_form=SearchByNameForm(),
        show_search_form=(len(form.areas.choices) > 7),
        page_title=f"Choose {library.name[0].lower()}{library.name[1:]}",
        broadcast_message=broadcast_message,
    )


def _get_broadcast_sub_area_back_link(service_id, broadcast_message_id, library_slug):
    if prev_area_slug := request.args.get("prev_area_slug"):
        return url_for(
            ".choose_broadcast_sub_area",
            service_id=service_id,
            broadcast_message_id=broadcast_message_id,
            library_slug=library_slug,
            area_slug=prev_area_slug,
        )
    else:
        return url_for(
            ".choose_broadcast_area",
            service_id=service_id,
            broadcast_message_id=broadcast_message_id,
            library_slug=library_slug,
        )


@main.route("/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/remove_custom/<postcode_slug>")
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def remove_postcode_area(service_id, broadcast_message_id, postcode_slug):
    BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    ).remove_area(postcode_slug)
    return redirect(
        url_for(
            ".choose_broadcast_library",
            service_id=current_service.id,
            broadcast_message_id=broadcast_message_id,
            library_slug="postcodes",
        )
    )


@main.route("/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/remove/>")
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def remove_coordinate_area(service_id, broadcast_message_id):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )
    broadcast_message.clear_areas()
    return redirect(
        url_for(
            ".choose_broadcast_library",
            service_id=current_service.id,
            broadcast_message_id=broadcast_message.id,
        )
    )


@main.route(
    "/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/libraries/<library_slug>/postcodes/",  # noqa: E501
    methods=["GET", "POST"],
)
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def search_postcodes(service_id, broadcast_message_id, library_slug):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )
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
        centroid, circle_polygon = create_custom_area_polygon(broadcast_message, form, postcode)
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
                broadcast_message.add_custom_areas(circle_polygon, id=id)
                return redirect(
                    url_for(
                        ".preview_broadcast_message" if broadcast_message.duration else ".choose_broadcast_duration",
                        service_id=current_service.id,
                        broadcast_message_id=broadcast_message.id,
                    ),
                )
    return render_postcode_page(
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
    )


@main.route(
    "/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/libraries/<library_slug>/<coordinate_type>/",  # noqa: E501
    methods=["GET", "POST"],
)
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def search_coordinates(service_id, broadcast_message_id, library_slug, coordinate_type):
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
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
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
            broadcast_message,
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
            broadcast_message,
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
            broadcast_message.add_custom_areas(polygon, id=id)
            return redirect(
                url_for(
                    ".preview_broadcast_message" if broadcast_message.duration else ".choose_broadcast_duration",
                    service_id=current_service.id,
                    broadcast_message_id=broadcast_message.id,
                ),
            )
    return render_coordinates_page(
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
    )


@main.route(
    "/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/libraries/<library_slug>/<area_slug>",
    methods=["GET", "POST"],
)
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def choose_broadcast_sub_area(service_id, broadcast_message_id, library_slug, area_slug):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )
    area = BroadcastMessage.libraries.get_areas([area_slug])[0]

    back_link = _get_broadcast_sub_area_back_link(service_id, broadcast_message_id, library_slug)

    is_county = any(sub_area.sub_areas for sub_area in area.sub_areas)

    form = BroadcastAreaFormWithSelectAll.from_library(
        [] if is_county else area.sub_areas,
        select_all_choice=(area.id, f"All of {area.name}"),
    )
    if form.validate_on_submit():
        broadcast_message.replace_areas([*form.selected_areas])
        return redirect(
            url_for(
                ".preview_broadcast_areas",
                service_id=current_service.id,
                broadcast_message_id=broadcast_message.id,
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
            broadcast_message=broadcast_message,
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
        broadcast_message=broadcast_message,
        back_link=back_link,
    )


@main.route("/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/remove/<area_slug>")
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def remove_broadcast_area(service_id, broadcast_message_id, area_slug):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )
    broadcast_message.remove_area(area_slug)
    if len(broadcast_message.areas) == 0:
        return redirect(
            url_for(
                ".choose_broadcast_library",
                service_id=current_service.id,
                broadcast_message_id=broadcast_message_id,
            )
        )
    else:
        return redirect(
            url_for(
                ".preview_broadcast_areas",
                service_id=current_service.id,
                broadcast_message_id=broadcast_message_id,
            )
        )


@main.route("/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/duration", methods=["GET", "POST"])
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def choose_broadcast_duration(service_id, broadcast_message_id):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )
    is_custom_broadcast = type(broadcast_message.areas) is CustomBroadcastAreas
    form = ChooseDurationForm(channel=current_service.broadcast_channel, duration=broadcast_message.broadcast_duration)
    back_link = url_for(
        ".preview_broadcast_areas", service_id=current_service.id, broadcast_message_id=broadcast_message_id
    )

    if form.validate_on_submit():
        BroadcastMessage.update_duration(
            service_id=current_service.id,
            broadcast_message_id=broadcast_message_id,
            duration=f"PT{form.hours.data}H{form.minutes.data}M",
        )
        return redirect(
            url_for(
                ".preview_broadcast_message", service_id=current_service.id, broadcast_message_id=broadcast_message.id
            )
        )

    return render_template(
        "views/broadcast/duration.html",
        form=form,
        broadcast_message=broadcast_message,
        back_link=back_link,
        custom_broadcast=is_custom_broadcast,
    )


@main.route(
    "/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/preview",
    methods=["GET", "POST"],
)
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def preview_broadcast_message(service_id, broadcast_message_id):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )
    is_custom_broadcast = type(broadcast_message.areas) is CustomBroadcastAreas
    areas = format_areas_list(broadcast_message.areas)
    if request.method == "POST":
        try:
            broadcast_message.check_can_update_status("pending-approval")
        except HTTPError as e:
            flash(e.message)
            return render_template(
                "views/broadcast/preview-message.html",
                back_link=url_for(
                    ".broadcast_dashboard",
                    service_id=current_service.id,
                ),
                broadcast_message=broadcast_message,
                custom_broadcast=is_custom_broadcast,
                areas=areas,
                label=create_map_label(areas),
                areas_string=stringify_areas(areas),
                broadcast_message_version_count=broadcast_message.get_count_of_versions(),
                last_updated_time=(
                    broadcast_message.get_latest_version().get("created_at")
                    if broadcast_message.get_latest_version()
                    else None
                ),
                returned_for_edit_by=broadcast_message.get_latest_returned_for_edit_reason().get("created_by_id"),
            )
        broadcast_message.request_approval()
        return redirect(
            url_for(
                ".view_current_broadcast",
                service_id=current_service.id,
                broadcast_message_id=broadcast_message.id,
            )
        )
    return render_template(
        "views/broadcast/preview-message.html",
        broadcast_message=broadcast_message,
        custom_broadcast=is_custom_broadcast,
        areas=areas,
        label=create_map_label(areas),
        areas_string=stringify_areas(areas),
        broadcast_message_version_count=broadcast_message.get_count_of_versions(),
        last_updated_time=(
            broadcast_message.get_latest_version().get("created_at") if broadcast_message.get_latest_version() else None
        ),
        returned_for_edit_by=broadcast_message.get_latest_returned_for_edit_reason().get("created_by_id"),
    )


@main.route("/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/submit", methods=["GET", "POST"])
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def submit_broadcast_message(service_id, broadcast_message_id):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )
    try:
        broadcast_message.check_can_update_status("pending-approval")
    except HTTPError as e:
        flash(e.message)
        return render_current_alert_page(broadcast_message, hide_stop_link=True)

    broadcast_message.request_approval()
    return redirect(
        url_for(
            ".view_current_broadcast",
            service_id=current_service.id,
            broadcast_message_id=broadcast_message.id,
        )
    )


@main.route(
    "/services/<uuid:service_id>/current-alerts/<uuid:broadcast_message_id>",
    endpoint="view_current_broadcast",
)
@main.route(
    "/services/<uuid:service_id>/previous-alerts/<uuid:broadcast_message_id>",
    endpoint="view_previous_broadcast",
)
@main.route(
    "/services/<uuid:service_id>/rejected-alerts/<uuid:broadcast_message_id>",
    endpoint="view_rejected_broadcast",
)
@user_has_permissions()
@service_has_permission("broadcast")
def view_broadcast(service_id, broadcast_message_id):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )

    for statuses, endpoint in (
        ({"completed", "cancelled"}, "main.view_previous_broadcast"),
        ({"broadcasting", "pending-approval", "draft", "returned"}, "main.view_current_broadcast"),
        ({"rejected"}, "main.view_rejected_broadcast"),
    ):
        if broadcast_message.status in statuses and request.endpoint != endpoint:
            return redirect(
                url_for(
                    endpoint,
                    service_id=current_service.id,
                    broadcast_message_id=broadcast_message.id,
                )
            )

    return render_current_alert_page(broadcast_message, back_link_url=_get_back_link_from_view_broadcast_endpoint())


@main.route("/services/<uuid:service_id>/current-alerts/<uuid:broadcast_message_id>", methods=["POST"])
@user_has_permissions("approve_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def approve_broadcast_message(service_id, broadcast_message_id):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )

    form = ConfirmBroadcastForm(
        service_is_live=current_service.live,
        channel=current_service.broadcast_channel,
        max_phones=broadcast_message.count_of_phones_likely,
    )

    is_custom_broadcast = type(broadcast_message.areas) is CustomBroadcastAreas
    areas = format_areas_list(broadcast_message.areas)

    try:
        broadcast_message.check_can_update_status("broadcasting")
    except HTTPError as e:
        flash(e.message)
        return render_template(
            "views/broadcast/preview-message.html",
            back_link=url_for(
                ".broadcast_dashboard",
                service_id=current_service.id,
            ),
            broadcast_message=broadcast_message,
            custom_broadcast=is_custom_broadcast,
            areas=areas,
            label=create_map_label(areas),
            areas_string=stringify_areas(areas),
            broadcast_message_version_count=broadcast_message.get_count_of_versions(),
            last_updated_time=(
                broadcast_message.get_latest_version().get("created_at")
                if broadcast_message.get_latest_version()
                else None
            ),
            returned_for_edit_by=broadcast_message.get_latest_returned_for_edit_reason().get("created_by_id"),
        )

    if broadcast_message.status != "pending-approval":
        return redirect(
            url_for(
                ".view_current_broadcast",
                service_id=current_service.id,
                broadcast_message_id=broadcast_message.id,
            )
        )

    if current_service.trial_mode:
        broadcast_message.approve_broadcast(channel=current_service.broadcast_channel)
        return redirect(
            url_for(
                ".broadcast_tour",
                service_id=current_service.id,
                step_index=6,
            )
        )
    elif form.validate_on_submit():
        broadcast_message.approve_broadcast(channel=current_service.broadcast_channel)
    else:
        return render_current_alert_page(
            broadcast_message, confirm_broadcast_form=form, back_link_url=_get_back_link_from_view_broadcast_endpoint()
        )

    return redirect(
        url_for(
            ".view_current_broadcast",
            service_id=current_service.id,
            broadcast_message_id=broadcast_message.id,
        )
    )


@main.route("/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/reject", methods=["GET", "POST"])
@user_has_permissions("create_broadcasts", "approve_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def reject_broadcast_message(service_id, broadcast_message_id):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )

    form = RejectionReasonForm()
    rejection_reason = form.rejection_reason.data

    try:
        broadcast_message.check_can_update_status("rejected")
    except HTTPError as e:
        flash(e.message)
        return render_current_alert_page(broadcast_message, back_link_url=_get_back_link_from_view_broadcast_endpoint())

    if broadcast_message.status != "pending-approval":
        return redirect(
            url_for(
                ".view_current_broadcast",
                service_id=current_service.id,
                broadcast_message_id=broadcast_message.id,
            )
        )

    if form.validate_on_submit():
        try:
            broadcast_message.reject_broadcast_with_reason(rejection_reason)
            return redirect(
                url_for(
                    ".broadcast_dashboard",
                    service_id=current_service.id,
                )
            )
        except HTTPError as e:
            if e.status_code == 400:
                form.rejection_reason.errors = ["Enter the reason for rejecting the alert."]

    return render_current_alert_page(
        broadcast_message, form, back_link_url=_get_back_link_from_view_broadcast_endpoint()
    )


@main.route(
    "/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/return-for-edit", methods=["GET", "POST"]
)
@user_has_permissions("create_broadcasts", "approve_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def return_broadcast_for_edit(service_id, broadcast_message_id):
    """
    This route first checks that the form submitted is valid (i.e. that the return_for_edit_reason
    field passes its validation) and then checks that the alert can be moved into returned state.
    If both are successful, the alert is moved into draft state and the return_for_edit_reason is submitted.
    If there are any errors at any point, the page is re-rendered with those errors displayed.
    """
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )

    form = ReturnForEditForm()
    if form.validate_on_submit():
        try:
            broadcast_message.check_can_update_status("returned")
        except HTTPError as e:
            flash(e.message)
            return render_current_alert_page(
                broadcast_message, back_link_url=_get_back_link_from_view_broadcast_endpoint()
            )

        if broadcast_message.status != "pending-approval":
            return redirect(
                url_for(
                    ".view_current_broadcast",
                    service_id=current_service.id,
                    broadcast_message_id=broadcast_message.id,
                )
            )

        try:
            broadcast_message.return_broadcast_message_for_edit(return_for_edit_reason=form.return_for_edit_reason.data)
        except Exception as e:
            form.return_for_edit_reason.errors.append(e.message)

        broadcast_message = BroadcastMessage.from_id(
            broadcast_message_id,
            service_id=current_service.id,
        )
    return render_current_alert_page(
        broadcast_message, back_link_url=_get_back_link_from_view_broadcast_endpoint(), return_for_edit_form=form
    )


@main.route("/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/discard", methods=["GET", "POST"])
@user_has_permissions("create_broadcasts", "approve_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def discard_broadcast_message(service_id, broadcast_message_id):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )

    try:
        broadcast_message.check_can_update_status("rejected")
    except HTTPError as e:
        flash(e.message)
        return render_current_alert_page(broadcast_message, back_link_url=_get_back_link_from_view_broadcast_endpoint())

    if broadcast_message.status != "pending-approval":
        return redirect(
            url_for(
                ".view_current_broadcast",
                service_id=current_service.id,
                broadcast_message_id=broadcast_message.id,
            )
        )

    broadcast_message.reject_broadcast()

    return redirect(
        url_for(
            ".broadcast_dashboard",
            service_id=current_service.id,
        )
    )


@main.route(
    "/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/cancel",
    methods=["GET", "POST"],
)
@user_has_permissions("create_broadcasts", "approve_broadcasts", restrict_admin_usage=False)
@service_has_permission("broadcast")
def cancel_broadcast_message(service_id, broadcast_message_id):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )

    try:
        broadcast_message.check_can_update_status("cancelled")
    except HTTPError as e:
        flash(e.message)
        return render_current_alert_page(broadcast_message, hide_stop_link=True)

    if broadcast_message.status != "broadcasting":
        return redirect(
            url_for(
                ".view_current_broadcast",
                service_id=current_service.id,
                broadcast_message_id=broadcast_message.id,
            )
        )

    if request.method == "POST":
        broadcast_message.cancel_broadcast()
        return redirect(
            url_for(
                ".view_previous_broadcast",
                service_id=current_service.id,
                broadcast_message_id=broadcast_message.id,
            )
        )

    flash(["Are you sure you want to stop this broadcast now?"], "stop broadcasting")

    return render_current_alert_page(broadcast_message, hide_stop_link=True)


@main.route(
    "/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/versions",
    methods=["GET", "POST"],
)
@user_has_permissions(allow_org_user=True)
def view_broadcast_versions(service_id, broadcast_message_id):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )
    versions = broadcast_message.get_versions()
    for message in versions:
        message["template"] = BroadcastPreviewTemplate(
            {
                "template_type": BroadcastPreviewTemplate.template_type,
                "name": message.get("reference"),
                "content": message.get("content"),
            }
        )
        message["formatted_areas"] = message.get("areas")["names"] if message.get("areas") else []
    return render_template(
        "views/broadcast/choose_history.html",
        broadcast_message_id=broadcast_message_id,
        versions=versions,
        back_link=request.referrer
        or url_for(
            ".view_current_broadcast",
            service_id=current_service.id,
            broadcast_message_id=broadcast_message.id,
        ),
        is_edited=len(versions) > 1,
    )


@main.route("/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/geojson", methods=["GET"])
@user_has_permissions()
def get_broadcast_geojson(service_id, broadcast_message_id):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )

    areas: Collection[BaseBroadcastArea] = broadcast_message.areas

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

    return Response(
        json.dumps(geojson),
        mimetype="application/geo+json",
        headers={
            "Content-Disposition": f"attachment;filename={broadcast_message.reference}-{broadcast_message.id}.geojson"
        },
    )


@main.route("/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/xml/<xml_type>", methods=["GET"])
@user_has_permissions()
def get_broadcast_unsigned_xml(service_id, broadcast_message_id, xml_type):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )

    is_cap_format = True
    if xml_type == "ibag":
        is_cap_format = False

    areas: Collection[BaseBroadcastArea] = broadcast_message.areas

    event = {
        # In a signed CAP message the identifier refers to a BroadcastProviderMessage which is unique per MNO
        # We don't have such a thing here so we just use the overall BroadcastMessage
        "identifier": broadcast_message_id,
        "message_type": "alert",
        "message_format": "cap" if is_cap_format else "ibag",
        "message_number": "00000001",  # Only relevant for IBAG, and is made up here
        "headline": HEADLINE,
        "description": broadcast_message.content,
        "language": "en-GB" if is_cap_format else "English",
        "areas": [
            {
                # as_coordinate_pairs_lat_long returns an extra surrounding list.
                # We do not expect this to ever have multiple items in.
                # (API doesn't need to do this when generating events as it doesn't use the Polygon classes)
                "polygon": area.polygons.as_coordinate_pairs_lat_long[0],
            }
            for area in areas
        ],
        "channel": current_service.broadcast_channel,
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
                else datetime.now(timezone.utc) + timedelta(seconds=broadcast_message.broadcast_duration)
            )
        ),
    }

    cap_xml = generate_xml_body(event)

    return Response(
        cap_xml,
        mimetype="application/xml",
        headers={
            "Content-Disposition": f"attachment;filename={broadcast_message.reference}-{broadcast_message.id}"
            f".{xml_type}.xml"
        },
    )
