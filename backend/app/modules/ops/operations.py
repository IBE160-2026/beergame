"""«Drift»: the Admin's operations view per Class session (Story 15.8, NFR-8, FR-79, AD-6, AD-12,
AD-15).

Errors come from `error_events`, the store this module owns; AI cost and response times from
`ai.calls.session_figures` over the call rows; fallback and the Play guard from
`games.service.session_ai_figures` over the Decision log and occupancy through the AD-15 mark
mapping. Nothing is summed twice and no Student data is read: counts, timings and amounts only.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.ai import calls, config
from app.modules.games import service as games
from app.modules.ops.models import ERROR_SOURCES, error_events
from app.modules.ops.operations_schemas import (
    ErrorCountsOut,
    ErrorHourOut,
    FallbackOut,
    OperationsOut,
    OperationsSessionListOut,
    OperationsSessionOut,
    ResponseTimeOut,
)
from app.modules.sessions import service as sessions
from app.platform.db import get_sessionmaker

__all__ = ["HOURS", "REFETCH_S", "list_sessions", "session_figures"]

HOURS = 24
"""The hours «Feil per time» shows, the current one last."""
REFETCH_S = 30
"""How often the open view reads again (the web app's interval, UX-DR58)."""


def _share(part: int, whole: int) -> str | None:
    if whole <= 0:
        return None
    return format((Decimal(part) / Decimal(whole)).quantize(Decimal("0.0001")), "f")


def _usd(value: Decimal) -> str:
    return format(value.quantize(Decimal("1e-8")), "f")


def _label(item: sessions.EvaluationSession) -> str:
    return f"{item.class_name} · Klasseøkt {item.number}"


async def _level_labels(config_ids: tuple[uuid.UUID, ...]) -> dict[str, str]:
    """The Norwegian label of each Effort level name in these model configs (the first config
    that labels a name wins); a level without one is shown by its name."""
    labels: dict[str, str] = {}
    for config_id in config_ids:
        found = await config.get(config_id)
        if found is None:
            continue
        for level in found.spec.effort_levels:
            if level.label:
                labels.setdefault(level.name, level.label)
    return labels


def _hour_start(now: datetime) -> datetime:
    return now.replace(minute=0, second=0, microsecond=0)


async def list_sessions(now: datetime) -> OperationsSessionListOut:
    """Every saved Class session, newest first, with its errors of the last 24 hours."""
    # The view's 24 hour buckets: from the start of the hour 23 hours ago to the current hour's end.
    since = _hour_start(now) - timedelta(hours=HOURS - 1)
    async with get_sessionmaker()() as s:
        found = await sessions.evaluation_sessions(s)
        counts = dict(
            (
                await s.execute(
                    select(error_events.c.class_session_id, func.count())
                    .where(
                        error_events.c.class_session_id.is_not(None),
                        error_events.c.occurred_at >= since,
                        error_events.c.occurred_at < since + timedelta(hours=HOURS),
                    )
                    .group_by(error_events.c.class_session_id)
                )
            ).all()
        )
    return OperationsSessionListOut(
        read_at=now,
        items=[
            OperationsSessionOut(
                id=item.id,
                label=_label(item),
                institution_name=item.institution_name,
                errors_24h=counts.get(item.id, 0),
            )
            for item in found
        ],
    )


async def session_exists(class_session_id: uuid.UUID) -> bool:
    """Whether a Class session of that id exists (the deliberate test error's 404)."""
    async with get_sessionmaker()() as s:
        return bool(await sessions.evaluation_sessions(s, [class_session_id]))


async def session_figures(class_session_id: uuid.UUID, now: datetime) -> OperationsOut | None:
    """The operations figures of one Class session, or None when there is no such session."""
    first_hour = _hour_start(now) - timedelta(hours=HOURS - 1)
    # Truncated in UTC whatever the connection's time zone; Oslo's offset is whole hours, so the
    # web app labels each start in Oslo time.
    hour = func.date_trunc("hour", error_events.c.occurred_at, "UTC").label("hour")
    in_session = error_events.c.class_session_id == class_session_id
    async with get_sessionmaker()() as s:
        found = await sessions.evaluation_sessions(s, [class_session_id])
        if not found:
            return None
        totals = dict(
            (
                await s.execute(
                    select(error_events.c.source, func.count())
                    .where(in_session)
                    .group_by(error_events.c.source)
                )
            ).all()
        )
        hourly = (
            await s.execute(
                select(hour, error_events.c.source, func.count())
                .where(
                    in_session,
                    error_events.c.occurred_at >= first_hour,
                    error_events.c.occurred_at < first_hour + timedelta(hours=HOURS),
                )
                .group_by(hour, error_events.c.source)
            )
        ).all()
    ai = await calls.session_figures(class_session_id)
    played = await games.session_ai_figures(class_session_id)
    labels = await _level_labels(ai.config_ids)
    by_hour: dict[datetime, dict[str, int]] = {}
    for start, source, count in hourly:
        by_hour.setdefault(start, {})[source] = count
    hours = []
    for offset in range(HOURS):
        start = first_hour + timedelta(hours=offset)
        counted = by_hour.get(start, {})
        hours.append(
            ErrorHourOut(hour=start, **{src: counted.get(src, 0) for src in ERROR_SOURCES})
        )
    [item] = found
    return OperationsOut(
        class_session_id=class_session_id,
        label=_label(item),
        institution_name=item.institution_name,
        read_at=now,
        hours=hours,
        totals=ErrorCountsOut(**{src: totals.get(src, 0) for src in ERROR_SOURCES}),
        llm_orders=played.llm_orders,
        fallbacks=[
            FallbackOut(
                kind=line.kind.value,
                orders=line.orders,
                share=_share(line.orders, played.llm_orders),
            )
            for line in played.fallbacks
        ],
        response_times=[
            ResponseTimeOut(
                effort_level=level.effort_level,
                label=labels.get(level.effort_level),
                calls=level.calls,
                median_ms=level.median_ms,
                p95_ms=level.p95_ms,
            )
            for level in ai.levels
        ],
        llm_seats=played.llm_seats,
        switched_seats=played.switched_seats,
        switched_share=_share(played.switched_seats, played.llm_seats),
        cost_usd=_usd(ai.usd),
        ai_calls=ai.calls,
    )
