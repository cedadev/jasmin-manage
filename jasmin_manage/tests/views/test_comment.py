from datetime import date
import random

from dateutil.relativedelta import relativedelta

from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase
from rest_framework import viewsets

from ...models import (
    Category,
    Collaborator,
    Comment,
    Consortium,
    Project,
    Requirement,
    Resource,
    Service
)
from ...serializers import CommentSerializer

from .utils import TestCase


class CommentViewSetTestCase(TestCase):
    """
    Tests for the requirement viewset.
    """
    @classmethod
    def setUpTestData(cls):
        # Create a project
        cls.consortium = Consortium.objects.create(
            name = 'Consortium 1',
            manager = get_user_model().objects.create_user('manager1')
        )
        cls.owner = get_user_model().objects.create_user('owner1')
        cls.project = cls.consortium.projects.create(
            name = 'Project 1',
            description = 'some description',
            owner = cls.owner
        )
        # Create some extra collaborators
        cls.contributors = [
            get_user_model().objects.create_user(f'contributor{i}')
            for i in range(3)
        ]
        for contributor in cls.contributors:
            cls.project.collaborators.create(
                user = contributor,
                role = Collaborator.Role.CONTRIBUTOR
            )

    def setUp(self):
        # Create a comment for each collaborator
        # We do this in setUp rather than setUpTestData so we can modify them without
        # affecting other tests
        self.project.comments.create(content = "Owner comment.", user = self.owner)
        for i, contributor in enumerate(self.contributors):
            self.project.comments.create(
                content = f"Contributor {i} comment.",
                user = contributor
            )

    def test_list_not_found(self):
        """
        Comments can only be listed via a project, so check that the list endpoint is not found.
        """
        self.assertNotFound("/comments/")

    def test_detail_allowed_methods(self):
        """
        Tests that the correct methods are permitted by the detail endpoint.
        """
        comment = Comment.objects.order_by('?').first()
        self.authenticateAsProjectOwner(self.project)
        self.assertAllowedMethods(
            "/comments/{}/".format(comment.pk),
            {'OPTIONS', 'HEAD', 'GET', 'PUT', 'PATCH', 'DELETE'}
        )

    def test_detail_project_owner(self):
        """
        Tests that the detail endpoint successfully retrieves a valid comment
        when the authenticated user is a project owner.
        """
        comment = Comment.objects.order_by('?').first()
        self.authenticateAsProjectOwner(self.project)
        self.assertDetailResponseMatchesInstance(
            "/comments/{}/".format(comment.pk),
            comment,
            CommentSerializer
        )

    def test_detail_project_contributor(self):
        """
        Tests that the detail endpoint successfully retrieves a valid comment
        when the authenticated user is a project contributor.
        """
        comment = Comment.objects.order_by('?').first()
        self.authenticateAsProjectContributor(self.project)
        self.assertDetailResponseMatchesInstance(
            "/comments/{}/".format(comment.pk),
            comment,
            CommentSerializer
        )

    def test_detail_consortium_manager(self):
        """
        Tests that the detail endpoint successfully retrieves a valid comment
        when the authenticated user is the consortium manager.
        """
        comment = Comment.objects.order_by('?').first()
        self.authenticateAsConsortiumManager(self.project.consortium)
        self.assertDetailResponseMatchesInstance(
            "/comments/{}/".format(comment.pk),
            comment,
            CommentSerializer
        )

    def test_detail_authenticated_not_collaborator(self):
        """
        Tests that the detail endpoint returns not found when the user is authenticated
        but does not have permission to view the comment.
        """
        self.authenticate()
        comment = Comment.objects.order_by('?').first()
        self.assertNotFound("/comments/{}/".format(comment.pk))

    def test_detail_unauthenticated(self):
        """
        Tests that the detail endpoint returns unauthorized when an unauthenticated
        user attempts to access a valid comment.
        """
        comment = Comment.objects.order_by('?').first()
        self.assertUnauthorized("/comments/{}/".format(comment.pk))

    def test_detail_missing(self):
        """
        Tests that the detail endpoint correctly reports not found for invalid comment.
        """
        self.authenticate()
        self.assertNotFound("/comments/100/")

    def assertCanUpdateComment(self, comment):
        """
        Asserts that the given comment can be updated by the currently authenticated user.
        """
        # Store the original user and edited_at for the comment
        original_user_pk = comment.user.pk
        original_edited_at = comment.edited_at
        # Check that the content is not already the updated content
        self.assertNotEqual(comment.content, "Updated content.")
        # Update the comment with new content
        self.assertUpdateResponseMatchesUpdatedInstance(
            "/comments/{}/".format(comment.pk),
            comment,
            dict(content = "Updated content."),
            CommentSerializer
        )
        # Test that the comment was updated in the expected way
        # Note that the comment was refreshed as part of the assert
        #   Verify that the content was updated
        self.assertEqual(comment.content, "Updated content.")
        #   Verify that the user stayed the same
        self.assertEqual(comment.user.pk, original_user_pk)
        #   Verify that edited_at changed
        self.assertGreater(comment.edited_at, original_edited_at)

    def assertCannotUpdateComment(self, comment):
        """
        Asserts that the given comment cannot be updated by the currently authenticated user.
        """
        # Store the original state for the comment
        original_content = comment.content
        original_user_pk = comment.user.pk
        original_edited_at = comment.edited_at
        # Try to update the comment and ensure we get permission denied
        self.assertPermissionDenied(
            "/comments/{}/".format(comment.pk),
            "PATCH",
            dict(content = "Updated content."),
        )
        comment.refresh_from_db()
        # Verify that the content has not changed
        self.assertNotEqual(comment.content, "Updated content.")
        self.assertEqual(comment.content, original_content)
        # Verify that the user stayed the same
        self.assertEqual(comment.user.pk, original_user_pk)
        # Verify that edited_at has not changed
        self.assertEqual(comment.edited_at, original_edited_at)

    def test_update_as_project_owner(self):
        """
        Tests that a comment can be updated by a project owner, both for their
        own comments and comments by others.
        """
        user = self.owner
        self.authenticate(user)
        # Check that the owner can update their own comment
        self.assertCanUpdateComment(
            self.project.comments.create(
                content = "User comment.",
                user = user
            )
        )
        # Check that the owner can update a manager's comment
        self.assertCanUpdateComment(
            self.project.comments.create(
                content = "Manager comment.",
                user = self.project.consortium.manager
            )
        )
        # Check that the owner can update another owner's comment
        other_owner = get_user_model().objects.create_user('testowner')
        self.project.collaborators.create(user = other_owner, role = Collaborator.Role.OWNER)
        self.assertCanUpdateComment(
            self.project.comments.create(
                content = "Owner comment.",
                user = other_owner
            )
        )
        # Check that the owner can update a contributor's comment
        self.assertCanUpdateComment(
            self.project.comments.create(
                content = "Contributor comment.",
                user = random.choice(self.contributors)
            )
        )

    def test_update_as_project_contributor(self):
        """
        Tests that a project contributor can update their own comment, but not those
        of others.
        """
        user = random.choice(self.contributors)
        self.authenticate(user)
        # Check that the user can update their own comment
        self.assertCanUpdateComment(
            self.project.comments.create(
                content = "User comment.",
                user = user
            )
        )
        # Check that the user cannot update a manager's comment
        self.assertCannotUpdateComment(
            self.project.comments.create(
                content = "Manager comment.",
                user = self.project.consortium.manager
            )
        )
        # Check that the user cannot update an owner's comment
        self.assertCannotUpdateComment(
            self.project.comments.create(
                content = "Owner comment.",
                user = self.owner
            )
        )
        # Check that the user cannot update another contributor's comment
        other_contributor = get_user_model().objects.create_user('testcontributor')
        self.project.collaborators.create(
            user = other_contributor,
            role = Collaborator.Role.CONTRIBUTOR
        )
        self.assertCannotUpdateComment(
            self.project.comments.create(
                content = "Contributor comment.",
                user = other_contributor
            )
        )

    def test_update_as_consortium_manager(self):
        """
        Tests that the consortium manager can update their own comment, but not those
        of others.
        """
        user = self.project.consortium.manager
        self.authenticate(user)
        # Check that the user can update their own comment
        self.assertCanUpdateComment(
            self.project.comments.create(
                content = "User comment.",
                user = user
            )
        )
        # Check that the user cannot update an owner's comment
        self.assertCannotUpdateComment(
            self.project.comments.create(
                content = "Owner comment.",
                user = self.owner
            )
        )
        # Check that the user cannot update a contributor's comment
        self.assertCannotUpdateComment(
            self.project.comments.create(
                content = "Contributor comment.",
                user = random.choice(self.contributors)
            )
        )

    def test_cannot_update_project(self):
        """
        Tests that the project cannot be updated.
        """
        comment = Comment.objects.order_by('?').first()
        self.authenticate(comment.user)
        original_project_pk = comment.project.pk
        # Make another project to include in the input data
        project = self.consortium.projects.create(
            name = 'Project 2',
            description = 'some description',
            owner = self.owner
        )
        self.assertNotEqual(original_project_pk, project.pk)
        # Try to make the update - it should succeed but the project should not be updated
        self.assertUpdateResponseMatchesUpdatedInstance(
            "/comments/{}/".format(comment.pk),
            comment,
            dict(project = project.pk),
            CommentSerializer
        )
        # Verify that the project was not updated
        self.assertEqual(comment.project.pk, original_project_pk)
        self.assertNotEqual(comment.project.pk, project.pk)

    def test_cannot_update_user(self):
        """
        Tests that the user cannot be updated.
        """
        comment = Comment.objects.order_by('?').first()
        self.authenticate(comment.user)
        original_user_pk = comment.user.pk
        # Make another user to include in the input data
        user = get_user_model().objects.create_user('user1')
        self.assertNotEqual(original_user_pk, user.pk)
        # Try to make the update - it should succeed but the user should not be updated
        self.assertUpdateResponseMatchesUpdatedInstance(
            "/comments/{}/".format(comment.pk),
            comment,
            dict(user = user.pk),
            CommentSerializer
        )
        # Verify that the user was not updated
        self.assertEqual(comment.user.pk, original_user_pk)
        self.assertNotEqual(comment.user.pk, user.pk)

    def test_cannot_update_with_blank_content(self):
        """
        Tests that a comment cannot be updated with blank content.
        """
        comment = Comment.objects.order_by('?').first()
        self.authenticate(comment.user)
        response_data = self.assertUpdateResponseIsBadRequest(
            "/comments/{}/".format(comment.pk),
            dict(content = "")
        )
        self.assertCountEqual(response_data.keys(), {'content'})
        self.assertEqual(response_data['content'][0]['code'], 'blank')

    def test_authenticated_user_cannot_update(self):
        """
        Tests that an authenticated user who is not associated with the project
        cannot update a comment, even if they own it.
        """
        # Authenticate as a user not associated with the project
        user = self.authenticate()
        # Make a comment on the project with them as the user
        comment = self.project.comments.create(
            content = "Comment content.",
            user = user
        )
        # Try to update the comment
        # This should be not found as the user is not permitted to view the comment either
        self.assertNotFound(
            "/comments/{}/".format(comment.pk),
            "PATCH",
            dict(content = "Updated content.")
        )

    def test_unauthenticated_user_cannot_update(self):
        """
        Tests that an unauthenticated user cannot update a comment.
        """
        comment = Comment.objects.order_by('?').first()
        # This should be unauthorized as the user has not authenticated
        self.assertUnauthorized(
            "/comments/{}/".format(comment.pk),
            "PATCH",
            dict(content = "Updated content.")
        )

    def assertCanDeleteComment(self, comment):
        """
        Asserts that the given comment can be deleted by the currently authenticated user.
        """
        # Delete the comment
        self.assertDeleteResponseIsEmpty("/comments/{}/".format(comment.pk))
        # Verify that the comment was removed
        self.assertFalse(Comment.objects.filter(pk = comment.pk).exists())

    def assertCannotDeleteComment(self, comment):
        """
        Asserts that the given comment cannot be deleted by the currently authenticated user.
        """
        # Try to delete the comment and ensure we get permission denied
        self.assertPermissionDenied("/comments/{}/".format(comment.pk), "DELETE")
        # Verify that the comment still exists
        self.assertTrue(Comment.objects.filter(pk = comment.pk).exists())

    def test_remove_as_project_owner(self):
        """
        Tests that a comment can be deleted by a project owner, both for their
        own comments and comments by others.
        """
        user = self.owner
        self.authenticate(user)
        # Check that the owner can delete their own comment
        self.assertCanDeleteComment(
            self.project.comments.create(
                content = "User comment.",
                user = user
            )
        )
        # Check that the owner can delete a manager's comment
        self.assertCanDeleteComment(
            self.project.comments.create(
                content = "Manager comment.",
                user = self.project.consortium.manager
            )
        )
        # Check that the owner can delete another owner's comment
        other_owner = get_user_model().objects.create_user('testowner')
        self.project.collaborators.create(user = other_owner, role = Collaborator.Role.OWNER)
        self.assertCanDeleteComment(
            self.project.comments.create(
                content = "Owner comment.",
                user = other_owner
            )
        )
        # Check that the owner can delete a contributor's comment
        self.assertCanDeleteComment(
            self.project.comments.create(
                content = "Contributor comment.",
                user = random.choice(self.contributors)
            )
        )

    def test_remove_as_project_contributor(self):
        """
        Tests that a project contributor can delete their own comment, but not those
        of others.
        """
        user = random.choice(self.contributors)
        self.authenticate(user)
        # Check that the user can delete their own comment
        self.assertCanDeleteComment(
            self.project.comments.create(
                content = "User comment.",
                user = user
            )
        )
        # Check that the user cannot delete a manager's comment
        self.assertCannotDeleteComment(
            self.project.comments.create(
                content = "Manager comment.",
                user = self.project.consortium.manager
            )
        )
        # Check that the user cannot delete an owner's comment
        self.assertCannotDeleteComment(
            self.project.comments.create(
                content = "Owner comment.",
                user = self.owner
            )
        )
        # Check that the user cannot delete another contributor's comment
        other_contributor = get_user_model().objects.create_user('testcontributor')
        self.project.collaborators.create(
            user = other_contributor,
            role = Collaborator.Role.CONTRIBUTOR
        )
        self.assertCannotDeleteComment(
            self.project.comments.create(
                content = "Contributor comment.",
                user = other_contributor
            )
        )

    def test_remove_as_consortium_manager(self):
        """
        Tests that the consortium manager can delete their own comment, but not those
        of others.
        """
        user = self.project.consortium.manager
        self.authenticate(user)
        # Check that the user can delete their own comment
        self.assertCanDeleteComment(
            self.project.comments.create(
                content = "User comment.",
                user = user
            )
        )
        # Check that the user cannot delete an owner's comment
        self.assertCannotDeleteComment(
            self.project.comments.create(
                content = "Owner comment.",
                user = self.owner
            )
        )
        # Check that the user cannot delete a contributor's comment
        self.assertCannotDeleteComment(
            self.project.comments.create(
                content = "Contributor comment.",
                user = random.choice(self.contributors)
            )
        )

    def test_authenticated_user_cannot_remove(self):
        """
        Tests that an authenticated user who is not associated with the project
        cannot delete a comment, even if they own it.
        """
        # Authenticate as a user not associated with the project
        user = self.authenticate()
        # Make a comment on the project with them as the user
        comment = self.project.comments.create(
            content = "Comment content.",
            user = user
        )
        # Try to delete the comment
        # This should be not found as the user is not permitted to view the comment either
        self.assertNotFound("/comments/{}/".format(comment.pk), "DELETE")

    def test_unauthenticated_user_cannot_remove(self):
        """
        Tests that an unauthenticated user cannot delete a comment.
        """
        comment = Comment.objects.order_by('?').first()
        # This should be unauthorized as the user has not authenticated
        self.assertUnauthorized("/comments/{}/".format(comment.pk), "DELETE")
