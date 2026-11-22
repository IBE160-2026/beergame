"""The `worker-ai` rescue loop: no Game waits for an AI player past its deadline (AD-5, NFR-2,
NFR-4).

Every `RESCUE_INTERVAL_S` seconds one pass:

- places the stored Rule-based reference Order, `decided_by = rule_based` and `fallback =
  timeout`, through `games.commands.place_order` for every `llm` turn past its `ai_deadline_at`
  without an Order: the job hung, died, never ran, or failed to write its Order;
- calls `games.commands.advance` for every running Game whose open Week is complete, so a
  process that stopped between an Order and the advance cannot stall a Game.

A late answer from the job then meets `order_exists` and the fallback Order stands; the late
attempts keep their rows in the LLM call log, tied to the turn by their caller reference. A
turn with no deadline (Epic 8's playout) is never picked. One failing item is logged and the
pass goes on. This module loads no LLM library.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime

import structlog

from app.modules.games import commands as games_commands
from app.modules.games import service as games_service

__all__ = ["RESCUE_INTERVAL_S", "RescuePass", "rescue_once", "run"]

log = structlog.get_logger(__name__)

RESCUE_INTERVAL_S = 5.0
"""Seconds between two passes (AD-5)."""

ENDED = frozenset({"order_exists", "week_not_open", "game_finished", "test_deadline_passed"})
"""Refusals that mean the turn no longer waits: the job or another pass placed the Order, or the
Replay was closed at its Test deadline and takes none (Story 10.6)."""


@dataclass(frozen=True)
class RescuePass:
    placed: int = 0
    """Fallback Orders placed."""
    advanced: int = 0
    """Games moved on by at least one Week."""
    failed: int = 0
    """Items that raised; each is logged and tried again by the next pass."""


async def _rescue_turn(overdue: games_service.OverdueTurn) -> bool:
    """Place the timeout fallback Order of one overdue turn; False when it no longer waits for
    an LLM Order."""
    turn = await games_service.llm_turn(overdue.game_id, overdue.seat_id, overdue.week)
    if (
        turn is None
        or turn.ordered
        or turn.guided
        or turn.occupant_kind is not games_service.OccupantKind.LLM
    ):
        return False
    try:
        await games_commands.place_order(
            turn.game_id,
            turn.seat_id,
            turn.week,
            turn.rule_based_reference_order,
            games_service.DecidedBy.RULE_BASED,
            fallback=games_service.Fallback.TIMEOUT,
        )
    except games_commands.CommandError as exc:
        if exc.code in ENDED:
            return False
        raise
    log.info("llm_order_rescued", game_id=turn.game_id, seat_id=turn.seat_id, week=turn.week)
    return True


async def rescue_once(now: datetime | None = None) -> RescuePass:
    """One pass of the loop. `now` (timezone-aware) is the time deadlines are compared with;
    by default the database clock, which stamped `opened_at` too."""
    placed = advanced = failed = 0
    for overdue in await games_service.overdue_llm_turns(now):
        try:
            placed += await _rescue_turn(overdue)
        except Exception:
            failed += 1
            log.exception(
                "llm_order_rescue_failed", game_id=overdue.game_id, seat_id=overdue.seat_id
            )
    for game_id in await games_service.complete_running_games():
        try:
            advanced += await games_commands.advance(game_id)
        except Exception:
            failed += 1
            log.exception("rescue_advance_failed", game_id=game_id)
    return RescuePass(placed, advanced, failed)


async def run(interval_s: float = RESCUE_INTERVAL_S, stop: asyncio.Event | None = None) -> None:
    """Run a pass every `interval_s` seconds until `stop` is set (or the task is cancelled). A
    pass that fails as a whole (the database is away) is logged; the loop goes on."""
    stop = stop or asyncio.Event()
    while not stop.is_set():
        try:
            done = await rescue_once()
            if done.placed or done.advanced or done.failed:
                log.info(
                    "rescue_pass", placed=done.placed, advanced=done.advanced, failed=done.failed
                )
        except Exception:
            log.exception("rescue_pass_failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_s)
        except TimeoutError:
            pass
