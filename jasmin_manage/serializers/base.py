from django.urls import get_resolver, NoReverseMatch

from rest_framework import fields, relations, serializers
from rest_framework.reverse import reverse


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
        self.related_links = kwargs.pop('related_links', [])
        self.action_links = kwargs.pop('action_links', [])
        kwargs['source'] = '*'
        super().__init__(**kwargs)

    def to_representation(self, value):
        request = self.context['request']
        format = self.context.get('format', None)
        if format and self.format and self.format != format:
            format = self.format
        # Always start with the self link
        links = dict(
            self = reverse(
                "{}-detail".format(self.basename),
                kwargs = dict(pk = value.pk),
                request = request,
                format = format
            )
        )
        # Add links to the related objects
        for name, model, attr in self.related_links:
            try:
                links.update({
                    name: reverse(
                        "{}-detail".format(model._meta.object_name.lower()),
                        kwargs = dict(pk = getattr(value, attr)),
                        request = request,
                        format = format
                    )
                })
            except NoReverseMatch:
                pass
        # Add links to the additional actions
        links.update({
            action: reverse(
                "{}-{}".format(self.basename, action),
                kwargs = dict(pk = value.pk),
                request = request,
                format = format
            )
            for action in self.action_links
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
        # Calculate the list of foreign key fields for which related links should be added
        related_links = [
            (f.name, f.related_model, f.get_attname())
            for f in model_class._meta.get_fields()
            if f.many_to_one or f.one_to_one
        ]
        # Get the names of all the views that define actions for the model
        actions = set(
            key[len(basename) + 1:]
            for key in get_resolver('jasmin_manage.urls').reverse_dict.keys()
            if isinstance(key, str) and key.startswith(basename + '-')
        )
        # Remove the list and detail views
        action_links = actions - {'list', 'detail'}
        # Pass the basename and extra links to the field constructor
        return (
            self.serializer_links_field,
            dict(
                basename = basename,
                related_links = related_links,
                action_links = action_links
            )
        )

    def build_field(self, field_name, info, model_class, nested_depth):
        if field_name == self.links_field_name:
            return self.build_links_field(field_name, model_class)
        else:
            return super().build_field(field_name, info, model_class, nested_depth)
