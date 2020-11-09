import random

from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework import mixins, status, viewsets

from ...models import Category, Resource
from ...serializers import CategorySerializer, ResourceSerializer

from .utils import ViewSetAssertionsMixin


class CategoryViewSetTestCase(ViewSetAssertionsMixin, APITestCase):
    """
    Tests for the category viewset.
    """
    @classmethod
    def setUpTestData(cls):
        """
        Create some test categories and resources.
        """
        # Create 20 resources
        resources = [
            Resource.objects.create(name = f'Resource {i}')
            for i in range(20)
        ]
        # Create 10 categories
        categories = [
            Category.objects.create(name = f'Category {i}')
            for i in range(10)
        ]
        # Attach up to 5 random resources to each category
        for category in categories:
            num_resources = random.randrange(5)
            category.resources.set(random.sample(resources, num_resources))

    def test_allowed_methods(self):
        """
        Tests that only safe methods are allowed for the list and detail endpoints.
        """
        self.assertAllowedMethods("/categories/", {'OPTIONS', 'HEAD', 'GET'})
        # Pick a random but valid category to use in the detail endpoint
        category = Category.objects.order_by('?').first()
        self.assertAllowedMethods(
            "/categories/{}/".format(category.pk),
            {'OPTIONS', 'HEAD', 'GET'}
        )

    def test_list_success(self):
        """
        Tests that a list response looks correct.
        """
        self.assertListResponseMatchesQuerySet(
            "/categories/",
            Category.objects.all(),
            CategorySerializer
        )

    def test_detail_success(self):
        """
        Tests that a detail response for a category looks correct.
        """
        category = Category.objects.order_by('?').first()
        self.assertDetailResponseMatchesInstance(
            "/categories/{}/".format(category.pk),
            category,
            CategorySerializer
        )

    def test_detail_missing(self):
        """
        Tests that the detail response for a non-existent category looks correct.
        """
        self.assertNotFound("/categories/20/")


class CategoryResourcesViewSetTestCase(ViewSetAssertionsMixin, APITestCase):
    """
    Tests for the category resources viewset.
    """
    @classmethod
    def setUpTestData(cls):
        """
        Create some test categories and resources.

        We want to make sure that we only return the resources for a particular category,
        so to do that we need multiple categories.
        """
        # Create 20 resources
        resources = [
            Resource.objects.create(name = f'Resource {i}')
            for i in range(20)
        ]
        # Create 10 categories
        categories = [
            Category.objects.create(name = f'Category {i}')
            for i in range(10)
        ]
        # Attach up to 5 random resources to each category
        for category in categories:
            num_resources = random.randrange(5)
            category.resources.set(random.sample(resources, num_resources))

    def test_allowed_methods(self):
        """
        Tests that only safe methods are allowed for the list endpoint.
        """
        # Pick a random but valid category to use in the endpoint
        category = Category.objects.order_by('?').first()
        self.assertAllowedMethods(
            "/categories/{}/resources/".format(category.pk),
            {'OPTIONS', 'HEAD', 'GET'}
        )

    def test_list_valid_category(self):
        """
        Tests that a list response for a valid category looks correct.
        """
        # Pick a random but valid category to use in the endpoint
        category = Category.objects.order_by('?').first()
        self.assertListResponseMatchesQuerySet(
            "/categories/{}/resources/".format(category.pk),
            category.resources.all(),
            ResourceSerializer
        )

    def test_list_invalid_category(self):
        """
        Tests that a list response for an invalid category correctly returns an empty list.
        """
        self.assertListResponseEmpty("/categories/20/resources/")
