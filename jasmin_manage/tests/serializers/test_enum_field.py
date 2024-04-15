from django.db import models
from django.test import TestCase

from ...serializers.base import EnumField

from ..utils import AssertValidationErrorsMixin


class TestChoices(models.IntegerChoices):
    """
    Choices class to use for testing.
    """

    CHOICE_1 = 10
    CHOICE_2 = 20
    CHOICE_3 = 30


class EnumFieldTestCase(AssertValidationErrorsMixin, TestCase):
    """
    Tests for the enum serializer field.
    """

    def test_choices_are_names(self):
        field = EnumField(TestChoices)
        choices = {choice.name: choice.name for choice in TestChoices}
        self.assertEqual(field.choices, choices)

    def test_to_internal_value(self):
        field = EnumField(TestChoices)
        # Test a valid choice
        self.assertEqual(field.to_internal_value("CHOICE_2"), TestChoices.CHOICE_2)
        # Test an invalid choice
        with self.assertDrfValidationErrors(['"CHOICE_4" is not a valid choice.']):
            field.to_internal_value("CHOICE_4")
        # Test that you can't specify a member value
        with self.assertDrfValidationErrors(['"20" is not a valid choice.']):
            field.to_internal_value(20)
        # Test that a blank or none value is not allowed
        with self.assertDrfValidationErrors(['"" is not a valid choice.']):
            field.to_internal_value("")
        # Test that a blank choice can be enabled and returns none
        field = EnumField(TestChoices, allow_blank=True)
        self.assertIsNone(field.to_internal_value(""))

    def test_to_representation(self):
        field = EnumField(TestChoices)
        self.assertIsNone(field.to_representation(None))
        # If an enum value is given, it should return the name
        self.assertEqual(field.to_representation(TestChoices.CHOICE_2), "CHOICE_2")
        # If any other value is given, it must be a value of the enum
        self.assertEqual(field.to_representation(30), "CHOICE_3")
        # Anything that isn't a valid value should be an error
        with self.assertRaises(ValueError):
            field.to_representation(50)
