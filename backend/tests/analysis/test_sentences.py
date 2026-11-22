"""Story 9.4: the sentence templates (AD-7, AD-23) and the step-2 heading rendered by code from the
Game's customer demand series (FR-44): one variant per shape of demand, every number filled by
code in the Norwegian format."""

import copy
import importlib.util
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from app.analysis.sentences import (
    DEMAND_TEMPLATES,
    SentenceTemplates,
    demand_heading,
    format_number,
)
from app.engine import DemandPattern, GameSettings, demand_series

MIGRATION = Path(__file__).parents[2] / "migrations" / "versions" / "0104_sentence_templates.py"


def _version_1() -> dict:
    spec = importlib.util.spec_from_file_location("migration_0104", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SENTENCE_TEMPLATES_V1


V1 = _version_1()
TEMPLATES = SentenceTemplates.model_validate(V1)
PATTERN = TypeAdapter(DemandPattern)


def heading(pattern: dict, series: list[int]) -> tuple[str, str]:
    found = demand_heading(PATTERN.validate_python(pattern), series, TEMPLATES)
    return found.template_id, found.text


def test_the_classic_step_reads_as_the_spine_says():
    classic = GameSettings()
    series = demand_series(classic)
    assert heading(classic.demand.model_dump(), list(series)) == (
        "demand-step",
        "Kundene bestilte 4, så 8. Etter det endret de seg aldri.",
    )


STEP = {"kind": "step", "start": 4, "new_level": 8, "change_week": 5}
FLAT = "Kundene bestilte 4 hver uke. Det endret seg aldri."
NOISE = {"kind": "step+noise", "start": 4, "new_level": 8, "change_week": 3, "spread": 2}


@pytest.mark.parametrize(
    ("pattern", "series", "expected"),
    [
        # Flat: a step with no change, or one past the last Uke.
        (STEP | {"new_level": 4}, [4, 4, 4], ("demand-flat", FLAT)),
        (STEP | {"change_week": 9}, [4, 4, 4], ("demand-flat", FLAT)),
        # A fixed series that steps once is told as a step; thousands get a no-break space.
        (
            {"kind": "fixed", "values": [1200, 1200, 2500]},
            [1200, 1200, 2500],
            ("demand-step", "Kundene bestilte 1 200, så 2 500. Etter det endret de seg aldri."),
        ),
        # Noise around a step: the levels from the pattern, the range from the series.
        (
            NOISE,
            [3, 5, 9, 6, 10],
            (
                "demand-step-noise",
                "Kundene bestilte rundt 4, så rundt 8 fra Uke 3. Hver uke lå de mellom 3 og 10.",
            ),
        ),
        # Noise whose step lies past the game, and random demand: around one level.
        (
            NOISE | {"change_week": 9},
            [3, 5, 4],
            ("demand-random", "Kundene bestilte rundt 4 hver uke, aldri under 3 og aldri over 5."),
        ),
        (
            {"kind": "random", "mean": 8, "spread": 3},
            [7, 11, 5, 8],
            ("demand-random", "Kundene bestilte rundt 8 hver uke, aldri under 5 og aldri over 11."),
        ),
        # Any other fixed series: its first Uke and its range after that.
        (
            {"kind": "fixed", "values": [4, 9, 2, 6]},
            [4, 9, 2, 6],
            ("demand-varied", "Kundene bestilte 4 i Uke 1, og siden aldri under 2 eller over 9."),
        ),
    ],
)
def test_each_shape_of_demand_has_its_variant(pattern, series, expected):
    assert heading(pattern, series) == expected


def test_numbers_are_written_the_norwegian_way():
    assert [format_number(v) for v in (0, 24, 1234, -1234567)] == [
        "0",
        "24",
        "1 234",
        "−1 234 567",
    ]


def broken(change) -> dict:
    body = copy.deepcopy(V1)
    change(body["templates"])
    return body


@pytest.mark.parametrize(
    "change",
    [
        lambda t: t[1].update(text="Kundene bestilte {before}!"),  # an exclamation mark
        lambda t: t[1].update(text="Kundene bestilte {level}."),  # a value the id is not given
        lambda t: t[1].update(text="Kundene bestilte {before.real}."),  # not a plain slot
        lambda t: t[1].update(text="Kundene bestilte {before"),  # not well formed
        lambda t: t[1].update(text="Kundene bestilte {before:d}."),  # a format spec
        lambda t: t[1].update(text="Kundene bestilte {before!r}."),  # a conversion
        lambda t: t[1].update(text="Kundene bestilte {before:{after}}."),  # a nested slot
        lambda t: t.pop(0),  # a demand variant missing
        lambda t: t.append(dict(t[0])),  # an id twice
    ],
)
def test_a_template_set_that_could_render_wrongly_is_refused(change):
    with pytest.raises(ValidationError):
        SentenceTemplates.model_validate(broken(change))


def test_version_1_holds_every_demand_variant():
    assert {t.id for t in TEMPLATES.templates} == set(DEMAND_TEMPLATES)
