from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase

from ...models import Category, Consortium, Project, Service

from ..utils import AssertValidationErrorsMixin


class ResourceChunkModelTestCase(AssertValidationErrorsMixin, TestCase):
    """
    Tests for the resource chunk model.
    """
    @classmethod
    def setUpTestData(cls):
        cls.consortium = Consortium.objects.create(
            name = 'Consortium 1',
            description = 'some description',
            manager = get_user_model().objects.create_user('manager1')
        )
        cls.project = cls.consortium.projects.create(
            name = 'Project 1',
            description = 'some description',
            owner = get_user_model().objects.create_user('owner1')
        )
        cls.category = Category.objects.create(name = 'Category 1')
        cls.category.services.create(name = 'service1', project = cls.project)

    def test_unique_together(self):
        # Test that category and name are unique together
        project = self.consortium.projects.create(
            name = 'Project 2',
            description = 'some description',
            owner = get_user_model().objects.create_user('owner2')
        )
        service = Service(category = self.category, project = project, name = 'service1')
        # Test that model validation raises the correct error
        expected_errors = {
            '__all__': ['Service with this Category and Name already exists.'],
        }
        with self.assertValidationErrors(expected_errors):
            service.full_clean()
        # Test that an integrity error is raised when saving
        with self.assertRaises(IntegrityError):
            service.save()

    def test_name_validation(self):
        service = Service(category = self.category, project = self.project)
        # First, try names that should pass
        service.name = 'service-1-with-hyphens'
        service.full_clean()
        service.name = 'service_2_with_underscores'
        service.full_clean()
        service.name = 'service_WITH_CAPS'
        service.full_clean()
        # Now try some names that should fail
        service.name = 'service with    whitespace'
        expected_errors = {
            'name': ['Service name can only contain letters, numbers, underscores and hyphens.']
        }
        with self.assertValidationErrors(expected_errors):
            service.full_clean()
        service.name = 'service@with#special&chars'
        with self.assertValidationErrors(expected_errors):
            service.full_clean()
        service.name = 'service-with-uñíçôdè-characters'
        with self.assertValidationErrors(expected_errors):
            service.full_clean()

    def test_get_event_aggregates(self):
        service = Service.objects.first()
        event_aggregates = service.get_event_aggregates()
        self.assertEqual(event_aggregates, (service.category, service.project))

    def test_to_string(self):
        service = Service.objects.first()
        self.assertEqual(str(service), 'Category 1 / service1')

    def test_natural_key(self):
        service = Service.objects.first()
        self.assertEqual(service.natural_key(), ('Category 1', 'service1'))

    def test_get_by_natural_key(self):
        service = Service.objects.get_by_natural_key('Category 1', 'service1')
        self.assertEqual(service.pk, 1)
