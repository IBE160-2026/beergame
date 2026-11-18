"""The open Week as the order source sees it, inside the transaction of a running command
(AD-2, AD-5).

`games.commands` hands `players.ensure_order` an `OpenGame`: a handle on its own transaction,
whose Game row it has locked. Reads through it see the rows the command has written but not yet
committed; `games.commands.place_order(..., within=game)` writes through it.
"""

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine import GameSettings, WeekState, guided_order
from app.modules.games import repo, rules
from app.modules.games.policy import policy
from app.modules.games.schemas import Lifecycle, PendingTurn
from app.modules.games.views import build_seat_state, stored_play
from app.platform.db import get_sessionmaker

__all__ = ["OpenGame", "llm_turn", "pending_turn", "play_of"]

Play = tuple[Sequence[WeekState], Sequence[Mapping[str, int]]]


@dataclass(frozen=True)
class OpenGame:
    """The running command's transaction on one Game, whose row it holds locked."""

    session: AsyncSession
    game_id: uuid.UUID
    play: Play | None = None
    """The command's own `stored_play` of the open Week, when it has just written it: the
    opened Weeks and the Order maps before the newest. Orders placed in the open Week do not
    change it, so the order source reuses it for every Seat instead of reading the Game's
    history again per Seat. None makes every read go to the tables."""


async def play_of(game: OpenGame) -> Play:
    """The open Game's `stored_play`: the one the command handed over, or read now."""
    if game.play is not None:
        return game.play
    return await stored_play(game.session, game.game_id)


def _uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except ValueError, TypeError, AttributeError:
        return None


async def pending_turn(game: OpenGame, seat_id: str) -> PendingTurn | None:
    """The Seat's turn in the open Week, or None when the Game is not running or the Seat has
    no turn or occupant in it."""
    session = game.session
    row = await repo.get_game(session, game.game_id)
    seat_uuid = _uuid(seat_id)
    if row is None or row["lifecycle"] != Lifecycle.RUNNING or seat_uuid is None:
        return None
    seat = await repo.seat(session, game.game_id, seat_uuid)
    opened, orders = await play_of(game)
    if seat is None or not opened:
        return None
    week = opened[-1].week
    turn = await repo.turn(session, game.game_id, seat_uuid, week)
    occupancy = await repo.occupancy_in_force(session, seat_uuid, week)
    if turn is None or occupancy is None:
        return None
    settings = GameSettings.model_validate(row["settings"])
    return PendingTurn(
        game_id=str(game.game_id),
        seat_id=str(seat_uuid),
        role=seat["role"],
        week=week,
        guided=rules.guided_week(policy(row["purpose"]), settings, week),
        guided_order=guided_order(settings),
        occupant_kind=occupancy["occupant_kind"],
        policy_id=occupancy["policy_id"],
        rule_based_reference_order=turn["rule_based_reference_order"],
        ordered=turn["ordered_at"] is not None,
        ai_deadline_at=turn["ai_deadline_at"],
        seat_state=build_seat_state(settings, opened, orders, seat["role"]),
    )


async def llm_turn(game_id: str, seat_id: str, week: int) -> PendingTurn | None:
    """The Seat's turn as an `ai-orders` job sees it, read in a session of its own: the turn of
    `pending_turn` when `week` is still the open Week of the running Game, else None. `read_at`
    is the database clock at the read."""
    game_uuid = _uuid(game_id)
    if game_uuid is None:
        return None
    async with get_sessionmaker()() as session:
        turn = await pending_turn(OpenGame(session=session, game_id=game_uuid), seat_id)
        if turn is None or turn.week != week:
            return None
        return turn.model_copy(update={"read_at": await repo.now(session)})
