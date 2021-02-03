from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueTogetherValidator

from ..models import Service

from .base import BaseSerializer


class CategoryNameUniqueTogether(UniqueTogetherValidator):
    """
    Custom validator that raises the unique together constraint against the name field.
    """
    def __init__(self):
        super().__init__(queryset = Service.objects.all(), fields = ('category', 'name'))

    def __call__(self, attrs, serializer):
        try:
            super().__call__(attrs, serializer)
        except ValidationError:
            # Raise the error against the name field, and with a nicer message
            category = attrs['category']
            raise ValidationError(
                dict(name = "{} with this name already exists.".format(category.name)),
                code = 'unique'
            )


class ServiceSerializer(BaseSerializer):
    """
    Serializer for the service model.
    """
    class Meta:
        model = Service
        fields = '__all__'
        # Replace the default unique_together validator for category and name
        # in order to customise the error message
        validators = [CategoryNameUniqueTogether()]
        read_only_fields = ('project', )
        create_only_fields = ('category', 'name')

    def create(self, validated_data):
        # Inject the project from the context into the model
        validated_data.update(project = self.context['project'])
        return super().create(validated_data)
