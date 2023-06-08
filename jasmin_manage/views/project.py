from functools import partial, wraps

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.utils.functional import cached_property

from rest_framework import mixins, serializers, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.reverse import reverse

from tsunami.models import Event
from tsunami.tracking import _instance_as_dict as instance_as_dict

from ..exceptions import Conflict
from ..models import (
    Collaborator,
    Comment,
    Invitation,
    Project,
    Requirement,
    Service
)
from ..permissions import (
    CollaboratorPermissions,
    CommentPermissions,
    InvitationPermissions,
    ProjectPermissions,
    ServicePermissions
)
from ..serializers import (
    CollaboratorSerializer,
    CommentSerializer,
    InvitationSerializer,
    ProjectSerializer,
    RequirementSerializer,
    ServiceSerializer
)
from .base import BaseViewSet


class ActionCommentSerializer(serializers.Serializer):
    """
    Serializer for requiring a comment when a project action is performed.
    """
    comment = serializers.CharField(
        help_text = "Can contain markdown syntax.",
        # Use a textarea when rendering the browsable API
        style = dict(base_template = 'textarea.html')
    )


class EventUserSerializer(serializers.ModelSerializer):
    """
    Serializer for the user of an event.
    """
    class Meta:
        model = get_user_model()
        fields = ('id', 'username', 'first_name', 'last_name')


class EventSerializer(serializers.ModelSerializer):
    """
    Serializer for project events.
    """
    class Meta:
        model = Event
        fields = (
            'id',
            'event_type',
            'target_type',
            'target_id',
            'target_link',
            'data',
            'user',
            'created_at'
        )

    target_type = serializers.SerializerMethodField()
    target_link = serializers.SerializerMethodField()
    data = serializers.SerializerMethodField()
    user = EventUserSerializer(read_only = True)

    def get_target_type(self, obj):
        return "{}.{}".format(obj.target_ctype.app_label, obj.target_ctype.model)

    def get_target_link(self, obj):
        try:
            return reverse(
                "{}-detail".format(obj.target_ctype.model),
                kwargs = dict(pk = obj.target_id),
                request = self.context['request']
            )
        except:
            return None

    def get_data(self, obj):
        return obj.data


class EventQueryParamsSerializer(serializers.Serializer):
    """
    Serializer used for parsing the query parameters for the project events view.
    """
    since = serializers.DateTimeField()


def project_action(viewset_method = None, serializer_class = serializers.Serializer):
    """
    Decorator that turns a project viewset method into an action that receives
    the project as its only argument.
    """
    # If no viewset method is given, return a decorator function
    if viewset_method is None:
        return partial(project_action, serializer_class = serializer_class)
    # Define the wrapper that processes the incoming data and finds the project
    @wraps(viewset_method)
    def wrapper(viewset, request, pk = None):
        # Get the project first - this will also process permissions
        project = viewset.get_object()
        # Then process the input data according to the serializer
        serializer = viewset.get_serializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        # Then call the view function
        return viewset_method(viewset, project, serializer.data)
    # Wrap the viewset method in the action decorator
    action_decorator = action(
        detail = True,
        methods = ['POST'],
        serializer_class = serializer_class
    )
    return action_decorator(wrapper)


def project_action_with_comment(viewset_method):
    """
    Decorator that turns a project viewset method into an action that requires
    a comment to be attached to the project.
    """
    @wraps(viewset_method)
    def wrapper(viewset, project, data):
        # Add the comment in the same transaction as the action runs
        with transaction.atomic():
            # Run the method first
            response = viewset_method(viewset, project, data)
            # If it is successful, add the comment as the authenticated user
            project.comments.create(
                content = data['comment'],
                user = viewset.request.user
            )
            # Return the original response
            return response
    return project_action(wrapper, ActionCommentSerializer)


# Projects cannot be deleted via the API
class ProjectViewSet(BaseViewSet,
                     mixins.ListModelMixin,
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
        if self.request.user:
            queryset = queryset.annotate_summary(self.request.user)
            # For a list operation, only show projects that the user is collaborating on
            # All other operations should be on a specific project and all projects should be used
            if self.action == 'list':
                queryset = queryset.filter(collaborator__user = self.request.user)
            return queryset
        return queryset

    @action(detail = True, serializer_class = EventSerializer)
    def events(self, request, pk = None):
        """
        List of events for the project.

        Supports a GET parameter called `since` that, if given, should be an ISO-formatted
        datetime and only events that occured since that time will be returned.
        """
        # Get the project itself
        project = self.get_object()
        # Get the content type for the project model
        content_type = ContentType.objects.get_for_model(project)
        # Filter the events so that only project events are included
        events = (
            Event.objects
                .filter(
                    aggregate__aggregate_ctype = content_type,
                    aggregate__aggregate_id = project.pk
                )
                .select_related('target_ctype', 'user')
        )
        # Check if the since parameter was given and use it to filter the events
        if request.query_params:
            params_serializer = EventQueryParamsSerializer(data = request.query_params)
            params_serializer.is_valid(raise_exception = True)
            events = events.filter(created_at__gt = params_serializer.data['since'])
        serializer = self.get_serializer(events, many = True)
        return Response(serializer.data)

    @project_action_with_comment
    def submit_for_review(self, project, data):
        """
        Submit the project for review.
        """
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

    @project_action_with_comment
    def request_changes(self, project, data):
        """
        Request changes to the project before it is submitted for provisioning.
        """
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

    @project_action
    def submit_for_provisioning(self, project, data):
        """
        Submit approved requirements for provisioning.
        """
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


# Collaborators cannot be created directly - they are created using invitations
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


class ProjectCommentsViewSet(mixins.ListModelMixin,
                             mixins.CreateModelMixin,
                             viewsets.GenericViewSet):
    """
    View set for listing and creating comments for a project.
    """
    permission_classes = [CommentPermissions]

    queryset = Comment.objects.select_related('user')
    serializer_class = CommentSerializer

    def get_queryset(self):
        return super().get_queryset().filter(project = self.kwargs['project_pk'])

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Creating a comment requires that we inject the project into the serializer context
        if self.action == 'create':
            context.update(project = self.project)
        return context

    # This property is required for the permissions check for listing
    @cached_property
    def project(self):
        return get_object_or_404(Project, pk = self.kwargs['project_pk'])


class ProjectInvitationsViewSet(mixins.ListModelMixin,
                                mixins.CreateModelMixin,
                                viewsets.GenericViewSet):
    """
    View set for listing and creating invitations for a project.
    """
    permission_classes = [InvitationPermissions]

    queryset = Invitation.objects.all()
    serializer_class = InvitationSerializer

    def get_queryset(self):
        return super().get_queryset().filter(project = self.kwargs['project_pk'])

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Creating an invitation requires that we inject the project into the serializer context
        if self.action == 'create':
            context.update(project = self.project)
        return context

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
