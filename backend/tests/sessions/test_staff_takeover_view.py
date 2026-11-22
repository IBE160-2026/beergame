"""Story 8.5 through the api: `POST /api/games/{id}/seats/{role}/takeover` lets a Lecturer or
Assistant lecturer of the game's Class put an AI player in a Student's Seat (FR-37, FR-24, AD-2,
AD-12, AD-14, AD-15). Spillinnsikt says per Seat from when it would apply (`takeover`), and the
Oversikt and Spillinnsikt name who put the AI player in (`mark_by`). A lost race answers 409
`takeover_exists` with `acted_by` and `acted_at`; anyone else gets 403.

One short Class game (`short_game`: two Students, Week 1 Guided) per test."""

import uuid

from app.engine import GameSettings
from app.modules.games import commands
from app.modules.games import service as games_service
from tests.classes.test_classes import LECTURER, OTHER, make
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.messaging.helpers import rows
from tests.sessions.test_game_end import _empty, clock, emitted, klass, short_game
from tests.sessions.test_game_insight import insight
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass"]


async def take_over(who: str, game_id: str, role: str):
    return await call(who, "POST", f"/api/games/{game_id}/seats/{role}/takeover")


def seat(body: dict, role: str) -> dict:
    return next(s for s in body["seats"] if s["role"] == role)


def user_id(address: str) -> str:
    [(found,)] = rows("SELECT id FROM users WHERE email = %s", address)
    return str(found)


async def student_seats(game_id: str) -> dict[str, uuid.UUID]:
    game = await games_service.get_game(game_id)
    return {s.role: s.user_id for s in game.seats if s.occupant_kind == "student"}


async def test_a_lecturer_puts_an_ai_player_in_the_seat_of_a_student_who_never_opened_uke_1(
    klass,
):
    session_id, game_id, _ = await short_game(klass)
    students = await student_seats(game_id)
    present, absent = sorted(students)
    before = (await insight(LECTURER, game_id)).json()
    assert {s["role"]: s["takeover"] for s in before["seats"]} == {
        role: ("this_week" if role in students else None)
        for role in (s["role"] for s in before["seats"])
    }
    # Opening the Guided Uke 1 is ordering it (Story 8.1): that Seat's AI player would take Uke 2.
    await commands.view_week(game_id, present, 1, actor=students[present])
    assert seat((await insight(LECTURER, game_id)).json(), present)["takeover"] == "next_week"

    answer = await take_over(LECTURER, game_id, absent)
    assert answer.status_code == 200
    body = answer.json()
    taken = seat(body, absent)
    assert (taken["holder"], taken["mark"], taken["mark_by"], taken["takeover"]) == (
        "ai",
        "takeover_staff",
        "Bard",
        None,
    )
    # The absent Seat counted as ordered once taken over: Uke 1 completed and Uke 2 opened.
    assert max(w["week"] for w in body["roles"][0]["weeks"]) == 2
    overview = (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}/overview")).json()
    [game] = [g for g in overview["items"] if g["game_id"] == game_id]
    assert seat(game, absent)["mark_by"] == "Bard"

    # A second press loses the race and is told who acted first, by kind and id only.
    again = await take_over(LECTURER, game_id, absent)
    assert again.status_code == 409
    error = again.json()["error"]
    assert error["code"] == "takeover_exists"
    assert error["fields"]["acted_by"] == {"kind": "staff", "user_id": user_id(LECTURER)}
    assert error["fields"]["acted_at"]


async def test_an_assistant_may_and_anyone_else_is_refused(klass):
    session_id, game_id, _ = await short_game(klass)
    students = await student_seats(game_id)
    first, second = sorted(students)
    ai_seat = next(
        role
        for role in ("retailer", "wholesaler", "distributor", "factory")
        if role not in students
    )
    test_game = await commands.create(
        "lecturer_test", GameSettings(), class_session_id=uuid.UUID(session_id)
    )
    refused = [
        await take_over(LECTURER, str(test_game), "retailer"),  # in no staff list (AD-13)
        await take_over(email(0), game_id, first),  # a Student of the game
        await take_over(OTHER, game_id, first),  # a Lecturer of another Class
        await take_over(LECTURER, str(uuid.uuid7()), first),  # no such Game
        await take_over(LECTURER, "not-an-id", first),
    ]
    assert {r.status_code for r in refused} == {403}
    assert rows("SELECT 1 FROM seat_occupancy WHERE reason = 'takeover_staff'") == []

    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    done = await take_over(ASSISTANT, game_id, first)
    assert done.status_code == 200
    assert seat(done.json(), first)["mark_by"] == "Assistent"
    # The Student's start is audited too (Story 8.10); the Takeover names the Assistant.
    [(actor, action)] = rows(
        "SELECT actor_user_id, action FROM audit_events WHERE target_ids->>'game_id' = %s "
        "AND action <> 'game.started'",
        game_id,
    )
    assert (str(actor), action) == (user_id(ASSISTANT), "seat.taken_over")
    # A Seat an AI player has held from the start is no Student's to take over.
    held = await take_over(LECTURER, game_id, ai_seat)
    assert (held.status_code, held.json()["error"]["code"]) == (409, "seat_not_student_held")
    assert seat((await insight(LECTURER, game_id)).json(), second)["takeover"] == "this_week"
    # Once the Assistant lecturer has left the Class, no name is given for them (AD-12).
    rows_deleted = rows(
        "DELETE FROM class_staff WHERE class_id = %s AND role = 'assistant' RETURNING 1", klass
    )
    assert rows_deleted == [(1,)]
    assert seat((await insight(LECTURER, game_id)).json(), first)["mark_by"] is None
