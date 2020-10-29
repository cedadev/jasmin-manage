from rest_framework import mixins, serializers, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.decorators import action
from rest_framework.response import Response

from ..exceptions import Conflict
from ..models import Collaborator, Project, Requirement, Service
from ..serializers import (
    read_only_serializer,
    CollaboratorSerializer,
    ProjectSerializer,
    RequirementSerializer,
    ServiceSerializer
)


ReadOnlyProjectSerializer = read_only_serializer(ProjectSerializer)


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

    @action(detail = True, methods = ['POST'], serializer_class = ReadOnlyProjectSerializer)
    def submit_for_review(self, request, pk = None):
        """
        Submit the project for review.
        """
        project = self.get_object()
        # The project must be editable
        if project.status != Project.Status.EDITABLE:
            status = Project.Status(project.status).name
            raise Conflict(f'Cannot submit project with status {status} for review.')
        # A project with no requirements in the requested state cannot be submitted for review
        if not (
            Requirement.objects
                .filter(service__project = project, status = Requirement.Status.REQUESTED)
                .exists()
        ):
            raise Conflict('Project has no requirements to review.')
        # Update the project status and return it
        project.status = Project.Status.UNDER_REVIEW
        project.save()
        return Response(self.get_serializer(project).data)

    @action(detail = True, methods = ['POST'], serializer_class = ReadOnlyProjectSerializer)
    def request_changes(self, request, pk = None):
        """
        Request changes to the project before it is submitted for provisioning.
        """
        project = self.get_object()
        # The project must be under review
        if project.status != Project.Status.UNDER_REVIEW:
            status = Project.Status(project.status).name
            raise Conflict(f'Cannot request changes for project with status {status}.')
        # There must not be any requirements in the requested state
        # We expect a decision on each requirement before returning the project
        requested = Requirement.objects.filter(
            service__project = project,
            status = Requirement.Status.REQUESTED
        )
        if requested.exists():
            raise Conflict('Please resolve outstanding requirements before requesting changes.')
        # Update the project status and return it
        project.status = Project.Status.EDITABLE
        project.save()
        return Response(self.get_serializer(project).data)

    @action(detail = True, methods = ['POST'], serializer_class = ReadOnlyProjectSerializer)
    def submit_for_provisioning(self, request, pk = None):
        """
        Submit approved requirements for provisioning.
        """
        project = self.get_object()
        # The project must be under review
        if project.status != Project.Status.UNDER_REVIEW:
            status = Project.Status(project.status).name
            raise Conflict(f'Cannot submit project with status {status} for provisioning.')
        # All requirements must be approved
        unapproved = Requirement.objects.filter(
            service__project = project,
            status__lt = Requirement.Status.APPROVED
        )
        if unapproved.exists():
            raise Conflict('All requirements must be approved before submitting for provisioning.')
        # Move all the approved requirements into the awaiting provisioning state
        approved = Requirement.objects.filter(
            service__project = project,
            status = Requirement.Status.APPROVED
        )
        approved.update(status = Requirement.Status.AWAITING_PROVISIONING)
        # Update the project status and return it
        project.status = Project.Status.EDITABLE
        project.save()
        return Response(self.get_serializer(project).data)


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
