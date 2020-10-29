from datetime import date

from dateutil.relativedelta import relativedelta

from django.db import models, transaction
from django.core.exceptions import ValidationError

from concurrency.fields import IntegerVersionField

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
    amount = models.PositiveIntegerField()
    # Default start date is today
    start_date = models.DateField(default = date.today)
    # Default end date is 5 years
    end_date = models.DateField(default = _five_years)
    created_at = models.DateTimeField(auto_now_add = True)
    # Version field for optimistic concurrency
    version = IntegerVersionField()

    def get_event_aggregates(self):
        # Aggregate requirement events over the service and resource
        return self.service, self.resource

    def get_event_type(self, diff):
        # If the status is in the diff, use it as the event type, otherwise use the default
        if 'status' in diff:
            return '{}.{}'.format(self._meta.label_lower, self.Status(self.status).name.lower())

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
        # The total provisioned for a resource/consortium combo cannot exceed the quota
        # Combined with the fact that the quotas cannot exceed the total available, this means
        # that the total provisioned for a resource cannot exceed the total available
        # if self.consortium_id:
        #     consortium = self.consortium
        # elif self.service_id:
        #     consortium = self.service.project.default_consortium
        # else:
        #     consortium = None
        # if consortium and \
        #    self.resource_id and \
        #    self.status == self.Status.PROVISIONED and \
        #    self.amount is not None:
        #     # Get the quota of the resource for the consortium, or 0 if there isn't one
        #     quota = self.resource.quotas.filter(consortium = consortium).first()
        #     quota_amount = getattr(quota, 'amount', 0)
        #     # Get the total provisioned for the consortium/resource
        #     provisioned = self.resource.requirements.filter(
        #         consortium = consortium,
        #         status = self.Status.PROVISIONED
        #     )
        #     # If the current requirement has already been saved, exclude it from the sum
        #     # We will add the current amount after, as it may have changed
        #     if not self._state.adding:
        #         provisioned = provisioned.exclude(pk = self.pk)
        #     # Sum the discovered amounts
        #     total_provisioned = provisioned.aggregate(total = models.Sum('amount'))['total'] or 0
        #     # Add on the current amount for this requirement
        #     total_provisioned = total_provisioned + self.amount
        #     # Check if it exceeds the quota
        #     if total_provisioned > quota_amount:
        #         errors.setdefault('amount', []).append(
        #             'Total provisioned ({}) cannot exceed consortium quota ({}).'.format(
        #                 self.resource.format_amount(total_provisioned),
        #                 self.resource.format_amount(quota_amount)
        #             )
        #         )
        if errors:
            raise ValidationError(errors)
