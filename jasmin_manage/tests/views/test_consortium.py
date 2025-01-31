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
        # Make a mixture of public and non-public consortia
        for i in range(20):
            Consortium.objects.create(
                name=f"Consortium {i}",
                is_public=(i < 12),
                manager=get_user_model().objects.create_user(f"manager{i}"),
            )

    def test_list_allowed_methods(self):
        """
        Tests that only safe methods are allowed for the list endpoint.
        """
        self.authenticate()
        self.assertAllowedMethods("/consortia/", {"OPTIONS", "HEAD", "GET"})

    def test_list_only_includes_public_consortia_for_non_staff(self):
        """
        Tests that a list response only includes public consortia for non-staff.
        """
        # Authenticate as a regular user
        user = self.authenticate()
        # Check that the response matches the appropriately filtered queryset
        self.assertListResponseMatchesQuerySet(
            "/consortia/", Consortium.objects.filter_visible(user), ConsortiumSerializer
        )

    def test_list_includes_non_public_consortia_for_staff(self):
        """
        Tests that a list response includes non-public consortia for a staff user.
        """
        # Authenticate as a regular user
        user = self.authenticate()
        # Make them a staff member
        user.is_staff = True
        user.save()
        # Check that the response matches the appropriately filtered queryset
        self.assertListResponseMatchesQuerySet(
            "/consortia/", Consortium.objects.filter_visible(user), ConsortiumSerializer
        )

    def test_list_includes_non_public_consortium_for_non_staff_user_if_manager(self):
        """
        Tests that a list response for a non-staff user includes a non-public consortium for
        which the user is the consortium manager while excluding all other non-public consortia.
        """
        # Pick a non-public consortium
        consortium = Consortium.objects.filter(is_public=False).order_by("?").first()
        # Authenticate as the consortium manager
        user = self.authenticateAsConsortiumManager(consortium)
        # Check that the response matches the appropriately filtered queryset
        self.assertListResponseMatchesQuerySet(
            "/consortia/", Consortium.objects.filter_visible(user), ConsortiumSerializer
        )

    def test_list_includes_non_public_consortium_for_non_staff_user_if_collaborator(
        self,
    ):
        """
        Tests that a list response for a non-staff user includes a non-public consortium
        in which the user has a project on which they are a collaborator, while excluding all other
        non-public consortia.
        """
        # Authenticate as a regular user
        user = self.authenticate()
        # Make a project in a non-public consortium with the user as the owner
        Consortium.objects.filter(is_public=False).order_by(
            "?"
        ).first().projects.create(
            name="Project 1", description="Some description.", owner=user
        )
        # Check that the response matches the appropriately filtered queryset
        self.assertListResponseMatchesQuerySet(
            "/consortia/", Consortium.objects.filter_visible(user), ConsortiumSerializer
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
        consortium = Consortium.objects.order_by("?").first()
        self.assertAllowedMethods(
            "/consortia/{}/".format(consortium.pk), {"OPTIONS", "HEAD", "GET"}
        )

    def test_detail_success_public_consortium_for_non_staff(self):
        """
        Tests that a detail response is successful for a public consortium for non-staff.
        """
        # Authenticate as a regular user
        user = self.authenticate()
        consortium = Consortium.objects.filter(is_public=True).order_by("?").first()
        self.assertDetailResponseMatchesInstance(
            "/consortia/{}/".format(consortium.pk), consortium, ConsortiumSerializer
        )

    def test_detail_success_non_public_consortium_for_staff(self):
        """
        Tests that a detail response is successful for a non-public consortium for a staff user.
        """
        # Authenticate as a regular user
        user = self.authenticate()
        # Make them a staff member
        user.is_staff = True
        user.save()
        consortium = Consortium.objects.filter(is_public=False).order_by("?").first()
        self.assertDetailResponseMatchesInstance(
            "/consortia/{}/".format(consortium.pk), consortium, ConsortiumSerializer
        )

    def test_detail_success_non_public_consortium_for_non_staff_user_if_manager(self):
        """
        Tests that a detail response is successful for a non-staff user and a non-public consortium
        when the user is the consortium manager.
        """
        # Pick a non-public consortium
        consortium = Consortium.objects.filter(is_public=False).order_by("?").first()
        # Authenticate as the consortium manager
        user = self.authenticateAsConsortiumManager(consortium)
        self.assertDetailResponseMatchesInstance(
            "/consortia/{}/".format(consortium.pk), consortium, ConsortiumSerializer
        )

    def test_detail_success_non_public_consortium_for_non_staff_user_if_collaborator(
        self,
    ):
        """
        Tests that a detail response is successful for a non-staff user and a non-public consortium
        when the user has a project in that consortium on which they are a collaborator.
        """
        # Authenticate as a regular user
        user = self.authenticate()
        # Pick a non-public consortium
        consortium = Consortium.objects.filter(is_public=False).order_by("?").first()
        # Make a project in the consortium with the user as the owner
        consortium.projects.create(
            name="Project 1", description="Some description.", owner=user
        )
        self.assertDetailResponseMatchesInstance(
            "/consortia/{}/".format(consortium.pk), consortium, ConsortiumSerializer
        )

    def test_detail_missing_non_public_consortium_for_non_staff(self):
        """
        Tests that the detail endpoint returns not found for a non-staff user if the consortium
        is non-public.
        """
        self.authenticate()
        consortium = Consortium.objects.filter(is_public=False).order_by("?").first()
        self.assertNotFound("/consortia/{}/".format(consortium.pk))

    def test_detail_unauthenticated(self):
        """
        Tests that the detail endpoint returns unauthorized for an unauthenticated user.
        """
        consortium = Consortium.objects.order_by("?").first()
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
        # Create a mixture of public and private consortia
        consortia = [
            Consortium.objects.create(
                name=f"Consortium {i}",
                is_public=(i < 5),
                manager=get_user_model().objects.create_user(f"manager{i}"),
            )
            for i in range(10)
        ]
        # Attach each project to a random consortium
        projects = [
            consortia[random.randrange(5)].projects.create(
                name=f"Project {i}",
                owner=get_user_model().objects.create_user(f"owner{i}"),
            )
            for i in range(20)
        ]

    def test_list_allowed_methods(self):
        """
        Tests that only safe methods are allowed for the list endpoint.
        """
        # Pick a random but valid consortium to use in the endpoint
        consortium = Consortium.objects.order_by("?").first()
        # Authenticate as the consortium manager
        self.authenticateAsConsortiumManager(consortium)
        self.assertAllowedMethods(
            "/consortia/{}/projects/".format(consortium.pk), {"OPTIONS", "HEAD", "GET"}
        )

    def test_list_consortium_manager(self):
        """
        Tests that the consortium manager can successfully list the projects.
        """
        consortium = Consortium.objects.order_by("?").first()
        # Authenticate as the consortium manager
        self.authenticateAsConsortiumManager(consortium)
        self.assertListResponseMatchesQuerySet(
            "/consortia/{}/projects/".format(consortium.pk),
            consortium.projects.annotate_summary(consortium.manager),
            ProjectSerializer,
        )

    def test_list_public_consortium_not_manager(self):
        """
        Tests that the list endpoint returns forbidden for a public consortium when the user
        is not the consortium manager.

        This should be forbidden rather than not found because the user can see the consortium.
        """
        self.authenticate()
        consortium = Consortium.objects.filter(is_public=True).order_by("?").first()
        self.assertPermissionDenied("/consortia/{}/projects/".format(consortium.pk))

    def test_list_non_public_staff_user_not_manager(self):
        """
        Tests that the list endpoint returns forbidden for a non-public consortium and a staff
        user who is not the consortium manager.

        This should be forbidden rather than not found because the user can see the consortium.
        """
        user = self.authenticate()
        user.is_staff = True
        user.save()
        consortium = Consortium.objects.filter(is_public=False).order_by("?").first()
        self.assertPermissionDenied("/consortia/{}/projects/".format(consortium.pk))

    def test_list_non_public_user_belongs_to_project_not_manager(self):
        """
        Tests that the list endpoint returns forbidden for a non-public consortium where the user
        belongs to a project in the consortium.

        This should be forbidden rather than not found because the user can see the consortium.
        """
        user = self.authenticate()
        consortium = Consortium.objects.filter(is_public=False).order_by("?").first()
        # Make a project in the consortium with the user as an owner
        consortium.projects.create(
            name="Owned project", description="Some description.", owner=user
        )
        self.assertPermissionDenied("/consortia/{}/projects/".format(consortium.pk))

    def test_list_consortium_not_visible(self):
        """
        Tests that the list endpoint returns not found when the consortium itself is not
        visible to the user.
        """
        # Authenticate as a regular user and pick a non-public consortium
        self.authenticate()
        consortium = Consortium.objects.filter(is_public=False).order_by("?").first()
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
        consortium = Consortium.objects.order_by("?").first()
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
                name=f"Consortium {i}",
                is_public=(i < 5),
                manager=get_user_model().objects.create_user(f"manager{i}"),
            )
            for i in range(10)
        ]
        resources = [Resource.objects.create(name=f"Resource {i}") for i in range(10)]
        # Create quotas for each combination of consortium and resource
        for consortium in consortia:
            for resource in resources:
                consortium.quotas.create(
                    resource=resource, amount=random.randint(1, 1000)
                )

    def test_list_allowed_methods(self):
        """
        Tests that only safe methods are allowed for the list endpoint.
        """
        # Pick a random but valid consortium to use in the endpoint
        consortium = Consortium.objects.order_by("?").first()
        # Authenticate as the consortium manager
        self.authenticateAsConsortiumManager(consortium)
        self.assertAllowedMethods(
            "/consortia/{}/quotas/".format(consortium.pk), {"OPTIONS", "HEAD", "GET"}
        )

    def test_list_consortium_manager(self):
        """
        Tests that the consortium manager can successfully list the quotas.
        """
        consortium = Consortium.objects.order_by("?").first()
        # Authenticate as the consortium manager
        self.authenticateAsConsortiumManager(consortium)
        self.assertListResponseMatchesQuerySet(
            "/consortia/{}/quotas/".format(consortium.pk),
            consortium.quotas.annotate_usage(),
            QuotaSerializer,
        )

    def test_list_public_consortium_not_manager(self):
        """
        Tests that the list endpoint returns forbidden for a public consortium when the user
        is not the consortium manager.

        This should be forbidden rather than not found because the user can see the consortium.
        """
        self.authenticate()
        consortium = Consortium.objects.filter(is_public=True).order_by("?").first()
        self.assertPermissionDenied("/consortia/{}/quotas/".format(consortium.pk))

    def test_list_non_public_staff_user_not_manager(self):
        """
        Tests that the list endpoint returns okay for a non-public consortium and a staff
        user who is not the consortium manager.
        """
        user = self.authenticate()
        user.is_staff = True
        user.save()
        consortium = Consortium.objects.filter(is_public=False).order_by("?").first()
        self.assertPermissionDenied("/consortia/{}/quotas/".format(consortium.pk))

    def test_list_non_public_user_belongs_to_project_not_manager(self):
        """
        Tests that the endpoint for a non-public consortium where the user owns a project
        in the consortium return the list successfully.
        """
        user = self.authenticate()
        # Pick a non-public consortium
        consortium = Consortium.objects.filter(is_public=False).order_by("?").first()
        # Make a project in the consortium with the user as an owner
        consortium.projects.create(
            name="Owned project", description="Some description.", owner=user
        )
        self.assertListResponseMatchesQuerySet(
            "/consortia/{}/quotas/".format(consortium.pk),
            consortium.quotas.annotate_usage(),
            QuotaSerializer,
        )

    def test_list_consortium_not_visible(self):
        """
        Tests that the list endpoint returns not found when the consortium itself is not
        visible to the user.
        """
        # Authenticate as a regular user and pick a non-public consortium
        self.authenticate()
        consortium = Consortium.objects.filter(is_public=False).order_by("?").first()
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
        consortium = Consortium.objects.order_by("?").first()
        self.assertUnauthorized("/consortia/{}/quotas/".format(consortium.pk))
