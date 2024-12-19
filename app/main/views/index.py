from flask import (
    abort,
    current_app,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user

from app.main import main
from app.main.views.sub_navigation_dictionaries import features_nav


@main.route("/robots.txt")
def static():
    return send_from_directory(current_app.static_folder, "metadata/" + request.path[1:])


@main.route("/")
def index():
    if current_user and current_user.is_authenticated:
        return redirect(url_for("main.choose_account"))

    return redirect(url_for("main.sign_in"))


@main.route("/error/<int:status_code>")
def error(status_code):
    if status_code >= 500:
        abort(404)
    abort(status_code)


@main.route("/cookies")
def cookies():
    return render_template("views/cookies.html")


@main.route("/privacy")
def privacy():
    return render_template("views/privacy.html")


@main.route("/accessibility-statement")
def accessibility_statement():
    return render_template("views/accessibility_statement.html")


# --- Features page set --- #


@main.route("/features/security", endpoint="security")
def security():
    return render_template("views/security.html", navigation_links=features_nav())


@main.route("/features/terms", endpoint="terms")
def terms():
    return render_template(
        "views/terms-of-use.html",
        navigation_links=features_nav(),
    )


@main.route("/features/training-mode")
def training_mode():
    return render_template(
        "views/training-mode.html",
        navigation_links=features_nav(),
    )


# --- Redirects --- #


@main.route("/terms", endpoint="old_terms")
@main.route("/information-security", endpoint="information_security")
@main.route("/information-risk-management", endpoint="information_risk_management")
def old_page_redirects():
    redirects = {
        "main.old_terms": "main.terms",
        "main.information_security": "main.security",
        "main.information_risk_management": "main.security",
    }
    return redirect(url_for(redirects[request.endpoint]), code=301)
