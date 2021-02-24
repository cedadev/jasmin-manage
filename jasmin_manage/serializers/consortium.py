from django.contrib.auth import get_user_model

from rest_framework import serializers

from ..models import Consortium

from .base import BaseSerializer


class ManagerSerializer(serializers.ModelSerializer):
    """
    Serializer for the manager of a consortium.
    """
    class Meta:
        model = get_user_model()
        fields = ('id', 'username', 'first_name', 'last_name')


class ConsortiumSerializer(BaseSerializer):
    """
    Serializer for the consortium model.
    """
    class Meta:
        model = Consortium
        fields = '__all__'

    # Use a nested representation for the manager, as it is the only place information is exposed
    manager = ManagerSerializer(read_only = True)
