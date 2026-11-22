"""The Oversikt of a Class session (Story 7.1, FR-39, FR-5, AD-12, AD-13, AD-25, NFR-3, NFR-7):
`GET /api/class-sessions/{id}/overview` answers the Class's staff with every Class game from its
`game_summaries` row, names resolved at read time, the headline counts and `server_now`, with an
`ETag`; anyone else, and a Class session that does not exist, gets the same 403. The api's clock is
fixed and the sweep is handed its `now`."""

import json
import uuid
from decimal import Decimal

from sqlalchemy import event

from app.engine import GameSettings
from app.modules.games import commands
from app.modules.games.views import chain_result
from app.modules.identity.schemas import AccountRole
from app.modules.progress import service as progress_service
from app.platform.db import get_engine
from tests.classes.test_classes import LECTURER, OTHER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW
from tests.classes.test_staff import ASSISTANT, call, put_staff
from tests.messaging.helpers import rows
from tests.sessions.test_game_end import (
    WEEKS,
    _empty,
    clock,
    emitted,
    klass,
    play_weeks,
    short_game,
)
from tests.sessions.test_open_games import confirmed
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass"]

ADMIN = "admin-only@x.no"


async def overview(who: str, session_id: str, **kw):
    return await call(who, "GET", f"/api/class-sessions/{session_id}/overview", **kw)


def user_name(address: str) -> str:
    return rows("SELECT name FROM users WHERE email = %s", address)[0][0]


async def test_before_the_start_date_the_overview_lists_the_allocation_without_numbers(klass):
    session_id, _ = await confirmed(klass, 6)
    response = await overview(LECTURER, session_id)
    assert response.status_code == 200
    body = response.json()
    assert body["before_start"] is True
    assert body["alert"] is None
    # The page reads again when the Start date passes (AD-8).
    assert body["start_at"] is not None
    assert body["next_change_at"] == body["start_at"]
    assert (body["class_name"], body["session_number"], body["next_cursor"]) == (
        "class-of-1994",
        1,
        None,
    )
    assert body["counts"] == {"waiting": 0, "running": 0, "not_started": 2, "finished": 0}
    assert [item["game_number"] for item in body["items"]] == [1, 2]
    for item in body["items"]:
        assert (item["status"], item["week"], item["chain_cost"], item["waiting_for"]) == (
            "not_started",
            None,
            None,
            [],
        )
        assert [seat["role"] for seat in item["seats"]] == [
            "factory",
            "distributor",
            "wholesaler",
            "retailer",
        ]
    named = {seat["name"] for item in body["items"] for seat in item["seats"] if seat["name"]}
    assert named == {user_name(email(i)) for i in range(6)}
    # The rail (Story 7.6): no cost block before the Start date; the Trakt counts the registered.
    assert body["cost"] is None
    assert body["ai"] == {"seats": 0, "games": 0}
    assert body["funnel"][0] == {"stage": "registered", "count": 6}
    assert {seat["holder"] for item in body["items"] for seat in item["seats"]} <= {
        "student",
        "free",
    }


async def test_staff_see_whom_a_running_game_waits_for_and_test_games_stay_out(klass):
    session_id, game_id, seated = await short_game(klass)
    first = await overview(LECTURER, session_id)
    assert first.status_code == 200
    body = first.json()
    assert body["before_start"] is False
    assert body["next_change_at"] is None
    [item] = body["items"]
    assert (item["status"], item["week"], item["chain_cost"]) == ("running", 1, "0.0000")
    assert body["counts"] == {"waiting": 0, "running": 1, "not_started": 0, "finished": 0}
    assert {seat["holder"] for seat in item["seats"]} == {"student", "ai"}
    # The rail (Story 7.6): the AI players counted from the Seats, no cost while none finished.
    assert body["ai"] == {"seats": 2, "games": 1}
    assert body["cost"] is None
    # Nothing waits: no Varselbånd (Story 7.11).
    assert body["alert"] is None
    assert [stage["stage"] for stage in body["funnel"]] == [
        "registered",
        "class_game",
        "debrief",
        "quiz_passed",
        "replay",
        "test_submitted",
        "assessment_ready",
    ]
    assert [stage["count"] for stage in body["funnel"]] == [2, 0, 0, 0, 0, 0, 0]
    # One Student opens the Guided Week, the other has not: the game waits for them by name.
    holders = {seat["role"]: seat["name"] for seat in item["seats"] if seat["holder"] == "student"}
    role_of = dict(
        rows(
            "SELECT o.user_id, s.role FROM seat_occupancy o JOIN seats s ON s.id = o.seat_id "
            "WHERE s.game_id = %s AND o.user_id IS NOT NULL",
            game_id,
        )
    )
    viewer, other = seated
    await commands.view_week(game_id, role_of[viewer], 1, actor=viewer)
    body = (await overview(LECTURER, session_id)).json()
    [item] = body["items"]
    assert item["status"] == "waiting"
    assert body["counts"]["waiting"] == 1
    [wait] = item["waiting_for"]
    assert (wait["role"], wait["name"]) == (role_of[other], holders[role_of[other]])
    assert wait["since"] == item["wait_started_at"]
    # The Varselbånd names the game and the Student, chosen by the api (Story 7.11, AD-10).
    assert body["alert"] == {
        "game_id": game_id,
        "game_number": item["game_number"],
        "role": role_of[other],
        "name": holders[role_of[other]],
        "user_id": str(other),
        "since": wait["since"],
    }
    # A Lecturer's test Game of the same session is in no list and no count (AD-13).
    await commands.create("lecturer_test", GameSettings(), class_session_id=uuid.UUID(session_id))
    again = (await overview(LECTURER, session_id)).json()
    assert [i["game_id"] for i in again["items"]] == [game_id]
    assert again["counts"] == body["counts"]
    assert again["ai"] == body["ai"]
    # An Assistant lecturer of the Class reads the same.
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    assistant = await overview(ASSISTANT, session_id)
    assert assistant.status_code == 200
    assert assistant.json()["items"] == again["items"]
    assert assistant.json()["alert"] == again["alert"] == body["alert"]


async def test_a_finished_game_fills_the_cost_block_and_the_trakt_with_a_new_etag(klass):
    """Story 7.6: once the Class game finishes, «Klassens kostnad» holds its chain cost as median
    and both quartiles and each Role's lager and restordre as its result shows them; the Trakt
    counts both Students' `class_game` step, and the ETag moves with it."""
    session_id, game_id, seated = await short_game(klass)
    await play_weeks(game_id, WEEKS - 1)
    before = await overview(LECTURER, session_id)
    await play_weeks(game_id, WEEKS)
    after = await overview(LECTURER, session_id, headers={"If-None-Match": before.headers["etag"]})
    assert after.status_code == 200
    body = after.json()
    [item] = body["items"]
    assert item["status"] == "finished"
    cost = body["cost"]
    assert cost["games"] == 1
    chain = Decimal(item["chain_cost"])
    assert {Decimal(cost[k]) for k in ("median", "lower_quartile", "upper_quartile")} == {chain}
    shown = await chain_result(game_id)
    chain_order = ["retailer", "wholesaler", "distributor", "factory"]
    assert [r["role"] for r in cost["roles"]] == chain_order
    for role, out in zip(shown.roles, cost["roles"], strict=True):
        assert Decimal(out["holding_cost"]) == role.holding_cost.quantize(Decimal("0.01"))
        assert Decimal(out["backorder_cost"]) == role.backorder_cost.quantize(Decimal("0.01"))
        assert Decimal(out["total_cost"]) == role.total_cost.quantize(Decimal("0.01"))
    assert Decimal(cost["holding_cost"]) + Decimal(cost["backorder_cost"]) == chain
    assert body["funnel"][:2] == [
        {"stage": "registered", "count": 2},
        {"stage": "class_game", "count": 2},
    ]
    # A step alone moves the Trakt and the ETag (`record_step` emits `session:<id>`).
    await progress_service.record_step(seated[0], uuid.UUID(session_id), "debrief", NOW)
    stepped = await overview(LECTURER, session_id, headers={"If-None-Match": after.headers["etag"]})
    assert stepped.status_code == 200
    assert stepped.json()["funnel"][2] == {"stage": "debrief", "count": 1}
    # A finished Lecturer test Game of the session counts in no cost, AI count or Trakt (AD-13):
    # its summary row, written straight to the table, is never read.
    test_game = uuid.uuid7()
    execute(
        "INSERT INTO games (id, purpose, lifecycle, version, class_session_id) "
        "VALUES (%s, 'lecturer_test', 'finished', 3, %s)",
        test_game,
        session_id,
    )
    execute(
        "INSERT INTO game_summaries (game_id, class_session_id, purpose, status, week, "
        "waiting_for, occupants, chain_cost, version) VALUES (%s, %s, 'lecturer_test', "
        "'finished', 2, '[]', %s, 99999, 3)",
        test_game,
        session_id,
        json.dumps([{"role": "retailer", "occupant_kind": "rule_based", "user_id": None}]),
    )
    unchanged = (await overview(LECTURER, session_id)).json()
    assert (unchanged["cost"], unchanged["ai"]) == (stepped.json()["cost"], stepped.json()["ai"])


async def test_a_repeat_with_the_etag_answers_304_until_something_changes(klass):
    session_id, game_id, seated = await short_game(klass)
    first = await overview(LECTURER, session_id)
    etag = first.headers["etag"]
    assert first.headers["cache-control"] == "private, no-cache"
    repeat = await overview(LECTURER, session_id, headers={"If-None-Match": etag})
    assert (repeat.status_code, repeat.content, repeat.headers["etag"]) == (304, b"", etag)
    # A weakened tag among others matches too (RFC 9110's weak comparison).
    weak = await overview(LECTURER, session_id, headers={"If-None-Match": f'"other", W/{etag}'})
    assert weak.status_code == 304
    viewer = seated[0]
    [(role,)] = rows(
        "SELECT s.role FROM seat_occupancy o JOIN seats s ON s.id = o.seat_id "
        "WHERE s.game_id = %s AND o.user_id = %s",
        game_id,
        viewer,
    )
    await commands.view_week(game_id, role, 1, actor=viewer)
    changed = await overview(LECTURER, session_id, headers={"If-None-Match": etag})
    assert changed.status_code == 200
    assert changed.headers["etag"] != etag


async def test_anyone_but_the_staff_of_the_class_is_refused_the_same(klass):
    session_id, _ = await confirmed(klass, 2)
    await make(ADMIN, roles=(AccountRole.admin,))
    refused = [
        await overview(email(0), session_id),  # a Student of the Class
        await overview(OTHER, session_id),  # a Lecturer of another Class
        await overview(ADMIN, session_id),  # an Admin not attached to the Class
        await overview(LECTURER, str(uuid.uuid7())),  # no such Class session
        await overview(LECTURER, "not-an-id"),
    ]
    assert {r.status_code for r in refused} == {403}
    assert len({r.content for r in refused}) == 1


async def test_the_overview_reads_a_fixed_number_of_queries_whatever_the_number_of_games(klass):
    session_id, _ = await confirmed(klass, 2)
    students = [
        row[0]
        for row in rows(
            "SELECT user_id FROM roster_entries WHERE class_id = %s AND user_id IS NOT NULL", klass
        )
    ]

    def add_games(first: int, count: int) -> None:
        """Class games with their summary rows, written straight to the tables: the endpoint
        reads only `game_summaries`, and 100 played games would make the test slow."""
        for number in range(first, first + count):
            game_id = uuid.uuid7()
            # Every other game finished, so «Klassens kostnad» is read for many as for one.
            finished = number % 2 == 0
            execute(
                "INSERT INTO games (id, purpose, lifecycle, version, class_session_id, "
                "game_number) VALUES (%s, 'class', %s, 3, %s, %s)",
                game_id,
                "finished" if finished else "running",
                session_id,
                number,
            )
            # Two Students per game, each game its own pair, and one of them waited for: the
            # names to resolve grow with the games.
            pair = [str(uuid.uuid4()), str(uuid.uuid4())] if number > 10 else students[:2]
            occupants = [
                {"role": role, "occupant_kind": "student", "user_id": str(pair[0])}
                if role == "retailer"
                else {"role": role, "occupant_kind": "student", "user_id": str(pair[1])}
                if role == "factory"
                else {"role": role, "occupant_kind": "rule_based", "user_id": None}
                for role in ("retailer", "wholesaler", "distributor", "factory")
            ]
            waiting = [
                {"role": "factory", "user_id": str(pair[1]), "since": "2026-11-19T09:00:00+00:00"}
            ]
            execute(
                "INSERT INTO game_summaries (game_id, class_session_id, game_number, purpose, "
                "status, week, wait_started_at, waiting_for, occupants, chain_cost, version) "
                "VALUES (%s, %s, %s, 'class', %s, 4, '2026-11-19T09:00:00+00:00', %s, %s, "
                "120.5, 3)",
                game_id,
                session_id,
                number,
                "finished" if finished else "waiting",
                json.dumps(waiting),
                json.dumps(occupants),
            )

    engine = get_engine().sync_engine
    statements: list[str] = []

    def record(conn, cursor, statement, *rest) -> None:
        statements.append(statement)

    # Past the Start date, so «Klassens kostnad» is read (Story 7.6).
    execute(
        "UPDATE class_sessions SET start_at = %s WHERE id = %s",
        "2026-11-01T09:00:00+00:00",
        session_id,
    )
    event.listen(engine, "before_cursor_execute", record)
    try:
        add_games(10, 1)
        progress_service._funnels.clear()
        statements.clear()
        few = await overview(LECTURER, session_id)
        with_few = len(statements)
        add_games(11, 99)
        progress_service._funnels.clear()  # both reads count the Trakt afresh
        statements.clear()
        many = await overview(LECTURER, session_id)
        with_many = len(statements)
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert (few.status_code, many.status_code) == (200, 200)
    assert len(many.json()["items"]) == len(few.json()["items"]) + 99
    assert many.json()["cost"]["games"] == 50
    assert with_many == with_few
