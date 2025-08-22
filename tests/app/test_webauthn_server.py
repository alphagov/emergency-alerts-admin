import os

import pytest

from app import webauthn_server


@pytest.fixture
def app_with_mock_config(mocker):
    app = mocker.Mock()

    tenant = f"{os.environ.get('TENANT')}." if os.environ.get("TENANT") is not None else ""
    subdomain = (
        "dev."
        if os.environ.get("ENVIRONMENT") == "development"
        else f"{os.environ.get('ENVIRONMENT')}." if os.environ.get("ENVIRONMENT") != "production" else ""
    )

    app.config = {
        "ADMIN_EXTERNAL_URL": f"https://{tenant}admin.{subdomain}emergency-alerts.service.gov.uk",
        "HOST": "local",
    }
    return app


@pytest.mark.parametrize(("environment, allowed"), [("local", True), ("production", False)])
def test_server_origin_verification(app_with_mock_config, environment, allowed):
    app_with_mock_config.config["HOST"] = environment
    webauthn_server.init_app(app_with_mock_config)
    assert app_with_mock_config.webauthn_server._verify("fake-domain") == allowed


def test_server_relying_party_id(
    app_with_mock_config,
    mocker,
):
    webauthn_server.init_app(app_with_mock_config)
    rp_id = "{}admin.{}emergency-alerts.service.gov.uk"
    tenant = f"{os.environ.get('TENANT')}." if os.environ.get("TENANT") is not None else ""
    subdomain = f"{os.environ.get('ENVIRONMENT')}." if os.environ.get("ENVIRONMENT") != "production" else ""
    assert app_with_mock_config.webauthn_server.rp.id == rp_id.format(tenant, subdomain).lower()
