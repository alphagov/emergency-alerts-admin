import base64
import os
import pathlib
from time import monotonic

import jinja2
from emergency_alerts_utils import logging, request_helper
from emergency_alerts_utils.sanitise_text import SanitiseASCII
from flask import (
    Flask,
    Response,
    current_app,
    flash,
    g,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import LoginManager, current_user
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError
from itsdangerous import BadSignature
from notifications_python_client.errors import HTTPError
from opentelemetry import trace
from werkzeug.exceptions import HTTPException as WerkzeugHTTPException
from werkzeug.exceptions import abort
from werkzeug.local import LocalProxy

from app import proxy_fix, webauthn_server
from app.asset_fingerprinter import asset_fingerprinter
from app.config import configs
from app.extensions import zendesk_client
from app.formatters import (
    convert_to_boolean,
    format_auth_type,
    format_date,
    format_date_human,
    format_date_normal,
    format_date_numeric,
    format_date_short,
    format_datetime,
    format_datetime_24h,
    format_datetime_human,
    format_datetime_normal,
    format_datetime_relative,
    format_datetime_short,
    format_day_of_week,
    format_delta,
    format_delta_days,
    format_mobile_networks,
    format_seconds_duration_as_time,
    format_thousands,
    format_time,
    format_yes_no,
    id_safe,
    iteration_count,
    message_count,
    message_count_label,
    message_count_noun,
    nl2br,
    parse_seconds_as_hours_and_minutes,
    redact_mobile_number,
    round_to_significant_figures,
    square_metres_to_square_miles,
    text_area_formatting,
    valid_phone_number,
)
from app.models.organisation import Organisation
from app.models.service import Service
from app.models.user import AnonymousUser, User
from app.navigation import (
    CaseworkNavigation,
    HeaderNavigation,
    MainNavigation,
    OrgNavigation,
)
from app.notify_client import InviteTokenError
from app.notify_client.admin_actions_api_client import admin_actions_api_client
from app.notify_client.api_key_api_client import api_key_api_client
from app.notify_client.broadcast_message_api_client import broadcast_message_api_client
from app.notify_client.events_api_client import events_api_client
from app.notify_client.feature_toggle_api_client import feature_toggle_api_client
from app.notify_client.invite_api_client import invite_api_client
from app.notify_client.org_invite_api_client import org_invite_api_client
from app.notify_client.organisations_api_client import organisations_client
from app.notify_client.reports_api_client import reports_api_client
from app.notify_client.service_api_client import service_api_client
from app.notify_client.status_api_client import status_api_client
from app.notify_client.template_api_client import template_api_client
from app.notify_client.template_folder_api_client import template_folder_api_client
from app.notify_client.user_api_client import user_api_client
from app.url_converters import (
    SimpleDateTypeConverter,
    TemplateTypeConverter,
    TicketTypeConverter,
)

login_manager = LoginManager()
csrf = CSRFProtect()

current_service = LocalProxy(lambda: g.current_service)

# The current organisation attached to the request stack.
current_organisation = LocalProxy(lambda: g.current_organisation)

current_service_status = LocalProxy(lambda: g.service_status_text)

content_nonce = LocalProxy(lambda: g.content_nonce)

navigation = {
    "casework_navigation": CaseworkNavigation(),
    "main_navigation": MainNavigation(),
    "header_navigation": HeaderNavigation(),
    "org_navigation": OrgNavigation(),
}


def create_app(application):
    notify_environment = os.environ["HOST"]

    application.config.from_object(configs[notify_environment])
    asset_fingerprinter._asset_root = application.config["ASSET_PATH"]

    init_app(application)

    if "extensions" not in application.jinja_options:
        application.jinja_options["extensions"] = []

    init_jinja(application)

    for client in (
        # Gubbins
        # Note, metrics purposefully first so we start measuring response times as early as possible before any
        # other `app.before_request` handlers (introduced by any of these clients) are processed (which would
        # otherwise mean we aren't measuring the full response time)
        csrf,
        login_manager,
        proxy_fix,
        request_helper,
        # API clients
        admin_actions_api_client,
        api_key_api_client,
        broadcast_message_api_client,
        events_api_client,
        feature_toggle_api_client,
        invite_api_client,
        org_invite_api_client,
        organisations_client,
        reports_api_client,
        service_api_client,
        status_api_client,
        template_api_client,
        template_folder_api_client,
        user_api_client,
        # External API clients
        zendesk_client,
    ):
        client.init_app(application)

    logging.init_app(application)
    webauthn_server.init_app(application)

    login_manager.login_view = "main.sign_in"
    login_manager.login_message_category = "default"
    login_manager.session_protection = None
    login_manager.anonymous_user = AnonymousUser

    setup_blueprints(application)

    add_template_filters(application)

    register_errorhandlers(application)

    setup_event_handlers()


def init_app(application: Flask):
    application.after_request(useful_headers_after_request)
    application.after_request(trace_id_after_request)

    application.before_request(inject_user_id_trace)
    application.before_request(load_service_before_request)
    application.before_request(load_organisation_before_request)
    application.before_request(load_service_status_before_request)
    application.before_request(generate_nonce_before_request)
    application.before_request(request_helper.check_proxy_header_before_request)

    font_paths = [
        str(item)[len(asset_fingerprinter._filesystem_path) :]
        for item in pathlib.Path(asset_fingerprinter._filesystem_path).glob("fonts/*.woff2")
    ]

    @application.context_processor
    def _attach_current_service():
        return {"current_service": current_service}

    @application.context_processor
    def _attach_current_organisation():
        return {"current_org": current_organisation}

    @application.context_processor
    def _attach_current_user():
        return {"current_user": current_user}

    @application.context_processor
    def _nav_selected():
        return navigation

    @application.before_request
    def record_start_time():
        g.start = monotonic()
        g.endpoint = request.endpoint

    @application.context_processor
    def inject_global_template_variables():
        return {
            "asset_path": application.config["ASSET_PATH"],
            "live_service_notice": current_service_status,
            "header_colour": application.config["HEADER_COLOUR"],
            "asset_url": asset_fingerprinter.get_url,
            "content_nonce": content_nonce,
            "font_paths": font_paths,
        }

    application.url_map.converters["uuid"].to_python = lambda self, value: value
    application.url_map.converters["template_type"] = TemplateTypeConverter
    application.url_map.converters["ticket_type"] = TicketTypeConverter
    application.url_map.converters["simple_date"] = SimpleDateTypeConverter


@login_manager.user_loader
def load_user(user_id):
    user = User.from_id(user_id)
    # Elevating to a platform admin is scoped to a session and isn't stored in the API
    if session.get("platform_admin_active", False):
        user.platform_admin_active = True

    return user


def load_service_before_request():
    g.current_service = None

    if "/static/" in request.url:
        return

    if request.view_args:
        service_id = request.view_args.get("service_id", session.get("service_id"))
    else:
        service_id = session.get("service_id")

    if service_id:
        try:
            g.current_service = Service.from_id(service_id)
        except HTTPError as exc:
            # if service id isn't real, then 404 rather than 500ing later because we expect service to be set
            if exc.status_code == 404:
                abort(404)
            else:
                raise


def load_organisation_before_request():
    g.current_organisation = None

    if "/static/" in request.url:
        return

    if request.view_args:
        org_id = request.view_args.get("org_id")

        if org_id:
            try:
                g.current_organisation = Organisation.from_id(org_id)
            except HTTPError as exc:
                # if org id isn't real, then 404 rather than 500ing later because we expect org to be set
                if exc.status_code == 404:
                    abort(404)
                else:
                    raise


def load_service_status_before_request():
    g.service_status_text = None

    if "/static/" in request.url:
        return

    service_is_not_live_flag = feature_toggle_api_client.get_feature_toggle("service_is_not_live")
    flag_enabled = service_is_not_live_flag.get("is_enabled", False)
    g.service_status_text = service_is_not_live_flag["display_html"] if flag_enabled else None


def generate_nonce_before_request():
    g.content_nonce = generate_nonce()


def generate_nonce():
    return base64.b64encode(os.urandom(16)).decode("utf-8")


#  https://www.owasp.org/index.php/List_of_useful_HTTP_headers
def useful_headers_after_request(response: Response):
    response.headers.add("X-Frame-Options", "deny")
    response.headers.add("X-Content-Type-Options", "nosniff")
    response.headers.add("X-XSS-Protection", "1; mode=block")
    response.headers.add(
        "Content-Security-Policy",
        (
            "default-src 'self' {asset_domain};"
            "report-to default;"
            "script-src 'self' {asset_domain} *.google-analytics.com 'nonce-{content_nonce}' 'unsafe-eval';"
            "style-src 'self' {asset_domain} 'nonce-{content_nonce}';"
            "connect-src 'self' *.google-analytics.com;"
            "object-src 'self';"
            "font-src 'self' {asset_domain} data:;"
            "img-src 'self' {asset_domain} *.tile.openstreetmap.org *.google-analytics.com data:;".format(
                asset_domain=current_app.config["ASSET_DOMAIN"], content_nonce=content_nonce
            )
        ),
    )
    response.headers.add("Strict-Transport-Security", "max-age=63072000; includeSubdomains; preload")
    response.headers.add(
        "Link",
        (
            "<{asset_url}>; rel=dns-prefetch, <{asset_url}>; rel=preconnect".format(
                asset_url=f'https://{current_app.config["ASSET_DOMAIN"]}'
            )
        ),
    )
    if "Cache-Control" in response.headers:
        del response.headers["Cache-Control"]
    response.headers.add("Cache-Control", "no-store, no-cache, private, must-revalidate")
    response.headers.add(
        "Reporting-Endpoints", f"default={current_app.config['ADMIN_EXTERNAL_URL']}{url_for('main.reports')}"
    )
    for key, value in response.headers:
        response.headers[key] = SanitiseASCII.encode(value)
    return response


def inject_user_id_trace():
    user_id = session.get("user_id", "(unknown)")
    span = trace.get_current_span()
    span.set_attribute("eas.user.id", session.get(user_id))


def trace_id_after_request(response: Response):
    span = trace.get_current_span()
    if span is not trace.INVALID_SPAN:
        # Convert to hex and strip out the 0x prefix
        trace_id = hex(span.get_span_context().trace_id)[2:]
        response.headers.add("X-EAS-Trace-Id", trace_id)

    return response


def register_errorhandlers(application):  # noqa (C901 too complex)
    def _error_response(error_code, error_page_template=None):
        if error_page_template is None:
            error_page_template = error_code
        resp = make_response(render_template("error/{0}.html".format(error_page_template)), error_code)
        return useful_headers_after_request(resp)

    @application.errorhandler(HTTPError)
    def render_http_error(error):
        application.logger.warning(
            "API {} failed with status {} message {}".format(
                error.response.url if error.response else "unknown", error.status_code, error.message
            )
        )
        error_code = error.status_code
        if error_code not in [401, 404, 403, 410]:
            # probably a 500 or 503.
            # it might be a 400, which we should handle as if it's an internal server error. If the API might
            # legitimately return a 400, we should handle that within the view or the client that calls it.
            application.logger.exception(
                "API {} failed with status {} message {}".format(
                    error.response.url if error.response else "unknown", error.status_code, error.message
                )
            )
            error_code = 500
        return _error_response(error_code)

    @application.errorhandler(400)
    def handle_client_error(error):
        # This is tripped if we call `abort(400)`.
        application.logger.exception("Unhandled 400 client error")
        return _error_response(400, error_page_template=500)

    @application.errorhandler(410)
    def handle_gone(error):
        return _error_response(410)

    @application.errorhandler(404)
    def handle_not_found(error):
        return _error_response(404)

    @application.errorhandler(403)
    def handle_not_authorized(error):
        return _error_response(403)

    @application.errorhandler(401)
    def handle_no_permissions(error):
        return _error_response(401)

    @application.errorhandler(BadSignature)
    def handle_bad_token(error):
        # if someone has a malformed token
        flash("There’s something wrong with the link you’ve used.")
        return _error_response(404)

    @application.errorhandler(CSRFError)
    def handle_csrf(reason):
        application.logger.warning("csrf.error_message: {}".format(reason))

        if "user_id" not in session:
            application.logger.warning("csrf.session_expired: Redirecting user to log in page")

            return application.login_manager.unauthorized()

        application.logger.warning(
            "csrf.invalid_token: Aborting request, user_id: {user_id}", extra={"user_id": session["user_id"]}
        )

        return _error_response(400, error_page_template=500)

    @application.errorhandler(405)
    def handle_method_not_allowed(error):
        return _error_response(405, error_page_template=500)

    @application.errorhandler(429)
    def handle_login_throttling(error):
        return _error_response(429)

    @application.errorhandler(WerkzeugHTTPException)
    def handle_http_error(error):
        if error.code == 301:
            # PermanentRedirect exception
            return error

        return _error_response(error.code)

    @application.errorhandler(InviteTokenError)
    def handle_bad_invite_token(error):
        flash(str(error))
        return redirect(url_for("main.sign_in"))

    @application.errorhandler(500)
    @application.errorhandler(Exception)
    def handle_bad_request(error):
        current_app.logger.exception(error)
        # We want the Flask in browser stacktrace
        if current_app.config.get("DEBUG", None):
            raise error
        return _error_response(500)


def setup_blueprints(application):
    """
    There are two blueprints: status_blueprint, and main_blueprint.

    main_blueprint is the default for everything.

    status_blueprint is only for the status page - unauthenticated, unstyled, no cookies, etc.
    """
    from app.main import main as main_blueprint
    from app.status import status as status_blueprint

    application.register_blueprint(main_blueprint)
    application.register_blueprint(status_blueprint)


def setup_event_handlers():
    from flask_login import user_logged_in

    from app.event_handlers import on_user_logged_in

    user_logged_in.connect(on_user_logged_in)


def add_template_filters(application):
    for fn in [
        convert_to_boolean,
        format_auth_type,
        format_date,
        format_date_human,
        format_date_normal,
        format_date_numeric,
        format_date_short,
        format_datetime,
        format_datetime_24h,
        format_datetime_human,
        format_datetime_normal,
        format_datetime_relative,
        format_datetime_short,
        format_day_of_week,
        format_delta,
        format_delta_days,
        format_mobile_networks,
        format_seconds_duration_as_time,
        format_thousands,
        format_time,
        format_yes_no,
        id_safe,
        iteration_count,
        message_count,
        message_count_label,
        message_count_noun,
        nl2br,
        parse_seconds_as_hours_and_minutes,
        redact_mobile_number,
        round_to_significant_figures,
        square_metres_to_square_miles,
        valid_phone_number,
        text_area_formatting,
    ]:
        application.add_template_filter(fn)


def init_jinja(application):
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    template_folders = [
        os.path.join(repo_root, "app/templates"),
    ]

    application.jinja_loader = jinja2.ChoiceLoader(
        [
            jinja2.FileSystemLoader(template_folders),
            jinja2.PrefixLoader({"govuk_frontend_jinja": jinja2.PackageLoader("govuk_frontend_jinja")}),
        ]
    )

    application.jinja_env.add_extension("jinja2.ext.do")
