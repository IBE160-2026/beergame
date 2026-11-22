"""Story 9.14: AI text that only connects computed facts (FR-44, AD-1, AD-7, NFR-9).

Golden tests of `analysis.validate_ai_text` (an accepted output and one rejection of each kind)
and of the code narration `analysis.render`, on the hand-built facts set of the moments' tests
(moments in Weeks 3, 9 and 10 of a Retailer)."""

import importlib.util
from pathlib import Path

import pytest
from pydantic import ValidationError

from app import analysis
from app.analysis import narration
from app.analysis.facts import facts
from app.analysis.narration import AiSentence, AiTextOutput, NarrationTemplates
from tests.analysis.test_facts import PATTERNS, log, student
from tests.analysis.test_moments import scenario

MIGRATION = Path(__file__).parents[2] / "migrations" / "versions" / "0112_debrief_narration.py"


def _version_1() -> dict:
    spec = importlib.util.spec_from_file_location("migration_0112", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.NARRATION_TEMPLATES_V1


V1 = _version_1()
TEMPLATES = NarrationTemplates.model_validate(V1)


def output(*sentences: tuple[str, tuple[str, ...]]) -> AiTextOutput:
    return AiTextOutput(
        sentences=tuple(AiSentence(template_id=t, fact_ids=ids) for t, ids in sentences)
    )


def test_version_1_holds_every_template():
    assert {t.id for t in TEMPLATES.templates} == set(narration.NARRATION_TEMPLATES)


def test_an_output_citing_own_facts_with_pinned_templates_is_accepted_and_rendered_by_code():
    built = scenario()
    verdict = analysis.validate_ai_text(
        output(
            ("narration-orders", ("moment:retailer:3", "moment:retailer:9")),
            ("narration-later-cost", ("moment:retailer:3",)),
            ("narration-weeks", ("moment:retailer:3", "moment:retailer:9", "moment:retailer:10")),
        ),
        built,
        TEMPLATES,
    )
    assert verdict.accepted and verdict.reason is None
    assert verdict.text == (
        "I Uke 3 bestilte du 12 da ordren inn var 4, og i Uke 9 bestilte du 12 da ordren inn "
        "var 4. Etter Uke 3: i Uke 4 til 7 kostet leddet ditt 25,00 kr. "
        "Øyeblikkene dine ligger i Uke 3, 9 og 10."
    )
    # A Detected pattern occurrence of the Seat is citable too.
    pattern = built.seat.patterns[0]
    cited = analysis.validate_ai_text(
        output(("narration-supply-line", (pattern.id,))), built, TEMPLATES
    )
    assert cited.accepted
    assert cited.text == (
        f"Da du bestilte {pattern.order} i Uke {pattern.week}, "
        f"var {pattern.state_seen.supply_line} allerede på vei."
    )


@pytest.mark.parametrize(
    ("sentences", "reason"),
    [
        # Another Seat's moment, and an id that is no fact at all.
        ((("narration-supply-line", ("moment:factory:3",)),), "unknown_fact"),
        ((("narration-supply-line", ("chain:total_cost",)),), "unknown_fact"),
        # A template the pinned version does not hold.
        ((("narration-because", ("moment:retailer:3",)),), "unknown_template"),
        # A template given more or fewer facts than it takes.
        ((("narration-orders", ("moment:retailer:3",)),), "wrong_arity"),
        # One fact twice in a sentence, and one sentence twice.
        ((("narration-orders", ("moment:retailer:3", "moment:retailer:3")),), "repeated"),
        (
            (
                ("narration-supply-line", ("moment:retailer:3",)),
                ("narration-supply-line", ("moment:retailer:3",)),
            ),
            "repeated",
        ),
    ],
)
def test_an_output_outside_the_facts_or_the_templates_is_rejected(sentences, reason):
    verdict = analysis.validate_ai_text(output(*sentences), scenario(), TEMPLATES)
    assert verdict == narration.Verdict(accepted=False, reason=reason)


def test_a_number_the_cited_facts_do_not_hold_is_rejected():
    """A template version whose text holds a literal number (or a slot of another fact) gives a
    number outside the rendered facts: rejected."""
    body = {
        "templates": [
            t
            if t["id"] != "narration-later-cost"
            else {**t, "text": "I 9 uker etter Uke {week_1} kostet leddet ditt {later_cost_1} kr."}
            for t in V1["templates"]
        ]
    }
    templates = NarrationTemplates.model_validate(body)
    verdict = analysis.validate_ai_text(
        output(("narration-later-cost", ("moment:retailer:3",))), scenario(), templates
    )
    assert verdict == narration.Verdict(accepted=False, reason="number_outside_facts")


def test_the_later_cost_sentence_needs_following_weeks_to_name():
    """A moment in the Game's last Uke (or the one before) has no range of later Uker to name."""
    built = scenario()
    last = built.seat.moments[-1].model_copy(update={"later_weeks": 1})
    moments = (*built.seat.moments[:-1], last)
    short = built.model_copy(update={"seat": built.seat.model_copy(update={"moments": moments})})
    verdict = analysis.validate_ai_text(
        output(("narration-later-cost", (last.id,))), short, TEMPLATES
    )
    assert verdict == narration.Verdict(accepted=False, reason="not_applicable")


def test_the_code_narration_connects_the_first_moments_and_the_largest_supply_line():
    built = scenario()
    rendered = analysis.render(built, TEMPLATES)
    assert rendered is not None
    assert rendered.text == (
        "I Uke 3 bestilte du 12 da ordren inn var 4, og i Uke 9 bestilte du 12 da ordren inn "
        "var 4. Da du bestilte 12 i Uke 3, var 16 allerede på vei."
    )
    # The code's own choice is an output the validator accepts, with the same text (the mock
    # answers with it).
    own = narration.code_output(built)
    assert own is not None
    assert analysis.validate_ai_text(own, built, TEMPLATES).text == rendered.text
    assert analysis.render(built, TEMPLATES) == rendered  # pure


def test_a_seat_played_mostly_by_ai_players_has_no_narration():
    built = facts(log(12, student(range(1, 10))), "retailer", PATTERNS)
    assert analysis.render(built, TEMPLATES) is None
    assert narration.code_output(built) is None


@pytest.mark.parametrize(
    "text",
    [
        "Uke {week_1} og {week_2}.",  # a fact left unused
        "Uke {week_1}, {week_2}, {week_3} og {name_1}.",  # an unknown value
        "Uke {week_1}, {week_2} og {week_4}.",  # a fact the template does not take
        "Uke {week_1}, {week_2} og {week_3} fordi det gikk slik.",  # a cause
    ],
)
def test_templates_use_each_cited_fact_and_state_no_cause(text):
    body = {
        "templates": [
            t if t["id"] != "narration-weeks" else {**t, "text": text} for t in V1["templates"]
        ]
    }
    with pytest.raises(ValidationError):
        NarrationTemplates.model_validate(body)


def test_the_output_schema_holds_template_and_fact_ids_only():
    schema = AiTextOutput.model_json_schema()
    sentence = schema["$defs"]["AiSentence"]["properties"]
    assert set(sentence) == {"template_id", "fact_ids"}
    assert schema["properties"]["sentences"]["maxItems"] == narration.MAX_SENTENCES
