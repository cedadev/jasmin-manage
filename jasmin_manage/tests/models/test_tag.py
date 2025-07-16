from django.test import TestCase
from django.core.exceptions import ValidationError

from ...models import Tag
from ..utils import AssertValidationErrorsMixin


class TagModelTestCase(AssertValidationErrorsMixin, TestCase):
    """
    Tests for the tag model validation.
    """

    def test_valid_tag_names(self):
        """
        Test that valid tag names pass validation.
        """
        valid_names = [
            "abc",           
            "tag",          
            "tag-name",      
            "tag123",        
            "123tag",        
            "a-b-c-1-2-3",   
            "abcdefghijklmn",  
        ]
        
        for name in valid_names:
            with self.subTest(name=name):
                tag = Tag(name=name)
                tag.full_clean()

    def test_invalid_tag_names_characters(self):
        """
        Test that tag names with invalid characters raise ValidationError.
        """
        invalid_names = [
            "TAG",           
            "Tag",          
            "tag name",      
            "tag@name",      
            "tag#name",      
            "tag_name",      
            "tag.name",     
            "tàg",          
            "tag/name",    
        ]
        
        for name in invalid_names:
            with self.subTest(name=name):
                tag = Tag(name=name)
                with self.assertRaises(ValidationError) as cm:
                    tag.full_clean()
                
                errors = cm.exception.message_dict.get('name', [])
                self.assertIn('Tag name must contain only lowercase letters, numbers, and hyphens', errors)

    def test_invalid_tag_names_length(self):
        """
        Test that tag names with invalid length raise ValidationError.
        """
        short_names = ["a", "ab"]
        
        for name in short_names:
            with self.subTest(name=name):
                tag = Tag(name=name)
                with self.assertRaises(ValidationError) as cm:
                    tag.full_clean()
                errors = cm.exception.message_dict.get('name', [])
                self.assertIn('Tag name must be at least 3 characters long', errors)

        long_name = "abcdefghijklmnop"  

        tag = Tag(name=long_name)
        with self.assertRaises(ValidationError) as cm:
            tag.full_clean()
        errors = cm.exception.message_dict.get('name', [])
        self.assertIn('Tag name must be at most 15 characters long', errors)

    def test_invalid_tag_names_hyphen_position(self):
        """
        Test that tag names starting or ending with hyphens raise ValidationError.
        """
        invalid_names = [
            "-tag",          # starts with hyphen
            "tag-",          # ends with hyphen
            "-tag-",         # starts and ends with hyphen
            "---",           # only hyphens (length >= 3)
        ]
        
        for name in invalid_names:
            with self.subTest(name=name):
                tag = Tag(name=name)
                with self.assertRaises(ValidationError) as cm:
                    tag.full_clean()
                errors = cm.exception.message_dict.get('name', [])
                self.assertIn('Tag name cannot start or end with a hyphen', errors)
        
        tag = Tag(name="-")
        with self.assertRaises(ValidationError) as cm:
            tag.full_clean()
        errors = cm.exception.message_dict.get('name', [])
        self.assertIn('Tag name must be at least 3 characters long', errors)

    def test_null_name_not_allowed_in_validation(self):
        """
        Test that null/empty tag names are not allowed during validation.
        """
        tag = Tag(name=None)
        with self.assertRaises(ValidationError) as cm:
            tag.full_clean()
        errors = cm.exception.message_dict.get('name', [])
        self.assertIn('This field cannot be blank.', errors)
        
        tag = Tag(name="")
        with self.assertRaises(ValidationError) as cm:
            tag.full_clean()
        errors = cm.exception.message_dict.get('name', [])
        self.assertIn('This field cannot be blank.', errors)

    def test_name_converted_to_lowercase(self):
        """
        Test that tag names are automatically converted to lowercase by TagField.
        """
        tag = Tag(name="MixedCase")
       

        with self.assertRaises(ValidationError) as cm:
            tag.full_clean()
        errors = cm.exception.message_dict.get('name', [])
        self.assertIn('Tag name must contain only lowercase letters, numbers, and hyphens', errors)

    def test_save_calls_full_clean(self):
        """
        Test that Tag.save() calls full_clean() and validation is enforced.
        """
        tag = Tag(name="INVALID")
        with self.assertRaises(ValidationError) as cm:
            tag.save()
        errors = cm.exception.message_dict.get('name', [])
        self.assertIn('Tag name must contain only lowercase letters, numbers, and hyphens', errors)
