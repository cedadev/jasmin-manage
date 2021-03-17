"""
jasmin_manage_site URL Configuration
"""

from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from django.views import defaults as error_views

from rest_framework import status


# We want to use errors handlers that return HTML for a browser but JSON when asked for
def page_not_found(request, exception):
    if request.META.get('HTTP_ACCEPT') == 'application/json':
        return JsonResponse(
            dict(detail = 'Not found.'),
            status = status.HTTP_404_NOT_FOUND
        )
    else:
        return error_views.page_not_found(request, exception)

handler404 = page_not_found


def server_error(request):
    if request.META.get('HTTP_ACCEPT') == 'application/json':
        return JsonResponse(
            dict(detail = 'Internal server error.'),
            status = status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    else:
        return error_views.server_error(request)

handler500 = server_error


def bad_request(request, exception):
    if request.META.get('HTTP_ACCEPT') == 'application/json':
        return JsonResponse(
            dict(detail = 'Bad request.'),
            status = status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    else:
        return error_views.bad_request(request, exception)

handler400 = bad_request


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
