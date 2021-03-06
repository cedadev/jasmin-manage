from django.utils.functional import cached_property

from rest_framework import mixins, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import SAFE_METHODS

from ..exceptions import Conflict
from ..models import Project, Requirement, Service
from ..permissions import RequirementPermissions, ServicePermissions
from ..serializers import RequirementSerializer, ServiceSerializer


# Services can only be listed and created via a project
# They also cannot be updated via the API
class ServiceViewSet(mixins.RetrieveModelMixin,
                     mixins.DestroyModelMixin,
                     viewsets.GenericViewSet):
    """
    View set for the resource model.
    """
    permission_classes = [ServicePermissions]

    queryset = Service.objects.all()
    serializer_class = ServiceSerializer

    def perform_destroy(self, instance):
        # To delete a service, the project must be editable
        if instance.project.status != Project.Status.EDITABLE:
            raise Conflict('Project is not currently editable.', 'invalid_status')
        # A service can only be deleted if it has no requirements
        if instance.requirements.exists():
            raise Conflict('Cannot delete service with requirements.', 'has_requirements')
        super().perform_destroy(instance)


class ServiceRequirementsViewSet(mixins.ListModelMixin,
                                 mixins.CreateModelMixin,
                                 viewsets.GenericViewSet):
    """
    View set for listing and creating requirements for a service.
    """
    permission_classes = [RequirementPermissions]

    queryset = Requirement.objects.all()
    serializer_class = RequirementSerializer

    def get_queryset(self):
        return super().get_queryset().filter(service = self.kwargs['service_pk'])

    @cached_property
    def service(self):
        return get_object_or_404(Service, pk = self.kwargs['service_pk'])

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Creating a requirement requires that we inject the service into the serializer context
        if self.action == 'create':
            context.update(service = self.service)
        return context

    def create(self, request, *args, **kwargs):
        # The project must be editable to create services
        if self.service.project.status == Project.Status.EDITABLE:
            return super().create(request, *args, **kwargs)
        else:
            raise Conflict('Project is not currently editable.', 'invalid_status')
