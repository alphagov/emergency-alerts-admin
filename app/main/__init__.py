from flask import Blueprint, request, session

main = Blueprint("main", __name__)

# Endpoints that must not write the session. The browser leaves out our SameSite=Strict session cookie when another
# site starts the navigation (e.g. a link clicked in webmail). A cookie set in reply would replace the user's real one
# and sign them out.
SESSION_WRITE_EXEMPT_ENDPOINTS = {"main.user_profile_email_confirm"}


def make_session_permanent():
    if request.endpoint in SESSION_WRITE_EXEMPT_ENDPOINTS:
        return
    session.permanent = True


def save_service_or_org_after_request(response):
    # Only save the current session if the request is 200
    service_id = request.view_args.get("service_id", None) if request.view_args else None
    organisation_id = request.view_args.get("org_id", None) if request.view_args else None
    if response.status_code == 200:
        if service_id:
            session["service_id"] = service_id
            session["organisation_id"] = None
        elif organisation_id:
            session["service_id"] = None
            session["organisation_id"] = organisation_id
    return response


main.before_request(make_session_permanent)
main.after_request(save_service_or_org_after_request)


from app.main.views import (  # noqa isort:skip
    add_service,
    api_keys,
    broadcast,
    broadcast_common,
    choose_account,
    code_not_received,
    dashboard,
    find_services,
    find_users,
    forgot_password,
    history,
    index,
    invites,
    manage_users,
    new_password,
    organisations,
    platform_admin,
    register,
    reports,
    security_policy,
    service_settings,
    sign_in,
    sign_out,
    support,
    templates,
    two_factor,
    user_profile,
    verify,
    webauthn_credentials,
)
