from emergency_alerts_utils.clients.zendesk.zendesk_client import EASSupportTicket
from flask import redirect, render_template, request, url_for
from flask_login import current_user

from app import convert_to_boolean, current_service
from app.extensions import zendesk_client
from app.main import main
from app.main.forms import FeedbackOrProblem
from app.utils import hide_from_search_engines


@main.route("/support", methods=["GET", "POST"])
@hide_from_search_engines
def support():
    form = FeedbackOrProblem()

    if current_user.is_authenticated:
        form.email_address.data = current_user.email_address
        form.name.data = current_user.name

    if form.validate_on_submit():
        user_email = form.email_address.data
        user_name = form.name.data or None

        feedback_msg = render_template(
            "support-tickets/support-ticket.txt",
            content=form.feedback.data,
        )

        ticket = EASSupportTicket(
            subject="Emergency Alerts feedback",
            message=feedback_msg,
            ticket_type=EASSupportTicket.TYPE_QUESTION,
            p1=False,
            user_name=user_name,
            user_email=user_email,
            org_id=current_service.organisation_id if current_service else None,
            org_type=current_service.organisation_type if current_service else None,
            service_id=current_service.id if current_service else None,
        )
        zendesk_client.send_ticket_to_zendesk(ticket)

        return redirect(
            url_for(
                ".thanks",
                email_address_provided=(current_user.is_authenticated or bool(form.email_address.data)),
            )
        )

    return render_template("views/support/index.html", form=form)


@main.route("/support/public")
@hide_from_search_engines
def support_public():
    return render_template("views/support/public.html")


@main.route("/support/thanks", methods=["GET", "POST"])
@hide_from_search_engines
def thanks():
    return render_template(
        "views/support/thanks.html",
        email_address_provided=convert_to_boolean(request.args.get("email_address_provided")),
    )
