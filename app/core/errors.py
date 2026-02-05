import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("app")


class AppError(Exception):
    code = "app_error"
    status_code = 400
    message = "Application error"

    def __init__(self, message: str | None = None, details: Any | None = None) -> None:
        self.message = message or self.message
        self.details = details


class NotFoundError(AppError):
    code = "not_found"
    status_code = 404
    message = "Resource not found"


class ConflictError(AppError):
    code = "conflict"
    status_code = 409
    message = "Conflict"


class UnauthorizedError(AppError):
    code = "unauthorized"
    status_code = 401
    message = "Unauthorized"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message, "details": exc.details},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": "http_error", "message": str(exc.detail), "details": None},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"code": "validation_error", "message": "Validation error", "details": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled exception")
        return JSONResponse(
            status_code=500,
            content={"code": "internal_error", "message": "Internal server error", "details": None},
        )
