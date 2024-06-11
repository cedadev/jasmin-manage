import random

from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework import mixins, status, viewsets

from ...models import Resource
from ...serializers import ResourceSerializer

from .utils import TestCase


class ResourceViewSetTestCase(TestCase):
    """
    Tests for the resource viewset.
    """

    @classmethod
    def setUpTestData(cls):
        for i in range(10):
            Resource.objects.create(name=f"Resource {i}")

    def test_list_allowed_methods(self):
        """
        Tests that only safe methods are allowed for the list endpoint.
        """
        self.authenticate()
        self.assertAllowedMethods("/resources/", {"OPTIONS", "HEAD", "GET"})

    def test_list_success(self):
        """
        Tests that a list response looks correct.
        """
        self.authenticate()
        self.assertListResponseMatchesQuerySet(
            "/resources/", Resource.objects.all(), ResourceSerializer
        )

    def test_list_unauthenticated(self):
        """
        Tests that the list endpoint requires an authenticated user.
        """
        self.assertUnauthorized("/resources/", "GET")

    def test_detail_allowed_methods(self):
        """
        Tests that only safe methods are allowed for the detail endpoint.
        """
        self.authenticate()
        resource = Resource.objects.order_by("?").first()
        self.assertAllowedMethods(
            "/resources/{}/".format(resource.pk), {"OPTIONS", "HEAD", "GET"}
        )

    def test_detail_success(self):
        """
        Tests that a detail response for a resource looks correct.
        """
        self.authenticate()
        resource = Resource.objects.order_by("?").first()
        self.assertDetailResponseMatchesInstance(
            "/resources/{}/".format(resource.pk), resource, ResourceSerializer
        )

    def test_detail_missing(self):
        """
        Tests that the detail response for a non-existent resource looks correct.
        """
        self.authenticate()
        self.assertNotFound("/resources/100/")

    def test_detail_unauthenticated(self):
        """
        Tests that the detail endpoint requires an authenticated user.
        """
        resource = Resource.objects.order_by("?").first()
        self.assertUnauthorized("/resources/{}/".format(resource.pk), "GET")
