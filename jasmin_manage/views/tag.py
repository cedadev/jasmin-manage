from rest_framework import mixins, permissions, viewsets

from ..models import Tag
from ..serializers import TagSerializer
from .base import BaseViewSet


class TagViewSet(
    BaseViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):  # , viewsets.ReadOnlyModelViewSet):
    """
    View set for the tag model.
    """

    permission_classes = [permissions.IsAuthenticated]

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
