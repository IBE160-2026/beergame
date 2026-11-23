"""The Oversikt of a Class session (Story 7.1, FR-39, AD-25): every Class game with its status,
whom it waits for and its chain cost, read from `games`' `game_summaries` only, with the Students'
names resolved now (AD-12, AD-14). A fixed number of queries whatever the number of Games (NFR-3).
"""

import asyncio
import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

import structlog

from app.analysis.class_cost import FinishedGame, class_cost
from app.analysis.wall import Cells, wall_aggregates
from app.engine.settings import ROLES, Role
from app.modules.classes import service as classes
from app.modules.games import commands as games_commands
from app.modules.games import service as games_service
from app.modules.games.service import ClassGameSummary, GameStatus, SeatMark
from app.modules.sessions import repo
from app.modules.sessions.schemas import (
    ClassCostOut,
    ClassOverviewOut,
    DemandWeekOut,
    FilledSeatsOut,
    FunnelStageOut,
    GameInsightOut,
    GameWeekOut,
    GameWeeksOut,
    InsightInRoomOut,
    InsightLinkOut,
    InsightPauseOut,
    InsightRoleOut,
    InsightSeatOut,
    InsightWeekOut,
    OverviewAiOut,
    OverviewAlertOut,
    OverviewCountsOut,
    OverviewGameOut,
    OverviewSeatOut,
    OverviewWaitOut,
    RoleCostOut,
    SkippedSeatOut,
    StartedGamesOut,
    StartGamesOut,
    WaitedForSeatsOut,
    WaitedGameOut,
    WaitedSeatOut,
    WaitingSeatOut,
    WallAggregatesOut,
    WallCells,
    WallStatus,
    WallWeekOut,
    WeekSeatOut,
)
from app.modules.sessions.service import (
    _class_for,
    current_lab_hour,
    funnel_of,
    is_locked,
    time_factors,
)
from app.platform import auth, authz
from app.platform.db import get_sessionmaker

log = structlog.get_logger(__name__)

BATCH_START_CONCURRENCY = 4
"""How many Games «Start 12 spill» starts at once (Story 8.10): below the pool size (10)."""

BATCH_FILL_CONCURRENCY = 4
"""How many Games «Sett inn 9 KI-spillere» fills at once (Story 8.12); the Seats of one Game go
one after another, each its own command on the Game row lock."""

__all__ = [
    "WallFilter",
    "class_overview",
    "etag_of",
    "game_weeks",
    "game_weeks_etag",
    "game_insight",
    "insight_etag",
    "readable_game",
    "take_over_seat",
    "TakeoverRefused",
    "PauseRefused",
    "pause_game",
    "set_agreed_time",
    "end_pause",
    "StartRefused",
    "InRoomRefused",
    "mark_in_room",
    "end_in_room",
    "start_game",
    "start_games",
    "start_games_page",
    "fill_waited_for",
    "waited_for_page",
    "wall_aggregates_out",
    "wall_games",
]


async def class_overview(user: authz.Principal, session_id: uuid.UUID) -> ClassOverviewOut | None:
    """The Oversikt, or None when the User may not see it or the Class session does not exist:
    one answer for both (FR-5, NFR-7). Its Lecturers and Assistant lecturers see it."""
    async with get_sessionmaker()() as s:
        row = await repo.session_row(s, session_id)
    if row is None:
        return None
    found = await _class_for(user, row["class_id"], "class_sessions.overview")
    if found is None:
        return None
    async with get_sessionmaker()() as s:
        number = await repo.number_of(s, session_id, row["class_id"])
        games = await games_service.class_overview(s, session_id)
        students = sorted(
            {seat.user_id for game in games for seat in game.seats if seat.user_id is not None}
            | {wait.user_id for game in games for wait in game.waiting_for if wait.user_id},
            key=str,
        )
        names = (
            await classes.student_names(row["class_id"], students, session=s) if students else {}
        )
        by = await classes.actor_names(s, row["class_id"], _actors(games))
        now = await games_service.database_now(s)
        # The Start-date lock on the api clock, as the Klasseøkt reads it (`get_session`).
        before_start = not is_locked(row)
        finished = [g for g in games if g.status is GameStatus.FINISHED]
        parts = (
            await games_service.cost_parts(s, [g.game_id for g in finished])
            if finished and not before_start
            else {}
        )
        # Story 13.1: the Trakt over the reporting Students (`reports.scope`), through
        # `reports.service.funnel`; `progress` counts their steps and looks up no one.
        trakt = await funnel_of(s, session_id)
        # «Start spill som ikke har startet (12)» (Story 8.10): for a Lecturer, after the lock.
        startable = (
            len(await games_service.startable_class_games(s, session_id))
            if not before_start and authz.can(user, "games.start", found)
            else 0
        )
        # «Sett inn KI-spiller i alle seter som blir ventet på (9)» (Story 8.12): for a Lecturer,
        # the waiting games' `waiting_for` less the Seats with Tilrettelegging, the rows the fill
        # page lists; one read whatever the number of games.
        fillable = (
            await _fillable(s, session_id, games)
            if authz.can(user, "games.fill_seats", found)
            else 0
        )
    counts = {status: 0 for status in GameStatus}
    for game in games:
        counts[game.status] += 1
    return ClassOverviewOut(
        items=[_game_out(game, names, before_start, by) for game in games],
        next_cursor=None,
        counts=OverviewCountsOut(
            waiting=counts[GameStatus.WAITING],
            # «15 pågår (herav 2 pauset)» (Story 8.6, EXPERIENCE.md → Oversikt Live).
            running=counts[GameStatus.RUNNING] + counts[GameStatus.PAUSED],
            paused=counts[GameStatus.PAUSED],
            not_started=counts[GameStatus.NOT_STARTED],
            finished=counts[GameStatus.FINISHED],
        ),
        server_now=now,
        before_start=before_start,
        start_at=row["start_at"],
        next_change_at=row["start_at"] if before_start else _next_due(games, now),
        ai=_ai_out(games),
        cost=None if before_start else _cost_out(finished, parts),
        funnel=[FunnelStageOut(stage="registered", count=trakt.registered)]
        + [FunnelStageOut(stage=step.value, count=count) for step, count in trakt.steps],
        alert=None if before_start else _alert(games, names),
        can_pause=authz.can(user, "games.pause", found),
        play_deadline=row["play_deadline"],
        startable=startable,
        fillable=fillable,
        class_id=found.id,
        class_name=found.name,
        session_number=number,
        # Never for a Control test Class session, which no report counts (AD-27).
        class_report=authz.can(user, "class_report.read", found) and not found.control_test,
    )


def _next_due(games: list[ClassGameSummary], now: datetime) -> datetime | None:
    """The nearest stored Takeover due time after `now` of any waited-for Seat of a waiting Class
    game (Stories 8.1 and 8.9, AD-8, AD-20): the Oversikt is read again then. Each Seat's own due
    time counts, not only the game's earliest: with Tilrettelegging the Seats of one game differ,
    and once the earliest has passed a later one still lies ahead. None without one."""
    due = [
        at
        for g in games
        if g.status is GameStatus.WAITING
        for at in (g.takeover_due_at, *(wait.takeover_due_at for wait in g.waiting_for))
        if at is not None and at > now
    ]
    return min(due, default=None)


def _alert(games: list[ClassGameSummary], names: dict[uuid.UUID, str]) -> OverviewAlertOut | None:
    """The Varselbånd's game (Stories 7.11 and 8.3, FR-39, AD-10, AD-25): of the waiting Class
    games with a waited-for Seat, the one an AI player takes over first, by the stored
    `takeover_due_at`; games without one come after, by Story 7.11's rule (the wait that started
    first, its `wait_started_at` else its earliest Seat). Ties go to the lowest game number. Within
    the game the Seat whose own due time comes first (Story 8.9's factor makes them differ), then
    the one waited for longest, then chain order. A due time already passed still counts: the
    sweep acts on it within the minute. The web app never picks it. `names` holds the Students
    still in the Class: anyone else is named by Role, with no `user_id` to write to."""
    waiting = [g for g in games if g.status is GameStatus.WAITING and g.waiting_for]
    if not waiting:
        return None

    def started(game: ClassGameSummary):
        return game.wait_started_at or min(wait.since for wait in game.waiting_for)

    game = min(
        waiting,
        key=lambda g: (
            g.takeover_due_at is None,
            g.takeover_due_at or started(g),
            g.game_number is None,
            g.game_number or 0,
            str(g.game_id),
        ),
    )
    # `min` keeps the first of equal keys: `waiting_for` is in chain order. A row written before
    # the Seats' own due times (Story 8.3) has none: the longest wait then names the Seat.
    wait = min(
        game.waiting_for,
        key=lambda w: (
            w.takeover_due_at is None,
            w.takeover_due_at or w.since,
            w.since,
        ),
    )
    name = names.get(wait.user_id) if wait.user_id else None
    return OverviewAlertOut(
        game_id=game.game_id,
        game_number=game.game_number,
        role=Role(wait.role),
        name=name,
        user_id=wait.user_id if name is not None else None,
        since=wait.since,
        takeover_due_at=wait.takeover_due_at or game.takeover_due_at,
    )


def _actors(games: list[ClassGameSummary]) -> list[uuid.UUID]:
    """The people who put an AI player in a Seat now held by one (Story 8.5), and who set each
    Pause in force (Story 8.6)."""
    return sorted(
        {
            seat.actor_user_id
            for game in games
            for seat in game.seats
            if seat.actor_user_id is not None and _is_ai(seat)
        }
        | {game.paused_by for game in games if game.paused_by is not None},
        key=str,
    )


def _mark_by(kind: str | None, actor: uuid.UUID | None, by: dict[uuid.UUID, str]) -> str | None:
    """Who put the AI player holding the Seat in, by name now (Story 8.5, FR-37); None for a
    Student or free Seat, a Takeover by no person, or someone no longer of the Class."""
    if kind is None or kind == games_service.OccupantKind.STUDENT or actor is None:
        return None
    return by.get(actor)


def _mark(kind: str | None, reason: str | None) -> SeatMark | None:
    """An AI-held Seat's mark from the one AD-15 mapping (Story 8.3, FR-34); None otherwise."""
    if kind is None or kind == games_service.OccupantKind.STUDENT:
        return None
    return games_service.seat_mark(None, None, kind, reason)


def _is_ai(seat: games_service.SummarySeat) -> bool:
    kind = seat.occupant_kind
    return kind is not None and kind != games_service.OccupantKind.STUDENT


def _ai_out(games: list[ClassGameSummary]) -> OverviewAiOut:
    """The Seats an AI player holds now and the Class games with one (UX-DR69)."""
    held = [sum(1 for seat in game.seats if _is_ai(seat)) for game in games]
    return OverviewAiOut(seats=sum(held), games=sum(1 for n in held if n > 0))


def _cost_out(
    finished: list[ClassGameSummary],
    parts: dict[uuid.UUID, dict[str, tuple[Decimal, Decimal]]],
) -> ClassCostOut | None:
    """«Klassens kostnad» over the finished Class games the overview lists, which leaves out
    lecturer test and simulation Games (AD-13); None while none has finished."""
    found = class_cost(
        [
            FinishedGame(chain_cost=g.chain_cost, roles=parts.get(g.game_id, {}))
            for g in finished
            if g.chain_cost is not None
        ],
        [str(role) for role in ROLES],
    )
    if found is None:
        return None
    return ClassCostOut(
        games=found.games,
        median=found.median,
        lower_quartile=found.lower_quartile,
        upper_quartile=found.upper_quartile,
        holding_cost=found.holding_cost,
        backorder_cost=found.backorder_cost,
        roles=[
            RoleCostOut(
                role=Role(mean.role),
                holding_cost=mean.holding_cost,
                backorder_cost=mean.backorder_cost,
                total_cost=mean.total_cost,
            )
            for mean in found.roles
        ],
    )


def _game_out(
    game: ClassGameSummary,
    names: dict[uuid.UUID, str],
    before_start: bool,
    by: dict[uuid.UUID, str] | None = None,
) -> OverviewGameOut:
    seats = []
    for seat in reversed(game.seats):  # Fabrikk first (UX-DR73)
        if seat.occupant_kind is None:
            holder, name = "free", None
        elif seat.occupant_kind == games_service.OccupantKind.STUDENT:
            holder, name = "student", names.get(seat.user_id) if seat.user_id else None
        else:
            holder, name = "ai", None
        seats.append(
            OverviewSeatOut(
                role=seat.role,
                holder=holder,
                name=name,
                mark=_mark(seat.occupant_kind, seat.reason),
                mark_by=_mark_by(seat.occupant_kind, seat.actor_user_id, by or {}),
            )
        )
    return OverviewGameOut(
        game_id=game.game_id,
        game_number=game.game_number,
        status=game.status,
        # A finished game's last Week would tell the game's length (FR-14): only its status shows.
        week=None if before_start or game.status is GameStatus.FINISHED else game.week,
        version=game.version,
        chain_cost=None if before_start else game.chain_cost,
        wait_started_at=game.wait_started_at,
        waiting_for=[
            OverviewWaitOut(
                role=wait.role,
                name=names.get(wait.user_id) if wait.user_id else None,
                since=wait.since,
            )
            for wait in game.waiting_for
        ],
        seats=seats,
        # The Pause in force (Story 8.6): since when and by whom, by name now.
        paused_at=game.paused_at,
        paused_by=(by or {}).get(game.paused_by) if game.paused_by is not None else None,
        in_room_until=game.in_room_until,
        resume_at=game.resume_at,
    )


def etag_of(overview: ClassOverviewOut) -> str:
    """A strong ETag of everything the Oversikt shows but the clock: it changes with any Game's
    summary, a name, the Start date or the counts, never with `server_now` alone (AD-25)."""
    body = overview.model_dump_json(exclude={"server_now"})
    return '"' + hashlib.sha256(body.encode()).hexdigest()[:32] + '"'


async def readable_game(user: authz.Principal, game_id: uuid.UUID) -> int | None:
    """The Game's `version` when `user` is staff of its Class session and the Lecturer overview
    lists the Game (AD-13), else None: one answer for a Game that does not exist, a test or
    simulation Game, and a Game of another Class (FR-5, NFR-7). Reads no Week."""
    async with get_sessionmaker()() as s:
        head = await games_service.class_game_head(s, game_id)
        if head is None or head.class_session_id is None or not head.listed:
            return None
        row = await repo.session_row(s, head.class_session_id)
    if row is None:
        return None
    if await _class_for(user, row["class_id"], "class_sessions.overview") is None:
        return None
    return head.version


async def game_weeks(game_id: uuid.UUID) -> GameWeeksOut | None:
    """The stored Week values of a Game the caller has checked with `readable_game`."""
    async with get_sessionmaker()() as s:
        found = await games_service.class_game_weeks(s, game_id)
    if found is None:
        return None
    return GameWeeksOut(
        game_id=found.game_id,
        version=found.version,
        weeks=[
            GameWeekOut(
                week=week,
                seats=[
                    WeekSeatOut(
                        role=seat.role,
                        net_inventory=seat.net_inventory,
                        order=seat.order,
                        cost=seat.cost,
                    )
                    for seat in seats
                ],
            )
            for week, seats in found.weeks
        ],
    )


def _holder(kind: str | None) -> Literal["student", "ai", "free"]:
    if kind is None:
        return "free"
    return "student" if kind == games_service.OccupantKind.STUDENT else "ai"


async def game_insight(user: authz.Principal, game_id: uuid.UUID) -> GameInsightOut | None:
    """Spillinnsikt (Story 7.7, FR-62): one Game week by week for the staff of its Class, through
    the `games.insight` policy and the Class staff scope; None, one answer, for a Game that does not
    exist, one whose policy keeps it off Spillinnsikt (a test or simulation Game, AD-13) and one of
    another Class (FR-5, NFR-7). A Student's Replay opens like a Class game, marked `replay` (Story
    10.5, FR-34). Students' names are resolved now (AD-12, AD-14); a fixed number of queries
    whatever the game's length."""
    async with get_sessionmaker()() as s:
        head = await games_service.class_game_head(s, game_id)
        if head is None or head.class_session_id is None or not head.insight:
            return None
        row = await repo.session_row(s, head.class_session_id)
    if row is None:
        return None
    found = await _class_for(user, row["class_id"], "games.insight")
    if found is None:
        return None
    async with get_sessionmaker()() as s:
        number = await repo.number_of(s, head.class_session_id, row["class_id"])
        insight = await games_service.game_insight(s, game_id)
        if insight is None:
            return None
        students = sorted(
            {seat.user_id for seat in insight.seats if seat.user_id is not None}
            | {w.user_id for r in insight.roles for w in r.weeks if w.user_id is not None},
            key=str,
        )
        names = (
            await classes.student_names(row["class_id"], students, session=s) if students else {}
        )
        by = await classes.actor_names(
            s,
            row["class_id"],
            sorted(
                {seat.actor_user_id for seat in insight.seats if seat.actor_user_id}
                | ({insight.paused_by} if insight.paused_by is not None else set())
                | ({insight.started_by} if insight.started_by is not None else set()),
                key=str,
            ),
        )
        # Tilrettelegging is for the Lecturers of the Class only (Story 8.9, UX-DR52, AD-12).
        can_adjust = authz.can(user, "class_sessions.manage", found)
        extra = (
            await time_factors(
                s,
                head.class_session_id,
                [
                    seat.user_id
                    for seat in insight.seats
                    if seat.user_id is not None
                    and seat.occupant_kind == games_service.OccupantKind.STUDENT
                ],
            )
            if can_adjust
            else {}
        )
        # «Sett inn KI-spiller i alle seter som blir ventet på (2)» (Story 8.12): for a Lecturer.
        filled, left = (
            await _waited_split(s, head.class_session_id, game_id)
            if authz.can(user, "games.fill_seats", found)
            else ([], [])
        )
        waited_names = (
            await classes.student_names(
                row["class_id"],
                sorted({w.user_id for w in (*filled, *left) if w.user_id is not None}, key=str),
                session=s,
            )
            if filled or left
            else {}
        )
    # «Marker som i rommet» (Story 8.11): a Lecturer, a running game, and the Lab hour on now on
    # the api's clock, the one Lab hours are judged on.
    can_mark = insight.markable and authz.can(user, "games.in_room", found)
    lab_hour = (
        await current_lab_hour(head.class_session_id, auth.utcnow())
        if can_mark and insight.in_room_minutes is None
        else None
    )
    return GameInsightOut(
        game_id=insight.game_id,
        class_session_id=head.class_session_id,
        class_id=found.id,
        class_name=found.name,
        session_number=number,
        game_number=insight.game_number,
        replay=head.replay,
        status=insight.status,
        end_reason=insight.end_reason,
        version=insight.version,
        weeks_total=insight.weeks_total,
        demand=[DemandWeekOut(week=week, demand=demand) for week, demand in insight.demand],
        seats=[
            InsightSeatOut(
                role=Role(seat.role),
                holder=_holder(seat.occupant_kind),
                name=names.get(seat.user_id) if seat.user_id else None,
                user_id=seat.user_id if seat.user_id in names else None,
                links=[InsightLinkOut(kind=link.kind, href=link.href) for link in seat.links],
                mark=_mark(seat.occupant_kind, seat.reason),
                mark_by=_mark_by(seat.occupant_kind, seat.actor_user_id, by),
                takeover=seat.takeover,
                extra_time=seat.occupant_kind == games_service.OccupantKind.STUDENT
                and seat.user_id in extra,
            )
            for seat in insight.seats
        ],
        roles=[
            InsightRoleOut(
                role=Role(each.role),
                first_large_order_week=each.first_large_order_week,
                weeks=[
                    InsightWeekOut(
                        week=week.week,
                        holder=_holder(week.occupant_kind),
                        name=names.get(week.user_id) if week.user_id else None,
                        incoming_order=week.incoming_order,
                        incoming_delivery=week.incoming_delivery,
                        inventory=week.inventory,
                        backlog=week.backlog,
                        order=week.order,
                        cost=week.cost,
                        marks=list(week.marks),
                        opened_at=week.opened_at,
                        ordered_at=week.ordered_at,
                    )
                    for week in each.weeks
                ],
            )
            for each in insight.roles
        ],
        pause=_insight_pause(insight, user, by),
        can_pause=insight.pausable and authz.can(user, "games.pause", found),
        play_deadline=row["play_deadline"],
        can_adjust=can_adjust,
        # «Start spillet» (Story 8.10): a Lecturer, a game with its snapshot, after the lock.
        can_start=insight.startable and is_locked(row) and authz.can(user, "games.start", found),
        started_by=by.get(insight.started_by) if insight.started_by is not None else None,
        started_at=insight.started_at,
        in_room=InsightInRoomOut(until=insight.in_room_until, minutes=insight.in_room_minutes)
        if insight.markable
        and insight.in_room_minutes is not None
        and insight.in_room_until is not None
        else None,
        can_mark_in_room=can_mark,
        lab_hour_ends_at=None if lab_hour is None else lab_hour.ends_at,
        waited_for=[_waited_out(w, waited_names) for w in filled],
        left_out=[_waited_out(w, waited_names) for w in left],
    )


def _insight_pause(
    insight: games_service.GameInsight, user: authz.Principal, by: dict[uuid.UUID, str]
) -> InsightPauseOut | None:
    """The Pause in force as Spillinnsikt reads it (Story 8.7): since when, by whom (the reader
    themself as «deg»), and the agreed time."""
    if insight.paused_at is None:
        return None
    return InsightPauseOut(
        paused_at=insight.paused_at,
        by=by.get(insight.paused_by) if insight.paused_by is not None else None,
        mine=insight.paused_by == user.id,
        resume_at=insight.resume_at,
    )


class TakeoverRefused(Exception):
    """A staff Takeover `games.commands.takeover` refused (Story 8.5): its stable code, status
    and `fields` (`acted_by`, `acted_at` on `takeover_exists`)."""

    def __init__(self, code: str, status: int, fields: dict[str, Any]) -> None:
        super().__init__(code)
        self.code = code
        self.status = status
        self.fields = fields


async def take_over_seat(
    user: authz.Principal, game_id: uuid.UUID, role: str
) -> GameInsightOut | None:
    """«Sett inn KI-spiller for …» (Story 8.5, FR-37, AD-2, AD-12): a Lecturer or Assistant
    lecturer of the game's Class puts an AI player in the Seat `role`, through the
    `games.takeover` policy and the Class staff scope; None, one answer, for a Game that does not
    exist, one the Oversikt does not list and one of another Class (FR-5). Only
    `games.commands.takeover` acts, with the staff member as actor; its refusals are raised as
    `TakeoverRefused`. Returns Spillinnsikt as it now stands."""
    async with get_sessionmaker()() as s:
        head = await games_service.class_game_head(s, game_id)
        if head is None or head.class_session_id is None or not head.listed:
            return None
        row = await repo.session_row(s, head.class_session_id)
    if row is None:
        return None
    if await _class_for(user, row["class_id"], "games.takeover") is None:
        return None
    try:
        await games_commands.takeover(str(game_id), role, actor="staff", actor_user_id=user.id)
    except games_commands.CommandError as refused:
        if refused.status == 404 and refused.code == "game_not_found":
            return None
        raise TakeoverRefused(refused.code, refused.status, dict(refused.fields)) from None
    return await game_insight(user, game_id)


class PauseRefused(Exception):
    """A Lecturer's Pause command refused (Story 8.7): its stable code, status and `fields`
    (`acted_by`, `acted_at` on `already_paused`)."""

    def __init__(self, code: str, status: int, fields: dict[str, Any]) -> None:
        super().__init__(code)
        self.code = code
        self.status = status
        self.fields = fields


async def _lecturer_game(user: authz.Principal, game_id: uuid.UUID) -> uuid.UUID | None:
    """The Class session of a Class game the Oversikt lists, when `user` is a Lecturer of its
    Class (`games.pause`, AD-12); None, one answer, for anything else (FR-5)."""
    async with get_sessionmaker()() as s:
        head = await games_service.class_game_head(s, game_id)
        if head is None or head.class_session_id is None or not head.listed:
            return None
        row = await repo.session_row(s, head.class_session_id)
    if row is None or await _class_for(user, row["class_id"], "games.pause") is None:
        return None
    return head.class_session_id


def _play_deadline(session_id: uuid.UUID) -> Any:
    """The Class session's Play deadline, read share-locked in the command's transaction before
    the Game row lock, so a deadline moved meanwhile is not passed (as Story 6.19's proposal)."""

    async def read(s: Any) -> datetime | None:
        row = await repo.session_row(s, session_id, share=True)
        return None if row is None else row["play_deadline"]

    return read


async def _staff_pause_command(
    user: authz.Principal, game_id: uuid.UUID, run: Any
) -> GameInsightOut | None:
    session_id = await _lecturer_game(user, game_id)
    if session_id is None:
        return None
    try:
        await run(session_id)
    except games_commands.CommandError as refused:
        if refused.status == 404 and refused.code == "game_not_found":
            return None
        raise PauseRefused(refused.code, refused.status, dict(refused.fields)) from None
    return await game_insight(user, game_id)


async def pause_game(
    user: authz.Principal, game_id: uuid.UUID, resume_at: datetime | None
) -> GameInsightOut | None:
    """«Pause spillet» (Story 8.7, FR-89, AD-2, AD-12): a Lecturer of the game's Class pauses it,
    with the agreed time `resume_at` or without one. Only `games.commands.pause` acts, with the
    Lecturer as a staff actor and the Play deadline as the latest time; its refusals are raised as
    `PauseRefused`. None, one answer, for anyone but a Lecturer of the Class and any Game the
    Oversikt does not list (FR-5). Returns Spillinnsikt as it now stands."""
    return await _staff_pause_command(
        user,
        game_id,
        lambda session_id: games_commands.pause(
            str(game_id),
            actor=user.id,
            staff=True,
            resume_at=resume_at,
            latest=_play_deadline(session_id),
        ),
    )


async def set_agreed_time(
    user: authz.Principal, game_id: uuid.UUID, resume_at: datetime | None
) -> GameInsightOut | None:
    """«Endre avtalt tid» (Story 8.7): a Lecturer of the game's Class sets, changes or clears the
    agreed time of the Pause in force through `games.commands.set_agreed_time`, as `pause_game`."""
    return await _staff_pause_command(
        user,
        game_id,
        lambda session_id: games_commands.set_agreed_time(
            str(game_id), resume_at, actor=user.id, latest=_play_deadline(session_id)
        ),
    )


async def end_pause(user: authz.Principal, game_id: uuid.UUID) -> GameInsightOut | None:
    """«Avslutt pausen» (Story 8.7): a Lecturer of the game's Class ends the Pause in force through
    `games.commands.resume`, as `pause_game`."""
    return await _staff_pause_command(
        user, game_id, lambda _: games_commands.resume(str(game_id), actor=user.id)
    )


class StartRefused(Exception):
    """A Lecturer's «Start spillet» `games.commands.start` refused (Story 8.10): its stable code,
    status and `fields` (`acted_by`, `acted_at` on `game_already_started`)."""

    def __init__(self, code: str, status: int, fields: dict[str, Any]) -> None:
        super().__init__(code)
        self.code = code
        self.status = status
        self.fields = fields


async def start_game(user: authz.Principal, game_id: uuid.UUID) -> GameInsightOut | None:
    """«Start spillet» in Spillstyring (Story 8.10, FR-22, AD-2, AD-12): a Lecturer of the game's
    Class starts it for all four Seats, through the `games.start` policy and the Class staff
    scope; None, one answer, for anyone else and any Game the Oversikt does not list (FR-5). Only
    `games.commands.start` acts, with the Lecturer as actor; before the lock, and for a game no
    Student holds a Seat in, it answers `game_not_ready`, and a game started first
    `game_already_started` with who did.
    Its refusals are raised as `StartRefused`. Returns Spillinnsikt as it now stands."""
    async with get_sessionmaker()() as s:
        head = await games_service.class_game_head(s, game_id)
        if head is None or head.class_session_id is None or not head.listed:
            return None
        row = await repo.session_row(s, head.class_session_id)
    if row is None or await _class_for(user, row["class_id"], "games.start") is None:
        return None
    if not is_locked(row):
        raise StartRefused("game_not_ready", 409, {})
    async with get_sessionmaker()() as s:
        ready = game_id in await games_service.startable_class_games(s, head.class_session_id)
        status = (await games_service.play_status(s, game_id)).status
    # A game not started that may not start yet (no snapshot, or no Student in it) is not ready;
    # one started already goes to the command, which says who started it first.
    if not ready and status in ("ready", "not_ready"):
        raise StartRefused("game_not_ready", 409, {})
    try:
        await games_commands.start(str(game_id), actor=user.id)
    except games_commands.CommandError as refused:
        if refused.status == 404 and refused.code == "game_not_found":
            return None
        raise StartRefused(refused.code, refused.status, dict(refused.fields)) from None
    log.info("lecturer_started_game", game_id=str(game_id))
    return await game_insight(user, game_id)


async def _lecturer_session(user: authz.Principal, session_id: uuid.UUID) -> tuple[Any, Any] | None:
    """The Class session row and its Class when `user` is a Lecturer of it (`games.start`); None,
    one answer, for anyone else and a Class session that does not exist (FR-5)."""
    async with get_sessionmaker()() as s:
        row = await repo.session_row(s, session_id)
    if row is None:
        return None
    found = await _class_for(user, row["class_id"], "games.start")
    return None if found is None else (row, found)


async def start_games_page(user: authz.Principal, session_id: uuid.UUID) -> StartGamesOut | None:
    """The «Start spill» page (Story 8.10, FR-22, UX-DR52): the Class games a Lecturer may start
    now, as the Oversikt words them (Students' names resolved now), by game number; none before
    the lock. None for anyone but a Lecturer of the Class (FR-5)."""
    own = await _lecturer_session(user, session_id)
    if own is None:
        return None
    row, found = own
    async with get_sessionmaker()() as s:
        number = await repo.number_of(s, session_id, row["class_id"])
        ready = (
            set(await games_service.startable_class_games(s, session_id))
            if is_locked(row)
            else set()
        )
        games = [g for g in await games_service.class_overview(s, session_id) if g.game_id in ready]
        students = sorted(
            {seat.user_id for game in games for seat in game.seats if seat.user_id is not None},
            key=str,
        )
        names = (
            await classes.student_names(row["class_id"], students, session=s) if students else {}
        )
    return StartGamesOut(
        class_session_id=session_id,
        class_id=found.id,
        class_name=found.name,
        session_number=number,
        games=[_game_out(game, names, True) for game in games],
    )


async def start_games(
    user: authz.Principal, session_id: uuid.UUID, game_ids: list[uuid.UUID]
) -> StartedGamesOut | None:
    """«Start 12 spill» (Story 8.10, FR-22, AD-2, NFR-7): one `games.commands.start` per listed
    Game, each in its own transaction, with the Lecturer as actor. Only the Class session's games
    that may start now are tried; any other id, a Game started meanwhile, one with no snapshot yet
    (`game_not_ready`) and one that fails are skipped, and a failure never stops the others, so a
    repeat is safe. Returns the real counts; None for anyone but a Lecturer of the Class (FR-5)."""
    own = await _lecturer_session(user, session_id)
    if own is None:
        return None
    row, _ = own
    wanted = list(dict.fromkeys(game_ids))  # each once, in the page's order
    if not is_locked(row):
        return StartedGamesOut(started=0, skipped=len(wanted))
    async with get_sessionmaker()() as s:
        ready = set(await games_service.startable_class_games(s, session_id))
    # A few Games at a time, each start its own command and transaction on its own Game row, so
    # a room of 100 games starts in seconds and the pool keeps connections for other requests.
    gate = asyncio.Semaphore(BATCH_START_CONCURRENCY)

    async def start_one(game_id: uuid.UUID) -> bool:
        async with gate:
            try:
                await games_commands.start(str(game_id), actor=user.id)
            except games_commands.CommandError as refused:
                log.info("batch_start_skipped", game_id=str(game_id), code=refused.code)
                return False
            except Exception:
                log.exception("batch_start_failed", game_id=str(game_id))
                return False
            return True

    outcomes = await asyncio.gather(*(start_one(g) for g in wanted if g in ready))
    started = sum(outcomes)
    log.info("lecturer_started_games", class_session_id=str(session_id), started=started)
    return StartedGamesOut(started=started, skipped=len(wanted) - started)


async def _fillable(s: Any, session_id: uuid.UUID, games: list[ClassGameSummary]) -> int:
    waits = [w for g in games if g.status is GameStatus.WAITING for w in g.waiting_for]
    extra = await time_factors(s, session_id, [w.user_id for w in waits if w.user_id])
    return sum(1 for w in waits if w.user_id not in extra)


async def _waited_split(
    s: Any, session_id: uuid.UUID, game_id: uuid.UUID | None = None
) -> tuple[list[games_service.WaitedSeat], list[games_service.WaitedSeat]]:
    """The Seats the Class session's games (or one game's) wait for now (Story 8.12), split into
    those the fill takes and those left out because their Student has a Tilrettelegging time
    factor (Story 8.9): the factor is what makes a Seat's time differ."""
    waited = await games_service.waited_for_seats(s, session_id, game_id)
    students = [w.user_id for w in waited if w.user_id is not None]
    extra = await time_factors(s, session_id, students) if students else {}
    return (
        [w for w in waited if w.user_id not in extra],
        [w for w in waited if w.user_id in extra],
    )


def _waited_out(seat: games_service.WaitedSeat, names: dict[uuid.UUID, str]) -> WaitedSeatOut:
    return WaitedSeatOut(
        seat_id=seat.seat_id,
        role=Role(seat.role),
        name=names.get(seat.user_id) if seat.user_id else None,
    )


async def _filler_session(user: authz.Principal, session_id: uuid.UUID) -> tuple[Any, Any] | None:
    """The Class session row and its Class when `user` is a Lecturer of it (`games.fill_seats`);
    None, one answer, for anyone else and a Class session that does not exist (FR-5)."""
    async with get_sessionmaker()() as s:
        row = await repo.session_row(s, session_id)
    if row is None:
        return None
    found = await _class_for(user, row["class_id"], "games.fill_seats")
    return None if found is None else (row, found)


async def waited_for_page(user: authz.Principal, session_id: uuid.UUID) -> WaitedForSeatsOut | None:
    """The «Sett inn KI-spillere» page (Story 8.12, FR-37, UX-DR52): the Seats the Class session's
    games wait for now, per game by game number with each Student's name now and the start of the
    wait, and the Seats left out for Tilrettelegging. None for anyone but a Lecturer of the Class
    (FR-5)."""
    own = await _filler_session(user, session_id)
    if own is None:
        return None
    row, found = own
    async with get_sessionmaker()() as s:
        number = await repo.number_of(s, session_id, row["class_id"])
        filled, left = await _waited_split(s, session_id)
        students = sorted({w.user_id for w in (*filled, *left) if w.user_id is not None}, key=str)
        names = (
            await classes.student_names(row["class_id"], students, session=s) if students else {}
        )
        now = await games_service.database_now(s)
    games: dict[uuid.UUID, WaitedGameOut] = {}
    for seat in filled:
        game = games.setdefault(
            seat.game_id,
            WaitedGameOut(game_id=seat.game_id, game_number=seat.game_number, seats=[]),
        )
        game.seats.append(WaitingSeatOut(**_waited_out(seat, names).model_dump(), since=seat.since))
    return WaitedForSeatsOut(
        class_session_id=session_id,
        class_id=found.id,
        class_name=found.name,
        session_number=number,
        server_now=now,
        games=list(games.values()),
        left_out=[_waited_out(w, names) for w in left],
    )


async def fill_waited_for(
    user: authz.Principal, session_id: uuid.UUID, seat_ids: list[uuid.UUID]
) -> FilledSeatsOut | None:
    """«Sett inn 9 KI-spillere» and «Sett inn KI-spiller i alle seter som blir ventet på (2)»
    (Story 8.12, FR-37, AD-2, AD-5): one `games.commands.takeover` per listed Seat with the
    Lecturer as `staff` actor and `only_waited_for`, each in its own transaction under its Game's
    row lock. Games go a few at a time, the Seats of one Game one after another. A Seat of no game
    of this Class session is skipped `not_listed`; a refusal (ordered since, no longer
    Student-held, Tilrettelegging now, paused, ...) is skipped with its code, any other failure
    `failed`, and neither stops the others; a repeat inserts nothing twice (`takeover_exists`).
    Returns the real counts; None for anyone but a Lecturer of the Class (FR-5)."""
    own = await _filler_session(user, session_id)
    if own is None:
        return None
    wanted = list(dict.fromkeys(seat_ids))  # each once, in the page's order
    async with get_sessionmaker()() as s:
        of_game = await games_service.class_seat_games(s, session_id, wanted)
    skipped = [
        SkippedSeatOut(seat_id=seat, reason="not_listed") for seat in wanted if seat not in of_game
    ]
    by_game: dict[uuid.UUID, list[uuid.UUID]] = {}
    for seat in wanted:
        if seat in of_game:
            by_game.setdefault(of_game[seat], []).append(seat)
    gate = asyncio.Semaphore(BATCH_FILL_CONCURRENCY)

    async def fill_game(game_id: uuid.UUID, seats: list[uuid.UUID]) -> list[SkippedSeatOut | None]:
        done: list[SkippedSeatOut | None] = []
        async with gate:
            for seat in seats:
                try:
                    await games_commands.takeover(
                        str(game_id),
                        str(seat),
                        actor="staff",
                        actor_user_id=user.id,
                        only_waited_for=True,
                    )
                except games_commands.CommandError as refused:
                    log.info("fill_seat_skipped", seat_id=str(seat), code=refused.code)
                    done.append(SkippedSeatOut(seat_id=seat, reason=refused.code))
                except Exception:
                    log.exception("fill_seat_failed", game_id=str(game_id), seat_id=str(seat))
                    done.append(SkippedSeatOut(seat_id=seat, reason="failed"))
                else:
                    done.append(None)
        return done

    outcomes = await asyncio.gather(*(fill_game(g, seats) for g, seats in by_game.items()))
    results = [each for game in outcomes for each in game]
    inserted = sum(1 for each in results if each is None)
    skipped += [each for each in results if each is not None]
    log.info(
        "lecturer_filled_seats",
        class_session_id=str(session_id),
        requested=len(wanted),
        inserted=inserted,
        skipped=len(skipped),
        failed=sum(1 for each in skipped if each.reason == "failed"),
    )
    return FilledSeatsOut(inserted=inserted, skipped=skipped)


class InRoomRefused(Exception):
    """A Lecturer's «I rommet» command refused (Story 8.11): its stable code, status and
    `fields` (`acted_by`, `acted_at` on `already_in_room`)."""

    def __init__(self, code: str, status: int, fields: dict[str, Any]) -> None:
        super().__init__(code)
        self.code = code
        self.status = status
        self.fields = fields


async def _in_room_game(user: authz.Principal, game_id: uuid.UUID) -> uuid.UUID | None:
    """The Class session of a Class game the Oversikt lists, when `user` is a Lecturer of its
    Class (`games.in_room`, AD-12); None, one answer, for anything else (FR-5)."""
    async with get_sessionmaker()() as s:
        head = await games_service.class_game_head(s, game_id)
        if head is None or head.class_session_id is None or not head.listed:
            return None
        row = await repo.session_row(s, head.class_session_id)
    if row is None or await _class_for(user, row["class_id"], "games.in_room") is None:
        return None
    return head.class_session_id


async def _in_room_command(
    user: authz.Principal, game_id: uuid.UUID, run: Any
) -> GameInsightOut | None:
    session_id = await _in_room_game(user, game_id)
    if session_id is None:
        return None
    try:
        await run(session_id)
    except games_commands.CommandError as refused:
        if refused.status == 404 and refused.code == "game_not_found":
            return None
        raise InRoomRefused(refused.code, refused.status, dict(refused.fields)) from None
    return await game_insight(user, game_id)


async def mark_in_room(
    user: authz.Principal, game_id: uuid.UUID, minutes: int | float
) -> GameInsightOut | None:
    """«Marker som i rommet» (Story 8.11, FR-36, AD-2, AD-12): a Lecturer of the game's Class marks
    it as played in the room with the in-room limit `minutes`, until the Class session's Lab hour
    on now ends (the api's clock, as Lab hours are judged); with none on, `not_in_lab_hour`. Only
    `games.commands.mark_in_room` acts; its refusals are raised as `InRoomRefused`. None, one
    answer, for anyone but a Lecturer of the Class and any Game the Oversikt does not list (FR-5).
    Returns Spillinnsikt as it now stands."""
    now = auth.utcnow()

    async def run(session_id: uuid.UUID) -> None:
        lab_hour = await current_lab_hour(session_id, now)
        if lab_hour is None:
            raise games_commands.CommandError("not_in_lab_hour", "no Lab hour is on now", 409)
        await games_commands.mark_in_room(
            str(game_id),
            minutes,
            actor=user.id,
            lab_hour_id=lab_hour.id,
            until=lab_hour.ends_at,
            now=now,
        )

    return await _in_room_command(user, game_id, run)


async def end_in_room(user: authz.Principal, game_id: uuid.UUID) -> GameInsightOut | None:
    """«Ikke i rommet lenger» (Story 8.11): a Lecturer of the game's Class ends the mark through
    `games.commands.end_in_room`, as `mark_in_room`."""
    return await _in_room_command(
        user, game_id, lambda _: games_commands.end_in_room(str(game_id), actor=user.id)
    )


def insight_etag(insight: GameInsightOut) -> str:
    """A strong ETag of the whole answer: it changes with the Game's version and with a name."""
    body = insight.model_dump_json()
    return '"' + hashlib.sha256(body.encode()).hexdigest()[:32] + '"'


def game_weeks_etag(version: int) -> str:
    """A strong ETag tied to the Game's `version` (AD-25): every change to a Game raises it."""
    return f'"v{version}"'


WALL_SHAPE = "wall-aggregates-1"


@dataclass(frozen=True)
class WallFilter:
    """One Veggfiltre combination (Story 7.4): the Role, what the cells show, which games."""

    role: Role
    cells: WallCells
    status: WallStatus


@dataclass(frozen=True)
class WallGames:
    """The Class games a filter matched, as `(game_id, version)` by game number, and the ETag of
    their aggregates: it changes with the filter and with any matched Game's version."""

    games: tuple[tuple[uuid.UUID, int], ...]
    etag: str


def _matches(game: ClassGameSummary, status: WallStatus) -> bool:
    if status is WallStatus.ALL:
        return True
    if status is WallStatus.WITH_AI:
        return any(_is_ai(seat) for seat in game.seats)
    return game.status.value == status.value


async def wall_games(
    user: authz.Principal, session_id: uuid.UUID, wanted: WallFilter
) -> WallGames | None:
    """The Class games of the Oversikt that `wanted` matches, or None when the User may not see
    the Oversikt or the Class session does not exist (one answer for both, FR-5). Reads the
    summaries only, so a repeat with the ETag is answered before any Week is read (AD-25)."""
    async with get_sessionmaker()() as s:
        row = await repo.session_row(s, session_id)
    if row is None:
        return None
    if await _class_for(user, row["class_id"], "class_sessions.overview") is None:
        return None
    async with get_sessionmaker()() as s:
        summaries = await games_service.class_overview(s, session_id)
    matched = tuple((g.game_id, g.version) for g in summaries if _matches(g, wanted.status))
    # `WALL_SHAPE` names the response's shape: a deploy that changes it never answers 304.
    body = f"{WALL_SHAPE}|{wanted.role}|{wanted.cells}|{wanted.status}|" + ",".join(
        f"{game_id}:{version}" for game_id, version in matched
    )
    return WallGames(games=matched, etag='"' + hashlib.sha256(body.encode()).hexdigest()[:32] + '"')


async def wall_aggregates_out(wanted: WallFilter, matched: WallGames) -> WallAggregatesOut:
    """The class median rows of the matched games from their stored Weeks (Story 7.4): the
    values of `analysis.wall_aggregates`, in two reads whatever the number of Games (NFR-3)."""
    ids = [game_id for game_id, _ in matched.games]
    async with get_sessionmaker()() as s:
        played = await games_service.class_played(s, ids, wanted.cells is WallCells.ORDER)
    weeks = wall_aggregates(played, str(wanted.role), Cells(wanted.cells.value))
    return WallAggregatesOut(
        role=wanted.role,
        cells=wanted.cells,
        status=wanted.status,
        games=len(ids),
        weeks=[
            WallWeekOut(
                week=w.week,
                games=w.games,
                median=w.median,
                lower_quartile=w.lower_quartile,
                upper_quartile=w.upper_quartile,
                chain_games=w.chain_games,
                chain_cost_mean=w.chain_cost_mean,
            )
            for w in weeks
        ],
    )
