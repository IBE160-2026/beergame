"""Story 12.3: written feedback that quotes the answer and matches the Student's games (FR-54,
NFR-9, AD-7).

Golden tests of `analysis.feedback.validate_feedback` (an accepted output and one rejection of each
kind) and `render_feedback` (quotes mapped through the scrubber's offset map to the original
answer, criteria from the guide, facts rendered by the narration's code), on the hand-built facts
set of the moments' tests (moments in Weeks 3, 9 and 10 of a Retailer)."""

import pytest
from pydantic import ValidationError

from app.ai.scrub import PLACEHOLDER, scrub
from app.analysis import feedback
from app.analysis.feedback import (
    AssessmentFeedbackOutput,
    FeedbackSentence,
    Span,
    render_feedback,
    validate_feedback,
)
from tests.analysis.test_moments import scenario
from tests.analysis.test_narration import TEMPLATES

ANSWER = "Kari Nordmann sa at ordrene svinger. Forsinkelsen gjør det verre."
CRITERIA = {"F1": "forklarer forsinkelse", "F5": "nevner informasjon"}
TERMS = ["Kari Nordmann"]


def sentence(template_id: str, **slots) -> FeedbackSentence:
    if "quote" in slots:
        slots["quote"] = Span(start=slots["quote"][0], end=slots["quote"][1])
    return FeedbackSentence(template_id=template_id, **slots)


def out(*sentences: FeedbackSentence, score: int = 3) -> AssessmentFeedbackOutput:
    return AssessmentFeedbackOutput(score=score, feedback=sentences)


def check(output: AssessmentFeedbackOutput, *, facts=True, answer: str = ANSWER):
    scrubbed = scrub(answer, TERMS)
    return validate_feedback(
        output,
        answer,
        scrubbed.offsets,
        list(CRITERIA),
        scenario() if facts else None,
        TEMPLATES if facts else None,
    )


def test_a_quote_a_criterion_and_an_own_fact_are_accepted_and_rendered_by_code():
    scrubbed = scrub(ANSWER, TERMS)
    assert scrubbed.text.startswith(PLACEHOLDER)
    # The LLM saw «[REDACTED] sa at ordrene svinger.» and quotes all of it, placeholder included.
    end = scrubbed.text.index(".") + 1
    output = out(
        sentence("quote-lacks", quote=(0, end), criterion="F5"),
        sentence("missing", criterion="F1"),
        sentence("narration-supply-line", fact_ids=("moment:retailer:3",)),
    )
    assert check(output).accepted
    text, parts = render_feedback(output, ANSWER, scrubbed.offsets, CRITERIA, scenario(), TEMPLATES)
    # The Student reads their own words, the name included; the LLM never saw it.
    # The quote's own full stop gives way to the sentence going on after it.
    quoted = "Kari Nordmann sa at ordrene svinger"
    assert parts[1] == {"quote": [0, len(quoted)]}
    assert ANSWER[0 : len(quoted)] == quoted
    assert text == (
        f"Du skriver «{quoted}», men svaret forklarer ikke kriteriet F5 (nevner informasjon). "
        "Svaret tar ikke opp kriteriet F1 (forklarer forsinkelse). "
        "Da du bestilte 12 i Uke 3, var 16 allerede på vei."
    )
    assert parts[0] == {"text": "Du skriver "}
    assert all(set(part) in ({"text"}, {"quote"}) for part in parts)


def test_a_quote_is_trimmed_to_the_words_and_never_retyped():
    answer = "  Ordrene svinger.  "
    scrubbed = scrub(answer, [])
    output = out(sentence("quote-covers", quote=(0, len(answer)), criterion="F1"))
    assert check(output, answer=answer, facts=False).accepted
    text, parts = render_feedback(output, answer, scrubbed.offsets, CRITERIA, None, None)
    assert parts[1] == {"quote": [2, 17]} and answer[2:17] == "Ordrene svinger"
    assert (
        text == "Du skriver «Ordrene svinger». Det svarer på kriteriet F1 (forklarer forsinkelse)."
    )


def test_a_span_cutting_a_word_takes_in_the_whole_word():
    answer = "Ordrene svinger mer oppover i kjeden"
    scrubbed = scrub(answer, [])
    # «rdrene svin»: the model counted one character off at each end.
    output = out(sentence("quote-lacks", quote=(1, 12), criterion="F1"))
    assert check(output, answer=answer, facts=False).accepted
    _, parts = render_feedback(output, answer, scrubbed.offsets, CRITERIA, None, None)
    [start, end] = parts[1]["quote"]
    assert answer[start:end] == "Ordrene svinger"


def test_a_quote_of_more_than_max_quote_characters_is_rejected():
    answer = "ord " * 100  # 400 characters
    exact = out(sentence("quote-lacks", quote=(0, feedback.MAX_QUOTE), criterion="F1"))
    assert check(exact, answer=answer, facts=False).accepted
    longer = out(sentence("quote-lacks", quote=(0, feedback.MAX_QUOTE + 1), criterion="F1"))
    verdict = check(longer, answer=answer, facts=False)
    assert (verdict.accepted, verdict.reason) == (False, "span_out_of_range")


@pytest.mark.parametrize(
    ("sentences", "facts", "reason"),
    [
        # A span past the end of the text the LLM saw, an empty one, a blank one (too long: below).
        ((sentence("quote-lacks", quote=(5, 500), criterion="F1"),), True, "span_out_of_range"),
        ((sentence("quote-lacks", quote=(5, 5), criterion="F1"),), True, "span_out_of_range"),
        ((sentence("quote-lacks", quote=(33, 34), criterion="F1"),), True, "span_out_of_range"),
        # A criterion the item's guide entry does not code.
        ((sentence("quote-lacks", quote=(0, 5), criterion="X9"),), True, "unknown_criterion"),
        # A template that is not approved, and one given the wrong slots.
        ((sentence("quote-praise", quote=(0, 5), criterion="F1"),), True, "unknown_template"),
        ((sentence("quote-lacks", quote=(0, 5)),), True, "wrong_arity"),
        ((sentence("missing", criterion="F1", quote=(0, 5)),), True, "wrong_arity"),
        (
            (
                sentence("quote-lacks", quote=(0, 5), criterion="F1"),
                sentence("narration-supply-line", fact_ids=("moment:retailer:3",), criterion="F1"),
            ),
            True,
            "wrong_arity",
        ),
        # No sentence quotes the answer.
        ((sentence("missing", criterion="F1"),), True, "no_quote"),
        # The same sentence twice.
        (
            (
                sentence("quote-lacks", quote=(0, 5), criterion="F1"),
                sentence("quote-lacks", quote=(0, 5), criterion="F1"),
            ),
            True,
            "repeated",
        ),
        # A fact of another Seat, a fact on an item with no facts set (a long answer).
        (
            (
                sentence("quote-lacks", quote=(0, 5), criterion="F1"),
                sentence("narration-supply-line", fact_ids=("moment:factory:3",)),
            ),
            True,
            "unknown_fact",
        ),
        (
            (
                sentence("quote-lacks", quote=(0, 5), criterion="F1"),
                sentence("narration-supply-line", fact_ids=("moment:retailer:3",)),
            ),
            False,
            "unknown_fact",
        ),
        # A fact sentence with the wrong number of facts (Epic 9's validator).
        (
            (
                sentence("quote-lacks", quote=(0, 5), criterion="F1"),
                sentence("narration-orders", fact_ids=("moment:retailer:3",)),
            ),
            True,
            "wrong_arity",
        ),
    ],
)
def test_feedback_outside_the_answer_the_guide_or_the_facts_is_rejected(sentences, facts, reason):
    verdict = check(out(*sentences), facts=facts)
    assert not verdict.accepted and verdict.reason == reason


def test_the_output_schema_holds_one_score_and_references_only():
    with pytest.raises(ValidationError):
        AssessmentFeedbackOutput(score=5, feedback=(sentence("missing", criterion="F1"),))
    with pytest.raises(ValidationError):
        AssessmentFeedbackOutput(score=2, feedback=())
    five = tuple(sentence("missing", criterion=f"F{n}") for n in range(1, 6))
    assert len(five) == feedback.MAX_FEEDBACK_SENTENCES + 1
    with pytest.raises(ValidationError):
        AssessmentFeedbackOutput(score=2, feedback=five)
    with pytest.raises(ValidationError):
        AssessmentFeedbackOutput.model_validate(
            {"score": 2, "feedback": [{"template_id": "missing", "text": "fritt skrevet"}]}
        )
    with pytest.raises(ValidationError):
        AssessmentFeedbackOutput.model_validate(
            {"score": 2, "criteria": {"F1": 3}, "feedback": [{"template_id": "missing"}]}
        )
    schema = AssessmentFeedbackOutput.model_json_schema()
    assert set(schema["properties"]) == {"score", "feedback"}


def test_feedback_templates_hold_no_digit_and_list_for_the_prompt():
    assert not any(
        any(c.isdigit() for c in text) for text, _ in feedback.FEEDBACK_TEMPLATES.values()
    )
    lines = feedback.template_lines(TEMPLATES).splitlines()
    assert lines[0].startswith("quote-covers (criterion, quote): ")
    assert any(line.startswith("narration-supply-line (1): ") for line in lines)
    assert not any(
        line.startswith("narration-") for line in feedback.template_lines(None).splitlines()
    )
