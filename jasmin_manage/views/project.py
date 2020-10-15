from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Project, Requirement, Service
from ..serializers import ProjectSerializer, RequirementSerializer, ServiceSerializer


class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View set for the project model.
    """
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    @action(detail = True, methods = ['GET'])
    def services(self, request, pk = None):
        """
        Returns the services for the project.
        """
        queryset = Service.objects.filter(project = pk)
        context = self.get_serializer_context()
        serializer = ServiceSerializer(queryset, many = True, context = context)
        return Response(serializer.data)

    @action(detail = True, methods = ['GET'])
    def requirements(self, request, pk = None):
        """
        Returns the requirements for the project.
        """
        queryset = Requirement.objects.filter(service__project = pk)
        context = self.get_serializer_context()
        serializer = RequirementSerializer(queryset, many = True, context = context)
        return Response(serializer.data)
