from django.contrib.auth import get_user_model
from django.forms import model_to_dict

from rest_framework import serializers

from ..models import Invitation

from .base import BaseSerializer, EnumField


class InvitationSerializer(BaseSerializer):
    """
    Serializer for the invitation model.
    """
    class Meta:
        model = Invitation
        exclude = ('code', )
        read_only_fields = ('project', )
        create_only_fields = ('email', )

    def validate(self, data):
        validated_data = super().validate(data)
        # Use the validated data to instantiate a model instance
        # If there is an instance, use the data from it as a starting point
        if self.instance:
            instance_data = model_to_dict(self.instance)
        else:
            # On create, use the project from the context
            instance_data = dict(project = self.context['project'])
        # Overwrite with the data from the serializer
        instance_data.update(validated_data)
        # Run the model validation
        instance = Invitation(**instance_data)
        instance.clean()
        return validated_data

    def create(self, validated_data):
        # Inject the project from the context into the model
        validated_data.update(project = self.context['project'])
        return super().create(validated_data)
