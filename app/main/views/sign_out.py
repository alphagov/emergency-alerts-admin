from flask import redirect, request, url_for
from flask_login import current_user

from app.main import main


@main.route("/sign-out", methods=(["GET"]))
def sign_out():
    status = request.args.get("status")
    redirect_url = request.args.get("next")
    # An AnonymousUser does not have an id
    if current_user.is_authenticated:
        current_user.sign_out()
        if status:
            return redirect(url_for("main.sign_in", next=redirect_url, status=status))
    return redirect(url_for("main.index"))
