"""What other modules may use from `games`. Writes go through `games.commands` only."""

import uuid
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import budget as ai_budget
from app.analysis.wall import PlayedGame
from app.engine import GameSettings, WeekState
from app.modules.games import repo
from app.modules.games.batches import create_batch, get_batch
from app.modules.games.checks import (
    finished_game_ids,
    rules_versions_without_package,
    verify_finished,
)
from app.modules.games.marks import seat_mark
from app.modules.games.policy import GamePolicy, PurposeNotSupportedError, policy, purposes_with
from app.modules.games.schemas import (
    DecidedBy,
    DecisionLogRow,
    Fallback,
    GameCheck,
    GameOverview,
    GameResult,
    GameStatus,
    GameSummary,
    Lifecycle,
    OccupancyReason,
    OccupancyRow,
    OccupantKind,
    OrderPlaced,
    PendingTurn,
    Purpose,
    SeatMark,
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
    chain_result,
    decision_log,
    occupancy_history,
    open_turn,
    seat_state,
    table_status,
)
from app.platform.db import get_sessionmaker

__all__ = [
    "ClassGameSummary",
    "ClassGameWeeks",
    "WeekSeatValues",
    "class_game_head",
    "class_game_weeks",
    "class_played",
    "DecidedBy",
    "DecisionLogRow",
    "Fallback",
    "GameCheck",
    "GameOverview",
    "GamePolicy",
    "GameStatus",
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
    "SeatMark",
    "SeatOverview",
    "SeatState",
    "SessionRuntime",
    "SimulationBatch",
    "StudentGame",
    "TestGameRef",
    "staff_test_games",
    "TableSeat",
    "TableStatus",
    "TimeProposal",
    "TurnOverview",
    "game_class_info",
    "open_time_proposal",
    "seated_students",
    "time_proposal_by_id",
    "ViewError",
    "ClassGame",
    "ClassGameSeat",
    "budget_scope",
    "class_game_ids",
    "class_games",
    "GameResult",
    "chain_result",
    "unchecked_finished_game_ids",
    "class_games_of",
    "class_sessions_awaiting_snapshot",
    "class_sessions_with_unstarted_games",
    "complete_running_games",
    "create_batch",
    "database_now",
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
    "seat_mark",
    "seat_state",
    "verify_finished",
]


async def unchecked_finished_game_ids(
    session: AsyncSession, limit: int, exclude: Collection[uuid.UUID] = ()
) -> list[uuid.UUID]:
    """At most `limit` finished Games with no finished-game check yet, oldest first (Story
    6.18), but those in `exclude`, read in the caller's session."""
    return await repo.unchecked_finished_game_ids(session, limit, exclude)


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
    number: int | None
    """The game number; None on a Lecturer's test Game, which has none (Story 6.20)."""
    role: str
    pre_play_gate: bool
    """Whether the briefing and Starting task come before play (`games.policy`, Story 6.18)."""
    test_game: bool = False
    """Whether a Lecturer of the Class session plays it as a test (`games.policy`
    `played_by_staff`, Story 6.20): reached from the Klasseøkt, never from Hjem."""


async def student_game(
    session: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID
) -> StudentGame | None:
    """The one way any module finds a Student's game (Story 6.1): the Class game of the Class
    session in which the Student holds a Seat now, else the one in which they held a Seat last
    (joined through `authz.own_seat`); None when they never held one. A Seat another Student
    held after them is never theirs to read: it shows that Student's play (FR-5). Read in the
    caller's transaction."""
    rows = [
        row
        for row in await repo.student_seats(session, class_session_id, user_id)
        if row["holds"] or not row["later_student"]
    ]
    if not rows:
        return None
    # A Seat held now wins; otherwise the latest occupancy row naming the Student (UUIDv7 ids).
    best = max(rows, key=lambda row: (bool(row["holds"]), row["row_id"].bytes))
    return StudentGame(
        game_id=best["game_id"],
        class_session_id=class_session_id,
        number=best["game_number"],
        role=best["role"],
        pre_play_gate=policy(best["purpose"]).pre_play_gate,
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


async def database_now(session: AsyncSession) -> datetime:
    """The database clock at this statement: the clock every stored time is on (AD-20)."""
    return await repo.clock_now(session)


@dataclass(frozen=True)
class TimeProposal:
    """A Class game's proposal of a time to play (Story 6.19, FR-22): who proposed which time and
    who accepted, in the order they did. Ids only; the caller resolves names."""

    id: uuid.UUID
    game_id: uuid.UUID
    at: datetime
    proposed_by: uuid.UUID
    accepted_by: tuple[uuid.UUID, ...]
    seated: frozenset[uuid.UUID]
    """The Students who hold a Seat of the Game now: those who may accept."""


def seated_students(seat_rows) -> frozenset[uuid.UUID]:
    """The Students who hold a Seat of the Game now (each Seat's latest occupancy row): the one
    rule both the scheduling aid's commands and its read use (Story 6.19)."""
    return frozenset(
        row["user_id"]
        for row in seat_rows
        if row["occupant_kind"] == OccupantKind.STUDENT and row["user_id"] is not None
    )


async def _time_proposal(session: AsyncSession, row) -> TimeProposal:
    seats = await repo.seats_with_occupant(session, row["game_id"])
    return TimeProposal(
        id=row["id"],
        game_id=row["game_id"],
        at=row["at"],
        proposed_by=row["proposed_by"],
        accepted_by=tuple(await repo.time_acceptors(session, row["id"])),
        seated=seated_students(seats),
    )


async def open_time_proposal(session: AsyncSession, game_id: uuid.UUID) -> TimeProposal | None:
    """The Game's open proposal of a time to play (Story 6.19): None when there is none, the
    Game has finished, or the time has passed on the database clock (AD-20)."""
    row = await repo.time_proposal(session, game_id)
    if row is None or row["at"] <= await repo.clock_now(session):
        return None
    game = await repo.get_game(session, game_id)
    if game is None or game["lifecycle"] == Lifecycle.FINISHED:
        return None
    return await _time_proposal(session, row)


async def time_proposal_by_id(session: AsyncSession, proposal_id: uuid.UUID) -> TimeProposal | None:
    """A proposal by its id, for the mail read at send time (Story 6.19); None once replaced.
    The caller judges whether it has passed, on its own clock."""
    row = await repo.time_proposal_by_id(session, proposal_id)
    return None if row is None else await _time_proposal(session, row)


async def game_class_info(
    session: AsyncSession, game_id: uuid.UUID
) -> tuple[uuid.UUID, int, bool] | None:
    """A Class game's Class session, game number and whether it has finished; None for a Game
    with no Class session or none at all."""
    game = await repo.get_game(session, game_id)
    if game is None or game["class_session_id"] is None:
        return None
    return game["class_session_id"], game["game_number"], game["lifecycle"] == Lifecycle.FINISHED


async def own_game(
    session: AsyncSession, user_id: uuid.UUID, game_id: uuid.UUID
) -> StudentGame | None:
    """The Game `game_id` when it is the Student's game, the one `student_game` gives for its
    Class session (joined through `authz.own_seat`); None for any other Game, also one they held a
    Seat in before a move, so another's reads the same as one that does not exist (FR-5)."""
    game = await repo.own_game(session, user_id, game_id)
    if game is None or game["class_session_id"] is None:
        return None
    rules = policy(game["purpose"])
    if rules.played_by_staff:
        # A Lecturer's test Game (Story 6.20): theirs while they hold its Seat; no Class game of
        # the session is ever one (`student_game` leaves it out).
        role = await repo.held_role(session, game_id, user_id)
        if role is None:
            return None
        return StudentGame(
            game_id=game_id,
            class_session_id=game["class_session_id"],
            number=game["game_number"],
            role=role,
            pre_play_gate=rules.pre_play_gate,
            test_game=True,
        )
    found = await student_game(session, user_id, game["class_session_id"])
    if found is None or found.game_id != game_id:
        return None
    return found


@dataclass(frozen=True)
class TestGameRef:
    """A Lecturer's test Game in a Class session (Story 6.20): its id and lifecycle."""

    id: uuid.UUID
    lifecycle: str


async def staff_test_games(
    session: AsyncSession, class_session_id: uuid.UUID, user_id: uuid.UUID
) -> list[TestGameRef]:
    """The test Games the User has played in the Class session, newest first (Story 6.20)."""
    rows = await repo.staff_test_games(session, class_session_id, user_id)
    return [TestGameRef(row["id"], row["lifecycle"]) for row in rows]


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


@dataclass(frozen=True)
class SummarySeat:
    role: str
    occupant_kind: str | None
    user_id: uuid.UUID | None


@dataclass(frozen=True)
class SummaryWait:
    role: str
    user_id: uuid.UUID | None
    since: datetime


@dataclass(frozen=True)
class ClassGameSummary:
    """A Class game's `game_summaries` row (Story 7.1, AD-25): ids only, never a name."""

    game_id: uuid.UUID
    game_number: int | None
    status: GameStatus
    week: int | None
    version: int
    chain_cost: Decimal | None
    wait_started_at: datetime | None
    waiting_for: tuple[SummaryWait, ...]
    """The Student Seats the Game waits for, in chain order."""
    seats: tuple[SummarySeat, ...]
    """Every Seat in chain order with its latest occupant; `occupant_kind` None is free."""


def _user(value: object) -> uuid.UUID | None:
    return None if value is None else uuid.UUID(str(value))


async def class_overview(
    session: AsyncSession, class_session_id: uuid.UUID
) -> list[ClassGameSummary]:
    """The summary rows of the Class session's Games that the Lecturer overview lists (AD-13), by
    game number, read only from `game_summaries` in one query (NFR-3). The caller has checked the
    User may see them and resolves names at read time."""
    return [
        ClassGameSummary(
            game_id=row["game_id"],
            game_number=row["game_number"],
            status=GameStatus(row["status"]),
            week=row["week"],
            version=row["version"],
            chain_cost=row["chain_cost"],
            wait_started_at=row["wait_started_at"],
            waiting_for=tuple(
                SummaryWait(
                    role=wait["role"],
                    user_id=_user(wait["user_id"]),
                    since=datetime.fromisoformat(wait["since"]),
                )
                for wait in row["waiting_for"]
            ),
            seats=tuple(
                SummarySeat(
                    role=seat["role"],
                    occupant_kind=seat["occupant_kind"],
                    user_id=_user(seat["user_id"]),
                )
                for seat in row["occupants"]
            ),
        )
        for row in await repo.class_summaries(session, class_session_id)
    ]


@dataclass(frozen=True)
class ClassGameHead:
    """What the staff's week read checks before it reads any Week (Story 7.2): the Game's Class
    session, whether the Lecturer overview lists its purpose (AD-13) and its `version`."""

    game_id: uuid.UUID
    class_session_id: uuid.UUID | None
    listed: bool
    version: int


@dataclass(frozen=True)
class WeekSeatValues:
    """One Seat in one opened Week as the engine stored it (AD-1): Netto lager is the stored
    inventory minus backlog, `cost` that Week's cost; `order` is None until it is placed."""

    role: str
    net_inventory: int
    order: int | None
    cost: Decimal


@dataclass(frozen=True)
class ClassGameWeeks:
    """Every opened Week of a Game, Week 1 first, its Seats in chain order (Story 7.2)."""

    game_id: uuid.UUID
    version: int
    weeks: tuple[tuple[int, tuple[WeekSeatValues, ...]], ...]


async def class_game_head(session: AsyncSession, game_id: uuid.UUID) -> ClassGameHead | None:
    """The Game's Class session, listing rule and version, or None for no such Game."""
    game = await repo.get_game(session, game_id)
    if game is None:
        return None
    return ClassGameHead(
        game_id=game["id"],
        class_session_id=game["class_session_id"],
        listed=str(game["purpose"]) in purposes_with("lecturer_overview"),
        version=game["version"],
    )


async def class_game_weeks(session: AsyncSession, game_id: uuid.UUID) -> ClassGameWeeks | None:
    """The stored values of every opened Week of the Game (Story 7.2, AD-1, AD-10), read in a
    fixed number of queries: the Game, its Week states and its placed Orders. The finished state
    after the last Week is no Week of its own and is left out. The caller has checked the User."""
    game = await repo.get_game(session, game_id)
    if game is None:
        return None
    placed = await repo.placed_orders(session, game_id)
    orders = {(row["week"], row["role"]): row["order"] for row in placed}
    weeks: list[tuple[int, tuple[WeekSeatValues, ...]]] = []
    for stored in await repo.week_states(session, game_id):
        state = WeekState.model_validate(stored)
        if state.finished:
            continue
        weeks.append(
            (
                state.week,
                tuple(
                    WeekSeatValues(
                        role=str(seat.role),
                        net_inventory=seat.inventory - seat.backlog,
                        order=orders.get((state.week, str(seat.role))),
                        cost=seat.cost,
                    )
                    for seat in state.seats
                ),
            )
        )
    return ClassGameWeeks(game_id=game["id"], version=game["version"], weeks=tuple(weeks))


async def class_played(
    session: AsyncSession, game_ids: Sequence[uuid.UUID], with_orders: bool
) -> list[PlayedGame]:
    """The stored play of the Games for the wall's aggregates (Story 7.4, AD-1): each Game's
    opened Week states and, when `with_orders`, its placed Orders, in two reads whatever the
    number of Games (NFR-3). The caller has checked the User and chosen the Games."""
    states: dict[uuid.UUID, list[WeekState]] = {game_id: [] for game_id in game_ids}
    for row in await repo.week_states_of(session, game_ids):
        states[row["game_id"]].append(WeekState.model_validate(row["state"]))
    orders: dict[uuid.UUID, dict[tuple[int, str], int]] = {game_id: {} for game_id in game_ids}
    if with_orders:
        for row in await repo.placed_orders_of(session, game_ids):
            orders[row["game_id"]][(row["week"], str(row["role"]))] = row["order"]
    return [PlayedGame(states=tuple(states[g]), orders=orders[g]) for g in game_ids]
