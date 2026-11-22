"""SQL for the games tables. Writers here are called only from `games.commands`."""

import uuid
from collections.abc import Collection, Sequence
from typing import Any

from sqlalchemy import Numeric, RowMapping, delete, func, select, text, update
from sqlalchemy.dialects.postgresql import distinct_on, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.games.models import (
    game_checks,
    game_summaries,
    game_weeks,
    games,
    seat_occupancy,
    seat_reclaims,
    seat_turns,
    seat_weeks,
    seats,
    simulation_batches,
    time_acceptances,
    time_proposals,
)
from app.modules.games.policy import purposes_with
from app.platform import authz


def _listed() -> Any:
    """The Games the Class session's lists count (Story 6.20): those of a purpose the Lecturer
    overview lists, so a Lecturer's test Game is in none of them (AD-13)."""
    return games.c.purpose.in_(purposes_with("lecturer_overview"))


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
    """Whether the Seat has an occupant now: a latest occupancy row with an occupant kind. A
    Seat with no row, or whose latest row freed it (Story 5.10), is free."""
    result = await session.execute(
        select(seat_occupancy.c.occupant_kind)
        .where(seat_occupancy.c.seat_id == seat_id)
        .order_by(seat_occupancy.c.id.desc())
        .limit(1)
    )
    row = result.first()
    return row is not None and row[0] is not None


async def append_occupancy(session: AsyncSession, values: dict[str, Any]) -> None:
    await session.execute(seat_occupancy.insert().values(**values))


async def get_game(session: AsyncSession, game_id: uuid.UUID) -> RowMapping | None:
    result = await session.execute(select(games).where(games.c.id == game_id))
    return result.mappings().one_or_none()


async def seats_with_occupant(session: AsyncSession, game_id: uuid.UUID) -> list[RowMapping]:
    """Each Seat of the Game in chain order, with its latest occupancy row (None when free): who
    holds it, why, who triggered it (`actor_user_id`, Story 8.5) and when."""
    latest = _latest_occupancy()
    result = await session.execute(
        select(
            seats.c.id,
            seats.c.role,
            latest.c.occupant_kind,
            latest.c.policy_id,
            latest.c.user_id,
            latest.c.reason,
            latest.c.actor_user_id,
            latest.c.created_at,
        )
        .select_from(seats.outerjoin(latest, latest.c.seat_id == seats.c.id))
        .where(seats.c.game_id == game_id)
        .order_by(seats.c.position)
    )
    return list(result.mappings())


def _latest_occupancy(*where: Any) -> Any:
    """Each Seat's latest occupancy row (by UUIDv7 id): its current occupant; `where` narrows
    the occupancy rows read."""
    return (
        select(
            seat_occupancy.c.seat_id,
            seat_occupancy.c.occupant_kind,
            seat_occupancy.c.policy_id,
            seat_occupancy.c.user_id,
            seat_occupancy.c.reason,
            seat_occupancy.c.actor_user_id,
            seat_occupancy.c.created_at,
        )
        .where(*where)
        .ext(distinct_on(seat_occupancy.c.seat_id))
        .order_by(seat_occupancy.c.seat_id, seat_occupancy.c.id.desc())
        .subquery()
    )


async def student_seated(
    session: AsyncSession, class_session_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    """Whether the Student holds a Seat in a Game of the Class session now (Story 5.9)."""
    return await student_seat_count(session, class_session_id, user_id) > 0


async def student_seats(
    session: AsyncSession, class_session_id: uuid.UUID, user_id: uuid.UUID
) -> list[RowMapping]:
    """Every Seat of the Class session's Games that the Student holds or has held (Story 6.1),
    joined through `authz.own_seat`: game id, game number, Role, the id of the last occupancy row
    naming the Student, whether they hold the Seat now (the Seat's latest row names them), and
    whether another Student held it after them (`later_student`)."""
    later = seat_occupancy.alias("later")
    named = (
        select(
            seat_occupancy.c.seat_id,
            seat_occupancy.c.id.label("row_id"),
        )
        .where(seat_occupancy.c.user_id == user_id)
        .subquery()
    )
    latest = _latest_occupancy(seat_occupancy.c.seat_id.in_(select(named.c.seat_id)))
    result = await session.execute(
        select(
            games.c.id.label("game_id"),
            games.c.game_number,
            games.c.purpose,
            seats.c.role,
            named.c.row_id,
            (latest.c.user_id == user_id).label("holds"),
            select(later.c.id)
            .where(
                later.c.seat_id == named.c.seat_id,
                later.c.id > named.c.row_id,
                later.c.occupant_kind == "student",
                later.c.user_id != user_id,
            )
            .exists()
            .label("later_student"),
        )
        .select_from(
            named.join(seats, seats.c.id == named.c.seat_id)
            .join(games, games.c.id == seats.c.game_id)
            .outerjoin(latest, latest.c.seat_id == seats.c.id)
        )
        .where(
            games.c.class_session_id == class_session_id,
            _listed(),
            games.c.id.in_(authz.own_seat(user_id)),
        )
    )
    return list(result.mappings())


async def own_game(
    session: AsyncSession, user_id: uuid.UUID, game_id: uuid.UUID
) -> RowMapping | None:
    """The Game, when the User holds or has held a Seat in it (`authz.own_seat`); None for any
    other Game, so another's reads as one that does not exist (Story 6.1, FR-5)."""
    result = await session.execute(
        select(games).where(games.c.id == game_id, games.c.id.in_(authz.own_seat(user_id, game_id)))
    )
    return result.mappings().one_or_none()


async def staff_test_games(
    session: AsyncSession, class_session_id: uuid.UUID, user_id: uuid.UUID
) -> list[RowMapping]:
    """The Games of the Class session that a Lecturer plays in a Student Seat (Story 6.20) and in
    which `user_id` holds or has held a Seat (`authz.own_seat`), newest first: id and lifecycle."""
    result = await session.execute(
        select(games.c.id, games.c.lifecycle)
        .where(
            games.c.class_session_id == class_session_id,
            games.c.purpose.in_(purposes_with("played_by_staff")),
            games.c.id.in_(authz.own_seat(user_id)),
        )
        .order_by(games.c.id.desc())
    )
    return list(result.mappings())


async def held_role(session: AsyncSession, game_id: uuid.UUID, user_id: uuid.UUID) -> str | None:
    """The Role of the Game's Seat the User holds now (its latest occupancy row names them)."""
    game_seats = select(seats.c.id).where(seats.c.game_id == game_id)
    latest = _latest_occupancy(seat_occupancy.c.seat_id.in_(game_seats))
    result = await session.execute(
        select(seats.c.role)
        .join(latest, latest.c.seat_id == seats.c.id)
        .where(seats.c.game_id == game_id, latest.c.user_id == user_id)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def last_seat_of(session: AsyncSession, game_id: uuid.UUID, user_id: uuid.UUID) -> str | None:
    """The Role of the Game's Seat the User holds now, else of the one they held last; None when
    they never held one (Story 6.1)."""
    game_seats = select(seats.c.id).where(seats.c.game_id == game_id)
    latest = _latest_occupancy(seat_occupancy.c.seat_id.in_(game_seats))
    held_now = await session.execute(
        select(seats.c.role)
        .join(latest, latest.c.seat_id == seats.c.id)
        .where(seats.c.game_id == game_id, latest.c.user_id == user_id)
        .limit(1)
    )
    role = held_now.scalar_one_or_none()
    if role is not None:
        return role
    last = await session.execute(
        select(seats.c.role)
        .join(seat_occupancy, seat_occupancy.c.seat_id == seats.c.id)
        .where(seats.c.game_id == game_id, seat_occupancy.c.user_id == user_id)
        .order_by(seat_occupancy.c.id.desc())
        .limit(1)
    )
    return last.scalar_one_or_none()


async def student_seat_count(
    session: AsyncSession, class_session_id: uuid.UUID, user_id: uuid.UUID
) -> int:
    """How many Seats the Student holds in the Games of the Class session now (Stories 5.9,
    5.10). Only the occupancy rows of that session's Seats are read."""
    session_seats = (
        select(seats.c.id)
        .join(games, games.c.id == seats.c.game_id)
        .where(games.c.class_session_id == class_session_id, _listed())
    )
    latest = _latest_occupancy(seat_occupancy.c.seat_id.in_(session_seats))
    result = await session.execute(
        select(func.count())
        .select_from(
            seats.join(latest, latest.c.seat_id == seats.c.id).join(
                games, games.c.id == seats.c.game_id
            )
        )
        .where(
            games.c.class_session_id == class_session_id,
            _listed(),
            latest.c.occupant_kind == "student",
            latest.c.user_id == user_id,
        )
    )
    return int(result.scalar_one())


async def class_game_ids(
    session: AsyncSession, class_session_id: uuid.UUID
) -> dict[int, uuid.UUID]:
    """The Class session's Games by game number (Story 5.10)."""
    result = await session.execute(
        select(games.c.game_number, games.c.id).where(
            games.c.class_session_id == class_session_id, _listed()
        )
    )
    return {number: game_id for number, game_id in result.all()}


async def set_snapshot(session: AsyncSession, game_id: uuid.UUID, values: dict[str, Any]) -> None:
    """Store the five snapshot columns of a Game that had none (Story 5.12)."""
    await session.execute(update(games).where(games.c.id == game_id).values(**values))


async def class_sessions_awaiting_snapshot(session: AsyncSession) -> list[uuid.UUID]:
    """The Class sessions with a `not_started` Game that has no snapshot yet (Story 5.12)."""
    result = await session.execute(
        select(games.c.class_session_id)
        .where(
            games.c.class_session_id.is_not(None),
            _listed(),
            games.c.settings.is_(None),
            games.c.lifecycle == "not_started",
        )
        .distinct()
        .order_by(games.c.class_session_id)
    )
    return list(result.scalars())


async def class_sessions_with_unstarted_games(session: AsyncSession) -> list[uuid.UUID]:
    """The Class sessions with a `not_started` Game that has its snapshot (Story 5.13)."""
    result = await session.execute(
        select(games.c.class_session_id)
        .where(
            games.c.class_session_id.is_not(None),
            _listed(),
            games.c.settings.is_not(None),
            games.c.lifecycle == "not_started",
        )
        .distinct()
        .order_by(games.c.class_session_id)
    )
    return list(result.scalars())


async def class_games(
    session: AsyncSession, class_session_ids: Sequence[uuid.UUID]
) -> list[RowMapping]:
    """The Games of these Class sessions by session and game number: id, session, number,
    lifecycle and whether the snapshot is stored (Story 5.12). One read for many sessions, so the
    sweep's finders do not ask once per session."""
    result = await session.execute(
        select(
            games.c.id,
            games.c.class_session_id,
            games.c.game_number,
            games.c.lifecycle,
            games.c.settings.is_not(None).label("has_snapshot"),
        )
        .where(games.c.class_session_id.in_(list(class_session_ids)), _listed())
        .order_by(games.c.class_session_id, games.c.game_number)
    )
    return list(result.mappings())


async def class_session_seats(
    session: AsyncSession, class_session_ids: Sequence[uuid.UUID]
) -> list[RowMapping]:
    """Every Seat of these Class sessions' Games in one read, by Game and chain order, with its
    latest occupancy row (None when free), as `seats_with_occupant` gives one Game's (5.12)."""
    in_sessions = games.c.class_session_id.in_(list(class_session_ids)) & _listed()
    session_seats = select(seats.c.id).join(games, games.c.id == seats.c.game_id).where(in_sessions)
    latest = _latest_occupancy(seat_occupancy.c.seat_id.in_(session_seats))
    result = await session.execute(
        select(
            seats.c.game_id,
            seats.c.role,
            latest.c.occupant_kind,
            latest.c.user_id,
        )
        .select_from(
            seats.join(games, games.c.id == seats.c.game_id).outerjoin(
                latest, latest.c.seat_id == seats.c.id
            )
        )
        .where(in_sessions)
        .order_by(seats.c.game_id, seats.c.position)
    )
    return list(result.mappings())


async def set_lifecycle(session: AsyncSession, game_id: uuid.UUID, lifecycle: str) -> None:
    await session.execute(update(games).where(games.c.id == game_id).values(lifecycle=lifecycle))


async def set_pause(
    session: AsyncSession, game_id: uuid.UUID, user_id: uuid.UUID, resume_at: Any = None
) -> Any:
    """Story 8.6: the Pause in force from the transaction's `now()`, by `user_id`, with the
    Lecturer's agreed time `resume_at` (Story 8.7; a Student's has none); the last Pause's end is
    forgotten. Returns `paused_at`."""
    result = await session.execute(
        update(games)
        .where(games.c.id == game_id)
        .values(
            paused_at=func.now(),
            paused_by=user_id,
            resume_at=resume_at,
            agreed_time_reached_at=None,
            pause_ended_at=None,
            pause_ended_by=None,
        )
        .returning(games.c.paused_at)
    )
    return result.scalar_one()


async def end_pause(session: AsyncSession, game_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Story 8.6: a Student's Order ends the Pause in force at the transaction's `now()`; from
    Story 8.7 also the Lecturer's «Avslutt pausen» (`user_id` the Lecturer)."""
    await session.execute(
        update(games)
        .where(games.c.id == game_id)
        .values(
            paused_at=None,
            paused_by=None,
            resume_at=None,
            agreed_time_reached_at=None,
            pause_ended_at=func.now(),
            pause_ended_by=user_id,
        )
    )


async def set_agreed_time(session: AsyncSession, game_id: uuid.UUID, resume_at: Any) -> None:
    """Story 8.7: the Lecturer's agreed time on the Pause in force (None clears it); the sweep
    has not seen it pass yet."""
    await session.execute(
        update(games)
        .where(games.c.id == game_id)
        .values(resume_at=resume_at, agreed_time_reached_at=None)
    )


async def mark_agreed_time_reached(session: AsyncSession, game_id: uuid.UUID, at: Any) -> None:
    """Story 8.7: the sweep saw the agreed time pass at `at`."""
    await session.execute(
        update(games).where(games.c.id == game_id).values(agreed_time_reached_at=at)
    )


async def due_agreed_times(session: AsyncSession, now: Any) -> list[uuid.UUID]:
    """Story 8.7 (AD-9): the running, paused Games whose agreed time lies at or before `now` and
    that the sweep has not announced yet, the earliest first."""
    result = await session.execute(
        select(games.c.id)
        .where(
            games.c.lifecycle == "running",
            games.c.paused_at.is_not(None),
            games.c.resume_at <= now,
            games.c.agreed_time_reached_at.is_(None),
        )
        .order_by(games.c.resume_at, games.c.id)
    )
    return list(result.scalars())


async def set_insert_allowed(session: AsyncSession, turn_id: uuid.UUID, at: Any) -> None:
    """Story 8.7: the turn's insert time, recomputed by a Lecturer's Pause command through
    `rules.turn_times`; its Takeover due time is never moved. The sweep has not announced the new
    time yet (Story 8.8)."""
    await session.execute(
        update(seat_turns)
        .where(seat_turns.c.id == turn_id)
        .values(insert_allowed_at=at, insert_announced_at=None)
    )


async def mark_insert_announced(session: AsyncSession, turn_id: uuid.UUID, at: Any) -> None:
    """Story 8.8: the sweep saw the turn's insert time pass at `at`."""
    await session.execute(
        update(seat_turns).where(seat_turns.c.id == turn_id).values(insert_announced_at=at)
    )


async def due_insert_times(session: AsyncSession, now: Any) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """Story 8.8 (AD-9): (Game id, Seat id) of each turn in the open Week of a running Game whose
    insert time lies at or before `now` and that the sweep has not announced yet, the earliest
    first. Whether the Seat still waits is the command's to judge under the lock."""
    opened = (
        select(func.max(game_weeks.c.week))
        .where(game_weeks.c.game_id == seat_turns.c.game_id, game_weeks.c.finished.is_(False))
        .scalar_subquery()
    )
    result = await session.execute(
        select(seat_turns.c.game_id, seat_turns.c.seat_id)
        .join(games, games.c.id == seat_turns.c.game_id)
        .where(
            games.c.lifecycle == "running",
            seat_turns.c.insert_allowed_at <= now,
            seat_turns.c.insert_announced_at.is_(None),
            seat_turns.c.week == opened,
        )
        .order_by(seat_turns.c.insert_allowed_at, seat_turns.c.id)
    )
    return [(row.game_id, row.seat_id) for row in result]


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


async def now(session: AsyncSession) -> Any:
    """The transaction's `now()`: the time every row the transaction stamps carries."""
    return (await session.execute(select(func.now()))).scalar_one()


async def clock_now(session: AsyncSession) -> Any:
    """The database clock at this statement (`clock_timestamp()`), not at the transaction's
    start: the moment a read ended, on the clock deadlines are stamped with."""
    return (await session.execute(select(func.clock_timestamp()))).scalar_one()


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


async def week_turns_with_occupant(
    session: AsyncSession, game_id: uuid.UUID, week: int
) -> list[RowMapping]:
    """The turns of every Seat in `week`, each with `occupant_kind` and `user_id` of the
    occupancy row in force in that Week (`occupancy_in_force`), for `rules.week_complete`."""
    in_force = (
        select(seat_occupancy.c.seat_id, seat_occupancy.c.occupant_kind, seat_occupancy.c.user_id)
        .where(
            seat_occupancy.c.from_week <= week,
            seat_occupancy.c.seat_id.in_(select(seats.c.id).where(seats.c.game_id == game_id)),
        )
        .ext(distinct_on(seat_occupancy.c.seat_id))
        .order_by(
            seat_occupancy.c.seat_id, seat_occupancy.c.from_week.desc(), seat_occupancy.c.id.desc()
        )
        .subquery()
    )
    result = await session.execute(
        select(seat_turns, in_force.c.occupant_kind, in_force.c.user_id)
        .select_from(seat_turns.outerjoin(in_force, in_force.c.seat_id == seat_turns.c.seat_id))
        .where(seat_turns.c.game_id == game_id, seat_turns.c.week == week)
    )
    return list(result.mappings())


async def set_viewed_at(session: AsyncSession, turn_id: uuid.UUID) -> Any:
    """Mark the turn as viewed at the transaction's `now()`; returns that time."""
    result = await session.execute(
        update(seat_turns)
        .where(seat_turns.c.id == turn_id)
        .values(viewed_at=func.now())
        .returning(seat_turns.c.viewed_at)
    )
    return result.scalar_one()


async def set_wait_times(
    session: AsyncSession,
    turn_id: uuid.UUID,
    *,
    wait_started_at: Any,
    takeover_due_at: Any,
    insert_allowed_at: Any,
) -> None:
    """Store when the game began to wait for the turn's Seat (Story 6.14) and its FR-36 due times
    (Story 8.1), all from one `rules.turn_times` result, only while the wait start is unset."""
    await session.execute(
        update(seat_turns)
        .where(seat_turns.c.id == turn_id, seat_turns.c.wait_started_at.is_(None))
        .values(
            wait_started_at=wait_started_at,
            takeover_due_at=takeover_due_at,
            insert_allowed_at=insert_allowed_at,
        )
    )


async def set_ordered_at(session: AsyncSession, turn_id: uuid.UUID) -> Any:
    """Mark the turn as ordered at the transaction's `now()`; returns that time."""
    result = await session.execute(
        update(seat_turns)
        .where(seat_turns.c.id == turn_id)
        .values(ordered_at=func.now())
        .returning(seat_turns.c.ordered_at)
    )
    return result.scalar_one()


async def set_ai_deadline(session: AsyncSession, turn_id: uuid.UUID, at: Any) -> None:
    """Give the turn its AI deadline (an LLM player that took the Seat mid-Week, Story 8.2),
    only while it has none: the `seat_turns` trigger keeps one once set."""
    await session.execute(
        update(seat_turns)
        .where(seat_turns.c.id == turn_id, seat_turns.c.ai_deadline_at.is_(None))
        .values(ai_deadline_at=at)
    )


async def guard_switched(session: AsyncSession, seat_id: uuid.UUID) -> bool:
    """Whether the Play guard has ever switched the Seat (a `guard_switch` row in its history):
    the switch outlasts a later Takeover or Reclaim (Story 8.2, FR-79)."""
    result = await session.execute(
        select(seat_occupancy.c.id)
        .where(seat_occupancy.c.seat_id == seat_id, seat_occupancy.c.reason == "guard_switch")
        .limit(1)
    )
    return result.first() is not None


TAKEOVER_REASONS = ("takeover_inactivity", "takeover_staff", "takeover_peer")
"""The occupancy reasons of an AI player that took a Student's Seat over (Story 8.2)."""


async def seat_histories(session: AsyncSession, game_id: uuid.UUID) -> dict[uuid.UUID, dict]:
    """Per Seat of the Game: `last_student`, the user id of its latest `student` row (None when
    no Student ever held it); `taken_over`, whether a Takeover row came after that row, so a later
    Play guard or cost-limit switch of the AI player keeps the Seat taken over; and
    `guard_switched`, whether it has a `guard_switch` row (Story 8.2): what the Setestatus says of
    an AI player that took a Student's Seat. Rows by id (UUIDv7): the order they were appended."""
    result = await session.execute(
        select(
            seat_occupancy.c.seat_id,
            seat_occupancy.c.occupant_kind,
            seat_occupancy.c.user_id,
            seat_occupancy.c.reason,
        )
        .join(seats, seats.c.id == seat_occupancy.c.seat_id)
        .where(seats.c.game_id == game_id)
        .order_by(seat_occupancy.c.id)
    )
    found: dict[uuid.UUID, dict] = {}
    for row in result.mappings():
        entry = found.setdefault(
            row["seat_id"], {"last_student": None, "taken_over": False, "guard_switched": False}
        )
        if row["occupant_kind"] == "student" and row["user_id"] is not None:
            entry["last_student"] = row["user_id"]
            entry["taken_over"] = False
        if row["reason"] in TAKEOVER_REASONS:
            entry["taken_over"] = True
        if row["reason"] == "guard_switch":
            entry["guard_switched"] = True
    return found


async def queue_reclaim(
    session: AsyncSession, game_id: uuid.UUID, seat_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    """Queue the Student's Reclaim of the Seat (Story 8.4); False, writing nothing, when one is
    queued already (one per Seat)."""
    result = await session.execute(
        insert(seat_reclaims)
        .values(seat_id=seat_id, game_id=game_id, user_id=user_id)
        .on_conflict_do_nothing(index_elements=[seat_reclaims.c.seat_id])
        .returning(seat_reclaims.c.seat_id)
    )
    return result.first() is not None


async def queued_reclaims(session: AsyncSession, game_id: uuid.UUID) -> dict[uuid.UUID, uuid.UUID]:
    """The Game's queued Reclaims: Seat id to the Student who asked (Story 8.4)."""
    result = await session.execute(
        select(seat_reclaims.c.seat_id, seat_reclaims.c.user_id).where(
            seat_reclaims.c.game_id == game_id
        )
    )
    return {row.seat_id: row.user_id for row in result}


async def delete_reclaim(session: AsyncSession, seat_id: uuid.UUID) -> None:
    await session.execute(delete(seat_reclaims).where(seat_reclaims.c.seat_id == seat_id))


async def delete_reclaims(session: AsyncSession, game_id: uuid.UUID) -> None:
    """Drop every queued Reclaim of the Game (it finished: no Week opens again)."""
    await session.execute(delete(seat_reclaims).where(seat_reclaims.c.game_id == game_id))


async def takeover_row(session: AsyncSession, occupancy_id: uuid.UUID) -> RowMapping | None:
    """A Takeover's occupancy row with its Game, Role and `student`: the Student who held the
    Seat before it (the latest earlier `student` row); None for an id that is no Takeover."""
    earlier = seat_occupancy.alias("earlier")
    result = await session.execute(
        select(
            seat_occupancy.c.id,
            seat_occupancy.c.from_week,
            seats.c.game_id,
            seats.c.role,
            select(earlier.c.user_id)
            .where(
                earlier.c.seat_id == seat_occupancy.c.seat_id,
                earlier.c.id < seat_occupancy.c.id,
                earlier.c.occupant_kind == "student",
            )
            .order_by(earlier.c.id.desc())
            .limit(1)
            .scalar_subquery()
            .label("student"),
        )
        .join(seats, seats.c.id == seat_occupancy.c.seat_id)
        .where(
            seat_occupancy.c.id == occupancy_id,
            seat_occupancy.c.reason.in_(TAKEOVER_REASONS),
        )
    )
    return result.mappings().one_or_none()


async def due_takeover_turns(session: AsyncSession, now: Any) -> list[RowMapping]:
    """The turns the sweep's Takeover may act on (Story 8.2, AD-9): in the open Week of a running
    Game whose policy has inactivity Takeover and that is not paused (Story 8.6), with no Order
    yet or (a Guided Week) no view, and a stored `takeover_due_at` at or before `now`, oldest due
    first. `game_id`, `seat_id`, `week`;
    `games.commands.takeover` decides under the lock (`rules.can_take_over`)."""
    open_weeks = _open_weeks()
    result = await session.execute(
        select(seat_turns.c.game_id, seat_turns.c.seat_id, seat_turns.c.week)
        .select_from(
            seat_turns.join(
                open_weeks,
                (open_weeks.c.game_id == seat_turns.c.game_id)
                & (open_weeks.c.week == seat_turns.c.week),
            ).join(games, games.c.id == seat_turns.c.game_id)
        )
        .where(
            games.c.purpose.in_(purposes_with("inactivity_takeover")),
            # A paused Game takes no Seat over (Story 8.6); `can_take_over` says so too.
            games.c.paused_at.is_(None),
            seat_turns.c.takeover_due_at.is_not(None),
            seat_turns.c.takeover_due_at <= now,
            (seat_turns.c.ordered_at.is_(None)) | (seat_turns.c.viewed_at.is_(None)),
        )
        .order_by(seat_turns.c.takeover_due_at, seat_turns.c.game_id, seat_turns.c.seat_id)
    )
    return list(result.mappings())


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


async def seat_week_order(
    session: AsyncSession, game_id: uuid.UUID, week: int, seat_id: uuid.UUID
) -> int | None:
    """The Seat's Order in `week`, or None before it has ordered."""
    result = await session.execute(
        select(seat_weeks.c.order).where(
            seat_weeks.c.game_id == game_id,
            seat_weeks.c.week == week,
            seat_weeks.c.seat_id == seat_id,
        )
    )
    return result.scalar_one_or_none()


async def insert_seat_week(session: AsyncSession, values: dict[str, Any]) -> None:
    await session.execute(seat_weeks.insert().values(**values))


async def week_states_of(
    session: AsyncSession, game_ids: Collection[uuid.UUID]
) -> list[RowMapping]:
    """The opened (not finished) Week states of the Games as `game_id`, `state`: one read
    whatever their number (NFR-3)."""
    if not game_ids:
        return []
    result = await session.execute(
        select(game_weeks.c.game_id, game_weeks.c.state)
        .where(game_weeks.c.game_id.in_(list(game_ids)), game_weeks.c.finished.is_(False))
        .order_by(game_weeks.c.game_id, game_weeks.c.week)
    )
    return list(result.mappings())


async def placed_orders_of(
    session: AsyncSession, game_ids: Collection[uuid.UUID]
) -> list[RowMapping]:
    """Every stored Order of the Games as `game_id`, `week`, `role`, `order`: one read."""
    if not game_ids:
        return []
    result = await session.execute(
        select(seat_weeks.c.game_id, seat_weeks.c.week, seats.c.role, seat_weeks.c.order)
        .select_from(seat_weeks.join(seats, seats.c.id == seat_weeks.c.seat_id))
        .where(seat_weeks.c.game_id.in_(list(game_ids)))
    )
    return list(result.mappings())


async def placed_orders(session: AsyncSession, game_id: uuid.UUID) -> list[RowMapping]:
    """Every stored Order of the Game as `week`, `role`, `order`, by Week."""
    result = await session.execute(
        select(seat_weeks.c.week, seats.c.role, seat_weeks.c.order)
        .select_from(seat_weeks.join(seats, seats.c.id == seat_weeks.c.seat_id))
        .where(seat_weeks.c.game_id == game_id)
        .order_by(seat_weeks.c.week, seats.c.position)
    )
    return list(result.mappings())


async def turn_clock(session: AsyncSession, game_id: uuid.UUID) -> list[RowMapping]:
    """When each opened Week opened for each Seat, when its Order was placed and when a Student
    viewed it (Story 8.1, FR-35), with the Seat's Role, by Week and chain order."""
    result = await session.execute(
        select(
            seat_turns.c.week,
            seats.c.role,
            seat_turns.c.opened_at,
            seat_turns.c.ordered_at,
            seat_turns.c.viewed_at,
        )
        .select_from(seat_turns.join(seats, seats.c.id == seat_turns.c.seat_id))
        .where(seat_turns.c.game_id == game_id)
        .order_by(seat_turns.c.week, seats.c.position)
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


async def seat_guard_rows(
    session: AsyncSession, game_id: uuid.UUID, seat_id: uuid.UUID
) -> list[RowMapping]:
    """The Seat's Decision log rows with what the Play guard reads, by Week."""
    result = await session.execute(
        select(
            seat_weeks.c.week,
            seat_weeks.c.order,
            seat_weeks.c.decided_by,
            seat_weeks.c.rule_based_reference_order,
            seat_weeks.c.near_optimal_reference_order,
        )
        .where(seat_weeks.c.game_id == game_id, seat_weeks.c.seat_id == seat_id)
        .order_by(seat_weeks.c.week)
    )
    return list(result.mappings())


async def occupancy_history(session: AsyncSession, game_id: uuid.UUID) -> list[RowMapping]:
    """Every occupancy row of the Game's Seats, by chain order and then as appended."""
    result = await session.execute(
        select(seat_occupancy, seats.c.role)
        .select_from(seat_occupancy.join(seats, seats.c.id == seat_occupancy.c.seat_id))
        .where(seats.c.game_id == game_id)
        .order_by(seats.c.position, seat_occupancy.c.id)
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


async def unchecked_finished_game_ids(
    session: AsyncSession, limit: int, exclude: Collection[uuid.UUID] = ()
) -> list[uuid.UUID]:
    """At most `limit` finished Games that have no `game_checks` row yet, oldest first (Story
    6.18): what the sweep's finished-game check still has to verify, but those in `exclude`."""
    query = (
        select(games.c.id)
        .select_from(games.outerjoin(game_checks, game_checks.c.game_id == games.c.id))
        .where(games.c.lifecycle == "finished", game_checks.c.id.is_(None))
    )
    if exclude:
        query = query.where(games.c.id.not_in(list(exclude)))
    result = await session.execute(query.order_by(games.c.id).limit(limit))
    return list(result.scalars())


async def running_games_of_config(
    session: AsyncSession, purpose: str, model_config_id: uuid.UUID
) -> list[uuid.UUID]:
    """The id of every running Game of `purpose` whose `SessionRuntime` froze
    `model_config_id`, oldest first."""
    result = await session.execute(
        select(games.c.id)
        .where(
            games.c.lifecycle == "running",
            games.c.purpose == purpose,
            games.c.session_runtime["model_config_id"].astext == str(model_config_id),
        )
        .order_by(games.c.id)
    )
    return list(result.scalars())


async def running_games_of_session(
    session: AsyncSession, class_session_id: uuid.UUID
) -> list[uuid.UUID]:
    """The id of every running Game of the Class session, oldest first."""
    result = await session.execute(
        select(games.c.id)
        .where(games.c.lifecycle == "running", games.c.class_session_id == class_session_id)
        .order_by(games.c.id)
    )
    return list(result.scalars())


async def stored_rules_versions(session: AsyncSession) -> list[int]:
    """Every distinct `rules_version` stored on a Game that has its snapshot."""
    result = await session.execute(
        select(games.c.rules_version)
        .where(games.c.rules_version.is_not(None))
        .distinct()
        .order_by(games.c.rules_version)
    )
    return list(result.scalars())


def _open_weeks() -> Any:
    """Each running Game's open Week (`game_id`, `week`) as a subquery."""
    return (
        select(game_weeks.c.game_id, func.max(game_weeks.c.week).label("week"))
        .select_from(game_weeks.join(games, games.c.id == game_weeks.c.game_id))
        .where(games.c.lifecycle == "running", game_weeks.c.finished.is_(False))
        .group_by(game_weeks.c.game_id)
        .subquery()
    )


async def overdue_llm_turns(session: AsyncSession, now: Any | None) -> list[RowMapping]:
    """`game_id`, `seat_id`, `week` of every turn in a running Game's open Week that has no
    Order and whose `ai_deadline_at` is at or before `now` (default: the database's `now()`),
    oldest deadline first."""
    open_weeks = _open_weeks()
    result = await session.execute(
        select(seat_turns.c.game_id, seat_turns.c.seat_id, seat_turns.c.week)
        .select_from(
            seat_turns.join(
                open_weeks,
                (open_weeks.c.game_id == seat_turns.c.game_id)
                & (open_weeks.c.week == seat_turns.c.week),
            )
        )
        .where(
            seat_turns.c.ordered_at.is_(None),
            seat_turns.c.ai_deadline_at.is_not(None),
            seat_turns.c.ai_deadline_at <= (func.now() if now is None else now),
        )
        .order_by(seat_turns.c.ai_deadline_at)
    )
    return list(result.mappings())


async def complete_running_games(session: AsyncSession) -> list[uuid.UUID]:
    """The id of every running Game whose open Week has turns and all of them have an Order."""
    open_weeks = _open_weeks()
    result = await session.execute(
        select(open_weeks.c.game_id)
        .select_from(
            open_weeks.join(
                seat_turns,
                (seat_turns.c.game_id == open_weeks.c.game_id)
                & (seat_turns.c.week == open_weeks.c.week),
            )
        )
        .group_by(open_weeks.c.game_id)
        .having(func.bool_and(seat_turns.c.ordered_at.is_not(None)))
        .order_by(open_weeks.c.game_id)
    )
    return list(result.scalars())


async def insert_batch(session: AsyncSession, values: dict[str, Any]) -> None:
    await session.execute(simulation_batches.insert().values(**values))


async def get_batch(session: AsyncSession, batch_id: uuid.UUID) -> RowMapping | None:
    result = await session.execute(
        select(simulation_batches).where(simulation_batches.c.id == batch_id)
    )
    return result.mappings().one_or_none()


async def batch_game_ids(session: AsyncSession, batch_id: uuid.UUID) -> list[uuid.UUID]:
    """The id of every Game of the batch, in the order they were created (ids are UUIDv7)."""
    result = await session.execute(
        select(games.c.id).where(games.c.batch_id == batch_id).order_by(games.c.id)
    )
    return list(result.scalars())


# The scheduling aid (Story 6.19, FR-22): one open proposal per Game and who accepted it.


async def time_proposal(session: AsyncSession, game_id: uuid.UUID) -> RowMapping | None:
    """The Game's proposal of a time to play, whether or not its time has passed."""
    result = await session.execute(
        select(time_proposals).where(time_proposals.c.game_id == game_id)
    )
    return result.mappings().one_or_none()


async def time_proposal_by_id(session: AsyncSession, proposal_id: uuid.UUID) -> RowMapping | None:
    result = await session.execute(select(time_proposals).where(time_proposals.c.id == proposal_id))
    return result.mappings().one_or_none()


async def replace_time_proposal(
    session: AsyncSession,
    game_id: uuid.UUID,
    proposal_id: uuid.UUID,
    proposed_by: uuid.UUID,
    at: Any,
) -> None:
    """The Game's one proposal becomes this one: the earlier proposal goes, and its acceptances
    with it (`ON DELETE CASCADE`)."""
    await session.execute(time_proposals.delete().where(time_proposals.c.game_id == game_id))
    await session.execute(
        time_proposals.insert().values(
            id=proposal_id, game_id=game_id, proposed_by=proposed_by, at=at
        )
    )


async def accept_time_proposal(
    session: AsyncSession, proposal_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    """Record that `user_id` accepted the proposal; False, changing nothing, when they had."""
    result = await session.execute(
        insert(time_acceptances)
        .values(proposal_id=proposal_id, user_id=user_id)
        .on_conflict_do_nothing(
            index_elements=[time_acceptances.c.proposal_id, time_acceptances.c.user_id]
        )
        .returning(time_acceptances.c.user_id)
    )
    return result.scalar_one_or_none() is not None


async def time_acceptors(session: AsyncSession, proposal_id: uuid.UUID) -> list[uuid.UUID]:
    """Who accepted the proposal, in the order they did."""
    result = await session.execute(
        select(time_acceptances.c.user_id)
        .where(time_acceptances.c.proposal_id == proposal_id)
        .order_by(time_acceptances.c.accepted_at, time_acceptances.c.user_id)
    )
    return list(result.scalars())


def chain_cost_of(state: Any) -> Any:
    """The chain Total cost of a stored Week state in SQL: the sum of its seats' `total_cost`, as
    revision 0051's backfill sums it."""
    seat = func.jsonb_array_elements(state["seats"]).table_valued("value").alias("seat")
    return (
        select(func.sum(seat.c.value.op("->>")("total_cost").cast(Numeric)))
        .select_from(seat)
        .scalar_subquery()
    )


async def newest_week(session: AsyncSession, game_id: uuid.UUID) -> RowMapping | None:
    """The Game's newest stored Week state row: `week`, `finished` and its `chain_cost`; the
    finished one once the Game has finished. None before the start."""
    result = await session.execute(
        select(
            game_weeks.c.week,
            game_weeks.c.finished,
            chain_cost_of(game_weeks.c.state).label("chain_cost"),
        )
        .where(game_weeks.c.game_id == game_id)
        .order_by(game_weeks.c.week.desc(), game_weeks.c.finished.desc())
        .limit(1)
    )
    return result.mappings().one_or_none()


async def upsert_summary(session: AsyncSession, values: dict[str, Any]) -> None:
    """Write the Game's `game_summaries` row (Story 7.1, AD-25), as `games.commands` only."""
    statement = insert(game_summaries).values(**values, updated_at=func.now())
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[game_summaries.c.game_id],
            set_={
                name: statement.excluded[name]
                for name in (*values, "updated_at")
                if name != "game_id"
            },
        )
    )


async def summary(session: AsyncSession, game_id: uuid.UUID) -> RowMapping | None:
    result = await session.execute(
        select(game_summaries).where(game_summaries.c.game_id == game_id)
    )
    return result.mappings().one_or_none()


async def class_summaries(session: AsyncSession, class_session_id: uuid.UUID) -> list[RowMapping]:
    """The `game_summaries` rows of the Class session's Games that the Lecturer overview lists
    (AD-13), by game number: one read whatever their number (NFR-3)."""
    result = await session.execute(
        select(game_summaries)
        .where(
            game_summaries.c.class_session_id == class_session_id,
            game_summaries.c.purpose.in_(purposes_with("lecturer_overview")),
        )
        .order_by(game_summaries.c.game_number, game_summaries.c.game_id)
    )
    return list(result.mappings())


_COST_PARTS = text(
    """
    SELECT w.game_id,
           seat ->> 'role' AS role,
           (g.settings ->> 'holding_cost')::numeric
               * sum((seat ->> 'inventory')::numeric) AS holding_cost,
           (g.settings ->> 'backorder_cost')::numeric
               * sum((seat ->> 'backlog')::numeric) AS backorder_cost
    FROM game_weeks w
    JOIN games g ON g.id = w.game_id
    CROSS JOIN LATERAL jsonb_array_elements(w.state -> 'seats') AS seat
    WHERE w.game_id = ANY(:ids) AND NOT w.finished
    GROUP BY w.game_id, seat ->> 'role', g.settings ->> 'holding_cost',
             g.settings ->> 'backorder_cost'
    """
)


async def cost_parts_of(session: AsyncSession, game_ids: Collection[uuid.UUID]) -> list[RowMapping]:
    """Each Role's Total cost of the Games split into lager and restordre, as `game_id`, `role`,
    `holding_cost`, `backorder_cost`: the Game's snapshot rates times the inventory and the backlog
    summed over its opened Week states, as `views.chain_result` adds them. One read whatever the
    number of Games (NFR-3)."""
    if not game_ids:
        return []
    result = await session.execute(_COST_PARTS, {"ids": list(game_ids)})
    return list(result.mappings())
