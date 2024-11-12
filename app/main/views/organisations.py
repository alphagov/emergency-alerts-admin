from collections import OrderedDict

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user
from notifications_python_client.errors import HTTPError

# from werkzeug import Response
from werkzeug.exceptions import abort

from app import current_organisation, org_invite_api_client, organisations_client
from app.main import main
from app.main.forms import (
    AdminNewOrganisationForm,
    AdminNotesForm,
    AdminOrganisationDomainsForm,
    InviteOrgUserForm,
    OrganisationCrownStatusForm,
    OrganisationOrganisationTypeForm,
    RenameOrganisationForm,
    SearchByNameForm,
    SearchUsersForm,
)
from app.models.organisation import AllOrganisations, Organisation
from app.models.user import InvitedOrgUser, User
from app.utils.user import user_has_permissions, user_is_platform_admin


@main.route("/organisations", methods=["GET"])
@user_is_platform_admin
def organisations():
    return render_template(
        "views/organisations/index.html",
        organisations=AllOrganisations(),
        search_form=SearchByNameForm(),
    )


@main.route("/organisations/add", methods=["GET", "POST"])
@user_is_platform_admin
def add_organisation():
    form = AdminNewOrganisationForm()

    if form.validate_on_submit():
        try:
            return redirect(
                url_for(
                    ".organisation_settings",
                    org_id=Organisation.create_from_form(form).id,
                )
            )
        except HTTPError as e:
            msg = "Organisation name already exists"
            if e.status_code == 400 and msg in e.message:
                form.name.errors.append("This organisation name is already in use")
            else:
                raise e

    return render_template("views/organisations/add-organisation.html", form=form)


@main.route("/organisations/<uuid:org_id>", methods=["GET"])
@user_has_permissions()
def organisation_dashboard(org_id):
    services = current_organisation.services
    return render_template(
        "views/organisations/organisation/index.html",
        services=services,
        search_form=SearchByNameForm() if len(services) > 7 else None,
    )


@main.route("/organisations/<uuid:org_id>/trial-services", methods=["GET"])
@user_is_platform_admin
def organisation_trial_mode_services(org_id):
    return render_template(
        "views/organisations/organisation/trial-mode-services.html",
        search_form=SearchByNameForm(),
    )


@main.route("/organisations/<uuid:org_id>/users", methods=["GET"])
@user_has_permissions()
def manage_org_users(org_id):
    return render_template(
        "views/organisations/organisation/users/index.html",
        users=current_organisation.team_members,
        show_search_box=(len(current_organisation.team_members) > 7),
        form=SearchUsersForm(),
    )


@main.route("/organisations/<uuid:org_id>/users/invite", methods=["GET", "POST"])
@user_has_permissions()
def invite_org_user(org_id):
    form = InviteOrgUserForm(inviter_email_address=current_user.email_address)
    if form.validate_on_submit():
        email_address = form.email_address.data
        invited_org_user = InvitedOrgUser.create(current_user.id, org_id, email_address)

        flash("Invite sent to {}".format(invited_org_user.email_address), "default_with_tick")
        return redirect(url_for(".manage_org_users", org_id=org_id))

    return render_template("views/organisations/organisation/users/invite-org-user.html", form=form)


@main.route("/organisations/<uuid:org_id>/users/<uuid:user_id>", methods=["GET"])
@user_has_permissions()
def edit_organisation_user(org_id, user_id):
    # The only action that can be done to an org user is to remove them from the org.
    # This endpoint is used to get the ID of the user to delete without passing it as a
    # query string, but it uses the template for all org team members in order to avoid
    # having a page containing a single link.
    return render_template(
        "views/organisations/organisation/users/index.html",
        users=current_organisation.team_members,
        show_search_box=(len(current_organisation.team_members) > 7),
        form=SearchUsersForm(),
        user_to_remove=User.from_id(user_id),
    )


@main.route("/organisations/<uuid:org_id>/users/<uuid:user_id>/delete", methods=["POST"])
@user_has_permissions()
def remove_user_from_organisation(org_id, user_id):
    organisations_client.remove_user_from_organisation(org_id, user_id)

    return redirect(url_for(".show_accounts_or_dashboard"))


@main.route("/organisations/<uuid:org_id>/cancel-invited-user/<uuid:invited_user_id>", methods=["GET"])
@user_has_permissions()
def cancel_invited_org_user(org_id, invited_user_id):
    org_invite_api_client.cancel_invited_user(org_id=org_id, invited_user_id=invited_user_id)

    invited_org_user = InvitedOrgUser.by_id_and_org_id(org_id, invited_user_id)

    flash(f"Invitation cancelled for {invited_org_user.email_address}", "default_with_tick")
    return redirect(url_for("main.manage_org_users", org_id=org_id))


@main.route("/organisations/<uuid:org_id>/settings/", methods=["GET"])
@user_is_platform_admin
def organisation_settings(org_id):
    return render_template("views/organisations/organisation/settings/index.html")


@main.route("/organisations/<uuid:org_id>/settings/edit-name", methods=["GET", "POST"])
@user_is_platform_admin
def edit_organisation_name(org_id):
    form = RenameOrganisationForm(name=current_organisation.name)

    if form.validate_on_submit():
        try:
            current_organisation.update(name=form.name.data)
        except HTTPError as http_error:
            error_msg = "Organisation name already exists"
            if http_error.status_code == 400 and error_msg in http_error.message:
                form.name.errors.append("This organisation name is already in use")
            else:
                raise http_error
        else:
            return redirect(url_for(".organisation_settings", org_id=org_id))

    return render_template(
        "views/organisations/organisation/settings/edit-name.html",
        form=form,
    )


@main.route("/organisations/<uuid:org_id>/settings/edit-type", methods=["GET", "POST"])
@user_is_platform_admin
def edit_organisation_type(org_id):
    form = OrganisationOrganisationTypeForm(organisation_type=current_organisation.organisation_type)

    if form.validate_on_submit():
        current_organisation.update(
            organisation_type=form.organisation_type.data,
        )
        return redirect(url_for(".organisation_settings", org_id=org_id))

    return render_template(
        "views/organisations/organisation/settings/edit-type.html",
        form=form,
    )


@main.route("/organisations/<uuid:org_id>/settings/edit-crown-status", methods=["GET", "POST"])
@user_is_platform_admin
def edit_organisation_crown_status(org_id):
    form = OrganisationCrownStatusForm(
        crown_status={
            True: "crown",
            False: "non-crown",
            None: "unknown",
        }.get(current_organisation.crown)
    )

    if form.validate_on_submit():
        crown_data = {
            "crown": True,
            "non-crown": False,
            "unknown": None,
        }.get(form.crown_status.data)

        current_organisation.update(crown=crown_data)
        return redirect(url_for(".organisation_settings", org_id=org_id))

    return render_template(
        "views/organisations/organisation/settings/edit-crown-status.html",
        form=form,
    )


@main.route("/organisations/<uuid:org_id>/settings/edit-organisation-domains", methods=["GET", "POST"])
@user_is_platform_admin
def edit_organisation_domains(org_id):
    form = AdminOrganisationDomainsForm()

    if form.validate_on_submit():
        try:
            organisations_client.update_organisation(
                org_id,
                domains=list(OrderedDict.fromkeys(domain.lower() for domain in filter(None, form.domains.data))),
            )
        except HTTPError as e:
            error_message = "Domain already exists"
            if e.status_code == 400 and error_message in e.message:
                flash("This domain is already in use", "error")
                return render_template(
                    "views/organisations/organisation/settings/edit-domains.html",
                    form=form,
                )
            else:
                raise e
        return redirect(url_for(".organisation_settings", org_id=org_id))

    if request.method == "GET":
        form.populate(current_organisation.domains)

    return render_template(
        "views/organisations/organisation/settings/edit-domains.html",
        form=form,
    )


@main.route("/organisations/<uuid:org_id>/settings/notes", methods=["GET", "POST"])
@user_is_platform_admin
def edit_organisation_notes(org_id):
    form = AdminNotesForm(notes=current_organisation.notes)

    if form.validate_on_submit():
        if form.notes.data == current_organisation.notes:
            return redirect(url_for(".organisation_settings", org_id=org_id))

        current_organisation.update(notes=form.notes.data)
        return redirect(url_for(".organisation_settings", org_id=org_id))

    return render_template(
        "views/organisations/organisation/settings/edit-organisation-notes.html",
        form=form,
    )


@main.route("/organisations/<uuid:org_id>/settings/archive", methods=["GET", "POST"])
@user_is_platform_admin
def archive_organisation(org_id):
    if not current_organisation.active:
        abort(403)

    if request.method == "POST":
        try:
            organisations_client.archive_organisation(org_id)
        except HTTPError as e:
            if e.status_code == 400 and ("team members" in e.message or "services" in e.message):
                flash(e.message)
                return organisation_settings(org_id)
            else:
                raise e

        flash(f"‘{current_organisation.name}’ was deleted", "default_with_tick")
        return redirect(url_for(".choose_account"))

    flash(
        f"Are you sure you want to delete ‘{current_organisation.name}’? There’s no way to undo this.",
        "delete",
    )
    return organisation_settings(org_id)
