"""Story 11.7: the Adapted item templates and their code-rendered text (FR-53, AD-7).

Each rule on a hand-built Decision log (the helpers of `test_facts.py`); the golden test on played
Games is `tests/individual_test/test_adapted.py`."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.analysis.adapted import (
    AdaptedTemplate,
    AdaptedTemplates,
    apportion,
    fill,
    render_wording,
    validate_wording,
)
from app.analysis.facts import facts
from app.analysis.narration import AiSentence, AiTextOutput
from tests.analysis.test_facts import PATTERNS, log, student

SHIPPED = Path(__file__).parents[2] / "app" / "modules" / "content" / "files"
NAMES = {pattern.id: pattern.name for pattern in PATTERNS.patterns}


def template(**changes) -> dict:
    return {
        "id": "tilpasset-x",
        "source": "game",
        "fact": "moment",
        "share": 100,
        "text": "Uke {week}: du bestilte {order} enheter som {role}.",
    } | changes


def test_the_shipped_templates_are_a_draft_with_shares_of_100():
    shipped = AdaptedTemplates.model_validate_json(
        (SHIPPED / "adapted_templates.json").read_text(encoding="utf-8")
    )
    assert shipped.status == "draft"
    assert [(t.id, t.source, t.fact) for t in shipped.templates] == [
        ("tilpasset-eget-spill", "game", "moment"),
        ("tilpasset-replay", "replay", "outcome"),
    ]
    # Every template has its Scoring guide question (Story 11.2), and the guide no other.
    guide = json.loads((SHIPPED / "scoring_guide.json").read_text(encoding="utf-8"))
    adapted = {q["id"] for q in guide["questions"] if q["kind"] == "adapted"}
    assert adapted == {t.id for t in shipped.templates}
    # No template id is a question set item id: the frozen list holds both.
    questions = json.loads((SHIPPED / "question_set.json").read_text(encoding="utf-8"))
    ids = {i["id"] for i in (*questions["items"], *questions["replacements"])}
    assert not ids & {t.id for t in shipped.templates}


@pytest.mark.parametrize(
    ("changes", "why"),
    [
        ({"text": "Uke {week}: {total_cost}"}, "a value its kind does not give"),
        ({"text": "Du bestilte {order} enheter."}, "the moment's Week left out"),
        ({"fact": "pattern", "text": "Uke {week}, ordre {order}."}, "the pattern left out"),
        ({"fact": "outcome", "text": "Du var {role}."}, "the outcome's cost left out"),
        ({"text": "Uke {week}: {order:>3}"}, "a format spec"),
        ({"text": "Uke {week}: {order!r}"}, "a conversion"),
        ({"text": "Uke {week}: {order} {"}, "a broken slot"),
        ({"text": "Uke {week}: {order}!"}, "an exclamation mark"),
        ({"pick": 4}, "a pick past the three moments"),
        ({"share": 0}, "a share of 0"),
        ({"source": "debrief"}, "an unknown Game"),
        ({"fact": "week"}, "an unknown fact kind"),
    ],
)
def test_a_template_that_breaks_a_rule_is_refused(changes, why):
    with pytest.raises(ValidationError):
        AdaptedTemplate.model_validate(template(**changes))


def test_ids_repeat_and_shares_off_100_are_refused():
    with pytest.raises(ValidationError, match="repeat"):
        AdaptedTemplates.model_validate(
            {"status": "draft", "templates": [template(share=50), template(share=50)]}
        )
    with pytest.raises(ValidationError, match="sum to 100"):
        AdaptedTemplates.model_validate({"status": "draft", "templates": [template(share=60)]})


@pytest.mark.parametrize(
    ("total", "shares", "parts"),
    [
        (30, [50, 50], [15, 15]),
        (25, [50, 50], [13, 12]),
        (25, [15, 15], [13, 12]),
        (10, [1, 1, 1], [4, 3, 3]),
        (7, [20, 30, 50], [1, 2, 4]),
        (0, [50, 50], [0, 0]),
        (100, [1], [100]),
    ],
)
def test_apportion_gives_whole_weights_that_sum_to_the_total(total, shares, parts):
    assert apportion(total, shares) == parts
    assert sum(parts) == total


def test_apportion_refuses_no_shares():
    for shares in ([], [0, 0], [-1, 2]):
        with pytest.raises(ValueError):
            apportion(10, shares)


def played() -> object:
    """Twelve Student Weeks of the Detaljist: a surge in Week 3 (the highest later cost) and Week
    9, gap moments elsewhere; the Rule-based Week 7 surge is not the Student's."""
    changes = student(range(1, 13))
    changes[(3, "retailer")] |= {"order": 12, "backlog": 1, "incoming_order": 5}
    changes[(4, "retailer")] |= {"backlog": 1}
    changes[(8, "retailer")] |= {"order": 2}
    changes[(10, "retailer")] |= {"order": 1}
    changes[(9, "retailer")] |= {"order": 12, "backlog": 1}
    changes[(7, "retailer")] = {"order": 20, "backlog": 1}
    return facts(log(12, changes), "retailer", PATTERNS)


def test_a_moment_template_takes_the_moment_with_the_highest_later_cost():
    built = played()
    first = fill(AdaptedTemplate.model_validate(template()), built, NAMES)
    assert first is not None
    assert first.fact_ids == ("moment:retailer:3",)
    assert first.text == "Uke 3: du bestilte 12 enheter som Detaljist."
    later = sorted(built.seat.moments, key=lambda m: (-m.later_cost, m.week))
    second = fill(AdaptedTemplate.model_validate(template(pick=2)), built, NAMES)
    assert second is not None and second.fact_ids == (later[1].id,)
    seen = template(
        text="Uke {week}: {incoming_order} inn, {inventory} på lager, {backlog} "
        "i restordre, {supply_line} på vei, {order} bestilt."
    )
    filled = fill(AdaptedTemplate.model_validate(seen), built, NAMES)
    assert filled is not None
    assert filled.text == "Uke 3: 5 inn, 12 på lager, 1 i restordre, 16 på vei, 12 bestilt."


def test_a_pattern_template_takes_only_the_students_own_occurrences():
    built = played()
    text = "I uke {week} viste ordren på {order} mønsteret «{pattern}»."
    filled = fill(AdaptedTemplate.model_validate(template(fact="pattern", text=text)), built, NAMES)
    assert filled is not None
    assert filled.fact_ids == ("surge-after-shortage:retailer:3",)
    assert filled.text == f"I uke 3 viste ordren på 12 mønsteret «{NAMES['surge-after-shortage']}»."
    third = template(fact="pattern", text=text, pick=3)  # the Week 7 surge is Rule-based
    assert fill(AdaptedTemplate.model_validate(third), built, NAMES) is None
    assert (
        fill(AdaptedTemplate.model_validate(template(fact="pattern", text=text)), built, {}) is None
    )


def test_an_outcome_template_writes_the_seats_cost_in_kroner():
    built = played()
    text = "Som {role} i {weeks} uker: {total_cost} kr ({holding_cost} + {backorder_cost})."
    filled = fill(AdaptedTemplate.model_validate(template(fact="outcome", text=text)), built, NAMES)
    entry = next(r for r in built.chain.by_role if r.role == "retailer")
    assert filled is not None and filled.fact_ids == ("outcome:retailer",)
    total = f"{entry.total_cost:.2f}".replace(".", ",")
    holding = f"{entry.holding_cost:.2f}".replace(".", ",")
    backorder = f"{entry.backorder_cost:.2f}".replace(".", ",")
    assert filled.text == f"Som Detaljist i 12 uker: {total} kr ({holding} + {backorder})."


def test_fewer_than_ten_student_orders_leave_a_moment_template_unfilled():
    built = facts(log(12, student(range(1, 10))), "retailer", PATTERNS)
    assert fill(AdaptedTemplate.model_validate(template()), built, NAMES) is None


# Story 11.8: the wordings an LLM may choose from, and the validator of its choice.

SHORT = {"id": "tilpasset-x-kort", "text": "I uke {week} bestilte du {order} enheter som {role}."}


@pytest.mark.parametrize(
    ("wording", "why"),
    [
        ({"id": "x-1", "text": "Du bestilte {order} enheter som {role}."}, "the Week left out"),
        ({"id": "x-1", "text": "Uke {week}: du bestilte {order}."}, "a template value left out"),
        ({"id": "x-1", "text": "Uke {week}: {order} som {role}, {backlog}."}, "a value added"),
        ({"id": "x-1", "text": "Uke {week}: {order}, {role}, {total_cost}"}, "a value it lacks"),
        ({"id": "x-1", "text": "Uke {week}: {order} som {role}!"}, "an exclamation mark"),
        ({"id": "X 1", "text": "Uke {week}: {order} som {role}"}, "an id that is not a slug"),
    ],
)
def test_a_wording_keeps_the_rules_of_its_template(wording, why):
    with pytest.raises(ValidationError):
        AdaptedTemplate.model_validate(template(wordings=[wording]))


def test_wording_ids_are_unique_in_the_whole_record_and_at_most_four_per_template():
    twice = template(wordings=[SHORT, SHORT])
    with pytest.raises(ValidationError, match="repeat"):
        AdaptedTemplates.model_validate({"status": "draft", "templates": [twice]})
    named_as_template = template(wordings=[{**SHORT, "id": "tilpasset-x"}])
    with pytest.raises(ValidationError, match="repeat"):
        AdaptedTemplates.model_validate({"status": "draft", "templates": [named_as_template]})
    five = [{**SHORT, "id": f"x-{n}"} for n in range(5)]
    with pytest.raises(ValidationError):
        AdaptedTemplate.model_validate(template(wordings=five))
    # Version 1 had none: still valid.
    assert AdaptedTemplate.model_validate(template()).wordings == ()


def test_the_shipped_wordings_are_drafts_with_the_templates_facts():
    """Each shipped template has draft wordings; the schema has checked that each uses exactly
    its template's values (the same facts for every Student, FR-53)."""
    shipped = AdaptedTemplates.model_validate_json(
        (SHIPPED / "adapted_templates.json").read_text(encoding="utf-8")
    )
    for each in shipped.templates:
        assert 2 <= len(each.wordings) <= 4
        assert all(w.text.startswith("Utkast:") and w.text != each.text for w in each.wordings)


def choice(template_id: str, *fact_ids: str) -> AiTextOutput:
    return AiTextOutput(sentences=(AiSentence(template_id=template_id, fact_ids=fact_ids),))


def test_a_chosen_wording_is_rendered_by_code_from_the_items_fact():
    built = played()
    moment = AdaptedTemplate.model_validate(template(wordings=[SHORT]))
    verdict = validate_wording(
        choice(SHORT["id"], "moment:retailer:3"), moment, built, NAMES, ("moment:retailer:3",)
    )
    assert verdict.accepted and verdict.text == "I uke 3 bestilte du 12 enheter som Detaljist."
    rendered = render_wording(moment, SHORT["id"], built, NAMES)
    assert rendered is not None and rendered.text == verdict.text
    # The outcome kind: its fact is `outcome:<role>`, not a moment.
    text = "Kostnaden ble {total_cost} kr."
    outcome = AdaptedTemplate.model_validate(
        template(fact="outcome", text=text, wordings=[{"id": "x-1", "text": f"Utkast: {text}"}])
    )
    accepted = validate_wording(
        choice("x-1", "outcome:retailer"), outcome, built, NAMES, ("outcome:retailer",)
    )
    assert accepted.accepted and accepted.text and accepted.text.startswith("Utkast: Kostnaden")


@pytest.mark.parametrize(
    ("output", "frozen", "reason"),
    [
        (choice("tilpasset-x-kort", "moment:retailer:9"), "moment:retailer:3", "unknown_fact"),
        (choice("tilpasset-x-kort", "moment:retailer:9"), "moment:retailer:9", "unknown_fact"),
        (choice("tilpasset-x", "moment:retailer:3"), "moment:retailer:3", "unknown_template"),
        (choice("narration-orders", "moment:retailer:3"), "moment:retailer:3", "unknown_template"),
        (choice("x-tall", "moment:retailer:3"), "moment:retailer:3", "number_outside_facts"),
    ],
)
def test_a_choice_outside_the_items_fact_or_wordings_is_rejected(output, frozen, reason):
    built = played()
    numbered = {"id": "x-tall", "text": "I uke {week} av 52 bestilte {role} {order} enheter."}
    moment = AdaptedTemplate.model_validate(template(wordings=[SHORT, numbered]))
    verdict = validate_wording(output, moment, built, NAMES, (frozen,))
    assert (verdict.accepted, verdict.reason, verdict.text) == (False, reason, None)


def test_two_sentences_are_rejected():
    built = played()
    moment = AdaptedTemplate.model_validate(template(wordings=[SHORT]))
    sentence = AiSentence(template_id=SHORT["id"], fact_ids=("moment:retailer:3",))
    two = AiTextOutput(sentences=(sentence, sentence))
    verdict = validate_wording(two, moment, built, NAMES, ("moment:retailer:3",))
    assert verdict.reason == "wrong_arity"


def test_a_pattern_wording_names_the_pattern_of_the_students_own_occurrence():
    built = played()
    text = "I uke {week} viste ordren på {order} mønsteret «{pattern}»."
    wording = {"id": "x-1", "text": "Mønsteret «{pattern}» viste seg i uke {week}: {order}."}
    pattern = AdaptedTemplate.model_validate(
        template(fact="pattern", text=text, wordings=[wording])
    )
    fact = ("surge-after-shortage:retailer:3",)
    verdict = validate_wording(choice("x-1", *fact), pattern, built, NAMES, fact)
    name = NAMES["surge-after-shortage"]
    assert verdict.accepted and verdict.text == f"Mønsteret «{name}» viste seg i uke 3: 12."
    # Without the pattern's name the fact is not the template's: rejected.
    assert validate_wording(choice("x-1", *fact), pattern, built, {}, fact).reason == "unknown_fact"
