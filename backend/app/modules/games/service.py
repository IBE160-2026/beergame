"""What other modules may use from `games`. Writes go through `games.commands` only."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import budget as ai_budget
from app.engine import GameSettings
from app.modules.games import repo
from app.modules.games.batches import create_batch, get_batch
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
    OccupancyReason,
    OccupancyRow,
    OccupantKind,
    OrderPlaced,
    PendingTurn,
    Purpose,
    SeatOverview,
    SeatState,
    SessionRuntime,
    SimulationBatch,
    TurnOverview,
)
from app.modules.games.summaries import game_summary
from app.modules.games.turns import OpenGame, llm_turn, pending_turn
from app.modules.games.views import (
    ViewError,
    decision_log,
    occupancy_history,
    open_turn,
    seat_state,
)
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
    "OccupancyReason",
    "OccupancyRow",
    "OccupantKind",
    "OpenGame",
    "OrderPlaced",
    "OverdueTurn",
    "PendingTurn",
    "Purpose",
    "PurposeNotSupportedError",
    "SeatOverview",
    "SeatState",
    "SessionRuntime",
    "SimulationBatch",
    "TurnOverview",
    "ViewError",
    "budget_scope",
    "class_game_ids",
    "complete_running_games",
    "create_batch",
    "games_charged_to",
    "scope_of",
    "decision_log",
    "finished_game_ids",
    "game_summary",
    "get_batch",
    "get_game",
    "llm_turn",
    "occupancy_history",
    "open_turn",
    "overdue_llm_turns",
    "pending_turn",
    "policy",
    "rules_versions_without_package",
    "seat_state",
    "verify_finished",
]


async def class_game_ids(session: AsyncSession, class_session_id: uuid.UUID) -> dict[int, str]:
    """The Class session's Games by game number, read in the caller's transaction (Story
    5.10)."""
    found = await repo.class_game_ids(session, class_session_id)
    return {number: str(game_id) for number, game_id in found.items()}


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
        settings=_or_none(GameSettings, game["settings"]),
        session_runtime=_or_none(SessionRuntime, game["session_runtime"]),
        class_session_id=_text_or_none(game["class_session_id"]),
        game_number=game["game_number"],
        seats=tuple(
            SeatOverview(
                id=str(seat["id"]),
                role=seat["role"],
                occupant_kind=seat["occupant_kind"],
                policy_id=seat["policy_id"],
                user_id=_text_or_none(seat["user_id"]),
            )
            for seat in seats
        ),
    )


def _or_none[T: (GameSettings, SessionRuntime)](model: type[T], value: object) -> T | None:
    return None if value is None else model.model_validate(value)


def _text_or_none(value: object) -> str | None:
    return None if value is None else str(value)


def scope_of(
    purpose: Purpose | str,
    runtime: SessionRuntime | None,
    class_session_id: uuid.UUID | str | None = None,
) -> ai_budget.BudgetScope | None:
    """The one rule for which budget a Game's LLM calls are charged to (AD-6, AD-22), with the
    Effort level the Game froze. A Game of a Class session charges that Class session's budget,
    the row Story 5.1 created (Story 5.9); a simulation Game charges its model config's
    evaluation budget. A later Game purpose adds its own answer here (and to
    `games_charged_to`). None for a Game with no model config, or no snapshot yet."""
    if runtime is None or runtime.model_config_id is None:
        return None
    if class_session_id is not None:
        return ai_budget.BudgetScope.class_session(
            class_session_id, effort_level=runtime.effort_level
        )
    if Purpose(purpose) is Purpose.SIMULATION:
        return ai_budget.BudgetScope.evaluation(
            runtime.model_config_id, effort_level=runtime.effort_level
        )
    return None


async def budget_scope(game_id: str) -> ai_budget.BudgetScope | None:
    """`scope_of` for a stored Game; None for a Game with no model config, or no such Game."""
    game = await get_game(game_id)
    if game is None:
        return None
    return scope_of(game.purpose, game.session_runtime, game.class_session_id)


async def games_charged_to(scope: ai_budget.BudgetScope) -> list[str]:
    """The id of every running Game whose LLM calls are charged to `scope` (the inverse of
    `scope_of`), oldest first: a Class session's running Class games, or the running simulation
    Games of an evaluation budget's model config."""
    async with get_sessionmaker()() as session:
        if scope.kind == "class_session":
            found = await repo.running_games_of_session(session, scope.id)
        elif scope.kind == "evaluation":
            found = await repo.running_games_of_config(session, Purpose.SIMULATION.value, scope.id)
        else:
            found = []
    return [str(game_id) for game_id in found]


@dataclass(frozen=True)
class OverdueTurn:
    game_id: str
    seat_id: str
    week: int


async def overdue_llm_turns(now: datetime | None = None) -> list[OverdueTurn]:
    """Every turn in a running Game's open Week that waits for an Order past its
    `ai_deadline_at` (AD-5): at or before `now`, by default the database clock, which also
    stamped `opened_at`. Oldest deadline first."""
    async with get_sessionmaker()() as session:
        rows = await repo.overdue_llm_turns(session, now)
    return [OverdueTurn(str(row["game_id"]), str(row["seat_id"]), row["week"]) for row in rows]


async def complete_running_games() -> list[str]:
    """The id of every running Game whose open Week is complete but not yet advanced: a
    process stopped between an Order and the advance (NFR-4)."""
    async with get_sessionmaker()() as session:
        return [str(game_id) for game_id in await repo.complete_running_games(session)]
