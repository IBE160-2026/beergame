"""The own moments, rendered by code from a stored facts set (Story 9.7, FR-44, AD-7).

`render(fact_set, templates, patterns)` fills the `moment_templates` (content, validated against
`sentences.MomentTemplates`) with numbers from the facts set only: each moment's Week, Order and
what the Seat saw, and the documented sums of them (Posisjon before and after the Order, the gap
between the Order and the incoming order, the range of the following Weeks). A moment's Detected
patterns are named by their name and definition from the pattern set the facts were built with,
then their mechanism, as patterns and never as causes. Later stories (AI narration, 9.14) cite
the same moments; an LLM never writes a number.

Pure (AD-1): stdlib, pydantic and `app.engine` only."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.analysis.facts import FactSet, Moment, PatternOccurrence
from app.analysis.patterns import Mechanism, PatternSet
from app.analysis.sentences import MomentTemplates, RenderedText, format_money, format_number

__all__ = ["MECHANISM_TEMPLATES", "RenderedMoment", "RenderedMoments", "position", "render"]

_FROZEN = ConfigDict(frozen=True, extra="forbid")

MECHANISM_TEMPLATES: dict[Mechanism, str] = {
    "delay": "mechanism-delay",
    "supply_line": "mechanism-supply-line",
    "demand_information_lost": "mechanism-demand-information-lost",
}


class RenderedMoment(BaseModel):
    """One own moment's text: its heading, «Dette regnet du», «Dette kostet det senere» and the
    pattern (or gap) sentences, in the order shown."""

    model_config = _FROZEN

    id: str
    """The facts set's `moment:<role>:<week>`."""
    week: int
    heading: RenderedText
    reckoning: RenderedText
    later: RenderedText
    patterns: tuple[RenderedText, ...]


class RenderedMoments(BaseModel):
    """Step 4's text: the heading from the first moment, None when the Seat has no moments."""

    model_config = _FROZEN

    heading: RenderedText | None
    moments: tuple[RenderedMoment, ...]


def position(moment: Moment) -> int:
    """Posisjon when the Seat ordered: inventory minus backlog plus the supply line."""
    seen = moment.state_seen
    return seen.inventory - seen.backlog + seen.supply_line


def _fill(
    templates: MomentTemplates, template_id: str, **values: int | Decimal | str
) -> RenderedText:
    """Template `template_id` with every number written as the web app writes it and text (a
    pattern's name and definition) as it is."""

    def written(value: int | Decimal | str) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, Decimal):
            return format_money(value)
        return format_number(value)

    text = templates.text_of(template_id).format(
        **{name: written(value) for name, value in values.items()}
    )
    return RenderedText(template_id=template_id, text=text)


def _later(templates: MomentTemplates, moment: Moment) -> RenderedText:
    if moment.later_weeks == 0:
        return _fill(templates, "moment-later-none")
    first = moment.week + 1
    if moment.later_weeks == 1:
        return _fill(templates, "moment-later-one", first_week=first, later_cost=moment.later_cost)
    return _fill(
        templates,
        "moment-later",
        first_week=first,
        last_week=moment.week + moment.later_weeks,
        later_cost=moment.later_cost,
    )


def _gap(templates: MomentTemplates, moment: Moment) -> RenderedText:
    incoming = moment.state_seen.incoming_order
    if moment.order > incoming:
        return _fill(
            templates, "moment-gap-above", gap=moment.order - incoming, incoming_order=incoming
        )
    if moment.order < incoming:
        return _fill(
            templates, "moment-gap-below", gap=incoming - moment.order, incoming_order=incoming
        )
    return _fill(templates, "moment-gap-equal", incoming_order=incoming)


def _patterns(
    templates: MomentTemplates,
    moment: Moment,
    found: dict[str, PatternOccurrence],
    patterns: PatternSet,
) -> tuple[RenderedText, ...]:
    if not moment.patterns:
        return (_gap(templates, moment),)
    defined = {pattern.id: pattern for pattern in patterns.patterns}
    texts: list[RenderedText] = []
    for occurrence_id in moment.patterns:
        occurrence = found.get(occurrence_id)
        pattern = defined.get(occurrence.pattern) if occurrence else None
        if occurrence is None or pattern is None:
            raise ValueError(f"{occurrence_id} is not a pattern of this facts set and pattern set")
        texts.append(
            _fill(templates, "moment-pattern", name=pattern.name, definition=pattern.definition)
        )
        texts.append(_fill(templates, MECHANISM_TEMPLATES[occurrence.mechanism]))
    return tuple(texts)


def _moment(
    templates: MomentTemplates,
    moment: Moment,
    found: dict[str, PatternOccurrence],
    patterns: PatternSet,
) -> RenderedMoment:
    seen = moment.state_seen
    before = position(moment)
    return RenderedMoment(
        id=moment.id,
        week=moment.week,
        heading=_fill(
            templates,
            "moment-heading",
            week=moment.week,
            order=moment.order,
            supply_line=seen.supply_line,
        ),
        reckoning=_fill(
            templates,
            "moment-position",
            inventory=seen.inventory,
            backlog=seen.backlog,
            supply_line=seen.supply_line,
            position=before,
            order=moment.order,
            position_after=before + moment.order,
        ),
        later=_later(templates, moment),
        patterns=_patterns(templates, moment, found, patterns),
    )


def render(fact_set: FactSet, templates: MomentTemplates, patterns: PatternSet) -> RenderedMoments:
    """The own moments of the facts set's Seat, by Week, and step 4's heading from the first.
    `patterns` is the pattern set the facts were built with (its names and definitions). Raises
    `ValueError` when a moment cites a pattern that set does not define."""
    found = {occurrence.id: occurrence for occurrence in fact_set.seat.patterns}
    moments = sorted(fact_set.seat.moments, key=lambda moment: moment.week)
    rendered = tuple(_moment(templates, moment, found, patterns) for moment in moments)
    if not moments:
        return RenderedMoments(heading=None, moments=())
    first = moments[0]
    heading = _fill(
        templates,
        "moments-heading",
        week=first.week,
        order=first.order,
        supply_line=first.state_seen.supply_line,
    )
    return RenderedMoments(heading=heading, moments=rendered)
