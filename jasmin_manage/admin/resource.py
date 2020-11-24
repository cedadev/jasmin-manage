from django.contrib import admin
from django.utils.html import format_html
from django.template.defaultfilters import pluralize

from ..models import Quota, Requirement, Resource, ResourceChunk
from .util import changelist_link


class ResourceChunkInline(admin.TabularInline):
    model = ResourceChunk


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    class Media:
        css = {
            "all": ('css/admin/highlight.css', )
        }
        js = ('js/admin/highlight.js', )

    list_display = (
        'name',
        'total_available_formatted',
        'total_quotas',
        'total_provisioned',
        'total_awaiting',
        'total_approved',
    )
    show_full_result_count = False
    readonly_fields = (
        'total_available_formatted',
        'total_quotas',
        'total_provisioned',
        'total_awaiting',
        'total_approved'
    )
    inlines = (ResourceChunkInline, )
    search_fields = ('name', )

    def get_exclude(self, request, obj = None):
        exclude = tuple(super().get_exclude(request, obj) or ())
        if obj and not self.has_change_permission(request, obj):
            return exclude + ('short_name', 'units')
        return exclude

    def get_readonly_fields(self, request, obj = None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj:
            return readonly_fields
        else:
            return ()

    def get_queryset(self, request):
        return super().get_queryset(request).annotate_usage()

    def total_available_formatted(self, obj):
        return obj.format_amount(obj.total_available)
    total_available_formatted.short_description = 'total available'

    def total_quotas(self, obj):
        total_formatted = obj.format_amount(obj.quota_total)
        if obj.quota_count > 0:
            content = format_html(
                "{} / {}",
                total_formatted,
                changelist_link(
                    Quota,
                    '{} quota{}'.format(obj.quota_count, pluralize(obj.quota_count)),
                    dict(resource__id__exact = obj.pk)
                )
            )
            if obj.quota_total > obj.total_available:
                # If the quota total is greater than available, use danger
                return format_html('<span class="highlight danger">{}</span>', content)
            else:
                return content
        else:
            return total_formatted

    def _cell_content(self, obj, status):
        count = getattr(obj, '{}_count'.format(status.name.lower()))
        total = getattr(obj, '{}_total'.format(status.name.lower()))
        total_formatted = obj.format_amount(total)
        # Only show the number of requirements if > 0
        if count > 0:
            return format_html(
                '{} / {}',
                total_formatted,
                changelist_link(
                    Requirement,
                    '{} requirement{}'.format(count, pluralize(count)),
                    dict(
                        resource__id__exact = obj.pk,
                        status__exact = status
                    )
                )
            )
        else:
            return total_formatted

    def total_provisioned(self, obj):
        content = self._cell_content(obj, Requirement.Status.PROVISIONED)
        if obj.provisioned_total > obj.total_available:
            # If the resource is overprovisioned, use danger
            return format_html('<span class="highlight danger">{}</span>', content)
        elif obj.provisioned_total > obj.total_available * 0.8:
            # If the resource is over 80% provisioned, use warning
            return format_html('<span class="highlight warning">{}</span>', content)
        else:
            # Otherwise, use success
            return format_html('<span class="highlight success">{}</span>', content)

    def total_awaiting(self, obj):
        content = self._cell_content(obj, Requirement.Status.AWAITING_PROVISIONING)
        awaiting = obj.awaiting_provisioning_total
        total = obj.provisioned_total + awaiting
        if awaiting > 0 and total > obj.total_available:
            # If the resource would be overprovisioned if the awaiting were provisioned, use warning
            return format_html('<span class="highlight warning">{}</span>', content)
        else:
            return content

    def total_approved(self, obj):
        content = self._cell_content(obj, Requirement.Status.APPROVED)
        approved = obj.approved_total
        total = obj.provisioned_total + obj.awaiting_provisioning_total + approved
        if approved > 0 and total > obj.total_available:
            # If the resource would be overprovisioned if the awaiting and approved
            # were provisioned, use warning
            return format_html('<span class="highlight warning">{}</span>', content)
        else:
            return content
