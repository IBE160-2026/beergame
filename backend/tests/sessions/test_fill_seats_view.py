"""Story 8.12 through the api: a Lecturer fills every waited-for Seat of one Class game (the list
on Spillinnsikt) or of all of them (`GET`/`POST /api/class-sessions/{id}/waited-for-seats`), one
staff `takeover` per Seat with `only_waited_for`; the Oversikt counts them from the same summary
rows as «Venter»; Seats with Tilrettelegging are left out; a Seat that ordered since is skipped and
a repeat inserts nothing twice; a failure in one Game stops no other (FR-24, FR-37, AD-2, AD-5,
AD-12, AD-15, UX-DR52). One Class session with two short games serves the whole flow."""

import asyncio
import json
import uuid

import pytest

from app.modules.games import commands as games_commands
from app.modules.games import service as games_service
from app.modules.ops import sweep
from app.modules.sessions import overview as sessions_overview
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import class_game_copies
from tests.messaging.helpers import rows
from tests.sessions.test_adjustment import save, user_id
from tests.sessions.test_dates import OUTSIDER, START
from tests.sessions.test_game_end import _empty, clock, klass
from tests.sessions.test_game_insight import insight
from tests.sessions.test_lock import MINUTE
from tests.sessions.test_open_games import confirmed
from tests.sessions.test_orders import code
from tests.sessions.test_overview import overview
from tests.sessions.test_staff_takeover_view import take_over
from tests.sessions.test_start_game import task_done

__all__ = ["_empty", "clock", "klass"]


def path(session_id: str) -> str:
    return f"/api/class-sessions/{session_id}/waited-for-seats"


async def page(who: str, session_id: str):
    return await call(who, "GET", path(session_id))


async def fill(who: str, session_id: str, seat_ids: list[str]):
    return await call(who, "POST", path(session_id), json={"seat_ids": seat_ids})


def seating(session_id: str) -> dict[str, list[tuple[str, str, str]]]:
    """Each game's Students now: game id → [(email, user id, seat id)] in chain order."""
    found: dict[str, list[tuple[str, str, str]]] = {}
    for game_id, address, user, seat in rows(
        "SELECT DISTINCT ON (s.id) g.id::text, u.email, u.id::text, s.id::text FROM seats s "
        "JOIN games g ON g.id = s.game_id JOIN seat_occupancy o ON o.seat_id = s.id "
        "JOIN users u ON u.id = o.user_id WHERE g.class_session_id = %s "
        "ORDER BY s.id, o.from_week DESC, o.created_at DESC",
        session_id,
    ):
        found.setdefault(game_id, []).append((address, user, seat))
    return found


def staff_rows(seat_id: str) -> list[tuple]:
    return rows(
        "SELECT reason, actor_user_id::text FROM seat_occupancy WHERE seat_id = %s "
        "AND reason = 'takeover_staff'",
        seat_id,
    )


def ids(listed: list[dict]) -> list[str]:
    return [seat["seat_id"] for seat in listed]


async def two_games(klass: str, lecturer: str) -> tuple[str, list, list]:
    """Two started short games, one with four Students and one with two, in the Guided Uke 1:
    (session, the four, the two), each Student as (email, user id, Seat id)."""
    session_id, seated = await confirmed(klass, 6)
    execute(
        "UPDATE class_sessions SET game_settings = game_settings || %s::jsonb WHERE id = %s",
        json.dumps({"weeks": 6, "guided_weeks": 1}),
        session_id,
    )
    await sweep.run(START + MINUTE)
    for user in seated:
        await task_done(user, session_id)
    by_game = seating(session_id)
    for game_id in by_game:
        await games_commands.start(game_id, actor=lecturer)
    four, two = sorted(by_game.values(), key=len, reverse=True)
    assert (len(four), len(two)) == (4, 2), by_game
    return session_id, four, two


def game_of(seat_id: str) -> str:
    return rows("SELECT game_id::text FROM seats WHERE id = %s", seat_id)[0][0]


async def view(who: tuple[str, str, str]) -> None:
    await games_commands.view_week(game_of(who[2]), who[2], 1, actor=who[1])


async def place(who: tuple[str, str, str], week: int) -> None:
    await games_commands.place_order(game_of(who[2]), who[2], week, 5, "student", actor=who[1])


async def test_a_lecturer_fills_the_waited_for_seats_of_one_game_and_of_all(klass, monkeypatch):
    lecturer = user_id(LECTURER)
    session_id, (a1, a2, a3, a4), (b1, b2) = await two_games(klass, lecturer)
    game_a, game_b = game_of(a1[2]), game_of(b1[2])
    assistant = await make(ASSISTANT, roles=())
    put_staff(klass, assistant, "assistant")
    await make(OUTSIDER, roles=())
    assert (await save(LECTURER, session_id, a3[1], {"time_factor": 2})).status_code == 200

    # Nobody has viewed Uke 1: no game waits, nothing to fill.
    assert (await overview(LECTURER, session_id)).json()["fillable"] == 0
    assert (await fill(LECTURER, session_id, [b2[2]])).json() == {
        "inserted": 0,
        "skipped": [{"seat_id": b2[2], "reason": "not_waited_for"}],
    }

    # Game A, a Guided Week: the first view starts the wait of the other three.
    await view(a1)
    seen = (await insight(LECTURER, game_a)).json()
    assert sorted(ids(seen["waited_for"])) == sorted([a2[2], a4[2]])
    assert ids(seen["left_out"]) == [a3[2]] and seen["left_out"][0]["name"]
    other = (await insight(ASSISTANT, game_a)).json()
    assert (other["waited_for"], other["left_out"]) == ([], [])
    assert (await overview(ASSISTANT, session_id)).json()["fillable"] == 0
    assert (await overview(LECTURER, session_id)).json()["fillable"] == 2
    # A Seat with Tilrettelegging is never taken by the fill, even when posted.
    answer = await fill(LECTURER, session_id, [a2[2], a3[2]])
    assert answer.json() == {
        "inserted": 1,
        "skipped": [{"seat_id": a3[2], "reason": "tilrettelegging"}],
    }
    assert staff_rows(a2[2]) == [("takeover_staff", lecturer)]
    # Story 8.2's effects: the AI player's Order stands this Week and every Student is told.
    [(ordered,)] = rows(
        "SELECT ordered_at IS NOT NULL FROM seat_turns WHERE seat_id = %s AND week = 1", a2[2]
    )
    assert ordered
    told = rows(
        "SELECT DISTINCT user_id::text FROM notices WHERE kind = 'takeover_notice' "
        "AND ref = (SELECT id FROM seat_occupancy WHERE seat_id = %s "
        "AND reason = 'takeover_staff')",
        a2[2],
    )
    assert sorted(user for (user,) in told) == sorted(x[1] for x in (a1, a2, a3, a4))
    # The other two view: the AI player's Guided Order stands, and the game moves to Uke 2.
    await view(a3)
    await view(a4)
    assert (await insight(LECTURER, game_a)).json()["waited_for"] == []

    # Uke 2: one Order in each game starts the wait of the others.
    for who in (b1, b2):
        await view(who)
    await place(b1, 2)
    await place(a1, 2)  # Game A waits for a3 (Tilrettelegging) and a4.

    body = (await overview(LECTURER, session_id)).json()
    assert body["fillable"] == 2
    assert body["counts"]["waiting"] == 2  # «Venter» reads the same summary rows
    listed = (await page(LECTURER, session_id)).json()
    assert {g["game_id"]: ids(g["seats"]) for g in listed["games"]} == {
        game_a: [a4[2]],
        game_b: [b2[2]],
    }
    numbers = [g["game_number"] for g in listed["games"]]
    assert numbers == sorted(numbers)
    assert ids(listed["left_out"]) == [a3[2]]
    assert all(seat["since"] and seat["name"] for g in listed["games"] for seat in g["seats"])
    assert listed["server_now"] and listed["class_session_id"] == session_id
    for who in (ASSISTANT, OUTSIDER, b1[0]):
        assert code(await page(who, session_id)) == (403, "forbidden")
        assert code(await fill(who, session_id, [b2[2]])) == (403, "forbidden")

    # A paused game is not filled, under the lock too.
    await games_commands.pause(game_b, actor=lecturer, staff=True)
    assert (await overview(LECTURER, session_id)).json()["fillable"] == 1
    assert (await fill(LECTURER, session_id, [b2[2]])).json() == {
        "inserted": 0,
        "skipped": [{"seat_id": b2[2], "reason": "game_paused"}],
    }
    await games_commands.resume(game_b, actor=lecturer)

    # a4 orders before the press: skipped; a Seat of no game of the session: not listed.
    await place(a4, 2)
    foreign = str(uuid.uuid4())
    answer = await fill(LECTURER, session_id, [a4[2], b2[2], foreign])
    assert answer.json() == {
        "inserted": 1,
        "skipped": [
            {"seat_id": foreign, "reason": "not_listed"},
            {"seat_id": a4[2], "reason": "order_exists"},
        ],
    }
    assert staff_rows(b2[2]) == [("takeover_staff", lecturer)]
    audited = rows(
        "SELECT count(*) FROM audit_events WHERE action = 'seat.taken_over' AND actor_user_id = %s",
        lecturer,
    )
    assert audited == [(2,)]
    # A repeat inserts nothing twice.
    again = await fill(LECTURER, session_id, [a2[2], b2[2]])
    assert again.json() == {
        "inserted": 0,
        "skipped": [
            {"seat_id": a2[2], "reason": "takeover_exists"},
            {"seat_id": b2[2], "reason": "takeover_exists"},
        ],
    }
    assert len(staff_rows(b2[2])) == 1
    assert (await overview(LECTURER, session_id)).json()["fillable"] == 0
    # The per-Seat action of Story 8.5 still reaches a Seat with Tilrettelegging, for an
    # Assistant lecturer too.
    [(role,)] = rows("SELECT role FROM seats WHERE id = %s", a3[2])
    assert (await take_over(ASSISTANT, game_a, role)).status_code == 200
    assert staff_rows(a3[2]) == [("takeover_staff", user_id(ASSISTANT))]

    # A failure in one Game neither undoes nor stops the others.
    called: list[str] = []

    async def takeover(game_id: str, seat: str, **kw) -> str:
        called.append(seat)
        if game_id == game_a:
            raise RuntimeError("down")
        if seat == b2[2]:
            raise games_commands.CommandError("order_exists", "ordered", 409)
        return "row"

    async def seat_games(s, session, seat_ids):
        return {
            uuid.UUID(a1[2]): uuid.UUID(game_a),
            **{uuid.UUID(x[2]): uuid.UUID(game_b) for x in (b1, b2)},
        }

    monkeypatch.setattr(games_commands, "takeover", takeover)
    monkeypatch.setattr(games_service, "class_seat_games", seat_games)
    answer = await fill(LECTURER, session_id, [a1[2], b1[2], b2[2]])
    assert answer.status_code == 200
    body = answer.json()
    assert body["inserted"] == 1
    assert sorted((x["seat_id"], x["reason"]) for x in body["skipped"]) == sorted(
        [(a1[2], "failed"), (b2[2], "order_exists")]
    )
    assert sorted(called) == sorted([a1[2], b1[2], b2[2]])

    # At most four Games at a time, and the Seats of one Game one after another.
    games = [uuid.uuid4() for _ in range(6)]
    seats = {uuid.uuid4(): game for game in games for _ in range(2)}
    running: dict[str, int] = {}
    peak = {"all": 0, "one_game": 0}

    async def counted(game_id: str, seat: str, **kw) -> str:
        running[game_id] = running.get(game_id, 0) + 1
        peak["all"] = max(peak["all"], sum(running.values()))
        peak["one_game"] = max(peak["one_game"], running[game_id])
        await asyncio.sleep(0.01)
        running[game_id] -= 1
        return "row"

    async def many_games(s, session, seat_ids):
        return seats

    monkeypatch.setattr(games_commands, "takeover", counted)
    monkeypatch.setattr(games_service, "class_seat_games", many_games)
    answer = await fill(LECTURER, session_id, [str(seat) for seat in seats])
    assert answer.json() == {"inserted": 12, "skipped": []}
    assert peak == {"all": sessions_overview.BATCH_FILL_CONCURRENCY, "one_game": 1}


@pytest.mark.long
async def test_a_hundred_class_games_fill_in_one_action(klass, monkeypatch):
    lecturer = user_id(LECTURER)
    session_id, seated = await confirmed(klass, 4)  # one Class game, four Students
    execute(
        "UPDATE class_sessions SET game_settings = game_settings || %s::jsonb WHERE id = %s",
        json.dumps({"weeks": 6, "guided_weeks": 0}),
        session_id,
    )
    await sweep.run(START + MINUTE)
    for user in seated:
        await task_done(user, session_id)
    [(game_id, students)] = seating(session_id).items()
    await games_commands.start(game_id, actor=lecturer)
    for student in students[:3]:
        await place(student, 1)  # the game waits for the fourth: one Seat per game keeps it quick
    keep = {session_id, lecturer, *(student[1] for student in students)}
    copies = class_game_copies(TEST_DATABASE_URL, session_id, game_id, range(2, 101), keep)
    games = [game_id, *copies]
    holder = dict(
        rows(
            "SELECT s.role, o.user_id::text FROM seats s JOIN seat_occupancy o ON o.seat_id = s.id "
            "WHERE s.game_id = %s AND o.user_id IS NOT NULL",
            game_id,
        )
    )

    assert (await overview(LECTURER, session_id)).json()["fillable"] == 100
    listed = (await page(LECTURER, session_id)).json()
    assert sorted(g["game_id"] for g in listed["games"]) == sorted(games)
    ids = [seat["seat_id"] for g in listed["games"] for seat in g["seats"]]
    assert len(ids) == 100
    # Ten Seats order between the listing and the press; one Game fails.
    late = [(g["game_id"], g["seats"][0]) for g in listed["games"][:10]]
    for game, seat in late:
        await games_commands.place_order(
            game, seat["seat_id"], 1, 5, "student", actor=holder[seat["role"]]
        )
    broken = listed["games"][50]["game_id"]
    original = games_commands.takeover

    async def takeover(game: str, seat: str, **kw) -> str:
        if game == broken:
            raise RuntimeError("the database went away")
        return await original(game, seat, **kw)

    monkeypatch.setattr(games_commands, "takeover", takeover)
    answer = await fill(LECTURER, session_id, ids)
    assert answer.status_code == 200
    body = answer.json()
    reasons = sorted(each["reason"] for each in body["skipped"])
    # A late Order completed its game's Week, so the game moved on and no longer waits for it.
    assert reasons == ["failed"] + ["not_waited_for"] * 10
    assert {each["seat_id"] for each in body["skipped"] if each["reason"] == "not_waited_for"} == {
        seat["seat_id"] for _, seat in late
    }
    # The counts match the occupancy rows written.
    assert body["inserted"] == 89
    assert rows(
        "SELECT count(*) FROM seat_occupancy o JOIN seats s ON s.id = o.seat_id "
        "JOIN games g ON g.id = s.game_id WHERE g.class_session_id = %s "
        "AND o.reason = 'takeover_staff' AND o.actor_user_id = %s",
        session_id,
        lecturer,
    ) == [(89,)]
