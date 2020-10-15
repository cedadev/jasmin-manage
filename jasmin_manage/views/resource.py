from rest_framework import viewsets

from ..models import Resource
from ..serializers import ResourceSerializer


class ResourceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View set for the resource model.
    """
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
