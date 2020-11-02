from datetime import date

from dateutil.relativedelta import relativedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from ...models import Category, Consortium, Requirement, Resource

from .utils import AssertValidationErrorsMixin


class RequirementModelTestCase(AssertValidationErrorsMixin, TestCase):
    """
    Tests for the requirement model.
    """
    @classmethod
    def setUpTestData(cls):
        UserModel = get_user_model()
        cls.resource = Resource.objects.create(name = 'Resource 1')
        cls.category = Category.objects.create(name = 'Category 1')
        cls.category.resources.add(cls.resource)
        cls.consortium = Consortium.objects.create(
            name = 'Consortium 1',
            description = 'some description',
            manager = UserModel.objects.create_user('manager1')
        )
        cls.project = cls.consortium.projects.create(
            name = 'Project 1',
            description = 'some description',
            owner = UserModel.objects.create_user('owner1')
        )
        cls.service = cls.project.services.create(name = 'service1', category = cls.category)
        cls.service.requirements.create(resource = cls.resource, amount = 20)

    def test_default_start_and_end_dates(self):
        requirement = Requirement.objects.first()
        today = date.today()
        self.assertEqual(requirement.start_date, today)
        self.assertEqual(requirement.end_date, today + relativedelta(years = 5))

    def test_get_event_type(self):
        requirement = Requirement.objects.first()
        # If status is in diff, the event type should have the status in it
        diff = dict(status = Requirement.Status.AWAITING_PROVISIONING)
        event_type = requirement.get_event_type(diff)
        self.assertEqual(event_type, 'jasmin_manage.requirement.awaiting_provisioning')
        # If status is not in diff, the event type should be null
        diff = dict(amount = 100)
        self.assertIsNone(requirement.get_event_type(diff))

    def test_get_event_aggregates(self):
        requirement = Requirement.objects.first()
        self.assertEqual(
            requirement.get_event_aggregates(),
            (requirement.service, requirement.resource)
        )

    def test_validates_resource_belongs_to_service_category(self):
        # Test that a valid model passes validation
        requirement = Requirement(service = self.service, resource = self.resource, amount = 10)
        requirement.full_clean()
        # Test that an invalid resource fails validation on create
        requirement = Requirement(
            service = self.service,
            resource = Resource.objects.create(name = 'Resource 2'),
            amount = 10
        )
        with self.assertValidationErrors({'resource': ['Resource is not valid for the selected service.']}):
            requirement.full_clean()
        # Force the save anyway and test that the resource is allowed on update
        requirement.save()
        requirement.refresh_from_db()
        requirement.full_clean()
        # Test that updating the resource to another resource in the category succeeds
        requirement.resource = self.category.resources.create(name = 'Resource 3')
        requirement.full_clean()
        # Test that updating to another resource not in the category fails validation
        requirement.resource = Resource.objects.create(name = 'Resource 4')
        with self.assertValidationErrors({'resource': ['Resource is not valid for the selected service.']}):
            requirement.full_clean()

    def test_validates_start_date_before_end_date(self):
        requirement = Requirement(service = self.service, resource = self.resource, amount = 10)
        requirement.full_clean()
        requirement.end_date = date.today() - relativedelta(days = 1)
        with self.assertValidationErrors({'end_date': ['End date must be after start date.']}):
            requirement.full_clean()
