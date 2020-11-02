from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.test import TestCase

from ...models import Collaborator, Consortium

from .utils import AssertValidationErrorsMixin


class CollaboratorModelTestCase(AssertValidationErrorsMixin, TestCase):
    """
    Tests for the collaborator model.
    """
    @classmethod
    def setUpTestData(cls):
        UserModel = get_user_model()
        consortium = Consortium.objects.create(
            name = 'Consortium 1',
            description = 'some description',
            manager = UserModel.objects.create_user('manager1')
        )
        cls.user = get_user_model().objects.create_user('user1')
        cls.project = consortium.projects.create(
            name = 'Project 1',
            owner = cls.user
        )

    def test_unique_together(self):
        # Test that project and user are unique together
        collaborator = Collaborator(project = self.project, user = self.user)
        # Test that model validation raises the correct error
        expected_errors = {
            '__all__': ['Collaborator with this Project and User already exists.'],
        }
        with self.assertValidationErrors(expected_errors):
            collaborator.full_clean()
        # Test that an integrity error is raised when saving
        with self.assertRaises(IntegrityError):
            collaborator.save()

    def test_user_is_protected(self):
        # Test that deleting a user that is a collaborator is not permitted
        with self.assertRaises(ProtectedError):
            self.user.delete()

    def test_get_event_aggregates(self):
        collaborator = Collaborator.objects.first()
        event_aggregates = collaborator.get_event_aggregates()
        self.assertEqual(event_aggregates, (self.project, self.user))

    def test_to_string(self):
        collaborator = Collaborator.objects.first()
        self.assertEqual(str(collaborator), 'Project 1 / user1 / OWNER')
