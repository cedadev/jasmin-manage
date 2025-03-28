from django.http import Http404

from rest_framework.permissions import IsAuthenticated, SAFE_METHODS

from ..models import Consortium


def user_can_view_consortium(user, consortium):
    """
    Returns true if the user can view the consortium, false otherwise.
    """
    if consortium.is_public:
        # All users can view public consortia
        return True
    elif user.is_staff:
        # Staff users can view all consortia
        return True
    elif consortium.manager == user:
        # Managers can view their own consortia
        return True
    else:
        # Non-staff users can view a non-public consortium if they belong
        # to a project in the consortium
        return consortium.projects.filter(collaborator__user=user).exists()


def user_can_view_quota(user, consortium):
    """
    Returns true if the user can view the nested quota, false otherwise.
    """
    # Consortium managers can view the quotas
    if consortium.manager == user:
        return True

    # Project collaborators and owners can view the quotas
    elif consortium.projects.filter(collaborator__user=user).exists():
        return True
    # Nobody else can see the quotas
    else:
        return False


def user_is_staff(user):
    """Returns true if the user is marked as staff, false otherwise."""
    # We want staff to be able to see quotas
    if user.is_staff:
        return True
    else:
        return False


class ConsortiumPermissions(IsAuthenticated):
    """
    DRF permissions class for the consortium viewset.
    """

    def has_object_permission(self, request, view, obj):
        if not super().has_object_permission(request, view, obj):
            return False
        # Always raise a 404 on failure in order to hide information about valid consortia
        if user_can_view_consortium(request.user, obj):
            return True
        else:
            raise Http404


class ConsortiumNestedViewSetPermissions(IsAuthenticated):
    """
    DRF permissions class for the nested consortium viewsets (for projects and quotas)
    that require the user to be the consortium manager.
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        # Get the consortium using the key from the viewset
        consortium = (
            Consortium.objects.prefetch_related("manager")
            .filter(pk=view.kwargs["consortium_pk"])
            .first()
        )
        if consortium and user_can_view_consortium(request.user, consortium):
            # Only the consortium manager is allowed to access nested resources
            # However we want to explicitly deny permission in the case where the consortium
            # is visible to the user but they are not the manager
            return request.user == consortium.manager
        else:
            # Raise not found in the case where the consortium does not exist, but also in the
            # case where the consortium is not visible to the user
            raise Http404


class ConsortiumQuotaViewSetPermissions(IsAuthenticated):
    """
    DRF permissions class for the nested consortium quota viewset that allow
    consortium managers, project owners and project collaborators to see quotas.
    """
    def has_permission(self, request, view):
        print(request)

        if not super().has_permission(request, view):
            return False
        # Get the consortium using the key from the viewset
        consortium = (
            Consortium.objects.prefetch_related("manager")
            .filter(pk=view.kwargs["consortium_pk"])
            .first()
        )
        if consortium and user_can_view_quota(request.user, consortium):
            return True
        elif user_is_staff(request.user):
            print("User marked as staff")
            return True
        # If a user can see the consortium but can't see the quota, explicitly deny permission
        elif consortium and user_can_view_consortium(request.user, consortium):
            return False
        else:
            # Raise not found in the case where the consortium does not exist, but also in the
            # case where the consortium is not visible to the user
            raise Http404
