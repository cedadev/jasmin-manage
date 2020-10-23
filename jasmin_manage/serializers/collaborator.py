from rest_framework import serializers

from ..models import Collaborator

from .base import BaseSerializer, EnumField


class CollaboratorSerializer(BaseSerializer):
    """
    Serializer for the collaborator model.
    """
    class Meta:
        model = Collaborator
        fields = '__all__'

    role = EnumField(Collaborator.Role)
