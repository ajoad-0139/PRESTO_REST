"""Define custom exception handling and application-specific API errors."""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.views import exception_handler

from sites.responses import error_response

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """Convert Django and DRF exceptions into a consistent API response."""
    if isinstance(exc, DjangoValidationError):
        exc = ValidationError(
            exc.message_dict if hasattr(exc, "error_dict") else exc.messages
        )

    response = exception_handler(exc, context)

    if response is None:
        logger.exception(
            "Unhandled error in %s", context.get("view"), exc_info=exc
        )

        if isinstance(exc, DatabaseError):
            message = "A database error occurred."
        else:
            message = "Internal server error."

        return error_response(message, status_code=500)

    data = response.data

    if isinstance(data, dict) and set(data) == {"detail"}:
        return error_response(
            str(data["detail"]),
            status_code=response.status_code,
        )

    return error_response(
        "Validation failed",
        errors=data,
        status_code=response.status_code,
    )


class APIError(APIException):
    """Provide a base exception for application-specific API errors."""

    status_code = 400
    default_detail = "Request failed"

    def __init__(self, message=None, status_code=None):
        """Initialize the API error with an optional message and status code."""
        super().__init__(detail=message)

        if status_code:
            self.status_code = status_code


class ThemeAlreadyExists(APIError):
    """Represent an attempt to create a theme that already exists."""

    status_code = 409
    default_detail = "A theme with this name already exists."


class ThemeNotFound(APIError):
    """Represent a request for a theme that does not exist."""

    status_code = 404
    default_detail = "Theme not found."


class ThemeInUse(APIError):
    """Represent an attempt to delete a theme that is still in use."""

    status_code = 409
    default_detail = "This theme cannot be deleted because it is still in use."


class ThemeIncomplete(APIError):
    """Represent a theme that is missing required files."""

    status_code = 422
    default_detail = "The selected theme is missing required files."


class SiteNotFound(APIError):
    """Represent a request for a site that does not exist."""

    status_code = 404
    default_detail = "Site not found."


class ImageNotFound(APIError):
    """Represent a request for an image that does not exist."""

    status_code = 404
    default_detail = "Image not found."


class VideoNotFound(APIError):
    """Represent a request for a video that does not exist."""

    status_code = 404
    default_detail = "Video not found."


class PageAlreadyExists(APIError):
    """Represent an attempt to create a page with an existing title."""

    status_code = 409
    default_detail = "A page with this title already exists in this site."


class PageNotFound(APIError):
    """Represent a request for a page that does not exist."""

    status_code = 404
    default_detail = "Page not found."