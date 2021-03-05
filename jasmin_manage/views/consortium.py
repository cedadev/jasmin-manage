from rest_framework import mixins, permissions, viewsets

from ..models import Consortium, Project, Quota
from ..permissions import (
    ConsortiumPermissions,
    ConsortiumNestedViewSetPermissions
)
from ..serializers import (
    ConsortiumSerializer,
    ProjectSerializer,
    QuotaSerializer
)


class ConsortiumViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View set for the consortium model.
    """
    permission_classes = [ConsortiumPermissions]

    queryset = Consortium.objects.select_related('manager')
    serializer_class = ConsortiumSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        # Always annotate with summary information for the current user
        queryset = queryset.annotate_summary(self.request.user)
        # When listing consortia, we need to apply filtering for the user
        if self.action == 'list':
            queryset = queryset.filter_visible(self.request.user)
        return queryset


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
        return queryset.filter(consortium = self.kwargs['consortium_pk'])


class ConsortiumQuotasViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    View set for listing the quotas for a consortium.
    """
    permission_classes = [ConsortiumNestedViewSetPermissions]

    queryset = Quota.objects.all()
    serializer_class = QuotaSerializer

    def get_queryset(self):
        # Filter the resources by consortium and annotate with usage
        queryset = super().get_queryset().filter(consortium = self.kwargs['consortium_pk'])
        return queryset.annotate_usage()
