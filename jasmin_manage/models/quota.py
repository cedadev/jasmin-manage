from itertools import chain

from django.db import models
from django.db.models import functions
from django.core.exceptions import ValidationError

from .consortium import Consortium
from .resource import Resource


class QuotaManager(models.Manager):
    """
    Manager for the quota model.
    """
    def get_by_natural_key(self, consortium_name, resource_name):
        return self.get(consortium__name = consortium_name, resource__name = resource_name)


class QuotaQuerySet(models.QuerySet):
    def annotate_usage(self, *statuses):
        """
        Returns the current queryset annotated with usage information from requirements
        that reference the resource.
        """
        from .requirement import Requirement
        # Generate the annotations for each possible status
        annotations = dict(chain.from_iterable(
            (
                ('{}_count'.format(status.name.lower()), models.Count(
                    'status',
                    filter = models.Q(status = status)
                )),
                ('{}_total'.format(status.name.lower()), models.Sum(
                    'amount',
                    filter = models.Q(status = status)
                ))
            )
            # If no statuses are given, use them all
            for status in (statuses or Requirement.Status)
        ))
        # This subquery fetches the count and total of all requirements for the quota
        requirements = (Requirement.objects
            .filter(
                service__project__consortium = models.OuterRef('consortium'),
                resource = models.OuterRef('resource')
            )
            .order_by()
            .values('service__project__consortium', 'resource')
            .annotate(**annotations)
        )
        # Apply the annotations to the current query
        return self.annotate(
            # Coalesce the corresponding annotation from the subquery
            **{
                annotation: functions.Coalesce(
                    models.Subquery(requirements.values(annotation)),
                    models.Value(0)
                )
                for annotation in annotations
            }
        )


class Quota(models.Model):
    """
    Represents a quota of a resource granted to a consortium.

    If no quota exists for a consortium/resource combination, it is assumed to be zero.
    """
    class Meta:
        ordering = ('consortium__name', 'resource__name')
        unique_together = ('consortium', 'resource')

    objects = QuotaManager.from_queryset(QuotaQuerySet)()

    consortium = models.ForeignKey(
        Consortium,
        models.CASCADE,
        related_name = 'quotas',
        related_query_name = 'quota'
    )
    resource = models.ForeignKey(
        Resource,
        models.CASCADE,
        related_name = 'quotas',
        related_query_name = 'quota'
    )
    amount = models.PositiveIntegerField()

    def get_event_aggregates(self):
        return self.consortium, self.resource

    def natural_key(self):
        return self.consortium.name, self.resource.name
    natural_key.dependencies = (Consortium._meta.label_lower, Resource._meta.label_lower)
