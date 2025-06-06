from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, ValidationError):
        customized_response = {'detail': {}}
        customized_response['detail'].update(response.data)
        response.data = customized_response
    elif isinstance(exc, ObjectValidationError) or issubclass(type(exc), APIException):
        customized_response = {'detail': {'object_error': [response.data['detail']]}}
        response.data = customized_response
    return response


class ObjectValidationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Object Error"
    default_code = "invalid_data"


class ObjectAlreadyExist(APIException):
    status_code = 400
    default_detail = "Object already exist."
    default_code = "object_already_exist"
