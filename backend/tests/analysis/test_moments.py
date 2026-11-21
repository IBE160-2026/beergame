"""Story 9.7: the own moments rendered by code from a facts set (FR-44, AD-1, AD-7, NFR-9).

The facts sets here are built by hand with `analysis.facts`, so each template path is checked on
the numbers that choose it; `tests/games/test_facts.py` renders the golden Games and checks every
number against their `seat_weeks` rows."""

import copy
import importlib.util
import re
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.analysis import moments as rendering
from app.analysis.facts import FactSet, Moment, facts
from app.analysis.sentences import MOMENT_TEMPLATES, MomentTemplates, format_money
from tests.analysis.test_facts import PATTERNS, log, student

MIGRATION = Path(__file__).parents[2] / "migrations" / "versions" / "0106_moment_templates.py"


def _version_1() -> dict:
    spec = importlib.util.spec_from_file_location("migration_0106", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.MOMENT_TEMPLATES_V1


V1 = _version_1()
TEMPLATES = MomentTemplates.model_validate(V1)
NUMBER = re.compile(r"−?\d{1,3}(?: \d{3})*(?:,\d{2})?")


def numbers(text: str) -> list[Decimal]:
    """Every number in a rendered text, as written by `format_number` or `format_money`."""
    return [
        Decimal(found.replace(" ", "").replace("−", "-").replace(",", "."))
        for found in NUMBER.findall(text)
    ]


def facts_numbers(moment: Moment) -> set[Decimal]:
    """The numbers a moment's text may hold: the facts set's own values of the moment, and the
    documented sums of them (Posisjon before and after the Order, the gap, the later Weeks)."""
    seen = moment.state_seen
    position = seen.inventory - seen.backlog + seen.supply_line
    return {
        Decimal(value)
        for value in (
            moment.week,
            moment.order,
            seen.incoming_order,
            seen.inventory,
            seen.backlog,
            seen.supply_line,
            position,
            position + moment.order,
            abs(moment.order - seen.incoming_order),
            moment.week + 1,
            moment.week + moment.later_weeks,
        )
    } | {moment.later_cost}


def assert_every_number_from_the_facts(fact_set: FactSet, shown: rendering.RenderedMoments):
    """NFR-9: every number in every rendered moment is one of the facts set's (or its sums)."""
    by_week = {moment.week: moment for moment in fact_set.seat.moments}
    for each in shown.moments:
        allowed = facts_numbers(by_week[each.week])
        for text in (each.heading, each.reckoning, each.later, *each.patterns):
            assert set(numbers(text.text)) <= allowed, (text.text, allowed)
    if shown.heading:
        first = by_week[min(by_week)]
        assert set(numbers(shown.heading.text)) <= facts_numbers(first)


def scenario() -> FactSet:
    """Two surges (Weeks 3 and 9) and a low Order (Week 10) by a Student on the Retailer."""
    changes = student(range(1, 13))
    changes[(3, "retailer")] |= {"order": 12, "backlog": 1}
    changes[(4, "retailer")] |= {"backlog": 1}
    changes[(8, "retailer")] |= {"order": 2}
    changes[(10, "retailer")] |= {"order": 1}
    changes[(9, "retailer")] |= {"order": 12, "backlog": 1}
    return facts(log(12, changes), "retailer", PATTERNS)


def test_version_1_is_valid_and_has_every_template():
    assert {t.id for t in TEMPLATES.templates} == set(MOMENT_TEMPLATES)


def test_the_moments_of_a_seat_are_rendered_from_its_facts():
    built = scenario()
    shown = rendering.render(built, TEMPLATES, PATTERNS)
    assert shown.heading is not None
    assert shown.heading.template_id == "moments-heading"
    assert shown.heading.text == (
        "Ditt øyeblikk: Uke 3. Du bestilte 12 med 16 på vei. Og hva det kostet kjeden."
    )
    first, second, third = shown.moments
    assert [m.week for m in shown.moments] == [3, 9, 10]
    assert first.id == "moment:retailer:3"
    assert first.heading.text == "Uke 3. Du bestilte 12 med 16 på vei."
    assert first.reckoning.text == "Posisjon 12 − 1 + 16 = 27. Med 12 ble den 39."
    assert first.later.text == "I Uke 4 til 7 kostet leddet ditt 25,00 kr."
    assert [p.template_id for p in first.patterns] == [
        "moment-pattern",
        "mechanism-demand-information-lost",
    ]
    assert first.patterns[0].text == (
        "Mønster: Stor ordre etter mangel. En ordre godt over innkommende ordre i en uke med "
        "restordre, eller i en av de to ukene etter."
    )
    assert second.later.text == "I Uke 10 til 12 kostet leddet ditt 18,00 kr."
    assert [p.template_id for p in third.patterns] == ["moment-gap-below"]
    assert third.patterns[0].text == (
        "Ingen av mønstrene passer denne uka. Du bestilte 3 mindre enn ordren inn, som var 4."
    )
    assert third.later.text == "I Uke 11 til 12 kostet leddet ditt 12,00 kr."
    assert_every_number_from_the_facts(built, shown)
    # Pure: the same facts give the same text.
    assert shown == rendering.render(built, TEMPLATES, PATTERNS)


def _with_moment(built: FactSet, **changes) -> FactSet:
    moment = built.seat.moments[0].model_copy(update=changes)
    seat = built.seat.model_copy(update={"moments": (moment,)})
    return built.model_copy(update={"seat": seat})


@pytest.mark.parametrize(
    ("later_weeks", "template_id", "text"),
    [
        (0, "moment-later-none", "Dette var spillets siste uke. Ingen senere uke kostet noe."),
        (1, "moment-later-one", "I Uke 4 kostet leddet ditt 25,00 kr."),
    ],
)
def test_the_last_weeks_of_a_game_say_how_much_later_there_was(later_weeks, template_id, text):
    shown = rendering.render(_with_moment(scenario(), later_weeks=later_weeks), TEMPLATES, PATTERNS)
    assert (shown.moments[0].later.template_id, shown.moments[0].later.text) == (template_id, text)


@pytest.mark.parametrize(
    ("order", "template_id", "text"),
    [
        (9, "moment-gap-above", "Du bestilte 5 mer enn ordren inn, som var 4."),
        (4, "moment-gap-equal", "Du bestilte det samme som ordren inn, 4."),
    ],
)
def test_a_moment_with_no_pattern_states_the_gap(order, template_id, text):
    built = _with_moment(scenario(), order=order, patterns=(), chosen_by="order_gap")
    [said] = rendering.render(built, TEMPLATES, PATTERNS).moments[0].patterns
    assert said.template_id == template_id
    assert said.text == f"Ingen av mønstrene passer denne uka. {text}"


def test_each_mechanism_has_its_sentence():
    seen = {}
    for pattern in PATTERNS.patterns:
        template = rendering.MECHANISM_TEMPLATES[pattern.mechanism]
        seen[pattern.mechanism] = TEMPLATES.text_of(template)
    assert set(seen) == {"delay", "supply_line", "demand_information_lost"}
    assert all(text.startswith("Mønsteret hører til mekanismen ") for text in seen.values())


def test_a_seat_played_mostly_by_ai_players_has_no_moments_and_no_heading():
    built = facts(log(12, student(range(1, 10))), "retailer", PATTERNS)
    assert built.seat.sm_excluded
    assert rendering.render(built, TEMPLATES, PATTERNS) == rendering.RenderedMoments(
        heading=None, moments=()
    )


def test_a_moment_citing_a_pattern_the_set_does_not_define_is_refused():
    built = _with_moment(scenario(), patterns=("nope:retailer:3",))
    with pytest.raises(ValueError, match="nope:retailer:3"):
        rendering.render(built, TEMPLATES, PATTERNS)


def _broken(change) -> dict:
    body = copy.deepcopy(V1)
    change(body["templates"])
    return body


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda t: t.pop(), "missing"),
        (lambda t: t.append({"id": "moment-extra", "text": "Mer."}), "unknown"),
        (lambda t: t.append(dict(t[0])), "repeat"),
        (lambda t: t[1].update(text="Uke {week} og {demand}."), "exactly"),
        (
            lambda t: t[3].update(text="I Uke {first_week} til {last_week} kostet det noe."),
            "exactly",
        ),
        (
            lambda t: t[3].update(
                text="Uke {first_week} til {last_week}: {later_cost} kr fordi du bestilte."
            ),
            "cause",
        ),
        (
            lambda t: t[3].update(
                text="Uke {first_week} til {last_week} ble dyre på grunn av {later_cost}."
            ),
            "cause",
        ),
        (lambda t: t[3].update(text="Det kostet {later_cost} kr!"), "exclamation"),
        (lambda t: t[3].update(text="Det kostet {later_cost:>5} kr."), "plain name"),
    ],
)
def test_templates_that_lack_ids_use_values_or_state_a_cause_are_refused(change, message):
    with pytest.raises(ValidationError, match=message):
        MomentTemplates.model_validate(_broken(change))


@pytest.mark.parametrize(
    ("value", "written"),
    [
        (Decimal("0"), "0,00"),
        (Decimal("111.5"), "111,50"),
        (Decimal("2266.00"), "2 266,00"),
        (Decimal("-0.5"), "−0,50"),
        (Decimal("0.005"), "0,00"),
        (Decimal("1234567.125"), "1 234 567,12"),
    ],
)
def test_money_is_written_the_norwegian_way(value, written):
    assert format_money(value) == written
