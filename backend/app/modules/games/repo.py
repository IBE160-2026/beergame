"""SQL for the games tables. Writers here are called only from `games.commands`."""

import uuid
from typing import Any

from sqlalchemy import RowMapping, func, select, update
from sqlalchemy.dialects.postgresql import distinct_on, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.games.models import (
    game_checks,
    game_weeks,
    games,
    seat_occupancy,
    seat_turns,
    seat_weeks,
    seats,
)


async def insert_game(session: AsyncSession, values: dict[str, Any]) -> None:
    await session.execute(games.insert().values(**values))


async def insert_seats(session: AsyncSession, game_id: uuid.UUID, roles: list[str]) -> None:
    await session.execute(
        seats.insert(),
        [
            {"id": uuid.uuid7(), "game_id": game_id, "role": role, "position": position}
            for position, role in enumerate(roles)
        ],
    )


async def lock_game(session: AsyncSession, game_id: uuid.UUID) -> RowMapping | None:
    """The Game row, locked until the transaction ends (`SELECT … FOR UPDATE`)."""
    result = await session.execute(select(games).where(games.c.id == game_id).with_for_update())
    return result.mappings().one_or_none()


async def bump_version(session: AsyncSession, game_id: uuid.UUID) -> int:
    result = await session.execute(
        update(games)
        .where(games.c.id == game_id)
        .values(version=games.c.version + 1)
        .returning(games.c.version)
    )
    return result.scalar_one()


async def seat_by_role(session: AsyncSession, game_id: uuid.UUID, role: str) -> RowMapping | None:
    result = await session.execute(
        select(seats).where(seats.c.game_id == game_id, seats.c.role == role)
    )
    return result.mappings().one_or_none()


async def seat(session: AsyncSession, game_id: uuid.UUID, seat_id: uuid.UUID) -> RowMapping | None:
    result = await session.execute(
        select(seats).where(seats.c.game_id == game_id, seats.c.id == seat_id)
    )
    return result.mappings().one_or_none()


async def has_occupant(session: AsyncSession, seat_id: uuid.UUID) -> bool:
    result = await session.execute(
        select(seat_occupancy.c.id).where(seat_occupancy.c.seat_id == seat_id).limit(1)
    )
    return result.first() is not None


async def append_occupancy(session: AsyncSession, values: dict[str, Any]) -> None:
    await session.execute(seat_occupancy.insert().values(**values))


async def get_game(session: AsyncSession, game_id: uuid.UUID) -> RowMapping | None:
    result = await session.execute(select(games).where(games.c.id == game_id))
    return result.mappings().one_or_none()


async def seats_with_occupant(session: AsyncSession, game_id: uuid.UUID) -> list[RowMapping]:
    """Each Seat of the Game in chain order, with its latest occupancy row (None when free)."""
    latest = (
        select(
            seat_occupancy.c.seat_id,
            seat_occupancy.c.occupant_kind,
            seat_occupancy.c.policy_id,
        )
        .ext(distinct_on(seat_occupancy.c.seat_id))
        .order_by(seat_occupancy.c.seat_id, seat_occupancy.c.id.desc())
        .subquery()
    )
    result = await session.execute(
        select(seats.c.id, seats.c.role, latest.c.occupant_kind, latest.c.policy_id)
        .select_from(seats.outerjoin(latest, latest.c.seat_id == seats.c.id))
        .where(seats.c.game_id == game_id)
        .order_by(seats.c.position)
    )
    return list(result.mappings())


async def set_lifecycle(session: AsyncSession, game_id: uuid.UUID, lifecycle: str) -> None:
    await session.execute(update(games).where(games.c.id == game_id).values(lifecycle=lifecycle))


async def insert_week(
    session: AsyncSession,
    game_id: uuid.UUID,
    week: int,
    state: dict[str, Any],
    *,
    finished: bool = False,
) -> None:
    await session.execute(
        game_weeks.insert().values(game_id=game_id, week=week, finished=finished, state=state)
    )


async def insert_turns(session: AsyncSession, rows: list[dict[str, Any]]) -> None:
    # One multi-row INSERT: an executemany goes through psycopg's pipeline mode, which costs
    # tens of milliseconds per call for these few rows.
    await session.execute(seat_turns.insert().values(rows))


async def week_states(session: AsyncSession, game_id: uuid.UUID) -> list[dict[str, Any]]:
    """The stored Week states of the Game, Week 1 first and the finished state (if any) last."""
    result = await session.execute(
        select(game_weeks.c.state)
        .where(game_weeks.c.game_id == game_id)
        .order_by(game_weeks.c.week, game_weeks.c.finished)
    )
    return list(result.scalars())


async def open_week(session: AsyncSession, game_id: uuid.UUID) -> int | None:
    """The newest opened Week of the Game (a finished state is not opened), or None."""
    result = await session.execute(
        select(func.max(game_weeks.c.week)).where(
            game_weeks.c.game_id == game_id, game_weeks.c.finished.is_(False)
        )
    )
    return result.scalar_one()


async def turn(
    session: AsyncSession, game_id: uuid.UUID, seat_id: uuid.UUID, week: int
) -> RowMapping | None:
    result = await session.execute(
        select(seat_turns).where(
            seat_turns.c.game_id == game_id,
            seat_turns.c.seat_id == seat_id,
            seat_turns.c.week == week,
        )
    )
    return result.mappings().one_or_none()


async def week_turns(session: AsyncSession, game_id: uuid.UUID, week: int) -> list[RowMapping]:
    """The turns of every Seat in `week`."""
    result = await session.execute(
        select(seat_turns).where(seat_turns.c.game_id == game_id, seat_turns.c.week == week)
    )
    return list(result.mappings())


async def set_ordered_at(session: AsyncSession, turn_id: uuid.UUID) -> Any:
    """Mark the turn as ordered at the transaction's `now()`; returns that time."""
    result = await session.execute(
        update(seat_turns)
        .where(seat_turns.c.id == turn_id)
        .values(ordered_at=func.now())
        .returning(seat_turns.c.ordered_at)
    )
    return result.scalar_one()


async def occupancy_in_force(
    session: AsyncSession, seat_id: uuid.UUID, week: int
) -> RowMapping | None:
    """The Seat's occupancy row that applies in `week`: the newest with `from_week <= week`."""
    result = await session.execute(
        select(seat_occupancy)
        .where(seat_occupancy.c.seat_id == seat_id, seat_occupancy.c.from_week <= week)
        .order_by(seat_occupancy.c.from_week.desc(), seat_occupancy.c.id.desc())
        .limit(1)
    )
    return result.mappings().one_or_none()


async def has_seat_week(
    session: AsyncSession, game_id: uuid.UUID, week: int, seat_id: uuid.UUID
) -> bool:
    result = await session.execute(
        select(seat_weeks.c.id)
        .where(
            seat_weeks.c.game_id == game_id,
            seat_weeks.c.week == week,
            seat_weeks.c.seat_id == seat_id,
        )
        .limit(1)
    )
    return result.first() is not None


async def insert_seat_week(session: AsyncSession, values: dict[str, Any]) -> None:
    await session.execute(seat_weeks.insert().values(**values))


async def placed_orders(session: AsyncSession, game_id: uuid.UUID) -> list[RowMapping]:
    """Every stored Order of the Game as `week`, `role`, `order`, by Week."""
    result = await session.execute(
        select(seat_weeks.c.week, seats.c.role, seat_weeks.c.order)
        .select_from(seat_weeks.join(seats, seats.c.id == seat_weeks.c.seat_id))
        .where(seat_weeks.c.game_id == game_id)
        .order_by(seat_weeks.c.week, seats.c.position)
    )
    return list(result.mappings())


async def decision_log(session: AsyncSession, game_id: uuid.UUID) -> list[RowMapping]:
    """The Game's Decision log rows with each Seat's Role, by Week and chain order."""
    result = await session.execute(
        select(seat_weeks, seats.c.role)
        .select_from(seat_weeks.join(seats, seats.c.id == seat_weeks.c.seat_id))
        .where(seat_weeks.c.game_id == game_id)
        .order_by(seat_weeks.c.week, seats.c.position)
    )
    return list(result.mappings())


async def orders_by_decided_by(session: AsyncSession, game_id: uuid.UUID) -> dict[str, int]:
    """The number of Decision log rows of the Game per `decided_by`."""
    result = await session.execute(
        select(seat_weeks.c.decided_by, func.count())
        .where(seat_weeks.c.game_id == game_id)
        .group_by(seat_weeks.c.decided_by)
    )
    return {decided_by: count for decided_by, count in result}


async def finished_state(session: AsyncSession, game_id: uuid.UUID) -> dict[str, Any] | None:
    """The Game's finished Week state, or None before the Game has finished."""
    result = await session.execute(
        select(game_weeks.c.state).where(game_weeks.c.game_id == game_id, game_weeks.c.finished)
    )
    return result.scalar_one_or_none()


async def week_rows(session: AsyncSession, game_id: uuid.UUID) -> list[RowMapping]:
    """Every stored Week state row (`week`, `finished`, `state`), Week 1 first, finished last."""
    result = await session.execute(
        select(game_weeks.c.week, game_weeks.c.finished, game_weeks.c.state)
        .where(game_weeks.c.game_id == game_id)
        .order_by(game_weeks.c.week, game_weeks.c.finished)
    )
    return list(result.mappings())


async def game_check(session: AsyncSession, game_id: uuid.UUID) -> RowMapping | None:
    result = await session.execute(select(game_checks).where(game_checks.c.game_id == game_id))
    return result.mappings().one_or_none()


async def insert_game_check(session: AsyncSession, values: dict[str, Any]) -> RowMapping | None:
    """Store the Game's check; None when the Game already has one (it is never replaced)."""
    result = await session.execute(
        insert(game_checks)
        .values(**values)
        .on_conflict_do_nothing(index_elements=[game_checks.c.game_id])
        .returning(*game_checks.c)
    )
    return result.mappings().one_or_none()


async def finished_game_ids(session: AsyncSession) -> list[uuid.UUID]:
    """The id of every finished Game, oldest first (ids are UUIDv7)."""
    result = await session.execute(
        select(games.c.id).where(games.c.lifecycle == "finished").order_by(games.c.id)
    )
    return list(result.scalars())


async def stored_rules_versions(session: AsyncSession) -> list[int]:
    """Every distinct `rules_version` stored on a Game."""
    result = await session.execute(
        select(games.c.rules_version).distinct().order_by(games.c.rules_version)
    )
    return list(result.scalars())
