# app/core/errors.py — Universal Error Format wiring (required, copy as-is)
import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("farmpool")

_STATUS_TO_CODE = {401: "AUTH_REQUIRED", 403: "FORBIDDEN_ROLE", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED",
                   413: "AUDIO_TOO_LARGE", 415: "AUDIO_FORMAT_UNSUPPORTED", 422: "VALIDATION_ERROR"}


class ApiError(Exception):
    """Raise this from any route/service for a contract error."""

    def __init__(self, status_code: int, code: str, message: str, details: dict[str, Any] | None = None):
        self.status_code, self.code, self.message, self.details = status_code, code, message, details or {}


def error_json(status_code: int, code: str, message: str, details: dict[str, Any] | None = None) -> JSONResponse:
    return JSONResponse(status_code=status_code,
                        content={"success": False, "error": {"code": code, "message": message, "details": details or {}}})


def _field_path(loc: tuple) -> str:
    parts = [str(p) for p in loc if p not in ("body", "query", "path", "form", "header")]
    return ".".join(parts) or "body"


def install_error_handling(app: FastAPI, cors_origins: list[str]) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return error_json(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _STATUS_TO_CODE.get(exc.status_code, "INTERNAL_ERROR")
        message = exc.detail if isinstance(exc.detail, str) else code
        return error_json(exc.status_code, code, message)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [{"field": _field_path(tuple(e.get("loc", ()))), "message": e.get("msg", "Invalid value"),
                   "type": e.get("type", "value_error")} for e in exc.errors()]
        return error_json(422, "VALIDATION_ERROR", "Request validation failed", {"fields": fields})

    # Catch-all as an HTTP middleware added BEFORE CORSMiddleware, so CORS stays the outer layer
    # and even 500 responses carry Access-Control-Allow-Origin (a plain Exception handler would not).
    @app.middleware("http")
    async def _catch_all(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception:  # noqa: BLE001
            log.exception("Unhandled error on %s %s", request.method, request.url.path)
            return error_json(500, "INTERNAL_ERROR", "Something went wrong. Please retry.")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
