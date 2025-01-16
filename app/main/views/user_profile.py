import json

from emergency_alerts_utils.url_safe_token import check_token
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

from app import user_api_client
from app.main import main
from app.main.forms import (
    ChangeEmailForm,
    ChangeMobileNumberForm,
    ChangeNameForm,
    ChangePasswordForm,
    ChangeSecurityKeyNameForm,
    ConfirmPasswordForm,
    ServiceOnOffSettingForm,
    TwoFactorForm,
)
from app.models.user import User
from app.models.webauthn_credential import WebAuthnCredential
from app.utils.user import user_is_gov_user, user_is_logged_in

NEW_EMAIL = "new-email"
NEW_MOBILE = "new-mob"
NEW_MOBILE_PASSWORD_CONFIRMED = "new-mob-password-confirmed"
NEW_NAME = "new-name"


@main.route("/user-profile")
@user_is_logged_in
def user_profile():
    return render_template(
        "views/user-profile.html",
        can_see_edit=current_user.is_gov_user,
    )


@main.route("/user-profile/name", methods=["GET", "POST"])
@user_is_logged_in
def user_profile_name():
    def _check_password(pwd):
        return user_api_client.verify_password(current_user.id, pwd)

    form = ChangeNameForm(_check_password, new_name=current_user.name)

    if form.validate_on_submit():
        current_user.update(name=form.new_name.data)
        return redirect(url_for(".user_profile"))

    return render_template(
        "views/user-profile/change.html", thing="name", form=form, security_detail_field=form.new_name
    )


@main.route("/user-profile/email", methods=["GET", "POST"])
@user_is_logged_in
@user_is_gov_user
def user_profile_email():
    def _check_password(pwd):
        return user_api_client.verify_password(current_user.id, pwd)

    form = ChangeEmailForm(User.already_registered, _check_password, email_address=current_user.email_address)

    try:
        if form.validate_on_submit():
            user_api_client.send_change_email_verification(current_user.id, form.email_address.data)
            return render_template("views/change-email-continue.html", new_email=form.email_address.data)

    except HTTPError as e:
        if e.status_code == 400:
            form.email_address.errors.append(e.message[0])
            return render_template(
                "views/user-profile/change.html",
                thing="email address",
                form=form,
                security_detail_field=form.email_address,
            )
    return render_template(
        "views/user-profile/change.html", thing="email address", form=form, security_detail_field=form.email_address
    )


@main.route("/user-profile/email/confirm/<token>", methods=["GET"])
@user_is_logged_in
def user_profile_email_confirm(token):
    token_data = check_token(
        token,
        current_app.config["SECRET_KEY"],
        current_app.config["DANGEROUS_SALT"],
        current_app.config["EMAIL_EXPIRY_SECONDS"],
    )
    token_data = json.loads(token_data)
    user = User.from_id(token_data["user_id"])
    user.update(email_address=token_data["email"])
    session.pop(NEW_EMAIL, None)

    return redirect(url_for(".user_profile"))


@main.route("/user-profile/mobile-number", methods=["GET", "POST"])
@main.route("/user-profile/mobile-number/delete", methods=["GET"], endpoint="user_profile_confirm_delete_mobile_number")
@user_is_logged_in
def user_profile_mobile_number():
    user = User.from_id(current_user.id)

    def _check_password(pwd):
        return user_api_client.verify_password(current_user.id, pwd)

    form = ChangeMobileNumberForm(_check_password, mobile_number=current_user.mobile_number)

    if form.validate_on_submit():
        session[NEW_MOBILE] = form.mobile_number.data
        session[NEW_MOBILE_PASSWORD_CONFIRMED] = True
        current_user.send_verify_code(to=session[NEW_MOBILE])
        return redirect(url_for(".user_profile_mobile_number_confirm"))

    if request.endpoint == "main.user_profile_confirm_delete_mobile_number":
        flash("Are you sure you want to delete your mobile number from Emergency Alerts?", "delete")

    return render_template(
        "views/user-profile/change.html",
        thing="mobile number",
        form=form,
        user_auth=user.auth_type,
        security_detail_field=form.mobile_number,
    )


@main.route("/user-profile/mobile-number/delete", methods=["POST"])
@user_is_logged_in
def user_profile_mobile_number_delete():
    if current_user.auth_type != "email_auth":
        abort(403)

    current_user.update(mobile_number=None)

    return redirect(url_for(".user_profile"))


@main.route("/user-profile/mobile-number/confirm", methods=["GET", "POST"])
@user_is_logged_in
def user_profile_mobile_number_confirm():
    # Validate verify code for form
    def _check_code(cde):
        return user_api_client.check_verify_code(current_user.id, cde, "sms")

    if NEW_MOBILE_PASSWORD_CONFIRMED not in session:
        return redirect(url_for(".user_profile_mobile_number"))

    form = TwoFactorForm(_check_code)

    if form.validate_on_submit():
        current_user.refresh_session_id()
        mobile_number = session[NEW_MOBILE]
        del session[NEW_MOBILE]
        del session[NEW_MOBILE_PASSWORD_CONFIRMED]
        current_user.update(mobile_number=mobile_number)
        return redirect(url_for(".user_profile"))

    return render_template("views/user-profile/confirm.html", form_field=form.sms_code, thing="mobile number")


@main.route("/user-profile/password", methods=["GET", "POST"])
@user_is_logged_in
def user_profile_password():
    # Validate password for form
    def _check_password(pwd):
        return user_api_client.verify_password(current_user.id, pwd)

    form = ChangePasswordForm(_check_password)

    if form.validate_on_submit():
        try:
            user_api_client.check_password_is_valid(current_user.id, form.new_password.data)
        except HTTPError as e:
            if e.status_code == 400:
                form.new_password.errors.append(e.message[0])
                return render_template("views/user-profile/change-password.html", form=form)
        user_api_client.update_password(current_user.id, password=form.new_password.data)
        return redirect(url_for(".user_profile"))

    return render_template("views/user-profile/change-password.html", form=form)


@main.route("/user-profile/disable-platform-admin-view", methods=["GET", "POST"])
@user_is_logged_in
def user_profile_disable_platform_admin_view():
    if not current_user.platform_admin and not session.get("disable_platform_admin_view"):
        abort(403)

    form = ServiceOnOffSettingForm(
        name="Use platform admin view",
        enabled=not session.get("disable_platform_admin_view"),
        truthy="Yes",
        falsey="No",
    )

    form.enabled.param_extensions = {"hint": {"text": "Signing in again clears this setting"}}

    if form.validate_on_submit():
        session["disable_platform_admin_view"] = not form.enabled.data
        return redirect(url_for(".user_profile"))

    return render_template("views/user-profile/disable-platform-admin-view.html", form=form)


@main.route("/user-profile/security-keys", methods=["GET"])
@user_is_logged_in
def user_profile_security_keys():
    if not current_user.can_use_webauthn:
        abort(403)

    return render_template(
        "views/user-profile/security-keys.html",
    )


@main.route(
    "/user-profile/security-keys/<uuid:key_id>/manage",
    methods=["GET", "POST"],
    endpoint="user_profile_manage_security_key",
)
@main.route(
    "/user-profile/security-keys/<uuid:key_id>/delete",
    methods=["GET"],
    endpoint="user_profile_confirm_delete_security_key",
)
@user_is_logged_in
def user_profile_manage_security_key(key_id):
    if not current_user.can_use_webauthn:
        abort(403)

    security_key = current_user.webauthn_credentials.by_id(key_id)

    if not security_key:
        abort(404)

    form = ChangeSecurityKeyNameForm(security_key_name=security_key.name)

    if form.validate_on_submit():
        if form.security_key_name.data != security_key.name:
            user_api_client.update_webauthn_credential_name_for_user(
                user_id=current_user.id, credential_id=key_id, new_name_for_credential=form.security_key_name.data
            )
        return redirect(url_for(".user_profile_security_keys"))

    if request.endpoint == "main.user_profile_confirm_delete_security_key":
        flash("Are you sure you want to delete this security key?", "delete")

    return render_template("views/user-profile/manage-security-key.html", security_key=security_key, form=form)


@main.route("/user-profile/security-keys/<uuid:key_id>/delete", methods=["POST"])
@user_is_logged_in
def user_profile_delete_security_key(key_id):
    if not current_user.can_use_webauthn:
        abort(403)

    if user_api_client.get_webauthn_credentials_count(current_user.id) == 1:
        flash("You cannot delete your last security key.")
        return redirect(url_for(".user_profile_manage_security_key", key_id=key_id))

    return redirect(url_for(".user_profile_security_key_authenticate", key_id=key_id))


@main.route("/user-profile/security-keys/<uuid:key_id>/authenticate", methods=["GET", "POST"])
@user_is_logged_in
def user_profile_security_key_authenticate(key_id):
    # Validate password for form
    def _check_password(pwd):
        return user_api_client.verify_password(current_user.id, pwd)

    security_key = current_user.webauthn_credentials.by_id(key_id)

    form = ConfirmPasswordForm(_check_password)

    if form.validate_on_submit():
        try:
            user_api_client.delete_webauthn_credential_for_user(user_id=current_user.id, credential_id=key_id)
        except HTTPError as e:
            message = "Cannot delete last remaining webauthn credential for user"
            if e.message == message:
                flash("You cannot delete your last security key.")
                return redirect(url_for(".user_profile_manage_security_key", key_id=key_id))
            else:
                raise e

        flash(
            f"{security_key.name} was deleted.",
            "default_with_tick",
        )
        return redirect(url_for(".user_profile_security_keys"))

    return render_template(
        "views/user-profile/authenticate.html",
        thing="security keys",
        form=form,
        back_link=url_for(".user_profile_security_keys"),
    )


@main.route("/user-profile/security-keys/create/authenticate", methods=["GET", "POST"])
@user_is_logged_in
def user_profile_security_key_create_authenticate():
    if not current_user.can_use_webauthn:
        abort(403)

    # Validate password for form
    def _check_password(pwd):
        return user_api_client.verify_password(current_user.id, pwd)

    form = ConfirmPasswordForm(_check_password)
    message = (
        "Registration complete. Next time you sign in to Emergency Alerts you’ll be asked to use your security key."
    )

    if form.validate_on_submit():
        credential = session.pop("webauthn_credential")
        cred = WebAuthnCredential.create(credential)
        current_user.create_webauthn_credential(cred)
        current_user.update(auth_type="webauthn_auth")
        flash(
            message,
            "default_with_tick",
        )
        return redirect(url_for(".user_profile_security_keys"))

    return render_template(
        "views/user-profile/authenticate.html",
        thing="security keys",
        form=form,
        back_link=url_for(".user_profile_security_keys"),
    )
