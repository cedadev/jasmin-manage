import contextlib

from django.core.exceptions import ValidationError


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
            self.fail('ValidationError was not raised.')
