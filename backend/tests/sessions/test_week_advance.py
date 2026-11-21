"""Story 6.15 (FR-26, AD-1, AD-2, AD-8): the last Order of a Week advances it in the same
transaction. That transaction stores the new Week state and its four turns, raises the Game's
`version` once and emits `game:<id>`, `session:<id>` (a Class game is on the Lecturer overview) and
`user:<id>` for every Student before any client is told; a last human Order and an AI Order
arriving at the same moment advance exactly once. The play screen then reads the new Week from
stored state on any device."""

import asyncio
import uuid

from app.engine import GameSettings
from app.modules.games import commands
from tests.ai.helpers import stored_config
from tests.conftest import TEST_DATABASE_URL
from tests.games.helpers import listening, query, seat_student, student_of
from tests.games.test_place_order import counts
from tests.sessions.test_orders import CLASSIC, free_week, order
from tests.sessions.test_play import play
from tests.sessions.test_student_home import _empty, clock, klass

__all__ = ["_empty", "clock", "klass"]


def week_rows(game_id: str, week: int) -> tuple[int, int]:
    """Stored Week states and turns of `week`."""
    ((states, turns),) = query(
        TEST_DATABASE_URL,
        "SELECT (SELECT count(*) FROM game_weeks WHERE game_id = %s AND week = %s), "
        "(SELECT count(*) FROM seat_turns WHERE game_id = %s AND week = %s)",
        (game_id, week) * 2,
    )
    return states, turns


def class_session_of(game_id: str) -> str:
    ((session_id,),) = query(
        TEST_DATABASE_URL, "SELECT class_session_id::text FROM games WHERE id = %s", (game_id,)
    )
    return session_id


def holders_of(game_id: str) -> set[str]:
    rows = query(
        TEST_DATABASE_URL,
        "SELECT DISTINCT o.user_id::text FROM seat_occupancy o JOIN seats s ON s.id = o.seat_id "
        "WHERE s.game_id = %s AND o.occupant_kind = 'student'",
        (game_id,),
    )
    return {row[0] for row in rows}


async def test_the_last_order_advances_the_week_and_tells_everyone_in_one_transaction(klass):
    game_id, by_role = await free_week(klass, students=3)
    week = CLASSIC.guided_weeks + 1
    *first, (_, last) = by_role.items()
    for _, who in first:
        assert (await order(who, game_id, week, {"order": 7})).status_code == 204
    ((version,),) = query(TEST_DATABASE_URL, "SELECT version FROM games WHERE id = %s", (game_id,))
    assert week_rows(game_id, week + 1) == (0, 0)
    with listening(TEST_DATABASE_URL) as heard:
        assert (await order(last, game_id, week, {"order": 9})).status_code == 204
        events = heard.drain()
    # One transaction: the new Week's state and all four turns, one version step, and its events.
    assert week_rows(game_id, week + 1) == (1, 4)
    assert events == [
        {"topic": "game", "id": game_id, "version": version + 1},
        {"topic": "session", "id": class_session_of(game_id), "version": None},
        *({"topic": "user", "id": user, "version": None} for user in sorted(holders_of(game_id))),
    ]
    # Every Student reads the new Week from stored state, on any device: the play envelope is
    # the same for a second read (a reload or another browser).
    for who in by_role.values():
        envelope = (await play(who, game_id)).json()
        assert envelope["seat_state"]["week"] == week + 1
        assert envelope["turn"]["order"] is None
        again = (await play(who, game_id)).json()
        assert envelope == {**again, "server_now": envelope["server_now"]}


async def test_a_last_human_order_and_an_ai_order_at_once_advance_exactly_once(games_db, ai_db):
    """The LLM player's Order (its job) and the last Student's Order race for the Game row lock:
    whichever commits second completes the Week, and the Week advances once."""
    config_id = await stored_config()
    for _ in range(3):
        game_id = await commands.create(
            "simulation",
            GameSettings(demand_seed=1, guided_weeks=0),
            seed=1,
            model_config_id=config_id,
        )
        await commands.assign_seat(game_id, "retailer", "llm")
        seat_student(TEST_DATABASE_URL, game_id, "wholesaler", "distributor", "factory")
        await commands.start(game_id)
        for role in ("wholesaler", "distributor"):
            await commands.place_order(game_id, role, 1, 4, "student")
        before = counts(games_db, game_id)[0]
        results = await asyncio.gather(
            commands.place_order(
                game_id, "factory", 1, 4, "student", actor=student_of(game_id, "factory")
            ),
            commands.place_order(game_id, "retailer", 1, 4, "llm", llm_call_ids=[uuid.uuid4()]),
        )
        assert sorted(r.open_week for r in results) == [1, 2]
        # One version step per Order and no extra one for the advance; two Week states, eight
        # turns, the four Orders of Week 1.
        assert counts(games_db, game_id) == (before + 2, 4, 2, 8, 4)
        assert week_rows(game_id, 2) == (1, 4)
