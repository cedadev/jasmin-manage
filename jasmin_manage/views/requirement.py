from rest_framework import mixins, viewsets
from rest_framework.permissions import SAFE_METHODS

from ..exceptions import Conflict
from ..models import Project, Requirement
from ..serializers import RequirementSerializer


# Requirements can only be listed and created via a service
class RequirementViewSet(mixins.RetrieveModelMixin,
                         mixins.UpdateModelMixin,
                         mixins.DestroyModelMixin,
                         viewsets.GenericViewSet):
    """
    View set for the resource model.
    """
    queryset = Requirement.objects.all()
    serializer_class = RequirementSerializer

    def get_object(self):
        obj = super().get_object()
        # If the request is a safe method, we are done
        if self.request.method in SAFE_METHODS:
            return obj
        # The project status must be editable
        if obj.service.project.status != Project.Status.EDITABLE:
            raise Conflict('Project is not currently editable.')
        # In order to be updated or deleted, the requirement must be pre-approval
        if obj.status >= Requirement.Status.APPROVED:
            raise Conflict('Approved requirements cannot be modified.')
        # If we get here, the operation is permitted
        return obj

    def perform_update(self, serializer):
        # Updating a requirement causes it to go back into the requested state
        serializer.save(status = Requirement.Status.REQUESTED)
