from django.contrib import admin
from django.utils.html import format_html
from django.template.defaultfilters import pluralize

from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter

from concurrency.admin import ConcurrentModelAdmin

from ..models import Quota, Requirement
from .util import changelist_link, change_link


@admin.register(Quota)
class QuotaAdmin(ConcurrentModelAdmin):
    class Media:
        css = {
            "all": ('css/admin/highlight.css', )
        }
        js = ('js/admin/highlight.js', )

    list_display = (
        'id',
        'consortium_link',
        'resource_link',
        'amount_formatted',
        'provisioned',
        'awaiting',
        'approved',
    )
    list_filter = (
        ('resource', RelatedDropdownFilter),
        ('consortium', RelatedDropdownFilter),
    )
    list_select_related = ('resource', 'consortium')
    show_full_result_count = False
    readonly_fields = ('provisioned', 'awaiting', 'approved')

    def get_readonly_fields(self, request, obj):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj and not self.has_change_permission(request, obj):
            return ('consortium_link', 'resource_link', 'amount_formatted', ) + readonly_fields
        elif not obj:
            return ()
        else:
            return readonly_fields

    def get_exclude(self, request, obj = None):
        exclude = tuple(super().get_exclude(request, obj) or ())
        if obj and not self.has_change_permission(request, obj):
            return exclude + ('consortium', 'resource', 'amount')
        else:
            return exclude

    def get_queryset(self, request):
        return super().get_queryset(request).annotate_usage()

    def consortium_link(self, obj):
        return change_link(obj.consortium)
    consortium_link.short_description = 'consortium'

    def resource_link(self, obj):
        return change_link(obj.resource)
    resource_link.short_description = 'resource'

    def amount_formatted(self, obj):
        return obj.resource.format_amount(obj.amount)
    amount_formatted.short_description = 'amount'

    def _cell_content(self, obj, status):
        count = getattr(obj, '{}_count'.format(status.name.lower()))
        total = getattr(obj, '{}_total'.format(status.name.lower()))
        total_formatted = obj.resource.format_amount(total)
        # Only show the number of requirements if > 0
        if count > 0:
            return format_html(
                '{} / {}',
                total_formatted,
                changelist_link(
                    Requirement,
                    '{} requirement{}'.format(count, pluralize(count)),
                    dict(
                        consortium__id__exact = obj.consortium.pk,
                        resource__id__exact = obj.resource.pk,
                        status__exact = status
                    )
                )
            )
        else:
            return total_formatted

    def provisioned(self, obj):
        content = self._cell_content(obj, Requirement.Status.PROVISIONED)
        if obj.provisioned_total > obj.amount:
            # If the quota is overprovisioned, use danger
            return format_html('<span class="highlight danger">{}</span>', content)
        elif obj.provisioned_total > obj.amount * 0.8:
            # If the quota is over 80% provisioned, use warning
            return format_html('<span class="highlight warning">{}</span>', content)
        else:
            # Otherwise, use success
            return format_html('<span class="highlight success">{}</span>', content)

    def awaiting(self, obj):
        content = self._cell_content(obj, Requirement.Status.AWAITING_PROVISIONING)
        awaiting = obj.awaiting_provisioning_total
        total = obj.provisioned_total + awaiting
        if awaiting > 0 and total > obj.amount:
            # If the quota would be overprovisioned if the awaiting were provisioned, use warning
            return format_html('<span class="highlight warning">{}</span>', content)
        else:
            return content

    def approved(self, obj):
        content = self._cell_content(obj, Requirement.Status.APPROVED)
        approved = obj.approved_total
        total = obj.provisioned_total + obj.awaiting_provisioning_total + approved
        if approved > 0 and total > obj.amount:
            # If the quota would be overprovisioned if the awaiting and approved
            # were provisioned, use warning
            return format_html('<span class="highlight warning">{}</span>', content)
        else:
            return content
