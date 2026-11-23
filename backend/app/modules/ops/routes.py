"""`/api/admin/evaluation`: «Pseudonymisert eksport» for the Admin (Story 15.4, FR-71, AD-12,
AD-14). The pseudonym key comes in a request body only, never in a URL, and no answer, error or
log line repeats it."""

import unicodedata
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import SecretStr

from app.modules.ops import evaluation
from app.modules.ops.schemas import (
    KEY_MAX,
    KEY_MIN,
    AgreementIn,
    EvaluationSessionListOut,
    EvaluationSessionOut,
    ExportIn,
    ExportListOut,
    KeyIn,
    KeyStateOut,
)
from app.platform import auth, authz
from app.platform.errors import documented, error_response

router = APIRouter(prefix="/api/admin/evaluation", tags=["admin"])

Manager = Annotated[authz.Principal, Depends(authz.require("evaluation.manage"))]


def _key(secret: SecretStr) -> str | Response:
    """The typed key without outer whitespace, or the 422 that names only the field."""
    # NFC, so the same key typed on another device (å as one character or two) is the same key.
    key = unicodedata.normalize("NFC", secret.get_secret_value().strip())
    if len(key) < KEY_MIN:
        return error_response(422, "invalid_request", "The key is too short.", {"key": "too_short"})
    if len(key) > KEY_MAX:
        return error_response(422, "invalid_request", "The key is too long.", {"key": "too_long"})
    return key


@router.get(
    "/class-sessions",
    response_model=EvaluationSessionListOut,
    responses=documented(401, 403),
    operation_id="listEvaluationSessions",
)
async def list_sessions(_: Manager) -> Response:
    """Every saved Class session, newest first, with its Institution agreement (or null) and the
    day its Student data is deleted (null while it has no Test deadline). No Student data."""
    return JSONResponse((await evaluation.list_sessions()).model_dump(mode="json"))


@router.put(
    "/class-sessions/{class_session_id}/agreement",
    response_model=EvaluationSessionOut,
    responses=documented(401, 403, 404, 422),
    operation_id="recordEvaluationAgreement",
)
async def record_agreement(
    class_session_id: uuid.UUID, body: AgreementIn, user: Manager
) -> Response:
    """Record or replace the Institution agreement of a Class session (FR-71): who agreed, on
    which day, and who is controller for the evaluation. Audited as
    `evaluation_agreement.recorded`."""
    now = auth.utcnow()
    if body.agreed_on > now.astimezone(evaluation.OSLO).date():
        return error_response(
            422,
            "invalid_request",
            "The agreement cannot be dated in the future.",
            {"agreed_on": "in_future"},
        )
    found = await evaluation.record_agreement(user, class_session_id, body, now=now)
    if found is None:
        return error_response(404, "not_found", "No such Class session.")
    return JSONResponse(found.model_dump(mode="json"))


@router.get(
    "/key",
    response_model=KeyStateOut,
    responses=documented(401, 403),
    operation_id="getPseudonymKeyState",
)
async def key_state(_: Manager) -> Response:
    """The stored fingerprint of the pseudonym key, or nulls before the first export."""
    return JSONResponse((await evaluation.key_state()).model_dump(mode="json"))


@router.post(
    "/key",
    response_model=KeyStateOut,
    responses=documented(401, 403, 422),
    operation_id="replacePseudonymKey",
)
async def replace_key(body: KeyIn, user: Manager) -> Response:
    """Replace the stored fingerprint with the new key's (AD-14), audited as
    `pseudonym_key.replaced`. Later exports must use the new key."""
    key = _key(body.key)
    if isinstance(key, Response):
        return key
    state = await evaluation.replace_key(user, key, now=auth.utcnow())
    return JSONResponse(state.model_dump(mode="json"))


@router.get(
    "/exports",
    response_model=ExportListOut,
    responses=documented(401, 403),
    operation_id="listEvaluationExports",
)
async def list_exports(_: Manager) -> Response:
    """The newest export runs and refusals: who, when, the Class sessions with their deletion
    dates, the key fingerprint and the outcome."""
    return JSONResponse((await evaluation.list_exports()).model_dump(mode="json"))


@router.post(
    "/exports",
    response_class=StreamingResponse,
    responses={
        200: {"content": {"application/zip": {"schema": {"type": "string", "format": "binary"}}}},
        **documented(401, 403, 409, 422),
    },
    operation_id="runEvaluationExport",
)
async def run_export(
    body: ExportIn,
    user: Annotated[authz.Principal, Depends(authz.require("export_pseudonymised"))],
) -> Response:
    """Run the pseudonymised export of the chosen Class sessions and stream it as a ZIP (FR-71).
    Refused with 403 `no_agreement` (`fields.class_session_ids`) when a Class session has no
    agreement, and 409 `pseudonym_key_changed` when the key is not the one whose fingerprint is
    stored. Every run and refusal is audited as `evaluation_export.run`."""
    key = _key(body.key)
    if isinstance(key, Response):
        return key
    try:
        export = await evaluation.run_export(user, body.class_session_ids, key, now=auth.utcnow())
    except evaluation.NoAgreement as refused:
        return error_response(
            403,
            evaluation.NO_AGREEMENT,
            "A chosen Class session has no Institution agreement.",
            {"class_session_ids": [str(i) for i in refused.class_session_ids]},
        )
    except evaluation.KeyChanged:
        return error_response(
            409,
            evaluation.KEY_CHANGED,
            "The key has changed: its fingerprint is not the stored one.",
        )
    return StreamingResponse(
        evaluation.zip_stream(export),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{evaluation.file_name(export)}"',
            "Cache-Control": "no-store",
        },
    )
