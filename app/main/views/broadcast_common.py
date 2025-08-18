from flask import redirect, request, url_for

from app import current_service
from app.broadcast_areas.models import CustomBroadcastAreas
from app.main import main
from app.main.views.broadcast import (
    choose_broadcast_area,
    choose_broadcast_library,
    choose_broadcast_sub_area,
    create_new_broadcast,
    preview_broadcast_areas,
    remove_broadcast_area,
    remove_custom_area_from_broadcast,
    search_coordinates_for_broadcast,
    search_postcodes_for_broadcast,
    update_broadcast,
)
from app.main.views.templates import (
    choose_template_area,
    choose_template_library,
    choose_template_sub_area,
    preview_template_areas,
    remove_custom_area_from_template,
    remove_template_area,
    search_coordinates_for_template,
    search_postcodes_for_template,
    write_new_broadcast_from_template,
)
from app.models.broadcast_message import BroadcastMessage
from app.models.template import Template
from app.utils import service_has_permission
from app.utils.broadcast import redirect_dependent_on_alert_area
from app.utils.user import user_has_permissions


@main.route("/services/<uuid:service_id>/write-new-broadcast", methods=["GET", "POST"])
@service_has_permission("broadcast")
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


@main.route("/services/<uuid:service_id>/new-broadcast/<uuid:template_id>")
@user_has_permissions("create_broadcasts", restrict_admin_usage=True)
@service_has_permission("broadcast")
def broadcast(service_id, template_id):
    template = Template.from_id(template_id=template_id, service_id=service_id)
    if template.reference and template.content:
        if template.areas:
            # As Template area already exists, created broadcast_message using this
            # and reference and content if they have been set also
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
            # Only reference and content have been set for Template,
            # so can only use these to create broadcast_message
            broadcast_message = BroadcastMessage.create_from_content(
                service_id=service_id, content=template.content, reference=template.reference
            )

        # If the current service is an operator service, user is redirected
        # straight to choose area as extra_content attribute shouldn't be set for
        # alerts created in operator services
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
        # ONLY Template area has been set, reference and content must be provided to
        # create broadcast_message so redirected to relevant page
        return redirect(
            url_for(
                ".write_new_broadcast",
                service_id=current_service.id,
                template_id=template.id,
            )
        )


@main.route(
    "/services/<uuid:service_id>/<message_type>/<uuid:message_id>/libraries",
    methods=["GET", "POST"],
)
@main.route(
    "/services/<uuid:service_id>/<message_type>/libraries",
    methods=["GET", "POST"],
)
@service_has_permission("broadcast")
def choose_library(service_id, message_type, message_id=None):
    template_folder_id = request.args.get("template_folder_id")
    if message_type == "broadcast":
        return choose_broadcast_library(service_id, message_id)
    elif message_type == "templates":
        return choose_template_library(service_id, message_id, template_folder_id=template_folder_id)


@main.route(
    "/services/<uuid:service_id>/<message_type>/<uuid:message_id>/libraries/<library_slug>",
    methods=["GET", "POST"],
)
@main.route(
    "/services/<uuid:service_id>/<message_type>/libraries/<library_slug>",
    methods=["GET", "POST"],
)
@service_has_permission("broadcast")
def choose_area(
    service_id,
    library_slug,
    message_type,
    message_id=None,
):
    template_folder_id = request.args.get("template_folder_id")
    if message_type == "broadcast":
        return choose_broadcast_area(service_id, library_slug, message_id)
    elif message_type == "templates":
        return choose_template_area(
            service_id, library_slug, template_id=message_id, template_folder_id=template_folder_id
        )


@main.route(
    "/services/<uuid:service_id>/<message_type>/<uuid:message_id>/libraries/<library_slug>/<area_slug>",  # noqa: E501
    methods=["GET", "POST"],
)
@service_has_permission("broadcast")
def choose_sub_area(service_id, message_type, library_slug, area_slug, message_id=None):
    template_folder_id = request.args.get("template_folder_id")
    if message_type == "broadcast":
        return choose_broadcast_sub_area(service_id, library_slug, area_slug, message_id)
    elif message_type == "templates":
        return choose_template_sub_area(service_id, library_slug, area_slug, message_id, template_folder_id)


@main.route("/services/<uuid:service_id>/<message_type>/<uuid:message_id>/areas")
@service_has_permission("broadcast")
def preview_areas(service_id, message_id, message_type):
    if message_type == "broadcast":
        return preview_broadcast_areas(service_id, message_id)
    elif message_type == "templates":
        return preview_template_areas(service_id, message_id)


@main.route(
    "/services/<uuid:service_id>/<message_type>/libraries/postcodes",
    methods=["GET", "POST"],
)
@main.route(
    "/services/<uuid:service_id>/<message_type>/<uuid:message_id>/libraries/postcodes",
    methods=["GET", "POST"],
)
@service_has_permission("broadcast")
def search_postcodes(service_id, message_type, message_id=None):
    template_folder_id = request.args.get("template_folder_id")
    if message_type == "broadcast":
        return search_postcodes_for_broadcast()
    elif message_type == "templates":
        return search_postcodes_for_template(service_id, message_id, template_folder_id)


@main.route(
    "/services/<uuid:service_id>/<message_type>/<uuid:message_id>/libraries/coordinates/<coordinate_type>/",  # noqa: E501
    methods=["GET", "POST"],
)
@main.route(
    "/services/<uuid:service_id>/<message_type>/libraries/coordinates/<coordinate_type>/",  # noqa: E501
    methods=["GET", "POST"],
)
@service_has_permission("broadcast")
def search_coordinates(service_id, coordinate_type, message_type, message_id=None):
    template_folder_id = request.args.get("template_folder_id")
    if message_type == "broadcast":
        return search_coordinates_for_broadcast(service_id, coordinate_type, message_id)
    elif message_type == "templates":
        return search_coordinates_for_template(service_id, coordinate_type, message_id, template_folder_id)


@main.route("/services/<uuid:service_id>/<message_type>/<uuid:message_id>/remove/<area_slug>")
@service_has_permission("broadcast")
def remove_area(service_id, message_id, area_slug, message_type):
    if message_type == "broadcast":
        return remove_broadcast_area(service_id, message_id, area_slug)
    elif message_type == "templates":
        return remove_template_area(service_id, message_id, area_slug)


@main.route("/services/<uuid:service_id>/<message_type>/<uuid:message_id>/remove/")
@service_has_permission("broadcast")
def remove_custom_area(service_id, message_id, message_type):
    if message_type == "broadcast":
        return remove_custom_area_from_broadcast(service_id, message_id)
    elif message_type == "templates":
        return remove_custom_area_from_template(service_id, message_id)
