"""Story 8.2: an AI player takes over after the Inactivity limit (FR-36, FR-30, FR-24, AD-2, AD-5,
AD-9, AD-13, NFR-4).

The sweep's `games.takeover` due action finds each Student-held Seat whose stored
`takeover_due_at` has passed and calls `games.commands.takeover(…, actor="system")`, which checks
`games.rules.can_take_over` under the Game row lock, appends one `takeover_inactivity` row from the
open Week, has the AI player order in the same transaction and tells every Student. The clock is
injected: the sweep and the command get `now` from the test, read from the stored due time, never
from the host (Issue #63)."""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.games import commands, rules
from app.modules.games import service as games_service
from app.modules.messaging import delivery
from app.modules.ops import sweep
from app.platform.db import get_sessionmaker
from app.platform.events.registry import COMMAND_TOPICS
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import execute, listening, query
from tests.games.test_set_snapshot import SETTINGS, snapshot

SECOND = timedelta(seconds=1)


def _user() -> uuid.UUID:
    """A User a notice may name (`notices.user_id` refers to `users`)."""
    user = uuid.uuid7()
    execute(
        TEST_DATABASE_URL,
        "INSERT INTO users (id, email, name, password_hash) VALUES (%s, %s, 'S', NULL)",
        (user, f"takeover-{user}@x.no"),
    )
    return user


async def class_game(
    roles: tuple[str, ...] = ("retailer", "factory"),
    *,
    guided_weeks: int = 0,
    stored: dict | None = None,
    before_snapshot=None,
) -> tuple[str, dict[str, uuid.UUID]]:
    """A started Class game whose `roles` are held by Students (real Users), with the snapshot's
    24-hour Inactivity limit; the other Seats get Rule-based players."""
    game_id = await commands.create("class", class_session_id=uuid.uuid7(), game_number=1)
    students = {role: _user() for role in roles}
    for role, user in students.items():
        await commands.assign_seat(game_id, role, "student", user_id=user)
    if before_snapshot is not None:
        before_snapshot(game_id)
    frozen = {
        **(stored or snapshot()),
        "settings": SETTINGS.model_copy(update={"guided_weeks": guided_weeks}).model_dump(
            mode="json"
        ),
    }
    await commands.set_snapshot(game_id, frozen, keep_students=list(students.values()))
    await commands.start(game_id)
    return game_id, students


def due_of(game_id: str, role: str, week: int = 1) -> datetime | None:
    [(due,)] = query(
        TEST_DATABASE_URL,
        "SELECT t.takeover_due_at FROM seat_turns t JOIN seats s ON s.id = t.seat_id "
        "WHERE t.game_id = %s AND s.role = %s AND t.week = %s",
        (game_id, role, week),
    )
    return due


def takeovers(game_id: str) -> list[tuple]:
    """(role, from_week, occupant_kind, actor_user_id) of the Game's Takeover rows."""
    return query(
        TEST_DATABASE_URL,
        "SELECT s.role, o.from_week, o.occupant_kind, o.actor_user_id FROM seat_occupancy o "
        "JOIN seats s ON s.id = o.seat_id WHERE s.game_id = %s "
        "AND o.reason = 'takeover_inactivity' ORDER BY o.id",
        (game_id,),
    )


def open_week(game_id: str) -> int:
    [(week,)] = query(
        TEST_DATABASE_URL,
        "SELECT max(week) FROM game_weeks WHERE game_id = %s AND NOT finished",
        (game_id,),
    )
    return week


# The one eligibility check (pure).

NOW = datetime(2026, 11, 21, 12, tzinfo=UTC)
RUNNING = {"lifecycle": "running", "purpose": "class"}


def turn(**changes) -> dict:
    return {
        "occupant_kind": "student",
        "ordered_at": None,
        "viewed_at": None,
        "takeover_due_at": NOW - SECOND,
        **changes,
    }


@pytest.mark.parametrize(
    ("game", "the_turn", "guided", "refused"),
    [
        (RUNNING, turn(), False, None),
        (RUNNING, turn(takeover_due_at=NOW), False, None),  # due at `now` exactly
        (RUNNING, turn(takeover_due_at=NOW + SECOND), False, "takeover_not_due"),
        (RUNNING, turn(takeover_due_at=None), False, "takeover_not_due"),  # nobody ordered
        (RUNNING, turn(ordered_at=NOW), False, "order_exists"),
        # A Guided Week's Order is placed at opening; the Student has not viewed it.
        (RUNNING, turn(ordered_at=NOW), True, None),
        (RUNNING, turn(ordered_at=NOW, viewed_at=NOW), True, "order_exists"),
        (RUNNING, turn(occupant_kind="rule_based"), False, "seat_not_student_held"),
        (RUNNING, None, False, "seat_not_student_held"),
        ({**RUNNING, "lifecycle": "finished"}, turn(), False, "game_not_running"),
        ({**RUNNING, "lifecycle": "not_started"}, turn(), False, "game_not_running"),
        ({**RUNNING, "purpose": "lecturer_test"}, turn(), False, "takeover_not_allowed"),
        ({**RUNNING, "purpose": "simulation"}, turn(), False, "takeover_not_allowed"),
    ],
)
def test_can_take_over_is_the_one_eligibility_check(game, the_turn, guided, refused):
    assert rules.can_take_over(game, the_turn, "system", NOW, guided=guided) == refused


# The command and the sweep.


async def test_the_sweep_takes_the_seat_over_within_a_minute_of_the_due_time(games_db, mail_db):
    game_id, students = await class_game()
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    due = due_of(game_id, "factory")
    assert due is not None
    # A second before the due time nothing happens.
    await sweep.run(due - SECOND)
    assert takeovers(game_id) == []
    with listening(games_db) as events:
        done = await sweep.run(due + 59 * SECOND)
        received = events.drain()
    assert done["games.takeover"] == 1
    assert takeovers(game_id) == [("factory", 1, "rule_based", None)]
    # The Rule-based player ordered in the same transaction; the Week completed and advanced.
    assert open_week(game_id) == 2
    takeover_events = {e["topic"] for e in received}
    assert COMMAND_TOPICS["games.takeover"] <= takeover_events
    assert {e["id"] for e in received if e["topic"] == "user"} >= {
        str(u) for u in students.values()
    }
    # Each Student is told at once, ids only.
    notices = query(
        TEST_DATABASE_URL,
        "SELECT user_id, dedupe_key FROM notices WHERE kind = 'takeover_notice' ORDER BY user_id",
    )
    [(occupancy,)] = query(
        TEST_DATABASE_URL,
        "SELECT o.id FROM seat_occupancy o JOIN seats s ON s.id = o.seat_id "
        "WHERE s.game_id = %s AND o.reason = 'takeover_inactivity'",
        (game_id,),
    )
    # One notice per occupancy row and Student (Story 8.5: a later Takeover of the Seat in the
    # same Week, after a Reclaim, is told too).
    assert sorted(notices) == sorted(
        (user, f"takeover_notice:{occupancy}:{user}") for user in students.values()
    )
    assert delivery.KINDS["takeover_notice"].mode == delivery.IMMEDIATE
    # An Order the Student sends after the Takeover is not theirs to place.
    with pytest.raises(commands.CommandError) as refused:
        await commands.place_order(game_id, "factory", 2, 4, "student", actor=students["factory"])
    assert (refused.value.code, refused.value.status) == ("seat_not_yours", 409)
    # The next minute's sweep finds nothing more to do.
    assert (await sweep.run(due + 2 * 60 * SECOND))["games.takeover"] == 0
    assert len(takeovers(game_id)) == 1


async def test_in_a_guided_week_the_takeover_keeps_the_fixed_order_and_the_week_advances(
    games_db, mail_db
):
    game_id, students = await class_game(guided_weeks=2)
    assert await commands.view_week(game_id, "retailer", 1, actor=students["retailer"])
    due = due_of(game_id, "factory")
    assert due is not None and open_week(game_id) == 1
    await sweep.run(due + 30 * SECOND)
    assert takeovers(game_id) == [("factory", 1, "rule_based", None)]
    assert open_week(game_id) == 2
    # The fixed Order placed when Week 1 opened stands: one Decision log row, decided by guided.
    assert query(
        TEST_DATABASE_URL,
        "SELECT w.decided_by FROM seat_weeks w JOIN seats s ON s.id = w.seat_id "
        "WHERE w.game_id = %s AND w.week = 1 AND s.role = 'factory'",
        (game_id,),
    ) == [("guided",)]


async def test_two_takeovers_race_and_one_row_is_appended(games_db, mail_db):
    game_id, students = await class_game()
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    now = due_of(game_id, "factory") + SECOND
    results = await asyncio.gather(
        commands.takeover(game_id, "factory", actor="system", now=now),
        commands.takeover(game_id, "factory", actor="system", now=now),
        return_exceptions=True,
    )
    refused = [r for r in results if isinstance(r, commands.CommandError)]
    # Story 8.5: the loser is told a Takeover exists and who made it (here the system).
    assert len(refused) == 1 and refused[0].code == "takeover_exists"
    assert refused[0].fields["acted_by"] == {"kind": "system", "user_id": None}
    assert refused[0].fields["acted_at"]
    assert len(takeovers(game_id)) == 1


async def test_an_order_committed_first_stands_and_a_race_leaves_one_outcome(games_db, mail_db):
    game_id, students = await class_game(("retailer", "wholesaler", "factory"))
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    now = due_of(game_id, "factory") + SECOND
    # The wholesaler's Student orders before the sweep acts: the Takeover is skipped.
    await commands.place_order(game_id, "wholesaler", 1, 5, "student", actor=students["wholesaler"])
    with pytest.raises(commands.CommandError) as refused:
        await commands.takeover(game_id, "wholesaler", actor="system", now=now)
    assert (refused.value.code, refused.value.status) == ("order_exists", 409)
    assert (await sweep.run(now))["games.takeover"] == 1  # only the factory is still due
    assert [row[0] for row in takeovers(game_id)] == ["factory"]


async def test_an_order_and_a_takeover_at_the_same_moment_end_one_way(games_db, mail_db):
    game_id, students = await class_game(("retailer", "factory", "wholesaler"))
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    now = due_of(game_id, "factory") + SECOND
    order, taken = await asyncio.gather(
        commands.place_order(game_id, "factory", 1, 7, "student", actor=students["factory"]),
        commands.takeover(game_id, "factory", actor="system", now=now),
        return_exceptions=True,
    )
    decided = query(
        TEST_DATABASE_URL,
        "SELECT w.decided_by FROM seat_weeks w JOIN seats s ON s.id = w.seat_id "
        "WHERE w.game_id = %s AND w.week = 1 AND s.role = 'factory'",
        (game_id,),
    )
    if isinstance(taken, commands.CommandError):  # the Order won the lock
        assert taken.code == "order_exists" and decided == [("student",)]
        assert takeovers(game_id) == []
    else:  # the Takeover won: the Student's Order is not theirs to place any more
        assert isinstance(order, commands.CommandError) and order.code == "seat_not_yours"
        assert decided == [("rule_based",)] and len(takeovers(game_id)) == 1


async def test_with_no_order_nothing_happens_for_days(games_db, mail_db):
    game_id, _ = await class_game()
    [(db_now,)] = query(TEST_DATABASE_URL, "SELECT now()")
    for days in (1, 3, 6):
        await sweep.run(db_now + timedelta(days=days))
    assert takeovers(game_id) == []
    assert due_of(game_id, "factory") is None and open_week(game_id) == 1


async def test_a_game_whose_policy_has_no_inactivity_takeover_is_never_taken_over(
    games_db, mail_db
):
    """AD-13: even with a due time written past the command (a simulation Game)."""
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
        "UPDATE seat_turns SET wait_started_at = now() - interval '2 days', "
        "takeover_due_at = now() - interval '1 day' WHERE game_id = %s",
        (game_id,),
    )
    [(db_now,)] = query(TEST_DATABASE_URL, "SELECT now()")
    assert await games_service.due_takeovers(db_now) == []
    with pytest.raises(commands.CommandError) as refused:
        await commands.takeover(game_id, "factory", actor="system", now=db_now)
    assert refused.value.code == "takeover_not_allowed"


async def test_an_llm_session_gets_an_llm_player_with_a_deadline(games_db, mail_db, ai_db):
    from tests.games.test_set_snapshot import llm_snapshot

    game_id, students = await class_game(stored=await llm_snapshot())
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    await commands.takeover(
        game_id, "factory", actor="system", now=due_of(game_id, "factory") + SECOND
    )
    assert takeovers(game_id) == [("factory", 1, "llm", None)]
    [(deadline,)] = query(
        TEST_DATABASE_URL,
        "SELECT t.ai_deadline_at FROM seat_turns t JOIN seats s ON s.id = t.seat_id "
        "WHERE t.game_id = %s AND t.week = 1 AND s.role = 'factory'",
        (game_id,),
    )
    assert deadline is not None  # the rescue loop places the fallback if the job never does


async def test_a_seat_the_play_guard_switched_or_a_cost_limited_budget_gets_rule_based(
    games_db, mail_db, ai_db, monkeypatch
):
    from tests.games.test_set_snapshot import llm_snapshot

    stored = await llm_snapshot()

    def guard_switched_once(game_id: str) -> None:
        """The factory Seat had an LLM player the Play guard switched, then its Student again."""
        for kind, reason, user in (
            ("rule_based", "guard_switch", None),
            ("student", "initial", "keep"),
        ):
            execute(
                TEST_DATABASE_URL,
                "INSERT INTO seat_occupancy (id, seat_id, from_week, occupant_kind, reason, "
                "user_id) SELECT %s, s.id, 1, %s, %s, CASE WHEN %s THEN ("
                "SELECT o.user_id FROM seat_occupancy o WHERE o.seat_id = s.id "
                "AND o.user_id IS NOT NULL ORDER BY o.id DESC LIMIT 1) END "
                "FROM seats s WHERE s.game_id = %s AND s.role = 'factory'",
                (uuid.uuid7(), kind, reason, user is not None, game_id),
            )

    game_id, students = await class_game(stored=stored, before_snapshot=guard_switched_once)
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    await commands.takeover(
        game_id, "factory", actor="system", now=due_of(game_id, "factory") + SECOND
    )
    assert takeovers(game_id) == [("factory", 1, "rule_based", None)]

    async def limited(session, game) -> bool:
        return True

    other, students = await class_game(stored=stored)
    await commands.place_order(other, "retailer", 1, 4, "student", actor=students["retailer"])
    monkeypatch.setattr(commands, "_cost_limited", limited)
    await commands.takeover(other, "factory", actor="system", now=due_of(other, "factory") + SECOND)
    assert takeovers(other) == [("factory", 1, "rule_based", None)]


async def test_a_later_guard_switch_keeps_the_seat_taken_over(games_db, mail_db, ai_db):
    """A Takeover's LLM player the Play guard switches later is still the Student's Seat taken over
    (the latest row is `guard_switch`): «bestiller for» stays, now rule-based, and the Student whose
    Seat it was still has no Ordrefelt."""
    from tests.games.test_set_snapshot import llm_snapshot

    game_id, students = await class_game(stored=await llm_snapshot())
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    await commands.takeover(
        game_id, "factory", actor="system", now=due_of(game_id, "factory") + SECOND
    )
    await commands.switch_to_rule_based(game_id, "factory", "guard_switch")

    async def names(ids):
        return {user: f"Navn {user}" for user in ids}

    async with get_sessionmaker()() as session:
        own = await games_service.table_status(
            session, uuid.UUID(game_id), students["factory"], names
        )
    [seat] = [s for s in own.seats if s.role == "factory"]
    assert (seat.holder, seat.mark, seat.mine) == ("ai", "guard_switch", True)
    assert (seat.taken_over, seat.guard_switched) == (True, True)
    assert seat.ordering_for == f"Navn {students['factory']}"


async def test_the_sweep_skips_a_race_and_reports_any_other_refusal(games_db, mail_db, monkeypatch):
    """A Seat that stopped being due between the finder and the lock is skipped quietly; any other
    refusal is the sweep's logged failure, and the sweep goes on."""
    game_id, students = await class_game()
    await commands.place_order(game_id, "retailer", 1, 4, "student", actor=students["retailer"])
    due = due_of(game_id, "factory")
    [(seat,)] = query(
        TEST_DATABASE_URL,
        "SELECT id FROM seats WHERE game_id = %s AND role = 'factory'",
        (game_id,),
    )

    async def found(now):
        return [(game_id, str(seat))]

    monkeypatch.setattr(games_service, "due_takeovers", found)
    with listening(TEST_DATABASE_URL) as events:
        await sweep.run(due - SECOND)  # not due yet under the lock: skipped, nothing written
        received = events.drain()
    assert takeovers(game_id) == []
    # The due time passed with no command (Story 8.3, AD-8): the Game and its Class session are
    # announced again, at the Game's current version, so open pages read it again.
    [(version, session_id)] = query(
        TEST_DATABASE_URL, "SELECT version, class_session_id FROM games WHERE id = %s", (game_id,)
    )
    received = [e for e in received if e["id"] in (game_id, str(session_id))]
    assert {item["topic"] for item in received} == COMMAND_TOPICS["ops.takeover_skipped"]
    assert [(e["id"], e.get("version")) for e in received if e["topic"] == "game"] == [
        (game_id, version)
    ]
    assert [e["id"] for e in received if e["topic"] == "session"] == [str(session_id)]

    async def broken(*args, **kwargs):
        raise commands.CommandError("parameter_set_changed", "changed", 409)

    monkeypatch.setattr(commands, "takeover", broken)
    assert (await sweep.run(due + SECOND))["games.takeover"] == 0  # failed, not counted
    assert takeovers(game_id) == []


def test_an_occupancy_row_without_a_person_never_names_an_actor(games_db):
    """The `actor_user_id` decision (AD-14): rows no person triggers keep it NULL."""
    import psycopg

    with pytest.raises(psycopg.errors.CheckViolation):
        execute(
            TEST_DATABASE_URL,
            "INSERT INTO seat_occupancy (id, seat_id, from_week, occupant_kind, reason, "
            "actor_user_id) VALUES (%s, %s, 1, 'rule_based', 'takeover_inactivity', %s)",
            (uuid.uuid7(), uuid.uuid7(), uuid.uuid7()),
        )
