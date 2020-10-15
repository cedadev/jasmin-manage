from ..models import Category

from .base import BaseSerializer


class CategorySerializer(BaseSerializer):
    """
    Serializer for the category model.
    """
    class Meta:
        model = Category
        exclude = ('version', 'resources')
