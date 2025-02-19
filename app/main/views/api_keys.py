from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from markupsafe import Markup

from app import api_key_api_client, current_service, service_api_client
from app.main import main
from app.main.forms import CreateKeyForm
from app.notify_client.admin_actions_api_client import admin_actions_api_client
from app.notify_client.api_key_api_client import KEY_TYPE_DESCRIPTIONS, KEY_TYPE_NORMAL
from app.utils.admin_action import ADMIN_CREATE_API_KEY
from app.utils.user import user_has_permissions

dummy_bearer_token = "bearer_token_set"


@main.route(
    "/services/<uuid:service_id>/api/keys",
)
@user_has_permissions("manage_api_keys")
def api_keys(service_id):
    return render_template("views/api/keys.html", key_type_descriptions=KEY_TYPE_DESCRIPTIONS)


@main.route("/services/<uuid:service_id>/api/keys/create", methods=["GET", "POST"])
@user_has_permissions("manage_api_keys")
def create_api_key(service_id):
    form = CreateKeyForm(current_service.api_keys)
    form.key_type.choices = [(type, description) for type, description in KEY_TYPE_DESCRIPTIONS.items()]
    # preserve order of items extended by starting with empty dicts
    form.key_type.param_extensions = {"items": [{}, {}]}
    if current_service.trial_mode:
        form.key_type.param_extensions["items"][0] = {
            "disabled": True,
            "hint": {
                "html": Markup(
                    "Not available because your service is in "
                    '<a class="govuk-link govuk-link--no-visited-state" '
                    'href="/features/training-mode">training mode</a>'
                )
            },
        }
    if form.validate_on_submit():
        if current_service.trial_mode and form.key_type.data == KEY_TYPE_NORMAL:
            abort(400)
        action = {
            "service_id": current_service.id,
            "created_by": current_user.id,
            "action_type": ADMIN_CREATE_API_KEY,
            "action_data": {
                "key_type": form.key_type.data,
                "key_name": form.key_name.data,
            },
        }
        admin_actions_api_client.create_admin_action(action)
        flash("An admin approval has been created", "default_with_tick")
        return redirect(url_for(".api_keys", service_id=service_id))
    return render_template("views/api/keys/create.html", form=form)


@main.route("/services/<uuid:service_id>/api/keys/revoke/<uuid:key_id>", methods=["GET", "POST"])
@user_has_permissions("manage_api_keys")
def revoke_api_key(service_id, key_id):
    key_name = current_service.get_api_key(key_id)["name"]
    if request.method == "GET":
        flash(
            [
                "Are you sure you want to revoke ‘{}’?".format(key_name),
                "You will not be able to use this API key to connect to GOV.UK Notify.",
            ],
            "revoke this API key",
        )
        return render_template("views/api/keys.html", key_type_descriptions=KEY_TYPE_DESCRIPTIONS)
    elif request.method == "POST":
        api_key_api_client.revoke_api_key(service_id=service_id, key_id=key_id)
        flash("‘{}’ was revoked".format(key_name), "default_with_tick")
        return redirect(url_for(".api_keys", service_id=service_id))


def get_apis():
    callback_api = None
    if current_service.service_callback_api:
        callback_api = service_api_client.get_service_callback_api(
            current_service.id, current_service.service_callback_api[0]
        )

    return callback_api


def check_token_against_dummy_bearer(token):
    if token != dummy_bearer_token:
        return token
    else:
        return ""


def get_delivery_status_callback_details():
    if current_service.service_callback_api:
        return service_api_client.get_service_callback_api(current_service.id, current_service.service_callback_api[0])
