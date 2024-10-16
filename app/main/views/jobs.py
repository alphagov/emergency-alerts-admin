# -*- coding: utf-8 -*-

from functools import partial

from emergency_alerts_utils.template import (
    EmailPreviewTemplate,
    LetterPreviewTemplate,
    SMSBodyPreviewTemplate,
)
from flask import Response, abort, jsonify, render_template, request, url_for
from flask_login import current_user
from markupsafe import Markup

from app import current_service, notification_api_client, service_api_client
from app.main import main
from app.main.forms import SearchNotificationsForm
from app.utils import parse_filter_args, set_status_filters
from app.utils.csv import generate_notifications_csv
from app.utils.pagination import (
    generate_next_dict,
    generate_previous_dict,
    get_page_from_request,
)
from app.utils.user import user_has_permissions


@main.route("/services/<uuid:service_id>/notifications", methods=["GET", "POST"])
@main.route("/services/<uuid:service_id>/notifications/<template_type:message_type>", methods=["GET", "POST"])
@user_has_permissions()
def view_notifications(service_id, message_type=None):
    return render_template(
        "views/notifications.html",
        partials=get_notifications(service_id, message_type),
        message_type=message_type,
        status=request.args.get("status") or "sending,delivered,failed",
        page=request.args.get("page", 1),
        search_form=SearchNotificationsForm(
            message_type=message_type,
            to=request.form.get("to"),
        ),
        things_you_can_search_by={
            "email": ["email address"],
            "sms": ["phone number"],
            "letter": ["postal address", "file name"],
            # We say recipient here because combining all 3 types, plus
            # reference gets too long for the hint text
            None: ["recipient"],
        }.get(message_type)
        + {
            True: ["reference"],
            False: [],
        }.get(bool(current_service.api_keys)),
        download_link=url_for(
            ".download_notifications_csv",
            service_id=current_service.id,
            message_type=message_type,
            status=request.args.get("status"),
        ),
    )


@main.route("/services/<uuid:service_id>/notifications.json", methods=["GET", "POST"])
@main.route("/services/<uuid:service_id>/notifications/<template_type:message_type>.json", methods=["GET", "POST"])
@user_has_permissions()
def get_notifications_as_json(service_id, message_type=None):
    return jsonify(get_notifications(service_id, message_type, status_override=request.args.get("status")))


@main.route("/services/<uuid:service_id>/notifications.csv", endpoint="view_notifications_csv")
@main.route(
    "/services/<uuid:service_id>/notifications/<template_type:message_type>.csv", endpoint="view_notifications_csv"
)
@user_has_permissions()
def get_notifications(service_id, message_type, status_override=None):
    # TODO get the api to return count of pages as well.
    page = get_page_from_request()
    if page is None:
        abort(404, "Invalid page argument ({}).".format(request.args.get("page")))
    filter_args = parse_filter_args(request.args)
    filter_args["status"] = set_status_filters(filter_args)
    service_data_retention_days = None
    search_term = request.form.get("to", "")

    if message_type is not None:
        service_data_retention_days = current_service.get_days_of_retention(message_type)

    if request.path.endswith("csv") and current_user.has_permissions("view_activity"):
        return Response(
            generate_notifications_csv(
                service_id=service_id,
                page=page,
                page_size=5000,
                template_type=[message_type],
                status=filter_args.get("status"),
                limit_days=service_data_retention_days,
            ),
            mimetype="text/csv",
            headers={"Content-Disposition": 'inline; filename="notifications.csv"'},
        )
    notifications = notification_api_client.get_notifications_for_service(
        service_id=service_id,
        page=page,
        template_type=[message_type] if message_type else [],
        status=filter_args.get("status"),
        limit_days=service_data_retention_days,
        to=search_term,
    )
    url_args = {"message_type": message_type, "status": request.args.get("status")}
    prev_page = None

    if "links" in notifications and notifications["links"].get("prev", None):
        prev_page = generate_previous_dict("main.view_notifications", service_id, page, url_args=url_args)
    next_page = None

    if "links" in notifications and notifications["links"].get("next", None):
        next_page = generate_next_dict("main.view_notifications", service_id, page, url_args)

    if message_type:
        download_link = url_for(
            ".view_notifications_csv",
            service_id=current_service.id,
            message_type=message_type,
            status=request.args.get("status"),
        )
    else:
        download_link = None

    return {
        "service_data_retention_days": service_data_retention_days,
        "counts": render_template(
            "views/activity/counts.html",
            status=request.args.get("status"),
            status_filters=get_status_filters(
                current_service,
                message_type,
                service_api_client.get_service_statistics(service_id, limit_days=service_data_retention_days),
            ),
        ),
        "notifications": render_template(
            "views/activity/notifications.html",
            notifications=list(add_preview_of_content_to_notifications(notifications["notifications"])),
            page=page,
            limit_days=service_data_retention_days,
            prev_page=prev_page,
            next_page=next_page,
            show_pagination=(not search_term),
            status=request.args.get("status"),
            message_type=message_type,
            download_link=download_link,
            single_notification_url=partial(
                url_for,
                ".view_notification",
                service_id=current_service.id,
            ),
        ),
    }


def get_status_filters(service, message_type, statistics):
    if message_type is None:
        stats = {
            key: sum(statistics[message_type][key] for message_type in {"email", "sms", "letter"})
            for key in {"requested", "delivered", "failed"}
        }
    else:
        stats = statistics[message_type]
    stats["sending"] = stats["requested"] - stats["delivered"] - stats["failed"]

    filters = [
        # key, label, option
        ("requested", "total", "sending,delivered,failed"),
        ("sending", "sending", "sending"),
        ("delivered", "delivered", "delivered"),
        ("failed", "failed", "failed"),
    ]
    return [
        # return list containing label, option, link, count
        (
            label,
            option,
            url_for(".view_notifications", service_id=service.id, message_type=message_type, status=option),
            stats[key],
        )
        for key, label, option in filters
    ]


def add_preview_of_content_to_notifications(notifications):
    for notification in notifications:
        yield dict(preview_of_content=get_preview_of_content(notification), **notification)


def get_preview_of_content(notification):
    if notification["template"].get("redact_personalisation"):
        notification["personalisation"] = {}

    if notification["template"]["is_precompiled_letter"]:
        return notification["client_reference"]

    if notification["template"]["template_type"] == "sms":
        return str(
            SMSBodyPreviewTemplate(
                notification["template"],
                notification["personalisation"],
            )
        )

    if notification["template"]["template_type"] == "email":
        return Markup(
            EmailPreviewTemplate(
                notification["template"],
                notification["personalisation"],
                redact_missing_personalisation=True,
            ).subject
        )

    if notification["template"]["template_type"] == "letter":
        return Markup(
            LetterPreviewTemplate(
                notification["template"],
                notification["personalisation"],
            ).subject
        )
