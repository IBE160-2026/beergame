"""Retention's scoped erasure (Story 15.3, FR-77, AD-14; Epic 15 close-out): with
`class_session_id`, every registered part of `identity.erase_user` deletes what a Student who keeps
the account left in that Class session, and nothing of another. One Student holds data of every
part in two Class sessions of the same Class; the scoped run on the first leaves the second as it
was. Rows are planted by SQL: each part's filter is what is under test, not how the rows arise."""

import json
import uuid

from app.modules.games import repo as games_repo
from app.modules.games import service as games_service
from app.modules.identity import service as identity
from app.platform import storage
from app.platform.db import get_sessionmaker
from tests.ai.helpers import stored_config
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW
from tests.messaging.helpers import rows
from tests.ops.test_retention import lecturer_id
from tests.reports.test_report_erasure import request, stored, zipped
from tests.reports.test_student_report import files
from tests.sessions.test_dates import new_session, student_of
from tests.sessions.test_student_home import _empty, clock, klass

__all__ = ["_empty", "clock", "files", "klass"]

TEXT = "Jeg bestilte for mye."


def llm_call(session_id: str, caller_ref: dict, config_id: str) -> None:
    execute(
        "INSERT INTO llm_call (id, purpose, scope_kind, scope_id, caller_ref, model_config_id, "
        "provider, endpoint, model_version, quantisation, effort_level, prompt_version, attempt, "
        "input_tokens, output_tokens, reasoning_tokens, cost_usd, latency_ms, outcome, request, "
        "response, started_at) VALUES (%s, 'debrief_follow_up', 'class_session', %s, %s, %s, "
        "'mock', 'mock', 'm', 'none', 'none', 1, 1, 1, 1, 0, 0.001, 1, 'ok', %s, %s, now())",
        uuid.uuid7(),
        session_id,
        json.dumps(caller_ref),
        config_id,
        json.dumps({"messages": [TEXT]}),
        TEXT,
    )


async def plant(session_id: str, user_id: uuid.UUID, lecturer: uuid.UUID, config_id: str) -> None:
    """One row of every part the scoped erasure reaches, in this Class session."""
    # A running Class game with the Student in a Seat (the `games` preparation).
    game, seat = uuid.uuid7(), uuid.uuid7()
    execute(
        "INSERT INTO games (id, purpose, lifecycle, version, class_session_id, game_number) "
        "VALUES (%s, 'class', 'running', 1, %s, 1)",
        game,
        session_id,
    )
    execute(
        "INSERT INTO seats (id, game_id, role, position) VALUES (%s, %s, 'retailer', 1)",
        seat,
        game,
    )
    execute(
        "INSERT INTO seat_occupancy (id, seat_id, from_week, occupant_kind, reason, user_id) "
        "VALUES (%s, %s, 1, 'student', 'initial', %s)",
        uuid.uuid7(),
        seat,
        user_id,
    )
    # The Debrief's text (`debrief`).
    fact_set = uuid.uuid7()
    execute(
        "INSERT INTO fact_sets (id, game_id, seat_id, analysis_version, payload) "
        "VALUES (%s, %s, %s, 1, '{}')",
        fact_set,
        game,
        seat,
    )
    execute(
        "INSERT INTO debrief_explanations (user_id, class_session_id, game_id, text, length, "
        "saved_at) VALUES (%s, %s, %s, %s, %s, now())",
        user_id,
        session_id,
        game,
        TEXT,
        len(TEXT),
    )
    execute(
        "INSERT INTO debrief_reflection_answers (user_id, class_session_id, question_id, game_id, "
        "questions_version, text, length, saved_at) VALUES (%s, %s, 'q1', %s, 1, %s, %s, now())",
        user_id,
        session_id,
        game,
        TEXT,
        len(TEXT),
    )
    execute(
        "INSERT INTO debrief_summaries (user_id, class_session_id, game_id, fact_set_id, "
        "moment_ids, reflection, finished_at) VALUES (%s, %s, %s, %s, '[]', %s, now())",
        user_id,
        session_id,
        game,
        fact_set,
        json.dumps([{"question_id": "q1", "questions_version": 1, "text": TEXT}]),
    )
    execute(
        "INSERT INTO debrief_follow_ups (id, user_id, class_session_id, fact_set_id, question, "
        "outcome, answer, llm_call_id) VALUES (%s, %s, %s, %s, %s, 'answered', %s, %s)",
        uuid.uuid7(),
        user_id,
        session_id,
        fact_set,
        TEXT,
        TEXT,
        uuid.uuid7(),
    )
    # Messages (`messaging`): one to the Student alone, their place among a Class session's
    # recipients, and a notice about the Class session.
    to_all = uuid.uuid7()
    for message, kind, recipient in (
        (uuid.uuid7(), "student", user_id),
        (to_all, "class_session", None),
    ):
        execute(
            "INSERT INTO messages (id, key, class_session_id, sender_id, recipient_kind, "
            "recipient_user_id, text) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            message,
            uuid.uuid4(),
            session_id,
            lecturer,
            kind,
            recipient,
            TEXT,
        )
    execute("INSERT INTO message_recipients (message_id, user_id) VALUES (%s, %s)", to_all, user_id)
    execute(
        "INSERT INTO notices (id, user_id, kind, dedupe_key, ref) "
        "VALUES (%s, %s, 'message', %s, %s)",
        uuid.uuid7(),
        user_id,
        f"planted:{uuid.uuid4()}",
        session_id,
    )
    # Completion corrections (`completion`), Tilrettelegging and own deadline and the body of an
    # AI call made for them (`sessions`).
    execute(
        "INSERT INTO completion_corrections (id, user_id, class_session_id, step, done, reason, "
        "actor_user_id, at) VALUES (%s, %s, %s, 'class_game', true, %s, %s, now())",
        uuid.uuid7(),
        user_id,
        session_id,
        TEXT,
        lecturer,
    )
    execute(
        "INSERT INTO student_adjustments (class_session_id, user_id, time_factor, updated_at) "
        "VALUES (%s, %s, 2.0, now())",
        session_id,
        user_id,
    )
    execute(
        "INSERT INTO student_deadline_extensions (class_session_id, user_id, test_deadline, "
        "updated_at) VALUES (%s, %s, now() + interval '30 days', now())",
        session_id,
        user_id,
    )
    llm_call(session_id, {"user_id": str(user_id)}, config_id)
    # A long answer, its AI assessment's feedback and the call that assessed it (`tests`).
    attempt, assessment = uuid.uuid7(), uuid.uuid7()
    execute(
        "INSERT INTO test_attempts (id, user_id, class_session_id, question_set_version, "
        "selection, items, statement_accepted_at, status, submitted_at) VALUES (%s, %s, %s, 1, "
        "'[]', %s, now(), 'submitted', now())",
        attempt,
        user_id,
        session_id,
        json.dumps([{"id": "i1", "type": "long"}]),
    )
    execute(
        "INSERT INTO test_answers (id, attempt_id, item_id, value, revision, saved_at) "
        "VALUES (%s, %s, 'i1', %s, 1, now())",
        uuid.uuid7(),
        attempt,
        json.dumps(TEXT),
    )
    execute(
        "INSERT INTO ai_assessments (id, attempt_id, class_session_id, user_id, status, "
        "question_set_version, created_at, updated_at) VALUES (%s, %s, %s, %s, 'ready', 1, now(), "
        "now())",
        assessment,
        attempt,
        session_id,
        user_id,
    )
    execute(
        "INSERT INTO ai_item_scores (assessment_id, item_id, score, source, question_set_version, "
        "created_at, llm_call_id, feedback) VALUES (%s, 'i1', 2, 'ai', 1, now(), %s, %s)",
        assessment,
        uuid.uuid7(),
        json.dumps({"text": TEXT, "ai_generated": True}),
    )
    llm_call(session_id, {"attempt_id": str(attempt)}, config_id)
    # The Student's report and the Class session's ZIP (`reports`).
    path = await stored(f"class-sessions/{session_id}/{user_id}/student-report.pdf")
    request(session_id, user_id, path)
    zipped(session_id, await stored(f"class-sessions/{session_id}/bundles/student-reports.zip"))


def footprint(session_id: str, user_id: uuid.UUID) -> dict[str, int]:
    """Per part, how many rows of the Student's data the Class session still holds."""
    s, u = session_id, user_id
    one = {
        "debrief_explanations": ("class_session_id = %s AND user_id = %s", (s, u)),
        "debrief_reflection_answers": ("class_session_id = %s AND user_id = %s", (s, u)),
        "debrief_follow_ups": ("class_session_id = %s AND user_id = %s", (s, u)),
        "debrief_summaries": (
            "class_session_id = %s AND user_id = %s AND reflection <> '[]'::jsonb",
            (s, u),
        ),
        "messages": ("class_session_id = %s AND recipient_user_id = %s", (s, u)),
        "message_recipients": (
            "user_id = %s AND message_id IN (SELECT id FROM messages WHERE class_session_id = %s)",
            (u, s),
        ),
        "notices": ("ref = %s AND user_id = %s", (s, u)),
        "completion_corrections": ("class_session_id = %s AND user_id = %s", (s, u)),
        "student_adjustments": ("class_session_id = %s AND user_id = %s", (s, u)),
        "student_deadline_extensions": ("class_session_id = %s AND user_id = %s", (s, u)),
        "llm_call": ("scope_id = %s AND response IS NOT NULL", (s,)),
        "test_answers": (
            "value <> to_jsonb(''::text) AND attempt_id IN "
            "(SELECT id FROM test_attempts WHERE class_session_id = %s AND user_id = %s)",
            (s, u),
        ),
        "ai_item_scores": (
            "feedback IS NOT NULL AND assessment_id IN "
            "(SELECT id FROM ai_assessments WHERE class_session_id = %s AND user_id = %s)",
            (s, u),
        ),
        "report_requests": ("class_session_id = %s AND user_id = %s", (s, u)),
        "report_zips": ("class_session_id = %s AND object_path IS NOT NULL", (s,)),
    }
    return {
        table: rows(f"SELECT count(*) FROM {table} WHERE {where}", *params)[0][0]
        for table, (where, params) in one.items()
    }


async def running_seats(user_id: uuid.UUID, scope: str) -> int:
    async with get_sessionmaker()() as s:
        return len(await games_repo.erasure_seats_of(s, user_id, uuid.UUID(scope)))


async def test_every_part_deletes_only_the_scoped_class_sessions_data(klass, files, monkeypatch):
    student = await student_of(klass)
    lecturer = lecturer_id()
    first, second = await new_session(klass), await new_session(klass)
    config_id = await stored_config()
    for session_id in (first, second):
        await plant(session_id, student, lecturer, config_id)
    planted = footprint(first, student)
    assert planted == footprint(second, student)
    assert all(count >= 1 for count in planted.values()), planted
    # The `games` preparation finds the running Seat of each Class session by scope alone.
    assert await running_seats(student, first) == await running_seats(student, second) == 1
    handed: list[tuple] = []

    async def hand_over(user_id, scope=None):
        handed.append((user_id, scope))

    monkeypatch.setattr(games_service, "hand_over_seats_of", hand_over)

    done = await identity.erase_user(student, now=NOW, class_session_id=uuid.UUID(first))

    assert done is True
    assert handed == [(student, uuid.UUID(first))]
    assert footprint(first, student) == dict.fromkeys(planted, 0)
    assert footprint(second, student) == planted
    folder = files / storage.REPORTS
    for session_id, kept in ((first, False), (second, True)):
        assert (
            folder / f"class-sessions/{session_id}/{student}/student-report.pdf"
        ).exists() is kept
        assert (
            folder / f"class-sessions/{session_id}/bundles/student-reports.zip"
        ).exists() is kept
    # The account stays as it was: a scoped run anonymises nothing and audits nothing.
    assert rows("SELECT deleted_at FROM users WHERE id = %s", student) == [(None,)]
    assert rows("SELECT count(*) FROM audit_events WHERE action = 'user.deleted'") == [(0,)]
