from rest_framework.exceptions import ErrorDetail, APIException
from rest_framework.views import exception_handler as drf_exception_handler


def get_response_data(obj):
    """
    Process the given object to get the response content.
    """
    if isinstance(obj, list):
        return [get_response_data(item) for item in obj]
    elif isinstance(obj, dict):
        return { key: get_response_data(value) for key, value in obj.items() }
    elif isinstance(obj, ErrorDetail):
        return dict(detail = str(obj), code = obj.code)
    else:
        return str(obj)


def exception_handler(exc, context):
    """
    Custom exception handler that will include codes with errors.
    """
    response = drf_exception_handler(exc, context)
    # Modify the response content for a validation error to include codes
    if isinstance(exc, APIException):
        response.data = get_response_data(exc.detail)
    return response
