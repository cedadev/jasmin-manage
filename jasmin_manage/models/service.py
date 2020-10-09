from django.db import models
from django.core import validators

from concurrency.fields import IntegerVersionField

from .category import Category
from .project import Project


class ServiceManager(models.Manager):
    """
    Manager for the service model.
    """
    def get_by_natural_key(self, category_name, name):
        return self.get(category__name = category_name, name = name)


class Service(models.Model):
    """
    Represents a service requested by a project.
    """
    class Meta:
        # Services in the same project can have the same name if they are in different categories
        # But service names must be unique within a category
        unique_together = ('category', 'name')

    objects = ServiceManager()

    category = models.ForeignKey(
        Category,
        models.CASCADE,
        related_name = 'services',
        related_query_name = 'service'
    )
    project = models.ForeignKey(
        Project,
        models.CASCADE,
        related_name = 'services',
        related_query_name = 'service'
    )
    name = models.CharField(
        max_length = 50,
        validators = (
            validators.RegexValidator(
                validators.slug_re,
                'Service name can only contain letters, numbers, underscores and hyphens.',
                'invalid'
            ),
        )
    )
    # Version field for optimistic concurrency
    version = IntegerVersionField()

    def get_event_aggregates(self):
        # Aggregate service events over the category and project
        return self.category, self.project

    def natural_key(self):
        return self.category.name, self.name
    natural_key.dependencies = (Category._meta.label_lower, )

    def __str__(self):
        return "{} / {}".format(self.category, self.name)
