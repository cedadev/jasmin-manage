from django.core import validators
from django.db import models

from .category import Category
from .project import Project
from .consortium import Consortium


class ServiceManager(models.Manager):
    """
    Manager for the service model.
    """

    def get_by_natural_key(self, category_name, name):
        return self.get(category__name=category_name, name=name)


class Service(models.Model):
    """
    Represents a service requested by a project.
    """

    class Meta:
        ordering = ("category__name", "name")
        # Services in the same project can have the same name if they are in different categories
        # But service names must be unique within a category
        unique_together = ("category", "name")

    objects = ServiceManager()

    category = models.ForeignKey(
        Category, models.CASCADE, related_name="services", related_query_name="service"
    )
    project = models.ForeignKey(
        Project, models.CASCADE, related_name="services", related_query_name="service"
    )

    name = models.CharField(
        # 20 characters is long enough for a service name
        max_length=30,
        # Index the field for faster searches
        db_index=True,
        # Use a regex to validate the field
        validators=[
            validators.RegexValidator(
                regex=r"^[a-z][-a-z0-9_]*\Z",
                message=(
                    "Service name must start with a letter and contain "
                    "lower-case letters, numbers, underscores and hyphens only."
                ),
            )
        ],
    )

    def get_event_aggregates(self):
        # Aggregate service events over the category and project
        return self.category, self.project

    def natural_key(self):
        return self.category.name, self.name

    def get_num_active_requirements(self):
        # Checks whether there are any active reqs. if so returns True, else False
        return self.requirements.filter(status=50).count()

    def get_parent_consortium(self):
        # Get the consortium of the parent project
        return self.project.consortium.id

    natural_key.dependencies = (Category._meta.label_lower,)

    def __str__(self):
        return "{} / {}".format(self.category, self.name)
