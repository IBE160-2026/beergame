"""The Oversikt of a Class session (Story 7.1, FR-39, AD-25): every Class game with its status,
whom it waits for and its chain cost, read from `games`' `game_summaries` only, with the Students'
names resolved now (AD-12, AD-14). A fixed number of queries whatever the number of Games (NFR-3).
"""

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

from app.analysis.class_cost import FinishedGame, class_cost
from app.analysis.wall import Cells, wall_aggregates
from app.engine.settings import ROLES, Role
from app.modules.classes import service as classes
from app.modules.games import service as games_service
from app.modules.games.service import ClassGameSummary, GameStatus, SeatMark
from app.modules.progress import service as progress
from app.modules.sessions import repo
from app.modules.sessions.schemas import (
    ClassCostOut,
    ClassOverviewOut,
    DemandWeekOut,
    FunnelStageOut,
    GameInsightOut,
    GameWeekOut,
    GameWeeksOut,
    InsightLinkOut,
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
    WallAggregatesOut,
    WallCells,
    WallStatus,
    WallWeekOut,
    WeekSeatOut,
)
from app.modules.sessions.service import _class_for, is_locked
from app.platform import authz
from app.platform.db import get_sessionmaker

__all__ = [
    "WallFilter",
    "class_overview",
    "etag_of",
    "game_weeks",
    "game_weeks_etag",
    "game_insight",
    "insight_etag",
    "readable_game",
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
        now = await games_service.database_now(s)
        # The Start-date lock on the api clock, as the Klasseøkt reads it (`get_session`).
        before_start = not is_locked(row)
        finished = [g for g in games if g.status is GameStatus.FINISHED]
        parts = (
            await games_service.cost_parts(s, [g.game_id for g in finished])
            if finished and not before_start
            else {}
        )
        # The registered Students of the Class: `progress` counts their steps and looks up no one.
        registered = await classes.registered_students(row["class_id"])
        trakt = await progress.funnel(s, session_id, registered)
    counts = {status: 0 for status in GameStatus}
    for game in games:
        counts[game.status] += 1
    return ClassOverviewOut(
        items=[_game_out(game, names, before_start) for game in games],
        next_cursor=None,
        counts=OverviewCountsOut(
            waiting=counts[GameStatus.WAITING],
            running=counts[GameStatus.RUNNING],
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
        class_id=found.id,
        class_name=found.name,
        session_number=number,
    )


def _next_due(games: list[ClassGameSummary], now: datetime) -> datetime | None:
    """The nearest stored Takeover due time of a waiting Class game after `now` (Story 8.1,
    AD-8, AD-20): the Oversikt is read again then. None without one."""
    due = [
        g.takeover_due_at
        for g in games
        if g.status is GameStatus.WAITING
        and g.takeover_due_at is not None
        and g.takeover_due_at > now
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
    game: ClassGameSummary, names: dict[uuid.UUID, str], before_start: bool
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
    exist, one the Lecturer overview does not list (a test or simulation Game, AD-13) and one of
    another Class (FR-5, NFR-7). Students' names are resolved now (AD-12, AD-14); a fixed number of
    queries whatever the game's length."""
    async with get_sessionmaker()() as s:
        head = await games_service.class_game_head(s, game_id)
        if head is None or head.class_session_id is None or not head.listed:
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
    return GameInsightOut(
        game_id=insight.game_id,
        class_session_id=head.class_session_id,
        class_id=found.id,
        class_name=found.name,
        session_number=number,
        game_number=insight.game_number,
        status=insight.status,
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
