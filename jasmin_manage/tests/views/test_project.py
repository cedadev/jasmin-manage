import random

from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework import mixins, status, viewsets

from ...models import (
    Category,
    Collaborator,
    Consortium,
    Project,
    Requirement,
    Resource,
    Service
)
from ...serializers import (
    CollaboratorSerializer,
    CommentSerializer,
    InvitationSerializer,
    ProjectSerializer,
    ServiceSerializer
)

from .utils import TestCase


class ProjectViewSetTestCase(TestCase):
    """
    Tests for the project viewset.
    """
    @classmethod
    def setUpTestData(cls):
        cls.consortium = Consortium.objects.create(
            name = 'Consortium 1',
            is_public = True,
            manager = get_user_model().objects.create_user('manager1')
        )
        cls.category = Category.objects.create(name = 'Category 1')
        cls.resource = Resource.objects.create(name = 'Resource 1')
        # Make a user to be the authenticated user
        cls.authenticated_user = get_user_model().objects.create_user('authenticateduser')

    def setUp(self):
        # Create projects here rather than setUpTestData so we can modify them without
        # affecting other tests
        projects = [
            self.consortium.projects.create(
                name = f'Project {i}',
                description = 'some description',
                owner = get_user_model().objects.create_user(f'owner{i}')
            )
            for i in range(10)
        ]
        # Attach the authenticated user to five random projects
        for project in random.sample(projects, 5):
            project.collaborators.create(
                user = self.authenticated_user,
                role = Collaborator.Role.CONTRIBUTOR
            )

    def test_list_allowed_methods(self):
        """
        Tests that the correct methods are permitted by the list endpoint.
        """
        self.authenticate()
        self.assertAllowedMethods("/projects/", {'OPTIONS', 'HEAD', 'GET', 'POST'})

    def test_list_authenticated_user_collaborating_projects_only(self):
        """
        Tests that the list endpoint returns only the projects that the user is collaborating
        on when the user is authenticated.
        """
        # Force authentication for the client
        self.client.force_authenticate(user = self.authenticated_user)
        self.assertListResponseMatchesQuerySet(
            "/projects/",
            Project.objects.filter(collaborator__user = self.authenticated_user),
            ProjectSerializer
        )

    def test_list_requires_authentication(self):
        """
        Tests that the list endpoint returns an unauthorized for an unauthenticated user.
        """
        self.assertUnauthorized("/projects/")

    def test_create_uses_authenticated_user_as_owner(self):
        """
        Tests that the creating a project uses the authenticated user as the project owner.
        """
        self.client.force_authenticate(self.authenticated_user)
        project = self.assertCreateResponseMatchesCreatedInstance(
            "/projects/",
            dict(
                consortium = self.consortium.pk,
                name = 'New project',
                description = 'some description'
            ),
            ProjectSerializer
        )
        # Verify that the project is created as editable
        self.assertEqual(project.status, Project.Status.EDITABLE)
        # Verify that the authenticated user is the project owner
        self.assertEqual(len(project.collaborators.all()), 1)
        self.assertEqual(project.collaborators.first().user.pk, self.authenticated_user.pk)

    def test_create_with_non_public_consortium_and_staff_user(self):
        """
        Tests that the serializer permits a staff user to create a project with a
        non-public consortium.
        """
        # Create a non-public consortium and a staff user to use
        consortium = Consortium.objects.create(
            name = 'Non-public Consortium',
            is_public = False,
            manager = get_user_model().objects.create_user('manager2')
        )
        staff_user = get_user_model().objects.create_user('staff_user', is_staff = True)
        self.client.force_authenticate(staff_user)
        project = self.assertCreateResponseMatchesCreatedInstance(
            "/projects/",
            dict(
                consortium = consortium.pk,
                name = 'New project',
                description = 'some description'
            ),
            ProjectSerializer
        )
        # Verify that the project is created as editable
        self.assertEqual(project.status, Project.Status.EDITABLE)
        # Verify that the authenticated user is the project owner
        self.assertEqual(len(project.collaborators.all()), 1)
        self.assertEqual(project.collaborators.first().user.pk, staff_user.pk)

    def test_create_enforces_required_fields_present(self):
        """
        Tests that the required fields are enforced on create.
        """
        self.client.force_authenticate(self.authenticated_user)
        response_data = self.assertBadRequest("/projects/", "POST", dict())
        required_fields = {'consortium', 'name', 'description'}
        self.assertCountEqual(response_data.keys(), required_fields)
        for name in required_fields:
            self.assertEqual(response_data[name][0]['code'], 'required')

    def test_create_enforces_required_fields_not_blank(self):
        """
        Tests that the required fields cannot be blank on create.
        """
        self.client.force_authenticate(self.authenticated_user)
        response_data = self.assertBadRequest(
            "/projects/",
            "POST",
            dict(consortium = self.consortium.pk, name = "", description = "")
        )
        required_fields = {'name', 'description'}
        self.assertCountEqual(response_data.keys(), required_fields)
        for name in required_fields:
            self.assertEqual(response_data[name][0]['code'], 'blank')

    def test_create_enforces_unique_name(self):
        """
        Tests that the uniqueness constraint is enforced on name when creating.
        """
        self.client.force_authenticate(self.authenticated_user)
        # Try to create another project with the same name as an existing project
        response_data = self.assertBadRequest(
            "/projects/",
            "POST",
            dict(
                consortium = self.consortium.pk,
                name = "Project 1",
                description = "some description"
            )
        )
        self.assertCountEqual(response_data.keys(), {'name'})
        self.assertEqual(response_data['name'][0]['code'], 'unique')

    def test_create_enforces_valid_consortium(self):
        """
        Tests that attempting to create with an invalid consortium will fail.
        """
        self.client.force_authenticate(self.authenticated_user)
        response_data = self.assertBadRequest(
            "/projects/",
            "POST",
            dict(
                consortium = 10,
                name = "New project",
                description = "some description"
            )
        )
        self.assertCountEqual(response_data.keys(), {'consortium'})
        self.assertEqual(response_data['consortium'][0]['code'], 'does_not_exist')

    def test_create_enforces_public_consortium_for_non_staff_user(self):
        """
        Tests that attempting to create a project in a non-public consortium as a
        non-staff user fails.
        """
        # Create a non-public consortium to use
        consortium = Consortium.objects.create(
            name = 'Non-public Consortium',
            is_public = False,
            manager = get_user_model().objects.create_user('manager2')
        )
        self.client.force_authenticate(self.authenticated_user)
        response_data = self.assertBadRequest(
            "/projects/",
            "POST",
            dict(
                consortium = consortium.pk,
                name = "New project",
                description = "some description"
            )
        )
        self.assertCountEqual(response_data.keys(), {'consortium'})
        self.assertEqual(response_data['consortium'][0]['code'], 'non_public_consortium')

    def test_create_ignores_status_if_specified(self):
        """
        Tests that the status cannot be specified on create.
        """
        self.client.force_authenticate(self.authenticated_user)
        project = self.assertCreateResponseMatchesCreatedInstance(
            "/projects/",
            dict(
                consortium = self.consortium.pk,
                name = 'New project',
                description = 'some description',
                status = Project.Status.UNDER_REVIEW.name
            ),
            ProjectSerializer
        )
        # Verify that the project is created as editable
        self.assertEqual(project.status, Project.Status.EDITABLE)

    def test_create_requires_authentication(self):
        """
        Tests that attempting to create a project returns unauthorized for an unauthenticated user.
        """
        self.assertUnauthorized(
            "/projects/",
            "POST",
            dict(
                consortium = self.consortium.pk,
                name = 'New project',
                description = 'some description'
            )
        )

    def test_detail_allowed_methods(self):
        """
        Tests that the correct methods are permitted by the detail endpoint.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        self.assertAllowedMethods(
            "/projects/{}/".format(project.pk),
            # Projects cannot be deleted via the API
            {'OPTIONS', 'HEAD', 'GET', 'PUT', 'PATCH'}
        )

    def test_detail_permitted_for_contributor(self):
        """
        Tests that the detail endpoint returns project information for a contributor.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectContributor(project)
        self.assertDetailResponseMatchesInstance(
            "/projects/{}/".format(project.pk),
            project,
            ProjectSerializer
        )

    def test_detail_permitted_for_owner(self):
        """
        Tests that the detail endpoint returns project information for an owner.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        self.assertDetailResponseMatchesInstance(
            "/projects/{}/".format(project.pk),
            project,
            ProjectSerializer
        )

    def test_detail_permitted_for_consortium_manager(self):
        """
        Tests that the detail endpoint returns project information for the consortium manager.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsConsortiumManager(project.consortium)
        self.assertDetailResponseMatchesInstance(
            "/projects/{}/".format(project.pk),
            project,
            ProjectSerializer
        )

    def test_detail_not_permitted_for_authenticated_user(self):
        """
        Tests that the detail endpoint returns not found for an authenticated user that is
        not associated with the project.
        """
        self.authenticate()
        project = Project.objects.order_by('?').first()
        self.assertNotFound("/projects/{}/".format(project.pk))

    def test_detail_missing(self):
        """
        Tests that the detail endpoint returns not found for an invalid project.
        """
        self.authenticate()
        self.assertNotFound("/projects/100/")

    def test_detail_requires_authentication(self):
        """
        Tests that the detail endpoint returns unauthorized when accessed by an unauthenticated user.
        """
        project = Project.objects.order_by('?').first()
        self.assertUnauthorized("/projects/{}/".format(project.pk))

    def test_update_name_and_description(self):
        """
        Tests that the name and description can be updated by the project owner.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        self.assertUpdateResponseMatchesUpdatedInstance(
            "/projects/{}/".format(project.pk),
            project,
            dict(name = 'New project name', description = 'new description'),
            ProjectSerializer
        )
        # Assert that the expected changes were applied
        self.assertEqual(project.name, 'New project name')
        self.assertEqual(project.description, 'new description')

    def test_update_enforces_required_fields_not_blank(self):
        """
        Tests that the required fields cannot be blank on update.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        response_data = self.assertBadRequest(
            "/projects/{}/".format(project.pk),
            "PATCH",
            data = dict(name = '', description = '')
        )
        self.assertCountEqual(response_data.keys(), {'name', 'description'})
        for name in {'name', 'description'}:
            self.assertEqual(response_data[name][0]['code'], 'blank')

    def test_update_enforces_unique_name(self):
        """
        Tests that the unique constraint is enforced for name on update.
        """
        project = Project.objects.get(name = 'Project 1')
        self.authenticateAsProjectOwner(project)
        response_data = self.assertBadRequest(
            "/projects/{}/".format(project.pk),
            "PATCH",
            # Change the project name to a name that collides with another project
            data = dict(name = 'Project 2')
        )
        self.assertCountEqual(response_data.keys(), {'name'})
        self.assertEqual(response_data['name'][0]['code'], 'unique')

    def test_update_consortium_not_allowed(self):
        """
        Tests that the consortium cannot be updated.
        """
        # Create another consortium that we will attempt to update with
        consortium = Consortium.objects.create(
            name = 'Consortium 2',
            manager = get_user_model().objects.create_user('manager2')
        )
        # Pick a project to update
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        self.assertUpdateResponseMatchesUpdatedInstance(
            "/projects/{}/".format(project.pk),
            project,
            dict(consortium = consortium.pk),
            ProjectSerializer
        )
        # The update should be accepted, but the consortium will not change
        self.assertEqual(project.consortium.pk, self.consortium.pk)

    def test_update_status_not_allowed(self):
        """
        Tests that the status cannot be updated.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        self.assertUpdateResponseMatchesUpdatedInstance(
            "/projects/{}/".format(project.pk),
            project,
            dict(status = Project.Status.UNDER_REVIEW.name),
            ProjectSerializer
        )
        # The update should be accepted, but the status will not change
        self.assertEqual(project.status, Project.Status.EDITABLE)

    def test_update_not_permitted_for_contributor(self):
        """
        Tests that a contributor cannot update a project's name and description.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectContributor(project)
        # This should be permission denied since the user can view the project
        self.assertPermissionDenied(
            "/projects/{}/".format(project.pk),
            "PATCH",
            dict(name = 'New project name', description = 'new description')
        )

    def test_update_not_permitted_for_consortium_manager(self):
        """
        Tests that a consortium manager cannot update a project's name and description.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsConsortiumManager(project.consortium)
        # This should be permission denied since the user can view the project
        self.assertPermissionDenied(
            "/projects/{}/".format(project.pk),
            "PATCH",
            dict(name = 'New project name', description = 'new description')
        )

    def test_update_not_permitted_for_authenticated_user(self):
        """
        Tests that an authenticated user cannot update a project that they are not
        associated with.
        """
        project = Project.objects.order_by('?').first()
        self.authenticate()
        # This should be not found since the user cannot view the project at all
        self.assertNotFound(
            "/projects/{}/".format(project.pk),
            "PATCH",
            dict(name = 'New project name', description = 'new description')
        )

    def test_update_requires_authentication(self):
        """
        Tests that updating a project requires authentication.
        """
        project = Project.objects.order_by('?').first()
        self.assertUnauthorized(
            "/projects/{}/".format(project.pk),
            "PATCH",
            dict(name = 'New project name', description = 'new description')
        )

    def test_delete_not_permitted(self):
        """
        Tests that the delete method returns method not allowed as expected.
        """
        # Pick a random but valid project to use in the detail endpoint
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        self.assertMethodNotAllowed("/projects/{}/".format(project.pk), "DELETE")

    def test_submit_for_review_allowed_methods(self):
        """
        Tests that the correct methods are permitted by the submit_for_review endpoint.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        self.assertAllowedMethods(
            "/projects/{}/submit_for_review/".format(project.pk),
            {'OPTIONS', 'POST'}
        )

    def test_submit_for_review_editable_with_requested_requirements_only(self):
        """
        Tests that the project owner can submit an editable project with only requested
        requirements for review.
        """
        project = Project.objects.order_by('?').first()
        user = self.authenticateAsProjectOwner(project)
        self.assertEqual(project.status, Project.Status.EDITABLE)
        # Make a requested requirement before submitting
        Requirement.objects.create(
            service = project.services.create(name = 'service1', category = self.category),
            resource = self.resource,
            status = Requirement.Status.REQUESTED,
            amount = 100
        )
        self.assertActionResponseMatchesUpdatedInstance(
            "/projects/{}/submit_for_review/".format(project.pk),
            project,
            dict(comment = "Submitting for review."),
            ProjectSerializer
        )
        # Verify that the project is now under review
        self.assertEqual(project.status, Project.Status.UNDER_REVIEW)
        # Verify that the project has a comment
        self.assertEqual(project.comments.count(), 1)
        # Verify that the comment has the right content and user
        comment = project.comments.first()
        self.assertEqual(comment.content, "Submitting for review.")
        self.assertEqual(comment.user.pk, user.pk)

    def test_submit_for_review_editable_with_approved_requirements_only(self):
        """
        Tests that the project owner can submit an editable project with only approved
        requirements for review.

        This is to cover the case where a project has been submitted for review and
        on review, some requirements were approved and some were rejected with an
        instruction to remove them. This leaves the project in the editable state
        with only approved requirements, so it must be able to be submitted for a final
        review before being submitted for provisioning.
        """
        project = Project.objects.order_by('?').first()
        user = self.authenticateAsProjectOwner(project)
        self.assertEqual(project.status, Project.Status.EDITABLE)
        # Make an approved requirement before submitting
        Requirement.objects.create(
            service = project.services.create(name = 'service1', category = self.category),
            resource = self.resource,
            status = Requirement.Status.APPROVED,
            amount = 100
        )
        self.assertActionResponseMatchesUpdatedInstance(
            "/projects/{}/submit_for_review/".format(project.pk),
            project,
            dict(comment = "Submitting for review."),
            ProjectSerializer
        )
        # Verify that the project is now under review
        self.assertEqual(project.status, Project.Status.UNDER_REVIEW)
        # Verify that the project has a comment
        self.assertEqual(project.comments.count(), 1)
        # Verify that the comment has the right content and user
        comment = project.comments.first()
        self.assertEqual(comment.content, "Submitting for review.")
        self.assertEqual(comment.user.pk, user.pk)

    def test_submit_for_review_editable_with_requested_and_approved_requirements(self):
        """
        Tests that the project owner can submit an editable project with required and
        approved requirements for review.
        """
        project = Project.objects.order_by('?').first()
        user = self.authenticateAsProjectOwner(project)
        self.assertEqual(project.status, Project.Status.EDITABLE)
        service = project.services.create(name = 'service1', category = self.category)
        # Make a requested and an approved requirement before submitting
        Requirement.objects.create(
            service = service,
            resource = self.resource,
            status = Requirement.Status.REQUESTED,
            amount = 100
        )
        Requirement.objects.create(
            service = service,
            resource = self.resource,
            status = Requirement.Status.APPROVED,
            amount = 100
        )
        self.assertActionResponseMatchesUpdatedInstance(
            "/projects/{}/submit_for_review/".format(project.pk),
            project,
            dict(comment = "Submitting for review."),
            ProjectSerializer
        )
        # Verify that the project is now under review
        self.assertEqual(project.status, Project.Status.UNDER_REVIEW)
        # Verify that the project has a comment
        self.assertEqual(project.comments.count(), 1)
        # Verify that the comment has the right content and user
        comment = project.comments.first()
        self.assertEqual(comment.content, "Submitting for review.")
        self.assertEqual(comment.user.pk, user.pk)

    def test_submit_for_review_requires_comment(self):
        """
        Tests that a comment is required when submitting a project for review.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        response_data = self.assertBadRequest(
            "/projects/{}/submit_for_review/".format(project.pk),
            "POST",
            dict()
        )
        self.assertCountEqual(response_data.keys(), {'comment'})
        self.assertEqual(response_data['comment'][0]['code'], 'required')

    def test_submit_for_review_blank_comment_not_permitted(self):
        """
        Tests that a blank comment is not allowed when submitting a project for review.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        response_data = self.assertBadRequest(
            "/projects/{}/submit_for_review/".format(project.pk),
            "POST",
            dict(comment = "")
        )
        self.assertCountEqual(response_data.keys(), {'comment'})
        self.assertEqual(response_data['comment'][0]['code'], 'blank')

    def test_submit_for_review_only_permitted_for_status_editable(self):
        """
        Tests that a project that is not editable cannot be submitted for review.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        for status in Project.Status:
            if status == Project.Status.EDITABLE:
                continue
            # Put the project into the given state
            project.status = status
            project.save()
            # Then check that it cannot be submitted for review
            response_data = self.assertConflict(
                "/projects/{}/submit_for_review/".format(project.pk),
                "POST",
                dict(comment = "Submitting for review.")
            )
            # Check that the error code is what we expected
            self.assertEqual(response_data['code'], 'invalid_status')
            # Check that the state in the DB was not changed
            project.refresh_from_db()
            self.assertEqual(project.status, status)
            # Check that no comment was created
            self.assertEqual(project.comments.count(), 0)

    def test_submit_for_review_not_allowed_with_rejected_requirements(self):
        """
        Tests that a project cannot be submitted for review if it has rejected
        requirements, even if it has other requested and approved requirements.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        service = project.services.create(name = 'service1', category = self.category)
        # Create a requirement that in the rejected state
        # We require that all rejected requests have been either modified (which sends them
        # back to requested) or removed before submitting for review
        Requirement.objects.create(
            service = service,
            resource = self.resource,
            status = Requirement.Status.REJECTED,
            amount = 100
        )
        # Make another requirement that is in the requested state, so that the project
        # would be submitted without the rejected requirement
        Requirement.objects.create(
            service = service,
            resource = self.resource,
            status = Requirement.Status.REQUESTED,
            amount = 100
        )
        Requirement.objects.create(
            service = service,
            resource = self.resource,
            status = Requirement.Status.APPROVED,
            amount = 100
        )
        # Then check that it cannot be submitted for review
        response_data = self.assertConflict(
            "/projects/{}/submit_for_review/".format(project.pk),
            "POST",
            dict(comment = "Submitting for review.")
        )
        # Check that the error code is what we expected
        self.assertEqual(response_data['code'], 'rejected_requirements')
        # Verify that the state is still editable
        project.refresh_from_db()
        self.assertEqual(project.status, Project.Status.EDITABLE)
        # Check that no comment was created
        self.assertEqual(project.comments.count(), 0)

    def test_submit_for_review_not_allowed_without_requested_or_approved_requirements(self):
        """
        Tests that a project cannot be submitted for review unless it has at
        least one requirement in the requested or approved state.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        # Create a requirement that is not in the required state, to test that this only
        # depends on requested requirements
        Requirement.objects.create(
            service = project.services.create(name = 'service1', category = self.category),
            resource = self.resource,
            status = Requirement.Status.PROVISIONED,
            amount = 100
        )
        # Then check that it cannot be submitted for review
        response_data = self.assertConflict(
            "/projects/{}/submit_for_review/".format(project.pk),
            "POST",
            dict(comment = "Submitting for review.")
        )
        # Check that the error code is what we expected
        self.assertEqual(response_data['code'], 'no_requirements_to_review')
        # Verify that the state is still editable
        project.refresh_from_db()
        self.assertEqual(project.status, Project.Status.EDITABLE)
        # Check that no comment was created
        self.assertEqual(project.comments.count(), 0)

    def test_submit_for_review_not_permitted_for_contributor(self):
        """
        Tests that a contributor cannot submit a project for review.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectContributor(project)
        # This should be permission denied since the user can view the project
        self.assertPermissionDenied(
            "/projects/{}/submit_for_review/".format(project.pk),
            "POST"
        )

    def test_submit_for_review_not_permitted_for_consortium_manager(self):
        """
        Tests that a consortium manager cannot submit a project for review.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsConsortiumManager(project.consortium)
        # This should be permission denied since the user can view the project
        self.assertPermissionDenied(
            "/projects/{}/submit_for_review/".format(project.pk),
            "POST"
        )

    def test_submit_for_review_not_permitted_for_authenticated_user(self):
        """
        Tests that an authenticated user cannot submit a project for review that they
        are not associated with.
        """
        project = Project.objects.order_by('?').first()
        self.authenticate()
        # This should be not found since the user cannot view the project at all
        self.assertNotFound(
            "/projects/{}/submit_for_review/".format(project.pk),
            "POST"
        )

    def test_submit_for_review_requires_authentication(self):
        """
        Tests that submitting a project for review requires authentication.
        """
        project = Project.objects.order_by('?').first()
        self.assertUnauthorized(
            "/projects/{}/submit_for_review/".format(project.pk),
            "POST"
        )

    def test_request_changes_allowed_methods(self):
        """
        Tests that the correct methods are permitted by the request_changes endpoint.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsConsortiumManager(project.consortium)
        self.assertAllowedMethods(
            "/projects/{}/request_changes/".format(project.pk),
            {'OPTIONS', 'POST'}
        )

    def test_request_changes_under_review_with_rejected_requirement(self):
        """
        Tests that a project in the under review status with a rejected requirement
        can be returned to the user requesting changes.
        """
        project = Project.objects.order_by('?').first()
        user = self.authenticateAsConsortiumManager(project.consortium)
        # Put the project into the expected state
        project.status = Project.Status.UNDER_REVIEW
        project.save()
        Requirement.objects.create(
            service = project.services.create(name = 'service1', category = self.category),
            resource = self.resource,
            status = Requirement.Status.REJECTED,
            amount = 100
        )
        # Attempt to return for changes
        self.assertActionResponseMatchesUpdatedInstance(
            "/projects/{}/request_changes/".format(project.pk),
            project,
            dict(comment = "Requesting changes."),
            ProjectSerializer
        )
        # Verify that the project is now editable
        self.assertEqual(project.status, Project.Status.EDITABLE)
        # Verify that the project has a comment
        self.assertEqual(project.comments.count(), 1)
        # Verify that the comment has the right content and user
        comment = project.comments.first()
        self.assertEqual(comment.content, "Requesting changes.")
        self.assertEqual(comment.user.pk, user.pk)

    def test_request_changes_requires_comment(self):
        """
        Tests that a comment is required when requesting changes to a project.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsConsortiumManager(project.consortium)
        response_data = self.assertBadRequest(
            "/projects/{}/request_changes/".format(project.pk),
            "POST",
            dict()
        )
        self.assertCountEqual(response_data.keys(), {'comment'})
        self.assertEqual(response_data['comment'][0]['code'], 'required')

    def test_request_changes_blank_comment_not_permitted(self):
        """
        Tests that a blank comment is not allowed when requesting changes to a project.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsConsortiumManager(project.consortium)
        response_data = self.assertBadRequest(
            "/projects/{}/request_changes/".format(project.pk),
            "POST",
            dict(comment = "")
        )
        self.assertCountEqual(response_data.keys(), {'comment'})
        self.assertEqual(response_data['comment'][0]['code'], 'blank')

    def test_request_changes_only_permitted_for_status_under_review(self):
        """
        Tests that a project can only be returned for changes when it is under review.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsConsortiumManager(project.consortium)
        for status in Project.Status:
            if status == Project.Status.UNDER_REVIEW:
                continue
            # Put the project into the given state
            project.status = status
            project.save()
            # Then check that it cannot be returned for changes
            response_data = self.assertConflict(
                "/projects/{}/request_changes/".format(project.pk),
                "POST",
                dict(comment = "Requesting changes.")
            )
            # Check that the error code is what we expected
            self.assertEqual(response_data['code'], 'invalid_status')
            # Check that the state in the DB was not changed
            project.refresh_from_db()
            self.assertEqual(project.status, status)
            # Check that no comment was created
            self.assertEqual(project.comments.count(), 0)

    def test_request_changes_not_allowed_with_requested_requirements(self):
        """
        Tests that a project cannot be returned for changes with unresolved requested
        requirements.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsConsortiumManager(project.consortium)
        # Put the project into the review state
        project.status = Project.Status.UNDER_REVIEW
        project.save()
        service = project.services.create(name = 'service1', category = self.category)
        # Create a requirement that in the requested state
        # We require that all requirements in the requested state have been resolved as
        # approved or rejected before returning to the user for changes
        Requirement.objects.create(
            service = service,
            resource = self.resource,
            status = Requirement.Status.REQUESTED,
            amount = 100
        )
        # Make another requirement that is in the rejected state, so that the project
        # would be returned without the requested requirement
        Requirement.objects.create(
            service = service,
            resource = self.resource,
            status = Requirement.Status.REJECTED,
            amount = 100
        )
        # Then check that it cannot be returned for changes
        response_data = self.assertConflict(
            "/projects/{}/request_changes/".format(project.pk),
            "POST",
            dict(comment = "Requesting changes.")
        )
        # Check that the error code is what we expected
        self.assertEqual(response_data['code'], 'unresolved_requirements')
        # Verify that the state is still under review
        project.refresh_from_db()
        self.assertEqual(project.status, Project.Status.UNDER_REVIEW)
        # Check that no comment was created
        self.assertEqual(project.comments.count(), 0)

    def test_request_changes_not_allowed_without_rejected_requirements(self):
        """
        Tests that a project cannot be returned for changes without a rejected requirement.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsConsortiumManager(project.consortium)
        project.status = Project.Status.UNDER_REVIEW
        project.save()
        # Create a requirement that is not in the required or rejected state, to test that this only
        # depends on rejected requirements
        Requirement.objects.create(
            service = project.services.create(name = 'service1', category = self.category),
            resource = self.resource,
            status = Requirement.Status.APPROVED,
            amount = 100
        )
        # Then check that it cannot be returned for changes
        response_data = self.assertConflict(
            "/projects/{}/request_changes/".format(project.pk),
            "POST",
            dict(comment = "Requesting changes.")
        )
        # Check that the error code is what we expected
        self.assertEqual(response_data['code'], 'no_changes_required')
        # Verify that the state is still under review
        project.refresh_from_db()
        self.assertEqual(project.status, Project.Status.UNDER_REVIEW)
        # Check that no comment was created
        self.assertEqual(project.comments.count(), 0)

    def test_request_changes_not_permitted_for_contributor(self):
        """
        Tests that a contributor cannot request changes to a project.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectContributor(project)
        # This should be permission denied since the user can view the project
        self.assertPermissionDenied(
            "/projects/{}/request_changes/".format(project.pk),
            "POST"
        )

    def test_request_changes_not_permitted_for_owner(self):
        """
        Tests that an owner cannot request changes to a project.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        # This should be permission denied since the user can view the project
        self.assertPermissionDenied(
            "/projects/{}/request_changes/".format(project.pk),
            "POST"
        )

    def test_request_changes_not_permitted_for_authenticated_user(self):
        """
        Tests that an authenticated user cannot request changes to a project that
        they are not associated with.
        """
        project = Project.objects.order_by('?').first()
        self.authenticate()
        # This should be not found since the user cannot view the project at all
        self.assertNotFound(
            "/projects/{}/request_changes/".format(project.pk),
            "POST"
        )

    def test_request_changes_requires_authentication(self):
        """
        Tests that requesting changes to a project requires authentication.
        """
        project = Project.objects.order_by('?').first()
        self.assertUnauthorized(
            "/projects/{}/request_changes/".format(project.pk),
            "POST"
        )

    def test_submit_for_provisioning_allowed_methods(self):
        """
        Tests that the correct methods are permitted by the submit_for_provisioning endpoint.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsConsortiumManager(project.consortium)
        self.assertAllowedMethods(
            "/projects/{}/submit_for_provisioning/".format(project.pk),
            {'OPTIONS', 'POST'}
        )

    def test_submit_for_provisioning_under_review_with_approved_requirement(self):
        """
        Tests that a project in the under review status with an approved requirement
        can be submitted for provisioning.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsConsortiumManager(project.consortium)
        # Put the project into the expected state
        project.status = Project.Status.UNDER_REVIEW
        project.save()
        requirement = Requirement.objects.create(
            service = project.services.create(name = 'service1', category = self.category),
            resource = self.resource,
            status = Requirement.Status.APPROVED,
            amount = 100
        )
        # Attempt to return for changes
        self.assertActionResponseMatchesUpdatedInstance(
            "/projects/{}/submit_for_provisioning/".format(project.pk),
            project,
            None,
            ProjectSerializer
        )
        # Verify that the project is now editable
        self.assertEqual(project.status, Project.Status.EDITABLE)
        # Verify that the requirement is now awaiting provisioning
        requirement.refresh_from_db()
        self.assertEqual(requirement.status, Requirement.Status.AWAITING_PROVISIONING)

    def test_submit_for_provisioning_only_permitted_for_status_under_review(self):
        """
        Tests that a project can only submitted for provisioning when it is under review.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsConsortiumManager(project.consortium)
        for status in Project.Status:
            if status == Project.Status.UNDER_REVIEW:
                continue
            # Put the project into the given state
            project.status = status
            project.save()
            # Then check that it cannot be returned for changes
            response_data = self.assertConflict(
                "/projects/{}/submit_for_provisioning/".format(project.pk),
                "POST"
            )
            # Check that the error code is what we expected
            self.assertEqual(response_data['code'], 'invalid_status')
            # Check that the state in the DB was not changed
            project.refresh_from_db()
            self.assertEqual(project.status, status)

    def test_submit_for_provisioning_not_allowed_with_requested_requirements(self):
        """
        Tests that a project cannot be submitted for provisioning with unresolved requested
        requirements.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsConsortiumManager(project.consortium)
        # Put the project into the review state
        project.status = Project.Status.UNDER_REVIEW
        project.save()
        # Create a requirement in the requested state
        # We require that all requirements in the requested state have been resolved as
        # approved before submitting a project for provisioning
        Requirement.objects.create(
            service = project.services.create(name = 'service1', category = self.category),
            resource = self.resource,
            status = Requirement.Status.REQUESTED,
            amount = 100
        )
        # Then check that it cannot be returned for changes
        response_data = self.assertConflict(
            "/projects/{}/submit_for_provisioning/".format(project.pk),
            "POST"
        )
        # Check that the error code is what we expected
        self.assertEqual(response_data['code'], 'unapproved_requirements')
        # Verify that the state is still under review
        project.refresh_from_db()
        self.assertEqual(project.status, Project.Status.UNDER_REVIEW)

    def test_submit_for_provisioning_not_allowed_with_rejected_requirements(self):
        """
        Tests that a project cannot be submitted for provisioning with rejected requirements.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsConsortiumManager(project.consortium)
        # Put the project into the review state
        project.status = Project.Status.UNDER_REVIEW
        project.save()
        # Create a requirement in the rejected state
        # We require that all requirements in the requested state have been resolved as
        # approved before submitting a project for provisioning
        Requirement.objects.create(
            service = project.services.create(name = 'service1', category = self.category),
            resource = self.resource,
            status = Requirement.Status.REJECTED,
            amount = 100
        )
        # Then check that it cannot be returned for changes
        response_data = self.assertConflict(
            "/projects/{}/submit_for_provisioning/".format(project.pk),
            "POST"
        )
        # Check that the error code is what we expected
        self.assertEqual(response_data['code'], 'unapproved_requirements')
        # Verify that the state is still under review
        project.refresh_from_db()
        self.assertEqual(project.status, Project.Status.UNDER_REVIEW)

    def test_submit_for_provisioning_not_permitted_for_contributor(self):
        """
        Tests that a contributor cannot submit a project for provisioning.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectContributor(project)
        # This should be permission denied since the user can view the project
        self.assertPermissionDenied(
            "/projects/{}/submit_for_provisioning/".format(project.pk),
            "POST"
        )

    def test_submit_for_provisioning_not_permitted_for_owner(self):
        """
        Tests that an owner cannot submit a project for provisioning.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        # This should be permission denied since the user can view the project
        self.assertPermissionDenied(
            "/projects/{}/submit_for_provisioning/".format(project.pk),
            "POST"
        )

    def test_submit_for_provisioning_not_permitted_for_authenticated_user(self):
        """
        Tests that an authenticated user cannot submit a project for provisioning that
        they are not associated with.
        """
        project = Project.objects.order_by('?').first()
        self.authenticate()
        # This should be not found since the user cannot view the project at all
        self.assertNotFound(
            "/projects/{}/submit_for_provisioning/".format(project.pk),
            "POST"
        )

    def test_submit_for_provisioning_requires_authentication(self):
        """
        Tests that submitting a project for provisioning requires authentication.
        """
        project = Project.objects.order_by('?').first()
        self.assertUnauthorized(
            "/projects/{}/submit_for_provisioning/".format(project.pk),
            "POST"
        )


class ProjectCollaboratorsViewSetTestCase(TestCase):
    """
    Tests for the project collaborators viewset.
    """
    @classmethod
    def setUpTestData(cls):
        cls.consortium = Consortium.objects.create(
            name = 'Consortium 1',
            manager = get_user_model().objects.create_user('manager1')
        )
        projects = [
            cls.consortium.projects.create(
                name = f'Project {i}',
                description = 'some description',
                owner = get_user_model().objects.create_user(f'owner{i}')
            )
            for i in range(10)
        ]
        # Create some more collaborators for random projects
        for i in range(20):
            projects[random.randrange(10)].collaborators.create(
                user = get_user_model().objects.create_user(f'contributor{i}'),
                role = Collaborator.Role.CONTRIBUTOR
            )

    def test_allowed_methods(self):
        """
        Tests that the correct methods are permitted for the endpoint.
        """
        # Pick a random but valid project to use in the endpoint
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        self.assertAllowedMethods(
            "/projects/{}/collaborators/".format(project.pk),
            {'OPTIONS', 'HEAD', 'GET'}
        )

    def test_list_project_owner(self):
        """
        Tests that a project owner can list the collaborators for a project.
        """
        # Pick a random but valid project to use in the endpoint
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        self.assertListResponseMatchesQuerySet(
            "/projects/{}/collaborators/".format(project.pk),
            project.collaborators.all(),
            CollaboratorSerializer
        )

    def test_list_project_contributor(self):
        """
        Tests that a project contributor can list the collaborators for a project.
        """
        # Pick a random but valid project to use in the endpoint
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectContributor(project)
        self.assertListResponseMatchesQuerySet(
            "/projects/{}/collaborators/".format(project.pk),
            project.collaborators.all(),
            CollaboratorSerializer
        )

    def test_list_consortium_manager(self):
        """
        Tests that the consortium manager can list the collaborators for a project.
        """
        # Pick a random but valid project to use in the endpoint
        project = Project.objects.order_by('?').first()
        self.authenticateAsConsortiumManager(project.consortium)
        self.assertListResponseMatchesQuerySet(
            "/projects/{}/collaborators/".format(project.pk),
            project.collaborators.all(),
            CollaboratorSerializer
        )

    def test_list_not_permitted_authenticated_user(self):
        """
        Tests that an authenticated user that is not associated with the project cannot
        list the collaborators.
        """
        project = Project.objects.order_by('?').first()
        self.authenticate()
        # The user is not permitted to view the project, so should get not found
        self.assertNotFound("/projects/{}/collaborators/".format(project.pk))

    def test_list_requires_authentication(self):
        """
        Tests that listing collaborators for a project requires authentication.
        """
        project = Project.objects.order_by('?').first()
        # The user is not permitted to view the project, so should get not found
        self.assertUnauthorized("/projects/{}/collaborators/".format(project.pk))

    def test_list_invalid_project(self):
        """
        Tests that a list response for an invalid project returns not found.
        """
        self.authenticate()
        self.assertNotFound("/projects/100/collaborators/")


class ProjectCommentsViewSetTestCase(TestCase):
    """
    Tests for the project comments viewset.
    """
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name = 'Category 1')
        cls.consortium = Consortium.objects.create(
            name = 'Consortium 1',
            manager = get_user_model().objects.create_user('manager1')
        )
        project_owners = [
            get_user_model().objects.create_user(f'owner{i}')
            for i in range(10)
        ]
        projects = [
            cls.consortium.projects.create(
                name = f'Project {i}',
                description = 'some description',
                owner = project_owners[i]
            )
            for i in range(10)
        ]
        # Create between 1 and 3 comments for each project
        for i, project in enumerate(projects):
            for j in range(random.randint(1, 3)):
                project.comments.create(
                    content = f'Comment {j} content.',
                    user = project_owners[i]
                )

    def test_allowed_methods(self):
        """
        Tests that the correct methods are permitted for the endpoint.
        """
        # Pick a random but valid project to use in the endpoint
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        self.assertAllowedMethods(
            "/projects/{}/comments/".format(project.pk),
            {'OPTIONS', 'HEAD', 'GET', 'POST'}
        )

    def test_list_project_owner(self):
        """
        Tests that a project owner can list the comments for a project.
        """
        # Pick a random but valid project to use in the endpoint
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        self.assertListResponseMatchesQuerySet(
            "/projects/{}/comments/".format(project.pk),
            project.comments.all(),
            CommentSerializer
        )

    def test_list_project_contributor(self):
        """
        Tests that a project contributor can list the comments for a project.
        """
        # Pick a random but valid project to use in the endpoint
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectContributor(project)
        self.assertListResponseMatchesQuerySet(
            "/projects/{}/comments/".format(project.pk),
            project.comments.all(),
            CommentSerializer
        )

    def test_list_consortium_manager(self):
        """
        Tests that the consortium manager can list the comments for a project.
        """
        # Pick a random but valid project to use in the endpoint
        project = Project.objects.order_by('?').first()
        self.authenticateAsConsortiumManager(project.consortium)
        self.assertListResponseMatchesQuerySet(
            "/projects/{}/comments/".format(project.pk),
            project.comments.all(),
            CommentSerializer
        )

    def test_list_not_permitted_authenticated_user(self):
        """
        Tests that an authenticated user that is not associated with the project cannot
        list the comments.
        """
        project = Project.objects.order_by('?').first()
        self.authenticate()
        # The user is not permitted to view the project, so should get not found
        self.assertNotFound("/projects/{}/comments/".format(project.pk))

    def test_list_requires_authentication(self):
        """
        Tests that listing comments for a project requires authentication.
        """
        project = Project.objects.order_by('?').first()
        # The user is not permitted to view the project, so should get not found
        self.assertUnauthorized("/projects/{}/comments/".format(project.pk))

    def test_list_invalid_project(self):
        """
        Tests that a list response for an invalid project returns not found.
        """
        self.authenticate()
        self.assertNotFound("/projects/100/comments/")

    def test_create_as_consortium_manager(self):
        """
        Tests that a consortium manager can create a comment.
        """
        project = Project.objects.order_by('?').first()
        user = self.authenticateAsConsortiumManager(project.consortium)
        comment = self.assertCreateResponseMatchesCreatedInstance(
            "/projects/{}/comments/".format(project.pk),
            dict(content = "Comment content."),
            CommentSerializer
        )
        self.assertEqual(comment.project.pk, project.pk)
        self.assertEqual(comment.user.pk, user.pk)
        self.assertEqual(comment.content, "Comment content.")

    def test_create_as_project_owner(self):
        """
        Tests that a project owner can create a comment.
        """
        project = Project.objects.order_by('?').first()
        user = self.authenticateAsProjectOwner(project)
        comment = self.assertCreateResponseMatchesCreatedInstance(
            "/projects/{}/comments/".format(project.pk),
            dict(content = "Comment content."),
            CommentSerializer
        )
        self.assertEqual(comment.project.pk, project.pk)
        self.assertEqual(comment.user.pk, user.pk)
        self.assertEqual(comment.content, "Comment content.")

    def test_create_as_project_contributor(self):
        """
        Tests that a project contributor can create a comment.
        """
        project = Project.objects.order_by('?').first()
        user = self.authenticateAsProjectContributor(project)
        comment = self.assertCreateResponseMatchesCreatedInstance(
            "/projects/{}/comments/".format(project.pk),
            dict(content = "Comment content."),
            CommentSerializer
        )
        self.assertEqual(comment.project.pk, project.pk)
        self.assertEqual(comment.user.pk, user.pk)
        self.assertEqual(comment.content, "Comment content.")

    def test_create_enforces_required_fields_present(self):
        """
        Tests that the required fields are enforced on create.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        response_data = self.assertBadRequest(
            "/projects/{}/comments/".format(project.pk),
            "POST",
            dict()
        )
        self.assertCountEqual(response_data.keys(), {'content'})
        self.assertEqual(response_data['content'][0]['code'], 'required')

    def test_cannot_create_with_blank_content(self):
        """
        Tests that creating with blank content correctly fails.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        response_data = self.assertBadRequest(
            "/projects/{}/comments/".format(project.pk),
            "POST",
            dict(content = "")
        )
        self.assertCountEqual(response_data.keys(), {'content'})
        self.assertEqual(response_data['content'][0]['code'], 'blank')

    def test_create_cannot_override_project(self):
        """
        Tests that the project cannot be overridden by specifying it in the input data.
        """
        project = Project.objects.get(pk = 1)
        self.authenticateAsProjectOwner(project)
        other_project = Project.objects.get(pk = 2)
        # Create the comment
        # It should create successfully, but the comment should belong to the project
        # in the URL, not the one in the input data
        comment = self.assertCreateResponseMatchesCreatedInstance(
            "/projects/{}/comments/".format(project.pk),
            dict(content = "Comment content.", project = other_project.pk),
            CommentSerializer
        )
        # Check that the service belongs to the correct project
        self.assertEqual(comment.project.pk, project.pk)

    def test_create_cannot_override_project(self):
        """
        Tests that the user cannot be overridden by specifying it in the input data.
        """
        project = Project.objects.order_by('?').first()
        user = self.authenticateAsProjectOwner(project)
        other_user = get_user_model().objects.create_user('otheruser')
        # Create the comment
        # It should create successfully, but the comment should belong to the authenticated
        # user, not the one in the input data
        comment = self.assertCreateResponseMatchesCreatedInstance(
            "/projects/{}/comments/".format(project.pk),
            dict(content = "Comment content.", user = other_user.pk),
            CommentSerializer
        )
        # Check that the service belongs to the correct project
        self.assertEqual(comment.user.pk, user.pk)

    def test_create_not_permitted_for_authenticated_user(self):
        """
        Tests that an authenticated user who is not associated with the project
        cannot create a comment.
        """
        self.authenticate()
        project = Project.objects.order_by('?').first()
        # This should be not found as the user cannot see the project
        self.assertNotFound(
            "/projects/{}/comments/".format(project.pk),
            "POST",
            dict(content = "Comment content."),
        )

    def test_create_requires_authentication(self):
        """
        Tests that an unauthenticated user cannot create a comment.
        """
        project = Project.objects.order_by('?').first()
        # This should be unauthorized as the endpoint requires authentication
        self.assertUnauthorized(
            "/projects/{}/comments/".format(project.pk),
            "POST",
            dict(content = "Comment content."),
        )


class ProjectInvitationsViewSetTestCase(TestCase):
    """
    Tests for the project invitations viewset.
    """
    @classmethod
    def setUpTestData(cls):
        cls.consortium = Consortium.objects.create(
            name = 'Consortium 1',
            manager = get_user_model().objects.create_user('manager1')
        )
        projects = [
            cls.consortium.projects.create(
                name = f'Project {i}',
                description = 'some description',
                owner = get_user_model().objects.create_user(f'owner{i}')
            )
            for i in range(10)
        ]
        # Create between 1 and 3 invitations for each project
        for i, project in enumerate(projects):
            for j in range(random.randint(1, 3)):
                project.invitations.create(email = f'user{i}@university{j}.ac.uk')

    def test_allowed_methods(self):
        """
        Tests that the correct methods are permitted for the endpoint.
        """
        # Pick a random but valid project to use in the endpoint
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        self.assertAllowedMethods(
            "/projects/{}/invitations/".format(project.pk),
            {'OPTIONS', 'HEAD', 'GET', 'POST'}
        )

    def test_list_project_owner(self):
        """
        Tests that a project owner can list the invitations for a project.
        """
        # Pick a random but valid project to use in the endpoint
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        self.assertListResponseMatchesQuerySet(
            "/projects/{}/invitations/".format(project.pk),
            project.invitations.all(),
            InvitationSerializer
        )

    def test_list_project_contributor(self):
        """
        Tests that a project contributor can list the invitations for a project.
        """
        # Pick a random but valid project to use in the endpoint
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectContributor(project)
        self.assertListResponseMatchesQuerySet(
            "/projects/{}/invitations/".format(project.pk),
            project.invitations.all(),
            InvitationSerializer
        )

    def test_list_consortium_manager(self):
        """
        Tests that the consortium manager can list the invitations for a project.
        """
        # Pick a random but valid project to use in the endpoint
        project = Project.objects.order_by('?').first()
        self.authenticateAsConsortiumManager(project.consortium)
        self.assertListResponseMatchesQuerySet(
            "/projects/{}/invitations/".format(project.pk),
            project.invitations.all(),
            InvitationSerializer
        )

    def test_list_not_permitted_authenticated_user(self):
        """
        Tests that an authenticated user that is not associated with the project cannot
        list the invitations.
        """
        project = Project.objects.order_by('?').first()
        self.authenticate()
        # The user is not permitted to view the project, so should get not found
        self.assertNotFound("/projects/{}/invitations/".format(project.pk))

    def test_list_requires_authentication(self):
        """
        Tests that listing invitations for a project requires authentication.
        """
        project = Project.objects.order_by('?').first()
        self.assertUnauthorized("/projects/{}/invitations/".format(project.pk))

    def test_list_invalid_project(self):
        """
        Tests that a list response for an invalid project returns not found.
        """
        self.authenticate()
        self.assertNotFound("/projects/100/invitations/")

    def test_create_as_project_owner(self):
        """
        Tests that a project owner can create a invitation.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        invitation = self.assertCreateResponseMatchesCreatedInstance(
            "/projects/{}/invitations/".format(project.pk),
            dict(email = 'joe.bloggs@example.com'),
            InvitationSerializer
        )
        self.assertEqual(invitation.project.pk, project.pk)
        self.assertEqual(invitation.email, 'joe.bloggs@example.com')

    def test_create_enforces_required_fields_present(self):
        """
        Tests that the required fields are enforced on create.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        response_data = self.assertBadRequest(
            "/projects/{}/invitations/".format(project.pk),
            "POST",
            dict()
        )
        self.assertCountEqual(response_data.keys(), {'email'})
        self.assertEqual(response_data['email'][0]['code'], 'required')

    def test_create_cannot_override_project(self):
        """
        Tests that the project cannot be overridden by specifying it in the input data.
        """
        project = Project.objects.get(pk = 1)
        self.authenticateAsProjectOwner(project)
        other_project = Project.objects.get(pk = 2)
        # Create the invitation
        # It should create successfully, but the invitation should belong to the project
        # in the URL, not the one in the input data
        invitation = self.assertCreateResponseMatchesCreatedInstance(
            "/projects/{}/invitations/".format(project.pk),
            dict(
                email = 'joe.bloggs@example.com',
                project = other_project.pk
            ),
            InvitationSerializer
        )
        # Check that the service belongs to the correct project
        self.assertEqual(invitation.project.pk, project.pk)

    def test_cannot_create_email_already_collaborator(self):
        """
        Tests that an invitation cannot be created if a user with the same email
        address is already a collaborator.
        """
        project = Project.objects.get(pk = 1)
        self.authenticateAsProjectOwner(project)
        # Make a collaborator with the same email address that we will use,
        # but with different capitalisation
        user = get_user_model().objects.create_user('jbloggs', email = 'Joe.Bloggs@example.com')
        project.collaborators.create(user = user)
        # Try to make an invitation with the same email address
        response_data = self.assertBadRequest(
            "/projects/{}/invitations/".format(project.pk),
            "POST",
            dict(email = 'joe.bloggs@example.com')
        )
        self.assertCountEqual(response_data.keys(), {'email'})
        self.assertEqual(response_data['email'][0]['code'], 'invalid')

    def test_cannot_create_email_already_invited(self):
        """
        Tests that an invitation cannot be created if an invitation with the same email
        address already exists.
        """
        project = Project.objects.get(pk = 1)
        self.authenticateAsProjectOwner(project)
        # Make an invitation with the same email address, but with different capitalisation
        project.invitations.create(email = 'Joe.Bloggs@example.com')
        # Try to make an invitation with the same email address
        response_data = self.assertBadRequest(
            "/projects/{}/invitations/".format(project.pk),
            "POST",
            dict(email = 'joe.bloggs@example.com')
        )
        self.assertCountEqual(response_data.keys(), {'email'})
        self.assertEqual(response_data['email'][0]['code'], 'invalid')

    def test_create_not_permitted_for_project_contributor(self):
        """
        Tests that a project contributor cannot create an invitation.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectContributor(project)
        # This should be permission denied as the user can see the project
        self.assertPermissionDenied(
            "/projects/{}/invitations/".format(project.pk),
            "POST",
            dict(email = 'joe.bloggs@example.com')
        )

    def test_create_not_permitted_for_consortium_manager(self):
        """
        Tests that a consortium manager cannot create an invitation.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsConsortiumManager(project.consortium)
        # This should be permission denied as the user can see the project
        self.assertPermissionDenied(
            "/projects/{}/invitations/".format(project.pk),
            "POST",
            dict(email = 'joe.bloggs@example.com')
        )

    def test_create_not_permitted_for_authenticated_user(self):
        """
        Tests that an authenticated user who is not associated with the project
        cannot create an invitation.
        """
        self.authenticate()
        project = Project.objects.order_by('?').first()
        # This should be not found as the user cannot see the project
        self.assertNotFound(
            "/projects/{}/invitations/".format(project.pk),
            "POST",
            dict(email = 'joe.bloggs@example.com')
        )

    def test_create_requires_authentication(self):
        """
        Tests that an unauthenticated user cannot create an invitation.
        """
        project = Project.objects.order_by('?').first()
        # This should be unauthorized as the endpoint requires authentication
        self.assertUnauthorized(
            "/projects/{}/invitations/".format(project.pk),
            "POST",
            dict(email = 'joe.bloggs@example.com')
        )


class ProjectServicesViewSetTestCase(TestCase):
    """
    Tests for the project services viewset.
    """
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name = 'Category 1')
        cls.consortium = Consortium.objects.create(
            name = 'Consortium 1',
            manager = get_user_model().objects.create_user('manager1')
        )
        projects = [
            cls.consortium.projects.create(
                name = f'Project {i}',
                description = 'some description',
                owner = get_user_model().objects.create_user(f'owner{i}')
            )
            for i in range(10)
        ]
        # Create between 1 and 3 services for each project
        for i, project in enumerate(projects):
            for j in range(random.randint(1, 3)):
                project.services.create(name = f'project{i}service{j}', category = cls.category)

    def test_allowed_methods(self):
        """
        Tests that the correct methods are permitted for the endpoint.
        """
        # Pick a random but valid project to use in the endpoint
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        self.assertAllowedMethods(
            "/projects/{}/services/".format(project.pk),
            {'OPTIONS', 'HEAD', 'GET', 'POST'}
        )

    def test_list_project_owner(self):
        """
        Tests that a project owner can list the services for a project.
        """
        # Pick a random but valid project to use in the endpoint
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        self.assertListResponseMatchesQuerySet(
            "/projects/{}/services/".format(project.pk),
            project.services.all(),
            ServiceSerializer
        )

    def test_list_project_contributor(self):
        """
        Tests that a project contributor can list the services for a project.
        """
        # Pick a random but valid project to use in the endpoint
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectContributor(project)
        self.assertListResponseMatchesQuerySet(
            "/projects/{}/services/".format(project.pk),
            project.services.all(),
            ServiceSerializer
        )

    def test_list_consortium_manager(self):
        """
        Tests that the consortium manager can list the services for a project.
        """
        # Pick a random but valid project to use in the endpoint
        project = Project.objects.order_by('?').first()
        self.authenticateAsConsortiumManager(project.consortium)
        self.assertListResponseMatchesQuerySet(
            "/projects/{}/services/".format(project.pk),
            project.services.all(),
            ServiceSerializer
        )

    def test_list_not_permitted_authenticated_user(self):
        """
        Tests that an authenticated user that is not associated with the project cannot
        list the services.
        """
        project = Project.objects.order_by('?').first()
        self.authenticate()
        # The user is not permitted to view the project, so should get not found
        self.assertNotFound("/projects/{}/services/".format(project.pk))

    def test_list_requires_authentication(self):
        """
        Tests that listing services for a project requires authentication.
        """
        project = Project.objects.order_by('?').first()
        # The user is not permitted to view the project, so should get not found
        self.assertUnauthorized("/projects/{}/services/".format(project.pk))

    def test_list_invalid_project(self):
        """
        Tests that a list response for an invalid project returns not found.
        """
        self.authenticate()
        self.assertNotFound("/projects/100/services/")

    def test_create_as_project_owner(self):
        """
        Tests that a project owner can create a service.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        service = self.assertCreateResponseMatchesCreatedInstance(
            "/projects/{}/services/".format(project.pk),
            dict(name = "service1", category = self.category.pk),
            ServiceSerializer
        )
        self.assertEqual(service.project.pk, project.pk)
        self.assertEqual(service.category.pk, self.category.pk)
        self.assertEqual(service.name, "service1")

    def test_create_as_project_contributor(self):
        """
        Tests that a project contributor can create a service.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectContributor(project)
        service = self.assertCreateResponseMatchesCreatedInstance(
            "/projects/{}/services/".format(project.pk),
            dict(name = "service1", category = self.category.pk),
            ServiceSerializer
        )
        self.assertEqual(service.project.pk, project.pk)
        self.assertEqual(service.category.pk, self.category.pk)
        self.assertEqual(service.name, "service1")

    def test_create_enforces_required_fields_present(self):
        """
        Tests that the required fields are enforced on create.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        response_data = self.assertBadRequest(
            "/projects/{}/services/".format(project.pk),
            "POST",
            dict()
        )
        required_fields = {'name', 'category'}
        self.assertCountEqual(response_data.keys(), required_fields)
        for name in required_fields:
            self.assertEqual(response_data[name][0]['code'], 'required')

    def test_cannot_create_with_same_category_and_name(self):
        """
        Tests that the unique together constraint on category and name is enforced during create.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        # Create an initial service
        project.services.create(name = "service1", category = self.category)
        # Then try to make the same service using the API
        response_data = self.assertBadRequest(
            "/projects/{}/services/".format(project.pk),
            "POST",
            dict(name = "service1", category = self.category.pk)
        )
        self.assertCountEqual(response_data.keys(), {'name'})
        self.assertEqual(response_data['name'][0]['code'], 'unique')

    def test_create_cannot_override_project(self):
        """
        Tests that the project cannot be overridden by specifying it in the input data.
        """
        project = Project.objects.get(pk = 1)
        self.authenticateAsProjectOwner(project)
        other_project = Project.objects.get(pk = 2)
        # Create the service
        # It should create successfully, but the service should belong to the project
        # in the URL, not the one in the input data
        service = self.assertCreateResponseMatchesCreatedInstance(
            "/projects/{}/services/".format(project.pk),
            dict(
                name = "service1",
                category = self.category.pk,
                project = other_project.pk
            ),
            ServiceSerializer
        )
        # Check that the service belongs to the correct project
        self.assertEqual(service.project.pk, project.pk)

    def test_cannot_create_with_invalid_category(self):
        """
        Tests that an invalid category correctly fails.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        response_data = self.assertBadRequest(
            "/projects/{}/services/".format(project.pk),
            "POST",
            dict(name = "service1", category = 10)
        )
        self.assertCountEqual(response_data.keys(), {'category'})
        self.assertEqual(response_data['category'][0]['code'], 'does_not_exist')

    def test_cannot_create_with_invalid_name(self):
        """
        Tests that an invalid name correctly fails.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        # Test with a blank name
        response_data = self.assertBadRequest(
            "/projects/{}/services/".format(project.pk),
            "POST",
            dict(name = "", category = self.category.pk)
        )
        self.assertCountEqual(response_data.keys(), {'name'})
        self.assertEqual(response_data['name'][0]['code'], 'blank')
        # Test with whitespace
        response_data = self.assertBadRequest(
            "/projects/{}/services/".format(project.pk),
            "POST",
            dict(name = "service 1", category = self.category.pk)
        )
        self.assertCountEqual(response_data.keys(), {'name'})
        self.assertEqual(response_data['name'][0]['code'], 'invalid')
        # Test with unicode characters
        response_data = self.assertBadRequest(
            "/projects/{}/services/".format(project.pk),
            "POST",
            dict(name = "sèrvíçë1", category = self.category.pk)
        )
        self.assertCountEqual(response_data.keys(), {'name'})
        self.assertEqual(response_data['name'][0]['code'], 'invalid')

    def test_create_only_permitted_for_status_editable(self):
        """
        Tests that services can only be created for an editable project.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsProjectOwner(project)
        num_services = project.services.count()
        for status in Project.Status:
            if status == Project.Status.EDITABLE:
                continue
            # Put the project into the given state
            project.status = status
            project.save()
            # Then check that it cannot be returned for changes
            response_data = self.assertConflict(
                "/projects/{}/services/".format(project.pk),
                "POST"
            )
            # Check that the error code is what we expected
            self.assertEqual(response_data['code'], 'invalid_status')
            # Check that the number of services didn't change
            project.refresh_from_db()
            self.assertEqual(project.services.count(), num_services)

    def test_create_not_permitted_for_consortium_manager(self):
        """
        Tests that a consortium manager cannot create a service.
        """
        project = Project.objects.order_by('?').first()
        self.authenticateAsConsortiumManager(project.consortium)
        # This should be permission denied as the user can see the project
        self.assertPermissionDenied(
            "/projects/{}/services/".format(project.pk),
            "POST",
            dict(name = "service1", category = self.category.pk),
        )

    def test_create_not_permitted_for_authenticated_user(self):
        """
        Tests that an authenticated user who is not associated with the project
        cannot create a service.
        """
        self.authenticate()
        project = Project.objects.order_by('?').first()
        # This should be not found as the user cannot see the project
        self.assertNotFound(
            "/projects/{}/services/".format(project.pk),
            "POST",
            dict(name = "service1", category = self.category.pk),
        )

    def test_create_requires_authentication(self):
        """
        Tests that an unauthenticated user cannot create a service.
        """
        project = Project.objects.order_by('?').first()
        # This should be unauthorized as the endpoint requires authentication
        self.assertUnauthorized(
            "/projects/{}/services/".format(project.pk),
            "POST",
            dict(name = "service1", category = self.category.pk),
        )
