"""Story 13.10 (FR-58, FR-54, C-2): the Student report's Individual test section from stored rows.

A Student opens the test, answers a choice, a table and a number item and a long answer, and
hands it in; the report holds every item in its frozen order with the saved answers and, for the
items a computed rule scores, the score `commands.score_answers` stored as points of the item's
weight (an unanswered scored item 0, a long answer none), and never a criterion, an explanation
or an answer key. While the attempt is open there is no score."""

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.modules.reports import report_data
from app.platform.db import get_sessionmaker
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call
from tests.individual_test.test_answer import first, opened, put
from tests.individual_test.test_submit import scores, submit_path
from tests.messaging.helpers import rows
from tests.sessions.test_lock import _empty
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "klass"]

NOW = datetime(2026, 12, 1, 12, tzinfo=UTC)


async def section_of(user_id: uuid.UUID, session_id: str) -> report_data.ReportTestOut | None:
    async with get_sessionmaker()() as s:
        data = await report_data.build_report_data(
            s, user_id, uuid.UUID(session_id), report_data.ReportOptions(), now=NOW
        )
    [section] = [each for each in data.sections if each.kind == "test"]
    assert isinstance(section, report_data.TestSectionOut)
    dumped = json.dumps(section.model_dump(mode="json"), ensure_ascii=False)
    for word in ("criteria", "explanation", "answer_key", "credit"):
        assert word not in dumped
    return section.test


async def test_a_handed_in_test_holds_every_item_its_answers_and_the_stored_scores(klass):
    session_id, seated, test = await opened(klass)
    choice = first(test, "choice")
    long = first(test, "long")
    answers = {
        choice["id"]: choice["options"][0],
        "tabell-annen-bransje": [8, None, 9, None, None],
        "tall-annen-bransje": 16,
        long["id"]: "Et langsvar.",
    }
    for item_id, value in answers.items():
        assert (await put(session_id, item_id, value, 1)).status_code == 200

    # Open: the answers so far, no score.
    found = await section_of(seated[0], session_id)
    assert found is not None and found.state == "open"
    assert all(item.points is None for item in found.items) and found.points is None

    assert (await call(email(0), "POST", submit_path(session_id))).status_code == 200
    found = await section_of(seated[0], session_id)
    assert found is not None and found.state == "submitted" and found.submitted_at is not None
    assert [item.number for item in found.items] == list(range(1, len(test["items"]) + 1))
    assert [item.title.text for item in found.items] == [item["title"] for item in test["items"]]
    [(frozen,)] = rows("SELECT items FROM test_attempts WHERE class_session_id = %s", session_id)
    weights = {each["id"]: each["weight"] for each in frozen}
    stored = scores(session_id)
    by_id = dict(zip([item["id"] for item in test["items"]], found.items, strict=True))
    for item_id, item in by_id.items():
        assert item.weight == weights[item_id]
        if item_id in answers:
            assert item.answer == answers[item_id]
        if item.type in ("long", "adapted"):
            assert item.points is None
        elif item_id in stored:
            credit = Decimal(str(stored[item_id][0]["credit"]))
            assert item.points == (credit * item.weight).quantize(Decimal("0.01"))
        else:  # a scored item never answered scores 0
            assert item.answer is None and item.points == Decimal("0.00")
    scored = [item for item in found.items if item.points is not None]
    assert found.points == sum(item.points for item in scored)
    assert found.points_of == sum(item.weight for item in scored)
    assert by_id["tabell-annen-bransje"].table is not None
    assert by_id["tall-annen-bransje"].column is not None
