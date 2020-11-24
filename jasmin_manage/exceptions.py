from django.utils.translation import gettext_lazy as _

from rest_framework import exceptions, status


class Conflict(exceptions.APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = _('Request conflicts with current state.')
    default_code = 'conflict'
