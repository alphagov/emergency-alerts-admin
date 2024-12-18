import pytest
from flask import Flask

from app import create_app
from app.navigation import (
    CaseworkNavigation,
    HeaderNavigation,
    MainNavigation,
    Navigation,
    OrgNavigation,
)
from tests.conftest import ORGANISATION_ID, SERVICE_ONE_ID

EXCLUDED_ENDPOINTS = tuple(
    map(
        Navigation.get_endpoint_with_blueprint,
        {
            "accept_invite",
            "accept_org_invite",
            "accessibility_statement",
            "action_blocked",
            "add_organisation",
            "add_service",
            "add_service_template",
            "api_keys",
            "approve_broadcast_message",
            "archive_organisation",
            "archive_service",
            "archive_user",
            "bat_phone",
            "broadcast",
            "broadcast_dashboard",
            "broadcast_dashboard_previous",
            "broadcast_dashboard_rejected",
            "broadcast_dashboard_updates",
            "broadcast_tour",
            "broadcast_tour_live",
            "cancel_broadcast_message",
            "cancel_invited_org_user",
            "cancel_invited_user",
            "change_user_auth",
            "check_and_resend_text_code",
            "check_and_resend_verification_code",
            "choose_account",
            "choose_broadcast_area",
            # "choose_broadcast_duration",
            "choose_broadcast_library",
            "choose_broadcast_sub_area",
            "choose_service",
            "choose_template",
            "choose_template_to_copy",
            "confirm_edit_user_email",
            "confirm_edit_user_mobile_number",
            "confirm_redact_template",
            "cookies",
            "copy_template",
            "count_content_length",
            "create_api_key",
            "delete_service_template",
            "delete_template_folder",
            "edit_organisation_crown_status",
            "edit_organisation_domains",
            "edit_organisation_name",
            "edit_organisation_notes",
            "edit_organisation_type",
            "edit_organisation_user",
            "edit_service_notes",
            "edit_service_template",
            "edit_user_email",
            "edit_user_mobile_number",
            "edit_user_permissions",
            "email_not_received",
            "error",
            "feedback",
            "find_services_by_name",
            "find_users_by_email",
            "forgot_password",
            "history",
            "index",
            "information_risk_management",
            "information_security",
            "invite_org_user",
            "invite_user",
            "link_service_to_organisation",
            "live_services",
            "manage_org_users",
            "manage_template_folder",
            "manage_users",
            "new_broadcast",
            "new_password",
            "old_service_dashboard",
            "old_terms",
            "organisation_dashboard",
            "organisation_settings",
            "organisation_trial_mode_services",
            "organisations",
            "platform_admin",
            "platform_admin_search",
            "preview_broadcast_areas",
            "preview_broadcast_message",
            "privacy",
            "redirect_old_search_pages",
            "redact_template",
            "register_from_invite",
            "register_from_org_invite",
            "reject_broadcast_message",
            "remove_broadcast_area",
            "remove_user_from_organisation",
            "remove_user_from_service",
            "remove_postcode_area",
            "reports",
            "resend_email_link",
            "resend_email_verification",
            "revalidate_email_sent",
            "revoke_api_key",
            "search_coordinates",
            "search_postcodes",
            "security",
            "security_policy",
            "service_dashboard",
            "service_name_change",
            "service_set_auth_type",
            "service_confirm_broadcast_account_type",
            "service_set_broadcast_channel",
            "service_set_broadcast_network",
            "service_set_permission",
            "service_settings",
            "services_or_dashboard",
            "show_accounts_or_dashboard",
            "sign_in",
            "sign_out",
            "static",
            "support",
            "support_public",
            "terms",
            "thanks",
            "training_mode",
            "triage",
            "trial_services",
            "two_factor_sms",
            "two_factor_email",
            "two_factor_email_interstitial",
            "two_factor_email_sent",
            "two_factor_webauthn",
            "user_information",
            "user_profile",
            "user_profile_confirm_delete_mobile_number",
            "user_profile_confirm_delete_security_key",
            "user_profile_delete_security_key",
            "user_profile_disable_platform_admin_view",
            "user_profile_email",
            "user_profile_email_authenticate",
            "user_profile_email_confirm",
            "user_profile_manage_security_key",
            "user_profile_mobile_number",
            "user_profile_mobile_number_authenticate",
            "user_profile_mobile_number_confirm",
            "user_profile_mobile_number_delete",
            "user_profile_name",
            "user_profile_password",
            "user_profile_security_keys",
            "verify",
            "verify_email",
            "view_current_broadcast",
            "view_previous_broadcast",
            "view_rejected_broadcast",
            "view_template",
            "view_template_version",
            "view_template_versions",
            "webauthn_begin_register",
            "webauthn_complete_register",
            "webauthn_begin_authentication",
            "webauthn_complete_authentication",
            "write_new_broadcast",
        },
    )
)


def flask_app():
    app = Flask("app")
    create_app(app)

    ctx = app.app_context()
    ctx.push()

    yield app


all_endpoints = [rule.endpoint for rule in next(flask_app()).url_map.iter_rules()]

navigation_instances = (
    MainNavigation(),
    HeaderNavigation(),
    OrgNavigation(),
    CaseworkNavigation(),
)


@pytest.mark.parametrize(
    "navigation_instance", navigation_instances, ids=(x.__class__.__name__ for x in navigation_instances)
)
def test_navigation_items_are_properly_defined(navigation_instance):
    for endpoint in navigation_instance.endpoints_with_navigation:
        assert endpoint in all_endpoints, "{} is not a real endpoint (in {}.mapping)".format(
            endpoint, type(navigation_instance).__name__
        )
        assert (
            navigation_instance.endpoints_with_navigation.count(endpoint) == 1
        ), "{} found more than once in {}.mapping".format(endpoint, type(navigation_instance).__name__)


def test_excluded_navigation_items_are_properly_defined():
    for endpoint in EXCLUDED_ENDPOINTS:
        assert endpoint in all_endpoints, f"{endpoint} is not a real endpoint (in EXCLUDED_ENDPOINTS)"

        assert EXCLUDED_ENDPOINTS.count(endpoint) == 1, f"{endpoint} found more than once in EXCLUDED_ENDPOINTS"


@pytest.mark.parametrize(
    "navigation_instance", navigation_instances, ids=(x.__class__.__name__ for x in navigation_instances)
)
def test_all_endpoints_are_covered(navigation_instance):
    covered_endpoints = (
        navigation_instance.endpoints_with_navigation + EXCLUDED_ENDPOINTS + ("static", "status.show_status", "metrics")
    )

    for endpoint in all_endpoints:
        assert endpoint in covered_endpoints, f"{endpoint} is not listed or excluded"


@pytest.mark.parametrize(
    "navigation_instance", navigation_instances, ids=(x.__class__.__name__ for x in navigation_instances)
)
@pytest.mark.xfail(raises=KeyError)
def test_raises_on_invalid_navigation_item(client_request, navigation_instance):
    navigation_instance.is_selected("foo")


@pytest.mark.parametrize(
    "endpoint, selected_nav_item",
    [
        ("main.choose_template", "Templates"),
        ("main.manage_users", "Team members"),
    ],
)
def test_a_page_should_nave_selected_navigation_item(
    client_request,
    mock_get_service_templates,
    mock_get_users_by_service,
    mock_get_invites_for_service,
    mock_get_template_folders,
    mock_get_api_keys,
    endpoint,
    selected_nav_item,
):
    page = client_request.get(endpoint, service_id=SERVICE_ONE_ID)
    selected_nav_items = page.select(".navigation a.selected")
    assert len(selected_nav_items) == 1
    assert selected_nav_items[0].text.strip() == selected_nav_item


@pytest.mark.parametrize(
    "endpoint, selected_nav_item",
    [
        ("main.support", "Support"),
    ],
)
def test_a_page_should_have_selected_header_navigation_item(
    client_request,
    endpoint,
    selected_nav_item,
):
    page = client_request.get(endpoint, service_id=SERVICE_ONE_ID)
    selected_nav_items = page.select(".govuk-header__navigation-item--active")
    assert len(selected_nav_items) == 1
    assert selected_nav_items[0].text.strip() == selected_nav_item


@pytest.mark.parametrize(
    "endpoint, selected_nav_item",
    [
        ("main.organisation_dashboard", "Services"),
        ("main.manage_org_users", "Team members"),
    ],
)
def test_a_page_should_nave_selected_org_navigation_item(
    client_request,
    mock_get_organisation,
    mock_get_users_for_organisation,
    mock_get_invited_users_for_organisation,
    endpoint,
    selected_nav_item,
    mocker,
):
    mocker.patch("app.organisations_client.get_organisation_services", return_value=[])
    page = client_request.get(endpoint, org_id=ORGANISATION_ID)
    selected_nav_items = page.select(".navigation a.selected")
    assert len(selected_nav_items) == 1
    assert selected_nav_items[0].text.strip() == selected_nav_item


def test_navigation_urls(
    client_request,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_get_api_keys,
):
    page = client_request.get("main.choose_template", service_id=SERVICE_ONE_ID)
    assert [a["href"] for a in page.select(".navigation a")] == [
        "/services/{}/current-alerts".format(SERVICE_ONE_ID),
        "/services/{}/past-alerts".format(SERVICE_ONE_ID),
        "/services/{}/rejected-alerts".format(SERVICE_ONE_ID),
        "/services/{}/templates".format(SERVICE_ONE_ID),
        "/services/{}/users".format(SERVICE_ONE_ID),
        "/services/{}/service-settings".format(SERVICE_ONE_ID),
        "/services/{}/api/keys".format(SERVICE_ONE_ID),
    ]


def test_navigation_for_services_with_broadcast_permission(
    client_request,
    service_one,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_get_api_keys,
    active_user_create_broadcasts_permission,
):
    service_one["permissions"] += ["broadcast"]
    client_request.login(active_user_create_broadcasts_permission)

    page = client_request.get("main.choose_template", service_id=SERVICE_ONE_ID)
    assert [a["href"] for a in page.select(".navigation a")] == [
        "/services/{}/current-alerts".format(SERVICE_ONE_ID),
        "/services/{}/past-alerts".format(SERVICE_ONE_ID),
        "/services/{}/rejected-alerts".format(SERVICE_ONE_ID),
        "/services/{}/templates".format(SERVICE_ONE_ID),
        "/services/{}/users".format(SERVICE_ONE_ID),
    ]


def test_navigation_for_services_with_broadcast_permission_platform_admin(
    client_request,
    service_one,
    mock_get_service_templates,
    mock_get_template_folders,
    mock_get_api_keys,
    platform_admin_user,
):
    service_one["permissions"] += ["broadcast"]

    client_request.login(platform_admin_user)
    page = client_request.get("main.choose_template", service_id=SERVICE_ONE_ID)
    assert [a["href"] for a in page.select(".navigation a")] == [
        "/services/{}/current-alerts".format(SERVICE_ONE_ID),
        "/services/{}/past-alerts".format(SERVICE_ONE_ID),
        "/services/{}/rejected-alerts".format(SERVICE_ONE_ID),
        "/services/{}/templates".format(SERVICE_ONE_ID),
        "/services/{}/users".format(SERVICE_ONE_ID),
        "/services/{}/service-settings".format(SERVICE_ONE_ID),
        "/services/{}/api/keys".format(SERVICE_ONE_ID),
    ]


def test_static_404s_return(client_request):
    client_request.get_response_from_url(
        "/static/images/some-image-that-doesnt-exist.png",
        _expected_status=404,
    )
