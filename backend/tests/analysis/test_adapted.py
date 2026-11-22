"""Story 11.7: the Adapted item templates and their code-rendered text (FR-53, AD-7).

Each rule on a hand-built Decision log (the helpers of `test_facts.py`); the golden test on played
Games is `tests/individual_test/test_adapted.py`."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.analysis.adapted import AdaptedTemplate, AdaptedTemplates, apportion, fill
from app.analysis.facts import facts
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
