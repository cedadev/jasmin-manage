"""
jasmin_manage_site URL Configuration
"""

from django.conf import settings
from django.contrib import admin
from django.urls import path, include


# If the jasmin-auth-django package is installed, use the login URLs from there
try:
    import jasmin_auth.urls
    auth_urls = 'jasmin_auth.urls'
except ImportError:
    auth_urls = 'rest_framework.urls'


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('jasmin_manage.urls')),
    path('auth/', include(auth_urls)),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))
