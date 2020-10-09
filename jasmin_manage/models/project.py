from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import html

from markupfield.fields import MarkupField

from concurrency.fields import IntegerVersionField

from .consortium import Consortium


class ProjectManager(models.Manager):
    """
    Manager for the project model.
    """
    def get_by_natural_key(self, name):
        return self.get(name = name)


class Project(models.Model):
    """
    Represents a project within a consortium.
    """
    class Meta:
        ordering = ('name', )

    # The statuses are ordered, as they represent a progression
    # So use an integer enum to represent them
    class Status(models.IntegerChoices):
        EDITABLE = 10
        UNDER_REVIEW = 20
        COMPLETED = 30

    objects = ProjectManager()

    name = models.CharField(max_length = 250, unique = True)
    description = MarkupField(default_markup_type = 'markdown', escape_html = True)
    status = models.PositiveSmallIntegerField(choices = Status.choices, default = Status.EDITABLE)
    # Projects can optionally have a default consortium that will be applied to new requirements
    default_consortium = models.ForeignKey(
        Consortium,
        models.CASCADE,
        null = True,
        blank = True,
        related_name = '+',
        help_text = html.format_html(
            '{}<br />{}',
            'Default consortium for requirements in the project, if known.',
            'Can be overridden on a per-requirement basis.'
        )
    )
    # The number of the next requirement for this project
    # Maintaining this field on the project (vs using MAX of the existing requirement numbers)
    # allows us to have monotonically increasing requirement numbers even when requirements
    # are deleted
    next_requirement_number = models.PositiveIntegerField(default = 1, editable = False)
    # Version field for optimistic concurrency
    version = IntegerVersionField()
    # Prevent a user being deleted if they are a project owner
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT)
    created_at = models.DateTimeField(auto_now_add = True)

    def get_event_type(self, diff):
        # If the status is in the diff, use it as the event type, otherwise use the default
        if 'status' in diff:
            return '{}.{}'.format(self._meta.label_lower, self.Status(self.status).name.lower())

    def natural_key(self):
        return (self.name, )

    def __str__(self):
        return self.name

    def clean(self):
        # For a project to be in the COMPLETED status, all the requirements must be decommisioned
        if self.status == self.Status.COMPLETED:
            from .requirement import Requirement
            requirements = (Requirement.objects
                .filter(service__project = self)
                .exclude(status__gte = Requirement.Status.DECOMMISSIONED)
            )
            if requirements.exists():
                raise ValidationError(
                    'A project cannot be completed until all requirements are decommissioned.'
                )
