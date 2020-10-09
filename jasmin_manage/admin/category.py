from django.contrib import admin
from django.template.defaultfilters import pluralize

from concurrency.admin import ConcurrentModelAdmin

from ..models import Category, Service
from .util import changelist_link


@admin.register(Category)
class CategoryAdmin(ConcurrentModelAdmin):
    list_display = ('name', 'num_resources', 'num_services')
    search_fields = ('name', )
    filter_horizontal = ('resources', )

    def num_resources(self, obj):
        count = obj.resources.count()
        return "{} resource{}".format(count, pluralize(count))
    num_resources.short_description = '# resources'

    def num_services(self, obj):
        count = obj.services.count()
        return changelist_link(
            Service,
            "{} service{}".format(count, pluralize(count)),
            dict(category__id__exact = obj.pk)
        )
    num_services.short_description = '# services'
