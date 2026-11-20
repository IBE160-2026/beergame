"""Confirming the allocation (Story 5.9, FR-20, FR-7, AD-2, AD-4, AD-9): «Bekreft fordeling»
commits exactly the stored draft the Lecturer is looking at, by id and revision, as Class games
and `student` Seats with a digest notice per Student; a stale draft or a removed Student commits
no Game. The api's clock is fixed and moved by hand; the database clock is never read."""

import uuid
from datetime import timedelta

import pytest

from app.modules.messaging import delivery
from app.modules.sessions import service
from app.platform.db import get_sessionmaker
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.classes.test_student_registration import emitted
from tests.messaging.helpers import mails, rows
from tests.sessions.test_allocation import open_, path, read, redraw, students
from tests.sessions.test_dates import PLAN, at, new_session, refusal, save, student_of
from tests.sessions.test_lab_hours import sweep_at

HOUR = timedelta(hours=1)

__all__ = ["clock", "emitted", "klass"]


@pytest.fixture(autouse=True)
def _empty(ai_db, mail_db, games_db):
    """No model config (Rule-based sessions), no notices and no Games."""


async def confirm(session_id: str, draft: dict | None, email=LECTURER, **changes):
    body = {"draft_id": draft["id"], "revision": draft["revision"]} if draft else {}
    return await call(email, "POST", path(session_id, "/confirm"), json={**body, **changes})


def committed(session_id: str) -> list[tuple]:
    """Each Student Seat of the Class session's Games: (game number, Role, user id)."""
    return rows(
        "SELECT g.game_number, s.role, o.user_id::text FROM games g "
        "JOIN seats s ON s.game_id = g.id JOIN seat_occupancy o ON o.seat_id = s.id "
        "WHERE g.class_session_id = %s ORDER BY 1, 2",
        session_id,
    )


def drafted(draft: dict) -> list[tuple]:
    return sorted(
        (game["number"], seat["role"], seat["user_id"])
        for game in draft["games"]
        for seat in game["seats"]
        if seat["user_id"]
    )


def counts() -> tuple:
    return rows(
        "SELECT (SELECT count(*) FROM games), (SELECT count(*) FROM seat_occupancy), "
        "(SELECT count(*) FROM notices)"
    )[0]


async def test_confirm_commits_the_draft_student_by_student(klass, emitted):
    five = await students(klass, 5)
    session_id = await new_session(klass)
    shown = (await open_(session_id)).json()
    emitted.clear()
    response = await confirm(session_id, shown["draft"])
    assert response.status_code == 200
    body = response.json()
    assert body["confirmed"] is True and body["draft"] == shown["draft"]
    # The Games and Seats equal the stored draft, Student by Student.
    assert committed(session_id) == drafted(shown["draft"])
    assert len(committed(session_id)) == 5
    games = rows(
        "SELECT id, purpose, lifecycle, game_number, settings IS NULL, session_runtime IS NULL "
        "FROM games WHERE class_session_id = %s ORDER BY game_number",
        session_id,
    )
    assert [g[1:] for g in games] == [
        ("class", "not_started", 1, True, True),
        ("class", "not_started", 2, True, True),
    ]
    # Empty Seats stay free until the lock; four Seats per Game.
    assert rows("SELECT count(*) FROM seats") == [(8,)]
    assert rows("SELECT count(*) FROM seat_occupancy WHERE occupant_kind <> 'student'") == [(0,)]
    # One digest notice per Student, ids only (AD-14).
    notices = rows("SELECT kind, dedupe_key, user_id, ref FROM notices ORDER BY user_id")
    draft_id = shown["draft"]["id"]
    assert notices == sorted(
        (
            (
                "allocation_confirmed",
                f"allocation_confirmed:{draft_id}:{s}",
                s,
                uuid.UUID(session_id),
            )
            for s in five
        ),
        key=lambda n: n[2],
    )
    assert delivery.ALLOCATION_KIND == service.ALLOCATION_NOTICE
    assert delivery.KINDS[service.ALLOCATION_NOTICE].mode == delivery.DIGEST
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["sessions.confirm_allocation"]
    assert {i for t, i in emitted if t == "user"} == {str(s) for s in five}
    assert {i for t, i in emitted if t == "game"} == {str(g[0]) for g in games}
    assert rows(
        "SELECT confirmed_at, confirmed_by::text FROM allocation_drafts WHERE id = %s", draft_id
    ) == [(NOW, rows("SELECT id::text FROM users WHERE email = %s", LECTURER)[0][0])]
    # Pressed again: the same answer and no second set of Games; never drawn again.
    before = counts()
    emitted.clear()
    assert (await confirm(session_id, shown["draft"])).json() == body
    assert counts() == before and emitted == []
    assert (await read(session_id)).json() == body
    assert (await open_(session_id)).json() == body
    assert refusal(await redraw(session_id)) == (
        409,
        "allocation_confirmed",
        {"allocation": "confirmed"},
    )


async def test_a_stale_draft_commits_nothing(klass, emitted):
    await students(klass, 6)
    session_id = await new_session(klass)
    assert refusal(await confirm(session_id, {"id": str(uuid.uuid7()), "revision": 1})) == (
        409,
        "allocation_changed",
        {"draft": "changed"},
    )
    seen = (await open_(session_id)).json()["draft"]
    await redraw(session_id)  # a co-owner drew again meanwhile
    before = counts()
    emitted.clear()
    for draft in (seen, {**(await read(session_id)).json()["draft"], "revision": 2}):
        assert refusal(await confirm(session_id, draft)) == (
            409,
            "allocation_changed",
            {"draft": "changed"},
        )
    assert counts() == before and emitted == []
    assert (await read(session_id)).json()["confirmed"] is False
    # The body is the draft id and revision, nothing else.
    current = (await read(session_id)).json()["draft"]
    assert (await confirm(session_id, current, extra=1)).status_code == 422
    assert (await confirm(session_id, current, revision="1")).status_code == 422


async def test_a_removed_student_frees_the_seat_and_commits_nothing(klass, emitted):
    await students(klass, 5)
    session_id = await new_session(klass)
    shown = (await open_(session_id)).json()["draft"]
    # The one Student of game 2 and one of game 1 leave the Roster after the preview.
    alone = next(s["user_id"] for s in shown["games"][1]["seats"] if s["user_id"])
    other = next(s["user_id"] for s in shown["games"][0]["seats"] if s["user_id"])
    execute(
        "UPDATE roster_entries SET removed_at = %s WHERE user_id IN (%s, %s)", NOW, alone, other
    )
    before = counts()
    emitted.clear()
    assert refusal(await confirm(session_id, shown)) == (
        409,
        "allocation_changed",
        {"draft": "students_removed"},
    )
    assert counts() == before
    assert emitted == [("session", session_id)]
    # The draft keeps its id, its revision is raised, the emptied game is gone.
    now = (await read(session_id)).json()
    assert (now["draft"]["id"], now["draft"]["revision"], now["confirmed"]) == (
        shown["id"],
        2,
        False,
    )
    assert [g["number"] for g in now["draft"]["games"]] == [1]
    assert {s["user_id"] for s in now["draft"]["games"][0]["seats"]} - {None} == {
        s["user_id"] for s in shown["games"][0]["seats"] if s["user_id"] not in (None, other)
    }
    # The preview shown now is the one confirmed.
    assert (await confirm(session_id, now["draft"])).status_code == 200
    assert committed(session_id) == drafted(now["draft"])


async def test_with_every_student_removed_the_draft_goes(klass):
    await students(klass, 2)
    session_id = await new_session(klass)
    shown = (await open_(session_id)).json()["draft"]
    execute("UPDATE roster_entries SET removed_at = %s WHERE class_id = %s", NOW, klass)
    assert refusal(await confirm(session_id, shown))[2] == {"draft": "students_removed"}
    assert (await read(session_id)).json() == {
        "registered_count": 0,
        "missing_count": 0,
        "draft": None,
        "confirmed": False,
    }
    assert counts()[0] == 0


async def test_once_locked_or_for_others_nothing_is_confirmed(klass, monkeypatch):
    await students(klass, 4)
    session_id = await new_session(klass)
    assert (await save(session_id, PLAN)).status_code == 200
    shown = (await open_(session_id)).json()["draft"]
    assistant = await make(ASSISTANT, roles=())
    put_staff(klass, assistant, "assistant")
    assert (await confirm(session_id, shown, ASSISTANT)).status_code == 403
    await make("annen@x.no")
    assert (await confirm(session_id, shown, "annen@x.no")).status_code == 403
    assert (await confirm("nope", shown)).status_code == 403
    at(monkeypatch, PLAN["start_at"] + timedelta(minutes=1))
    assert refusal(await confirm(session_id, shown)) == (
        409,
        "session_locked",
        {"allocation": "locked"},
    )
    at(monkeypatch, NOW)
    execute("UPDATE classes SET archived_at = %s WHERE id = %s", NOW, klass)
    assert refusal(await confirm(session_id, shown))[:2] == (409, "class_archived")
    assert counts()[0] == 0


async def test_the_lecturer_home_stops_naming_a_confirmed_session(klass):
    await students(klass, 4)
    session_id = await new_session(klass)
    assert (await save(session_id, PLAN)).status_code == 200

    async def waiting() -> list:
        body = (await call(LECTURER, "GET", "/api/lecturer-home/class-sessions")).json()
        return [s for c in body["waiting"] for s in c["sessions"]]

    assert await waiting() == [{"id": session_id, "number": 1, "lacks": ["allocation"]}]
    await confirm(session_id, (await open_(session_id)).json()["draft"])
    assert await waiting() == []


async def test_the_notice_mail_names_the_class_while_the_student_is_in_it(klass):
    two = await students(klass, 2)
    session_id = await new_session(klass)
    await confirm(session_id, (await open_(session_id)).json()["draft"])
    ref = uuid.UUID(session_id)

    async def context(user_id: uuid.UUID, of: uuid.UUID | None = ref):
        async with get_sessionmaker().begin() as s:
            return await service.allocation_mail_context(s, user_id, of, NOW)

    assert await context(two[0]) == {"class_name": "class-of-1994"}
    assert await context(two[0], None) is None
    assert await context(two[0], uuid.uuid7()) is None
    assert await context(uuid.uuid7()) is None  # not in the allocation
    execute("UPDATE roster_entries SET removed_at = %s WHERE user_id = %s", NOW, two[1])
    assert await context(two[1]) is None
    execute("UPDATE classes SET archived_at = %s WHERE id = %s", NOW, klass)
    assert await context(two[0]) is None


async def test_an_emptied_first_game_is_dropped_and_the_rest_numbered_from_one(klass):
    await students(klass, 6)
    session_id = await new_session(klass)
    shown = (await open_(session_id)).json()["draft"]
    first = [s["user_id"] for s in shown["games"][0]["seats"] if s["user_id"]]
    execute("UPDATE roster_entries SET removed_at = %s WHERE user_id = ANY(%s::uuid[])", NOW, first)
    assert refusal(await confirm(session_id, shown))[2] == {"draft": "students_removed"}
    now = (await read(session_id)).json()["draft"]
    assert [g["number"] for g in now["games"]] == [1]
    assert {s["user_id"] for s in now["games"][0]["seats"]} == {
        s["user_id"] for s in shown["games"][1]["seats"]
    }
    assert (await confirm(session_id, now)).status_code == 200
    assert {n for n, _, _ in committed(session_id)} == {1}


async def test_the_digest_tells_the_student_without_naming_the_game_or_role(klass):
    student = await student_of(klass)
    session_id = await new_session(klass)
    await confirm(session_id, (await open_(session_id)).json()["draft"])
    await sweep_at(NOW + HOUR)  # 11:00 in Oslo, inside the digest hours
    [mail] = mails()
    assert mail.to == "student@x.no"
    assert "Du er satt i et spill i Klassen class-of-1994." in mail.text
    for banned in ("Beer Game", "bullwhip", "uker", "Uke", "Spill 1", "Detaljist", "Grossist"):
        assert banned not in mail.text
    # A Student who leaves the Class before the digest gets no mail.
    other = await new_session(klass)
    await confirm(other, (await open_(other)).json()["draft"])
    execute("UPDATE roster_entries SET removed_at = %s WHERE user_id = %s", NOW, student)
    await sweep_at(NOW + 26 * HOUR)
    assert len(mails()) == 1
