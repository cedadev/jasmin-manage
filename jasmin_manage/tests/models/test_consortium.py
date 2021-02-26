import itertools
import random

from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.test import TestCase

from ...models import Consortium


class ConsortiumModelTestCase(TestCase):
    """
    Tests for the consortium model.
    """
    def test_name_unique(self):
        self.assertTrue(Consortium._meta.get_field('name').unique)

    def test_manager_is_protected(self):
        """
        Tests that the consortium manager cannot be deleted.
        """
        manager = get_user_model().objects.create_user('manager')
        Consortium.objects.create(
            name = 'Consortium X',
            description = 'some description',
            manager = manager
        )
        with self.assertRaises(ProtectedError):
            manager.delete()

    def test_get_num_projects(self):
        """
        Tests that fetching the number of projects for a consortium works correctly
        for projects that come from both annotated and un-annotated queries.
        """
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

    def test_filter_visible_includes_non_public_consortia_for_staff(self):
        """
        Tests that non-public consortia are included when filtering the visible consortia for a staff user.
        """
        # Create some consortia that are a mixture of public and non-public
        for i in range(10):
            Consortium.objects.create(
                name = f'Consortium {i}',
                description = 'Some description.',
                is_public = (i < 5),
                manager = get_user_model().objects.create_user(f'manager{i}')
            )
        # Create a staff user
        staff_user = get_user_model().objects.create_user('staff_user', is_staff = True)
        # Check that all 10 consortia appear in the filtered query
        queryset = Consortium.objects.filter_visible(staff_user)
        self.assertEqual(queryset.count(), 10)

    def test_filter_visible_excludes_non_public_consortia_for_non_staff(self):
        """
        Tests that non-public consortia are not included when filtering the visible consortia for a non-staff user.
        """
        # Create some consortia that are a mixture of public and non-public
        for i in range(10):
            Consortium.objects.create(
                name = f'Consortium {i}',
                description = 'Some description.',
                is_public = (i < 5),
                manager = get_user_model().objects.create_user(f'manager{i}')
            )
        # Create a regular user
        user = get_user_model().objects.create_user('user1')
        # Check that only the 5 public consortia appear in the filtered query
        queryset = Consortium.objects.filter_visible(user)
        self.assertEqual(queryset.count(), 5)
        self.assertTrue(all(c.is_public for c in queryset))

    def test_filter_visible_includes_non_public_consortium_for_non_staff_user_if_collaborator(self):
        """
        Tests that filtering the visible consortia for a non-staff user includes a non-public consortium
        in which the user has a project on which they are a collaborator, while excluding all other
        non-public consortia.
        """
        # Create some consortia that are a mixture of public and non-public
        for i in range(10):
            Consortium.objects.create(
                name = f'Consortium {i}',
                description = 'Some description.',
                is_public = (i < 5),
                manager = get_user_model().objects.create_user(f'manager{i}')
            )
        # Create a regular user
        user = get_user_model().objects.create_user('user1')
        # Create a project with the user as the owner in a non-public consortium
        project_consortium = Consortium.objects.filter(is_public = False).first()
        project_consortium.projects.create(
            name = 'Project 1',
            description = 'Some description.',
            owner = user
        )
        # Check that the five public consortia plus the non-public consortium in which the user's
        # project is in appear in the filtered query
        queryset = Consortium.objects.filter_visible(user)
        self.assertEqual(queryset.count(), 6)
        # Partition the query into public and non-public
        public, non_public = queryset.filter(is_public = True), queryset.filter(is_public = False)
        self.assertEqual(public.count(), 5)
        self.assertEqual(non_public.count(), 1)
        # Check that the non-public consortium is the right one
        self.assertEqual(non_public.first(), project_consortium)

    def test_to_string(self):
        manager = get_user_model().objects.create_user('manager')
        consortium = Consortium.objects.create(
            name = 'Consortium X',
            description = 'some description',
            manager = manager
        )
        self.assertEqual(str(consortium), 'Consortium X')

    def test_natural_key(self):
        manager = get_user_model().objects.create_user('manager')
        consortium = Consortium.objects.create(
            name = 'Consortium X',
            description = 'some description',
            manager = manager
        )
        self.assertEqual(consortium.natural_key(), ('Consortium X', ))

    def test_get_by_natural_key(self):
        manager = get_user_model().objects.create_user('manager')
        Consortium.objects.create(
            name = 'Consortium X',
            description = 'some description',
            manager = manager
        )
        consortium = Consortium.objects.get_by_natural_key('Consortium X')
        self.assertEqual(consortium.pk, 1)
