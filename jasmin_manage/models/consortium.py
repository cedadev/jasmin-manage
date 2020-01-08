from django.db import models
from django.conf import settings

from markupfield.fields import MarkupField


class ConsortiumManager(models.Manager):
    """
    Manager for the consortium model.
    """
    def get_by_natural_key(self, name):
        return self.get(name = name)


class Consortium(models.Model):
    """
    Represents a consortium.

    A consortium represents a science area to which projects belong. They are allocated
    resources to be distributed by a consortium manager.
    """
    class Meta:
        ordering = ('name', )
        verbose_name_plural = 'consortia'

    objects = ConsortiumManager()

    name = models.CharField(max_length = 250, unique = True)
    description = MarkupField(default_markup_type = 'markdown', escape_html = True)
    # Prevent a user being deleted if they are a consortium manager
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT)

    def natural_key(self):
        return (self.name, )

    def __str__(self):
        return self.name
