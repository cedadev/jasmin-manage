from rest_framework import mixins, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.decorators import action
from rest_framework.response import Response

from ..exceptions import Conflict
from ..models import Collaborator, Project, Requirement, Service
from ..serializers import (
    CollaboratorSerializer,
    ProjectSerializer,
    RequirementSerializer,
    ServiceSerializer
)


# Projects cannot be deleted via the API
class ProjectViewSet(mixins.ListModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.CreateModelMixin,
                     mixins.UpdateModelMixin,
                     viewsets.GenericViewSet):
    """
    View set for the project model.
    """
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        # For a list operation, only show projects that the user is collaborating on
        # All other operations should be on a specific project and all projects should be used
        if self.action == 'list':
            if getattr(self.request.user, 'is_authenticated', False):
                queryset = queryset.filter(collaborator__user = self.request.user)
            else:
                queryset = queryset.none()
        return queryset


class ProjectCollaboratorsViewSet(mixins.ListModelMixin,
                                  mixins.CreateModelMixin,
                                  viewsets.GenericViewSet):
    """
    View set for listing and creating collaborators for a project.
    """
    queryset = Collaborator.objects.all()
    serializer_class = CollaboratorSerializer

    def get_queryset(self):
        return super().get_queryset().filter(project = self.kwargs['project_pk'])

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update(project = get_object_or_404(Project, pk = self.kwargs['project_pk']))
        return context


class ProjectServicesViewSet(mixins.ListModelMixin,
                             mixins.CreateModelMixin,
                             viewsets.GenericViewSet):
    """
    View set for listing and creating services for a project.
    """
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer

    def get_queryset(self):
        return super().get_queryset().filter(project = self.kwargs['project_pk'])

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update(project = get_object_or_404(Project, pk = self.kwargs['project_pk']))
        return context

    def perform_create(self, serializer):
        # The project must be editable to create services
        project = serializer.context['project']
        if project.status == Project.Status.EDITABLE:
            super().perform_create(serializer)
        else:
            raise Conflict('Project is not currently editable.')
