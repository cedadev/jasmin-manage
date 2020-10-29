from rest_framework import serializers

from ..models import Project

from .base import BaseSerializer, EnumField


class ProjectSerializer(BaseSerializer):
    """
    Serializer for the project model.
    """
    class Meta:
        model = Project
        exclude = ('next_requirement_number', )
        read_only_fields = ('status', 'version')
        create_only_fields = ('consortium', )

    status = EnumField(Project.Status)

    def create(self, validated_data):
        # Inject the user from the request as the owner when creating
        validated_data.update(owner = self.context['request'].user)
        return super().create(validated_data)
