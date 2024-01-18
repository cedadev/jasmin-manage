from django.contrib import admin
from django.template.defaultfilters import pluralize

from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter

from ..models import Invitation
from .util import change_link


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("id", "project_link", "email", "created_at")
    list_select_related = ("project",)
    list_filter = (("project", RelatedDropdownFilter),)
    autocomplete_fields = ("project",)
    search_fields = ("project__name", "email")
    readonly_fields = ("created_at",)

    def project_link(self, obj):
        return change_link(obj.project)

    project_link.short_description = "project"
