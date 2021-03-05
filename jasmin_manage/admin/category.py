from django.contrib import admin
from django.db.models import Count
from django.template.defaultfilters import pluralize

from ..models import Category, Service
from .util import changelist_link


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'num_resources', 'num_services')
    search_fields = ('name', )
    filter_horizontal = ('resources', )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Annotate the queryset with information about the number of resources and services
        qs = qs.annotate(
            num_resources = Count('resources', distinct = True),
            num_services = Count('service', distinct = True),
        )
        # The annotations clear the ordering, so re-apply the default one
        return qs.order_by(*qs.query.get_meta().ordering)

    def num_resources(self, obj):
        return "{} resource{}".format(obj.num_resources, pluralize(obj.num_resources))
    num_resources.short_description = '# resources'

    def num_services(self, obj):
        count = obj.num_services
        return changelist_link(
            Service,
            "{} service{}".format(count, pluralize(count)),
            dict(category__id__exact = obj.pk)
        )
    num_services.short_description = '# services'
