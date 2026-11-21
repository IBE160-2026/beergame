"""What other modules and the routes use of `debrief` (Story 9.2).

- `open_mine(user, class_session_id)`: the Student's Debrief, opened on first use; raises
  `NotAvailable` with the code the route answers (`debrief_not_open`, `debrief_held`), and None
  for every case the route answers `forbidden` (FR-5).
- `mine(user, debrief_id)`: the same read by the Debrief's id.
- `due_releases(now)` / `release_due(id, now)`: the sweep's Debrief release (AD-9).
"""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select

from app.modules.debrief import commands, rules
from app.modules.debrief.models import debrief_releases, debrief_sessions
from app.modules.debrief.schemas import DebriefOut
from app.modules.games import service as games
from app.modules.sessions import service as sessions
from app.platform import authz
from app.platform.db import get_sessionmaker

__all__ = ["NotAvailable", "due_releases", "mine", "open_mine", "release_due"]


class NotAvailable(Exception):
    """The Student's Debrief is not open: `debrief_not_open` (their game has not finished) or
    `debrief_held` (the Lecturer holds every Debrief until all Class games have finished)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


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


async def mine(user: authz.Principal, debrief_id: uuid.UUID) -> DebriefOut | None:
    """The Debrief session `debrief_id` when it is the one of the Student's own game, under the
    same availability rule; None for any other id alike."""
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
    return _out(commands.row_of(row), found.game)


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
