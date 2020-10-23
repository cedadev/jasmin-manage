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

from ..models import Collaborator, Project, Requirement, Service
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
        'consortium_link',
        'num_services',
        'num_requirements',
        'num_collaborators',
        'created_at'
    )
    list_filter = (
        ('consortium', RelatedDropdownFilter),
        'status',
    )
    autocomplete_fields = ('consortium', )
    search_fields = ('name', )
    readonly_fields = (
        'num_services',
        'num_requirements',
        'num_collaborators',
        'created_at'
    )

    def get_exclude(self, request, obj = None):
        exclude = tuple(super().get_exclude(request, obj) or ())
        if obj and not self.has_change_permission(request, obj):
            return exclude + ('status', 'consortium')
        else:
            return exclude

    def get_readonly_fields(self, request, obj = None):
        readonly_fields = tuple(super().get_readonly_fields(request, obj))
        if obj and not self.has_change_permission(request, obj):
            return ('status_formatted', 'consortium_link') + readonly_fields
        if not obj:
            return ()
        else:
            return readonly_fields

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(
            # Annotate the queryset with information about the number of collaborators, services and requirements
            collaborator_count = Count('collaborator', distinct = True),
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
        # The annotations clear the ordering, so re-apply the default one
        return qs.order_by(*qs.query.get_meta().ordering)

    def status_formatted(self, obj):
        return format_html('<code>{}</code>', Project.Status(obj.status).label)
    status_formatted.short_description = 'status'

    def consortium_link(self, obj):
        return change_link(obj.consortium)
    consortium_link.short_description = 'consortium'

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

    def num_collaborators(self, obj):
        return changelist_link(
            Collaborator,
            "{} collaborator{}".format(obj.collaborator_count, pluralize(obj.collaborator_count)),
            dict(project__id__exact = obj.pk)
        )
    num_collaborators.short_description = '# collaborators'
