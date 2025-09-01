from flask import redirect, render_template, request, url_for

from app.broadcast_areas.models import CustomBroadcastAreas
from app.main import main
from app.main.forms import BroadcastAreaForm, ChooseCoordinateTypeForm, SearchByNameForm
from app.main.views.broadcast import (
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
from app.utils.broadcast import _get_choose_library_back_link
from app.utils.user import user_has_any_permissions


def get_message_type(message_type):
    return {
        "broadcast": BroadcastMessage,
        "templates": Template,
    }[message_type]


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
    if message_id:
        message = Message.from_id_or_403(message_id, service_id=service_id)
        is_custom_broadcast = type(message.areas) is CustomBroadcastAreas
        if is_custom_broadcast:
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
    if library_slug == "coordinates":
        form = ChooseCoordinateTypeForm()
        if form.validate_on_submit():
            return redirect(
                url_for(
                    ".search_coordinates",
                    service_id=service_id,
                    message_id=message_id,
                    library_slug="coordinates",
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
        return redirect(
            url_for(
                ".search_postcodes",
                service_id=service_id,
                broadcast_message_id=message_id,
                library_slug="postcodes",
                message_type=message_type,
                template_folder_id=template_folder_id,
            )
        )

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
    if message_type == "broadcast":
        return choose_broadcast_sub_area(service_id, library_slug, area_slug, message_id)
    elif message_type == "templates":
        return choose_template_sub_area(service_id, library_slug, area_slug, message_id, template_folder_id)


@main.route("/services/<uuid:service_id>/<message_type>/<uuid:message_id>/areas")
@service_has_permission("broadcast")
@user_has_any_permissions(["create_broadcasts", "manage_templates"], restrict_admin_usage=True)
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
@user_has_any_permissions(["create_broadcasts", "manage_templates"], restrict_admin_usage=True)
def search_postcodes(service_id, message_type, message_id=None):
    template_folder_id = request.args.get("template_folder_id")
    if message_type == "broadcast":
        return search_postcodes_for_broadcast(service_id, message_id)
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
@user_has_any_permissions(["create_broadcasts", "manage_templates"], restrict_admin_usage=True)
def search_coordinates(service_id, coordinate_type, message_type, message_id=None):
    template_folder_id = request.args.get("template_folder_id")
    if message_type == "broadcast":
        return search_coordinates_for_broadcast(service_id, coordinate_type, message_id)
    elif message_type == "templates":
        return search_coordinates_for_template(service_id, coordinate_type, message_id, template_folder_id)


@main.route("/services/<uuid:service_id>/<message_type>/<uuid:message_id>/remove/<area_slug>")
@service_has_permission("broadcast")
@user_has_any_permissions(["create_broadcasts", "manage_templates"], restrict_admin_usage=True)
def remove_area(service_id, message_id, area_slug, message_type):
    if message_type == "broadcast":
        return remove_broadcast_area(service_id, message_id, area_slug)
    elif message_type == "templates":
        return remove_template_area(service_id, message_id, area_slug)


@main.route("/services/<uuid:service_id>/<message_type>/<uuid:message_id>/remove/")
@service_has_permission("broadcast")
@user_has_any_permissions(["create_broadcasts", "manage_templates"], restrict_admin_usage=True)
def remove_custom_area(service_id, message_id, message_type):
    if message_type == "broadcast":
        return remove_custom_area_from_broadcast(service_id, message_id)
    elif message_type == "templates":
        return remove_custom_area_from_template(service_id, message_id)
