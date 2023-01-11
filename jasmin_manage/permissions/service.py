from .base import BaseProjectPermissions


class ServicePermissions(BaseProjectPermissions):
    """
    DRF permissions class determining permissions for services.
    """
    def get_project_from_viewset(self, viewset):
        try:
            return viewset.project
        except AttributeError:
            return None

    def get_project_from_object(self, obj):
        return obj.project

    def has_action_permission(self, project, user, action, obj = None):
        if action in {'list', 'retrieve'}:
            # Collaborators and consortium managers can see services
            return (
                self.is_consortium_manager(project, user) or
                self.is_project_collaborator(project, user) or 
                user.is_staff
            )
        elif action in {'create', 'destroy'}:
            # Any project collaborator can create and delete services
            return self.is_project_collaborator(project, user)
        else:
            # Default to deny for any unknown actions
            return False
