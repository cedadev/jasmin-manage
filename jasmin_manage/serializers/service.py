from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueTogetherValidator
from rest_framework import serializers

from ..models import Service, Requirement, Resource

from .base import BaseSerializer


class CategoryNameUniqueTogether(UniqueTogetherValidator):
    """
    Custom validator that raises the unique together constraint against the name field.
    """

    def __init__(self):
        super().__init__(queryset=Service.objects.all(), fields=("category", "name"))

    def __call__(self, attrs, serializer):
        try:
            super().__call__(attrs, serializer)
        except ValidationError:
            # Raise the error against the name field, and with a nicer message
            category = attrs["category"]
            raise ValidationError(
                dict(name="{} with this name already exists.".format(category.name)),
                code="unique",
            )


class ServiceRequirementResourceSerializer(BaseSerializer):
    """
    Serializer for resource for the requirements of service.
    """

    class Meta:
        model = Resource
        fields = ["id", "name", "short_name", "description", "units"]


class ServiceRequirementSerializer(BaseSerializer):
    """
    Serializer for requirements of a service.
    """

    resource = ServiceRequirementResourceSerializer()

    class Meta:
        model = Requirement
        fields = [
            "id",
            "status",
            "amount",
            "start_date",
            "end_date",
            "created_at",
            "location",
            "service",
            "resource",
        ]


class ServiceSerializer(BaseSerializer):
    """
    Serializer for the service model.
    """

    class Meta:
        model = Service
        fields = "__all__"
        # Replace the default unique_together validator for category and name
        # in order to customise the error message
        validators = [CategoryNameUniqueTogether()]
        read_only_fields = ("project",)
        create_only_fields = ("category", "name")

    def create(self, validated_data):
        # Inject the project from the context into the model
        validated_data.update(project=self.context["project"])
        return super().create(validated_data)


class ServiceListSerializer(BaseSerializer):
    """
    Serializer for the service model.
    """

    requirements = ServiceRequirementSerializer(many=True)
    # Add fields for summary data
    is_active_requirements = serializers.SerializerMethodField()
    consortium = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            "id",
            "name",
            "category",
            "project",
            "consortium",
            "is_active_requirements",
            "requirements",
            "_links",
        ]
        # Replace the default unique_together validator for category and name
        # in order to customise the error message
        validators = [CategoryNameUniqueTogether()]
        read_only_fields = ("project",)
        create_only_fields = ("category", "name")

    def create(self, validated_data):
        # Inject the project from the context into the model
        validated_data.update(project=self.context["project"])
        return super().create(validated_data)

    def get_is_active_requirements(self, obj):
        # Works out if there are any active requirements in the service
        return True if obj.get_num_active_requirements() else False

    def get_consortium(self, obj):
        # Get the parent project's consortium
        return obj.get_parent_consortium()
