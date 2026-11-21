"""Story 8.5: a Lecturer or Assistant lecturer puts an AI player in one Seat (FR-37, FR-3, FR-24,
AD-2, AD-5, AD-14, AD-15).

`games.commands.takeover(…, actor="staff", actor_user_id=…)` checks `games.rules.can_take_over`
under the Game row lock and appends one `takeover_staff` row naming the staff member: from the
open Week, with the AI player's Order, when the Seat has not ordered; from the next Week when it
has. It writes one audit row, and a lost race answers `takeover_exists` with who acted first, by
id only. No clock is read from the host (Issue #63)."""

import asyncio
import json
import uuid

import pytest

from app.modules.games import commands, rules
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import execute, query
from tests.games.test_game_summaries import check
from tests.games.test_takeover import NOW, RUNNING, _user, class_game, open_week, turn


def staff_rows(game_id: str) -> list[tuple]:
    """(role, from_week, occupant_kind, actor_user_id) of the Game's `takeover_staff` rows."""
    return query(
        TEST_DATABASE_URL,
        "SELECT s.role, o.from_week, o.occupant_kind, o.actor_user_id FROM seat_occupancy o "
        "JOIN seats s ON s.id = o.seat_id WHERE s.game_id = %s "
        "AND o.reason = 'takeover_staff' ORDER BY o.id",
        (game_id,),
    )


def orders_of(game_id: str, role: str) -> dict[int, tuple]:
    """Per Week the Seat's stored Order and who decided it."""
    found = query(
        TEST_DATABASE_URL,
        'SELECT w.week, w."order", w.decided_by FROM seat_weeks w '
        "JOIN seats s ON s.id = w.seat_id WHERE w.game_id = %s AND s.role = %s",
        (game_id, role),
    )
    return {week: (order, decided_by) for week, order, decided_by in found}


def audit_rows(game_id: str) -> list[tuple]:
    return query(
        TEST_DATABASE_URL,
        "SELECT actor_user_id, action, target_ids, change FROM audit_events "
        "WHERE target_ids->>'game_id' = %s",
        (game_id,),
    )


def notices(game_id: str) -> list[tuple]:
    return query(
        TEST_DATABASE_URL,
        "SELECT n.user_id, n.dedupe_key FROM notices n JOIN seat_occupancy o ON o.id = n.ref "
        "JOIN seats s ON s.id = o.seat_id WHERE s.game_id = %s AND n.kind = 'takeover_notice'",
        (game_id,),
    )


# The one eligibility check (pure).


@pytest.mark.parametrize(
    ("game", "the_turn", "seat", "refused"),
    [
        (RUNNING, turn(takeover_due_at=None), None, None),  # no due time needed
        (RUNNING, turn(ordered_at=NOW), None, None),  # ordered: the next Week
        (RUNNING, turn(), {"occupant_kind": "llm", "reason": "takeover_staff"}, "takeover_exists"),
        (
            RUNNING,
            turn(ordered_at=NOW),
            {"occupant_kind": "rule_based", "reason": "takeover_inactivity"},
            "takeover_exists",
        ),
        (
            RUNNING,
            turn(),
            {"occupant_kind": "rule_based", "reason": "guard_switch"},
            "seat_not_student_held",
        ),
        (RUNNING, turn(occupant_kind="rule_based"), None, "seat_not_student_held"),
        ({**RUNNING, "lifecycle": "finished"}, turn(), None, "game_not_running"),
        ({**RUNNING, "lifecycle": "not_started"}, None, None, "game_not_running"),
        ({**RUNNING, "purpose": "simulation"}, turn(), None, "takeover_not_allowed"),
    ],
)
def test_the_staff_may_put_an_ai_player_in_any_student_seat(game, the_turn, seat, refused):
    assert rules.can_take_over(game, the_turn, "staff", NOW, guided=False, seat=seat) == refused


def test_a_system_takeover_meets_a_staff_one_as_a_lost_race():
    seat = {"occupant_kind": "llm", "reason": "takeover_staff"}
    assert rules.can_take_over(RUNNING, turn(), "system", NOW, guided=False, seat=seat) == (
        "takeover_exists"
    )


# The command.


async def test_a_seat_that_has_not_ordered_is_taken_from_this_week(games_db, mail_db):
    game_id, students = await class_game(("retailer", "wholesaler", "factory"))
    staff = _user()
    occupancy = await commands.takeover(game_id, "factory", actor="staff", actor_user_id=staff)
    assert staff_rows(game_id) == [("factory", 1, "rule_based", staff)]
    # The AI player orders this Week in the same transaction; no other Student has ordered.
    assert orders_of(game_id, "factory")[1][1] == "rule_based"
    assert open_week(game_id) == 1
    [(actor, action, target, change)] = audit_rows(game_id)
    assert (actor, action) == (staff, "seat.taken_over")
    assert target["occupancy_id"] == occupancy
    assert target["user_id"] == str(students["factory"])  # whose Seat it was
    assert change == {"reason": "takeover_staff", "from_week": 1, "occupant_kind": "rule_based"}
    # Every Student of the game is told, the one whose Seat it was too (Story 8.2's notices).
    told = notices(game_id)
    assert {user for user, _ in told} == set(students.values())
    assert {key for _, key in told} == {
        f"takeover_notice:{occupancy}:{user}" for user in students.values()
    }
    row = await check(game_id)
    [factory] = [o for o in row["occupants"] if o["role"] == "factory"]
    assert (factory["reason"], factory["actor_user_id"]) == ("takeover_staff", str(staff))


async def test_a_seat_that_has_ordered_is_taken_from_the_next_week(games_db, mail_db):
    game_id, students = await class_game(("retailer", "factory"))
    await commands.place_order(game_id, "retailer", 1, 7, "student", actor=students["retailer"])
    staff = _user()
    await commands.takeover(game_id, "retailer", actor="staff", actor_user_id=staff)
    assert staff_rows(game_id) == [("retailer", 2, "rule_based", staff)]
    # The Student's own Order of this Week stands; the game still waits for the factory.
    assert orders_of(game_id, "retailer") == {1: (7, "student")}
    assert (await check(game_id))["status"] == "waiting"
    assert len(notices(game_id)) == 2
    await commands.place_order(game_id, "factory", 1, 4, "student", actor=students["factory"])
    assert open_week(game_id) == 2
    assert orders_of(game_id, "retailer")[2][1] == "rule_based"
    # A second press finds the Takeover there and names who made it.
    with pytest.raises(commands.CommandError) as refused:
        await commands.takeover(game_id, "retailer", actor="staff", actor_user_id=_user())
    assert (refused.value.code, refused.value.status) == ("takeover_exists", 409)
    assert refused.value.fields["acted_by"] == {"kind": "staff", "user_id": str(staff)}


async def test_two_presses_at_once_append_one_row_and_name_the_first(games_db, mail_db):
    game_id, _ = await class_game(("retailer", "factory"))
    first, second = _user(), _user()
    results = await asyncio.gather(
        commands.takeover(game_id, "factory", actor="staff", actor_user_id=first),
        commands.takeover(game_id, "factory", actor="staff", actor_user_id=second),
        return_exceptions=True,
    )
    [refused] = [r for r in results if isinstance(r, commands.CommandError)]
    [(_, _, _, winner)] = staff_rows(game_id)
    assert refused.code == "takeover_exists"
    assert refused.fields["acted_by"] == {"kind": "staff", "user_id": str(winner)}
    assert refused.fields["acted_at"]
    assert json.dumps(refused.fields)  # the envelope carries it as it is
    assert len(audit_rows(game_id)) == 1


async def test_a_seat_no_student_holds_or_a_game_not_started_is_refused(games_db, mail_db):
    game_id, _ = await class_game(("retailer",))
    with pytest.raises(commands.CommandError) as refused:
        await commands.takeover(game_id, "factory", actor="staff", actor_user_id=_user())
    assert (refused.value.code, refused.value.status) == ("seat_not_student_held", 409)
    unstarted = await commands.create("class", class_session_id=uuid.uuid7(), game_number=2)
    with pytest.raises(commands.CommandError) as refused:
        await commands.takeover(unstarted, "factory", actor="staff", actor_user_id=_user())
    assert refused.value.code == "game_not_running"
    assert staff_rows(game_id) == [] and audit_rows(game_id) == []


def _weeks(game_id: str, weeks: int) -> None:
    """The Game's number of Weeks as the command reads it (the engine's checks are not run)."""
    execute(
        TEST_DATABASE_URL,
        "UPDATE games SET settings = jsonb_set(settings, '{weeks}', %s::jsonb) WHERE id = %s",
        (str(weeks), game_id),
    )


async def test_the_seat_that_has_ordered_the_last_week_is_refused(games_db, mail_db):
    game_id, students = await class_game(("retailer", "wholesaler", "factory"))
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    _weeks(game_id, 1)  # the open Week 1 is the Game's last
    with pytest.raises(commands.CommandError) as refused:
        await commands.takeover(game_id, "retailer", actor="staff", actor_user_id=_user())
    assert (refused.value.code, refused.value.status) == ("order_exists", 409)
    assert staff_rows(game_id) == [] and notices(game_id) == []
    _weeks(game_id, 8)
    await commands.takeover(game_id, "retailer", actor="staff", actor_user_id=_user())
    assert [row[:2] for row in staff_rows(game_id)] == [("retailer", 2)]


async def test_an_llm_player_put_in_after_the_order_waits_for_the_next_week(
    games_db, mail_db, ai_db
):
    from tests.games.test_set_snapshot import llm_snapshot

    game_id, students = await class_game(stored=await llm_snapshot())
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    await commands.takeover(game_id, "retailer", actor="staff", actor_user_id=_user())
    assert [row[:3] for row in staff_rows(game_id)] == [("retailer", 2, "llm")]
    [(deadline,)] = query(
        TEST_DATABASE_URL,
        "SELECT t.ai_deadline_at FROM seat_turns t JOIN seats s ON s.id = t.seat_id "
        "WHERE t.game_id = %s AND t.week = 1 AND s.role = 'retailer'",
        (game_id,),
    )
    assert deadline is None  # the Student's own Order of Week 1 stands; no AI turn there


async def test_in_a_guided_week_opening_it_is_ordering_it(games_db, mail_db):
    game_id, students = await class_game(("retailer", "wholesaler", "factory"), guided_weeks=1)
    await commands.view_week(game_id, "wholesaler", 1, actor=students["wholesaler"])
    await commands.view_week(game_id, "retailer", 1, actor=students["retailer"])
    await commands.takeover(game_id, "retailer", actor="staff", actor_user_id=_user())
    # The Student opened Guided Week 1: the AI player takes Week 2; Week 1 waits for the factory.
    assert [row[:2] for row in staff_rows(game_id)] == [("retailer", 2)]
    assert open_week(game_id) == 1
    await commands.takeover(game_id, "factory", actor="staff", actor_user_id=_user())
    # The factory had not opened it: taken this Week, so Week 1 completes and Week 2 opens
    # (the wholesaler's Student holds Week 2 open).
    assert [row[:2] for row in staff_rows(game_id)] == [("retailer", 2), ("factory", 1)]
    assert open_week(game_id) == 2


async def test_a_reclaim_before_the_next_week_keeps_the_seat_with_its_student(games_db, mail_db):
    """Story 8.4 meets a next-Week Takeover: the Student asks for the Seat back before the AI
    player's Week opens; the Reclaim row comes later, so the Student keeps the Seat."""
    game_id, students = await class_game(("retailer", "factory"))
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    await commands.takeover(game_id, "retailer", actor="staff", actor_user_id=_user())
    assert await commands.request_reclaim(game_id, "retailer", actor=students["retailer"])
    await commands.place_order(game_id, "factory", 1, 4, "student", actor=students["factory"])
    assert open_week(game_id) == 2
    [(kind, reason)] = query(
        TEST_DATABASE_URL,
        "SELECT o.occupant_kind, o.reason FROM seat_occupancy o JOIN seats s ON s.id = o.seat_id "
        "WHERE s.game_id = %s AND s.role = 'retailer' ORDER BY o.id DESC LIMIT 1",
        (game_id,),
    )
    assert (kind, reason) == ("student", "reclaim")
    assert 2 not in orders_of(game_id, "retailer")  # the AI player never ordered for it
