from ..models import Service

from .base import BaseSerializer


class ServiceSerializer(BaseSerializer):
    """
    Serializer for the service model.
    """
    class Meta:
        model = Service
        fields = '__all__'
        read_only_fields = ('project', )
        create_only_fields = ('category', 'name')

    def create(self, validated_data):
        # Inject the project from the context into the model
        validated_data.update(project = self.context['project'])
        return super().create(validated_data)
