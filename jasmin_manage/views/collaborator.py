from rest_framework import mixins, viewsets

from ..exceptions import Conflict
from ..models import Collaborator
from ..permissions import CollaboratorPermissions
from ..serializers import CollaboratorSerializer


# Collaborators can only be listed and created via a project
class CollaboratorViewSet(mixins.RetrieveModelMixin,
                          mixins.UpdateModelMixin,
                          mixins.DestroyModelMixin,
                          viewsets.GenericViewSet):
    """
    View set for the collaborator model.
    """
    permission_classes = [CollaboratorPermissions]

    queryset = Collaborator.objects.all()
    serializer_class = CollaboratorSerializer

    def _is_sole_owner(self, instance):
        # If the instance is not an owner, then it can't be the sole owner
        if instance.role != Collaborator.Role.OWNER:
            return False
        # Otherwise check that it is not the only owner of the project
        owners = instance.project.collaborators.filter(role = Collaborator.Role.OWNER)
        return not owners.exclude(pk = instance.pk).exists()

    def perform_update(self, serializer):
        # Check that the project will still have an owner after the update
        role = serializer.validated_data.get('role')
        if role:
            # If the role is being updated, it must not leave the project without an owner
            # If the new role is owner, then that is not possible
            # If the new role is not owner, then the instance being updated must not be the last owner
            if role != Collaborator.Role.OWNER and self._is_sole_owner(serializer.instance):
                raise Conflict('Project must have an owner.', 'sole_owner')
        return super().perform_update(serializer)

    def perform_destroy(self, instance):
        # Make sure that deleting the instance would not leave the project without an owner
        if not self._is_sole_owner(instance):
            return super().perform_destroy(instance)
        else:
            raise Conflict('Project must have an owner.', 'sole_owner')
