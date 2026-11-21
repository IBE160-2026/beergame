"""Sentence templates and the code-rendered Debrief text (FR-44, AD-7, AD-23).

The templates are one immutable versioned record of kind `sentence_templates` in
`modules/content`, which validates every version against `SentenceTemplates`. Code fills every
number into them: an LLM never writes a number or a cause (AD-7). Story 9.4 renders the step-2
heading from the Game's customer demand series (`demand_heading`); later stories add the
templates of the moments.

Pure (AD-1): stdlib, pydantic and `app.engine` only."""

import string
from collections.abc import Mapping, Sequence
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.engine.demand import DemandPattern, DemandRandom, DemandStepNoise

__all__ = [
    "DEMAND_TEMPLATES",
    "RenderedText",
    "SentenceTemplate",
    "SentenceTemplates",
    "demand_heading",
    "format_number",
    "render",
]

_FROZEN = ConfigDict(frozen=True, extra="forbid")

DEMAND_TEMPLATES: Mapping[str, frozenset[str]] = {
    "demand-flat": frozenset({"level"}),
    "demand-step": frozenset({"before", "after", "change_week"}),
    "demand-step-noise": frozenset({"before", "after", "change_week", "low", "high"}),
    "demand-random": frozenset({"level", "low", "high"}),
    "demand-varied": frozenset({"first", "low", "high"}),
}
"""The step-2 heading's variants and the values each may use (Story 9.4)."""


def _fields(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name is not None}


def _plain_slots(text: str) -> bool:
    """Every slot a bare name: no format spec, conversion or nested slot, which `render` (whose
    values are already text) could not fill."""
    return all(
        name is None or (name.isidentifier() and not spec and conversion is None)
        for _, name, spec, conversion in string.Formatter().parse(text)
    )


class SentenceTemplate(BaseModel):
    """One template: its id and its text with `{name}` slots that code fills."""

    model_config = _FROZEN

    id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]{0,59}$")]
    text: Annotated[str, Field(min_length=1, max_length=500)]

    @model_validator(mode="after")
    def _well_formed(self) -> SentenceTemplate:
        # No exclamation mark (UX-DR78); every slot a plain name, so `render` never evaluates one.
        if "!" in self.text:
            raise ValueError(f"template {self.id!r} may not hold an exclamation mark")
        try:
            plain = _plain_slots(self.text)
        except ValueError as broken:
            raise ValueError(f"template {self.id!r} is not well formed: {broken}") from None
        if not plain:
            raise ValueError(f"template {self.id!r} has a slot that is not a plain name")
        return self


class SentenceTemplates(BaseModel):
    """The sentence templates (Story 9.4): every demand heading variant, each using only the
    values its id allows."""

    model_config = _FROZEN

    templates: Annotated[tuple[SentenceTemplate, ...], Field(min_length=1, max_length=200)]

    @model_validator(mode="after")
    def _complete(self) -> SentenceTemplates:
        ids = [template.id for template in self.templates]
        if len(set(ids)) != len(ids):
            raise ValueError("template ids repeat")
        missing = set(DEMAND_TEMPLATES) - set(ids)
        if missing:
            raise ValueError(f"templates missing: {sorted(missing)}")
        for template in self.templates:
            allowed = DEMAND_TEMPLATES.get(template.id)
            if allowed is not None and not _fields(template.text) <= allowed:
                raise ValueError(f"template {template.id!r} uses a value it is not given")
        return self

    def text_of(self, template_id: str) -> str:
        return next(t.text for t in self.templates if t.id == template_id)


class RenderedText(BaseModel):
    """Text rendered by code from a template: never AI text (AD-7)."""

    model_config = _FROZEN

    template_id: str
    text: str


def format_number(value: int) -> str:
    """A whole number as the web app writes it (UX-DR5): a no-break space between thousands and
    a true minus sign («−1 234»)."""
    grouped = f"{abs(value):,}".replace(",", " ")
    return f"−{grouped}" if value < 0 else grouped


def render(templates: SentenceTemplates, template_id: str, **values: int) -> RenderedText:
    """Template `template_id` with each value written as a Norwegian number."""
    text = templates.text_of(template_id).format(
        **{name: format_number(value) for name, value in values.items()}
    )
    return RenderedText(template_id=template_id, text=text)


def _single_step(series: Sequence[int]) -> int | None:
    """The Week of the one change in a series that changes once and never again, or None."""
    changes = [week for week in range(2, len(series) + 1) if series[week - 1] != series[week - 2]]
    return changes[0] if len(changes) == 1 else None


def demand_heading(
    pattern: DemandPattern, series: Sequence[int], templates: SentenceTemplates
) -> RenderedText:
    """The step-2 heading (Story 9.4, FR-44): what the customers ordered, from the Game's demand
    series. The shape of the series picks the variant first (flat, one step); a noisy pattern
    then says the level it varied around (from the pattern) and the lowest and highest Week
    (from the series); any other series says its first Week and its range after that."""
    if not series:
        raise ValueError("a demand series has at least one Week")
    first = series[0]
    if all(value == first for value in series):
        return render(templates, "demand-flat", level=first)
    step = _single_step(series)
    if step is not None:
        return render(templates, "demand-step", before=first, after=series[-1], change_week=step)
    low, high = min(series), max(series)
    if (
        isinstance(pattern, DemandStepNoise)
        and pattern.first_change_week is not None
        and pattern.change_week <= len(series)
    ):
        return render(
            templates,
            "demand-step-noise",
            before=pattern.start,
            after=pattern.new_level,
            change_week=pattern.change_week,
            low=low,
            high=high,
        )
    if isinstance(pattern, (DemandRandom, DemandStepNoise)):
        return render(templates, "demand-random", level=pattern.starting_level, low=low, high=high)
    rest = series[1:]
    return render(templates, "demand-varied", first=first, low=min(rest), high=max(rest))
