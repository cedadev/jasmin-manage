from typing import Any
from django.db import models


class TagManager(models.Manager):
    """
    Manager for the resource model.
    """

    def get_by_natural_key(self, name):
        return self.get(name=name)


class TagField(models.SlugField):
    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return value if value is None else value.lower()


class Tag(models.Model):
    name = TagField(max_length=255, null=True, unique=True)
    help_text = "Lowercase letters, numbers, underscores or hypens only please."

    def natural_key(self):
        return (self.name,)

    def __str__(self):
        return self.name
