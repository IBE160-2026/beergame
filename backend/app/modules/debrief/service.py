"""What other modules and the routes use of `debrief` (Stories 9.2, 9.3, 9.4).

- `open_mine(user, class_session_id)`: the Student's Debrief, opened on first use; raises
  `NotAvailable` with the code the route answers (`debrief_not_open`, `debrief_held`), and None
  for every case the route answers `forbidden` (FR-5).
- `mine(user, debrief_id)`: the same read by the Debrief's id.
- `due_releases(now)` / `release_due(id, now)`: the sweep's Debrief release (AD-9).
- Step 1 (Story 9.3): `own_net_inventory`, `own_explanation`, `save_mine` (raises
  `InvalidExplanation`, `commands.ExplanationExists`).
- `require_explanation(user_id, class_session_id)`: the one gate every Debrief read after step 1
  goes through (raises `ExplanationRequired`, 403 `explanation_required`, FR-41, FR-43);
  `step(user, debrief_id, n)` is the step endpoint behind it; step 2 carries the reveal of
  customer demand (Story 9.4, `reveal`).
- `staff_explanation(user, class_session_id, student_id)`: the Explanation for the Class's staff
  (`explanations.read`, AD-12); None for everyone else.
"""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select

from app.analysis import sentences
from app.engine.settings import Role
from app.modules.content import service as content
from app.modules.debrief import commands, rules
from app.modules.debrief.models import (
    EXPLANATION_MAX,
    debrief_explanations,
    debrief_releases,
    debrief_sessions,
)
from app.modules.debrief.schemas import (
    DebriefOut,
    DebriefStepOut,
    ExplanationOut,
    LargestOrderOut,
    MyExplanationOut,
    NetInventoryOut,
    NetWeekOut,
    RevealOut,
    RevealWeekOut,
)
from app.modules.games import service as games
from app.modules.progress import service as progress
from app.modules.sessions import service as sessions
from app.platform import authz
from app.platform.db import get_sessionmaker

__all__ = [
    "ExplanationRequired",
    "InvalidExplanation",
    "NoExplanation",
    "NotAvailable",
    "due_releases",
    "judge_explanation",
    "mine",
    "open_mine",
    "own_explanation",
    "own_net_inventory",
    "release_due",
    "require_explanation",
    "save_mine",
    "staff_explanation",
    "step",
]


class NotAvailable(Exception):
    """The Student's Debrief is not open: `debrief_not_open` (their game has not finished) or
    `debrief_held` (the Lecturer holds every Debrief until all Class games have finished)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ExplanationRequired(Exception):
    """A read after step 1 without the Student's saved Explanation (403 `explanation_required`,
    FR-41): checked here, in the api, never only in the web app."""


class InvalidExplanation(Exception):
    """An Explanation that may not be stored: `blank` (white space only) or `too_long`."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class NoExplanation(Exception):
    """The Student has not sent an Explanation in the Class session (404 `not_found`)."""


def _open_or_raise(found: rules.Availability) -> None:
    if found.state == "not_open":
        raise NotAvailable("debrief_not_open")
    if found.state == "held":
        raise NotAvailable("debrief_held")


def _out(row: commands.DebriefRow, game: games.StudentGame) -> DebriefOut:
    return DebriefOut(
        id=row.id,
        class_session_id=row.class_session_id,
        game_id=row.game_id,
        game_number=game.number,
        role=game.role,
        step=row.step,
    )


async def open_mine(user: authz.Principal, class_session_id: uuid.UUID) -> DebriefOut | None:
    """«Gå til Debrief» and Stegene's Debrief step (FR-42): `debrief.commands.open` for the
    Student's game, through `games.service.student_game` only."""
    found = await rules.available(user, class_session_id)
    if found is None:
        return None
    _open_or_raise(found)
    row = await commands.open(found.game.game_id, class_session_id)
    return _out(row, found.game)


async def _own(
    user: authz.Principal, debrief_id: uuid.UUID
) -> tuple[commands.DebriefRow, games.StudentGame] | None:
    """The Debrief session `debrief_id` with the Student's game when it is the one of their own
    game; None for any other id alike. Raises `NotAvailable` while it is not open."""
    async with get_sessionmaker()() as s:
        row = (
            (await s.execute(select(debrief_sessions).where(debrief_sessions.c.id == debrief_id)))
            .mappings()
            .one_or_none()
        )
    if row is None:
        return None
    # Whose it is first: another Game's Debrief reads as one that does not exist (FR-5), never
    # as not open or held.
    found = await rules.available(user, row["class_session_id"])
    if found is None or found.game.game_id != row["game_id"]:
        return None
    _open_or_raise(found)
    return commands.row_of(row), found.game


async def mine(user: authz.Principal, debrief_id: uuid.UUID) -> DebriefOut | None:
    """The Debrief session `debrief_id` when it is the one of the Student's own game, under the
    same availability rule; None for any other id alike."""
    found = await _own(user, debrief_id)
    return _out(*found) if found else None


async def own_net_inventory(user: authz.Principal, debrief_id: uuid.UUID) -> NetInventoryOut | None:
    """«Ditt netto lager, hele spillet» (Story 9.3): the Netto lager of the Student's own Seat in
    every Uke of the Decision log, as the Seat saw it when ordering. Only rows of the Student's
    own Role go into the answer: no demand, no other Seat (FR-14). Not gated by the Explanation,
    nor is the number of Uker: the finished game has shown them all."""
    found = await _own(user, debrief_id)
    if found is None:
        return None
    row, game = found
    logged = await games.decision_log(str(row.game_id))
    own = sorted((e for e in logged if str(e.role) == str(game.role)), key=lambda e: e.week)
    return NetInventoryOut(
        weeks=[NetWeekOut(week=e.week, net_inventory=e.state_seen.net_inventory) for e in own]
    )


async def _stored(user_id: uuid.UUID, class_session_id: uuid.UUID) -> ExplanationOut | None:
    async with get_sessionmaker()() as s:
        row = (
            (
                await s.execute(
                    select(debrief_explanations).where(
                        debrief_explanations.c.user_id == user_id,
                        debrief_explanations.c.class_session_id == class_session_id,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        return None
    return ExplanationOut(text=row["text"], length=row["length"], saved_at=row["saved_at"])


async def own_explanation(user: authz.Principal, debrief_id: uuid.UUID) -> MyExplanationOut | None:
    """The Student's own Explanation in this Debrief, `explanation` None before it is sent.
    Keyed by the caller: no Student reads another's (FR-41)."""
    found = await _own(user, debrief_id)
    if found is None:
        return None
    row, _ = found
    return MyExplanationOut(explanation=await _stored(user.id, row.class_session_id))


def judge_explanation(text: str) -> None:
    """Raises `InvalidExplanation` for white space only or more than 5000 characters."""
    if not text.strip():
        raise InvalidExplanation("blank")
    if len(text) > EXPLANATION_MAX:
        raise InvalidExplanation("too_long")


async def save_mine(
    user: authz.Principal, debrief_id: uuid.UUID, text: str
) -> ExplanationOut | None:
    """«Send Forklaring»: `debrief.commands.save_explanation` for the Student's own Debrief.
    Raises `NotAvailable`, `InvalidExplanation` or `commands.ExplanationExists`."""
    found = await _own(user, debrief_id)
    if found is None:
        return None
    row, _ = found
    judge_explanation(text)
    saved = await commands.save_explanation(row.game_id, row.class_session_id, user.id, text)
    return ExplanationOut(text=saved.text, length=saved.length, saved_at=saved.saved_at)


async def require_explanation(user_id: uuid.UUID, class_session_id: uuid.UUID) -> None:
    """The gate (FR-41, FR-43, AD-21): every Debrief read after step 1 (the steps, the demand
    series, another Seat's Orders, inventory or backlog) calls this first. Raises
    `ExplanationRequired` until the Student's Explanation is saved."""
    if not await progress.has_step(user_id, class_session_id, progress.Step.EXPLANATION):
        raise ExplanationRequired


async def step(user: authz.Principal, debrief_id: uuid.UUID, number: int) -> DebriefStepOut | None:
    """A step after step 1, behind the gate. Raises `NotAvailable` or `ExplanationRequired`."""
    found = await _own(user, debrief_id)
    if found is None:
        return None
    row, game = found
    await require_explanation(user.id, row.class_session_id)
    shown = await _reveal(row.game_id, game.role) if number == 2 else None
    return DebriefStepOut(debrief_id=row.id, step=number, reveal=shown)


async def _reveal(game_id: uuid.UUID, role: str) -> RevealOut:
    """Step 2 (Story 9.4, FR-44): the heading from the Game's stored demand series with the
    sentence templates its Class session pinned at the lock (the latest for a session locked
    before the pin), and per logged Uke of the own Seat: Kundene, Ordre inn and Din ordre. Call
    only behind `require_explanation`."""
    found = await games.get_game(str(game_id))
    series = await games.demand_series(str(game_id))
    if found is None or found.settings is None or not series:
        raise RuntimeError(f"a finished Game {game_id} has no demand series")
    pins = found.session_runtime.pins if found.session_runtime else None
    _, templates = await content.sentence_templates(
        content.pinned_version(pins, content.Kind.SENTENCE_TEMPLATES)
    )
    heading = sentences.demand_heading(found.settings.demand, series, templates)
    logged = await games.decision_log(str(game_id))
    own = sorted((e for e in logged if str(e.role) == str(role)), key=lambda e: e.week)
    weeks = [
        RevealWeekOut(
            week=e.week,
            demand=series[e.week - 1],
            incoming_order=e.state_seen.incoming_order,
            order=e.order,
        )
        for e in own
    ]
    # The first Uke of the largest Order (max keeps the first of equals); none when every Order
    # was 0, so no label stands on an empty baseline.
    largest = max(weeks, key=lambda w: w.order, default=None)
    if largest is not None and largest.order == 0:
        largest = None
    return RevealOut(
        heading=heading.text,
        template_id=heading.template_id,
        role=Role(role),
        weeks=weeks,
        largest_order=LargestOrderOut(week=largest.week, order=largest.order) if largest else None,
    )


async def staff_explanation(
    user: authz.Principal, class_session_id: uuid.UUID, student_id: uuid.UUID
) -> ExplanationOut | None:
    """A Student's Explanation for the staff of the Class (`explanations.read`: its owners and
    Assistant lecturers, AD-12); None for every other caller alike (FR-5). Raises
    `NoExplanation` when the Student has not sent one."""
    if not await sessions.class_staff_may(user, class_session_id, "explanations.read"):
        return None
    found = await _stored(student_id, class_session_id)
    if found is None:
        raise NoExplanation
    return found


async def due_releases(now: datetime) -> Sequence[str]:
    """The held Class sessions whose Class games have all finished and that are not released yet
    (Story 9.2): ids only."""
    async with get_sessionmaker()() as s:
        held = await sessions.held_debrief_sessions(s)
        if not held:
            return []
        released = set(
            (
                await s.scalars(
                    select(debrief_releases.c.class_session_id).where(
                        debrief_releases.c.class_session_id.in_(held)
                    )
                )
            ).all()
        )
        waiting = [session_id for session_id in held if session_id not in released]
        found = await games.class_games_of(s, waiting)
    return [
        str(session_id)
        for session_id in waiting
        if found.get(session_id)
        and all(game.lifecycle == games.Lifecycle.FINISHED for game in found[session_id])
    ]


async def release_due(class_session_id: object, now: datetime) -> bool:
    """The sweep's act: `debrief.commands.release` for one Class session id."""
    assert isinstance(class_session_id, str)
    return await commands.release(uuid.UUID(class_session_id), now)
