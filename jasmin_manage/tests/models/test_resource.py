import random

from django.contrib.auth import get_user_model
from django.test import TestCase

from ...models import (
    Category,
    Consortium,
    Project,
    Quota,
    Requirement,
    Resource
)


class ResourceModelTestCase(TestCase):
    """
    Tests for the resource model.
    """
    def test_name_unique(self):
        self.assertTrue(Resource._meta.get_field('name').unique)

    def test_to_string(self):
        resource1 = Resource.objects.create(name = 'Resource 1')
        self.assertEqual(str(resource1), 'Resource 1')
        resource2 = Resource.objects.create(name = 'Resource 2', units = 'GB')
        self.assertEqual(str(resource2), 'Resource 2 (GB)')

    def test_natural_key(self):
        resource = Resource.objects.create(name = 'Resource 1')
        self.assertEqual(resource.natural_key(), ('Resource 1', ))

    def test_get_by_natural_key(self):
        Resource.objects.create(name = 'Resource 1')
        resource = Resource.objects.get_by_natural_key('Resource 1')
        self.assertEqual(resource.pk, 1)

    def test_format_amount(self):
        resource1 = Resource.objects.create(name = 'Resource 1')
        self.assertEqual(resource1.format_amount(20), '20')
        resource2 = Resource.objects.create(name = 'Resource 2', units = 'GB')
        self.assertEqual(resource2.format_amount(20), '20 GB')

    def test_total_available(self):
        # We want to test that this works for a number of chunks spread across a number of resources
        # So we generate them programmatically

        # This dict contains the counts and totals indexed by resource PK
        expected = {}
        # Make 20 resources...
        for i in range(20):
            resource = Resource.objects.create(name = f'Resource {i}')
            expected.setdefault(resource.pk, 0)
            # Each with between 1 and 10 chunks...
            for j in range(random.randint(1, 10)):
                # Where each chunk has an amount between 100 and 1000
                amount = random.randint(100, 1000)
                expected[resource.pk] += amount
                resource.chunks.create(name = f'r{i}chunk{j}', amount = amount)

        # Fetch the resources and check that the reported totals match our totals
        for resource in Resource.objects.all():
            self.assertEqual(resource.total_available, expected[resource.pk])

    def test_annotate_usage_quotas(self):
        # We want to test that this works for a number of chunks spread across a number of consortia and resources
        # So we generate them programmatically

        # Make 20 resources
        resources = [Resource.objects.create(name = f'Resource {i}') for i in range(20)]

        # Make 10 consortia
        consortia = [
            Consortium.objects.create(
                name = f'Consortium {i}',
                description = 'some description',
                manager = get_user_model().objects.create_user(f'manager{i}')
            )
            for i in range(10)
        ]

        # For each resource, add some quotas
        # Keep a track of the expected number and total for each resource
        expected = {}
        for resource in resources:
            # Pick a random number of consortia to add quotas for
            num_quotas = random.randint(0, 10)
            total_quotas = 0
            # Pick the consortia at random for which to add quotas
            for consortium in random.sample(consortia, num_quotas):
                # Pick a random amount between 100 and 1000 for the quota
                amount = random.randint(100, 1000)
                total_quotas += amount
                consortium.quotas.create(resource = resource, amount = amount)
            # Store the expected values
            expected[resource.pk] = dict(count = num_quotas, total = total_quotas)

        # Fetch the annotated resources and test that the annotations match our expected values
        for resource in Resource.objects.annotate_usage():
            self.assertEqual(resource.quota_count, expected[resource.pk]['count'])
            self.assertEqual(resource.quota_total, expected[resource.pk]['total'])

    def test_annotate_usage_requirements(self):
        # We want to test that this works for a number of requirements spread across a good mix of
        # services, projects, consortia, resources, statuses and amounts
        # So we generate them programmatically

        # Make 20 resources
        resources = [Resource.objects.create(name = f'Resource {i}') for i in range(20)]

        # Make one category
        # We won't be worrying about validating the resources for the requirements so we
        # only need to worry about having a foreign key to attach services to
        category = Category.objects.create(name = 'Category 1')

        # Make 10 consortia
        consortia = [
            Consortium.objects.create(
                name = f'Consortium {i}',
                description = 'some description',
                manager = get_user_model().objects.create_user(f'manager{i}')
            )
            for i in range(10)
        ]

        # Make 100 projects spread randomly across consortia
        projects = [
            consortia[random.randrange(10)].projects.create(
                name = f'Project {i}',
                description = 'some description',
                owner = get_user_model().objects.create_user(f'owner{i}')
            )
            for i in range(100)
        ]

        # Make 400 services spread randomly accross projects
        services = [
            projects[random.randrange(100)].services.create(
                name = f'service{i}',
                category = category
            )
            for i in range(400)
        ]

        # Make 2000 requirements spread randomly across services, resources, statuses and amounts
        # Keep track of the count and total for each resource and status
        expected = {}
        for i in range(2000):
            # Make the random choices
            service = random.choice(services)
            resource = random.choice(resources)
            status = random.choice(list(Requirement.Status))
            amount = random.randint(1, 1000)
            # Increment the expected values
            expected_status = expected.setdefault(resource.pk, {}).setdefault(status, { 'count': 0, 'total': 0 })
            expected_status['count'] += 1
            expected_status['total'] += amount
            # Create the requirement
            service.requirements.create(resource = resource, status = status, amount = amount)

        # Fetch the annotated resources and test that the annotations match our expected values
        for resource in Resource.objects.annotate_usage():
            for status in Requirement.Status:
                expected_status = expected.get(resource.pk, {}).get(status, { 'count': 0, 'total': 0 })
                actual_count = getattr(resource, '{}_count'.format(status.name.lower()))
                actual_total = getattr(resource, '{}_total'.format(status.name.lower()))
                self.assertEqual(actual_count, expected_status['count'])
                self.assertEqual(actual_total, expected_status['total'])
