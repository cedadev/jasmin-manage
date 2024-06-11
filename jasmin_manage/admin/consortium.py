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

    list_display = ("name", "is_public")
    search_fields = ("name",)
    

  
