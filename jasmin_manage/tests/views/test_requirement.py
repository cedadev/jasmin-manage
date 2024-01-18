from datetime import date
import random

from dateutil.relativedelta import relativedelta

from django.contrib.auth import get_user_model

from rest_framework.test import APITestCase
from rest_framework import viewsets

from ...models import (
    Category,
    Collaborator,
    Consortium,
    Project,
    Requirement,
    Resource,
    Service,
)
from ...serializers import RequirementSerializer

from .utils import TestCase


class RequirementViewSetTestCase(TestCase):
    """
    Tests for the requirement viewset.
    """

    @classmethod
    def setUpTestData(cls):
        category = Category.objects.create(name="Category 1")
        consortium = Consortium.objects.create(
            name="Consortium 1",
            manager=get_user_model().objects.create_user("manager1"),
        )
        cls.resources = [
            Resource.objects.create(name=f"Resource {i}") for i in range(10)
        ]
        # Create 10 projects
        projects = [
            consortium.projects.create(
                name=f"Project {i}",
                description="some description",
                owner=get_user_model().objects.create_user(f"owner{i}"),
            )
            for i in range(10)
        ]
        # Create between 1 and 3 services for each project
        cls.services = [
            project.services.create(name=f"project{i}service{j}", category=category)
            for j in range(random.randint(1, 3))
            for i, project in enumerate(projects)
        ]

    def setUp(self):
        # Create requirements here rather than setUpTestData so we can modify them
        # without affecting other tests
        # We create between 1 and 5 requests for each service
        Requirement.objects.bulk_create(
            [
                Requirement(
                    service=service,
                    resource=random.choice(self.resources),
                    amount=random.randint(1, 1000),
                )
                for service in self.services
                for i in range(random.randint(1, 5))
            ]
        )

    def test_list_not_found(self):
        """
        Requirements can only be listed via a service, so check that the list endpoint is not found.
        """
        self.assertNotFound("/requirements/")

    def test_detail_allowed_methods(self):
        """
        Tests that the correct methods are permitted by the detail endpoint.
        """
        # Pick a random but valid requirement to use in the detail and extra actions
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsProjectOwner(requirement.service.project)
        self.assertAllowedMethods(
            "/requirements/{}/".format(requirement.pk),
            {"OPTIONS", "HEAD", "GET", "PUT", "PATCH", "DELETE"},
        )

    def test_detail_project_owner(self):
        """
        Tests that the detail endpoint successfully retrieves a valid requirement
        when the authenticated user is a project owner.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsProjectOwner(requirement.service.project)
        self.assertDetailResponseMatchesInstance(
            "/requirements/{}/".format(requirement.pk),
            requirement,
            RequirementSerializer,
        )

    def test_detail_project_contributor(self):
        """
        Tests that the detail endpoint successfully retrieves a valid requirement
        when the authenticated user is a project contributor.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsProjectContributor(requirement.service.project)
        self.assertDetailResponseMatchesInstance(
            "/requirements/{}/".format(requirement.pk),
            requirement,
            RequirementSerializer,
        )

    def test_detail_consortium_manager(self):
        """
        Tests that the detail endpoint successfully retrieves a valid requirement
        when the authenticated user is a project contributor.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsConsortiumManager(requirement.service.project.consortium)
        self.assertDetailResponseMatchesInstance(
            "/requirements/{}/".format(requirement.pk),
            requirement,
            RequirementSerializer,
        )

    def test_detail_authenticated_not_collaborator(self):
        """
        Tests that the detail endpoint returns not found when the user is authenticated
        but does not have permission to view the requirement.
        """
        self.authenticate()
        requirement = Requirement.objects.order_by("?").first()
        self.assertNotFound("/requirements/{}/".format(requirement.pk))

    def test_detail_unauthenticated(self):
        """
        Tests that the detail endpoint returns unauthorized when an unauthenticated
        user attempts to access a valid requirement.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.assertUnauthorized("/requirements/{}/".format(requirement.pk))

    def test_detail_missing(self):
        """
        Tests that the detail endpoint correctly reports not found for invalid requirement.
        """
        self.authenticate()
        self.assertNotFound("/requirements/100/")

    def test_update_as_project_owner(self):
        """
        Tests that the amount can be updated by a project owner without updating the dates,
        even if the start date is in the past.

        Also verify that this puts the requirement back into the requested state.
        """
        # Make a requirement with a start date in the past for testing
        start_date = date.today() - relativedelta(months=3)
        requirement = Requirement.objects.create(
            service=random.choice(self.services),
            resource=random.choice(self.resources),
            status=Requirement.Status.REJECTED,
            amount=250,
            start_date=start_date,
        )
        self.authenticateAsProjectOwner(requirement.service.project)
        self.assertUpdateResponseMatchesUpdatedInstance(
            "/requirements/{}/".format(requirement.pk),
            requirement,
            dict(amount=500),
            RequirementSerializer,
        )
        # Test that the instance was updated in the expected way
        # Note that the instance was refreshed as part of the assert
        #   Verify that the amount was updated
        self.assertEqual(requirement.amount, 500)
        #   Verify that the start date stayed the same
        self.assertEqual(requirement.start_date, start_date)
        #   Verify that the requirement was put back into the requested state
        self.assertEqual(requirement.status, Requirement.Status.REQUESTED)

    def test_update_as_project_contributor(self):
        """
        Tests that the amount can be updated by a project contributor.
        """
        # Make a requirement with a start date in the past for testing
        start_date = date.today() - relativedelta(months=3)
        requirement = Requirement.objects.create(
            service=random.choice(self.services),
            resource=random.choice(self.resources),
            status=Requirement.Status.REJECTED,
            amount=250,
            start_date=start_date,
        )
        self.authenticateAsProjectContributor(requirement.service.project)
        self.assertUpdateResponseMatchesUpdatedInstance(
            "/requirements/{}/".format(requirement.pk),
            requirement,
            dict(amount=500),
            RequirementSerializer,
        )
        # Test that the instance was updated in the expected way
        # Note that the instance was refreshed as part of the assert
        #   Verify that the amount was updated
        self.assertEqual(requirement.amount, 500)
        #   Verify that the start date stayed the same
        self.assertEqual(requirement.start_date, start_date)
        #   Verify that the requirement was put back into the requested state
        self.assertEqual(requirement.status, Requirement.Status.REQUESTED)

    def test_update_start_and_end_dates(self):
        """
        Tests that the start and end dates can be updated.

        Also verify that this puts the requirement back into the requested state.
        """
        # Set up the requirement
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsProjectContributor(requirement.service.project)
        requirement.status = Requirement.Status.REJECTED
        requirement.amount = 250
        requirement.save()
        # Pick a new start and end date
        start_date = date.today() + relativedelta(weeks=2)
        end_date = start_date + relativedelta(years=2)
        # Make the update
        self.assertUpdateResponseMatchesUpdatedInstance(
            "/requirements/{}/".format(requirement.pk),
            requirement,
            dict(start_date=start_date, end_date=end_date),
            RequirementSerializer,
        )
        # Test that the instance was updated in the expected way
        # Note that the instance was refreshed as part of the assert
        #   Verify that the amount was not updated
        self.assertEqual(requirement.amount, 250)
        #   Verify that the start and end dates were updated correctly
        self.assertEqual(requirement.start_date, start_date)
        self.assertEqual(requirement.end_date, end_date)
        #   Verify that the requirement was put back into the requested state
        self.assertEqual(requirement.status, Requirement.Status.REQUESTED)

    def test_cannot_update_service(self):
        """
        Tests that the service cannot be updated.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsProjectContributor(requirement.service.project)
        original_service_pk = requirement.service.pk
        # Pick a valid service that is not the current service to try to update to
        service = Service.objects.exclude(pk=original_service_pk).order_by("?").first()
        self.assertNotEqual(original_service_pk, service.pk)
        # Try to make the update - it should succeed but the service should not be updated
        self.assertUpdateResponseMatchesUpdatedInstance(
            "/requirements/{}/".format(requirement.pk),
            requirement,
            dict(service=service.pk),
            RequirementSerializer,
        )
        # Verify that the service was not updated
        self.assertEqual(requirement.service.pk, original_service_pk)
        self.assertNotEqual(requirement.service.pk, service.pk)

    def test_cannot_update_resource(self):
        """
        Tests that the resource cannot be updated.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsProjectContributor(requirement.service.project)
        original_resource_pk = requirement.resource.pk
        # Pick a valid resource that is not the current resource to try to update to
        resource = (
            Resource.objects.exclude(pk=original_resource_pk).order_by("?").first()
        )
        self.assertNotEqual(original_resource_pk, resource.pk)
        # Try to make the update - it should succeed but the resource should not be updated
        self.assertUpdateResponseMatchesUpdatedInstance(
            "/requirements/{}/".format(requirement.pk),
            requirement,
            dict(resource=resource.pk),
            RequirementSerializer,
        )
        # Verify that the resource was not updated
        self.assertEqual(requirement.resource.pk, original_resource_pk)
        self.assertNotEqual(requirement.resource.pk, resource.pk)

    def test_cannot_update_status(self):
        """
        Tests that the status cannot be directly updated.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsProjectContributor(requirement.service.project)
        requirement.status = Requirement.Status.REJECTED
        requirement.save()
        # Try to make the update - it should succeed but the status should not be updated
        self.assertUpdateResponseMatchesUpdatedInstance(
            "/requirements/{}/".format(requirement.pk),
            requirement,
            dict(status=Requirement.Status.AWAITING_PROVISIONING),
            RequirementSerializer,
        )
        # Check that the status did not change
        self.assertEqual(requirement.status, Requirement.Status.REJECTED)

    def test_cannot_update_with_negative_amount(self):
        """
        Tests that a requirement cannot be updated with a negative amount.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsProjectContributor(requirement.service.project)
        response_data = self.assertBadRequest(
            "/requirements/{}/".format(requirement.pk), "PATCH", dict(amount=-100)
        )
        self.assertCountEqual(response_data.keys(), {"amount"})
        self.assertEqual(response_data["amount"][0]["code"], "min_value")

    def test_cannot_update_with_start_date_in_past(self):
        """
        Tests that the start date cannot be updated to a date in the past.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsProjectContributor(requirement.service.project)
        # Get a new start date in the past to attempt to update to
        start_date = date.today() - relativedelta(weeks=2)
        response_data = self.assertBadRequest(
            "/requirements/{}/".format(requirement.pk),
            "PATCH",
            dict(start_date=start_date),
        )
        self.assertCountEqual(response_data.keys(), {"start_date"})
        self.assertEqual(response_data["start_date"][0]["code"], "date_in_past")

    def test_cannot_update_with_end_date_before_start_date(self):
        """
        Tests that the end date cannot be updated to a date that is before the
        start date, even if the start date does not change.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsProjectContributor(requirement.service.project)

        # Test with just a start date that is after the requirement's end date
        start_date = requirement.end_date + relativedelta(weeks=2)
        response_data = self.assertBadRequest(
            "/requirements/{}/".format(requirement.pk),
            "PATCH",
            dict(start_date=start_date),
        )
        self.assertCountEqual(response_data.keys(), {"end_date"})
        self.assertEqual(response_data["end_date"][0]["code"], "before_start_date")

        # Test with just an end date that is before the requirement's start date
        end_date = requirement.start_date - relativedelta(weeks=2)
        response_data = self.assertBadRequest(
            "/requirements/{}/".format(requirement.pk), "PATCH", dict(end_date=end_date)
        )
        self.assertCountEqual(response_data.keys(), {"end_date"})
        self.assertEqual(response_data["end_date"][0]["code"], "before_start_date")

        # Test with a start and an end date where the end date is before
        start_date = date.today() + relativedelta(months=6)
        end_date = start_date - relativedelta(weeks=2)
        response_data = self.assertBadRequest(
            "/requirements/{}/".format(requirement.pk),
            "PATCH",
            dict(start_date=start_date, end_date=end_date),
        )
        self.assertCountEqual(response_data.keys(), {"end_date"})
        self.assertEqual(response_data["end_date"][0]["code"], "before_start_date")

    def test_cannot_update_when_project_is_not_editable(self):
        """
        Tests that a requirement cannot be updated when the containing project is not editable.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsProjectContributor(requirement.service.project)
        requirement.amount = 120
        requirement.save()
        for status in Project.Status:
            if status == Project.Status.EDITABLE:
                continue
            # Put the containing project into the current state
            requirement.service.project.status = status
            requirement.service.project.save()
            # Try to change the amount
            response_data = self.assertConflict(
                "/requirements/{}/".format(requirement.pk), "PATCH", dict(amount=250)
            )
            # Check that the error code is what we expected
            self.assertEqual(response_data["code"], "invalid_status")
            # Check that the state in the DB was not changed
            requirement.refresh_from_db()
            self.assertEqual(requirement.amount, 120)

    def test_cannot_update_when_requirement_is_approved(self):
        """
        Tests that a requirement cannot be updated once it has been approved.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsProjectContributor(requirement.service.project)
        requirement.amount = 120
        requirement.save()
        for status in Requirement.Status:
            # Edits are allowed for required and rejected statuses
            if status < Requirement.Status.APPROVED:
                continue
            # Put the requirement into the current state
            requirement.status = status
            requirement.save()
            # Try to change the amount
            response_data = self.assertConflict(
                "/requirements/{}/".format(requirement.pk), "PATCH", dict(amount=250)
            )
            # Check that the error code is what we expected
            self.assertEqual(response_data["code"], "invalid_status")
            # Check that the state in the DB was not changed
            requirement.refresh_from_db()
            self.assertEqual(requirement.amount, 120)

    def test_consortium_manager_cannot_update(self):
        """
        Tests that a consortium manager cannot update a requirement.
        """
        requirement = Requirement.objects.order_by("?").first()
        # Authenticate the client as the consortium manager for the project
        self.authenticateAsConsortiumManager(requirement.service.project.consortium)
        # This should be permission denied as the user is permitted to view the requirement
        self.assertPermissionDenied(
            "/requirements/{}/".format(requirement.pk), "PATCH", dict(amount=250)
        )

    def test_authenticated_user_cannot_update(self):
        """
        Tests that an authenticated user who is not associated with the project
        cannot update a requirement.
        """
        requirement = Requirement.objects.order_by("?").first()
        # Authenticate the client as a user not associated with the project
        self.authenticate()
        # This should be not found as the user is not permitted to view the requirement either
        self.assertNotFound(
            "/requirements/{}/".format(requirement.pk), "PATCH", dict(amount=250)
        )

    def test_unauthenticated_user_cannot_update(self):
        """
        Tests that an unauthenticated user cannot update a requirement.
        """
        requirement = Requirement.objects.order_by("?").first()
        # This should be unauthorized as the user has not authenticated
        self.assertUnauthorized(
            "/requirements/{}/".format(requirement.pk), "PATCH", dict(amount=250)
        )

    def test_remove_as_project_owner(self):
        """
        Tests that a project owner can remove a requirement.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsProjectOwner(requirement.service.project)
        self.assertDeleteResponseIsEmpty("/requirements/{}/".format(requirement.pk))
        # Test that the requirement was removed
        self.assertFalse(Requirement.objects.filter(pk=requirement.pk).exists())

    def test_remove_as_project_contributor(self):
        """
        Tests that a project contributor can remove a requirement.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsProjectContributor(requirement.service.project)
        self.assertDeleteResponseIsEmpty("/requirements/{}/".format(requirement.pk))
        # Test that the requirement was removed
        self.assertFalse(Requirement.objects.filter(pk=requirement.pk).exists())

    def test_cannot_remove_when_project_is_not_editable(self):
        """
        Tests that a requirement cannot be removed when the containing project is not editable.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsProjectOwner(requirement.service.project)
        for status in Project.Status:
            if status == Project.Status.EDITABLE:
                continue
            # Put the containing project into the current state
            requirement.service.project.status = status
            requirement.service.project.save()
            # Try to delete the requirement
            response_data = self.assertConflict(
                "/requirements/{}/".format(requirement.pk), "DELETE"
            )
            # Check that the error code is what we expected
            self.assertEqual(response_data["code"], "invalid_status")
            # Check that the requirement still exists in the DB
            self.assertTrue(Requirement.objects.filter(pk=requirement.pk).exists())

    def test_cannot_remove_when_requirement_is_approved(self):
        """
        Tests that a requirement cannot be removed once it has been approved.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsProjectOwner(requirement.service.project)
        for status in Requirement.Status:
            # Requirements cannot be removed once they are approved
            if status < Requirement.Status.APPROVED:
                continue
            # Put the requirement into the current state
            requirement.status = status
            requirement.save()
            # Try to change the amount
            response_data = self.assertConflict(
                "/requirements/{}/".format(requirement.pk), "DELETE"
            )
            # Check that the error code is what we expected
            self.assertEqual(response_data["code"], "invalid_status")
            # Check that the requirement still exists in the DB
            self.assertTrue(Requirement.objects.filter(pk=requirement.pk).exists())

    def test_consortium_manager_cannot_remove(self):
        """
        Tests that a consortium manager cannot remove a requirement.
        """
        requirement = Requirement.objects.order_by("?").first()
        # Authenticate the client as the consortium manager for the project
        self.authenticateAsConsortiumManager(requirement.service.project.consortium)
        # This should be permission denied as the user is permitted to view the requirement
        self.assertPermissionDenied(
            "/requirements/{}/".format(requirement.pk), "DELETE"
        )

    def test_authenticated_user_cannot_remove(self):
        """
        Tests that an authenticated user who is not associated with the project
        cannot remove a requirement.
        """
        requirement = Requirement.objects.order_by("?").first()
        # Authenticate the client as a user not associated with the project
        self.authenticate()
        # This should be not found as the user is not permitted to view the requirement either
        self.assertNotFound("/requirements/{}/".format(requirement.pk), "DELETE")

    def test_unauthenticated_user_cannot_remove(self):
        """
        Tests that an unauthenticated user cannot remove a requirement.
        """
        requirement = Requirement.objects.order_by("?").first()
        # This should be unauthorized as the user has not authenticated
        self.assertUnauthorized("/requirements/{}/".format(requirement.pk), "DELETE")

    def test_approve_allowed_methods(self):
        """
        Tests that the correct methods are permitted by the approve endpoint.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsConsortiumManager(requirement.service.project.consortium)
        self.assertAllowedMethods(
            "/requirements/{}/approve/".format(requirement.pk), {"OPTIONS", "POST"}
        )

    def test_approve_requested(self):
        """
        Tests that a requested requirement can be successfully approved.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsConsortiumManager(requirement.service.project.consortium)
        # Put the containing project into the review status
        requirement.service.project.status = Project.Status.UNDER_REVIEW
        requirement.service.project.save()
        # Give the consortium a quota that is enough to approve the requirement
        requirement.service.project.consortium.quotas.create(
            resource=requirement.resource, amount=requirement.amount + 1
        )
        self.assertActionResponseMatchesUpdatedInstance(
            "/requirements/{}/approve/".format(requirement.pk),
            requirement,
            None,
            RequirementSerializer,
        )
        # Verify that the status is now approved
        self.assertEqual(requirement.status, Requirement.Status.APPROVED)

    def test_approve_rejected(self):
        """
        Tests that a rejected requirement can be approved while the project is still under review.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsConsortiumManager(requirement.service.project.consortium)
        requirement.status = Requirement.Status.REJECTED
        requirement.save()
        # Put the containing project into the review status
        requirement.service.project.status = Project.Status.UNDER_REVIEW
        requirement.service.project.save()
        # Give the consortium a quota that is enough to approve the requirement
        requirement.service.project.consortium.quotas.create(
            resource=requirement.resource, amount=requirement.amount + 1
        )
        self.assertActionResponseMatchesUpdatedInstance(
            "/requirements/{}/approve/".format(requirement.pk),
            requirement,
            None,
            RequirementSerializer,
        )
        # Verify that the status is now approved
        self.assertEqual(requirement.status, Requirement.Status.APPROVED)

    def test_approve_already_approved(self):
        """
        Tests that an already approved requirement can be re-approved.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsConsortiumManager(requirement.service.project.consortium)
        requirement.status = Requirement.Status.APPROVED
        requirement.save()
        # Put the containing project into the review status
        requirement.service.project.status = Project.Status.UNDER_REVIEW
        requirement.service.project.save()
        # Give the consortium a quota that is enough to approve the requirement
        requirement.service.project.consortium.quotas.create(
            resource=requirement.resource, amount=requirement.amount + 1
        )
        self.assertActionResponseMatchesUpdatedInstance(
            "/requirements/{}/approve/".format(requirement.pk),
            requirement,
            None,
            RequirementSerializer,
        )
        # Verify that the status is now approved
        self.assertEqual(requirement.status, Requirement.Status.APPROVED)

    def test_cannot_approve_when_project_is_not_under_review(self):
        """
        Tests that a requirement cannot be approved when the project is not under review.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsConsortiumManager(requirement.service.project.consortium)
        for status in Project.Status:
            if status == Project.Status.UNDER_REVIEW:
                continue
            # Put the containing project into the current state
            requirement.service.project.status = status
            requirement.service.project.save()
            # Try to approve the requirement
            response_data = self.assertConflict(
                "/requirements/{}/approve/".format(requirement.pk), "POST"
            )
            # Check that the error code is what we expected
            self.assertEqual(response_data["code"], "invalid_status")
            # Check that the requirement is still in the requested state
            requirement.refresh_from_db()
            self.assertEqual(requirement.status, Requirement.Status.REQUESTED)

    def test_cannot_approve_once_awaiting_provisioning(self):
        """
        Tests that a requirement cannot be approved when it is already awaiting provisioning.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsConsortiumManager(requirement.service.project.consortium)
        # Put the project into the review state
        requirement.service.project.status = Project.Status.UNDER_REVIEW
        requirement.service.project.save()
        for status in Requirement.Status:
            if status <= Requirement.Status.APPROVED:
                continue
            # Put the containing project into the current state
            requirement.status = status
            requirement.save()
            # Try to approve the requirement
            response_data = self.assertConflict(
                "/requirements/{}/approve/".format(requirement.pk), "POST"
            )
            # Check that the error code is what we expected
            self.assertEqual(response_data["code"], "invalid_status")
            # Check that the requirement is still in the required state
            requirement.refresh_from_db()
            self.assertEqual(requirement.status, status)

    def test_cannot_approve_when_quota_exceeded(self):
        """
        Tests that a requirement cannot be approved when it would take the consortium beyond
        it's quota for the resource.
        """
        # First, test that this works for no quotas
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsConsortiumManager(requirement.service.project.consortium)
        # Put the project into the review state
        requirement.service.project.status = Project.Status.UNDER_REVIEW
        requirement.service.project.save()

        # Try to approve the requirement without setting a quota
        response_data = self.assertConflict(
            "/requirements/{}/approve/".format(requirement.pk), "POST"
        )
        # Check that the error code is what we expected
        self.assertEqual(response_data["code"], "quota_exceeded")
        # Check that the requirement is still in the requested state
        requirement.refresh_from_db()
        self.assertEqual(requirement.status, Requirement.Status.REQUESTED)

        # Make a quota that is not enough for the requirement and try again
        requirement.service.project.consortium.quotas.create(
            resource=requirement.resource, amount=requirement.amount - 1
        )
        response_data = self.assertConflict(
            "/requirements/{}/approve/".format(requirement.pk), "POST"
        )
        self.assertEqual(response_data["code"], "quota_exceeded")
        requirement.refresh_from_db()
        self.assertEqual(requirement.status, Requirement.Status.REQUESTED)

    def test_project_contributor_cannot_approve(self):
        """
        Tests that a project contributor cannot approve a requirement.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsProjectContributor(requirement.service.project)
        self.assertPermissionDenied(
            "/requirements/{}/approve/".format(requirement.pk), "POST"
        )

    def test_project_owner_cannot_approve(self):
        """
        Tests that a project owner cannot approve a requirement.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsProjectOwner(requirement.service.project)
        self.assertPermissionDenied(
            "/requirements/{}/approve/".format(requirement.pk), "POST"
        )

    def test_authenticated_user_cannot_approve(self):
        """
        Tests that an authenticated user that is not associated with the project cannot
        approve a requirement.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticate()
        self.assertNotFound("/requirements/{}/approve/".format(requirement.pk), "POST")

    def test_approve_authentication_required(self):
        """
        Tests that authentication is required to approve a requirement.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.assertUnauthorized(
            "/requirements/{}/approve/".format(requirement.pk), "POST"
        )

    def test_reject_allowed_methods(self):
        """
        Tests that the correct methods are permitted by the reject endpoint.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsConsortiumManager(requirement.service.project.consortium)
        self.assertAllowedMethods(
            "/requirements/{}/reject/".format(requirement.pk), {"OPTIONS", "POST"}
        )

    def test_reject_requested(self):
        """
        Tests that a requested requirement can be rejected.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsConsortiumManager(requirement.service.project.consortium)
        # Put the containing project into the review status
        requirement.service.project.status = Project.Status.UNDER_REVIEW
        requirement.service.project.save()
        self.assertActionResponseMatchesUpdatedInstance(
            "/requirements/{}/reject/".format(requirement.pk),
            requirement,
            None,
            RequirementSerializer,
        )
        # Verify that the status is now rejected
        self.assertEqual(requirement.status, Requirement.Status.REJECTED)

    def test_reject_approved(self):
        """
        Tests that an approved requirement can be rejected while the project is still under review.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsConsortiumManager(requirement.service.project.consortium)
        requirement.status = Requirement.Status.APPROVED
        requirement.save()
        # Put the containing project into the review status
        requirement.service.project.status = Project.Status.UNDER_REVIEW
        requirement.service.project.save()
        self.assertActionResponseMatchesUpdatedInstance(
            "/requirements/{}/reject/".format(requirement.pk),
            requirement,
            None,
            RequirementSerializer,
        )
        # Verify that the status is now rejected
        self.assertEqual(requirement.status, Requirement.Status.REJECTED)

    def test_reject_already_rejected(self):
        """
        Tests that an already rejected requirement can be re-rejected.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsConsortiumManager(requirement.service.project.consortium)
        requirement.status = Requirement.Status.REJECTED
        requirement.save()
        # Put the containing project into the review status
        requirement.service.project.status = Project.Status.UNDER_REVIEW
        requirement.service.project.save()
        self.assertActionResponseMatchesUpdatedInstance(
            "/requirements/{}/reject/".format(requirement.pk),
            requirement,
            None,
            RequirementSerializer,
        )
        # Verify that the status is still rejected
        self.assertEqual(requirement.status, Requirement.Status.REJECTED)

    def test_cannot_reject_when_project_is_not_under_review(self):
        """
        Tests that a requirement cannot be rejected when the project is not under review.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsConsortiumManager(requirement.service.project.consortium)
        for status in Project.Status:
            if status == Project.Status.UNDER_REVIEW:
                continue
            # Put the containing project into the current state
            requirement.service.project.status = status
            requirement.service.project.save()
            # Try to reject the requirement
            response_data = self.assertConflict(
                "/requirements/{}/reject/".format(requirement.pk), "POST"
            )
            # Check that the error code is what we expected
            self.assertEqual(response_data["code"], "invalid_status")
            # Check that the requirement is still in the requested state
            requirement.refresh_from_db()
            self.assertEqual(requirement.status, Requirement.Status.REQUESTED)

    def test_cannot_reject_once_awaiting_provisioning(self):
        """
        Tests that a requirement cannot be rejected when it is already awaiting provisioning or later.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsConsortiumManager(requirement.service.project.consortium)
        # Put the project into the review state
        requirement.service.project.status = Project.Status.UNDER_REVIEW
        requirement.service.project.save()
        for status in Requirement.Status:
            if status <= Requirement.Status.APPROVED:
                continue
            # Put the containing project into the current state
            requirement.status = status
            requirement.save()
            # Try to reject the requirement
            response_data = self.assertConflict(
                "/requirements/{}/reject/".format(requirement.pk), "POST"
            )
            # Check that the error code is what we expected
            self.assertEqual(response_data["code"], "invalid_status")
            # Check that the requirement is still in the required state
            requirement.refresh_from_db()
            self.assertEqual(requirement.status, status)

    def test_project_contributor_cannot_reject(self):
        """
        Tests that a project contributor cannot reject a requirement.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsProjectContributor(requirement.service.project)
        self.assertPermissionDenied(
            "/requirements/{}/reject/".format(requirement.pk), "POST"
        )

    def test_project_owner_cannot_reject(self):
        """
        Tests that a project owner cannot reject a requirement.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticateAsProjectOwner(requirement.service.project)
        self.assertPermissionDenied(
            "/requirements/{}/reject/".format(requirement.pk), "POST"
        )

    def test_authenticated_user_cannot_reject(self):
        """
        Tests that an authenticated user that is not associated with the project cannot
        reject a requirement.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.authenticate()
        self.assertNotFound("/requirements/{}/reject/".format(requirement.pk), "POST")

    def test_reject_authentication_required(self):
        """
        Tests that authentication is required to reject a requirement.
        """
        requirement = Requirement.objects.order_by("?").first()
        self.assertUnauthorized(
            "/requirements/{}/reject/".format(requirement.pk), "POST"
        )
