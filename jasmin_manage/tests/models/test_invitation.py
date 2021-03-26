from django.contrib.auth import get_user_model
from django.test import TestCase

from ...models import Collaborator, Consortium, Invitation

from ..utils import AssertValidationErrorsMixin


class RequirementModelTestCase(AssertValidationErrorsMixin, TestCase):
    """
    Tests for the requirement model.
    """
    @classmethod
    def setUpTestData(cls):
        UserModel = get_user_model()
        cls.consortium = Consortium.objects.create(
            name = 'Consortium 1',
            description = 'some description',
            manager = UserModel.objects.create_user('manager1')
        )
        cls.project = cls.consortium.projects.create(
            name = 'Project 1',
            description = 'some description',
            owner = UserModel.objects.create_user('owner1')
        )

    def test_default_code(self):
        # First, test that the default code is a 32 character alpha-numeric string
        invitation1 = self.project.invitations.create(email = 'joe.bloggs@example.com')
        self.assertRegex(invitation1.code, r"^[a-z0-9]{32}$")
        # Test that a second invitation has a different code
        invitation2 = self.project.invitations.create(email = 'jane.doe@example.com')
        self.assertNotEqual(invitation1.code, invitation2.code)

    def test_get_event_aggregates(self):
        # The project should be in the event aggregates
        invitation = self.project.invitations.create(email = 'joe.bloggs@example.com')
        self.assertEqual(invitation.get_event_aggregates(), (invitation.project, ))

    def test_to_string(self):
        invitation = self.project.invitations.create(email = 'joe.bloggs@example.com')
        self.assertEqual(str(invitation), 'Project 1 / joe.bloggs@example.com')

    def test_validates_email_not_a_collaborator(self):
        """
        Tests that an invitation cannot be created if a user with the same email
        address is already a collaborator.
        """
        # Make a collaborator with the same email address, but with different capitalisation
        user = get_user_model().objects.create_user('jbloggs', email = 'Joe.Bloggs@example.com')
        self.project.collaborators.create(user = user)
        invitation = Invitation(project = self.project, email = 'joe.bloggs@example.com')
        expected_errors = {
            'email': [
                'User with this email address is already a project collaborator (jbloggs).',
            ],
        }
        with self.assertValidationErrors(expected_errors):
            invitation.full_clean()

    def test_validates_email_not_already_invited_on_create(self):
        """
        Tests that an invitation cannot be created if an invitation with the same email
        address already exists.
        """
        # Make an invitation with the same email address, but with different capitalisation
        self.project.invitations.create(email = 'Joe.Bloggs@example.com')
        invitation = Invitation(project = self.project, email = 'joe.bloggs@example.com')
        expected_errors = {
            'email': ['Email address already has an invitation for this project.'],
        }
        with self.assertValidationErrors(expected_errors):
            invitation.full_clean()

    def test_validates_email_not_already_invited_on_update(self):
        """
        Tests that an invitation cannot be update to an email address for which an invitation
        already exists.
        """
        # Make an invitation that we will modify
        invitation = self.project.invitations.create(email = 'jane.doe@example.com')
        # Make a second invitation with a different email address
        self.project.invitations.create(email = 'Joe.Bloggs@example.com')
        # Try to update the invitation
        invitation.email = 'joe.bloggs@example.com'
        expected_errors = {
            'email': ['Email address already has an invitation for this project.'],
        }
        with self.assertValidationErrors(expected_errors):
            invitation.full_clean()

    def test_accept_new_collaborator(self):
        """
        Tests that accepting an invitation makes a new collaborator when the user
        is not already a collaborator.
        """
        # Make the invitation that we will accept
        invitation = self.project.invitations.create(email = 'joe.bloggs@example.com')
        # Make the user to accept the invitation
        user = get_user_model().objects.create_user('jbloggs')

        # Assert on the current state of the collaborators
        self.assertEqual(self.project.collaborators.count(), 1)
        self.assertFalse(self.project.collaborators.filter(user = user).exists())

        # Accept the invitation
        invitation.accept(user)

        # Check that the number of collaborators has increased
        self.assertEqual(self.project.collaborators.count(), 2)
        # The new collaborator should be a contributor, not an owner
        collaborator = self.project.collaborators.get(user = user)
        self.assertEqual(collaborator.role, Collaborator.Role.CONTRIBUTOR)

        # Check that the invitation no longer exists
        self.assertFalse(self.project.invitations.filter(pk = invitation.pk).exists())

    def test_accept_existing_collaborator(self):
        """
        Tests that if an existing collaborator accepts an invitation, then the collaborators
        for the project are not changed.
        """
        # Make the invitation that we will accept
        invitation = self.project.invitations.create(email = 'joe.bloggs@example.com')

        # Assert on the current state of the collaborators
        self.assertEqual(self.project.collaborators.count(), 1)

        # Accept the invitation as the project owner
        project_owner = self.project.collaborators.filter(role = Collaborator.Role.OWNER).first().user
        invitation.accept(project_owner)

        # Check that the number of collaborators has not increased
        self.assertEqual(self.project.collaborators.count(), 1)
        # Check that the project owner is still an owner
        collaborator = self.project.collaborators.get(user = project_owner)
        self.assertEqual(collaborator.role, Collaborator.Role.OWNER)

        # Check that the invitation no longer exists
        self.assertFalse(self.project.invitations.filter(pk = invitation.pk).exists())
