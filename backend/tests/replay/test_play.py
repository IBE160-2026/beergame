"""Play the Replay (Story 10.4, FR-48, FR-49, FR-14, AD-2, AD-3, AD-13, UX-DR19, UX-DR64).

The Student's started Replay opens on the Epic 6 play routes (`/api/me/games/{id}`, `/play`,
`/weeks/{w}/order`) like their Class game: the card says `replay`, its rules are the Replay's own
drawn settings, and the envelope carries `projection` from `games.policy`. Orders go through
`games.commands.place_order`; the AI players answer and the next Week opens, which Hjem's Replay
block shows. Nobody else reaches it, and it has no time proposal, Starting task or Debrief. One
Class session runs the whole chain; the steps before the quiz are recorded directly."""

import uuid

from app.modules.games import commands as games_commands
from tests.classes.test_staff import call
from tests.messaging.helpers import rows
from tests.replay.test_start import passed, start
from tests.sessions.test_play import FORBIDDEN, keys, play, running
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import _empty, clock, home, klass

__all__ = ["_empty", "clock", "klass"]


async def test_the_replay_plays_on_the_play_routes_with_the_projection(klass, monkeypatch):
    session_id, class_game, _ = await running(klass, 3)
    student = rows("SELECT id FROM users WHERE email = %s", email(0))[0][0]
    await passed(student, session_id)
    game_id = (await start(session_id, email(0))).json()["game_id"]
    [(settings,)] = rows("SELECT settings FROM games WHERE id = %s", game_id)

    # The card: the Replay, no number, its own rules, no Debrief, no briefing first.
    card = await call(email(0), "GET", f"/api/me/games/{game_id}")
    assert card.status_code == 200
    body = card.json()
    assert (body["replay"], body["test_game"], body["number"], body["status"], body["week"]) == (
        True,
        False,
        None,
        "running",
        1,
    )
    assert (body["briefing_first"], body["debrief"], body["time_proposal"]) == (False, None, None)
    # Its rules are its own drawn settings: no Guided Weeks, where the Class game has four.
    ruled = ("order_delay", "shipping_delay", "production_delay", "guided_weeks")
    assert {key: body["rules"][key] for key in ruled} == {key: settings[key] for key in ruled}
    assert (body["rules"]["holding_cost"], body["rules"]["backorder_cost"]) == (
        settings["holding_cost"],
        settings["backorder_cost"],
    )
    assert body["rules"]["guided_weeks"] == 0
    # The Class game stays a Class game, with the Class session's rules.
    class_card = (await call(email(0), "GET", f"/api/me/games/{class_game}")).json()
    assert (class_card["replay"], class_card["number"]) == (False, 1)
    assert class_card["rules"]["guided_weeks"] == 4

    # The envelope: the own Seat as Epic 6 builds it, the projection on, nothing hidden leaks.
    envelope = await play(email(0), game_id)
    assert envelope.status_code == 200
    shown = envelope.json()
    assert shown["projection"] is True
    assert (shown["seat_state"]["week"], shown["turn"]) == (
        1,
        {"guided": False, "order": None, "viewed": False},
    )
    assert sorted(seat["holder"] for seat in shown["table_status"]["seats"]) == [
        "ai",
        "ai",
        "ai",
        "student",
    ]
    assert not keys(shown) & FORBIDDEN
    assert (await play(email(0), class_game)).json()["projection"] is False

    # An Order only through `games.commands.place_order`, with the Student as actor (AD-2).
    placed = []
    real = games_commands.place_order

    async def recording(*args, **kwargs):
        placed.append((args, kwargs.get("actor")))
        return await real(*args, **kwargs)

    monkeypatch.setattr(games_commands, "place_order", recording)
    ordered = await call(
        email(0), "POST", f"/api/me/games/{game_id}/weeks/1/order", json={"order": 12}
    )
    monkeypatch.setattr(games_commands, "place_order", real)
    assert ordered.status_code == 204
    # The Student's Order first; the AI players' Orders follow through the same command.
    assert (placed[0][0][2:5], placed[0][1]) == ((1, 12, "student"), student)
    assert [args[4] for args, _ in placed[1:]] and all(
        args[4] != "student" for args, _ in placed[1:]
    )
    again = await call(
        email(0), "POST", f"/api/me/games/{game_id}/weeks/1/order", json={"order": 12}
    )
    assert (again.status_code, again.json()["error"]["code"]) == (409, "order_exists")

    # The AI players answered, so Uke 2 is open: the envelope, the card and Hjem agree (UX-DR64).
    after = (await play(email(0), game_id)).json()
    assert after["seat_state"]["week"] == 2
    assert [row["order"] for row in after["seat_state"]["history"]] == [12]
    assert (await call(email(0), "GET", f"/api/me/games/{game_id}")).json()["week"] == 2
    replay = (await home(email(0)))["replay"]["game"]
    assert (replay["id"], replay["status"], replay["week"]) == (game_id, "running", 2)

    # Nobody else reaches it (FR-5), not even classmates of the same Class session.
    for who in (email(1), email(2)):
        for path in ("", "/play", "/result"):
            refused = await call(who, "GET", f"/api/me/games/{game_id}{path}")
            assert refused.status_code == 403, (who, path)
        refused = await call(
            who, "POST", f"/api/me/games/{game_id}/weeks/2/order", json={"order": 1}
        )
        assert refused.status_code == 403

    # No group to agree a time with, no Starting task (as a test Game, Story 6.20).
    proposal = await call(
        email(0),
        "POST",
        f"/api/me/games/{game_id}/time-proposal",
        json={"at": "2026-12-01T10:00:00Z"},
    )
    assert proposal.status_code == 403
    accept = await call(
        email(0), "POST", f"/api/me/games/{game_id}/time-proposal/{uuid.uuid4()}/accept"
    )
    assert accept.status_code == 403
    task = await call(email(0), "GET", f"/api/me/games/{game_id}/starting-task")
    assert task.status_code == 403
