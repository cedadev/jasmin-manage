from rest_framework import permissions, viewsets

from ..models import Resource
from ..serializers import ResourceSerializer
from .base import BaseViewSet


class ResourceViewSet(BaseViewSet, viewsets.ReadOnlyModelViewSet):
    """
    View set for the resource model.
    """

    permission_classes = [permissions.IsAuthenticated]

    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
