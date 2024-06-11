from django.http import Http404
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated

from ..models import Collaborator


class BaseProjectPermissions(IsAuthenticated):
    """
    Base class for DRF permissions classes for project resources.
    """

    def is_project_collaborator(self, project, user):
        """
        Returns true if the user is a collaborator for the project.
        """
        try:
            return project.collaborators.filter(user=user).exists()
        except AttributeError:
            return None

    def is_project_owner(self, project, user):
        """
        Returns true if the user is an owner for the project.
        """
        return project.collaborators.filter(
            user=user, role=Collaborator.Role.OWNER
        ).exists()

    def is_consortium_manager(self, project, user):
        """
        Returns true if the user is the consortium manager for the project.
        """
        try:
            return project.consortium.manager == user
        except AttributeError as e:
            print(e)
            return None

    def get_project_from_viewset(self, viewset):
        """
        Return the project for the given viewset.

        Used for actions when an object is not available, i.e. list, create and
        extra actions with `detail=False`.
        """
        raise NotImplementedError  # pragma: nocover

    def get_project_from_object(self, obj):
        """
        Return the project for the given object.

        Used for actions when an object is available, i.e. retrieve, update, destroy
        and extra actions with `detail=True`.
        """
        raise NotImplementedError  # pragma: nocover

    def has_action_permission(self, project, user, action, obj=None):
        """
        Returns true if the user has permission for the given action and project.
        """
        raise NotImplementedError  # pragma: nocover

    def _has_permission_or_404(self, request, view, project, obj=None):
        """
        Returns either a boolean indicating whether the user has permission to perform
        the action or raises a 404, depending on whether project is None or not.

        Raising a 404 is done to avoid exposing information about what is a valid
        project if the user is not permitted to access it.
        """
        # Determine the action and the corresponding safe action
        action = view.action
        safe_action = "retrieve" if view.detail else "list"
        # If no action is set and the request uses a safe method, use the safe action
        # to determine permissions
        # This is important for the browsable API as the renderer interrogates permissions
        # without setting an action
        if action is None and request.method in SAFE_METHODS:
            action = safe_action
        # For the metadata action, use the permissions for the safe action
        if action == "metadata":
            action = safe_action
        # Check whether the authenticated user has permission for the primary action
        has_permission = self.has_action_permission(project, request.user, action, obj)
        # If the user has permission, we are done
        if has_permission:
            return True
        # Otherwise, decide whether to return a 403 or a 404 to aid information hiding
        # If there is no project, always use permission denied as there is no information to hide
        if not project:
            return False
        # For safe methods, always use not found to hide the existence of the project
        if request.method in SAFE_METHODS:
            raise Http404
        # For unsafe methods, it depends whether they are denied from seeing the object
        # at all or whether they are just not allowed to execute this action
        # Use the permission for the safe action to determine this
        if self.has_action_permission(project, request.user, safe_action, obj):
            return False
        else:
            raise Http404

    def has_permission(self, request, view):
        # If the parent check fails, we are done (the user is not logged in.)
        if not super().has_permission(request, view):
            return False
        # If the view is a detail view, defer to the object permissions
        if view.detail:
            return True
        # Extract the project from the viewset
        project = self.get_project_from_viewset(view)
        # Use it to determine the permissions
        return self._has_permission_or_404(request, view, project)

    def has_object_permission(self, request, view, obj):
        # Get the project from the object
        project = self.get_project_from_object(obj)
        # Use the project to determine the permissions
        return self._has_permission_or_404(request, view, project, obj)
