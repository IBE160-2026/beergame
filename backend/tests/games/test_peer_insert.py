"""Story 8.8: a Student puts an AI player in an absent Seat once its insert time has passed
(FR-89, FR-37, FR-3, FR-24, AD-2, AD-8, AD-9, AD-15, AD-20).

`games.commands.takeover(…, actor="peer")` asks `rules.can_take_over`: the actor holds another
Seat of the Game and the Seat's stored `insert_allowed_at` has passed, whether or not the Game is
paused. The sweep's `games.announce_insert_time` marks a passed insert time once and emits the
Game's events. Insert times that must have passed are written directly and every time is read from
the database clock, never the host's (Issue #63); a test never waits."""

import asyncio
import uuid
from datetime import datetime, timedelta

import pytest

from app.modules.games import commands, rules
from app.modules.ops import sweep
from app.platform.events.registry import COMMAND_TOPICS
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import execute, listening, query
from tests.games.test_game_summaries import check
from tests.games.test_staff_pause import audit_actions, db_now, insert_of, refused
from tests.games.test_takeover import NOW, RUNNING, class_game, open_week, turn

SECOND = timedelta(seconds=1)
HOUR = timedelta(hours=1)


# The one eligibility check with the `peer` actor (pure).


def peer_turn(**changes) -> dict:
    return turn(**{"insert_allowed_at": NOW - SECOND, "takeover_due_at": NOW + HOUR, **changes})


@pytest.mark.parametrize(
    ("game", "the_turn", "guided", "seated", "seat", "expected"),
    [
        (RUNNING, peer_turn(), False, True, None, None),
        (RUNNING, peer_turn(insert_allowed_at=NOW), False, True, None, None),  # at `now` exactly
        # A Pause is no condition for the peer (it is for the system).
        ({**RUNNING, "paused_at": NOW}, peer_turn(), False, True, None, None),
        (
            RUNNING,
            peer_turn(insert_allowed_at=NOW + SECOND),
            False,
            True,
            None,
            "insert_not_allowed_yet",
        ),
        (RUNNING, peer_turn(insert_allowed_at=None), False, True, None, "insert_not_allowed_yet"),
        (RUNNING, peer_turn(), False, False, None, "seat_not_yours"),
        (RUNNING, peer_turn(ordered_at=NOW), False, True, None, "order_exists"),
        # In a Guided Week the Order is placed at opening; only the view counts as ordering.
        (RUNNING, peer_turn(ordered_at=NOW), True, True, None, None),
        (RUNNING, peer_turn(ordered_at=NOW, viewed_at=NOW), True, True, None, "order_exists"),
        (RUNNING, peer_turn(occupant_kind="llm"), False, True, None, "seat_not_student_held"),
        # A Takeover done or queued from the next Week: the Seat's latest row is an AI player's.
        (
            RUNNING,
            peer_turn(),
            False,
            True,
            {"occupant_kind": "rule_based", "reason": "takeover_staff"},
            "takeover_exists",
        ),
        ({**RUNNING, "lifecycle": "finished"}, peer_turn(), False, True, None, "game_not_running"),
        (
            {**RUNNING, "purpose": "simulation"},
            peer_turn(),
            False,
            True,
            None,
            "takeover_not_allowed",
        ),
    ],
)
def test_the_peer_actor_waits_for_the_insert_time(game, the_turn, guided, seated, seat, expected):
    assert (
        rules.can_take_over(
            game, the_turn, "peer", NOW, guided=guided, seat=seat, peer_seated=seated
        )
        == expected
    )


def test_system_and_staff_are_unchanged_by_the_insert_time():
    early = peer_turn(insert_allowed_at=NOW + HOUR, takeover_due_at=NOW - SECOND)
    assert rules.can_take_over(RUNNING, early, "system", NOW, guided=False) is None
    assert rules.can_take_over(RUNNING, early, "staff", NOW, guided=False) is None


# The command.


def seat_id(game_id: str, role: str) -> str:
    [(found,)] = query(
        TEST_DATABASE_URL,
        "SELECT id FROM seats WHERE game_id = %s AND role = %s",
        (game_id, role),
    )
    return str(found)


def allow_insert(game_id: str, role: str, at: datetime) -> None:
    """The Seat's insert time set directly: a test never waits on real time."""
    execute(
        TEST_DATABASE_URL,
        "UPDATE seat_turns SET insert_allowed_at = %s WHERE game_id = %s AND seat_id = %s "
        "AND week = (SELECT max(week) FROM game_weeks WHERE game_id = %s AND NOT finished)",
        (at, game_id, seat_id(game_id, role), game_id),
    )


def peer_rows(game_id: str) -> list[tuple]:
    """(role, from_week, actor_user_id) of the Game's peer Takeover rows."""
    return query(
        TEST_DATABASE_URL,
        "SELECT s.role, o.from_week, o.actor_user_id FROM seat_occupancy o "
        "JOIN seats s ON s.id = o.seat_id WHERE s.game_id = %s AND o.reason = 'takeover_peer' "
        "ORDER BY o.id",
        (game_id,),
    )


def ordered(game_id: str, role: str) -> bool:
    [(at,)] = query(
        TEST_DATABASE_URL,
        "SELECT t.ordered_at FROM seat_turns t JOIN seats s ON s.id = t.seat_id "
        "WHERE t.game_id = %s AND s.role = %s AND t.week = 1",
        (game_id, role),
    )
    return at is not None


def notices(game_id: str) -> int:
    [(count,)] = query(
        TEST_DATABASE_URL,
        "SELECT count(*) FROM notices WHERE kind = 'takeover_notice' AND ref IN "
        "(SELECT o.id FROM seat_occupancy o JOIN seats s ON s.id = o.seat_id "
        "WHERE s.game_id = %s)",
        (game_id,),
    )
    return count


async def test_a_student_puts_an_ai_player_in_once_the_insert_time_has_passed(games_db, mail_db):
    game_id, students = await class_game(("retailer", "wholesaler", "distributor", "factory"))
    sara, noah, ida, jonas = (
        students[role] for role in ("retailer", "wholesaler", "distributor", "factory")
    )
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=sara)
    await commands.pause(game_id, actor=sara)
    assert insert_of(game_id, "factory") is not None  # the Seat's own limit, ahead

    # Before the insert time, from a Seat that is not another one, or on a Seat that has ordered.
    early = await refused(commands.takeover(game_id, "factory", actor="peer", actor_user_id=noah))
    assert (early.code, early.status) == ("insert_not_allowed_yet", 409)
    allow_insert(game_id, "factory", db_now() - SECOND)
    own = await refused(commands.takeover(game_id, "factory", actor="peer", actor_user_id=jonas))
    assert own.code == "seat_not_yours"
    outsider = uuid.uuid7()
    stranger = await refused(
        commands.takeover(game_id, "factory", actor="peer", actor_user_id=outsider)
    )
    assert stranger.code == "seat_not_yours"
    done = await refused(commands.takeover(game_id, "retailer", actor="peer", actor_user_id=noah))
    assert done.code == "order_exists"
    assert peer_rows(game_id) == []

    # Two Students press at the same moment: one row, and the other is told who came first.
    with listening(games_db) as events:
        outcomes = await asyncio.gather(
            commands.takeover(game_id, "factory", actor="peer", actor_user_id=noah),
            commands.takeover(game_id, "factory", actor="peer", actor_user_id=ida),
            return_exceptions=True,
        )
        received = events.drain()
    [winner] = [i for i, o in enumerate(outcomes) if isinstance(o, str)]
    [loser] = [o for o in outcomes if isinstance(o, commands.CommandError)]
    first = (noah, ida)[winner]
    assert peer_rows(game_id) == [("factory", 1, first)]
    assert (loser.code, loser.status) == ("takeover_exists", 409)
    assert loser.fields["acted_by"] == {"kind": "student", "user_id": str(first)}
    assert loser.fields["acted_at"] is not None
    assert {e["topic"] for e in received} >= COMMAND_TOPICS["games.takeover"]
    # Taken from this Week: the AI player has ordered for Jonas, in the same transaction.
    assert ordered(game_id, "factory")
    # Each Student of the game is told, the one whose Seat it was too (Story 8.2's notice).
    assert notices(game_id) == 4
    [(actor, action, change)] = [
        row for row in audit_actions(game_id) if row[1] == "seat.taken_over"
    ]
    assert (actor, action, change["reason"], change["from_week"]) == (
        first,
        "seat.taken_over",
        "takeover_peer",
        1,
    )
    await check(game_id)
    # The Pause goes on: an AI player's Order never ends it (only a Student's does).
    [(paused_at,)] = query(
        TEST_DATABASE_URL, "SELECT paused_at FROM games WHERE id = %s", (game_id,)
    )
    assert paused_at is not None
    # The sweep marks a passed insert time of a Seat taken over quietly: no version, no events.
    version = version_of(game_id)
    assert not await commands.announce_insert_time(
        game_id, seat_id(game_id, "factory"), now=db_now()
    )
    assert announced(game_id, "factory") is not None
    assert version_of(game_id) == version
    # A third press finds it done.
    again = await refused(commands.takeover(game_id, "factory", actor="peer", actor_user_id=sara))
    assert again.code == "takeover_exists"


async def test_the_right_survives_the_order_that_ends_the_pause(games_db, mail_db):
    game_id, students = await class_game(("retailer", "wholesaler", "factory"))
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    await commands.pause(game_id, actor=students["retailer"])
    passed = db_now() - SECOND
    allow_insert(game_id, "factory", passed)
    placed = await commands.place_order(
        game_id, "wholesaler", 1, 4, "student", actor=students["wholesaler"]
    )
    assert placed.pause_ended
    assert insert_of(game_id, "factory") == passed  # kept: the right has arisen
    await commands.takeover(game_id, "factory", actor="peer", actor_user_id=students["retailer"])
    assert peer_rows(game_id) == [("factory", 1, students["retailer"])]
    # Factory was the last to order Week 1: its AI player's Order completes it.
    assert open_week(game_id) == 2


async def test_a_press_and_the_absent_students_order_end_one_way(games_db, mail_db):
    game_id, students = await class_game(("retailer", "wholesaler", "factory"))
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    allow_insert(game_id, "factory", db_now() - SECOND)
    outcomes = await asyncio.gather(
        commands.place_order(game_id, "factory", 1, 4, "student", actor=students["factory"]),
        commands.takeover(game_id, "factory", actor="peer", actor_user_id=students["wholesaler"]),
        return_exceptions=True,
    )
    order, takeover = outcomes
    if isinstance(takeover, str):
        # The press came first: the Student's late Order is refused, one AI Order stands.
        assert isinstance(order, commands.CommandError)
        assert peer_rows(game_id) == [("factory", 1, students["wholesaler"])]
    else:
        # The Order came first: the press is refused and the Seat stays the Student's.
        assert isinstance(takeover, commands.CommandError) and takeover.code == "order_exists"
        assert peer_rows(game_id) == []
    assert ordered(game_id, "factory")
    await check(game_id)


async def test_in_a_guided_week_the_peer_takeover_applies_now_and_the_week_advances(
    games_db, mail_db
):
    game_id, students = await class_game(guided_weeks=2)
    await commands.view_week(game_id, "retailer", 1, actor=students["retailer"])
    allow_insert(game_id, "factory", db_now() - SECOND)
    await commands.takeover(game_id, "factory", actor="peer", actor_user_id=students["retailer"])
    assert peer_rows(game_id) == [("factory", 1, students["retailer"])]
    assert open_week(game_id) == 2


# The sweep.


def announced(game_id: str, role: str) -> datetime | None:
    [(at,)] = query(
        TEST_DATABASE_URL,
        "SELECT t.insert_announced_at FROM seat_turns t JOIN seats s ON s.id = t.seat_id "
        "WHERE t.game_id = %s AND s.role = %s "
        "AND t.week = (SELECT max(week) FROM game_weeks WHERE game_id = %s AND NOT finished)",
        (game_id, role, game_id),
    )
    return at


def version_of(game_id: str) -> int:
    [(version,)] = query(TEST_DATABASE_URL, "SELECT version FROM games WHERE id = %s", (game_id,))
    return version


async def test_the_sweep_announces_a_passed_insert_time_once(games_db, mail_db):
    game_id, students = await class_game(("retailer", "wholesaler", "factory"))
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    await commands.pause(game_id, actor=students["retailer"])
    insert = insert_of(game_id, "factory")
    assert insert is not None
    version = version_of(game_id)

    assert (await sweep.run(insert - SECOND))["games.announce_insert_time"] == 0
    with listening(games_db) as events:
        done = await sweep.run(insert)
        received = events.drain()
    # Both Seats that have not ordered share the clock, so both insert times have passed.
    assert done["games.announce_insert_time"] == 2
    assert {e["topic"] for e in received} >= COMMAND_TOPICS["games.announce_insert_time"]
    assert {e["id"] for e in received if e["topic"] == "user"} == {
        str(u) for u in students.values()
    }
    assert announced(game_id, "factory") == insert
    assert version_of(game_id) == version + 2
    assert peer_rows(game_id) == []  # it never takes the Seat
    assert (await check(game_id))["status"] == "paused"
    # Idempotent.
    assert (await sweep.run(insert + HOUR))["games.announce_insert_time"] == 0
    assert not await commands.announce_insert_time(
        game_id, seat_id(game_id, "factory"), now=insert + HOUR
    )
    # A Lecturer's new insert time clears the mark; a Seat that has ordered is marked quietly.
    later = (db_now() + HOUR).replace(microsecond=0)
    await commands.set_agreed_time(game_id, later, actor=uuid.uuid7())
    assert announced(game_id, "factory") is None
    await commands.place_order(game_id, "wholesaler", 1, 4, "student", actor=students["wholesaler"])
    allow_insert(game_id, "wholesaler", later)  # an Order placed: the Seat no longer waits
    version = version_of(game_id)
    assert not await commands.announce_insert_time(
        game_id, seat_id(game_id, "wholesaler"), now=later
    )
    assert announced(game_id, "wholesaler") == later
    assert version_of(game_id) == version
    assert await commands.announce_insert_time(game_id, seat_id(game_id, "factory"), now=later)
    assert version_of(game_id) == version + 1


async def test_the_finder_skips_a_game_that_no_longer_runs(games_db, mail_db):
    game_id, students = await class_game()
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    insert = insert_of(game_id, "factory")
    assert insert is not None
    execute(
        TEST_DATABASE_URL, "UPDATE games SET lifecycle = 'playing_out' WHERE id = %s", (game_id,)
    )
    assert (await sweep.run(insert))["games.announce_insert_time"] == 0
