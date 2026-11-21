"""Story 8.4: take the Seat back with «Ta tilbake setet» (FR-37, FR-79, AD-2, AD-5, AD-15).

`games.commands.request_reclaim` queues the Student's request under the Game row lock and changes
no occupancy; the command that opens the next Week (`_step`) appends the `reclaim` row with the
Student as actor and deletes the request. Takeovers run at their stored due time (injected clock,
Issue #63)."""

import uuid

import pytest

from app.modules.games import commands, insight
from app.modules.games import service as games_service
from app.platform.db import get_sessionmaker
from app.platform.events.registry import COMMAND_TOPICS
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import listening, query
from tests.games.test_takeover import SECOND, _user, class_game, due_of, open_week


async def taken_over(roles=("retailer", "factory"), **kwargs) -> tuple[str, dict]:
    """A Class game whose factory Seat an AI player took over in Week 1; Week 2 is open (the
    Rule-based player ordered at once, so Week 1 completed)."""
    game_id, students = await class_game(roles, **kwargs)
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    await commands.takeover(
        game_id, "factory", actor="system", now=due_of(game_id, "factory") + SECOND
    )
    return game_id, students


def occupancy(game_id: str, role: str = "factory") -> list[tuple]:
    """(from_week, occupant_kind, reason, user_id, actor_user_id) of the Seat, as appended."""
    return query(
        TEST_DATABASE_URL,
        "SELECT o.from_week, o.occupant_kind, o.reason, o.user_id, o.actor_user_id "
        "FROM seat_occupancy o JOIN seats s ON s.id = o.seat_id "
        "WHERE s.game_id = %s AND s.role = %s ORDER BY o.id",
        (game_id, role),
    )


def queued(game_id: str) -> list[tuple]:
    return query(
        TEST_DATABASE_URL,
        "SELECT s.role, r.user_id FROM seat_reclaims r JOIN seats s ON s.id = r.seat_id "
        "WHERE r.game_id = %s",
        (game_id,),
    )


def version(game_id: str) -> int:
    [(found,)] = query(TEST_DATABASE_URL, "SELECT version FROM games WHERE id = %s", (game_id,))
    return found


async def test_the_request_is_queued_and_changes_no_occupancy(games_db, mail_db):
    game_id, students = await taken_over()
    before, at = occupancy(game_id), version(game_id)
    with listening(games_db) as events:
        assert await commands.request_reclaim(game_id, "factory", actor=students["factory"])
        received = events.drain()
    assert occupancy(game_id) == before
    assert queued(game_id) == [("factory", students["factory"])]
    assert version(game_id) == at + 1
    assert {e["topic"] for e in received} == COMMAND_TOPICS["games.request_reclaim"]
    assert {e["id"] for e in received if e["topic"] == "user"} == {str(students["factory"])}
    # A second press, or a repeat of the request, changes nothing.
    with listening(games_db) as events:
        assert not await commands.request_reclaim(game_id, "factory", actor=students["factory"])
        assert events.drain() == []
    assert version(game_id) == at + 1 and len(queued(game_id)) == 1


async def test_the_seat_is_the_students_again_when_the_next_week_opens(games_db, mail_db):
    game_id, students = await taken_over()
    student = students["factory"]
    await commands.request_reclaim(game_id, "factory", actor=student)
    assert open_week(game_id) == 2
    with listening(games_db) as events:
        await commands.place_order(game_id, "retailer", 2, 4, "student", actor=students["retailer"])
        received = events.drain()
    assert open_week(game_id) == 3
    assert occupancy(game_id)[-1] == (3, "student", "reclaim", student, student)
    assert queued(game_id) == []
    # Its new turn starts with no clock running.
    [times] = query(
        TEST_DATABASE_URL,
        "SELECT t.wait_started_at, t.takeover_due_at, t.insert_allowed_at, t.ordered_at "
        "FROM seat_turns t JOIN seats s ON s.id = t.seat_id "
        "WHERE t.game_id = %s AND s.role = 'factory' AND t.week = 3",
        (game_id,),
    )
    assert times == (None, None, None, None)
    assert "game" in {e["topic"] for e in received}
    assert str(student) in {e["id"] for e in received if e["topic"] == "user"}
    # The Student orders again; a repeat after the Reclaim changed nothing.
    assert not await commands.request_reclaim(game_id, "factory", actor=student)
    await commands.place_order(game_id, "factory", 3, 6, "student", actor=student)


async def test_a_guided_view_that_opens_the_week_hands_the_seat_back(games_db, mail_db):
    game_id, students = await class_game(guided_weeks=2)
    assert await commands.view_week(game_id, "retailer", 1, actor=students["retailer"])
    await commands.takeover(
        game_id, "factory", actor="system", now=due_of(game_id, "factory") + SECOND
    )
    assert open_week(game_id) == 2
    student = students["factory"]
    await commands.request_reclaim(game_id, "factory", actor=student)
    with listening(games_db) as events:
        assert await commands.view_week(game_id, "retailer", 2, actor=students["retailer"])
        received = events.drain()
    assert open_week(game_id) == 3
    assert occupancy(game_id)[-1] == (3, "student", "reclaim", student, student)
    assert str(student) in {e["id"] for e in received if e["topic"] == "user"}


async def test_the_last_week_finishes_the_game_with_no_reclaim_row(games_db):
    """A request queued in the last Week has no next Week to take effect in. A Class game's finish
    records `progress` for a real Class session, so the step is shown on a one-Week simulation
    Game whose factory Seat has a Takeover row written as the command writes it."""
    from app.engine import GameSettings
    from tests.games.helpers import execute, seat_student, student_of

    base = GameSettings(weeks=1, guided_weeks=0)
    one_week = GameSettings.model_validate(
        base.model_copy(
            update={"demand": base.demand.model_copy(update={"change_week": 1})}
        ).model_dump()
    )
    game_id = await commands.create("simulation", one_week, seed=2)
    seat_student(games_db, game_id, "retailer", "factory")
    await commands.start(game_id)
    execute(
        games_db,
        "INSERT INTO seat_occupancy (id, seat_id, from_week, occupant_kind, reason) "
        "SELECT %s, id, 1, 'rule_based', 'takeover_inactivity' FROM seats "
        "WHERE game_id = %s AND role = 'factory'",
        (uuid.uuid7(), game_id),
    )
    factory = student_of(game_id, "factory")
    assert await commands.request_reclaim(game_id, "factory", actor=factory)
    await commands.place_order(game_id, "factory", 1, 4, "rule_based")
    rows = len(occupancy(game_id))
    await commands.place_order(game_id, "retailer", 1, 4, "student")
    [(lifecycle,)] = query(games_db, "SELECT lifecycle FROM games WHERE id = %s", (game_id,))
    assert lifecycle == "finished"
    assert len(occupancy(game_id)) == rows  # no Week opened, so no Reclaim row
    assert queued(game_id) == []  # and the request went with the Game
    with pytest.raises(commands.CommandError) as refused:
        await commands.request_reclaim(game_id, "factory", actor=factory)
    assert (refused.value.code, refused.value.status) == ("game_finished", 409)


async def test_only_the_student_whose_seat_was_taken_over_may_ask(games_db, mail_db):
    game_id, students = await taken_over()
    for actor in (students["retailer"], _user()):  # another Student; a User who never held it
        with pytest.raises(commands.CommandError) as refused:
            await commands.request_reclaim(game_id, "factory", actor=actor)
        assert (refused.value.code, refused.value.status) == ("seat_not_yours", 409)
    # Their own Seat, held and never taken over, is not theirs to reclaim either.
    with pytest.raises(commands.CommandError) as refused:
        await commands.request_reclaim(game_id, "retailer", actor=students["retailer"])
    assert refused.value.code == "seat_not_yours"
    assert queued(game_id) == []


async def test_a_game_not_started_refuses(games_db, mail_db):
    game_id = await commands.create("class", class_session_id=uuid.uuid7(), game_number=1)
    student = _user()
    await commands.assign_seat(game_id, "factory", "student", user_id=student)
    with pytest.raises(commands.CommandError) as refused:
        await commands.request_reclaim(game_id, "factory", actor=student)
    assert (refused.value.code, refused.value.status) == ("game_not_running", 409)


async def test_weeks_the_ai_player_ordered_stay_ai_weeks(games_db, mail_db):
    """AD-15: the Decision log rows are untouched and Spillinnsikt reads the AI Week as the AI
    player's, the Week back as the Student's."""
    game_id, students = await taken_over()
    before = query(
        TEST_DATABASE_URL,
        "SELECT w.week, w.occupant_kind, w.reason, w.decided_by FROM seat_weeks w "
        "JOIN seats s ON s.id = w.seat_id WHERE w.game_id = %s AND s.role = 'factory' "
        "ORDER BY w.week",
        (game_id,),
    )
    await commands.request_reclaim(game_id, "factory", actor=students["factory"])
    await commands.place_order(game_id, "retailer", 2, 4, "student", actor=students["retailer"])
    await commands.place_order(game_id, "factory", 3, 6, "student", actor=students["factory"])
    after = query(
        TEST_DATABASE_URL,
        "SELECT w.week, w.occupant_kind, w.reason, w.decided_by FROM seat_weeks w "
        "JOIN seats s ON s.id = w.seat_id WHERE w.game_id = %s AND s.role = 'factory' "
        "AND w.week < 3 ORDER BY w.week",
        (game_id,),
    )
    assert after == before
    assert [row[1] for row in after] == ["rule_based", "rule_based"]
    async with get_sessionmaker()() as session:
        found = await insight.game_insight(session, uuid.UUID(game_id))
    assert found is not None
    [factory] = [r for r in found.roles if r.role == "factory"]
    weeks = {w.week: w for w in factory.weeks}
    assert weeks[1].occupant_kind == "rule_based" and "takeover_inactivity" in weeks[1].marks
    assert weeks[2].occupant_kind == "rule_based"
    assert weeks[3].occupant_kind == "student" and "reclaim" in weeks[3].marks


async def test_a_play_guard_switch_outlasts_the_reclaim(games_db, mail_db, ai_db):
    """FR-79: the Seat's LLM player was switched by the Play guard; back with the Student, then lost
    again, it gets a Rule-based player."""
    from tests.games.test_set_snapshot import llm_snapshot

    game_id, students = await class_game(stored=await llm_snapshot())
    # The two AI Seats order at once (their LLM jobs never run here).
    for role in ("wholesaler", "distributor"):
        await commands.switch_to_rule_based(game_id, role, "cost_limit")
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    await commands.takeover(
        game_id, "factory", actor="system", now=due_of(game_id, "factory") + SECOND
    )
    assert occupancy(game_id)[-1][:3] == (1, "llm", "takeover_inactivity")
    await commands.switch_to_rule_based(game_id, "factory", "guard_switch")
    assert open_week(game_id) == 2
    await commands.request_reclaim(game_id, "factory", actor=students["factory"])
    await commands.place_order(game_id, "retailer", 2, 4, "student", actor=students["retailer"])
    assert occupancy(game_id)[-1][2] == "reclaim"
    await commands.place_order(game_id, "retailer", 3, 4, "student", actor=students["retailer"])
    await commands.takeover(
        game_id, "factory", actor="system", now=due_of(game_id, "factory", 3) + SECOND
    )
    assert occupancy(game_id)[-1][:3] == (3, "rule_based", "takeover_inactivity")


async def test_the_own_seat_shows_the_queued_request_to_its_student_only(games_db, mail_db):
    game_id, students = await taken_over()
    await commands.request_reclaim(game_id, "factory", actor=students["factory"])

    async def names(ids):
        return {user: "Navn" for user in ids}

    async with get_sessionmaker()() as session:
        own = await games_service.table_status(
            session, uuid.UUID(game_id), students["factory"], names
        )
        other = await games_service.table_status(
            session, uuid.UUID(game_id), students["retailer"], names
        )
    assert [s.role for s in own.seats if s.reclaim_queued] == ["factory"]
    assert not any(s.reclaim_queued for s in other.seats)
