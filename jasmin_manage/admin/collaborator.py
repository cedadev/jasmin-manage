from django.contrib import admin
from django.template.defaultfilters import pluralize

from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter

from ..models import Collaborator
from .util import change_link


@admin.register(Collaborator)
class CollaboratorAdmin(admin.ModelAdmin):
    list_display = ("id", "project_link", "user_link", "role")
    list_select_related = ("project", "user")
    list_filter = (
        ("project", RelatedDropdownFilter),
        ("user", RelatedDropdownFilter),
        "role",
    )
    autocomplete_fields = ("project", "user")
    search_fields = ("project__name", "user__username", "role")

    def project_link(self, obj):
        return change_link(obj.project)

    project_link.short_description = "project"

    def user_link(self, obj):
        return change_link(obj.user)

    user_link.short_description = "user"
