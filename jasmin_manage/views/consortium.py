import rest_framework.decorators as rf_decorators
import rest_framework.response as rf_response
import rest_framework.permissions as rf_perms
from rest_framework import mixins, viewsets

import oauth2_provider.contrib.rest_framework as oauth2_rf

from ..models import Consortium, Project, Quota
from ..permissions import (
    ConsortiumNestedViewSetPermissions,
    ConsortiumPermissions,
    ConsortiumQuotaViewSetPermissions,
)
from ..serializers import (
    ConsortiumSerializer,
    ConsortiumSummarySerializer,
    ProjectSerializer,
    QuotaSerializer,
)
from .base import BaseViewSet, TokenHasAtLeastOneScope


class ConsortiumViewSet(BaseViewSet, viewsets.ReadOnlyModelViewSet):
    """
    View set for the consortium model.
    """

    permission_classes = [ConsortiumPermissions]

    queryset = Consortium.objects.prefetch_related("manager", "quotas")
    serializer_class = ConsortiumSerializer
    action_serializers = {"summary": ConsortiumSummarySerializer}

    def get_serializer_class(self):
        if hasattr(self, "action_serializers"):
            return self.action_serializers.get(self.action, self.serializer_class)

        return super().get_serializer_class()

    def get_queryset(self):
        queryset = super().get_queryset()
        # Always annotate with summary information for the current user
        queryset = queryset.annotate_summary(self.request.user)
        # When listing consortia, we need to apply filtering for the user
        if self.action == "list":
            queryset = queryset.filter_visible(self.request.user)
        return queryset

    @rf_decorators.action(detail=True, required_scopes=["jasmin_manage.projects"])
    def summary(self, request, pk=None):
        """Create summary of projects in Consortium"""
        serializer = ConsortiumSummarySerializer(
            self.get_object(), context={"request": request}
        )
        return rf_response.Response(serializer.data)


# class ConsortiumProjectsSummaryViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
#     """
#     View set for summarising projects in a consortium.
#     """
#     permission_classes = [ConsortiumNestedViewSetPermissions]

#     queryset = Project.objects.all()
#     serializer_class = ProjectSerializer

#     def get_queryset(self):
#         queryset = super().get_queryset()
#         # Annotate the queryset with summary information to avoid the N+1 problem
#         queryset = queryset.annotate_summary(self.request.user)
#         # Filter the resources by consortium
#         return queryset.filter(consortium = self.kwargs['consortium_pk'])


class ConsortiumProjectsViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    View set for listing projects for a consortium.
    """

    permission_classes = [ConsortiumNestedViewSetPermissions]

    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        # Annotate the queryset with summary information to avoid the N+1 problem
        queryset = queryset.annotate_summary(self.request.user)
        # Filter the resources by consortium
        return queryset.filter(consortium=self.kwargs["consortium_pk"])


class ConsortiumQuotasViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    View set for listing the quotas for a consortium.
    """
    permission_classes = [ConsortiumQuotaViewSetPermissions]
    required_scopes = ["jasmin.projects.services.all", "jasmin.projects.all"]

    queryset = Quota.objects.all()
    serializer_class = QuotaSerializer

    def get_queryset(self):
        # Filter the resources by consortium and annotate with usage
        queryset = (
            super().get_queryset().filter(consortium=self.kwargs["consortium_pk"])
        )
        return queryset.annotate_usage()

    def get_permissions(self):
        if self.action == "list":
            # if not self.request.user:
            #     perms = TokenHasAtLeastOneScope()
            #     permission_classes = [
            #         rf_perms.OR(perms, rf_perms.IsAdminUser())
            #     ]
            # else:
            #     perms = ConsortiumQuotaViewSetPermissions()
            #     permission_classes = [perms]
            # return permission_classes
            token_perms = TokenHasAtLeastOneScope()
            user_perms = ConsortiumQuotaViewSetPermissions()
            permissions_classes = [
                rf_perms.OR(token_perms, user_perms)
            ]
            return permissions_classes
        return super().get_permissions()