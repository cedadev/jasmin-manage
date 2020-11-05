from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework.test import APIRequestFactory

from ...models import Collaborator, Consortium
from ...serializers import CollaboratorSerializer


class CollaboratorSerializerTestCase(TestCase):
    """
    Tests for the collaborator serializer.
    """
    @classmethod
    def setUpTestData(cls):
        # Set up a consortium and project to use
        cls.consortium = Consortium.objects.create(
            name = 'Consortium 1',
            description = 'some description',
            manager = get_user_model().objects.create_user('manager1')
        )
        cls.owner = get_user_model().objects.create_user('owner1')
        # This will create an initial collaborator
        cls.project = cls.consortium.projects.create(
            name = 'Project 1',
            description = 'some description',
            owner = cls.owner
        )

    def test_renders_instance_correctly(self):
        """
        Tests that the serializer renders an existing instance correctly.
        """
        collaborator = self.project.collaborators.first()
        # In order to render the links correctly, there must be a request in the context
        request = APIRequestFactory().post('/collaborators/{}/'.format(collaborator.pk))
        serializer = CollaboratorSerializer(collaborator, context = dict(request = request))
        # Check that the right keys are present
        self.assertCountEqual(serializer.data.keys(), {'id', 'project', 'user', 'role', '_links'})
        # Check the the values are correct
        # Don't explicitly check the links field - it has tests
        self.assertEqual(serializer.data['id'], collaborator.pk)
        self.assertEqual(serializer.data['project'], collaborator.project.pk)
        self.assertEqual(serializer.data['user'], collaborator.user.pk)
        self.assertEqual(serializer.data['role'], Collaborator.Role.OWNER.name)

    def test_create_enforces_required_fields(self):
        """
        Tests that required fields are enforced on create.
        """
        serializer = CollaboratorSerializer(data = {}, context = dict(project = self.project))
        self.assertFalse(serializer.is_valid())
        required_fields = {'role', 'user'}
        self.assertCountEqual(serializer.errors.keys(), required_fields)
        for name in required_fields:
            self.assertEqual(serializer.errors[name][0].code, 'required')

    def test_create_uses_project_from_context(self):
        """
        Tests that creating a collaborator uses the project from the context.
        """
        user = get_user_model().objects.create_user('user1')
        serializer = CollaboratorSerializer(
            data = dict(user = user.pk, role = "CONTRIBUTOR"),
            context = dict(project = self.project)
        )
        self.assertTrue(serializer.is_valid())
        collaborator = serializer.save()
        # Re-fetch the collaborator from the database before asserting
        collaborator.refresh_from_db()
        self.assertEqual(collaborator.project.pk, self.project.pk)
        self.assertEqual(collaborator.user.pk, user.pk)
        self.assertEqual(collaborator.role, Collaborator.Role.CONTRIBUTOR)

    def test_cannot_create_collaborator_with_same_project_and_user(self):
        """
        Tests that the serializer enforces the unique together constraint on project/user
        even though the project is read-only.
        """
        # Try to create another collaborator for the same user and project
        serializer = CollaboratorSerializer(
            data = dict(user = self.owner.pk, role = "CONTRIBUTOR"),
            context = dict(project = self.project)
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors['non_field_errors'][0].code, 'unique')

    def test_cannot_override_project_on_create(self):
        """
        Tests that the project cannot be overridden by specifying it in the input data.
        """
        # Create a project whose PK will be given in the data
        # We will specify cls.project in the context, which is the project that the
        # collaborator should be added to
        project = self.consortium.projects.create(
            name = 'Project 2',
            description = 'some description',
            owner = get_user_model().objects.create_user('owner2')
        )
        # Make a user that is not the owner of either project to create a record for
        user = get_user_model().objects.create_user('user1')
        serializer = CollaboratorSerializer(
            data = dict(project = project.pk, user = user.pk, role = "OWNER"),
            context = dict(project = self.project)
        )
        self.assertTrue(serializer.is_valid())
        collaborator = serializer.save()
        # Re-fetch the collaborator from the database before asserting
        collaborator.refresh_from_db()
        # Check that the collaborator belongs to cls.project, not the project we created
        self.assertEqual(len(project.collaborators.all()), 1) # This should just be the original owner
        self.assertEqual(len(self.project.collaborators.all()), 2)
        self.assertEqual(collaborator.project.pk, self.project.pk)
        self.assertEqual(collaborator.user.pk, user.pk)
        self.assertEqual(collaborator.role, Collaborator.Role.OWNER)

    def test_cannot_create_with_invalid_role(self):
        """
        Tests that an invalid role correctly fails.
        """
        # Try to create a collaborator for an invalid role and test that it fails validation
        user = get_user_model().objects.create_user('user1')
        serializer = CollaboratorSerializer(
            data = dict(user = self.owner.pk, role = "NOT_VALID"),
            context = dict(project = self.project)
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors['role'][0].code, 'invalid_choice')

    def test_update_role(self):
        """
        Tests that the role can be updated.
        """
        collaborator = self.project.collaborators.first()
        self.assertEqual(collaborator.role, Collaborator.Role.OWNER)
        serializer = CollaboratorSerializer(collaborator, data = dict(role = "CONTRIBUTOR"))
        self.assertTrue(serializer.is_valid())
        collaborator = serializer.save()
        collaborator.refresh_from_db()
        self.assertEqual(collaborator.role, Collaborator.Role.CONTRIBUTOR)

    def test_cannot_update_project_or_user(self):
        """
        Tests that the project and user cannot be updated by specifying them in the input data.
        """
        collaborator = self.project.collaborators.first()
        self.assertEqual(collaborator.project.pk, self.project.pk)
        self.assertEqual(collaborator.user.pk, self.owner.pk)
        self.assertEqual(collaborator.role, Collaborator.Role.OWNER)
        # Make a new project and user to use
        project = self.consortium.projects.create(
            name = 'Project 2',
            description = 'some description',
            owner = get_user_model().objects.create_user('owner2')
        )
        user = get_user_model().objects.create_user('user1')
        # Attempt to update the project and user
        serializer = CollaboratorSerializer(
            collaborator,
            data = dict(project = project.pk, user = user.pk, role = "OWNER")
        )
        # The serializer should still pass as valid, as unknown or read-only fields are just ignored,
        # but saving should not change anything
        self.assertTrue(serializer.is_valid())
        collaborator = serializer.save()
        collaborator.refresh_from_db()
        self.assertEqual(collaborator.project.pk, self.project.pk)
        self.assertNotEqual(collaborator.project.pk, project.pk)
        self.assertEqual(collaborator.user.pk, self.owner.pk)
        self.assertNotEqual(collaborator.user.pk, user.pk)
