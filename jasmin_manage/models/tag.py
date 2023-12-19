from django.db import models


class TagManager(models.Manager):
    """
    Manager for the resource model.
    """

    def get_by_natural_key(self, name):
        return self.get(name=name)


class Tag(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)

    def natural_key(self):
        return (self.name,)
