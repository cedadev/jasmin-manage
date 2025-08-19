from typing import Any
import re

from django.db import models
from django.core.exceptions import ValidationError


class TagManager(models.Manager):
    """
    Manager for the tag model.
    """

    def get_by_natural_key(self, name):
        return self.get(name=name)


class TagField(models.SlugField):
    """
    Type of field to create tags and enforce lowercase.
    """

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return value if value is None else value.lower()


class Tag(models.Model):
    """
    Represents a tag for a project.
    """

    class Meta:
        ordering = ("name",)

    objects = TagManager()

    # Enforce a length of 255, allow null values and make sure they are unique.
    name = TagField(max_length=15, null=True, unique=True)
    help_text = "Lowercase letters, numbers and hyphens only please."

    def clean(self):
        """
        Validate the tag name according to rules.
        """
        print(f"Tag.clean() called with name: '{self.name}'")
        super().clean()
        
        if self.name is not None:
            # Check if tag contains only lowercase letters, numbers, and hyphens
            if not re.match(r'^[a-z0-9-]+$', self.name):
                raise ValidationError({
                    'name': 'Tag name must contain only lowercase letters, numbers, and hyphens'
                })
            
            # Check minimum and maximum length
            if len(self.name) < 3:
                raise ValidationError({
                    'name': 'Tag name must be at least 3 characters long'
                })
            
            if len(self.name) > 15:
                raise ValidationError({
                    'name': 'Tag name must be at most 15 characters long'
                })
            
            # Check that tag doesn't start or end with hyphen
            if self.name.startswith('-') or self.name.endswith('-'):
                raise ValidationError({
                    'name': 'Tag name cannot start or end with a hyphen'
                })
        
        print(f" Tag.clean() passed validation for: '{self.name}'")

    def save(self, *args, **kwargs):
        """
        Override save to call full_clean before saving.
        """
        print(f"Tag.save() called for: '{self.name}'")
        self.full_clean()
        print(f"Tag.full_clean() completed for: '{self.name}'")
        super().save(*args, **kwargs)
        print(f"Tag.save() completed for: '{self.name}'")

    def natural_key(self):
        return (self.name,)

    def __str__(self):
        return self.name
