from django.contrib import admin
from django.utils.html import format_html
from django.db.models import (
    Count,
    Subquery,
    OuterRef,
    Value,
    IntegerField
)
from django.db.models.functions import Coalesce
from django.template.defaultfilters import pluralize

from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter

from concurrency.admin import ConcurrentModelAdmin

from ..models import Requirement, Service
from .util import changelist_link, change_link


@admin.register(Service)
class ServiceAdmin(ConcurrentModelAdmin):
    class Media:
        css = {
            "all": ('css/admin/highlight.css', )
        }
        js = ('js/admin/highlight.js', )

    list_display = ('name', 'project_link', 'category_link', 'num_requirements')
    list_filter = (
        ('category', RelatedDropdownFilter),
        ('project', RelatedDropdownFilter),
    )
    search_fields = ('project__name', 'name')
    autocomplete_fields = ('project', )
    readonly_fields = ('num_requirements', )

    def get_exclude(self, request, obj = None):
        exclude = tuple(super().get_exclude(request, obj) or ())
        if obj and not self.has_change_permission(request, obj):
            return exclude + ('category', 'project')
        else:
            return exclude

    def get_readonly_fields(self, request, obj = None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj and not self.has_change_permission(request, obj):
            return ('category_link', 'project_link') + readonly_fields
        elif not obj:
            return ()
        else:
            return readonly_fields

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            # Annotate the queryset with information about the number of requirements
            requirement_count = Count('requirement', distinct = True),
            # Also annotate with information about the number of requirements awaiting provisioning
            awaiting_count = Coalesce(
                Subquery(Requirement.objects
                    .filter(
                        service = OuterRef('pk'),
                        status = Requirement.Status.AWAITING_PROVISIONING
                    )
                    .order_by()
                    .values('service')
                    .annotate(count = Count("*"))
                    .values('count')
                ),
                Value(0),
                output_field = IntegerField()
            )
        )

    def category_link(self, obj):
        return change_link(obj.category)
    category_link.short_description = 'category'

    def project_link(self, obj):
        return change_link(obj.project)
    project_link.short_description = 'project'

    def num_requirements(self, obj):
        text = "{} requirement{}".format(obj.requirement_count, pluralize(obj.requirement_count))
        if obj.awaiting_count > 0:
            text = "{} / {} awaiting provisioning".format(text, obj.awaiting_count)
        # Highlight any projects that have requirements that are AWAITING_PROVISIONING
        content = changelist_link(
            Requirement,
            text,
            dict(service__id__exact = obj.pk)
        )
        if obj.awaiting_count > 0:
            return format_html('<span class="highlight warning">{}</span>', content)
        else:
            return content
    num_requirements.short_description = '# requirements'
