"""Read models of a Game for its players (AD-3). Views assemble; the engine computes.

`seat_state` is the single information boundary: the play screen, the LLM player's prompt and
the Decision log read the `SeatState` it returns and nothing else about the Game.
"""

import uuid
from collections.abc import Awaitable, Callable, Mapping, Sequence

from sqlalchemy import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine import GameSettings, Role, WeekState, seat_detail, seat_view
from app.modules.games import repo, rules
from app.modules.games.policy import policy
from app.modules.games.schemas import (
    DecisionLogRow,
    Lifecycle,
    OccupancyRow,
    OccupantKind,
    SeatState,
    TableSeat,
    TableStatus,
    TurnOverview,
)
from app.platform.db import get_sessionmaker

__all__ = [
    "ViewError",
    "build_seat_state",
    "decision_log",
    "occupancy_history",
    "open_turn",
    "seat_state",
    "table_status",
]


class ViewError(Exception):
    """A refused read, with a stable code for the API envelope (AD-19)."""

    def __init__(self, code: str, message: str, status: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def build_seat_state(
    settings: GameSettings,
    states: Sequence[WeekState],
    orders: Sequence[Mapping[str, int]],
    role: Role | str,
) -> SeatState:
    """The `SeatState` of `role` in the last of the opened Weeks `states`, given the Order maps
    of the earlier Weeks. Reads only that Role's Seat."""
    view = seat_view(settings, states, orders, role)
    detail = seat_detail(settings, states, orders, role)
    return SeatState.model_validate({**dict(view), **dict(detail)})


def _uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except ValueError, TypeError, AttributeError:
        return None


async def _game_and_seat(
    session: AsyncSession, game_id: str, seat: str
) -> tuple[RowMapping, RowMapping]:
    game_uuid = _uuid(game_id)
    game = await repo.get_game(session, game_uuid) if game_uuid else None
    if game is None:
        raise ViewError("game_not_found", f"no Game {game_id!r}", 404)
    seats = await repo.seats_with_occupant(session, game["id"])
    seat_uuid = _uuid(seat)
    for row in seats:
        if row["role"] == seat or row["id"] == seat_uuid:
            break
    else:
        raise ViewError("seat_not_found", f"the Game has no Seat {seat!r}", 404)
    if game["lifecycle"] == Lifecycle.NOT_STARTED:
        raise ViewError("game_not_started", "the Game has not started", 409)
    return game, row


async def _opened(session: AsyncSession, game_id: uuid.UUID) -> list[WeekState]:
    """The stored opened Weeks of the Game, Week 1 first (a finished state is not opened)."""
    stored = await repo.week_states(session, game_id)
    return [s for s in map(WeekState.model_validate, stored) if not s.finished]


async def stored_orders(session: AsyncSession, game_id: uuid.UUID) -> list[dict[str, int]]:
    """The Order map of every Week that has an Order in the Decision log, Week 1 first."""
    maps: list[dict[str, int]] = []
    for row in await repo.placed_orders(session, game_id):
        while len(maps) < row["week"]:
            maps.append({})
        maps[row["week"] - 1][row["role"]] = row["order"]
    return maps


async def stored_play(
    session: AsyncSession, game_id: uuid.UUID
) -> tuple[list[WeekState], list[dict[str, int]]]:
    """The opened Weeks and the Order maps of the Weeks before the newest opened one."""
    opened = await _opened(session, game_id)
    orders = await stored_orders(session, game_id)
    return opened, orders[: max(len(opened) - 1, 0)]


def _week(opened: Sequence[WeekState], week: int | None) -> int:
    """`week`, or the newest opened Week; refuses a Week that has not been opened."""
    week = len(opened) if week is None else week
    if not 1 <= week <= len(opened):
        raise ViewError("week_not_open", f"Week {week} has not been opened", 409)
    return week


async def seat_state(game_id: str, seat: str, week: int | None = None) -> SeatState:
    """What `seat` (a Role or a Seat id) sees in `week`, by default the newest opened Week.

    Built from the Game's snapshot settings and its stored Week states only."""
    async with get_sessionmaker()() as session:
        game, row = await _game_and_seat(session, game_id, seat)
        opened, orders = await stored_play(session, game["id"])
    week = _week(opened, week)
    settings = GameSettings.model_validate(game["settings"])
    return build_seat_state(settings, opened[:week], orders[: week - 1], row["role"])


async def open_turn(game_id: str, seat: str, week: int | None = None) -> TurnOverview:
    """The turn of `seat` (a Role or a Seat id) in `week`, by default the newest opened Week."""
    async with get_sessionmaker()() as session:
        game, row = await _game_and_seat(session, game_id, seat)
        week = _week(await _opened(session, game["id"]), week)
        turn = await repo.turn(session, game["id"], row["id"], week)
        order = await repo.seat_week_order(session, game["id"], week, row["id"])
    if turn is None:
        raise ViewError("week_not_open", f"the Seat has no turn in Week {week}", 409)
    settings = GameSettings.model_validate(game["settings"])
    return TurnOverview(
        week=turn["week"],
        guided=rules.guided_week(policy(game["purpose"]), settings, turn["week"]),
        opened_at=turn["opened_at"],
        ordered_at=turn["ordered_at"],
        viewed_at=turn["viewed_at"],
        order=order,
        rule_based_reference_order=turn["rule_based_reference_order"],
        near_optimal_reference_order=turn["near_optimal_reference_order"],
        near_optimal_algorithm_version=turn["near_optimal_algorithm_version"],
    )


async def decision_log(game_id: str) -> tuple[DecisionLogRow, ...]:
    """The Game's Decision log: one row per Seat per Week with an Order, by Week and chain
    order (AD-15)."""
    game_uuid = _uuid(game_id)
    async with get_sessionmaker()() as session:
        game = await repo.get_game(session, game_uuid) if game_uuid else None
        if game is None:
            raise ViewError("game_not_found", f"no Game {game_id!r}", 404)
        rows = await repo.decision_log(session, game_uuid)
    return tuple(
        DecisionLogRow(
            week=row["week"],
            role=row["role"],
            seat_id=str(row["seat_id"]),
            order=row["order"],
            decided_by=row["decided_by"],
            fallback=row["fallback"],
            occupant_kind=row["occupant_kind"],
            reason=row["reason"],
            opened_at=row["opened_at"],
            ordered_at=row["ordered_at"],
            ai_deadline_at=row["ai_deadline_at"],
            rule_based_reference_order=row["rule_based_reference_order"],
            near_optimal_reference_order=row["near_optimal_reference_order"],
            near_optimal_algorithm_version=row["near_optimal_algorithm_version"],
            llm_call_ids=tuple(str(call_id) for call_id in row["llm_call_ids"]),
            effort_level=row["effort_level"],
            state_seen=SeatState.model_validate(row["state_seen"]),
        )
        for row in rows
    )


async def occupancy_history(game_id: str) -> tuple[OccupancyRow, ...]:
    """Every Seat's occupancy history, by chain order and then as appended (AD-5): the Week a
    Seat was switched is the `from_week` of its switch row (FR-67, FR-79)."""
    game_uuid = _uuid(game_id)
    async with get_sessionmaker()() as session:
        game = await repo.get_game(session, game_uuid) if game_uuid else None
        if game is None:
            raise ViewError("game_not_found", f"no Game {game_id!r}", 404)
        rows = await repo.occupancy_history(session, game_uuid)
    return tuple(
        OccupancyRow(
            role=row["role"],
            seat_id=str(row["seat_id"]),
            from_week=row["from_week"],
            occupant_kind=row["occupant_kind"],
            policy_id=row["policy_id"],
            reason=row["reason"],
        )
        for row in rows
    )


NameResolver = Callable[[list[uuid.UUID]], Awaitable[Mapping[uuid.UUID, str]]]
"""Given Student ids, their names now; an id left out has no name to show (no longer in the
Class). `games` imports no feature module, so the caller passes it (`classes.student_names`)."""


async def table_status(
    session: AsyncSession, game_id: uuid.UUID, viewer_id: uuid.UUID, names: NameResolver
) -> TableStatus:
    """Who sits in each Seat of the Game, as `viewer_id` sees it (Story 6.1, AD-3): Fabrikk first
    (UX-DR73), a Student by the name `names` gives now, every AI player as an AI player with no
    kind, a Seat with no occupant as free. The viewer's own Seat is the one they hold now, else
    the one they held last. Built at read time; never stored and never sent to an LLM."""
    rows = await repo.seats_with_occupant(session, game_id)
    held = {row["role"]: row["user_id"] for row in rows}
    own = await repo.last_seat_of(session, game_id, viewer_id)
    found = await names(sorted({u for u in held.values() if u is not None}))
    seats = []
    for row in reversed(rows):  # chain order serves the customer first; Fabrikk leads here
        kind = row["occupant_kind"]
        if kind is None:
            holder, name = "free", None
        elif kind == OccupantKind.STUDENT:
            holder, name = "student", found.get(row["user_id"])
        else:
            holder, name = "ai", None
        # A Seat another Student holds now is never the viewer's, even if the viewer held it once.
        mine = row["role"] == own and (holder != "student" or row["user_id"] == viewer_id)
        seats.append(TableSeat(role=row["role"], holder=holder, name=name, mine=mine))
    return TableStatus(seats=tuple(seats))
