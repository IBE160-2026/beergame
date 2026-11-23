"""The Klasserapport (Story 14.1, FR-64, FR-68, FR-70, FR-79, FR-5, AD-10, AD-12, AD-13, AD-15,
AD-25): `GET /api/class-sessions/{id}/class-report` answers the Class's owners with figures over
the finished Class games, computed in the api from `game_summaries`, the Decision log, the
occupancy rows, the stored facts sets and the plausibility ratings; everyone else gets one 403.
One short Class game (`tests.sessions.test_game_end.short_game`) serves the played tests."""

import json
import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import event

from app.analysis.wall import quartiles
from app.modules.games.views import chain_result
from app.modules.identity.schemas import AccountRole
from app.modules.progress import service as progress_service
from app.modules.reports import class_report, class_report_jobs
from app.platform.db import get_engine
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER, OTHER, make
from tests.classes.test_invitation_counts import execute
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
CHAIN_ORDER = ["retailer", "wholesaler", "distributor", "factory"]


async def report(who: str, session_id: str):
    return await call(who, "GET", f"/api/class-sessions/{session_id}/class-report")


def add_game(session_id: str, number: int, status: str, purpose: str = "class") -> uuid.UUID:
    """A Game with its summary row, written straight to the tables (as the Oversikt's tests do):
    the report reads `game_summaries`, and a played game per row would make the tests slow."""
    game_id = uuid.uuid7()
    execute(
        "INSERT INTO games (id, purpose, lifecycle, version, class_session_id, game_number) "
        "VALUES (%s, %s, %s, 3, %s, %s)",
        game_id,
        purpose,
        "finished" if status == "finished" else "running",
        session_id,
        number if purpose == "class" else None,
    )
    execute(
        "INSERT INTO game_summaries (game_id, class_session_id, game_number, purpose, status, "
        "week, waiting_for, occupants, chain_cost, version) "
        "VALUES (%s, %s, %s, %s, %s, 4, '[]', '[]', %s, 3)",
        game_id,
        session_id,
        number if purpose == "class" else None,
        purpose,
        status,
        Decimal("120.5") if status == "finished" else None,
    )
    return game_id


def fail(lock: str) -> None:
    """The waiting job under `lock` runs and fails, as a worker would mark it (procrastinate
    records the `failed` event on the change from `doing`)."""
    execute(
        "UPDATE procrastinate_jobs SET status = 'doing' "
        "WHERE queueing_lock = %s AND status = 'todo'",
        lock,
    )
    execute(
        "UPDATE procrastinate_jobs SET status = 'failed' "
        "WHERE queueing_lock = %s AND status = 'doing'",
        lock,
    )


def test_the_pure_helpers_round_half_up_and_take_the_middle_of_the_ratings():
    assert class_report.percent(1, 3) == Decimal("33.3")
    assert class_report.percent(2, 3) == Decimal("66.7")
    assert class_report.percent(0, 0) is None
    assert class_report.rating_median({2: 1, 4: 1, 5: 1}) == Decimal(4)
    assert class_report.rating_median({3: 1, 4: 1}) == Decimal("3.5")
    assert class_report.rating_median({}) is None
    spread = class_report.distribution([Decimal("1"), Decimal("2"), Decimal("4"), Decimal("10")])
    assert spread is not None
    assert (spread.lower_quartile, spread.median, spread.upper_quartile) == (
        Decimal("1.75"),
        Decimal("3.00"),
        Decimal("5.50"),
    )
    assert class_report.distribution([]) is None


async def test_no_finished_game_reads_the_trakt_and_no_game_figure(klass):
    session_id, _, _ = await short_game(klass)
    response = await report(LECTURER, session_id)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert (body["games"], body["finished"], body["facts_games"]) == (1, 0, 0)
    assert body["cost"] is None
    assert body["patterns"] == []
    assert [a["distribution"] for a in body["amplification"]] == [None] * 4
    assert body["ai"]["seats"] == 0 and body["ai"]["games"] == []
    assert body["funnel"][0] == {"stage": "registered", "count": 2}
    assert body["session_number"] == 1


async def test_a_finished_game_fills_every_figure_and_its_facts_arrive_by_the_job(klass, emitted):
    session_id, game_id, seated = await short_game(klass)
    await play_weeks(game_id, WEEKS)
    # Its finish deferred the job that stores the facts sets, ids only, one per game.
    [(queue, lock, args)] = rows(
        "SELECT queue_name, queueing_lock, args FROM procrastinate_jobs WHERE task_name = %s "
        "AND args->>'game_id' = %s",
        class_report_jobs.STORE_TASK,
        game_id,
    )
    assert (queue, lock) == ("llm-batch", class_report_jobs.facts_key(game_id))
    assert args == {"game_id": game_id, "class_session_id": session_id}
    # A running Class game, a finished Lecturer test Game and a simulation are in no figure.
    add_game(session_id, 12, "waiting")
    add_game(session_id, 0, "finished", purpose="lecturer_test")

    body = (await report(LECTURER, session_id)).json()
    assert (body["games"], body["finished"], body["facts_games"]) == (2, 1, 0)
    shown = await chain_result(game_id)
    cost = body["cost"]
    chain = shown.chain.total_cost.quantize(Decimal("0.01"))
    assert Decimal(cost["chain"]["median"]) == chain
    assert cost["games"] == [{"number": 1, "chain_cost": str(chain)}]
    assert [r["role"] for r in cost["roles"]] == CHAIN_ORDER
    for role, out in zip(shown.roles, cost["roles"], strict=True):
        assert Decimal(out["holding_cost"]) == role.holding_cost.quantize(Decimal("0.01"))
        assert Decimal(out["backorder_cost"]) == role.backorder_cost.quantize(Decimal("0.01"))
        assert Decimal(out["distribution"]["median"]) == role.total_cost.quantize(Decimal("0.01"))
    # Two Students and two AI players from the start: two Seats played by AI the whole game.
    ai = body["ai"]
    assert (ai["seats"], ai["ai_seats"], ai["whole_game"], ai["ai_percent"]) == (4, 2, 2, "50.0")
    [game] = ai["games"]
    assert game["number"] == 1
    assert game["ordered"] == 4 * (WEEKS - 1)  # the Guided Week is no decision
    assert game["llm"] == 0 and game["llm_percent"] == "0.0"
    # Before the job: no Forsterkning and no «Mønstre».
    assert body["patterns"] == []

    emitted.clear()
    await class_report_jobs.store(game_id, session_id)
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["reports.store_class_facts"]
    assert ("session", session_id) in emitted
    sets = [
        json.loads(payload) if isinstance(payload, str) else payload
        for (payload,) in rows("SELECT payload FROM fact_sets WHERE game_id = %s", game_id)
    ]
    assert len(sets) == 4
    body = (await report(LECTURER, session_id)).json()
    assert body["facts_games"] == 1
    by_role = {r["role"]: r["amplification"] for r in sets[0]["facts"]["chain"]["by_role"]}
    for out in body["amplification"]:
        value = by_role[out["role"]]
        if value is None:
            assert out["distribution"] is None
        else:
            assert Decimal(out["distribution"]["median"]) == Decimal(value).quantize(
                Decimal("0.01")
            )
    expected: dict[str, int] = {}
    for one in sets:
        for occurrence in one["facts"]["seat"]["patterns"]:
            if occurrence["decided_by"] == "student":
                expected[occurrence["pattern"]] = expected.get(occurrence["pattern"], 0) + 1
    assert {p["pattern"]: p["occurrences"] for p in body["patterns"]} == expected
    assert all(p["games"] == 1 and p["name"] for p in body["patterns"])
    # The job delivered again stores nothing new.
    await class_report_jobs.store(game_id, session_id)
    assert len(rows("SELECT id FROM fact_sets WHERE game_id = %s", game_id)) == 4
    # No name and no Student id anywhere in the answer (AD-14).
    text = (await report(LECTURER, session_id)).text
    assert not any(str(user) in text for user in seated)


async def test_switches_and_ratings_read_through_the_one_mapping_with_no_user_id(klass):
    session_id, game_id, _ = await short_game(klass)
    await play_weeks(game_id, WEEKS)
    seat = dict(rows("SELECT role, id FROM seats WHERE game_id = %s", game_id))
    # An LLM player in the Wholesaler Seat the Play guard switched at Week 3, and the cost limit
    # at Week 4 in the Distributor Seat, written straight to the occupancy rows.
    for role, week, kind, reason in (
        ("wholesaler", 2, "llm", "initial"),
        ("wholesaler", 3, "rule_based", "guard_switch"),
        ("distributor", 4, "rule_based", "cost_limit"),
    ):
        execute(
            "INSERT INTO seat_occupancy (id, seat_id, from_week, occupant_kind, reason) "
            "VALUES (%s, %s, %s, %s, %s)",
            uuid.uuid7(),
            seat[role],
            week,
            kind,
            reason,
        )
    raters = [uuid.uuid4() for _ in range(5)]
    replay = add_game(session_id, 0, "finished", purpose="replay")
    test_game = add_game(session_id, 0, "finished", purpose="lecturer_test")
    for game, user, purpose, mode, rating in (
        (game_id, raters[0], "class", "llm", 2),
        (game_id, raters[1], "class", "llm", 5),
        (replay, raters[2], "replay", "llm", 4),
        (replay, raters[3], "replay", "rule_based", 3),
        (test_game, raters[4], "lecturer_test", "llm", 1),
    ):
        execute(
            "INSERT INTO believability_ratings (game_id, user_id, purpose, ai_mode, rating) "
            "VALUES (%s, %s, %s, %s, %s)",
            game,
            user,
            purpose,
            mode,
            rating,
        )
    response = await report(LECTURER, session_id)
    body = response.json()
    assert body["ai"]["switches"] == [
        {"number": 1, "role": "wholesaler", "week": 3, "mark": "guard_switch"},
        {"number": 1, "role": "distributor", "week": 4, "mark": "cost_limit"},
    ]
    assert (body["ai"]["llm_seats"], body["ai"]["guard_switched"]) == (1, 1)
    assert body["ai"]["guard_percent"] == "100.0"
    assert body["ratings"] == [
        {
            "ai_mode": "llm",
            "count": 3,
            "median": "4",
            "values": [
                {"rating": 1, "count": 0},
                {"rating": 2, "count": 1},
                {"rating": 3, "count": 0},
                {"rating": 4, "count": 1},
                {"rating": 5, "count": 1},
            ],
        },
        {
            "ai_mode": "rule_based",
            "count": 1,
            "median": "3",
            "values": [{"rating": r, "count": int(r == 3)} for r in range(1, 6)],
        },
    ]
    assert not any(str(user) in response.text for user in raters)


async def test_a_control_test_class_session_counts_no_game(klass, monkeypatch):
    """A Control test Class session (Story 12.7, AD-27) is never in a report. Its kind never
    changes (a trigger), so the read is told it is one."""
    session_id, game_id, _ = await short_game(klass)
    await play_weeks(game_id, WEEKS)

    async def control_test(class_session_id, *, session=None):
        return class_report.sessions.CONTROL_TEST

    monkeypatch.setattr(class_report.sessions, "kind_of", control_test)
    body = (await report(LECTURER, session_id)).json()
    assert (body["games"], body["finished"], body["cost"], body["ratings"]) == (0, 0, None, [])
    assert body["funnel"][0] == {"stage": "registered", "count": 0}


async def test_only_the_lecturers_of_the_class_read_it_and_the_oversikt_says_so(klass):
    session_id, _ = await confirmed(klass, 2)
    await make(ADMIN, roles=(AccountRole.admin,))
    put_staff(klass, await make(ASSISTANT, roles=()), "assistant")
    refused = [
        await report(ASSISTANT, session_id),  # an Assistant lecturer of the Class
        await report(email(0), session_id),  # a Student of the Class
        await report(OTHER, session_id),  # a Lecturer of another Class
        await report(ADMIN, session_id),  # an Admin not attached to the Class
        await report(LECTURER, str(uuid.uuid7())),  # no such Class session
        await report(LECTURER, "not-an-id"),
    ]
    assert {r.status_code for r in refused} == {403}
    assert len({r.content for r in refused}) == 1
    assert (await report(LECTURER, session_id)).status_code == 200
    overview = f"/api/class-sessions/{session_id}/overview"
    assert (await call(LECTURER, "GET", overview)).json()["class_report"] is True
    assert (await call(ASSISTANT, "GET", overview)).json()["class_report"] is False


async def test_the_report_reads_a_fixed_number_of_queries_whatever_the_number_of_games(klass):
    session_id, _ = await confirmed(klass, 2)
    engine = get_engine().sync_engine
    statements: list[str] = []

    def record(conn, cursor, statement, *rest) -> None:
        statements.append(statement)

    for number in (11, 12):  # the allocation's own games hold the first numbers
        add_game(session_id, number, "finished")
    event.listen(engine, "before_cursor_execute", record)
    try:
        progress_service._funnels.clear()
        statements.clear()
        few = await report(LECTURER, session_id)
        with_few = len(statements)
        for number in range(13, 111):
            add_game(session_id, number, "finished" if number % 2 else "waiting")
        progress_service._funnels.clear()
        statements.clear()
        many = await report(LECTURER, session_id)
        with_many = len(statements)
    finally:
        event.remove(engine, "before_cursor_execute", record)
    assert (few.status_code, many.status_code) == (200, 200)
    assert (few.json()["finished"], many.json()["finished"]) == (2, 51)
    assert many.json()["games"] == few.json()["games"] + 98
    assert with_many == with_few
    spread = quartiles([Decimal("120.5")] * 51)
    assert spread is not None
    assert Decimal(many.json()["cost"]["chain"]["median"]) == spread[1]


async def test_the_sweep_builds_missing_facts_sets_until_the_job_has_failed_three_times(klass):
    """Close-out of Epic 14: a finished Class game whose facts job was lost (or ran before this
    job existed) gets it again from the sweep ten minutes on; a live job is not doubled, and a job
    that failed `MAX_FAILURES` times is not deferred again."""
    session_id, game_id, _ = await short_game(klass)
    await play_weeks(game_id, WEEKS)
    key = class_report_jobs.facts_key(game_id)
    execute("DELETE FROM procrastinate_jobs WHERE queueing_lock = %s", key)
    [(now,)] = rows("SELECT now()")  # database time: the finish is stamped by it (Issue #63)
    item = (game_id, session_id)
    assert item not in await class_report_jobs.due_games(now)
    later = now + class_report_jobs.SWEEP_AFTER + timedelta(minutes=1)
    assert item in await class_report_jobs.due_games(later)
    assert await class_report_jobs.defer_due(item, later) is True
    assert item not in await class_report_jobs.due_games(later)
    for _ in range(class_report_jobs.MAX_FAILURES - 1):
        fail(key)
        assert item in await class_report_jobs.due_games(later)
        assert await class_report_jobs.defer_due(item, later) is True
    fail(key)
    assert item not in await class_report_jobs.due_games(later)
    # Once its sets are stored, nothing is missing.
    execute("DELETE FROM procrastinate_jobs WHERE queueing_lock = %s", key)
    await class_report_jobs.store(game_id, session_id)
    assert item not in await class_report_jobs.due_games(later)
