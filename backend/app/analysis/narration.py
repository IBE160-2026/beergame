"""AI narration that only connects computed facts (Story 9.14, FR-44, AD-7).

An LLM never writes a word of the shown text. Its output (`AiTextOutput`) names sentence
templates of the pinned `narration_templates` version and, for each, the facts it connects: ids
of the Seat's own moments (`moment:<role>:<week>`) or Detected pattern occurrences
(`<pattern>:<role>:<week>`) from the stored facts set. Code fills each template's slots with the
cited facts' numbers (`render_output`). `validate_ai_text` accepts only output that cites facts
of the set and templates of the version, with the count each template takes, and whose rendered
text holds no number other than the cited facts' own. A sentence may not cite one fact twice or
repeat another sentence, and a sentence naming a fact's following Weeks needs a fact with at least
two of them. `render` is the code narration every caller falls back to.

Story 9.15: from version 2 the same content kind also holds the follow-up's hint templates
(`HINT_TEMPLATES`); a caller names the ids its output may use (`allowed`), so the narration never
cites a hint and a follow-up answer only hints.

A template's slots are `<value>_<n>`: the `n`-th cited fact's `week`, `order`, `supply_line`,
`incoming_order`, `later_cost` (kroner) and the first and last of the following Weeks that cost
covers (`later_first_week`, `later_last_week`). `NARRATION_TEMPLATES` fixes how many facts each
id cites; a template uses every one of them and states no cause.

Pure (AD-1): stdlib, pydantic and `app.engine` only."""

import re
from collections.abc import Collection, Mapping
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.analysis.facts import FactSet, Moment, PatternOccurrence
from app.analysis.patterns import CAUSE_WORDS
from app.analysis.sentences import (
    RenderedText,
    SentenceTemplate,
    _fields,
    format_money,
    format_number,
)

__all__ = [
    "HINT_TEMPLATES",
    "MAX_SENTENCES",
    "NARRATION_TEMPLATES",
    "TEMPLATE_FACTS",
    "NARRATION_VALUES",
    "AiSentence",
    "AiTextOutput",
    "NarrationTemplates",
    "Verdict",
    "citable",
    "code_output",
    "render",
    "render_output",
    "validate_ai_text",
]

_FROZEN = ConfigDict(frozen=True, extra="forbid")

NARRATION_TEMPLATES: Mapping[str, int] = {
    # Two moments side by side: what was ordered, and what came in.
    "narration-orders": 2,
    # One moment: what was already on the way when the Seat ordered.
    "narration-supply-line": 1,
    # One moment: what the following Weeks cost the Seat.
    "narration-later-cost": 1,
    # Three moments: the Weeks they fall in.
    "narration-weeks": 3,
}
"""The narration templates and how many facts each cites."""

HINT_TEMPLATES: Mapping[str, int] = {
    # Story 9.15: hints that point to where to look, never a worked answer (FR-45).
    # One fact: its row in the table, what was ordered and what came in.
    "hint-row": 1,
    # One fact: what was on the way when the Seat ordered.
    "hint-supply-line": 1,
    # One fact: the following Weeks' cost to follow.
    "hint-later": 1,
    # Two facts: two Weeks to compare.
    "hint-compare": 2,
}
"""The follow-up's hint templates (version 2 of the `narration_templates` content kind on) and
how many facts each cites."""

TEMPLATE_FACTS: Mapping[str, int] = {**NARRATION_TEMPLATES, **HINT_TEMPLATES}
"""Every template id a version may hold, with how many facts it cites."""

NARRATION_VALUES = (
    "week",
    "order",
    "supply_line",
    "incoming_order",
    "later_cost",
    "later_first_week",
    "later_last_week",
)
"""The values of a cited fact a slot may name."""

MAX_SENTENCES = 3
"""The most sentences one narration has."""

LATER_SPAN = ("later_first_week", "later_last_week")
"""The slots that name the following Weeks: a template using one of them for a fact applies only
to a fact with `MIN_LATER_WEEKS` of them (the later-cost sentence and its hint)."""
MIN_LATER_WEEKS = 2

_SLOT = re.compile(r"^([a-z_]+)_([1-9])$")
_NUMBER = re.compile(r"\d+")


class NarrationTemplates(BaseModel):
    """The narration templates (content kind `narration_templates`): every id of
    `NARRATION_TEMPLATES` and, from version 2 on, the hint templates of `HINT_TEMPLATES` (Story
    9.15), nothing else; each slot `<value>_<n>` with `n` from 1 to the template's count, every
    cited fact used, no cause stated."""

    model_config = _FROZEN

    templates: Annotated[tuple[SentenceTemplate, ...], Field(min_length=1, max_length=50)]

    @model_validator(mode="after")
    def _complete(self) -> NarrationTemplates:
        ids = [template.id for template in self.templates]
        if len(set(ids)) != len(ids):
            raise ValueError("template ids repeat")
        missing = set(NARRATION_TEMPLATES) - set(ids)
        unknown = set(ids) - set(TEMPLATE_FACTS)
        if missing or unknown:
            raise ValueError(f"templates missing or unknown: {sorted(missing | unknown)}")
        for template in self.templates:
            count = TEMPLATE_FACTS[template.id]
            used: set[int] = set()
            for name in _fields(template.text):
                found = _SLOT.match(name)
                if found is None or found.group(1) not in NARRATION_VALUES:
                    raise ValueError(f"template {template.id!r} has an unknown slot {name!r}")
                used.add(int(found.group(2)))
            if used != set(range(1, count + 1)):
                raise ValueError(f"template {template.id!r} does not use each of its {count} facts")
            if CAUSE_WORDS.search(template.text):
                raise ValueError(f"template {template.id!r} states a cause")
        return self

    def text_of(self, template_id: str) -> str | None:
        return next((t.text for t in self.templates if t.id == template_id), None)

    def has_hints(self) -> bool:
        """Whether this version holds every hint template (version 2 on): the follow-up's
        condition (Story 9.15)."""
        return set(HINT_TEMPLATES) <= {t.id for t in self.templates}

    def lines(self, allowed: Collection[str]) -> list[str]:
        """The templates of `allowed` ids, one per line for a prompt: `id (n): text`."""
        return [
            f"{t.id} ({TEMPLATE_FACTS[t.id]}): {t.text}" for t in self.templates if t.id in allowed
        ]


_FactId = Annotated[str, Field(min_length=1, max_length=80)]


class AiSentence(BaseModel):
    """One sentence of the LLM's output: a template id and the ids of the facts it connects."""

    model_config = _FROZEN

    template_id: Annotated[str, Field(min_length=1, max_length=60)]
    fact_ids: Annotated[tuple[_FactId, ...], Field(min_length=1, max_length=3)]


class AiTextOutput(BaseModel):
    """The output schema of every facts-only LLM call (AD-7): template ids and fact ids only."""

    model_config = _FROZEN

    sentences: Annotated[tuple[AiSentence, ...], Field(min_length=1, max_length=MAX_SENTENCES)]


class Verdict(BaseModel):
    """`validate_ai_text`'s answer: the rendered text when accepted, else the reason."""

    model_config = _FROZEN

    accepted: bool
    text: str | None = None
    reason: (
        Literal[
            "unknown_fact",
            "unknown_template",
            "wrong_arity",
            "repeated",
            "not_applicable",
            "number_outside_facts",
        ]
        | None
    ) = None


type Citable = Moment | PatternOccurrence


def citable(fact_set: FactSet) -> dict[str, Citable]:
    """The facts a narration may cite: the Seat's own moments and pattern occurrences, by id."""
    found: dict[str, Citable] = {moment.id: moment for moment in fact_set.seat.moments}
    for occurrence in fact_set.seat.patterns:
        found[occurrence.id] = occurrence
    return found


def _values(fact: Citable) -> dict[str, str]:
    seen = fact.state_seen
    return {
        "week": format_number(fact.week),
        "order": format_number(fact.order),
        "supply_line": format_number(seen.supply_line),
        "incoming_order": format_number(seen.incoming_order),
        "later_cost": format_money(Decimal(fact.later_cost)),
        "later_first_week": format_number(fact.week + 1),
        "later_last_week": format_number(fact.week + fact.later_weeks),
    }


def _sentence(text: str, facts: list[Citable]) -> str:
    values = {
        f"{name}_{n}": value
        for n, fact in enumerate(facts, start=1)
        for name, value in _values(fact).items()
    }
    return text.format(**{name: values[name] for name in _fields(text)})


def render_output(
    output: AiTextOutput, fact_set: FactSet, templates: NarrationTemplates
) -> RenderedText:
    """The text of an output that `validate_ai_text` accepted: each sentence's template filled
    with its facts' numbers, joined by a space. Raises `KeyError` or `ValueError` otherwise."""
    facts = citable(fact_set)
    parts = []
    for sentence in output.sentences:
        text = templates.text_of(sentence.template_id)
        if text is None:
            raise KeyError(sentence.template_id)
        parts.append(_sentence(text, [facts[fact_id] for fact_id in sentence.fact_ids]))
    ids = ",".join(sentence.template_id for sentence in output.sentences)
    return RenderedText(template_id=f"narration:{ids}", text=" ".join(parts))


def _spans_later(text: str) -> set[int]:
    """The cited facts (by number) whose following Weeks a template names."""
    found = (_SLOT.match(name) for name in _fields(text))
    return {int(m.group(2)) for m in found if m is not None and m.group(1) in LATER_SPAN}


def validate_ai_text(
    output: AiTextOutput,
    fact_set: FactSet,
    templates: NarrationTemplates,
    allowed: Collection[str] = NARRATION_TEMPLATES,
) -> Verdict:
    """Accept the output only when every cited fact id is one of the set's own, every template id
    is one of `allowed` (the narration's own by default; the hints for a follow-up) and in the
    pinned version, with as many facts as it takes, no fact or sentence repeats, a sentence that
    names a fact's following Weeks cites a fact with enough of them, and every number in the
    rendered text is one of the cited facts' rendered values (FR-44, FR-45, AD-7, NFR-9)."""
    facts = citable(fact_set)
    numbers: set[str] = set()
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for sentence in output.sentences:
        if any(fact_id not in facts for fact_id in sentence.fact_ids):
            return Verdict(accepted=False, reason="unknown_fact")
        text = templates.text_of(sentence.template_id)
        if sentence.template_id not in allowed or text is None:
            return Verdict(accepted=False, reason="unknown_template")
        if TEMPLATE_FACTS.get(sentence.template_id) != len(sentence.fact_ids):
            return Verdict(accepted=False, reason="wrong_arity")
        key = (sentence.template_id, sentence.fact_ids)
        if len(set(sentence.fact_ids)) != len(sentence.fact_ids) or key in seen:
            return Verdict(accepted=False, reason="repeated")
        seen.add(key)
        if any(
            facts[sentence.fact_ids[n - 1]].later_weeks < MIN_LATER_WEEKS
            for n in _spans_later(text)
        ):
            return Verdict(accepted=False, reason="not_applicable")
        for fact_id in sentence.fact_ids:
            for value in _values(facts[fact_id]).values():
                numbers.update(_NUMBER.findall(value))
    rendered = render_output(output, fact_set, templates)
    if any(number not in numbers for number in _NUMBER.findall(rendered.text)):
        return Verdict(accepted=False, reason="number_outside_facts")
    return Verdict(accepted=True, text=rendered.text)


def code_output(fact_set: FactSet) -> AiTextOutput | None:
    """The code's own choice of sentences: the first two moments side by side, then the supply
    line of the moment with the most on the way; one moment alone gets the supply-line sentence.
    None when the Seat has no moments (a game played mostly by AI players)."""
    moments = sorted(fact_set.seat.moments, key=lambda moment: moment.week)
    if not moments:
        return None
    if len(moments) == 1:
        return AiTextOutput(
            sentences=(AiSentence(template_id="narration-supply-line", fact_ids=(moments[0].id,)),)
        )
    most = max(moments, key=lambda moment: (moment.state_seen.supply_line, -moment.week))
    return AiTextOutput(
        sentences=(
            AiSentence(template_id="narration-orders", fact_ids=(moments[0].id, moments[1].id)),
            AiSentence(template_id="narration-supply-line", fact_ids=(most.id,)),
        )
    )


def render(fact_set: FactSet, templates: NarrationTemplates) -> RenderedText | None:
    """The code narration (the fallback of every narration call): `code_output` rendered. None
    when the Seat has no moments."""
    output = code_output(fact_set)
    return None if output is None else render_output(output, fact_set, templates)
