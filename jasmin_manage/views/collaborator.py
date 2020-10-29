from rest_framework import mixins, viewsets

from ..exceptions import Conflict
from ..models import Collaborator
from ..serializers import CollaboratorSerializer


# Collaborators can only be listed and created via a project
class CollaboratorViewSet(mixins.RetrieveModelMixin,
                          mixins.UpdateModelMixin,
                          mixins.DestroyModelMixin,
                          viewsets.GenericViewSet):
    """
    View set for the collaborator model.
    """
    queryset = Collaborator.objects.all()
    serializer_class = CollaboratorSerializer

    def is_sole_owner(self, instance):
        # If the instance is not an owner, then it can't be the sole owner
        if instance.role != Collaborator.Role.OWNER:
            return False
        # Otherwise check that it is not the only owner of the project
        owners = instance.project.collaborators.filter(role = Collaborator.Role.OWNER)
        return not owners.exclude(pk = instance.pk).exists()

    def perform_update(self, serializer):
        # Check that the project will still have an owner after the update
        new_role = serializer.validated_data['role']
        if new_role == Collaborator.Role.OWNER or not self.is_sole_owner(serializer.instance):
            return super().perform_update(serializer)
        else:
            raise Conflict('Project must have an owner.')

    def perform_destroy(self, instance):
        # Make sure that deleting the instance would not leave the project without an owner
        if not self.is_sole_owner(instance):
            return super().perform_destroy(instance)
        else:
            raise Conflict('Project must have an owner.')
