"""The Student's own `assessment` rows for «Mine data» (Story 15.1, FR-75): the AI assessment of
each of their attempts, every stored item score with its written feedback, the pieces of feedback
they marked as wrong, and the human scores of their answers in a Control test. By the caller's
own id only; a scorer is named by nothing but «sensor»."""

import uuid

from sqlalchemy import column, select, table

from app.modules.assessment.models import (
    ai_assessments,
    ai_feedback_flags,
    ai_item_scores,
    human_scores,
)
from app.platform.db import get_sessionmaker
from app.platform.own_data import OwnRecord, record

# `tests` tables by name only, to reach the Student's answers (as `platform/authz` does).
_answers = table("test_answers", column("id"), column("attempt_id"), column("item_id"))
_attempts = table("test_attempts", column("id"), column("user_id"), column("class_session_id"))


def _feedback(stored: object) -> str | None:
    return stored.get("text") if isinstance(stored, dict) else None


async def own_records(user_id: uuid.UUID) -> dict[str, list[OwnRecord]]:
    x, i, f = ai_assessments, ai_item_scores, ai_feedback_flags
    async with get_sessionmaker()() as s:
        assessments = (
            (await s.execute(select(x).where(x.c.user_id == user_id).order_by(x.c.created_at)))
            .mappings()
            .all()
        )
        scores = (
            (
                await s.execute(
                    select(i, x.c.class_session_id)
                    .join(x, x.c.id == i.c.assessment_id)
                    .where(x.c.user_id == user_id)
                    .order_by(i.c.created_at, i.c.item_id)
                )
            )
            .mappings()
            .all()
        )
        flags = (
            (
                await s.execute(
                    select(f, x.c.class_session_id)
                    .join(x, x.c.id == f.c.assessment_id)
                    .where(x.c.user_id == user_id)
                    .order_by(f.c.flagged_at)
                )
            )
            .mappings()
            .all()
        )
        human = (
            (
                await s.execute(
                    select(
                        human_scores.c.score,
                        human_scores.c.submitted_at,
                        _answers.c.item_id,
                        _attempts.c.class_session_id,
                    )
                    .join(_answers, _answers.c.id == human_scores.c.answer_id)
                    .join(_attempts, _attempts.c.id == _answers.c.attempt_id)
                    .where(_attempts.c.user_id == user_id)
                    .order_by(human_scores.c.submitted_at)
                )
            )
            .mappings()
            .all()
        )
    found = [
        record(
            "assessment",
            [
                ("status", "code", row["status"]),
                ("ready_at", "datetime", row["ready_at"]),
                ("letter_chosen", "bool", row["letter_chosen"]),
            ],
            class_session_id=row["class_session_id"],
            at=row["created_at"],
        )
        for row in assessments
    ]
    found += [
        record(
            "item_score",
            [
                ("item_id", "code", row["item_id"]),
                ("score", "number", row["score"]),
                ("feedback", "text", _feedback(row["feedback"])),
                ("feedback_note", "code", row["feedback_note"]),
            ],
            class_session_id=row["class_session_id"],
            at=row["created_at"],
        )
        for row in scores
    ]
    found += [
        record(
            "flag",
            [("item_id", "code", row["item_id"])],
            class_session_id=row["class_session_id"],
            at=row["flagged_at"],
        )
        for row in flags
    ]
    found += [
        record(
            "human_score",
            [("item_id", "code", row["item_id"]), ("score", "number", row["score"])],
            class_session_id=row["class_session_id"],
            at=row["submitted_at"],
        )
        for row in human
    ]
    return {"assessment": found}
