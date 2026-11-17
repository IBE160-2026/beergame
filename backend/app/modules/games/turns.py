"""The open Week as the order source sees it, inside the transaction of a running command
(AD-2, AD-5).

`games.commands` hands `players.ensure_order` an `OpenGame`: a handle on its own transaction,
whose Game row it has locked. Reads through it see the rows the command has written but not yet
committed; `games.commands.place_order(..., within=game)` writes through it.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine import GameSettings, guided_order
from app.modules.games import repo, rules
from app.modules.games.policy import policy
from app.modules.games.schemas import Lifecycle, PendingTurn
from app.modules.games.views import build_seat_state, stored_play

__all__ = ["OpenGame", "pending_turn"]


@dataclass(frozen=True)
class OpenGame:
    """The running command's transaction on one Game, whose row it holds locked."""

    session: AsyncSession
    game_id: uuid.UUID


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
    opened, orders = await stored_play(session, game.game_id)
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
        seat_state=build_seat_state(settings, opened, orders, seat["role"]),
    )
