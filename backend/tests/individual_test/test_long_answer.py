"""Write long answers with autosave (Story 11.6, FR-51, FR-52, FR-54, AD-7, AD-10).

`PUT …/answers/{item_id}` stores a long-answer item's text exactly as typed through
`tests.commands.save_answer` (Story 11.4's path, the same revision rule); anything that is not
text within the limit stores nothing. No score is computed, no LLM is called and the text never
reaches a log line. The api's clock is fixed."""

from structlog.testing import capture_logs

from app.modules.content import service as content
from app.modules.tests import commands, scoring
from tests.classes.test_roster_upload import clock, klass
from tests.classes.test_staff import call
from tests.individual_test.test_answer import opened, put, stored
from tests.individual_test.test_open import code, path
from tests.messaging.helpers import rows
from tests.sessions.test_lock import _empty
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "klass"]

LONG = "langsvar-forsinkelse"


async def test_a_long_answer_is_stored_exactly_as_typed_and_read_back(klass):
    session_id, _, test = await opened(klass)
    item = next(i for i in test["items"] if i["id"] == LONG)
    assert (item["type"], item["options"], item["table"], item["column"]) == (
        "long",
        [],
        None,
        None,
    )
    text = "  Forsinkelsen gjør at ordren kommer fram to uker senere.\n\nDerfor …  "
    with capture_logs() as logs:
        saved = await put(session_id, LONG, text, 1)
    assert saved.status_code == 200
    assert (saved.json()["value"], saved.json()["revision"]) == (text, 1)
    # No answer text in any log line.
    assert "Forsinkelsen" not in str(logs)
    # Emptied: stored as the empty text, with the next revision.
    assert (await put(session_id, LONG, "", 2)).status_code == 200
    again = (await call(email(0), "GET", path(session_id))).json()
    answer = next(i for i in again["items"] if i["id"] == LONG)["answer"]
    assert (answer["value"], answer["revision"]) == ("", 2)
    # A later revision with the text again; an older one changes nothing.
    assert (await put(session_id, LONG, text, 3)).status_code == 200
    late = await put(session_id, LONG, "eldre", 2)
    assert (late.status_code, late.json()["value"], late.json()["revision"]) == (200, text, 3)
    assert stored(session_id) == [(LONG, text, 3)]


async def test_anything_but_text_within_the_limit_stores_nothing(klass):
    session_id, _, _ = await opened(klass)
    # The page's field stops at the same length (`LONG_ANSWER_MAX` in `autosave.ts`).
    assert commands.LONG_ANSWER_MAX == 20_000
    longest = "a" * commands.LONG_ANSWER_MAX
    for value in (
        None,
        12,
        ["tekst"],
        {"tekst": "a"},
        True,
        longest + "a",
        "Hemmelig før\u0000etter",
    ):
        with capture_logs() as logs:
            refused = await put(session_id, LONG, value, 1)
        assert code(refused) == (422, "invalid_answer"), repr(value)[:40]
        # A refused answer is not logged either.
        assert "Hemmelig" not in str(logs) and "aaaaaaaaaa" not in str(logs)
    # A lone surrogate, as a JSON escape (no client encodes it as text).
    lone = await call(
        email(0),
        "PUT",
        f"{path(session_id)}/answers/{LONG}",
        content=b'{"value": "a\\ud800", "revision": 1}',
        headers={"Content-Type": "application/json"},
    )
    assert code(lone) == (422, "invalid_answer")
    assert stored(session_id) == []
    assert (await put(session_id, LONG, longest, 1)).status_code == 200
    assert stored(session_id) == [(LONG, longest, 1)]


async def test_the_question_is_the_pinned_sets_wording_unchanged(klass):
    """Every item's text is its title in the attempt's pinned question set version, as written;
    so the item tagged as using the Explanation's wording keeps that wording (FR-52)."""
    session_id, _, test = await opened(klass)
    [(version,)] = rows(
        "SELECT question_set_version FROM test_attempts WHERE class_session_id = %s", session_id
    )
    question_set = await content.get(content.Kind.QUESTION_SET, version)
    by_id = {i.id: i for i in (*question_set.items, *question_set.replacements)}
    for item in test["items"]:
        assert item["title"] == by_id[item["id"]].title
    [tagged] = [i for i in question_set.items if "explanation-wording" in i.tags]
    assert any(item["id"] == tagged.id for item in test["items"])


async def test_a_long_answer_has_no_computed_score():
    """Long answers are scored against the Scoring guide in Epic 12; no rule scores them here."""
    _, question_set = await content.question_set(None)
    _, task = await content.starting_task(None)
    long_items = [i for i in (*question_set.items, *question_set.replacements) if i.type == "long"]
    assert long_items
    for item in long_items:
        assert scoring.score_answer(item, "Et svar.", task) is None
