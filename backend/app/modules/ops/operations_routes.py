"""`/api/admin/operations`: «Drift» for the Admin (Story 15.8, NFR-8, FR-79, AD-12): error counts,
fallback, AI response times, the Play guard share and AI cost per Class session. Counts and
timings only; the Admin needs no Class membership, since nothing here is Student data (FR-5)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response

from app.modules.ops import connection_budget, operations
from app.modules.ops.operations_schemas import (
    ConnectionBudgetOut,
    OperationsOut,
    OperationsSessionListOut,
)
from app.platform import auth, authz
from app.platform.errors import documented, error_response

router = APIRouter(prefix="/api/admin/operations", tags=["admin"])

Reader = Annotated[authz.Principal, Depends(authz.require("operations.read"))]


@router.get(
    "/class-sessions",
    response_model=OperationsSessionListOut,
    responses=documented(401, 403),
    operation_id="listOperationsSessions",
)
async def list_sessions(_: Reader) -> Response:
    """Every saved Class session, newest first, with its errors of the last 24 hours."""
    found = await operations.list_sessions(auth.utcnow())
    return JSONResponse(found.model_dump(mode="json"))


@router.get(
    "/class-sessions/{class_session_id}",
    response_model=OperationsOut,
    responses=documented(401, 403, 404),
    operation_id="getSessionOperations",
)
async def session_figures(class_session_id: uuid.UUID, _: Reader) -> Response:
    """One Class session's errors by source and hour (the last 24 hours) and in total, the share
    of its LLM players' Orders each fallback kind replaced, their response times per Effort level
    (median and 95th percentile), the share of LLM Seats the Play guard switched, and its AI
    cost. 404 `not_found` for an unknown Class session."""
    found = await operations.session_figures(class_session_id, auth.utcnow())
    if found is None:
        return error_response(404, "not_found", "No such Class session.")
    return JSONResponse(found.model_dump(mode="json"))


class DeliberateTestError(RuntimeError):
    """Raised on purpose by the Admin's test error, so it reaches the tracker and «Drift»."""


TestErrorAdmin = Annotated[authz.Principal, Depends(authz.require("operations.test_error"))]


@router.post(
    "/class-sessions/{class_session_id}/test-error",
    responses=documented(401, 403, 404),
    operation_id="raiseOperationsTestError",
)
async def test_error(class_session_id: uuid.UUID, _: TestErrorAdmin) -> Response:
    """Raise a deliberate error in one Class session (Story 15.11, NFR-4): the answer is 500, the
    error tracker gets a report of type `DeliberateTestError`, and «Drift» counts one `api_error`
    for the session. The readiness record's check of the tracker in production. 404 `not_found`
    for an unknown Class session; nothing else is changed."""
    if not await operations.session_exists(class_session_id):
        return error_response(404, "not_found", "No such Class session.")
    raise DeliberateTestError("deliberate test error")


@router.get(
    "/connections",
    response_model=ConnectionBudgetOut,
    responses=documented(401, 403),
    operation_id="getConnectionBudget",
)
async def connections(_: Reader) -> Response:
    """The database connection budget (Story 15.9, NFR-3, NFR-4): per process its written budget
    and what its latest start reported, the sums against the budget and a deploy overlap, and the
    pooler check (`DB_POOLER_SIZE` against twice the budget plus the migration's connection; not
    checked while it is unset)."""
    found = await connection_budget.read_budget(auth.utcnow())
    return JSONResponse(found.model_dump(mode="json"))
