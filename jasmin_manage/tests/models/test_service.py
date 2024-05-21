from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase

from ...models import Category, Consortium, Project, Service
from ..utils import AssertValidationErrorsMixin


class ServiceModelTestCase(AssertValidationErrorsMixin, TestCase):
    """
    Tests for the service model.
    """

    @classmethod
    def setUpTestData(cls):
        cls.consortium = Consortium.objects.create(
            name="Consortium 1",
            description="some description",
            manager=get_user_model().objects.create_user("manager1"),
        )
        cls.project = cls.consortium.projects.create(
            name="Project 1",
            description="some description",
            owner=get_user_model().objects.create_user("owner1"),
        )
        cls.category = Category.objects.create(name="Category 1")
        cls.category.services.create(name="service1", project=cls.project)

    def test_unique_together(self):
        # Test that category and name are unique together
        project = self.consortium.projects.create(
            name="Project 2",
            description="some description",
            owner=get_user_model().objects.create_user("owner2"),
        )
        service = Service(category=self.category, project=project, name="service1")
        # Test that model validation raises the correct error
        expected_errors = {
            "__all__": ["Service with this Category and Name already exists."],
        }
        with self.assertValidationErrors(expected_errors):
            service.full_clean()
        # Test that an integrity error is raised when saving
        with self.assertRaises(IntegrityError):
            service.save()

    def test_name_validation(self):
        service = Service(category=self.category, project=self.project)
        # First, try names that should pass
        service.name = "serv-1-with-hyphens"
        service.full_clean()
        service.name = "serv_2_w_underscores"
        service.full_clean()
        # Now try some names that should fail
        expected_errors = {
            "name": [
                "Service name must start with a letter and contain "
                "lower-case letters, numbers, underscores and hyphens only."
            ]
        }
        service.name = "1-serv-start-w-num"
        with self.assertValidationErrors(expected_errors):
            service.full_clean()
        service.name = "service_WITH_CAPS"
        with self.assertValidationErrors(expected_errors):
            service.full_clean()
        service.name = "serv with    white"
        with self.assertValidationErrors(expected_errors):
            service.full_clean()
        service.name = "serv@w#spec&chars"
        with self.assertValidationErrors(expected_errors):
            service.full_clean()
        service.name = "serv-w-uñíçôdè-char"
        with self.assertValidationErrors(expected_errors):
            service.full_clean()

        expected_errors_long = {
            "name": ["Ensure this value has at most 20 characters (it has 26)."]
        }
        service.name = "service-name-is-toooo-long"
        with self.assertValidationErrors(expected_errors_long):
            service.full_clean()

    def test_get_event_aggregates(self):
        service = Service.objects.first()
        event_aggregates = service.get_event_aggregates()
        self.assertEqual(event_aggregates, (service.category, service.project))

    def test_to_string(self):
        service = Service.objects.first()
        self.assertEqual(str(service), "Category 1 / service1")

    def test_natural_key(self):
        service = Service.objects.first()
        self.assertEqual(service.natural_key(), ("Category 1", "service1"))

    def test_get_by_natural_key(self):
        service = Service.objects.get_by_natural_key("Category 1", "service1")
        self.assertEqual(service.pk, 1)
