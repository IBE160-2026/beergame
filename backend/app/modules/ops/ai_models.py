"""«KI-kostnad», its first page: the Admin pins and freezes a model config for Class sessions
(Story 15.5, FR-68, FR-78, FR-3, AD-4, AD-6, AD-17, UX-DR57).

- The model configs are listed with their Effort levels and the newest measurement of each that
  counts here, read through `ai.config.catalogue` exactly as stored (Story 2.12).
- A pin replaces a Class session's model config before its Start date
  (`sessions.service.pin_model_config`, under the session's row lock); once the session is
  locked or its Start date has passed it is refused with `model_config_frozen`, because the config
  is frozen in `SessionRuntime` (AD-4). Each change is audited as `model_config.pinned`.
- A study freeze (`ai.config.freeze`) pins one config to the chosen Class sessions and makes it
  the default of new ones until it is lifted; while it is in force a session of the study cannot
  be pinned to another config (`study_frozen`).

Only `app/ai` reads or writes the model config tables (AD-6); only `sessions` writes the Class
session row.

**Seam for Epic 12.** The AI assessment takes its model like the Debrief's AI text: a pin
provider registered with `sessions.register_pin_provider` reads `class_sessions.model_config_id`
at the lock, so a pin made here reaches it with nothing added.
"""

import uuid
from collections.abc import Collection
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.ai import config
from app.modules.ops.ai_schemas import (
    EffortLevelEntryOut,
    FreezeOut,
    FreezeStateOut,
    FrozenSettingOut,
    MeasurementOut,
    ModelConfigListOut,
    ModelConfigOut,
    ModelSessionListOut,
    ModelSessionOut,
)
from app.modules.sessions import service as sessions
from app.platform import audit, authz
from app.platform.db import get_sessionmaker

PIN_ACTION = "model_config.pinned"
FREEZE_ACTION = "model_config.frozen"
LIFT_ACTION = "model_config.freeze_lifted"
PROVIDER_KEY_MISSING = "provider_key_missing"
LLM = "llm"


@dataclass
class Refused(Exception):
    """A pin, freeze or lift the rules refuse; nothing was stored."""

    status: int
    code: str
    message: str
    fields: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__init__(self.code)


def _decimal(value: Decimal | None) -> str | None:
    """A stored figure as a decimal string without the column's trailing zeros."""
    return None if value is None else format(value.normalize(), "f")


def _measurement(found: config.EffortMeasurement | None) -> MeasurementOut | None:
    if found is None:
        return None
    return MeasurementOut(
        mock=found.mock,
        games=found.games,
        cost_per_game_usd=_decimal(found.cost_per_game_usd),
        fallback_share=_decimal(found.fallback_share),
        switched_share=_decimal(found.switched_share),
        time_per_order_p95_s=_decimal(found.time_per_order_p95_s),
        approved_at=found.approved_at,
    )


async def list_configs() -> ModelConfigListOut:
    """Every model config, oldest first, with its facts and measured Effort levels."""
    async with get_sessionmaker().begin() as s:
        entries = await config.catalogue(session=s)
        frozen = await config.active_freeze(session=s)
    items = []
    for entry in entries:
        spec = entry.config.spec
        items.append(
            ModelConfigOut(
                id=entry.config.id,
                name=spec.name,
                provider=spec.provider,
                endpoint=spec.endpoint,
                region=spec.region,
                model_version=spec.model_version,
                quantisation=spec.quantisation,
                prompts=dict(spec.prompts),
                referenced=entry.config.referenced,
                may_answer=entry.may_answer,
                pinnable=any(level.measurement is not None for level in entry.levels),
                active_default=entry.active_default,
                frozen=frozen is not None and frozen.model_config_id == entry.config.id,
                effort_levels=[
                    EffortLevelEntryOut(
                        name=level.level.name,
                        label=level.level.label,
                        offered=level.offered,
                        measurement=_measurement(level.measurement),
                    )
                    for level in entry.levels
                ],
            )
        )
    return ModelConfigListOut(items=items)


def _session_out(
    setting: sessions.ModelSetting,
    configs: dict[uuid.UUID, config.ModelConfig],
    frozen: config.Freeze | None,
) -> ModelSessionOut:
    found = configs.get(setting.model_config_id) if setting.model_config_id else None
    held = None
    if setting.frozen_model_config_id is not None:
        at_lock = configs.get(setting.frozen_model_config_id)
        held = FrozenSettingOut(
            model_config_id=setting.frozen_model_config_id,
            model_name=at_lock.spec.name if at_lock else None,
            model_version=at_lock.spec.model_version if at_lock else None,
            endpoint=at_lock.spec.endpoint if at_lock else None,
            effort_level=setting.frozen_effort_level,
            prompt_versions=dict(setting.prompt_versions or {}),
        )
    warnings = []
    if (
        setting.ai_mode == LLM
        and not setting.locked
        and found is not None
        and not config.may_answer(found)
    ):
        warnings.append(PROVIDER_KEY_MISSING)
    return ModelSessionOut(
        id=setting.id,
        number=setting.number,
        class_name=setting.class_name,
        institution_name=setting.institution_name,
        start_at=setting.start_at,
        locked=setting.locked,
        ai_mode=setting.ai_mode,
        model_config_id=setting.model_config_id,
        model_name=found.spec.name if found else None,
        model_version=found.spec.model_version if found else None,
        effort_level=setting.effort_level,
        in_freeze=frozen is not None and setting.id in frozen.class_session_ids,
        frozen=held,
        warnings=warnings,
    )


async def _sessions_out(ids: list[uuid.UUID] | None, *, now: datetime) -> list[ModelSessionOut]:
    async with get_sessionmaker().begin() as s:
        found = await sessions.model_settings(s, ids, now=now)
        configs = {row.id: row for row in await config.list_all(session=s)}
        frozen = await config.active_freeze(session=s)
    return [_session_out(item, configs, frozen) for item in found]


async def list_sessions(*, now: datetime) -> ModelSessionListOut:
    """Every saved Class session, newest first, with its model setting. No Student data."""
    return ModelSessionListOut(items=await _sessions_out(None, now=now))


async def _pinnable(s, config_id: uuid.UUID) -> None:
    try:
        measured = await config.measured_levels(config_id, session=s)
    except config.ConfigNotFound:
        raise Refused(404, "config_not_found", "No such model config.") from None
    if not measured:
        raise Refused(409, "no_measured_level", "The model config has no measured Effort level.")


async def _pin(
    s,
    actor: authz.Principal,
    class_session_id: uuid.UUID,
    config_id: uuid.UUID,
    *,
    now: datetime,
) -> bool:
    """Pin in the caller's transaction and audit a change; False when the session is gone."""
    try:
        outcome = await sessions.pin_model_config(s, class_session_id, config_id, now=now)
    except sessions.ModelConfigFrozen:
        raise Refused(
            409,
            sessions.ModelConfigFrozen.code,
            "The Class session is locked: its model config is frozen.",
            {"class_session_ids": [str(class_session_id)]},
        ) from None
    if outcome is None:
        return False
    if outcome.changed:
        await audit.record(
            s,
            actor.id,
            PIN_ACTION,
            {"class_session_id": class_session_id},
            {
                "model_config_id": str(config_id),
                "previous_model_config_id": (
                    str(outcome.previous) if outcome.previous is not None else None
                ),
            },
            now,
        )
    return True


async def pin(
    actor: authz.Principal, class_session_id: uuid.UUID, config_id: uuid.UUID, *, now: datetime
) -> ModelSessionOut | None:
    """Pin a model config for one Class session (FR-68); None when the session does not exist.
    Raises `Refused`."""
    async with get_sessionmaker().begin() as s:
        await _pinnable(s, config_id)
        frozen = await config.active_freeze(session=s)
        if (
            frozen is not None
            and class_session_id in frozen.class_session_ids
            and frozen.model_config_id != config_id
        ):
            raise Refused(
                409, "study_frozen", "The Class session belongs to a frozen learning study."
            )
        if not await _pin(s, actor, class_session_id, config_id, now=now):
            return None
    [found] = await _sessions_out([class_session_id], now=now)
    return found


def _freeze_out(found: config.Freeze, configs: dict[uuid.UUID, config.ModelConfig]) -> FreezeOut:
    held = configs.get(found.model_config_id)
    return FreezeOut(
        id=found.id,
        model_config_id=found.model_config_id,
        model_name=held.spec.name if held else None,
        model_version=held.spec.model_version if held else None,
        class_session_ids=list(found.class_session_ids),
        frozen_at=found.frozen_at,
        lifted_at=found.lifted_at,
    )


async def freeze_state() -> FreezeStateOut:
    async with get_sessionmaker().begin() as s:
        frozen = await config.active_freeze(session=s)
        configs = {row.id: row for row in await config.list_all(session=s)}
    return FreezeStateOut(active=_freeze_out(frozen, configs) if frozen else None)


async def freeze(
    actor: authz.Principal,
    config_id: uuid.UUID,
    class_session_ids: Collection[uuid.UUID],
    *,
    now: datetime,
) -> FreezeStateOut:
    """Freeze a config for a learning study (FR-68): the chosen Class sessions get it, in one
    transaction, and new ones get it as their default until the freeze is lifted. A chosen
    session that is locked must hold this config already. Raises `Refused`."""
    ids = list(dict.fromkeys(class_session_ids))
    async with get_sessionmaker().begin() as s:
        await _pinnable(s, config_id)
        found = {item.id: item for item in await sessions.model_settings(s, ids, now=now)}
        missing = [str(i) for i in ids if i not in found]
        if missing:
            raise Refused(
                404, "not_found", "No such Class session.", {"class_session_ids": missing}
            )
        blocked = [
            str(item.id)
            for item in found.values()
            if item.locked and (item.frozen_model_config_id or item.model_config_id) != config_id
        ]
        if blocked:
            raise Refused(
                409,
                sessions.ModelConfigFrozen.code,
                "A chosen Class session is locked with another model config.",
                {"class_session_ids": blocked},
            )
        try:
            made = await config.freeze(config_id, ids, now=now, session=s)
        except config.ConfigRefused as refused:
            raise Refused(409, refused.code, refused.message) from None
        for item in found.values():
            if not item.locked:
                await _pin(s, actor, item.id, config_id, now=now)
        await audit.record(
            s,
            actor.id,
            FREEZE_ACTION,
            {"model_config_id": config_id},
            {"freeze_id": str(made.id), "class_session_ids": [str(i) for i in ids]},
            now,
        )
    return await freeze_state()


async def lift(actor: authz.Principal, freeze_id: uuid.UUID, *, now: datetime) -> FreezeStateOut:
    """Lift a freeze: new Class sessions take the newest pin again; pinned ones keep their
    config. Raises `Refused`."""
    async with get_sessionmaker().begin() as s:
        try:
            lifted = await config.lift_freeze(freeze_id, now=now, session=s)
        except config.FreezeNotFound:
            raise Refused(404, "not_found", "No such freeze.") from None
        except config.ConfigRefused as refused:
            raise Refused(409, refused.code, refused.message) from None
        await audit.record(
            s,
            actor.id,
            LIFT_ACTION,
            {"model_config_id": lifted.model_config_id},
            {"freeze_id": str(lifted.id)},
            now,
        )
    return await freeze_state()


async def config_labels(ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    """«mock-two · mock-1» for the audit page's `model_config_id` targets."""
    return await config.config_labels(ids)
