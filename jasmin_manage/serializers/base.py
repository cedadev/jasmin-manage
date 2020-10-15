from django.urls import get_resolver, URLPattern

from rest_framework import fields, relations, serializers
from rest_framework.reverse import reverse


def get_url_patterns(resolver):
    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLPattern):
            yield pattern
        else:
            yield from get_url_patterns(pattern)


class EnumField(fields.Field):
    """
    Serializer field for a Python enum.
    """
    default_error_messages = {
        'invalid_choice': '"{input}" is not a valid choice.'
    }

    def __init__(self, choices, **kwargs):
        self.choices = choices
        self.allow_none = kwargs.get('allow_none', False)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if data is None and self.allow_none:
            return None
        try:
            return self.choices[str(data)]
        except KeyError:
            self.fail('invalid_choice', input = data)

    def to_representation(self, value):
        if value is None:
            return value
        if not isinstance(value, self.choices):
            value = self.choices(value)
        return value.name

    # def iter_options(self):
    #     """
    #     Helper method for use with templates rendering select widgets.
    #     """
    #     return iter_options(
    #         self.grouped_choices,
    #         cutoff=self.html_cutoff,
    #         cutoff_text=self.html_cutoff_text
    #     )


class LinksField(fields.ReadOnlyField):
    """
    Field class for a links field for an object.
    """
    def __init__(self, **kwargs):
        self.basename = kwargs.pop('basename')
        self.extra_actions = kwargs.pop('extra_actions', [])
        kwargs['source'] = '*'
        super().__init__(**kwargs)

    def get_action_url(self, obj, action, request, format):
        view_name = "{}-{}".format(self.basename, action)
        return reverse(
            view_name,
            kwargs = dict(pk = obj.pk),
            request = request,
            format = format
        )

    def to_representation(self, value):
        request = self.context['request']
        format = self.context.get('format', None)
        if format and self.format and self.format != format:
            format = self.format
        # Always start with the self link
        links = dict(self = self.get_action_url(value, 'detail', request, format))
        # Add the links for the specified actions
        links.update({
            action: self.get_action_url(value, action, request, format)
            for action in self.extra_actions
        })
        return links


class BaseSerializer(serializers.ModelSerializer):
    """
    Base class for JASMIN Manage serializers.
    """
    serializer_links_field = LinksField
    links_field_name = "_links"

    def get_default_field_names(self, declared_fields, model_info):
        return (
            super().get_default_field_names(declared_fields, model_info) +
            [self.links_field_name]
        )

    def build_links_field(self, field_name, model_class):
        """
        Create a field representing the object's own URL.
        """
        basename = model_class._meta.object_name.lower()
        # Get the names of all the views that define actions for the model
        actions = set(
            key.replace(basename + '-', '')
            for key in get_resolver('jasmin_manage.urls').reverse_dict.keys()
            if isinstance(key, str) and key.startswith(basename + '-')
        )
        # Remove the list and detail views
        extra_actions = actions - {'list', 'detail'}
        # Pass the basename and extra actions to the links field
        return (
            self.serializer_links_field,
            dict(basename = basename, extra_actions = extra_actions)
        )

    def build_field(self, field_name, info, model_class, nested_depth):
        if field_name == self.links_field_name:
            return self.build_links_field(field_name, model_class)
        else:
            return super().build_field(field_name, info, model_class, nested_depth)
