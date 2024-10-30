import dataclasses
import itertools
import uuid
from collections import OrderedDict
from datetime import datetime
from typing import Optional

from flask import flash, redirect, render_template, request, url_for
from notifications_python_client.errors import HTTPError

from app import service_api_client, user_api_client
from app.extensions import redis_client
from app.main import main
from app.main.forms import AdminClearCacheForm, DateFilterForm, PlatformAdminSearch
from app.notify_client.platform_admin_api_client import admin_api_client
from app.utils.user import user_is_platform_admin

COMPLAINT_THRESHOLD = 0.02
FAILURE_THRESHOLD = 3
ZERO_FAILURE_THRESHOLD = 0


@main.route("/find-services-by-name", methods=["GET"])
@main.route("/find-users-by-email", methods=["GET"])
@user_is_platform_admin
def redirect_old_search_pages():
    return redirect(url_for(".platform_admin_search"))


@main.route("/platform-admin", methods=["GET", "POST"])
@user_is_platform_admin
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
        api_args["end_date"] = form.end_date.data or datetime.utcnow().date()

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
        api_args["end_date"] = form.end_date.data or datetime.utcnow().date()

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


@main.route("/platform-admin/clear-cache", methods=["GET", "POST"])
@user_is_platform_admin
def clear_cache():
    # note: `service-{uuid}-templates` cache is cleared for both services and templates.
    CACHE_KEYS = OrderedDict(
        [
            (
                "user",
                [
                    "user-????????-????-????-????-????????????",
                ],
            ),
            (
                "service",
                [
                    "has_jobs-????????-????-????-????-????????????",
                    "service-????????-????-????-????-????????????",
                    "service-????????-????-????-????-????????????-templates",
                    "service-????????-????-????-????-????????????-data-retention",
                    "service-????????-????-????-????-????????????-template-folders",
                ],
            ),
            (
                "template",
                [
                    "service-????????-????-????-????-????????????-templates",
                    "service-????????-????-????-????-????????????-template-????????-????-????-????-????????????-version-*",  # noqa
                    "service-????????-????-????-????-????????????-template-????????-????-????-????-????????????-versions",  # noqa
                ],
            ),
            (
                "organisation",
                [
                    "organisations",
                    "domains",
                    "live-service-and-organisation-counts",
                    "organisation-????????-????-????-????-????????????-name",
                ],
            ),
            (
                "broadcast",
                [
                    "service-????????-????-????-????-????????????-broadcast-message-????????-????-????-????-????????????",  # noqa
                ],
            ),
        ]
    )

    form = AdminClearCacheForm()

    form.model_type.choices = [(key, key.replace("_", " ").title()) for key in CACHE_KEYS]

    if form.validate_on_submit():
        group_keys = form.model_type.data
        groups = map(CACHE_KEYS.get, group_keys)
        patterns = list(itertools.chain(*groups))

        num_deleted = sum(redis_client.delete_by_pattern(pattern) for pattern in patterns)

        msg = f"Removed {num_deleted} objects across {len(patterns)} key formats " f'for {", ".join(group_keys)}'

        flash(msg, category="default")

    return render_template("views/platform-admin/clear-cache.html", form=form)


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
            "notification": _EndpointSpec("main.view_notification", "notification_id", with_service_id=True),
            "template": _EndpointSpec("main.view_template", "template_id", with_service_id=True),
            "user": _EndpointSpec(".user_information", "user_id"),
            "provider": _EndpointSpec(".view_provider", "provider_id"),
            "reply_to_email": _EndpointSpec(".service_edit_email_reply_to", "reply_to_email_id", with_service_id=True),
            "job": _EndpointSpec(".view_job", "job_id", with_service_id=True),
            "service_contact_list": _EndpointSpec(".contact_list", "contact_list_id", with_service_id=True),
            "service_data_retention": _EndpointSpec(".edit_data_retention", "data_retention_id", with_service_id=True),
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
