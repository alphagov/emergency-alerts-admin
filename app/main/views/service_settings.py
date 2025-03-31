from collections import OrderedDict

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from notifications_python_client.errors import HTTPError

from app import current_service, organisations_client, service_api_client
from app.event_handlers import (
    create_archive_service_event,
    create_broadcast_account_type_change_event,
)
from app.main import main
from app.main.forms import (  # ServiceBroadcastAccountTypeForm,
    AdminNotesForm,
    AdminSetOrganisationForm,
    RenameServiceForm,
    SearchByNameForm,
    ServiceBroadcastAccountForm,
    ServiceBroadcastChannelForm,
    ServiceBroadcastNetworkForm,
    ServiceOnOffSettingForm,
)
from app.utils.user import user_has_permissions, user_is_platform_admin

PLATFORM_ADMIN_SERVICE_PERMISSIONS = OrderedDict(
    [
        ("email_auth", {"title": "Email authentication"}),
    ]
)


@main.route("/services/<uuid:service_id>/service-settings")
@user_has_permissions("manage_service", "manage_api_keys")
def service_settings(service_id):
    return render_template(
        "views/service-settings.html",
        service_permissions=PLATFORM_ADMIN_SERVICE_PERMISSIONS,
    )


@main.route("/services/<uuid:service_id>/service-settings/name", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_name_change(service_id):
    form = RenameServiceForm(name=current_service.name)

    if form.validate_on_submit():
        try:
            current_service.update(
                name=form.name.data,
            )
        except HTTPError as http_error:
            if http_error.status_code == 400:
                error_message = service_api_client.parse_edit_service_http_error(http_error)
                if not error_message:
                    raise http_error

                form.name.errors.append(error_message)

        else:
            return redirect(url_for(".service_settings", service_id=service_id))

    if current_service.organisation_type == "local":
        return render_template(
            "views/service-settings/name-local.html",
            form=form,
        )

    return render_template(
        "views/service-settings/name.html",
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/permissions/<permission>", methods=["GET", "POST"])
@user_is_platform_admin
def service_set_permission(service_id, permission):
    if permission not in PLATFORM_ADMIN_SERVICE_PERMISSIONS:
        abort(404)

    title = PLATFORM_ADMIN_SERVICE_PERMISSIONS[permission]["title"]
    form = ServiceOnOffSettingForm(name=title, enabled=current_service.has_permission(permission))

    if form.validate_on_submit():
        current_service.force_permission(permission, on=form.enabled.data)

        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/set-service-setting.html",
        title=title,
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/broadcasts", methods=["GET", "POST"])
@user_is_platform_admin
def service_set_broadcast_channel(service_id):
    if current_service.has_permission("broadcast"):
        if current_service.live:
            channel = current_service.broadcast_channel
        else:
            channel = "training"
    else:
        channel = None

    form = ServiceBroadcastChannelForm(channel=channel)

    if form.validate_on_submit():
        if form.channel.data == "training":
            return redirect(
                url_for(
                    ".service_confirm_broadcast_account_type",
                    service_id=current_service.id,
                    account_type="training-test-all",
                )
            )
        return redirect(
            url_for(
                ".service_set_broadcast_network",
                service_id=current_service.id,
                broadcast_channel=form.channel.data,
            )
        )

    return render_template(
        "views/service-settings/service-set-broadcast-channel.html",
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/broadcasts/<broadcast_channel>", methods=["GET", "POST"])
@user_is_platform_admin
def service_set_broadcast_network(service_id, broadcast_channel):
    providers = service_api_client.get_broadcast_providers(current_service.id)["data"]

    form = ServiceBroadcastNetworkForm(
        broadcast_channel=broadcast_channel,
        networks=[item["provider"] for item in providers],
    )

    if form.validate_on_submit():
        return redirect(
            url_for(
                ".service_confirm_broadcast_account_type",
                service_id=current_service.id,
                account_type=form.account_type,
            )
        )

    return render_template(
        "views/service-settings/service-set-broadcast-network.html",
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/broadcasts/<account_type>/confirm", methods=["GET", "POST"])
@user_is_platform_admin
def service_confirm_broadcast_account_type(service_id, account_type):
    # form = ServiceBroadcastAccountTypeForm(account_type=account_type)
    # form.validate()

    form = ServiceBroadcastAccountForm(account_type=account_type)
    form.validate()

    if form.account_type.errors:
        abort(404)

    if form.validate_on_submit():
        service_api_client.set_service_broadcast_settings(
            current_service.id,
            service_mode=form.service_mode,
            broadcast_channel=form.broadcast_channel,
            provider_restriction=form.provider_restriction,
        )
        create_broadcast_account_type_change_event(
            service_id=current_service.id,
            changed_by_id=current_user.id,
            service_mode=form.service_mode,
            broadcast_channel=form.broadcast_channel,
            provider_restriction=form.provider_restriction,
        )
        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/service-confirm-broadcast-account-type.html",
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/archive", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def archive_service(service_id):
    if not current_service.active or not (current_service.trial_mode or current_user.platform_admin):
        abort(403)
    if request.method == "POST":
        service_api_client.archive_service(service_id)
        create_archive_service_event(service_id=service_id, archived_by_id=current_user.id)

        flash(
            "‘{}’ was deleted".format(current_service.name),
            "default_with_tick",
        )
        return redirect(url_for(".choose_account"))
    else:
        flash(
            "Are you sure you want to delete ‘{}’? There’s no way to undo this.".format(current_service.name),
            "delete",
        )
        return service_settings(service_id)


@main.route("/services/<uuid:service_id>/service-settings/set-auth-type", methods=["GET"])
@user_has_permissions("manage_service")
def service_set_auth_type(service_id):
    return render_template(
        "views/service-settings/set-auth-type.html",
    )


@main.route("/services/<uuid:service_id>/service-settings/link-service-to-organisation", methods=["GET", "POST"])
@user_is_platform_admin
def link_service_to_organisation(service_id):
    all_organisations = organisations_client.get_organisations()

    form = AdminSetOrganisationForm(
        choices=convert_dictionary_to_wtforms_choices_format(all_organisations, "id", "name"),
        organisations=current_service.organisation_id,
    )

    if form.validate_on_submit():
        if form.organisations.data != current_service.organisation_id:
            organisations_client.update_service_organisation(service_id, form.organisations.data)
        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/link-service-to-organisation.html",
        has_organisations=all_organisations,
        form=form,
        search_form=SearchByNameForm(),
    )


@main.route("/services/<uuid:service_id>/notes", methods=["GET", "POST"])
@user_is_platform_admin
def edit_service_notes(service_id):
    form = AdminNotesForm(notes=current_service.notes)

    if form.validate_on_submit():
        if form.notes.data == current_service.notes:
            return redirect(url_for(".service_settings", service_id=service_id))

        current_service.update(notes=form.notes.data)
        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/edit-service-notes.html",
        form=form,
    )


def convert_dictionary_to_wtforms_choices_format(dictionary, value, label):
    return [(item[value], item[label]) for item in dictionary]


def check_contact_details_type(contact_details):
    if contact_details.startswith("http"):
        return "url"
    elif "@" in contact_details:
        return "email_address"
    else:
        return "phone_number"


def format_provider_string(provider_list):
    return ",".join(provider_list)
