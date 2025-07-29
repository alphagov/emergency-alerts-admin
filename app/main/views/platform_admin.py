import dataclasses
import uuid
from datetime import datetime, timezone
from typing import Optional

from emergency_alerts_utils.admin_action import (
    ADMIN_ELEVATE_USER,
    ADMIN_STATUS_APPROVED,
    ADMIN_STATUS_PENDING,
)
from emergency_alerts_utils.api_key import KEY_TYPE_DESCRIPTIONS
from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user
from notifications_python_client.errors import HTTPError

from app import service_api_client, user_api_client
from app.main import main
from app.main.forms import DateFilterForm, PlatformAdminSearch
from app.models.service import Service
from app.notify_client.admin_actions_api_client import admin_actions_api_client
from app.notify_client.platform_admin_api_client import admin_api_client
from app.utils.admin_action import (
    create_or_replace_admin_action,
    process_admin_action,
    send_elevated_notifications,
    send_notifications,
)
from app.utils.user import user_is_platform_admin, user_is_platform_admin_capable
from app.utils.user_permissions import broadcast_permission_options, permission_options

COMPLAINT_THRESHOLD = 0.02
FAILURE_THRESHOLD = 3
ZERO_FAILURE_THRESHOLD = 0


@main.route("/find-services-by-name", methods=["GET"])
@main.route("/find-users-by-email", methods=["GET"])
@user_is_platform_admin
def redirect_old_search_pages():
    return redirect(url_for(".platform_admin_search"))


@main.route("/platform-admin", methods=["GET", "POST"])
@user_is_platform_admin_capable
def platform_admin_search():
    users, services = [], []
    search_form = PlatformAdminSearch()

    if search_form.validate_on_submit():
        users, services, redirect_to_something_url = [
            user_api_client.find_users_by_full_or_partial_email(search_form.search.data)["data"],
            service_api_client.find_services_by_name(search_form.search.data)["data"],
            get_url_for_notify_record(search_form.search.data),
        ]

        if redirect_to_something_url:
            return redirect(redirect_to_something_url)

    return render_template(
        "views/platform-admin/search.html",
        search_form=search_form,
        show_results=search_form.is_submitted() and search_form.search.data,
        users=users,
        services=services,
    )


@main.route("/platform-admin/summary")
@user_is_platform_admin
def platform_admin():
    form = DateFilterForm(request.args, meta={"csrf": False})
    api_args = {}

    form.validate()

    if form.start_date.data:
        api_args["start_date"] = form.start_date.data
        api_args["end_date"] = form.end_date.data or datetime.now(timezone.utc).date()

    return render_template("views/platform-admin/index.html", form=form)


@main.route("/platform-admin/live-services", endpoint="live_services")
@main.route("/platform-admin/trial-services", endpoint="trial_services")
@user_is_platform_admin
def platform_admin_services():
    form = DateFilterForm(request.args)
    if all(
        (
            request.args.get("include_from_test_key") is None,
            request.args.get("start_date") is None,
            request.args.get("end_date") is None,
        )
    ):
        # Default to True if the user hasn’t done any filtering,
        # otherwise respect their choice
        form.include_from_test_key.data = True

    include_from_test_key = form.include_from_test_key.data
    api_args = {
        # "detailed": True,
        "only_active": False,  # specifically DO get inactive services
        "include_from_test_key": include_from_test_key,
    }

    if form.start_date.data:
        api_args["start_date"] = form.start_date.data
        api_args["end_date"] = form.end_date.data or datetime.now(timezone.utc).date()

    services = filter_and_sort_services(
        service_api_client.get_services(api_args)["data"],
        trial_mode_services=request.endpoint == "main.trial_services",
    )

    return render_template(
        "views/platform-admin/services.html",
        include_from_test_key=include_from_test_key,
        form=form,
        services=list(format_service_data(services)),
        page_title=f"{'Trial mode' if request.endpoint == 'main.trial_services' else 'Live'} services",
    )


@main.route("/platform-admin/admin-actions", endpoint="admin_actions")
@user_is_platform_admin_capable
def platform_admin_actions():
    pending_actions = admin_actions_api_client.get_pending_admin_actions()

    return render_template(
        "views/platform-admin/admin-actions.html",
        **pending_actions,
        permission_labels=dict(permission_options + broadcast_permission_options),
        key_type_labels=KEY_TYPE_DESCRIPTIONS,
        allow_self_approval=current_app.config["ADMIN_ACTION_ALLOW_SELF_APPROVAL"],
    )


@main.route(
    "/platform-admin/admin-actions/<uuid:action_id>/review/<new_status>",
    endpoint="review_admin_action",
    methods=["POST"],
)
@user_is_platform_admin_capable
def platform_review_admin_action(action_id, new_status):
    action = admin_actions_api_client.get_admin_action_by_id(action_id)

    if action["status"] != ADMIN_STATUS_PENDING:
        flash("That action is not pending and cannot be reviewed")
    elif (
        not current_app.config["ADMIN_ACTION_ALLOW_SELF_APPROVAL"]
        and new_status == "approved"
        and action["created_by"] == current_user.id
    ):
        flash("You cannot approve your own admin approvals")
    else:
        service = Service.from_id(action["service_id"]) if bool(action.get("service_id")) else None
        send_notifications(new_status, action, service)

        admin_actions_api_client.review_admin_action(action_id, new_status)

        if new_status == ADMIN_STATUS_APPROVED:
            current_app.logger.info("Approving and fulfilling admin action", extra={"admin_action": action})
            # Now we need to 'do' the thing we've approved
            return process_admin_action(action)

    return redirect(url_for(".admin_actions"))


@main.route("/platform-admin/request-elevation", endpoint="platform_admin_request_elevation", methods=["GET", "POST"])
@user_is_platform_admin_capable
def platform_admin_request_elevation():
    if current_user.has_pending_platform_admin_elevation:
        # It has been approved already, just prompt the user elevate without signing out
        return redirect(url_for(".platform_admin_elevation"))

    if request.method == "POST":
        action = {
            "created_by": current_user.id,
            "action_type": ADMIN_ELEVATE_USER,
            "action_data": {},
        }
        create_or_replace_admin_action(action)
        flash("An admin approval has been created", "default_with_tick")
        return redirect(url_for(".admin_actions"))

    pending_actions = admin_actions_api_client.get_pending_admin_actions()["pending"]
    has_pending_elevation_request = [
        x for x in pending_actions if x["action_type"] == ADMIN_ELEVATE_USER and x["created_by"] == str(current_user.id)
    ]

    return render_template(
        "views/platform-admin/request-elevation.html",
        has_pending_elevation_request=has_pending_elevation_request,
    )


@main.route("/platform-admin/elevation", endpoint="platform_admin_elevation", methods=["GET", "POST"])
@user_is_platform_admin_capable
def platform_admin_elevation():
    # Assert they are actually due to become an admin
    if not current_user.has_pending_platform_admin_elevation:
        flash("You do not have a pending platform admin elevation")
        return abort(403)

    if request.method == "POST":
        # Mark the user as platform admin for the session
        user_api_client.redeem_admin_elevation(current_user.id)
        current_user.platform_admin_active = True
        session["platform_admin_active"] = True
        send_elevated_notifications()
        return redirect(url_for("main.platform_admin_search"))

    return render_template(
        "views/platform-admin/sign-in-elevation.html", platform_admin_redemption=current_user.platform_admin_redemption
    )


def get_url_for_notify_record(uuid_):
    @dataclasses.dataclass
    class _EndpointSpec:
        endpoint: str
        param: Optional[str] = None
        with_service_id: bool = False

        # Extra parameters to pass to `url_for`.
        extra: dict = dataclasses.field(default_factory=lambda: {})

    try:
        uuid.UUID(uuid_)
    except ValueError:
        return None

    result, found = None, False
    try:
        result = admin_api_client.find_by_uuid(uuid_)
        found = True
    except HTTPError as e:
        if e.status_code != 404:
            raise e

    if result and found:
        url_for_data = {
            "organisation": _EndpointSpec(".organisation_dashboard", "org_id"),
            "service": _EndpointSpec(".service_dashboard", "service_id"),
            "template": _EndpointSpec("main.view_template", "template_id", with_service_id=True),
            "user": _EndpointSpec(".user_information", "user_id"),
            "api_key": _EndpointSpec(".api_keys", with_service_id=True),
            "template_folder": _EndpointSpec(".choose_template", "template_folder_id", with_service_id=True),
        }
        if not (spec := url_for_data.get(result["type"])):
            raise KeyError(f"Don't know how to redirect to {result['type']}")

        url_for_kwargs = {"endpoint": spec.endpoint, **spec.extra}

        if spec.param:
            url_for_kwargs[spec.param] = uuid_

        if spec.with_service_id:
            url_for_kwargs["service_id"] = result["context"]["service_id"]

        return url_for(**url_for_kwargs)

    return None


def sum_service_usage(service):
    total = 0
    for notification_type in service["statistics"].keys():
        total += service["statistics"][notification_type]["requested"]
    return total


def filter_and_sort_services(services, trial_mode_services=False):
    return [
        service
        for service in sorted(
            services,
            key=lambda service: (service["active"], service["created_at"]),
            reverse=True,
        )
        if service["restricted"] == trial_mode_services
    ]


def format_service_data(services):
    for service in services:
        yield {
            "id": service["id"],
            "name": service["name"],
            "restricted": service["restricted"],
            "created_at": service["created_at"],
            "active": service["active"],
        }
