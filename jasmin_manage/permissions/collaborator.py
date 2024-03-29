from rest_framework.permissions import IsAuthenticated

from .base import BaseProjectPermissions


class CollaboratorPermissions(BaseProjectPermissions):
    """
    DRF permissions class determining permissions for collaborator objects.
    """

    def get_project_from_viewset(self, viewset):
        return viewset.project

    def get_project_from_object(self, obj):
        return obj.project

    def has_action_permission(self, project, user, action, obj=None):
        # Allow project collaborators and consortium managers to view the collaborators
        # Allow only owners to modify or delete collaborators
        # Collaborators cannot be created directly
        if action in {"list", "retrieve"}:
            return (
                self.is_consortium_manager(project, user)
                or self.is_project_collaborator(project, user)
                or user.is_staff
            )
        elif action in {"update", "partial_update", "destroy"}:
            return self.is_project_owner(project, user)
        else:
            # Default to deny for any unknown actions
            return False
