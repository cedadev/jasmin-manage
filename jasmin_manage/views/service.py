from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Requirement, Service
from ..serializers import RequirementSerializer, ServiceSerializer


class ServiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View set for the resource model.
    """
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer

    @action(detail = True, methods = ['GET'])
    def requirements(self, request, pk = None):
        """
        Returns the requirements for the project.
        """
        queryset = Requirement.objects.filter(service = pk)
        context = self.get_serializer_context()
        serializer = RequirementSerializer(queryset, many = True, context = context)
        return Response(serializer.data)
