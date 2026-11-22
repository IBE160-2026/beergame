"""Story 8.6 through the api: a Student presses «Ta pause» (`POST /api/me/games/{id}/pause`); every
Student of the game reads the pause line on Hjem and Spill, the Oversikt groups the game as paused
with since when and by whom, counts it in «herav n pauset» and leaves it out of the Varselbånd; a
second Student's Order ends it, and the line then names who ordered (FR-89, FR-39, AD-2, AD-12).

One short Class game (`short_game`: three Students, Uke 1 Guided) per test."""

import uuid

from app.modules.games import service as games_service
from app.modules.sessions import overview as sessions_overview
from app.modules.sessions.schemas import WallStatus
from app.platform.db import get_sessionmaker
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_staff import call
from tests.messaging.helpers import rows
from tests.sessions.test_dates import OUTSIDER
from tests.sessions.test_game_end import _empty, clock, klass, short_game
from tests.sessions.test_orders import code, order
from tests.sessions.test_overview import overview
from tests.sessions.test_play import play
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import home

__all__ = ["_empty", "clock", "klass"]


async def pause(who: str, game_id: str):
    return await call(who, "POST", f"/api/me/games/{game_id}/pause")


def name_of(address: str) -> str:
    return rows("SELECT name FROM users WHERE email = %s", address)[0][0]


async def three_students_in_uke_2(klass: str) -> tuple[str, str, dict[str, str]]:
    """The short game with three Students, each past the Guided Uke 1: (session, game, email by
    Role)."""
    session_id, game_id, _ = await short_game(klass, students=3)
    by_role = {(await home(email(i)))["game"]["role"]: email(i) for i in range(3)}
    for who in by_role.values():
        assert (await call(who, "POST", f"/api/me/games/{game_id}/weeks/1/view")).status_code == 204
    return session_id, game_id, by_role


async def test_a_student_pauses_and_another_students_order_ends_it(klass):
    session_id, game_id, by_role = await three_students_in_uke_2(klass)
    sara, jonas, third = by_role.values()
    before = await home(sara)
    assert (before["game"]["can_pause"], before["game"]["pause"]) == (True, None)

    answer = await pause(sara, game_id)
    assert answer.status_code == 200
    assert (answer.json()["can_pause"], answer.json()["pause"]) == (
        False,
        {"state": "paused", "name": name_of(sara), "mine": True, "staff": False, "resume_at": None},
    )
    # Every Student of the game reads the line, on Hjem and on Spill.
    for who in (jonas, third):
        game = (await home(who))["game"]
        assert (game["can_pause"], game["pause"]) == (
            False,
            {
                "state": "paused",
                "name": name_of(sara),
                "mine": False,
                "staff": False,
                "resume_at": None,
            },
        )
        status = (await play(who, game_id)).json()["table_status"]
        assert status["pause"] == {
            "state": "paused",
            "name": name_of(sara),
            "mine": False,
            "staff": False,
            "resume_at": None,
        }

    # A second press is told who came first, by kind and id.
    again = await pause(jonas, game_id)
    assert code(again) == (409, "already_paused")
    [(sara_id,)] = rows("SELECT id FROM users WHERE email = %s", sara)
    assert again.json()["error"]["fields"]["acted_by"] == {
        "kind": "student",
        "user_id": str(sara_id),
    }

    # The Oversikt: paused, since when and by whom; counted as running; not in the Varselbånd.
    body = (await overview(LECTURER, session_id)).json()
    [listed] = [g for g in body["items"] if g["game_id"] == game_id]
    assert (listed["status"], listed["paused_by"], listed["waiting_for"]) == (
        "paused",
        name_of(sara),
        [],
    )
    assert listed["paused_at"]
    assert (body["counts"]["running"], body["counts"]["paused"]) == (1, 1)
    assert body["alert"] is None
    # The wall's Status filter has «Pause n» of its own (Epic 8 close-out): «Pågår» leaves the
    # paused game out, though the headline still counts it («1 pågår (herav 1 pauset)»).
    async with get_sessionmaker()() as s:
        [summary] = [
            g
            for g in await games_service.class_overview(s, uuid.UUID(session_id))
            if str(g.game_id) == game_id
        ]
    assert sessions_overview._matches(summary, WallStatus.PAUSED)
    assert not sessions_overview._matches(summary, WallStatus.RUNNING)
    assert not sessions_overview._matches(summary, WallStatus.WAITING)
    assert listed["resume_at"] is None  # a Student's Pause has no agreed time

    # Jonas orders Uke 2: the Pause ends, and the line names who ordered until Uke 3 opens.
    assert (await order(jonas, game_id, 2, {"order": 4})).status_code in (200, 204)
    for who, mine in ((sara, False), (jonas, True), (third, False)):
        game = (await home(who))["game"]
        assert game["pause"] == {
            "state": "ended",
            "name": name_of(jonas),
            "mine": mine,
            "staff": False,
            "resume_at": None,
        }
    assert (await home(sara))["game"]["can_pause"] is True
    body = (await overview(LECTURER, session_id)).json()
    [listed] = [g for g in body["items"] if g["game_id"] == game_id]
    assert (listed["status"], listed["paused_at"]) == ("waiting", None)
    assert body["counts"]["paused"] == 0

    # The Week opens: the ended line is gone.
    for who in (sara, third):
        assert (await order(who, game_id, 2, {"order": 4})).status_code in (200, 204)
    assert (await home(sara))["game"]["pause"] is None


async def test_only_a_student_of_the_game_may_pause_it(klass):
    _, game_id, _ = await short_game(klass)
    await make(OUTSIDER, roles=())
    assert code(await pause(OUTSIDER, game_id)) == (403, "forbidden")
    assert code(await pause(LECTURER, game_id)) == (403, "forbidden")
    assert code(await pause(email(0), str(uuid.uuid7()))) == (403, "forbidden")
    assert rows("SELECT paused_at FROM games WHERE id = %s", game_id) == [(None,)]
