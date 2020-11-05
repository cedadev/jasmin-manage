from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase

from ...models import ResourceChunk, Resource

from ..utils import AssertValidationErrorsMixin


class ResourceChunkModelTestCase(AssertValidationErrorsMixin, TestCase):
    """
    Tests for the resource chunk model.
    """
    @classmethod
    def setUpTestData(cls):
        cls.resource = Resource.objects.create(name = 'Resource 1')
        cls.resource.chunks.create(name = 'Chunk 1', amount = 1000)
        cls.resource.chunks.create(name = 'Chunk 2', amount = 1600)

    def test_unique_together(self):
        # Test that resource and name are unique together
        chunk = ResourceChunk(resource = self.resource, name = 'Chunk 1', amount = 500)
        # Test that model validation raises the correct error
        expected_errors = {
            '__all__': ['Resource chunk with this Resource and Name already exists.'],
        }
        with self.assertValidationErrors(expected_errors):
            chunk.full_clean()
        # Test that an integrity error is raised when saving
        with self.assertRaises(IntegrityError):
            chunk.save()

    def test_get_event_aggregates(self):
        chunk = ResourceChunk.objects.first()
        event_aggregates = chunk.get_event_aggregates()
        self.assertEqual(event_aggregates, (chunk.resource, ))

    def test_to_string(self):
        chunk = ResourceChunk.objects.first()
        self.assertEqual(str(chunk), 'Resource 1 / Chunk 1')

    def test_natural_key(self):
        chunk = ResourceChunk.objects.first()
        self.assertEqual(chunk.natural_key(), ('Resource 1', 'Chunk 1'))

    def test_get_by_natural_key(self):
        chunk = ResourceChunk.objects.get_by_natural_key('Resource 1', 'Chunk 1')
        self.assertEqual(chunk.pk, 1)
