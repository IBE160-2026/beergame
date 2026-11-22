"""Spillinnsikt's read of one Game (Story 7.7, FR-62, FR-34, AD-1, AD-15): per Role and opened
Week the stored engine values, the Order from the Decision log, who held the Seat and the marks of
the one mapping (`marks.seat_mark`). Ids only, never a name (AD-14): the caller resolves names.

Each Week also says when it opened for the Seat and when the Seat ordered (Story 8.1, FR-35).

Read in a fixed number of queries whatever the Game's length. Link providers registered by later
modules (`register_insight_links`, Epic 9) add links to the Student-held Seats; `games` imports
none of them."""

import uuid
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.engine import GameSettings, WeekState
from app.modules.games import overview, repo, rules
from app.modules.games.marks import seat_mark
from app.modules.games.policy import policy
from app.modules.games.schemas import GameStatus, Lifecycle, OccupantKind, SeatMark

__all__ = [
    "LARGE_ORDER",
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


LARGE_ORDER = 10
"""An Order this large or larger is a large Order (UX-DR33: the first one is marked); the same
threshold as Story 9.1's `analysis.facts.LARGE_ORDER`."""

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
    reason: str | None = None
    """The latest occupancy row's reason (Story 8.3): the Seat's AD-15 mark is read from it."""
    actor_user_id: uuid.UUID | None = None
    """Who triggered the latest occupancy row (Story 8.5): a Takeover's staff member or Student."""
    takeover: Literal["this_week", "next_week"] | None = None
    """Whether staff may put an AI player in the Seat now (Story 8.5, FR-37) and from when: this
    Week when its Student has not ordered in the open Week (in a Guided Week: not opened it), the
    next Week when they have. None for a Seat no Student holds or a Game not running."""


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
    opened_at: datetime | None = None
    """When the Week opened for the Seat (Story 8.1, FR-35); None for a Week with no stored turn."""
    ordered_at: datetime | None = None
    """When the Seat ordered (`rules.has_ordered`): its Order's time, or in a Guided Week the time
    the Student holding it opened the Week (FR-24); None while it has not ordered."""


@dataclass(frozen=True)
class InsightRole:
    role: str
    weeks: tuple[InsightWeek, ...]
    first_large_order_week: int | None = None
    """The first Week whose stored Order is `LARGE_ORDER` or more; None with none (Story 7.8, the
    Ordrestolper's dot)."""


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
    paused_at: datetime | None = None
    """Story 8.7: since when the Pause in force runs; None when the Game is not paused."""
    paused_by: uuid.UUID | None = None
    """Story 8.7: who set the Pause in force, by id (AD-14)."""
    resume_at: datetime | None = None
    """Story 8.7: the Lecturer's agreed time of the Pause in force; None without one."""
    pausable: bool = False
    """Story 8.7 (FR-89): a Pause applies to the Game now: it runs and its policy has Pause."""
    startable: bool = False
    """Story 8.10 (FR-22): the Game has not started, has its settings snapshot (the lock) and a
    Student in a Seat."""
    started_by: uuid.UUID | None = None
    """Story 8.10: who pressed «Start spillet», by id (AD-14); None when no person did."""
    started_at: datetime | None = None
    """Story 8.10: when the Game started; None before, and for a Game started before 0060."""


def _in_force(history: Sequence[Mapping[str, Any]], week: int) -> Mapping[str, Any] | None:
    """The Seat's occupancy row in force in `week`: the latest appended with `from_week ≤ week`."""
    found = None
    for row in history:  # as appended (UUIDv7 ids)
        if row["from_week"] <= week:
            found = row
    return found


def _ordered_at(turn: Mapping[str, Any] | None, kind: object, guided: bool) -> datetime | None:
    """When the Seat ordered in the turn's Week, by `rules.has_ordered`'s meaning: in a Guided
    Week a Student-held Seat ordered when its Student opened the Week (FR-24, Story 8.1)."""
    if turn is None:
        return None
    if guided and kind == OccupantKind.STUDENT:
        return turn["viewed_at"] if turn["ordered_at"] is not None else None
    return turn["ordered_at"]


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
    clock = {(row["week"], row["role"]): row for row in await repo.turn_clock(session, game_id)}
    snapshot = game["settings"]
    settings = GameSettings.model_validate(snapshot) if snapshot is not None else None
    game_policy = policy(str(game["purpose"]))
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
            turn = clock.get((state.week, role))
            guided = settings is not None and rules.guided_week(game_policy, settings, state.week)
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
                    opened_at=turn["opened_at"] if turn is not None else None,
                    ordered_at=_ordered_at(turn, kind, guided),
                )
            )
        large = next(
            (row.week for row in rows if row.order is not None and row.order >= LARGE_ORDER), None
        )
        roles.append(InsightRole(role=role, weeks=tuple(rows), first_large_order_week=large))

    first = held[0]["role"] if held else None
    takeover = await _takeover_from(session, game, settings, clock)
    return GameInsight(
        game_id=game["id"],
        class_session_id=game["class_session_id"],
        game_number=game["game_number"],
        status=status,
        version=game["version"],
        weeks_total=settings.weeks if settings is not None else None,
        demand=tuple((state.week, state.seat(first).incoming_order) for state in states)
        if first is not None
        else (),
        seats=tuple(
            InsightSeat(
                role=seat["role"],
                occupant_kind=seat["occupant_kind"],
                user_id=seat["user_id"],
                reason=None if seat["reason"] is None else str(seat["reason"]),
                actor_user_id=seat["actor_user_id"],
                takeover=takeover.get(seat["role"])
                if seat["occupant_kind"] == OccupantKind.STUDENT
                else None,
                links=tuple(link for link in links if link.role == seat["role"])
                if seat["occupant_kind"] == OccupantKind.STUDENT
                else (),
            )
            for seat in held
        ),
        roles=tuple(roles),
        paused_at=game["paused_at"],
        paused_by=game["paused_by"],
        resume_at=game["resume_at"],
        pausable=game["lifecycle"] == Lifecycle.RUNNING and game_policy.pause,
        # As `service.startable_class_games`: a Student must hold a Seat (Story 8.10).
        startable=game["lifecycle"] == Lifecycle.NOT_STARTED
        and snapshot is not None
        and any(seat["occupant_kind"] == OccupantKind.STUDENT for seat in held),
        started_by=game["started_by"],
        started_at=game["started_at"],
    )


async def _takeover_from(
    session: AsyncSession,
    game: Mapping[str, Any],
    settings: GameSettings | None,
    clock: Mapping[tuple[int, str], Mapping[str, Any]],
) -> dict[str, Literal["this_week", "next_week"]]:
    """Per Role, from when a staff Takeover would apply (Story 8.5): read from the open Week's
    turns while the Game runs and its policy has Takeover; the caller keeps it to Student-held
    Seats, as `rules.can_take_over` does."""
    game_policy = policy(str(game["purpose"]))
    if (
        game["lifecycle"] != Lifecycle.RUNNING
        or settings is None
        or not game_policy.inactivity_takeover
    ):
        return {}
    week = await repo.open_week(session, game["id"])
    if week is None:
        return {}
    guided = rules.guided_week(game_policy, settings, week)
    found: dict[str, Literal["this_week", "next_week"]] = {}
    for (turn_week, role), turn in clock.items():
        if turn_week != week:
            continue
        ordered = _ordered_at(turn, OccupantKind.STUDENT, guided) is not None
        if ordered and week >= settings.weeks:
            continue  # the last Week: no next Week for an AI player to take (as the command)
        found[role] = "next_week" if ordered else "this_week"
    return found
