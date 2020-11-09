import random

from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework import mixins, status, viewsets

from ...models import Collaborator, Consortium
from ...serializers import CollaboratorSerializer

from .utils import ViewSetAssertionsMixin


class CollaboratorViewSetTestCase(ViewSetAssertionsMixin, APITestCase):
    """
    Tests for the collaborator viewset.
    """
    @classmethod
    def setUpTestData(cls):
        # Create a project
        cls.consortium = Consortium.objects.create(
            name = 'Consortium 1',
            manager = get_user_model().objects.create_user('manager1')
        )
        cls.project = cls.consortium.projects.create(
            name = 'Project 1',
            description = 'some description',
            owner = get_user_model().objects.create_user('owner1')
        )

    def setUp(self):
        # Create a few more contributors
        # We do this in setUp rather than setUpTestData so we can modify them without
        # affecting other tests
        for i in range(5):
            self.project.collaborators.create(
                user = get_user_model().objects.create_user(f'contributer{i}'),
                role = Collaborator.Role.CONTRIBUTOR
            )

    def test_allowed_methods(self):
        """
        Tests that the correct methods are permitted by the detail endpoint.
        """
        # Pick a random but valid collaborator to use in the detail endpoint
        collaborator = Collaborator.objects.order_by('?').first()
        self.assertAllowedMethods(
            "/collaborators/{}/".format(collaborator.pk),
            # Everything except POST is supported
            {'OPTIONS', 'HEAD', 'GET', 'PUT', 'PATCH', 'DELETE'}
        )

    def test_list_not_found(self):
        """
        Collaborators can only be listed via a project, so check that the list endpoint is not found.
        """
        self.assertNotFound("/collaborators/")

    def test_detail_success(self):
        """
        Tests that the detail endpoint successfully retrieves a valid collaborator.
        """
        # Pick a random but valid collaborator to use in the detail endpoint
        collaborator = Collaborator.objects.order_by('?').first()
        self.assertDetailResponseMatchesInstance(
            "/collaborators/{}/".format(collaborator.pk),
            collaborator,
            CollaboratorSerializer
        )

    def test_detail_missing(self):
        """
        Tests that the detail endpoint correctly reports not found for invalid collaborator.
        """
        self.assertNotFound("/collaborators/20/")

    def test_update_role(self):
        """
        Tests that the role can be updated.
        """
        collaborator = (
            Collaborator.objects
                .filter(role = Collaborator.Role.CONTRIBUTOR)
                .order_by('?')
                .first()
        )
        self.assertUpdateResponseMatchesUpdatedInstance(
            "/collaborators/{}/".format(collaborator.pk),
            collaborator,
            dict(role = Collaborator.Role.OWNER.name),
            CollaboratorSerializer
        )
        # Test that the instance was updated in the expected way
        # Note that the instance was refreshed as part of the assert
        self.assertEqual(collaborator.role, Collaborator.Role.OWNER)

    def test_cannot_update_with_invalid_role(self):
        """
        Tests that updating with an invalid role correctly fails.
        """
        collaborator = (
            Collaborator.objects
                .filter(role = Collaborator.Role.CONTRIBUTOR)
                .order_by('?')
                .first()
        )
        response_data = self.assertUpdateResponseIsBadRequest(
            "/collaborators/{}/".format(collaborator.pk),
            dict(role = "NOT_VALID")
        )
        self.assertEqual(response_data['role'][0]['code'], 'invalid_choice')

    def test_cannot_update_project_or_user(self):
        """
        Tests that the project and user cannot be updated.
        """
        # Make another valid project and user to specify
        project = self.consortium.projects.create(
            name = 'Project 2',
            description = 'some description',
            owner = get_user_model().objects.create_user('owner2')
        )
        user = get_user_model().objects.create_user('anotheruser')
        # Pick a random contributor to attempt to modify
        collaborator = (
            Collaborator.objects
                .filter(role = Collaborator.Role.CONTRIBUTOR)
                .order_by('?')
                .first()
        )
        original_project_pk = collaborator.project.pk
        original_user_pk = collaborator.user.pk
        # The update should go through, but the project and user should remain unchanged
        self.assertUpdateResponseMatchesUpdatedInstance(
            "/collaborators/{}/".format(collaborator.pk),
            collaborator,
            dict(project = project.pk, user = user.pk),
            CollaboratorSerializer
        )
        # Test that the project and user were not updated
        # Note that the instance was refreshed as part of the assert
        self.assertEqual(collaborator.project.pk, original_project_pk)
        self.assertNotEqual(collaborator.project.pk, project.pk)
        self.assertEqual(collaborator.user.pk, original_user_pk)
        self.assertNotEqual(collaborator.user.pk, user.pk)

    def test_can_downgrade_owner_when_multiple_owners(self):
        """
        Tests that an owner can be downgraded when there are multiple owners.
        """
        # Make an extra owner for the project
        collaborator = self.project.collaborators.create(
            user = get_user_model().objects.create_user('owner2'),
            role = Collaborator.Role.OWNER
        )
        self.assertUpdateResponseMatchesUpdatedInstance(
            "/collaborators/{}/".format(collaborator.pk),
            collaborator,
            dict(role = Collaborator.Role.CONTRIBUTOR.name),
            CollaboratorSerializer
        )
        # Check that the role was changed
        self.assertEqual(collaborator.role, Collaborator.Role.CONTRIBUTOR)

    def test_cannot_downgrade_sole_owner(self):
        """
        Tests that an owner cannot be downgraded when it is the only owner.
        """
        # Get the current sole owner for the project
        collaborator = self.project.collaborators.filter(role = Collaborator.Role.OWNER).first()
        # Trying to downgrade them to a contributor should result in a conflict
        response_data = self.assertConflict(
            "/collaborators/{}/".format(collaborator.pk),
            "PATCH",
            dict(role = Collaborator.Role.CONTRIBUTOR.name)
        )
        # Check that the error code is what we expected
        self.assertEqual(response_data['code'], 'sole_owner')
        # Check that the role was not changed
        collaborator.refresh_from_db()
        self.assertEqual(collaborator.role, Collaborator.Role.OWNER)

    def test_remove_contributor(self):
        """
        Tests that a collaborator is correctly removed by the DELETE method.
        """
        # Pick a random contributer to remove
        collaborator = (
            Collaborator.objects
                .filter(role = Collaborator.Role.CONTRIBUTOR)
                .order_by('?')
                .first()
        )
        self.assertDeleteResponseIsEmpty("/collaborators/{}/".format(collaborator.pk))
        # Test that the collaborator was removed
        self.assertFalse(Collaborator.objects.filter(pk = collaborator.pk).exists())

    def test_can_remove_owner_when_multiple_owners(self):
        """
        Tests that an owner can be deleted when there are multiple owners.
        """
        # Make an extra owner for the project
        collaborator = self.project.collaborators.create(
            user = get_user_model().objects.create_user('owner2'),
            role = Collaborator.Role.OWNER
        )
        # Try to delete them
        self.assertDeleteResponseIsEmpty("/collaborators/{}/".format(collaborator.pk))
        # Test that the collaborator was removed
        self.assertFalse(Collaborator.objects.filter(pk = collaborator.pk).exists())

    def test_cannot_remove_sole_owner(self):
        """
        Tests that an owner cannot be deleted when it is the only owner.
        """
        # Get the current sole owner for the project
        collaborator = self.project.collaborators.filter(role = Collaborator.Role.OWNER).first()
        # Trying to delete the owner record should result in a conflict
        response_data = self.assertConflict(
            "/collaborators/{}/".format(collaborator.pk),
            "DELETE"
        )
        # Check that the error code is what we expected
        self.assertEqual(response_data['code'], 'sole_owner')
        # Test that the collaborator was not removed
        self.assertTrue(Collaborator.objects.filter(pk = collaborator.pk).exists())
