"""Story 8.13: the turn reminder's due time and the sweep that queues it (FR-27, FR-24, AD-9,
AD-13, AD-20).

`games.commands` stores `seat_turns.reminder_due_at` with the wait start, from `rules.turn_times`;
the sweep's `games.queue_turn_reminder` queues one `turn_reminder` digest notice per User, Game and
Week while the game waits for the Seat, never while it is paused. Every time is read from the
database, never the host's clock (Issue #63); a test never waits. The mail itself is tested in
`tests/sessions/test_turn_reminder_mail.py`."""

import uuid
from datetime import datetime, timedelta

from app.modules.games import commands
from app.modules.games import service as games_service
from app.modules.messaging import delivery
from app.modules.ops import sweep
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker
from app.platform.events.registry import COMMAND_TOPICS
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import execute, listening, query
from tests.games.test_set_snapshot import SETTINGS
from tests.games.test_takeover import _user, class_game, open_week

SECOND = timedelta(seconds=1)
HOUR = timedelta(hours=1)
ACTION = "games.queue_turn_reminder"


def seat_id(game_id: str, role: str) -> str:
    [(found,)] = query(
        TEST_DATABASE_URL,
        "SELECT id FROM seats WHERE game_id = %s AND role = %s",
        (game_id, role),
    )
    return str(found)


def _turn(game_id: str, role: str, column: str) -> datetime | None:
    [(at,)] = query(
        TEST_DATABASE_URL,
        f"SELECT t.{column} FROM seat_turns t JOIN seats s ON s.id = t.seat_id "  # noqa: S608
        "WHERE t.game_id = %s AND s.role = %s "
        "AND t.week = (SELECT max(week) FROM game_weeks WHERE game_id = %s AND NOT finished)",
        (game_id, role, game_id),
    )
    return at


def turn_id(game_id: str, role: str) -> uuid.UUID:
    [(found,)] = query(
        TEST_DATABASE_URL,
        "SELECT t.id FROM seat_turns t JOIN seats s ON s.id = t.seat_id "
        "WHERE t.game_id = %s AND s.role = %s "
        "AND t.week = (SELECT max(week) FROM game_weeks WHERE game_id = %s AND NOT finished)",
        (game_id, role, game_id),
    )
    return found


def reminder_of(game_id: str, role: str) -> datetime | None:
    return _turn(game_id, role, "reminder_due_at")


def queued(game_id: str, role: str) -> datetime | None:
    return _turn(game_id, role, "reminder_queued_at")


def reminders(game_id: str) -> list[tuple]:
    """(user_id, dedupe_key, ref, not_before) of the Game's `turn_reminder` notices."""
    return query(
        TEST_DATABASE_URL,
        "SELECT n.user_id, n.dedupe_key, n.ref, n.not_before FROM notices n "
        "JOIN seat_turns t ON t.id = n.ref WHERE n.kind = 'turn_reminder' AND t.game_id = %s "
        "ORDER BY n.dedupe_key",
        (game_id,),
    )


def version_of(game_id: str) -> int:
    [(version,)] = query(TEST_DATABASE_URL, "SELECT version FROM games WHERE id = %s", (game_id,))
    return version


async def test_the_sweep_queues_one_reminder_per_waited_for_seat(games_db, mail_db):
    game_id, students = await class_game(("retailer", "wholesaler", "factory"))
    # Nobody has ordered: no wait, so no reminder time (FR-27).
    assert reminder_of(game_id, "factory") is None
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    delay = timedelta(minutes=get_settings().turn_reminder_delay_minutes)
    assert delay == 2 * HOUR  # the placeholder
    due = reminder_of(game_id, "factory")
    assert due == _turn(game_id, "factory", "wait_started_at") + delay
    assert reminder_of(game_id, "wholesaler") == due
    assert reminder_of(game_id, "retailer") is None  # it ordered: never waited for
    # A Rule-based Seat is never reminded.
    assert reminder_of(game_id, "distributor") is None
    version = version_of(game_id)

    await sweep.run(due - SECOND)
    assert reminders(game_id) == []
    with listening(games_db) as events:
        await sweep.run(due)
        received = events.drain()
    assert {e["topic"] for e in received} >= COMMAND_TOPICS[ACTION]
    assert {e["id"] for e in received if e["topic"] == "user"} >= {
        str(students["wholesaler"]),
        str(students["factory"]),
    }
    found = reminders(game_id)
    assert {(user, key) for user, key, _, _ in found} == {
        (students[role], f"turn_reminder:{students[role]}:{game_id}:1")
        for role in ("wholesaler", "factory")
    }
    assert all(not_before == due for *_, not_before in found)
    assert queued(game_id, "factory") == due
    assert version_of(game_id) == version  # nothing a game view shows changed
    assert delivery.KINDS["turn_reminder"].mode == delivery.DIGEST

    # Idempotent: the mark and the dedupe key.
    await sweep.run(due + HOUR)
    assert not await commands.queue_turn_reminder(
        game_id, seat_id(game_id, "factory"), now=due + HOUR
    )
    assert len(reminders(game_id)) == 2


async def test_a_paused_game_is_reminded_only_once_the_pause_ends(games_db, mail_db):
    game_id, students = await class_game(("retailer", "wholesaler", "factory"))
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    await commands.pause(game_id, actor=students["retailer"])
    due = reminder_of(game_id, "factory")
    assert due is not None
    await sweep.run(due + HOUR)
    assert not await commands.queue_turn_reminder(
        game_id, seat_id(game_id, "factory"), now=due + HOUR
    )
    assert queued(game_id, "factory") is None and reminders(game_id) == []

    # Wholesaler's Order ends the Pause; the game still waits for Factory.
    await commands.place_order(game_id, "wholesaler", 1, 4, "student", actor=students["wholesaler"])
    await sweep.run(due + HOUR)
    [(user, *_)] = reminders(game_id)
    assert user == students["factory"]


async def test_a_seat_no_longer_waited_for_is_marked_quietly(games_db, mail_db):
    game_id, students = await class_game(("retailer", "wholesaler", "distributor", "factory"))
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    due = reminder_of(game_id, "factory")
    assert due is not None
    # Wholesaler orders; an AI player takes Distributor's Seat from Spillstyring.
    await commands.place_order(game_id, "wholesaler", 1, 4, "student", actor=students["wholesaler"])
    # A mail built now leaves the Week's game out for Wholesaler only: the Week is still open.
    async with get_sessionmaker()() as session:
        assert (
            await games_service.turn_reminder_of(
                session, turn_id(game_id, "wholesaler"), students["wholesaler"]
            )
            is None
        )
        waiting = await games_service.turn_reminder_of(
            session, turn_id(game_id, "factory"), students["factory"]
        )
    assert waiting is not None and waiting.role == "factory"
    await commands.takeover(game_id, "distributor", actor="staff", actor_user_id=uuid.uuid7())
    for role in ("wholesaler", "distributor"):
        assert not await commands.queue_turn_reminder(game_id, seat_id(game_id, role), now=due)
        assert queued(game_id, role) == due
    assert reminders(game_id) == []
    # Only Factory is still waited for.
    await sweep.run(due)
    assert [user for user, *_ in reminders(game_id)] == [students["factory"]]
    # The Week completes and the next one opens: its turns have no reminder yet.
    await commands.place_order(game_id, "factory", 1, 4, "student", actor=students["factory"])
    assert open_week(game_id) == 2
    assert reminder_of(game_id, "factory") is None


async def test_the_finder_leaves_a_past_week_alone(games_db, mail_db):
    """Turns whose Students ordered before their reminder time are closed when the Week
    completes, so they leave the finder's index; and the finder reads the open Week only."""
    game_id, students = await class_game(("retailer", "wholesaler", "factory"))
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    due = reminder_of(game_id, "factory")
    assert due is not None
    for role in ("wholesaler", "factory"):
        await commands.place_order(game_id, role, 1, 4, "student", actor=students[role])
    assert open_week(game_id) == 2
    [(unqueued,)] = query(
        TEST_DATABASE_URL,
        "SELECT count(*) FROM seat_turns WHERE game_id = %s AND week = 1 "
        "AND reminder_due_at IS NOT NULL AND reminder_queued_at IS NULL",
        (game_id,),
    )
    assert unqueued == 0
    # Even an unclosed past-Week turn is never found.
    execute(
        TEST_DATABASE_URL,
        "UPDATE seat_turns SET reminder_queued_at = NULL WHERE game_id = %s AND week = 1",
        (game_id,),
    )
    found = await games_service.due_turn_reminders(due + HOUR)
    assert all(game != game_id for game, _ in found)
    await sweep.run(due + HOUR)
    assert reminders(game_id) == []


async def test_no_reminder_without_inactivity_rules_or_once_the_game_stops_running(
    games_db, mail_db
):
    """AD-13: a simulation Game never gets one, even with a reminder time written past the
    command; nor does a Game that no longer runs."""
    game_id = await commands.create("simulation", SETTINGS.model_copy(update={"guided_weeks": 0}))
    execute(
        TEST_DATABASE_URL,
        "INSERT INTO seat_occupancy (id, seat_id, from_week, occupant_kind, reason, user_id) "
        "SELECT %s, id, 1, 'student', 'initial', %s FROM seats WHERE game_id = %s "
        "AND role = 'factory'",
        (uuid.uuid7(), _user(), game_id),
    )
    await commands.start(game_id)
    execute(
        TEST_DATABASE_URL,
        "UPDATE seat_turns SET wait_started_at = now() - interval '3 hours', "
        "reminder_due_at = now() - interval '1 hour' WHERE game_id = %s",
        (game_id,),
    )
    due = reminder_of(game_id, "factory")
    assert due is not None
    assert not await commands.queue_turn_reminder(game_id, seat_id(game_id, "factory"), now=due)
    assert reminders(game_id) == []

    stopped, students = await class_game()
    await commands.place_order(stopped, "retailer", 1, 4, "student", actor=students["retailer"])
    due = reminder_of(stopped, "factory")
    assert due is not None
    execute(
        TEST_DATABASE_URL, "UPDATE games SET lifecycle = 'playing_out' WHERE id = %s", (stopped,)
    )
    await sweep.run(due)
    assert queued(stopped, "factory") is None  # the finder skips it
    assert not await commands.queue_turn_reminder(stopped, seat_id(stopped, "factory"), now=due)
    assert reminders(stopped) == []
