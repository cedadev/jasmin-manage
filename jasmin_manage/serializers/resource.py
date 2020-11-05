from ..models import Resource

from .base import BaseSerializer


class ResourceSerializer(BaseSerializer):
    """
    Serializer for the resource model.
    """
    class Meta:
        model = Resource
        fields = '__all__'
