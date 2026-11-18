"""`/api/admin/audit`: the audit log for the Admin (Story 3.12, FR-3, NFR-7). Read only; the
rows are written by the actions themselves through `platform/audit.record`."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response

from app.modules.admin import service
from app.modules.admin.schemas import (
    ACTION_MAX_LENGTH,
    AUDIT_PAGE_DEFAULT,
    AUDIT_PAGE_MAX,
    AuditActorsOut,
    AuditListOut,
)
from app.platform import authz
from app.platform.errors import documented, error_response

router = APIRouter(prefix="/api/admin/audit", tags=["admin"])

SYSTEM = "system"
"""The `actor` filter value for the rows the system wrote."""


@router.get(
    "",
    response_model=AuditListOut,
    responses=documented(401, 403, 422),
    operation_id="listAuditEvents",
)
async def list_audit_events(
    _: Annotated[authz.Principal, Depends(authz.require("audit.read"))],
    actor: Annotated[str | None, Query(max_length=36)] = None,
    action: Annotated[str | None, Query(max_length=ACTION_MAX_LENGTH)] = None,
    since: date | None = None,
    until: date | None = None,
    cursor: Annotated[str | None, Query(max_length=128)] = None,
    limit: Annotated[int, Query(ge=1, le=AUDIT_PAGE_MAX)] = AUDIT_PAGE_DEFAULT,
) -> Response:
    """Audit events newest first, with actor and target names read now (FR-3, AD-14). Filter by
    `actor` (a User id, or `system` for the rows with no actor), `action`, and the inclusive
    Europe/Oslo days `since` and `until`."""
    actor = actor or None  # an empty filter is no filter, as for `action`
    actor_id = None
    if actor is not None and actor != SYSTEM:
        try:
            actor_id = uuid.UUID(actor)
        except ValueError:
            return error_response(
                422, "invalid_request", "The actor is not valid.", {"actor": "invalid_actor"}
            )
    if since is not None and until is not None and until < since:
        return error_response(
            422, "invalid_request", "The range ends before it starts.", {"until": "range_reversed"}
        )
    try:
        page = await service.audit_page(
            cursor=cursor,
            limit=limit,
            actor=actor_id,
            system=actor == SYSTEM,
            action=action or None,
            since=since,
            until=until,
        )
    except service.InvalidCursor:
        return error_response(
            422, "invalid_request", "The cursor is not valid.", {"cursor": "invalid_cursor"}
        )
    return JSONResponse(page.model_dump(mode="json"))


@router.get(
    "/actors",
    response_model=AuditActorsOut,
    responses=documented(401, 403),
    operation_id="listAuditActors",
)
async def list_audit_actors(
    _: Annotated[authz.Principal, Depends(authz.require("audit.read"))],
) -> Response:
    """Everyone who appears as actor in the log, for the filter: the system first (`id` null),
    then Users by name."""
    return JSONResponse((await service.audit_actors()).model_dump(mode="json"))
