import random

from ...models import Category, Resource
from ...serializers import CategorySerializer

from .utils import TestCase


class CategoryViewSetTestCase(TestCase):
    """
    Tests for the category viewset.
    """

    @classmethod
    def setUpTestData(cls):
        """
        Create some test categories and resources.
        """
        # Create 20 resources
        resources = [Resource.objects.create(name=f"Resource {i}") for i in range(20)]
        # Create 10 categories
        categories = [Category.objects.create(name=f"Category {i}") for i in range(10)]
        # Attach up to 5 random resources to each category
        for category in categories:
            num_resources = random.randrange(5)
            category.resources.set(random.sample(resources, num_resources))

    def test_list_allowed_methods(self):
        """
        Tests that only safe methods are allowed for the list endpoint.
        """
        self.authenticate()
        self.assertAllowedMethods("/categories/", {"OPTIONS", "HEAD", "GET"})

    def test_list_success(self):
        """
        Tests that a list response looks correct.
        """
        self.authenticate()
        self.assertListResponseMatchesQuerySet(
            "/categories/", Category.objects.all(), CategorySerializer
        )

    def test_list_unauthenticated(self):
        """
        Tests that the list endpoint requires an authenticated user.
        """
        self.assertUnauthorized("/categories/", "GET")

    def test_detail_allowed_methods(self):
        """
        Tests that only safe methods are allowed for the detail endpoint.
        """
        self.authenticate()
        # Pick a random but valid category to use in the detail endpoint
        category = Category.objects.order_by("?").first()
        self.assertAllowedMethods(
            "/categories/{}/".format(category.pk), {"OPTIONS", "HEAD", "GET"}
        )

    def test_detail_success(self):
        """
        Tests that a detail response for a category looks correct.
        """
        self.authenticate()
        category = Category.objects.order_by("?").first()
        self.assertDetailResponseMatchesInstance(
            "/categories/{}/".format(category.pk), category, CategorySerializer
        )

    def test_detail_missing(self):
        """
        Tests that the detail response for a non-existent category looks correct.
        """
        self.authenticate()
        self.assertNotFound("/categories/20/")

    def test_detail_unauthenticated(self):
        """
        Tests that the detail endpoint requires an authenticated user.
        """
        category = Category.objects.order_by("?").first()
        self.assertUnauthorized("/categories/{}/".format(category.pk), "GET")
