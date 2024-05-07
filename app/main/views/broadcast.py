from flask import abort, flash, jsonify, redirect, render_template, request, url_for

from app import current_service
from app.broadcast_areas.models import CustomBroadcastAreas
from app.main import main
from app.main.forms import (
    BroadcastAreaForm,
    BroadcastAreaFormWithSelectAll,
    BroadcastTemplateForm,
    CartesianCoordinatesForm,
    ChooseCoordinateTypeForm,
    ConfirmBroadcastForm,
    DecimalCoordinatesForm,
    NewBroadcastForm,
    PostcodeForm,
    SearchByNameForm,
)
from app.models.broadcast_message import BroadcastMessage, BroadcastMessages
from app.utils import service_has_permission
from app.utils.broadcast import (
    all_fields_empty,
    check_coordinates_valid_for_enclosed_polygons,
    create_coordinate_area,
    create_coordinate_area_id,
    create_custom_area_polygon,
    create_postcode_area_id,
    create_postcode_db_id,
    extract_attributes_from_custom_area,
    get_centroid,
    normalising_point,
    parse_coordinate_form_data,
    postcode_in_db,
    preview_button_clicked,
    render_postcode_page,
    valid_postcode_and_radius_entered,
    valid_postcode_entered,
)
from app.utils.user import user_has_permissions


def _get_back_link_from_view_broadcast_endpoint():
    return {
        "main.view_current_broadcast": ".broadcast_dashboard",
        "main.view_previous_broadcast": ".broadcast_dashboard_previous",
        "main.view_rejected_broadcast": ".broadcast_dashboard_rejected",
        "main.approve_broadcast_message": ".broadcast_dashboard",
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
            broadcasts=broadcast_messages.with_status("pending-approval", "broadcasting"),
            empty_message="You do not have any current alerts",
            view_broadcast_endpoint=".view_current_broadcast",
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


@main.route("/services/<uuid:service_id>/write-new-broadcast", methods=["GET", "POST"])
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def write_new_broadcast(service_id):
    form = BroadcastTemplateForm()

    broadcast_message_id = request.args.get("broadcast_message_id")
    broadcast_message = None

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
                ".choose_broadcast_library",
                service_id=current_service.id,
                broadcast_message_id=broadcast_message_id,
            )
        )

    if broadcast_message_id:
        broadcast_message = BroadcastMessage.from_id(
            broadcast_message_id,
            service_id=current_service.id,
        )
        if broadcast_message.status == "draft":
            form.template_content.data = broadcast_message.content
            form.name.data = broadcast_message.reference
        else:
            broadcast_message = None

    return render_template(
        "views/broadcast/write-new-broadcast.html",
        broadcast_message=broadcast_message,
        form=form,
    )


@main.route("/services/<uuid:service_id>/new-broadcast/<uuid:template_id>")
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def broadcast(service_id, template_id):
    return redirect(
        url_for(
            ".choose_broadcast_library",
            service_id=current_service.id,
            broadcast_message_id=BroadcastMessage.create(
                service_id=service_id,
                template_id=template_id,
            ).id,
        )
    )


# @main.route("/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/duration", methods=["GET", "POST"])
# @user_has_permissions("create_broadcasts", restrict_admin_usage=True)
# @service_has_permission("broadcast")
# def choose_broadcast_duration(service_id, broadcast_message_id):
#     form = ChooseDurationForm()

#     broadcast_message = BroadcastMessage.from_id(
#         broadcast_message_id,
#         service_id=current_service.id,
#     )

#     back_link = url_for(
#         ".preview_broadcast_areas", service_id=current_service.id, broadcast_message_id=broadcast_message_id
#     )

#     if form.validate_on_submit():
#         BroadcastMessage.update_duration(
#             service_id=current_service.id,
#             broadcast_message_id=broadcast_message_id,
#             duration=form.content.data,
#         )
#         return redirect(
#             url_for(
#                 ".preview_broadcast_message", service_id=current_service.id, broadcast_message_id=broadcast_message.id
#             )
#         )

#     return render_template("views/broadcast/duration.html", form=form, back_link=back_link)


@main.route("/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/areas")
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def preview_broadcast_areas(service_id, broadcast_message_id):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )
    if broadcast_message.template_id:
        back_link = url_for(
            ".view_template",
            service_id=current_service.id,
            template_id=broadcast_message.template_id,
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
            page_title="Choose coordinates type",
            form=form,
            back_link=url_for(
                ".choose_broadcast_library", service_id=service_id, broadcast_message_id=broadcast_message_id
            ),
        )
    elif library_slug == "postcodes":
        form = PostcodeForm()
        centroid, bleed, estimated_area, estimated_area_with_bleed, count_of_phones, count_of_phones_likely = (
            None,
            None,
            None,
            None,
            None,
            None,
        )

        if all_fields_empty(request, form):
            form.validate_on_submit()
        elif valid_postcode_entered(request, form):
            broadcast_message.clear_areas()
            postcode = create_postcode_db_id(form)
            try:
                area = BroadcastMessage.libraries.get_areas([postcode])[0]
                centroid = get_centroid(area)
            except IndexError:
                form.postcode.errors.append("Postcode not found. Enter a valid postcode.")
        elif valid_postcode_and_radius_entered(request, form):
            centroid, circle_polygon = create_custom_area_polygon(broadcast_message, form)
            if postcode_in_db(form):
                (
                    bleed,
                    estimated_area,
                    estimated_area_with_bleed,
                    count_of_phones,
                    count_of_phones_likely,
                ) = extract_attributes_from_custom_area(circle_polygon)
                id = create_postcode_area_id(form)
                if preview_button_clicked(request):
                    broadcast_message.add_custom_areas(circle_polygon, id=id)
                    return redirect(
                        url_for(
                            ".preview_broadcast_message",
                            service_id=current_service.id,
                            broadcast_message_id=broadcast_message.id,
                        )
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
        broadcast_message.add_areas(*form.areas.data)
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
            ".choose_broadcast_area",
            service_id=current_service.id,
            broadcast_message_id=broadcast_message_id,
            library_slug="postcodes",
        )
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
        show_error,
    ) = (
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        False,
    )
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )
    if coordinate_type == "decimal":
        form = DecimalCoordinatesForm()
    elif coordinate_type == "cartesian":
        form = CartesianCoordinatesForm()

    if (
        request.method == "POST"
        and form.data["radius"] is None
        and (form.data["first_coordinate"] is None or form.data["second_coordinate"] is None)
    ):
        form.validate_on_submit()
    elif request.method == "POST" and form.data["radius"] is None and form.pre_validate(form):
        first_coordinate = float(form.data["first_coordinate"])
        second_coordinate = float(form.data["second_coordinate"])
        in_enclosed_polygons = check_coordinates_valid_for_enclosed_polygons(
            broadcast_message,
            first_coordinate,
            second_coordinate,
            coordinate_type,
        )
        broadcast_message.clear_areas()
        if not in_enclosed_polygons:  # if coordinate not in either UK or test area
            form.form_errors.append("Invalid coordinates.")
            show_error = True
        else:  # if in either test area or UK, plot the marker
            Point = normalising_point(first_coordinate, second_coordinate, coordinate_type)
            marker = [Point.y, Point.x]
    elif request.method == "POST" and form.data["radius"] is not None and form.validate_on_submit():
        first_coordinate, second_coordinate, radius = parse_coordinate_form_data(form)
        if in_enclosed_polygons := check_coordinates_valid_for_enclosed_polygons(
            broadcast_message,
            first_coordinate,
            second_coordinate,
            coordinate_type,
        ):
            if polygon := create_coordinate_area(
                first_coordinate,
                second_coordinate,
                radius,
                coordinate_type,
            ):
                form.form_errors = []
                id = create_coordinate_area_id(coordinate_type, first_coordinate, second_coordinate, radius)
                (
                    bleed,
                    estimated_area,
                    estimated_area_with_bleed,
                    count_of_phones,
                    count_of_phones_likely,
                ) = extract_attributes_from_custom_area(polygon)

        else:
            form.form_errors.append("Invalid coordinates.")
            show_error = True
            broadcast_message.clear_areas()
        if request.form.get("preview"):
            broadcast_message.add_custom_areas(polygon, id=id)
            return redirect(
                url_for(
                    ".preview_broadcast_message",
                    service_id=current_service.id,
                    broadcast_message_id=broadcast_message.id,
                )
            )
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
        show_error=show_error,
        coordinate_type=coordinate_type,
        marker=marker,
        bleed=bleed,
        estimated_area=estimated_area,
        estimated_area_with_bleed=estimated_area_with_bleed,
        count_of_phones=count_of_phones,
        count_of_phones_likely=count_of_phones_likely,
        centroid=marker,
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
        broadcast_message.add_areas(*form.selected_areas)
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
    BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    ).remove_area(area_slug)
    return redirect(
        url_for(
            ".preview_broadcast_areas",
            service_id=current_service.id,
            broadcast_message_id=broadcast_message_id,
        )
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
    if request.method == "POST":
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
    if broadcast_message.status == "draft":
        abort(404)

    for statuses, endpoint in (
        ({"completed", "cancelled"}, "main.view_previous_broadcast"),
        ({"broadcasting", "pending-approval"}, "main.view_current_broadcast"),
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

    return render_template(
        "views/broadcast/view-message.html",
        broadcast_message=broadcast_message,
        back_link=url_for(
            _get_back_link_from_view_broadcast_endpoint(),
            service_id=current_service.id,
        ),
        form=ConfirmBroadcastForm(
            service_is_live=current_service.live,
            channel=current_service.broadcast_channel,
            max_phones=broadcast_message.count_of_phones_likely,
        ),
        is_custom_broadcast=type(broadcast_message.areas) is CustomBroadcastAreas,
    )


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
        return render_template(
            "views/broadcast/view-message.html",
            broadcast_message=broadcast_message,
            back_link=url_for(
                _get_back_link_from_view_broadcast_endpoint(),
                service_id=current_service.id,
            ),
            form=form,
            is_custom_broadcast=type(broadcast_message.areas) is CustomBroadcastAreas,
        )

    return redirect(
        url_for(
            ".view_current_broadcast",
            service_id=current_service.id,
            broadcast_message_id=broadcast_message.id,
        )
    )


@main.route("/services/<uuid:service_id>/broadcast/<uuid:broadcast_message_id>/reject")
@user_has_permissions("create_broadcasts", "approve_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def reject_broadcast_message(service_id, broadcast_message_id):
    broadcast_message = BroadcastMessage.from_id(
        broadcast_message_id,
        service_id=current_service.id,
    )

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

    return render_template(
        "views/broadcast/view-message.html",
        broadcast_message=broadcast_message,
        hide_stop_link=True,
        is_custom_broadcast=type(broadcast_message.areas) is CustomBroadcastAreas,
    )
