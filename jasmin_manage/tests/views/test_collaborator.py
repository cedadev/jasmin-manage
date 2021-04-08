import random

from django.contrib.auth import get_user_model

from ...models import Collaborator, Consortium
from ...serializers import CollaboratorSerializer

from .utils import TestCase


class CollaboratorViewSetTestCase(TestCase):
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
                user = get_user_model().objects.create_user(f'contributor{i}'),
                role = Collaborator.Role.CONTRIBUTOR
            )

    def test_list_not_found(self):
        """
        Collaborators can only be listed via a project, so check that the list endpoint is not found.
        """
        self.assertNotFound("/collaborators/")

    def test_detail_allowed_methods(self):
        """
        Tests that the correct methods are permitted by the detail endpoint.
        """
        # Pick a random but valid collaborator to use in the detail endpoint
        collaborator = Collaborator.objects.order_by('?').first()
        # Authenticate the client as an owner of the project
        self.authenticateAsProjectOwner(collaborator.project)
        self.assertAllowedMethods(
            "/collaborators/{}/".format(collaborator.pk),
            # Everything except POST is supported
            {'OPTIONS', 'HEAD', 'GET', 'PUT', 'PATCH', 'DELETE'}
        )

    def test_detail_project_owner(self):
        """
        Tests that the detail endpoint successfully retrieves a valid collaborator
        when the authenticated user is a project owner.
        """
        collaborator = Collaborator.objects.order_by('?').first()
        self.authenticateAsProjectOwner(collaborator.project)
        self.assertDetailResponseMatchesInstance(
            "/collaborators/{}/".format(collaborator.pk),
            collaborator,
            CollaboratorSerializer
        )

    def test_detail_project_contributor(self):
        """
        Tests that the detail endpoint successfully retrieves a valid collaborator
        when the authenticated user is a project contributor.
        """
        # Pick a random but valid collaborator to use in the detail endpoint
        collaborator = Collaborator.objects.order_by('?').first()
        # Authenticate the client as a contributor to the project
        self.authenticateAsProjectContributor(collaborator.project)
        self.assertDetailResponseMatchesInstance(
            "/collaborators/{}/".format(collaborator.pk),
            collaborator,
            CollaboratorSerializer
        )

    def test_detail_consortium_manager(self):
        """
        Tests that the detail endpoint successfully retrieves a valid collaborator
        when the authenticated user is a project contributor.
        """
        # Pick a random but valid collaborator to use in the detail endpoint
        collaborator = Collaborator.objects.order_by('?').first()
        # Authenticate the client as the consortium manager
        self.authenticateAsConsortiumManager(collaborator.project.consortium)
        self.assertDetailResponseMatchesInstance(
            "/collaborators/{}/".format(collaborator.pk),
            collaborator,
            CollaboratorSerializer
        )

    def test_detail_authenticated_not_collaborator(self):
        """
        Tests that the detail endpoint returns not found when the user is authenticated
        but does not have permission to view the collaborator.
        """
        collaborator = Collaborator.objects.order_by('?').first()
        self.authenticate()
        self.assertNotFound("/collaborators/{}/".format(collaborator.pk), "GET")

    def test_detail_unauthenticated(self):
        """
        Tests that the detail endpoint returns unauthorized when an unauthenticated
        user attempts to access a valid collaborator.
        """
        collaborator = Collaborator.objects.order_by('?').first()
        self.assertUnauthorized("/collaborators/{}/".format(collaborator.pk), "GET")

    def test_detail_missing(self):
        """
        Tests that the detail endpoint correctly reports not found for invalid collaborator.
        """
        self.authenticate()
        self.assertNotFound("/collaborators/100/")

    def test_update_role(self):
        """
        Tests that the role can be updated by a project owner.
        """
        collaborator = (
            Collaborator.objects
                .filter(role = Collaborator.Role.CONTRIBUTOR)
                .order_by('?')
                .first()
        )
        # Authenticate the client as an owner of the project
        self.authenticateAsProjectOwner(collaborator.project)
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
        # Authenticate the client as an owner of the project
        self.authenticateAsProjectOwner(collaborator.project)
        response_data = self.assertBadRequest(
            "/collaborators/{}/".format(collaborator.pk),
            "PATCH",
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
        # Authenticate the client as an owner of the project
        self.authenticateAsProjectOwner(collaborator.project)
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
        # Authenticate the client as an owner of the project
        self.authenticateAsProjectOwner(collaborator.project)
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
        # Authenticate as the owner from the discovered collaborator
        self.client.force_authenticate(user = collaborator.user)
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

    def test_project_contributor_cannot_update(self):
        """
        Tests that a project contributor cannot update a contributor.
        """
        collaborator = Collaborator.objects.order_by('?').first()
        # Authenticate the client as an contributor of the project
        self.authenticateAsProjectContributor(collaborator.project)
        # This should be permission denied as the user is permitted to view the collaborator
        self.assertPermissionDenied(
            "/collaborators/{}/".format(collaborator.pk),
            "PATCH",
            dict(role = Collaborator.Role.OWNER.name),
        )

    def test_consortium_manager_cannot_update(self):
        """
        Tests that a consortium manager cannot update a contributor.
        """
        collaborator = Collaborator.objects.order_by('?').first()
        # Authenticate the client as the consortium manager for the project
        self.authenticateAsConsortiumManager(collaborator.project.consortium)
        # This should be permission denied as the user is permitted to view the collaborator
        self.assertPermissionDenied(
            "/collaborators/{}/".format(collaborator.pk),
            "PATCH",
            dict(role = Collaborator.Role.OWNER.name),
        )

    def test_authenticated_user_cannot_update(self):
        """
        Tests that an authenticated user who is not associated with the project
        cannot update a contributor.
        """
        collaborator = Collaborator.objects.order_by('?').first()
        # Authenticate the client as a user not associated with the project
        self.authenticate()
        # This should be not found as the user is not permitted to view the collaborator either
        self.assertNotFound(
            "/collaborators/{}/".format(collaborator.pk),
            "PATCH",
            dict(role = Collaborator.Role.OWNER.name),
        )

    def test_unauthenticated_user_cannot_update(self):
        """
        Tests that an unauthenticated user cannot update a contributor.
        """
        collaborator = Collaborator.objects.order_by('?').first()
        # This should be unauthorized as the user has not authenticated
        self.assertUnauthorized(
            "/collaborators/{}/".format(collaborator.pk),
            "PATCH",
            dict(role = Collaborator.Role.OWNER.name),
        )

    def test_remove_contributor(self):
        """
        Tests that a project owner can remove a collaborator using the DELETE method.
        """
        # Pick a random contributor to remove
        collaborator = (
            Collaborator.objects
                .filter(role = Collaborator.Role.CONTRIBUTOR)
                .order_by('?')
                .first()
        )
        # Authenticate the client as an owner of the project
        self.authenticateAsProjectOwner(collaborator.project)
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
        # Authenticate the client as an owner of the project
        self.authenticateAsProjectOwner(collaborator.project)
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
        # Authenticate as the owner from the discovered collaborator
        self.client.force_authenticate(user = collaborator.user)
        # Trying to delete the owner record should result in a conflict
        response_data = self.assertConflict(
            "/collaborators/{}/".format(collaborator.pk),
            "DELETE"
        )
        # Check that the error code is what we expected
        self.assertEqual(response_data['code'], 'sole_owner')
        # Test that the collaborator was not removed
        self.assertTrue(Collaborator.objects.filter(pk = collaborator.pk).exists())

    def test_project_contributor_cannot_remove(self):
        """
        Tests that a project contributor cannot remove a contributor.
        """
        collaborator = Collaborator.objects.order_by('?').first()
        # Authenticate the client as an contributor of the project
        self.authenticateAsProjectContributor(collaborator.project)
        # This should be permission denied as the user is permitted to view the collaborator
        self.assertPermissionDenied(
            "/collaborators/{}/".format(collaborator.pk),
            "DELETE"
        )

    def test_consortium_manager_cannot_remove(self):
        """
        Tests that a consortium manager cannot remove a contributor.
        """
        collaborator = Collaborator.objects.order_by('?').first()
        # Authenticate the client as the consortium manager for the project
        self.authenticateAsConsortiumManager(collaborator.project.consortium)
        # This should be permission denied as the user is permitted to view the collaborator
        self.assertPermissionDenied(
            "/collaborators/{}/".format(collaborator.pk),
            "DELETE"
        )

    def test_authenticated_user_cannot_remove(self):
        """
        Tests that an authenticated user who is not associated with the project
        cannot remove a contributor.
        """
        collaborator = Collaborator.objects.order_by('?').first()
        # Authenticate the client as a user not associated with the project
        self.authenticate()
        # This should be not found as the user is not permitted to view the collaborator either
        self.assertNotFound(
            "/collaborators/{}/".format(collaborator.pk),
            "DELETE"
        )

    def test_unauthenticated_user_cannot_remove(self):
        """
        Tests that an unauthenticated user cannot remove a contributor.
        """
        collaborator = Collaborator.objects.order_by('?').first()
        # This should be unauthorized as the user has not authenticated
        self.assertUnauthorized(
            "/collaborators/{}/".format(collaborator.pk),
            "DELETE"
        )
