from ..models import Service

from .base import BaseSerializer


class ServiceSerializer(BaseSerializer):
    """
    Serializer for the service model.
    """
    class Meta:
        model = Service
        fields = '__all__'
