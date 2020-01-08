from datetime import date

from dateutil.relativedelta import relativedelta

from django.db import models
from django.core.exceptions import ValidationError

from .service import Service
from .resource import Resource
from .project import Project


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
    amount = models.PositiveIntegerField()
    # Default start date is today
    start_date = models.DateField(default = date.today)
    # Default end date is 5 years
    end_date = models.DateField(default = _five_years)
    created_at = models.DateTimeField(auto_now_add = True)

    def get_event_aggregates(self):
        # Aggregate requirement events over the service and resource
        return self.service, self.resource

    def get_event_type(self, diff):
        # If the status is in the diff, use it as the event type, otherwise use the default
        if 'status' in diff:
            return '{}.{}'.format(self._meta.label_lower, self.Status(self.status).name.lower())

    def clean(self):
        # Edits cannot be made to requirements in completed projects
        # This is combined with a check in Project.clean that ensures all requirements
        # are decommisioned before a project can be closed
        if self.service and self.service.project.status == Project.Status.COMPLETED:
            raise ValidationError('Cannot modify the requirements of a completed project.')
        if self.service and self.resource:
            # For new requirements, the selected resource must belong to the category of the service
            # For existing requirements, it is also allowed to be the current resource
            allowed_resources = self.service.category.resources.all()
            if not self._state.adding:
                allowed_resources = (
                    allowed_resources |
                    Resource.objects.filter(requirement = self)
                )
            if not allowed_resources.filter(pk = self.resource.pk).exists():
                raise ValidationError({
                    'resource': 'Resource is not valid for the selected service.'
                })
            # The total provisioned for a resource/consortium combo cannot exceed the quota
            # Combined with the fact that the quotas cannot exceed the total available, this means
            # that the total provisioned for a resource cannot exceed the total available
            if self.status == self.Status.PROVISIONED and self.amount is not None:
                quota = self.service.project.consortium.quotas.filter(resource = self.resource).first()
                quota_amount = getattr(quota, 'amount', 0)
                # Get the total provisioned for the consortium/resource
                provisioned = self.resource.requirements.filter(
                    service__project__consortium = self.service.project.consortium,
                    status = self.Status.PROVISIONED
                )
                if not self._state.adding:
                    provisioned = provisioned.exclude(pk = self.pk)
                total_provisioned = provisioned.aggregate(total = models.Sum('amount'))['total'] or 0
                # Add on the current amount for this requirement
                total_provisioned = total_provisioned + self.amount
                if total_provisioned > quota_amount:
                    raise ValidationError({
                        'amount': 'Total provisioned ({}) cannot exceed consortium quota ({}).'.format(
                            self.resource.format_amount(total_provisioned),
                            self.resource.format_amount(quota_amount)
                        )
                    })
