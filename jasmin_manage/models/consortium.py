from django.db import models
from django.conf import settings


class ConsortiumManager(models.Manager):
    """
    Manager for the consortium model.
    """
    def get_by_natural_key(self, name):
        return self.get(name = name)


class ConsortiumQuerySet(models.QuerySet):
    """
    Queryset for the consortium model.
    """
    def annotate_summary(self):
        """
        Annotates the query with summary information for each consortium.
        """
        # Just add the number of projects for now
        return self.annotate(
            num_projects = models.Count('project', distinct = True)
        )


class Consortium(models.Model):
    """
    Represents a consortium.

    A consortium represents a science area to which projects belong. They are allocated
    resources to be distributed by a consortium manager.
    """
    class Meta:
        ordering = ('name', )
        verbose_name_plural = 'consortia'

    objects = ConsortiumManager.from_queryset(ConsortiumQuerySet)()

    name = models.CharField(max_length = 250, unique = True)
    description = models.TextField()
    # Indicates if the consortium is a public one
    is_public = models.BooleanField(default = False)
    # Prevent a user being deleted if they are a consortium manager
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT)

    def get_num_projects(self):
        if hasattr(self, 'num_projects'):
            # Use the value from the object if present (e.g. from an annotation)
            return self.num_projects
        else:
            # Otherwise calculate it on the fly
            return self.projects.count()

    def natural_key(self):
        return (self.name, )

    def __str__(self):
        return self.name
