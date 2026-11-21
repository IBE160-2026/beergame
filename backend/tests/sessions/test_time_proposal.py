"""The scheduling aid (Story 6.19, FR-22, AD-2, AD-8, AD-9, AD-20): a Student of a Class game
proposes a time to play, a date and a time only, between now and the Play deadline; the game keeps
one open proposal, a new one replaces it and its acceptances; the other Students are told by a
`digest` notice per proposal and accept with one press; Hjem and the play route show who proposed
which time and who accepted, until the time has passed or the game has finished. The proposal is
no input of `turn_times`: `seat_turns` never changes.

Every time here is read from the database clock (Issue #63); the Play deadline is set from it."""

import uuid
from datetime import datetime

from app.modules.sessions import service
from app.platform.db import get_sessionmaker
from tests.classes.test_classes import make
from tests.classes.test_staff import call
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import execute, query
from tests.sessions.test_dates import OUTSIDER
from tests.sessions.test_game_end import (
    WEEKS,
    _empty,
    clock,
    emitted,
    klass,
    play_weeks,
    short_game,
)
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import game_of, home

__all__ = ["_empty", "clock", "emitted", "klass"]


def db_time(interval: str) -> datetime:
    """`now() + interval` on the database clock."""
    [(at,)] = query(TEST_DATABASE_URL, "SELECT now() + %s::interval", (interval,))
    return at


def deadline_in(session_id: str, interval: str) -> datetime:
    """Move the Class session's deadlines, in order, so the Play deadline lies `interval` ahead
    on the database clock; returns it."""
    execute(
        TEST_DATABASE_URL,
        "UPDATE class_sessions SET start_at = LEAST(start_at, now() - interval '1 day'), "
        "play_deadline = now() + %s::interval, "
        "debrief_deadline = now() + %s::interval + interval '1 day', "
        "test_deadline = now() + %s::interval + interval '2 days' WHERE id = %s",
        (interval, interval, interval, session_id),
    )
    [(at,)] = query(
        TEST_DATABASE_URL, "SELECT play_deadline FROM class_sessions WHERE id = %s", (session_id,)
    )
    return at


async def propose(who: str, game_id: str, at: datetime | str):
    value = at if isinstance(at, str) else at.isoformat()
    return await call(who, "POST", f"/api/me/games/{game_id}/time-proposal", json={"at": value})


async def accept(who: str, game_id: str, proposal_id: str):
    return await call(who, "POST", f"/api/me/games/{game_id}/time-proposal/{proposal_id}/accept")


def refusal(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def notices() -> list[tuple[str, uuid.UUID]]:
    found = query(
        TEST_DATABASE_URL,
        "SELECT dedupe_key, user_id FROM notices WHERE kind = 'time_proposed' ORDER BY id",
    )
    return [(key, user) for key, user in found]


def seat_turns(game_id: str) -> list[tuple]:
    return query(
        TEST_DATABASE_URL, "SELECT * FROM seat_turns WHERE game_id = %s ORDER BY id", (game_id,)
    )


async def test_a_proposal_tells_the_others_who_accept_and_a_new_one_replaces_it(klass, emitted):
    session_id, game_id, seated = await short_game(klass)
    deadline_in(session_id, "7 days")
    before = seat_turns(game_id)
    at = db_time("1 day")
    emitted.clear()
    response = await propose(email(0), game_id, at)
    assert response.status_code == 200
    mine = response.json()["time_proposal"]
    assert mine["proposed_by"]["mine"] and not mine["can_accept"] and mine["accepted_by"] == []
    assert datetime.fromisoformat(mine["at"]) == at
    first = mine["id"]
    # One `digest` notice for the other Student, keyed by the proposal; their Hjem reads again.
    assert notices() == [(f"time_proposed:{first}:{seated[1]}", seated[1])]
    assert {("game", game_id), ("session", session_id)} | {
        ("user", str(each)) for each in seated
    } <= set(emitted)
    # The other Student sees it by name, on Hjem and on the play route alike, and accepts.
    seen = (await home(email(1)))["game"]["time_proposal"]
    assert seen["proposed_by"]["name"] and not seen["proposed_by"]["mine"] and seen["can_accept"]
    assert (await game_of(email(1), game_id)).json()["time_proposal"] == seen
    emitted.clear()
    accepted = await accept(email(1), game_id, first)
    assert accepted.status_code == 200
    body = accepted.json()["time_proposal"]
    assert [(p["name"] is not None, p["mine"]) for p in body["accepted_by"]] == [(True, True)]
    assert not body["can_accept"]
    assert {("game", game_id)} | {("user", str(each)) for each in seated} <= set(emitted)
    # Its mail, read at send time, asks nothing of a Student who has accepted meanwhile.
    async with get_sessionmaker()() as s:
        now = db_time("0 seconds")
        assert await service.time_proposal_mail_context(s, seated[1], uuid.UUID(first), now) is None
    # The proposer sees who accepted.
    theirs = (await home(email(0)))["game"]["time_proposal"]
    assert [(p["name"] is not None, p["mine"]) for p in theirs["accepted_by"]] == [(True, False)]
    # A second press is done already and emits nothing; the proposer cannot accept their own.
    emitted.clear()
    assert (await accept(email(1), game_id, first)).status_code == 200
    assert ("game", game_id) not in set(emitted)
    assert refusal(await accept(email(0), game_id, first)) == (409, "own_proposal")

    # A new proposal replaces the old one and its acceptances.
    second = (await propose(email(1), game_id, db_time("2 days"))).json()["time_proposal"]
    assert second["id"] != first and second["accepted_by"] == []
    assert query(TEST_DATABASE_URL, "SELECT count(*) FROM time_acceptances") == [(0,)]
    shown = (await home(email(0)))["game"]["time_proposal"]
    assert shown["id"] == second["id"] and shown["can_accept"]
    assert refusal(await accept(email(0), game_id, first)) == (409, "proposal_gone")
    assert [key for key, _ in notices()] == [
        f"time_proposed:{first}:{seated[1]}",
        f"time_proposed:{second['id']}:{seated[0]}",
    ]
    # The mail reads the proposal at send time: the replaced one sends nothing.
    now = db_time("0 seconds")
    async with get_sessionmaker()() as s:
        assert await service.time_proposal_mail_context(s, seated[1], uuid.UUID(first), now) is None
        context = await service.time_proposal_mail_context(
            s, seated[0], uuid.UUID(second["id"]), now
        )
    assert context is not None and context["proposer"] and context["class_name"]
    assert context["game_number"] >= 1 and context["at"].utcoffset() is not None
    # AD-20: no command of the scheduling aid touched a turn.
    assert seat_turns(game_id) == before
    # Any other game is refused alike (FR-5).
    await make(OUTSIDER, roles=())
    for path in ("time-proposal", f"time-proposal/{second['id']}/accept"):
        refused = await call(
            OUTSIDER, "POST", f"/api/me/games/{game_id}/{path}", json={"at": at.isoformat()}
        )
        assert refused.status_code == 403


async def test_only_a_time_from_now_to_the_play_deadline_and_none_once_passed_or_finished(klass):
    session_id, game_id, _ = await short_game(klass, students=1)
    deadline = deadline_in(session_id, "3 days")
    for at in (db_time("-1 minute"), db_time("3 days 1 minute")):
        assert refusal(await propose(email(0), game_id, at)) == (422, "time_out_of_range")
    assert (await propose(email(0), game_id, "2026-12-01T14:15:00")).status_code == 422  # naive
    answer = await propose(email(0), game_id, deadline)  # the deadline itself
    assert answer.status_code == 200
    assert notices() == []  # nobody else holds a Seat
    # A time that has passed is no longer shown, nor open.
    execute(TEST_DATABASE_URL, "UPDATE time_proposals SET at = now() - interval '1 minute'")
    assert (await home(email(0)))["game"]["time_proposal"] is None
    passed = answer.json()["time_proposal"]["id"]
    assert refusal(await accept(email(0), game_id, passed)) == (409, "proposal_gone")
    # Nor once the game has finished.
    assert (await propose(email(0), game_id, db_time("1 day"))).status_code == 200
    await play_weeks(game_id, WEEKS)
    item = await home(email(0))
    assert item["game"]["status"] == "finished" and item["game"]["time_proposal"] is None
    assert refusal(await propose(email(0), game_id, db_time("1 day"))) == (409, "game_finished")
