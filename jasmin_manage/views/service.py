from rest_framework import mixins, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import SAFE_METHODS

from ..exceptions import Conflict
from ..models import Project, Requirement, Service
from ..serializers import RequirementSerializer, ServiceSerializer


# Services can only be listed and created via a project
class ServiceViewSet(mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     mixins.DestroyModelMixin,
                     viewsets.GenericViewSet):
    """
    View set for the resource model.
    """
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer

    def get_object(self):
        obj = super().get_object()
        # Edit options require the service's project to be editable
        if self.request.method in SAFE_METHODS:
            return obj
        elif obj.project.status == Project.Status.EDITABLE:
            return obj
        else:
            raise Conflict('Project is not currently editable.')

    def perform_destroy(self, instance):
        # A service can only be deleted if it has no requirements
        if not instance.requirements.exists():
            super().perform_destroy(instance)
        else:
            raise Conflict('Cannot delete service with requirements.')


class ServiceRequirementsViewSet(mixins.ListModelMixin,
                                 mixins.CreateModelMixin,
                                 viewsets.GenericViewSet):
    """
    View set for listing and creating requirements for a service.
    """
    queryset = Requirement.objects.all()
    serializer_class = RequirementSerializer

    def get_queryset(self):
        return super().get_queryset().filter(service = self.kwargs['service_pk'])

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update(service = get_object_or_404(Service, pk = self.kwargs['service_pk']))
        return context

    def perform_create(self, serializer):
        project = serializer.context['service'].project
        if project.status == Project.Status.EDITABLE:
            super().perform_create(serializer)
        else:
            raise Conflict('Project is not currently editable.')
