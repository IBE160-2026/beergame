"""The AD-19 error envelope: `{"error": {"code", "message", "fields"}}`. The web app maps each
stable `code` to Norwegian copy; `message` is developer text."""

from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str
    message: str
    fields: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    error: ErrorBody


def error_response(
    status: int,
    code: str,
    message: str,
    fields: dict | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "fields": fields or {}}},
        headers=headers,
    )


def documented(*statuses: int) -> dict[int | str, dict[str, Any]]:
    """`responses=` for a route: each status answers with the envelope (for the OpenAPI client)."""
    return {status: {"model": ErrorEnvelope} for status in statuses}
