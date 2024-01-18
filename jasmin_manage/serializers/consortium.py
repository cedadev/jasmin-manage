from django.contrib.auth import get_user_model
from rest_framework import serializers

from ..models import Consortium, Project, Quota
from .base import BaseSerializer


class ManagerSerializer(serializers.ModelSerializer):
    """
    Serializer for the manager of a consortium.
    """

    class Meta:
        model = get_user_model()
        fields = ("id", "username", "first_name", "last_name")


class QuotaSerializer(serializers.ModelSerializer):
    """Serializer to show the provisioned resources for a consortium."""

    resource = serializers.StringRelatedField()

    class Meta:
        model = Quota
        fields = ["resource", "amount"]


class ConsortiumSummarySerializer(serializers.ModelSerializer):
    """Serializer for projects summary"""

    # Add fields for summary data
    num_projects = serializers.SerializerMethodField()
    # Use a nested representation for the manager, as it is the only place information is exposed
    manager = ManagerSerializer(read_only=True)
    resources = QuotaSerializer(source="quotas", read_only=True, many=True)
    project_summaries = serializers.SerializerMethodField()

    class Meta:
        model = Consortium
        fields = ["name", "num_projects", "manager", "resources", "project_summaries"]

    def get_num_projects(self, obj):
        return obj.get_num_projects()

    def get_project_summaries(self, obj):
        """Create a summary of the resource provision for the consortium and the projects under that consortium."""
        # Get projects from consortium object and loop through to build per project provioned information for resources
        projects = obj.projects.all()
        data = []
        collab_lookup = {20: "contributor", 40: "owner"}
        for p in projects:
            name = p.name
            services = p.services.all()
            service_data = []
            # We want total resouces for the project so init requirements dict here, not per service
            requirement_data = {}
            for s in services:
                requirments = s.requirements.all()
                for r in requirments:
                    if r.status == 50:  # This is the code for provisioned requirements
                        resource = r.resource.name
                        amount = r.amount
                        if resource in requirement_data:
                            requirement_data[resource] += amount
                        else:
                            requirement_data[resource] = amount

                service_data.append(requirement_data)
            # Get collaborator information to add to the summary
            collaborators = p.collaborators.all()
            collaborators_data = []
            for c in collaborators:
                # Removed email as not sure on the permissions scoping for access to the summaries
                user = c.user.get_username()
                full_name = c.user.get_full_name()
                role = collab_lookup[c.role]
                collaborators_data.append(
                    {"username": user, "name": full_name, "role": role}
                )

            project_data = {
                "project_name": name,
                "collaborators": collaborators_data,
                "resource_summary": service_data,
            }

            data.append(project_data)

        return data


class ConsortiumSerializer(BaseSerializer):
    """
    Serializer for the consortium model.
    """

    class Meta:
        model = Consortium
        fields = "__all__"

    # Use a nested representation for the manager, as it is the only place information is exposed
    manager = ManagerSerializer(read_only=True)

    # Add fields for summary data
    num_projects = serializers.SerializerMethodField()
    num_projects_current_user = serializers.SerializerMethodField()

    def get_num_projects(self, obj):
        return obj.get_num_projects()

    def get_num_projects_current_user(self, obj):
        return obj.get_num_projects_for_user(self.context["request"].user)
