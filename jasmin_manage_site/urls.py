"""
jasmin_manage_site URL Configuration
"""

from django.conf import settings
from django.contrib import admin
from django.urls import path, include

from rest_framework.urls import urlpatterns as authurls


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('jasmin_manage.urls')),
    # In order for the browsable API to pick them up, auth view must be
    # in the rest_framework namespace
    path('auth/', include((authurls, 'rest_framework'))),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))
