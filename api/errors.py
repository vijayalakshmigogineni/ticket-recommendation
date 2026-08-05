"""Exception types + handlers for the debug API. This is a trusted, no-auth,
local-only engineering tool -- exposing tracebacks on uncaught errors is
acceptable and useful here, not a security concern.
"""

from __future__ import annotations

import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from recommender.ollama_client import OllamaError


class NotFoundError(Exception):
    def __init__(self, detail: str):
        self.detail = detail


class ConflictError(Exception):
    def __init__(self, detail: str):
        self.detail = detail


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"error": "not_found", "detail": exc.detail})

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"error": "conflict", "detail": exc.detail})

    @app.exception_handler(OllamaError)
    async def ollama_error_handler(request: Request, exc: OllamaError) -> JSONResponse:
        return JSONResponse(
            status_code=502, content={"error": "ollama_unreachable", "detail": str(exc)}
        )

    @app.exception_handler(OperationalError)
    async def db_error_handler(request: Request, exc: OperationalError) -> JSONResponse:
        return JSONResponse(
            status_code=503, content={"error": "database_unreachable", "detail": str(exc.orig)}
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "detail": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
