"""The one order source for every Seat that no Student holds (AD-5, FR-30).

`games.commands` calls `ensure_order` when a Week opens and right after a switch, inside its own
transaction. Guided, Rule-based and scripted Orders are placed there and then, through
`games.commands.place_order(..., within=game)`, so they share that command's lock, version
increment and event. `players` reaches game state only through `games.service` and
`games.commands`.
"""

import structlog

from app.engine.scripted import REGISTRY
from app.modules.games import commands as games_commands
from app.modules.games import service as games_service

__all__ = ["ensure_order"]

log = structlog.get_logger(__name__)


def _order(turn: games_service.PendingTurn) -> tuple[int, games_service.DecidedBy] | None:
    """The Order of the turn and who decided it, or None when this source places none."""
    kind = turn.occupant_kind
    if kind is games_service.OccupantKind.STUDENT:
        return None
    if turn.guided:
        return turn.guided_order, games_service.DecidedBy.GUIDED
    if kind is games_service.OccupantKind.RULE_BASED:
        return turn.rule_based_reference_order, games_service.DecidedBy.RULE_BASED
    if kind is games_service.OccupantKind.SCRIPTED:
        policy = REGISTRY.get(turn.policy_id or "")
        if policy is None:
            raise games_commands.CommandError(
                "occupant_not_playable", f"no scripted policy {turn.policy_id!r}", 422
            )
        return policy(turn.seat_state), games_service.DecidedBy.SCRIPTED
    return None  # `llm`: an `ai-orders` job, from Story 2.5


async def ensure_order(game: games_service.OpenGame, seat: str) -> None:
    """Make sure the Seat with id `seat` gets its Order for the open Week.

    In a Guided Week every non-student occupant orders the Guided Order; outside it a
    `rule_based` occupant orders the reference Order stored on its turn (never recomputed) and
    a `scripted` occupant the Order of the policy on its occupancy row. Does nothing for a
    Student, when the Game is not running, or when the Seat has already ordered, so it is safe
    to call again (AD-9)."""
    turn = await games_service.pending_turn(game, seat)
    if turn is None or turn.ordered:
        return
    decided = _order(turn)
    if decided is None:
        return
    order, decided_by = decided
    await games_commands.place_order(
        turn.game_id, turn.seat_id, turn.week, order, decided_by, within=game
    )
    log.debug("order_ensured", game_id=turn.game_id, seat_id=turn.seat_id, week=turn.week)
