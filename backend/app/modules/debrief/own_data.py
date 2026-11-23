"""The Student's own `debrief` rows for «Mine data» (Story 15.1, FR-75): the Forklaring, the
reflection answers, the follow-up questions with the AI answers, the Debrief summary and the
marks of their way through the Debrief, and the Debrief quiz attempts. Every stored row at any
time (not the step-gated page views), by the caller's own id only."""

import uuid

from sqlalchemy import select

from app.modules.debrief.models import (
    debrief_alone,
    debrief_explanations,
    debrief_follow_up_closures,
    debrief_follow_ups,
    debrief_members,
    debrief_reflection_answers,
    debrief_sessions,
    debrief_step_marks,
    debrief_summaries,
    quiz_attempts,
)
from app.platform.db import get_sessionmaker
from app.platform.own_data import OwnRecord, record


async def _all(s, query) -> list:
    return list((await s.execute(query)).mappings().all())


async def own_records(user_id: uuid.UUID) -> dict[str, list[OwnRecord]]:
    t = debrief_explanations
    async with get_sessionmaker()() as s:
        explanations = await _all(s, select(t).where(t.c.user_id == user_id).order_by(t.c.saved_at))
        r = debrief_reflection_answers
        reflections = await _all(
            s, select(r).where(r.c.user_id == user_id).order_by(r.c.saved_at, r.c.question_id)
        )
        f = debrief_follow_ups
        follow_ups = await _all(s, select(f).where(f.c.user_id == user_id).order_by(f.c.id))
        c = debrief_follow_up_closures
        closures = await _all(s, select(c).where(c.c.user_id == user_id))
        m = debrief_summaries
        summaries = await _all(s, select(m).where(m.c.user_id == user_id))
        session_of = debrief_sessions.c.class_session_id
        marks = await _all(
            s,
            select(debrief_step_marks, session_of)
            .join(debrief_sessions, debrief_sessions.c.id == debrief_step_marks.c.debrief_id)
            .where(debrief_step_marks.c.user_id == user_id)
            .order_by(debrief_step_marks.c.done_at),
        )
        members = await _all(
            s,
            select(debrief_members, session_of, debrief_sessions.c.shared)
            .join(debrief_sessions, debrief_sessions.c.id == debrief_members.c.debrief_id)
            .where(debrief_members.c.user_id == user_id),
        )
        alone = await _all(
            s,
            select(debrief_alone, session_of)
            .join(debrief_sessions, debrief_sessions.c.id == debrief_alone.c.debrief_id)
            .where(debrief_alone.c.user_id == user_id),
        )
        q = quiz_attempts
        quizzes = await _all(s, select(q).where(q.c.user_id == user_id).order_by(q.c.submitted_at))

    debrief: list[OwnRecord] = [
        record(
            "summary",
            [
                ("finished_at", "datetime", row["finished_at"]),
                ("moments", "number", len(row["moment_ids"] or [])),
                ("reflection_copy", "text", _reflection_text(row["reflection"])),
            ],
            class_session_id=row["class_session_id"],
            at=row["finished_at"],
        )
        for row in summaries
    ]
    debrief += [
        record(
            "member",
            [
                ("shared", "bool", row["shared"]),
                ("joined_at", "datetime", row["joined_at"]),
                ("last_seen_at", "datetime", row["last_seen_at"]),
            ],
            class_session_id=row["class_session_id"],
            at=row["joined_at"],
        )
        for row in members
    ]
    debrief += [
        record(
            "step_mark",
            [("step", "number", row["step"]), ("done_at", "datetime", row["done_at"])],
            class_session_id=row["class_session_id"],
            at=row["done_at"],
        )
        for row in marks
    ]
    debrief += [
        record(
            "alone",
            [("step", "number", row["step"]), ("reason", "code", row["reason"])],
            class_session_id=row["class_session_id"],
            at=row["since"],
        )
        for row in alone
    ]
    follow = [
        record(
            "question",
            [
                ("question", "text", row["question"]),
                ("answer", "text", row["answer"]),
                ("outcome", "code", row["outcome"]),
            ],
            class_session_id=row["class_session_id"],
            at=row["asked_at"],
        )
        for row in follow_ups
    ]
    follow += [
        record(
            "closure",
            [("closed_at", "datetime", row["closed_at"])],
            class_session_id=row["class_session_id"],
            at=row["closed_at"],
        )
        for row in closures
    ]
    return {
        "explanation": [
            record(
                "explanation",
                [("text", "text", row["text"])],
                class_session_id=row["class_session_id"],
                at=row["saved_at"],
            )
            for row in explanations
        ],
        "reflection": [
            record(
                "answer",
                [("question_id", "code", row["question_id"]), ("text", "text", row["text"])],
                class_session_id=row["class_session_id"],
                at=row["saved_at"],
            )
            for row in reflections
        ],
        "follow_ups": follow,
        "debrief": debrief,
        "quiz": [
            record(
                "attempt",
                [
                    ("number", "number", row["number"]),
                    ("passed", "bool", row["passed"]),
                    ("answers", "number", len(row["answers"] or {})),
                ],
                class_session_id=row["class_session_id"],
                at=row["submitted_at"],
            )
            for row in quizzes
        ]
        # Story 15.1 close-out (FR-75): each stored answer of each attempt, the Student's own
        # choice and whether it was right, not only how many there were.
        + [
            record(
                "answer",
                [
                    ("number", "number", row["number"]),
                    ("question_id", "code", answer.get("question_id")),
                    ("choice", "code", answer.get("choice_id")),
                    ("correct", "bool", answer.get("correct")),
                ],
                class_session_id=row["class_session_id"],
                at=row["submitted_at"],
            )
            for row in quizzes
            for answer in (row["answers"] or [])
            if isinstance(answer, dict)
        ],
    }


def _reflection_text(stored: object) -> str | None:
    """The reflection the summary copied (`[{question_id, text}]`), its texts joined: the
    Student's own words."""
    if not isinstance(stored, list):
        return None
    texts = [str(item["text"]) for item in stored if isinstance(item, dict) and item.get("text")]
    return "\n\n".join(texts) or None
