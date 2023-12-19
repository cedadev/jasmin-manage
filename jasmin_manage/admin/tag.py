from django.contrib import admin
from django.db.models import Count
from django.template.defaultfilters import pluralize

from ..models import Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "num_projects")
    search_fields = ("name",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Annotate the queryset with information about the number of resources and services
        qs = qs.annotate(
            num_projects=Count("projects", distinct=True),
        )
        # The annotations clear the ordering, so re-apply the default one
        return qs.order_by(*qs.query.get_meta().ordering)

    def num_projects(self, obj):
        return "{} project{}".format(obj.num_projects, pluralize(obj.num_projects))

    num_projects.short_description = "# projects"
