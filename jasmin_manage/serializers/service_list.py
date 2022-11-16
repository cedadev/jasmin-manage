from ..models import Service

from .base import BaseSerializer

from .service import CategoryNameUniqueTogether


class ServiceListSerializer(BaseSerializer):
    """
    Serializer for service list using the service model.
    """
    class Meta:
        model = Service
        fields = '__all__'
        # Replace the default unique together validator for category and name
        # in order to customise the error message
        validators = [CategoryNameUniqueTogether()]
        read_only_fields = ('project', )
        create_only_fields = ('category', 'name')

    def create(self, validated_data):
        #Inject the project from the context into the model
        validated_data.update(project = self.context['project'])
        return super().create(validated_data)
