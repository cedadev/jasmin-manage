from django.contrib import admin
from django.db.models import (
    Case,
    Count,
    F,
    IntegerField,
    OuterRef,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.template.defaultfilters import pluralize
from django.utils.html import format_html

from ..models import Consortium, Project, Quota, Requirement
from .util import change_link, changelist_link


@admin.register(Consortium)
class ConsortiumAdmin(admin.ModelAdmin):
    class Media:
        css = {"all": ("css/admin/highlight.css",)}
        js = ("js/admin/highlight.js",)

    list_display = ("name", "is_public", "manager_link", "num_quotas", "num_projects")
    list_select_related = ("manager",)
    search_fields = ("name",)
    autocomplete_fields = ("manager",)
    readonly_fields = ("num_quotas", "num_projects", "num_requirements")
    

    def get_exclude(self, request, obj=None):
        exclude = tuple(super().get_exclude(request, obj) or ())
        if obj and not self.has_change_permission(request, obj):
            return exclude + ("manager",)
        else:
            return exclude

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj and not self.has_change_permission(request, obj):
            return ("manager_link",) + readonly_fields
        elif not obj:
            return ()
        else:
            return readonly_fields

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Annotate the consortia with information about the number of quotas, projects and requirements
        qs = qs.annotate(
            quota_count=Count("quota", distinct=True),
            project_count=Count("project", distinct=True),
            requirement_count=Count("project__service__requirement", distinct=True),
        )
        # Also annotate with information about the number of overprovisioned quotas
        overprovisioned_quotas = (
            Quota.objects.filter(consortium=OuterRef("pk"))
            .annotate_usage()
            .annotate(
                overprovisioned=Case(
                    When(provisioned_total__gt=F("amount"), then=1),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            )
        )
        qs = qs.annotate(
            overprovisioned_count=Coalesce(
                Subquery(
                    overprovisioned_quotas.order_by()
                    .values("consortium")
                    .annotate(overprovisioned_count=Sum("overprovisioned"))
                    .values("overprovisioned_count")
                ),
                Value(0),
            )
        )
        # The annotations remove the ordering, so re-apply the default ones
        return qs.order_by(*qs.query.get_meta().ordering)

    def num_quotas(self, obj):
        text = "{} quota{}".format(obj.quota_count, pluralize(obj.quota_count))
        if obj.overprovisioned_count > 0:
            text = "{} / {} overprovisioned".format(text, obj.overprovisioned_count)
        content = changelist_link(Quota, text, dict(consortium__id__exact=obj.pk))
        # If the consortium has at least one quota that is overprovisioned, highlight it
        if obj.overprovisioned_count > 0:
            return format_html('<span class="highlight warning">{}</span>', content)
        else:
            return content

    num_quotas.short_description = "# quotas"

    def num_projects(self, obj):
        return changelist_link(
            Project,
            "{} project{}".format(obj.project_count, pluralize(obj.project_count)),
            dict(consortium__id__exact=obj.pk),
        )

    num_projects.short_description = "# projects"

    def num_requirements(self, obj):
        return changelist_link(
            Requirement,
            "{} requirement{}".format(
                obj.requirement_count, pluralize(obj.requirement_count)
            ),
            dict(service__project__consortium__id__exact=obj.pk),
        )

    num_requirements.short_description = "# requirements"

    def manager_link(self, obj):
        return change_link(obj.manager)

    manager_link.short_description = "manager"
