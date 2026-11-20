"""Moving and swapping Students in the allocation (Story 5.10, FR-20, AD-2, AD-8, AD-9): the
stored draft changes under its id with its revision raised by one, by the revision the Lecturer
was looking at; once confirmed, the Class games change with it through `games.move_seat` and the
Students who moved are told again. The api's clock is fixed and moved by hand."""

import uuid
from datetime import timedelta

import pytest

from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.classes.test_student_registration import emitted
from tests.messaging.helpers import rows
from tests.sessions.test_allocation import open_, path, read, students
from tests.sessions.test_allocation_confirm import confirm, drafted
from tests.sessions.test_dates import PLAN, at, new_session, refusal, save

__all__ = ["clock", "emitted", "klass"]


@pytest.fixture(autouse=True)
def _empty(ai_db, mail_db, games_db):
    """No model config (Rule-based sessions), no notices and no Games."""


async def move(session_id: str, draft: dict, src: tuple, dst: tuple, email=LECTURER, **extra):
    body = {
        "draft_id": draft["id"],
        "revision": draft["revision"],
        "from_game": src[0],
        "from_role": src[1],
        "to_game": dst[0],
        "to_role": dst[1],
        **extra,
    }
    return await call(email, "POST", path(session_id, "/move"), json=body)


def holder(draft: dict, number: int, role: str) -> str | None:
    game = next(g for g in draft["games"] if g["number"] == number)
    return next(s["user_id"] for s in game["seats"] if s["role"] == role)


def free_role(draft: dict, number: int) -> str:
    game = next(g for g in draft["games"] if g["number"] == number)
    return next(s["role"] for s in game["seats"] if s["user_id"] is None)


def student_role(draft: dict, number: int, index: int = 0) -> str:
    game = next(g for g in draft["games"] if g["number"] == number)
    return [s["role"] for s in game["seats"] if s["user_id"]][index]


def seated(session_id: str) -> list[tuple]:
    """Each Seat a Student holds now in the Class session's Games: (game number, Role, user)."""
    return rows(
        "SELECT number, role, user_id FROM (SELECT DISTINCT ON (s.id) g.game_number AS number, "
        "s.role, o.occupant_kind, o.user_id::text AS user_id FROM games g "
        "JOIN seats s ON s.game_id = g.id JOIN seat_occupancy o ON o.seat_id = s.id "
        "WHERE g.class_session_id = %s ORDER BY s.id, o.id DESC) latest "
        "WHERE occupant_kind = 'student' ORDER BY 1, 2",
        session_id,
    )


def notices() -> list[tuple]:
    return rows("SELECT dedupe_key, user_id::text FROM notices ORDER BY dedupe_key")


async def test_a_move_to_a_free_seat_edits_the_draft_under_its_id(klass, emitted):
    await students(klass, 5)
    session_id = await new_session(klass)
    shown = (await open_(session_id)).json()["draft"]
    src = (1, student_role(shown, 1))
    dst = (2, free_role(shown, 2))
    emitted.clear()
    response = await move(session_id, shown, src, dst)
    assert response.status_code == 200
    now = response.json()["draft"]
    assert (now["id"], now["revision"], now["drawn_at"]) == (shown["id"], 2, shown["drawn_at"])
    assert holder(now, *dst) == holder(shown, *src)
    assert holder(now, *src) is None
    assert len(drafted(now)) == 5
    assert emitted == [("session", session_id)]
    assert (await read(session_id)).json()["draft"] == now
    # Not confirmed: no Game and nobody told; the edited draft is what confirm commits.
    assert rows("SELECT count(*) FROM games") == [(0,)]
    assert notices() == []
    assert refusal(await confirm(session_id, shown)) == (
        409,
        "allocation_changed",
        {"draft": "changed"},
    )
    assert (await confirm(session_id, now)).status_code == 200
    assert seated(session_id) == drafted(now)


async def test_a_swap_and_a_role_change_in_the_draft(klass):
    await students(klass, 6)
    session_id = await new_session(klass)
    shown = (await open_(session_id)).json()["draft"]
    a, b = (1, student_role(shown, 1)), (2, student_role(shown, 2))
    swapped = (await move(session_id, shown, a, b)).json()["draft"]
    assert (holder(swapped, *a), holder(swapped, *b)) == (holder(shown, *b), holder(shown, *a))
    assert swapped["revision"] == 2
    # Within game 2, to its free Role.
    c = (2, free_role(swapped, 2))
    turned = (await move(session_id, swapped, b, c)).json()["draft"]
    assert (holder(turned, *c), holder(turned, *b), turned["revision"]) == (
        holder(swapped, *b),
        None,
        3,
    )


async def test_moves_the_draft_cannot_take_change_nothing(klass, emitted):
    await students(klass, 5)
    session_id = await new_session(klass)
    shown = (await open_(session_id)).json()["draft"]
    full = (1, student_role(shown, 1))
    free = (2, free_role(shown, 2))
    emitted.clear()
    cases = [
        (full, full, {"to": "same"}),
        ((3, "retailer"), free, {"from": "unknown"}),
        (full, (3, "retailer"), {"to": "unknown"}),
        (free, full, {"from": "empty"}),
    ]
    for src, dst, fields in cases:
        assert refusal(await move(session_id, shown, src, dst)) == (422, "invalid_move", fields)
    assert emitted == []
    assert (await read(session_id)).json()["draft"] == shown
    # The body is checked by the api: extra keys and loose numbers are refused.
    assert (await move(session_id, shown, full, free, extra=1)).status_code == 422
    assert (await move(session_id, {**shown, "revision": "1"}, full, free)).status_code == 422
    assert (await move(session_id, shown, full, (2, "nope"))).status_code == 422


async def test_the_last_student_of_a_game_is_not_moved_out(klass):
    """A free Seat outside the short game only exists once a Student has left the Roster."""
    await students(klass, 9)
    session_id = await new_session(klass)
    shown = (await open_(session_id)).json()["draft"]
    execute(
        "UPDATE roster_entries SET removed_at = %s WHERE user_id = %s",
        NOW,
        holder(shown, 1, student_role(shown, 1)),
    )
    assert refusal(await confirm(session_id, shown))[2] == {"draft": "students_removed"}
    now = (await read(session_id)).json()["draft"]
    alone = (3, student_role(now, 3))
    assert refusal(await move(session_id, now, alone, (1, free_role(now, 1)))) == (
        422,
        "invalid_move",
        {"from": "last_student"},
    )
    # A swap out of it is fine: the game keeps a Student.
    assert (await move(session_id, now, alone, (2, student_role(now, 2)))).status_code == 200


async def test_a_stale_draft_is_not_edited(klass, emitted):
    await students(klass, 5)
    session_id = await new_session(klass)
    shown = (await open_(session_id)).json()["draft"]
    src, dst = (1, student_role(shown, 1)), (2, free_role(shown, 2))
    assert (await move(session_id, shown, src, dst)).status_code == 200
    emitted.clear()
    for stale in (shown, {**shown, "id": str(uuid.uuid7()), "revision": 2}):
        assert refusal(await move(session_id, stale, src, dst)) == (
            409,
            "allocation_changed",
            {"draft": "changed"},
        )
    assert emitted == []
    assert (await read(session_id)).json()["draft"]["revision"] == 2


async def test_a_confirmed_move_changes_the_class_games_and_tells_the_student(klass, emitted):
    await students(klass, 5)
    session_id = await new_session(klass)
    shown = (await open_(session_id)).json()["draft"]
    confirmed = (await confirm(session_id, shown)).json()
    assert confirmed["confirmed_at"] is not None
    src, dst = (1, student_role(shown, 1)), (2, free_role(shown, 2))
    student = holder(shown, *src)
    games_before = rows("SELECT id, version FROM games ORDER BY game_number")
    emitted.clear()
    response = await move(session_id, shown, src, dst)
    assert response.status_code == 200
    body = response.json()
    now = body["draft"]
    assert (body["confirmed"], body["confirmed_at"], now["revision"]) == (
        True,
        confirmed["confirmed_at"],
        2,
    )
    # The Seats are what the draft shows; the left Seat has a free-Seat row.
    assert seated(session_id) == drafted(now)
    assert rows("SELECT reason FROM seat_occupancy WHERE occupant_kind IS NULL") == [("moved",)]
    assert [v for _, v in rows("SELECT id, version FROM games ORDER BY game_number")] == [
        v + 1 for _, v in games_before
    ]
    # Only the Student who moved is told again, keyed by the new revision.
    assert (f"allocation_confirmed:{shown['id']}:2:{student}", student) in notices()
    assert len(notices()) == 6
    assert {t for t, _ in emitted} == COMMAND_TOPICS["sessions.move_allocation"]
    assert {i for t, i in emitted if t == "user"} == {student}


async def test_a_confirmed_swap_tells_both_students(klass):
    await students(klass, 8)
    session_id = await new_session(klass)
    shown = (await open_(session_id)).json()["draft"]
    await confirm(session_id, shown)
    a, b = (1, student_role(shown, 1)), (2, student_role(shown, 2, 1))
    now = (await move(session_id, shown, a, b)).json()["draft"]
    assert seated(session_id) == drafted(now)
    told = {u for key, u in notices() if key.startswith(f"allocation_confirmed:{shown['id']}:2:")}
    assert told == {holder(shown, *a), holder(shown, *b)}


async def test_a_started_class_game_refuses_the_move_and_nothing_is_kept(klass):
    await students(klass, 5)
    session_id = await new_session(klass)
    shown = (await open_(session_id)).json()["draft"]
    await confirm(session_id, shown)
    execute("UPDATE games SET lifecycle = 'running' WHERE game_number = 2")
    before = notices()
    response = await move(session_id, shown, (1, student_role(shown, 1)), (2, free_role(shown, 2)))
    assert refusal(response) == (
        409,
        "game_already_started",
        {"allocation": "game_already_started"},
    )
    assert (await read(session_id)).json()["draft"]["revision"] == 1
    assert notices() == before


async def test_once_locked_or_for_others_nothing_is_moved(klass, monkeypatch):
    await students(klass, 5)
    session_id = await new_session(klass)
    assert (await save(session_id, PLAN)).status_code == 200
    shown = (await open_(session_id)).json()["draft"]
    src, dst = (1, student_role(shown, 1)), (2, free_role(shown, 2))
    assistant = await make(ASSISTANT, roles=())
    put_staff(klass, assistant, "assistant")
    assert (await move(session_id, shown, src, dst, ASSISTANT)).status_code == 403
    assert (await move("nope", shown, src, dst)).status_code == 403
    at(monkeypatch, PLAN["start_at"] + timedelta(minutes=1))
    assert refusal(await move(session_id, shown, src, dst)) == (
        409,
        "session_locked",
        {"allocation": "locked"},
    )
    at(monkeypatch, NOW)
    execute("UPDATE classes SET archived_at = %s WHERE id = %s", NOW, klass)
    assert refusal(await move(session_id, shown, src, dst))[:2] == (409, "class_archived")
    assert (await read(session_id)).json()["draft"]["revision"] == 1
