"""Student choice of a Class game and a Seat (Story 5.17, FR-21, AD-2, AD-4, AD-8, AD-9, AD-17):
behind `FEATURE_STUDENT_CHOICE` the Lecturer saves the method, which creates empty Class games and
tells the Students; each Student takes or changes a Seat until the lock, which draws a free Seat
for anyone who chose none. The api's clock is fixed and the sweep is handed its `now`; the
database clock is never read."""

import asyncio
import uuid

from app.modules.messaging import delivery
from app.modules.ops import sweep
from app.modules.sessions import service
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import call
from tests.classes.test_student_registration import emitted
from tests.messaging.helpers import mails, rows
from tests.sessions.test_allocation import open_, read, students
from tests.sessions.test_allocation_confirm import HOUR, confirm
from tests.sessions.test_allocation_move import move
from tests.sessions.test_dates import START, at, refusal, student_of
from tests.sessions.test_lab_hours import sweep_at
from tests.sessions.test_late_registrants import draft_row, seat_of
from tests.sessions.test_lock import MINUTE, _empty, dated
from tests.sessions.test_open_games import games_of, holders

__all__ = ["_empty", "clock", "emitted", "klass"]

OFFER = "sessions.offer_student_choice"
ROLES = ("factory", "distributor", "wholesaler", "retailer")
BEFORE = NOW + MINUTE


def flag(monkeypatch, on: bool) -> None:
    monkeypatch.setenv("FEATURE_STUDENT_CHOICE", "true" if on else "false")
    get_settings.cache_clear()


def email(i: int) -> str:
    """The address `students` gave the i-th Student."""
    return f"s{i}@x.no"


async def choose(session_id: str, method: str = "student_choice"):
    return await call(
        LECTURER,
        "PUT",
        f"/api/class-sessions/{session_id}",
        json={"ai_mode": "rule_based", "allocation_method": method},
    )


def path(session_id: str) -> str:
    return f"/api/me/class-sessions/{session_id}/seat-choice"


async def look(session_id: str, who: str):
    return await call(who, "GET", path(session_id))


async def take(session_id: str, who: str, game: int, role: str):
    return await call(who, "PUT", path(session_id), json={"game_number": game, "role": role})


def choice_notices() -> list[str]:
    return [
        key
        for (key,) in rows(
            "SELECT dedupe_key FROM notices WHERE kind = 'student_choice_open' ORDER BY dedupe_key"
        )
    ]


async def choosing(klass: str, n: int) -> tuple[str, list[uuid.UUID]]:
    seated = await students(klass, n)
    session_id = await dated(klass)
    assert (await choose(session_id)).status_code == 200
    return session_id, seated


async def test_saving_student_choice_creates_empty_games_and_tells_each_student(
    klass, monkeypatch, emitted
):
    flag(monkeypatch, True)
    seated = await students(klass, 5)
    session_id = await dated(klass)
    before = (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}")).json()
    assert (before["allocation_method"], before["student_choice_enabled"]) == ("random", True)
    # A preview drawn before is replaced.
    assert (await open_(session_id)).status_code == 200
    emitted.clear()
    response = await choose(session_id)
    assert response.status_code == 200
    assert response.json()["allocation_method"] == "student_choice"
    games = games_of(session_id)
    assert [(g[1], g[2], g[4]) for g in games] == [
        (1, "not_started", None),
        (2, "not_started", None),
    ]
    assert all(kind is None for *_, kind, _, _ in holders(session_id))
    _, revision, assignments = draft_row(session_id)
    assert (revision, assignments) == (1, [])
    assert rows(
        "SELECT confirmed_at IS NOT NULL FROM allocation_drafts WHERE class_session_id = %s",
        session_id,
    ) == [(True,)]
    assert choice_notices() == sorted(f"student_choice_open:{session_id}:{s}" for s in seated)
    assert {t for t, _ in emitted} == COMMAND_TOPICS["sessions.open_student_choice"]
    assert {i for t, i in emitted if t == "user"} == {str(s) for s in seated}
    # The block lists the empty games; nothing waits on the Lærerhjem.
    body = (await read(session_id)).json()
    assert (body["method"], body["confirmed"], body["missing_count"]) == ("student_choice", True, 5)
    assert [g["number"] for g in body["draft"]["games"]] == [1, 2]
    assert all(g["lifecycle"] is None for g in body["draft"]["games"])
    home = (await call(LECTURER, "GET", "/api/lecturer-home/class-sessions")).json()
    assert all("allocation" not in r["lacks"] for c in home["waiting"] for r in c["sessions"])
    # The method is final, and a random allocation is never drawn again.
    assert refusal(await choose(session_id, "random")) == (
        409,
        "allocation_confirmed",
        {"allocation_method": "confirmed"},
    )
    assert (await choose(session_id)).status_code == 200  # unchanged: never judged


async def test_with_the_flag_off_nothing_about_student_choice_is_offered(klass, monkeypatch):
    flag(monkeypatch, False)
    await students(klass, 2)
    session_id = await dated(klass)
    body = (await call(LECTURER, "GET", f"/api/class-sessions/{session_id}")).json()
    assert body["student_choice_enabled"] is False
    assert refusal(await choose(session_id)) == (
        422,
        "feature_disabled",
        {"allocation_method": "feature_disabled"},
    )
    assert rows("SELECT allocation_method FROM class_sessions WHERE id = %s", session_id) == [
        ("random",)
    ]
    assert games_of(session_id) == [] and choice_notices() == []
    # Resending random changes nothing, and the Student route is not there.
    assert (await choose(session_id, "random")).status_code == 200
    assert refusal(await look(session_id, email(0)))[:2] == (404, "not_found")
    me = (await call(email(0), "GET", "/api/me/class-sessions")).json()["items"]
    assert [(i["seat_choice_open"], i["drawn_seat"]) for i in me] == [(False, None)]


async def test_a_confirmed_or_locked_random_allocation_refuses_student_choice(klass, monkeypatch):
    flag(monkeypatch, True)
    await students(klass, 3)
    session_id = await dated(klass)
    shown = (await open_(session_id)).json()["draft"]
    assert (await confirm(session_id, shown)).status_code == 200
    assert refusal(await choose(session_id)) == (
        409,
        "allocation_confirmed",
        {"allocation_method": "confirmed"},
    )
    other = await dated(klass)
    at(monkeypatch, START + MINUTE)
    assert refusal(await choose(other))[:2] == (409, "session_locked")


async def test_the_student_route_is_not_found_for_others(klass, monkeypatch):
    flag(monkeypatch, True)
    await students(klass, 2)
    random_session = await dated(klass)
    assert refusal(await look(random_session, email(0)))[:2] == (404, "not_found")
    session_id = await dated(klass)
    assert (await choose(session_id)).status_code == 200
    await student_of(await other_class(), "ute@x.no")
    assert refusal(await look(session_id, "ute@x.no"))[:2] == (404, "not_found")
    assert refusal(await take(session_id, "ute@x.no", 1, "retailer"))[:2] == (404, "not_found")
    assert refusal(await call(email(0), "GET", path("not-an-id")))[:2] == (404, "not_found")
    # The same session reads, and the flag switched off hides it.
    assert (await look(session_id, email(0))).status_code == 200
    flag(monkeypatch, False)
    assert refusal(await look(session_id, email(0)))[:2] == (404, "not_found")


async def other_class() -> str:
    place = rows("SELECT institution_id::text FROM classes LIMIT 1")[0][0]
    response = await call(
        LECTURER, "POST", "/api/classes", json={"name": "annen", "institution_id": place}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def test_a_student_takes_a_free_seat_and_changes_it(klass, monkeypatch, emitted):
    flag(monkeypatch, True)
    session_id, seated = await choosing(klass, 5)
    body = (await look(session_id, email(0))).json()
    assert (body["open"], body["my_seat"], body["drawn"]) == (True, None, False)
    assert [g["number"] for g in body["games"]] == [1, 2]
    assert [s["role"] for s in body["games"][0]["seats"]] == [
        "factory",
        "distributor",
        "wholesaler",
        "retailer",
    ]
    assert all(s["holder"] == "free" for g in body["games"] for s in g["seats"])
    emitted.clear()
    response = await take(session_id, email(0), 2, "wholesaler")
    assert response.status_code == 200
    taken = response.json()
    assert taken["my_seat"] == {"game_number": 2, "role": "wholesaler"}
    seat = next(s for s in taken["games"][1]["seats"] if s["role"] == "wholesaler")
    assert seat["holder"] == "student" and seat["mine"] is True and seat["name"]
    assert seat_of(session_id, seated[0]) == [(2, "wholesaler")]
    _, revision, assignments = draft_row(session_id)
    assert (revision, assignments) == (
        2,
        [{"user_id": str(seated[0]), "game_number": 2, "role": "wholesaler"}],
    )
    assert {t for t, _ in emitted} == COMMAND_TOPICS["sessions.choose_seat"]
    assert {i for t, i in emitted if t == "user"} == {str(s) for s in seated}
    # Another Student sees the name and not «mine».
    other = (await look(session_id, email(1))).json()
    seen = next(s for s in other["games"][1]["seats"] if s["role"] == "wholesaler")
    assert (seen["holder"], seen["mine"], seen["name"]) == ("student", False, seat["name"])
    # Their own Seat again changes nothing; another free Seat moves them in the same request.
    assert (await take(session_id, email(0), 2, "wholesaler")).status_code == 200
    assert draft_row(session_id)[1] == 2
    moved = await take(session_id, email(0), 1, "factory")
    assert moved.status_code == 200
    assert seat_of(session_id, seated[0]) == [(1, "factory")]
    left = [h for h in holders(session_id) if (h[0], h[1]) == (2, "wholesaler")]
    assert left == [(2, "wholesaler", None, "moved", None)]
    assert draft_row(session_id)[2] == [
        {"user_id": str(seated[0]), "game_number": 1, "role": "factory"}
    ]


async def test_a_seat_another_holds_or_none_is_refused(klass, monkeypatch):
    flag(monkeypatch, True)
    session_id, _ = await choosing(klass, 3)
    assert (await take(session_id, email(0), 1, "retailer")).status_code == 200
    assert refusal(await take(session_id, email(1), 1, "retailer")) == (
        409,
        "seat_taken",
        {"seat": "taken"},
    )
    for game, role in ((9, "retailer"), (1, "captain"), (0, "factory")):
        assert refusal(await take(session_id, email(1), game, role)) == (
            422,
            "invalid_seat",
            {"seat": "unknown"},
        )
    assert draft_row(session_id)[1] == 2


async def test_two_students_pressing_one_free_seat_one_gets_it(klass, monkeypatch):
    flag(monkeypatch, True)
    session_id, seated = await choosing(klass, 2)
    first, second = await asyncio.gather(
        take(session_id, email(0), 1, "distributor"),
        take(session_id, email(1), 1, "distributor"),
    )
    assert sorted([first.status_code, second.status_code]) == [200, 409]
    loser = second if second.status_code == 409 else first
    assert loser.json()["error"]["code"] == "seat_taken"
    held = [h[4] for h in holders(session_id) if (h[0], h[1]) == (1, "distributor")]
    assert len(held) == 1 and held[0] in {str(s) for s in seated}


async def test_a_late_registrant_gets_the_offer_and_more_games_once(klass, monkeypatch, emitted):
    flag(monkeypatch, True)
    session_id, seated = await choosing(klass, 8)
    # Two games hold the eight registered Students, seated or not.
    assert (await take(session_id, email(0), 2, "retailer")).status_code == 200
    late = await student_of(klass, "sen@x.no")
    assert await service.student_choice_offers(BEFORE) == [(uuid.UUID(session_id), late)]
    emitted.clear()
    done = await sweep.run(BEFORE)
    assert (done[OFFER], done["sessions.seat_late_registrant"]) == (1, 0)
    assert [g[1] for g in games_of(session_id)] == [1, 2, 3]
    assert seat_of(session_id, late) == []
    assert f"student_choice_open:{session_id}:{late}" in choice_notices()
    assert {t for t, _ in emitted} == COMMAND_TOPICS[OFFER]
    assert (await sweep.run(BEFORE + MINUTE))[OFFER] == 0
    assert await service.offer_student_choice(uuid.UUID(session_id), late, now=BEFORE) is False
    assert len(seated) == 8
    # With the flag off the sweep offers nothing.
    await student_of(klass, "senere@x.no")
    flag(monkeypatch, False)
    assert await service.student_choice_offers(BEFORE) == []


async def test_the_lock_draws_a_seat_for_each_student_who_chose_none(klass, monkeypatch):
    flag(monkeypatch, True)
    session_id, seated = await choosing(klass, 5)
    assert (await take(session_id, email(0), 1, "retailer")).status_code == 200
    assert (await take(session_id, email(1), 2, "factory")).status_code == 200
    assert (await sweep.run(START + MINUTE))["sessions.lock"] == 1
    for student in seated:
        assert len(seat_of(session_id, student)) == 1
    assert seat_of(session_id, seated[0]) == [(1, "retailer")]
    assert all(kind is not None for *_, kind, _, _ in holders(session_id))
    assert sum(1 for *_, kind, _, _ in holders(session_id) if kind == "student") == 5
    _, _, assignments = draft_row(session_id)
    drawn = {a["user_id"] for a in assignments if a.get("drawn")}
    assert drawn == {str(s) for s in seated[2:]}
    told = {
        user
        for (user,) in rows("SELECT user_id::text FROM notices WHERE kind = 'allocation_confirmed'")
    }
    assert told == drawn
    # The drawn Student is told where; the one who chose is not.
    me = (await call(email(2), "GET", "/api/me/class-sessions")).json()["items"][0]
    (game, role) = seat_of(session_id, seated[2])[0]
    assert me["seat_choice_open"] is False
    assert me["drawn_seat"] == {"game_number": game, "role": role}
    assert (await call(email(0), "GET", "/api/me/class-sessions")).json()["items"][0][
        "drawn_seat"
    ] is None
    body = (await look(session_id, email(2))).json()
    assert (body["open"], body["drawn"]) == (False, True)
    assert {s["holder"] for g in body["games"] for s in g["seats"]} == {"student", "ai"}
    # Locked: no Seat changes.
    at(monkeypatch, START + MINUTE)
    assert refusal(await take(session_id, email(0), 2, "retailer")) == (
        409,
        "session_locked",
        {"seat": "locked"},
    )


async def test_the_lock_adds_a_class_game_when_no_seat_is_free(klass, monkeypatch):
    flag(monkeypatch, True)
    session_id, _ = await choosing(klass, 4)
    for i, role in enumerate(ROLES):
        assert (await take(session_id, email(i), 1, role)).status_code == 200
    late = await student_of(klass, "sen@x.no")
    flag(monkeypatch, False)  # no offer, so no new game before the lock
    assert (await sweep.run(START + MINUTE))["sessions.lock"] == 1
    assert [g[1] for g in games_of(session_id)] == [1, 2]
    assert [n for n, _ in seat_of(session_id, late)] == [2]


async def test_the_lock_draws_into_the_seat_of_a_student_who_left(klass, monkeypatch):
    """Follow-up review: a Seat chosen by a Student removed from the Class since is free to the
    draw, so nobody is drawn into a new game of AI players while it goes to an AI player."""
    flag(monkeypatch, True)
    session_id, seated = await choosing(klass, 4)
    for i, role in enumerate(ROLES):
        assert (await take(session_id, email(i), 1, role)).status_code == 200
    gone = seated[0]
    execute("UPDATE roster_entries SET removed_at = %s WHERE user_id = %s", NOW, gone)
    late = await student_of(klass, "sen@x.no")
    flag(monkeypatch, False)  # no offer, so no new game before the lock
    assert (await sweep.run(START + MINUTE))["sessions.lock"] == 1
    assert [g[1] for g in games_of(session_id)] == [1]
    assert seat_of(session_id, late) == [(1, "factory")]
    assert seat_of(session_id, gone) == []
    _, _, assignments = draft_row(session_id)
    assert str(gone) not in {a["user_id"] for a in assignments}
    assert {a["user_id"] for a in assignments if a.get("drawn")} == {str(late)}


async def test_before_the_lock_a_late_registrant_is_not_seated_by_the_draw(klass, monkeypatch):
    flag(monkeypatch, True)
    session_id, _ = await choosing(klass, 2)
    late = await student_of(klass, "sen@x.no")
    assert await service.late_registrants(BEFORE) == []
    assert await service.seat_late_registrant(uuid.UUID(session_id), late, now=BEFORE) is False


async def test_the_mail_names_the_class_and_is_dropped_once_locked(klass, monkeypatch):
    flag(monkeypatch, True)
    session_id, seated = await choosing(klass, 1)
    assert delivery.KINDS["student_choice_open"].mode == delivery.DIGEST
    ref = uuid.UUID(session_id)
    async with get_sessionmaker().begin() as s:
        found = await service.student_choice_mail_context(s, seated[0], ref, BEFORE)
        assert found is not None and found["class_name"] and found["start_at"] is not None
        assert await service.student_choice_mail_context(s, seated[0], ref, START) is None
        assert await service.student_choice_mail_context(s, seated[0], None, BEFORE) is None
    execute("UPDATE roster_entries SET removed_at = %s WHERE user_id = %s", NOW, seated[0])
    async with get_sessionmaker().begin() as s:
        assert await service.student_choice_mail_context(s, seated[0], ref, BEFORE) is None


async def test_a_student_registering_after_the_lock_gets_a_drawn_seat(klass, monkeypatch):
    flag(monkeypatch, True)
    session_id, _ = await choosing(klass, 3)
    assert (await sweep.run(START + MINUTE))["sessions.lock"] == 1
    late = await student_of(klass, "sen@x.no")
    assert (await sweep.run(START + 2 * MINUTE))["sessions.seat_late_registrant"] == 1
    ((game, role),) = seat_of(session_id, late)
    assert {"user_id": str(late), "game_number": game, "role": role, "drawn": True} in draft_row(
        session_id
    )[2]
    me = (await call("sen@x.no", "GET", "/api/me/class-sessions")).json()["items"][0]
    assert me["drawn_seat"] == {"game_number": game, "role": role}


async def test_the_lecturer_moves_no_seat_the_students_chose(klass, monkeypatch):
    flag(monkeypatch, True)
    session_id, _ = await choosing(klass, 2)
    assert (await take(session_id, email(0), 1, "retailer")).status_code == 200
    shown = (await read(session_id)).json()["draft"]
    response = await move(session_id, shown, (1, "retailer"), (1, "factory"))
    assert refusal(response) == (409, "allocation_confirmed", {"allocation": "student_choice"})
    assert draft_row(session_id)[1] == 2


async def test_the_digest_tells_each_student_they_may_choose(klass, monkeypatch):
    flag(monkeypatch, True)
    await choosing(klass, 1)
    await sweep_at(NOW + HOUR)  # 11:00 in Oslo, inside the digest hours
    [mail] = mails()
    assert mail.to == email(0)
    assert "I Klassen class-of-1994 velger du selv spill og sete før startdatoen " in mail.text
    assert "får du et sete ved trekning" in mail.text
    for banned in ("Beer Game", "bullwhip", "uker", "Uke"):
        assert banned not in mail.text
    # With the flag off by the time the digest goes, no mail sends Students to a missing page.
    await choosing(klass, 0)
    other = await student_of(klass, "sen@x.no")
    async with get_sessionmaker().begin() as s:
        sessions = rows("SELECT id FROM class_sessions ORDER BY id")
        ref = sessions[-1][0]
        assert await service.student_choice_mail_context(s, other, ref, BEFORE) is not None
        flag(monkeypatch, False)
        assert await service.student_choice_mail_context(s, other, ref, BEFORE) is None
