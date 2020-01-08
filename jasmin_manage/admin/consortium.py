from django.contrib import admin
from django.utils.html import format_html
from django.db.models import (
    Sum,
    Count,
    Subquery,
    Case,
    When,
    OuterRef,
    Value,
    F,
    IntegerField
)
from django.db.models.functions import Coalesce
from django.template.defaultfilters import pluralize

from ..models import Consortium, Project, Quota
from .util import changelist_link, change_link


@admin.register(Consortium)
class ConsortiumAdmin(admin.ModelAdmin):
    class Media:
        css = {
            "all": ('css/admin/highlight.css', )
        }
        js = ('js/admin/highlight.js', )

    list_display = ('name', 'manager_link', 'num_quotas', 'num_projects')
    search_fields = ('name', )
    autocomplete_fields = ('manager', )
    readonly_fields = ('num_quotas', 'num_projects')

    def get_exclude(self, request, obj = None):
        exclude = tuple(super().get_exclude(request, obj) or ())
        if obj and not self.has_change_permission(request, obj):
            return exclude + ('manager', 'description_markup_type')
        else:
            return exclude

    def get_readonly_fields(self, request, obj = None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj and not self.has_change_permission(request, obj):
            return ('manager_link', ) + readonly_fields
        elif not obj:
            return ()
        else:
            return readonly_fields

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Annotate the consortia with information about the number of quotas and projects
        qs = qs.annotate(
            quota_count = Count('quota', distinct = True),
            project_count = Count('project', distinct = True)
        )
        # Also annotate with information about the number of overprovisioned quotas
        overprovisioned_quotas = (Quota.objects
            .filter(consortium = OuterRef('pk'))
            .annotate_usage()
            .annotate(
                overprovisioned = Case(
                    When(provisioned_total__gt = F('amount'), then = 1),
                    default = Value(0),
                    output_field = IntegerField()
                )
            )
        )
        return qs.annotate(
            overprovisioned_count = Coalesce(
                Subquery(overprovisioned_quotas
                    .order_by()
                    .values('consortium')
                    .annotate(overprovisioned_count = Sum('overprovisioned'))
                    .values('overprovisioned_count')
                ),
                Value(0)
            )
        )

    def num_quotas(self, obj):
        text = '{} quota{}'.format(obj.quota_count, pluralize(obj.quota_count))
        if obj.overprovisioned_count > 0:
            text = '{} / {} overprovisioned'.format(text, obj.overprovisioned_count)
        content = changelist_link(
            Quota,
            text,
            dict(consortium__id__exact = obj.pk)
        )
        # If the consortium has at least one quota that is overprovisioned, highlight it
        if obj.overprovisioned_count > 0:
            return format_html('<span class="highlight warning">{}</span>', content)
        else:
            return content
    num_quotas.short_description = '# quotas'

    def num_projects(self, obj):
        return changelist_link(
            Project,
            '{} project{}'.format(obj.project_count, pluralize(obj.project_count)),
            dict(consortium__id__exact = obj.pk)
        )
    num_projects.short_description = '# projects'

    def manager_link(self, obj):
        return change_link(obj.manager)
    manager_link.short_description = 'manager'
