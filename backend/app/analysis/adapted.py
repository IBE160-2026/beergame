"""Adapted item templates and their code-rendered text (Story 11.7, FR-53, AD-7, AD-23).

The templates are one immutable versioned record of kind `adapted_templates` in `modules/content`,
validated against `AdaptedTemplates`: the same templates for every Student, each naming the Game it
reads (`game`, the Student's own Class game, or `replay`, their Replay), the kind of fact it needs
and its share of the Adapted total weight. `fill` picks the fact from one stored facts set and
renders every number, Week and Role into the text: an LLM never writes a number (AD-7).

The fact kinds:

- `moment` (a Week and the Order placed in it, with what the Seat saw): the Seat's own moments,
  highest later cost first, then the earlier Week; the `pick`-th. Its fact id is the moment's.
- `pattern` (a Detected pattern): the Seat's pattern occurrences on an Order a Student placed
  (`decided_by = student`), in the same order; the `pick`-th. Its fact id is the occurrence's.
- `outcome` (the Seat's result over the Game): the Seat's entry in `chain.by_role`; fact id
  `outcome:<role>`.

Story 11.8 (FR-53, AD-7): from version 2 a template may hold `wordings`, approved plain phrasings
of the same question with exactly the template's slots, so each gives the Student the same facts.
An LLM may only choose one of them for the item's own fact (`AiTextOutput`: a wording id and the
fact id); `validate_wording` checks that choice with the rules and verdict reasons of the
Debrief's AI-text validator (`analysis.narration`), and `render_wording` fills it from the same
values as `fill`.

Pure (AD-1): stdlib, pydantic and `app.analysis` only."""

import re
import string
from collections.abc import Mapping, Sequence
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.analysis.facts import FactSet, Moment, PatternOccurrence, Seen
from app.analysis.narration import AiTextOutput, Verdict
from app.analysis.sentences import format_money, format_number

__all__ = [
    "FACT_VALUES",
    "KEY_VALUES",
    "ROLE_NAMES",
    "AdaptedTemplate",
    "AdaptedTemplates",
    "Filled",
    "Wording",
    "apportion",
    "fill",
    "picked",
    "render_wording",
    "validate_wording",
]

_FROZEN = ConfigDict(frozen=True, extra="forbid")

type FactKind = Literal["moment", "pattern", "outcome"]

_SEEN = frozenset(
    {"role", "week", "order", "incoming_order", "inventory", "backlog", "supply_line"}
)
FACT_VALUES: Mapping[str, frozenset[str]] = {
    "moment": _SEEN,
    "pattern": _SEEN | {"pattern"},
    "outcome": frozenset({"role", "weeks", "total_cost", "holding_cost", "backorder_cost"}),
}
"""The values a template of each fact kind may use."""

KEY_VALUES: Mapping[str, frozenset[str]] = {
    "moment": frozenset({"week", "order"}),
    "pattern": frozenset({"week", "pattern"}),
    "outcome": frozenset({"total_cost"}),
}
"""The values a template of each fact kind must use, so the item names its fact."""

ROLE_NAMES: Mapping[str, str] = {
    "retailer": "Detaljist",
    "wholesaler": "Grossist",
    "distributor": "Distributør",
    "factory": "Fabrikk",
}
"""The Roles as the web app names them (`frontend/src/copy/nb.ts`, `roles`)."""


def _fields(text: str) -> list[tuple[str, str, str | None]]:
    return [
        (name, spec, conversion)
        for _, name, spec, conversion in string.Formatter().parse(text)
        if name is not None
    ]


_ID = r"^[a-z][a-z0-9-]{0,39}$"


def _check_text(owner: str, text: str, fact: str) -> set[str]:
    """The rules every template and wording text keeps: no `!`, well formed, plain `{name}`
    slots only, only the values its fact kind gives, and every key value of that kind. Returns
    the slots it uses. `owner` names the template or wording in the error."""
    if "!" in text:
        raise ValueError(f"{owner} may not hold an exclamation mark")
    try:
        fields = _fields(text)
    except ValueError as broken:
        raise ValueError(f"{owner} is not well formed: {broken}") from None
    if any(not name.isidentifier() or spec or conv is not None for name, spec, conv in fields):
        raise ValueError(f"{owner} has a slot that is not a plain name")
    used = {name for name, _, _ in fields}
    if not used <= FACT_VALUES[fact]:
        raise ValueError(f"{owner} uses a value its fact kind does not give")
    if not KEY_VALUES[fact] <= used:
        raise ValueError(f"{owner} does not name its fact")
    return used


class Wording(BaseModel):
    """An approved plain phrasing of a template's question (Story 11.8): its id, which an LLM
    names, and its text with the template's `{name}` slots."""

    model_config = _FROZEN

    id: Annotated[str, Field(pattern=_ID)]
    text: Annotated[str, Field(min_length=1, max_length=1000)]


class AdaptedTemplate(BaseModel):
    """One Adapted item template: its id (the Scoring guide's `adapted` question id), the Game it
    reads, the fact kind it needs, which fact of that kind (`pick`, 1 = the first), its share of
    the Adapted total weight in whole percent, and its text with `{name}` slots code fills. From
    version 2 it may hold up to four `wordings` an LLM may choose from (Story 11.8)."""

    model_config = _FROZEN

    id: Annotated[str, Field(pattern=_ID)]
    source: Literal["game", "replay"]
    fact: FactKind
    pick: Annotated[int, Field(strict=True, ge=1, le=3)] = 1
    share: Annotated[int, Field(strict=True, ge=1, le=100)]
    text: Annotated[str, Field(min_length=1, max_length=1000)]
    wordings: Annotated[tuple[Wording, ...], Field(max_length=4)] = ()

    @model_validator(mode="after")
    def _well_formed(self) -> AdaptedTemplate:
        used = _check_text(f"template {self.id!r}", self.text, self.fact)
        for wording in self.wordings:
            # The same facts as the template's text, so every Student is asked with the same
            # information whichever wording is chosen (FR-53).
            if _check_text(f"wording {wording.id!r}", wording.text, self.fact) != used:
                raise ValueError(f"wording {wording.id!r} does not use the template's values")
        return self

    def wording(self, wording_id: str) -> Wording | None:
        return next((w for w in self.wordings if w.id == wording_id), None)


class AdaptedTemplates(BaseModel):
    """The Adapted item templates (Story 11.7, FR-53): `draft` until the founder approves the real
    text (issue #16); ids unique; the shares split the Adapted total weight and sum to 100."""

    model_config = _FROZEN

    status: Literal["draft", "approved"]
    templates: Annotated[tuple[AdaptedTemplate, ...], Field(min_length=1, max_length=10)]

    @model_validator(mode="after")
    def _complete(self) -> AdaptedTemplates:
        ids = [template.id for template in self.templates]
        ids += [wording.id for template in self.templates for wording in template.wordings]
        if len(set(ids)) != len(ids):
            raise ValueError("template ids repeat (a wording id counts as one)")
        if sum(template.share for template in self.templates) != 100:
            raise ValueError("the template shares sum to 100")
        return self


class Filled(BaseModel):
    """One template filled from one facts set: the fact ids it cites and the rendered text."""

    model_config = _FROZEN

    fact_ids: tuple[str, ...]
    text: str


def apportion(total: int, shares: Sequence[int]) -> list[int]:
    """`total` split into whole numbers in proportion to `shares`, summing exactly to `total`: each
    gets the floor of its part, and what is left goes one by one to the largest remainders (ties:
    the earlier). Used for the Adapted items' and the replacement items' weights."""
    if total < 0 or not shares or any(share < 0 for share in shares) or sum(shares) <= 0:
        raise ValueError("apportion needs a total ≥ 0 and positive shares")
    whole = sum(shares)
    parts = [total * share // whole for share in shares]
    rests = [total * share % whole for share in shares]
    order = sorted(range(len(shares)), key=lambda i: (-rests[i], i))
    for i in order[: total - sum(parts)]:
        parts[i] += 1
    return parts


def _by_cost[T: (Moment, PatternOccurrence)](found: Sequence[T]) -> list[T]:
    return sorted(found, key=lambda each: (-each.later_cost, each.week))


def _seen_values(role: str, week: int, order: int, seen: Seen) -> dict[str, str]:
    return {
        "role": ROLE_NAMES[role],
        "week": format_number(week),
        "order": format_number(order),
        "incoming_order": format_number(seen.incoming_order),
        "inventory": format_number(seen.inventory),
        "backlog": format_number(seen.backlog),
        "supply_line": format_number(seen.supply_line),
    }


def picked(
    template: AdaptedTemplate, facts: FactSet, pattern_names: Mapping[str, str]
) -> tuple[str, dict[str, str]] | None:
    """The fact a template takes from the set, as its id and its rendered values; None when the
    set holds no such fact."""
    role = facts.seat.role
    values: dict[str, str]
    if template.fact == "moment":
        moments = _by_cost(facts.seat.moments)
        if len(moments) < template.pick:
            return None
        moment = moments[template.pick - 1]
        fact_id = moment.id
        values = _seen_values(role, moment.week, moment.order, moment.state_seen)
    elif template.fact == "pattern":
        found = _by_cost([p for p in facts.seat.patterns if p.decided_by == "student"])
        if len(found) < template.pick:
            return None
        occurrence = found[template.pick - 1]
        name = pattern_names.get(occurrence.pattern)
        if name is None:
            return None
        fact_id = occurrence.id
        values = _seen_values(role, occurrence.week, occurrence.order, occurrence.state_seen)
        values["pattern"] = name
    else:
        entry = next((each for each in facts.chain.by_role if each.role == role), None)
        if entry is None:
            return None
        fact_id = f"outcome:{role}"
        values = {
            "role": ROLE_NAMES[role],
            "weeks": format_number(facts.chain.weeks),
            "total_cost": format_money(entry.total_cost),
            "holding_cost": format_money(entry.holding_cost),
            "backorder_cost": format_money(entry.backorder_cost),
        }
    return fact_id, values


def fill(
    template: AdaptedTemplate, facts: FactSet, pattern_names: Mapping[str, str]
) -> Filled | None:
    """The template filled from the Seat's facts set; None when the set holds no such fact (fewer
    own moments or pattern occurrences than `pick`, or no entry for the Seat's Role).
    `pattern_names` names each Detected pattern by its id (the definitions the set was built
    with)."""
    found = picked(template, facts, pattern_names)
    if found is None:
        return None
    fact_id, values = found
    return Filled(fact_ids=(fact_id,), text=template.text.format(**values))


def render_wording(
    template: AdaptedTemplate,
    wording_id: str,
    facts: FactSet,
    pattern_names: Mapping[str, str],
) -> Filled | None:
    """One of the template's wordings filled from the same fact and values as `fill`; None for
    an id the template does not hold or a fact the set lacks."""
    wording = template.wording(wording_id)
    found = picked(template, facts, pattern_names)
    if wording is None or found is None:
        return None
    fact_id, values = found
    return Filled(fact_ids=(fact_id,), text=wording.text.format(**values))


_NUMBER = re.compile(r"\d+")


def validate_wording(
    output: AiTextOutput,
    template: AdaptedTemplate,
    facts: FactSet,
    pattern_names: Mapping[str, str],
    fact_ids: Sequence[str],
) -> Verdict:
    """Accept an LLM's wording of an Adapted item only when it is one sentence that names one of
    the template's wordings and exactly the item's frozen fact ids, which are still the fact the
    template takes from this set, and every number in the rendered text is one of that fact's own
    rendered values (the rules and verdict reasons of `narration.validate_ai_text`; FR-53,
    AD-7)."""
    if len(output.sentences) != 1:
        return Verdict(accepted=False, reason="wrong_arity")
    [sentence] = output.sentences
    found = picked(template, facts, pattern_names)
    cited = tuple(sentence.fact_ids)
    if found is None or cited != tuple(fact_ids) or cited != (found[0],):
        return Verdict(accepted=False, reason="unknown_fact")
    rendered = render_wording(template, sentence.template_id, facts, pattern_names)
    if rendered is None:
        return Verdict(accepted=False, reason="unknown_template")
    numbers = {n for value in found[1].values() for n in _NUMBER.findall(value)}
    if any(number not in numbers for number in _NUMBER.findall(rendered.text)):
        return Verdict(accepted=False, reason="number_outside_facts")
    return Verdict(accepted=True, text=rendered.text)
