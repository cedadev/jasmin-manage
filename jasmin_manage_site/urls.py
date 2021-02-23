"""
jasmin_manage_site URL Configuration
"""

from django.conf import settings
from django.contrib import admin
from django.urls import path, include


# Use the configured authentication URLs, falling back to the rest_framework
# views if not defined
auth_urls = getattr(settings, 'JASMIN_MANAGE_AUTH_URLS', 'rest_framework.urls')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('jasmin_manage.urls')),
    path('auth/', include(auth_urls)),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))
