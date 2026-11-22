"""Read written feedback that quotes my answer and matches my games (Story 12.3, FR-54, FR-81,
NFR-9, AD-6, AD-7, C-1).

On a model config naming prompt `assessment/v2`, each `assessment` call also gives feedback built
from approved template ids, quote spans over the scrubbed answer, criterion codes and fact ids.
`analysis.feedback.validate_feedback` checks it (Epic 9's validator for the facts, on the Adapted
item's stored facts set); a rejected feedback is asked for once more, then left out with a note,
the first call's score kept. The Student reads it at `GET …/test/assessment`. On the mock
provider; scripted answers stand in for a misbehaving model (`mock.script`)."""

import json
import uuid

from app.ai import config as ai_config
from app.ai import mock, seed
from app.ai.scrub import PLACEHOLDER, scrub
from app.modules.assessment import service as assessment
from app.modules.content import service as content
from app.modules.sessions import service as sessions
from tests.assessment.test_assess import (
    ANSWER,
    LONG,
    adapted_session,
    answer_all,
    assessments,
    attempt_id_of,
    calls,
    closed,
    view,
)
from tests.classes.test_roster_upload import clock, klass
from tests.individual_test.test_adapted import OWN, REPLAY
from tests.individual_test.test_answer import put
from tests.messaging.helpers import rows
from tests.sessions.test_lock import _empty
from tests.sessions.test_student_choice import email

__all__ = ["_empty", "clock", "klass"]

AI_ITEMS = (*LONG, OWN, REPLAY)
FIRST = ANSWER.index(".") + 1
"""The first sentence of `ANSWER`, which the scripted outputs quote."""
SHOWN = ANSWER[: FIRST - 1]
"""What the Student reads of it: «…», men svaret …: the sentence's own full stop is left out."""


def feedback_rows() -> dict[str, tuple]:
    found = rows("SELECT item_id, score, llm_call_id, feedback, feedback_note FROM ai_item_scores")
    return {row[0]: row[1:] for row in found}


def output(score: int, *sentences: dict) -> str:
    return json.dumps({"score": score, "feedback": list(sentences)})


def quote(start: int, end: int, criterion: str = "F5") -> dict:
    return {
        "template_id": "quote-lacks",
        "quote": {"start": start, "end": end},
        "criterion": criterion,
    }


async def only(klass: str, monkeypatch, item_id: str) -> tuple[str, uuid.UUID]:
    """A closed attempt whose only answered AI item is `item_id` (the others empty: no call)."""
    session_id, test = await adapted_session(klass, monkeypatch)
    await answer_all(session_id, test, blank=tuple(i for i in AI_ITEMS if i != item_id))
    await closed(session_id)
    return session_id, attempt_id_of(session_id)


def item_of(body: dict, item_id: str) -> dict:
    return next(item for item in body["items"] if item["id"] == item_id)


async def test_valid_feedback_quotes_the_answer_and_cites_the_students_own_game(klass, monkeypatch):
    session_id, test = await adapted_session(klass, monkeypatch)
    await answer_all(session_id, test)
    await closed(session_id)
    attempt_id = attempt_id_of(session_id)
    assert await assessment.assess(attempt_id) == "ready"
    # The mock's feedback is valid: one call per item, no regeneration.
    made = calls()
    assert len(made) == 4 and all(outcome == "ok" for *_, outcome in made)
    stored = feedback_rows()
    call_ids = {row[0] for row in made}
    for item_id in AI_ITEMS:
        _, call_id, given, note = stored[item_id]
        assert note is None and given["ai_generated"] is True
        assert uuid.UUID(given["llm_call_id"]) == call_id and call_id in call_ids
        assert given["parts"][1] == {"quote": [0, FIRST - 1]}
    # An Adapted item's feedback cites a fact of its own stored facts set, rendered by code.
    own = stored[OWN][2]
    assert "allerede på vei" in own["text"]
    # The prompt listed the templates and that set's facts; the long answer's listed no facts.
    own_request = next(r for _, _, _, r, _ in made if f"({OWN})" in r)
    assert "narration-supply-line (1): " in json.loads(own_request)["prompt"]
    assert "moment:" in json.loads(own_request)["prompt"]

    body = (await view(session_id, monkeypatch)).json()
    assert body["state"] == "ready" and body["checked"] is False
    long_ai = item_of(body, LONG[0])["ai"]
    assert long_ai["feedback_dropped"] is False
    feedback = long_ai["feedback"]
    assert feedback["ai_generated"] is True
    assert feedback["parts"][0] == {"kind": "text", "text": "Du skriver "}
    assert feedback["parts"][1] == {"kind": "quote", "text": SHOWN}
    assert "kriteriet F5 (Utkast: kriterium 5)" in feedback["text"]
    assert f"«{SHOWN}», men" in feedback["text"]


async def test_the_view_reads_checked_from_the_content_service(klass, monkeypatch):
    session_id, _ = await only(klass, monkeypatch, LONG[0])
    await assessment.assess(attempt_id_of(session_id))
    [(guide_id, config_id)] = rows("SELECT scoring_guide_id, model_config_id FROM ai_assessments")
    asked = []

    async def checked(version_id, model_config_id):
        asked.append((version_id, model_config_id))
        return True

    monkeypatch.setattr(content, "is_checked", checked)
    assert (await view(session_id, monkeypatch)).json()["checked"] is True
    assert asked == [(guide_id, config_id)]


async def test_a_span_out_of_range_is_regenerated_once_and_the_second_is_kept(klass, monkeypatch):
    session_id, attempt_id = await only(klass, monkeypatch, LONG[0])
    with mock.script(output(3, quote(0, 5000)), output(1, quote(0, FIRST, "F2"))):
        assert await assessment.assess(attempt_id) == "ready"
    first, second = calls()
    assert first[4] == second[4] == "ok"
    score, call_id, given, note = feedback_rows()[LONG[0]]
    # The first call's score stands; the feedback is the second call's.
    assert (score, call_id, note) == (3, first[0], None)
    assert uuid.UUID(given["llm_call_id"]) == second[0]
    assert "F2" in given["text"]


async def test_a_foreign_fact_id_is_regenerated_once(klass, monkeypatch):
    session_id, attempt_id = await only(klass, monkeypatch, OWN)
    foreign = {"template_id": "narration-supply-line", "fact_ids": ["moment:factory:3"]}
    with mock.script(output(2, quote(0, FIRST, "S1"), foreign)):
        assert await assessment.assess(attempt_id) == "ready"
    first, second = calls()
    score, call_id, given, note = feedback_rows()[OWN]
    assert (score, call_id, note) == (2, first[0], None)
    # The second (the mock's own) cites the item's fact from its stored set.
    assert uuid.UUID(given["llm_call_id"]) == second[0] and "allerede på vei" in given["text"]


async def test_feedback_rejected_twice_is_left_out_with_a_note_and_the_score_kept(
    klass, monkeypatch
):
    session_id, attempt_id = await only(klass, monkeypatch, LONG[0])
    with mock.script(
        output(4, quote(0, 5000)), output(0, {"template_id": "missing", "criterion": "F1"})
    ):
        assert await assessment.assess(attempt_id) == "ready"
    first, second = calls()
    assert first[4] == second[4] == "ok" and first[0] != second[0]
    assert feedback_rows()[LONG[0]] == (4, first[0], None, "dropped")
    ai = item_of((await view(session_id, monkeypatch)).json(), LONG[0])["ai"]
    assert (ai["step"], ai["feedback"], ai["feedback_dropped"]) == (4, None, True)


async def test_a_failed_second_call_drops_the_feedback_and_keeps_the_score(klass, monkeypatch):
    session_id, attempt_id = await only(klass, monkeypatch, LONG[0])
    with mock.script(output(3, quote(0, 5000)), mock.ERROR):
        assert await assessment.assess(attempt_id) == "ready"
    assert [c[4] for c in calls()] == ["ok", "provider_error"]
    score, call_id, given, note = feedback_rows()[LONG[0]]
    assert (score, given, note) == (3, None, "dropped")
    [row] = assessments()
    assert row[3] == "ready"


async def test_a_quoted_roster_name_is_seen_by_the_student_and_never_by_the_llm(klass, monkeypatch):
    session_id, test = await adapted_session(klass, monkeypatch)
    await answer_all(session_id, test, blank=AI_ITEMS)
    [(name,)] = rows("SELECT name FROM users WHERE email = %s", email(0))
    text = f"{name} mener at ordrene svinger. {ANSWER}"
    assert (await put(session_id, LONG[0], text, 1)).status_code == 200
    await closed(session_id)
    scrubbed = scrub(text, [name]).text
    assert scrubbed.startswith(PLACEHOLDER)
    end = scrubbed.index(".") + 1  # «[REDACTED] mener at ordrene svinger.», as the LLM saw it
    with mock.script(output(2, quote(0, end))):
        assert await assessment.assess(attempt_id_of(session_id)) == "ready"
    [(_, _, _, request, _)] = calls()
    assert PLACEHOLDER in request and name not in request
    given = feedback_rows()[LONG[0]][2]
    original = text[: text.index(".")]
    assert original.startswith(name)
    assert given["parts"][1] == {"quote": [0, len(original)]}
    ai = item_of((await view(session_id, monkeypatch)).json(), LONG[0])["ai"]
    assert ai["feedback"]["parts"][1] == {"kind": "quote", "text": original}


async def test_a_session_pinned_to_the_score_only_prompt_keeps_score_only_output(
    klass, monkeypatch
):
    await seed.ensure_zero_config()
    default = await ai_config.active_default()
    assert default is not None and default.spec.prompts["assessment"] >= assessment.FEEDBACK_VERSION
    spec = {**seed.MOCK_SPEC, "name": "kun-poeng"}
    spec["prompts"] = {**seed.MOCK_SPEC["prompts"], "assessment": 1}
    score_only = await ai_config.add(ai_config.parse(spec))

    async def pinned(s, row):
        return score_only.id, None

    monkeypatch.setattr(sessions, "_assessment_config", pinned)
    session_id, attempt_id = await only(klass, monkeypatch, LONG[0])
    assert await assessment.assess(attempt_id) == "ready"
    [(_, _, _, request, _)] = calls()
    assert set(json.loads(request)["output_schema"]["properties"]) == {"score"}
    assert feedback_rows()[LONG[0]][2:] == (None, None)
    ai = item_of((await view(session_id, monkeypatch)).json(), LONG[0])["ai"]
    assert (ai["feedback"], ai["feedback_dropped"]) == (None, False)


async def test_unreadable_narration_templates_leave_feedback_without_facts(klass, monkeypatch):
    """The pinned narration templates cannot be read: the Adapted item is still scored, the prompt
    offers no fact to cite, and its feedback holds no sentence about the game."""
    session_id, attempt_id = await only(klass, monkeypatch, OWN)

    async def unreadable(version):
        raise LookupError(version)

    monkeypatch.setattr(content, "narration_templates", unreadable)
    assert await assessment.assess(attempt_id) == "ready"
    [(_, _, _, request, _)] = calls()
    prompt = json.loads(request)["prompt"]
    assert "narration-" not in prompt
    citable = prompt.split("empty when none may be cited:")[1].split("The templates you may use")[0]
    assert citable.strip() == ""
    score, _, given, note = feedback_rows()[OWN]
    assert note is None and "allerede på vei" not in given["text"]
