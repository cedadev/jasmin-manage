from rest_framework import serializers

from ..models import Collaborator

from .base import BaseSerializer, EnumField, ContextDefault


class CollaboratorSerializer(BaseSerializer):
    """
    Serializer for the collaborator model.
    """
    class Meta:
        model = Collaborator
        fields = '__all__'
        create_only_fields = ('user', )

    # This field is required to validate the unique_together constraint when project is read-only
    # See https://www.django-rest-framework.org/api-guide/serializers/#specifying-read-only-fields
    project = serializers.PrimaryKeyRelatedField(
        read_only = True,
        default = ContextDefault('project')
    )
    # Use an enum field that emits the enum member names instead of values
    role = EnumField(Collaborator.Role)

    def create(self, validated_data):
        # Inject the project from the context into the model
        validated_data.update(project = self.context['project'])
        return super().create(validated_data)
