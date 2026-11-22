"""Story 8.11: «I rommet» on the turn times (FR-36, AD-2, AD-9, AD-20).

`games.commands.mark_in_room` replaces the Inactivity limit with the in-room limit (times each
Student's Tilrettelegging factor) for the open Week and every Week that opens while the mark
holds; `end_in_room` puts the limit back from the same wait starts, by a person, by the sweep at
the Lab hour's end, or through `games.service.lab_hour_changed` when the Lab hour is moved or
removed. The factor comes from `sessions.service.time_factors`, stubbed here. Times are read from
the database, never compared with the host clock (Issue #63)."""

import uuid
from datetime import timedelta

import pytest

from app.engine import GameSettings
from app.modules.games import commands
from app.modules.games import service as games_service
from app.modules.ops import sweep
from app.modules.sessions import service as sessions_service
from app.platform.events.registry import COMMAND_TOPICS
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import listening, query
from tests.games.test_game_summaries import check
from tests.games.test_staff_pause import LECTURER, db_now, insert_of
from tests.games.test_takeover import class_game, due_of, open_week, takeovers
from tests.games.test_turn_factor import wait_of

MINUTE = timedelta(minutes=1)
LIMIT = timedelta(hours=24)
LAB = uuid.UUID("01900000-0000-7000-8000-0000000b8110")


@pytest.fixture
def factors(monkeypatch) -> dict[uuid.UUID, float]:
    """The factors `sessions.service.time_factors` answers, by Student."""
    found: dict[uuid.UUID, float] = {}

    async def stub(session, class_session_id, user_ids):
        return {user: found[user] for user in user_ids if user in found}

    monkeypatch.setattr(sessions_service, "time_factors", stub)
    return found


def audit_actions(game_id: str) -> list[tuple]:
    return query(
        TEST_DATABASE_URL,
        "SELECT action, actor_user_id, change FROM audit_events "
        "WHERE target_ids->>'game_id' = %s AND action LIKE 'game.%%room%%' ORDER BY id",
        (game_id,),
    )


def mark_of(game_id: str) -> tuple:
    [row] = query(
        TEST_DATABASE_URL,
        "SELECT in_room_minutes, in_room_until, in_room_lab_hour_id, in_room_by FROM games "
        "WHERE id = %s",
        (game_id,),
    )
    return row


async def mark(game_id: str, minutes: object = 10, **kw) -> bool:
    now = kw.pop("now", None) or db_now()
    return await commands.mark_in_room(
        game_id,
        minutes,
        actor=kw.pop("actor", LECTURER),
        lab_hour_id=kw.pop("lab_hour_id", LAB),
        until=kw.pop("until", now + timedelta(hours=1)),
        now=now,
    )


async def test_marking_shortens_the_open_weeks_limit_and_ending_restores_it(
    games_db, mail_db, factors
):
    game_id, students = await class_game(("retailer", "wholesaler", "factory"))
    factors[students["factory"]] = 2.0  # Jonas keeps his own extended limit in the room too
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    wait = wait_of(game_id, "factory")
    assert due_of(game_id, "wholesaler") == wait + LIMIT

    until = (db_now() + timedelta(hours=1)).replace(microsecond=0)
    with listening(games_db) as events:
        assert await mark(game_id, 10, until=until)
        received = events.drain()
    assert {e["topic"] for e in received} == COMMAND_TOPICS["games.mark_in_room"]
    assert {e["id"] for e in received if e["topic"] == "user"} == {
        str(u) for u in students.values()
    }
    # From the same wait start: 10 min, and 20 min for Jonas's 2 ×.
    assert due_of(game_id, "wholesaler") == wait + 10 * MINUTE
    assert due_of(game_id, "factory") == wait + 20 * MINUTE
    assert due_of(game_id, "retailer") is None  # it has ordered
    assert mark_of(game_id) == (10, until, LAB, LECTURER)
    row = await check(game_id)  # the summary follows, with the wall's mark
    assert row["in_room_until"] == until
    assert row["takeover_due_at"] == wait + 10 * MINUTE

    # A second mark is told who marked first, by id (Story 8.5's shape).
    with pytest.raises(commands.CommandError) as again:
        await mark(game_id, 20)
    assert (again.value.status, again.value.code) == (409, "already_in_room")
    assert again.value.fields["acted_by"] == {"kind": "staff", "user_id": str(LECTURER)}
    assert again.value.fields["acted_at"] is not None

    # «Ikke i rommet lenger»: back to the Inactivity limit from the same wait start.
    with listening(games_db) as events:
        assert await commands.end_in_room(game_id, actor=LECTURER)
        received = events.drain()
    assert {e["topic"] for e in received} == COMMAND_TOPICS["games.end_in_room"]
    assert due_of(game_id, "wholesaler") == wait + LIMIT
    assert due_of(game_id, "factory") == wait + 2 * LIMIT
    assert wait_of(game_id, "factory") == wait
    assert mark_of(game_id) == (None, None, None, None)
    assert (await check(game_id))["in_room_until"] is None
    with pytest.raises(commands.CommandError) as unmarked:
        await commands.end_in_room(game_id, actor=LECTURER)
    assert (unmarked.value.status, unmarked.value.code) == (409, "not_in_room")
    # The system finds nothing to end and writes nothing.
    assert not await commands.end_in_room(game_id, actor=None, now=until)

    actions = audit_actions(game_id)
    assert [(a, actor) for a, actor, _ in actions] == [
        ("game.marked_in_room", LECTURER),
        ("game.in_room_ended", LECTURER),
    ]
    assert actions[0][2] == {"minutes": 10, "in_room_until": until.isoformat()}


async def test_marks_out_of_range_outside_a_lab_hour_or_on_a_game_not_running_are_refused(
    games_db, mail_db
):
    game_id, _ = await class_game()
    for minutes in (1, 121, 7.5, True, "10", None):
        with pytest.raises(commands.CommandError) as refused:
            await mark(game_id, minutes)
        assert (refused.value.status, refused.value.code) == (422, "minutes_out_of_range")
    now = db_now()
    with pytest.raises(commands.CommandError) as over:
        await mark(game_id, 10, now=now, until=now)
    assert (over.value.status, over.value.code) == (409, "not_in_lab_hour")
    assert mark_of(game_id) == (None, None, None, None)

    waiting = await commands.create("class", class_session_id=uuid.uuid7(), game_number=1)
    with pytest.raises(commands.CommandError) as not_started:
        await mark(waiting)
    assert (not_started.value.status, not_started.value.code) == (409, "game_not_running")
    simulation = await commands.create("simulation", GameSettings(weeks=8), seed=1)
    with pytest.raises(commands.CommandError) as no_takeover:
        await mark(simulation)
    assert (no_takeover.value.status, no_takeover.value.code) == (409, "in_room_not_allowed")


async def test_the_sweep_takes_over_on_the_in_room_limit_and_ends_the_mark_at_the_lab_hours_end(
    games_db, mail_db
):
    game_id, students = await class_game(("retailer", "wholesaler", "factory"))
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    wait = wait_of(game_id, "factory")
    until = wait + timedelta(hours=1)
    assert await mark(game_id, 5, now=wait, until=until)
    due = due_of(game_id, "factory")
    assert due == wait + 5 * MINUTE

    # Within the minute of the in-room due time, the automatic Takeover of Story 8.2.
    done = await sweep.run(due)
    assert done["games.takeover"] == 2  # the Grossist and the Fabrikk
    assert done["games.end_in_room"] == 0
    assert {role for role, *_ in takeovers(game_id)} == {"wholesaler", "factory"}

    assert open_week(game_id) == 2  # the AI players ordered Uke 1 at once

    # At the Lab hour's end the sweep ends the mark, once.
    assert (await sweep.run(until - MINUTE))["games.end_in_room"] == 0
    assert (await sweep.run(until))["games.end_in_room"] == 1
    assert (await sweep.run(until))["games.end_in_room"] == 0
    assert mark_of(game_id) == (None, None, None, None)
    await check(game_id)


async def test_a_new_week_under_the_mark_waits_on_the_in_room_limit(games_db, mail_db):
    game_id, students = await class_game(("retailer", "factory"))
    assert await mark(game_id, 3)
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    wait = wait_of(game_id, "factory")
    assert due_of(game_id, "factory") == wait + 3 * MINUTE


async def test_a_moved_or_removed_lab_hour_moves_or_ends_its_marks(games_db, mail_db):
    first, _ = await class_game()
    second, _ = await class_game()
    now = db_now()
    until = (now + timedelta(hours=1)).replace(microsecond=0)
    other = uuid.uuid7()
    assert await mark(first, 10, now=now, until=until)
    assert await mark(second, 10, now=now, until=until, lab_hour_id=other)

    # Moved to end later: the mark follows; the other Lab hour's mark is untouched.
    later = until + timedelta(minutes=30)
    assert await games_service.lab_hour_changed(LAB, now - MINUTE, later, now) == 1
    assert mark_of(first)[1] == later
    assert mark_of(second)[1] == until
    assert await games_service.lab_hour_changed(LAB, now - MINUTE, later, now) == 0  # unchanged
    await check(first)

    # Moved so it is no longer on: the mark ends. Removed: the other one ends too.
    assert await games_service.lab_hour_changed(LAB, now + MINUTE, later, now) == 1
    assert mark_of(first) == (None, None, None, None)
    assert await games_service.lab_hour_changed(other, None, None, now) == 1
    assert mark_of(second) == (None, None, None, None)
    # The system's own writes are not audited as a person's.
    assert [a for a, *_ in audit_actions(first)] == ["game.marked_in_room"]


async def test_a_seat_due_before_the_lab_hours_end_is_taken_in_the_sweep_that_ends_the_mark(
    games_db, mail_db
):
    """The sweep's Takeover runs before its in-room end: a Seat whose in-room due time passed by
    the Lab hour's end is still taken over in that same minute, not handed the long limit."""
    game_id, students = await class_game(("retailer", "factory"))
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    wait = wait_of(game_id, "factory")
    until = wait + 10 * MINUTE
    assert await mark(game_id, 5, now=wait, until=until)
    done = await sweep.run(until)  # the first sweep after the due time is the Lab hour's end
    assert (done["games.takeover"], done["games.end_in_room"]) == (1, 1)
    assert [role for role, *_ in takeovers(game_id)] == ["factory"]


async def test_a_pause_under_the_mark_keeps_the_in_room_insert_times(games_db, mail_db):
    """`_recompute_insert_times` (Story 8.7) reads the in-room limit too: a Lecturer's Pause and
    its end leave the insert time on the in-room due time, and an agreed time stands as usual."""
    game_id, students = await class_game(("retailer", "factory"))
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    wait = wait_of(game_id, "factory")
    assert await mark(game_id, 10, now=wait, until=wait + timedelta(hours=1))
    assert insert_of(game_id, "factory") == wait + 10 * MINUTE
    agreed = (db_now() + timedelta(hours=2)).replace(microsecond=0)
    await commands.pause(game_id, actor=LECTURER, staff=True, resume_at=agreed)
    assert insert_of(game_id, "factory") == agreed
    await commands.set_agreed_time(game_id, None, actor=LECTURER)
    assert insert_of(game_id, "factory") == wait + 10 * MINUTE
    await commands.resume(game_id, actor=LECTURER)
    assert (due_of(game_id, "factory"), insert_of(game_id, "factory")) == (
        wait + 10 * MINUTE,
        wait + 10 * MINUTE,
    )


@pytest.mark.parametrize(
    ("minutes", "factor", "shown"),
    [(10, None, 10), (5, 1.5, 7), (7, 3.0, 21), (10, 0.5, 10)],
)
def test_the_students_own_minutes_are_rounded_down_and_never_shortened(minutes, factor, shown):
    from datetime import UTC, datetime

    from app.modules.games.views import _in_room

    until = datetime(2026, 11, 24, 15, tzinfo=UTC)
    game = {"in_room_minutes": minutes, "in_room_until": until, "lifecycle": "running"}
    found = _in_room(game, factor)  # type: ignore[arg-type]
    assert found is not None and (found.until, found.minutes) == (until, shown)
    assert _in_room({**game, "lifecycle": "finished"}, factor) is None  # type: ignore[arg-type]
    assert _in_room({**game, "in_room_minutes": None}, factor) is None  # type: ignore[arg-type]
