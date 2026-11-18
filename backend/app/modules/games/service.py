"""What other modules may use from `games`. Writes go through `games.commands` only."""

import uuid

from app.ai import budget as ai_budget
from app.engine import GameSettings
from app.modules.games import repo
from app.modules.games.checks import (
    finished_game_ids,
    rules_versions_without_package,
    verify_finished,
)
from app.modules.games.policy import GamePolicy, PurposeNotSupportedError, policy
from app.modules.games.schemas import (
    DecidedBy,
    DecisionLogRow,
    Fallback,
    GameCheck,
    GameOverview,
    GameSummary,
    Lifecycle,
    OccupantKind,
    OrderPlaced,
    PendingTurn,
    Purpose,
    SeatOverview,
    SeatState,
    SessionRuntime,
    TurnOverview,
)
from app.modules.games.summaries import game_summary
from app.modules.games.turns import OpenGame, llm_turn, pending_turn
from app.modules.games.views import ViewError, decision_log, open_turn, seat_state
from app.platform.db import get_sessionmaker

__all__ = [
    "DecidedBy",
    "DecisionLogRow",
    "Fallback",
    "GameCheck",
    "GameOverview",
    "GamePolicy",
    "GameSummary",
    "Lifecycle",
    "OccupantKind",
    "OpenGame",
    "OrderPlaced",
    "PendingTurn",
    "Purpose",
    "PurposeNotSupportedError",
    "SeatOverview",
    "SeatState",
    "SessionRuntime",
    "TurnOverview",
    "ViewError",
    "budget_scope",
    "decision_log",
    "finished_game_ids",
    "game_summary",
    "get_game",
    "llm_turn",
    "open_turn",
    "pending_turn",
    "policy",
    "rules_versions_without_package",
    "seat_state",
    "verify_finished",
]


async def get_game(game_id: str) -> GameOverview | None:
    """The stored Game with each Seat's current occupant, or None when there is no such Game."""
    try:
        game_uuid = uuid.UUID(game_id)
    except ValueError, TypeError, AttributeError:
        return None
    async with get_sessionmaker()() as session:
        game = await repo.get_game(session, game_uuid)
        if game is None:
            return None
        seats = await repo.seats_with_occupant(session, game_uuid)
    return GameOverview(
        id=str(game["id"]),
        purpose=game["purpose"],
        lifecycle=game["lifecycle"],
        version=game["version"],
        demand_seed=game["demand_seed"],
        rules_version=game["rules_version"],
        settings=GameSettings.model_validate(game["settings"]),
        session_runtime=SessionRuntime.model_validate(game["session_runtime"]),
        seats=tuple(
            SeatOverview(
                id=str(seat["id"]),
                role=seat["role"],
                occupant_kind=seat["occupant_kind"],
                policy_id=seat["policy_id"],
            )
            for seat in seats
        ),
    )


async def budget_scope(game_id: str) -> ai_budget.BudgetScope | None:
    """The one answer to which budget a Game's LLM calls are charged to (AD-6, AD-22), with the
    Effort level the Game froze. A simulation Game charges its model config's evaluation budget;
    a later Game purpose adds its own answer here. None for a Game with no model config, or no
    such Game."""
    game = await get_game(game_id)
    if game is None or game.session_runtime.model_config_id is None:
        return None
    runtime = game.session_runtime
    if game.purpose is Purpose.SIMULATION:
        return ai_budget.BudgetScope.evaluation(
            runtime.model_config_id, effort_level=runtime.effort_level
        )
    return None
