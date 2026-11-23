"""The stored aggregates and Tverrklasse-statistikk (Story 14.3, FR-65, FR-6, AD-9, AD-10, AD-12,
AD-13, AD-14, AD-27, UX-DR51): `reports.write_aggregate` stores the Klasserapport's measures of a
Class session without any identifier, withheld under 10 Students; the sweep defers its job on
`reports-bulk` only once the test can bring no more answers; retention writes it first; and
`GET /api/class-statistics` reads only the stored rows, so its figures hold after the live rows
are gone. One short Class game (`tests.sessions.test_game_end.short_game`) of two Students."""

import uuid
from datetime import timedelta
from decimal import Decimal

import pytest

from app.modules.ops import retention, sweep
from app.modules.reports import aggregates, cross_class
from app.modules.reports import service as report_service
from app.modules.reports.models import class_aggregate_measures, class_aggregates
from app.platform.db import get_sessionmaker
from tests.classes.test_classes import LECTURER, OTHER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_staff import call, put_staff
from tests.messaging.helpers import rows
from tests.reports.test_class_report import add_game, report
from tests.sessions.test_dates import DAY, TEST, new_session
from tests.sessions.test_game_end import (
    WEEKS,
    _empty,
    clock,
    emitted,
    klass,
    play_weeks,
    short_game,
)
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass"]

AFTER = TEST + DAY
"""A day after the Class session's Test deadline (`tests.sessions.test_dates.PLAN`)."""


@pytest.fixture
def small_groups(monkeypatch):
    """The anonymisation threshold at 2, so the two-Student game's figures are stored."""
    monkeypatch.setattr(aggregates, "MIN_GROUP", 2)


async def played(klass) -> str:
    session_id, game_id, _ = await short_game(klass)
    await play_weeks(game_id, WEEKS)
    return session_id


def stored(session_id: str) -> dict[str, tuple[int, Decimal | None, bool]]:
    return {
        measure: (group, value, withheld)
        for measure, group, value, withheld in rows(
            "SELECT measure, group_size, value, withheld FROM class_aggregate_measures "
            "WHERE class_session_id = %s",
            session_id,
        )
    }


def header(session_id: str) -> tuple | None:
    found = rows(
        "SELECT written_at, students, game_students, games_finished, keys FROM class_aggregates "
        "WHERE class_session_id = %s",
        session_id,
    )
    return found[0] if found else None


async def statistics(who: str = LECTURER):
    return await call(who, "GET", "/api/class-statistics")


def test_the_tables_hold_no_identifier():
    names = {c.name for c in class_aggregates.columns} | {
        c.name for c in class_aggregate_measures.columns
    }
    assert not names & {"user_id", "seat_id", "game_id", "name", "email", "text"}


async def test_a_group_under_ten_is_stored_withheld_with_no_value(klass):
    session_id = await played(klass)
    assert await report_service.write_aggregate(uuid.UUID(session_id)) is True
    found = stored(session_id)
    group, value, withheld = found[aggregates.CHAIN_MEDIAN]
    assert (group, value, withheld) == (2, None, True)
    assert found["funnel.registered"] == (2, None, True)
    assert all(withheld for _, _, withheld in found.values())
    written_at, students, game_students, finished, keys = header(session_id)
    assert (students, game_students, finished) == (2, 2, 1)
    # The keys a comparison holds equal, the demand seed left out (each session draws its own).
    assert keys["ai_mode"] == "rule_based" and "demand_seed" not in keys["game_settings"]
    assert keys["game_settings"]["weeks"] == WEEKS
    assert "question_set_version" in keys and "scoring_guide" in keys


async def test_a_group_of_enough_students_stores_the_klasserapports_figures(klass, small_groups):
    session_id = await played(klass)
    shown = (await report(LECTURER, session_id)).json()
    await aggregates.write_aggregate(uuid.UUID(session_id))
    found = stored(session_id)
    assert found[aggregates.CHAIN_MEDIAN] == (2, Decimal(shown["cost"]["chain"]["median"]), False)
    for role in shown["cost"]["roles"]:
        assert found[f"cost.{role['role']}.median"][1] == Decimal(role["distribution"]["median"])
    assert found["ai.seats_percent"][1] == Decimal(shown["ai"]["ai_percent"])
    assert found["funnel.registered"] == (2, Decimal(2), False)
    # No Student, Seat or Game id is in any stored code or value.
    ids = {r[0] for r in rows("SELECT id::text FROM games WHERE class_session_id = %s", session_id)}
    ids |= {r[0] for r in rows("SELECT id::text FROM seats")}
    assert not any(any(i in measure for i in ids) for measure in found)
    # A second write replaces the rows: no duplicate, the same figures.
    await aggregates.write_aggregate(uuid.UUID(session_id))
    assert stored(session_id) == found


async def test_no_aggregate_is_due_while_the_test_can_still_bring_answers(klass):
    session_id, game_id, seated = await short_game(klass)
    await play_weeks(game_id, WEEKS)
    key = uuid.UUID(session_id)
    # Before the Test deadline, whether nobody opened the test or some handed in early.
    assert key not in await aggregates.due_sessions(TEST - DAY)
    # A Student's own Test deadline ahead keeps it open (Story 13.9's latest effective deadline).
    student = seated[0]
    execute(
        "INSERT INTO student_deadline_extensions (class_session_id, user_id, test_deadline, "
        "updated_at) VALUES (%s, %s, %s, %s)",
        session_id,
        student,
        TEST + 3 * DAY,
        TEST,
    )
    assert key not in await aggregates.due_sessions(AFTER)
    assert key in await aggregates.due_sessions(TEST + 4 * DAY)


async def test_an_open_attempt_keeps_it_back(klass, monkeypatch):
    session_id = await played(klass)
    key = uuid.UUID(session_id)

    async def open_(s, ids):
        return {key}

    monkeypatch.setattr(aggregates.tests, "sessions_with_open_attempts", open_)
    assert key not in await aggregates.due_sessions(AFTER)


async def test_after_the_deadline_one_job_on_reports_bulk_then_written_once(klass):
    session_id = await played(klass)
    key = uuid.UUID(session_id)
    assert key in await aggregates.due_sessions(AFTER)
    assert await aggregates.defer_due(key, AFTER) is True
    [(queue, lock, args)] = rows(
        "SELECT queue_name, queueing_lock, args FROM procrastinate_jobs WHERE task_name = %s "
        "AND args->>'class_session_id' = %s",
        aggregates.WRITE_TASK,
        session_id,
    )
    assert (queue, lock, args) == (
        "reports-bulk",
        aggregates.aggregate_key(session_id),
        {"class_session_id": session_id},
    )
    # A live job keeps the finder from deferring another.
    assert key not in await aggregates.due_sessions(AFTER)
    execute("DELETE FROM procrastinate_jobs WHERE queueing_lock = %s", lock)
    await aggregates.write_class_aggregate(session_id)
    # The AI assessment is off: written once, never again.
    assert key not in await aggregates.due_sessions(AFTER + DAY)


async def test_a_later_ai_assessment_makes_it_due_again(klass, monkeypatch):
    session_id = await played(klass)
    key = uuid.UUID(session_id)
    await aggregates.write_aggregate(key)
    written_at = header(session_id)[0]

    async def latest(s, ids):
        return {key: written_at + timedelta(seconds=1)}

    monkeypatch.setattr(aggregates.assessment, "latest_updates", latest)
    assert key in await aggregates.due_sessions(AFTER)


async def test_the_sweep_runs_the_due_action_last(klass):
    names = [action.name for action in sweep.DUE_ACTIONS]
    assert names[-1] == "reports.write_aggregate"


async def test_a_control_test_or_a_deleted_session_gets_none(klass, monkeypatch):
    session_id = await played(klass)
    key = uuid.UUID(session_id)
    execute("UPDATE class_sessions SET data_deleted_at = %s WHERE id = %s", AFTER, session_id)
    assert await aggregates.write_aggregate(key) is False
    assert key not in await aggregates.due_sessions(AFTER)
    execute("UPDATE class_sessions SET data_deleted_at = NULL WHERE id = %s", session_id)

    # A Control test Class session (`kind` is fixed at creation, so the scope's read stands in).
    async def control_test(s, class_session_id):
        return False

    monkeypatch.setattr(aggregates.scope, "is_reporting_session", control_test)
    assert await aggregates.write_aggregate(key) is False
    assert await aggregates.ensure_aggregate(key) is None
    assert header(session_id) is None


async def test_the_page_reads_only_the_aggregates(klass, small_groups):
    session_id = await played(klass)
    later = await new_session(klass)
    body = (await statistics()).json()
    # Two Class sessions, neither ready: listed, nothing compared.
    assert [s["class_session_id"] for s in body["sessions"]] == [session_id, later]
    assert [s["session_number"] for s in body["sessions"]] == [1, 2]
    assert all(s["written_at"] is None for s in body["sessions"]) and body["measures"] == []
    await aggregates.write_aggregate(uuid.UUID(session_id))
    before = (await statistics()).json()
    assert [m["key"] for m in before["measures"]] == [key for key, _ in cross_class.SHOWN]
    chain = before["measures"][0]
    assert [v["class_session_id"] for v in chain["values"]] == [session_id]
    assert chain["values"][0]["withheld"] is False and chain["values"][0]["value"] is not None
    # The live rows go; the comparison does not move.
    execute("DELETE FROM game_summaries WHERE class_session_id = %s", session_id)
    execute("DELETE FROM roster_entries WHERE class_id = %s", klass)
    after = (await statistics()).json()
    assert after == before


async def test_only_the_lecturers_own_classes_are_listed(klass):
    session_id = await played(klass)
    assert [s["class_session_id"] for s in (await statistics()).json()["sessions"]] == [session_id]
    # Another Lecturer sees none of it; a Student is refused.
    assert (await statistics(OTHER)).json()["sessions"] == []
    assert (await statistics(email(0))).status_code == 403
    # An archived Class is still listed.
    execute("UPDATE classes SET archived_at = %s WHERE id = %s", AFTER, klass)
    [listed] = (await statistics()).json()["sessions"]
    assert listed["archived"] is True


async def test_retention_writes_the_aggregate_first_and_the_figures_hold(klass, small_groups):
    session_id = await played(klass)
    key = uuid.UUID(session_id)
    execute("UPDATE class_sessions SET deletion_date = %s WHERE id = %s", AFTER.date(), session_id)
    assert header(session_id) is None
    run = await retention.retain(key, AFTER + DAY)
    assert run.outcome == "deleted"
    first = header(session_id)
    assert first is not None and stored(session_id)[aggregates.CHAIN_MEDIAN][2] is False
    figures = (await statistics()).json()["measures"]
    # A rerun keeps the aggregate it finds; the sweep never writes after the deletion.
    await aggregates.ensure_aggregate(key)
    assert header(session_id) == first
    assert key not in await aggregates.due_sessions(AFTER + 2 * DAY)
    assert (await statistics()).json()["measures"] == figures


async def test_fjoraret_is_the_previous_sessions_stored_median(klass, small_groups):
    session_id = await played(klass)
    later = await new_session(klass)
    add_game(later, 1, "finished")
    async with get_sessionmaker()() as s:
        assert await aggregates.previous_median(s, uuid.UUID(later)) is None
    await aggregates.write_aggregate(uuid.UUID(session_id))
    median = stored(session_id)[aggregates.CHAIN_MEDIAN][1]
    async with get_sessionmaker()() as s:
        assert await aggregates.previous_median(s, uuid.UUID(later)) == median
        assert await aggregates.previous_median(s, uuid.UUID(session_id)) is None
    cost = (await report(LECTURER, later)).json()["cost"]
    assert Decimal(cost["previous_median"]) == median


async def test_a_withheld_previous_median_draws_no_mark(klass):
    session_id = await played(klass)
    later = await new_session(klass)
    await aggregates.write_aggregate(uuid.UUID(session_id))
    async with get_sessionmaker()() as s:
        assert await aggregates.previous_median(s, uuid.UUID(later)) is None


async def test_the_reads_of_open_attempts_and_assessments_are_real(klass):
    """`tests.sessions_with_open_attempts` and `assessment.latest_updates` over the stored rows:
    an open attempt holds the aggregate back; an assessment changed after it makes it due."""
    session_id, game_id, seated = await short_game(klass)
    await play_weeks(game_id, WEEKS)
    key = uuid.UUID(session_id)
    attempt = uuid.uuid7()
    execute(
        "INSERT INTO test_attempts (id, user_id, class_session_id, question_set_version, "
        "selection, items, statement_accepted_at) VALUES (%s, %s, %s, 1, '{}', '[]', %s)",
        attempt,
        seated[0],
        session_id,
        TEST - DAY,
    )
    assert key not in await aggregates.due_sessions(AFTER)
    execute(
        "UPDATE test_attempts SET status = 'submitted', submitted_at = %s, closed_at = %s "
        "WHERE id = %s",
        TEST,
        TEST,
        attempt,
    )
    assert key in await aggregates.due_sessions(AFTER)
    await aggregates.write_aggregate(key)
    assert key not in await aggregates.due_sessions(AFTER)
    written_at = header(session_id)[0]
    execute(
        "INSERT INTO ai_assessments (id, attempt_id, class_session_id, user_id, status, "
        "question_set_version, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, 'ready', 1, %s, %s)",
        uuid.uuid7(),
        attempt,
        session_id,
        seated[0],
        written_at,
        written_at + timedelta(minutes=5),
    )
    assert key in await aggregates.due_sessions(AFTER)


async def test_an_assistant_with_the_lecturer_role_sees_none_of_the_class(klass):
    """The route admits the Lecturer role; the owner-only Class action keeps an Assistant out."""
    session_id = await played(klass)
    put_staff(klass, await make("assistent-faglaerer@x.no"), "assistant")
    assert (await statistics("assistent-faglaerer@x.no")).json()["sessions"] == []
    assert [s["class_session_id"] for s in (await statistics()).json()["sessions"]] == [session_id]


async def test_no_job_writes_once_the_deletion_date_has_come(klass):
    """From the deletion date on, retention owns the Class session: the sweep finds it no more,
    and a job queued before then writes nothing; retention's own gate still writes one."""
    session_id = await played(klass)
    key = uuid.UUID(session_id)
    assert key in await aggregates.due_sessions(AFTER)
    execute("UPDATE class_sessions SET deletion_date = %s WHERE id = %s", AFTER.date(), session_id)
    assert key not in await aggregates.due_sessions(AFTER)
    assert await aggregates.write_aggregate(key, now=AFTER) is False
    assert header(session_id) is None
    assert await aggregates.write_aggregate(key, now=AFTER, for_retention=True) is True


async def test_retentions_gate_keeps_an_aggregate_it_finds(klass, small_groups):
    """An interrupted retention (Students partly erased, `data_deleted_at` still NULL) reruns the
    gate: the aggregate written before stays as it was."""
    session_id = await played(klass)
    key = uuid.UUID(session_id)
    await aggregates.write_aggregate(key)
    first, rows_before = header(session_id), stored(session_id)
    execute("DELETE FROM roster_entries WHERE class_id = %s", klass)
    execute("DELETE FROM game_summaries WHERE class_session_id = %s", session_id)
    await aggregates.ensure_aggregate(key)
    assert header(session_id) == first
    assert stored(session_id) == rows_before


def test_each_measure_family_is_withheld_by_its_own_group():
    """`measures` (pure): the learning measures over the registered Students, a computed question
    over the Students whose test held it (an AI-scored one is not stored), the Core-only subscore
    over the ready assessments (never the total), the ratings over the Students who rated."""
    from app.modules.reports.class_report import ReportParts
    from app.modules.reports.class_report_learning_schemas import (
        AdaptedPartOut,
        ClassLearningOut,
        LearningAiOut,
        LearningStartingTaskOut,
        QuestionResultOut,
    )
    from app.modules.reports.class_report_schemas import (
        DistributionOut,
        RatingModeOut,
        ReportAiOut,
    )
    from app.modules.sessions.service import FunnelStageOut

    spread = DistributionOut(
        values=[], median=Decimal(70), lower_quartile=Decimal(60), upper_quartile=Decimal(80)
    )
    question = dict(
        title="t",
        weight=10,
        excluded=False,
        answered=9,
        right=5,
        partly=2,
        wrong=2,
        not_answered=0,
    )
    report = ReportParts(
        games=0,
        finished=0,
        facts_games=0,
        funnel=[FunnelStageOut(stage="registered", count=12)],
        cost=None,
        amplification=[],
        patterns=[],
        ai=ReportAiOut(
            seats=0,
            ai_seats=0,
            whole_game=0,
            ai_percent=None,
            games=[],
            switches=[],
            llm_seats=0,
            guard_switched=0,
            guard_percent=None,
        ),
        ratings=[RatingModeOut(ai_mode="llm", count=12, median=Decimal(4), values=[])],
        game_ids=(),
    )
    learning = ClassLearningOut(
        class_session_id=uuid.uuid7(),
        students=12,
        submitted=11,
        still_to_submit=0,
        starting_task=LearningStartingTaskOut(students=0, items=[]),
        questions=[
            QuestionResultOut(
                number=1,
                id="q1",
                type="choice",
                scoring="computed",
                students=11,
                percent=Decimal("62.5"),
                **question,
            ),
            QuestionResultOut(
                number=2,
                id="q2",
                type="long",
                scoring="ai",
                students=11,
                percent=None,
                **question,
            ),
        ],
        adapted=AdaptedPartOut(weight=0, adapted=0, replaced=0),
        ai=LearningAiOut(state="ready", ready=9, submitted=11, total=spread, core=spread, bands=[]),
    )
    found = {
        m.measure: (m.group_size, m.value)
        for m in aggregates.measures(report, learning, game_students=0, rating_students={"llm": 3})
    }
    assert found["learning.submitted_percent"] == (12, Decimal("91.7"))
    assert found["question.q1.percent"] == (11, Decimal("62.5"))
    assert "question.q2.percent" not in found
    assert found["core.median"] == (9, Decimal(70))  # 9 ready: withheld when written
    assert not any(code.startswith("total") for code in found)
    assert found["rating.llm.median"] == (3, Decimal(4))  # 12 ratings from 3 Students
    assert "chain.median" not in found and "ai.seats_percent" not in found


async def test_the_oversikt_draws_fjoraret_from_the_previous_sessions_aggregate(klass):
    """The Oversikt's Kostnadsfordeling (Story 7.6) carries the previous Class session's stored
    median, and nothing while that one is withheld."""
    earlier = str(uuid.uuid7())  # an id from before the played Class session's: the one before
    session_id = await played(klass)
    execute(
        "INSERT INTO class_sessions SELECT (jsonb_populate_record(NULL::class_sessions, "
        "to_jsonb(c) || jsonb_build_object('id', %s::text))).* FROM class_sessions c "
        "WHERE id = %s",
        earlier,
        session_id,
    )
    execute(
        "INSERT INTO class_aggregates (class_session_id, written_at, students, game_students, "
        "games_finished, keys, institution_id) VALUES (%s, %s, 12, 12, 3, '{}', "
        "(SELECT c.institution_id FROM class_sessions s JOIN classes c ON c.id = s.class_id "
        "WHERE s.id = %s))",
        earlier,
        TEST,
        earlier,
    )
    execute(
        "INSERT INTO class_aggregate_measures (class_session_id, measure, group_size, value, "
        "withheld) VALUES (%s, 'chain.median', 12, 2740, false)",
        earlier,
    )
    overview = f"/api/class-sessions/{session_id}/overview"
    cost = (await call(LECTURER, "GET", overview)).json()["cost"]
    assert Decimal(cost["previous_median"]) == Decimal(2740)
    execute(
        "UPDATE class_aggregate_measures SET value = NULL, withheld = true, group_size = 9 "
        "WHERE class_session_id = %s",
        earlier,
    )
    assert (await call(LECTURER, "GET", overview)).json()["cost"]["previous_median"] is None


async def test_a_late_rating_makes_it_due_again_by_database_time(klass):
    """Close-out of Epic 14: the aggregate is stamped in database time, and a plausibility rating
    (or a finished game or a stored facts set) after it makes it due again."""
    session_id, game_id, seated = await short_game(klass)
    await play_weeks(game_id, WEEKS)
    key = uuid.UUID(session_id)
    await aggregates.write_aggregate(key)
    assert key not in await aggregates.due_sessions(AFTER)
    execute(
        "INSERT INTO believability_ratings (game_id, user_id, purpose, ai_mode, rating) "
        "VALUES (%s, %s, 'class', 'rule_based', 4)",
        game_id,
        seated[0],
    )
    assert key in await aggregates.due_sessions(AFTER)
    await aggregates.write_aggregate(key)
    assert key not in await aggregates.due_sessions(AFTER)


async def test_a_job_that_failed_three_times_is_not_deferred_again(klass):
    session_id = await played(klass)
    key = uuid.UUID(session_id)
    lock = aggregates.aggregate_key(session_id)
    for _ in range(aggregates.MAX_FAILURES):
        assert key in await aggregates.due_sessions(AFTER)
        assert await aggregates.defer_due(key, AFTER) is True
        execute("UPDATE procrastinate_jobs SET status = 'failed' WHERE queueing_lock = %s", lock)
    assert key not in await aggregates.due_sessions(AFTER)
