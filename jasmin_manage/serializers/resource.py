from rest_framework import serializers

from ..models import Requirement, Resource

from .base import BaseSerializer


class ResourceSerializer(BaseSerializer):
    """
    Serializer for the resource model.
    """
    class Meta:
        model = Resource
        exclude = ('version', )

    total_available = serializers.IntegerField(read_only = True)
