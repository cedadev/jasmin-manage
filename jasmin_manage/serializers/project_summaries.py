from rest_framework import serializers

from ..models import Collaborator, Project, Resource
from .base import BaseSerializer, EnumField


class ProjectSummarySerializer(BaseSerializer):
    """
    Serializer for the project model.
    """

    class Meta:
        model = Project
        fields = ["id", "name", "consortium", "tags", "resource_summary", "status"]
        create_only_fields = ("consortium",)

    status = EnumField(Project.Status, read_only=True)

    # Add fields for summary data
    resource_summary = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    consortium = serializers.SerializerMethodField()

    def create(self, validated_data):
        # Inject the user from the request as the owner when creating
        validated_data.update(owner=self.context["request"].user)
        return super().create(validated_data)

    def validate_consortium(self, consortium):
        user = self.context["request"].user
        if user.is_staff or consortium.is_public:
            # Allow the validation to proceed for staff users or public consortia
            return consortium
        else:
            # Non-staff users cannot use non-public consortia
            raise serializers.ValidationError(
                "You are not allowed to create projects in non-public consortia.",
                "non_public_consortium",
            )

    def get_tags(self, obj):
        """Convert the tags into the names."""
        tags = [t["name"] for t in obj.tags.values()]
        return tags

    def get_consortium(self, obj):
        """Convert the consortium into its name."""
        return obj.consortium.name

    def get_resource_summary(self, obj):
        """Create summary of all resources under the project"""
        services = obj.services.all()
        resqueryset = Resource.objects.all()
        tags = [t["name"] for t in obj.tags.values()]
        # We want total resouces for the project so init requirements dict here, not per service
        requirement_data = {res.name: 0 for res in resqueryset}
        for s in services:
            requirments = s.requirements.all()
            for r in requirments:
                if r.status == 50:  # This is the code for provisioned requirements
                    resource = r.resource.name
                    amount = r.amount
                    requirement_data[resource] += amount
        return requirement_data
