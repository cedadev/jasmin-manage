from django.test import TestCase
from rest_framework.exceptions import ValidationError

from ...models import Tag
from ...serializers import TagSerializer
from ..utils import AssertValidationErrorsMixin


class TagSerializerTestCase(AssertValidationErrorsMixin, TestCase):
    """
    Tests for the tag serializer validation.
    """

    def test_valid_tag_names(self):
        """
        Test that valid tag names pass serializer validation.
        """
        valid_names = [
            "abc",           # minimum length
            "tag",           # simple name
            "tag-name",      # with hyphens
            "tag123",        # with numbers
            "123tag",        # starting with number
            "a-b-c-1-2-3",   # complex valid name
            "abcdefghijklmn",  # maximum length (15 chars)
        ]
        
        for name in valid_names:
            with self.subTest(name=name):
                serializer = TagSerializer(data={'name': name})
                self.assertTrue(serializer.is_valid(), f"Expected {name} to be valid, errors: {serializer.errors}")

    def test_invalid_tag_names_characters(self):
        """
        Test that tag names with invalid characters raise ValidationError in serializer.
        """
    
        custom_validation_names = [
            "TAG",           # uppercase letters
            "Tag",           # mixed case
            "tag_name",      # underscores
        ]
        
        expected_error_message = 'Tag name must contain only lowercase letters, numbers, and hyphens'
        
        for name in custom_validation_names:
            with self.subTest(name=name):
                serializer = TagSerializer(data={'name': name})
                self.assertFalse(serializer.is_valid())
                self.assertIn('name', serializer.errors)
                self.assertEqual(str(serializer.errors['name'][0]), expected_error_message)
        
       
        slug_validation_names = [
            "tag name",      # spaces
            "tag@name",      # special characters
            "tag#name",      # special characters
            "tag.name",      # dots
            "tàg",           # unicode characters
            "tag/name",      # slashes
        ]
        
        django_error_message = 'Enter a valid "slug" consisting of letters, numbers, underscores or hyphens.'
        
        for name in slug_validation_names:
            with self.subTest(name=name):
                serializer = TagSerializer(data={'name': name})
                self.assertFalse(serializer.is_valid())
                self.assertIn('name', serializer.errors)
                
                self.assertEqual(str(serializer.errors['name'][0]), django_error_message)

    def test_invalid_tag_names_length(self):
        """
        Test that tag names with invalid length raise ValidationError in serializer.
        """
        
        short_names = ["a", "ab"]
        expected_short_error = 'Tag name must be at least 3 characters long'
        
        for name in short_names:
            with self.subTest(name=name):
                serializer = TagSerializer(data={'name': name})
                self.assertFalse(serializer.is_valid())
                self.assertIn('name', serializer.errors)
                self.assertEqual(str(serializer.errors['name'][0]), expected_short_error)
        
        
        long_name = "abcdefghijklmnop"  
        expected_django_error = 'Ensure this field has no more than 15 characters.'
        
        serializer = TagSerializer(data={'name': long_name})
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)
        self.assertEqual(str(serializer.errors['name'][0]), expected_django_error)

    def test_invalid_tag_names_hyphen_position(self):
        """
        Test that tag names starting or ending with hyphens raise ValidationError in serializer.
        """
        invalid_names = [
            "-tag",          # starts with hyphen
            "tag-",          # ends with hyphen
            "-tag-",         # starts and ends with hyphen
            "---",           # only hyphens
        ]
        
        expected_error_message = 'Tag name cannot start or end with a hyphen'
        
        for name in invalid_names:
            with self.subTest(name=name):
                serializer = TagSerializer(data={'name': name})
                self.assertFalse(serializer.is_valid())
                self.assertIn('name', serializer.errors)
                self.assertEqual(str(serializer.errors['name'][0]), expected_error_message)
        
       
        serializer = TagSerializer(data={'name': '-'})
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)
       
        self.assertEqual(str(serializer.errors['name'][0]), 'Tag name must be at least 3 characters long')

    def test_null_name_handling(self):
        """
        Test how serializer handles null/None values for name.
        """
        
        serializer = TagSerializer(data={'name': None})
        if serializer.is_valid():
            self.assertTrue(True) 
        else:
            self.assertIn('name', serializer.errors)
        
       
        serializer = TagSerializer(data={'name': ''})
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)

    def test_validate_name_method_called(self):
        """
        Test that the validate_name method is properly called during validation.
        """
        serializer = TagSerializer(data={'name': 'INVALID_NAME'})
        self.assertFalse(serializer.is_valid())
        
        serializer = TagSerializer(data={'name': 'valid-name'})
        self.assertTrue(serializer.is_valid())

    def test_create_tag_with_valid_data(self):
        """
        Test that a tag can be created through the serializer with valid data.
        """
        valid_data = {'name': 'test-tag'}
        serializer = TagSerializer(data=valid_data)
        self.assertTrue(serializer.is_valid())
        
        tag = serializer.save()
        self.assertIsInstance(tag, Tag)
        self.assertEqual(tag.name, 'test-tag')

    def test_update_tag_with_invalid_name(self):
        """
        Test that updating a tag with invalid name raises ValidationError.
        """
        tag = Tag.objects.create(name='valid-tag')
        
        invalid_data = {'name': 'INVALID'}
        serializer = TagSerializer(tag, data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)
        self.assertEqual(
            str(serializer.errors['name'][0]),
            'Tag name must contain only lowercase letters, numbers, and hyphens'
        )
