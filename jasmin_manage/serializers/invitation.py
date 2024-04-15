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
        exclude = ("code",)
        read_only_fields = ("project",)
        create_only_fields = ("email",)

    def validate(self, data):
        validated_data = super().validate(data)
        # We do not allow updating of invitations via the API
        # So this serializer doesn't need to deal with updates
        # So we just let this be a key error on updates
        instance_data = dict(project=self.context["project"])
        # Update with the data from the serializer
        instance_data.update(validated_data)
        # Run the model validation
        instance = Invitation(**instance_data)
        instance.clean()
        return validated_data

    def create(self, validated_data):
        # Inject the project from the context into the model
        validated_data.update(project=self.context["project"])
        return super().create(validated_data)
