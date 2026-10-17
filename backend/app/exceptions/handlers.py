"""
Global Exception Handlers for FastAPI app.
Registers uniform JSON error envelope responses for uncaught AppException and standard HTTP exceptions.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from app.exceptions.base import BaseAppException


async def app_exception_handler(request: Request, exc: BaseAppException) -> JSONResponse:
    """Formats custom application exceptions into a standardized API response envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "data": None,
            "meta": {
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        },
    )
