from functools import partial

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from notifications_python_client.errors import HTTPError

from app import (
    current_service,
    service_api_client,
    template_api_client,
    template_folder_api_client,
)
from app.broadcast_areas.models import CustomBroadcastAreas
from app.formatters import character_count
from app.main import main
from app.main.forms import (
    BroadcastTemplateForm,
    ChooseTemplateFieldsForm,
    PostcodeForm,
    SearchTemplatesForm,
    TemplateAndFoldersSelectionForm,
    TemplateFolderForm,
)
from app.models.broadcast_message import BroadcastMessage
from app.models.service import Service
from app.models.template import Template
from app.models.template_list import TemplateList, UserTemplateList, UserTemplateLists
from app.utils import BROADCAST_TYPE
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
    render_coordinates_page,
    render_postcode_page,
    select_coordinate_form,
    validate_form_based_on_fields_entered,
)
from app.utils.templates import get_template
from app.utils.user import user_has_permissions

form_objects = {
    "broadcast": BroadcastTemplateForm,
}


@main.route("/services/<uuid:service_id>/templates/<uuid:template_id>")
@user_has_permissions(allow_org_user=True)
def view_template(service_id, template_id):
    template = Template.from_id(template_id=template_id, service_id=service_id)
    template_folder = current_service.get_template_folder(template.folder)

    user_has_template_permission = current_user.has_template_folder_permission(template_folder)

    return render_template(
        "views/templates/template.html",
        formatted_template=get_template(template.reference, template.content),  # returns BroadcastPreviewTemplate
        user_has_template_permission=user_has_template_permission,
        template=template,
        message=template,
        template_folder_path=current_service.get_template_folder_path(template.folder),
    )


@main.route("/services/<uuid:service_id>/templates/all", methods=["GET", "POST"])
@main.route("/services/<uuid:service_id>/templates", methods=["GET", "POST"])
@main.route("/services/<uuid:service_id>/templates/folders/<uuid:template_folder_id>", methods=["GET", "POST"])
@main.route("/services/<uuid:service_id>/templates/<template_type:template_type>", methods=["GET", "POST"])
@main.route("/services/<uuid:service_id>/templates/all/folders/<uuid:template_folder_id>", methods=["GET", "POST"])
@main.route(
    "/services/<uuid:service_id>/templates/<template_type:template_type>/folders/<uuid:template_folder_id>",
    methods=["GET", "POST"],
)
@user_has_permissions(allow_org_user=True)
def choose_template(service_id, template_type="all", template_folder_id=None):
    template_folder = current_service.get_template_folder(template_folder_id)
    user_has_template_folder_permission = current_user.has_template_folder_permission(template_folder)

    template_list = UserTemplateList(
        service=current_service, template_type=template_type, template_folder_id=template_folder_id, user=current_user
    )

    all_template_folders = UserTemplateList(service=current_service, user=current_user).all_template_folders

    templates_and_folders_form = TemplateAndFoldersSelectionForm(
        all_template_folders=all_template_folders,
        template_list=template_list,
        template_type=template_type,
        available_template_types=current_service.available_template_types,
        allow_adding_copy_of_template=(current_service.all_templates or len(current_user.service_ids) > 1),
    )
    option_hints = {template_folder_id: "current folder"}

    single_notification_channel = BROADCAST_TYPE

    if request.method == "POST" and templates_and_folders_form.validate_on_submit():
        if not current_user.has_permissions("manage_templates"):
            abort(403)
        try:
            return process_folder_management_form(templates_and_folders_form, template_folder_id)
        except HTTPError as e:
            flash(e.message)
    elif templates_and_folders_form.trying_to_add_unavailable_template_type:
        return redirect(
            url_for(
                ".action_blocked",
                service_id=current_service.id,
                notification_type=templates_and_folders_form.add_template_by_template_type.data,
                return_to="add_new_template",
            )
        )

    if "templates_and_folders" in templates_and_folders_form.errors:
        flash("Select at least one template or folder")

    initial_state = request.args.get("initial_state")
    if request.method == "GET" and initial_state:
        templates_and_folders_form.op = initial_state

    service = Service(service_api_client.get_service(service_id)["data"])

    return render_template(
        "views/templates/choose.html",
        current_template_folder_id=template_folder_id,
        template_folder_path=service.get_template_folder_path(template_folder_id),
        template_list=template_list,
        show_search_box=current_service.count_of_templates_and_folders > 7,
        template_nav_items=get_template_nav_items(template_folder_id),
        template_type=template_type,
        search_form=SearchTemplatesForm(current_service.api_keys),
        templates_and_folders_form=templates_and_folders_form,
        move_to_children=templates_and_folders_form.move_to.children(),
        user_has_template_folder_permission=user_has_template_folder_permission,
        single_notification_channel=single_notification_channel,
        option_hints=option_hints,
    )


def process_folder_management_form(form, current_folder_id):
    current_service.get_template_folder_with_user_permission_or_403(current_folder_id, current_user)
    new_folder_id = None

    if form.is_add_template_op:
        return _add_template_by_type(
            form.add_template_by_template_type.data,
            current_folder_id,
        )

    if form.is_add_folder_op:
        new_folder_id = template_folder_api_client.create_template_folder(
            current_service.id, name=form.get_folder_name(), parent_id=current_folder_id
        )

    if form.is_move_op:
        # if we've just made a folder, we also want to move there
        move_to_id = new_folder_id or form.move_to.data

        current_service.move_to_folder(ids_to_move=form.templates_and_folders.data, move_to=move_to_id)

    return redirect(request.url)


def get_template_nav_label(value):
    return {
        "broadcast": "Broadcast",
    }[value]


def get_template_nav_items(template_folder_id):
    return [
        (
            get_template_nav_label("broadcast"),
            "broadcast",
            url_for(
                ".choose_template",
                service_id=current_service.id,
                template_type="broadcast",
                template_folder_id=template_folder_id,
            ),
            "",
        )
    ]


def _view_template_version(service_id, template_id, version):
    version = Template.from_id(template_id, service_id=service_id).get_template_version(
        service_id=service_id, version=version
    )
    return version


@main.route("/services/<uuid:service_id>/templates/<uuid:template_id>/version/<int:version>")
@user_has_permissions(allow_org_user=True)
def view_template_version(service_id, template_id, version):
    template_version = _view_template_version(service_id=service_id, template_id=template_id, version=version)
    return render_template(
        "views/templates/template_history.html",
        formatted_template=get_template(
            template_version.get("reference"),
            template_version.get("content"),
        ),
        template=template_version,
    )


def _add_template_by_type(template_type, template_folder_id):
    if template_type == "copy-existing":
        return redirect(
            url_for(
                ".choose_template_to_copy",
                service_id=current_service.id,
            )
        )

    return redirect(
        url_for(
            ".add_service_template",
            service_id=current_service.id,
            template_type=template_type,
            template_folder_id=template_folder_id,
        )
    )


@main.route("/services/<uuid:service_id>/templates/copy")
@main.route("/services/<uuid:service_id>/templates/copy/from-folder/<uuid:from_folder>")
@main.route("/services/<uuid:service_id>/templates/copy/from-service/<uuid:from_service>")
@main.route(
    "/services/<uuid:service_id>/templates/copy/from-service/<uuid:from_service>/from-folder/<uuid:from_folder>"
)
@user_has_permissions("manage_templates")
def choose_template_to_copy(
    service_id,
    from_service=None,
    from_folder=None,
):
    if from_service:
        current_user.belongs_to_service_or_403(from_service)
        service = Service(service_api_client.get_service(from_service)["data"])

        return render_template(
            "views/templates/copy.html",
            services_templates_and_folders=UserTemplateList(
                service=service, template_folder_id=from_folder, user=current_user
            ),
            template_folder_path=service.get_template_folder_path(from_folder),
            from_service=service,
            search_form=SearchTemplatesForm(current_service.api_keys),
        )

    else:
        return render_template(
            "views/templates/copy.html",
            services_templates_and_folders=UserTemplateLists(current_user),
            search_form=SearchTemplatesForm(current_service.api_keys),
        )


@main.route("/services/<uuid:service_id>/templates/copy/<uuid:template_id>", methods=["GET", "POST"])
@user_has_permissions("manage_templates")
def copy_template(service_id, template_id):
    from_service = request.args.get("from_service")

    current_user.belongs_to_service_or_403(from_service)

    template = Template.get_template(from_service, template_id)["data"]

    template_folder = template_folder_api_client.get_template_folder(from_service, template["folder"])
    if not current_user.has_template_folder_permission(template_folder):
        abort(403)

    if request.method == "POST":
        return add_service_template(service_id, template["template_type"])

    template["reference"] = _get_template_copy_name(template, current_service.all_templates)
    form = form_objects[template["template_type"]](**template)

    if template["folder"]:
        back_link = url_for(
            ".choose_template_to_copy",
            service_id=current_service.id,
            from_service=from_service,
            from_folder=template["folder"],
        )
    else:
        back_link = url_for(
            ".choose_template_to_copy",
            service_id=current_service.id,
            from_service=from_service,
        )

    return render_template(
        "views/edit-{}-template.html".format(template["template_type"]),
        form=form,
        template=template,
        heading_action="Add",
        services=current_user.service_ids,
        back_link=back_link,
    )


def _get_template_copy_name(template, existing_templates):
    template_names = [existing["reference"] for existing in existing_templates]

    for index in reversed(range(1, 10)):
        if "{} (copy {})".format(template["reference"], index) in template_names:
            return "{} (copy {})".format(template["reference"], index + 1)

    if "{} (copy)".format(template["reference"]) in template_names:
        return "{} (copy 2)".format(template["reference"])

    return "{} (copy)".format(template["reference"])


@main.route(("/services/<uuid:service_id>/templates/action-blocked/" "<template_type:notification_type>/<return_to>"))
@main.route(
    (
        "/services/<uuid:service_id>/templates/action-blocked/"
        "<template_type:notification_type>/<return_to>/<uuid:template_id>"
    )
)
@user_has_permissions("manage_templates")
def action_blocked(service_id, notification_type, return_to, template_id=None):
    back_link = {
        "add_new_template": partial(url_for, ".choose_template", service_id=current_service.id),
        "templates": partial(url_for, ".choose_template", service_id=current_service.id),
        "view_template": partial(url_for, ".view_template", service_id=current_service.id, template_id=template_id),
    }.get(return_to)

    return (
        render_template(
            "views/templates/action_blocked.html",
            service_id=service_id,
            notification_type=notification_type,
            back_link=back_link(),
        ),
        403,
    )


@main.route("/services/<uuid:service_id>/templates/folders/<uuid:template_folder_id>/manage", methods=["GET", "POST"])
@user_has_permissions("manage_templates")
def manage_template_folder(service_id, template_folder_id):
    template_folder = current_service.get_template_folder_with_user_permission_or_403(template_folder_id, current_user)
    form = TemplateFolderForm(
        name=template_folder["name"],
        users_with_permission=template_folder.get("users_with_permission", None),
        all_service_users=[user for user in current_service.active_users if user.id != current_user.id],
    )
    if form.validate_on_submit():
        if current_user.has_permissions("manage_service") and form.users_with_permission.all_service_users:
            users_with_permission = form.users_with_permission.data + [current_user.id]
        else:
            users_with_permission = None
        template_folder_api_client.update_template_folder(
            current_service.id, template_folder_id, name=form.name.data, users_with_permission=users_with_permission
        )
        return redirect(url_for(".choose_template", service_id=service_id, template_folder_id=template_folder_id))

    service = Service(service_api_client.get_service(service_id)["data"])
    return render_template(
        "views/templates/manage-template-folder.html",
        form=form,
        template_folder_path=service.get_template_folder_path(template_folder_id),
        current_service_id=current_service.id,
        template_folder_id=template_folder_id,
        template_type="all",
    )


@main.route("/services/<uuid:service_id>/templates/folders/<uuid:template_folder_id>/delete", methods=["GET", "POST"])
@user_has_permissions("manage_templates")
def delete_template_folder(service_id, template_folder_id):
    template_folder = current_service.get_template_folder_with_user_permission_or_403(template_folder_id, current_user)
    template_list = TemplateList(service=current_service, template_folder_id=template_folder_id)

    if not template_list.folder_is_empty:
        flash("You must empty this folder before you can delete it", "info")
        return redirect(
            url_for(
                ".choose_template", service_id=service_id, template_type="all", template_folder_id=template_folder_id
            )
        )

    if request.method == "POST":
        try:
            template_folder_api_client.delete_template_folder(current_service.id, template_folder_id)

            return redirect(
                url_for(".choose_template", service_id=service_id, template_folder_id=template_folder["parent_id"])
            )
        except HTTPError as e:
            msg = "Folder is not empty"
            if e.status_code == 400 and msg in e.message:
                flash("You must empty this folder before you can delete it", "info")
                return redirect(
                    url_for(
                        ".choose_template",
                        service_id=service_id,
                        template_type="all",
                        template_folder_id=template_folder_id,
                    )
                )
            else:
                abort(500, e)
    else:
        flash("Are you sure you want to delete the ‘{}’ folder?".format(template_folder["name"]), "delete")
        return manage_template_folder(service_id, template_folder_id)


@main.route(
    "/services/<uuid:service_id>/templates/add-<template_type:template_type>",
    methods=["GET", "POST"],
)
@main.route(
    """/services/<uuid:service_id>/templates/folders/<uuid:template_folder_id>
    /add-<template_type:template_type>""",
    methods=["GET", "POST"],
)
@main.route(
    """/services/<uuid:service_id>/templates/folders/<uuid:template_folder_id>
    /add-<template_type:template_type>""",
    methods=["GET", "POST"],
)
@user_has_permissions("manage_templates")
def add_service_template(service_id, template_type, template_folder_id=None):
    adding_area = request.args.get("adding_area")
    if template_type not in current_service.available_template_types:
        return redirect(
            url_for(
                ".action_blocked",
                service_id=service_id,
                notification_type=template_type,
                template_folder_id=template_folder_id,
                return_to="templates",
            )
        )

    form = form_objects[template_type]()
    if form.validate_on_submit():
        try:
            new_template = Template.create(
                service_id=service_id,
                reference=form.reference.data,
                content=form.content.data,
                template_folder_id=template_folder_id,
            )
        except HTTPError as e:
            if (
                e.status_code == 400
                and "content" in e.message
                and any(["character count greater than" in x for x in e.message["content"]])
            ):
                form.content.errors.extend(e.message["content"])
            else:
                raise e
        else:
            return (
                redirect(
                    url_for(
                        ".choose_library",
                        service_id=service_id,
                        message_type="templates",
                        message_id=new_template.id,
                        template_folder_id=template_folder_id,
                    )
                )
                if adding_area == "True"
                else redirect(url_for(".view_template", service_id=service_id, template_id=new_template.id))
            )

    return render_template(
        f"views/edit-{template_type}-template.html",
        form=form,
        template_type=template_type,
        template_folder_id=template_folder_id,
        heading_action="New",
        back_link=url_for(
            "main.choose_template",
            service_id=current_service.id,
            template_folder_id=template_folder_id,
        ),
    )


def abort_403_if_not_admin_user():
    if not current_user.platform_admin:
        abort(403)


@main.route("/services/<uuid:service_id>/templates/<uuid:template_id>/edit", methods=["GET", "POST"])
@user_has_permissions("manage_templates")
def edit_service_template(service_id, template_id):
    template = current_service.get_template_with_user_permission_or_403(template_id, current_user)
    template_data = {"content": template.content, "reference": template.reference}
    form = form_objects[template.template_type](**template_data)
    if form.validate_on_submit():
        new_template_data = {
            "reference": form.reference.data,
            "content": form.content.data,
            "template_type": template.template_type,
            "id": template.id,
        }

        new_template = get_template(new_template_data["reference"], new_template_data["content"])
        template_change = get_template(template_data["reference"], template_data["content"]).compare_to(new_template)

        if template_change.placeholders_added and not request.form.get("confirm") and current_service.api_keys:
            return render_template(
                "views/templates/breaking-change.html",
                template_change=template_change,
                new_template=new_template,
                form=form,
            )
        try:
            template.update_from_content(
                service_id=current_service.id,
                template_id=template.id,
                content=form.content.data,
                reference=form.reference.data,
            )
        except HTTPError as e:
            if e.status_code == 400:
                if "content" in e.message and any(["character count greater than" in x for x in e.message["content"]]):
                    form.content.errors.extend(e.message["content"])
                else:
                    raise e
            else:
                raise e
        else:
            return redirect(url_for(".view_template", service_id=service_id, template_id=template_id))

    if template.template_type not in current_service.available_template_types:
        return redirect(
            url_for(
                ".action_blocked",
                service_id=service_id,
                notification_type=template.template_type,
                return_to="view_template",
                template_id=template_id,
            )
        )
    else:
        service = Service(service_api_client.get_service(service_id)["data"])
        return render_template(
            "views/edit-{}-template.html".format(template.template_type),
            form=form,
            template=template,
            back_link=url_for("main.view_template", service_id=current_service.id, template_id=template.id),
            template_folder_path=service.get_template_folder_path(template.folder),
        )


@main.route(
    "/services/<uuid:service_id>/templates/count-<template_type:template_type>-<field>-length",
    methods=["POST"],
)
@user_has_permissions()
def count_content_length(service_id, template_type, field):
    if template_type != "broadcast":
        abort(404)

    error, message = _get_content_count_error_and_message_for_template(
        get_template(
            content=request.form.get(str(field), ""),
        )
    )

    return jsonify(
        {
            "html": render_template(
                "partials/templates/content-count-message.html",
                error=error,
                message=message,
            )
        }
    )


def _get_content_count_error_and_message_for_template(template):
    if template.template_type == "broadcast":
        if template.content_too_long:
            return True, (
                f"You have "
                f"{character_count(template.encoded_content_count - template.max_content_count)} "
                f"too many"
            )
        else:
            return False, (
                f"You have "
                f"{character_count(template.max_content_count - template.encoded_content_count)} "
                f"remaining"
            )


@main.route("/services/<uuid:service_id>/templates/<uuid:template_id>/delete", methods=["GET", "POST"])
@user_has_permissions("manage_templates")
def delete_service_template(service_id, template_id):
    template = current_service.get_template_with_user_permission_or_403(template_id, current_user)

    if request.method == "POST":
        template_api_client.delete_template(service_id, template_id)
        return redirect(
            url_for(
                ".choose_template",
                service_id=service_id,
                template_folder_id=template.folder,
            )
        )

    if template.reference:
        flash(
            f"Are you sure you want to delete ‘{template.reference}’?",
            "delete",
        )
    else:
        flash("Are you sure you want to delete this template?", "delete")

    return render_template(
        "views/templates/template.html",
        formatted_template=get_template(template.reference, template.content),
        user_has_template_permission=True,
        template=template,
        message=template,
        template_folder_path=current_service.get_template_folder_path(template.folder),
    )


@main.route("/services/<uuid:service_id>/templates/<uuid:template_id>/redact", methods=["GET"])
@user_has_permissions("manage_templates")
def confirm_redact_template(service_id, template_id):
    template = current_service.get_template_with_user_permission_or_403(template_id, current_user)

    return render_template(
        "views/templates/template.html",
        template=get_template(
            template.reference,
            template.content,
        ),
        user_has_template_permission=True,
        show_redaction_message=True,
        template_folder_path=current_service.get_template_folder_path(template.folder),
    )


@main.route("/services/<uuid:service_id>/templates/<uuid:template_id>/redact", methods=["POST"])
@user_has_permissions("manage_templates")
def redact_template(service_id, template_id):
    service_api_client.redact_service_template(service_id, template_id)

    flash("Personalised content will be hidden for messages sent with this template", "default_with_tick")

    return redirect(
        url_for(
            ".view_template",
            service_id=service_id,
            template_id=template_id,
        )
    )


@main.route("/services/<uuid:service_id>/templates/<uuid:template_id>/versions")
@user_has_permissions(allow_org_user=True)
def view_template_versions(service_id, template_id):
    template = Template.from_id(template_id=template_id, service_id=service_id)
    return render_template(
        "views/templates/choose_history.html",
        versions=[
            (
                get_template(
                    template_version.get("reference"),
                    template_version.get("content"),
                ),
                template_version,
            )
            for template_version in template.get_template_versions(service_id=service_id)
        ],
    )


@main.route(
    "/services/<uuid:service_id>/templates/folders/<uuid:template_folder_id>/choose-template-fields",
    methods=["GET", "POST"],
)
@main.route(
    "/services/<uuid:service_id>/templates/choose-template-fields",
    methods=["GET", "POST"],
)
@user_has_permissions("manage_templates")
def choose_template_fields(service_id, template_folder_id=None):
    form = ChooseTemplateFieldsForm()
    if form.validate_on_submit():
        template_fields = form.content.data
        if template_fields == "content_and_area":
            return redirect(
                url_for(
                    ".add_service_template",
                    service_id=service_id,
                    template_type="broadcast",
                    template_folder_id=template_folder_id,
                    adding_area=True,
                )
            )
        elif template_fields == "content_only":
            return redirect(
                url_for(
                    ".add_service_template",
                    service_id=service_id,
                    template_type="broadcast",
                    template_folder_id=template_folder_id,
                )
            )
        elif template_fields == "area_only":
            return redirect(
                url_for(
                    ".choose_library",
                    service_id=current_service.id,
                    message_type="templates",
                    template_folder_id=template_folder_id,
                )
            )
    return render_template(
        "views/templates/_choose_template_fields.html",
        form=form,
        back_link=url_for("main.choose_template", service_id=current_service.id, template_folder_id=template_folder_id),
        page_title="Choose how to populate template",
    )


@user_has_permissions("manage_templates")
def write_new_broadcast_from_template(service_id, template_id):
    template = Template.from_id(template_id, service_id=current_service.id) if template_id else None
    message = None

    form = BroadcastTemplateForm()

    if form.validate_on_submit():
        if template_id and template and template.areas:
            # If Template has already been made and has areas, create broadcast_message
            #  from anything existing in Template
            if isinstance(template.areas, CustomBroadcastAreas):
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

        return redirect(
            # Redirects to 'Choose library' page if created in operator service,
            # as you cannot add extra_content in operator service, otherwise redirects
            # to page to add extra_content
            url_for(
                ".choose_extra_content" if current_service.broadcast_channel != "operator" else ".choose_library",
                service_id=current_service.id,
                broadcast_message_id=message.id,
            )
        )

    return render_template(
        "views/broadcast/write-new-broadcast.html",
        broadcast_message=message,
        form=form,
    )


@user_has_permissions("manage_templates")
def preview_template_areas(service_id, template_id):
    template = Template.from_id(template_id, service_id=service_id)
    return render_template(
        "views/broadcast/preview-areas.html",
        message=template,
        back_link=request.referrer,
        is_custom_broadcast=type(template.areas) is CustomBroadcastAreas,
        redirect_url=url_for(
            ".view_template", service_id=current_service.id, template_id=template.id
        ),  # The url for when 'Save and continue' button clicked
        message_type="templates",
    )


@user_has_permissions("manage_templates")
def search_postcodes_for_template(service_id, template_id=None, template_folder_id=None):
    template = Template.from_id(template_id, service_id=service_id) if template_id else None
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
                if template:
                    template.add_custom_areas(circle_polygon, id=id)
                else:
                    template = Template.create_with_custom_area(
                        circle_polygon, id, service_id, template_folder_id=template_folder_id
                    )
                return redirect(
                    url_for(
                        ".view_template",
                        service_id=current_service.id,
                        template_id=template.id,
                    )
                )
    return render_postcode_page(
        service_id,
        template_id,
        template,
        form,
        centroid,
        bleed,
        estimated_area,
        estimated_area_with_bleed,
        count_of_phones,
        count_of_phones_likely,
        "templates",
        template_folder_id,
    )


@user_has_permissions("manage_templates")
def search_coordinates_for_template(service_id, coordinate_type, template_id=None, template_folder_id=None):
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
    template = Template.from_id(template_id, service_id=service_id) if template_id else None
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
            if template:
                template.add_custom_areas(polygon, id=id)
            else:
                template = Template.create_with_custom_area(
                    polygon, id, service_id, template_folder_id=template_folder_id
                )
            return redirect(
                url_for(
                    ".view_template",
                    service_id=current_service.id,
                    template_id=template.id,
                )
            )
    return render_coordinates_page(
        service_id,
        template_id,
        coordinate_type,
        bleed,
        estimated_area,
        estimated_area_with_bleed,
        count_of_phones,
        count_of_phones_likely,
        marker,
        template,
        form,
        "templates",
        template_folder_id,
    )


@user_has_permissions("manage_templates")
def remove_template_area(service_id, template_id, area_slug):
    template = Template.from_id(template_id, service_id=service_id)
    template.remove_area(area_slug)
    # Fetch updated template as not returned by method
    template = Template.from_id(template_id, service_id=service_id)
    url = ".choose_library" if len(template.areas) == 0 else ".preview_areas"
    return redirect(
        url_for(
            url,
            service_id=current_service.id,
            message_id=template_id,
            message_type="templates",
        )
    )


@user_has_permissions("manage_templates")
def remove_custom_area_from_template(service_id, template_id):
    template = Template.from_id(template_id, service_id=service_id)
    template.clear_areas()
    return redirect(
        url_for(
            ".choose_library",
            service_id=service_id,
            message_id=template_id,
            message_type="templates",
        )
    )
