"""The Debrief quiz: its shape, its scoring by answer key and the own-game sentence of an
explanation, rendered from a stored facts set (Story 9.9, FR-46, AD-7, AD-23).

The quiz is one immutable versioned record of kind `debrief_quiz` in `modules/content`, which
validates every version against `DebriefQuiz`. Each question is single choice with one right
choice (`answer`), a fixed `explanation` and, optionally, `in_your_game`: a template whose slots
are values of the Student's own Game (`QUIZ_VALUES`), filled by code from the facts set of their
Seat (`render_in_your_game`). `score` judges an attempt by the answer key; the server alone calls
it.

Pure (AD-1): stdlib, pydantic and `app.engine` only; no clock, no randomness."""

from collections.abc import Callable, Mapping, Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.analysis.facts import FactSet
from app.analysis.sentences import RenderedText, _fields, _plain_slots, format_money, format_number

__all__ = [
    "QUIZ_VALUES",
    "DebriefQuiz",
    "QuizChoice",
    "QuizQuestion",
    "ScoredAnswer",
    "ScoredAttempt",
    "WrongAnswers",
    "render_in_your_game",
    "score",
]

_FROZEN = ConfigDict(frozen=True, extra="forbid")
_Key = Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{0,39}$")]
_Text = Annotated[str, Field(min_length=1, max_length=500)]


def _one_decimal(value: Decimal) -> str:
    """Forsterkning as the Debrief writes it: one decimal after a comma, half up («7,6»)."""
    rounded = value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    whole, _, fraction = f"{abs(rounded):f}".partition(".")
    text = f"{format_number(int(whole))},{fraction}"
    return f"−{text}" if rounded < 0 else text


def _role_facts(fact_set: FactSet, role: str):
    return next((each for each in fact_set.chain.by_role if str(each.role) == role), None)


def _own_amplification(fact_set: FactSet) -> str | None:
    found = _role_facts(fact_set, str(fact_set.seat.role))
    return _one_decimal(found.amplification) if found and found.amplification is not None else None


def _factory_amplification(fact_set: FactSet) -> str | None:
    found = _role_facts(fact_set, "factory")
    return _one_decimal(found.amplification) if found and found.amplification is not None else None


def _own_first_large_order_week(fact_set: FactSet) -> str | None:
    found = _role_facts(fact_set, str(fact_set.seat.role))
    week = found.first_large_order_week if found else None
    return format_number(week) if week is not None else None


def _first_moment_week(fact_set: FactSet) -> str | None:
    weeks = [moment.week for moment in fact_set.seat.moments]
    return format_number(min(weeks)) if weeks else None


QUIZ_VALUES: Mapping[str, Callable[[FactSet], str | None]] = {
    # The Game's last Week.
    "weeks": lambda f: format_number(f.chain.weeks),
    # The chain's Total cost in kroner («2 266,00»).
    "chain_total_cost": lambda f: format_money(f.chain.total_cost),
    # Forsterkning of the Student's own Role and of the Fabrikk; None when demand never varied.
    "own_amplification": _own_amplification,
    "factory_amplification": _factory_amplification,
    # The first Week the Student's Role ordered 10 or more; None when it never did.
    "own_first_large_order_week": _own_first_large_order_week,
    # The Week of the Student's first own moment; None when the Seat has none (mostly AI).
    "first_moment_week": _first_moment_week,
}
"""The values of the Student's own Game an explanation may name, each written as the web app
writes it, from the facts set of their Seat only (AD-7)."""


class QuizChoice(BaseModel):
    model_config = _FROZEN

    id: _Key
    text: _Text


class QuizQuestion(BaseModel):
    """One single-choice question (FR-46): the prompt, its choices in the order shown, the right
    choice's id, the fixed explanation and the optional own-game sentence."""

    model_config = _FROZEN

    id: _Key
    prompt: _Text
    choices: Annotated[tuple[QuizChoice, ...], Field(min_length=2, max_length=6)]
    answer: _Key
    """The answer key: the id of the right choice. Never sent before an attempt is scored."""
    explanation: _Text
    in_your_game: _Text | None = None
    """A template with `{name}` slots from `QUIZ_VALUES`, e.g. «Det står i kolonne
    {first_moment_week} i din egen tabell.»"""

    @model_validator(mode="after")
    def _well_formed(self) -> QuizQuestion:
        ids = [choice.id for choice in self.choices]
        if len(set(ids)) != len(ids):
            raise ValueError(f"question {self.id!r}: choice ids repeat")
        if self.answer not in ids:
            raise ValueError(f"question {self.id!r}: the answer is not one of its choices")
        texts = [self.prompt, self.explanation, self.in_your_game or ""]
        texts += [choice.text for choice in self.choices]
        if any("!" in text for text in texts):
            raise ValueError(f"question {self.id!r} may not hold an exclamation mark")
        if "{" in self.explanation or "}" in self.explanation:
            raise ValueError(f"question {self.id!r}: the explanation takes no slots")
        if self.in_your_game is not None:
            try:
                plain = _plain_slots(self.in_your_game)
            except ValueError as broken:
                raise ValueError(f"question {self.id!r}: {broken}") from None
            if not plain or not _fields(self.in_your_game) <= set(QUIZ_VALUES):
                raise ValueError(f"question {self.id!r}: in_your_game uses an unknown value")
        return self


class DebriefQuiz(BaseModel):
    """The Debrief quiz (Story 9.9, FR-46): fixed questions in order. `placeholder` marks content
    that is not the real quiz yet (issue #16); the web app says so."""

    model_config = _FROZEN

    placeholder: bool
    questions: Annotated[tuple[QuizQuestion, ...], Field(min_length=1, max_length=20)]

    @model_validator(mode="after")
    def _ids_unique(self) -> DebriefQuiz:
        ids = [question.id for question in self.questions]
        if len(set(ids)) != len(ids):
            raise ValueError("question ids repeat")
        return self

    def question(self, question_id: str) -> QuizQuestion:
        return next(q for q in self.questions if q.id == question_id)


def render_in_your_game(fact_set: FactSet, question: QuizQuestion) -> RenderedText | None:
    """The question's own-game sentence filled from the facts set of the Student's Seat; None
    when it has none or a value it names is missing in this Game (no moments, no large Order,
    flat demand), so the explanation then stands alone and never shows a gap."""
    if question.in_your_game is None:
        return None
    values: dict[str, str] = {}
    for name in _fields(question.in_your_game):
        value = QUIZ_VALUES[name](fact_set)
        if value is None:
            return None
        values[name] = value
    return RenderedText(
        template_id=f"quiz:{question.id}", text=question.in_your_game.format(**values)
    )


class WrongAnswers(ValueError):
    """An attempt that cannot be scored: `incomplete` (not every asked question exactly once, or
    another) or `unknown_choice`."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class ScoredAnswer(BaseModel):
    model_config = _FROZEN

    question_id: str
    choice_id: str
    correct: bool


class ScoredAttempt(BaseModel):
    """An attempt judged by the answer key: each answer in the order shown, and whether every
    asked question is right."""

    model_config = _FROZEN

    answers: tuple[ScoredAnswer, ...]
    passed: bool


def score(
    quiz: DebriefQuiz, asked: Sequence[str], answers: Sequence[tuple[str, str]]
) -> ScoredAttempt:
    """Score `answers` (question id, choice id), in the order shown, against the answer key.
    `asked` are the question ids the attempt must answer, each exactly once. Raises
    `WrongAnswers`."""
    ids = [question_id for question_id, _ in answers]
    if len(set(ids)) != len(ids) or set(ids) != set(asked):
        raise WrongAnswers("incomplete")
    scored = []
    for question_id, choice_id in answers:
        question = quiz.question(question_id)
        if choice_id not in {choice.id for choice in question.choices}:
            raise WrongAnswers("unknown_choice")
        scored.append(
            ScoredAnswer(
                question_id=question_id,
                choice_id=choice_id,
                correct=choice_id == question.answer,
            )
        )
    return ScoredAttempt(answers=tuple(scored), passed=all(each.correct for each in scored))
