from itertools import chain

from django.db import models
from django.db.models import functions
from django.utils import html
from django.core.exceptions import ValidationError


class ResourceManager(models.Manager):
    """
    Manager for the resource model.
    """
    def get_by_natural_key(self, name):
        return self.get(name = name)


class ResourceQuerySet(models.QuerySet):
    def annotate_usage(self):
        """
        Returns the current queryset annotated with usage information from
        quotas and requirements that reference the resource.
        """
        # This subquery returns the count and total of all quotas for the outer resource
        from .quota import Quota
        quotas = (Quota.objects
            .filter(resource = models.OuterRef('pk'))
            .order_by()
            .values('resource')
            .annotate(count = models.Count('*'), total = models.Sum('amount'))
        )
        # This subquery fetches the count and total of all requirements for the current resource for each status
        from .requirement import Requirement
        #   Generate the annotations for each possible status
        subquery_annotations = dict(chain.from_iterable(
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
            for status in Requirement.Status
        ))
        requirements = (Requirement.objects
            .filter(resource = models.OuterRef('pk'))
            .order_by()
            .values('resource')
            .annotate(**subquery_annotations)
        )
        # Apply the annotations to the current query
        return self.annotate(
            quota_count = functions.Coalesce(
                models.Subquery(quotas.values('count')),
                models.Value(0)
            ),
            quota_total = functions.Coalesce(
                models.Subquery(quotas.values('total')),
                models.Value(0)
            ),
            # Coalesce the corresponding annotation from the subquery
            **{
                annotation: functions.Coalesce(
                    models.Subquery(requirements.values(annotation)),
                    models.Value(0)
                )
                for annotation in subquery_annotations
            }
        )


class Resource(models.Model):
    """
    Represents an available resource, e.g. cloud CPUs, Quobyte disk, tape.
    """
    class Meta:
        ordering = ('name', )

    objects = ResourceManager.from_queryset(ResourceQuerySet)()

    name = models.CharField(
        max_length = 250,
        unique = True,
        help_text = 'Full resource name, used when the resource is referenced '
                    'standalone, e.g. "Cloud Disk", "Panasas Disk".'
    )
    # The short name is optional, and is used in the context of a category/service
    short_name = models.CharField(
        max_length = 50,
        blank = True,
        help_text = html.format_html(
            '{}<br />{}',
            'Short resource name, used when the resource is referenced in the context '
            'of a category or service, e.g. "Disk".',
            'If not given, the full name is used in all contexts.'
        )
    )
    # Units can be empty for a unitless resource, e.g. CPUs.
    units = models.CharField(
        max_length = 10,
        null = True,
        blank = True,
        help_text = html.format_html(
            '{}<br />{}',
            'Canonical units for the resource.',
            'Leave blank for a unit-less resource, e.g. CPUs.'
        )
    )
    total_available = models.PositiveIntegerField(
        help_text = 'The total amount of the resource that is available.'
    )

    def format_amount(self, amount):
        """
        Returns the amount formatted with the resource's units.
        """
        if self.units:
            return "{} {}".format(amount, self.units)
        else:
            return str(amount)

    def natural_key(self):
        return (self.name, )

    def __str__(self):
        if self.units:
            return '{} ({})'.format(self.name, self.units)
        else:
            return self.name

    def clean(self):
        # The total available must be >= the sum of the quotas
        if not self._state.adding and self.total_available is not None:
            total_quotas = self.quotas.aggregate(total = models.Sum('amount'))['total'] or 0
            if self.total_available < total_quotas:
                raise ValidationError({
                    'total_available': 'Total available cannot be less than total quotas.'
                })
