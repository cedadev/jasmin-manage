from django.utils.functional import cached_property

from rest_framework import mixins, viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import SAFE_METHODS
import rest_framework.permissions as rf_perms
import oauth2_provider.contrib.rest_framework as oauth2_rf

from ..exceptions import Conflict
from ..models import Project, Requirement, Service
from ..permissions import RequirementPermissions, ServicePermissions
from ..serializers import (
    RequirementSerializer,
    ServiceSerializer,
    ServiceListSerializer,
)
from .base import BaseViewSet, TokenHasAtLeastOneScope


# Services cannot be updated via the API
class ServiceViewSet(
    BaseViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    View set for the service model.
    """

    queryset = Service.objects.all().prefetch_related("requirements")
    permission_classes = [ServicePermissions]
    required_scopes = ["jasmin.projects.services.all", "jasmin.projects.all"]

    def get_queryset(self):
        """
        Optionally restricts the returned services by filtering against a 
        service name query parameter in the URL.
        """
        queryset = super().get_queryset()
        service_name = self.request.query_params.get('name')
        if service_name is not None:
            queryset = queryset.filter(service__name=service_name)
        return queryset

    def perform_destroy(self, instance):
        # To delete a service, the project must be editable
        if instance.project.status != Project.Status.EDITABLE:
            raise Conflict("Project is not currently editable.", "invalid_status")
        # A service can only be deleted if it has no requirements
        if instance.requirements.exists():
            raise Conflict(
                "Cannot delete service with requirements.", "has_requirements"
            )
        super().perform_destroy(instance)

    def get_permissions(self):
        # If listing the services, edit the perimission classes to check user has permission
        # or is authenticated using a token with one of the required scopes.
        if self.action == "list":
            permission_classes = [
                rf_perms.OR(TokenHasAtLeastOneScope(), rf_perms.IsAdminUser())
            ]
            return permission_classes
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == "list":
            return ServiceListSerializer
        return ServiceSerializer


class ServiceRequirementsViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    """
    View set for listing and creating requirements for a service.
    """

    permission_classes = [RequirementPermissions]

    queryset = Requirement.objects.all()
    serializer_class = RequirementSerializer

    def get_queryset(self):
        return super().get_queryset().filter(service=self.kwargs["service_pk"])

    @cached_property
    def service(self):
        return get_object_or_404(Service, pk=self.kwargs["service_pk"])

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Creating a requirement requires that we inject the service into the serializer context
        if self.action == "create":
            context.update(service=self.service)
        return context

    def create(self, request, *args, **kwargs):
        # The project must be editable to create services
        if self.service.project.status == Project.Status.EDITABLE:
            return super().create(request, *args, **kwargs)
        else:
            raise Conflict("Project is not currently editable.", "invalid_status")