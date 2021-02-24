import random

from django.contrib.auth import get_user_model
from django.test import TestCase

from ...models import Category, Consortium, Quota, Requirement, Resource
from ...serializers import QuotaSerializer


class QuotaSerializerTestCase(TestCase):
    """
    Tests for the quota serializer.
    """
    def test_renders_instance_correctly(self):
        """
        Tests that the serializer renders an existing instance correctly.
        """
        # Create a consortium, resource, and some requirements spread across projects and services
        consortium = Consortium.objects.create(
            name = 'Consortium 1',
            description = 'Some description.',
            manager = get_user_model().objects.create_user('manager1')
        )
        resource = Resource.objects.create(name = 'Resource 1', description = 'Some description.')
        category = Category.objects.create(name = 'Category 1', description = 'Some description.')
        projects = [
            consortium.projects.create(
                name = f'Project {i}',
                description = 'Some description.',
                owner = get_user_model().objects.create_user(f'owner{i}')
            )
            for i in range(5)
        ]
        services = [
            random.choice(projects).services.create(category = category, name = f'service{i}')
            for i in range(20)
        ]
        requirement_totals = {}
        for i in range(200):
            service = random.choice(services)
            status = random.choice(list(Requirement.Status))
            amount = random.randint(1, 1000)
            service.requirements.create(resource = resource, status = status, amount = amount)
            previous_amount = requirement_totals.setdefault(status, 0)
            requirement_totals[status] = previous_amount + amount

        # Create a quota to serialize
        quota = Quota.objects.create(consortium = consortium, resource = resource, amount = 1000000)
        serializer = QuotaSerializer(quota)
        # Check that the right keys are present
        self.assertCountEqual(
            serializer.data.keys(),
            {
                'id',
                'consortium',
                'resource',
                'amount',
                'total_provisioned',
                'total_awaiting_provisioning',
                'total_approved',
            }
        )
        # Check the the values are correct
        self.assertEqual(serializer.data['id'], quota.pk)
        self.assertEqual(serializer.data['consortium'], consortium.pk)
        self.assertEqual(serializer.data['resource'], resource.pk)
        self.assertEqual(serializer.data['amount'], 1000000)
        self.assertEqual(serializer.data['total_provisioned'], requirement_totals[Requirement.Status.PROVISIONED])
        self.assertEqual(serializer.data['total_awaiting_provisioning'], requirement_totals[Requirement.Status.AWAITING_PROVISIONING])
        self.assertEqual(serializer.data['total_approved'], requirement_totals[Requirement.Status.APPROVED])
