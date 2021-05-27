from .base import BaseProjectPermissions
from _ast import Or


class ProjectPermissions(BaseProjectPermissions):
    """
    DRF permissions class determining permissions for projects.
    """
    def get_project_from_viewset(self, viewset):
        # The viewset has no project
        return None

    def get_project_from_object(self, obj):
        return obj

    def has_action_permission(self, project, user, action, obj = None):
        if action in {'list', 'create'}:
            # List and create are permitted for any authenticated user
            return True
        elif action in {'retrieve', 'events'}:
            return (
                self.is_consortium_manager(project, user) or
                self.is_project_collaborator(project, user) or 
                user.is_staff
            )
        elif action in {'update', 'partial_update', 'submit_for_review'}:
            return self.is_project_owner(project, user)
        elif action in {'request_changes', 'submit_for_provisioning'}:
            return self.is_consortium_manager(project, user)
        else:
            # Default to deny for any unknown actions
            return False
