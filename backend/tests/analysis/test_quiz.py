"""Story 9.9: the Debrief quiz's shape, its scoring by answer key and the own-game sentence of an
explanation, rendered from a stored facts set (FR-46, AD-1, AD-7, AD-23)."""

import copy
import importlib.util
import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.analysis import quiz as rules
from app.analysis.facts import FactSet
from app.modules.content.schemas import DebriefQuiz

ROOT = Path(__file__).parents[2]
MIGRATION = ROOT / "migrations" / "versions" / "0108_debrief_quiz.py"
GOLDEN = ROOT / "tests" / "golden" / "facts" / "takeover.json"


def _version_1() -> dict:
    spec = importlib.util.spec_from_file_location("migration_0108", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.DEBRIEF_QUIZ_V1


V1 = _version_1()
QUIZ = DebriefQuiz.model_validate(V1)
RIGHT = [(q.id, q.answer) for q in QUIZ.questions]


def golden(role: str = "retailer") -> FactSet:
    return FactSet.model_validate(json.loads(GOLDEN.read_text(encoding="utf-8"))[role]["facts"])


def test_version_one_is_a_marked_placeholder_with_three_questions():
    assert QUIZ.placeholder is True
    assert [q.id for q in QUIZ.questions] == ["posisjon", "forsinkelse", "forsterkning"]
    for question in QUIZ.questions:
        assert question.answer in {c.id for c in question.choices}
        assert "kolonne" in (question.in_your_game or "") or question.id == "forsterkning"


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        (lambda b: b["questions"][0].update(answer="nope"), "not one of its choices"),
        (lambda b: b["questions"][0]["choices"].append({"id": "netto", "text": "x"}), "repeat"),
        (lambda b: b["questions"][1].update(id="posisjon"), "question ids repeat"),
        (lambda b: b["questions"][0].update(prompt="Hva!"), "exclamation"),
        (lambda b: b["questions"][0].update(explanation="Uke {weeks}."), "no slots"),
        (lambda b: b["questions"][0].update(in_your_game="Uke {navn}."), "unknown value"),
        (lambda b: b["questions"][0].update(in_your_game="Uke {weeks:>3}."), "unknown value"),
        (lambda b: b["questions"][0].update(choices=[{"id": "a", "text": "A"}]), "at least 2"),
        (lambda b: b.update(questions=[]), "at least 1"),
    ],
)
def test_a_malformed_quiz_is_refused(change, reason):
    body = copy.deepcopy(V1)
    change(body)
    with pytest.raises(ValidationError, match=reason):
        DebriefQuiz.model_validate(body)


def test_scoring_is_by_answer_key_in_the_order_shown():
    shown = list(reversed(RIGHT))
    scored = rules.score(QUIZ, [q for q, _ in RIGHT], shown)
    assert scored.passed is True
    assert [(a.question_id, a.correct) for a in scored.answers] == [(q, True) for q, _ in shown]

    wrong = [("posisjon", "netto"), *RIGHT[1:]]
    scored = rules.score(QUIZ, [q for q, _ in RIGHT], wrong)
    assert scored.passed is False
    assert [a.correct for a in scored.answers] == [False, True, True]
    assert scored.answers[0].choice_id == "netto"


@pytest.mark.parametrize(
    ("answers", "reason"),
    [
        (RIGHT[:2], "incomplete"),
        ([*RIGHT, RIGHT[0]], "incomplete"),
        ([*RIGHT[:2], ("annet", "x")], "incomplete"),
        ([("posisjon", "ukjent"), *RIGHT[1:]], "unknown_choice"),
    ],
)
def test_an_attempt_that_cannot_be_scored_is_refused(answers, reason):
    with pytest.raises(rules.WrongAnswers) as refused:
        rules.score(QUIZ, [q for q, _ in RIGHT], answers)
    assert refused.value.reason == reason


def test_the_own_game_sentence_is_filled_from_the_facts_set():
    facts = golden("retailer")
    own = next(r for r in facts.chain.by_role if r.role == "retailer")
    factory = next(r for r in facts.chain.by_role if r.role == "factory")
    posisjon, forsinkelse, forsterkning = QUIZ.questions

    first = min(m.week for m in facts.seat.moments)
    rendered = rules.render_in_your_game(facts, posisjon)
    assert rendered is not None
    assert rendered.text == (
        f"Ditt første øyeblikk var Uke {first}. Det står i kolonne {first} i din egen tabell."
    )
    assert rendered.template_id == "quiz:posisjon"

    week = own.first_large_order_week
    assert week is not None
    text = rules.render_in_your_game(facts, forsinkelse).text
    assert text == (
        f"Din første ordre på 10 eller mer kom i Uke {week}. "
        f"Det står i kolonne {week} i din egen tabell."
    )

    assert factory.amplification is not None
    rounded = factory.amplification.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    written = f"{rounded:f}".replace(".", ",")
    assert rules.render_in_your_game(facts, forsterkning).text == (
        f"I ditt spill var Forsterkningen hos Fabrikken {written}."
    )


def test_a_missing_value_leaves_the_sentence_out():
    facts = golden("retailer")
    none_seat = facts.model_copy(
        update={"seat": facts.seat.model_copy(update={"moments": ()})}, deep=True
    )
    assert rules.render_in_your_game(none_seat, QUIZ.questions[0]) is None
    flat = facts.model_copy(
        update={
            "chain": facts.chain.model_copy(
                update={
                    "by_role": tuple(
                        r.model_copy(update={"amplification": None, "first_large_order_week": None})
                        for r in facts.chain.by_role
                    )
                }
            )
        },
        deep=True,
    )
    assert rules.render_in_your_game(flat, QUIZ.questions[1]) is None
    assert rules.render_in_your_game(flat, QUIZ.questions[2]) is None
    bare = QUIZ.questions[0].model_copy(update={"in_your_game": None})
    assert rules.render_in_your_game(facts, bare) is None


def test_every_value_is_written_as_the_web_app_writes_it():
    facts = golden("wholesaler")
    values = {name: read(facts) for name, read in rules.QUIZ_VALUES.items()}
    assert values["weeks"] == str(facts.chain.weeks)
    assert values["chain_total_cost"] is not None and "," in values["chain_total_cost"]
    assert values["own_amplification"] == "5,4"  # 5.426, one decimal half up
    assert values["factory_amplification"] == "21,3"
    assert values["own_first_large_order_week"] == "7"
    assert values["first_moment_week"] is None
