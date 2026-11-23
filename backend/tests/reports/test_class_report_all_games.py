"""«Alle spill side om side» (Story 14.5, FR-86, FR-5, AD-12, AD-13, AD-14, AD-16):
`GET /api/me/class-sessions/{id}/all-games` answers a Student of the Class session, once their
Debrief is done and the Play deadline has passed, with every Class game's Orders per Role and
Week keyed by game number and their own game marked; Hjem's `all_games_open` says the same.
One short Class game (`tests.sessions.test_game_end.short_game`) serves the played tests; the
other games are written straight to the tables (`test_class_report.add_game`)."""

import uuid
from datetime import timedelta

from sqlalchemy import event

from app.modules.games import commands
from app.modules.games import service as games_service
from app.modules.progress import service as progress
from app.modules.reports.class_report_all_games_schemas import ClassGamesOut
from app.modules.sessions import service as sessions_service
from app.platform import auth
from app.platform.db import get_engine
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_staff import call
from tests.messaging.helpers import rows
from tests.reports.test_class_report import CHAIN_ORDER, add_game
from tests.sessions.test_dates import OUTSIDER, PLAY
from tests.sessions.test_game_end import _empty, clock, emitted, klass, play_weeks, short_game
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass"]

AFTER_PLAY = PLAY + timedelta(minutes=1)
ALLOWED_FIELDS = {"weeks", "own_game", "roles", "role", "games", "number", "own", "orders"}
"""Every field name the answer may hold: game numbers, Roles, Weeks and Orders only (AD-14)."""


async def all_games(who: str, session_id: str):
    return await call(who, "GET", f"/api/me/class-sessions/{session_id}/all-games")


async def flag(who: str, session_id: str) -> bool:
    response = await call(who, "GET", "/api/me/class-sessions")
    [item] = [item for item in response.json()["items"] if item["id"] == session_id]
    return item["all_games_open"]


async def debriefed(user_id: uuid.UUID, session_id: str) -> None:
    await progress.record_step(user_id, uuid.UUID(session_id), progress.Step.DEBRIEF, AFTER_PLAY)


def code(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


def field_names(value) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {name for inner in value.values() for name in field_names(inner)}
    if isinstance(value, list):
        return {name for inner in value for name in field_names(inner)}
    return set()


def schema_fields(schema: dict) -> set[str]:
    found: set[str] = set(schema.get("properties", {}))
    for definition in schema.get("$defs", {}).values():
        found |= set(definition.get("properties", {}))
    return found


def test_the_answer_schema_holds_no_identifying_or_cost_field():
    assert schema_fields(ClassGamesOut.model_json_schema()) == ALLOWED_FIELDS


async def test_the_view_stays_locked_until_the_debrief_is_done_and_the_play_deadline_passed(
    klass, monkeypatch
):
    session_id, game_id, seated = await short_game(klass)
    await play_weeks(game_id, 3)
    # Neither: the Debrief is not done and the Play deadline is ahead.
    assert code(await all_games(email(0), session_id)) == (403, "all_games_locked")
    assert await flag(email(0), session_id) is False
    # While locked, a User who is not a Student of the session reads forbidden, not locked.
    await make(OUTSIDER, roles=())  # a User with no Class
    assert code(await all_games(OUTSIDER, session_id)) == (403, "forbidden")
    assert code(await all_games(LECTURER, session_id)) == (403, "forbidden")
    # The Debrief done, the Play deadline still ahead.
    await debriefed(seated[0], session_id)
    assert code(await all_games(email(0), session_id)) == (403, "all_games_locked")
    assert await flag(email(0), session_id) is False
    # At the Play deadline itself the view opens; a second before it stays locked.
    monkeypatch.setattr(auth, "utcnow", lambda: PLAY - timedelta(seconds=1))
    assert code(await all_games(email(0), session_id)) == (403, "all_games_locked")
    monkeypatch.setattr(auth, "utcnow", lambda: PLAY)
    assert (await all_games(email(0), session_id)).status_code == 200
    assert await flag(email(0), session_id) is True
    # The Play deadline passed: open for the Student whose Debrief is done, not for the other.
    monkeypatch.setattr(auth, "utcnow", lambda: AFTER_PLAY)
    opened = await all_games(email(0), session_id)
    assert opened.status_code == 200
    assert opened.headers["cache-control"] == "no-store"
    assert await flag(email(0), session_id) is True
    assert code(await all_games(email(1), session_id)) == (403, "all_games_locked")
    assert await flag(email(1), session_id) is False
    # Not their own Class session: one answer for all (FR-5).
    refused = [
        await all_games(OUTSIDER, session_id),
        await all_games(LECTURER, session_id),
        await all_games(email(0), str(uuid.uuid7())),
        await all_games(email(0), "not-an-id"),
    ]
    assert {r.status_code for r in refused} == {403}
    assert {r.json()["error"]["code"] for r in refused} == {"forbidden"}
    assert len({r.content for r in refused}) == 1


async def test_every_class_game_by_number_with_the_own_game_marked_and_nothing_identifying(
    klass, monkeypatch
):
    session_id, game_id, seated = await short_game(klass)
    await play_weeks(game_id, 4)
    # A Class game with no Order yet, and a Lecturer test Game and a Replay that are never listed.
    add_game(session_id, 12, "waiting")
    add_game(session_id, 0, "finished", purpose="lecturer_test")
    add_game(session_id, 0, "finished", purpose="replay")
    await debriefed(seated[0], session_id)
    monkeypatch.setattr(auth, "utcnow", lambda: AFTER_PLAY)

    response = await all_games(email(0), session_id)
    body = response.json()
    stored = rows(
        "SELECT s.role, w.week, w.order FROM seat_weeks w JOIN seats s ON s.id = w.seat_id "
        "WHERE w.game_id = %s",
        game_id,
    )
    weeks = max(week for _, week, _ in stored)
    assert body["weeks"] == weeks
    assert body["own_game"] == 1
    assert [r["role"] for r in body["roles"]] == CHAIN_ORDER
    for role in body["roles"]:
        assert [(g["number"], g["own"]) for g in role["games"]] == [(1, True), (12, False)]
        own, other = role["games"]
        expected = {week: order for r, week, order in stored if r == role["role"]}
        assert own["orders"] == [expected.get(week) for week in range(1, weeks + 1)]
        assert other["orders"] == [None] * weeks
    # Game numbers, Roles, Weeks and Orders only: no name, id, occupant or cost (AD-14).
    assert field_names(body) <= ALLOWED_FIELDS
    text = response.text
    assert not any(str(user) in text for user in seated)
    assert game_id not in text


async def test_a_student_whose_seat_was_taken_over_keeps_their_class_game_as_their_own(
    klass, monkeypatch
):
    session_id, game_id, seated = await short_game(klass)
    await play_weeks(game_id, 2)
    seat = next(
        s for s in (await games_service.get_game(game_id)).seats if str(s.user_id) == str(seated[0])
    )
    await commands.switch_to_rule_based(game_id, seat.role, "takeover_inactivity")
    add_game(session_id, 12, "waiting")
    await debriefed(seated[0], session_id)
    monkeypatch.setattr(auth, "utcnow", lambda: AFTER_PLAY)
    body = (await all_games(email(0), session_id)).json()
    assert body["own_game"] == 1
    assert [g["own"] for g in body["roles"][0]["games"]] == [True, False]


async def test_a_control_test_session_lists_no_game(klass, monkeypatch):
    # The kind of a Class session never changes (a database trigger), so the read is told it.
    session_id, _, seated = await short_game(klass)

    async def control_test(class_session_id, *, session=None):
        return sessions_service.CONTROL_TEST

    monkeypatch.setattr(sessions_service, "kind_of", control_test)
    await debriefed(seated[0], session_id)
    monkeypatch.setattr(auth, "utcnow", lambda: AFTER_PLAY)
    body = (await all_games(email(0), session_id)).json()
    assert body["own_game"] is None
    assert [role["games"] for role in body["roles"]] == [[]] * 4
    assert body["weeks"] == 0


async def test_the_read_takes_a_fixed_number_of_queries_whatever_the_number_of_games(
    klass, monkeypatch
):
    session_id, game_id, seated = await short_game(klass)
    await play_weeks(game_id, 2)
    await debriefed(seated[0], session_id)
    monkeypatch.setattr(auth, "utcnow", lambda: AFTER_PLAY)
    engine = get_engine().sync_engine
    statements: list[str] = []

    def record(conn, cursor, statement, *rest) -> None:
        statements.append(statement)

    add_game(session_id, 12, "waiting")
    event.listen(engine, "before_cursor_execute", record)
    try:
        statements.clear()
        few = await all_games(email(0), session_id)
        with_few = len(statements)
        for number in range(13, 30):
            add_game(session_id, number, "finished")
        statements.clear()
        many = await all_games(email(0), session_id)
        with_many = len(statements)
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert (few.status_code, many.status_code) == (200, 200)
    assert len(many.json()["roles"][0]["games"]) == len(few.json()["roles"][0]["games"]) + 17
    assert with_many == with_few
