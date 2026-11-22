"""Story 13.1 (FR-17, AD-1, AD-16, C-2): `analysis.completion`, table-driven."""

import ast
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.analysis import completion as module
from app.analysis.completion import (
    COMPLETION_STEPS,
    CompletionSettings,
    Correction,
    DecisionLogSummary,
    LoggedWeek,
    StepInputs,
    completion,
)

AT = datetime(2026, 11, 2, 12, tzinfo=UTC)
ALL = {step: AT for step in COMPLETION_STEPS}
PARTS = ("choice", "interactive", "long", "adapted")


def settings(**changes) -> CompletionSettings:
    base = {
        "obligatory": True,
        "required_share": 80,
        "explanation_min_length": 50,
        "test_required_parts": PARTS,
    }
    return CompletionSettings(**(base | changes))


def log(*rows: tuple[str, str], guided: int = 2, weeks: int | None = None) -> DecisionLogSummary:
    """A Decision log: the Guided Weeks, then one row per `(decided_by, reason)` after them."""
    guided_rows = [LoggedWeek(week, "guided", "initial") for week in range(1, guided + 1)]
    later = [LoggedWeek(guided + i, by, why) for i, (by, why) in enumerate(rows, start=1)]
    return DecisionLogSummary(
        weeks=weeks if weeks is not None else guided + len(rows),
        guided_weeks=guided,
        rows=(*guided_rows, *later),
    )


OWN = ("student", "initial")


def inputs(**changes) -> StepInputs:
    base = {
        "events": ALL,
        "explanation_length": 200,
        "test_status": "submitted",
        "test_parts": None,
    }
    return StepInputs(**(base | changes))


CASES = [
    # (id, steps, log, corrections, settings, expected done per step, requirement_met)
    (
        "all done",
        inputs(),
        log(*[OWN] * 10),
        (),
        settings(),
        dict.fromkeys(COMPLETION_STEPS, True),
        True,
    ),
    (
        "share exactly at the limit",
        inputs(),
        log(*[OWN] * 8, ("llm", "initial"), ("llm", "initial")),
        (),
        settings(),
        {"class_game": True},
        True,
    ),
    (
        "one Week under the limit",
        inputs(),
        log(*[OWN] * 7, *[("llm", "initial")] * 3),
        (),
        settings(),
        {"class_game": False},
        False,
    ),
    (
        "takeover and playout Weeks count as not ordered",
        inputs(),
        log(*[OWN] * 7, ("llm", "takeover_inactivity"), ("student", "playout"), ("llm", "playout")),
        (),
        settings(),
        {"class_game": False},
        False,
    ),
    (
        "a peer's Takeover is not the Student's Order",
        inputs(),
        log(*[OWN] * 7, *[("student", "takeover_peer")] * 3),
        (),
        settings(),
        {"class_game": False},
        False,
    ),
    (
        "a reclaimed Seat orders again",
        inputs(),
        log(*[OWN] * 6, *[("student", "reclaim")] * 2, *[("llm", "takeover_staff")] * 2),
        (),
        settings(),
        {"class_game": True},
        True,
    ),
    (
        "unplayed Weeks count as not ordered",
        inputs(),
        log(*[OWN] * 7, weeks=12),
        (),
        settings(),
        {"class_game": False},
        False,
    ),
    (
        "an adjusted share",
        inputs(),
        log(*[OWN] * 6, *[("llm", "initial")] * 4),
        (),
        settings(adjusted_share=60),
        {"class_game": True},
        True,
    ),
    ("no Class game snapshot", inputs(), None, (), settings(), {"class_game": False}, False),
    (
        "no Week after the Guided Weeks",
        inputs(),
        log(guided=4),
        (),
        settings(),
        {"class_game": True},
        True,
    ),
    (
        "class game not recorded",
        inputs(events={s: AT for s in COMPLETION_STEPS if s != "class_game"}),
        log(*[OWN] * 10),
        (),
        settings(),
        {"class_game": False},
        False,
    ),
    (
        "a short Explanation",
        inputs(explanation_length=49),
        log(*[OWN] * 10),
        (),
        settings(),
        {"debrief": False},
        False,
    ),
    (
        "an Explanation at the minimum",
        inputs(explanation_length=50),
        log(*[OWN] * 10),
        (),
        settings(),
        {"debrief": True},
        True,
    ),
    (
        "no Explanation",
        inputs(explanation_length=None),
        log(*[OWN] * 10),
        (),
        settings(),
        {"debrief": False},
        False,
    ),
    (
        "an auto-submitted test without content in a part",
        inputs(test_status="auto_submitted", test_parts={"choice": True, "long": False}),
        log(*[OWN] * 10),
        (),
        settings(),
        {"test_submitted": False},
        False,
    ),
    (
        "an auto-submitted test with content in each part it holds",
        inputs(test_status="auto_submitted", test_parts={"choice": True, "long": True}),
        log(*[OWN] * 10),
        (),
        settings(),
        {"test_submitted": True},
        True,
    ),
    (
        "a part not required is not checked",
        inputs(test_status="auto_submitted", test_parts={"choice": True, "long": False}),
        log(*[OWN] * 10),
        (),
        settings(test_required_parts=("choice",)),
        {"test_submitted": True},
        True,
    ),
    (
        "the Student's own submit counts as it is",
        inputs(test_status="submitted", test_parts={"choice": True, "long": False}),
        log(*[OWN] * 10),
        (),
        settings(),
        {"test_submitted": True},
        True,
    ),
    (
        "a correction to done",
        inputs(),
        log(*[OWN] * 5, *[("llm", "playout")] * 5),
        (Correction("class_game", True, AT),),
        settings(),
        {"class_game": True},
        True,
    ),
    (
        "the latest correction applies",
        inputs(),
        log(*[OWN] * 10),
        (
            Correction("debrief", True, AT),
            Correction("debrief", False, AT + timedelta(hours=1)),
            Correction("debrief", True, AT - timedelta(hours=1)),
        ),
        settings(),
        {"debrief": False},
        False,
    ),
    (
        "a Class session that is not obligatory",
        inputs(),
        log(*[OWN] * 10),
        (),
        settings(obligatory=False),
        dict.fromkeys(COMPLETION_STEPS, True),
        None,
    ),
    (
        "nothing recorded",
        inputs(events={}),
        None,
        (),
        settings(),
        dict.fromkeys(COMPLETION_STEPS, False),
        False,
    ),
]


@pytest.mark.parametrize(
    ("steps", "logged", "corrections", "config", "done", "met"),
    [c[1:] for c in CASES],
    ids=[c[0] for c in CASES],
)
def test_completion(steps, logged, corrections, config, done, met):
    status = completion(steps, logged, corrections, config)
    for name, expected in done.items():
        assert status.step(name).done is expected, name
    assert status.requirement_met is met
    assert [each.step for each in status.steps] == list(COMPLETION_STEPS)


def test_recorded_and_done_are_both_carried_with_the_date():
    status = completion(inputs(explanation_length=10), log(*[OWN] * 10), (), settings())
    debrief = status.step("debrief")
    assert (debrief.recorded, debrief.recorded_at, debrief.done, debrief.corrected) == (
        True,
        AT,
        False,
        False,
    )
    corrected = completion(inputs(events={}), None, (Correction("replay", True, AT),), settings())
    replay = corrected.step("replay")
    assert (replay.recorded, replay.recorded_at, replay.done, replay.corrected) == (
        False,
        None,
        True,
        True,
    )


def test_the_shares_and_the_playout_figures():
    status = completion(
        inputs(),
        log(
            *[OWN] * 7,
            ("llm", "takeover_inactivity"),
            ("llm", "playout"),
            ("rule_based", "playout"),
        ),
        (),
        settings(adjusted_share=60),
    )
    assert (status.ordered_share, status.playout_share, status.required_share) == (70, 20, 60)
    assert (status.ordered_weeks, status.weeks_after_guided, status.playout_weeks) == (7, 10, 2)
    assert completion(inputs(), None, (), settings()).ordered_share is None


def test_a_recorded_assessment_ready_step_changes_nothing():
    """AD-16, C-2: the AI assessment is never an input; its step event is ignored."""
    for logged in (log(*[OWN] * 10), log(*[OWN] * 5, *[("llm", "initial")] * 5)):
        plain = completion(inputs(), logged, (), settings())
        with_ai = completion(inputs(events=ALL | {"assessment_ready": AT}), logged, (), settings())
        assert with_ai == plain


def test_the_function_is_pure():
    """AD-1: no I/O, no clock, no AI assessment or Indicative letter module."""
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    names = [
        alias.name if isinstance(node, ast.Import) else f"{node.module}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in node.names
    ]
    allowed = ("collections.abc", "dataclasses", "typing")
    assert all(name in allowed for name in names), names
    source = Path(module.__file__).read_text(encoding="utf-8")
    for forbidden in ("now(", "today(", "open("):
        assert forbidden not in source, forbidden
