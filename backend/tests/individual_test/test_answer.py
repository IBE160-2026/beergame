"""Answer multiple-choice items with autosave (Story 11.4, FR-51, FR-52, FR-54, FR-5, AD-10).

`PUT /api/me/class-sessions/{id}/test/answers/{item_id}` stores the answer through
`tests.commands.save_answer` only when its revision is above the stored one and returns the stored
answer either way; the test the page reads carries each choice item's options and saved answer,
never a score or the answer key. The api's clock is fixed and moved by hand."""

import asyncio
import uuid
from datetime import timedelta

from app.modules.content import service as content
from app.modules.identity.schemas import AccountRole
from app.platform.events.registry import COMMAND_TOPICS
from tests.classes.test_classes import LECTURER, make
from tests.classes.test_invitation_counts import execute
from tests.classes.test_roster_upload import NOW, clock, klass
from tests.classes.test_staff import call
from tests.classes.test_student_registration import emitted
from tests.individual_test.test_open import code, locked_session, path, replayed
from tests.messaging.helpers import rows
from tests.sessions.test_dates import TEST, at
from tests.sessions.test_lock import _empty
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "emitted", "klass"]

Z = NOW.isoformat().replace("+00:00", "Z")


def answer(session_id: str, item_id: str) -> str:
    return f"{path(session_id)}/answers/{item_id}"


async def opened(klass: str, n: int = 1) -> tuple[str, list, dict]:
    """A locked session whose first Student has opened the test: (session, seated, the test)."""
    session_id, seated = await locked_session(klass, n)
    await replayed(seated[0], session_id)
    test = await call(email(0), "POST", path(session_id))
    assert test.status_code == 201
    return session_id, seated, test.json()


def first(test: dict, kind: str) -> dict:
    return next(item for item in test["items"] if item["type"] == kind)


async def put(session_id: str, item_id: str, value, revision, who: str | None = None):
    return await call(
        who or email(0),
        "PUT",
        answer(session_id, item_id),
        json={"value": value, "revision": revision},
    )


def stored(session_id: str) -> list[tuple]:
    return rows(
        "SELECT a.item_id, a.value, a.revision FROM test_answers a "
        "JOIN test_attempts t ON t.id = a.attempt_id WHERE t.class_session_id = %s "
        "ORDER BY a.item_id",
        session_id,
    )


async def test_a_choice_is_saved_and_read_back_with_no_score(klass, emitted):
    session_id, _, test = await opened(klass)
    item = first(test, "choice")
    [(version,)] = rows(
        "SELECT question_set_version FROM test_attempts WHERE class_session_id = %s", session_id
    )
    question_set = await content.get(content.Kind.QUESTION_SET, version)
    assert item["options"] == list(
        next(i for i in question_set.items if i.id == item["id"]).options
    )
    assert all(i["options"] == [] for i in test["items"] if i["type"] != "choice")

    emitted.clear()
    saved = await put(session_id, item["id"], item["options"][0], 1)
    assert saved.status_code == 200
    assert saved.json() == {
        "item_id": item["id"],
        "value": item["options"][0],
        "revision": 1,
        "saved_at": Z,
    }
    assert emitted == [] and COMMAND_TOPICS["tests.save_answer"] == frozenset()

    changed = await put(session_id, item["id"], item["options"][1], 2)
    assert (changed.json()["value"], changed.json()["revision"]) == (item["options"][1], 2)
    assert stored(session_id) == [(item["id"], item["options"][1], 2)]

    # Read back on any device: the answer, with no score, key or right/wrong state (FR-54).
    again = (await call(email(0), "GET", path(session_id))).json()
    back = next(i for i in again["items"] if i["id"] == item["id"])
    assert back["answer"] == {"value": item["options"][1], "revision": 2, "saved_at": Z}


async def test_a_lower_or_equal_revision_returns_the_stored_answer_without_an_error(
    klass, monkeypatch
):
    session_id, _, test = await opened(klass)
    item = first(test, "choice")
    a, b = item["options"][:2]
    assert (await put(session_id, item["id"], a, 3)).status_code == 200
    at(monkeypatch, NOW + timedelta(minutes=5))
    for revision in (2, 3):
        late = await put(session_id, item["id"], b, revision)
        assert late.status_code == 200
        assert late.json() == {"item_id": item["id"], "value": a, "revision": 3, "saved_at": Z}
    assert stored(session_id) == [(item["id"], a, 3)]


async def test_two_devices_saving_at_once_keep_the_highest_revision(klass):
    session_id, _, test = await opened(klass)
    item = first(test, "choice")
    a, b = item["options"][:2]
    for _ in range(3):
        execute("DELETE FROM test_answers")
        lower, higher = await asyncio.gather(
            put(session_id, item["id"], a, 2), put(session_id, item["id"], b, 3)
        )
        assert lower.status_code == higher.status_code == 200
        assert higher.json()["revision"] == 3
        assert lower.json()["revision"] in (2, 3)
        assert stored(session_id) == [(item["id"], b, 3)]


async def test_a_value_that_is_no_answer_or_an_unknown_item_stores_nothing(klass):
    session_id, _, test = await opened(klass)
    item = first(test, "choice")
    for value in ("z", 1, None, [item["options"][0]], {"id": item["options"][0]}):
        assert code(await put(session_id, item["id"], value, 1)) == (422, "invalid_answer")
    # Long answers arrive with Story 11.6 (table and number: `test_interactive.py`).
    long_item = first(test, "long")["id"]
    assert code(await put(session_id, long_item, "tekst", 1)) == (422, "invalid_answer")
    assert code(await put(session_id, "no-such-item", "a", 1)) == (422, "unknown_item")
    for revision in (0, -1, 1_000_001, "2"):
        bad = await put(session_id, item["id"], item["options"][0], revision)
        assert bad.status_code == 422
    assert stored(session_id) == []


async def test_after_the_deadline_or_once_handed_in_nothing_is_saved(klass, monkeypatch):
    session_id, _, test = await opened(klass)
    item = first(test, "choice")
    assert (await put(session_id, item["id"], item["options"][0], 1)).status_code == 200
    execute("UPDATE test_attempts SET status = 'submitted', submitted_at = %s", NOW)
    submitted = await put(session_id, item["id"], item["options"][1], 2)
    assert code(submitted) == (409, "attempt_submitted")
    execute("UPDATE test_attempts SET status = 'open', submitted_at = NULL")
    at(monkeypatch, TEST)
    passed = await put(session_id, item["id"], item["options"][1], 2)
    assert code(passed) == (409, "test_deadline_passed")
    assert stored(session_id) == [(item["id"], item["options"][0], 1)]


async def test_no_one_else_saves_and_an_unopened_test_saves_nothing(klass):
    session_id, seated, test = await opened(klass, 2)
    item = first(test, "choice")
    await replayed(seated[1], session_id)  # their own session, the test not opened
    await make("admin@x.no", roles=(AccountRole.admin,))
    for who, target in (
        (email(1), session_id),
        (LECTURER, session_id),
        ("admin@x.no", session_id),
        (email(0), str(uuid.uuid7())),
        (email(0), "not-an-id"),
    ):
        refused = await put(target, item["id"], "a", 1, who=who)
        assert code(refused) == (403, "forbidden")
    assert stored(session_id) == []
