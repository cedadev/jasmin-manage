import random

from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.test import TestCase

from ...models import Consortium


class ConsortiumModelTestCase(TestCase):
    """
    Tests for the consortium model.
    """
    @classmethod
    def setUpTestData(cls):
        cls.manager = get_user_model().objects.create_user('manager')
        Consortium.objects.create(
            name = 'Consortium X',
            description = 'some description',
            manager = cls.manager
        )

    def test_name_unique(self):
        self.assertTrue(Consortium._meta.get_field('name').unique)

    def test_manager_is_protected(self):
        # Test that deleting a user that is a collaborator is not permitted
        with self.assertRaises(ProtectedError):
            self.manager.delete()

    def test_get_num_projects(self):
        # Test that fetching the number of projects for a consortium works correctly
        # for projects that come from both annotated and un-annotated queries
        # Create some consortia
        consortia = [
            Consortium.objects.create(
                name = f'Consortium {i}',
                description = 'Some description.',
                manager = get_user_model().objects.create_user(f'manager{i}')
            )
            for i in range(10)
        ]
        # Create some projects spread across the consortia
        # Leave one consortium with no projects to test that
        project_counts = {}
        for i, consortium in enumerate(consortia[1:]):
            num_projects = random.randint(1, 20)
            for j in range(num_projects):
                consortium.projects.create(
                    name = f'Project {i} {j}',
                    description = 'Some description.',
                    owner = get_user_model().objects.create_user(f'owner{i}{j}')
                )
            project_counts[consortium.pk] = num_projects

        # Test that the annotated and un-annotated querysets both return correct answers
        for queryset in (Consortium.objects.all(), Consortium.objects.annotate_summary()):
            for consortium in queryset:
                self.assertEqual(consortium.get_num_projects(), project_counts.get(consortium.pk, 0))

    def test_to_string(self):
        consortium = Consortium.objects.first()
        self.assertEqual(str(consortium), 'Consortium X')

    def test_natural_key(self):
        consortium = Consortium.objects.first()
        self.assertEqual(consortium.natural_key(), ('Consortium X', ))

    def test_get_by_natural_key(self):
        consortium = Consortium.objects.get_by_natural_key('Consortium X')
        self.assertEqual(consortium.pk, 1)
