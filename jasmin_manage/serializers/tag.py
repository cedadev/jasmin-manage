from ..models import Tag

from .base import BaseSerializer


class TagSerializer(BaseSerializer):
    """
    Serializer for the tag model.
    """

    class Meta:
        model = Tag
        fields = "__all__"
