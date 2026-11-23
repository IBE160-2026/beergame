"""Students who register after the allocation, and Students removed after the open (Story 5.13,
FR-7, FR-20, AD-2, AD-5, AD-8, AD-9): the sweep seats a late registrant in a free Seat or a new
Class game before the lock, in an AI player's Seat of a game that has not started after it, or
lists them as without a Seat; a removed Student's Seat in a game that has not started goes to an
AI player. The api's clock is fixed and the sweep is handed its `now`; the database clock is never
read."""

import asyncio
import dataclasses
import uuid

from app.modules.games import commands as games_commands
from app.modules.ops import sweep
from app.modules.sessions import service
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_student_registration import emitted
from tests.messaging.helpers import rows
from tests.sessions.test_ai_mode import two_levels
from tests.sessions.test_allocation import open_, read, students
from tests.sessions.test_dates import START, student_of
from tests.sessions.test_lock import MINUTE, _empty, dated
from tests.sessions.test_open_games import confirmed, games_of, holders

__all__ = ["_empty", "clock", "emitted", "klass", "two_levels"]

SEAT = "sessions.seat_late_registrant"
REPLACE = "sessions.replace_removed_student"
BEFORE = NOW + MINUTE
"""A sweep before the Start date."""


def history(user_id) -> list[tuple]:
    """Every occupancy row of the Seat the Student holds or held: (kind, reason, user id), each
    from Week 1."""
    found = rows(
        "SELECT o.occupant_kind, o.reason, o.user_id::text, o.from_week FROM seat_occupancy o "
        "WHERE o.seat_id = (SELECT seat_id FROM seat_occupancy WHERE user_id = %s LIMIT 1) "
        "ORDER BY o.id",
        user_id,
    )
    assert {week for *_, week in found} == {1}
    return [row[:3] for row in found]


def draft_row(session_id: str) -> tuple:
    return rows(
        "SELECT id::text, revision, assignments FROM allocation_drafts WHERE class_session_id = %s",
        session_id,
    )[0]


def seat_of(session_id: str, user_id) -> list[tuple]:
    return [(n, role) for n, role, _, _, user in holders(session_id) if user == str(user_id)]


async def opened(klass: str, n: int, ai_mode: str = "rule_based") -> tuple[str, list]:
    session_id, seated = await confirmed(klass, n, ai_mode)
    assert (await sweep.run(START + MINUTE))["sessions.lock"] == 1
    return session_id, seated


async def test_before_the_lock_a_late_registrant_takes_a_free_seat(klass, emitted):
    session_id, seated = await confirmed(klass, 5)
    draft_id, revision, _ = draft_row(session_id)
    in_game_two = [user for n, _, _, _, user in holders(session_id) if n == 2 and user]
    late = await student_of(klass, "sen@x.no")
    assert (await read(session_id)).json()["without_seat"] == []
    emitted.clear()
    assert (await sweep.run(BEFORE))[SEAT] == 1
    ((number, role),) = seat_of(session_id, late)
    assert number == 2
    # The draft is what the Seats hold, under a new revision; the Student is told.
    _, now_revision, assignments = draft_row(session_id)
    assert now_revision == revision + 1
    assert {"user_id": str(late), "game_number": 2, "role": role} in assignments
    assert rows("SELECT dedupe_key FROM notices WHERE user_id = %s", late) == [
        (f"allocation_confirmed:{draft_id}:{now_revision}:{late}",)
    ]
    # The Student, the other Students of that game and the staff hear of it.
    assert {i for t, i in emitted if t == "user"} == {str(late), *in_game_two}
    assert ("session", session_id) in emitted
    assert {t for t, _ in emitted} == COMMAND_TOPICS[SEAT]
    body = (await read(session_id)).json()
    names = {s["user_id"]: s["name"] for g in body["draft"]["games"] for s in g["seats"]}
    assert names[str(late)] and body["missing_count"] == 0
    # Idempotent: the next sweep finds nobody, and a direct call does nothing.
    assert (await sweep.run(BEFORE + MINUTE))[SEAT] == 0
    assert await service.seat_late_registrant(uuid.UUID(session_id), late, now=BEFORE) is False
    assert len(seated) == 5


async def test_with_every_seat_taken_a_new_class_game_is_created(klass):
    session_id, _ = await confirmed(klass, 4)
    late = await student_of(klass, "sen@x.no")
    assert (await sweep.run(BEFORE))[SEAT] == 1
    games = games_of(session_id)
    assert [(g[1], g[2], g[4]) for g in games] == [
        (1, "not_started", None),
        (2, "not_started", None),
    ]
    assert [n for n, _ in seat_of(session_id, late)] == [2]
    assert sum(1 for n, _, kind, _, _ in holders(session_id) if n == 2 and kind) == 1
    # Its other Seats get AI players at the lock.
    await sweep.run(START + MINUTE)
    kinds = sorted(k for n, _, k, _, _ in holders(session_id) if n == 2)
    assert kinds == ["rule_based", "rule_based", "rule_based", "student"]


async def test_two_late_registrants_in_one_sweep_share_the_new_class_game(klass):
    session_id, _ = await confirmed(klass, 4)
    first = await student_of(klass, "sen@x.no")
    second = await student_of(klass, "senere@x.no")
    assert (await sweep.run(BEFORE))[SEAT] == 2
    assert [g[1] for g in games_of(session_id)] == [1, 2]
    assert [n for n, _ in seat_of(session_id, first) + seat_of(session_id, second)] == [2, 2]


async def test_after_the_lock_a_late_registrant_takes_an_ai_players_seat(klass, emitted):
    session_id, _ = await opened(klass, 3)
    late = await student_of(klass, "sen@x.no")
    # Listed without a Seat until the sweep seats them.
    assert [s["user_id"] for s in (await read(session_id)).json()["without_seat"]] == [str(late)]
    emitted.clear()
    assert (await sweep.run(START + 2 * MINUTE))[SEAT] == 1
    # The AI player's row stays in the history; the Student holds the Seat from Week 1.
    assert history(late) == [
        ("rule_based", "initial", None),
        ("student", "initial", str(late)),
    ]
    assert {t for t, _ in emitted} == COMMAND_TOPICS[SEAT]
    body = (await read(session_id)).json()
    assert body["opened"] is True and body["without_seat"] == []
    named = {s["user_id"]: s["name"] for g in body["draft"]["games"] for s in g["seats"]}
    assert named[str(late)]
    assert rows("SELECT count(*) FROM notices WHERE user_id = %s", late) == [(1,)]


async def test_after_the_lock_with_no_ai_seat_left_the_student_is_listed_without_one(klass):
    session_id, _ = await opened(klass, 4)
    late = await student_of(klass, "sen@x.no")
    assert await service.late_registrants(START + 2 * MINUTE) == []
    assert (await sweep.run(START + 2 * MINUTE))[SEAT] == 0
    assert await service.seat_late_registrant(uuid.UUID(session_id), late, now=START) is False
    assert await service.students_without_seat(uuid.UUID(session_id)) == [late]
    body = (await read(session_id)).json()
    assert [s["user_id"] for s in body["without_seat"]] == [str(late)]
    assert body["without_seat"][0]["name"]


async def test_a_game_that_started_never_gives_its_ai_seat_away(klass):
    session_id, _ = await opened(klass, 3)
    await games_commands.start(games_of(session_id)[0][0])
    late = await student_of(klass, "sen@x.no")
    assert await service.late_registrants(START + 2 * MINUTE) == []
    assert await service.seat_late_registrant(uuid.UUID(session_id), late, now=START) is False
    assert seat_of(session_id, late) == []
    assert await service.students_without_seat(uuid.UUID(session_id)) == [late]


async def test_a_student_whose_seat_was_taken_over_is_never_seated_again(klass):
    # Five Students: game 1 holds four, game 2 one Student and three AI players, not started.
    session_id, _ = await opened(klass, 5)
    game_id = games_of(session_id)[0][0]
    await games_commands.start(game_id)
    game_one = {role: uuid.UUID(user) for n, role, _, _, user in holders(session_id) if n == 1}
    absent = game_one["factory"]
    taken = await games_commands.takeover(
        game_id, "factory", actor="staff", actor_user_id=game_one["retailer"]
    )
    assert taken is not None
    # The Student's Seat is the AI player's now, but the Student keeps game 1 (FR-37): the sweep
    # does not move them into an AI player's Seat of game 2, and they are not without a Seat.
    assert await service.late_registrants(START + 2 * MINUTE) == []
    assert (await sweep.run(START + 2 * MINUTE))[SEAT] == 0
    assert await service.seat_late_registrant(uuid.UUID(session_id), absent, now=START) is False
    assert [n for n, _, _, _, user in holders(session_id) if user == str(absent)] == []
    assert await service.students_without_seat(uuid.UUID(session_id)) == []


async def test_a_game_started_after_it_was_read_refuses_under_its_row_lock(klass, monkeypatch):
    session_id, _ = await opened(klass, 3)
    game_id = games_of(session_id)[0][0]
    late = await student_of(klass, "sen@x.no")
    # The seating read the game as not started; it starts before the Seat is assigned.
    real = service.games_service.class_games

    async def read_before_the_start(s, class_session_id):
        found = await real(s, class_session_id)
        return [dataclasses.replace(g, lifecycle="not_started") for g in found]

    await games_commands.start(game_id)
    monkeypatch.setattr(service.games_service, "class_games", read_before_the_start)
    assert await service.seat_late_registrant(uuid.UUID(session_id), late, now=START) is False
    assert seat_of(session_id, late) == []


async def test_a_seat_a_removal_frees_takes_a_late_registrant_in_the_same_sweep(klass):
    session_id, seated = await opened(klass, 4)
    execute("UPDATE roster_entries SET removed_at = %s WHERE user_id = %s", NOW, seated[0])
    late = await student_of(klass, "sen@x.no")
    done = await sweep.run(START + 2 * MINUTE)
    assert (done[REPLACE], done[SEAT]) == (1, 1)
    assert history(seated[0]) == [
        ("student", "initial", str(seated[0])),
        ("rule_based", "initial", None),
        ("student", "initial", str(late)),
    ]


async def test_start_racing_the_seating_never_changes_a_started_games_seats(klass):
    session_id, _ = await opened(klass, 3)
    game_id = games_of(session_id)[0][0]
    late = await student_of(klass, "sen@x.no")
    started, seated = await asyncio.gather(
        games_commands.start(game_id),
        service.seat_late_registrant(uuid.UUID(session_id), late, now=START + 2 * MINUTE),
    )
    assert started == 1 and games_of(session_id)[0][2] != "not_started"
    assert bool(seat_of(session_id, late)) is seated
    # No Seat of the Game got an occupant after its first turn was opened (UUIDv7 ids).
    ((last_occupant, first_turn),) = rows(
        "SELECT (SELECT max(o.id::text) FROM seat_occupancy o JOIN seats s ON s.id = o.seat_id "
        "WHERE s.game_id = %s), (SELECT min(t.id::text) FROM seat_turns t "
        "JOIN seats s ON s.id = t.seat_id WHERE s.game_id = %s)",
        game_id,
        game_id,
    )
    assert last_occupant < first_turn


async def test_nothing_before_the_allocation_is_confirmed(klass):
    await students(klass, 3)
    session_id = await dated(klass)
    assert (await open_(session_id)).json()["draft"] is not None
    late = await student_of(klass, "sen@x.no")
    assert await service.late_registrants(BEFORE) == []
    assert await service.seat_late_registrant(uuid.UUID(session_id), late, now=BEFORE) is False


async def test_nothing_for_a_seated_unregistered_or_unknown_student(klass):
    confirmed_id, seated = await confirmed(klass, 1)
    late = await student_of(klass, "sen@x.no")
    sid = uuid.UUID(confirmed_id)
    assert await service.seat_late_registrant(sid, seated[0], now=BEFORE) is False
    assert await service.seat_late_registrant(sid, uuid.uuid7(), now=BEFORE) is False
    assert await service.seat_late_registrant(uuid.uuid7(), late, now=BEFORE) is False


async def test_an_archived_class_seats_nobody(klass):
    session_id, _ = await confirmed(klass, 4)
    late = await student_of(klass, "sen@x.no")
    execute("UPDATE classes SET archived_at = %s WHERE id = %s", NOW, klass)
    assert await service.late_registrants(BEFORE) == []
    assert await service.seat_late_registrant(uuid.UUID(session_id), late, now=BEFORE) is False


async def test_a_removed_students_seat_goes_to_an_ai_player_after_the_open(klass, emitted):
    session_id, seated = await opened(klass, 4)
    gone, *others = seated
    execute("UPDATE roster_entries SET removed_at = %s WHERE user_id = %s", NOW, gone)
    emitted.clear()
    assert (await sweep.run(START + 2 * MINUTE))[REPLACE] == 1
    assert history(gone) == [("student", "initial", str(gone)), ("rule_based", "initial", None)]
    assert {i for t, i in emitted if t == "user"} == {str(s) for s in seated}
    assert {t for t, _ in emitted} == COMMAND_TOPICS[REPLACE]
    assert (await sweep.run(START + 3 * MINUTE))[REPLACE] == 0
    assert await service.replace_removed_student(uuid.UUID(session_id), gone) is False
    assert await service.replace_removed_student(uuid.UUID(session_id), others[0]) is False


async def test_with_llm_players_the_removed_students_seat_gets_one(klass, two_levels):
    session_id, seated = await opened(klass, 4, "llm")
    execute("UPDATE roster_entries SET removed_at = %s WHERE user_id = %s", NOW, seated[0])
    assert (await sweep.run(START + 2 * MINUTE))[REPLACE] == 1
    assert history(seated[0])[-1] == ("llm", "initial", None)


async def test_before_the_lock_a_removal_waits_for_the_open(klass):
    session_id, seated = await confirmed(klass, 4)
    execute("UPDATE roster_entries SET removed_at = %s WHERE user_id = %s", NOW, seated[0])
    assert await service.removed_students(BEFORE) == []
    assert await service.replace_removed_student(uuid.UUID(session_id), seated[0]) is False


async def test_a_started_games_removed_student_keeps_the_seat_and_is_marked(klass):
    session_id, seated = await opened(klass, 4)
    await games_commands.start(games_of(session_id)[0][0])
    gone = seated[0]
    execute("UPDATE roster_entries SET removed_at = %s WHERE user_id = %s", NOW, gone)
    assert (await sweep.run(START + 2 * MINUTE))[REPLACE] == 0
    assert history(gone) == [("student", "initial", str(gone))]
    body = (await read(session_id)).json()
    seats = {s["user_id"]: s["name"] for g in body["draft"]["games"] for s in g["seats"]}
    # Held by a removed Student: an id with no name («Ikke lenger i Klassen»).
    assert str(gone) in seats and seats[str(gone)] is None
