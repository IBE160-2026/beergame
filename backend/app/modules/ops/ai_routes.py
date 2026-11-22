"""`/api/admin/ai`: «KI-kostnad» for the Admin, its first page (Story 15.5, FR-68, FR-78): the
model configs with their measured Effort levels, each Class session's model setting, the pin and
the study freeze."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response

from app.modules.ops import ai_models
from app.modules.ops.ai_schemas import (
    FreezeIn,
    FreezeStateOut,
    ModelConfigListOut,
    ModelSessionListOut,
    ModelSessionOut,
    PinIn,
)
from app.platform import auth, authz
from app.platform.errors import documented, error_response

router = APIRouter(prefix="/api/admin/ai", tags=["admin"])

Manager = Annotated[authz.Principal, Depends(authz.require("ai_models.manage"))]


def _refused(refused: ai_models.Refused) -> Response:
    return error_response(refused.status, refused.code, refused.message, refused.fields or None)


@router.get(
    "/model-configs",
    response_model=ModelConfigListOut,
    responses=documented(401, 403),
    operation_id="listModelConfigs",
)
async def list_configs(_: Manager) -> Response:
    """Every model config with provider, endpoint, region, model version and per Effort level the
    newest measurement that counts here (cost per Game, fallback share, Play-guard switched
    share), as stored by Story 2.12."""
    return JSONResponse((await ai_models.list_configs()).model_dump(mode="json"))


@router.get(
    "/class-sessions",
    response_model=ModelSessionListOut,
    responses=documented(401, 403),
    operation_id="listModelSessions",
)
async def list_sessions(_: Manager) -> Response:
    """Every saved Class session, newest first, with its model config and Effort level; once
    locked, what `SessionRuntime` froze (model version, endpoint, prompt versions)."""
    found = await ai_models.list_sessions(now=auth.utcnow())
    return JSONResponse(found.model_dump(mode="json"))


@router.put(
    "/class-sessions/{class_session_id}/model-config",
    response_model=ModelSessionOut,
    responses=documented(401, 403, 404, 409, 422),
    operation_id="pinModelConfig",
)
async def pin(class_session_id: uuid.UUID, body: PinIn, user: Manager) -> Response:
    """Pin a model config for a Class session before its Start date (FR-68), audited as
    `model_config.pinned`. Refused with 409 `model_config_frozen` once the session is locked,
    `study_frozen` for another config in a frozen study, `no_measured_level` for a config with no
    measured Effort level here; 404 `config_not_found` or `not_found`. The answer warns
    `provider_key_missing` when its LLM players' provider has no key here (AD-17)."""
    try:
        found = await ai_models.pin(user, class_session_id, body.model_config_id, now=auth.utcnow())
    except ai_models.Refused as refused:
        return _refused(refused)
    if found is None:
        return error_response(404, "not_found", "No such Class session.")
    return JSONResponse(found.model_dump(mode="json"))


@router.get(
    "/freeze",
    response_model=FreezeStateOut,
    responses=documented(401, 403),
    operation_id="getModelFreeze",
)
async def freeze_state(_: Manager) -> Response:
    """The study freeze in force, or null."""
    return JSONResponse((await ai_models.freeze_state()).model_dump(mode="json"))


@router.post(
    "/freezes",
    response_model=FreezeStateOut,
    responses=documented(401, 403, 404, 409, 422),
    operation_id="freezeModelConfig",
)
async def freeze(body: FreezeIn, user: Manager) -> Response:
    """Freeze a model config for a learning study (FR-68): the chosen Class sessions get it and
    new ones get it as their default until it is lifted. Refused with 409 `freeze_active`,
    `no_measured_level` or `model_config_frozen` (a chosen session locked with another config,
    `fields.class_session_ids`); 404 `config_not_found` or `not_found`. Audited as
    `model_config.frozen`."""
    try:
        found = await ai_models.freeze(
            user, body.model_config_id, body.class_session_ids, now=auth.utcnow()
        )
    except ai_models.Refused as refused:
        return _refused(refused)
    return JSONResponse(found.model_dump(mode="json"))


@router.post(
    "/freezes/{freeze_id}/lift",
    response_model=FreezeStateOut,
    responses=documented(401, 403, 404, 409),
    operation_id="liftModelFreeze",
)
async def lift(freeze_id: uuid.UUID, user: Manager) -> Response:
    """Lift the study freeze, audited as `model_config.freeze_lifted`; 409 `freeze_lifted` when
    it was lifted already."""
    try:
        found = await ai_models.lift(user, freeze_id, now=auth.utcnow())
    except ai_models.Refused as refused:
        return _refused(refused)
    return JSONResponse(found.model_dump(mode="json"))
