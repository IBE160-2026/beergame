"""A Replay with Information visibility on (Story 10.9, cut list, FR-83, AD-3, AD-4, AD-17): the
own scenario's views, frozen by the lock's pin, are in the Replay's snapshot settings; the
Student's `seat_state` holds the neighbours' numbers, the AI players' Orders are made from the
same `seat_state`, and the Decision log records what each Seat saw. With the flag off nothing
shows. One Class session, one Student, one Week."""

from app.modules.games import service as games_service
from app.modules.ops import sweep
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call
from tests.games.test_neighbour_numbers import NEIGHBOURS
from tests.games.test_neighbour_numbers import flag as views_flag
from tests.messaging.helpers import rows
from tests.replay.test_start import passed, start
from tests.sessions.test_dates import START
from tests.sessions.test_lock import MINUTE, _empty
from tests.sessions.test_open_games import confirmed
from tests.sessions.test_play import play
from tests.sessions.test_replay_own import own, save
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "klass"]

BOTH = {"upstream": True, "downstream": True}


async def test_a_replay_with_views_shows_and_records_the_neighbours_numbers(klass, monkeypatch):
    views_flag(monkeypatch, True)
    session_id, seated = await confirmed(klass, 1)
    saved = await save(session_id, "own", own(info_visibility=BOTH))
    assert saved.status_code == 200, saved.text
    assert saved.json()["game_settings"]["info_visibility"]["upstream"] is False
    await sweep.run(START + MINUTE)  # the lock pins the own template
    await passed(seated[0], session_id)
    game_id = (await start(session_id, email(0))).json()["game_id"]
    [(settings,)] = rows("SELECT settings FROM games WHERE id = %s", game_id)
    assert settings["info_visibility"] == BOTH

    envelope = (await play(email(0), game_id)).json()
    state = envelope["seat_state"]
    role = next(seat.role for seat in (await games_service.get_game(game_id)).seats if seat.user_id)
    assert [n["role"] for n in state["neighbour_numbers"]][::2] == NEIGHBOURS[role]
    assert {n["quantity"] for n in state["neighbour_numbers"]} == {"inventory", "backlog"}

    ordered = await call(
        email(0), "POST", f"/api/me/games/{game_id}/weeks/1/order", json={"order": 8}
    )
    assert ordered.status_code == 204
    logged = await games_service.decision_log(game_id)
    assert {row.role for row in logged} == set(NEIGHBOURS)  # the Student and three AI players
    for row in logged:
        assert [n.role for n in row.state_seen.neighbour_numbers][::2] == NEIGHBOURS[row.role]

    # The flag off: the same Replay shows no neighbour (AD-17).
    views_flag(monkeypatch, False)
    assert (await play(email(0), game_id)).json()["seat_state"]["neighbour_numbers"] == []
