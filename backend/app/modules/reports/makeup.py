"""«Gi oppfølgingsspill»: a Lecturer gives one Student a make-up game (Story 13.4, FR-17, FR-20,
FR-30, FR-3, AD-2, AD-4, AD-8, AD-9, AD-12, AD-13).

Only the Lecturers of the Class (`makeup.give`), once `sessions.lock` has frozen the Class
session's snapshot and before the Student's effective Test deadline. In one transaction, under the
session row's share lock: `games.commands.create` makes a `makeup` Game on that snapshot unchanged
(Game settings, demand series, seed, `rules_version`, `SessionRuntime`); `assign_seat` gives the
Student their Class game's Role (a drawn one if they never held a Seat) and each other Seat an AI
player of the session's AI mode, so `start` finds no free Seat; a `makeup_games` row names it; one
audit row by ids and codes; a `makeup_given` notice; and `user:<student>` and `session:<id>`. The
Game is not started: the Student starts it from Hjem after the pre-play gate, as a Class game.
One per Student and Class session: a second press, also one at the same moment, answers the
existing one and writes nothing. It is closed at the Test deadline by the sweep's
`games.close_at_test_deadline`, which its policy row (`closes_at_test_deadline`) turns on."""

import secrets
import uuid
from collections.abc import Mapping
from datetime import datetime
from typing import Any

import structlog

from app.modules.classes import service as classes
from app.modules.games import commands as games_commands
from app.modules.games import service as games
from app.modules.reports import repo, scope
from app.modules.sessions import service as sessions
from app.platform import audit, auth, authz, events, notify
from app.platform.db import get_sessionmaker

__all__ = ["GIVE", "GIVEN", "NOTICE", "MakeupRefused", "give", "refusal"]

log = structlog.get_logger(__name__)

GIVE = "makeup.give"
"""The Class action of «Gi oppfølgingsspill»: the Class's owners only."""

GIVEN = "makeup.given"
"""The audit action: target the Class session, the Student and the Game; change the Role."""

NOTICE = "makeup_given"
"""The digest notice the Student gets: «Du har fått et Oppfølgingsspill» (AD-9)."""


class MakeupRefused(Exception):
    """409: `not_counted` (a Student reports leave out), `session_not_locked` (no frozen snapshot
    yet), `no_test_deadline`, `test_deadline_passed`."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def refusal(
    row: Mapping[str, Any], user_id: uuid.UUID, now: datetime, *, counted: bool
) -> str | None:
    """Why no Oppfølgingsspill can be given now in the Class session `row` (read with the
    Student's own deadlines), or None: for a Student reports leave out (`counted` False: a test
    student, or any Student of a Control test Class session, `scope.reporting_students`), before
    `sessions.lock` has stored the frozen snapshot, with no Test deadline, or once the Student's
    effective Test deadline has passed (app clock). The command and the Studentside's
    `can_give_makeup` both ask this one function."""
    if not counted:
        return "not_counted"
    if row["snapshot"] is None:
        return "session_not_locked"
    deadline = sessions.effective_test_deadline(user_id, row)
    if deadline is None:
        return "no_test_deadline"
    if deadline <= now:
        return "test_deadline_passed"
    return None


class _Taken(Exception):
    """Another press made the Student's Oppfølgingsspill first: this one's Game is rolled back."""


async def give(
    user: authz.Principal, class_session_id: uuid.UUID, user_id: uuid.UUID
) -> bool | None:
    """Give the Student an Oppfølgingsspill: True when this press made it, False when they had
    one already (nothing written); None (403) for anyone but a Lecturer of the Class and for a
    User who is no Student of it (FR-5). Raises `MakeupRefused` or `classes.ClassArchived`, with
    nothing written."""
    reached = await sessions.student_target(user, class_session_id, user_id, GIVE)
    if reached is None:
        return None
    now = auth.utcnow()
    try:
        async with get_sessionmaker().begin() as s:
            if await repo.makeup_of(s, user_id, class_session_id) is not None:
                return False
            if not await classes.is_writable(reached.class_id, session=s):
                raise classes.ClassArchived
            row = await sessions.makeup_session_row(s, class_session_id, user_id, share=True)
            if row is None:
                return None
            counted = user_id in await scope.reporting_students(s, class_session_id)
            refused = refusal(row, user_id, now, counted=counted)
            if refused is not None:
                raise MakeupRefused(refused)
            snapshot = row["snapshot"]
            roles = list(snapshot["settings"]["roles"])
            own = await games.student_game(s, user_id, class_session_id)
            # The Student's own Role, or one drawn at random for a Student who never held a Seat.
            role = own.role if own is not None else secrets.choice(roles)
            ai = (
                games.OccupantKind.LLM
                if snapshot["session_runtime"]["model_config_id"] is not None
                else games.OccupantKind.RULE_BASED
            )
            game_id = await games_commands.create(
                "makeup", snapshot=snapshot, class_session_id=class_session_id, within=s
            )
            for each in roles:
                if each == role:
                    await games_commands.assign_seat(
                        game_id, each, "student", user_id=user_id, within=s
                    )
                else:
                    await games_commands.assign_seat(game_id, each, ai.value, within=s)
            makeup_id = await repo.insert_makeup(
                s,
                user_id=user_id,
                class_session_id=class_session_id,
                game_id=uuid.UUID(game_id),
                given_by=user.id,
                given_at=now,
            )
            if makeup_id is None:
                raise _Taken
            await audit.record(
                s,
                user.id,
                GIVEN,
                {"class_session_id": class_session_id, "user_id": user_id, "game_id": game_id},
                {"role": role},
                now,
            )
            await notify.enqueue(s, user_id, NOTICE, f"{NOTICE}:{makeup_id}", ref=class_session_id)
            # The Student's Hjem shows it at once, and the open Studentside reads it again (AD-8).
            await events.emit(s, "user", str(user_id))
            await events.emit(s, "session", str(class_session_id))
    except _Taken:
        return False
    log.info("makeup_given", game_id=game_id, class_session_id=str(class_session_id))
    return True
