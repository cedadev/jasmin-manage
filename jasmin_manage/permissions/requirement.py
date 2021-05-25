from .base import BaseProjectPermissions


class RequirementPermissions(BaseProjectPermissions):
    """
    DRF permissions class determining permissions for requirements.
    """
    def get_project_from_viewset(self, viewset):
        # The viewset has no project
        return viewset.service.project

    def get_project_from_object(self, obj):
        return obj.service.project

    def has_action_permission(self, project, user, action, obj = None):
        if action in {'list', 'retrieve'}:
            return (
                self.is_consortium_manager(project, user) or
                self.is_project_collaborator(project, user) or 
                user.is_staff
            )
        elif action in {'create', 'update', 'partial_update', 'destroy'}:
            # Any project collaborator can create, edit and delete requirements
            return self.is_project_collaborator(project, user)
        elif action in {'approve', 'reject'}:
            # Only the consortium manager can approve or reject
            return self.is_consortium_manager(project, user)
        else:
            # Default to deny for any unknown actions
            return False
