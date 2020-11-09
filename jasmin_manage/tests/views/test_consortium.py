import random

from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework import mixins, status, viewsets

from ...models import Consortium, Project, Quota, Resource
from ...serializers import ConsortiumSerializer, ProjectSerializer, QuotaSerializer

from .utils import ViewSetAssertionsMixin


class ConsortiumViewSetTestCase(ViewSetAssertionsMixin, APITestCase):
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

    def test_allowed_methods(self):
        """
        Tests that only safe methods are allowed for the list and detail endpoints.
        """
        self.assertAllowedMethods("/consortia/", {'OPTIONS', 'HEAD', 'GET'})
        # Pick a random but valid consortium to use in the detail endpoint
        consortium = Consortium.objects.order_by('?').first()
        self.assertAllowedMethods(
            "/consortia/{}/".format(consortium.pk),
            {'OPTIONS', 'HEAD', 'GET'}
        )

    def test_list_success(self):
        """
        Tests that a list response looks correct.
        """
        self.assertListResponseMatchesQuerySet(
            "/consortia/",
            Consortium.objects.all(),
            ConsortiumSerializer
        )

    def test_detail_success(self):
        """
        Tests that a detail response for a consortium looks correct.
        """
        consortium = Consortium.objects.order_by('?').first()
        self.assertDetailResponseMatchesInstance(
            "/consortia/{}/".format(consortium.pk),
            consortium,
            ConsortiumSerializer
        )

    def test_detail_missing(self):
        """
        Tests that the detail response for a non-existent consortium looks correct.
        """
        self.assertNotFound("/consortia/20/")


class ConsortiumProjectsViewSetTestCase(ViewSetAssertionsMixin, APITestCase):
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

    def test_allowed_methods(self):
        """
        Tests that only safe methods are allowed for the list endpoint.
        """
        # Pick a random but valid consortium to use in the endpoint
        consortium = Consortium.objects.order_by('?').first()
        self.assertAllowedMethods(
            "/consortia/{}/projects/".format(consortium.pk),
            {'OPTIONS', 'HEAD', 'GET'}
        )

    def test_list_valid_category(self):
        """
        Tests that a list response for a valid category looks correct.
        """
        # Pick a random but valid category to use in the endpoint
        consortium = Consortium.objects.order_by('?').first()
        self.assertListResponseMatchesQuerySet(
            "/consortia/{}/projects/".format(consortium.pk),
            consortium.projects.all(),
            ProjectSerializer
        )

    def test_list_invalid_category(self):
        """
        Tests that a list response for an invalid category correctly returns an empty list.
        """
        self.assertListResponseEmpty("/consortia/20/projects/")


class ConsortiumQuotasViewSetTestCase(ViewSetAssertionsMixin, APITestCase):
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

    def test_allowed_methods(self):
        """
        Tests that only safe methods are allowed for the list endpoint.
        """
        # Pick a random but valid consortium to use in the endpoint
        consortium = Consortium.objects.order_by('?').first()
        self.assertAllowedMethods(
            "/consortia/{}/quotas/".format(consortium.pk),
            {'OPTIONS', 'HEAD', 'GET'}
        )

    def test_list_valid_category(self):
        """
        Tests that a list response for a valid category looks correct.
        """
        # Pick a random but valid category to use in the endpoint
        consortium = Consortium.objects.order_by('?').first()
        self.assertListResponseMatchesQuerySet(
            "/consortia/{}/quotas/".format(consortium.pk),
            consortium.quotas.all(),
            QuotaSerializer
        )

    def test_list_invalid_category(self):
        """
        Tests that a list response for an invalid category correctly returns an empty list.
        """
        self.assertListResponseEmpty("/consortia/20/quotas/")
