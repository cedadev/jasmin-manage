from django.utils.html import format_html
from django.utils.encoding import force_str
from django.utils.http import urlencode
from django.urls import reverse, NoReverseMatch


def changelist_link(related_model, text, query_params):
    """
    Returns a link to the changelist page for the related model.
    """
    try:
        return format_html(
            '<a href="{}?{}">{}</a>',
            reverse(
                "admin:{}_changelist".format(
                    related_model._meta.label_lower.replace(".", "_")
                )
            ),
            urlencode(query_params),
            text,
        )
    except NoReverseMatch:
        return text


def change_link(obj, text=None):
    """
    Returns a link to the admin view/change page for an object.
    """
    if not text:
        text = force_str(obj)
    try:
        return format_html(
            '<a href="{}">{}</a>',
            reverse(
                "admin:{}_change".format(obj._meta.label_lower.replace(".", "_")),
                args=(obj.pk,),
            ),
            text,
        )
    except NoReverseMatch:
        return text
