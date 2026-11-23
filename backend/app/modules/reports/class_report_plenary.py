"""«Alle spill i plenum» (Story 14.6, FR-86, AD-12, AD-13, AD-14): every Class game of a Class
session for the projector, without names and without ranking.

`plenary(user, class_session_id)` is the one read. It follows the Oversikt's policy
(`class_sessions.overview`: the Lecturers and Assistant lecturers of the Class); anyone else and
a Class session that does not exist get None, the route's 403 `forbidden` (FR-5).

The games are the Klasserapport's scope (`class_report._class_games`: the Class games of this
Class session, none for a Control test; the Epic 13 merge relinks it to
`reports.scope.reporting_games`), so lecturer test Games, simulations, make-up games and Replays
are never listed; games without a number are left out. Each game's stored Week states give its
Netto lager per Role and opened Week, and its Decision log its Orders (`games.class_played`).

The answer is keyed by game number only and holds no name, id, occupant, status, wait, cost or
result (AD-14): it is a dedicated read, so the page never calls the staff overview endpoints.
Games stay in game-number order, so nothing ranks them (UX-DR72). A fixed number of queries
whatever the number of games (NFR-3), and no write.
"""

import uuid

from app.analysis.wall import PlayedGame
from app.engine.settings import ROLES
from app.modules.games import service as games
from app.modules.reports.class_report import _class_games
from app.modules.reports.class_report_plenary_schemas import (
    PlenaryGameOut,
    PlenaryOut,
    PlenaryRoleOut,
)
from app.modules.sessions import service as sessions
from app.platform import authz
from app.platform.db import get_sessionmaker

__all__ = ["READ", "plenary"]

READ = "class_sessions.overview"
"""The Oversikt's policy: the plenary is shown from the Oversikt, by its readers."""


async def plenary(user: authz.Principal, class_session_id: uuid.UUID) -> PlenaryOut | None:
    """Every Class game of the Class session per Role and Week, or None when the User may not see
    the Oversikt or the Class session does not exist: one answer for both (FR-5, NFR-7)."""
    if await sessions.staffed_session(user, class_session_id, READ) is None:
        return None
    async with get_sessionmaker()() as s:
        kind = await sessions.kind_of(class_session_id, session=s)
        listed = [
            game
            for game in await _class_games(s, class_session_id, kind == sessions.CONTROL_TEST)
            if game.number is not None
        ]
        played = await games.class_played(s, [game.game_id for game in listed], True)
    # Each listed game beside its stored play (`class_played` answers in the order asked).
    pairs = list(zip(listed, played, strict=True))
    weeks = max(
        (state.week for _, game in pairs for state in game.states if not state.finished),
        default=0,
    )
    return PlenaryOut(
        weeks=weeks,
        roles=[
            PlenaryRoleOut(
                role=role,
                games=[
                    PlenaryGameOut(
                        number=game.number,
                        net=_net(play, str(role)),
                        orders=[play.orders.get((week, str(role))) for week in range(1, weeks + 1)],
                    )
                    for game, play in pairs
                    if game.number is not None
                ],
            )
            for role in ROLES
        ],
    )


def _net(play: PlayedGame, role: str) -> list[int]:
    """The Role's Netto lager per opened Week, Uke 1 first, as the Oversikt's Matrisevegg shows it
    (`games.class_game_weeks`: the stored Week state's inventory minus backlog)."""
    states = sorted((s for s in play.states if not s.finished), key=lambda s: s.week)
    return [state.seat(role).inventory - state.seat(role).backlog for state in states]
