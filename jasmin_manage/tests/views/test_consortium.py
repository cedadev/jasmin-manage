import random

from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework import mixins, status, viewsets

from ...models import Consortium, Project, Quota, Resource
from ...serializers import ConsortiumSerializer, ProjectSerializer, QuotaSerializer

from .utils import TestCase


class ConsortiumViewSetTestCase(TestCase):
    """
    Tests for the consortium viewset.
    """
    @classmethod
    def setUpTestData(cls):
        """
        Create some test consortia.
        """
        for i in range(10):
            Consortium.objects.create(
                name = f'Consortium {i}',
                manager = get_user_model().objects.create_user(f'manager{i}')
            )

    def test_list_allowed_methods(self):
        """
        Tests that only safe methods are allowed for the list endpoint.
        """
        self.authenticate()
        self.assertAllowedMethods("/consortia/", {'OPTIONS', 'HEAD', 'GET'})

    def test_list_success(self):
        """
        Tests that a list response is successful for an authenticated user.
        """
        self.authenticate()
        self.assertListResponseMatchesQuerySet(
            "/consortia/",
            Consortium.objects.all(),
            ConsortiumSerializer
        )

    def test_list_unauthenticated(self):
        """
        Tests that the list endpoint returns unauthorized for an unauthenticated user.
        """
        self.assertUnauthorized("/consortia/", "GET")

    def test_detail_allowed_methods(self):
        """
        Tests that only safe methods are allowed for the detail endpoint.
        """
        self.authenticate()
        # Pick a random but valid consortium to use in the detail endpoint
        consortium = Consortium.objects.order_by('?').first()
        self.assertAllowedMethods(
            "/consortia/{}/".format(consortium.pk),
            {'OPTIONS', 'HEAD', 'GET'}
        )

    def test_detail_success(self):
        """
        Tests that a detail response for a consortium looks correct.
        """
        self.authenticate()
        consortium = Consortium.objects.order_by('?').first()
        self.assertDetailResponseMatchesInstance(
            "/consortia/{}/".format(consortium.pk),
            consortium,
            ConsortiumSerializer
        )

    def test_detail_unauthenticated(self):
        """
        Tests that the detail endpoint returns unauthorized for an unauthenticated user.
        """
        consortium = Consortium.objects.order_by('?').first()
        self.assertUnauthorized("/consortia/{}/".format(consortium.pk), "GET")

    def test_detail_missing(self):
        """
        Tests that the detail endpoint returns not found for an invalid consortium.
        """
        self.authenticate()
        self.assertNotFound("/consortia/100/")


class ConsortiumProjectsViewSetTestCase(TestCase):
    """
    Tests for the consortium projects viewset.
    """
    @classmethod
    def setUpTestData(cls):
        """
        Create some test consortia and projects.

        We want to make sure that we only return the projects for a particular consortium,
        so to do that we need multiple consortia.
        """
        consortia = [
            Consortium.objects.create(
                name = f'Consortium {i}',
                manager = get_user_model().objects.create_user(f'manager{i}')
            )
            for i in range(5)
        ]
        # Attach each project to a random consortium
        projects = [
            consortia[random.randrange(5)].projects.create(
                name = f'Project {i}',
                owner = get_user_model().objects.create_user(f'owner{i}')
            )
            for i in range(20)
        ]

    def test_list_allowed_methods(self):
        """
        Tests that only safe methods are allowed for the list endpoint.
        """
        # Pick a random but valid consortium to use in the endpoint
        consortium = Consortium.objects.order_by('?').first()
        # Authenticate as the consortium manager
        self.authenticateAsConsortiumManager(consortium)
        self.assertAllowedMethods(
            "/consortia/{}/projects/".format(consortium.pk),
            {'OPTIONS', 'HEAD', 'GET'}
        )

    def test_list_valid_consortium(self):
        """
        Tests that the consortium manager can successfully list the projects.
        """
        consortium = Consortium.objects.order_by('?').first()
        # Authenticate as the consortium manager
        self.authenticateAsConsortiumManager(consortium)
        self.assertListResponseMatchesQuerySet(
            "/consortia/{}/projects/".format(consortium.pk),
            consortium.projects.annotate_summary(consortium.manager),
            ProjectSerializer
        )

    def test_list_not_manager(self):
        """
        Tests that the list endpoint returns not found when an authenticated user who
        is not the consortium manager attempts to list projects for a valid consortium.
        """
        self.authenticate()
        consortium = Consortium.objects.order_by('?').first()
        self.assertNotFound("/consortia/{}/projects/".format(consortium.pk))

    def test_list_invalid_consortium(self):
        """
        Tests that the list endpoint returns not found when an authenticated user
        attempts to list project for an invalid consortium.
        """
        self.authenticate()
        self.assertNotFound("/consortia/100/projects/")

    def test_list_unauthenticated(self):
        """
        Tests that the list endpoint returns unauthorized when an unauthenticated user
        attempts to list projects.
        """
        consortium = Consortium.objects.order_by('?').first()
        self.assertUnauthorized("/consortia/{}/projects/".format(consortium.pk))


class ConsortiumQuotasViewSetTestCase(TestCase):
    """
    Tests for the consortium quotas viewset.
    """
    @classmethod
    def setUpTestData(cls):
        """
        Create some test consortia and quotas.

        We want to make sure that we only return the quotas for a particular consortium,
        so to do that we need multiple consortia.
        """
        consortia = [
            Consortium.objects.create(
                name = f'Consortium {i}',
                manager = get_user_model().objects.create_user(f'manager{i}')
            )
            for i in range(5)
        ]
        resources = [
            Resource.objects.create(name = f'Resource {i}')
            for i in range(10)
        ]
        # Create quotas for each combination of consortium and resource
        for consortium in consortia:
            for resource in resources:
                consortium.quotas.create(resource = resource, amount = random.randint(1, 1000))

    def test_list_allowed_methods(self):
        """
        Tests that only safe methods are allowed for the list endpoint.
        """
        # Pick a random but valid consortium to use in the endpoint
        consortium = Consortium.objects.order_by('?').first()
        # Authenticate as the consortium manager
        self.authenticateAsConsortiumManager(consortium)
        self.assertAllowedMethods(
            "/consortia/{}/quotas/".format(consortium.pk),
            {'OPTIONS', 'HEAD', 'GET'}
        )

    def test_list_valid_consortium(self):
        """
        Tests that the consortium manager can list the consortium quotas.
        """
        # Pick a random but valid consortium to use in the endpoint
        consortium = Consortium.objects.order_by('?').first()
        # Authenticate as the consortium manager
        self.authenticateAsConsortiumManager(consortium)
        self.assertListResponseMatchesQuerySet(
            "/consortia/{}/quotas/".format(consortium.pk),
            consortium.quotas.all(),
            QuotaSerializer
        )

    def test_list_not_manager(self):
        """
        Tests that the list endpoint returns not found when an authenticated user who
        is not the consortium manager attempts to list quotas for a valid consortium.
        """
        self.authenticate()
        consortium = Consortium.objects.order_by('?').first()
        self.assertNotFound("/consortia/{}/quotas/".format(consortium.pk))

    def test_list_invalid_consortium(self):
        """
        Tests that the list endpoint returns not found when an authenticated user
        attempts to list quotas for an invalid consortium.
        """
        self.authenticate()
        self.assertNotFound("/consortia/100/quotas/")

    def test_list_unauthenticated(self):
        """
        Tests that the list endpoint returns unauthorized when an unauthenticated user
        attempts to list quotas.
        """
        consortium = Consortium.objects.order_by('?').first()
        self.assertUnauthorized("/consortia/{}/quotas/".format(consortium.pk))
