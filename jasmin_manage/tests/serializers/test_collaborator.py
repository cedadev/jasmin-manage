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
            name="Consortium 1",
            description="some description",
            manager=get_user_model().objects.create_user("manager1"),
        )
        cls.owner = get_user_model().objects.create_user(
            "owner1", first_name="Owner", last_name="One"
        )
        # This will create an initial collaborator
        cls.project = cls.consortium.projects.create(
            name="Project 1", description="some description", owner=cls.owner
        )

    def test_renders_instance_correctly(self):
        """
        Tests that the serializer renders an existing instance correctly.
        """
        collaborator = self.project.collaborators.first()
        # In order to render the links correctly, there must be a request in the context
        request = APIRequestFactory().post("/collaborators/{}/".format(collaborator.pk))
        serializer = CollaboratorSerializer(collaborator, context=dict(request=request))
        # Check that the right keys are present
        self.assertCountEqual(
            serializer.data.keys(),
            {"id", "project", "user", "role", "created_at", "_links"},
        )
        # Check the the values are correct
        # Don't explicitly check the links field - it has tests
        self.assertEqual(serializer.data["id"], collaborator.pk)
        self.assertEqual(serializer.data["project"], collaborator.project.pk)
        self.assertEqual(serializer.data["role"], Collaborator.Role.OWNER.name)
        # Check that the user nested dict has the correct shape
        self.assertCountEqual(
            serializer.data["user"].keys(),
            {"id", "username", "first_name", "last_name", "email"},
        )
        self.assertEqual(serializer.data["user"]["id"], collaborator.user.pk)
        self.assertEqual(
            serializer.data["user"]["username"], collaborator.user.username
        )
        self.assertEqual(
            serializer.data["user"]["first_name"], collaborator.user.first_name
        )
        self.assertEqual(
            serializer.data["user"]["last_name"], collaborator.user.last_name
        )

    def test_update_role(self):
        """
        Tests that the role can be updated.
        """
        collaborator = self.project.collaborators.first()
        self.assertEqual(collaborator.role, Collaborator.Role.OWNER)
        serializer = CollaboratorSerializer(collaborator, data=dict(role="CONTRIBUTOR"))
        self.assertTrue(serializer.is_valid())
        collaborator = serializer.save()
        collaborator.refresh_from_db()
        self.assertEqual(collaborator.role, Collaborator.Role.CONTRIBUTOR)

    def test_cannot_update_with_invalid_role(self):
        """
        Tests that updating with an invalid role correctly fails.
        """
        collaborator = self.project.collaborators.first()
        # Try to update the collaborator with an invalid role and test that it fails validation
        serializer = CollaboratorSerializer(collaborator, data=dict(role="NOT_VALID"))
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["role"][0].code, "invalid_choice")

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
            name="Project 2",
            description="some description",
            owner=get_user_model().objects.create_user("owner2"),
        )
        user = get_user_model().objects.create_user("user1")
        # Attempt to update the project and user
        serializer = CollaboratorSerializer(
            collaborator, data=dict(project=project.pk, user=user.pk, role="OWNER")
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
