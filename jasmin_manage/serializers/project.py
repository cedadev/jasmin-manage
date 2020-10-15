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

    status = EnumField(Project.Status)
