"""Read models of a Game for its players (AD-3). Views assemble; the engine computes.

`seat_state` is the single information boundary: the play screen, the LLM player's prompt and
the Decision log read the `SeatState` it returns and nothing else about the Game.
"""

import uuid
from collections.abc import Awaitable, Callable, Mapping, Sequence
from datetime import datetime
from decimal import Decimal

from sqlalchemy import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine import (
    GameSettings,
    Role,
    WeekState,
    neighbour_numbers,
    seat_detail,
    seat_view,
)
from app.modules.games import repo, rules
from app.modules.games.marks import TAKEOVER_MARKS, seat_mark
from app.modules.games.policy import policy
from app.modules.games.schemas import (
    ChainWeekCost,
    CostSum,
    DecisionLogRow,
    GameResult,
    Lifecycle,
    OccupancyRow,
    OccupantKind,
    RoleCost,
    SeatState,
    TableSeat,
    TableStatus,
    TurnOverview,
)
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker, reading

__all__ = [
    "ViewError",
    "build_seat_state",
    "chain_result",
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
    *,
    neighbours: bool | None = None,
) -> SeatState:
    """The `SeatState` of `role` in the last of the opened Weeks `states`, given the Order maps
    of the earlier Weeks. Reads only that Role's Seat, and with `neighbours` the inventory and
    backlog of the neighbours whose view `settings.info_visibility` switches on (Story 6.21).

    `neighbours` None follows `FEATURE_INFO_VISIBILITY` now: with the flag off no neighbour
    number is filled, whatever the snapshot says (AD-17). Only the Game check passes it, to
    rebuild a state as it was recorded."""
    view = seat_view(settings, states, orders, role)
    detail = seat_detail(settings, states, orders, role)
    if neighbours is None:
        neighbours = get_settings().feature_info_visibility
    shown = neighbour_numbers(settings, states[-1], role) if neighbours else ()
    return SeatState.model_validate({**dict(view), **dict(detail), "neighbour_numbers": shown})


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


async def seat_state(
    game_id: str, seat: str, week: int | None = None, *, session: AsyncSession | None = None
) -> SeatState:
    """What `seat` (a Role or a Seat id) sees in `week`, by default the newest opened Week.

    Built from the Game's snapshot settings and its stored Week states only. In the caller's
    `session` when given."""
    async with reading(session) as s:
        game, row = await _game_and_seat(s, game_id, seat)
        opened, orders = await stored_play(s, game["id"])
    week = _week(opened, week)
    settings = GameSettings.model_validate(game["settings"])
    return build_seat_state(settings, opened[:week], orders[: week - 1], row["role"])


async def chain_result(game_id: str) -> GameResult:
    """The finished Game's cost per Role and the chain's cost per Uke (Story 6.18, FR-28), from
    its snapshot settings, stored Week states and Orders through the engine's `seat_detail`: each
    Role's running sums in every Uke it played. Only this sums Roles into the chain.

    Refuses (`ViewError`): `game_not_found` 404, `game_not_finished` 409 before the end, so no
    chain number leaks during play (AD-3, FR-14)."""
    game_uuid = _uuid(game_id)
    async with get_sessionmaker()() as session:
        game = await repo.get_game(session, game_uuid) if game_uuid else None
        if game is None:
            raise ViewError("game_not_found", f"no Game {game_id!r}", 404)
        if game["lifecycle"] != Lifecycle.FINISHED:
            raise ViewError("game_not_finished", "the Game has not finished", 409)
        opened = await _opened(session, game["id"])
        orders = await stored_orders(session, game["id"])
    settings = GameSettings.model_validate(game["settings"])
    roles: list[RoleCost] = []
    per_week: list[list[tuple[Decimal, Decimal, Decimal]]] = []
    for role in settings.roles:
        detail = seat_detail(settings, opened, orders[: len(opened) - 1], role)
        running = [
            (row.total_holding_cost, row.total_backorder_cost, row.total_cost)
            for row in detail.history
        ]
        last = (detail.total_holding_cost, detail.total_backorder_cost, detail.total_cost)
        running.append(last)
        per_week.append(running)
        roles.append(
            RoleCost(role=role, holding_cost=last[0], backorder_cost=last[1], total_cost=last[2])
        )
    weeks = tuple(
        ChainWeekCost(
            week=number,
            holding_cost=sum((each[number - 1][0] for each in per_week), Decimal(0)),
            backorder_cost=sum((each[number - 1][1] for each in per_week), Decimal(0)),
            total_cost=sum((each[number - 1][2] for each in per_week), Decimal(0)),
        )
        for number in range(1, len(opened) + 1)
    )
    chain = CostSum(
        holding_cost=sum((r.holding_cost for r in roles), Decimal(0)),
        backorder_cost=sum((r.backorder_cost for r in roles), Decimal(0)),
        total_cost=sum((r.total_cost for r in roles), Decimal(0)),
    )
    return GameResult(roles=tuple(roles), chain=chain, weeks=weeks)


async def open_turn(
    game_id: str, seat: str, week: int | None = None, *, session: AsyncSession | None = None
) -> TurnOverview:
    """The turn of `seat` (a Role or a Seat id) in `week`, by default the newest opened Week. In
    the caller's `session` when given."""
    async with reading(session) as s:
        game, row = await _game_and_seat(s, game_id, seat)
        week = _week(await _opened(s, game["id"]), week)
        turn = await repo.turn(s, game["id"], row["id"], week)
        order = await repo.seat_week_order(s, game["id"], week, row["id"])
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
    the one they held last. Built at read time; never stored and never sent to an LLM.

    While the Game runs, each Seat also says whether it has ordered in the open Week
    (`rules.has_ordered`), the stored wait start of a Seat that has not, and its mark
    (`marks.seat_mark`); and the stored due times still open: AI deadlines (Story 6.14), Takeover
    due times and insert times (Story 8.1, AD-20).
    Nothing here computes a wait."""
    rows = await repo.seats_with_occupant(session, game_id)
    held = {row["role"]: row["user_id"] for row in rows}
    own = await repo.last_seat_of(session, game_id, viewer_id)
    histories = await repo.seat_histories(session, game_id)
    named = {u for u in held.values() if u is not None} | {
        h["last_student"] for h in histories.values() if h["last_student"] is not None
    }
    found = await names(sorted(named))
    turns, guided = await _open_turns(session, game_id)
    queued = await repo.queued_reclaims(session, game_id)
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
        turn = turns.get(row["id"])
        ordered = None if turn is None else rules.has_ordered(turn, guided=guided)
        mark = seat_mark(None, None, kind, row["reason"])
        history = histories.get(
            row["id"], {"last_student": None, "taken_over": False, "guard_switched": False}
        )
        # Taken over since its Student's last row, also after a later guard or cost-limit switch.
        taken_over = holder == "ai" and (mark in TAKEOVER_MARKS or history["taken_over"])
        seats.append(
            TableSeat(
                role=row["role"],
                holder=holder,
                name=name,
                mine=mine,
                ordered=ordered,
                wait_started_at=turn["wait_started_at"] if ordered is False else None,
                mark=mark,
                taken_over=taken_over,
                ordering_for=found.get(history["last_student"]) if taken_over else None,
                guard_switched=kind == OccupantKind.RULE_BASED and history["guard_switched"],
                # Story 8.4: only the Student who asked sees their queued Reclaim.
                reclaim_queued=mine and taken_over and queued.get(row["id"]) == viewer_id,
            )
        )
    due = sorted(
        at
        for turn in turns.values()
        if not rules.has_ordered(turn, guided=guided)
        for at in _due_times_of(turn)
        if at is not None
    )
    return TableStatus(seats=tuple(seats), due_times=tuple(due))


def _due_times_of(turn: RowMapping) -> tuple[datetime | None, ...]:
    """A turn's stored due times that still apply: its AI deadline, and its FR-36 due times
    while a Student holds the Seat (Story 8.1)."""
    if turn["occupant_kind"] != OccupantKind.STUDENT:
        return (turn["ai_deadline_at"],)
    return (turn["ai_deadline_at"], turn["takeover_due_at"], turn["insert_allowed_at"])


async def _open_turns(
    session: AsyncSession, game_id: uuid.UUID
) -> tuple[dict[uuid.UUID, RowMapping], bool]:
    """The open Week's turns by Seat id, each with its occupant in force, and whether it is a
    Guided Week; none when the Game is not running."""
    game = await repo.get_game(session, game_id)
    if game is None or game["lifecycle"] not in (Lifecycle.RUNNING, Lifecycle.PLAYING_OUT):
        return {}, False
    week = await repo.open_week(session, game_id)
    if week is None:
        return {}, False
    settings = GameSettings.model_validate(game["settings"])
    guided = rules.guided_week(policy(game["purpose"]), settings, week)
    turns = await repo.week_turns_with_occupant(session, game_id, week)
    return {turn["seat_id"]: turn for turn in turns}, guided
