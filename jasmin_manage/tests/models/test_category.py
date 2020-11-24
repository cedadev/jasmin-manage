from django.test import TestCase

from ...models import Category


class CategoryModelTestCase(TestCase):
    """
    Tests for the category model.
    """
    @classmethod
    def setUpTestData(cls):
        Category.objects.create(name = 'Category 1')

    def test_plural_name(self):
        self.assertEqual(Category._meta.verbose_name_plural, 'categories')

    def test_name_unique(self):
        self.assertTrue(Category._meta.get_field('name').unique)

    def test_to_string(self):
        category = Category.objects.first()
        self.assertEqual(str(category), 'Category 1')

    def test_natural_key(self):
        category = Category.objects.first()
        self.assertEqual(category.natural_key(), ('Category 1', ))

    def test_get_by_natural_key(self):
        category = Category.objects.get_by_natural_key('Category 1')
        self.assertEqual(category.pk, 1)
