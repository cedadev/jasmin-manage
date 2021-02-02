from django.contrib.auth import get_user_model

from rest_framework import serializers

from ..models import Collaborator

from .base import BaseSerializer, EnumField, ContextDefault


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the user of a collaborator.
    """
    class Meta:
        model = get_user_model()
        fields = ('id', 'username', 'first_name', 'last_name')


class CollaboratorSerializer(BaseSerializer):
    """
    Serializer for the collaborator model.
    """
    class Meta:
        model = Collaborator
        fields = '__all__'
        read_only_fields = ('project', )

    # Use a nested representation for the user, as it is the only place information is exposed
    user = UserSerializer(read_only = True)
    # Use an enum field that emits the enum member names instead of values
    role = EnumField(Collaborator.Role)
