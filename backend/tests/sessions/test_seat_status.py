"""Story 6.14: who has ordered this Week and whom the game waits for (FR-24, FR-25, FR-34,
AD-3, AD-15, AD-20). `games.commands` stores `seat_turns.wait_started_at` when the first Student
orders (or views a Guided Week) on the turns that have not ordered; `table_status` reads it, with
`ordered` and the mark, for the play envelope and Hjem."""

from datetime import datetime

import psycopg
import pytest

from app.engine import GameSettings
from app.modules.games import commands
from app.modules.games import service as games_service
from app.modules.games.schemas import DecidedBy, Fallback, OccupancyReason, OccupantKind
from tests.classes.test_invitation_counts import execute
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import query
from tests.sessions.test_guided_weeks import view
from tests.sessions.test_orders import free_week, order
from tests.sessions.test_play import play, running
from tests.sessions.test_student_home import _empty, clock, home, klass

__all__ = ["_empty", "clock", "klass"]

CLASSIC = GameSettings()


def turns(game_id: str, week: int) -> dict[str, tuple]:
    """(ordered_at, viewed_at, wait_started_at) of each Role's turn in `week`."""
    rows = query(
        TEST_DATABASE_URL,
        "SELECT s.role, t.ordered_at, t.viewed_at, t.wait_started_at FROM seat_turns t "
        "JOIN seats s ON s.id = t.seat_id WHERE t.game_id = %s AND t.week = %s",
        (game_id, week),
    )
    return {role: rest for role, *rest in rows}


def seats(body: dict) -> dict[str, dict]:
    return {seat["role"]: seat for seat in body["table_status"]["seats"]}


async def test_the_first_students_order_starts_the_wait_for_the_seats_that_have_not_ordered(klass):
    game_id, by_role = await free_week(klass, students=3)
    week = CLASSIC.guided_weeks + 1
    first, second, third = by_role
    ai = ({"factory", "distributor", "wholesaler", "retailer"} - set(by_role)).pop()
    # Nobody has ordered: the Students wait with no duration; the Rule-based player has ordered.
    before = seats((await play(by_role[first], game_id)).json())
    for role in by_role:
        assert (before[role]["ordered"], before[role]["wait_started_at"]) == (False, None)
    assert before[ai] | {"wait_started_at": None} == {
        "role": ai,
        "holder": "ai",
        "name": None,
        "mine": False,
        "ordered": True,
        "wait_started_at": None,
        "mark": None,
    }
    assert all(t[2] is None for t in turns(game_id, week).values())

    assert (await order(by_role[first], game_id, week, {"order": 9})).status_code == 204
    stored = turns(game_id, week)
    started = stored[first][0]  # the first Order's transaction time
    assert stored[first][2] is None and stored[ai][2] is None  # ordered: never waited for
    assert stored[second][2] == started and stored[third][2] == started

    # The second Order changes no wait start; only the third Student is still waited for.
    assert (await order(by_role[second], game_id, week, {"order": 5})).status_code == 204
    assert turns(game_id, week)[third][2] == started
    body = (await play(by_role[third], game_id)).json()
    shown = seats(body)
    assert [shown[r]["ordered"] for r in (first, second, third)] == [True, True, False]
    assert shown[first]["wait_started_at"] is None
    assert datetime.fromisoformat(shown[third]["wait_started_at"]) == started
    assert shown[third]["mine"] is True
    # Hjem shows the same Seats, with the server's clock to count the wait from.
    game = (await home(by_role[first]))["game"]
    assert game["seats"] == list(seats(await _as(by_role[first], game_id)).values())
    assert datetime.fromisoformat(game["server_now"]) >= started
    # The stored start cannot be moved.
    with pytest.raises(psycopg.errors.RestrictViolation, match="keeps its opening values"):
        execute(
            "UPDATE seat_turns SET wait_started_at = now() WHERE game_id = %s AND week = %s",
            game_id,
            week,
        )


async def _as(who: str, game_id: str) -> dict:
    return (await play(who, game_id)).json()


async def test_in_a_guided_week_the_first_view_starts_the_wait_for_the_absent_student(klass):
    _, game_id, by_role = await running(klass, students=3)
    first, second, absent = by_role
    shown = seats((await play(by_role[first], game_id)).json())
    # The Guided Orders were placed when the Week opened; a Student who has not viewed waits.
    assert [shown[r]["ordered"] for r in by_role] == [False, False, False]
    assert all(seat["ordered"] for role, seat in shown.items() if role not in by_role)
    assert (await view(by_role[first], game_id, 1)).status_code == 204
    stored = turns(game_id, 1)
    started = stored[first][1]  # the first view's transaction time
    assert stored[first][2] is None
    assert stored[second][2] == started and stored[absent][2] == started
    assert (await view(by_role[second], game_id, 1)).status_code == 204
    shown = seats((await play(by_role[second], game_id)).json())
    # Opening the Week counts as ordering; the absent Student is why the Week has not advanced.
    assert [shown[r]["ordered"] for r in by_role] == [True, True, False]
    assert datetime.fromisoformat(shown[absent]["wait_started_at"]) == started
    assert turns(game_id, 1)[absent][2] == started


async def test_a_game_that_is_not_running_tells_no_order_state(klass):
    _, game_id, by_role = await running(klass, students=1)
    [who] = by_role.values()
    execute("UPDATE games SET lifecycle = 'finished' WHERE id = %s", game_id)
    game = (await home(who))["game"]
    assert {(s["ordered"], s["wait_started_at"], s["mark"]) for s in game["seats"]} == {
        (None, None, None)
    }


async def test_a_seat_the_play_guard_switched_is_marked(klass):
    _, game_id, by_role = await running(klass, students=3)
    [ai] = {"factory", "distributor", "wholesaler", "retailer"} - set(by_role)
    await commands.switch_to_rule_based(game_id, ai, OccupancyReason.GUARD_SWITCH)
    shown = seats((await play(next(iter(by_role.values())), game_id)).json())
    assert (shown[ai]["holder"], shown[ai]["mark"]) == ("ai", "guard_switch")
    assert {shown[r]["mark"] for r in by_role} == {None}


def test_the_one_mapping_marks_a_guard_switch_of_a_rule_based_player():
    """Every other reason and fallback: `tests/games/test_marks.py` (Story 7.7)."""
    mark = games_service.seat_mark
    assert mark(None, None, OccupantKind.RULE_BASED, OccupancyReason.GUARD_SWITCH) == "guard_switch"
    assert mark(DecidedBy.RULE_BASED, Fallback.NONE, "rule_based", "guard_switch") == "guard_switch"
    for kind, reason in [
        (OccupantKind.RULE_BASED, OccupancyReason.INITIAL),
        (OccupantKind.LLM, OccupancyReason.GUARD_SWITCH),
        (OccupantKind.LLM, OccupancyReason.INITIAL),
        (OccupantKind.STUDENT, OccupancyReason.INITIAL),
        (None, OccupancyReason.MOVED),
    ]:
        assert mark(None, None, kind, reason) is None


async def test_next_change_at_is_the_nearest_ai_deadline_still_to_come(klass):
    game_id, by_role = await free_week(klass, students=3)
    week = CLASSIC.guided_weeks + 1
    first, second, third = by_role
    assert (await play(by_role[first], game_id)).json()["next_change_at"] is None
    # Stand-ins for an LLM player's due time on the three unordered turns: the nearest one ahead,
    # a later one, and one already past.
    for role, shift in [(third, "2 hours"), (first, "1 hour"), (second, "-1 hour")]:
        execute(
            "UPDATE seat_turns t SET ai_deadline_at = now() + %s::interval FROM seats s "
            "WHERE s.id = t.seat_id AND t.game_id = %s AND t.week = %s AND s.role = %s",
            shift,
            game_id,
            week,
            role,
        )
    [(ahead,)] = query(
        TEST_DATABASE_URL,
        "SELECT t.ai_deadline_at FROM seat_turns t JOIN seats s ON s.id = t.seat_id "
        "WHERE t.game_id = %s AND t.week = %s AND s.role = %s",
        (game_id, week, first),
    )
    body = (await play(by_role[second], game_id)).json()
    assert datetime.fromisoformat(body["next_change_at"]) == ahead
    # Once that Seat has ordered, the later one is next; once it has too, nothing is due ahead.
    assert (await order(by_role[first], game_id, week, {"order": 4})).status_code == 204
    later = (await play(by_role[second], game_id)).json()["next_change_at"]
    assert datetime.fromisoformat(later) > ahead
    assert (await order(by_role[third], game_id, week, {"order": 4})).status_code == 204
    assert (await play(by_role[second], game_id)).json()["next_change_at"] is None
