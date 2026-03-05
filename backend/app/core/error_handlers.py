"""Unified error handling for the application.

Provides consistent JSON error responses for all exception types:
- HTTPException → standard FastAPI error with consistent format
- RequestValidationError → 422 with field-level details
- Unhandled exceptions → 500 internal server error
"""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Application-level error with status code and detail."""

    def __init__(self, status_code: int, detail: str, error_code: str | None = None):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code or "APP_ERROR"
        super().__init__(detail)


def _build_error_response(
    status_code: int,
    detail: str,
    error_code: str = "ERROR",
    errors: list | None = None,
) -> JSONResponse:
    """Build a consistent error JSON response."""
    body: dict = {
        "error": {
            "code": error_code,
            "message": detail,
            "status": status_code,
        }
    }
    if errors:
        body["error"]["details"] = errors
    return JSONResponse(status_code=status_code, content=body)


def register_error_handlers(app: FastAPI) -> None:
    """Register all error handlers on the FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return _build_error_response(
            status_code=exc.status_code,
            detail=exc.detail,
            error_code=exc.error_code,
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return _build_error_response(
            status_code=exc.status_code,
            detail=str(exc.detail),
            error_code="HTTP_ERROR",
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = []
        for error in exc.errors():
            loc = " → ".join(str(x) for x in error.get("loc", []))
            errors.append({
                "field": loc,
                "message": error.get("msg", ""),
                "type": error.get("type", ""),
            })
        return _build_error_response(
            status_code=422,
            detail="Request validation failed",
            error_code="VALIDATION_ERROR",
            errors=errors,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled exception: %s %s — %s",
            request.method,
            request.url.path,
            exc,
            exc_info=True,
        )
        return _build_error_response(
            status_code=500,
            detail="Internal server error",
            error_code="INTERNAL_ERROR",
        )
