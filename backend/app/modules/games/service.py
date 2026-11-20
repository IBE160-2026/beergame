"""What other modules may use from `games`. Writes go through `games.commands` only."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

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
    TableSeat,
    TableStatus,
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
    table_status,
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
    "StudentGame",
    "TableSeat",
    "TableStatus",
    "TurnOverview",
    "ViewError",
    "ClassGame",
    "ClassGameSeat",
    "budget_scope",
    "class_game_ids",
    "class_games",
    "class_games_of",
    "class_sessions_awaiting_snapshot",
    "class_sessions_with_unstarted_games",
    "complete_running_games",
    "create_batch",
    "games_charged_to",
    "scope_of",
    "own_game",
    "PlayStatus",
    "play_status",
    "student_game",
    "student_seated",
    "table_status",
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


@dataclass(frozen=True)
class ClassGameSeat:
    role: str
    occupant_kind: str | None
    user_id: uuid.UUID | None


@dataclass(frozen=True)
class ClassGame:
    """A Class game as the Klasseøkt lists it (Story 5.12): its Seats in chain order."""

    id: uuid.UUID
    number: int
    lifecycle: str
    has_snapshot: bool
    seats: tuple[ClassGameSeat, ...]


async def class_games(session: AsyncSession, class_session_id: uuid.UUID) -> list[ClassGame]:
    """The Class session's Games by number with each Seat's current occupant, read in the
    caller's transaction (Story 5.12)."""
    return (await class_games_of(session, [class_session_id])).get(class_session_id, [])


async def class_games_of(
    session: AsyncSession, class_session_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, list[ClassGame]]:
    """`class_games` of many Class sessions in two reads, by session id; a session with no Game
    is left out. For the sweep's finders, which judge every confirmed session each minute."""
    if not class_session_ids:
        return {}
    seats: dict[uuid.UUID, list[ClassGameSeat]] = {}
    for seat in await repo.class_session_seats(session, class_session_ids):
        seats.setdefault(seat["game_id"], []).append(
            ClassGameSeat(seat["role"], seat["occupant_kind"], seat["user_id"])
        )
    found: dict[uuid.UUID, list[ClassGame]] = {}
    for game in await repo.class_games(session, class_session_ids):
        found.setdefault(game["class_session_id"], []).append(
            ClassGame(
                id=game["id"],
                number=game["game_number"],
                lifecycle=game["lifecycle"],
                has_snapshot=game["has_snapshot"],
                seats=tuple(seats.get(game["id"], ())),
            )
        )
    return found


async def class_sessions_awaiting_snapshot(session: AsyncSession) -> list[uuid.UUID]:
    """The Class sessions with a Game that is `not_started` and has no snapshot (Story 5.12)."""
    return await repo.class_sessions_awaiting_snapshot(session)


async def class_sessions_with_unstarted_games(session: AsyncSession) -> list[uuid.UUID]:
    """The Class sessions with a Game that has its snapshot and is `not_started`: where a late
    registrant can still take an AI player's Seat, or a removed Student's Seat can go to one
    (Story 5.13)."""
    return await repo.class_sessions_with_unstarted_games(session)


async def student_seated(
    session: AsyncSession, class_session_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    """Whether the Student holds a Seat in a Game of the Class session now (Story 5.13)."""
    return await repo.student_seated(session, class_session_id, user_id)


@dataclass(frozen=True)
class StudentGame:
    """A Student's game in a Class session (Story 6.1): the Game, its number and the Role of the
    Student's Seat."""

    game_id: uuid.UUID
    class_session_id: uuid.UUID
    number: int
    role: str


async def student_game(
    session: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID
) -> StudentGame | None:
    """The one way any module finds a Student's game (Story 6.1): the Class game of the Class
    session in which the Student holds a Seat now, else the one in which they held a Seat last
    (joined through `authz.own_seat`); None when they never held one. Read in the caller's
    transaction."""
    rows = await repo.student_seats(session, class_session_id, user_id)
    if not rows:
        return None
    # A Seat held now wins; otherwise the latest occupancy row naming the Student (UUIDv7 ids).
    best = max(rows, key=lambda row: (bool(row["holds"]), row["row_id"].bytes))
    return StudentGame(
        game_id=best["game_id"],
        class_session_id=class_session_id,
        number=best["game_number"],
        role=best["role"],
    )


PlayStatusName = Literal["not_ready", "ready", "running", "finished"]


@dataclass(frozen=True)
class PlayStatus:
    """Where a Game stands for its Students (Story 6.5): `not_ready` before its snapshot,
    `ready` to start, `running` (also while it plays out) with its open Week, or `finished`.
    Never the number of Weeks (FR-14)."""

    status: PlayStatusName
    week: int | None


async def play_status(session: AsyncSession, game_id: uuid.UUID) -> PlayStatus:
    """The Game's `PlayStatus`, read in the caller's transaction."""
    game = await repo.get_game(session, game_id)
    if game is None:
        raise LookupError(f"no Game {game_id}")
    lifecycle = game["lifecycle"]
    if lifecycle == Lifecycle.NOT_STARTED:
        return PlayStatus("ready" if game["settings"] is not None else "not_ready", None)
    if lifecycle == Lifecycle.FINISHED:
        return PlayStatus("finished", None)
    if lifecycle in (Lifecycle.RUNNING, Lifecycle.PLAYING_OUT):
        return PlayStatus("running", await repo.open_week(session, game_id))
    raise ValueError(f"unknown lifecycle {lifecycle!r}")


async def own_game(
    session: AsyncSession, user_id: uuid.UUID, game_id: uuid.UUID
) -> StudentGame | None:
    """The Game `game_id` when it is the Student's game, the one `student_game` gives for its
    Class session (joined through `authz.own_seat`); None for any other Game, also one they held a
    Seat in before a move, so another's reads the same as one that does not exist (FR-5)."""
    game = await repo.own_game(session, user_id, game_id)
    if game is None or game["class_session_id"] is None:
        return None
    found = await student_game(session, user_id, game["class_session_id"])
    if found is None or found.game_id != game_id:
        return None
    return found


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
