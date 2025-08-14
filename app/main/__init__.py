from flask import Blueprint, request, session

main = Blueprint("main", __name__)


def make_session_permanent():
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
    choose_account,
    code_not_received,
    common,
    dashboard,
    feedback,
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
    templates,
    two_factor,
    user_profile,
    verify,
    webauthn_credentials,
)
