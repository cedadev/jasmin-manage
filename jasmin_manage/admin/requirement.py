from datetime import date

from django.contrib import admin
from django.utils.html import format_html
from django.utils import formats
from django import forms

from django_admin_listfilter_dropdown.filters import (
    RelatedDropdownFilter,
    RelatedOnlyDropdownFilter
)

from rangefilter.filter import DateRangeFilter

from concurrency.admin import ConcurrentModelAdmin

from ..models import Requirement
from .util import change_link


@admin.register(Requirement)
class RequirementAdmin(ConcurrentModelAdmin):
    class Media:
        css = {
            "all": ('css/admin/highlight.css', )
        }
        js = ('js/admin/highlight.js', )

    list_display = (
        'id',
        'project_link',
        'service_link',
        'resource_link',
        'status_formatted',
        'amount_formatted',
        'start_date_formatted',
        'end_date_formatted',
    )
    list_filter = (
        ('service__project__consortium', RelatedDropdownFilter),
        ('service__project', RelatedDropdownFilter),
        ('resource', RelatedDropdownFilter),
        'status',
        ('start_date', DateRangeFilter),
        ('end_date', DateRangeFilter),
    )
    autocomplete_fields = ('service', 'resource')
    exclude = (
        'service',
        'resource',
        'status',
        'amount',
        'start_date',
        'end_date'
    )
    readonly_fields = (
        'project_link',
        'service_link',
        'resource_link',
        'status_formatted',
        'amount_formatted',
        'start_date_formatted',
        'end_date_formatted'
    )
    save_as = True

    def get_exclude(self, request, obj = None):
        if obj and not self.has_change_permission(request, obj):
            return super().get_exclude(request, obj)
        else:
            return ()

    def get_readonly_fields(self, request, obj = None):
        if obj and not self.has_change_permission(request, obj):
            return super().get_readonly_fields(request, obj)
        else:
            return ()

    def project_link(self, obj):
        return change_link(obj.service.project)
    project_link.short_description = 'project'

    def service_link(self, obj):
        return change_link(obj.service, obj.service.name)
    service_link.short_description = 'service'

    def resource_link(self, obj):
        return change_link(obj.resource)
    resource_link.short_description = 'resource'

    STATUS_CLASSES = dict(
        REJECTED = 'danger',
        APPROVED = 'info',
        AWAITING_PROVISIONING = 'warning',
        PROVISIONED = 'success',
        DECOMMISSIONED = 'muted'
    )
    def status_formatted(self, obj):
        status = Requirement.Status(obj.status)
        return format_html(
            '<code class="highlight {css}">{label}</code>',
            label = status.label,
            css = self.STATUS_CLASSES.get(status.name, '')
        )
    status_formatted.short_description = 'status'

    def amount_formatted(self, obj):
        return obj.resource.format_amount(obj.amount)
    amount_formatted.short_description = 'amount'

    def start_date_formatted(self, obj):
        formatted_date = formats.date_format(obj.start_date)
        # If the requirement is overdue for provisioning, print it coloured
        if obj.start_date <= date.today() and \
           obj.status == Requirement.Status.AWAITING_PROVISIONING:
            return format_html(
                '<span class="highlight danger">{}</span>',
                formatted_date
            )
        else:
            return formatted_date
    start_date_formatted.short_description = 'start date'

    def end_date_formatted(self, obj):
        formatted_date = formats.date_format(obj.end_date)
        # If the requirement is overdue for decommisioning, print it coloured
        if obj.end_date < date.today() and obj.status == Requirement.Status.PROVISIONED:
            return format_html(
                '<span class="highlight danger">{}</span>',
                formatted_date
            )
        else:
            return formatted_date
    end_date_formatted.short_description = 'end date'
