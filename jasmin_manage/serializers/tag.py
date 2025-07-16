import re
from rest_framework import serializers

from ..models import Tag

from .base import BaseSerializer


class TagSerializer(BaseSerializer):
    """
    Serializer for the tag model.
    """

    class Meta:
        model = Tag
        fields = "__all__"
    
    def validate_name(self, value):
        """
        Validate the tag name according to business rules.
        """
        print(f"TagSerializer.validate_name() called with value: '{value}'")
        if value is not None:
            # Check if tag contains only lowercase letters, numbers, and hyphens
            if not re.match(r'^[a-z0-9-]+$', value):
                raise serializers.ValidationError(
                    'Tag name must contain only lowercase letters, numbers, and hyphens'
                )
            
            # Check minimum and maximum length
            if len(value) < 3:
                raise serializers.ValidationError(
                    'Tag name must be at least 3 characters long'
                )
            
            if len(value) > 15:
                raise serializers.ValidationError(
                    'Tag name must be at most 15 characters long'
                )
            
            # Check that tag doesn't start or end with hyphen
            if value.startswith('-') or value.endswith('-'):
                raise serializers.ValidationError(
                    'Tag name cannot start or end with a hyphen'
                )
        
        print(f"TagSerializer.validate_name() passed validation for: '{value}'")
        return value
