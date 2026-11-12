"""Provide standardized success and error responses for API endpoints."""

from rest_framework import status
from rest_framework.response import Response


def success_response(data=None, message="OK", status_code=status.HTTP_200_OK):
    """Return a standardized successful API response."""
    return Response(
        {"success": True, "message": message, "data": data, "errors": None},
        status=status_code,
    )


def error_response(message="Something went wrong", errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    """Return a standardized error API response."""
    return Response(
        {"success": False, "message": message, "data": None, "errors": errors},
        status=status_code,
    )