from datetime import date
import random

from dateutil.relativedelta import relativedelta

from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework import mixins, status, viewsets

from ...models import (
    Category,
    Collaborator,
    Consortium,
    Project,
    Requirement,
    Resource,
    Service
)
from ...serializers import RequirementSerializer, ServiceSerializer

from .utils import ViewSetAssertionsMixin


class ServiceViewSetTestCase(ViewSetAssertionsMixin, APITestCase):
    """
    Tests for the project viewset.
    """
    @classmethod
    def setUpTestData(cls):
        # Create 5 categories
        cls.categories = [
            Category.objects.create(name = f'Category {i}')
            for i in range(5)
        ]
        consortium = Consortium.objects.create(
            name = 'Consortium 1',
            manager = get_user_model().objects.create_user('manager1')
        )
        # Create 10 projects
        cls.projects = [
            consortium.projects.create(
                name = f'Project {i}',
                description = 'some description',
                owner = get_user_model().objects.create_user(f'owner{i}')
            )
            for i in range(10)
        ]

    def setUp(self):
        # For each project, create a between 1 and 3 services with different categories
        Service.objects.bulk_create([
            Service(
                project = project,
                category = category,
                name = f'project{i}service{j}'
            )
            for j, category in enumerate(random.sample(self.categories, random.randint(1, 3)))
            for i, project in enumerate(self.projects)
        ])

    def test_allowed_methods(self):
        """
        Tests that the correct methods are permitted by the detail endpoint.
        """
        service = Service.objects.order_by('?').first()
        self.assertAllowedMethods(
            "/services/{}/".format(service.pk),
            # Services cannot be updated via the API
            {'OPTIONS', 'HEAD', 'GET', 'DELETE'}
        )

    def test_list_not_found(self):
        """
        Services can only be listed via a project, so check that the list endpoint is not found.
        """
        self.assertNotFound("/services/")

    def test_detail_not_collaborator(self):
        """
        Tests that the detail endpoint successfully retrieves a service.
        """
        service = Service.objects.order_by('?').first()
        self.assertDetailResponseMatchesInstance(
            "/services/{}/".format(service.pk),
            service,
            ServiceSerializer
        )

    def test_detail_missing(self):
        """
        Tests that the detail endpoint correctly reports not found for invalid project.
        """
        self.assertNotFound("/services/100/")

    def test_remove_service(self):
        """
        Tests that a service is correctly removed by the DELETE method.
        """
        service = Service.objects.order_by('?').first()
        self.assertDeleteResponseIsEmpty("/services/{}/".format(service.pk))
        # Test that the service was removed
        self.assertFalse(Service.objects.filter(pk = service.pk).exists())

    def test_cannot_remove_when_project_is_not_editable(self):
        """
        Tests that a service cannot be removed when the containing project is not editable.
        """
        service = Service.objects.order_by('?').first()
        for status in Project.Status:
            if status == Project.Status.EDITABLE:
                continue
            # Put the containing project into the current state
            service.project.status = status
            service.project.save()
            # Try to delete the service
            response_data = self.assertConflict(
                "/services/{}/".format(service.pk),
                "DELETE"
            )
            # Check that the error code is what we expected
            self.assertEqual(response_data['code'], 'invalid_status')
            # Check that the service still exists in the DB
            self.assertTrue(Service.objects.filter(pk = service.pk).exists())

    def test_cannot_remove_with_requirements(self):
        """
        Tests that a service cannot be removed if it has requirements.
        """
        service = Service.objects.order_by('?').first()
        service.requirements.create(
            resource = Resource.objects.create(name = 'Resource 1'),
            amount = 1000
        )
        # Try to delete the service
        response_data = self.assertConflict(
            "/services/{}/".format(service.pk),
            "DELETE"
        )
        # Check that the error code is what we expected
        self.assertEqual(response_data['code'], 'has_requirements')
        # Check that the service still exists in the DB
        self.assertTrue(Service.objects.filter(pk = service.pk).exists())


class ServiceRequirementsViewSetTestCase(ViewSetAssertionsMixin, APITestCase):
    """
    Tests for the service requirements viewset.
    """
    @classmethod
    def setUpTestData(cls):
        resources = [
            Resource.objects.create(name = f'Resource {i}')
            for i in range(10)
        ]
        categories = []
        for i in range(5):
            category = Category.objects.create(name = f'Category {i}')
            categories.append(category)
            # Add between 1 and 5 resources to each category
            category.resources.set(random.sample(resources, random.randint(1, 5)))
        consortium = Consortium.objects.create(
            name = 'Consortium 1',
            manager = get_user_model().objects.create_user('manager1')
        )
        projects = [
            consortium.projects.create(
                name = f'Project {i}',
                description = 'some description',
                owner = get_user_model().objects.create_user(f'owner{i}')
            )
            for i in range(10)
        ]
        # For each project, create between 1 and 3 services with different categories
        services = [
            project.services.create(
                category = category,
                name = f'project{i}service{j}'
            )
            for j, category in enumerate(random.sample(categories, random.randint(1, 3)))
            for i, project in enumerate(projects)
        ]
        # For each service, create a requirement for each resource
        Requirement.objects.bulk_create([
            Requirement(
                service = service,
                resource = resource,
                amount = random.randint(1, 100)
            )
            for service in services
            for resource in service.category.resources.all()
        ])

    def test_allowed_methods(self):
        """
        Tests that the correct methods are permitted for the endpoint.
        """
        # Pick a random but valid service to use in the endpoint
        service = Service.objects.order_by('?').first()
        self.assertAllowedMethods(
            "/services/{}/requirements/".format(service.pk),
            {'OPTIONS', 'HEAD', 'GET', 'POST'}
        )

    def test_list_valid_service(self):
        """
        Tests that a list response for a valid service looks correct.
        """
        service = Service.objects.order_by('?').first()
        self.assertListResponseMatchesQuerySet(
            "/services/{}/requirements/".format(service.pk),
            service.requirements.all(),
            RequirementSerializer
        )

    def test_list_invalid_service(self):
        """
        Tests that a list response for an invalid service correctly returns an empty list.
        """
        self.assertListResponseEmpty("/services/1000/requirements/")

    def test_create_uses_service_from_url(self):
        """
        Tests that creating a requirement uses the service from the URL.
        """
        service = Service.objects.order_by('?').first()
        resource = service.category.resources.first()
        requirement = self.assertCreateResponseMatchesCreatedInstance(
            "/services/{}/requirements/".format(service.pk),
            dict(resource = resource.pk, amount = 1000),
            RequirementSerializer
        )
        self.assertEqual(requirement.service.pk, service.pk)
        self.assertEqual(requirement.resource.pk, resource.pk)
        self.assertEqual(requirement.status, Requirement.Status.REQUESTED)
        self.assertEqual(requirement.amount, 1000)
        self.assertEqual(requirement.start_date, date.today())
        self.assertEqual(requirement.end_date, date.today() + relativedelta(years = 5))

    def test_create_with_non_default_start_and_end_date(self):
        """
        Tests that a requirement can be created with non-default start and end dates.
        """
        service = Service.objects.order_by('?').first()
        resource = service.category.resources.first()
        start_date = date.today() + relativedelta(months = 3)
        end_date = start_date + relativedelta(months = 1)
        requirement = self.assertCreateResponseMatchesCreatedInstance(
            "/services/{}/requirements/".format(service.pk),
            dict(
                resource = resource.pk,
                amount = 1000,
                start_date = start_date,
                end_date = end_date
            ),
            RequirementSerializer
        )
        self.assertEqual(requirement.start_date, start_date)
        self.assertEqual(requirement.end_date, end_date)

    def test_create_enforces_required_fields(self):
        """
        Tests that the required fields are enforced on create.
        """
        service = Service.objects.order_by('?').first()
        response_data = self.assertCreateResponseIsBadRequest(
            "/services/{}/requirements/".format(service.pk),
            dict()
        )
        required_fields = {'resource', 'amount'}
        self.assertCountEqual(response_data.keys(), required_fields)
        for name in required_fields:
            self.assertEqual(response_data[name][0]['code'], 'required')

    def test_cannot_create_with_negative_amount(self):
        """
        Tests that a requirement cannot be created with a negative amount.
        """
        service = Service.objects.order_by('?').first()
        response_data = self.assertCreateResponseIsBadRequest(
            "/services/{}/requirements/".format(service.pk),
            dict(
                resource = service.category.resources.first().pk,
                amount = -100
            )
        )
        self.assertCountEqual(response_data.keys(), {'amount'})
        self.assertEqual(response_data['amount'][0]['code'], 'min_value')

    def test_cannot_override_service_on_create(self):
        """
        Tests that the service cannot be set directly when creating.
        """
        # Pick a service to use in the URL
        service = Service.objects.order_by('?').first()
        resource = service.category.resources.first()
        # Pick any other service to use
        other_service = Service.objects.exclude(pk = service.pk).order_by('?').first()
        # Make the requirement specifying one service in the URL and the other in the data
        requirement = self.assertCreateResponseMatchesCreatedInstance(
            "/services/{}/requirements/".format(service.pk),
            dict(
                service = other_service.pk,
                resource = resource.pk,
                amount = 1000
            ),
            RequirementSerializer
        )
        self.assertEqual(requirement.service.pk, service.pk)
        self.assertNotEqual(requirement.service.pk, other_service.pk)

    def test_cannot_override_status_on_create(self):
        """
        Tests that the status cannot be set directly when creating.
        """
        service = Service.objects.order_by('?').first()
        resource = service.category.resources.first()
        requirement = self.assertCreateResponseMatchesCreatedInstance(
            "/services/{}/requirements/".format(service.pk),
            dict(
                resource = resource.pk,
                amount = 1000,
                status = Requirement.Status.AWAITING_PROVISIONING
            ),
            RequirementSerializer
        )
        self.assertEqual(requirement.status, Requirement.Status.REQUESTED)

    def test_cannot_create_with_resource_not_in_category(self):
        """
        Tests that the resource must be in the category for the service.
        """
        service = Service.objects.order_by('?').first()
        # Select a resource that does not belong to the service's category
        resource = Resource.objects.exclude(category = service.category).order_by('?').first()
        response_data = self.assertCreateResponseIsBadRequest(
            "/services/{}/requirements/".format(service.pk),
            dict(resource = resource.pk, amount = 1000)
        )
        self.assertCountEqual(response_data.keys(), {'resource'})
        self.assertEqual(response_data['resource'][0]['code'], 'does_not_exist')

    def test_cannot_create_with_start_date_in_past(self):
        """
        Tests that the start date must be in the future when creating.
        """
        service = Service.objects.order_by('?').first()
        resource = service.category.resources.first()
        start_date = date.today() - relativedelta(weeks = 2)
        response_data = self.assertCreateResponseIsBadRequest(
            "/services/{}/requirements/".format(service.pk),
            dict(
                resource = resource.pk,
                amount = 1000,
                start_date = start_date
            )
        )
        self.assertCountEqual(response_data.keys(), {'start_date'})
        self.assertEqual(response_data['start_date'][0]['code'], 'date_in_past')

    def test_cannot_create_with_end_date_before_start_date(self):
        """
        Tests that the end date must be after the start date when creating.
        """
        service = Service.objects.order_by('?').first()
        resource = service.category.resources.first()

        # Test with just a start date that is after the default end date
        start_date = date.today() + relativedelta(years = 5, weeks = 2)
        response_data = self.assertCreateResponseIsBadRequest(
            "/services/{}/requirements/".format(service.pk),
            dict(resource = resource.pk, amount = 1000, start_date = start_date)
        )
        self.assertCountEqual(response_data.keys(), {'end_date'})
        self.assertEqual(response_data['end_date'][0]['code'], 'before_start_date')

        # Test with just an end date that is before the default start date
        end_date = date.today() - relativedelta(weeks = 2)
        response_data = self.assertCreateResponseIsBadRequest(
            "/services/{}/requirements/".format(service.pk),
            dict(resource = resource.pk, amount = 1000, end_date = end_date)
        )
        self.assertCountEqual(response_data.keys(), {'end_date'})
        self.assertEqual(response_data['end_date'][0]['code'], 'before_start_date')

        # Test with a start and an end date where the end date is before
        start_date = date.today() + relativedelta(months = 6)
        end_date = start_date - relativedelta(weeks = 2)
        response_data = self.assertCreateResponseIsBadRequest(
            "/services/{}/requirements/".format(service.pk),
            dict(resource = resource.pk, amount = 1000, start_date = start_date, end_date = end_date)
        )
        self.assertCountEqual(response_data.keys(), {'end_date'})
        self.assertEqual(response_data['end_date'][0]['code'], 'before_start_date')

    def test_create_only_permitted_for_status_editable(self):
        """
        Tests that requirements can only be created for an editable project.
        """
        service = Service.objects.order_by('?').first()
        resource = service.category.resources.first()
        num_requirements = service.requirements.count()
        for status in Project.Status:
            if status == Project.Status.EDITABLE:
                continue
            # Put the project into the given state
            service.project.status = status
            service.project.save()
            # Then check that it cannot be returned for changes
            response_data = self.assertConflict(
                "/services/{}/requirements/".format(service.pk),
                "POST"
            )
            # Check that the error code is what we expected
            self.assertEqual(response_data['code'], 'invalid_status')
            # Check that the number of requirements didn't change
            service.refresh_from_db()
            self.assertEqual(service.requirements.count(), num_requirements)
