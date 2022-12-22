import uuid
from collections import OrderedDict
from datetime import datetime

from emergency_alerts_utils.clients.zendesk.zendesk_client import NotifySupportTicket
from emergency_alerts_utils.timezones import utc_string_to_aware_gmt_datetime
from flask import (
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user
from notifications_python_client.errors import HTTPError

from app import (
    billing_api_client,
    current_service,
    inbound_number_client,
    notification_api_client,
    organisations_client,
    service_api_client,
)
from app.event_handlers import (
    create_archive_service_event,
    create_broadcast_account_type_change_event,
)
from app.extensions import zendesk_client
from app.formatters import email_safe
from app.main import main
from app.main.forms import (
    AdminBillingDetailsForm,
    AdminNotesForm,
    AdminPreviewBrandingForm,
    AdminServiceAddDataRetentionForm,
    AdminServiceEditDataRetentionForm,
    AdminServiceInboundNumberForm,
    AdminServiceMessageLimitForm,
    AdminServiceRateLimitForm,
    AdminServiceSMSAllowanceForm,
    AdminSetBrandingAddToBrandingPoolStepForm,
    AdminSetEmailBrandingForm,
    AdminSetLetterBrandingForm,
    AdminSetOrganisationForm,
    ChooseEmailBrandingForm,
    ChooseLetterBrandingForm,
    EmailBrandingAltTextForm,
    EmailBrandingChooseBanner,
    EmailBrandingChooseBannerColour,
    EmailBrandingChooseLogoForm,
    EmailBrandingLogoUpload,
    EstimateUsageForm,
    GovernmentIdentityLogoForm,
    RenameServiceForm,
    SearchByNameForm,
    ServiceBroadcastAccountTypeForm,
    ServiceBroadcastChannelForm,
    ServiceBroadcastNetworkForm,
    ServiceContactDetailsForm,
    ServiceEditInboundNumberForm,
    ServiceLetterContactBlockForm,
    ServiceOnOffSettingForm,
    ServiceReplyToEmailForm,
    ServiceSmsSenderForm,
    ServiceSwitchChannelForm,
    SMSPrefixForm,
    SomethingElseBrandingForm,
)
from app.main.views.pricing import CURRENT_SMS_RATE
from app.models.branding import (
    AllEmailBranding,
    AllLetterBranding,
    EmailBranding,
    LetterBranding,
)
from app.models.organisation import Organisation
from app.s3_client.s3_logo_client import upload_email_logo
from app.utils import (
    DELIVERED_STATUSES,
    FAILURE_STATUSES,
    SENDING_STATUSES,
    service_belongs_to_org_type,
)
from app.utils.branding import get_email_choices as get_email_branding_choices
from app.utils.user import (
    user_has_permissions,
    user_is_gov_user,
    user_is_platform_admin,
)

PLATFORM_ADMIN_SERVICE_PERMISSIONS = OrderedDict(
    [
        ("inbound_sms", {"title": "Receive inbound SMS", "requires": "sms", "endpoint": ".service_set_inbound_number"}),
        ("email_auth", {"title": "Email authentication"}),
        ("international_letters", {"title": "Send international letters", "requires": "letter"}),
    ]
)

THANKS_FOR_BRANDING_REQUEST_MESSAGE = "Thanks for your branding request. We’ll get back to you within one working day."


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
                email_from=email_safe(form.name.data),
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


@main.route("/services/<uuid:service_id>/service-settings/request-to-go-live/estimate-usage", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def estimate_usage(service_id):

    form = EstimateUsageForm(
        volume_email=current_service.volume_email,
        volume_sms=current_service.volume_sms,
        volume_letter=current_service.volume_letter,
        consent_to_research={
            True: "yes",
            False: "no",
        }.get(current_service.consent_to_research),
    )

    if form.validate_on_submit():
        current_service.update(
            volume_email=form.volume_email.data,
            volume_sms=form.volume_sms.data,
            volume_letter=form.volume_letter.data,
            consent_to_research=(form.consent_to_research.data == "yes"),
        )
        return redirect(
            url_for(
                "main.request_to_go_live",
                service_id=service_id,
            )
        )

    return render_template(
        "views/service-settings/estimate-usage.html",
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/request-to-go-live", methods=["GET"])
@user_has_permissions("manage_service")
def request_to_go_live(service_id):
    if current_service.live:
        return render_template("views/service-settings/service-already-live.html")

    return render_template("views/service-settings/request-to-go-live.html")


@main.route("/services/<uuid:service_id>/service-settings/request-to-go-live", methods=["POST"])
@user_has_permissions("manage_service")
@user_is_gov_user
def submit_request_to_go_live(service_id):
    ticket_message = render_template("support-tickets/go-live-request.txt") + "\n"

    ticket = NotifySupportTicket(
        subject=f"Request to go live - {current_service.name}",
        message=ticket_message,
        ticket_type=NotifySupportTicket.TYPE_QUESTION,
        user_name=current_user.name,
        user_email=current_user.email_address,
        requester_sees_message_content=False,
        org_id=current_service.organisation_id,
        org_type=current_service.organisation_type,
        service_id=current_service.id,
    )
    zendesk_client.send_ticket_to_zendesk(ticket)

    current_service.update(go_live_user=current_user.id)

    flash("Thanks for your request to go live. We’ll get back to you within one working day.", "default")
    return redirect(url_for(".service_settings", service_id=service_id))


@main.route("/services/<uuid:service_id>/service-settings/switch-live", methods=["GET", "POST"])
@user_is_platform_admin
def service_switch_live(service_id):
    form = ServiceOnOffSettingForm(name="Make service live", enabled=not current_service.trial_mode)

    if form.validate_on_submit():
        current_service.update_status(live=form.enabled.data)
        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/set-service-setting.html",
        title="Make service live",
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/switch-count-as-live", methods=["GET", "POST"])
@user_is_platform_admin
def service_switch_count_as_live(service_id):

    form = ServiceOnOffSettingForm(
        name="Count in list of live services",
        enabled=current_service.count_as_live,
        truthy="Yes",
        falsey="No",
    )

    if form.validate_on_submit():
        current_service.update_count_as_live(form.enabled.data)
        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/set-service-setting.html",
        title="Count in list of live services",
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
    # only populate old settings when the channel is unchanged
    if current_service.broadcast_channel == broadcast_channel:
        provider = current_service.allowed_broadcast_provider

        form = ServiceBroadcastNetworkForm(
            broadcast_channel=broadcast_channel,
            all_networks=provider == "all",
            network=provider if provider != "all" else None,
        )
    else:
        form = ServiceBroadcastNetworkForm(broadcast_channel=broadcast_channel)

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
    form = ServiceBroadcastAccountTypeForm(account_type=account_type)
    form.validate()

    if form.account_type.errors:
        abort(404)

    if form.validate_on_submit():
        cached_service_user_ids = [user.id for user in current_service.active_users]

        service_api_client.set_service_broadcast_settings(
            current_service.id,
            service_mode=form.account_type.service_mode,
            broadcast_channel=form.account_type.broadcast_channel,
            provider_restriction=form.account_type.provider_restriction,
            cached_service_user_ids=cached_service_user_ids,
        )
        create_broadcast_account_type_change_event(
            service_id=current_service.id,
            changed_by_id=current_user.id,
            service_mode=form.account_type.service_mode,
            broadcast_channel=form.account_type.broadcast_channel,
            provider_restriction=form.account_type.provider_restriction,
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
        # We need to purge the cache for the services users as otherwise, although they will have had their permissions
        # removed in the DB, they would still have permissions in the cache to view/edit/manage this service
        cached_service_user_ids = [user.id for user in current_service.active_users]

        service_api_client.archive_service(service_id, cached_service_user_ids)
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


@main.route("/services/<uuid:service_id>/service-settings/send-files-by-email", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def send_files_by_email_contact_details(service_id):
    form = ServiceContactDetailsForm()
    contact_details = None

    if request.method == "GET":
        contact_details = current_service.contact_link
        if contact_details:
            contact_type = check_contact_details_type(contact_details)
            field_to_update = getattr(form, contact_type)

            form.contact_details_type.data = contact_type
            field_to_update.data = contact_details

    if form.validate_on_submit():
        contact_type = form.contact_details_type.data

        current_service.update(contact_link=form.data[contact_type])
        return redirect(url_for(".service_settings", service_id=current_service.id))

    return render_template(
        "views/service-settings/send-files-by-email.html", form=form, contact_details=contact_details
    )


@main.route("/services/<uuid:service_id>/service-settings/set-reply-to-email", methods=["GET"])
@user_has_permissions("manage_service")
def service_set_reply_to_email(service_id):
    return redirect(url_for(".service_email_reply_to", service_id=service_id))


@main.route("/services/<uuid:service_id>/service-settings/email-reply-to", methods=["GET"])
@user_has_permissions("manage_service", "manage_api_keys")
def service_email_reply_to(service_id):
    return render_template("views/service-settings/email_reply_to.html")


@main.route("/services/<uuid:service_id>/service-settings/email-reply-to/add", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_add_email_reply_to(service_id):
    form = ServiceReplyToEmailForm()
    first_email_address = current_service.count_email_reply_to_addresses == 0
    is_default = first_email_address if first_email_address else form.is_default.data
    if form.validate_on_submit():
        if current_user.platform_admin:
            service_api_client.add_reply_to_email_address(
                service_id, email_address=form.email_address.data, is_default=is_default
            )
            return redirect(url_for(".service_email_reply_to", service_id=service_id))
        else:
            try:
                notification_id = service_api_client.verify_reply_to_email_address(service_id, form.email_address.data)[
                    "data"
                ]["id"]
            except HTTPError as e:
                if e.status_code == 409:
                    flash(e.message, "error")
                    return redirect(url_for(".service_email_reply_to", service_id=service_id))
                else:
                    raise e
            return redirect(
                url_for(
                    ".service_verify_reply_to_address",
                    service_id=service_id,
                    notification_id=notification_id,
                    is_default=is_default,
                )
            )

    return render_template(
        "views/service-settings/email-reply-to/add.html", form=form, first_email_address=first_email_address
    )


@main.route(
    "/services/<uuid:service_id>/service-settings/email-reply-to/<uuid:notification_id>/verify", methods=["GET", "POST"]
)
@user_has_permissions("manage_service")
def service_verify_reply_to_address(service_id, notification_id):
    replace = request.args.get("replace", False)
    is_default = request.args.get("is_default", False)
    return render_template(
        "views/service-settings/email-reply-to/verify.html",
        service_id=service_id,
        notification_id=notification_id,
        partials=get_service_verify_reply_to_address_partials(service_id, notification_id),
        verb=("Change" if replace else "Add"),
        replace=replace,
        is_default=is_default,
    )


@main.route("/services/<uuid:service_id>/service-settings/email-reply-to/<uuid:notification_id>/verify.json")
@user_has_permissions("manage_service")
def service_verify_reply_to_address_updates(service_id, notification_id):
    return jsonify(**get_service_verify_reply_to_address_partials(service_id, notification_id))


def get_service_verify_reply_to_address_partials(service_id, notification_id):
    form = ServiceReplyToEmailForm()
    first_email_address = current_service.count_email_reply_to_addresses == 0
    notification = notification_api_client.get_notification(current_app.config["NOTIFY_SERVICE_ID"], notification_id)
    replace = request.args.get("replace", False)
    replace = False if replace == "False" else replace
    existing_is_default = False
    if replace:
        existing = current_service.get_email_reply_to_address(replace)
        existing_is_default = existing["is_default"]
    verification_status = "pending"
    is_default = True if (request.args.get("is_default", False) == "True") else False
    if notification["status"] in DELIVERED_STATUSES:
        verification_status = "success"
        if notification["to"] not in [i["email_address"] for i in current_service.email_reply_to_addresses]:
            if replace:
                service_api_client.update_reply_to_email_address(
                    current_service.id, replace, email_address=notification["to"], is_default=is_default
                )
            else:
                service_api_client.add_reply_to_email_address(
                    current_service.id, email_address=notification["to"], is_default=is_default
                )
    seconds_since_sending = (
        utc_string_to_aware_gmt_datetime(datetime.utcnow().isoformat())
        - utc_string_to_aware_gmt_datetime(notification["created_at"])
    ).seconds
    if notification["status"] in FAILURE_STATUSES or (
        notification["status"] in SENDING_STATUSES
        and seconds_since_sending > current_app.config["REPLY_TO_EMAIL_ADDRESS_VALIDATION_TIMEOUT"]
    ):
        verification_status = "failure"
        form.email_address.data = notification["to"]
        form.is_default.data = is_default
    return {
        "status": render_template(
            "views/service-settings/email-reply-to/_verify-updates.html",
            reply_to_email_address=notification["to"],
            service_id=current_service.id,
            notification_id=notification_id,
            verification_status=verification_status,
            is_default=is_default,
            existing_is_default=existing_is_default,
            form=form,
            first_email_address=first_email_address,
            replace=replace,
        ),
        "stop": 0 if verification_status == "pending" else 1,
    }


@main.route(
    "/services/<uuid:service_id>/service-settings/email-reply-to/<uuid:reply_to_email_id>/edit",
    methods=["GET", "POST"],
    endpoint="service_edit_email_reply_to",
)
@main.route(
    "/services/<uuid:service_id>/service-settings/email-reply-to/<uuid:reply_to_email_id>/delete",
    methods=["GET"],
    endpoint="service_confirm_delete_email_reply_to",
)
@user_has_permissions("manage_service")
def service_edit_email_reply_to(service_id, reply_to_email_id):
    form = ServiceReplyToEmailForm()
    reply_to_email_address = current_service.get_email_reply_to_address(reply_to_email_id)

    if request.method == "GET":
        form.email_address.data = reply_to_email_address["email_address"]
        form.is_default.data = reply_to_email_address["is_default"]

    show_choice_of_default_checkbox = not reply_to_email_address["is_default"]

    if form.validate_on_submit():
        if form.email_address.data == reply_to_email_address["email_address"] or current_user.platform_admin:
            service_api_client.update_reply_to_email_address(
                current_service.id,
                reply_to_email_id=reply_to_email_id,
                email_address=form.email_address.data,
                is_default=True if reply_to_email_address["is_default"] else form.is_default.data,
            )
            return redirect(url_for(".service_email_reply_to", service_id=service_id))
        try:
            notification_id = service_api_client.verify_reply_to_email_address(service_id, form.email_address.data)[
                "data"
            ]["id"]
        except HTTPError as e:
            if e.status_code == 409:
                flash(e.message, "error")
                return redirect(url_for(".service_email_reply_to", service_id=service_id))
            else:
                raise e
        return redirect(
            url_for(
                ".service_verify_reply_to_address",
                service_id=service_id,
                notification_id=notification_id,
                is_default=True if reply_to_email_address["is_default"] else form.is_default.data,
                replace=reply_to_email_id,
            )
        )

    if request.endpoint == "main.service_confirm_delete_email_reply_to":
        flash("Are you sure you want to delete this reply-to email address?", "delete")
    return render_template(
        "views/service-settings/email-reply-to/edit.html",
        form=form,
        reply_to_email_address_id=reply_to_email_id,
        show_choice_of_default_checkbox=show_choice_of_default_checkbox,
    )


@main.route(
    "/services/<uuid:service_id>/service-settings/email-reply-to/<uuid:reply_to_email_id>/delete", methods=["POST"]
)
@user_has_permissions("manage_service")
def service_delete_email_reply_to(service_id, reply_to_email_id):
    service_api_client.delete_reply_to_email_address(
        service_id=current_service.id,
        reply_to_email_id=reply_to_email_id,
    )
    return redirect(url_for(".service_email_reply_to", service_id=service_id))


@main.route("/services/<uuid:service_id>/service-settings/set-inbound-number", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_set_inbound_number(service_id):
    available_inbound_numbers = inbound_number_client.get_available_inbound_sms_numbers()
    inbound_numbers_value_and_label = [(number["id"], number["number"]) for number in available_inbound_numbers["data"]]
    no_available_numbers = available_inbound_numbers["data"] == []
    form = AdminServiceInboundNumberForm(inbound_number_choices=inbound_numbers_value_and_label)

    if form.validate_on_submit():
        service_api_client.add_sms_sender(
            current_service.id,
            sms_sender=form.inbound_number.data,
            is_default=True,
            inbound_number_id=form.inbound_number.data,
        )
        current_service.force_permission("inbound_sms", on=True)
        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/set-inbound-number.html",
        form=form,
        no_available_numbers=no_available_numbers,
    )


@main.route("/services/<uuid:service_id>/service-settings/sms-prefix", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_set_sms_prefix(service_id):

    form = SMSPrefixForm(enabled=current_service.prefix_sms)

    form.enabled.label.text = "Start all text messages with ‘{}:’".format(current_service.name)

    if form.validate_on_submit():
        current_service.update(prefix_sms=form.enabled.data)
        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template("views/service-settings/sms-prefix.html", form=form)


@main.route("/services/<uuid:service_id>/service-settings/set-international-sms", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_set_international_sms(service_id):
    form = ServiceOnOffSettingForm(
        "Send text messages to international phone numbers",
        enabled=current_service.has_permission("international_sms"),
    )
    if form.validate_on_submit():
        current_service.force_permission(
            "international_sms",
            on=form.enabled.data,
        )
        return redirect(url_for(".service_settings", service_id=service_id))
    return render_template(
        "views/service-settings/set-international-sms.html",
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/set-international-letters", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_set_international_letters(service_id):
    form = ServiceOnOffSettingForm(
        "Send letters to international addresses",
        enabled=current_service.has_permission("international_letters"),
    )
    if form.validate_on_submit():
        current_service.force_permission(
            "international_letters",
            on=form.enabled.data,
        )
        return redirect(url_for(".service_settings", service_id=service_id))
    return render_template(
        "views/service-settings/set-international-letters.html",
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/set-inbound-sms", methods=["GET"])
@user_has_permissions("manage_service")
def service_set_inbound_sms(service_id):
    return render_template(
        "views/service-settings/set-inbound-sms.html",
    )


@main.route("/services/<uuid:service_id>/service-settings/set-letters", methods=["GET"])
@user_has_permissions("manage_service")
def service_set_letters(service_id):
    return redirect(
        url_for(
            ".service_set_channel",
            service_id=current_service.id,
            channel="letter",
        ),
        code=301,
    )


@main.route("/services/<uuid:service_id>/service-settings/set-<channel>", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_set_channel(service_id, channel):

    if channel not in {"email", "sms", "letter"}:
        abort(404)

    if current_service.has_permission("broadcast"):
        abort(403)

    form = ServiceSwitchChannelForm(channel=channel, enabled=current_service.has_permission(channel))

    if form.validate_on_submit():
        current_service.force_permission(
            channel,
            on=form.enabled.data,
        )
        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/set-{}.html".format(channel),
        form=form,
        sms_rate=CURRENT_SMS_RATE,
    )


@main.route("/services/<uuid:service_id>/service-settings/set-auth-type", methods=["GET"])
@user_has_permissions("manage_service")
def service_set_auth_type(service_id):
    return render_template(
        "views/service-settings/set-auth-type.html",
    )


@main.route("/services/<uuid:service_id>/service-settings/letter-contacts", methods=["GET"])
@user_has_permissions("manage_service", "manage_api_keys")
def service_letter_contact_details(service_id):
    letter_contact_details = service_api_client.get_letter_contacts(service_id)
    return render_template(
        "views/service-settings/letter-contact-details.html", letter_contact_details=letter_contact_details
    )


@main.route("/services/<uuid:service_id>/service-settings/letter-contact/add", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_add_letter_contact(service_id):
    form = ServiceLetterContactBlockForm()
    first_contact_block = current_service.count_letter_contact_details == 0
    from_template = request.args.get("from_template")
    if form.validate_on_submit():
        new_letter_contact = service_api_client.add_letter_contact(
            current_service.id,
            contact_block=form.letter_contact_block.data.replace("\r", "") or None,
            is_default=first_contact_block if first_contact_block else form.is_default.data,
        )
        if from_template:
            service_api_client.update_service_template_sender(
                service_id,
                from_template,
                new_letter_contact["data"]["id"],
            )
            return redirect(url_for(".view_template", service_id=service_id, template_id=from_template))
        return redirect(url_for(".service_letter_contact_details", service_id=service_id))
    return render_template(
        "views/service-settings/letter-contact/add.html",
        form=form,
        first_contact_block=first_contact_block,
        back_link=(
            url_for("main.view_template", template_id=from_template, service_id=current_service.id)
            if from_template
            else url_for(".service_letter_contact_details", service_id=current_service.id)
        ),
    )


@main.route(
    "/services/<uuid:service_id>/service-settings/letter-contact/<uuid:letter_contact_id>/edit",
    methods=["GET", "POST"],
    endpoint="service_edit_letter_contact",
)
@main.route(
    "/services/<uuid:service_id>/service-settings/letter-contact/<uuid:letter_contact_id>/delete",
    methods=["GET"],
    endpoint="service_confirm_delete_letter_contact",
)
@user_has_permissions("manage_service")
def service_edit_letter_contact(service_id, letter_contact_id):
    letter_contact_block = current_service.get_letter_contact_block(letter_contact_id)
    form = ServiceLetterContactBlockForm(letter_contact_block=letter_contact_block["contact_block"])
    if request.method == "GET":
        form.is_default.data = letter_contact_block["is_default"]
    if form.validate_on_submit():
        current_service.edit_letter_contact_block(
            id=letter_contact_id,
            contact_block=form.letter_contact_block.data.replace("\r", "") or None,
            is_default=letter_contact_block["is_default"] or form.is_default.data,
        )
        return redirect(url_for(".service_letter_contact_details", service_id=service_id))

    if request.endpoint == "main.service_confirm_delete_letter_contact":
        flash("Are you sure you want to delete this contact block?", "delete")
    return render_template(
        "views/service-settings/letter-contact/edit.html", form=form, letter_contact_id=letter_contact_block["id"]
    )


@main.route("/services/<uuid:service_id>/service-settings/letter-contact/make-blank-default")
@user_has_permissions("manage_service")
def service_make_blank_default_letter_contact(service_id):
    current_service.remove_default_letter_contact_block()
    return redirect(url_for(".service_letter_contact_details", service_id=service_id))


@main.route(
    "/services/<uuid:service_id>/service-settings/letter-contact/<uuid:letter_contact_id>/delete",
    methods=["POST"],
)
@user_has_permissions("manage_service")
def service_delete_letter_contact(service_id, letter_contact_id):
    service_api_client.delete_letter_contact(
        service_id=current_service.id,
        letter_contact_id=letter_contact_id,
    )
    return redirect(url_for(".service_letter_contact_details", service_id=current_service.id))


@main.route("/services/<uuid:service_id>/service-settings/sms-sender", methods=["GET"])
@user_has_permissions("manage_service", "manage_api_keys")
def service_sms_senders(service_id):
    return render_template(
        "views/service-settings/sms-senders.html",
    )


@main.route("/services/<uuid:service_id>/service-settings/sms-sender/add", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def service_add_sms_sender(service_id):
    form = ServiceSmsSenderForm()
    first_sms_sender = current_service.count_sms_senders == 0
    if form.validate_on_submit():
        service_api_client.add_sms_sender(
            current_service.id,
            sms_sender=form.sms_sender.data.replace("\r", "") or None,
            is_default=first_sms_sender if first_sms_sender else form.is_default.data,
        )
        return redirect(url_for(".service_sms_senders", service_id=service_id))
    return render_template("views/service-settings/sms-sender/add.html", form=form, first_sms_sender=first_sms_sender)


@main.route(
    "/services/<uuid:service_id>/service-settings/sms-sender/<uuid:sms_sender_id>/edit",
    methods=["GET", "POST"],
    endpoint="service_edit_sms_sender",
)
@main.route(
    "/services/<uuid:service_id>/service-settings/sms-sender/<uuid:sms_sender_id>/delete",
    methods=["GET"],
    endpoint="service_confirm_delete_sms_sender",
)
@user_has_permissions("manage_service")
def service_edit_sms_sender(service_id, sms_sender_id):
    sms_sender = current_service.get_sms_sender(sms_sender_id)
    is_inbound_number = sms_sender["inbound_number_id"]
    if is_inbound_number:
        form = ServiceEditInboundNumberForm(is_default=sms_sender["is_default"])
    else:
        form = ServiceSmsSenderForm(**sms_sender)

    if form.validate_on_submit():
        service_api_client.update_sms_sender(
            current_service.id,
            sms_sender_id=sms_sender_id,
            sms_sender=sms_sender["sms_sender"] if is_inbound_number else form.sms_sender.data.replace("\r", ""),
            is_default=True if sms_sender["is_default"] else form.is_default.data,
        )
        return redirect(url_for(".service_sms_senders", service_id=service_id))

    form.is_default.data = sms_sender["is_default"]
    if request.endpoint == "main.service_confirm_delete_sms_sender":
        flash("Are you sure you want to delete this text message sender?", "delete")
    return render_template(
        "views/service-settings/sms-sender/edit.html",
        form=form,
        sms_sender=sms_sender,
        inbound_number=is_inbound_number,
        sms_sender_id=sms_sender_id,
    )


@main.route(
    "/services/<uuid:service_id>/service-settings/sms-sender/<uuid:sms_sender_id>/delete",
    methods=["POST"],
)
@user_has_permissions("manage_service")
def service_delete_sms_sender(service_id, sms_sender_id):
    service_api_client.delete_sms_sender(
        service_id=current_service.id,
        sms_sender_id=sms_sender_id,
    )
    return redirect(url_for(".service_sms_senders", service_id=service_id))


@main.route("/services/<uuid:service_id>/service-settings/set-free-sms-allowance", methods=["GET", "POST"])
@user_is_platform_admin
def set_free_sms_allowance(service_id):

    form = AdminServiceSMSAllowanceForm(free_sms_allowance=current_service.free_sms_fragment_limit)

    if form.validate_on_submit():
        billing_api_client.create_or_update_free_sms_fragment_limit(service_id, form.free_sms_allowance.data)

        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/set-free-sms-allowance.html",
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/set-message-limit", methods=["GET", "POST"])
@user_is_platform_admin
def set_message_limit(service_id):

    form = AdminServiceMessageLimitForm(message_limit=current_service.message_limit)

    if form.validate_on_submit():
        current_service.update(message_limit=form.message_limit.data)

        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/set-message-limit.html",
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/set-rate-limit", methods=["GET", "POST"])
@user_is_platform_admin
def set_rate_limit(service_id):

    form = AdminServiceRateLimitForm(rate_limit=current_service.rate_limit)

    if form.validate_on_submit():
        current_service.update(rate_limit=form.rate_limit.data)

        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/set-rate-limit.html",
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/set-<notification_type>-branding", methods=["GET", "POST"])
@user_is_platform_admin
def service_set_branding(service_id, notification_type):
    notification_type = notification_type.lower()

    if notification_type == "email":
        form = AdminSetEmailBrandingForm(
            all_branding_options=AllEmailBranding().as_id_and_name,
            current_branding=current_service.email_branding_id,
        )

    elif notification_type == "letter":
        form = AdminSetLetterBrandingForm(
            all_branding_options=AllLetterBranding().as_id_and_name,
            current_branding=current_service.letter_branding_id,
        )

    else:
        abort(404)

    if form.validate_on_submit():
        # As of 2022-12-02 we only get to this point (eg a POST on this endpoint) if JavaScript fails for the user on
        # this page. With JS enabled, the preview is shown as part of this view, and so the 'save' action skips the
        # separate preview page.
        return redirect(
            url_for(
                ".service_preview_branding",
                service_id=service_id,
                notification_type=notification_type,
                branding_style=form.branding_style.data,
            )
        )

    return render_template(
        "views/service-settings/set-branding.html",
        form=form,
        search_form=SearchByNameForm(),
        notification_type=notification_type,
    )


@main.route(
    "/services/<uuid:service_id>/service-settings/set-<notification_type>-branding/add-to-branding-pool-step",
    methods=["GET", "POST"],
)
@user_is_platform_admin
def service_set_branding_add_to_branding_pool_step(service_id, notification_type):
    branding_id = request.args.get("branding_id")
    notification_type = notification_type.lower()
    branding_type = f"{notification_type}_branding"

    if notification_type == "email":
        branding = EmailBranding.from_id(branding_id)
        add_brandings_to_pool = organisations_client.add_brandings_to_email_branding_pool

    elif notification_type == "letter":
        branding = LetterBranding.from_id(branding_id)
        add_brandings_to_pool = organisations_client.add_brandings_to_letter_branding_pool

    else:
        abort(404)

    branding_name = branding.name
    org_id = current_service.organisation.id

    form = AdminSetBrandingAddToBrandingPoolStepForm()

    if form.validate_on_submit():
        # The service’s branding gets updated either way
        current_service.update(**{branding_type: branding_id})
        message = f"The {notification_type} branding has been set to {branding_name}"

        # If the platform admin chose "yes" the branding is added to the organisation's branding pool
        if form.add_to_pool.data == "yes":
            branding_ids = [branding_id]
            add_brandings_to_pool(org_id, branding_ids)
            message = (
                f"The {notification_type} branding has been set to {branding_name} and it has been "
                f"added to {current_service.organisation.name}'s {notification_type} branding pool"
            )

        flash(message, "default_with_tick")
        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/set-branding-add-to-branding-pool-step.html",
        back_link=url_for(".service_set_branding", service_id=current_service.id, notification_type=notification_type),
        form=form,
        branding_name=branding_name,
    )


@main.route(
    "/services/<uuid:service_id>/service-settings/preview-<notification_type>-branding", methods=["GET", "POST"]
)
@user_is_platform_admin
def service_preview_branding(service_id, notification_type):
    branding_style = request.args.get("branding_style")
    notification_type = notification_type.lower()
    branding_type = f"{notification_type}_branding"

    if notification_type == "email":
        service_branding_pool = current_service.email_branding_pool

    elif notification_type == "letter":
        service_branding_pool = current_service.letter_branding_pool

    else:
        abort(404)

    form = AdminPreviewBrandingForm(branding_style=branding_style)

    if form.validate_on_submit():
        branding_id = form.branding_style.data
        if branding_id == "__NONE__":  # This represents the email GOV.UK brand
            branding_id = None

        if current_service.organisation and branding_id and branding_id not in service_branding_pool.ids:
            return redirect(
                url_for(
                    "main.service_set_branding_add_to_branding_pool_step",
                    service_id=service_id,
                    notification_type=notification_type,
                    branding_id=branding_id,
                )
            )

        current_service.update(**{branding_type: branding_id})
        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/preview-branding.html",
        form=form,
        service_id=service_id,
        notification_type=notification_type,
        action=url_for("main.service_preview_branding", service_id=service_id, notification_type=notification_type),
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


def create_email_branding_zendesk_ticket(form_option_selected, detail=None):
    form = ChooseEmailBrandingForm(current_service)

    ticket_message = render_template(
        "support-tickets/branding-request.txt",
        current_branding=current_service.email_branding.name,
        branding_requested=dict(form.options.choices)[form_option_selected],
        detail=detail,
    )
    ticket = NotifySupportTicket(
        subject=f"Email branding request - {current_service.name}",
        message=ticket_message,
        ticket_type=NotifySupportTicket.TYPE_QUESTION,
        user_name=current_user.name,
        user_email=current_user.email_address,
        org_id=current_service.organisation_id,
        org_type=current_service.organisation_type,
        service_id=current_service.id,
    )
    zendesk_client.send_ticket_to_zendesk(ticket)


@main.route("/services/<uuid:service_id>/service-settings/email-branding", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def email_branding_request(service_id):
    form = ChooseEmailBrandingForm(current_service)
    if form.something_else_is_only_option:
        return redirect(
            url_for(".email_branding_choose_banner_type", service_id=current_service.id, back_link=".service_settings")
        )
    if form.validate_on_submit():

        branding_choice = form.options.data

        if branding_choice == EmailBranding.NHS_ID:
            return redirect(
                url_for(
                    ".email_branding_nhs",
                    service_id=current_service.id,
                )
            )
        if branding_choice == "govuk":
            return redirect(url_for(".email_branding_govuk", service_id=current_service.id))

        if branding_choice in current_service.email_branding_pool.ids:
            return redirect(
                url_for(".email_branding_pool_option", service_id=current_service.id, branding_option=branding_choice)
            )

        if current_service.organisation_type == "central":
            return redirect(
                url_for(".email_branding_choose_logo", service_id=current_service.id, branding_choice=branding_choice)
            )
        else:
            return redirect(
                url_for(
                    ".email_branding_choose_banner_type",
                    service_id=current_service.id,
                    back_link=".email_branding_request",
                    branding_choice=branding_choice,
                )
            )

    return render_template(
        "views/service-settings/branding/email-branding-options.html",
        form=form,
    )


@main.route("/services/<uuid:service_id>/service-settings/email-branding/pool", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def email_branding_pool_option(service_id):
    try:
        chosen_branding = current_service.email_branding_pool.get_item_by_id(request.args.get("branding_option"))
    except current_service.email_branding_pool.NotFound:
        flash("No branding found for this id.")
        return redirect(url_for(".email_branding_request", service_id=current_service.id))

    if request.method == "POST":
        current_service.update(email_branding=chosen_branding.id)

        flash("You’ve updated your email branding", "default")
        return redirect(url_for(".service_settings", service_id=current_service.id))

    return render_template(
        "views/service-settings/branding/email-branding-pool-option.html",
        chosen_branding=chosen_branding,
    )


def check_email_branding_allowed_for_service(branding):
    allowed_branding_for_service = dict(get_email_branding_choices(current_service))

    if branding not in allowed_branding_for_service:
        abort(404)


@main.route("/services/<uuid:service_id>/service-settings/email-branding/govuk", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def email_branding_govuk(service_id):
    check_email_branding_allowed_for_service("govuk")

    if request.method == "POST":
        current_service.update(email_branding=None)

        flash("You’ve updated your email branding", "default")
        return redirect(url_for(".service_settings", service_id=current_service.id))

    return render_template("views/service-settings/branding/email-branding-govuk.html")


@main.route("/services/<uuid:service_id>/service-settings/email-branding/nhs", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def email_branding_nhs(service_id):
    check_email_branding_allowed_for_service(EmailBranding.NHS_ID)

    if request.method == "POST":
        current_service.update(email_branding=EmailBranding.NHS_ID)

        flash("You’ve updated your email branding", "default")
        return redirect(url_for(".service_settings", service_id=current_service.id))

    return render_template(
        "views/service-settings/branding/email-branding-nhs.html", nhs_branding_id=EmailBranding.NHS_ID
    )


@main.route("/services/<uuid:service_id>/service-settings/email-branding/something-else", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def email_branding_something_else(service_id):
    form = SomethingElseBrandingForm()

    if form.validate_on_submit():
        create_email_branding_zendesk_ticket("something_else", detail=form.something_else.data)

        flash(THANKS_FOR_BRANDING_REQUEST_MESSAGE, "default")
        return redirect(url_for(".service_settings", service_id=current_service.id))

    branding_options = ChooseEmailBrandingForm(current_service)
    default_back_view = (
        ".service_settings" if branding_options.something_else_is_only_option else ".email_branding_request"
    )
    back_link = url_for(
        request.args.get("back_link", default_back_view),
        service_id=current_service.id,
        **_email_branding_flow_query_params(request),
    )
    return render_template(
        "views/service-settings/branding/email-branding-something-else.html",
        form=form,
        back_link=back_link,
    )


@main.route(
    "/services/<uuid:service_id>/service-settings/email-branding/request-government-identity-logo",
    methods=["GET"],
)
@user_has_permissions("manage_service")
@service_belongs_to_org_type("central")
def email_branding_request_government_identity_logo(service_id):
    branding_choice = request.args.get("branding_choice")
    return render_template(
        "views/service-settings/branding/email-branding-create-government-identity-logo.html",
        service_id=service_id,
        back_link=url_for(".email_branding_choose_logo", service_id=service_id, branding_choice=branding_choice),
        branding_choice=branding_choice,
        example=AllEmailBranding().example_government_identity_branding,
    )


@main.route(
    "/services/<uuid:service_id>/service-settings/email-branding/request-government-identity-logo/enter-text",
    methods=["GET", "POST"],
)
@user_has_permissions("manage_service")
@service_belongs_to_org_type("central")
def email_branding_enter_government_identity_logo_text(service_id):
    form = GovernmentIdentityLogoForm()
    branding_choice = request.args.get("branding_choice")

    if form.validate_on_submit():
        ticket_message = render_template(
            "support-tickets/government-logo-branding-request.txt",
            logo_text=form.logo_text.data,
            branding_choice=branding_choice,
        )
        ticket = NotifySupportTicket(
            subject=f"Email branding request - {current_service.name}",
            message=ticket_message,
            ticket_type=NotifySupportTicket.TYPE_TASK,
            user_name=current_user.name,
            user_email=current_user.email_address,
            org_id=current_service.organisation_id,
            org_type=current_service.organisation_type,
            service_id=current_service.id,
        )
        zendesk_client.send_ticket_to_zendesk(ticket)
        flash((THANKS_FOR_BRANDING_REQUEST_MESSAGE), "default")
        return redirect(url_for(".service_settings", service_id=current_service.id))

    return render_template(
        "views/service-settings/branding/email-branding-enter-government-identity-logo-text.html",
        form=form,
        back_link=url_for(
            ".email_branding_request_government_identity_logo", service_id=service_id, branding_choice=branding_choice
        ),
    )


@main.route("/services/<uuid:service_id>/service-settings/email-branding/choose-logo", methods=["GET", "POST"])
@user_has_permissions("manage_service")
@service_belongs_to_org_type("central")
def email_branding_choose_logo(service_id):
    form = EmailBrandingChooseLogoForm()
    branding_choice = request.args.get("branding_choice")

    if form.validate_on_submit():
        if form.branding_options.data == "org":

            if branding_choice == "govuk_and_org":
                return redirect(
                    url_for(
                        ".email_branding_upload_logo",
                        service_id=current_service.id,
                        branding_choice=branding_choice,
                        brand_type="both",
                        back_link=".email_branding_choose_logo",
                    )
                )

            return redirect(
                url_for(
                    ".email_branding_choose_banner_type",
                    service_id=current_service.id,
                    back_link=".email_branding_choose_logo",
                    **_email_branding_flow_query_params(request),
                )
            )
        elif form.branding_options.data == "single_identity":
            return redirect(
                url_for(
                    ".email_branding_request_government_identity_logo",
                    service_id=current_service.id,
                    **_email_branding_flow_query_params(request),
                )
            )

    return (
        render_template(
            "views/service-settings/branding/add-new-branding/email-branding-choose-logo.html",
            form=form,
            branding_options=form,
        ),
        400 if form.errors else 200,
    )


@main.route("/services/<uuid:service_id>/service-settings/email-branding/upload-logo", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def email_branding_upload_logo(service_id):
    form = EmailBrandingLogoUpload()

    if form.validate_on_submit():
        # We don't need to care about the filename as we're providing a UUID, and if we include the filename then we
        # have to filter that through subsequent pages in query params as well. Let's just use no filename.
        filename = ""
        upload_id = str(uuid.uuid4())

        logo_filename = upload_email_logo(
            filename,
            form.logo.data.read(),
            current_app.config["AWS_REGION"],
            user_id=current_user.id,
            unique_id=upload_id,
        )

        return redirect(
            url_for(
                "main.email_branding_set_alt_text",
                service_id=service_id,
                **_email_branding_flow_query_params(request, logo=logo_filename),
            )
        )

    abandon_flow_link = url_for(
        "main.email_branding_something_else",
        service_id=current_service.id,
        back_link=".email_branding_upload_logo",
        **_email_branding_flow_query_params(request),
    )
    if request.args.get("brand_type") == "org_banner":
        back_link = url_for(
            ".email_branding_choose_banner_colour",
            service_id=service_id,
            **_email_branding_flow_query_params(request, colour=None),
        )
    else:
        back_link = url_for(
            ".email_branding_choose_banner_type",
            service_id=service_id,
            **_email_branding_flow_query_params(request, brand_type=None),
        )

    return (
        render_template(
            "views/service-settings/branding/add-new-branding/upload-logo.html",
            form=form,
            back_link=back_link,
            abandon_flow_link=abandon_flow_link,
        ),
        400 if form.errors else 200,
    )


def _should_set_default_org_branding(branding_choice):
    # 1. the user has chosen ‘[organisation name]’ in the first page of the journey
    user_chose_org_name = branding_choice == "organisation"
    # 2. and the organisation doesn’t have default branding already
    org_doesnt_have_default_branding = current_service.organisation.email_branding_id is None
    # 3. and the organisation is not central government
    #    (it might be appropriate for them to keep GOV.UK as a default instead)
    org_not_central = current_service.organisation_type != Organisation.TYPE_CENTRAL
    # 4. and the organisation has no other live services
    no_other_live_services_in_org = not any(
        service.id != current_service.id for service in current_service.organisation.live_services
    )

    return (
        user_chose_org_name and org_doesnt_have_default_branding and org_not_central and no_other_live_services_in_org
    )


@main.route(
    "/services/<uuid:service_id>/service-settings/email-branding/when-you-use-this-branding", methods=["GET", "POST"]
)
@user_has_permissions("manage_service")
def email_branding_set_alt_text(service_id):
    email_branding_data = _email_branding_flow_query_params(request)

    if not email_branding_data["brand_type"]:
        return redirect(url_for("main.email_branding_choose_banner_type", service_id=service_id))
    elif not email_branding_data["logo"]:
        return redirect(url_for("main.email_branding_upload_logo", service_id=service_id, **email_branding_data))

    form = EmailBrandingAltTextForm()

    if form.validate_on_submit():
        # we use this key to keep track of user choices through the journey but we don't use it to save the branding
        branding_choice = email_branding_data.pop("branding_choice")

        new_email_branding = EmailBranding.create(
            alt_text=form.alt_text.data,
            **email_branding_data,
        )

        # set as service branding
        current_service.update(email_branding=new_email_branding.id)

        # add to org pool
        organisations_client.add_brandings_to_email_branding_pool(
            current_service.organisation.id, [new_email_branding.id]
        )

        if _should_set_default_org_branding(branding_choice):
            current_service.organisation.update(email_branding_id=new_email_branding.id, delete_services_cache=True)

        flash(
            "You’ve changed your email branding. Send yourself an email to make sure it looks OK.", "default_with_tick"
        )

        return redirect(url_for("main.service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/branding/add-new-branding/email-branding-set-alt-text.html",
        back_link=url_for(
            ".email_branding_upload_logo",
            service_id=service_id,
            **_email_branding_flow_query_params(request, logo=None),
        ),
        email_preview_data=email_branding_data,
        form=form,
    )


def _email_branding_flow_query_params(request, **kwargs):
    """Return a dictionary containing values for the new email branding flow.

    In order to create a new email branding for a user we need to collect and remember a series of information:
    - what kind of brand they want
    - what colour banner they want (optional)
    - what logo to use

    We pass this information between pages uses request query params. This function will collect them all from the
    URL, and optionally allows the caller to update or remove some of the options.

    To set a new value:
        _email_branding_flow_query_params(request, brand_type='org')

    To remove a value:
        _email_branding_flow_query_params(request, brand_type=None)

    These values can get passed to the `/_email` endpoint to generate a preview of a new brand.
    """
    return {k: kwargs.get(k, request.args.get(k)) for k in ("brand_type", "branding_choice", "colour", "logo")}


@main.route("/services/<uuid:service_id>/service-settings/email-branding/add-banner", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def email_branding_choose_banner_type(service_id):
    form = EmailBrandingChooseBanner()

    if form.validate_on_submit():
        if form.banner.data == "org":
            return redirect(
                url_for(
                    ".email_branding_upload_logo",
                    service_id=service_id,
                    **_email_branding_flow_query_params(request, brand_type=form.banner.data),
                )
            )

        elif form.banner.data == "org_banner":
            return redirect(
                url_for(
                    ".email_branding_choose_banner_colour",
                    service_id=service_id,
                    **_email_branding_flow_query_params(request, brand_type=form.banner.data),
                )
            )

    org_type = current_service.organisation_type
    back_link_fallback = ".email_branding_choose_logo" if org_type == "central" else ".service_settings"
    return (
        render_template(
            "views/service-settings/branding/add-new-branding/email-branding-choose-banner.html",
            form=form,
            back_link=url_for(
                request.args.get("back_link", back_link_fallback),
                service_id=current_service.id,
                **_email_branding_flow_query_params(request),
            ),
        ),
        400 if form.errors else 200,
    )


@main.route("/services/<uuid:service_id>/service-settings/email-branding/choose-banner-colour", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def email_branding_choose_banner_colour(service_id):
    form = EmailBrandingChooseBannerColour()

    if form.validate_on_submit():
        return redirect(
            url_for(
                ".email_branding_upload_logo",
                service_id=service_id,
                **_email_branding_flow_query_params(request, colour=form.hex_colour.data),
            )
        )

    abandon_flow_link = url_for(
        ".email_branding_something_else",
        service_id=current_service.id,
        back_link=".email_branding_choose_banner_colour",
        **_email_branding_flow_query_params(request),
    )
    return (
        render_template(
            "views/service-settings/branding/add-new-branding/email-branding-choose-banner-colour.html",
            form=form,
            back_link=url_for(
                ".email_branding_choose_banner_type",
                service_id=service_id,
                **_email_branding_flow_query_params(request),
            ),
            abandon_flow_link=abandon_flow_link,
        ),
        400 if form.errors else 200,
    )


@main.route("/services/<uuid:service_id>/service-settings/letter-branding", methods=["GET", "POST"])
@user_has_permissions("manage_service")
def letter_branding_request(service_id):
    form = ChooseLetterBrandingForm(current_service)
    from_template = request.args.get("from_template")
    if form.validate_on_submit():
        branding_choice = form.options.data

        if branding_choice in current_service.letter_branding_pool.ids:
            return redirect(
                url_for(".letter_branding_pool_option", service_id=current_service.id, branding_option=branding_choice)
            )

        ticket_message = render_template(
            "support-tickets/branding-request.txt",
            current_branding=current_service.letter_branding.name or "no",
            branding_requested=dict(form.options.choices)[form.options.data],
            detail=form.something_else.data,
        )
        ticket = NotifySupportTicket(
            subject=f"Letter branding request - {current_service.name}",
            message=ticket_message,
            ticket_type=NotifySupportTicket.TYPE_QUESTION,
            user_name=current_user.name,
            user_email=current_user.email_address,
            org_id=current_service.organisation_id,
            org_type=current_service.organisation_type,
            service_id=current_service.id,
        )
        zendesk_client.send_ticket_to_zendesk(ticket)
        flash((THANKS_FOR_BRANDING_REQUEST_MESSAGE), "default")
        return redirect(
            url_for(".view_template", service_id=current_service.id, template_id=from_template)
            if from_template
            else url_for(".service_settings", service_id=current_service.id)
        )

    return render_template(
        "views/service-settings/branding/letter-branding-options.html",
        form=form,
        from_template=from_template,
    )


@user_has_permissions("manage_service")
@main.route("/services/<uuid:service_id>/service-settings/letter-branding/pool", methods=["GET", "POST"])
def letter_branding_pool_option(service_id):
    try:
        chosen_branding = current_service.letter_branding_pool.get_item_by_id(request.args.get("branding_option"))
    except current_service.letter_branding_pool.NotFound:
        flash("No branding found for this id.")
        return redirect(url_for(".letter_branding_request", service_id=current_service.id))

    if request.method == "POST":
        current_service.update(letter_branding=chosen_branding.id)

        flash("You’ve updated your letter branding", "default")
        return redirect(url_for(".service_settings", service_id=current_service.id))

    return render_template(
        "views/service-settings/branding/letter-branding-pool-option.html",
        chosen_branding=chosen_branding,
    )


@main.route("/services/<uuid:service_id>/data-retention", methods=["GET"])
@user_is_platform_admin
def data_retention(service_id):
    return render_template(
        "views/service-settings/data-retention.html",
    )


@main.route("/services/<uuid:service_id>/data-retention/add", methods=["GET", "POST"])
@user_is_platform_admin
def add_data_retention(service_id):
    form = AdminServiceAddDataRetentionForm()
    if form.validate_on_submit():
        service_api_client.create_service_data_retention(
            service_id, form.notification_type.data, form.days_of_retention.data
        )
        return redirect(url_for(".data_retention", service_id=service_id))
    return render_template("views/service-settings/data-retention/add.html", form=form)


@main.route("/services/<uuid:service_id>/data-retention/<uuid:data_retention_id>/edit", methods=["GET", "POST"])
@user_is_platform_admin
def edit_data_retention(service_id, data_retention_id):
    data_retention_item = current_service.get_data_retention_item(data_retention_id)
    form = AdminServiceEditDataRetentionForm(days_of_retention=data_retention_item["days_of_retention"])
    if form.validate_on_submit():
        service_api_client.update_service_data_retention(service_id, data_retention_id, form.days_of_retention.data)
        return redirect(url_for(".data_retention", service_id=service_id))
    return render_template(
        "views/service-settings/data-retention/edit.html",
        form=form,
        data_retention_id=data_retention_id,
        notification_type=data_retention_item["notification_type"],
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


@main.route("/services/<uuid:service_id>/edit-billing-details", methods=["GET", "POST"])
@user_is_platform_admin
def edit_service_billing_details(service_id):
    form = AdminBillingDetailsForm(
        billing_contact_email_addresses=current_service.billing_contact_email_addresses,
        billing_contact_names=current_service.billing_contact_names,
        billing_reference=current_service.billing_reference,
        purchase_order_number=current_service.purchase_order_number,
        notes=current_service.notes,
    )

    if form.validate_on_submit():
        current_service.update(
            billing_contact_email_addresses=form.billing_contact_email_addresses.data,
            billing_contact_names=form.billing_contact_names.data,
            billing_reference=form.billing_reference.data,
            purchase_order_number=form.purchase_order_number.data,
            notes=form.notes.data,
        )
        return redirect(url_for(".service_settings", service_id=service_id))

    return render_template(
        "views/service-settings/edit-service-billing-details.html",
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
