import logging
from django.db import DatabaseError
from sites.responses import error_response
from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException, ValidationError
from django.core.exceptions import ValidationError as DjangoValidationError

logger = logging.getLogger(__name__)

class APIError(APIException):
    """Custom error: raise APIError("Domain already in use", 409)"""

    status_code = 400
    default_detail = "Request failed"

    def __init__(self, message=None, status_code=None):
        super().__init__(detail=message)
        if status_code:
            self.status_code = status_code


def custom_exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        exc = ValidationError(exc.message_dict if hasattr(exc, "error_dict") else exc.messages)

    response = exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled error in %s", context.get("view"), exc_info=exc)
        if isinstance(exc, DatabaseError):
            message = "A database error occurred."
        else:
            message = "Internal server error."
        return error_response(message, status_code=500)

    data = response.data
    if isinstance(data, dict) and set(data) == {"detail"}:
        return error_response(str(data["detail"]), status_code=response.status_code)
    return error_response("Validation failed", errors=data, status_code=response.status_code)


class ThemeAlreadyExists(APIError):
    status_code = 409
    default_detail = "A theme with this name already exists."

class ThemeNotFound(APIError):
    status_code = 404
    default_detail = "Theme not found."

class ThemeInUse(APIError):
    status_code = 409
    default_detail = "This theme cannot be deleted because it is still in use."

class ThemeIncomplete(APIError):
    status_code = 422
    default_detail = "The selected theme is missing required files."

class SiteNotFound(APIError):
    status_code = 404
    default_detail = "Site not found."

class ImageNotFound(APIError):
    status_code = 404
    default_detail = "Image not found."