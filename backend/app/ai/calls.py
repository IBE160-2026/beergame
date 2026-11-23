"""Reading `llm_call` rows (FR-67, FR-69): what one call's attempts cost and took, for reports
such as `python -m app.sim endpoint`, a scope's cost per Game and day for
`python -m app.ai.cli cost`, and the player attempts of a simulation batch's Games for
`python -m app.sim report` (Story 2.11). Only `app/ai` reads the table (AD-6)."""

import uuid
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import ARRAY, Uuid, any_, func, literal, or_, select, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.budget import BudgetScope
from app.ai.db import transaction
from app.ai.models import (
    budgets,
    default_pins,
    effort_measurements,
    llm_calls,
    model_configs,
    model_freezes,
    spend_alerts,
)

CALL_TABLE = llm_calls.name
"""The call table's name, for the personal-data registry (Story 15.2): only `app/ai` spells it."""

TABLES_WITHOUT_PERSONAL_DATA = {
    budgets.name: "Budgets per scope.",
    default_pins.name: "Pinned model configs.",
    model_configs.name: "Model configs.",
    effort_measurements.name: "Simulation measurements.",
    model_freezes.name: "Study freezes of a model config: ids and times only (Story 15.5).",
    spend_alerts.name: "Daily AI spend alerts: a day, amounts and a time (Story 15.7).",
}
"""The `app/ai` tables that hold no personal data, for the registry (Story 15.2, AD-14)."""

EMPTY_REQUEST = literal({}, JSONB)
"""The request body of a call whose body was cleared (Story 15.2)."""


@dataclass(frozen=True)
class Attempt:
    id: uuid.UUID
    attempt: int
    outcome: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    cost_usd: Decimal
    served_model: str | None
    served_by: str | None
    error: str | None


@dataclass(frozen=True)
class CostLine:
    """The summed cost and the number of attempts of one group of `llm_call` rows."""

    key: str
    usd: Decimal
    calls: int


@dataclass(frozen=True)
class Costs:
    total: CostLine
    games: list[CostLine]
    """Per Game in the rows' caller reference (`-` for rows without one), dearest first."""
    days: list[CostLine]
    """Per UTC day of `started_at`, oldest first."""


async def costs(scope: BudgetScope) -> Costs:
    """The AI cost of a scope summed from its settled `llm_call` rows (every outcome, so failed
    and late attempts count too), in total, per Game and per day (FR-69)."""
    where = (llm_calls.c.scope_kind == scope.kind) & (llm_calls.c.scope_id == scope.id)
    usd = func.coalesce(func.sum(llm_calls.c.cost_usd), 0)
    calls = func.count(llm_calls.c.id)
    # Labelled, so GROUP BY and ORDER BY name the column instead of repeating its parameters.
    game = func.coalesce(llm_calls.c.caller_ref["game"].astext, "-").label("game")
    day = func.to_char(func.timezone("UTC", llm_calls.c.started_at), "YYYY-MM-DD").label("day")
    usd = usd.label("usd")
    async with transaction(None) as session:
        total = (await session.execute(select(usd, calls).where(where))).one()
        games = (
            await session.execute(
                select(game, usd, calls)
                .where(where)
                .group_by(game)
                .order_by(usd.desc(), game.asc())
            )
        ).all()
        days = (
            await session.execute(select(day, usd, calls).where(where).group_by(day).order_by(day))
        ).all()

    def line(key: str, amount: object, count: int) -> CostLine:
        return CostLine(key, Decimal(str(amount)).quantize(Decimal("1e-8")), count)

    return Costs(
        line("total", *total),
        [line(*row) for row in games],
        [line(*row) for row in days],
    )


OSLO = ZoneInfo("Europe/Oslo")
"""The day a daily spend is summed over (Story 15.7, AD-6)."""


def oslo_day(day: date) -> tuple[datetime, datetime]:
    """The start and end of the Europe/Oslo calendar day `day`, as aware times."""
    return (
        datetime.combine(day, time(0), OSLO),
        datetime.combine(day + timedelta(days=1), time(0), OSLO),
    )


def oslo_date(now: datetime) -> date:
    """The Europe/Oslo calendar day that holds `now`."""
    return now.astimezone(OSLO).date()


@dataclass(frozen=True)
class ScopeSpend:
    """One Class session's AI spend on a day."""

    class_session_id: uuid.UUID
    usd: Decimal
    calls: int


@dataclass(frozen=True)
class DaySpend:
    """The AI spend of one Europe/Oslo day across every scope (Story 15.7, FR-69)."""

    day: date
    total_usd: Decimal
    calls: int
    evaluation_usd: Decimal
    """What simulation runs (evaluation budgets) spent, apart from Class sessions (AD-22)."""
    sessions: list[ScopeSpend]
    """The dearest Class sessions, dearest first (ties by id), at most `top`."""
    session_count: int
    """How many Class sessions spent anything that day."""


def _usd(amount: object) -> Decimal:
    return Decimal(str(amount)).quantize(Decimal("1e-8"))


async def day_spend(day: date, *, top: int = 10, session: AsyncSession | None = None) -> DaySpend:
    """The AI spend of the Europe/Oslo day `day`: every `llm_call` row (every outcome and scope)
    whose `started_at` lies in that day, summed unrounded, with the dearest `top` Class sessions
    and the evaluation scopes as one sum. The one place the daily spend is summed (AD-6): the
    alert of Story 15.7, its mail and «KI-kostnad» read it here."""
    start, end = oslo_day(day)
    in_day = (llm_calls.c.started_at >= start) & (llm_calls.c.started_at < end)
    usd = func.coalesce(func.sum(llm_calls.c.cost_usd), 0).label("usd")
    calls = func.count(llm_calls.c.id).label("calls")
    is_session = llm_calls.c.scope_kind == "class_session"
    is_evaluation = llm_calls.c.scope_kind == "evaluation"
    # Total, evaluation sum and session count in one statement, so they agree with each other.
    figures = select(
        usd,
        calls,
        func.coalesce(func.sum(llm_calls.c.cost_usd).filter(is_evaluation), 0).label("evaluation"),
        func.count(func.distinct(llm_calls.c.scope_id)).filter(is_session).label("sessions"),
    ).where(in_day)
    in_sessions = in_day & is_session
    async with transaction(session) as s:
        total = (await s.execute(figures)).one()
        rows = []
        if top > 0:
            rows = (
                await s.execute(
                    select(llm_calls.c.scope_id, usd, calls)
                    .where(in_sessions)
                    .group_by(llm_calls.c.scope_id)
                    .order_by(usd.desc(), llm_calls.c.scope_id)
                    .limit(top)
                )
            ).all()
    return DaySpend(
        day=day,
        total_usd=_usd(total.usd),
        calls=total.calls,
        evaluation_usd=_usd(total.evaluation),
        sessions=[ScopeSpend(row.scope_id, _usd(row.usd), row.calls) for row in rows],
        session_count=total.sessions,
    )


@dataclass(frozen=True)
class SessionCost:
    """One Class session's AI cost (Story 15.6, FR-69): every call of its scope, and those that
    name a Game."""

    class_session_id: uuid.UUID
    usd: Decimal
    calls: int
    games: dict[uuid.UUID, Decimal]
    """Per Game its calls name (`game` or `game_id`), by Game id."""


def _game_id(key: str | None) -> uuid.UUID | None:
    """The Game id a caller reference names; None for none, or for a value that is no id."""
    if key is None:
        return None
    try:
        return uuid.UUID(key)
    except ValueError:
        return None


def _game_key() -> Any:
    """The Game a call names: `game` (players) or `game_id` (narrations, Adapted items)."""
    return func.coalesce(
        llm_calls.c.caller_ref["game"].astext, llm_calls.c.caller_ref["game_id"].astext
    )


async def session_costs(
    ids: Collection[uuid.UUID] | None = None, *, session: AsyncSession | None = None
) -> dict[uuid.UUID, SessionCost]:
    """The AI cost of these Class sessions' scopes (every one with calls when None), summed
    unrounded over every outcome, by id; a session with no call is left out. The one place a
    Class session's total is summed for «KI-kostnad» (AD-6)."""
    where = llm_calls.c.scope_kind == "class_session"
    if ids is not None:
        if not ids:
            return {}
        where = where & llm_calls.c.scope_id.in_(list(ids))
    game = _game_key().label("game")
    query = (
        select(
            llm_calls.c.scope_id,
            game,
            func.sum(llm_calls.c.cost_usd),
            func.count(llm_calls.c.id),
        )
        .where(where)
        .group_by(llm_calls.c.scope_id, game)
    )
    async with transaction(session) as s:
        rows = (await s.execute(query)).all()
    found: dict[uuid.UUID, SessionCost] = {}
    for scope_id, key, usd, count in rows:
        item = found.get(scope_id) or SessionCost(scope_id, Decimal(0), 0, {})
        game_id = _game_id(key)
        games = dict(item.games)
        if game_id is not None:
            games[game_id] = games.get(game_id, Decimal(0)) + _usd(usd)
        found[scope_id] = SessionCost(scope_id, item.usd + _usd(usd), item.calls + count, games)
    return found


@dataclass(frozen=True)
class GameCost:
    game_id: uuid.UUID | None
    """None: the calls that name no Game (the Debrief, follow-ups, the AI assessment)."""
    usd: Decimal
    calls: int


@dataclass(frozen=True)
class DayCost:
    day: date
    """The Europe/Oslo calendar day of `started_at`."""
    usd: Decimal
    calls: int


@dataclass(frozen=True)
class SessionBreakdown:
    """One Class session's AI cost per Game and per day (Story 15.6, FR-69)."""

    games: list[GameCost]
    """Per Game in the calls' caller reference, by Game id; the calls naming none last."""
    days: list[DayCost]
    """Per Europe/Oslo day, oldest first."""
    dearest_reserve_call: Decimal | None
    """The largest cost of one attempt of a purpose other than the players' (what the reserve
    pays for); None before any."""


async def session_breakdown(
    class_session_id: uuid.UUID, *, session: AsyncSession | None = None
) -> SessionBreakdown:
    """A Class session scope's AI cost per Game and per Europe/Oslo day, summed unrounded over
    every outcome, and the dearest non-player attempt so far."""
    where = (llm_calls.c.scope_kind == "class_session") & (llm_calls.c.scope_id == class_session_id)
    usd = func.coalesce(func.sum(llm_calls.c.cost_usd), 0).label("usd")
    calls = func.count(llm_calls.c.id).label("calls")
    game = _game_key().label("game")
    day = func.to_char(func.timezone(str(OSLO), llm_calls.c.started_at), "YYYY-MM-DD").label("day")
    async with transaction(session) as s:
        games = (await s.execute(select(game, usd, calls).where(where).group_by(game))).all()
        days = (
            await s.execute(select(day, usd, calls).where(where).group_by(day).order_by(day))
        ).all()
        dearest = (
            await s.execute(
                select(func.max(llm_calls.c.cost_usd)).where(
                    where, llm_calls.c.purpose != PLAYER_PURPOSE
                )
            )
        ).scalar_one()
    merged: dict[uuid.UUID | None, tuple[Decimal, int]] = {}
    for key, amount, count in games:
        game_id = _game_id(key)
        usd, calls_so_far = merged.get(game_id, (Decimal(0), 0))
        merged[game_id] = (usd + _usd(amount), calls_so_far + count)
    lines = [GameCost(game_id, usd, count) for game_id, (usd, count) in merged.items()]
    lines.sort(key=lambda line: (line.game_id is None, str(line.game_id)))
    return SessionBreakdown(
        games=lines,
        days=[DayCost(date.fromisoformat(key), _usd(amount), count) for key, amount, count in days],
        dearest_reserve_call=None if dearest is None else _usd(dearest),
    )


@dataclass(frozen=True)
class LevelTimes:
    """The response times of one Effort level's player attempts (nearest rank)."""

    effort_level: str
    calls: int
    median_ms: int
    p95_ms: int


@dataclass(frozen=True)
class SessionFigures:
    """The AI figures of one Class session (Story 15.8, NFR-8)."""

    usd: Decimal
    """Every call of the session's scope, every purpose and outcome, unrounded."""
    calls: int
    levels: list[LevelTimes]
    """Per Effort level of its `player_order` attempts, by name."""
    config_ids: tuple[uuid.UUID, ...] = ()
    """The model configs of those attempts, so a reader can name each level by its label."""


async def session_figures(class_session_id: uuid.UUID) -> SessionFigures:
    """The AI cost of a Class session's scope and the response times of its LLM players' attempts
    per Effort level, median and 95th percentile by nearest rank (`percentile_disc`), as
    `python -m app.sim report` takes them (Story 2.11). The one place they are read (AD-6)."""
    in_scope = (llm_calls.c.scope_kind == "class_session") & (
        llm_calls.c.scope_id == class_session_id
    )
    latency = llm_calls.c.latency_ms
    async with transaction(None) as session:
        total = (
            await session.execute(
                select(
                    func.coalesce(func.sum(llm_calls.c.cost_usd), 0), func.count(llm_calls.c.id)
                ).where(in_scope)
            )
        ).one()
        rows = (
            await session.execute(
                select(
                    llm_calls.c.effort_level,
                    func.count(llm_calls.c.id),
                    func.percentile_disc(0.5).within_group(latency),
                    func.percentile_disc(0.95).within_group(latency),
                )
                .where(in_scope, llm_calls.c.purpose == PLAYER_PURPOSE)
                .group_by(llm_calls.c.effort_level)
                .order_by(llm_calls.c.effort_level)
            )
        ).all()
        config_ids = (
            (
                await session.execute(
                    select(llm_calls.c.model_config_id)
                    .where(in_scope, llm_calls.c.purpose == PLAYER_PURPOSE)
                    .distinct()
                )
            )
            .scalars()
            .all()
        )
    return SessionFigures(
        usd=_usd(total[0]),
        calls=total[1],
        levels=[
            LevelTimes(level, count, int(median), int(p95)) for level, count, median, p95 in rows
        ],
        config_ids=tuple(sorted(config_ids)),
    )


async def get(ids: Sequence[uuid.UUID]) -> list[Attempt]:
    """The rows with these ids, in attempt order."""
    if not ids:
        return []
    columns = [getattr(llm_calls.c, name) for name in Attempt.__dataclass_fields__]
    async with transaction(None) as session:
        rows = (
            await session.execute(
                select(*columns)
                .where(llm_calls.c.id.in_(list(ids)))
                .order_by(llm_calls.c.started_at, llm_calls.c.attempt)
            )
        ).all()
    return [Attempt(*row) for row in rows]


EXPORT_COLUMNS = (
    "id",
    "purpose",
    "model_config_id",
    "provider",
    "endpoint",
    "model_version",
    "quantisation",
    "effort_level",
    "seed",
    "temperature",
    "prompt_version",
    "attempt",
    "input_tokens",
    "output_tokens",
    "reasoning_tokens",
    "cost_usd",
    "latency_ms",
    "outcome",
    "served_model",
    "served_by",
    "started_at",
)
"""The call metadata in the pseudonymised export (Story 15.4, FR-67, FR-71): no body, no caller
reference and no error text, which could quote what the call was about."""


async def export_metadata(
    ids: Sequence[uuid.UUID], session: AsyncSession | None = None
) -> tuple[tuple[str, ...], list[tuple]]:
    """The metadata of the calls with these ids, oldest first (Story 15.4)."""
    if not ids:
        return EXPORT_COLUMNS, []
    columns = [getattr(llm_calls.c, name) for name in EXPORT_COLUMNS]
    async with transaction(session) as session:
        rows = (
            await session.execute(
                select(*columns)
                .where(llm_calls.c.id == any_(literal(list(ids), ARRAY(Uuid))))
                .order_by(llm_calls.c.started_at, llm_calls.c.id)
            )
        ).all()
    return EXPORT_COLUMNS, [tuple(row) for row in rows]


PLAYER_PURPOSE = "player_order"
"""The purpose of an LLM player's Order (`players.llm.PURPOSE`); named here, since `app/ai`
imports nothing from `modules` (AD-6)."""


@dataclass(frozen=True)
class GameAttempt:
    """One player attempt of a Game, as a simulation batch report reads it (Story 2.11)."""

    id: uuid.UUID
    game: str
    """The Game id in the row's caller reference."""
    attempt: int
    outcome: str
    effort_level: str
    started_at: datetime
    latency_ms: int
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    cost_usd: Decimal


async def game_attempts(game_ids: Sequence[str]) -> list[GameAttempt]:
    """Every `player_order` attempt whose caller reference names one of `game_ids`, of every
    outcome, oldest first (FR-67, FR-78)."""
    if not game_ids:
        return []
    game = llm_calls.c.caller_ref["game"].astext
    columns = [
        llm_calls.c.id,
        game.label("game"),
        llm_calls.c.attempt,
        llm_calls.c.outcome,
        llm_calls.c.effort_level,
        llm_calls.c.started_at,
        llm_calls.c.latency_ms,
        llm_calls.c.input_tokens,
        llm_calls.c.output_tokens,
        llm_calls.c.reasoning_tokens,
        llm_calls.c.cost_usd,
    ]
    async with transaction(None) as session:
        rows = (
            await session.execute(
                select(*columns)
                .where(
                    llm_calls.c.purpose == PLAYER_PURPOSE,
                    game.in_([str(game_id) for game_id in game_ids]),
                )
                .order_by(llm_calls.c.started_at, llm_calls.c.id)
            )
        ).all()
    return [GameAttempt(*row) for row in rows]


async def clear_bodies_of_user(session: AsyncSession, user_id: uuid.UUID) -> int:
    """Story 15.2 (FR-76, AD-14): empty the scrubbed request and the response of every call made
    for the User, in the caller's transaction: those whose `caller_ref` names them (a Debrief
    follow-up question quotes the Student's own text). The row stays, with its cost, tokens and
    outcome, so cost sums do not change. Idempotent; returns how many rows held a body."""
    result = await session.execute(
        update(llm_calls)
        .where(
            llm_calls.c.caller_ref["user_id"].astext == str(user_id),
            or_(llm_calls.c.request != EMPTY_REQUEST, llm_calls.c.response.is_not(None)),
        )
        .values(request=EMPTY_REQUEST, response=None)
    )
    return result.rowcount or 0


async def clear_bodies_by_ref(
    session: AsyncSession, name: str, values: Collection[uuid.UUID]
) -> int:
    """As `clear_bodies_of_user`, for the calls whose `caller_ref[name]` is one of `values`: the
    AI assessment's calls name the Test attempt (`attempt_id`), and their bodies hold the
    Student's answer (Story 15.2 after Epic 12). Idempotent; returns how many rows held a body."""
    if not values:
        return 0
    result = await session.execute(
        update(llm_calls)
        .where(
            llm_calls.c.caller_ref[name].astext.in_(sorted(str(value) for value in values)),
            or_(llm_calls.c.request != EMPTY_REQUEST, llm_calls.c.response.is_not(None)),
        )
        .values(request=EMPTY_REQUEST, response=None)
    )
    return result.rowcount or 0
