from urllib.parse import urlparse

from fido2.server import Fido2Server
from fido2.webauthn import PublicKeyCredentialRpEntity


def init_app(app):
    admin_url = app.config["ADMIN_EXTERNAL_URL"]

    base_url = urlparse(admin_url)
    verify_origin_callback = None

    # stub verification in dev (to avoid need for HTTPS)
    if app.config["HOST"] == "local":
        verify_origin_callback = stub_origin_checker

    relying_party = PublicKeyCredentialRpEntity(
        id=base_url.hostname,
        name="GOV.UK Emergency Alerts",
    )

    app.logger.info(f"Relying party: {relying_party}")

    app.webauthn_server = Fido2Server(
        relying_party,
        attestation="direct",
        verify_origin=verify_origin_callback,
    )

    # some browsers don't seem to have a default timeout
    # 30 seconds seems like a generous amount of time
    app.webauthn_server.timeout = 30_000


def stub_origin_checker(*args):
    return True
