import random

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from ...models import Category, Consortium, Quota, Requirement, Resource

from ..utils import AssertValidationErrorsMixin


class QuotaModelTestCase(AssertValidationErrorsMixin, TestCase):
    """
    Tests for the quota model.
    """

    def create_quota(self):
        consortium = Consortium.objects.create(
            name="Consortium 1",
            description="some description",
            manager=get_user_model().objects.create_user("manager1"),
        )
        resource = Resource.objects.create(name="Resource 1")
        return Quota.objects.create(consortium=consortium, resource=resource, amount=50)

    def test_unique_together(self):
        # Make an initial quota
        quota = self.create_quota()
        # Try to validate and save another quota with the same consortium and resource
        # Test that consortium and resource are unique together
        new_quota = Quota(
            consortium=quota.consortium, resource=quota.resource, amount=20
        )
        # Test that model validation raises the correct error
        expected_errors = {
            "__all__": ["Quota with this Consortium and Resource already exists."],
        }
        with self.assertValidationErrors(expected_errors):
            new_quota.full_clean()
        # Test that an integrity error is raised when saving
        with self.assertRaises(IntegrityError):
            new_quota.save()

    def test_to_string(self):
        quota = self.create_quota()
        self.assertEqual(str(quota), "Consortium 1 / Resource 1")

    def test_natural_key(self):
        quota = self.create_quota()
        self.assertEqual(quota.natural_key(), ("Consortium 1", "Resource 1"))

    def test_get_by_natural_key(self):
        self.create_quota()
        quota = Quota.objects.get_by_natural_key("Consortium 1", "Resource 1")
        self.assertEqual(quota.pk, 1)

    def test_get_event_aggregates(self):
        quota = self.create_quota()
        self.assertEqual(
            quota.get_event_aggregates(), (quota.consortium, quota.resource)
        )

    def test_get_total_for_status(self):
        # We want to test that this works for a number of quotas spread across different consortia and resources
        # So we generate them programmatically

        # Make 20 resources
        resources = [Resource.objects.create(name=f"Resource {i}") for i in range(20)]

        # Make one category
        # We won't be worrying about validating the resources for the requirements so we
        # only need to worry about having a foreign key to attach services to
        category = Category.objects.create(name="Category 1")

        # Make 10 consortia
        consortia = [
            Consortium.objects.create(
                name=f"Consortium {i}",
                description="some description",
                manager=get_user_model().objects.create_user(f"manager{i}"),
            )
            for i in range(10)
        ]

        # For each resource and consortium, add a quota
        # The quota amount doesn't matter - we just want to check that we can get usage totals
        for resource in resources:
            for consortium in consortia:
                consortium.quotas.create(resource=resource, amount=100)

        # Make 100 projects spread randomly across consortia
        projects = [
            consortia[random.randrange(10)].projects.create(
                name=f"Project {i}",
                description="some description",
                owner=get_user_model().objects.create_user(f"owner{i}"),
            )
            for i in range(100)
        ]

        # Make 400 services spread randomly accross projects
        services = [
            projects[random.randrange(100)].services.create(
                name=f"service{i}", category=category
            )
            for i in range(400)
        ]

        # Make 2000 requirements spread randomly across services, resources, statuses and amounts
        # Keep track of the count and total for each resource, consortium and status
        expected = {}
        for i in range(2000):
            # Make the random choices
            service = random.choice(services)
            resource = random.choice(resources)
            status = random.choice(list(Requirement.Status))
            amount = random.randint(1, 1000)
            # Increment the expected values
            resource_status = expected.setdefault(resource.pk, {})
            consortium_status = resource_status.setdefault(
                service.project.consortium.pk, {}
            )
            requirement_status = consortium_status.setdefault(
                status, {"count": 0, "total": 0}
            )
            requirement_status["count"] += 1
            requirement_status["total"] += amount
            # Create the requirement
            service.requirements.create(resource=resource, status=status, amount=amount)

        # Test the results for two different queries - one annotated and one not
        # They should return the same results
        for queryset in (Quota.objects.all(), Quota.objects.annotate_usage()):
            for quota in queryset:
                expected_quota = expected.get(quota.resource.pk, {}).get(
                    quota.consortium.pk, {}
                )
                for status in Requirement.Status:
                    expected_status = expected_quota.get(
                        status, {"count": 0, "total": 0}
                    )
                    actual_count = quota.get_count_for_status(status)
                    actual_total = quota.get_total_for_status(status)
                    self.assertEqual(actual_count, expected_status["count"])
                    self.assertEqual(actual_total, expected_status["total"])
