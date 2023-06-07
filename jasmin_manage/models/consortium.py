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
    def filter_visible(self, user):
        """
        Filters the query to only those consortia that should be visible to the given user.
        """
        if user:
            if not user.is_staff:
                # For non-staff users we need to apply a filter
                # We include consortia if:
                #   * The consortium is public OR
                #   * The user is the manager of the consortium OR
                #   * The user belongs to a project in the consortium
                return self.filter(
                    models.Q(is_public = True) |
                    models.Q(manager = user) |
                    models.Q(project__collaborator__user = user)
                )
        # Staff users and apps authenticating with a token can see everything
        return self

    def annotate_summary(self, user = None):
        """
        Annotates the query with summary information for each consortium.

        If a user is given, it will also annotate with information about the user's
        projects in the consortium.
        """
        # Annotate with the total number of projects
        queryset = self.annotate(
            num_projects = models.Count('project', distinct = True)
        )
        # Annotate with the number of projects that the user has in the consortium, if given
        if user:
            queryset = queryset.annotate(
                num_projects_for_user = models.Count(
                    'project',
                    distinct = True,
                    filter = models.Q(project__collaborator__user = user)
                )
            )
        return queryset


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

    def get_num_projects_for_user(self, user):
        if hasattr(self, 'num_projects_for_user'):
            # Use the value from the object if present (e.g. from an annotation)
            return self.num_projects_for_user
        else:
            # Otherwise calculate it on the fly
            return self.projects.filter(collaborator__user = user).count()

    def natural_key(self):
        return (self.name, )

    def __str__(self):
        return self.name
