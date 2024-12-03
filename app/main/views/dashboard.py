from flask import abort, session, url_for
from werkzeug.utils import redirect

from app.main import main
from app.utils.time import get_current_financial_year
from app.utils.user import user_has_permissions


@main.route("/services/<uuid:service_id>/dashboard")
@user_has_permissions("view_activity")
def old_service_dashboard(service_id):
    return redirect(url_for(".service_dashboard", service_id=service_id))


@main.route("/services/<uuid:service_id>")
@user_has_permissions()
def service_dashboard(service_id):
    if session.get("invited_user_id"):
        session.pop("invited_user_id", None)
        session["service_id"] = service_id
    return redirect(url_for("main.broadcast_dashboard", service_id=service_id))


def requested_and_current_financial_year(request):
    try:
        return (
            int(request.args.get("year", get_current_financial_year())),
            get_current_financial_year(),
        )
    except ValueError:
        abort(404)


def get_tuples_of_financial_years(
    partial_url,
    start=2015,
    end=None,
):
    return (
        (
            "financial year",
            year,
            partial_url(year=year),
            "{} to {}".format(year, year + 1),
        )
        for year in reversed(range(start, end + 1))
    )
