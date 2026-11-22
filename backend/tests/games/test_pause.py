"""Story 8.6: a Student pauses the Class game with «Ta pause» (FR-89, FR-36, FR-39, AD-2, AD-8,
AD-13, AD-25).

`games.commands.pause` writes the Pause columns under the Game row lock; `rules.game_status` then
says `paused` and `rules.can_take_over` refuses the automatic Takeover, so the sweep takes no Seat
over while the stored due times keep running unmoved. Any Student's Order ends the Pause in its own
transaction, and a Seat past its due time is then taken at the next sweep. The clock is injected
from the stored due time, never read from the host (Issue #63)."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.games import commands, rules, views
from app.modules.games.schemas import GameStatus
from app.modules.ops import sweep
from app.platform.db import get_sessionmaker
from app.platform.events.registry import COMMAND_TOPICS
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import execute, listening, query
from tests.games.test_game_summaries import check
from tests.games.test_takeover import class_game, due_of, open_week, takeovers

SECOND = timedelta(seconds=1)


def pause_columns(game_id: str) -> tuple:
    [row] = query(
        TEST_DATABASE_URL,
        "SELECT paused_at, paused_by, resume_at, pause_ended_at, pause_ended_by, lifecycle "
        "FROM games WHERE id = %s",
        (game_id,),
    )
    return row


async def refused(call) -> commands.CommandError:
    with pytest.raises(commands.CommandError) as caught:
        await call
    return caught.value


async def test_a_student_pauses_and_a_second_pause_names_who_came_first(games_db, mail_db):
    game_id, students = await class_game()
    sara, jonas = students["retailer"], students["factory"]
    (version,) = query(TEST_DATABASE_URL, "SELECT version FROM games WHERE id = %s", (game_id,))[0]
    with listening(games_db) as events:
        await commands.pause(game_id, actor=sara)
        received = events.drain()
    paused_at, paused_by, resume_at, ended_at, ended_by, lifecycle = pause_columns(game_id)
    assert (paused_by, resume_at, ended_at, ended_by, lifecycle) == (
        sara,
        None,
        None,
        None,
        "running",
    )
    assert paused_at is not None
    assert {e["topic"] for e in received} == COMMAND_TOPICS["games.pause"]
    assert {e["id"] for e in received if e["topic"] == "user"} == {str(sara), str(jonas)}
    row = await check(game_id)  # the summary equals a recomputation
    assert (row["status"], row["paused_at"], row["paused_by"], row["waiting_for"]) == (
        "paused",
        paused_at,
        sara,
        [],
    )
    assert row["version"] == version + 1
    # The audit row names the Student and the game, ids only.
    [(actor, action, target, change)] = query(
        TEST_DATABASE_URL,
        "SELECT actor_user_id, action, target_ids, change FROM audit_events "
        "WHERE target_ids->>'game_id' = %s",
        (game_id,),
    )
    assert (actor, action, target, change["resume_at"]) == (
        sara,
        "game.paused",
        {"game_id": game_id},
        None,
    )

    second = await refused(commands.pause(game_id, actor=jonas))
    assert (second.code, second.status) == ("already_paused", 409)
    assert second.fields == {
        "acted_by": {"kind": "student", "user_id": str(sara)},
        "acted_at": paused_at.isoformat(),
    }
    assert pause_columns(game_id)[:2] == (paused_at, sara)


async def test_no_takeover_while_paused_and_the_next_sweep_after_an_order(games_db, mail_db):
    game_id, students = await class_game(("retailer", "wholesaler", "factory"))
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    due = due_of(game_id, "factory")
    assert due is not None
    await commands.pause(game_id, actor=students["factory"])

    # Past the due time the sweep finds nothing, and the command itself refuses.
    assert (await sweep.run(due + 30 * SECOND))["games.takeover"] == 0
    assert takeovers(game_id) == []
    error = await refused(commands.takeover(game_id, "factory", actor="system", now=due))
    assert error.code == "game_paused"
    assert due_of(game_id, "factory") == due  # the clock kept running: nothing moved

    # A Guided-Week view would not end it; an Order by any Student does, whoever paused.
    await commands.place_order(game_id, "wholesaler", 1, 4, "student", actor=students["wholesaler"])
    paused_at, paused_by, resume_at, ended_at, ended_by, _ = pause_columns(game_id)
    assert (paused_at, paused_by, resume_at, ended_by) == (None, None, None, students["wholesaler"])
    assert ended_at is not None
    row = await check(game_id)
    assert (row["status"], row["paused_at"], [w["role"] for w in row["waiting_for"]]) == (
        "waiting",
        None,
        ["factory"],
    )
    # The overdue Seat is taken at the next sweep, within the minute.
    assert (await sweep.run(due + 60 * SECOND))["games.takeover"] == 1
    assert takeovers(game_id) == [("factory", 1, "rule_based", None)]
    assert open_week(game_id) == 2


async def test_the_order_that_ends_the_pause_tells_every_student(games_db, mail_db):
    game_id, students = await class_game(("retailer", "wholesaler", "factory"))
    await commands.pause(game_id, actor=students["retailer"])
    with listening(games_db) as events:
        placed = await commands.place_order(
            game_id, "factory", 1, 4, "student", actor=students["factory"]
        )
        received = events.drain()
    assert placed.pause_ended and placed.open_week == 1
    assert {e["id"] for e in received if e["topic"] == "user"} == {
        str(u) for u in students.values()
    }


async def test_a_guided_view_does_not_end_the_pause(games_db, mail_db):
    game_id, students = await class_game(guided_weeks=1)
    await commands.pause(game_id, actor=students["retailer"])
    await commands.view_week(game_id, "factory", 1, actor=students["factory"])
    assert pause_columns(game_id)[1] == students["retailer"]
    assert (await check(game_id))["status"] == "paused"


async def test_an_ai_players_order_does_not_end_the_pause(games_db, mail_db):
    """A staff Takeover while paused (staff are not limited) has the AI player order at once; that
    Order is no Student's and leaves the Pause in force."""
    game_id, students = await class_game(("retailer", "wholesaler", "factory"))
    await commands.pause(game_id, actor=students["retailer"])
    staff = uuid.uuid7()
    await commands.takeover(game_id, "factory", actor="staff", actor_user_id=staff)
    assert takeovers(game_id) == []  # a staff row, not an inactivity one
    assert pause_columns(game_id)[1] == students["retailer"]
    assert (await check(game_id))["status"] == "paused"


async def test_who_may_pause(games_db, mail_db):
    game_id, students = await class_game()
    outsider = uuid.uuid7()
    assert (await refused(commands.pause(game_id, actor=outsider))).code == "seat_not_yours"
    # A Student whose Seat an AI player took over holds no Seat now.
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    due = due_of(game_id, "factory")
    await commands.takeover(game_id, "factory", actor="system", now=due)
    assert (await refused(commands.pause(game_id, actor=students["factory"]))).code == (
        "seat_not_yours"
    )
    missing = await refused(commands.pause(str(uuid.uuid7()), actor=students["retailer"]))
    assert (missing.code, missing.status) == ("game_not_found", 404)
    assert pause_columns(game_id)[0] is None


async def can_pause(game_id: str, viewer: uuid.UUID) -> bool:
    """Whether `views.table_status` offers «Ta pause» to `viewer`."""

    async def no_names(ids):
        return {}

    async with get_sessionmaker()() as session:
        status = await views.table_status(session, uuid.UUID(game_id), viewer, no_names)
    return status.can_pause


async def test_not_started_finished_and_test_games_have_no_pause(games_db, mail_db):
    unstarted = await commands.create("class", class_session_id=uuid.uuid7(), game_number=1)
    student = uuid.uuid7()
    await commands.assign_seat(unstarted, "retailer", "student", user_id=student)
    assert not await can_pause(unstarted, student)
    error = await refused(commands.pause(unstarted, actor=student))
    assert (error.code, error.status) == ("game_not_running", 409)
    # The same Game running, finished, then as a Lecturer's test Game, whose policy has no Pause.
    game_id, students = await class_game()
    assert await can_pause(game_id, students["retailer"])
    execute(TEST_DATABASE_URL, "UPDATE games SET lifecycle = 'finished' WHERE id = %s", (game_id,))
    assert not await can_pause(game_id, students["retailer"])
    assert (await refused(commands.pause(game_id, actor=students["retailer"]))).code == (
        "game_finished"
    )
    execute(
        TEST_DATABASE_URL,
        "UPDATE games SET lifecycle = 'running', purpose = 'lecturer_test', game_number = NULL "
        "WHERE id = %s",
        (game_id,),
    )
    assert not await can_pause(game_id, students["retailer"])
    assert (await refused(commands.pause(game_id, actor=students["retailer"]))).code == (
        "pause_not_allowed"
    )


NOW = datetime(2026, 11, 21, 12, tzinfo=UTC)


def test_the_status_and_the_takeover_check_read_the_pause():
    game = {"lifecycle": "running", "purpose": "class", "settings": None, "paused_at": NOW}
    assert rules.game_status(game, []) is GameStatus.PAUSED
    assert rules.game_status({**game, "lifecycle": "finished"}, []) is GameStatus.FINISHED
    assert rules.game_status({**game, "lifecycle": "not_started"}, []) is GameStatus.NOT_STARTED
    turn = {
        "occupant_kind": "student",
        "ordered_at": None,
        "viewed_at": None,
        "takeover_due_at": NOW - SECOND,
    }
    seat = {"occupant_kind": "student", "reason": "initial"}
    can = rules.can_take_over
    assert can(game, turn, "system", NOW, guided=False, seat=seat) == "game_paused"
    # Staff are not limited by a Pause (Story 8.5's per-Seat action stays).
    assert can(game, turn, "staff", NOW, guided=False, seat=seat) is None
    assert can({**game, "paused_at": None}, turn, "system", NOW, guided=False, seat=seat) is None
