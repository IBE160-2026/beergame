"""Story 9.15: a follow-up answer only declines or hints, and hints only connect computed facts
(FR-45, AD-1, AD-7, NFR-9).

Golden tests of `analysis.follow_up.validate_follow_up` and of the mock's answer on the
hand-built facts set of the moments' tests (moments in Weeks 3, 9 and 10 of a Retailer), with
version 2 of the narration templates as migration 0113 stores it. No database."""

import importlib.util
from pathlib import Path

import pytest

from app.analysis import follow_up, narration
from app.analysis.facts import facts
from app.analysis.narration import AiSentence, NarrationTemplates
from tests.analysis.test_facts import PATTERNS, log, student
from tests.analysis.test_moments import scenario
from tests.analysis.test_narration import TEMPLATES as V1_TEMPLATES

MIGRATION = Path(__file__).parents[2] / "migrations" / "versions" / "0113_debrief_follow_up.py"


def _version_2() -> dict:
    spec = importlib.util.spec_from_file_location("migration_0113", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.NARRATION_TEMPLATES_V2


V2 = NarrationTemplates.model_validate(_version_2())
BUILT = scenario()


def answer(*sentences: tuple[str, tuple[str, ...]], decline: bool = False):
    return follow_up.FollowUpOutput(
        decline=decline,
        sentences=tuple(AiSentence(template_id=t, fact_ids=ids) for t, ids in sentences),
    )


def test_version_2_holds_the_narration_and_every_hint():
    assert {t.id for t in V2.templates} == set(narration.TEMPLATE_FACTS)
    assert V2.has_hints() and not V1_TEMPLATES.has_hints()
    # Version 1's narration sentences are unchanged in version 2.
    for template in V1_TEMPLATES.templates:
        assert V2.text_of(template.id) == template.text


def test_hints_citing_own_facts_are_accepted_and_rendered_by_code():
    verdict = follow_up.validate_follow_up(
        answer(
            ("hint-row", ("moment:retailer:3",)),
            ("hint-later", ("moment:retailer:3",)),
            ("hint-compare", ("moment:retailer:3", "moment:retailer:9")),
        ),
        BUILT,
        V2,
    )
    assert verdict == follow_up.FollowUpVerdict(
        accepted=True,
        text=(
            "Se på raden for Uke 3: der bestilte du 12, og ordren inn var 4. "
            "Følg kostnaden etter Uke 3: i Uke 4 til 7 kostet leddet ditt 25,00 kr. "
            "Sammenlign Uke 3 og Uke 9: du bestilte 12 og 12, og ordren inn var 4 og 4."
        ),
    )
    supply = follow_up.validate_follow_up(
        answer(("hint-supply-line", ("moment:retailer:3",))), BUILT, V2
    )
    assert supply.text == "Se på kolonnen På vei i Uke 3: 16 var allerede på vei da du bestilte 12."


def test_a_decline_carries_no_sentence():
    assert follow_up.validate_follow_up(answer(decline=True), BUILT, V2) == (
        follow_up.FollowUpVerdict(accepted=True, declined=True)
    )


@pytest.mark.parametrize(
    ("output", "reason"),
    [
        # A decline that also hints, and an answer with nothing in it.
        (answer(("hint-row", ("moment:retailer:3",)), decline=True), "inconsistent"),
        (answer(), "empty"),
        # A narration sentence states rather than points: never in a follow-up answer.
        (answer(("narration-supply-line", ("moment:retailer:3",))), "unknown_template"),
        # Another Seat's fact, a wrong count, a repeat.
        (answer(("hint-row", ("moment:factory:3",))), "unknown_fact"),
        (answer(("hint-compare", ("moment:retailer:3",))), "wrong_arity"),
        (answer(("hint-compare", ("moment:retailer:3", "moment:retailer:3"))), "repeated"),
    ],
)
def test_anything_but_a_clean_decline_or_hints_is_rejected(output, reason):
    verdict = follow_up.validate_follow_up(output, BUILT, V2)
    assert verdict == follow_up.FollowUpVerdict(accepted=False, reason=reason)


def test_a_session_on_version_1_has_no_hints_to_give():
    verdict = follow_up.validate_follow_up(
        answer(("hint-row", ("moment:retailer:3",))), BUILT, V1_TEMPLATES
    )
    assert verdict.reason == "unknown_template"


def test_the_narration_never_cites_a_hint():
    verdict = narration.validate_ai_text(
        narration.AiTextOutput(sentences=(AiSentence(template_id="hint-row", fact_ids=("x",)),)),
        BUILT,
        V2,
    )
    assert verdict.reason == "unknown_fact"
    verdict = narration.validate_ai_text(
        narration.AiTextOutput(
            sentences=(AiSentence(template_id="hint-row", fact_ids=("moment:retailer:3",)),)
        ),
        BUILT,
        V2,
    )
    assert verdict.reason == "unknown_template"


def test_the_later_hint_needs_following_weeks_and_numbers_stay_the_facts():
    last = BUILT.seat.moments[-1].model_copy(update={"later_weeks": 1})
    short = BUILT.model_copy(
        update={"seat": BUILT.seat.model_copy(update={"moments": (*BUILT.seat.moments[:-1], last)})}
    )
    verdict = follow_up.validate_follow_up(answer(("hint-later", (last.id,))), short, V2)
    assert verdict.reason == "not_applicable"
    literal = NarrationTemplates.model_validate(
        {
            "templates": [
                t.model_dump()
                if t.id != "hint-row"
                else {"id": "hint-row", "text": "Se på Uke {week_1} og de 99 neste: {order_1}."}
                for t in V2.templates
            ]
        }
    )
    verdict = follow_up.validate_follow_up(
        answer(("hint-row", ("moment:retailer:3",))), BUILT, literal
    )
    assert verdict.reason == "number_outside_facts"


def test_the_mock_declines_a_question_outside_the_game_and_hints_otherwise():
    declined = follow_up.mock_output("Hva er hovedstaden i Frankrike?", BUILT)
    assert declined == answer(decline=True)
    hinted = follow_up.mock_output("Hvorfor bestilte jeg så mye i uke 3?", BUILT)
    assert hinted == answer(("hint-row", ("moment:retailer:3",)))
    assert follow_up.validate_follow_up(hinted, BUILT, V2).accepted
    # A Seat played mostly by AI players has nothing to point to.
    mostly_ai = facts(log(12, student(range(1, 10))), "retailer", PATTERNS)
    assert follow_up.mock_output("Hva skjedde i uke 3?", mostly_ai) == answer(decline=True)


def test_the_output_schema_holds_a_decline_flag_and_ids_only():
    schema = follow_up.FollowUpOutput.model_json_schema()
    assert set(schema["properties"]) == {"decline", "sentences"}
    assert schema["properties"]["sentences"]["maxItems"] == narration.MAX_SENTENCES
