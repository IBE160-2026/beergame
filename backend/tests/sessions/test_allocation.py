"""The allocation draft of a Class session (Story 5.8, FR-20, FR-9, AD-12, AD-14): the pure
`allocation.allocate`, the stored draft that opening «Fordeling» draws and «Kjør fordeling på nytt»
replaces, names resolved at read time, and the refusals. The api's clock is fixed (2026-11-19
09:00 UTC) and moved by hand; the database clock is never read."""

import uuid
from collections import Counter
from datetime import datetime, timedelta

import pytest

from app.engine.settings import ROLES
from app.modules.sessions import allocation
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.classes.test_student_registration import emitted
from tests.messaging.helpers import rows
from tests.sessions.test_dates import PLAN, at, new_session, refusal, save, student_of

__all__ = ["clock", "emitted", "klass"]


@pytest.fixture(autouse=True)
def _empty(ai_db, mail_db):
    """No model config (Rule-based sessions), and no notices."""


def ids(n: int) -> list[uuid.UUID]:
    return [uuid.UUID(int=i + 1) for i in range(n)]


# The pure function.


@pytest.mark.parametrize("n", [*range(1, 10), 250])
def test_every_student_is_placed_once_in_groups_of_four_with_one_short_group_at_most(n):
    seats = allocation.allocate(ids(n), seed=7)
    assert sorted(seat.user_id for seat in seats) == ids(n)
    sizes = Counter(seat.game_number for seat in seats)
    assert sorted(sizes) == list(range(1, -(-n // 4) + 1))
    short = [size for size in sizes.values() if size != 4]
    assert len(short) == (0 if n % 4 == 0 else 1)
    assert all(1 <= size <= 3 for size in short)
    for game in sizes:
        roles = [seat.role for seat in seats if seat.game_number == game]
        assert len(set(roles)) == len(roles) and set(roles) <= set(ROLES)


def test_the_same_ids_in_any_order_and_seed_give_the_same_draft():
    students = ids(23)
    first = allocation.allocate(students, seed=12345)
    assert allocation.allocate(list(reversed(students)), seed=12345) == first
    assert allocation.allocate(students, seed=12346) != first
    assert allocation.allocate([], seed=1) == []


def test_a_fixed_seed_gives_a_fixed_draft():
    """Pins the algorithm: a change to it changes every stored seed's meaning."""
    seats = allocation.allocate(ids(5), seed=2026)
    assert [(s.user_id.int, s.game_number, s.role.value) for s in seats] == GOLDEN


GOLDEN = [
    (2, 1, "retailer"),
    (5, 1, "factory"),
    (4, 1, "distributor"),
    (3, 1, "wholesaler"),
    (1, 2, "retailer"),
]


def test_roles_are_random_across_seeds():
    """A Student's Role is drawn, not the order: over seeds the first id holds every Role."""
    held = {
        next(s.role for s in allocation.allocate(ids(8), seed) if s.user_id.int == 1)
        for seed in range(40)
    }
    assert held == set(ROLES)


def test_a_drawn_seed_is_exact_in_json():
    assert all(0 <= allocation.draw_seed() < 2**53 for _ in range(20))


# The routes.


def path(session_id: str, tail: str = "") -> str:
    return f"/api/class-sessions/{session_id}/allocation{tail}"


async def open_(session_id: str, email=LECTURER):
    return await call(email, "POST", path(session_id))


async def redraw(session_id: str, email=LECTURER):
    return await call(email, "POST", path(session_id, "/redraw"))


async def read(session_id: str, email=LECTURER):
    return await call(email, "GET", path(session_id))


async def students(class_id: str, n: int) -> list[uuid.UUID]:
    return [await student_of(class_id, f"s{i}@x.no") for i in range(n)]


def placed(body: dict) -> dict[str, tuple[int, str]]:
    return {
        seat["user_id"]: (game["number"], seat["role"])
        for game in body["draft"]["games"]
        for seat in game["seats"]
        if seat["user_id"]
    }


def counts() -> tuple:
    return rows("SELECT (SELECT count(*) FROM games), (SELECT count(*) FROM notices)")[0]


async def test_opening_draws_and_stores_a_draft_once(klass, emitted):
    five = await students(klass, 5)
    session_id = await new_session(klass)
    before = counts()
    emitted.clear()
    response = await open_(session_id)
    assert response.status_code == 200
    body = response.json()
    draft = body["draft"]
    assert (body["registered_count"], body["missing_count"], draft["revision"]) == (5, 0, 1)
    assert [game["number"] for game in draft["games"]] == [1, 2]
    assert [seat["role"] for seat in draft["games"][0]["seats"]] == [
        "factory",
        "distributor",
        "wholesaler",
        "retailer",
    ]
    assert sorted(placed(body)) == sorted(str(s) for s in five)
    # Names are read now; an empty Seat has none.
    names = {seat["name"] for game in draft["games"] for seat in game["seats"] if seat["user_id"]}
    assert names == {f"S{i}" for i in range(5)}
    empty = [seat for seat in draft["games"][1]["seats"] if seat["user_id"] is None]
    assert len(empty) == 3 and all(seat["name"] is None for seat in empty)
    assert emitted == [("session", session_id)]
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["sessions.draw_allocation"]
    # Stored: ids, game numbers and Roles only, with the seed and who drew it (AD-14).
    stored = rows(
        "SELECT id::text, revision, seed, drawn_by, assignments::text FROM allocation_drafts "
        "WHERE class_session_id = %s",
        session_id,
    )
    assert len(stored) == 1
    assert stored[0][0] == draft["id"] and stored[0][2] >= 0
    assert str(stored[0][3]) == rows("SELECT id::text FROM users WHERE email = %s", LECTURER)[0][0]
    assert datetime.fromisoformat(draft["drawn_at"]) == NOW
    assert "@" not in stored[0][4] and "S1" not in stored[0][4]
    # No Game, Seat or notice.
    assert counts() == before
    # Opening again and reading show the stored draft, never a new one.
    emitted.clear()
    assert (await open_(session_id)).json() == body
    assert (await read(session_id)).json() == body
    assert emitted == []


async def test_only_registered_students_are_allocated(klass):
    two = await students(klass, 2)
    execute(
        "INSERT INTO roster_entries (id, class_id, email, registration, added_at) "
        "VALUES (gen_random_uuid(), %s, 'invitert@x.no', 'invited', %s)",
        klass,
        NOW,
    )
    session_id = await new_session(klass)
    body = (await open_(session_id)).json()
    assert body["registered_count"] == 2
    assert sorted(placed(body)) == sorted(str(s) for s in two)


async def test_running_it_again_replaces_the_draft_under_a_new_id(klass, emitted):
    await students(klass, 9)
    session_id = await new_session(klass)
    first = (await open_(session_id)).json()["draft"]
    seed = rows("SELECT seed FROM allocation_drafts WHERE id = %s", first["id"])[0][0]
    before = counts()
    emitted.clear()
    response = await redraw(session_id)
    assert response.status_code == 200
    again = response.json()["draft"]
    assert again["id"] != first["id"] and again["revision"] == 1
    assert len(again["games"]) == 3
    assert rows(
        "SELECT id::text, seed <> %s FROM allocation_drafts WHERE class_session_id = %s",
        seed,
        session_id,
    ) == [(again["id"], True)]
    assert emitted == [("session", session_id)]
    assert counts() == before


async def test_with_no_registered_student_nothing_is_drawn(klass, emitted):
    session_id = await new_session(klass)
    emitted.clear()
    for response in (await read(session_id), await open_(session_id), await redraw(session_id)):
        assert response.status_code == 200
        assert response.json() == {
            "registered_count": 0,
            "missing_count": 0,
            "draft": None,
            "confirmed": False,
            "confirmed_at": None,
            "opened": False,
            "method": "random",  # Story 5.17
            "without_seat": [],
        }
    assert emitted == []
    assert rows(
        "SELECT count(*) FROM allocation_drafts WHERE class_session_id = %s", session_id
    ) == [(0,)]


async def test_a_redraw_after_every_student_left_removes_the_draft(klass, emitted):
    await students(klass, 2)
    session_id = await new_session(klass)
    assert (await open_(session_id)).json()["draft"] is not None
    execute("UPDATE roster_entries SET removed_at = %s WHERE class_id = %s", NOW, klass)
    # Until then the stale draft is still read, so it can be seen and cleared.
    assert (await read(session_id)).json()["draft"] is not None
    emitted.clear()
    empty = {
        "registered_count": 0,
        "missing_count": 0,
        "draft": None,
        "confirmed": False,
        "confirmed_at": None,
        "opened": False,
        "method": "random",  # Story 5.17
        "without_seat": [],
    }
    assert (await redraw(session_id)).json() == empty
    assert emitted == [("session", session_id)]
    assert (await read(session_id)).json() == empty
    assert rows(
        "SELECT count(*) FROM allocation_drafts WHERE class_session_id = %s", session_id
    ) == [(0,)]


async def test_a_late_registrant_is_counted_missing_and_a_removed_student_loses_the_name(klass):
    first = await students(klass, 3)
    session_id = await new_session(klass)
    drawn = (await open_(session_id)).json()
    await student_of(klass, "sen@x.no")
    execute(
        "UPDATE roster_entries SET removed_at = %s WHERE class_id = %s AND user_id = %s",
        NOW,
        klass,
        first[0],
    )
    body = (await read(session_id)).json()
    assert (body["registered_count"], body["missing_count"]) == (3, 1)
    # Before the lock nobody is listed as without a Seat (Story 5.13).
    assert body["without_seat"] == []
    assert body["draft"]["id"] == drawn["draft"]["id"]
    seats = {seat["user_id"]: seat["name"] for seat in body["draft"]["games"][0]["seats"]}
    assert str(first[0]) in seats and seats[str(first[0])] is None
    assert seats[str(first[1])] == "S1"


async def test_once_locked_the_draft_is_read_but_never_drawn(klass, monkeypatch):
    await students(klass, 4)
    session_id = await new_session(klass)
    assert (await save(session_id, PLAN)).status_code == 200
    drawn = (await open_(session_id)).json()
    other = await new_session(klass)
    assert (await save(other, PLAN)).status_code == 200
    at(monkeypatch, PLAN["start_at"] + timedelta(minutes=1))
    assert (await read(session_id)).json() == drawn
    # Opening the stored draft only reads it; drawing is refused.
    assert (await open_(session_id)).json() == drawn
    assert refusal(await redraw(session_id)) == (409, "session_locked", {"allocation": "locked"})
    assert refusal(await open_(other)) == (409, "session_locked", {"allocation": "locked"})


async def test_an_assistant_reads_and_an_archived_class_or_outsider_draws_nothing(klass):
    await students(klass, 4)
    session_id = await new_session(klass)
    drawn = (await open_(session_id)).json()
    assistant = await make(ASSISTANT, roles=())
    put_staff(klass, assistant, "assistant")
    assert (await read(session_id, ASSISTANT)).json() == drawn
    assert (await open_(session_id, ASSISTANT)).status_code == 403
    assert (await redraw(session_id, ASSISTANT)).status_code == 403
    await make("annen@x.no")
    assert (await read(session_id, "annen@x.no")).status_code == 403
    assert (await open_(session_id, "annen@x.no")).status_code == 403
    assert (await read("nope")).status_code == 403
    execute("UPDATE classes SET archived_at = %s WHERE id = %s", NOW, klass)
    assert (await read(session_id)).json() == drawn
    assert refusal(await redraw(session_id))[:2] == (409, "class_archived")
    assert refusal(await open_(session_id))[:2] == (409, "class_archived")
