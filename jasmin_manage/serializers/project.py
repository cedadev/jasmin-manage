from django.db import models

from rest_framework import serializers

from ..models import Collaborator, Project

from .base import BaseSerializer, EnumField


class ProjectSerializer(BaseSerializer):
    """
    Serializer for the project model.
    """
    class Meta:
        model = Project
        fields = '__all__'
        create_only_fields = ('consortium', )

    status = EnumField(Project.Status, read_only = True)

    # Add fields for summary data
    num_services = serializers.SerializerMethodField()
    num_requirements = serializers.SerializerMethodField()
    num_collaborators = serializers.SerializerMethodField()
    current_user_role = serializers.SerializerMethodField()

    def create(self, validated_data):
        # Inject the user from the request as the owner when creating
        validated_data.update(owner = self.context['request'].user)
        return super().create(validated_data)

    def get_num_services(self, obj):
        return obj.get_num_services()

    def get_num_requirements(self, obj):
        return obj.get_num_requirements()

    def get_num_collaborators(self, obj):
        return obj.get_num_collaborators()

    def get_current_user_role(self, obj):
        role = obj.get_current_user_role(self.context['request'].user)
        if role:
            return Collaborator.Role(role).name
        else:
            return None
