from datetime import date
from types import SimpleNamespace

from dateutil.relativedelta import relativedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework.test import APIRequestFactory

from ...models import Category, Consortium, Project, Requirement, Resource
from ...serializers import InvitationSerializer


class InvitationSerializerTestCase(TestCase):
    """
    Tests for the invitation serializer.
    """

    @classmethod
    def setUpTestData(cls):
        UserModel = get_user_model()
        cls.consortium = Consortium.objects.create(
            name="Consortium 1",
            description="some description",
            manager=UserModel.objects.create_user("manager1"),
        )
        cls.project = cls.consortium.projects.create(
            name="Project 1",
            description="some description",
            owner=UserModel.objects.create_user("owner1"),
        )

    def test_renders_instance_correctly(self):
        """
        Tests that the serializer renders an existing instance correctly.
        """
        invitation = self.project.invitations.create(email="joe.bloggs@example.com")
        # In order to render the links correctly, there must be a request in the context
        request = APIRequestFactory().post("/invitations/{}/".format(invitation.pk))
        serializer = InvitationSerializer(invitation, context=dict(request=request))
        # Check that the right keys are present
        self.assertCountEqual(
            serializer.data.keys(), {"id", "project", "email", "created_at", "_links"}
        )
        # Check the the values are correct
        # Don't explicitly check the links field - it has tests
        self.assertEqual(serializer.data["id"], invitation.pk)
        self.assertEqual(serializer.data["project"], self.project.pk)
        self.assertEqual(serializer.data["email"], invitation.email)
        self.assertEqual(
            serializer.data["created_at"], invitation.created_at.isoformat()
        )

    def test_create_enforces_required_fields(self):
        """
        Tests that the required fields are enforced on create.
        """
        serializer = InvitationSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {"email"})
        self.assertEqual(serializer.errors["email"][0].code, "required")

    def test_create_uses_project_from_context(self):
        """
        Tests that creating an invitation uses the project from the context.
        """
        serializer = InvitationSerializer(
            data=dict(email="joe.bloggs@example.com"),
            context=dict(project=self.project),
        )
        self.assertTrue(serializer.is_valid())
        invitation = serializer.save()
        invitation.refresh_from_db()
        self.assertEqual(invitation.project.pk, self.project.pk)
        self.assertEqual(invitation.email, "joe.bloggs@example.com")

    def test_cannot_override_project_on_create(self):
        """
        Tests that the project cannot be overridden by specifying it in the input data.
        """
        # Create a project whose PK will be given in the data
        # We will specify cls.project in the context, which is the project that the
        # service should be added to
        project = self.consortium.projects.create(
            name="Project 2",
            description="some description",
            owner=get_user_model().objects.create_user("owner2"),
        )
        serializer = InvitationSerializer(
            data=dict(project=project.pk, email="joe.bloggs@example.com"),
            context=dict(project=self.project),
        )
        self.assertTrue(serializer.is_valid())
        invitation = serializer.save()
        # Re-fetch the invitation from the database before asserting
        invitation.refresh_from_db()
        # Check that the invitation belongs to cls.project, not the project we created
        self.assertEqual(
            project.invitations.count(), 0
        )  # This project should have no invitations
        self.assertEqual(self.project.invitations.count(), 1)
        self.assertEqual(invitation.project.pk, self.project.pk)

    def test_cannot_override_code_on_create(self):
        """
        Tests that the invitation code cannot be set directly when creating.
        """
        # The chances of this code appearing randomly are zero, because it has a capital letter
        code = "Abcdefghijklmnopqrstuvwxyz012345"
        serializer = InvitationSerializer(
            data=dict(email="joe.bloggs@example.com", code=code),
            context=dict(project=self.project),
        )
        # The serializer should be valid - the code should just be ignored
        self.assertTrue(serializer.is_valid())
        invitation = serializer.save()
        invitation.refresh_from_db()
        self.assertNotEqual(invitation.code, code)

    def test_cannot_create_email_already_collaborator(self):
        """
        Tests that an invitation cannot be created if a user with the same email
        address is already a collaborator.
        """
        # Make a collaborator with the same email address, but with different capitalisation
        user = get_user_model().objects.create_user(
            "jbloggs", email="Joe.Bloggs@example.com"
        )
        self.project.collaborators.create(user=user)
        serializer = InvitationSerializer(
            data=dict(email="joe.bloggs@example.com"),
            context=dict(project=self.project),
        )
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {"email"})
        self.assertEqual(serializer.errors["email"][0].code, "invalid")

    def test_cannot_create_email_already_invited(self):
        """
        Tests that an invitation cannot be created if an invitation with the same email
        address already exists.
        """
        # Make an invitation with the same email address, but with different capitalisation
        self.project.invitations.create(email="Joe.Bloggs@example.com")
        serializer = InvitationSerializer(
            data=dict(email="joe.bloggs@example.com"),
            context=dict(project=self.project),
        )
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {"email"})
        self.assertEqual(serializer.errors["email"][0].code, "invalid")
