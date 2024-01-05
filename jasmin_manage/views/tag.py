from rest_framework import permissions, viewsets

from ..models import Tag
from ..serializers import TagSerializer
from .base import BaseViewSet


class TagViewSet(BaseViewSet, viewsets.ReadOnlyModelViewSet):
    """
    View set for the tag model.
    """

    permission_classes = [permissions.IsAuthenticated]

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
