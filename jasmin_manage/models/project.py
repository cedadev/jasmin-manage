from django.db import models
from django.core.exceptions import ValidationError

from concurrency.fields import IntegerVersionField

from .consortium import Consortium


class ProjectManager(models.Manager):
    """
    Manager for the project model.
    """
    def get_by_natural_key(self, name):
        return self.get(name = name)


class ProjectQuerySet(models.QuerySet):
    """
    Queryset for the project model.
    """
    def create(self, *, owner, **kwargs):
        # Import here to avoid circular dependencies
        from .collaborator import Collaborator
        project = super().create(**kwargs)
        # Make a collaborator object for the given owner
        Collaborator.objects.create(project = project, user = owner, role = Collaborator.Role.OWNER)
        return project


class Project(models.Model):
    """
    Represents a project within a consortium.
    """
    class Meta:
        ordering = ('name', )

    class Status(models.IntegerChoices):
        """
        Represents the status of a project.

        The statuses are ordered as they represent a progression.
        """
        EDITABLE = 10
        UNDER_REVIEW = 20
        COMPLETED = 30

    objects = ProjectManager.from_queryset(ProjectQuerySet)()

    name = models.CharField(max_length = 250, unique = True)
    description = models.TextField(help_text = "Can contain markdown syntax.")
    status = models.PositiveSmallIntegerField(choices = Status.choices, default = Status.EDITABLE)
    consortium = models.ForeignKey(
        Consortium,
        models.CASCADE,
        related_name = 'projects',
        related_query_name = 'project'
    )
    # The number of the next requirement for this project
    # Maintaining this field on the project (vs using MAX of the existing requirement numbers)
    # allows us to have monotonically increasing requirement numbers even when requirements
    # are deleted
    next_requirement_number = models.PositiveIntegerField(default = 1, editable = False)
    # Version field for optimistic concurrency
    version = IntegerVersionField()
    created_at = models.DateTimeField(auto_now_add = True)

    def get_event_type(self, diff):
        # If the status is in the diff, use it as the event type, otherwise use the default
        if 'status' in diff:
            return '{}.{}'.format(self._meta.label_lower, self.Status(self.status).name.lower())

    def get_event_aggregates(self):
        # Aggregate project events over the consortium
        return (self.consortium, )

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
