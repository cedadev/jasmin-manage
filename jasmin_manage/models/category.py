from django.db import models

from .resource import Resource


class CategoryManager(models.Manager):
    """
    Manager for the category model.
    """
    def get_by_natural_key(self, name):
        return self.get(name = name)


class Category(models.Model):
    """
    Represents an available category of service.

    A category defines a collection of related resources, e.g. Group Workspace, Cloud Tenancy.
    """
    class Meta:
        ordering = ('name', )
        verbose_name_plural = 'categories'

    objects = CategoryManager()

    name = models.CharField(max_length = 250, unique = True)
    resources = models.ManyToManyField(
        Resource,
        related_name = 'categories',
        related_query_name = 'category'
    )

    def natural_key(self):
        return (self.name, )

    def __str__(self):
        return self.name
