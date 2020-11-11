from django.http import Http404

from rest_framework.permissions import IsAuthenticated, SAFE_METHODS

from ..models import Consortium


class ConsortiumNestedViewSetPermissions(IsAuthenticated):
    """
    DRF permissions class for the nested consortium viewsets (for projects and quotas)
    that require the user to be the consortium manager.
    """
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        queryset = Consortium.objects.filter(
            pk = view.kwargs['consortium_pk'],
            manager = request.user
        )
        # Always raise a 404 on failure, as even if this is called with an unsafe method
        # the same permissions apply for the corresponding safe method
        if request.method in SAFE_METHODS and queryset.exists():
            return True
        else:
            raise Http404
