from django.db import models
from django.core.exceptions import ValidationError

from .resource import Resource


class ResourceChunkManager(models.Manager):
    """
    Manager for the resource chunk model.
    """
    def get_by_natural_key(self, resource_name, chunk_name):
        return self.get(resource__name = resource_name, name = chunk_name)


class ResourceChunk(models.Model):
    """
    Represents a chunk of a resource, i.e. from a particular procurement.
    """
    class Meta:
        ordering = ('resource__name', 'name')
        unique_together = ('resource', 'name')

    objects = ResourceChunkManager()

    resource = models.ForeignKey(
        Resource,
        models.CASCADE,
        related_name = 'chunks',
        related_query_name = 'chunk'
    )
    name = models.CharField(
        max_length = 250,
        help_text = 'The name of the resource chunk, e.g. QB1, QB2.'
    )
    amount = models.PositiveBigIntegerField(
        help_text = 'The amount of the resource that is in this chunk.'
    )

    def natural_key(self):
        return self.resource.name, self.name
    natural_key.dependencies = (Resource._meta.label_lower, )

    def get_event_aggregates(self):
        # Aggregate chunk events over the resource
        return (self.resource, )

    def __str__(self):
        return '{} / {}'.format(self.resource.name, self.name)
