import copy

from django.urls import get_resolver, NoReverseMatch

from rest_framework import fields, relations, serializers
from rest_framework.reverse import reverse


class EnumField(fields.ChoiceField):
    """
    Serializer field for a Python enum.
    """
    def __init__(self, enum, **kwargs):
        self.enum = enum
        # Use the enum names for the choices
        super().__init__([v.name for v in enum], **kwargs)

    def to_internal_value(self, data):
        if data is None and self.allow_none:
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


class LinksField(fields.ReadOnlyField):
    """
    Field class for a links field for an object.
    """
    def __init__(self, **kwargs):
        self.basename = kwargs.pop('basename')
        self.related_object_links = kwargs.pop('related_object_links', [])
        self.related_list_links = kwargs.pop('related_list_links', [])
        self.action_links = kwargs.pop('action_links', [])
        kwargs.update(source = '*', read_only = True)
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
        links.update({
            name: reverse(
                view_name,
                kwargs = dict(pk = getattr(value, attr)),
                request = request,
                format = format
            )
            for name, view_name, attr in self.related_object_links
        })
        # Add the related list links
        links.update({
            name: reverse(
                view_name,
                kwargs = { self.basename + '_pk': value.pk },
                request = request,
                format = format
            )
            for name, view_name in self.related_list_links
        })
        # Add links to the additional actions
        for action in self.action_links:
            try:
                links.update({
                    action: reverse(
                        "{}-{}".format(self.basename, action),
                        kwargs = dict(pk = value.pk),
                        request = request,
                        format = format
                    )
                })
            except NoReverseMatch:
                pass
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
        # Get the set of all view names
        view_names = set(
            key
            for key in get_resolver('jasmin_manage.urls').reverse_dict.keys()
            if isinstance(key, str)
        )
        # Calculate the list of foreign key fields and reverse foreign key relations
        # for which links should be added
        related_object_links = []
        related_list_links = []
        for field in model_class._meta.get_fields():
            if field.many_to_one or field.one_to_one:
                view_name = "{}-detail".format(field.related_model._meta.object_name.lower())
                if view_name in view_names:
                    related_object_links.append((field.name, view_name, field.get_attname()))
            elif field.one_to_many or field.many_to_many:
                # If the field has a related name, use that, otherwise use the field name
                field_name = getattr(field, 'related_name', None) or field.name
                view_name = "{}-{}-list".format(basename, field_name)
                if view_name in view_names:
                    related_list_links.append((field_name, view_name))
        # Get the names of all the views that are for actions
        actions = set()
        #     key[len(basename) + 1:]
        #     for key in get_resolver('jasmin_manage.urls').reverse_dict.keys()
        #     if isinstance(key, str) and key.startswith(basename + '-')
        # )
        # Remove the list and detail views
        action_links = actions - {'list', 'detail'}
        # Pass the basename and extra links to the field constructor
        return (
            self.serializer_links_field,
            dict(
                basename = basename,
                related_object_links = related_object_links,
                related_list_links = related_list_links,
                action_links = action_links
            )
        )

    def build_field(self, field_name, info, model_class, nested_depth):
        if field_name == self.links_field_name:
            return self.build_links_field(field_name, model_class)
        else:
            return super().build_field(field_name, info, model_class, nested_depth)

    def get_fields(self):
        fields = super().get_fields()
        # Apply read_only_fields even when the field classes are explicitly defined
        for field_name in getattr(self.Meta, 'read_only_fields', []):
            fields[field_name].read_only = True
        # Set read_only on fields that should not be written for the current request
        request = self.context.get('request')
        # If there is no request, there is nothing more to do
        if not request:
            return fields
        # For POST requests, make the update-only fields read-only
        if request.method == 'POST':
            for field_name in getattr(self.Meta, 'update_only_fields', []):
                fields[field_name].read_only = True
        # For PUT or PATCH requests, make the create-only fields read-only
        elif request.method in {'PUT', 'PATCH'}:
            for field_name in getattr(self.Meta, 'create_only_fields', []):
                fields[field_name].read_only = True
        return fields

    def validate(self, data):
        data = super().validate(data)
        # Don't modify self.instance as it is not supposed to be mutated until save is called
        # Instead, we make a copy to run validation against
        if self.instance:
            instance = copy.copy(self.instance)
            for attr, value in data.items():
                setattr(instance, attr, value)
        else:
            instance = self.Meta.model(**data)
        # Run the model clean as a default validation
        instance.full_clean()
        return data
