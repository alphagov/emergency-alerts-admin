import os

header_colors = {
    "local": "#FF8000",
    "development": "#81878b",
    "preview": "#F499BE",
    "staging": "#6F72AF",
    "production": "#1d70b8",
}

if os.environ.get("VCAP_APPLICATION"):
    # on cloudfoundry, config is a json blob in VCAP_APPLICATION - unpack it, and populate
    # standard environment variables from it
    from app.cloudfoundry_config import extract_cloudfoundry_config

    extract_cloudfoundry_config()


class Config(object):
    ADMIN_CLIENT_SECRET = os.environ.get("ADMIN_CLIENT_SECRET")

    SECRET_KEY = os.environ.get("SECRET_KEY")
    DANGEROUS_SALT = os.environ.get("DANGEROUS_SALT")

    ENCRYPTION_SECRET_KEY = os.environ.get("ENCRYPTION_SECRET_KEY")
    ENCRYPTION_DANGEROUS_SALT = os.environ.get("ENCRYPTION_DANGEROUS_SALT")

    API_HOST_NAME = os.environ.get("API_HOST_NAME", "http://localhost:6011")
    ADMIN_EXTERNAL_URL = os.environ.get("ADMIN_EXTERNAL_URL", "http://localhost:6012")
    ZENDESK_API_KEY = os.environ.get("ZENDESK_API_KEY")

    GEOJSON_BUCKET = os.environ.get("POSTCODE_BUCKET_NAME")

    # if we're not on cloudfoundry, we can get to this app from localhost. but on cloudfoundry its different
    ADMIN_BASE_URL = os.environ.get("ADMIN_BASE_URL", "http://localhost:6012")

    TEMPLATE_PREVIEW_API_HOST = os.environ.get("TEMPLATE_PREVIEW_API_HOST", "http://localhost:6013")
    TEMPLATE_PREVIEW_API_KEY = os.environ.get("TEMPLATE_PREVIEW_API_KEY", "my-secret-key")

    # Logging
    DEBUG = True
    NOTIFY_LOG_PATH = "application.log"

    ADMIN_CLIENT_USER_NAME = "notify-admin"

    ANTIVIRUS_API_HOST = "http://localhost:6016"
    ANTIVIRUS_API_KEY = "test-key"

    ASSETS_DEBUG = False
    AWS_REGION = os.environ.get("AWS_REGION")
    DEFAULT_SERVICE_LIMIT = 50

    EMAIL_EXPIRY_SECONDS = 3600  # 1 hour
    INVITATION_EXPIRY_SECONDS = 3600 * 24 * 2  # 2 days - also set on api
    EMAIL_2FA_EXPIRY_SECONDS = 1800  # 30 Minutes
    HEADER_COLOUR = "#81878b"  # mix(govuk-colour("dark-grey"), govuk-colour("mid-grey"))
    HTTP_PROTOCOL = "http"
    NOTIFY_APP_NAME = "admin"
    NOTIFY_LOG_LEVEL = "DEBUG"
    PERMANENT_SESSION_LIFETIME = 60 * 60  # 60 minutes - maximum duration for a session
    SEND_FILE_MAX_AGE_DEFAULT = 365 * 24 * 60 * 60  # 1 year
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_NAME = "emergency_alerts_session"
    SESSION_COOKIE_SECURE = False
    SESSION_PROTECTION = None
    SESSION_COOKIE_SAMESITE = "Strict"
    # don't send back the cookie if it hasn't been modified by the request. this means that the expiry time won't be
    # updated unless the session is changed - but it's generally refreshed by `save_service_or_org_after_request`
    # every time anyway, except for specific endpoints (png/pdfs generally) where we've disabled that handler.
    SESSION_REFRESH_EACH_REQUEST = False
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    CSV_UPLOAD_BUCKET_NAME = "local-notifications-csv-upload"
    CONTACT_LIST_UPLOAD_BUCKET_NAME = "local-contact-list"
    ACTIVITY_STATS_LIMIT_DAYS = 7

    REPLY_TO_EMAIL_ADDRESS_VALIDATION_TIMEOUT = 45

    HOST = "local"
    LOGO_UPLOAD_BUCKET_NAME = "public-logos-local"
    MOU_BUCKET_NAME = "local-mou"
    TRANSIENT_UPLOADED_LETTERS = "local-transient-uploaded-letters"
    ROUTE_SECRET_KEY_1 = os.environ.get("ROUTE_SECRET_KEY_1", "")
    ROUTE_SECRET_KEY_2 = os.environ.get("ROUTE_SECRET_KEY_2", "")
    CHECK_PROXY_HEADER = False
    ANTIVIRUS_ENABLED = True

    LOGO_CDN_DOMAIN = "static-logos.notify.tools"

    REDIS_URL = "redis://localhost:6379/0"
    REDIS_ENABLED = os.environ.get("REDIS_ENABLED") == "1"

    ASSET_DOMAIN = ""
    ASSET_PATH = "/static/"

    # as defined in api db migration 0331_add_broadcast_org.py
    BROADCAST_ORGANISATION_ID = "38e4bf69-93b0-445d-acee-53ea53fe02df"

    NOTIFY_SERVICE_ID = "d6aa2c68-a2d9-4437-ab19-3ae8eb202553"

    NOTIFY_RUNTIME_PLATFORM = os.environ.get("NOTIFY_RUNTIME_PLATFORM", "paas")

    INACTIVITY_MINS = 28
    EXPIRY_WARNING_MINS = 58
    INACTIVITY_WARNING_DURATION = 2

    FUNCTIONAL_TEST_PERMANENT_SESSION_LIFETIME = 0.667 * 60
    FUNCTIONAL_TEST_INACTIVITY_MINS = 0.167
    FUNCTIONAL_TEST_EXPIRY_WARNING_MINS = 0.5
    FUNCTIONAL_TEST_INACTIVITY_WARNING_DURATION = 0.167

    FUNCTIONAL_TEST_USER_ID = os.environ.get("FUNCTIONAL_TEST_USER_ID", "")


class Hosted(Config):
    HOST = "hosted"
    TENANT = f"{os.environ.get('TENANT')}." if os.environ.get("TENANT") is not None else ""
    SUBDOMAIN = (
        "dev."
        if os.environ.get("ENVIRONMENT") == "development"
        else f"{os.environ.get('ENVIRONMENT')}."
        if os.environ.get("ENVIRONMENT") != "production"
        else ""
    )
    API_HOST_NAME = f"http://api.{TENANT}ecs.local:6011"
    ADMIN_BASE_URL = f"http://admin.{TENANT}ecs.local:6012"
    HEADER_COLOUR = header_colors.get(os.environ.get("ENVIRONMENT"), "#81878b")
    ADMIN_EXTERNAL_URL = f"https://{TENANT}admin.{SUBDOMAIN}emergency-alerts.service.gov.uk"
    TEMPLATE_PREVIEW_API_HOST = f"http://api.{TENANT}ecs.local:6013"
    ANTIVIRUS_API_HOST = f"http://admin.{TENANT}ecs.local:6016"
    REDIS_URL = f"redis://api.{TENANT}ecs.local:6379/0"

    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SESSION_PROTECTION = "strong"


class Test(Config):
    DEBUG = True
    TESTING = True
    WTF_CSRF_ENABLED = False
    CSV_UPLOAD_BUCKET_NAME = "test-notifications-csv-upload"
    CONTACT_LIST_UPLOAD_BUCKET_NAME = "test-contact-list"
    LOGO_UPLOAD_BUCKET_NAME = "public-logos-test"
    LOGO_CDN_DOMAIN = "static-logos.test.com"
    MOU_BUCKET_NAME = "test-mou"
    TRANSIENT_UPLOADED_LETTERS = "test-transient-uploaded-letters"
    PRECOMPILED_ORIGINALS_BACKUP_LETTERS = "test-letters-precompiled-originals-backup"
    HOST = "test"
    API_HOST_NAME = "http://you-forgot-to-mock-an-api-call-to"
    TEMPLATE_PREVIEW_API_HOST = "http://localhost:9999"
    ANTIVIRUS_API_HOST = "https://test-antivirus"
    ANTIVIRUS_API_KEY = "test-antivirus-secret"
    ANTIVIRUS_ENABLED = True
    TENANT = f"{os.environ.get('TENANT')}." if os.environ.get("TENANT") is not None else ""
    SUBDOMAIN = (
        "dev."
        if os.environ.get("ENVIRONMENT") == "development"
        else f"{os.environ.get('ENVIRONMENT')}."
        if os.environ.get("ENVIRONMENT") != "production"
        else ""
    )
    ADMIN_EXTERNAL_URL = f"https://{TENANT}admin.{SUBDOMAIN}emergency-alerts.service.gov.uk"
    ASSET_DOMAIN = "static.example.com"
    ASSET_PATH = "https://static.example.com/"


configs = {
    "local": Config,
    "hosted": Hosted,
    "test": Test,
}
