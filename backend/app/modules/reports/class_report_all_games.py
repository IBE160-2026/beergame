"""«Alle spill side om side» (Story 14.5, FR-86, AD-12, AD-13, AD-14, AD-16): every Class game's
Orders per Role and Week beside the Student's own, once their Debrief is done and the Play
deadline has passed.

`class_games(user, class_session_id, now)` is the one read. The gate, in this order:

- the Class session is one of the Student's own locked ones (`sessions.enrolled_locked_row`),
  else None (the route's 403 `forbidden`, one answer for every other case, FR-5);
- their Debrief step (`progress.has_step`) and the session's Play deadline passed
  (`sessions.play_deadline_passed`), else `Locked` (403 `all_games_locked`). Hjem's
  `all_games_open` asks the same two things.

The games are the Klasserapport's scope (`class_report._class_games`: the Class games of this
Class session, none for a Control test; the Epic 13 merge relinks it to
`reports.scope.reporting_games`), so lecturer test Games, simulations, make-up games and Replays
are never listed. The Student's own game is `games.student_game` (the Seat held now, else the one
held last: a Student whose Seat was taken over keeps the Class game they were allocated to).

The answer is keyed by game number only and holds no name, id, occupant, cost or result (AD-14);
games stay in game-number order, so nothing ranks them (UX-DR72). A fixed number of queries
whatever the number of games (NFR-3), and no write.
"""

import uuid
from datetime import datetime

from app.engine.settings import ROLES
from app.modules.games import service as games
from app.modules.progress import service as progress
from app.modules.reports.class_report import _class_games
from app.modules.reports.class_report_all_games_schemas import (
    ClassGamesOut,
    GameOrdersOut,
    RoleOrdersOut,
)
from app.modules.sessions import service as sessions
from app.platform import authz
from app.platform.db import get_sessionmaker

__all__ = ["OWN", "Locked", "class_games"]

OWN = "all_games.own"
"""Any User; the read holds them to their own locked Class session."""


class Locked(Exception):
    """The view is not open yet: the Student's Debrief is not done or the Play deadline has not
    passed (403 `all_games_locked`)."""

    code = "all_games_locked"


async def class_games(
    user: authz.Principal, class_session_id: uuid.UUID, now: datetime
) -> ClassGamesOut | None:
    """Every Class game of the Student's Class session side by side, or None when it is not one
    of their own locked Class sessions. Raises `Locked` while the view is closed."""
    async with get_sessionmaker()() as s:
        row = await sessions.enrolled_locked_row(s, user, class_session_id)
        if row is None:
            return None
        debriefed = await progress.has_step(user.id, class_session_id, progress.Step.DEBRIEF)
        if not (debriefed and sessions.play_deadline_passed(row, now)):
            raise Locked
        kind = await sessions.kind_of(class_session_id, session=s)
        listed = [
            game
            for game in await _class_games(s, class_session_id, kind == sessions.CONTROL_TEST)
            if game.number is not None
        ]
        own = await games.student_game(s, user.id, class_session_id)
        orders = await games.class_orders(s, [game.game_id for game in listed])
    own_id = own.game_id if own is not None else None
    weeks = max(
        (week for by_role in orders.values() for by_week in by_role.values() for week in by_week),
        default=0,
    )
    roles = [
        RoleOrdersOut(
            role=role,
            games=[
                GameOrdersOut(
                    number=game.number,
                    own=game.game_id == own_id,
                    orders=[
                        orders.get(game.game_id, {}).get(str(role), {}).get(week)
                        for week in range(1, weeks + 1)
                    ],
                )
                for game in listed
                if game.number is not None
            ],
        )
        for role in ROLES
    ]
    own_game = next((game.number for game in listed if game.game_id == own_id), None)
    return ClassGamesOut(weeks=weeks, own_game=own_game, roles=roles)
