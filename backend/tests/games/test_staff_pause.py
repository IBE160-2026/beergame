"""Story 8.7: a Lecturer pauses a Class game with an agreed time, changes it and ends the Pause
(FR-89, AD-2, AD-8, AD-9, AD-10, AD-15, AD-20).

`games.commands.pause` with a staff actor, `set_agreed_time` and `resume` write the Pause columns
under the Game row lock and recompute the open Week's insert times through `rules.turn_times`; the
Takeover due times never move. The sweep marks an agreed time once it has passed and emits the
Game's events, but never ends the Pause and never takes a Seat. Times are judged on the database
clock: every agreed time here is read from it, never from the host (Issue #63)."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.games import commands, rules
from app.modules.games.schemas import OccupantKind
from app.modules.ops import sweep
from app.platform.events.registry import COMMAND_TOPICS
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import execute, listening, query
from tests.games.test_game_summaries import check
from tests.games.test_takeover import class_game, due_of, takeovers

HOUR = timedelta(hours=1)
SECOND = timedelta(seconds=1)
LECTURER = uuid.UUID("01900000-0000-7000-8000-00000000a807")


def db_now() -> datetime:
    [(now,)] = query(TEST_DATABASE_URL, "SELECT clock_timestamp()", ())
    return now


def insert_of(game_id: str, role: str, week: int = 1) -> datetime | None:
    [(at,)] = query(
        TEST_DATABASE_URL,
        "SELECT t.insert_allowed_at FROM seat_turns t JOIN seats s ON s.id = t.seat_id "
        "WHERE t.game_id = %s AND s.role = %s AND t.week = %s",
        (game_id, role, week),
    )
    return at


def pause_row(game_id: str) -> tuple:
    [row] = query(
        TEST_DATABASE_URL,
        "SELECT paused_by, resume_at, agreed_time_reached_at, pause_ended_by, version "
        "FROM games WHERE id = %s",
        (game_id,),
    )
    return row


def audit_actions(game_id: str) -> list[tuple]:
    return query(
        TEST_DATABASE_URL,
        "SELECT actor_user_id, action, change FROM audit_events "
        "WHERE target_ids->>'game_id' = %s ORDER BY id",
        (game_id,),
    )


async def refused(call) -> commands.CommandError:
    with pytest.raises(commands.CommandError) as caught:
        await call
    return caught.value


# `rules.turn_times`: the agreed time as insert time (pure).

START = datetime(2026, 11, 21, 12, tzinfo=UTC)
AGREED = START + 3 * HOUR
STUDENT = rules.TurnSeat(occupant_kind=OccupantKind.STUDENT, opened_at=START)


@pytest.mark.parametrize(
    ("clock_start", "factor", "expected"),
    [
        # With a clock: the agreed time wins, earlier or later than the limit.
        (START, None, (START + 24 * HOUR, AGREED)),
        # Tilrettelegging never gets an insert time before its own extended limit.
        (START, 1.5, (START + 36 * HOUR, START + 36 * HOUR)),
        # No clock yet (nobody else ordered): no due time, the agreed time stands.
        (None, None, (None, AGREED)),
        (None, 1.5, (None, AGREED)),
    ],
)
def test_the_agreed_time_is_the_insert_time(clock_start, factor, expected):
    times = rules.turn_times(
        rules.TurnGame(guided_week=False),
        STUDENT,
        rules.TurnInputs(
            clock_start=clock_start,
            inactivity_limit=24 * HOUR,
            time_factor=factor,
            agreed_time=AGREED,
        ),
    )
    assert (times.takeover_due_at, times.insert_allowed_at) == expected


def test_without_a_limit_the_agreed_time_still_stands():
    times = rules.turn_times(
        rules.TurnGame(guided_week=False),
        STUDENT,
        rules.TurnInputs(clock_start=START, agreed_time=AGREED),
    )
    assert (times.takeover_due_at, times.insert_allowed_at) == (None, AGREED)


def test_an_ai_seat_gets_no_insert_time_from_an_agreed_time():
    ai = rules.TurnSeat(occupant_kind=OccupantKind.RULE_BASED, opened_at=START)
    times = rules.turn_times(
        rules.TurnGame(guided_week=False), ai, rules.TurnInputs(agreed_time=AGREED)
    )
    assert times.insert_allowed_at is None


# The commands.


async def test_a_lecturer_pauses_with_an_agreed_time_changes_it_and_ends_it(games_db, mail_db):
    game_id, students = await class_game(("retailer", "wholesaler", "factory"))
    sara = students["retailer"]
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=sara)
    due = due_of(game_id, "factory")
    assert due is not None and insert_of(game_id, "factory") == due
    agreed = (db_now() + 2 * HOUR).replace(microsecond=0)

    with listening(games_db) as events:
        await commands.pause(game_id, actor=LECTURER, staff=True, resume_at=agreed)
        received = events.drain()
    paused_by, resume_at, reached, _, version = pause_row(game_id)
    assert (paused_by, resume_at, reached) == (LECTURER, agreed, None)
    assert {e["topic"] for e in received} == COMMAND_TOPICS["games.pause"]
    assert {e["id"] for e in received if e["topic"] == "user"} == {
        str(u) for u in students.values()
    }
    # The agreed time is the insert time of every Seat that has not ordered; due times stay.
    assert (insert_of(game_id, "factory"), insert_of(game_id, "wholesaler")) == (agreed, agreed)
    assert insert_of(game_id, "retailer") is None  # it has ordered
    assert due_of(game_id, "factory") == due
    assert (await check(game_id))["status"] == "paused"

    later = agreed + HOUR
    with listening(games_db) as events:
        assert await commands.set_agreed_time(game_id, later, actor=LECTURER)
        received = events.drain()
    assert {e["topic"] for e in received} == COMMAND_TOPICS["games.set_agreed_time"]
    assert pause_row(game_id)[:2] == (LECTURER, later)
    await check(game_id)  # set_agreed_time leaves the summary equal to a recomputation
    assert insert_of(game_id, "factory") == later
    # The same time again writes nothing.
    assert not await commands.set_agreed_time(game_id, later, actor=LECTURER)
    assert pause_row(game_id)[4] == version + 1

    with listening(games_db) as events:
        assert await commands.resume(game_id, actor=LECTURER)
        received = events.drain()
    assert {e["topic"] for e in received} == COMMAND_TOPICS["games.resume"]
    paused_by, resume_at, reached, ended_by, _ = pause_row(game_id)
    assert (paused_by, resume_at, reached, ended_by) == (None, None, None, LECTURER)
    # Back to the limit: no insert time had passed yet.
    assert insert_of(game_id, "factory") == due
    assert due_of(game_id, "factory") == due
    assert (await check(game_id))["status"] == "waiting"

    assert [(actor, action) for actor, action, _ in audit_actions(game_id)] == [
        (LECTURER, "game.paused"),
        (LECTURER, "game.pause_time_set"),
        (LECTURER, "game.resumed"),
    ]
    changes = [change for _, _, change in audit_actions(game_id)]
    assert changes[0]["resume_at"] == agreed.isoformat()
    assert (changes[1]["resume_at"], changes[1]["was"]) == (later.isoformat(), agreed.isoformat())


async def test_the_lecturer_sets_a_time_on_a_students_pause(games_db, mail_db):
    game_id, students = await class_game()
    sara = students["retailer"]
    await commands.pause(game_id, actor=sara)
    agreed = (db_now() + HOUR).replace(microsecond=0)
    assert await commands.set_agreed_time(game_id, agreed, actor=LECTURER)
    assert pause_row(game_id)[:2] == (sara, agreed)
    # No clock runs (nobody has ordered): the agreed time stands as both Seats' insert time.
    assert (insert_of(game_id, "retailer"), insert_of(game_id, "factory")) == (agreed, agreed)
    # «Uten avtalt tid» clears it again.
    assert await commands.set_agreed_time(game_id, None, actor=LECTURER)
    assert pause_row(game_id)[:2] == (sara, None)
    assert insert_of(game_id, "factory") is None


async def test_a_time_outside_now_to_the_play_deadline_is_refused(games_db, mail_db):
    game_id, _ = await class_game()
    now = db_now()
    deadline = now + 5 * HOUR
    for at in (now - SECOND, deadline + SECOND):
        error = await refused(
            commands.pause(game_id, actor=LECTURER, staff=True, resume_at=at, latest=deadline)
        )
        assert (error.code, error.status) == ("time_out_of_range", 422)
    assert pause_row(game_id)[:2] == (None, None)
    # The Play deadline itself is allowed; with none, a time up to the horizon.
    await commands.pause(game_id, actor=LECTURER, staff=True, resume_at=deadline, latest=deadline)
    error = await refused(
        commands.set_agreed_time(game_id, now + commands.PROPOSAL_HORIZON + HOUR, actor=LECTURER)
    )
    assert error.code == "time_out_of_range"
    naive = await refused(
        commands.set_agreed_time(game_id, datetime(2030, 1, 1), actor=LECTURER)  # noqa: DTZ001
    )
    assert naive.code == "time_out_of_range"


async def test_refusals_of_change_and_end(games_db, mail_db):
    game_id, students = await class_game()
    soon = db_now() + HOUR
    for call in (
        commands.set_agreed_time(game_id, soon, actor=LECTURER),
        commands.resume(game_id, actor=LECTURER),
    ):
        error = await refused(call)
        assert (error.code, error.status) == ("not_paused", 409)
    await commands.pause(game_id, actor=LECTURER, staff=True)
    second = await refused(commands.pause(game_id, actor=students["retailer"]))
    assert second.code == "already_paused"
    assert second.fields["acted_by"] == {"kind": "staff", "user_id": str(LECTURER)}
    with pytest.raises(ValueError):
        await commands.pause(game_id, actor=students["retailer"], resume_at=soon)
    missing = await refused(commands.resume(str(uuid.uuid7()), actor=LECTURER))
    assert (missing.code, missing.status) == ("game_not_found", 404)


async def test_ending_the_pause_keeps_an_insert_time_already_passed(games_db, mail_db):
    game_id, students = await class_game(("retailer", "wholesaler", "factory"))
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    due = due_of(game_id, "factory")
    await commands.pause(game_id, actor=LECTURER, staff=True, resume_at=db_now() + HOUR)
    # The agreed time has passed (set directly: a test never waits on real time).
    passed = db_now() - SECOND
    execute(
        TEST_DATABASE_URL,
        "UPDATE seat_turns SET insert_allowed_at = %s WHERE game_id = %s "
        "AND seat_id = (SELECT id FROM seats WHERE game_id = %s AND role = 'factory')",
        (passed, game_id, game_id),
    )
    await commands.resume(game_id, actor=LECTURER)
    assert insert_of(game_id, "factory") == passed  # the right survives the end
    assert insert_of(game_id, "wholesaler") == due  # not passed: back to the limit


async def test_the_first_order_keeps_the_agreed_time_and_ends_the_pause(games_db, mail_db):
    game_id, students = await class_game(("retailer", "wholesaler", "factory"))
    agreed = (db_now() + HOUR).replace(microsecond=0)
    await commands.pause(game_id, actor=LECTURER, staff=True, resume_at=agreed)
    placed = await commands.place_order(
        game_id, "retailer", 1, 4, "student", actor=students["retailer"]
    )
    assert placed.pause_ended
    assert pause_row(game_id)[:4] == (None, None, None, students["retailer"])
    # The clock starts now, but the agreed time stays the insert time for this Week.
    due = due_of(game_id, "factory")
    assert due is not None and due != agreed
    assert insert_of(game_id, "factory") == agreed
    # A later Pause without a time (a Student's) leaves that insert time as it is.
    await commands.pause(game_id, actor=students["wholesaler"])
    assert insert_of(game_id, "factory") == agreed
    # The same agreed time again is no change, also once it would be out of range.
    assert await commands.set_agreed_time(game_id, agreed, actor=LECTURER)
    assert not await commands.set_agreed_time(game_id, agreed, actor=LECTURER)


async def test_the_sweep_marks_the_agreed_time_once_and_takes_no_seat(games_db, mail_db):
    game_id, students = await class_game(("retailer", "wholesaler", "factory"))
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    due = due_of(game_id, "factory")
    assert due is not None
    agreed = (db_now() + HOUR).replace(microsecond=0)
    await commands.pause(game_id, actor=LECTURER, staff=True, resume_at=agreed)
    version = pause_row(game_id)[4]

    assert (await sweep.run(agreed - SECOND))["games.reach_agreed_time"] == 0
    with listening(games_db) as events:
        done = await sweep.run(agreed)
        received = events.drain()
    assert done["games.reach_agreed_time"] == 1
    assert {e["topic"] for e in received} >= COMMAND_TOPICS["games.reach_agreed_time"]
    _, resume_at, reached, _, after = pause_row(game_id)
    assert (resume_at, reached, after) == (agreed, agreed, version + 1)
    assert (await check(game_id))["status"] == "paused"  # the Pause goes on
    # Idempotent, and past the due time no Takeover runs while paused.
    assert (await sweep.run(due + SECOND))["games.reach_agreed_time"] == 0
    assert takeovers(game_id) == []
    assert not await commands.reach_agreed_time(game_id, now=due)
    # A Game that no longer runs is never announced (its Pause cannot be acted on).
    execute(
        TEST_DATABASE_URL, "UPDATE games SET lifecycle = 'playing_out' WHERE id = %s", (game_id,)
    )
    execute(
        TEST_DATABASE_URL,
        "UPDATE games SET agreed_time_reached_at = NULL WHERE id = %s",
        (game_id,),
    )
    assert (await sweep.run(agreed))["games.reach_agreed_time"] == 0
    assert not await commands.reach_agreed_time(game_id, now=agreed)
    execute(TEST_DATABASE_URL, "UPDATE games SET lifecycle = 'running' WHERE id = %s", (game_id,))
    # A new time clears the mark, so the sweep announces it again when it passes.
    later = agreed + HOUR
    await commands.set_agreed_time(game_id, later, actor=LECTURER)
    assert pause_row(game_id)[2] is None
    assert not await commands.reach_agreed_time(game_id, now=agreed)
    assert await commands.reach_agreed_time(game_id, now=later)
    # Another Student's Order ends the Pause; the absent Seat keeps the agreed time as its insert
    # time for this Week (open-assumptions), and its due time never moved.
    await commands.place_order(game_id, "wholesaler", 1, 4, "student", actor=students["wholesaler"])
    assert pause_row(game_id)[:3] == (None, None, None)
    assert (insert_of(game_id, "factory"), due_of(game_id, "factory")) == (later, due)
