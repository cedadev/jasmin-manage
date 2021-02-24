import copy
import functools

from django.urls import get_resolver, NoReverseMatch

from rest_framework import fields, relations, serializers
from rest_framework.reverse import reverse as drf_reverse

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field


class EnumField(fields.ChoiceField):
    """
    Serializer field for a Python enum.
    """
    def __init__(self, enum, **kwargs):
        self.enum = enum
        # Use the enum names for the choices
        super().__init__([v.name for v in enum], **kwargs)

    def to_internal_value(self, data):
        if not data and self.allow_blank:
            return None
        try:
            return self.enum[str(data)]
        except KeyError:
            self.fail('invalid_choice', input = data)

    def to_representation(self, value):
        if value is None:
            return value
        if not isinstance(value, self.enum):
            value = self.enum(value)
        return value.name


@extend_schema_field(OpenApiTypes.OBJECT)
class LinksField(fields.Field):
    """
    Field class for a links field for an object.

    For model serializers, the basename and set of links will be automatically derived
    from the model. For non-model serializers, they must be specified manually.
    """
    def __init__(self, **kwargs):
        self.basename = kwargs.pop('basename', None)
        self.urlconf = kwargs.pop('urlconf', None)
        self.related_object_links = kwargs.pop('related_object_links', None)
        self.related_list_links = kwargs.pop('related_list_links', None)
        self.action_links = kwargs.pop('action_links', None)
        kwargs.update(source = '*', read_only = True)
        super().__init__(**kwargs)

    def bind(self, field_name, parent):
        super().bind(field_name, parent)
        # Extract the model meta from the given serializer class
        if not self.basename:
            self.basename = parent.Meta.model._meta.object_name.lower()
        # If all the links were given already, we are done
        if (
            self.related_object_links is not None and
            self.related_list_links is not None and
            self.action_links is not None
        ):
            return
        # Derive the urlconf to use from the app containing the model
        if not self.urlconf:
            self.urlconf = "{}.urls".format(parent.Meta.model._meta.app_label)
        # Get the set of all view names in the app
        view_names = set(
            key
            for key in get_resolver(self.urlconf).reverse_dict.keys()
            if isinstance(key, str)
        )
        # Calculate the views that correspond to related objects in either direction
        related_object_links = []
        related_list_links = []
        for field in parent.Meta.model._meta.get_fields():
            if field.many_to_one or field.one_to_one:
                view_name = "{}-detail".format(field.related_model._meta.object_name.lower())
                if view_name in view_names:
                    related_object_links.append((field.name, view_name, field.get_attname()))
            elif field.one_to_many or field.many_to_many:
                # If the field has a related name, use that, otherwise use the field name
                field_name = getattr(field, 'related_name', None) or field.name
                view_name = "{}-{}-list".format(self.basename, field_name)
                if view_name in view_names:
                    related_list_links.append((field_name, view_name))
        # Calculate the views that correspond to extra actions
        action_links = []
        for view_name in view_names:
            if not view_name.startswith(self.basename):
                continue
            if view_name in {link[1] for link in related_object_links}:
                continue
            if view_name in {link[1] for link in related_list_links}:
                continue
            action = view_name[len(self.basename) + 1:]
            if action in {'list', 'detail'}:
                continue
            action_links.append((action, view_name))
        if self.related_object_links is None:
            self.related_object_links = related_object_links
        if self.related_list_links is None:
            self.related_list_links = related_list_links
        if self.action_links is None:
            self.action_links = action_links

    def to_representation(self, value):
        # Get the parameters we need for reversing
        request = self.context['request']
        format = self.context.get('format', None)
        if format and self.format and self.format != format:
            format = self.format
        reverse = lambda view_name, kwargs: drf_reverse(
            view_name,
            kwargs = kwargs,
            request = request,
            format = format
        )
        # Always start with the self link
        links = dict(
            self = reverse("{}-detail".format(self.basename), dict(pk = value.pk))
        )
        # Add links to the related objects
        links.update({
            name: reverse(view_name, dict(pk = getattr(value, attr)))
            for name, view_name, attr in (self.related_object_links or [])
        })
        # Add the related list links
        links.update({
            name: reverse(view_name, { self.basename + '_pk': value.pk })
            for name, view_name in (self.related_list_links or [])
        })
        # Add extra actions to the links
        links.update({
            name: reverse(view_name, dict(pk = value.pk))
            for name, view_name in (self.action_links or [])
        })
        return links


class BaseSerializer(serializers.ModelSerializer):
    """
    Base class for JASMIN Manage serializers.
    """
    _links = LinksField()

    def get_fields(self):
        fields = super().get_fields()
        # Move the links field to the end of the field list if present
        links_field = fields.pop('_links', None)
        if links_field:
            fields['_links'] = links_field
        # Apply read_only_fields even when the field classes are explicitly defined
        for field_name in getattr(self.Meta, 'read_only_fields', []):
            fields[field_name].read_only = True
        # Use the presence of an instance to decide if it is an update or a create
        if self.instance:
            # For an update, make the create-only fields read-only
            for field_name in getattr(self.Meta, 'create_only_fields', []):
                fields[field_name].read_only = True
        else:
            # For a create, make the update-only fields read-only
            for field_name in getattr(self.Meta, 'update_only_fields', []):
                fields[field_name].read_only = True
        return fields
