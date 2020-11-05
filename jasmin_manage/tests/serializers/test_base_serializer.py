from django.test import TestCase

from rest_framework import serializers

from ...models import Project
from ...serializers.base import BaseSerializer


class BaseSerializerTestCase(TestCase):
    """
    Tests for the base serializer.
    """
    def test_read_only_fields(self):
        # Test that read_only_fields is respected even when fields are explicitly defined
        read_only_fields = ('status', 'consortium', 'extra_ro_field')
        serializer_class = type(
            'ProjectSerializer',
            (BaseSerializer, ),
            {
                'Meta': type(
                    'Meta',
                    (),
                    {
                        'model': Project,
                        'fields': (
                            'name',
                            'description',
                            'status',
                            'consortium',
                            'extra_ro_field',
                            'extra_rw_field',
                        ),
                        'read_only_fields': read_only_fields,
                    },
                ),
                'extra_ro_field': serializers.CharField(),
                'extra_rw_field': serializers.CharField(),
            }
        )
        for field_name, field in serializer_class().get_fields().items():
            self.assertEqual(field.read_only, field_name in read_only_fields)

    def test_create_only_fields(self):
        # Test that create_only_fields are writable for POST requests and read-only for PUT/PATCH
        create_only_fields = ('status', 'consortium')
        serializer_class = type(
            'ProjectSerializer',
            (BaseSerializer, ),
            {
                'Meta': type(
                    'Meta',
                    (),
                    {
                        'model': Project,
                        'fields': (
                            'name',
                            'description',
                            'status',
                            'consortium',
                        ),
                        'create_only_fields': create_only_fields,
                    },
                ),
            }
        )
        # If no instance is given, the fields should be writable
        serializer = serializer_class()
        for field_name, field in serializer.get_fields().items():
            self.assertFalse(field.read_only)
        # If an instance is given, the create-only fields should be read-only
        serializer = serializer_class(Project(name = 'Project 1'))
        for field_name, field in serializer.get_fields().items():
            self.assertEqual(field.read_only, field_name in create_only_fields)

    def test_update_only_fields(self):
        # Test that create_only_fields are writable for PUT requests and read-only for POST
        update_only_fields = ('status', 'consortium')
        serializer_class = type(
            'ProjectSerializer',
            (BaseSerializer, ),
            {
                'Meta': type(
                    'Meta',
                    (),
                    {
                        'model': Project,
                        'fields': (
                            'name',
                            'description',
                            'status',
                            'consortium',
                        ),
                        'update_only_fields': update_only_fields,
                    },
                ),
            }
        )
        # If no instance is given, the update-only fields should be read-only
        serializer = serializer_class()
        for field_name, field in serializer.get_fields().items():
            self.assertEqual(field.read_only, field_name in update_only_fields)
        # If an instance is given, the update-only fields should be writable
        serializer = serializer_class(Project(name = 'Project 1'))
        for field_name, field in serializer.get_fields().items():
            self.assertFalse(field.read_only)
