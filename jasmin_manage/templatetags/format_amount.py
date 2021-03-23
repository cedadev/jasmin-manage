from django import template


register = template.Library()


@register.filter(is_safe = True)
def format_amount(amount, resource):
    """
    Formats the given amount using the given resource.
    """
    return resource.format_amount(amount)
