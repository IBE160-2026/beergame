"""The game figures of the Admin's operations view (Story 15.8, NFR-8, FR-79, AD-15): per Class
session, the LLM-path Orders and how many each fallback kind replaced, and the LLM Seats and how
many of them the Play guard switched. Counts only, read from the Decision log and the occupancy
through the one mark mapping (`marks.seat_mark`); no Student, answer or assessment.

The Games counted are those of the Class session that Students play: its Class games, played-out
ones included, Replays and make-up Games; a Lecturer's test Game is left out (Story 6.20).
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import distinct_on

from app.modules.games.marks import seat_mark
from app.modules.games.models import games, seat_occupancy, seat_weeks, seats
from app.modules.games.schemas import (
    DecidedBy,
    Fallback,
    OccupancyReason,
    OccupantKind,
    Purpose,
    SeatMark,
)
from app.platform.db import get_sessionmaker

__all__ = ["FallbackCount", "SessionAiFigures", "class_session_of", "session_ai_figures"]


@dataclass(frozen=True)
class FallbackCount:
    kind: SeatMark
    """The fallback's mark (`fallback_timeout`, …) from `seat_mark`."""
    orders: int


@dataclass(frozen=True)
class SessionAiFigures:
    llm_orders: int
    """Orders placed while an `llm` occupant held the Seat, Guided Weeks left out."""
    fallbacks: tuple[FallbackCount, ...]
    """Every fallback kind but `none`, in `Fallback` order, zero included."""
    llm_seats: int
    """Seats whose first occupant was an LLM player."""
    switched_seats: int
    """Of those, the Seats the Play guard switched to a Rule-based player (FR-79)."""


def _played(class_session_id: uuid.UUID):
    return (games.c.class_session_id == class_session_id) & (
        games.c.purpose != Purpose.LECTURER_TEST.value
    )


async def class_session_of(game_id: uuid.UUID | str) -> uuid.UUID | None:
    """The Class session of a Game (a Class game, a Replay, a make-up or test Game), or None for a
    Game without one or an unknown id."""
    try:
        game_uuid = game_id if isinstance(game_id, uuid.UUID) else uuid.UUID(str(game_id))
    except ValueError:
        return None
    async with get_sessionmaker()() as session:
        return (
            await session.execute(select(games.c.class_session_id).where(games.c.id == game_uuid))
        ).scalar_one_or_none()


async def session_ai_figures(class_session_id: uuid.UUID) -> SessionAiFigures:
    """The fallback and Play guard counts of a Class session's played Games (Story 15.8)."""
    played = _played(class_session_id)
    async with get_sessionmaker()() as session:
        by_fallback = dict(
            (
                await session.execute(
                    select(seat_weeks.c.fallback, func.count())
                    .select_from(seat_weeks.join(games, games.c.id == seat_weeks.c.game_id))
                    .where(
                        played,
                        seat_weeks.c.occupant_kind == OccupantKind.LLM.value,
                        seat_weeks.c.decided_by != DecidedBy.GUIDED.value,
                    )
                    .group_by(seat_weeks.c.fallback)
                )
            ).all()
        )
        # Each Seat's first occupancy row (UUIDv7 ids sort by time) and whether a `guard_switch`
        # row with a Rule-based occupant follows; the mark decides, as on every other view.
        first = (
            select(seat_occupancy.c.seat_id, seat_occupancy.c.occupant_kind)
            .select_from(
                seat_occupancy.join(seats, seats.c.id == seat_occupancy.c.seat_id).join(
                    games, games.c.id == seats.c.game_id
                )
            )
            .where(played)
            .ext(distinct_on(seat_occupancy.c.seat_id))
            .order_by(seat_occupancy.c.seat_id, seat_occupancy.c.id)
            .subquery()
        )
        llm_seats = set(
            (
                await session.execute(
                    select(first.c.seat_id).where(first.c.occupant_kind == OccupantKind.LLM.value)
                )
            ).scalars()
        )
        switches = (
            await session.execute(
                select(
                    seat_occupancy.c.seat_id,
                    seat_occupancy.c.occupant_kind,
                    seat_occupancy.c.reason,
                )
                .select_from(
                    seat_occupancy.join(seats, seats.c.id == seat_occupancy.c.seat_id).join(
                        games, games.c.id == seats.c.game_id
                    )
                )
                .where(played, seat_occupancy.c.reason == OccupancyReason.GUARD_SWITCH.value)
            )
        ).all()
    switched = {
        row.seat_id
        for row in switches
        if seat_mark(None, None, row.occupant_kind, row.reason) is SeatMark.GUARD_SWITCH
    }
    fallbacks = []
    for kind in Fallback:
        mark = seat_mark(None, kind, None, None)
        if mark is None:  # `none`: nothing replaced the Order
            continue
        fallbacks.append(FallbackCount(mark, by_fallback.get(kind.value, 0)))
    return SessionAiFigures(
        llm_orders=sum(by_fallback.values()),
        fallbacks=tuple(fallbacks),
        llm_seats=len(llm_seats),
        switched_seats=len(llm_seats & switched),
    )
