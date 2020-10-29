from ..models import Service

from .base import BaseSerializer


class ServiceSerializer(BaseSerializer):
    """
    Serializer for the service model.
    """
    class Meta:
        model = Service
        fields = '__all__'
        read_only_fields = ('project', 'version')
        create_only_fields = ('category', )

    def validate(self, data):
        # Update the validated data with the project if required
        project = self.context.get('project')
        if project:
            data.update(project = project)
        return super().validate(data)

    def create(self, validated_data):
        # Inject the project from the context when creating
        validated_data.update(project = self.context['project'])
        return super().create(validated_data)
