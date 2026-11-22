"""Story 8.10: `games.commands.start` records who started the Game and when (FR-22, AD-2, AD-15).

`start(…, actor=…)` stores `started_by` and `started_at` (the transaction's clock) under the Game
row lock and records a person's start in the audit log; a start that comes second answers 409
`game_already_started` with Story 8.5's `fields.acted_by` and `fields.acted_at`, by id only."""

import uuid

import pytest

from app.modules.games import commands
from app.platform.events.registry import COMMAND_TOPICS
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import listening, query, tamper
from tests.games.test_set_snapshot import SETTINGS, snapshot
from tests.games.test_takeover import _user

LECTURER = uuid.UUID("01900000-0000-7000-8000-00000000a810")


async def ready_game() -> tuple[str, dict[str, uuid.UUID]]:
    """A Class game with its snapshot, not started; two Students hold Seats."""
    game_id = await commands.create("class", class_session_id=uuid.uuid7(), game_number=1)
    students = {role: _user() for role in ("retailer", "factory")}
    for role, user in students.items():
        await commands.assign_seat(game_id, role, "student", user_id=user)
    frozen = {
        **snapshot(),
        "settings": SETTINGS.model_copy(update={"guided_weeks": 0}).model_dump(mode="json"),
    }
    await commands.set_snapshot(game_id, frozen, keep_students=list(students.values()))
    return game_id, students


def started(game_id: str) -> tuple:
    [row] = query(
        TEST_DATABASE_URL,
        "SELECT lifecycle, started_by, started_at FROM games WHERE id = %s",
        (game_id,),
    )
    return row


def audit_rows(game_id: str) -> list[tuple]:
    return query(
        TEST_DATABASE_URL,
        "SELECT actor_user_id, action, change, occurred_at FROM audit_events "
        "WHERE target_ids->>'game_id' = %s ORDER BY id",
        (game_id,),
    )


async def refusal(game_id: str, actor=None) -> commands.CommandError:
    with pytest.raises(commands.CommandError) as refused:
        await commands.start(game_id, actor=actor)
    assert (refused.value.code, refused.value.status) == ("game_already_started", 409)
    return refused.value


async def test_a_lecturers_start_is_stored_audited_and_named_to_whoever_comes_second(games_db):
    game_id, students = await ready_game()
    with listening(games_db) as events:
        assert await commands.start(game_id, actor=LECTURER) == 1
        received = events.drain()
    lifecycle, by, at = started(game_id)
    assert (lifecycle, by) == ("running", LECTURER) and at is not None
    # Every Student of the game reads it started (AD-8).
    assert {e["topic"] for e in received} == COMMAND_TOPICS["games.start"]
    assert {e["id"] for e in received if e["topic"] == "user"} == {
        str(u) for u in students.values()
    }
    [(actor, action, change, occurred)] = audit_rows(game_id)
    assert (actor, action, change, occurred) == (
        LECTURER,
        "game.started",
        {"started_at": at.isoformat()},
        at,
    )
    # A Student's press after it: who started it first, by id, and when.
    late = await refusal(game_id, actor=students["retailer"])
    assert late.fields == {
        "acted_by": {"kind": "staff", "user_id": str(LECTURER)},
        "acted_at": at.isoformat(),
    }
    assert len(audit_rows(game_id)) == 1  # the refused start records nothing


async def test_a_student_who_started_first_is_named_as_a_student(games_db):
    game_id, students = await ready_game()
    await commands.start(game_id, actor=students["factory"])
    _, by, at = started(game_id)
    assert by == students["factory"]
    late = await refusal(game_id, actor=LECTURER)
    assert late.fields["acted_by"] == {"kind": "student", "user_id": str(students["factory"])}
    assert late.fields["acted_at"] == at.isoformat()


async def test_a_start_by_no_person_stores_no_actor_and_no_audit_row(games_db):
    game_id, _ = await ready_game()
    await commands.start(game_id)
    _, by, at = started(game_id)
    assert by is None and at is not None
    assert audit_rows(game_id) == []
    late = await refusal(game_id, actor=LECTURER)
    assert late.fields["acted_by"] == {"kind": "system", "user_id": None}
    with pytest.raises(ValueError):
        await commands.start(game_id, actor="not-a-user")


async def test_a_game_started_before_the_start_was_recorded_names_no_one(games_db):
    game_id, _ = await ready_game()
    await commands.start(game_id)
    # As a Game started before revision 0060 reads: no starter, no time.
    tamper(games_db, "UPDATE games SET started_at = NULL WHERE id = %s", (game_id,))
    late = await refusal(game_id, actor=LECTURER)
    assert late.fields == {"acted_by": {"kind": "system", "user_id": None}, "acted_at": None}


async def test_a_student_taken_over_since_is_still_named_as_a_student(games_db):
    game_id, students = await ready_game()
    await commands.start(game_id, actor=students["retailer"])
    await commands.takeover(game_id, "retailer", actor="staff", actor_user_id=LECTURER)
    late = await refusal(game_id, actor=LECTURER)
    assert late.fields["acted_by"] == {"kind": "student", "user_id": str(students["retailer"])}
