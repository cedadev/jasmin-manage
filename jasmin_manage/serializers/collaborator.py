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
        read_only_fields = ('project', 'version')
        create_only_fields = ('user', )

    role = EnumField(Collaborator.Role)

    def validate(self, data):
        # Update the validated data with the project from the context if present
        project = self.context.get('project')
        if project:
            data.update(project = project)
        return super().validate(data)

    def create(self, validated_data):
        # Inject the project from the context when creating
        validated_data.update(project = self.context['project'])
        return super().create(validated_data)
