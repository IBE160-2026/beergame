"""Spillinnsikt's read of one Game (Story 7.7, FR-62, FR-34, AD-1, AD-15): per Role and opened
Week the stored engine values, the Order from the Decision log, who held the Seat and the marks of
the one mapping (`marks.seat_mark`). Ids only, never a name (AD-14): the caller resolves names.

Read in a fixed number of queries whatever the Game's length. Link providers registered by later
modules (`register_insight_links`, Epic 9) add links to the Student-held Seats; `games` imports
none of them."""

import uuid
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine import GameSettings, WeekState
from app.modules.games import overview, repo
from app.modules.games.marks import seat_mark
from app.modules.games.schemas import GameStatus, OccupantKind, SeatMark

__all__ = [
    "GameInsight",
    "InsightLink",
    "InsightLinkProvider",
    "InsightRole",
    "InsightSeat",
    "InsightWeek",
    "game_insight",
    "register_insight_links",
    "unregister_insight_links",
]


@dataclass(frozen=True)
class InsightLink:
    """A link a later module offers for one Seat's Student (Epic 9: the Explanation, the Debrief
    summary): `kind` names what it is, the page words it; `href` is the page's own path."""

    role: str
    kind: str
    href: str


InsightLinkProvider = Callable[[AsyncSession, uuid.UUID], Awaitable[Sequence[InsightLink]]]
"""`(session, game_id)` → the links for that Game's Seats."""

_providers: list[InsightLinkProvider] = []


def register_insight_links(provider: InsightLinkProvider) -> None:
    """Called once by a later module at start-up (the pattern of Story 5.11's pin providers);
    registering the same provider again changes nothing. None is registered in Epic 7."""
    if provider not in _providers:
        _providers.append(provider)


def unregister_insight_links(provider: InsightLinkProvider) -> None:
    """For tests: take a provider out again."""
    if provider in _providers:
        _providers.remove(provider)


@dataclass(frozen=True)
class InsightSeat:
    """A Seat as it is held now: `occupant_kind` None is free; `links` only on a Student's."""

    role: str
    occupant_kind: str | None
    user_id: uuid.UUID | None
    links: tuple[InsightLink, ...]


@dataclass(frozen=True)
class InsightWeek:
    """One Seat in one opened Week: the stored `SeatState` values, the Order once placed, who
    held the Seat that Week and its marks (the seat mark in the Week its occupancy began, then
    the Order's)."""

    week: int
    occupant_kind: str | None
    user_id: uuid.UUID | None
    incoming_order: int
    incoming_delivery: int
    inventory: int
    backlog: int
    order: int | None
    cost: Decimal
    marks: tuple[SeatMark, ...]


@dataclass(frozen=True)
class InsightRole:
    role: str
    weeks: tuple[InsightWeek, ...]


@dataclass(frozen=True)
class GameInsight:
    """Everything Spillinnsikt shows of a Game, in chain order (the Role serving the customer
    first). `weeks_total` and `demand` are served to the staff only (AD-3)."""

    game_id: uuid.UUID
    class_session_id: uuid.UUID | None
    game_number: int | None
    status: GameStatus
    version: int
    weeks_total: int | None
    """The snapshot's number of Weeks; None before the Game has its snapshot."""
    demand: tuple[tuple[int, int], ...]
    """(Week, the customer demand the first Role received that Week), per opened Week."""
    seats: tuple[InsightSeat, ...]
    roles: tuple[InsightRole, ...]


def _in_force(history: Sequence[Mapping[str, Any]], week: int) -> Mapping[str, Any] | None:
    """The Seat's occupancy row in force in `week`: the latest appended with `from_week ≤ week`."""
    found = None
    for row in history:  # as appended (UUIDv7 ids)
        if row["from_week"] <= week:
            found = row
    return found


async def game_insight(session: AsyncSession, game_id: uuid.UUID) -> GameInsight | None:
    """The Game's insight, or None for no such Game. The caller has checked the User."""
    game = await repo.get_game(session, game_id)
    if game is None:
        return None
    summary = await repo.summary(session, game_id)
    status = (
        GameStatus(summary["status"])
        if summary is not None
        else GameStatus((await overview.recompute(session, game))["status"])
    )
    held = await repo.seats_with_occupant(session, game_id)
    history: dict[str, list[Mapping[str, Any]]] = {}
    for row in await repo.occupancy_history(session, game_id):
        history.setdefault(row["role"], []).append(row)
    students = {
        role: [row for row in appended if row["occupant_kind"] == OccupantKind.STUDENT]
        for role, appended in history.items()
    }
    logged = {(row["week"], row["role"]): row for row in await repo.decision_log(session, game_id)}
    states = [
        state
        for state in map(WeekState.model_validate, await repo.week_states(session, game_id))
        if not state.finished
    ]
    links: list[InsightLink] = []
    for provider in _providers:
        links.extend(await provider(session, game_id))

    roles: list[InsightRole] = []
    for seat in held:  # chain order
        role = seat["role"]
        rows: list[InsightWeek] = []
        last: tuple[object, object] | None = None
        for state in states:
            values = state.seat(role)
            occupancy = _in_force(history.get(role, []), state.week)
            log = logged.get((state.week, role))
            source = log if log is not None else occupancy
            kind = source["occupant_kind"] if source is not None else None
            reason = source["reason"] if source is not None else None
            marks: list[SeatMark] = []
            # The seat mark stands in the Week the Seat's occupancy began, not on every later one.
            if (kind, reason) != last:
                mark = seat_mark(None, None, kind, reason)
                if mark is not None:
                    marks.append(mark)
            last = (kind, reason)
            if log is not None:
                mark = seat_mark(log["decided_by"], log["fallback"], None, None)
                if mark is not None:
                    marks.append(mark)
            # The Student who played: the Student row in force that Week, also when a later
            # switch in the same Week (a Takeover after the Order) is the row in force now.
            student = (
                _in_force(students.get(role, []), state.week)
                if kind == OccupantKind.STUDENT
                else None
            )
            rows.append(
                InsightWeek(
                    week=state.week,
                    occupant_kind=kind,
                    user_id=student["user_id"] if student is not None else None,
                    incoming_order=values.incoming_order,
                    incoming_delivery=values.incoming_delivery,
                    inventory=values.inventory,
                    backlog=values.backlog,
                    order=log["order"] if log is not None else None,
                    cost=values.cost,
                    marks=tuple(marks),
                )
            )
        roles.append(InsightRole(role=role, weeks=tuple(rows)))

    first = held[0]["role"] if held else None
    snapshot = game["settings"]
    return GameInsight(
        game_id=game["id"],
        class_session_id=game["class_session_id"],
        game_number=game["game_number"],
        status=status,
        version=game["version"],
        weeks_total=GameSettings.model_validate(snapshot).weeks if snapshot is not None else None,
        demand=tuple((state.week, state.seat(first).incoming_order) for state in states)
        if first is not None
        else (),
        seats=tuple(
            InsightSeat(
                role=seat["role"],
                occupant_kind=seat["occupant_kind"],
                user_id=seat["user_id"],
                links=tuple(link for link in links if link.role == seat["role"])
                if seat["occupant_kind"] == OccupantKind.STUDENT
                else (),
            )
            for seat in held
        ),
        roles=tuple(roles),
    )
