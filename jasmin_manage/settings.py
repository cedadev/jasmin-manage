"""
Application settings for the jasmin-manage application.
"""


INSTALLED_APPS = [
    "oauth2_provider",
    "jasmin_auth",
    "jasmin_auth.apps.AdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_admin_listfilter_dropdown",
    "rangefilter",
    "jasmin_manage",
    "debug_toolbar",
    "rest_framework",
    "drf_spectacular",
    "tsunami",
    "tsunami_notify",
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "oauth2_provider.backends.OAuth2Backend",
]

MIDDLEWARE = [
    "oauth2_provider.middleware.OAuth2TokenMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "jasmin_auth.middleware.ImpersonateMiddleware",
    "tsunami.middleware.user_tracking",
]

ROOT_URLCONF = "jasmin_manage_site.urls"

WSGI_APPLICATION = "jasmin_manage_site.wsgi.application"

# We need the CSRF cookie to be available to Javascript
CSRF_COOKIE_HTTPONLY = False

# Since authentication is transparent, we expire sessions when the user closes their browser
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# The default of /static/ collides with create-react-app
STATIC_URL = "/assets/"

# Use the jasmin auth login views
JASMIN_MANAGE_AUTH_URLS = "jasmin_auth.urls"
LOGIN_URL = "jasmin_auth:login"

# Customise the rest framework settings
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PERMISSION_CLASSES": [],
    "EXCEPTION_HANDLER": "jasmin_manage.views.exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
        "oauth2_provider.contrib.rest_framework.OAuth2Authentication",
    ),
}
SPECTACULAR_SETTINGS = {
    "SCHEMA_PATH_PREFIX": r"/api",
    "SERVE_INCLUDE_SCHEMA": False,
}
SLACK_NOTIFICATIONS = {
    "WEBHOOK_URL": "https://hooks.slack.com/services/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",
    "SERVICE_REQUEST_URL": "http://manage-preproduction.130.246.130.221.nip.io/request/service-",
}
