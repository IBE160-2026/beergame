"""The erasure of a User (Story 15.2, FR-76, AD-14) after Epics 11 and 12: the text of the
Student's long and Adapted answers, the written feedback that quotes it and the bodies of the AI
calls that assessed it go; the answer rows, their scores, the AI item scores and the call cost rows
stay under the same ids. On the mock provider; `erase_user` is called directly (the system)."""

import uuid

from app.modules.assessment import service as assessment
from app.modules.identity import erasure
from tests.assessment.test_assess import (
    ANSWER,
    adapted_session,
    answer_all,
    attempt_id_of,
    closed,
)
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.identity.test_user_delete import everywhere, user_id_of
from tests.messaging.helpers import rows
from tests.sessions.test_lock import _empty
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "klass"]


def answers(attempt_id: uuid.UUID) -> dict[str, tuple]:
    found = rows(
        "SELECT item_id, id, value, score FROM test_answers WHERE attempt_id = %s", attempt_id
    )
    return {row[0]: row[1:] for row in found}


def item_scores(attempt_id: uuid.UUID) -> dict[str, tuple]:
    found = rows(
        "SELECT s.item_id, s.score, s.llm_call_id, s.feedback IS NULL FROM ai_item_scores s "
        "JOIN ai_assessments a ON a.id = s.assessment_id WHERE a.attempt_id = %s",
        attempt_id,
    )
    return {row[0]: row[1:] for row in found}


def call_bodies(attempt_id: uuid.UUID) -> list[tuple]:
    return rows(
        "SELECT id, request::text = '{}', response IS NULL, cost_usd FROM llm_call "
        "WHERE caller_ref->>'attempt_id' = %s ORDER BY id",
        str(attempt_id),
    )


async def test_the_erasure_empties_the_students_answer_text_and_the_feedback_quoting_it(
    klass, monkeypatch
):
    session_id, test = await adapted_session(klass, monkeypatch)
    await answer_all(session_id, test)
    await closed(session_id)
    attempt_id = attempt_id_of(session_id)
    assert await assessment.assess(attempt_id) == "ready"
    types = {item["id"]: item["type"] for item in test["items"]}
    texts = {item for item, kind in types.items() if kind in ("long", "adapted")}
    assert texts

    before_answers = answers(attempt_id)
    before_scores = item_scores(attempt_id)
    before_calls = call_bodies(attempt_id)
    assert before_calls and not any(cleared for _, cleared, _, _ in before_calls)
    assert any(not empty for *_, empty in before_scores.values())
    assert everywhere(ANSWER[:60])[ANSWER[:60]]

    user_id = user_id_of(email(0))
    assert await erasure.erase_user(user_id, now=NOW) is True

    after_answers = answers(attempt_id)
    assert after_answers.keys() == before_answers.keys()
    for item_id, (answer_id, value, score) in after_answers.items():
        old_id, old_value, old_score = before_answers[item_id]
        # The ids and the computed scores hold; only the Student's text is emptied.
        assert (answer_id, score) == (old_id, old_score)
        assert value == ("" if item_id in texts else old_value)
    after_scores = item_scores(attempt_id)
    assert {k: v[:2] for k, v in after_scores.items()} == {
        k: v[:2] for k, v in before_scores.items()
    }
    assert all(empty for *_, empty in after_scores.values())
    after_calls = call_bodies(attempt_id)
    assert [(i, cost) for i, _, _, cost in after_calls] == [
        (i, cost) for i, _, _, cost in before_calls
    ]
    assert all(cleared and no_response for _, cleared, no_response, _ in after_calls)
    # No table holds the answer any more.
    assert everywhere(ANSWER[:60])[ANSWER[:60]] == []

    # A repeat finds nothing left to do.
    assert await erasure.erase_user(user_id, now=NOW) is True
    assert answers(attempt_id) == after_answers
