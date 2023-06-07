from rest_framework import viewsets
import rest_framework.permissions as rf_perms
import oauth2_provider.contrib.rest_framework as oauth2_rf

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