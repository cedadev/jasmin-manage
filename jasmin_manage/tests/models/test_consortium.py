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
        cls.manager = get_user_model().objects.create_user('manager1')
        Consortium.objects.create(
            name = 'Consortium 1',
            description = 'some description',
            manager = cls.manager
        )

    def test_name_unique(self):
        self.assertTrue(Consortium._meta.get_field('name').unique)

    def test_manager_is_protected(self):
        # Test that deleting a user that is a collaborator is not permitted
        with self.assertRaises(ProtectedError):
            self.manager.delete()

    def test_to_string(self):
        consortium = Consortium.objects.first()
        self.assertEqual(str(consortium), 'Consortium 1')

    def test_natural_key(self):
        consortium = Consortium.objects.first()
        self.assertEqual(consortium.natural_key(), ('Consortium 1', ))

    def test_get_by_natural_key(self):
        consortium = Consortium.objects.get_by_natural_key('Consortium 1')
        self.assertEqual(consortium.pk, 1)
