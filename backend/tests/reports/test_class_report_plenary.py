"""«Alle spill i plenum» (Story 14.6, FR-86, FR-5, AD-12, AD-13, AD-14):
`GET /api/class-sessions/{id}/plenary` answers the readers of the Oversikt with every Class game's
Netto lager and Orders per Role and Week keyed by game number, and nothing that names, places or
costs a team. One short Class game (`tests.sessions.test_game_end.short_game`) serves the played
tests; the other games are written straight to the tables (`test_class_report.add_game`)."""

import uuid

from sqlalchemy import event

from app.engine.state import WeekState
from app.modules.identity.schemas import AccountRole
from app.modules.reports.class_report_plenary_schemas import PlenaryOut
from app.modules.sessions import service as sessions_service
from app.platform.db import get_engine
from tests.classes.test_classes import LECTURER, OTHER, make
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.messaging.helpers import rows
from tests.reports.test_class_report import ADMIN, CHAIN_ORDER, add_game
from tests.reports.test_class_report_all_games import field_names, schema_fields
from tests.sessions.test_game_end import _empty, clock, emitted, klass, play_weeks, short_game
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass"]

ALLOWED_FIELDS = {"weeks", "roles", "role", "games", "number", "net", "orders"}
"""Every field name the answer may hold: game numbers, Roles, Weeks, Netto lager and Orders."""


async def plenary(who: str, session_id: str):
    return await call(who, "GET", f"/api/class-sessions/{session_id}/plenary")


def test_the_answer_schema_holds_no_identifying_status_or_cost_field():
    assert schema_fields(PlenaryOut.model_json_schema()) == ALLOWED_FIELDS


async def test_the_readers_of_the_oversikt_read_it_and_everyone_else_is_refused_alike(klass):
    session_id, _, _ = await short_game(klass)
    await make(ADMIN, roles=(AccountRole.admin,))
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    owner = await plenary(LECTURER, session_id)
    assert owner.status_code == 200
    assert owner.headers["cache-control"] == "no-store"
    assistant = await plenary(ASSISTANT, session_id)
    assert assistant.status_code == 200
    assert assistant.json() == owner.json()
    refused = [
        await plenary(email(0), session_id),  # a Student of the Class
        await plenary(OTHER, session_id),  # a Lecturer of another Class
        await plenary(ADMIN, session_id),  # an Admin not attached to the Class
        await plenary(LECTURER, str(uuid.uuid7())),  # no such Class session
        await plenary(LECTURER, "not-an-id"),
    ]
    assert {r.status_code for r in refused} == {403}
    assert {r.json()["error"]["code"] for r in refused} == {"forbidden"}
    assert len({r.content for r in refused}) == 1


async def test_every_class_game_by_number_with_its_net_inventory_and_orders_and_nothing_else(
    klass,
):
    session_id, game_id, seated = await short_game(klass)
    await play_weeks(game_id, 4)
    # A Class game not started, and a Lecturer test Game and a Replay that are never listed.
    add_game(session_id, 12, "waiting")
    add_game(session_id, 0, "finished", purpose="lecturer_test")
    add_game(session_id, 0, "finished", purpose="replay")

    response = await plenary(LECTURER, session_id)
    body = response.json()
    states = [
        WeekState.model_validate(state)
        for (state,) in rows(
            "SELECT state FROM game_weeks WHERE game_id = %s AND NOT finished ORDER BY week",
            game_id,
        )
    ]
    orders = rows(
        "SELECT s.role, w.week, w.order FROM seat_weeks w JOIN seats s ON s.id = w.seat_id "
        "WHERE w.game_id = %s",
        game_id,
    )
    weeks = states[-1].week
    assert weeks >= 4
    assert body["weeks"] == weeks
    assert [r["role"] for r in body["roles"]] == CHAIN_ORDER
    for role in body["roles"]:
        assert [g["number"] for g in role["games"]] == [1, 12]
        played, unstarted = role["games"]
        seat = [state.seat(role["role"]) for state in states]
        assert played["net"] == [s.inventory - s.backlog for s in seat]
        expected = {week: order for r, week, order in orders if r == role["role"]}
        assert played["orders"] == [expected.get(week) for week in range(1, weeks + 1)]
        # Not started: no Week of its own, every Order empty.
        assert unstarted["net"] == []
        assert unstarted["orders"] == [None] * weeks
    # Game numbers, Roles, Weeks and values only: no name, id, occupant, status or cost (AD-14).
    assert field_names(body) <= ALLOWED_FIELDS
    text = response.text
    assert not any(str(user) in text for user in seated)
    assert game_id not in text


async def test_a_control_test_session_lists_no_game(klass, monkeypatch):
    # The kind of a Class session never changes (a database trigger), so the read is told it.
    session_id, game_id, _ = await short_game(klass)
    await play_weeks(game_id, 2)

    async def control_test(class_session_id, *, session=None):
        return sessions_service.CONTROL_TEST

    monkeypatch.setattr(sessions_service, "kind_of", control_test)
    body = (await plenary(LECTURER, session_id)).json()
    assert [role["games"] for role in body["roles"]] == [[]] * 4
    assert body["weeks"] == 0


async def test_the_read_takes_a_fixed_number_of_queries_whatever_the_number_of_games(klass):
    session_id, game_id, _ = await short_game(klass)
    await play_weeks(game_id, 2)
    engine = get_engine().sync_engine
    statements: list[str] = []

    def record(conn, cursor, statement, *rest) -> None:
        statements.append(statement)

    add_game(session_id, 12, "waiting")
    event.listen(engine, "before_cursor_execute", record)
    try:
        statements.clear()
        few = await plenary(LECTURER, session_id)
        with_few = len(statements)
        for number in range(13, 30):
            add_game(session_id, number, "finished")
        statements.clear()
        many = await plenary(LECTURER, session_id)
        with_many = len(statements)
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert (few.status_code, many.status_code) == (200, 200)
    assert len(many.json()["roles"][0]["games"]) == len(few.json()["roles"][0]["games"]) + 17
    assert with_many == with_few
