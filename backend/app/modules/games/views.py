"""Read models of a Game for its players (AD-3). Views assemble; the engine computes.

`seat_state` is the single information boundary: the play screen, the LLM player's prompt and
the Decision log read the `SeatState` it returns and nothing else about the Game.
"""

import uuid
from collections.abc import Mapping, Sequence

from sqlalchemy import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine import GameSettings, Role, WeekState, placed_orders, seat_detail, seat_view
from app.modules.games import repo
from app.modules.games.schemas import Lifecycle, SeatState, TurnOverview
from app.platform.db import get_sessionmaker

__all__ = ["ViewError", "build_seat_state", "open_turn", "seat_state"]


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
        opened = await _opened(session, game["id"])
    states = opened[: _week(opened, week)]
    settings = GameSettings.model_validate(game["settings"])
    return build_seat_state(settings, states, placed_orders(settings, states), row["role"])


async def open_turn(game_id: str, seat: str, week: int | None = None) -> TurnOverview:
    """The turn of `seat` (a Role or a Seat id) in `week`, by default the newest opened Week."""
    async with get_sessionmaker()() as session:
        game, row = await _game_and_seat(session, game_id, seat)
        week = _week(await _opened(session, game["id"]), week)
        turn = await repo.turn(session, game["id"], row["id"], week)
    if turn is None:
        raise ViewError("week_not_open", f"the Seat has no turn in Week {week}", 409)
    return TurnOverview(
        week=turn["week"],
        opened_at=turn["opened_at"],
        ordered_at=turn["ordered_at"],
        rule_based_reference_order=turn["rule_based_reference_order"],
    )
