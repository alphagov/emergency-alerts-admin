from itertools import chain

from flask import request


class Navigation:
    mapping = {}
    selected_class = "selected"

    def __init__(self):
        self.mapping = {
            navigation: {
                # if not specified, assume endpoints are all in the `main` blueprint.
                self.get_endpoint_with_blueprint(endpoint)
                for endpoint in endpoints
            }
            for navigation, endpoints in self.mapping.items()
        }

    @property
    def endpoints_with_navigation(self):
        return tuple(chain.from_iterable((endpoints for navigation_item, endpoints in self.mapping.items())))

    def is_selected(self, navigation_item):
        if request.endpoint in self.mapping[navigation_item]:
            return " " + self.selected_class
        return ""

    @staticmethod
    def get_endpoint_with_blueprint(endpoint):
        return endpoint if "." in endpoint else "main.{}".format(endpoint)


class HeaderNavigation(Navigation):
    mapping = {
        "support": {
            "bat_phone",
            "feedback",
            "support",
            "support_public",
            "thanks",
            "triage",
        },
        "features": {
            "features",
            "features_email",
            "features_letters",
            "features_sms",
            "message_status",
            "roadmap",
            "security",
            "terms",
            "trial_mode_new",
            "using_emergency_alerts",
        },
        "documentation": {
            "documentation",
            "integration_testing",
        },
        "user-profile": {
            "user_profile",
            "user_profile_confirm_delete_mobile_number",
            "user_profile_email",
            "user_profile_email_authenticate",
            "user_profile_email_confirm",
            "user_profile_mobile_number",
            "user_profile_mobile_number_authenticate",
            "user_profile_mobile_number_confirm",
            "user_profile_mobile_number_delete",
            "user_profile_name",
            "user_profile_password",
            "user_profile_disable_platform_admin_view",
        },
        "platform-admin": {
            "archive_user",
            "change_user_auth",
            "clear_cache",
            "find_services_by_name",
            "find_users_by_email",
            "live_services",
            "organisations",
            "platform_admin",
            "platform_admin_search",
            "trial_services",
            "user_information",
        },
        "sign-in": {
            "revalidate_email_sent",
            "sign_in",
            "two_factor_sms",
            "two_factor_email",
            "two_factor_email_sent",
            "two_factor_email_interstitial",
            "two_factor_webauthn",
            "verify",
            "verify_email",
        },
    }

    # header HTML now comes from GOVUK Frontend so requires a boolean, not an attribute
    def is_selected(self, navigation_item):
        return request.endpoint in self.mapping[navigation_item]


class MainNavigation(Navigation):
    mapping = {
        "dashboard": {
            "broadcast_tour",
            "service_dashboard",
        },
        "current-broadcasts": {
            "broadcast_dashboard",
            "broadcast_dashboard_updates",
            "view_current_broadcast",
            "new_broadcast",
            "write_new_broadcast",
            # "choose_broadcast_duration",
        },
        "previous-broadcasts": {
            "broadcast_dashboard_previous",
            "view_previous_broadcast",
        },
        "rejected-broadcasts": {
            "broadcast_dashboard_rejected",
            "view_rejected_broadcast",
        },
        "templates": {
            "action_blocked",
            "add_service_template",
            "choose_template",
            "choose_template_to_copy",
            "confirm_redact_template",
            "copy_template",
            "delete_service_template",
            "edit_service_template",
            "edit_template_postage",
            "manage_template_folder",
            "view_template",
            "view_template_version",
            "view_template_versions",
            "broadcast",
            "preview_broadcast_areas",
            "choose_broadcast_library",
            "choose_broadcast_area",
            "choose_broadcast_sub_area",
            "remove_broadcast_area",
            "preview_broadcast_message",
            "approve_broadcast_message",
            "reject_broadcast_message",
            "cancel_broadcast_message",
            "remove_postcode_area",
        },
        "team-members": {
            "confirm_edit_user_email",
            "confirm_edit_user_mobile_number",
            "edit_user_email",
            "edit_user_mobile_number",
            "edit_user_permissions",
            "invite_user",
            "manage_users",
            "remove_user_from_service",
        },
        "settings": {
            "add_organisation_from_gp_service",
            "add_organisation_from_nhs_local_service",
            "estimate_usage",
            "link_service_to_organisation",
            "request_to_go_live",
            "service_add_email_reply_to",
            "service_add_letter_contact",
            "service_confirm_delete_email_reply_to",
            "service_confirm_delete_letter_contact",
            "service_edit_email_reply_to",
            "service_edit_letter_contact",
            "service_email_reply_to",
            "service_letter_contact_details",
            "service_make_blank_default_letter_contact",
            "service_name_change",
            "service_set_auth_type",
            "service_set_channel",
            "service_confirm_broadcast_account_type",
            "service_set_broadcast_channel",
            "service_set_broadcast_network",
            "service_set_international_letters",
            "service_set_international_sms",
            "service_set_letters",
            "service_set_reply_to_email",
            "service_set_sms_prefix",
            "service_verify_reply_to_address",
            "service_verify_reply_to_address_updates",
            "service_settings",
            "set_free_sms_allowance",
            "set_message_limit",
            "set_rate_limit",
            "submit_request_to_go_live",
        },
        "api-integration": {
            "api_callbacks",
            "api_documentation",
            "api_integration",
            "api_keys",
            "create_api_key",
            "delivery_status_callback",
            "revoke_api_key",
            "guest_list",
            "old_guest_list",
        },
        "reports": {
            "reports",
        },
    }


class CaseworkNavigation(Navigation):
    mapping = {
        "dashboard": {
            "broadcast_tour",
            "broadcast_dashboard",
            "broadcast_dashboard_previous",
            "broadcast_dashboard_updates",
        },
    }


class OrgNavigation(Navigation):
    mapping = {
        "dashboard": {
            "organisation_dashboard",
        },
        "settings": {
            "archive_organisation",
            "edit_organisation_agreement",
            "edit_organisation_crown_status",
            "edit_organisation_domains",
            "edit_organisation_domains",
            "edit_organisation_go_live_notes",
            "edit_organisation_name",
            "edit_organisation_notes",
            "edit_organisation_type",
            "organisation_settings",
        },
        "team-members": {
            "edit_organisation_user",
            "invite_org_user",
            "manage_org_users",
            "remove_user_from_organisation",
        },
        "trial-services": {
            "organisation_trial_mode_services",
        },
    }
