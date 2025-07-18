from datetime import datetime, timedelta, timezone

from flask import abort, redirect, render_template, request, session, url_for
from notifications_python_client.errors import HTTPError

from app import user_api_client
from app.main import main
from app.main.forms import RegisterUserFromInviteForm, RegisterUserFromOrgInviteForm
from app.main.views.verify import activate_user
from app.models.user import InvitedOrgUser, InvitedUser, User


@main.route("/register-from-invite", methods=["GET", "POST"])
def register_from_invite():
    invited_user = InvitedUser.from_session()

    if not invited_user:
        token = request.args.get("token")
        if token is not None:
            invited_user = InvitedUser.from_token(token)
            session["invited_user_id"] = invited_user.id

    if not invited_user:
        abort(404)

    form = RegisterUserFromInviteForm(invited_user)

    if form.validate_on_submit():
        try:
            user_api_client.check_password_is_valid(invited_user.id, form.password.data)
        except HTTPError as e:
            if e.status_code == 400:
                form.password.errors.append(e.message[0])
                return render_template("views/register-from-invite.html", invited_user=invited_user, form=form)
        if form.service.data != invited_user.service or form.email_address.data != invited_user.email_address:
            abort(400)
        _do_registration(form, send_email=False, send_sms=invited_user.sms_auth)
        invited_user.accept_invite()
        if invited_user.sms_auth:
            return redirect(url_for("main.verify"))
        else:
            # we've already proven this user has email because they clicked the invite link,
            # so just activate them straight away
            return activate_user(session["user_details"]["id"])

    return render_template("views/register-from-invite.html", invited_user=invited_user, form=form)


@main.route("/register-from-org-invite", methods=["GET", "POST"])
def register_from_org_invite():
    invited_org_user = InvitedOrgUser.from_session()
    if not invited_org_user:
        abort(404)

    form = RegisterUserFromOrgInviteForm(
        invited_org_user,
    )
    form.auth_type.data = "sms_auth"

    if form.validate_on_submit():
        try:
            user_api_client.check_password_is_valid(invited_org_user.id, form.password.data)
        except HTTPError as e:
            if e.status_code == 400:
                form.password.errors.append(e.message[0])
                return render_template(
                    "views/register-from-org-invite.html", invited_org_user=invited_org_user, form=form
                )
        if (
            form.organisation.data != invited_org_user.organisation
            or form.email_address.data != invited_org_user.email_address
        ):
            abort(400)
        _do_registration(form, send_email=False, send_sms=True, organisation_id=invited_org_user.organisation)
        invited_org_user.accept_invite()

        return redirect(url_for("main.verify"))
    return render_template("views/register-from-org-invite.html", invited_org_user=invited_org_user, form=form)


def _do_registration(form, send_sms=True, send_email=True, organisation_id=None):
    user = User.from_email_address_or_none(form.email_address.data)
    if user:
        if send_email:
            user.send_already_registered_email()
        session["expiry_date"] = str(datetime.now(timezone.utc) + timedelta(hours=1))
        session["user_details"] = {"email": user.email_address, "id": user.id}
    else:
        user = User.register(
            name=form.name.data,
            email_address=form.email_address.data,
            mobile_number=form.mobile_number.data,
            password=form.password.data,
            auth_type=form.auth_type.data,
        )

        if send_email:
            user.send_verify_email()

        if send_sms:
            user.send_verify_code()
        session["expiry_date"] = str(datetime.now(timezone.utc) + timedelta(hours=1))
        session["user_details"] = {"email": user.email_address, "id": user.id}
    if organisation_id:
        session["organisation_id"] = organisation_id
