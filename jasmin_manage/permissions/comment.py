from rest_framework.permissions import IsAuthenticated

from .base import BaseProjectPermissions


class CommentPermissions(BaseProjectPermissions):
    """
    DRF permissions class determining permissions for comment objects.
    """
    def get_project_from_viewset(self, viewset):
        return viewset.project

    def get_project_from_object(self, obj):
        return obj.project

    def has_action_permission(self, project, user, action, obj = None):
        if action in {'list', 'retrieve', 'create'}:
            # Comments can be viewed and created by:
            return (
                # Consortium managers
                self.is_consortium_manager(project, user) or
                # Project collaborators
                self.is_project_collaborator(project, user)
            )
        elif action in {'update', 'partial_update', 'destroy'}:
            # Project owners can update or delete any comments
            if self.is_project_owner(project, user):
                return True
            # Other users can only update their own comments
            if obj.user != user:
                return False
            # But only if they are still associated with the project, either
            # as a manager or a contributor
            return (
                self.is_consortium_manager(project, user) or
                self.is_project_collaborator(project, user)
            )
        else:
            # Any other actions are denied
            return False
