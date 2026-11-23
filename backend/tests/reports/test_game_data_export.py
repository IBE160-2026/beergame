"""Story 14.8 at the api (cut list, FR-88, AD-12, AD-13, AD-14, AD-15, AD-17, C-2): the Game data
export, `GET /api/class-sessions/{id}/game-data-export`.

One short Class game played three Weeks serves every played test. A make-up game, a Replay and a
Lecturer test Game get Decision log rows copied from it (`copied`), so the purposes, the ordinals
and the marks are checked without playing more games; the file is held against `seat_weeks`."""

import csv
import io
import uuid
from datetime import date

import pytest
from sqlalchemy import event

from app.modules.games.schemas import SeatState
from app.modules.games.service import Purpose, SessionGame
from app.modules.identity.schemas import AccountRole
from app.modules.reports import game_data_export
from app.modules.sessions import service as sessions_service
from app.platform.config import get_settings
from app.platform.db import get_engine
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.messaging.helpers import rows
from tests.reports.test_class_report import add_game
from tests.reports.test_studentside import ADMIN, OTHER_LECTURER
from tests.sessions.test_dates import OUTSIDER
from tests.sessions.test_game_end import _empty, clock, klass, play_weeks, short_game
from tests.sessions.test_open_games import confirmed
from tests.sessions.test_orders import code
from tests.sessions.test_student_choice import email
from tests.sessions.test_test_game import flag

__all__ = ["_empty", "clock", "klass"]

HEADER = (
    "purpose",
    "game",
    "week",
    "role",
    "incoming_order",
    "incoming_delivery",
    "inventory",
    "backlog",
    "order",
    "cost",
    "decided_by",
    "mark",
    "occupant",
)
CHAIN = ["retailer", "wholesaler", "distributor", "factory"]
BANNED = ("ai_", "ki", "score", "feedback", "letter", "bokstav", "name", "navn", "mail", "user")


def export_path(session_id: str) -> str:
    return f"/api/class-sessions/{session_id}/game-data-export"


async def download(session_id: str, who: str = LECTURER):
    return await call(who, "GET", export_path(session_id))


def zip_state(session_id: str) -> str:
    return f"/api/class-sessions/{session_id}/reports/zip"


def audited() -> list[tuple]:
    return rows(
        "SELECT actor_user_id, target_ids, change FROM audit_events "
        "WHERE action = 'game_data_export.downloaded' ORDER BY occurred_at, id"
    )


def lines(response) -> list[list[str]]:
    return list(csv.reader(io.StringIO(response.content.decode("utf-8-sig")), delimiter=";"))


def copied(
    session_id: str,
    source: str,
    purpose: str,
    *,
    fallback_week: int | None = None,
    kind: str = "llm",
    reason: str = "initial",
):
    """A Game of `purpose` with the Decision log of `source` copied, as an AI player's of `kind`
    under the occupancy `reason`: in `fallback_week` the Order is the Rule-based fallback after a
    timeout."""
    game_id = add_game(session_id, 0, "finished", purpose=purpose)
    execute(
        'INSERT INTO seat_weeks (id, game_id, seat_id, week, state_seen, "order", decided_by, '
        "fallback, occupant_kind, reason, opened_at, ordered_at, rule_based_reference_order) "
        'SELECT gen_random_uuid(), %s, seat_id, week, state_seen, "order", '
        "CASE WHEN week = %s THEN 'rule_based' ELSE 'llm' END, "
        "CASE WHEN week = %s THEN 'timeout' ELSE 'none' END, %s, %s, opened_at, "
        "ordered_at, rule_based_reference_order FROM seat_weeks WHERE game_id = %s",
        game_id,
        fallback_week or 0,
        fallback_week or 0,
        kind,
        reason,
        source,
    )
    return game_id


def stored(game_id: str) -> dict[tuple[int, str], tuple]:
    found = rows(
        "SELECT w.week, s.role, w.state_seen, w.order, w.decided_by, w.occupant_kind "
        "FROM seat_weeks w JOIN seats s ON s.id = w.seat_id WHERE w.game_id = %s",
        game_id,
    )
    return {(week, role): (seen, order, by, kind) for week, role, seen, order, by, kind in found}


@pytest.fixture
def flag_off(monkeypatch):
    flag(monkeypatch, False, "FEATURE_GAME_DATA_EXPORT")
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


def test_the_columns_are_the_fixed_allow_list_with_no_ai_or_personal_data():
    assert game_data_export.COLUMNS == HEADER
    for column in game_data_export.COLUMNS:
        assert not any(word in column.lower() for word in BANNED), column


def test_class_games_keep_their_number_and_the_others_count_within_their_purpose():
    ids = [uuid.uuid7() for _ in range(5)]
    found = [
        SessionGame(game_id=ids[0], purpose=Purpose.REPLAY, number=None, end_reason=None),
        SessionGame(game_id=ids[1], purpose=Purpose.CLASS, number=7, end_reason=None),
        SessionGame(game_id=ids[2], purpose=Purpose.MAKEUP, number=None, end_reason=None),
        SessionGame(game_id=ids[3], purpose=Purpose.REPLAY, number=None, end_reason=None),
        SessionGame(game_id=ids[4], purpose=Purpose.CLASS, number=None, end_reason=None),
    ]
    assert game_data_export.game_keys(list(reversed(found))) == {
        ids[0]: (Purpose.REPLAY, 1),
        ids[1]: (Purpose.CLASS, 7),
        ids[2]: (Purpose.MAKEUP, 1),
        ids[3]: (Purpose.REPLAY, 2),
    }


async def test_a_lecturer_downloads_every_reporting_game_week_and_seat_and_nothing_else(klass):
    session_id, game_id, seated = await short_game(klass)
    await play_weeks(game_id, 3)
    replay = copied(session_id, game_id, "replay", fallback_week=2)
    makeup = copied(session_id, game_id, "makeup")
    test_game = copied(session_id, game_id, "lecturer_test")
    class_rows = stored(game_id)
    weeks = sorted({week for week, _ in class_rows})
    assert weeks[-1] >= 3

    got = await download(session_id)
    assert got.status_code == 200, got.text
    assert got.headers["content-type"] == "text/csv; charset=utf-8"
    assert got.headers["cache-control"] == "no-store"
    assert got.headers["content-disposition"] == (
        'attachment; filename="spilldata-klasseokt-1.csv"'
    )
    assert got.content.startswith("﻿".encode()) and b"\r\n" in got.content
    found = lines(got)
    assert tuple(found[0]) == HEADER
    body = found[1:]
    per_game = len(class_rows)
    assert len(body) == 3 * per_game  # the Class game, the make-up game, the Replay
    # Purpose, game, Week, Role in chain order.
    assert [(r[0], r[1]) for r in body] == (
        [("class", "1")] * per_game + [("makeup", "1")] * per_game + [("replay", "1")] * per_game
    )
    # The open Week holds only the Orders placed so far.
    assert [(int(r[2]), r[3]) for r in body[:per_game]] == sorted(
        class_rows, key=lambda key: (key[0], CHAIN.index(key[1]))
    )
    for r in body[:per_game]:
        seen, order, by, kind = class_rows[(int(r[2]), r[3])]
        assert r[4:10] == [
            str(seen["incoming_order"]),
            str(seen["incoming_delivery"]),
            str(seen["inventory"]),
            str(seen["backlog"]),
            str(order),
            format(SeatState.model_validate(seen).week_cost, "f").replace(".", ","),
        ]
        assert r[10] == by
        assert r[12] == ("student" if kind == "student" else "ai")
    # The one AD-15 mapping: the Replay's fallback Week is marked, its other Weeks are not.
    replay_rows = body[2 * per_game :]
    assert {r[11] for r in replay_rows if r[2] == "2"} == {"fallback_timeout"}
    assert {r[11] for r in replay_rows if r[2] != "2"} == {""}
    assert {r[10] for r in replay_rows if r[2] == "2"} == {"rule_based"}
    assert {r[12] for r in replay_rows} == {"ai"}
    assert {r[12] for r in body[:per_game]} >= {"student"}
    # No name, e-mail, user, Seat or Game id; the Lecturer test Game is never in it.
    text = got.content.decode("utf-8-sig")
    for value in [*map(str, seated), game_id, str(replay), str(makeup), str(test_game)]:
        assert value not in text
    [(names,)] = rows("SELECT array_agg(email) FROM users WHERE id = ANY(%s)", list(seated))
    assert not any(address in text for address in names)
    assert "lecturer_test" not in text
    # One audit row, with counts only.
    [(_, targets, change)] = audited()
    assert targets == {"class_session_id": session_id}
    assert change == {"games": 3, "rows": 3 * per_game}


async def test_the_read_takes_a_fixed_number_of_queries_whatever_the_number_of_games(klass):
    session_id, game_id, _ = await short_game(klass)
    await play_weeks(game_id, 2)
    engine = get_engine().sync_engine
    statements: list[str] = []

    def record(conn, cursor, statement, *rest) -> None:
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", record)
    try:
        statements.clear()
        few = await download(session_id)
        with_few = len(statements)
        for _ in range(5):
            copied(session_id, game_id, "replay")
        statements.clear()
        many = await download(session_id)
        with_many = len(statements)
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert (few.status_code, many.status_code) == (200, 200)
    assert len(lines(many)) - 1 == 6 * (len(lines(few)) - 1)
    assert with_many == with_few


async def test_a_session_whose_games_have_no_order_yet_gives_the_header_only(klass):
    unstarted, _ = await confirmed(klass, 1)  # its Class game has no Order yet
    only = (await download(unstarted)).content.decode("utf-8-sig").splitlines()
    assert only == [";".join(HEADER)]


async def test_a_control_test_session_gives_the_header_only(klass, monkeypatch):
    async def control_test(class_session_id, *, session=None):
        return sessions_service.CONTROL_TEST

    session_id, game_id, _ = await short_game(klass)
    await play_weeks(game_id, 2)
    monkeypatch.setattr(sessions_service, "kind_of", control_test)
    only = (await download(session_id)).content.decode("utf-8-sig").splitlines()
    assert only == [";".join(HEADER)]


async def test_only_the_lecturers_of_the_class_may_export_and_the_block_says_so(klass):
    session_id, _, _ = await short_game(klass)
    await make(OTHER_LECTURER)
    await make(ADMIN, roles=(AccountRole.admin,))
    await make(OUTSIDER, roles=())
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    assisting = "assisterende-faglaerer@x.no"
    put_staff(klass, await make(assisting), "assistant")
    refusals = [
        await download(session_id, ASSISTANT),
        await download(session_id, assisting),
        await download(session_id, OTHER_LECTURER),
        await download(session_id, ADMIN),
        await download(session_id, OUTSIDER),
        await download(session_id, email(0)),
        await download("not-an-id"),
        await download(str(uuid.uuid7())),
    ]
    assert {(r.status_code, r.text) for r in refusals} == {
        (refusals[0].status_code, refusals[0].text)
    }
    assert code(refusals[0]) == (403, "forbidden")
    assert audited() == []

    assert (await call(LECTURER, "GET", zip_state(session_id))).json()["game_data_export"] is True
    assert (await call(ASSISTANT, "GET", zip_state(session_id))).json()["game_data_export"] is False
    assert (await call(assisting, "GET", zip_state(session_id))).json()["game_data_export"] is False

    # Once the Student data is deleted, no file.
    execute(
        "UPDATE class_sessions SET deletion_date = %s WHERE id = %s", date(2000, 1, 1), session_id
    )
    assert code(await download(session_id)) == (409, "data_deleted")
    assert audited() == []


async def test_with_the_flag_off_the_route_does_not_exist_and_the_block_has_no_action(
    klass, flag_off
):
    session_id, _, _ = await short_game(klass)
    off = await download(session_id)
    unknown = await call(LECTURER, "GET", f"/api/class-sessions/{session_id}/no-such-export")
    assert off.status_code == 404
    assert (off.status_code, off.content) == (unknown.status_code, unknown.content)
    # Before any policy: an Assistant lecturer gets the same answer.
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    assert (await download(session_id, ASSISTANT)).content == unknown.content
    assert (await call(LECTURER, "GET", zip_state(session_id))).json()["game_data_export"] is False
    assert audited() == []


async def test_the_mark_is_the_one_ad15_mapping_of_each_row(klass):
    session_id, game_id, _ = await short_game(klass)
    await play_weeks(game_id, 3)
    # Replays in creation order: each copies the Class game's log under one occupancy.
    cases = [
        ("llm", "takeover_inactivity", None, "takeover_inactivity"),
        ("rule_based", "guard_switch", None, "guard_switch"),
        ("llm", "guard_switch", None, ""),  # only a Rule-based occupant marks the switch
        ("rule_based", "cost_limit", None, "cost_limit"),
        ("rule_based", "playout", None, "playout"),
        ("student", "reclaim", None, "reclaim"),
        ("llm", "takeover_staff", 2, "fallback_timeout"),  # a fallback marks first
    ]
    for kind, reason, fallback_week, _ in cases:
        copied(session_id, game_id, "replay", fallback_week=fallback_week, kind=kind, reason=reason)
    body = lines(await download(session_id))[1:]
    for ordinal, (kind, _, fallback_week, expected) in enumerate(cases, start=1):
        replay = [r for r in body if r[0] == "replay" and r[1] == str(ordinal)]
        assert replay
        week = str(fallback_week or 1)
        assert {r[11] for r in replay if r[2] == week} == {expected}, (ordinal, kind)
        assert {r[12] for r in replay} == {"student" if kind == "student" else "ai"}
    # The last Replay's other Weeks carry the Takeover by staff.
    last = [r for r in body if r[0] == "replay" and r[1] == str(len(cases))]
    assert {r[11] for r in last if r[2] != "2"} == {"takeover_staff"}
    # The Class game's Students placed their Orders themselves: no mark.
    assert {r[11] for r in body if r[0] == "class" and r[12] == "student"} == {""}
