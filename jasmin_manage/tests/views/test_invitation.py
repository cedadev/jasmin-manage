from datetime import date
import random

from dateutil.relativedelta import relativedelta

from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework import mixins, status, viewsets

from ...models import Consortium, Invitation
from ...serializers import InvitationSerializer

from .utils import TestCase


class InvitationViewSetTestCase(TestCase):
    """
    Tests for the invitation viewset.
    """
    @classmethod
    def setUpTestData(cls):
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
        # For each project, create between 1 and 3 invitations
        Invitation.objects.bulk_create([
            Invitation(project = project, email = 'user{j}@university{i}.ac.uk')
            for j in range(random.randint(1, 3))
            for i, project in enumerate(self.projects)
        ])

    def test_list_not_found(self):
        """
        Invitations can only be listed via a project, so check that the list endpoint is not found.
        """
        self.assertNotFound("/invitations/")

    def test_detail_allowed_methods(self):
        """
        Tests that the correct methods are permitted by the detail endpoint.
        """
        invitation = Invitation.objects.order_by('?').first()
        self.authenticateAsProjectOwner(invitation.project)
        self.assertAllowedMethods(
            "/invitations/{}/".format(invitation.pk),
            # Invitations cannot be updated via the API
            {'OPTIONS', 'HEAD', 'GET', 'DELETE'}
        )

    def test_detail_as_project_owner(self):
        """
        Tests that a project owner can view the detail for an invitation.
        """
        invitation = Invitation.objects.order_by('?').first()
        self.authenticateAsProjectOwner(invitation.project)
        self.assertDetailResponseMatchesInstance(
            "/invitations/{}/".format(invitation.pk),
            invitation,
            InvitationSerializer
        )

    def test_detail_as_project_contributor(self):
        """
        Tests that a project contributor can view the detail for an invitation.
        """
        invitation = Invitation.objects.order_by('?').first()
        self.authenticateAsProjectContributor(invitation.project)
        self.assertDetailResponseMatchesInstance(
            "/invitations/{}/".format(invitation.pk),
            invitation,
            InvitationSerializer
        )

    def test_detail_as_consortium_manager(self):
        """
        Tests that the consortium manager can view the detail for an invitation.
        """
        invitation = Invitation.objects.order_by('?').first()
        self.authenticateAsConsortiumManager(invitation.project.consortium)
        self.assertDetailResponseMatchesInstance(
            "/invitations/{}/".format(invitation.pk),
            invitation,
            InvitationSerializer
        )

    def test_detail_not_permitted_authenticated(self):
        """
        Tests that an authenticated user that is not associated with the project
        cannot view the detail for an invitation.
        """
        self.authenticate()
        invitation = Invitation.objects.order_by('?').first()
        self.assertNotFound("/invitations/{}/".format(invitation.pk))

    def test_detail_requires_authentication(self):
        """
        Tests that authentication is required to view the detail for an invitation.
        """
        invitation = Invitation.objects.order_by('?').first()
        self.assertUnauthorized("/invitations/{}/".format(invitation.pk))

    def test_detail_missing(self):
        """
        Tests that the detail endpoint correctly reports not found for invalid invitation.
        """
        self.authenticate()
        self.assertNotFound("/invitations/100/")

    def test_remove_as_project_owner(self):
        """
        Tests that an invitation can be removed by a project owner.
        """
        invitation = Invitation.objects.order_by('?').first()
        self.authenticateAsProjectOwner(invitation.project)
        self.assertDeleteResponseIsEmpty("/invitations/{}/".format(invitation.pk))
        # Test that the invitation was removed
        self.assertFalse(Invitation.objects.filter(pk = invitation.pk).exists())

    def test_remove_not_permitted_for_project_contributor(self):
        """
        Tests that an invitation cannot be removed by a project contributor.
        """
        invitation = Invitation.objects.order_by('?').first()
        self.authenticateAsProjectContributor(invitation.project)
        self.assertPermissionDenied("/invitations/{}/".format(invitation.pk), "DELETE")

    def test_remove_not_permitted_for_consortium_manager(self):
        """
        Tests that the consortium manager cannot remove an invitation.
        """
        invitation = Invitation.objects.order_by('?').first()
        self.authenticateAsConsortiumManager(invitation.project.consortium)
        self.assertPermissionDenied("/invitations/{}/".format(invitation.pk), "DELETE")

    def test_remove_not_permitted_for_authenticated_user(self):
        """
        Tests that an invitation cannot be removed by a user that is not associated with the project.
        """
        self.authenticate()
        invitation = Invitation.objects.order_by('?').first()
        self.assertNotFound("/invitations/{}/".format(invitation.pk), "DELETE")

    def test_remove_requires_authentication(self):
        """
        Tests that removing an invitation requires authentication.
        """
        invitation = Invitation.objects.order_by('?').first()
        self.assertUnauthorized("/invitations/{}/".format(invitation.pk), "DELETE")
