"""The `ai-orders` job: one LLM player's Order for one Week (AD-5, AD-6, FR-32, FR-67).

`players.service.ensure_order` defers it, keyed `(game, week, seat)`, with ids only. The job
reads the Seat's turn, asks the gateway once (`ai.run`, at most 6 attempts inside the gateway)
and places the Order through `games.commands.place_order`:

- a valid answer: the model's Order, `decided_by = llm`, with the ids of every attempt;
- a typed failure (`timeout`, `invalid_output`, `budget_exhausted`, `provider_error`): the
  Rule-based reference Order stored on the turn, `decided_by = rule_based`, `fallback` = the
  failure type, with the ids of the failed attempts. The occupancy stays `llm`, so the model is
  asked again next Week.

The job never retries itself and never stalls the Game: a call the gateway refuses to prepare
(`GatewayError`, a config mistake) also places the fallback Order, as `provider_error`. A job
delivered twice, or one that finds the Seat has ordered, the Week moved on or the Game
finished, ends without error (`order_exists`, `week_not_open`, `game_finished`).
"""

import structlog

from app.ai import gateway
from app.modules.games import commands as games_commands
from app.modules.games import service as games_service
from app.modules.players import llm
from app.modules.players.service import PLACE_LLM_ORDER
from app.platform import jobs

__all__ = ["place_llm_order"]

log = structlog.get_logger(__name__)

ENDED = frozenset({"order_exists", "week_not_open", "game_finished"})
"""Refusals that mean the Order is no longer this job's to place."""


async def _decide(
    turn: games_service.PendingTurn,
) -> tuple[int, games_service.DecidedBy, games_service.Fallback, tuple[str, ...]]:
    """The Order, who decided it, the fallback mark and the LLM call ids."""
    reference = turn.rule_based_reference_order
    fallback = (reference, games_service.DecidedBy.RULE_BASED)
    scope = await games_service.budget_scope(turn.game_id)
    state = turn.seat_state
    try:
        if scope is None:
            raise gateway.GatewayError("scope_unresolved", "the Game has no model config")
        result = await gateway.run(
            llm.PURPOSE,
            scope,
            llm.request_inputs(turn.game_id, turn.seat_id, turn.week, state, reference),
            llm.order_schema(state.min_order, state.max_order),
            deadline=None,  # the per-Order time budget comes with Story 2.6
        )
    except gateway.GatewayError as exc:
        log.error(
            "llm_order_not_prepared", game_id=turn.game_id, seat_id=turn.seat_id, code=exc.code
        )
        return *fallback, games_service.Fallback.PROVIDER_ERROR, ()
    except Exception:  # never stall the Game: any other failure also gets the fallback Order
        log.exception("llm_order_call_failed", game_id=turn.game_id, seat_id=turn.seat_id)
        return *fallback, games_service.Fallback.PROVIDER_ERROR, ()
    ids = tuple(str(call_id) for call_id in result.llm_call_ids)
    if isinstance(result, gateway.Failure):
        log.info("llm_order_fallback", game_id=turn.game_id, seat_id=turn.seat_id, kind=result.kind)
        return *fallback, games_service.Fallback(result.kind), ids
    return (
        result.output.order,
        games_service.DecidedBy.LLM,
        games_service.Fallback.NONE,
        ids,
    )


@jobs.app.task(name=PLACE_LLM_ORDER, queue=jobs.AI_ORDERS)
async def place_llm_order(game_id: str, seat_id: str, week: int) -> None:
    """Place the LLM player's Order of `seat_id` for `week` of `game_id`, or end without one
    when that turn no longer waits for an LLM Order."""
    turn = await games_service.llm_turn(game_id, seat_id, week)
    if (
        turn is None
        or turn.ordered
        or turn.guided
        or turn.occupant_kind is not games_service.OccupantKind.LLM
    ):
        log.info("llm_order_not_needed", game_id=game_id, seat_id=seat_id, week=week)
        return
    order, decided_by, fallback, ids = await _decide(turn)
    try:
        await games_commands.place_order(
            game_id, seat_id, week, order, decided_by, fallback=fallback, llm_call_ids=ids
        )
    except games_commands.CommandError as exc:
        if exc.code in ENDED:
            log.info("llm_order_ended", game_id=game_id, seat_id=seat_id, week=week, code=exc.code)
            return
        if decided_by is not games_service.DecidedBy.LLM:
            raise
        # The model's Order was refused (it passed the schema, so this is unexpected): the
        # Week still gets the reference Order, marked as an invalid answer.
        log.error("llm_order_refused", game_id=game_id, seat_id=seat_id, code=exc.code)
        await _place_fallback(turn, games_service.Fallback.INVALID_OUTPUT, ids)


async def _place_fallback(
    turn: games_service.PendingTurn, fallback: games_service.Fallback, ids: tuple[str, ...]
) -> None:
    try:
        await games_commands.place_order(
            turn.game_id,
            turn.seat_id,
            turn.week,
            turn.rule_based_reference_order,
            games_service.DecidedBy.RULE_BASED,
            fallback=fallback,
            llm_call_ids=ids,
        )
    except games_commands.CommandError as exc:
        if exc.code not in ENDED:
            raise
