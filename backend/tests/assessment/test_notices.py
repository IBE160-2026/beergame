"""Be told when the AI assessment is ready (Story 12.4, FR-18, FR-54, FR-55, FR-61, FR-69, NFR-8,
AD-8, AD-9, AD-16, AD-19).

The run of `assessment.assess` that marks an assessment `ready` records the `assessment_ready`
step and enqueues the Student's `assessment_ready` digest notice in its own transaction; the run
that marks one `failed` tells each active Admin once per Class session. `schedule` creates the
assessment row at the close, so the sweep's `assessment.overdue` action finds every assessment
still not ready 24 hours after its attempt's `effective_deadline`, logs it once and defers its job
again when none is alive. `stop_for_session` and `resume_for_session` stop and restart the
assessment of a Class session. The provider is the mock; the api's clock is fixed and moved by
hand, and the database clock is never compared with it."""

import uuid
from datetime import timedelta
from decimal import Decimal

import psycopg
import pytest
from structlog.testing import capture_logs

from app.ai import budget as ai_budget
from app.ai import gateway, seed
from app.modules.assessment import service as assessment
from app.modules.identity import service as identity
from app.modules.identity.schemas import AccountRole
from app.modules.messaging import delivery
from app.modules.messaging import service as messaging
from app.modules.ops import sweep
from app.modules.sessions import service as sessions
from app.modules.tests import commands
from app.platform import jobs
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker
from app.platform.events.registry import COMMAND_TOPICS
from tests.assessment.test_assess import (
    ANSWER,
    LONG,
    adapted_session,
    answer_all,
    assess_jobs,
    assessments,
    attempt_id_of,
    calls,
    closed,
    view,
)
from tests.classes.test_classes import make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import call
from tests.classes.test_student_registration import emitted
from tests.debrief.test_explanation import user_id
from tests.individual_test.test_adapted import locked_with, stand_in
from tests.individual_test.test_answer import put
from tests.individual_test.test_extension import extend
from tests.individual_test.test_open import path
from tests.messaging.helpers import drain, enqueue, mails, rows
from tests.sessions.test_dates import TEST, at
from tests.sessions.test_lock import MINUTE, _empty
from tests.sessions.test_student_choice import email
from tests.sessions.test_student_home import home

__all__ = ["_empty", "clock", "emitted", "klass"]

HOUR = timedelta(hours=1)
DAY = timedelta(days=1)
LATE = TEST + 24 * HOUR
"""The 24-hour target after the Test deadline (`assessment_overdue_hours`)."""


@pytest.fixture(autouse=True)
def _settings():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def notices(kind: str) -> list[tuple]:
    return rows(
        "SELECT user_id, dedupe_key, ref::text FROM notices WHERE kind = %s ORDER BY id", kind
    )


def steps(session_id: str) -> list[tuple]:
    return rows(
        "SELECT user_id, at FROM progress_steps WHERE class_session_id = %s "
        "AND step = 'assessment_ready'",
        session_id,
    )


def row_of(attempt_id) -> tuple:
    [found] = rows(
        "SELECT status, runs, due_at, overdue_at, updated_at, reason FROM ai_assessments "
        "WHERE attempt_id = %s",
        attempt_id,
    )
    return found


def audits(action: str) -> list[tuple]:
    return rows(
        "SELECT actor_user_id, target_ids, change FROM audit_events WHERE action = %s ORDER BY id",
        action,
    )


def failing(monkeypatch) -> list[int]:
    """Every `assessment` call raises a `GatewayError`; the list counts the calls."""
    made: list[int] = []

    async def refuse(*args, **kwargs):
        made.append(1)
        raise gateway.GatewayError("provider_key_missing", "no key here")

    monkeypatch.setattr(gateway, "run", refuse)
    return made


async def mail_digests(now) -> None:
    """The sweep's first due action at `now` (claim due notices into mails), then the mail jobs."""
    for item in await messaging.due_items(now):
        await messaging.claim(item, now)
    await drain(now)


async def ready_session(klass, monkeypatch) -> tuple[str, uuid.UUID]:
    session_id, test = await adapted_session(klass, monkeypatch)
    await answer_all(session_id, test)
    await closed(session_id)
    return session_id, attempt_id_of(session_id)


# Ready: the step and the notice in the run's transaction.


async def test_the_ready_run_records_the_step_and_one_notice_and_a_repeat_none(
    klass, monkeypatch, emitted
):
    session_id, attempt_id = await ready_session(klass, monkeypatch)
    student = user_id(email(0))
    # The close made the row (no run yet, due at the attempt's deadline) and deferred the job.
    assert row_of(attempt_id)[:3] == ("incomplete", 0, TEST)
    assert (await view(session_id, monkeypatch)).json()["state"] == "not_ready"
    report = next(s for s in (await home(email(0)))["steps"] if s["step"] == "report")
    assert report["state"] != "done"

    emitted.clear()
    at(monkeypatch, TEST + HOUR)
    assert await assessment.assess(attempt_id) == "ready"
    [(who, when)] = steps(session_id)
    assert who == student
    assert notices("assessment_ready") == [(student, f"assessment_ready:{attempt_id}", session_id)]
    assert {("user", str(student)), ("session", session_id)} == set(emitted)
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["assessment.assess"]
    # Hjem's last step, «Rapport», is done; the view is ready.
    report = next(s for s in (await home(email(0)))["steps"] if s["step"] == "report")
    assert report["state"] == "done"
    assert (await view(session_id, monkeypatch)).json()["state"] == "ready"

    # A repeat run: no second step, no second notice.
    assert await assessment.assess(attempt_id) == "ready"
    assert len(steps(session_id)) == 1 and len(notices("assessment_ready")) == 1
    assert steps(session_id)[0][1] == when


async def test_the_step_and_the_notice_commit_with_the_ready_state_or_not_at_all(
    klass, monkeypatch
):
    session_id, attempt_id = await ready_session(klass, monkeypatch)

    async def broken(*args, **kwargs):
        raise RuntimeError("notices are down")

    monkeypatch.setattr(assessment.notify, "enqueue", broken)
    with pytest.raises(RuntimeError):
        await assessment.assess(attempt_id)
    assert row_of(attempt_id)[:2] == ("incomplete", 0)
    assert steps(session_id) == [] and notices("assessment_ready") == []


async def test_the_mail_is_a_digest_that_says_ai_generated_no_grade_and_holds_no_score(
    klass, monkeypatch
):
    session_id, attempt_id = await ready_session(klass, monkeypatch)
    assert delivery.KINDS[assessment.READY_NOTICE].mode == delivery.DIGEST
    assert delivery.KINDS[assessment.FAILED_NOTICE].mode == delivery.DIGEST
    assert delivery.ASSESSMENT_READY_KIND == assessment.READY_NOTICE
    assert delivery.ASSESSMENT_FAILED_KIND == assessment.FAILED_NOTICE
    await assessment.assess(attempt_id)
    # 22:30 in Oslo: a digest is never claimed between 22:00 and 07:00.
    night = TEST.replace(hour=21, minute=30)
    await mail_digests(night)
    assert mails() == []
    morning = TEST.replace(hour=6) + DAY  # 07:00 in Oslo
    await mail_digests(morning)
    # (The allocation's digest of an earlier day goes out this morning as well.)
    [mail] = [each for each in mails() if "KI-vurdering" in each.text]
    assert mail.to == email(0)
    for line in ("KI-generert og kan ta feil", "teller ikke", "ingen karakter"):
        assert line in mail.text and line in mail.html
    assert "KI-vurderingen av den individuelle testen din i Klassen" in mail.text
    # No score, no letter, no feedback text: nothing of the answer or the scale.
    for banned in ("av 4", "Utkast", "poeng", "karakter A", ANSWER[:20], "Veiledende"):
        assert banned not in mail.text and banned not in mail.html
    section = mail.text.split("KI-vurderingen av")[1].split("\n")[0]
    assert not any(char.isdigit() for char in section.replace("class-of-1994", ""))
    # At most one digest per User per day: a second ready notice today waits for tomorrow.
    assert await enqueue(user_id(email(0)), assessment.READY_NOTICE, ref=uuid.UUID(session_id))
    await mail_digests(morning + HOUR)
    assert len([each for each in mails() if "KI-vurdering" in each.text]) == 1


# Failed: one notice per Admin per Class session.


async def test_a_failed_assessment_tells_each_admin_once_per_class_session(klass, monkeypatch):
    monkeypatch.setenv("ASSESSMENT_MAX_RUNS", "1")
    get_settings.cache_clear()
    await make("admin1@example.com", (AccountRole.admin,))
    await make("admin2@example.com", (AccountRole.admin,))
    await seed.ensure_zero_config()
    stand_in(monkeypatch, own=range(1, 13))
    session_id, seated = await locked_with(klass, 30, n=2)
    for who in (0, 1):
        opened = await call_open(session_id, who)
        assert opened.status_code == 201
    await answer_both(session_id, monkeypatch)
    assert await sessions.lock_test(uuid.UUID(session_id), now=TEST + MINUTE)
    for each in await commands.due_closes(TEST + MINUTE):
        assert await commands.close_attempt(each, TEST + MINUTE)
    made = failing(monkeypatch)
    attempts = [row[1] for row in assessments()]
    assert len(attempts) == 2
    assert await assessment.assess(attempts[0]) == "failed"
    async with get_sessionmaker()() as s:
        admins = await identity.active_admins(s)
    assert len(admins) >= 2
    told = notices("assessment_failed")
    assert sorted(told) == sorted(
        (admin, f"assessment_failed:{session_id}:{admin}", session_id) for admin in admins
    )
    # The second failed assessment of the same Class session tells no one again.
    assert await assessment.assess(attempts[1]) == "failed"
    assert len(notices("assessment_failed")) == len(admins) and made
    assert notices("assessment_ready") == []
    # The Admin's mail names the Class and the Class session, nothing of a Student.
    await mail_digests(TEST + HOUR)
    sent = {mail.to: mail for mail in mails()}
    mail = sent["admin1@example.com"]
    assert "kunne ikke lages" in mail.text and "Klasseøkt" in mail.text
    assert email(0) not in mail.text and email(1) not in mail.text


async def call_open(session_id: str, who: int):
    return await call(email(who), "POST", path(session_id))


async def answer_both(session_id: str, monkeypatch) -> None:
    """Each Student writes the first long answer only; every other item is left empty."""
    for who in (0, 1):
        at(monkeypatch, NOW + HOUR)
        response = await put(session_id, LONG[0], f"{ANSWER} ({who})", 1, who=email(who))
        assert response.status_code == 200, response.text


# The close, and an extended Student.


async def test_an_extended_student_is_assessed_after_their_own_deadline_with_the_pinned_guide(
    klass, monkeypatch
):
    await seed.ensure_zero_config()
    stand_in(monkeypatch, own=range(1, 13))
    session_id, seated = await locked_with(klass, 30, n=2)
    for who in (0, 1):
        assert (await call_open(session_id, who)).status_code == 201
    own = TEST + 3 * DAY
    at(monkeypatch, NOW + HOUR)
    assert (await extend(session_id, seated[1], own)).status_code == 200
    # The original Test deadline: the lock pins the guide; only the other Student is closed and
    # assessed, without waiting.
    assert await sessions.lock_test(uuid.UUID(session_id), now=TEST + MINUTE)
    due = await commands.due_closes(TEST + MINUTE)
    assert len(due) == 1
    assert await commands.close_attempt(due[0], TEST + MINUTE)
    [(_, attempt, student, *_)] = assessments()
    assert student == seated[0]
    assert len(assess_jobs()) == 1
    assert await assessment.assess(attempt) == "ready"
    # Their own deadline: closed and assessed then, with the guide pinned at the original one.
    assert await commands.due_closes(own - MINUTE) == []
    [late] = await commands.due_closes(own + MINUTE)
    assert await commands.close_attempt(late, own + MINUTE)
    found = {row[2]: row for row in assessments()}
    assert set(found) == set(seated)
    assert rows("SELECT due_at FROM ai_assessments WHERE attempt_id = %s", late) == [(own,)]
    assert await assessment.assess(late) == "ready"
    [(pinned,)] = rows(
        "SELECT scoring_guide_id FROM test_scoring_guides WHERE class_session_id = %s", session_id
    )
    guides = rows("SELECT scoring_guide_id FROM ai_assessments ORDER BY created_at")
    assert guides == [(pinned,), (pinned,)]


# The sweep's overdue action.


async def test_an_overdue_assessment_is_logged_once_and_its_lost_job_deferred_again(
    klass, monkeypatch
):
    session_id, attempt_id = await ready_session(klass, monkeypatch)
    assert "assessment.overdue" in [action.name for action in sweep.DUE_ACTIONS]
    names = [action.name for action in sweep.DUE_ACTIONS]
    assert names.index("assessment.overdue") == names.index("tests.close_attempt") + 1
    # Before the 24-hour target: nothing is due.
    assert await assessment.due_overdue(LATE - MINUTE) == []
    # Past it, with the job still waiting: logged once, nothing deferred.
    assert await assessment.due_overdue(LATE + MINUTE) == [attempt_id]
    with capture_logs() as logs:
        assert await assessment.overdue_due(attempt_id, LATE + MINUTE) is False
    overdue = [entry for entry in logs if entry["event"] == "assessment_overdue"]
    assert len(overdue) == 1
    assert set(overdue[0]) >= {"attempt_id", "assessment_id", "class_session_id"}
    assert ANSWER[:10] not in str(overdue[0])
    assert row_of(attempt_id)[3] == LATE + MINUTE
    assert len(assess_jobs()) == 1
    # The look is stamped: the finder leaves it alone for `assessment_retry_minutes`.
    assert await assessment.due_overdue(LATE + 2 * MINUTE) == []
    # The job is lost (a crash before any run): the next look defers it again, as a run.
    execute("DELETE FROM procrastinate_jobs WHERE task_name = %s", assessment.ASSESS_TASK)
    again = LATE + 32 * MINUTE
    with capture_logs() as logs:
        assert await assessment.due_overdue(again) == [attempt_id]
        assert await assessment.overdue_due(attempt_id, again) is True
    assert [e for e in logs if e["event"] == "assessment_overdue"] == []
    assert row_of(attempt_id)[1] == 1
    [(queue, lock, args, _, status)] = assess_jobs()
    assert (queue, lock, args, status) == (
        "llm-batch",
        f"assessment:{attempt_id}",
        {"attempt_id": str(attempt_id)},
        "todo",
    )
    # Not again for `assessment_retry_minutes`; then only while no job is alive.
    assert await assessment.due_overdue(again + MINUTE) == []
    later = again + 40 * MINUTE
    assert await assessment.due_overdue(later) == [attempt_id]
    assert await assessment.overdue_due(attempt_id, later) is False
    assert len(assess_jobs()) == 1
    # The run makes it ready; then nothing is due.
    assert await assessment.assess(attempt_id) == "ready"
    assert await assessment.due_overdue(LATE + DAY) == []


async def test_a_job_that_keeps_getting_lost_is_deferred_again_at_most_its_runs(klass, monkeypatch):
    monkeypatch.setenv("ASSESSMENT_MAX_RUNS", "2")
    get_settings.cache_clear()
    _, attempt_id = await ready_session(klass, monkeypatch)
    deferred = []
    for look in range(4):
        execute("DELETE FROM procrastinate_jobs WHERE task_name = %s", assessment.ASSESS_TASK)
        now = LATE + (1 + 40 * look) * MINUTE
        found = await assessment.due_overdue(now)
        deferred.append(bool(found) and await assessment.overdue_due(attempt_id, now))
    assert deferred == [True, True, False, False]
    assert row_of(attempt_id)[:2] == ("incomplete", 2) and assess_jobs() == []


async def test_the_overdue_action_skips_a_stopped_session_and_one_without_runs_left(
    klass, monkeypatch
):
    monkeypatch.setenv("ASSESSMENT_MAX_RUNS", "2")
    get_settings.cache_clear()
    session_id, attempt_id = await ready_session(klass, monkeypatch)
    execute("DELETE FROM procrastinate_jobs WHERE task_name = %s", assessment.ASSESS_TASK)
    assert await assessment.stop_for_session(uuid.UUID(session_id), None, now=LATE)
    assert await assessment.due_overdue(LATE + MINUTE) == []
    assert await assessment.overdue_due(attempt_id, LATE + MINUTE) is False
    assert await assessment.resume_for_session(uuid.UUID(session_id), None, now=LATE) == 1
    execute("DELETE FROM procrastinate_jobs WHERE task_name = %s", assessment.ASSESS_TASK)
    # Runs used up but still `incomplete` (a row left behind): logged, never deferred again.
    execute(
        "UPDATE ai_assessments SET runs = 2, overdue_at = %s, updated_at = %s "
        "WHERE attempt_id = %s",
        LATE,
        LATE,
        attempt_id,
    )
    assert await assessment.due_overdue(LATE + DAY) == []
    assert await assessment.overdue_due(attempt_id, LATE + DAY) is False
    assert assess_jobs() == []


# Stop and resume.


async def test_a_close_while_stopped_makes_the_row_and_no_job_and_resume_defers_it(
    klass, monkeypatch, emitted
):
    admin = await make("admin1@example.com", (AccountRole.admin,))
    session_id, test = await adapted_session(klass, monkeypatch)
    await answer_all(session_id, test)
    emitted.clear()
    assert await assessment.stop_for_session(uuid.UUID(session_id), admin, now=TEST)
    assert {topic for topic, _ in emitted} <= COMMAND_TOPICS["assessment.stop_for_session"]
    # A second stop changes nothing and writes no audit row.
    assert await assessment.stop_for_session(uuid.UUID(session_id), admin, now=TEST) is False
    assert audits(assessment.STOPPED) == [(admin, {"class_session_id": session_id}, {})]
    await closed(session_id)
    attempt_id = attempt_id_of(session_id)
    assert row_of(attempt_id)[:2] == ("incomplete", 0) and assess_jobs() == []
    assert await assessment.assess(attempt_id) == "stopped"
    assert calls() == [] and row_of(attempt_id)[1] == 0
    assert (await view(session_id, monkeypatch)).json()["state"] == "switched_off"
    # Resume: the mark cleared, the job deferred, audited; the run makes it ready.
    emitted.clear()
    at(monkeypatch, TEST + HOUR)
    assert await assessment.resume_for_session(uuid.UUID(session_id), admin, now=TEST + HOUR) == 1
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["assessment.resume_for_session"]
    assert audits(assessment.RESUMED) == [
        (admin, {"class_session_id": session_id}, {"reset": 1, "deferred": 1})
    ]
    assert [row[1] for row in assess_jobs()] == [f"assessment:{attempt_id}"]
    assert await assessment.assess(attempt_id) == "ready"
    assert (await view(session_id, monkeypatch)).json()["state"] == "ready"


async def test_a_stop_tells_the_session_and_each_student_with_an_assessment(
    klass, monkeypatch, emitted
):
    session_id, attempt_id = await ready_session(klass, monkeypatch)
    emitted.clear()
    assert await assessment.stop_for_session(uuid.UUID(session_id), None, now=TEST + HOUR)
    assert set(emitted) == {("session", session_id), ("user", str(user_id(email(0))))}
    assert {topic for topic, _ in emitted} == COMMAND_TOPICS["assessment.stop_for_session"]
    [(stopped_at, stopped_by)] = rows(
        "SELECT stopped_at, stopped_by FROM assessment_switches WHERE class_session_id = %s",
        session_id,
    )
    assert (stopped_at, stopped_by) == (TEST + HOUR, None)
    assert audits(assessment.STOPPED) == [(None, {"class_session_id": session_id}, {})]


async def test_the_stop_mark_may_change_after_the_pin_and_the_pinned_columns_may_not(
    klass, monkeypatch
):
    session_id, _ = await ready_session(klass, monkeypatch)
    execute(
        "UPDATE assessment_switches SET stopped_at = %s WHERE class_session_id = %s",
        TEST,
        session_id,
    )
    for column, value in (
        ("enabled", False),
        ("pinned_at", TEST + HOUR),
        ("model_config_id", uuid.uuid4()),
        ("effort_level", "high"),
    ):
        with pytest.raises(psycopg.errors.RestrictViolation):
            execute(
                f"UPDATE assessment_switches SET {column} = %s WHERE class_session_id = %s",
                value,
                session_id,
            )


async def test_a_run_that_ends_while_stopped_defers_no_later_run(klass, monkeypatch):
    session_id, attempt_id = await ready_session(klass, monkeypatch)
    execute("DELETE FROM procrastinate_jobs WHERE task_name = %s", assessment.ASSESS_TASK)
    made: list[int] = []

    async def stop_on_the_last(*args, **kwargs):
        made.append(1)
        if len(made) == 4:  # the stop lands during the last item's call
            await assessment.stop_for_session(uuid.UUID(session_id), None, now=TEST + HOUR)
        raise gateway.GatewayError("provider_key_missing", "no key here")

    monkeypatch.setattr(gateway, "run", stop_on_the_last)
    assert await assessment.assess(attempt_id) == "incomplete"
    assert len(made) == 4
    assert row_of(attempt_id)[:2] == ("incomplete", 1) and assess_jobs() == []


async def test_a_stop_ends_a_running_job_before_its_next_call_and_a_ready_one_stays_readable(
    klass, monkeypatch
):
    session_id, attempt_id = await ready_session(klass, monkeypatch)
    real = gateway.run
    made: list[int] = []

    async def stop_after_first(*args, **kwargs):
        made.append(1)
        result = await real(*args, **kwargs)
        await assessment.stop_for_session(uuid.UUID(session_id), None, now=TEST + HOUR)
        return result

    monkeypatch.setattr(gateway, "run", stop_after_first)
    assert await assessment.assess(attempt_id) == "stopped"
    assert len(made) == 1
    # The run is not counted and no later run is deferred; the Student reads switched off.
    assert row_of(attempt_id)[:2] == ("incomplete", 0)
    assert [row[4] for row in assess_jobs()] == ["todo"]  # the close's job, run by hand here
    assert (await view(session_id, monkeypatch)).json()["state"] == "switched_off"
    monkeypatch.setattr(gateway, "run", real)
    await assessment.resume_for_session(uuid.UUID(session_id), None, now=TEST + 2 * HOUR)
    assert await assessment.assess(attempt_id) == "ready"
    # A stop after it is ready leaves it readable.
    assert await assessment.stop_for_session(uuid.UUID(session_id), None, now=TEST + 3 * HOUR)
    assert (await view(session_id, monkeypatch)).json()["state"] == "ready"


async def test_stop_raise_the_limit_resume_and_every_assessment_is_ready(klass, monkeypatch):
    """The cost limit: the session's budget has no room, so each call is refused with
    `budget_exhausted` and the assessment fails after its runs; the Admin stops it, raises the
    limit and resumes, and it is ready."""
    monkeypatch.setenv("ASSESSMENT_MAX_RUNS", "1")
    get_settings.cache_clear()
    session_id, attempt_id = await ready_session(klass, monkeypatch)
    [(_, _, _, _, _, _, _, config_id, _)] = assessments()
    scope = ai_budget.BudgetScope.class_session(uuid.UUID(session_id), model_config_id=config_id)
    await ai_budget.set_budget(scope, limit=Decimal("0"), reserve=Decimal("0"))
    assert await assessment.assess(attempt_id) == "failed"
    assert {outcome for *_, outcome in calls()} <= {"budget_exhausted"}
    assert row_of(attempt_id)[5] == "runs_exhausted"
    assert (await view(session_id, monkeypatch)).json()["state"] == "failed"
    assert await assessment.stop_for_session(uuid.UUID(session_id), None, now=TEST + HOUR)
    assert (await view(session_id, monkeypatch)).json()["state"] == "switched_off"
    await ai_budget.set_budget(scope, limit=Decimal("100"))
    assert await assessment.resume_for_session(uuid.UUID(session_id), None, now=TEST + HOUR) == 1
    assert row_of(attempt_id)[:2] == ("incomplete", 0) and row_of(attempt_id)[5] is None
    await jobs.run_until_idle([jobs.LLM_BATCH])
    assert row_of(attempt_id)[0] == "ready"
    assert (await view(session_id, monkeypatch)).json()["state"] == "ready"


# Throughput on the mock provider.


@pytest.mark.long
async def test_four_hundred_submitted_attempts_all_become_ready_through_llm_batch(
    klass, monkeypatch
):
    """400 closed attempts, each with one long answer to score, run through `llm-batch` on the
    mock provider: all are ready (the real duration against the provider's rate limit is checked
    in the rehearsal; 24 hours stays a target until measured)."""
    session_id, _ = await adapted_session(klass, monkeypatch)
    assert (await put(session_id, LONG[0], ANSWER, 1)).status_code == 200
    await closed(session_id)
    [(original,)] = rows("SELECT id FROM test_attempts WHERE class_session_id = %s", session_id)
    execute(
        "INSERT INTO users (id, email, name) SELECT gen_random_uuid(), "
        "'last' || n || '@example.com', 'Last ' || n FROM generate_series(1, 399) AS n"
    )
    execute(
        "INSERT INTO test_attempts (id, user_id, class_session_id, question_set_version, "
        "selection, items, statement_accepted_at, effective_deadline, status, submitted_at, "
        "closed_at) SELECT gen_random_uuid(), u.id, a.class_session_id, a.question_set_version, "
        "a.selection, a.items, a.statement_accepted_at, a.effective_deadline, a.status, "
        "a.submitted_at, a.closed_at FROM test_attempts a, users u "
        "WHERE a.id = %s AND u.email LIKE 'last%%@example.com'",
        original,
    )
    execute(
        "INSERT INTO test_answers (id, attempt_id, item_id, value, revision, saved_at, score) "
        "SELECT gen_random_uuid(), t.id, x.item_id, x.value, x.revision, x.saved_at, x.score "
        "FROM test_answers x, test_attempts t "
        "WHERE x.attempt_id = %s AND t.id <> %s AND t.class_session_id = %s",
        original,
        original,
        session_id,
    )
    others = rows(
        "SELECT id, user_id, question_set_version FROM test_attempts "
        "WHERE class_session_id = %s AND id <> %s",
        session_id,
        original,
    )
    assert len(others) == 399
    async with get_sessionmaker().begin() as s:
        for attempt, student, version in others:
            assert await assessment.schedule(
                s,
                attempt,
                uuid.UUID(session_id),
                user_id=student,
                question_set_version=version,
                due_at=TEST,
                now=TEST + MINUTE,
            )
    assert len(assess_jobs()) == 400
    await jobs.run_worker(
        [jobs.LLM_BATCH], wait=False, concurrency=8, install_signal_handlers=False
    )
    states = rows(
        "SELECT status, count(*) FROM ai_assessments WHERE class_session_id = %s GROUP BY status",
        session_id,
    )
    assert states == [("ready", 400)]
    assert len(notices("assessment_ready")) == 400
