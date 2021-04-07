from rest_framework.permissions import IsAuthenticated

from .base import BaseProjectPermissions


class InvitationPermissions(BaseProjectPermissions):
    """
    DRF permissions class determining permissions for invitation objects.
    """
    def get_project_from_viewset(self, viewset):
        return viewset.project

    def get_project_from_object(self, obj):
        return obj.project

    def has_action_permission(self, project, user, action, obj = None):
        # Allow project collaborators and consortium managers to view the invitations
        # Allow only owners to create or delete invitations
        if action in {'list', 'retrieve'}:
            return (
                self.is_consortium_manager(project, user) or
                self.is_project_collaborator(project, user)
            )
        elif action in {'create', 'destroy'}:
            return self.is_project_owner(project, user)
        else:
            # Default to deny for any unknown actions
            return False
