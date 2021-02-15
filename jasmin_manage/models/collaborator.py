from django.db import models
from django.conf import settings

from .project import Project


class Collaborator(models.Model):
    """
    Represents a collaborator on a project.
    """
    class Meta:
        ordering = ('project__name', 'role', 'user__username')
        unique_together = ('project', 'user')

    class Role(models.IntegerChoices):
        """
        Represents the possible roles that a collaborator can have.
        """
        #: A contributor is permitted to create requirements
        CONTRIBUTOR = 20
        #: An owner can add new contributors and submit the project for review
        OWNER = 40

    project = models.ForeignKey(
        Project,
        models.CASCADE,
        related_name = 'collaborators',
        related_query_name = 'collaborator'
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT)
    role = models.PositiveSmallIntegerField(choices = Role.choices, default = Role.CONTRIBUTOR)
    created_at = models.DateTimeField(auto_now_add = True)

    def get_event_aggregates(self):
        # Aggregate collaborator events over the project and user
        return (self.project, self.user)

    def __str__(self):
        return "{} / {} / {}".format(
            self.project,
            self.user,
            self.Role(self.role).name
        )
