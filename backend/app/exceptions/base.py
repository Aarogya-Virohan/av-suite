"""
Base exception classes for the application.
Centralizing custom exceptions allows uniform error handling across services and endpoints.
"""

from typing import Any, Dict, Optional


class BaseAppException(Exception):
    """Base exception class for all custom application errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class ResourceNotFoundError(BaseAppException):
    """Raised when a requested database resource is not found."""

    def __init__(self, resource_name: str, resource_id: Any):
        message = f"{resource_name} with identifier '{resource_id}' was not found."
        super().__init__(message=message, code="NOT_FOUND", status_code=404)


class AppValidationError(BaseAppException):
    """Raised when domain or business logic validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, code="VALIDATION_ERROR", status_code=400, details=details)


class PermissionDeniedError(BaseAppException):
    """Raised when user does not have permission for an operation."""

    def __init__(self, message: str = "Permission denied for this resource."):
        super().__init__(message=message, code="FORBIDDEN", status_code=403)


class ConflictError(BaseAppException):
    """Raised when an operation conflicts with existing state (e.g., unique key violation)."""

    def __init__(self, message: str):
        super().__init__(message=message, code="CONFLICT", status_code=409)
