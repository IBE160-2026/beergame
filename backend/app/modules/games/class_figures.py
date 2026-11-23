"""What the Klasserapport reads of `games` (Story 14.1, FR-64, FR-68, FR-70, FR-79, AD-15, AD-25).

Each read takes the Class session or the Games the caller chose and answers in one query whatever
their number (NFR-3): the Class games' `game_summaries` rows, the stored facts sets' Order
amplification and Student pattern occurrences (never built here: a facts set missing is a game
not covered yet), the Decision log's counts per Seat, the occupancy rows of LLM players and of the
switches, the Seats per Game and the plausibility ratings per AI mode and value. Ids, Roles,
Weeks and counts only: never a name, never a `user_id` (AD-14). Exported through `games.service`.
"""

import uuid
from collections.abc import Collection
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.games.models import (
    believability_ratings,
    game_summaries,
    games,
    seat_occupancy,
    seat_weeks,
    seats,
)
from app.modules.games.schemas import (
    DecidedBy,
    Fallback,
    GameStatus,
    OccupancyReason,
    OccupantKind,
    Purpose,
)

__all__ = [
    "ClassGameRow",
    "FactFigures",
    "OccupancyFigure",
    "SeatFigure",
    "class_orders",
    "report_class_games",
    "fact_figures",
    "occupancy_figures",
    "rating_counts",
    "seat_counts",
    "seat_figures",
]


@dataclass(frozen=True)
class ClassGameRow:
    """A Class game of the Class session as its `game_summaries` row has it (AD-25)."""

    game_id: uuid.UUID
    number: int | None
    finished: bool
    chain_cost: Decimal | None


async def report_class_games(
    session: AsyncSession, class_session_id: uuid.UUID
) -> list[ClassGameRow]:
    """Every Class game (`purpose = class`) of the Class session from `game_summaries`, by game
    number: lecturer test Games, simulations, Replays and make-up games are never one (AD-13)."""
    result = await session.execute(
        select(
            game_summaries.c.game_id,
            game_summaries.c.game_number,
            game_summaries.c.status,
            game_summaries.c.chain_cost,
        )
        .where(
            game_summaries.c.class_session_id == class_session_id,
            game_summaries.c.purpose == Purpose.CLASS,
        )
        .order_by(game_summaries.c.game_number, game_summaries.c.game_id)
    )
    return [
        ClassGameRow(
            game_id=row.game_id,
            number=row.game_number,
            finished=row.status == GameStatus.FINISHED,
            chain_cost=row.chain_cost,
        )
        for row in result
    ]


@dataclass(frozen=True)
class FactFigures:
    """The stored facts sets of the Games: how many Seats have one per Game, each Game's Order
    amplification per Role (the chain part, the same in every set of a Game; None when customer
    demand never varied) and the Student-decided pattern occurrences per Game and pattern."""

    seats: dict[uuid.UUID, int]
    amplification: dict[uuid.UUID, dict[str, Decimal | None]]
    patterns: dict[uuid.UUID, dict[str, int]]


_FACT_SEATS = text(
    """
    SELECT game_id, count(*) AS seats,
           (array_agg(payload -> 'facts' -> 'chain' -> 'by_role' ORDER BY seat_id))[1] AS by_role
    FROM fact_sets
    WHERE game_id = ANY(:ids)
    GROUP BY game_id
    """
)

_FACT_PATTERNS = text(
    """
    SELECT f.game_id, occurrence ->> 'pattern' AS pattern, count(*) AS occurrences
    FROM fact_sets AS f
    CROSS JOIN LATERAL jsonb_array_elements(f.payload -> 'facts' -> 'seat' -> 'patterns')
        AS occurrence
    WHERE f.game_id = ANY(:ids) AND occurrence ->> 'decided_by' = :student
    GROUP BY f.game_id, occurrence ->> 'pattern'
    """
)


async def fact_figures(session: AsyncSession, game_ids: Collection[uuid.UUID]) -> FactFigures:
    """`FactFigures` of the Games in two reads; JSON is taken apart in SQL, so the sets' moments
    and the Weeks each occurrence saw never leave the database."""
    found = FactFigures(seats={}, amplification={}, patterns={})
    if not game_ids:
        return found
    ids = list(game_ids)
    for row in await session.execute(_FACT_SEATS, {"ids": ids}):
        found.seats[row.game_id] = row.seats
        found.amplification[row.game_id] = {
            part["role"]: None if part["amplification"] is None else Decimal(part["amplification"])
            for part in row.by_role or []
        }
    student = DecidedBy.STUDENT.value
    for row in await session.execute(_FACT_PATTERNS, {"ids": ids, "student": student}):
        found.patterns.setdefault(row.game_id, {})[row.pattern] = row.occurrences
    return found


@dataclass(frozen=True)
class SeatFigure:
    """One Seat's Decision log in counts (AD-15): its Weeks held by a Student and by an AI
    player (`occupant_kind`), its Orders outside Guided Weeks, those an LLM player decided and
    those replaced by the fallback."""

    game_id: uuid.UUID
    role: str
    student_weeks: int
    ai_weeks: int
    ordered: int
    llm: int
    fallback: int


async def seat_figures(session: AsyncSession, game_ids: Collection[uuid.UUID]) -> list[SeatFigure]:
    """`SeatFigure` of every Seat of the Games with a Decision log row, in one read."""
    if not game_ids:
        return []
    student = seat_weeks.c.occupant_kind == OccupantKind.STUDENT
    result = await session.execute(
        select(
            seat_weeks.c.game_id,
            seats.c.role,
            func.count().filter(student).label("student_weeks"),
            func.count().filter(~student).label("ai_weeks"),
            func.count().filter(seat_weeks.c.decided_by != DecidedBy.GUIDED).label("ordered"),
            func.count().filter(seat_weeks.c.decided_by == DecidedBy.LLM).label("llm"),
            func.count().filter(seat_weeks.c.fallback != Fallback.NONE).label("fallback"),
        )
        .select_from(seat_weeks.join(seats, seats.c.id == seat_weeks.c.seat_id))
        .where(seat_weeks.c.game_id.in_(list(game_ids)))
        .group_by(seat_weeks.c.game_id, seats.c.role)
    )
    return [
        SeatFigure(
            game_id=row.game_id,
            role=row.role,
            student_weeks=row.student_weeks,
            ai_weeks=row.ai_weeks,
            ordered=row.ordered,
            llm=row.llm,
            fallback=row.fallback,
        )
        for row in result
    ]


@dataclass(frozen=True)
class OccupancyFigure:
    """An occupancy row of an LLM player, or of a switch by the cost limit or the Play guard:
    the Seat (Game, Role), from which Week, who holds it and why (AD-15)."""

    game_id: uuid.UUID
    role: str
    from_week: int
    occupant_kind: str | None
    reason: str


SWITCH_REASONS = (OccupancyReason.GUARD_SWITCH, OccupancyReason.COST_LIMIT)


async def occupancy_figures(
    session: AsyncSession, game_ids: Collection[uuid.UUID]
) -> list[OccupancyFigure]:
    """Every occupancy row of the Games that put an LLM player in a Seat or switched one by the
    cost limit or the Play guard, oldest first per Seat, in one read."""
    if not game_ids:
        return []
    result = await session.execute(
        select(
            seats.c.game_id,
            seats.c.role,
            seat_occupancy.c.from_week,
            seat_occupancy.c.occupant_kind,
            seat_occupancy.c.reason,
        )
        .select_from(seat_occupancy.join(seats, seats.c.id == seat_occupancy.c.seat_id))
        .where(
            seats.c.game_id.in_(list(game_ids)),
            (seat_occupancy.c.occupant_kind == OccupantKind.LLM)
            | seat_occupancy.c.reason.in_([str(reason) for reason in SWITCH_REASONS]),
        )
        .order_by(seats.c.game_id, seats.c.position, seat_occupancy.c.from_week)
    )
    return [
        OccupancyFigure(
            game_id=row.game_id,
            role=row.role,
            from_week=row.from_week,
            occupant_kind=row.occupant_kind,
            reason=row.reason,
        )
        for row in result
    ]


async def seat_counts(
    session: AsyncSession, game_ids: Collection[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """The number of Seats of each Game, in one read."""
    if not game_ids:
        return {}
    result = await session.execute(
        select(seats.c.game_id, func.count())
        .where(seats.c.game_id.in_(list(game_ids)))
        .group_by(seats.c.game_id)
    )
    return {game_id: count for game_id, count in result}


async def rating_counts(
    session: AsyncSession, class_session_id: uuid.UUID
) -> dict[str, dict[int, int]]:
    """The plausibility ratings (Story 10.8, FR-70) of the Class session's Class games and
    Replays, counted per AI mode and value: no `user_id` leaves the database, and a single
    rating is never returned on its own."""
    result = await session.execute(
        select(believability_ratings.c.ai_mode, believability_ratings.c.rating, func.count())
        .select_from(
            believability_ratings.join(games, games.c.id == believability_ratings.c.game_id)
        )
        .where(
            games.c.class_session_id == class_session_id,
            believability_ratings.c.purpose.in_([Purpose.CLASS.value, Purpose.REPLAY.value]),
        )
        .group_by(believability_ratings.c.ai_mode, believability_ratings.c.rating)
    )
    found: dict[str, dict[int, int]] = {}
    for mode, rating, count in result:
        found.setdefault(mode, {})[rating] = count
    return found


async def class_orders(
    session: AsyncSession, game_ids: Collection[uuid.UUID]
) -> dict[uuid.UUID, dict[str, dict[int, int]]]:
    """Every stored Order of the Games (Story 14.5, FR-86) as `{game_id: {role: {week: order}}}`,
    in one read whatever their number (NFR-3): Week, Role and amount only, never who decided it
    or who held the Seat (AD-14). The caller has chosen the Games."""
    if not game_ids:
        return {}
    result = await session.execute(
        select(seat_weeks.c.game_id, seats.c.role, seat_weeks.c.week, seat_weeks.c.order)
        .select_from(seat_weeks.join(seats, seats.c.id == seat_weeks.c.seat_id))
        .where(seat_weeks.c.game_id.in_(list(game_ids)))
    )
    found: dict[uuid.UUID, dict[str, dict[int, int]]] = {}
    for game_id, role, week, order in result:
        found.setdefault(game_id, {}).setdefault(str(role), {})[week] = order
    return found
