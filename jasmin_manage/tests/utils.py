import contextlib

from django.core.exceptions import ValidationError

from rest_framework.exceptions import ValidationError as DrfValidationError


class AssertValidationErrorsMixin:
    """
    Mixin for test cases providing a method to assert on validation messages.
    """

    @contextlib.contextmanager
    def assertValidationErrors(self, expected_errors):
        """
        Assert that a validation error is raised that contains the expected errors.
        """
        try:
            yield
        except ValidationError as exc:
            self.assertEqual(exc.message_dict, expected_errors)
        else:
            self.fail("ValidationError was not raised.")

    @contextlib.contextmanager
    def assertDrfValidationErrors(self, expected_errors):
        """
        Assert that a DRF validation error is raised whose detail contains the expected errors.
        """
        try:
            yield
        except DrfValidationError as exc:
            self.assertEqual(exc.detail, expected_errors)
        else:
            self.fail("DRF ValidationError was not raised.")
