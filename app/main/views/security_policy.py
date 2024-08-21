from flask import redirect

from app.main import main


@main.route("/.well-known/security.txt", methods=["GET"])
@main.route("/security.txt", methods=["GET"])
def security_policy():
    # This endpoint implements the GDS Way security policy, found here:
    # https://gds-way.cloudapps.digital/standards/vulnerability-disclosure.html#vulnerability-disclosure-and-security-txt
    return redirect("https://vdp.cabinetoffice.gov.uk/.well-known/security.txt")
