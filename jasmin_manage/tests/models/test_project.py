from django.contrib.auth import get_user_model
from django.test import TestCase

from ...models import Collaborator, Consortium, Project

from .utils import AssertValidationErrorsMixin


class ProjectModelTestCase(AssertValidationErrorsMixin, TestCase):
    """
    Tests for the project model.
    """
    @classmethod
    def setUpTestData(cls):
        UserModel = get_user_model()
        Project.objects.create(
            name = 'Project 1',
            consortium = Consortium.objects.create(
                name = 'Consortium 1',
                description = 'some description',
                manager = UserModel.objects.create_user('manager1')
            ),
            owner = UserModel.objects.create_user('user1')
        )

    def test_create_makes_owner(self):
        # Test that creating the project created a collaborator instance for the owner
        project = Project.objects.first()
        collaborators = project.collaborators.all()
        self.assertEqual(collaborators.count(), 1)
        self.assertEqual(collaborators[0].user.username, 'user1')
        self.assertEqual(collaborators[0].role, Collaborator.Role.OWNER)

    def test_name_unique(self):
        self.assertTrue(Project._meta.get_field('name').unique)

    def test_to_string(self):
        project = Project.objects.first()
        self.assertEqual(str(project), 'Project 1')

    def test_natural_key(self):
        project = Project.objects.first()
        self.assertEqual(project.natural_key(), ('Project 1', ))

    def test_get_by_natural_key(self):
        project = Project.objects.get_by_natural_key('Project 1')
        self.assertEqual(project.pk, 1)

    def test_get_event_type(self):
        project = Project.objects.first()
        # If status is in diff, the event type should have the status in it
        diff = dict(status = Project.Status.UNDER_REVIEW)
        event_type = project.get_event_type(diff)
        self.assertEqual(event_type, 'jasmin_manage.project.under_review')
        # If status is not in diff, the event type should be null
        diff = dict(name = 'New project name')
        self.assertIsNone(project.get_event_type(diff))

    def test_get_event_aggregates(self):
        project = Project.objects.first()
        self.assertEqual(project.get_event_aggregates(), (project.consortium, ))
