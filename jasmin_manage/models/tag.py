from typing import Any

from django.db import models


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

    # Enforce a length of 255, allow null values and make sure they are unique.
    name = TagField(max_length=255, null=True, unique=True)
    help_text = "Lowercase letters, numbers and hypens only please."

    # Indicates if the consortium is a public one
    is_public = models.BooleanField(default=False)

    def natural_key(self):
        return (self.name,)

    def __str__(self):
        return self.name
