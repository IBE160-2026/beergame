"""What other modules may use from `games`. Writes go through `games.commands` only."""

import uuid
from collections.abc import Awaitable, Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import budget as ai_budget
from app.analysis.wall import PlayedGame
from app.engine import GameSettings, WeekState
from app.modules.games import facts as _facts
from app.modules.games import repo, rules
from app.modules.games.batches import create_batch, get_batch
from app.modules.games.checks import (
    finished_game_ids,
    rules_versions_without_package,
    verify_finished,
)
from app.modules.games.insight import (
    GameInsight,
    InsightLink,
    InsightLinkProvider,
    InsightRole,
    InsightSeat,
    InsightWeek,
    game_insight,
    register_insight_links,
    unregister_insight_links,
)
from app.modules.games.marks import seat_mark
from app.modules.games.operations import (
    FallbackCount,
    SessionAiFigures,
    class_session_of,
    session_ai_figures,
)
from app.modules.games.policy import GamePolicy, PurposeNotSupportedError, policy, purposes_with
from app.modules.games.ratings import BelievabilityRefused, believability, rate_believability
from app.modules.games.schemas import (
    Believability,
    DecidedBy,
    DecisionLogRow,
    EndReason,
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
from app.platform import events, jobs
from app.platform.db import get_sessionmaker

__all__ = [
    "Believability",
    "BelievabilityRefused",
    "believability",
    "rate_believability",
    "GameInsight",
    "InsightLink",
    "InsightLinkProvider",
    "InsightRole",
    "InsightSeat",
    "InsightWeek",
    "game_insight",
    "register_insight_links",
    "unregister_insight_links",
    "ClassGameSummary",
    "WaitedSeat",
    "ClassGameWeeks",
    "WeekSeatValues",
    "assigned_students",
    "class_game_head",
    "class_game_students",
    "ClassGameStudents",
    "class_game_weeks",
    "class_played",
    "cost_parts",
    "DecidedBy",
    "DecisionLogRow",
    "EndReason",
    "Fallback",
    "TestDeadlineProvider",
    "past_test_deadline",
    "register_test_deadline",
    "due_test_deadline_closes",
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
    "due_takeovers",
    "overdue_playouts",
    "playout_games",
    "sessions_with_playout_games",
    "stalled_playout_turns",
    "takeover_of",
    "TurnReminderInfo",
    "due_turn_reminders",
    "turn_reminder_of",
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
    "finished_at",
    "FinishedGame",
    "FinishHook",
    "on_game_finished",
    "run_finish_hooks",
    "FinishedSeat",
    "finished_student_seats",
    "demand_series",
    "fact_set",
    "StoredFactSet",
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
    "announce",
    "open_takeover_due",
    "verify_finished",
    "FallbackCount",
    "SessionAiFigures",
    "class_session_of",
    "session_ai_figures",
]


async def unchecked_finished_game_ids(
    session: AsyncSession, limit: int, exclude: Collection[uuid.UUID] = ()
) -> list[uuid.UUID]:
    """At most `limit` finished Games with no finished-game check yet, oldest first (Story
    6.18), but those in `exclude`, read in the caller's session."""
    return await repo.unchecked_finished_game_ids(session, limit, exclude)


async def due_takeovers(now: datetime) -> list[tuple[str, str]]:
    """The sweep's Takeover finder (Story 8.2, AD-9): `(game id, seat id)` of every Student-held
    Seat that `rules.can_take_over` lets the `system` actor take over at `now`, oldest due
    first. `games.commands.takeover` checks again under the Game row lock."""
    found: list[tuple[str, str]] = []
    async with get_sessionmaker()() as session:
        candidates = await repo.due_takeover_turns(session, now)
        by_game: dict[uuid.UUID, list] = {}
        for row in candidates:
            by_game.setdefault(row["game_id"], []).append(row)
        for game_id, rows in by_game.items():
            game = await repo.get_game(session, game_id)
            if game is None or game["settings"] is None:
                continue
            week = rows[0]["week"]
            guided = rules.guided_week(
                policy(game["purpose"]), GameSettings.model_validate(game["settings"]), week
            )
            turns = {
                t["seat_id"]: t for t in await repo.week_turns_with_occupant(session, game_id, week)
            }
            for row in rows:
                turn = turns.get(row["seat_id"])
                if rules.can_take_over(game, turn, "system", now, guided=guided) is None:
                    found.append((str(game_id), str(row["seat_id"])))
    return found


async def due_agreed_times(now: datetime) -> list[str]:
    """The sweep's finder for a Lecturer's agreed Pause time (Story 8.7, AD-9): the paused Games
    whose agreed time lies at or before `now` and that are not marked yet, earliest first.
    `games.commands.reach_agreed_time` checks again under the Game row lock."""
    async with get_sessionmaker()() as session:
        return [str(game_id) for game_id in await repo.due_agreed_times(session, now)]


async def due_insert_times(now: datetime) -> list[tuple[str, str]]:
    """The sweep's finder for insert times passed (Story 8.8, AD-9): (Game id, Seat id) of each
    open-Week turn of a running Game whose insert time lies at or before `now` and that is not
    marked yet, earliest first. `games.commands.announce_insert_time` checks again under the
    Game row lock."""
    async with get_sessionmaker()() as session:
        return [
            (str(game_id), str(seat_id))
            for game_id, seat_id in await repo.due_insert_times(session, now)
        ]


async def due_turn_reminders(now: datetime) -> list[tuple[str, str]]:
    """The sweep's finder for turn reminders (Story 8.13, FR-27, AD-9): (Game id, Seat id) of
    each open-Week turn of a running Game with no Pause in force whose reminder time lies at or
    before `now` and that is not queued yet, earliest first. `games.commands.queue_turn_reminder`
    checks again under the Game row lock."""
    async with get_sessionmaker()() as session:
        return [
            (str(game_id), str(seat_id))
            for game_id, seat_id in await repo.due_turn_reminders(session, now)
        ]


async def due_in_room_ends(now: datetime) -> list[str]:
    """The sweep's finder for «I rommet» marks whose Lab hour has ended (Story 8.11, AD-9): the
    marked Games whose `in_room_until` lies at or before `now`, earliest first.
    `games.commands.end_in_room` checks again under the Game row lock."""
    async with get_sessionmaker()() as session:
        return [str(game_id) for game_id in await repo.due_in_room_ends(session, now)]


async def lab_hour_changed(
    lab_hour_id: uuid.UUID, starts_at: datetime | None, ends_at: datetime | None, now: datetime
) -> int:
    """A Lab hour was moved or (`starts_at`/`ends_at` None) removed (Story 8.11, FR-36): each Game
    marked «I rommet» for it ends its mark when the Lab hour is gone or no longer on at `now`
    (the api's clock Lab hours are judged on), else its mark follows the new end. One
    `games.commands` call per Game, each its own transaction. Returns how many Games changed."""
    # Imported here: `commands` imports this module.
    from app.modules.games import commands

    async with get_sessionmaker()() as session:
        marked = await repo.games_in_room_of(session, lab_hour_id)
    changed = 0
    on = starts_at is not None and ends_at is not None and starts_at <= now < ends_at
    for game_id in marked:
        if on:
            assert ends_at is not None
            done = await commands.mark_in_room(
                str(game_id), None, actor=None, lab_hour_id=lab_hour_id, until=ends_at, now=now
            )
        else:
            done = await commands.end_in_room(str(game_id), actor=None, lab_hour_id=lab_hour_id)
        changed += int(done)
    return changed


async def playout_games(
    session: AsyncSession, class_session_ids: Sequence[uuid.UUID]
) -> list[tuple[str, uuid.UUID]]:
    """The Play deadline playout's Games (Story 8.14, AD-9, AD-13): `(game id, Class session id)`
    of every Game of `class_session_ids` that has neither finished nor begun its playout, where
    `games.policy` has the playout, oldest first; read in the caller's transaction.
    `games.commands.playout` checks again under the Game row lock."""
    return [
        (str(row["id"]), row["class_session_id"])
        for row in await repo.playout_games(session, class_session_ids)
    ]


async def sessions_with_playout_games(session: AsyncSession) -> list[uuid.UUID]:
    """Story 8.14: the Class sessions with a Game the Play deadline playout has still to take
    (`playout_games` lists them), read in the caller's transaction."""
    return await repo.sessions_with_playout_games(session)


async def overdue_playouts(before: datetime) -> list[str]:
    """Story 8.14 (NFR-3): the Games still playing out whose playout began at or before `before`,
    the earliest first."""
    async with get_sessionmaker()() as session:
        return [str(game_id) for game_id in await repo.overdue_playouts(session, before)]


async def stalled_playout_turns() -> list[tuple[str, str]]:
    """Story 8.14 (AD-5, AD-9): `(game id, seat id)` of each open-Week turn of a Game playing out
    with no Order and no live job for it on `llm-batch` (`players.llm_order_key`): its job was
    lost, so the sweep gives the Seat its Order again. Oldest first."""
    # `players` imports `games`: the key is built here as `players.service.llm_order_key` builds it.
    from app.modules.players import service as players

    async with get_sessionmaker()() as session:
        turns = await repo.playout_turns_without_order(session)
        keys = {
            (row["game_id"], row["seat_id"]): tuple(
                players.llm_order_key(
                    str(row["game_id"]), row["week"], str(row["seat_id"]), playout=playout
                )
                for playout in (True, False)
            )
            for row in turns
        }
        # A job of the turn on `ai-orders` (deferred before the playout) is alive too.
        alive = await jobs.live_locks(session, [key for pair in keys.values() for key in pair])
    return [
        (str(game), str(seat))
        for (game, seat), pair in keys.items()
        if not any(key in alive for key in pair)
    ]


async def announce(game_id: str) -> None:
    """Story 8.3 (AD-8): a due Takeover the sweep found but `takeover` refused changes nothing,
    yet the due time has passed; emit `game:<id>` at its current version and, for a Game the
    Lecturer overview lists, `session:<id>`, so open pages read the Game again. Writes nothing."""
    async with get_sessionmaker().begin() as session:
        game = await repo.get_game(session, uuid.UUID(game_id))
        if game is None:
            return
        await events.emit(session, "game", str(game["id"]), game["version"])
        if game["class_session_id"] is not None and policy(game["purpose"]).lecturer_overview:
            await events.emit(session, "session", str(game["class_session_id"]))


async def hand_over_seats_of(user_id: uuid.UUID) -> list[str]:
    """Before a User is erased (Story 15.2, FR-76, AD-2, AD-5): every Seat of a running Game they
    hold, or have a Reclaim of queued, goes through `commands.takeover` with `erasing`, which
    drops the Reclaims and hands a held Seat to an AI player, so no group waits for a deleted
    Student. Idempotent; returns the occupancy row ids written."""
    # Imported here: `commands` imports this module.
    from app.modules.games import commands

    async with get_sessionmaker().begin() as session:
        found = await repo.erasure_seats_of(session, user_id)
    written = []
    for game_id, seat_id in found:
        try:
            occupancy = await commands.takeover(
                str(game_id), str(seat_id), actor="system", erasing=user_id
            )
        except commands.CommandError as error:
            # The Game went to its playout or away since the read: nothing is left to hand over.
            if error.code not in ERASURE_GONE:
                raise
            continue
        if occupancy is not None:
            written.append(occupancy)
    return written


ERASURE_GONE = frozenset({"play_deadline_passed", "game_not_found", "seat_not_found"})
"""Refusals `takeover` raises before its erasure skips, when the Game is playing out or gone."""


async def open_takeover_due(game_id: uuid.UUID, role: str) -> datetime | None:
    """The stored `takeover_due_at` of the Seat with `role` in the Game's open Week; None without
    one. Read for the local dev route that runs a Takeover at its due time (Story 8.3)."""
    async with get_sessionmaker()() as session:
        newest = await repo.newest_week(session, game_id)
        if newest is None:
            return None
        seat_ids = {
            s["id"] for s in await repo.seats_with_occupant(session, game_id) if s["role"] == role
        }
        for turn in await repo.week_turns_with_occupant(session, game_id, newest["week"]):
            if turn["seat_id"] in seat_ids:
                return turn["takeover_due_at"]
    return None


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


async def startable_class_games(
    session: AsyncSession, class_session_id: uuid.UUID
) -> list[uuid.UUID]:
    """The Class session's Games a Lecturer may start (Story 8.10, FR-22), by game number: not
    started, with their settings snapshot, which the lock gives them (Story 5.12, the readiness
    Story 6.5 uses for the Student's button), and with a Student in a Seat: a game of AI players
    alone would play itself out at the start, and AI players never play a Class game on their own
    before the Play deadline (Story 8.14 plays those out). Two reads."""
    return [
        game.id
        for game in await class_games(session, class_session_id)
        if game.lifecycle == Lifecycle.NOT_STARTED
        and game.has_snapshot
        and any(seat.occupant_kind == OccupantKind.STUDENT for seat in game.seats)
    ]


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
    replay: bool = False
    """Whether it is the Student's own round outside the Class games: a Game of the Class session
    without a number that no Lecturer plays, the Replay (Story 10.4). Never `student_game`."""
    projection: bool = False
    """Whether the play screen draws the projection (`games.policy`, Story 10.4, UX-DR19)."""


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


@dataclass(frozen=True)
class GameStudent:
    """A Student whose game (`student_game`) a Class game is (Story 9.11): their Seat's Role and
    how many of its Orders a Student decided (`decided_by = student`)."""

    user_id: uuid.UUID
    role: str
    student_orders: int


async def game_students(session: AsyncSession, game_id: uuid.UUID) -> list[GameStudent]:
    """The Students whose game the Class game `game_id` is, through `student_game` (so a Student
    moved to another game since is left out), with their own-Order counts, in the caller's
    transaction; empty for a Game with no Class session."""
    game = await repo.get_game(session, game_id)
    if game is None or game["class_session_id"] is None:
        return []
    orders = await repo.student_orders_by_role(session, game_id)
    found = []
    for user_id in await repo.named_students(session, game_id):
        theirs = await student_game(session, user_id, game["class_session_id"])
        if theirs is not None and theirs.game_id == game_id:
            found.append(GameStudent(user_id, theirs.role, orders.get(theirs.role, 0)))
    return sorted(found, key=lambda each: str(each.user_id))


PlayStatusName = Literal["not_ready", "ready", "running", "finished"]


@dataclass(frozen=True)
class PlayStatus:
    """Where a Game stands for its Students (Story 6.5): `not_ready` before its snapshot,
    `ready` to start, `running` (also while it plays out) with its open Week, or `finished`.
    Never the number of Weeks (FR-14)."""

    status: PlayStatusName
    week: int | None
    played_out: bool = False
    """The Play deadline playout took the Game over (Story 8.14): it plays out, or ended so."""
    end_reason: EndReason | None = None
    """Story 10.6: with `finished`, why the Game ended without its last Week (`close`): it is then
    not finished in any result's sense, and no screen may show it as such."""


async def play_status(session: AsyncSession, game_id: uuid.UUID) -> PlayStatus:
    """The Game's `PlayStatus`, read in the caller's transaction."""
    game = await repo.get_game(session, game_id)
    if game is None:
        raise LookupError(f"no Game {game_id}")
    lifecycle = game["lifecycle"]
    played_out = game["played_out_at"] is not None
    if lifecycle == Lifecycle.NOT_STARTED:
        return PlayStatus("ready" if game["settings"] is not None else "not_ready", None)
    if lifecycle == Lifecycle.FINISHED:
        reason = game["end_reason"]
        return PlayStatus(
            "finished",
            None,
            played_out,
            end_reason=EndReason(reason) if reason is not None else None,
        )
    if lifecycle in (Lifecycle.RUNNING, Lifecycle.PLAYING_OUT):
        return PlayStatus("running", await repo.open_week(session, game_id), played_out)
    raise ValueError(f"unknown lifecycle {lifecycle!r}")


async def finished_at(session: AsyncSession, game_id: uuid.UUID) -> datetime | None:
    """When the Game finished (its finished Week state was stored, database time), read in the
    caller's transaction; None before then (Story 9.12)."""
    return await repo.finished_at(session, game_id)


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


@dataclass(frozen=True)
class TakeoverInfo:
    """A Takeover as its notice mail tells it (Story 8.2): the Class game, the Seat's Role and the
    Student whose Seat it was (None if none held it before). Ids only (AD-14)."""

    game_id: uuid.UUID
    class_session_id: uuid.UUID
    number: int | None
    role: str
    student: uuid.UUID | None


async def takeover_of(session: AsyncSession, occupancy_id: uuid.UUID) -> TakeoverInfo | None:
    """The Takeover whose occupancy row is `occupancy_id`, read in the caller's session; None for
    an id that is no Takeover or a Game with no Class session."""
    row = await repo.takeover_row(session, occupancy_id)
    if row is None:
        return None
    game = await repo.get_game(session, row["game_id"])
    if game is None or game["class_session_id"] is None:
        return None
    return TakeoverInfo(
        game_id=row["game_id"],
        class_session_id=game["class_session_id"],
        number=game["game_number"],
        role=row["role"],
        student=row["student"],
    )


@dataclass(frozen=True)
class TurnReminderInfo:
    """A turn reminder as its mail tells it (Story 8.13): the Class game and the Seat's Role. Ids
    only (AD-14); never the Week."""

    game_id: uuid.UUID
    class_session_id: uuid.UUID
    number: int | None
    role: str


async def turn_reminder_of(
    session: AsyncSession, turn_id: uuid.UUID, user_id: uuid.UUID
) -> TurnReminderInfo | None:
    """The turn `turn_id` while the game still waits for `user_id` on it, read in the caller's
    session (Story 8.13, FR-27): the turn is in the open Week of a running Class game whose policy
    has inactivity rules, `user_id` holds its Seat that Week and the game waits for it
    (`rules.waited_for`). None otherwise: the Student ordered, an AI player took the Seat, the
    Week moved on or the game no longer runs, so the mail leaves it out. A Pause that began after
    the reminder was queued keeps it: the game still cannot go on without the Student's Order, and
    the turn is marked, so it would get no other reminder that Week."""
    row = await repo.turn_with_role(session, turn_id)
    if row is None:
        return None
    game = await repo.get_game(session, row["game_id"])
    if (
        game is None
        or game["class_session_id"] is None
        or game["settings"] is None
        or game["lifecycle"] != Lifecycle.RUNNING
        or not policy(game["purpose"]).inactivity_takeover
    ):
        return None
    week = await repo.open_week(session, game["id"])
    if week != row["week"]:
        return None
    turn = next(
        (
            t
            for t in await repo.week_turns_with_occupant(session, game["id"], week)
            if t["id"] == turn_id
        ),
        None,
    )
    guided = rules.guided_week(
        policy(game["purpose"]), GameSettings.model_validate(game["settings"]), week
    )
    if turn is None or turn["user_id"] != user_id or not rules.waited_for(turn, guided=guided):
        return None
    return TurnReminderInfo(
        game_id=game["id"],
        class_session_id=game["class_session_id"],
        number=game["game_number"],
        role=row["role"],
    )


def _own_round(rules: GamePolicy) -> bool:
    """Whether Games of this policy are a Student's own round outside the Class games: of a Class
    session, without a number, and no Lecturer plays it — the Replay (Stories 10.4, 10.5)."""
    return rules.class_session_game and not rules.game_number and not rules.played_by_staff


async def own_game(
    session: AsyncSession, user_id: uuid.UUID, game_id: uuid.UUID
) -> StudentGame | None:
    """The Game `game_id` when it is the Student's game, the one `student_game` gives for its
    Class session (joined through `authz.own_seat`); None for any other Game, also one they held a
    Seat in before a move, so another's reads the same as one that does not exist (FR-5)."""
    game = await repo.own_game(session, user_id, game_id)
    if game is None or game["class_session_id"] is None:
        return None
    game_policy = policy(game["purpose"])
    if game_policy.played_by_staff or _own_round(game_policy):
        # A Lecturer's test Game (Story 6.20) or a Student's Replay (Story 10.4): theirs while they
        # hold its Seat; no Class game of the session is ever one (`student_game` leaves it out).
        role = await repo.held_role(session, game_id, user_id)
        if role is None:
            return None
        return StudentGame(
            game_id=game_id,
            class_session_id=game["class_session_id"],
            number=game["game_number"],
            role=role,
            pre_play_gate=game_policy.pre_play_gate,
            test_game=game_policy.played_by_staff,
            replay=_own_round(game_policy),
            projection=game_policy.projection,
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
        end_reason=game["end_reason"],
    )


async def demand_series(game_id: str) -> tuple[int, ...] | None:
    """The Game's stored customer demand series, Week 1 first (FR-13, AD-4), or None when there
    is no such Game or it has no snapshot yet. Only for reveals after the Explanation (Story 9.4,
    FR-14): no Seat state carries it."""
    try:
        game_uuid = uuid.UUID(game_id)
    except ValueError, TypeError, AttributeError:
        return None
    async with get_sessionmaker()() as session:
        game = await repo.get_game(session, game_uuid)
    if game is None or game["demand_series"] is None:
        return None
    return tuple(int(value) for value in game["demand_series"])


StoredFactSet = _facts.StoredFactSet


async def fact_set(game_id: str, seat: str) -> StoredFactSet:
    """The stored facts set of the Seat (its Role or id) of the finished Game (Story 9.1, AD-7):
    built and stored by the first call, as stored after that. For readers outside `games` (the
    Debrief, Story 9.5). Raises `ViewError` as `games.facts.get_or_create` does."""
    return await _facts.get_or_create(game_id, seat)


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
        # The frozen config travels with the scope, so the gateway resolves it (Epic 8 close-out:
        # without it every Class game LLM Order was the `provider_error` fallback).
        return ai_budget.BudgetScope.class_session(
            class_session_id,
            effort_level=runtime.effort_level,
            model_config_id=runtime.model_config_id,
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


# Story 10.6: a Student's Test deadline, as `sessions` reads it. `sessions` imports `games`, so it
# registers its reader here instead of `games` importing it (AD-25), as the finish hooks do.

type TestDeadlineProvider = Callable[
    [AsyncSession, uuid.UUID, uuid.UUID], Awaitable[datetime | None]
]
"""`(session, user_id, class_session_id)` → `sessions.service.effective_test_deadline` of the
Student in the Class session, or None (no such session, or no Test deadline)."""

_test_deadline: list[TestDeadlineProvider] = []


def register_test_deadline(provider: TestDeadlineProvider) -> None:
    """`sessions.service` registers its one reader at import; another is refused."""
    if _test_deadline and _test_deadline[0] is not provider:
        raise ValueError("a Test deadline provider is registered already")
    _test_deadline[:] = [provider]


async def past_test_deadline(session: AsyncSession, game: Mapping[str, Any], at: datetime) -> bool:
    """Whether the Game's Test deadline has passed at `at` (Story 10.6, FR-18): the Game belongs
    to a Class session and the deadline of every Student its occupancy history names is set and
    no later than `at`. False while no reader is registered, so nothing is judged without one.
    `at` is the app's clock (`auth.utcnow()`, or the sweep's `now`), the one the deadline is set
    and judged on elsewhere (`replay.start`), never the database clock (Issue #63)."""
    if not _test_deadline or game["class_session_id"] is None:
        return False
    students = await repo.named_students(session, game["id"])
    if not students:
        return False
    for user_id in students:
        deadline = await _test_deadline[0](session, user_id, game["class_session_id"])
        if deadline is None or deadline > at:
            return False
    return True


async def due_test_deadline_closes(now: datetime) -> list[str]:
    """The sweep's finder for `games.close_at_test_deadline` (Story 10.6, AD-9): every Game of a
    purpose whose policy closes it at the Test deadline (`closes_at_test_deadline`), not finished,
    whose Test deadline has passed at `now`, oldest first. Ids only."""
    async with get_sessionmaker()() as session:
        rows = await repo.unfinished_games(session, purposes_with("closes_at_test_deadline"))
        return [str(row["id"]) for row in rows if await past_test_deadline(session, row, now)]


# The finish hooks (Story 9.14, AD-9): the pattern of the lock's pin providers (Story 5.11).


@dataclass(frozen=True)
class FinishedGame:
    """What a finish hook is told about the Game that has just finished, ids only: its purpose,
    its Class session (None outside one), its snapshot's pins and the Seats a Student ever held,
    from the occupancy history (so one whose Seat an AI player took over counts too)."""

    game_id: uuid.UUID
    purpose: str
    class_session_id: uuid.UUID | None
    pins: Mapping[str, Any]
    student_seat_ids: tuple[uuid.UUID, ...]


type FinishHook = Callable[[AsyncSession, FinishedGame], Awaitable[None]]
"""`(session, finished)`: runs inside the finishing command's transaction."""

_finish_hooks: dict[str, FinishHook] = {}


def on_game_finished(name: str, hook: FinishHook) -> None:
    """Run `hook` inside the transaction that finishes every Game from now on (Story 9.14): the
    Debrief defers its narration jobs there, so `games` imports nothing from the module that
    registers. Registering the same hook again changes nothing; another under a taken name is
    refused."""
    known = _finish_hooks.get(name)
    if known is not None and known is not hook:
        raise ValueError(f"a finish hook named {name!r} is registered already")
    _finish_hooks[name] = hook


async def run_finish_hooks(session: AsyncSession, game_id: uuid.UUID) -> None:
    """Called by `games.commands.finish` once the Game is finished, in its transaction: every
    registered hook, by name. A hook's exception rolls the finish back, so hooks only defer."""
    if not _finish_hooks:
        return
    game = await repo.get_game(session, game_id)
    if game is None:
        return
    runtime = game["session_runtime"] or {}
    seats = []
    for row in await repo.occupancy_history(session, game_id):
        if row["occupant_kind"] == OccupantKind.STUDENT and row["seat_id"] not in seats:
            seats.append(row["seat_id"])
    finished = FinishedGame(
        game_id=game_id,
        purpose=game["purpose"],
        class_session_id=game["class_session_id"],
        pins=runtime.get("pins") or {},
        student_seat_ids=tuple(seats),
    )
    for _, hook in sorted(_finish_hooks.items()):
        await hook(session, finished)


@dataclass(frozen=True)
class FinishedSeat:
    """A Seat a Student held in a finished Class game (Story 9.14): ids, the snapshot's pins and
    the Seat's stored facts set id (None before one is stored)."""

    game_id: uuid.UUID
    seat_id: uuid.UUID
    pins: Mapping[str, Any]
    fact_set_id: uuid.UUID | None


async def finished_student_seats(
    finished_after: datetime, finished_before: datetime
) -> list[FinishedSeat]:
    """Each Seat a Student ever held in a Class game that finished after `finished_after` and at
    or before `finished_before` (database time), oldest finish first: for the Debrief's sweep,
    which defers a lost narration job again."""
    async with get_sessionmaker()() as session:
        rows = await repo.finished_student_seats(session, finished_after, finished_before)
    return [
        FinishedSeat(row["game_id"], row["seat_id"], row["pins"] or {}, row["fact_set_id"])
        for row in rows
    ]


@dataclass(frozen=True)
class SummarySeat:
    role: str
    occupant_kind: str | None
    user_id: uuid.UUID | None
    reason: str | None = None
    """The latest occupancy row's reason (Story 8.3); None for a free Seat or an older row."""
    actor_user_id: uuid.UUID | None = None
    """Who triggered that row (Story 8.5): the staff member or Student of a Takeover by a person;
    None otherwise or in an older row."""


@dataclass(frozen=True)
class SummaryWait:
    role: str
    user_id: uuid.UUID | None
    since: datetime
    takeover_due_at: datetime | None = None
    """The Seat's own stored Takeover due time (Story 8.3); None without one or in an older row,
    written before the Seat's due time was stored there."""


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
    takeover_due_at: datetime | None = None
    """The nearest stored `takeover_due_at` of `waiting_for` (Story 8.1); None without one."""
    paused_at: datetime | None = None
    """Since when the Pause in force runs (Story 8.6); None when the game is not paused."""
    paused_by: uuid.UUID | None = None
    """Who set it, by id (Story 8.6)."""
    in_room_until: datetime | None = None
    """Until when the game is marked «I rommet» (Story 8.11); None when it is not."""
    resume_at: datetime | None = None
    """The Lecturer's agreed time of the Pause in force (Story 8.7); None without one."""


def _user(value: object) -> uuid.UUID | None:
    return None if value is None else uuid.UUID(str(value))


def _moment(value: object) -> datetime | None:
    return None if value is None else datetime.fromisoformat(str(value))


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
            takeover_due_at=row["takeover_due_at"],
            paused_at=row["paused_at"],
            paused_by=row["paused_by"],
            in_room_until=row["in_room_until"],
            resume_at=row["resume_at"],
            waiting_for=tuple(
                SummaryWait(
                    role=wait["role"],
                    user_id=_user(wait["user_id"]),
                    since=datetime.fromisoformat(wait["since"]),
                    takeover_due_at=_moment(wait.get("takeover_due_at")),
                )
                for wait in row["waiting_for"]
            ),
            seats=tuple(
                SummarySeat(
                    role=seat["role"],
                    occupant_kind=seat["occupant_kind"],
                    user_id=_user(seat["user_id"]),
                    reason=seat.get("reason"),
                    actor_user_id=_user(seat.get("actor_user_id")),
                )
                for seat in row["occupants"]
            ),
        )
        for row in await repo.class_summaries(session, class_session_id)
    ]


async def cost_parts(
    session: AsyncSession, game_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, dict[str, tuple[Decimal, Decimal]]]:
    """Each Game's Total cost per Role split into (lager, restordre) (Story 7.6, FR-39), for
    finished Games the caller has chosen: what the Game's result (`views.chain_result`) shows, in
    one read whatever their number (NFR-3). A Game with no Week is left out."""
    found: dict[uuid.UUID, dict[str, tuple[Decimal, Decimal]]] = {}
    for row in await repo.cost_parts_of(session, game_ids):
        found.setdefault(row["game_id"], {})[row["role"]] = (
            row["holding_cost"],
            row["backorder_cost"],
        )
    return found


@dataclass(frozen=True)
class ClassGameHead:
    """What the staff's week read checks before it reads any Week (Story 7.2): the Game's Class
    session, whether the Lecturer overview lists its purpose (AD-13) and its `version`."""

    game_id: uuid.UUID
    class_session_id: uuid.UUID | None
    listed: bool
    version: int
    insight: bool = False
    """Whether its Class's staff open it on Spillinnsikt (`games.policy` `staff_insight`)."""
    replay: bool = False
    """Whether it is a Student's Replay, labelled so on Spillinnsikt (Story 10.5)."""


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


@dataclass(frozen=True)
class WaitedSeat:
    """A Seat a Class game waits for (Story 8.12, FR-37): its Game, the Seat, its Student and since
    when, as the game's `game_summaries` row lists it (`rules.waited_for`)."""

    game_id: uuid.UUID
    game_number: int | None
    seat_id: uuid.UUID
    role: str
    user_id: uuid.UUID | None
    since: datetime


async def waited_for_seats(
    session: AsyncSession, class_session_id: uuid.UUID, game_id: uuid.UUID | None = None
) -> list[WaitedSeat]:
    """The Seats the Class session's games wait for now (Story 8.12), or one game's (`game_id`),
    by game number and chain order: the `waiting_for` of the `waiting` summary rows, the same rows
    the Oversikt's «Venter» count reads, so the two never disagree. A paused game waits for no one
    (its status is `paused`). Two reads."""
    games = [
        game
        for game in await class_overview(session, class_session_id)
        if game.status is GameStatus.WAITING and (game_id is None or game.game_id == game_id)
    ]
    if not games:
        return []
    seat_ids = {
        (row["game_id"], row["role"]): row["id"]
        for row in await repo.class_session_seat_ids(session, class_session_id)
    }
    return [
        WaitedSeat(
            game_id=game.game_id,
            game_number=game.game_number,
            seat_id=seat_ids[(game.game_id, wait.role)],
            role=wait.role,
            user_id=wait.user_id,
            since=wait.since,
        )
        for game in games
        for wait in game.waiting_for
        if (game.game_id, wait.role) in seat_ids
    ]


async def class_seat_games(
    session: AsyncSession, class_session_id: uuid.UUID, seat_ids: Collection[uuid.UUID]
) -> dict[uuid.UUID, uuid.UUID]:
    """The Game of each of `seat_ids` that is a Seat of the Class session's listed Games (Story
    8.12); any other id is left out. One read."""
    wanted = set(seat_ids)
    return {
        row["id"]: row["game_id"]
        for row in await repo.class_session_seat_ids(session, class_session_id)
        if row["id"] in wanted
    }


async def class_game_head(session: AsyncSession, game_id: uuid.UUID) -> ClassGameHead | None:
    """The Game's Class session, listing rule and version, or None for no such Game."""
    game = await repo.get_game(session, game_id)
    if game is None:
        return None
    rules = policy(game["purpose"])
    return ClassGameHead(
        game_id=game["id"],
        class_session_id=game["class_session_id"],
        listed=rules.lecturer_overview,
        version=game["version"],
        insight=rules.staff_insight,
        replay=_own_round(rules),
    )


@dataclass(frozen=True)
class ClassGameStudents:
    """A Class game as a Message to it sees it (Story 7.9): its Class session, number, whether
    the Lecturer overview lists it (AD-13), and its Students."""

    game_id: uuid.UUID
    class_session_id: uuid.UUID | None
    game_number: int | None
    listed: bool
    students: tuple[uuid.UUID, ...]
    """Per Seat in chain order its Student now, or, where an AI player holds it now, the Student
    who held it last. A free row (a Student moved away before the start) ends a Student's claim,
    so a moved Student belongs to the game they were moved to."""


def assigned_students(rows) -> tuple[uuid.UUID, ...]:
    """`ClassGameStudents.students` from `repo.occupancy_history` rows (one rule, tested)."""
    held: dict[uuid.UUID, uuid.UUID | None] = {}
    for row in rows:
        if row["occupant_kind"] == OccupantKind.STUDENT and row["user_id"] is not None:
            held[row["seat_id"]] = row["user_id"]
        elif row["occupant_kind"] is None:
            held[row["seat_id"]] = None
        else:
            held.setdefault(row["seat_id"], None)
    found: list[uuid.UUID] = []
    for user_id in held.values():
        if user_id is not None and user_id not in found:
            found.append(user_id)
    return tuple(found)


async def class_game_students(
    session: AsyncSession, game_id: uuid.UUID
) -> ClassGameStudents | None:
    """The Game with its Students for a Message (Story 7.9), or None for no such Game. Read in the
    caller's transaction; the caller checks the User and the Class session."""
    game = await repo.get_game(session, game_id)
    if game is None:
        return None
    return ClassGameStudents(
        game_id=game["id"],
        class_session_id=game["class_session_id"],
        game_number=game["game_number"],
        listed=str(game["purpose"]) in purposes_with("lecturer_overview"),
        students=assigned_students(await repo.occupancy_history(session, game_id)),
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


ExportRows = tuple[tuple[str, ...], list[tuple[Any, ...]]]
"""A section of the pseudonymised export: its column names and its rows (Story 15.4)."""


async def export_decision_log(
    session: AsyncSession,
    class_session_ids: Collection[uuid.UUID],
    in_scope: Any,
    students: Any,
) -> ExportRows:
    """The Decision log of the Class sessions for the pseudonymised export (Story 15.4, FR-67,
    FR-71, AD-15): every `seat_week` column, the Role, the game number and, in `student`, the User
    id of the Student who held the Seat that Week. `in_scope` and `students` are the
    `reports.scope` subqueries (AD-13); the caller replaces `student` by a pseudonym."""
    rows = await repo.decision_log_rows(session, class_session_ids, in_scope, students)
    columns = repo.DECISION_LOG_COLUMNS
    return columns, [tuple(row[name] for name in columns) for row in rows]
