from django.contrib.auth import get_user_model

from rest_framework import serializers

from ..models import Comment

from .base import BaseSerializer, EnumField


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the user of a comment.
    """

    class Meta:
        model = get_user_model()
        fields = ("id", "username", "first_name", "last_name")


class CommentSerializer(BaseSerializer):
    """
    Serializer for the comment model.
    """

    class Meta:
        model = Comment
        fields = "__all__"
        read_only_fields = ("project", "created_at", "edited_at")

    # Use a nested representation for the user, as we don't provide a mechanism
    # for fetching user information in isolation
    user = UserSerializer(read_only=True)

    def create(self, validated_data):
        validated_data.update(
            # Inject the project from the context into the model
            project=self.context["project"],
            # Also inject the user from the request
            user=self.context["request"].user,
        )
        return super().create(validated_data)
