from datetime import date

from dateutil.relativedelta import relativedelta

from django.db import models, transaction
from django.core.exceptions import ValidationError

from .project import Project
from .resource import Resource
from .service import Service


def _five_years():
    return date.today() + relativedelta(years = 5)


class Requirement(models.Model):
    """
    Represents an amount of resource required by a project.

    The resource must be one that is allowed for the service via the category.
    """
    class Meta:
        ordering = ('-created_at', )

    # The statuses are ordered, as they represent a progression
    # So use integers for them as it allows some queries to be more efficient
    class Status(models.IntegerChoices):
        REQUESTED = 10
        REJECTED = 20
        APPROVED = 30
        AWAITING_PROVISIONING = 40
        PROVISIONED = 50
        DECOMMISSIONED = 60

    service = models.ForeignKey(
        Service,
        models.CASCADE,
        related_name = 'requirements',
        related_query_name = 'requirement'
    )
    resource = models.ForeignKey(
        Resource,
        models.CASCADE,
        related_name = 'requirements',
        related_query_name = 'requirement'
    )
    status = models.PositiveSmallIntegerField(choices = Status.choices, default = Status.REQUESTED)
    amount = models.PositiveBigIntegerField()
    # Default start date is today
    start_date = models.DateField(default = date.today)
    # Default end date is 5 years
    end_date = models.DateField(default = _five_years)
    created_at = models.DateTimeField(auto_now_add = True)
    location = models.CharField(max_length=100, default='TBC')

    def get_event_aggregates(self):
        # Aggregate requirement events over the service and resource
        return self.service, self.resource

    def get_event_type(self, diff):
        # If the status is in the diff, use it as the event type, otherwise use the default
        if 'status' in diff:
            return '{}.{}'.format(self._meta.label_lower, self.Status(diff['status']).name.lower())

    def clean(self):
        errors = dict()
        # Make sure that the selected resource is compatible with the category of the selected service
        if self.service_id and self.resource_id:
            # For new requirements, the selected resource must belong to the category of the service
            # For existing requirements, it is also allowed to be the current resource
            allowed_resources = self.service.category.resources.all()
            if not self._state.adding:
                allowed_resources = allowed_resources | Resource.objects.filter(requirement = self)
            if not allowed_resources.filter(pk = self.resource.pk).exists():
                errors.setdefault('resource', []).append('Resource is not valid for the selected service.')
        # Make sure that the end date is always later than the start date
        if self.end_date <= self.start_date:
            errors.setdefault('end_date', []).append('End date must be after start date.')
        if errors:
            raise ValidationError(errors)
