"""Completion of a Class session (Story 13.1, FR-17, AD-1, AD-16, C-2).

Pure: no I/O, no clock, and no input from the AI assessment or the Indicative letter. The one
definition of whether a Student has done each step and met the requirement of an Obligatory class
session; `reports.service.completion_status` gathers the inputs and every reader (Hjem, the
Studentside, the Completion export, the Student report) goes through it.

A step is `recorded` when `modules/progress` holds its step event, and `done` when it counts:
- `class_game`: recorded, and the Student's own Orders over the Weeks after the Guided Weeks are
  at least the required share (the adjusted share where the Student has one). An own Order is a
  Decision log row with `decided_by = student` that no Takeover or playout placed; a Week never
  played counts as not ordered.
- `debrief`: recorded, and the Explanation has at least the minimum length.
- `test_submitted`: recorded, and an auto-submitted attempt has content in each required part it
  holds. A Student's own submit counts as it is.
- `quiz_passed`, `replay`: recorded.
The latest correction of a step (Story 13.3) sets `done` whatever the rest says. Time spent and
constant Orders are never inputs.
"""

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

__all__ = [
    "COMPLETION_STEPS",
    "CompletionSettings",
    "CompletionStatus",
    "CompletionStep",
    "Correction",
    "DecisionLogSummary",
    "LoggedWeek",
    "StepInputs",
    "completion",
]

COMPLETION_STEPS: tuple[str, ...] = (
    "class_game",
    "debrief",
    "quiz_passed",
    "replay",
    "test_submitted",
)
"""The steps of the requirement, in order (FR-17), named as `progress.Step` values."""

NOT_OWN_REASONS = frozenset({"takeover_inactivity", "takeover_staff", "takeover_peer", "playout"})
"""Occupancy reasons whose Orders count as not ordered by the Student (FR-17, AD-15)."""

TestStatus = Literal["open", "submitted", "auto_submitted"]

Moment = Any
"""When something happened: an aware `datetime` the caller passes, only ever compared. The
module does not import `datetime`, so it cannot read a clock (AD-1)."""


@dataclass(frozen=True)
class LoggedWeek:
    """One Decision log row of the Student's Seat: its Week, who decided it and why the occupant
    held the Seat (`seat_weeks.decided_by` and `reason`)."""

    week: int
    decided_by: str
    reason: str


@dataclass(frozen=True)
class DecisionLogSummary:
    """The Student's Class game as Completion reads it: the snapshot's number of Weeks and Guided
    Weeks, and the Seat's Decision log rows."""

    weeks: int
    guided_weeks: int
    rows: Sequence[LoggedWeek] = ()


@dataclass(frozen=True)
class StepInputs:
    """The step events of the Student in the Class session (step value → when it was recorded),
    the Explanation's length (None without one), and the Individual test attempt's status and
    which of its parts hold content (None without an attempt)."""

    events: Mapping[str, Moment]
    explanation_length: int | None = None
    test_status: TestStatus | None = None
    test_parts: Mapping[str, bool] | None = None


@dataclass(frozen=True)
class Correction:
    """A Lecturer's correction of one step (Story 13.3): the new status and when it was made."""

    step: str
    done: bool
    at: Moment


@dataclass(frozen=True)
class CompletionSettings:
    """What the Class session and configuration say: whether it is obligatory, the required share
    as a whole percent, the Student's adjusted share (None: the session's own), and the two
    minimums [ASSUMPTION: these minimums]."""

    obligatory: bool
    required_share: int
    explanation_min_length: int
    test_required_parts: Collection[str]
    adjusted_share: int | None = None


@dataclass(frozen=True)
class CompletionStep:
    """One step: whether its step event is recorded and when, whether it counts as done after the
    share, the minimums and any correction, and whether a correction decided it."""

    step: str
    recorded: bool
    recorded_at: Moment | None
    done: bool
    corrected: bool = False


@dataclass(frozen=True)
class CompletionStatus:
    """A Student's Completion status in one Class session. `requirement_met` is None when the Class
    session is not obligatory. The shares are whole percents rounded down, None without a Class
    game snapshot or without a Week after the Guided Weeks (the Week counts are then 0);
    `required_share` is the one that applies to this Student."""

    steps: tuple[CompletionStep, ...]
    obligatory: bool
    requirement_met: bool | None
    required_share: int
    ordered_share: int | None = None
    playout_share: int | None = None
    ordered_weeks: int | None = None
    weeks_after_guided: int | None = None
    playout_weeks: int | None = None

    def step(self, name: str) -> CompletionStep:
        """The step named `name` (a value of `COMPLETION_STEPS`)."""
        return next(each for each in self.steps if each.step == name)


def _percent(part: int, whole: int) -> int:
    return part * 100 // whole


def _class_game_counts(log: DecisionLogSummary | None, required: int) -> tuple[bool, dict]:
    """Whether the own Orders reach the share, and the figures behind it."""
    if log is None:
        return False, {}
    after = max(log.weeks - log.guided_weeks, 0)
    later = [row for row in log.rows if log.guided_weeks < row.week <= log.weeks]
    own = sum(
        1 for row in later if row.decided_by == "student" and row.reason not in NOT_OWN_REASONS
    )
    played_out = sum(1 for row in later if row.reason == "playout")
    if after == 0:
        # No Week after the Guided Weeks to order in: nothing is asked of the Student.
        return True, {"ordered_weeks": 0, "weeks_after_guided": 0, "playout_weeks": 0}
    figures = {
        "ordered_share": _percent(own, after),
        "playout_share": _percent(played_out, after),
        "ordered_weeks": own,
        "weeks_after_guided": after,
        "playout_weeks": played_out,
    }
    # Exact: 8 of 10 meets 80 %, 79 of 100 does not, with no rounding in between.
    return own * 100 >= required * after, figures


def _test_counts(steps: StepInputs, settings: CompletionSettings) -> bool:
    if steps.test_status != "auto_submitted":
        return True
    parts = steps.test_parts or {}
    return all(parts[part] for part in settings.test_required_parts if part in parts)


def completion(
    steps: StepInputs,
    decision_log_summary: DecisionLogSummary | None,
    corrections: Sequence[Correction],
    settings: CompletionSettings,
) -> CompletionStatus:
    """The Student's Completion status (FR-17). See the module docstring for the rules."""
    required = (
        settings.adjusted_share if settings.adjusted_share is not None else settings.required_share
    )
    game_counts, figures = _class_game_counts(decision_log_summary, required)
    rule = {
        "class_game": game_counts,
        "debrief": (steps.explanation_length or 0) >= settings.explanation_min_length,
        "quiz_passed": True,
        "replay": True,
        "test_submitted": _test_counts(steps, settings),
    }
    latest: dict[str, Correction] = {}
    for correction in corrections:
        held = latest.get(correction.step)
        if held is None or correction.at >= held.at:
            latest[correction.step] = correction
    found = []
    for name in COMPLETION_STEPS:
        at = steps.events.get(name)
        correction = latest.get(name)
        if correction is not None:
            done, corrected = correction.done, True
        else:
            done, corrected = at is not None and rule[name], False
        found.append(
            CompletionStep(
                step=name, recorded=at is not None, recorded_at=at, done=done, corrected=corrected
            )
        )
    return CompletionStatus(
        steps=tuple(found),
        obligatory=settings.obligatory,
        requirement_met=all(each.done for each in found) if settings.obligatory else None,
        required_share=required,
        **figures,
    )
