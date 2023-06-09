from rest_framework import viewsets
import rest_framework.permissions as rf_perms
import oauth2_provider.contrib.rest_framework as oauth2_rf
from django.core.exceptions import ImproperlyConfigured
from rest_framework.permissions import SAFE_METHODS
from oauth2_provider.settings import oauth2_settings

class BaseViewSet(viewsets.GenericViewSet):
    """
    Base view set to provide permissions for all API endpoints.
    """
    required_scopes = ['jasmin.projects.all']

    def get_permissions(self):
        # If listing the services, edit the perimission classes to check user has permission
        # or is authenticated using a token with the required scopes.
        is_real_user = self.request.user
        if not is_real_user:
            if self.action == 'list':
                permission_classes = [rf_perms.OR(oauth2_rf.TokenHasResourceScope(), rf_perms.IsAdminUser())]
                return permission_classes
        return super().get_permissions()
    
class TokenHasAtLeastOneScope(rf_perms.BasePermission):
    """
    The request is authenticated if the token used has at least one of the right scopes.
    """
    def has_permission(self, request, view):
        token = request.auth
        if not token:
            return False
        if hasattr(token, "scope"):
            required_scopes = self.get_scopes(request, view)
            # If any scope in the list of required scopes is valid, return True.
            for given_scope in required_scopes:
                if token.is_valid([given_scope]):
                    return True
            return False
        assert False, (
            "Error in TokenHAsAtLeastOneScope."
        )

    def get_scopes(self, request, view):
        try:
            view_scopes = getattr(view, "required_scopes")
        except ImproperlyConfigured:
            view_scopes = []
        if request.method.upper() in SAFE_METHODS:
            scope_type = oauth2_settings.READ_SCOPE
        else:
            scope_type = oauth2_settings.WRITE_SCOPE

        required_scopes = ["{}:{}".format(scope, scope_type) for scope in view_scopes]

        return required_scopes