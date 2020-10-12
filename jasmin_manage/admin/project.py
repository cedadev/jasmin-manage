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

from ..models import Project, Requirement, Service
from .util import changelist_link, change_link


@admin.register(Project)
class ProjectAdmin(ConcurrentModelAdmin):
    class Media:
        css = {
            "all": ('css/admin/highlight.css', )
        }
        js = ('js/admin/highlight.js', )

    list_display = (
        'name',
        'status_formatted',
        'num_services',
        'num_requirements',
        'owner_link',
        'created_at'
    )
    list_filter = (
        ('service__requirement__consortium', RelatedDropdownFilter),
        'status',
    )
    autocomplete_fields = ('owner', )
    search_fields = ('name', )
    readonly_fields = ('num_services', 'num_requirements', 'created_at')

    def get_exclude(self, request, obj = None):
        exclude = tuple(super().get_exclude(request, obj) or ())
        if obj and not self.has_change_permission(request, obj):
            return exclude + ('status', 'owner')
        else:
            return exclude

    def get_readonly_fields(self, request, obj = None):
        readonly_fields = tuple(super().get_readonly_fields(request, obj))
        if obj and not self.has_change_permission(request, obj):
            return ('status_formatted', 'owner_link') + readonly_fields
        if not obj:
            return ()
        else:
            return readonly_fields

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            # Annotate the queryset with information about the number of services and requirements
            service_count = Count('service', distinct = True),
            requirement_count = Count('service__requirement', distinct = True),
            # Also annotate with information about the number of requirements awaiting provisioning
            awaiting_count = Coalesce(
                Subquery(Requirement.objects
                    .filter(
                        service__project = OuterRef('pk'),
                        status = Requirement.Status.AWAITING_PROVISIONING
                    )
                    .order_by()
                    .values('service__project')
                    .annotate(count = Count("*"))
                    .values('count')
                ),
                Value(0),
                output_field = IntegerField()
            )
        )

    def status_formatted(self, obj):
        return format_html('<code>{}</code>', Project.Status(obj.status).label)
    status_formatted.short_description = 'status'

    def num_services(self, obj):
        return changelist_link(
            Service,
            "{} service{}".format(obj.service_count, pluralize(obj.service_count)),
            dict(project__id__exact = obj.pk)
        )
    num_services.short_description = '# services'

    def num_requirements(self, obj):
        text = "{} requirement{}".format(obj.requirement_count, pluralize(obj.requirement_count))
        if obj.awaiting_count > 0:
            text = "{} / {} awaiting provisioning".format(text, obj.awaiting_count)
        # Highlight any projects that have requirements that are AWAITING_PROVISIONING
        content = changelist_link(
            Requirement,
            text,
            dict(service__project__id__exact = obj.pk)
        )
        if obj.awaiting_count > 0:
            return format_html('<span class="highlight warning">{}</span>', content)
        else:
            return content
    num_requirements.short_description = '# requirements'

    def owner_link(self, obj):
        return change_link(obj.owner)
    owner_link.short_description = 'owner'
