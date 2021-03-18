from django.db import models
from django.utils.functional import cached_property

from rest_framework import mixins, serializers, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.decorators import action
from rest_framework.response import Response

from ..exceptions import Conflict
from ..models import Collaborator, Project, Requirement, Service
from ..permissions import CollaboratorPermissions, ProjectPermissions, ServicePermissions
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
    permission_classes = [ProjectPermissions]

    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        # Annotate the queryset with summary information to avoid the N+1 problem
        queryset = queryset.annotate_summary(self.request.user)
        # For a list operation, only show projects that the user is collaborating on
        # All other operations should be on a specific project and all projects should be used
        if self.action == 'list':
            queryset = queryset.filter(collaborator__user = self.request.user)
        return queryset

    @action(detail = True, methods = ['POST'], serializer_class = serializers.Serializer)
    def submit_for_review(self, request, pk = None):
        """
        Submit the project for review.
        """
        project = self.get_object()
        # The project must be editable
        if project.status != Project.Status.EDITABLE:
            status = Project.Status(project.status).name
            raise Conflict(
                f'Cannot submit project with status {status} for review.',
                'invalid_status'
            )
        # Fetch the number of requested and rejected requirements for the project in one query
        requirement_counts = (
            Requirement.objects
                .filter(service__project = project)
                .aggregate(
                    requested_count = models.Count(
                        'status',
                        filter = models.Q(status = Requirement.Status.REQUESTED)
                    ),
                    rejected_count = models.Count(
                        'status',
                        filter = models.Q(status = Requirement.Status.REJECTED)
                    ),
                    approved_count = models.Count(
                        'status',
                        filter = models.Q(status = Requirement.Status.APPROVED)
                    ),
                )
        )
        # A project with requirements in the rejected state cannot be submitted for review
        if requirement_counts.get('rejected_count', 0) >= 1:
            raise Conflict(
                'Cannot submit project with rejected requirements.',
                'rejected_requirements'
            )
        # A project must have at least one requirement in either the requested or approved
        # state to be submitted for review
        requested_count = requirement_counts.get('requested_count', 0)
        approved_count = requirement_counts.get('approved_count', 0)
        if (requested_count + approved_count) < 1:
            raise Conflict(
                'Project has no requirements to review.',
                'no_requirements_to_review'
            )
        # Update the project status and return it
        project.status = Project.Status.UNDER_REVIEW
        project.save()
        context = self.get_serializer_context()
        return Response(ProjectSerializer(project, context = context).data)

    @action(detail = True, methods = ['POST'], serializer_class = serializers.Serializer)
    def request_changes(self, request, pk = None):
        """
        Request changes to the project before it is submitted for provisioning.
        """
        project = self.get_object()
        # The project must be under review
        if project.status != Project.Status.UNDER_REVIEW:
            status = Project.Status(project.status).name
            raise Conflict(
                f'Cannot request changes for project with status {status}.',
                'invalid_status'
            )
        # Fetch the number of requested and rejected requirements for the project in one query
        requirement_counts = (
            Requirement.objects
                .filter(service__project = project)
                .aggregate(
                    requested_count = models.Count(
                        'status',
                        filter = models.Q(status = Requirement.Status.REQUESTED)
                    ),
                    rejected_count = models.Count(
                        'status',
                        filter = models.Q(status = Requirement.Status.REJECTED)
                    ),
                )
        )
        # There must not be any requirements in the requested state
        # We expect a decision on each requirement before returning the project
        if requirement_counts.get('requested_count', 0) >= 1:
            raise Conflict(
                'Please resolve outstanding requirements before requesting changes.',
                'unresolved_requirements'
            )
        # There must be at least one requirement in the rejected state, otherwise everything is
        # approved and the project should be submitted for provisioning
        if requirement_counts.get('rejected_count', 0) < 1:
            raise Conflict(
                'All requirements have been approved - please submit for provisioning instead.',
                'no_changes_required'
            )
        # Update the project status and return it
        project.status = Project.Status.EDITABLE
        project.save()
        context = self.get_serializer_context()
        return Response(ProjectSerializer(project, context = context).data)

    @action(detail = True, methods = ['POST'], serializer_class = serializers.Serializer)
    def submit_for_provisioning(self, request, pk = None):
        """
        Submit approved requirements for provisioning.
        """
        project = self.get_object()
        # The project must be under review
        if project.status != Project.Status.UNDER_REVIEW:
            status = Project.Status(project.status).name
            raise Conflict(
                f'Cannot submit project with status {status} for provisioning.',
                'invalid_status'
            )
        # All requirements must be approved
        unapproved = Requirement.objects.filter(
            service__project = project,
            status__lt = Requirement.Status.APPROVED
        )
        if unapproved.exists():
            raise Conflict(
                'All requirements must be approved before submitting for provisioning.',
                'unapproved_requirements'
            )
        # Move all the approved requirements into the awaiting provisioning state
        approved = Requirement.objects.filter(
            service__project = project,
            status = Requirement.Status.APPROVED
        )
        approved.update(status = Requirement.Status.AWAITING_PROVISIONING)
        # Update the project status and return it
        project.status = Project.Status.EDITABLE
        project.save()
        context = self.get_serializer_context()
        return Response(ProjectSerializer(project, context = context).data)


# Collaborators will be created using an invite system
class ProjectCollaboratorsViewSet(mixins.ListModelMixin,
                                  viewsets.GenericViewSet):
    """
    View set for listing collaborators for a project.
    """
    permission_classes = [CollaboratorPermissions]

    queryset = Collaborator.objects.select_related('user')
    serializer_class = CollaboratorSerializer

    def get_queryset(self):
        return super().get_queryset().filter(project = self.kwargs['project_pk'])

    # This property is required for the permissions check for listing
    @cached_property
    def project(self):
        return get_object_or_404(Project, pk = self.kwargs['project_pk'])


class ProjectServicesViewSet(mixins.ListModelMixin,
                             mixins.CreateModelMixin,
                             viewsets.GenericViewSet):
    """
    View set for listing and creating services for a project.
    """
    permission_classes = [ServicePermissions]

    queryset = Service.objects.all()
    serializer_class = ServiceSerializer

    def get_queryset(self):
        return super().get_queryset().filter(project = self.kwargs['project_pk'])

    @cached_property
    def project(self):
        return get_object_or_404(Project, pk = self.kwargs['project_pk'])

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Creating a service requires that we inject the project into the serializer context
        if self.action == 'create':
            context.update(project = self.project)
        return context

    def create(self, request, *args, **kwargs):
        # The project must be editable to create services
        if self.project.status == Project.Status.EDITABLE:
            return super().create(request, *args, **kwargs)
        else:
            raise Conflict('Project is not currently editable.', 'invalid_status')
