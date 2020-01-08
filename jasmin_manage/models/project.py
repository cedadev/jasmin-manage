from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

from markupfield.fields import MarkupField

from .consortium import Consortium


class ProjectManager(models.Manager):
    """
    Manager for the project model.
    """
    def get_by_natural_key(self, consortium_name, name):
        return self.get(consortium__name = consortium_name, name = name)


class Project(models.Model):
    """
    Represents a project within a consortium.
    """
    class Meta:
        ordering = ('name', )
        unique_together = ('consortium', 'name')

    # The statuses are ordered, as they represent a progression
    # So use an integer enum to represent them
    class Status(models.IntegerChoices):
        EDITABLE = 10
        UNDER_REVIEW = 20
        COMPLETED = 30

    objects = ProjectManager()

    consortium = models.ForeignKey(
        Consortium,
        models.CASCADE,
        related_name = 'projects',
        related_query_name = 'project'
    )
    name = models.CharField(max_length = 250)
    description = MarkupField(default_markup_type = 'markdown', escape_html = True)
    status = models.PositiveSmallIntegerField(choices = Status.choices, default = Status.EDITABLE)
    # Prevent a user being deleted if they are a project owner
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT)
    created_at = models.DateTimeField(auto_now_add = True)

    def get_event_aggregates(self):
        # Aggregate project events over the consortium
        return (self.consortium, )

    def get_event_type(self, diff):
        # If the status is in the diff, use it as the event type, otherwise use the default
        if 'status' in diff:
            return '{}.{}'.format(self._meta.label_lower, self.Status(self.status).name.lower())

    def natural_key(self):
        return self.consortium.name, self.name
    natural_key.dependencies = (Consortium._meta.label_lower, )

    def __str__(self):
        return "{} / {}".format(self.consortium.name, self.name)

    def clean(self):
        # For a project to be in the COMPLETED status, all the requirements must be decommisioned
        if self.status == self.Status.COMPLETED:
            from .requirement import Requirement
            requirements = (Requirement.objects
                .filter(service__project = self)
                .exclude(status = Requirement.Status.DECOMMISSIONED)
            )
            if requirements.exists():
                raise ValidationError(
                    'A project cannot be completed until all requirements are decommissioned.'
                )
