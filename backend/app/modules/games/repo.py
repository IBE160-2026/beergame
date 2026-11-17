"""SQL for the games tables. Writers here are called only from `games.commands`."""

import uuid
from typing import Any

from sqlalchemy import RowMapping, select, update
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.games.models import game_weeks, games, seat_occupancy, seat_turns, seats


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
    session: AsyncSession, game_id: uuid.UUID, week: int, state: dict[str, Any]
) -> None:
    await session.execute(game_weeks.insert().values(game_id=game_id, week=week, state=state))


async def insert_turns(session: AsyncSession, rows: list[dict[str, Any]]) -> None:
    await session.execute(seat_turns.insert(), rows)


async def week_states(session: AsyncSession, game_id: uuid.UUID) -> list[dict[str, Any]]:
    """The stored Week states of the Game, Week 1 first."""
    result = await session.execute(
        select(game_weeks.c.state)
        .where(game_weeks.c.game_id == game_id)
        .order_by(game_weeks.c.week)
    )
    return list(result.scalars())


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
