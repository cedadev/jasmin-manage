from rest_framework import mixins, permissions, viewsets

from ..models import Consortium, Project, Quota
from ..permissions import ConsortiumNestedViewSetPermissions
from ..serializers import (
    ConsortiumSerializer,
    ProjectSerializer,
    QuotaSerializer
)


class ConsortiumViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View set for the consortium model.
    """
    permission_classes = [permissions.IsAuthenticated]

    queryset = Consortium.objects.all()
    serializer_class = ConsortiumSerializer


class ConsortiumProjectsViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    View set for listing projects for a consortium.
    """
    permission_classes = [ConsortiumNestedViewSetPermissions]

    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    def get_queryset(self):
        # Filter the resources by consortium
        return super().get_queryset().filter(consortium = self.kwargs['consortium_pk'])


class ConsortiumQuotasViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    View set for listing the quotas for a consortium.
    """
    permission_classes = [ConsortiumNestedViewSetPermissions]

    queryset = Quota.objects.all()
    serializer_class = QuotaSerializer

    def get_queryset(self):
        # Filter the resources by consortium
        return super().get_queryset().filter(consortium = self.kwargs['consortium_pk'])
