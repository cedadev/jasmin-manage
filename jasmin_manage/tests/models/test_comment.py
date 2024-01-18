from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.test import TestCase

from ...models import Comment, Consortium


class CommentModelTestCase(TestCase):
    """
    Tests for the comment model.
    """

    @classmethod
    def setUpTestData(cls):
        UserModel = get_user_model()
        consortium = Consortium.objects.create(
            name="Consortium 1",
            description="some description",
            manager=UserModel.objects.create_user("manager1"),
        )
        cls.user = get_user_model().objects.create_user("user1")
        cls.project = consortium.projects.create(name="Project 1", owner=cls.user)

    def test_user_is_protected(self):
        """
        Test that deleting a user with a comment is not permitted.
        """
        # To test this in isolation from the user being a project collaborator,
        # we need to have a user who is not a project collaborator to own the comment
        user = get_user_model().objects.create_user("user2")
        self.project.comments.create(content="Some content.", user=user)
        with self.assertRaises(ProtectedError):
            user.delete()

    def test_get_event_aggregates(self):
        """
        Test that the event aggregates are correct.
        """
        comment = self.project.comments.create(content="Some content.", user=self.user)
        event_aggregates = comment.get_event_aggregates()
        self.assertEqual(event_aggregates, (self.project, self.user))
