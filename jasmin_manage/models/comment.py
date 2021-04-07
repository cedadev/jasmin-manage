from django.db import models
from django.conf import settings

from .project import Project


class Comment(models.Model):
    """
    Represents a comment on a project.
    """
    class Meta:
        ordering = ('project__name', '-created_at')

    project = models.ForeignKey(
        Project,
        models.CASCADE,
        related_name = 'comments',
        related_query_name = 'comment'
    )
    content = models.TextField(help_text = "Can contain markdown syntax.")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT)
    created_at = models.DateTimeField(auto_now_add = True)
    edited_at = models.DateTimeField(auto_now = True)

    def get_event_aggregates(self):
        # Aggregate comment events over the project and user
        return (self.project, self.user)
