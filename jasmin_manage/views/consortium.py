from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Consortium, Project, Quota
from ..serializers import (
    ConsortiumSerializer,
    ProjectSerializer,
    QuotaSerializer
)


class ConsortiumViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View set for the consortium model.
    """
    queryset = Consortium.objects.all()
    serializer_class = ConsortiumSerializer

    @action(detail = True, methods = ['GET'])
    def projects(self, request, pk = None):
        """
        Returns the projects for the consortium.
        """
        queryset = Project.objects.filter(consortium = pk)
        context = self.get_serializer_context()
        serializer = ProjectSerializer(queryset, many = True, context = context)
        return Response(serializer.data)

    @action(detail = True, methods = ['GET'])
    def quotas(self, request, pk = None):
        """
        Returns the quotas for the consortium.
        """
        queryset = Quota.objects.filter(consortium = pk)
        context = self.get_serializer_context()
        serializer = QuotaSerializer(queryset, many = True, context = context)
        return Response(serializer.data)
