"""The wall's class median rows (Story 7.4, FR-39, FR-5, AD-1, AD-10, AD-13, AD-25, NFR-3):
`GET /api/class-sessions/{id}/overview/aggregates?role=&cells=&status=` answers the Class's staff
with `analysis.wall_aggregates` over the stored Weeks of the Class games the Status filter matches,
with an `ETag` over the filter and the Games' versions; anyone else gets the overview's 403.

One short Class game (`short_game`, 6 Weeks) serves the value test; the query count test writes
its Games straight to the tables."""

import json
import uuid
from decimal import Decimal

from sqlalchemy import event

from app.analysis.wall import Cells, PlayedGame, wall_aggregates
from app.engine import WeekState
from app.modules.games import commands
from app.modules.identity.schemas import AccountRole
from app.platform.db import get_engine
from tests.classes.test_classes import LECTURER, OTHER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.messaging.helpers import rows
from tests.sessions.test_game_end import _empty, clock, emitted, klass, play_weeks, short_game
from tests.sessions.test_open_games import confirmed
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass"]

ADMIN = "admin-only@x.no"


async def aggregates(who: str, session_id: str, query: str = "", **kw):
    return await call(
        who, "GET", f"/api/class-sessions/{session_id}/overview/aggregates{query}", **kw
    )


def played(game_id: str) -> PlayedGame:
    """The Game's stored Week states and placed Orders, read straight from the tables."""
    states = [
        WeekState.model_validate(state)
        for (state,) in rows(
            "SELECT state FROM game_weeks WHERE game_id = %s AND NOT finished ORDER BY week",
            game_id,
        )
    ]
    orders = rows(
        'SELECT w.week, s.role, w."order" FROM seat_weeks w JOIN seats s ON s.id = w.seat_id '
        "WHERE w.game_id = %s",
        game_id,
    )
    return PlayedGame(states=tuple(states), orders={(w, r): o for w, r, o in orders})


def expected(game: PlayedGame, role: str, cells: Cells) -> list[dict]:
    text = lambda v: None if v is None else str(v)  # noqa: E731
    return [
        {
            "week": w.week,
            "games": w.games,
            "median": text(w.median),
            "lower_quartile": text(w.lower_quartile),
            "upper_quartile": text(w.upper_quartile),
            "chain_games": w.chain_games,
            "chain_cost_mean": text(w.chain_cost_mean),
        }
        for w in wall_aggregates([game], role, cells)
    ]


def decimals(weeks: list[dict]) -> list[dict]:
    """Decimal strings compared by value («4.0» equals «4»)."""
    keys = ("median", "lower_quartile", "upper_quartile", "chain_cost_mean")
    return [
        {k: (Decimal(v) if k in keys and v is not None else v) for k, v in w.items()} for w in weeks
    ]


async def test_staff_read_the_median_rows_of_the_stored_weeks_for_each_filter(klass):
    session_id, game_id, seated = await short_game(klass)
    await play_weeks(game_id, 2)  # Weeks 1 and 2 have run; Week 3 is open
    game = played(game_id)
    [(student_role,)] = rows(
        "SELECT s.role FROM seat_occupancy o JOIN seats s ON s.id = o.seat_id "
        "WHERE s.game_id = %s AND o.user_id = %s",
        game_id,
        seated[0],
    )
    response = await aggregates(LECTURER, session_id)  # Fabrikk, Netto lager, every game
    assert response.status_code == 200
    body = response.json()
    assert (body["role"], body["cells"], body["status"], body["games"]) == (
        "factory",
        "net",
        "all",
        1,
    )
    assert [w["week"] for w in body["weeks"]] == [1, 2, 3]
    assert decimals(body["weeks"]) == decimals(expected(game, "factory", Cells.NET))
    assert response.headers["cache-control"] == "private, no-cache"
    # Ordre: the open Week's Student Seats have not ordered, so Week 3 has a chain cost but the
    # Student's Role has no Order there.
    order = (await aggregates(LECTURER, session_id, f"?role={student_role}&cells=order")).json()
    assert decimals(order["weeks"]) == decimals(expected(game, student_role, Cells.ORDER))
    assert order["weeks"][2]["games"] == 0 and order["weeks"][2]["chain_games"] == 1
    cost = (await aggregates(LECTURER, session_id, "?role=wholesaler&cells=cost")).json()
    assert decimals(cost["weeks"]) == decimals(expected(game, "wholesaler", Cells.COST))
    # The game seats two Students, so AI players hold the rest: «Med KI-spiller» matches it.
    with_ai = (await aggregates(LECTURER, session_id, "?status=with_ai")).json()
    assert (with_ai["games"], with_ai["weeks"]) == (1, body["weeks"])
    finished = (await aggregates(LECTURER, session_id, "?status=finished")).json()
    assert (finished["games"], finished["weeks"]) == (0, [])
    # An Assistant lecturer of the Class reads the same.
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    assistant = await aggregates(ASSISTANT, session_id)
    assert (assistant.status_code, assistant.json()) == (200, body)


async def test_a_repeat_with_the_etag_answers_304_until_a_game_or_the_filter_changes(klass):
    session_id, game_id, seated = await short_game(klass)
    first = await aggregates(LECTURER, session_id)
    etag = first.headers["etag"]
    repeat = await aggregates(LECTURER, session_id, headers={"If-None-Match": etag})
    assert (repeat.status_code, repeat.content, repeat.headers["etag"]) == (304, b"", etag)
    other = await aggregates(LECTURER, session_id, "?cells=cost", headers={"If-None-Match": etag})
    assert other.status_code == 200 and other.headers["etag"] != etag
    [(role,)] = rows(
        "SELECT s.role FROM seat_occupancy o JOIN seats s ON s.id = o.seat_id "
        "WHERE s.game_id = %s AND o.user_id = %s",
        game_id,
        seated[0],
    )
    await commands.view_week(game_id, role, 1, actor=seated[0])
    changed = await aggregates(LECTURER, session_id, headers={"If-None-Match": etag})
    assert changed.status_code == 200 and changed.headers["etag"] != etag


async def test_anyone_but_the_staff_and_any_unknown_session_is_refused_the_same(klass):
    session_id, _ = await confirmed(klass, 2)
    await make(ADMIN, roles=(AccountRole.admin,))
    refused = [
        await aggregates(email(0), session_id),  # a Student of the Class
        await aggregates(OTHER, session_id),  # a Lecturer of another Class
        await aggregates(ADMIN, session_id),  # an Admin not attached to the Class
        await aggregates(LECTURER, str(uuid.uuid7())),  # no such Class session
        await aggregates(LECTURER, "not-an-id"),
    ]
    assert {r.status_code for r in refused} == {403}
    assert len({r.content for r in refused}) == 1
    bad = await aggregates(LECTURER, session_id, "?cells=everything")
    assert bad.status_code == 422


async def test_the_aggregates_read_a_fixed_number_of_queries_whatever_the_number_of_games(klass):
    session_id, _ = await confirmed(klass, 2)
    seat = {
        "incoming_order": 4,
        "incoming_delivery": 4,
        "shipped": 4,
        "inventory": 12,
        "backlog": 0,
        "cost": "6",
        "total_cost": "0",
        "incoming_orders": [],
        "goods_slots": [],
        "production_orders": [],
    }
    state = {
        "week": 1,
        "finished": False,
        "seats": [
            {**seat, "role": r} for r in ("retailer", "wholesaler", "distributor", "factory")
        ],
    }

    def add_games(first: int, count: int) -> None:
        """Running Class games with a summary row and two Week states each, written straight to
        the tables: 100 played games would make the test slow."""
        for number in range(first, first + count):
            game_id = uuid.uuid7()
            execute(
                "INSERT INTO games (id, purpose, lifecycle, version, class_session_id, "
                "game_number) VALUES (%s, 'class', 'running', 3, %s, %s)",
                game_id,
                session_id,
                number,
            )
            execute(
                "INSERT INTO game_summaries (game_id, class_session_id, game_number, purpose, "
                "status, week, waiting_for, occupants, chain_cost, version) "
                "VALUES (%s, %s, %s, 'class', 'running', 2, '[]', '[]', 48, 3)",
                game_id,
                session_id,
                number,
            )
            for week in (1, 2):
                execute(
                    "INSERT INTO game_weeks (game_id, week, finished, state) "
                    "VALUES (%s, %s, false, %s)",
                    game_id,
                    week,
                    json.dumps({**state, "week": week}),
                )

    engine = get_engine().sync_engine
    statements: list[str] = []

    def record(conn, cursor, statement, *rest) -> None:
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        add_games(10, 1)
        counts = []
        for query in ("?status=running", "?status=running&cells=order"):
            statements.clear()
            few = await aggregates(LECTURER, session_id, query)
            counts.append(len(statements))
            assert few.json()["games"] == 1
        add_games(11, 99)
        for i, query in enumerate(("?status=running", "?status=running&cells=order")):
            statements.clear()
            many = await aggregates(LECTURER, session_id, query)
            assert len(statements) == counts[i]
            assert many.json()["games"] == 100
    finally:
        event.remove(engine, "before_cursor_execute", record)
    weeks = many.json()["weeks"]
    assert [(w["week"], w["games"], w["chain_games"]) for w in weeks] == [(1, 0, 100), (2, 0, 100)]
    net = (await aggregates(LECTURER, session_id, "?status=running")).json()["weeks"]
    assert [(w["median"], w["chain_cost_mean"]) for w in net] == [("12", "24.00"), ("12", "24.00")]
