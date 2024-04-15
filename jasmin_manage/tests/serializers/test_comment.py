from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework.request import Request
from rest_framework.test import APIRequestFactory, force_authenticate

from ...models import Comment, Consortium
from ...serializers import CommentSerializer


class CommentSerializerTestCase(TestCase):
    """
    Tests for the comment serializer.
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
        user = get_user_model().objects.create_user(
            "user1", first_name="User", last_name="One"
        )
        comment = self.project.comments.create(content="Some content.", user=user)
        # In order to render the links correctly, there must be a request in the context
        request = APIRequestFactory().get("/comments/{}/".format(comment.pk))
        serializer = CommentSerializer(comment, context=dict(request=request))
        # Check that the right keys are present
        self.assertCountEqual(
            serializer.data.keys(),
            {"id", "project", "content", "user", "created_at", "edited_at", "_links"},
        )
        # Check the the values are correct
        # Don't explicitly check the links field - it has tests
        self.assertEqual(serializer.data["id"], comment.pk)
        self.assertEqual(serializer.data["project"], self.project.pk)
        self.assertEqual(serializer.data["content"], comment.content)
        # Check that the user nested dict has the correct shape
        self.assertCountEqual(
            serializer.data["user"].keys(),
            {"id", "username", "first_name", "last_name"},
        )
        self.assertEqual(serializer.data["user"]["id"], user.pk)
        self.assertEqual(serializer.data["user"]["username"], user.username)
        self.assertEqual(serializer.data["user"]["first_name"], user.first_name)
        self.assertEqual(serializer.data["user"]["last_name"], user.last_name)
        # Test the created at and edited at fields have the correct format
        self.assertEqual(serializer.data["created_at"], comment.created_at.isoformat())
        self.assertEqual(serializer.data["edited_at"], comment.edited_at.isoformat())

    def test_create_uses_project_and_user_from_context(self):
        """
        Tests that creating a comment uses the project from the context and the
        authenticated user.
        """
        user = get_user_model().objects.create_user("user1")
        request = APIRequestFactory().post(
            "/projects/{}/comments/".format(self.project.pk)
        )
        force_authenticate(request, user)
        serializer = CommentSerializer(
            data=dict(content="Some comment content."),
            context=dict(project=self.project, request=Request(request)),
        )
        self.assertTrue(serializer.is_valid())
        comment = serializer.save()
        comment.refresh_from_db()
        self.assertEqual(comment.project.pk, self.project.pk)
        self.assertEqual(comment.user.pk, user.pk)

    def test_create_enforces_required_fields(self):
        """
        Tests that required fields are enforced on create.
        """
        user = get_user_model().objects.create_user("user1")
        request = APIRequestFactory().post(
            "/projects/{}/comments/".format(self.project.pk)
        )
        force_authenticate(request, user)
        serializer = CommentSerializer(
            data={}, context=dict(project=self.project, request=Request(request))
        )
        self.assertFalse(serializer.is_valid())
        self.assertCountEqual(serializer.errors.keys(), {"content"})
        self.assertEqual(serializer.errors["content"][0].code, "required")

    def test_cannot_create_with_blank_content(self):
        """
        Tests that creating with blank content correctly fails.
        """
        user = get_user_model().objects.create_user("user1")
        request = APIRequestFactory().post(
            "/projects/{}/comments/".format(self.project.pk)
        )
        force_authenticate(request, user)
        serializer = CommentSerializer(
            data=dict(content=""),
            context=dict(project=self.project, request=Request(request)),
        )
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["content"][0].code, "blank")

    def test_cannot_override_project_on_create(self):
        """
        Tests that the project cannot be overridden by specifying it in the input data.
        """
        # Create a project whose PK will be given in the data
        # We will specify cls.project in the context, which is the project that the
        # comment should be added to
        project = self.consortium.projects.create(
            name="Project 2",
            description="some description",
            owner=get_user_model().objects.create_user("owner2"),
        )
        # Pretend to be creating the comment as the project owner
        request = APIRequestFactory().post(
            "/projects/{}/comments/".format(self.project.pk)
        )
        force_authenticate(request, self.owner)
        serializer = CommentSerializer(
            data=dict(content="Some comment content.", project=project.pk),
            context=dict(project=self.project, request=Request(request)),
        )
        self.assertTrue(serializer.is_valid())
        comment = serializer.save()
        # Re-fetch the collaborator from the database before asserting
        comment.refresh_from_db()
        # Check that the comment belongs to cls.project, not the project we created
        self.assertEqual(project.comments.count(), 0)
        self.assertEqual(self.project.comments.count(), 1)
        self.assertEqual(comment.project.pk, self.project.pk)

    def test_cannot_override_user_on_create(self):
        """
        Tests that the user cannot be overridden by specifying it in the input data.
        """
        # Create a user whose PK will be given in the data
        # We will specify cls.owner in the context, which is the user that the
        # comment should be associated with
        user = get_user_model().objects.create_user("user1")
        # Pretend to be creating the comment as the project owner
        request = APIRequestFactory().post(
            "/projects/{}/comments/".format(self.project.pk)
        )
        force_authenticate(request, self.owner)
        serializer = CommentSerializer(
            data=dict(content="Some comment content.", user=user.pk),
            context=dict(project=self.project, request=Request(request)),
        )
        self.assertTrue(serializer.is_valid())
        comment = serializer.save()
        # Re-fetch the collaborator from the database before asserting
        comment.refresh_from_db()
        # Check that the comment belongs to cls.project, not the project we created
        self.assertEqual(comment.user.pk, self.owner.pk)

    def test_update_content(self):
        """
        Tests that the content of a comment can be updated.
        """
        comment = self.project.comments.create(
            content="Initial content.", user=self.owner
        )
        serializer = CommentSerializer(comment, data=dict(content="Updated content."))
        self.assertTrue(serializer.is_valid())
        comment = serializer.save()
        comment.refresh_from_db()
        self.assertEqual(comment.content, "Updated content.")

    def test_cannot_update_with_blank_content(self):
        """
        Tests that updating with blank content correctly fails.
        """
        comment = self.project.comments.create(
            content="Initial content.", user=self.owner
        )
        serializer = CommentSerializer(comment, data=dict(content=""))
        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["content"][0].code, "blank")

    def test_cannot_update_project_or_user(self):
        """
        Tests that the project and user cannot be updated by specifying them in the input data.
        """
        comment = self.project.comments.create(content="Some content.", user=self.owner)
        self.assertEqual(comment.project.pk, self.project.pk)
        self.assertEqual(comment.user.pk, self.owner.pk)
        # Make a new project and user to use
        project = self.consortium.projects.create(
            name="Project 2",
            description="some description",
            owner=get_user_model().objects.create_user("owner2"),
        )
        user = get_user_model().objects.create_user("user1")
        # Attempt to update the project and user
        serializer = CommentSerializer(
            comment,
            data=dict(content="Updated content.", project=project.pk, user=user.pk),
        )
        # The serializer should still pass as valid, as unknown or read-only fields are just ignored,
        # but saving should not change the project or user
        self.assertTrue(serializer.is_valid())
        comment = serializer.save()
        comment.refresh_from_db()
        self.assertEqual(comment.project.pk, self.project.pk)
        self.assertEqual(comment.user.pk, self.owner.pk)
        self.assertEqual(comment.content, "Updated content.")
