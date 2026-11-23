"""`analysis.scoring` (AD-1): the Starting task's `score_sum` (Story 6.3, FR-85), the Individual
test's `score_choice` (Story 11.4, FR-52) and `score_interactive` (Story 11.5, FR-80)."""

import pytest
from pydantic import ValidationError

from app.analysis.scoring import (
    BalanceCheck,
    CellCheck,
    ChoiceScore,
    Criterion,
    FlowCheck,
    InteractiveRule,
    InteractiveScore,
    SumScore,
    score_choice,
    score_interactive,
    score_sum,
)

POSITION = [(1, 0), (-1, 13), (1, 16)]  # Lager 0 − Restordre 13 + På vei 16


def test_a_right_and_a_wrong_answer_to_the_position():
    assert score_sum(POSITION, 3) == SumScore(expected=3, correct=True)
    assert score_sum(POSITION, 29) == SumScore(expected=3, correct=False)


def test_a_negative_sum_and_a_bad_sign():
    assert score_sum([(1, 0), (-1, 13)], -13).correct
    with pytest.raises(ValueError):
        score_sum([(2, 1)], 2)


def test_a_right_a_wrong_and_an_unanswered_choice():
    assert score_choice("b", "b") == ChoiceScore(answered=True, correct=True, credit=1.0)
    assert score_choice("c", "b") == ChoiceScore(answered=True, correct=False, credit=0.0)
    assert score_choice(None, "b") == ChoiceScore(answered=False, correct=False, credit=0.0)


# Interactive items (Story 11.5, FR-80): golden cases of `score_interactive`.

STOCK = InteractiveRule(  # a bakery: 10 units before Uke 1, then in and out per Uke
    labels=("Uke 1", "Uke 2", "Uke 3", "Uke 4"),
    columns={"inn": (20, 20, 25, 25), "ut": (22, 24, 20, 18)},
    criteria=(
        Criterion(
            code="K1",
            weight=50,
            check=FlowCheck(kind="flow", inflow="inn", outflow="ut", start=10),
        ),
        Criterion(code="K2", weight=30, check=CellCheck(kind="cell", row=3, value=16)),
        Criterion(code="K3", weight=20, check=CellCheck(kind="cell", row=0, value=8)),
    ),
)
RIGHT = [8, 4, 9, 16]

SHORTFALL = InteractiveRule(  # a number item: units to add for everything missing
    labels=("Legg til",),
    columns={"mangler": (3, 5, 2, 6)},
    criteria=(
        Criterion(
            code="K1",
            weight=100,
            check=BalanceCheck(kind="balance", added="answer", missing="mangler"),
        ),
    ),
)


def met(score: InteractiveScore) -> dict[str, bool]:
    return {c.code: c.met for c in score.criteria}


def with_criteria(*criteria: Criterion) -> InteractiveRule:
    return InteractiveRule.model_validate({**STOCK.model_dump(), "criteria": criteria})


def test_a_fully_right_answer_meets_every_criterion_with_its_reason():
    score = score_interactive(RIGHT, STOCK)
    assert score.answered and score.credit == 1.0
    assert met(score) == {"K1": True, "K2": True, "K3": True}
    assert (
        score.criteria[0].explanation == "Hver rad stemmer med raden over, pluss inn og minus ut."
    )
    assert score.criteria[1].explanation == "Uke 4: 16, som regelen gir."
    right = score_interactive([16], SHORTFALL)
    assert (right.credit, right.criteria[0].explanation) == (
        1.0,
        "Lagt til 16 enheter, mangler 16 enheter: like mange.",
    )


def test_each_single_criterion_failing_costs_only_its_weight():
    # K1 alone: Uke 2 slips and the Uker after it are judged on the Student's own value (Uke 3:
    # 5 + 25 - 20 = 10 holds), so the slip fails the flow once and the cells K2, K3 still hold.
    slip = score_interactive([8, 5, 10, 16], STOCK)
    assert (met(slip), slip.credit) == ({"K1": False, "K2": True, "K3": True}, 0.5)
    assert slip.criteria[0].explanation == "Uke 2: 8 + 20 − 24 = 4, svaret er 5."
    # K2 alone and K3 alone: a rule whose cell asks another value than the flow gives.
    k2 = Criterion(code="K2", weight=30, check=CellCheck(kind="cell", row=3, value=17))
    cell = score_interactive(RIGHT, with_criteria(STOCK.criteria[0], k2, STOCK.criteria[2]))
    assert (met(cell), cell.credit) == ({"K1": True, "K2": False, "K3": True}, 0.7)
    assert cell.criteria[1].explanation == "Uke 4: 16, regelen gir 17."
    k3 = Criterion(code="K3", weight=20, check=CellCheck(kind="cell", row=0, value=9))
    first = score_interactive(RIGHT, with_criteria(*STOCK.criteria[:2], k3))
    assert (met(first), first.credit) == ({"K1": True, "K2": True, "K3": False}, 0.8)
    # The balance, on a number item.
    wrong = score_interactive([15], SHORTFALL)
    assert (wrong.credit, met(wrong)) == (0.0, {"K1": False})
    assert wrong.criteria[0].explanation == (
        "Lagt til 15 enheter, mangler 16 enheter: ikke like mange."
    )


def test_an_empty_answer_scores_nothing_and_says_what_is_missing():
    score = score_interactive([None, None, None, None], STOCK)
    assert not score.answered and score.credit == 0.0 and not any(met(score).values())
    assert score.criteria[0].explanation == "Uke 1 er ikke besvart."
    assert score.criteria[1].explanation == "Uke 4 er ikke besvart."
    empty = score_interactive([None], SHORTFALL)
    assert (empty.answered, empty.credit) == (False, 0.0)
    assert empty.criteria[0].explanation == "Legg til er ikke besvart."


def test_a_partly_filled_table_gets_only_the_criteria_its_values_meet():
    score = score_interactive([8, 4, None, 16], STOCK)
    assert score.answered and score.credit == 0.5
    assert met(score) == {"K1": False, "K2": True, "K3": True}
    assert score.criteria[0].explanation == "Uke 3 er ikke besvart."


def test_the_score_never_looks_at_the_curve_shape():
    """Answers that meet the same criteria score the same, swinging or flat (FR-80): only the
    values count."""
    k2 = Criterion(code="K2", weight=50, check=CellCheck(kind="cell", row=3, value=10))
    swinging = InteractiveRule(
        labels=STOCK.labels,
        columns={"inn": (30, 0, 30, 0), "ut": (0, 30, 0, 30)},
        criteria=(STOCK.criteria[0], k2),
    )
    flat = swinging.model_copy(update={"columns": {"inn": (5, 5, 5, 5), "ut": (5, 5, 5, 5)}})
    assert score_interactive([40, 10, 40, 10], swinging).credit == 1.0
    assert score_interactive([10, 10, 10, 10], flat).credit == 1.0


def test_a_negative_value_is_written_with_a_minus_sign_and_a_wrong_length_is_refused():
    rule = InteractiveRule(
        labels=("Uke 1",),
        criteria=(Criterion(code="K1", weight=100, check=CellCheck(kind="cell", row=0, value=-3)),),
    )
    assert score_interactive([-4], rule).criteria[0].explanation == ("Uke 1: −4, regelen gir −3.")
    with pytest.raises(ValueError):
        score_interactive([1, 2], rule)


GIVEN_ONLY = Criterion(
    code="K1", weight=100, check=BalanceCheck(kind="balance", added="inn", missing="ut")
)


@pytest.mark.parametrize(
    "change",
    [
        {"criteria": STOCK.criteria[:2]},  # weights 80, not 100
        {"columns": {"inn": (1, 2, 3)}},  # the flow names a missing column
        {"columns": {"inn": (1, 2, 3), "ut": (1, 2, 3)}},  # a flow value per row
        {"columns": {**STOCK.columns, "answer": (1, 2, 3, 4)}},
        {"labels": ("Uke 1",)},  # K2 names row 3
        {"criteria": (GIVEN_ONLY,)},  # a balance of given columns alone
        {
            "criteria": (
                STOCK.criteria[0],
                STOCK.criteria[1].model_copy(update={"code": "K1"}),
                STOCK.criteria[2],
            )
        },
        {  # a balance on a column the rule does not have
            "criteria": (
                Criterion(
                    code="K1",
                    weight=100,
                    check=BalanceCheck(kind="balance", added="answer", missing="nope"),
                ),
            )
        },
    ],
)
def test_a_rule_that_does_not_add_up_is_refused(change):
    with pytest.raises(ValidationError):
        InteractiveRule.model_validate({**STOCK.model_dump(), **change})
