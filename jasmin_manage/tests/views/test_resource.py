import random

from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework import mixins, status, viewsets

from ...models import Resource
from ...serializers import ResourceSerializer

from .utils import ViewSetAssertionsMixin


class ResourceViewSetTestCase(ViewSetAssertionsMixin, APITestCase):
    """
    Tests for the resource viewset.
    """
    @classmethod
    def setUpTestData(cls):
        for i in range(10):
            Resource.objects.create(name = f'Resource {i}')

    def test_allowed_methods(self):
        """
        Tests that only safe methods are allowed for the list and detail endpoints.
        """
        self.assertAllowedMethods("/resources/", {'OPTIONS', 'HEAD', 'GET'})
        # Pick a random but valid resource to use in the detail endpoint
        resource = Resource.objects.order_by('?').first()
        self.assertAllowedMethods(
            "/resources/{}/".format(resource.pk),
            {'OPTIONS', 'HEAD', 'GET'}
        )

    def test_list_success(self):
        """
        Tests that a list response looks correct.
        """
        self.assertListResponseMatchesQuerySet(
            "/resources/",
            Resource.objects.all(),
            ResourceSerializer
        )

    def test_detail_success(self):
        """
        Tests that a detail response for a consortium looks correct.
        """
        resource = Resource.objects.order_by('?').first()
        self.assertDetailResponseMatchesInstance(
            "/resources/{}/".format(resource.pk),
            resource,
            ResourceSerializer
        )

    def test_detail_missing(self):
        """
        Tests that the detail response for a non-existent consortium looks correct.
        """
        self.assertNotFound("/resources/20/")
