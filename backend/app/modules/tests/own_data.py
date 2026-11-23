"""The Student's own `tests` rows for «Mine data» (Story 15.1, FR-75): the Starting task answers,
the Individual test attempts with every saved answer and the prepared Adapted items, and the
Indicative letter exactly as the Student's own «KI-vurdering» gives it (the letter is computed,
never stored: the view's gate decides, Story 12.6). By the caller's own id only."""

import json
import uuid

from sqlalchemy import select

from app.modules.tests import assessed
from app.modules.tests.models import (
    starting_task_answers,
    test_answers,
    test_attempts,
    test_prepared_items,
)
from app.platform.db import get_sessionmaker
from app.platform.own_data import OwnRecord, record


def answer_text(value: object) -> str | None:
    """A saved answer as the Student gave it: text as text, anything else as compact JSON."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and isinstance(value.get("text"), str):
        return value["text"]
    return json.dumps(value, ensure_ascii=False, separators=(", ", ": "))


async def own_records(user_id: uuid.UUID) -> dict[str, list[OwnRecord]]:
    a, t, p, st = test_attempts, test_answers, test_prepared_items, starting_task_answers
    async with get_sessionmaker()() as s:
        starting = (
            (await s.execute(select(st).where(st.c.user_id == user_id).order_by(st.c.answered_at)))
            .mappings()
            .all()
        )
        attempts = (
            (await s.execute(select(a).where(a.c.user_id == user_id).order_by(a.c.id)))
            .mappings()
            .all()
        )
        answers = (
            (
                await s.execute(
                    select(t, a.c.class_session_id)
                    .join(a, a.c.id == t.c.attempt_id)
                    .where(a.c.user_id == user_id)
                    .order_by(t.c.saved_at, t.c.item_id)
                )
            )
            .mappings()
            .all()
        )
        prepared = (await s.execute(select(p).where(p.c.user_id == user_id))).mappings().all()
    test = [
        record(
            "attempt",
            [
                ("status", "code", row["status"]),
                ("statement_accepted_at", "datetime", row["statement_accepted_at"]),
                ("submitted_at", "datetime", row["submitted_at"]),
                ("items", "number", len(row["items"] or [])),
            ],
            class_session_id=row["class_session_id"],
            at=row["submitted_at"] or row["statement_accepted_at"],
        )
        for row in attempts
    ]
    test += [
        record(
            "answer",
            [("item_id", "code", row["item_id"]), ("value", "text", answer_text(row["value"]))],
            class_session_id=row["class_session_id"],
            at=row["saved_at"],
        )
        for row in answers
    ]
    test += [
        record(
            "prepared",
            [("items", "number", len(row["items"] or []))],
            class_session_id=row["class_session_id"],
            at=row["prepared_at"],
        )
        for row in prepared
    ]
    letters: list[OwnRecord] = []
    for row in attempts:
        view, _ = await assessed._view(row["class_session_id"], user_id)
        letter = view.letter
        if letter is None:
            continue
        letters.append(
            record(
                "letter",
                [
                    ("setting", "code", letter.setting),
                    ("chosen", "bool", letter.chosen),
                    ("letter", "text", letter.value),
                ],
                class_session_id=row["class_session_id"],
            )
        )
    return {
        "starting_task": [
            record(
                "answer",
                [
                    ("item_id", "code", row["item_id"]),
                    (
                        "choice",
                        "text",
                        row["choice"] if row["choice"] is not None else row["answer"],
                    ),
                    ("correct", "bool", row["correct"]),
                ],
                class_session_id=row["class_session_id"],
                at=row["answered_at"],
            )
            for row in starting
        ],
        "test": test,
        "letter": letters,
    }
