from ..models import Category

from .base import BaseSerializer


class CategorySerializer(BaseSerializer):
    """
    Serializer for the category model.
    """
    class Meta:
        model = Category
        # Categories are readonly in the API, so no version is required
        exclude = ('version', )
