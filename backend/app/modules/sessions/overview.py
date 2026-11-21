"""The Oversikt of a Class session (Story 7.1, FR-39, AD-25): every Class game with its status,
whom it waits for and its chain cost, read from `games`' `game_summaries` only, with the Students'
names resolved now (AD-12, AD-14). A fixed number of queries whatever the number of Games (NFR-3).
"""

import hashlib
import uuid
from dataclasses import dataclass

from app.analysis.wall import Cells, wall_aggregates
from app.engine.settings import Role
from app.modules.classes import service as classes
from app.modules.games import service as games_service
from app.modules.games.service import ClassGameSummary, GameStatus
from app.modules.sessions import repo
from app.modules.sessions.schemas import (
    ClassOverviewOut,
    GameWeekOut,
    GameWeeksOut,
    OverviewCountsOut,
    OverviewGameOut,
    OverviewSeatOut,
    OverviewWaitOut,
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
        class_id=found.id,
        class_name=found.name,
        session_number=number,
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
        seats.append(OverviewSeatOut(role=seat.role, holder=holder, name=name))
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
        return any(
            seat.occupant_kind is not None
            and seat.occupant_kind != games_service.OccupantKind.STUDENT
            for seat in game.seats
        )
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
