from datetime import date
from types import SimpleNamespace

from dateutil.relativedelta import relativedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework.test import APIRequestFactory

from ...models import Category, Consortium, Project, Requirement, Resource
from ...serializers import RequirementSerializer


class RequirementSerializerTestCase(TestCase):
    """
    Tests for the requirement serializer.
    """
    @classmethod
    def setUpTestData(cls):
        cls.resource = Resource.objects.create(name = 'Resource 1')
        cls.category = Category.objects.create(name = 'Category 1')
        cls.category.resources.add(cls.resource)
        cls.consortium = Consortium.objects.create(
            name = 'Consortium 1',
            description = 'some description',
            manager = get_user_model().objects.create_user('manager1')
        )
        cls.owner = get_user_model().objects.create_user('owner1')
        cls.project = cls.consortium.projects.create(
            name = 'Project 1',
            description = 'some description',
            owner = cls.owner
        )
        cls.service = cls.project.services.create(name = 'service1', category = cls.category, location = 'TBC')

    def test_renders_instance_correctly(self):
        """
        Tests that the serializer renders an existing instance correctly.
        """
        requirement = self.service.requirements.create(
            resource = self.resource,
            status = Requirement.Status.AWAITING_PROVISIONING,
            amount = 100
        )
        # In order to render the links correctly, there must be a request in the context
        request = APIRequestFactory().post('/requirements/{}/'.format(requirement.pk))
        serializer = RequirementSerializer(requirement, context = dict(request = request))
        # Check that the right keys are present
        self.assertCountEqual(
            serializer.data.keys(),
            {
                'id',
                'service',
                'resource',
                'status',
                'amount',
                'start_date',
                'end_date',
                'created_at',
                'location',
                '_links'
            }
        )
        # Check the the values are correct
        # Don't explicitly check the links field - it has tests
        self.assertEqual(serializer.data['id'], requirement.pk)
        self.assertEqual(serializer.data['service'], self.service.pk)
        self.assertEqual(serializer.data['resource'], self.resource.pk)
        self.assertEqual(serializer.data['status'], Requirement.Status.AWAITING_PROVISIONING.name)
        self.assertEqual(serializer.data['amount'], requirement.amount)
        self.assertEqual(serializer.data['location'], requirement.location)
        start_date = date.today()
        self.assertEqual(serializer.data['start_date'], start_date.strftime("%Y-%m-%d"))
        end_date = date.today() + relativedelta(years = 5)
        self.assertEqual(serializer.data['end_date'], end_date.strftime("%Y-%m-%d"))

    def test_create_enforces_required_fields(self):
        """
        Tests that the required fields are enforced on create.
        """
        serializer = RequirementSerializer(data = {})
        self.assertFalse(serializer.is_valid())
        required_fields = {'resource', 'amount'}
        self.assertCountEqual(serializer.errors.keys(), required_fields)
        for name in required_fields:
            self.assertEqual(serializer.errors[name][0].code, 'required')

    def test_create_uses_service_from_context(self):
        """
        Tests that creating a requirement uses the service from the context.
        """
        serializer = RequirementSerializer(
            data = dict(resource = self.resource.pk, amount = 1000),
            context = dict(service = self.service)
        )
        self.assertTrue(serializer.is_valid())
        requirement = serializer.save()
        requirement.refresh_from_db()
        self.assertEqual(requirement.service.pk, self.service.pk)
        self.assertEqual(requirement.resource.pk, self.resource.pk)
        self.assertEqual(requirement.status, Requirement.Status.REQUESTED)
        self.assertEqual(requirement.amount, 1000)
        self.assertEqual(requirement.start_date, date.today())
        self.assertEqual(requirement.end_date, date.today() + relativedelta(years = 5))

    def test_cannot_create_with_negative_amount(self):
        """
        Tests that a requirement cannot be created with a negative amount.
        """
        serializer = RequirementSerializer(
            data = dict(resource = self.resource.pk, amount = -100),
            context = dict(service = self.service)
        )
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {'amount'})
        self.assertEqual(serializer.errors['amount'][0].code, 'min_value')

    def test_create_with_non_default_start_and_end_date(self):
        """
        Tests that a requirement can be created with non-default start and end dates.
        """
        start_date = date.today() + relativedelta(months = 3)
        end_date = start_date + relativedelta(months = 1)
        serializer = RequirementSerializer(
            data = dict(
                resource = self.resource.pk,
                amount = 1000,
                start_date = start_date.strftime("%Y-%m-%d"),
                end_date = end_date.strftime("%Y-%m-%d")
            ),
            context = dict(service = self.service)
        )
        self.assertTrue(serializer.is_valid())
        requirement = serializer.save()
        requirement.refresh_from_db()
        self.assertEqual(requirement.start_date, start_date)
        self.assertEqual(requirement.end_date, end_date)

    def test_cannot_override_service_on_create(self):
        """
        Tests that the service cannot be set directly when creating.
        """
        # Make another valid service that we will attempt to set as the service via data
        service = self.project.services.create(name = 'service2', category = self.category)
        serializer = RequirementSerializer(
            data = dict(
                service = service.pk,
                resource = self.resource.pk,
                amount = 1000
            ),
            # Pass the original service as the context - this should be the service for the
            # resulting requirement
            context = dict(service = self.service)
        )
        # The serializer should be valid - the service should just be ignored
        self.assertTrue(serializer.is_valid())
        requirement = serializer.save()
        requirement.refresh_from_db()
        self.assertEqual(requirement.service.pk, self.service.pk)
        self.assertNotEqual(requirement.service.pk, service.pk)

    def test_cannot_override_status_on_create(self):
        """
        Tests that the status cannot be set directly when creating.
        """
        serializer = RequirementSerializer(
            data = dict(
                resource = self.resource.pk,
                amount = 1000,
                # Specify a status other than REQUESTED
                status = Requirement.Status.PROVISIONED
            ),
            context = dict(service = self.service)
        )
        # The serializer should be valid - the status should just be ignored
        self.assertTrue(serializer.is_valid())
        requirement = serializer.save()
        requirement.refresh_from_db()
        self.assertEqual(requirement.status, Requirement.Status.REQUESTED)

    def test_cannot_create_with_resource_not_in_category(self):
        """
        Tests that the resource must be in the category for the service.
        """
        # Make another resource to use
        resource = Resource.objects.create(name = 'Resource 2')
        serializer = RequirementSerializer(
            data = dict(resource = resource.pk, amount = 1000),
            context = dict(service = self.service)
        )
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {'resource'})
        self.assertEqual(serializer.errors['resource'][0].code, 'does_not_exist')

    def test_cannot_create_with_start_date_in_past(self):
        """
        Tests that the start date must be in the future when creating.
        """
        start_date = date.today() - relativedelta(weeks = 2)
        serializer = RequirementSerializer(
            data = dict(
                resource = self.resource.pk,
                amount = 1000,
                start_date = start_date.strftime("%Y-%m-%d")
            ),
            context = dict(service = self.service)
        )
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {'start_date'})
        self.assertEqual(serializer.errors['start_date'][0].code, 'date_in_past')

    def test_cannot_create_with_end_date_before_start_date(self):
        """
        Tests that the end date must be after the start date when creating.
        """
        # Test with just a start date that is after the default end date
        start_date = date.today() + relativedelta(years = 5, weeks = 2)
        serializer = RequirementSerializer(
            data = dict(
                resource = self.resource.pk,
                amount = 1000,
                start_date = start_date.strftime("%Y-%m-%d")
            ),
            context = dict(service = self.service)
        )
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {'end_date'})
        self.assertEqual(serializer.errors['end_date'][0].code, 'before_start_date')

        # Test with just an end date that is before the default start date
        end_date = date.today() - relativedelta(weeks = 2)
        serializer = RequirementSerializer(
            data = dict(
                resource = self.resource.pk,
                amount = 1000,
                end_date = end_date.strftime("%Y-%m-%d")
            ),
            context = dict(service = self.service)
        )
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {'end_date'})
        self.assertEqual(serializer.errors['end_date'][0].code, 'before_start_date')

        # Test with a start and an end date where the end date is before
        start_date = date.today() + relativedelta(months = 6)
        end_date = start_date - relativedelta(weeks = 2)
        serializer = RequirementSerializer(
            data = dict(
                resource = self.resource.pk,
                amount = 1000,
                start_date = start_date.strftime("%Y-%m-%d"),
                end_date = end_date.strftime("%Y-%m-%d")
            ),
            context = dict(service = self.service)
        )
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {'end_date'})
        self.assertEqual(serializer.errors['end_date'][0].code, 'before_start_date')

    def test_update_amount(self):
        """
        Tests that the amount can be updated without updating the dates, even if the
        start date is in the past.
        """
        # Make a requirement with a start date in the past for testing
        start_date = date.today() - relativedelta(months = 3)
        requirement = self.service.requirements.create(
            resource = self.resource,
            status = Requirement.Status.AWAITING_PROVISIONING,
            amount = 100,
            start_date = start_date
        )
        serializer = RequirementSerializer(requirement, data = dict(amount = 120), partial = True)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        requirement.refresh_from_db()
        self.assertEqual(requirement.amount, 120)
        self.assertEqual(requirement.start_date, start_date)

    def test_update_start_and_end_dates(self):
        """
        Tests that the start and end dates can be updated.
        """
        requirement = self.service.requirements.create(
            resource = self.resource,
            status = Requirement.Status.AWAITING_PROVISIONING,
            amount = 100
        )
        start_date = date.today() + relativedelta(weeks = 2)
        end_date = start_date + relativedelta(years = 2)
        serializer = RequirementSerializer(
            requirement,
            data = dict(start_date = start_date, end_date = end_date),
            partial = True
        )
        self.assertTrue(serializer.is_valid())
        serializer.save()
        requirement.refresh_from_db()
        self.assertEqual(requirement.amount, 100)
        self.assertEqual(requirement.start_date, start_date)
        self.assertEqual(requirement.end_date, end_date)

    def test_cannot_update_service(self):
        """
        Tests that the service cannot be updated.
        """
        # Make a pre-existing requirement
        requirement = self.service.requirements.create(
            resource = self.resource,
            status = Requirement.Status.AWAITING_PROVISIONING,
            amount = 100
        )
        # Make another valid service to attempt to update to
        service = self.project.services.create(name = 'service2', category = self.category)
        serializer = RequirementSerializer(
            requirement,
            data = dict(service = service.pk),
            partial = True
        )
        # The serializer should validate but the service should be ignored
        self.assertTrue(serializer.is_valid())
        serializer.save()
        requirement.refresh_from_db()
        self.assertEqual(requirement.service.pk, self.service.pk)
        self.assertNotEqual(requirement.service.pk, service.pk)

    def test_cannot_update_resource(self):
        """
        Tests that the resource cannot be updated.
        """
        # Make a pre-existing requirement
        requirement = self.service.requirements.create(
            resource = self.resource,
            status = Requirement.Status.AWAITING_PROVISIONING,
            amount = 100
        )
        # Make another valid resource to attempt to update to
        resource = Resource.objects.create(name = 'Resource 2')
        serializer = RequirementSerializer(
            requirement,
            data = dict(resource = resource.pk),
            partial = True
        )
        # The serializer should validate but the service should be ignored
        self.assertTrue(serializer.is_valid())
        serializer.save()
        requirement.refresh_from_db()
        self.assertEqual(requirement.resource.pk, self.resource.pk)
        self.assertNotEqual(requirement.resource.pk, resource.pk)

    def test_cannot_update_status(self):
        """
        Tests that the status cannot be directly updated.
        """
        # Make a pre-existing requirement
        requirement = self.service.requirements.create(
            resource = self.resource,
            status = Requirement.Status.AWAITING_PROVISIONING,
            amount = 100
        )
        serializer = RequirementSerializer(
            requirement,
            data = dict(status = Requirement.Status.PROVISIONED.name),
            partial = True
        )
        # The serializer should validate but the status should be ignored
        self.assertTrue(serializer.is_valid())
        serializer.save()
        requirement.refresh_from_db()
        self.assertEqual(requirement.status, Requirement.Status.AWAITING_PROVISIONING)

    def test_cannot_update_with_negative_amount(self):
        """
        Tests that a requirement cannot be updated with a negative amount.
        """
        # Make a pre-existing requirement
        requirement = self.service.requirements.create(
            resource = self.resource,
            status = Requirement.Status.AWAITING_PROVISIONING,
            amount = 100
        )
        serializer = RequirementSerializer(
            requirement,
            data = dict(amount = -100),
            partial = True
        )
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {'amount'})
        self.assertEqual(serializer.errors['amount'][0].code, 'min_value')

    def test_cannot_update_with_start_date_in_past(self):
        """
        Tests that the start date cannot be updated to a date in the past.
        """
        # Make a pre-existing requirement whose start date is in the past
        requirement = self.service.requirements.create(
            resource = self.resource,
            status = Requirement.Status.AWAITING_PROVISIONING,
            amount = 100,
            start_date = date.today() - relativedelta(months = 6)
        )
        # Check that if updating the start date, it must be in the future
        start_date = date.today() - relativedelta(weeks = 2)
        serializer = RequirementSerializer(
            requirement,
            data = dict(start_date = start_date.strftime("%Y-%m-%d")),
            partial = True
        )
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {'start_date'})
        self.assertEqual(serializer.errors['start_date'][0].code, 'date_in_past')

    def test_cannot_update_with_end_date_before_start_date(self):
        """
        Tests that the end date cannot be updated to a date that is before the
        start date, even if the start date does not change.
        """
        # Make a pre-existing requirement
        requirement = self.service.requirements.create(
            resource = self.resource,
            status = Requirement.Status.AWAITING_PROVISIONING,
            amount = 100,
        )
        # Test with just a start date that is after the requirement's end date
        start_date = date.today() + relativedelta(years = 5, weeks = 2)
        serializer = RequirementSerializer(
            requirement,
            data = dict(start_date = start_date.strftime("%Y-%m-%d")),
            partial = True
        )
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {'end_date'})
        self.assertEqual(serializer.errors['end_date'][0].code, 'before_start_date')

        # Test with just an end date that is before the requirement's start date
        end_date = date.today() - relativedelta(weeks = 2)
        serializer = RequirementSerializer(
            requirement,
            data = dict(end_date = end_date.strftime("%Y-%m-%d")),
            partial = True
        )
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {'end_date'})
        self.assertEqual(serializer.errors['end_date'][0].code, 'before_start_date')

        # Test with a start and an end date where the end date is before
        start_date = date.today() + relativedelta(months = 6)
        end_date = start_date - relativedelta(weeks = 2)
        serializer = RequirementSerializer(
            requirement,
            data = dict(
                start_date = start_date.strftime("%Y-%m-%d"),
                end_date = end_date.strftime("%Y-%m-%d")
            ),
            partial = True
        )
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {'end_date'})
        self.assertEqual(serializer.errors['end_date'][0].code, 'before_start_date')
