"""Start a Student's Replay (Story 10.3, FR-48, FR-49, FR-30, AD-2, AD-4, AD-5, AD-13, AD-16).

`start` makes one `replay` Game per Student and Class session: the Class session's frozen
snapshot with only the Game settings, the demand series and the seed replaced by the Replay's own,
drawn from the session's locked template with a fresh seed (`engine.replay_settings`). The Student
holds the Role of their own game (`games.service.student_game`), AI players of the session's AI
mode hold the others, and the Game is started, so the Student never meets an empty Seat or a Game
that has not started. This module writes no game table: Games only through `games.commands`, its
own `replays` row naming the Game. It reaches other modules only through their `service.py` (and
`games.commands`, the one write path for Games)."""

import secrets
import uuid
from dataclasses import dataclass
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine import ReplayTemplate, demand_series, replay_settings
from app.engine.demand import new_seed
from app.modules.games import commands as games_commands
from app.modules.games import service as games_service
from app.modules.progress import service as progress
from app.modules.replay import repo
from app.modules.replay.schemas import WalkthroughRunOut
from app.modules.replay.walkthrough import ReplayReport
from app.modules.replay.walkthrough import report as report_replay
from app.modules.sessions import service as sessions
from app.platform import auth, authz, events
from app.platform.db import get_sessionmaker

__all__ = [
    "REPLAY_LINK",
    "ReplayRefused",
    "ReplayReport",
    "WalkthroughRunOut",
    "Started",
    "insight_links",
    "insight_path",
    "replay_game_of",
    "report_replay",
    "start",
]

log = structlog.get_logger(__name__)


class ReplayRefused(Exception):
    """A start the api refuses: 403 `quiz_required` before the Debrief quiz is passed (AD-16),
    409 `test_deadline_passed` after the Student's Test deadline (FR-18)."""

    def __init__(self, code: str, status: int) -> None:
        super().__init__(code)
        self.code = code
        self.status = status


@dataclass(frozen=True)
class Started:
    """The Student's Replay: its Game id, and whether this request made it."""

    game_id: uuid.UUID
    created: bool


class _Taken(Exception):
    """Another start made the Student's Replay first: this one's Game is rolled back."""


async def replay_game_of(
    session: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID
) -> uuid.UUID | None:
    """The Student's Replay Game in the Class session, or None; for Hjem (`sessions`)."""
    return await repo.replay_game(session, user_id, class_session_id)


sessions.register_replay_game(replay_game_of)


async def _record_replay_step(session: AsyncSession, finished: games_service.FinishedGame) -> None:
    """The finish hook (Story 10.5, FR-48, AD-16): when the finished Game is a Student's Replay —
    the one their `replays` row names — record their `replay` step at database time, in the
    finishing transaction, which unlocks the Individual test. `record_step` stores it once and
    emits `user:<id>` and `session:<id>`, so Stegene moves on without reload (AD-8). Its time,
    against the Debrief deadline, is what lateness is read from (FR-18)."""
    owner = await repo.replay_owner(session, finished.game_id)
    if owner is None:
        return
    user_id, class_session_id = owner
    at = await games_service.database_now(session)
    if await progress.record_step(
        user_id, class_session_id, progress.Step.REPLAY, at, within=session
    ):
        log.info("replay_finished", game_id=str(finished.game_id))


games_service.on_game_finished("replay.step", _record_replay_step)

REPLAY_LINK = "replay"
"""The kind of the link from a Student's Seat on their Class game's Spillinnsikt to their Replay."""


def insight_path(class_session_id: object, game_id: object) -> str:
    """Spillinnsikt of a Game in the web app (the staff page `/klasseokter/…/oversikt/spill/…`)."""
    return f"/klasseokter/{class_session_id}/oversikt/spill/{game_id}"


async def insight_links(
    session: AsyncSession, game_id: uuid.UUID
) -> list[games_service.InsightLink]:
    """On a Class game's Spillinnsikt, a link from each Student-held Seat to that Student's Replay
    in the Class session, where they have one (Story 10.5, FR-34): the way staff reach it, since
    the Oversikt does not list it. Spillinnsikt gives links to Student-held Seats only (Story
    7.7), like the Debrief's. None on any other Game. Ids only (AD-14)."""
    found = await games_service.get_game(str(game_id))
    if found is None or found.class_session_id is None:
        return []
    if not games_service.policy(found.purpose).lecturer_overview:
        return []
    held = {uuid.UUID(seat.user_id): seat.role for seat in found.seats if seat.user_id}
    replays = await repo.replay_games(session, list(held), uuid.UUID(found.class_session_id))
    return [
        games_service.InsightLink(
            role=held[user_id],
            kind=REPLAY_LINK,
            href=insight_path(found.class_session_id, replay_game),
        )
        for user_id, replay_game in sorted(replays.items(), key=lambda item: str(item[0]))
    ]


games_service.register_insight_links(insight_links)


def _replay_snapshot(frozen: dict[str, Any], seed: int, template: ReplayTemplate) -> dict[str, Any]:
    """The Class session's frozen snapshot with the Replay's own settings, demand series and
    seed; its `SessionRuntime` and `rules_version` stay the session's (AD-4)."""
    settings = replay_settings(template, seed)
    return {
        **frozen,
        "settings": settings.model_dump(mode="json"),
        "demand_series": list(demand_series(settings)),
        "demand_seed": settings.demand_seed,
    }


async def _started(game_id: uuid.UUID) -> None:
    """Start the Replay; one already started (by a start that ran at the same moment, or after a
    start that failed after its commit) counts as done."""
    try:
        await games_commands.start(str(game_id))
    except games_commands.CommandError as refused:
        if refused.code != "game_already_started":
            raise


async def start(user: authz.Principal, class_session_id: uuid.UUID) -> Started | None:
    """«Start Replay» (Story 10.3). Returns the Student's Replay, the one they have already or a
    new one; None when the Class session is not one of their own locked sessions or they have no
    game in it (the route's 403, FR-5). Raises `ReplayRefused` without `quiz_passed` or once the
    Test deadline (`sessions.effective_test_deadline`) has passed.

    The Game, its Seats and the `replays` row are made in one transaction; a second start at the
    same moment waits on the row's unique key, finds the first one's and its own Game is rolled
    back. The start runs after the commit, so a Replay whose start failed is started by the next
    request instead of being made twice."""
    async with get_sessionmaker().begin() as s:
        row = await sessions.replay_session_of(s, user, class_session_id)
        if row is None or await games_service.student_game(s, user.id, class_session_id) is None:
            return None
        existing = await repo.replay_game(s, user.id, class_session_id)
    if existing is not None:
        await _started(existing)
        return Started(existing, created=False)
    if not await progress.has_step(user.id, class_session_id, progress.Step.QUIZ_PASSED):
        raise ReplayRefused("quiz_required", 403)
    try:
        async with get_sessionmaker().begin() as s:
            row = await sessions.replay_session_of(s, user, class_session_id)
            if row is None:
                return None
            # Judged under the row's share lock, so the deadline cannot move while this runs.
            if sessions.test_deadline_passed(user, row, auth.utcnow()):
                raise ReplayRefused("test_deadline_passed", 409)
            own = await games_service.student_game(s, user.id, class_session_id)
            if own is None:
                return None
            frozen = row["snapshot"] or await sessions.build_snapshot(row, session=s)
            seed = new_seed(secrets.token_bytes(16))
            snapshot = _replay_snapshot(frozen, seed, sessions.replay_template(row))
            ai = (
                games_service.OccupantKind.LLM
                if snapshot["session_runtime"]["model_config_id"] is not None
                else games_service.OccupantKind.RULE_BASED
            )
            game_id = await games_commands.create(
                "replay", snapshot=snapshot, class_session_id=class_session_id, within=s
            )
            for role in snapshot["settings"]["roles"]:
                if role == own.role:
                    await games_commands.assign_seat(
                        game_id, role, "student", user_id=user.id, within=s
                    )
                else:
                    await games_commands.assign_seat(game_id, role, ai.value, within=s)
            if not await repo.insert_replay(s, user.id, class_session_id, uuid.UUID(game_id)):
                raise _Taken
            # Hjem on the Student's other devices shows the Replay at once (AD-8).
            await events.emit(s, "user", str(user.id))
    except _Taken:
        async with get_sessionmaker().begin() as s:
            taken = await repo.replay_game(s, user.id, class_session_id)
        if taken is None:  # the other start's Game went with its Class session or account
            return None
        await _started(taken)
        return Started(taken, created=False)
    await _started(uuid.UUID(game_id))
    log.info("replay_started", game_id=game_id, class_session_id=str(class_session_id))
    return Started(uuid.UUID(game_id), created=True)
