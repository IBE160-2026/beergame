"""The AI assessment (Epic 12). Other modules import only this file.

Story 12.1 (FR-61, AD-9, AD-12): the «KI-vurdering» switch of a Class session. It is on unless a
Lecturer switched it off; «Lagre Klasseøkt» stores it here (`set_switch`) inside the save's
transaction, and `sessions.lock_test` pins it at the original Test deadline (`pin_switch`), once
and idempotently, in the same step that pins what else hangs on that deadline. Once pinned it
never changes (a trigger refuses it too). `assessment_due` is the one question the assessment of
Story 12.2 asks before it assesses anything or calls an LLM: only a pinned switch that is on says
yes, so nothing is assessed before the Test deadline and nothing at all when it is off.

Story 12.2 (FR-54, AD-6, AD-9, AD-23): the assessment of one Test attempt.

- `schedule` is called by `tests.commands.close_attempt` only, in its transaction, when the attempt
  is closed at its `effective_deadline`: when `assessment_due` says yes it defers the idempotent job
  `assessment.assess(attempt_id)` on `llm-batch`, ids only. Nothing else enqueues a first
  assessment; the job itself defers its later runs.
- `assess` (the job) reads the attempt through the reader `tests` registers
  (`register_attempt_reader`: this module imports no other module), keeps one `ai_assessments` row
  per attempt, and makes one `gateway.run(purpose="assessment")` call per long-answer or Adapted
  item that has no score yet, on the Class session's budget and the model config the
  Test-deadline lock pinned with the switch (`pinned_config`). The output is one overall score on
  the Scoring guide's five-step scale (`AssessmentOutput`); an empty answer gets step 0 by code
  with no call. A typed failure or a `GatewayError` leaves the item without a score: the job never
  asks again in the same run. When every item has a score the assessment is `ready`; otherwise it
  stays `incomplete` and one later run is deferred after a back-off (`assessment_retry_minutes`,
  doubled per run), until `assessment_max_runs` runs have finished and it is `failed` (at once
  when no model config was pinned).
- Scores are written once; nothing here copies or recomputes the computed scores `tests` stored,
  and no total is stored: `analysis.total_score` makes it when read.

Story 12.3 (FR-54, AD-6, AD-7): written feedback. When the pinned config names prompt
`assessment/v2` or later, the call's output (`analysis.feedback.AssessmentFeedbackOutput`) also
holds one to four feedback sentences built from approved template ids, quote spans over the
scrubbed answer, criterion codes and fact ids. `analysis.feedback.validate_feedback` checks them
(Epic 9's AI-text validator for the facts, on the item's stored facts set); code renders the text,
the quotes mapped through the gateway's offset map to the Student's original answer. A rejected
feedback is asked for once more with a new call; when that one is rejected too (or fails), the
feedback is left out with the note `dropped` and the first call's score is kept. A config naming
`assessment/v1` keeps the score-only output of Story 12.2.

Story 12.4 (FR-54, FR-55, FR-61, FR-69, AD-9, AD-16): being told.

- `schedule` now also creates the attempt's `ai_assessments` row (`incomplete`, no run yet, with
  the attempt's `effective_deadline` as `due_at`) in the close's transaction, so every closed
  attempt of a due Class session has a row even when its job is lost or crashes before a run.
- The run that marks an assessment `ready` records the `assessment_ready` step through
  `progress.record_step` and enqueues the `assessment_ready` digest notice
  (`platform/notify`), in the same transaction; both are idempotent. The run that marks it
  `failed` enqueues one `assessment_failed` digest notice per active Admin per Class session.
- `due_overdue` / `overdue_due` are the sweep's `assessment.overdue` action: an assessment still
  `incomplete` `assessment_overdue_hours` after `due_at` is logged as `assessment_overdue` once,
  and its job is deferred again when no job of it is alive and runs remain.
- `stop_for_session` sets a stop mark (time, actor, audited) that `schedule`, the job and the
  sweep honour and the Student's view reads as switched off unless the assessment is ready;
  `resume_for_session` clears it (audited), resets every unsettled or failed assessment of the
  Class session and defers each again.

Story 12.6 (FR-56, AD-1, AD-12): the Indicative letter. The switch row also holds the letter
setting (`all`, `student_choice`, `unavailable`) and the lower bounds of A to E, stored by «Lagre
Klasseøkt» (`set_letter`) and pinned with the switch, the bounds in force included (the configured
defaults when none were stored). `letter_chosen` on the assessment is the Student's own opt-in
(`set_letter_choice`). `letter_for` is the one place that decides who gets a letter: the
Student's own view, the staff (only when it is shown to everyone), never an export or a ZIP, and a
report only when the Student asks for it; the letter itself comes from
`analysis.indicative_letter` only, and never for an assessment that is not ready. The caller
passes the Institution's no-letter mark to `letter_rules` (this module imports no `identity`).

Story 12.5 (FR-55, AD-12): flags. `set_flag` stores or removes the Student's «Marker som feil» on
one item's written feedback (`ai_feedback_flags`), emitting `user` and `session`; the caller
(`tests`) has judged that the Student's view shows that feedback now. `AssessmentRecord.flags`
carries the flagged items, and `summaries_for_session` gives each Student's assessment state,
runs and flag count for the staff list of the Klasseøkt and for Epic 13.

Story 12.9 (FR-82, AD-27): blind human scoring of a Control test. `name_scorer` / `remove_scorer`
keep the Users the Admin named for one Control test (`control_test_scorers`); `insert_human_score`
writes one score per answer and scorer once (a second is refused, and a trigger refuses any
update); `human_scores_by` and `score_counts` read them back. The caller (`tests.scoring`) has
judged access through `platform/authz` and writes the audit rows.

Story 12.10 (FR-81, AD-27): `record_human_score` is how a scorer's score is stored. The caller
first holds the Control test's scorer rows (`hold_scorers`, so two last scores never miss each
other) and then reads the listed answers; it refuses a scorer no longer named, inserts once and,
when every named scorer has now scored every listed answer and no attempt is still open, calls
`content.service.mark_checked` for the pinned Scoring guide version and model config in the same
transaction: this module is its only caller. `settle_after_removal` does the same when a removal
leaves the remaining scorers complete.
`scores_of` reads every score of the listed answers for the results page.

No answer text, guide text or score is logged: ids, counts and codes only.

This module imports no feature module but `progress.service` (AD-16: any module records a step
through it) and `content.service` (Story 12.10, AD-27: the checked mark; `content` imports no
feature module): `sessions` and `tests` call it, never the other way round, and the Admins come
through the reader `sessions` registers."""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Annotated, Any, Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, literal, select, update
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import budget as ai_budget
from app.ai import calls as ai_calls
from app.ai import config as ai_config
from app.ai import gateway
from app.analysis import feedback as feedback_rules
from app.analysis.facts import FactSet
from app.analysis.letter import Letter, indicative_letter, parse_thresholds
from app.analysis.narration import NarrationTemplates, citable, fact_lines
from app.analysis.total import SCALE_TOP
from app.modules.assessment.models import (
    ai_assessments,
    ai_feedback_flags,
    ai_item_scores,
    assessment_switches,
    control_test_scorers,
    human_scores,
)
from app.modules.content import service as content
from app.modules.progress import service as progress
from app.platform import audit, auth, events, jobs, notify
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

__all__ = [
    "own_records",
    "ASSESS_TASK",
    "DEFAULT_SWITCH",
    "PURPOSE",
    "FEEDBACK_VERSION",
    "FAILED_NOTICE",
    "READY_NOTICE",
    "RESUMED",
    "STOPPED",
    "AssessmentOutput",
    "AssessmentRecord",
    "AssessmentSummary",
    "DEFAULT_LETTER_SETTING",
    "LetterReader",
    "LetterRules",
    "LetterSetting",
    "ItemFeedback",
    "AttemptToAssess",
    "ItemToAssess",
    "PinnedConfig",
    "Switch",
    "SwitchPinned",
    "assess",
    "assessment_due",
    "assessment_key",
    "assessment_of",
    "backoff",
    "copy_switch",
    "default_thresholds",
    "letter_for",
    "letter_rules",
    "due_overdue",
    "mock_feedback",
    "mock_score",
    "overdue_due",
    "pin_switch",
    "pinned_config",
    "register_admin_reader",
    "register_attempt_reader",
    "resume_for_session",
    "schedule",
    "set_flag",
    "set_letter",
    "set_letter_choice",
    "set_switch",
    "stop_for_session",
    "summaries_for_session",
    "switch_of",
    "HumanScore",
    "human_scores_by",
    "insert_human_score",
    "hold_scorers",
    "record_human_score",
    "RecordedScore",
    "ScorerNotNamed",
    "scores_of",
    "settle_after_removal",
    "name_scorer",
    "remove_scorer",
    "score_counts",
    "scorers_of",
]

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class Switch:
    """The «KI-vurdering» switch of a Class session: on or off, and when the Test-deadline lock
    pinned it (None while it can still change)."""

    enabled: bool
    pinned_at: datetime | None
    stopped_at: datetime | None = None
    """Story 12.4: when `stop_for_session` stopped the assessment; None when it runs."""
    letter_setting: LetterSetting = "student_choice"
    """Story 12.6: the Indicative letter setting the Lecturer saved."""
    letter_thresholds: dict[str, int] | None = None
    """Story 12.6: the stored lower bounds of A to E; None for the configured defaults."""

    @property
    def pinned(self) -> bool:
        return self.pinned_at is not None

    @property
    def stopped(self) -> bool:
        return self.stopped_at is not None


DEFAULT_SWITCH = Switch(enabled=True, pinned_at=None)
"""A Class session with no row: on, not pinned (FR-61: on by default)."""

LetterSetting = Literal["all", "student_choice", "unavailable"]
"""Story 12.6 (FR-56): the Indicative letter shown to everyone in the Class session, left to each
Student for their own view, or unavailable."""

DEFAULT_LETTER_SETTING: LetterSetting = "student_choice"


def default_thresholds() -> dict[str, int]:
    """The configured default bounds of A to E (`indicative_letter_thresholds`, placeholders)."""
    return parse_thresholds(get_settings().indicative_letter_thresholds)


class SwitchPinned(Exception):
    """The switch was pinned at the Test deadline and no longer changes."""


async def switch_of(
    session: AsyncSession, class_session_id: uuid.UUID, *, share: bool = False
) -> Switch:
    """The Class session's switch as stored, or `DEFAULT_SWITCH` when nothing is stored. With
    `share` its row is share-locked until the transaction ends (Story 12.4: a close and a
    `resume_for_session` then see each other's work)."""
    query = select(
        assessment_switches.c.enabled,
        assessment_switches.c.pinned_at,
        assessment_switches.c.stopped_at,
        assessment_switches.c.letter_setting,
        assessment_switches.c.letter_thresholds,
    ).where(assessment_switches.c.class_session_id == class_session_id)
    if share:
        query = query.with_for_update(read=True)
    row = (await session.execute(query)).first()
    if row is None:
        return DEFAULT_SWITCH
    return Switch(
        enabled=row.enabled,
        pinned_at=row.pinned_at,
        stopped_at=row.stopped_at,
        letter_setting=row.letter_setting,
        letter_thresholds=dict(row.letter_thresholds) if row.letter_thresholds else None,
    )


async def set_switch(
    session: AsyncSession, class_session_id: uuid.UUID, enabled: bool, *, now: datetime
) -> None:
    """Store the switch in the caller's transaction (the caller holds the Class session's row
    lock). Raises `SwitchPinned` when it is pinned; an unchanged value stores nothing."""
    current = await switch_of(session, class_session_id)
    if current.enabled == enabled:
        return
    if current.pinned:
        raise SwitchPinned
    statement = insert(assessment_switches).values(
        class_session_id=class_session_id, enabled=enabled, updated_at=now
    )
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[assessment_switches.c.class_session_id],
            set_={"enabled": statement.excluded.enabled, "updated_at": now},
            where=assessment_switches.c.pinned_at.is_(None),
        )
    )


async def pin_switch(
    session: AsyncSession,
    class_session_id: uuid.UUID,
    *,
    at: datetime,
    model_config_id: uuid.UUID | None = None,
    effort_level: str | None = None,
) -> bool:
    """Pin the switch as it stands (on when nothing is stored) as of `at`, in the caller's
    transaction: `sessions.lock_test` at the original Test deadline. Story 12.2: with it the model
    config (and Effort level) every assessment of the Class session uses; None when no config
    could be pinned. True when this call pinned it; a second call changes nothing and answers
    False."""
    values = {
        "pinned_at": at,
        "updated_at": at,
        "model_config_id": model_config_id,
        "effort_level": effort_level,
    }
    # Story 12.6: the letter bounds in force are pinned too, so a later change of the configured
    # defaults never moves a pinned Class session's letters.
    defaults = default_thresholds()
    statement = insert(assessment_switches).values(
        class_session_id=class_session_id, enabled=True, letter_thresholds=defaults, **values
    )
    pinned = await session.execute(
        statement.on_conflict_do_update(
            index_elements=[assessment_switches.c.class_session_id],
            set_={
                **values,
                "letter_thresholds": func.coalesce(
                    assessment_switches.c.letter_thresholds, literal(defaults, JSONB)
                ),
            },
            where=assessment_switches.c.pinned_at.is_(None),
        ).returning(assessment_switches.c.class_session_id)
    )
    return pinned.first() is not None


async def copy_switch(
    session: AsyncSession, source_id: uuid.UUID, target_id: uuid.UUID, *, now: datetime
) -> None:
    """«Lag kopi» (Story 5.18, FR-66): the new Class session takes the source's value, not its
    pin. Nothing is stored when the source's is on, the default."""
    source = await switch_of(session, source_id)
    if not source.enabled:
        await set_switch(session, target_id, False, now=now)
    # Story 12.6 (FR-66): the letter setting and the bounds the source's Lecturer stored. A pinned
    # source holds the bounds the pin stored, which are copied as they stand.
    if source.letter_setting != DEFAULT_LETTER_SETTING or source.letter_thresholds is not None:
        await set_letter(
            session,
            target_id,
            setting=source.letter_setting,
            thresholds=source.letter_thresholds,
            now=now,
        )


async def set_letter(
    session: AsyncSession,
    class_session_id: uuid.UUID,
    *,
    setting: LetterSetting | None,
    thresholds: dict[str, int] | None,
    now: datetime,
) -> None:
    """Story 12.6 (FR-56): store the letter setting and/or the bounds of A to E (None keeps each)
    in the caller's transaction, which holds the Class session's row lock and has judged them.
    Raises `SwitchPinned` when the switch is pinned and something would change."""
    current = await switch_of(session, class_session_id)
    changes: dict[str, Any] = {}
    if setting is not None and setting != current.letter_setting:
        changes["letter_setting"] = setting
    if thresholds is not None and thresholds != current.letter_thresholds:
        changes["letter_thresholds"] = dict(thresholds)
    if not changes:
        return
    if current.pinned:
        raise SwitchPinned
    statement = insert(assessment_switches).values(
        class_session_id=class_session_id, updated_at=now, **changes
    )
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[assessment_switches.c.class_session_id],
            set_={**changes, "updated_at": now},
            where=assessment_switches.c.pinned_at.is_(None),
        )
    )


@dataclass(frozen=True)
class LetterRules:
    """What decides a Class session's Indicative letter (Story 12.6): the setting in force (the
    Lecturer's, or `unavailable` when the Institution forbids the letter) and the bounds in
    force."""

    setting: LetterSetting
    thresholds: dict[str, int]
    forced: bool = False
    """The Institution's no-letter mark made it unavailable."""


def letter_rules(switch: Switch, *, institution_forbids: bool) -> LetterRules:
    """The rules in force for a Class session with `switch`; `institution_forbids` is the
    Institution's no-letter mark, which the caller reads through `identity.service`."""
    return LetterRules(
        setting="unavailable" if institution_forbids else switch.letter_setting,
        thresholds=switch.letter_thresholds or default_thresholds(),
        forced=institution_forbids,
    )


LetterReader = Literal["student", "staff", "export", "zip", "report"]
"""Who a letter is read for (Story 12.6, FR-56, AD-12, C-2): the Student's own view, the staff of
the Class, an export, a ZIP of reports, or one report (`requested_by_student` says whose ask)."""


def letter_for(
    rules: LetterRules,
    *,
    total: float | None,
    total_max: int | None,
    ready: bool,
    opted_in: bool,
    reader: LetterReader,
    requested_by_student: bool = False,
) -> Letter | None:
    """The Indicative letter a `reader` may be given, or None (Story 12.6, FR-56). None while the
    assessment is not ready (no total), when the letter is unavailable, and always for an export
    or a ZIP. The staff get it only when it is shown to everyone; the Student also when they
    turned it on for themselves (`opted_in`); a report only when the Student asks for it, then as
    the Student's own view. The letter is `analysis.indicative_letter` of the total over its
    maximum; it is never an input to Completion."""
    if not ready or total is None or not total_max or rules.setting == "unavailable":
        return None
    if reader in ("export", "zip"):
        return None
    if reader == "report":
        if not requested_by_student:
            return None
        reader = "student"
    shown = rules.setting == "all" or (
        reader == "student" and rules.setting == "student_choice" and opted_in
    )
    if not shown:
        return None
    return indicative_letter(total, rules.thresholds, total_max)


async def set_letter_choice(attempt_id: uuid.UUID, on: bool) -> bool:
    """Story 12.6 (FR-56, AD-12): the Student turns the Indicative letter on or off for their own
    view, stored on their own assessment, idempotently, in a transaction of its own; a change
    emits `user:<student>` (their other tabs). Not audited: the Student's own view. False when
    the attempt has no assessment. The caller judges that the choice is open."""
    async with get_sessionmaker().begin() as s:
        row = (
            await s.execute(
                select(
                    ai_assessments.c.id, ai_assessments.c.user_id, ai_assessments.c.letter_chosen
                )
                .where(ai_assessments.c.attempt_id == attempt_id)
                .with_for_update()
            )
        ).first()
        if row is None:
            return False
        if row.letter_chosen != on:
            await s.execute(
                update(ai_assessments).where(ai_assessments.c.id == row.id).values(letter_chosen=on)
            )
            await events.emit(s, "user", str(row.user_id))
            log.info("assessment_letter_chosen", assessment_id=str(row.id), on=on)
    return True


async def assessment_due(
    class_session_id: uuid.UUID, *, session: AsyncSession | None = None
) -> bool:
    """Whether the Class session's Individual tests are to be assessed by the AI: only once the
    Test-deadline lock has pinned the switch, and only when it is on (FR-61, AD-9). Story 12.2's
    assessment asks this before it creates an assessment or makes any LLM call."""
    if session is not None:
        switch = await switch_of(session, class_session_id)
    else:
        async with get_sessionmaker()() as s:
            switch = await switch_of(s, class_session_id)
    return switch.pinned and switch.enabled


# Story 12.2: the assessment of one Test attempt.

ASSESS_TASK = "assessment.assess"
"""The `llm-batch` task that assesses one Test attempt."""

PURPOSE = "assessment"
"""The gateway purpose of one item's score (`prompts/assessment/v<N>.md`)."""

Status = Literal["incomplete", "ready", "failed"]


def assessment_key(attempt_id: object) -> str:
    """The job's queueing lock: one waiting assessment job per attempt."""
    return f"assessment:{attempt_id}"


class AssessmentOutput(BaseModel):
    """What the LLM answers for one item: one overall score on the five-step scale, never a score
    per criterion (FR-54, FR-81)."""

    model_config = ConfigDict(extra="forbid")

    score: Annotated[int, Field(ge=0, le=SCALE_TOP)]


@dataclass(frozen=True)
class ItemToAssess:
    """One long-answer or Adapted item of a closed attempt, as the prompt needs it: the question
    as the Student read it, their answer (None when not answered), the pinned Scoring guide entry
    (title, guide text, criteria as `(code, weight, text)`) and, for an Adapted item, the lines of
    the facts it cites from its stored facts set (`""` otherwise). Story 12.3: an Adapted item's
    stored facts set itself (`fact_set`, read by its id, never rebuilt) and the fact ids it was
    frozen with, which its feedback may cite."""

    item_id: str
    question: str
    answer: str | None
    guide_title: str
    guide_text: str
    criteria: tuple[tuple[str, int, str], ...]
    facts: str = ""
    fact_set: FactSet | None = None
    fact_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class AttemptToAssess:
    """A Test attempt as `tests` hands it to the assessment: whether it is closed, the pinned
    versions it was frozen and is scored with, the scale's labels and its items to score. Story
    12.3: the narration templates the Class session pinned, which a feedback sentence about the
    Student's game uses (None when they cannot be read)."""

    attempt_id: uuid.UUID
    user_id: uuid.UUID
    class_session_id: uuid.UUID
    closed: bool
    question_set_version: int
    scoring_guide_id: uuid.UUID | None
    scale: tuple[tuple[int, str], ...]
    items: tuple[ItemToAssess, ...]
    narration_templates: NarrationTemplates | None = None


AttemptReader = Callable[[uuid.UUID], Awaitable[AttemptToAssess | None]]
"""`(attempt_id)`: the attempt as the assessment needs it, or None when it is gone."""

_readers: list[AttemptReader] = []


def register_attempt_reader(reader: AttemptReader) -> None:
    """Register where a Test attempt is read (`tests` registers itself at import; this module may
    not import it). One reader; registering again replaces it."""
    _readers[:] = [reader]


def _reader() -> AttemptReader:
    if not _readers:  # pragma: no cover - the app, the worker and the tests import `tests`
        raise RuntimeError("no Test attempt reader is registered")
    return _readers[0]


AdminReader = Callable[[AsyncSession], Awaitable[list[uuid.UUID]]]
"""`(session)`: the ids of the active Admins, read in the caller's transaction."""

_admin_readers: list[AdminReader] = []


def register_admin_reader(reader: AdminReader) -> None:
    """Register where the active Admins are read (Story 12.4: `sessions` registers
    `identity.active_admins` at import; this module may not import `identity`). One reader;
    registering again replaces it."""
    _admin_readers[:] = [reader]


async def _admins(s: AsyncSession) -> list[uuid.UUID]:
    if not _admin_readers:  # pragma: no cover - the app, the worker and the tests import sessions
        raise RuntimeError("no Admin reader is registered")
    return await _admin_readers[0](s)


@dataclass(frozen=True)
class PinnedConfig:
    """The model config (and Effort level) the Test-deadline lock pinned for the assessment."""

    model_config_id: uuid.UUID
    effort_level: str | None


async def pinned_config(s: AsyncSession, class_session_id: uuid.UUID) -> PinnedConfig | None:
    """The model config pinned with the switch; None before the pin or when none was pinned."""
    row = (
        await s.execute(
            select(assessment_switches.c.model_config_id, assessment_switches.c.effort_level).where(
                assessment_switches.c.class_session_id == class_session_id,
                assessment_switches.c.pinned_at.is_not(None),
            )
        )
    ).first()
    if row is None or row.model_config_id is None:
        return None
    return PinnedConfig(row.model_config_id, row.effort_level)


async def schedule(
    s: AsyncSession,
    attempt_id: uuid.UUID,
    class_session_id: uuid.UUID,
    *,
    user_id: uuid.UUID,
    question_set_version: int,
    due_at: datetime,
    now: datetime,
) -> bool:
    """`tests.commands.close_attempt`'s call, in its transaction, once per attempt: when the
    pinned switch is on (`assessment_due`), create the attempt's assessment row (`incomplete`,
    no run yet, `due_at` its `effective_deadline`, Story 12.4) and defer its job, unless the
    Class session's assessment is stopped (`resume_for_session` defers it then). True when
    deferred. The one place a first assessment is enqueued (AD-9). The switch row is
    share-locked, so a resume running at the same time either sees this row or is seen as done."""
    switch = await switch_of(s, class_session_id, share=True)
    if not (switch.pinned and switch.enabled):
        return False
    pin = await pinned_config(s, class_session_id)
    await s.execute(
        insert(ai_assessments)
        .values(
            id=uuid.uuid7(),
            attempt_id=attempt_id,
            class_session_id=class_session_id,
            user_id=user_id,
            status="incomplete",
            runs=0,
            question_set_version=question_set_version,
            model_config_id=None if pin is None else pin.model_config_id,
            due_at=due_at,
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_nothing(constraint="uq_ai_assessments_attempt")
    )
    if switch.stopped:
        log.info("assessment_not_deferred", attempt_id=str(attempt_id), reason="stopped")
        return False
    return await _defer(s, attempt_id)


async def _defer(
    s: AsyncSession, attempt_id: uuid.UUID, *, schedule_at: datetime | None = None
) -> bool:
    """Defer one run of the attempt's assessment on `llm-batch`, ids only; False when a run of
    it waits already (its queueing lock)."""
    return await jobs.defer(
        s,
        ASSESS_TASK,
        queue=jobs.LLM_BATCH,
        queueing_lock=assessment_key(attempt_id),
        schedule_at=schedule_at,
        attempt_id=str(attempt_id),
    )


@dataclass(frozen=True)
class ItemFeedback:
    """An item's stored written feedback (Story 12.3): its text and parts (`{"text": …}` or
    `{"quote": [start, end]}` over the original answer) with the call it came from, or `dropped`
    when it was rejected twice and left out."""

    text: str | None
    parts: tuple[dict[str, Any], ...]
    llm_call_id: str | None
    dropped: bool


@dataclass(frozen=True)
class AssessmentRecord:
    """An attempt's stored assessment: its state, finished runs, why it failed (a code), the
    score of each assessed item by id, and (Story 12.3) the pinned Scoring guide version and model
    config it was made with and each item's written feedback, when it has any."""

    status: Status
    runs: int
    reason: str | None
    scores: dict[str, int]
    scoring_guide_id: uuid.UUID | None = None
    model_config_id: uuid.UUID | None = None
    feedback: dict[str, ItemFeedback] = field(default_factory=dict)
    flags: frozenset[str] = frozenset()
    """Story 12.5: the items whose written feedback the Student marked as wrong."""
    letter_chosen: bool = False
    """Story 12.6: the Student turned the Indicative letter on for their own view."""


async def assessment_of(s: AsyncSession, attempt_id: uuid.UUID) -> AssessmentRecord | None:
    """The attempt's assessment as stored, read in `s`; None before the job made one."""
    row = (
        (await s.execute(select(ai_assessments).where(ai_assessments.c.attempt_id == attempt_id)))
        .mappings()
        .one_or_none()
    )
    if row is None:
        return None
    found = (
        await s.execute(
            select(
                ai_item_scores.c.item_id,
                ai_item_scores.c.score,
                ai_item_scores.c.feedback,
                ai_item_scores.c.feedback_note,
            ).where(ai_item_scores.c.assessment_id == row["id"])
        )
    ).all()
    flagged = await s.scalars(
        select(ai_feedback_flags.c.item_id).where(ai_feedback_flags.c.assessment_id == row["id"])
    )
    return AssessmentRecord(
        status=row["status"],
        runs=row["runs"],
        reason=row["reason"],
        scores={each.item_id: each.score for each in found},
        scoring_guide_id=row["scoring_guide_id"],
        model_config_id=row["model_config_id"],
        feedback={
            each.item_id: _item_feedback(each.feedback, each.feedback_note)
            for each in found
            if each.feedback is not None or each.feedback_note is not None
        },
        flags=frozenset(flagged),
        letter_chosen=row["letter_chosen"],
    )


def _item_feedback(stored: Any, note: str | None) -> ItemFeedback:
    if not isinstance(stored, dict):
        return ItemFeedback(text=None, parts=(), llm_call_id=None, dropped=note == "dropped")
    return ItemFeedback(
        text=stored.get("text"),
        parts=tuple(stored.get("parts") or ()),
        llm_call_id=stored.get("llm_call_id"),
        dropped=False,
    )


def _quoted(text: str) -> str:
    """Free text as the prompt quotes it: angle brackets become look-alikes, so an answer cannot
    close its `<answer>` block and pose as the prompt's own words."""
    return text.replace("<", "‹").replace(">", "›")


def mock_score(answer: str) -> int:
    """The mock provider's deterministic score (AD-17): one step per 25 words, from 1, at most 4."""
    return min(SCALE_TOP, 1 + len(answer.split()) // 25)


FEEDBACK_VERSION = 2
"""The first `assessment` prompt version whose output holds written feedback (Story 12.3)."""


def _first_sentence(text: str) -> tuple[int, int]:
    """The first sentence of `text` (at most `MAX_QUOTE` characters) as a span, edge spaces left
    out."""
    start = len(text) - len(text.lstrip())
    end = min(len(text), start + feedback_rules.MAX_QUOTE)
    for n in range(start, end):
        if text[n] in ".?!":
            end = n + 1
            break
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def mock_feedback(
    found: AttemptToAssess, item: ItemToAssess
) -> tuple[feedback_rules.FeedbackSentence, ...]:
    """The mock provider's deterministic feedback (AD-17): the answer's first sentence quoted with
    the item's last criterion as not explained, and for an item about the Student's game one
    sentence on the fact it was frozen with (or the set's first moment)."""
    start, end = _first_sentence(_quoted(item.answer or ""))
    code = item.criteria[-1][0] if item.criteria else None
    sentences = [
        feedback_rules.FeedbackSentence(
            template_id="quote-lacks",
            quote=feedback_rules.Span(start=start, end=end),
            criterion=code,
        )
    ]
    if item.fact_set is not None and found.narration_templates is not None:
        facts = citable(item.fact_set)
        fact_id = next((each for each in item.fact_ids if each in facts), None)
        if fact_id is None and item.fact_set.seat.moments:
            fact_id = min(item.fact_set.seat.moments, key=lambda moment: moment.week).id
        if fact_id is not None:
            sentences.append(
                feedback_rules.FeedbackSentence(
                    template_id="narration-supply-line", fact_ids=(fact_id,)
                )
            )
    return tuple(sentences)


def _inputs(found: AttemptToAssess, item: ItemToAssess, *, feedback: bool) -> gateway.Inputs:
    """The call's inputs: Story 12.2's for a score-only prompt; with `feedback` (prompt v2 on)
    also the templates a feedback sentence may use, the facts of the item's stored facts set it
    may cite, and the limits."""
    answer = item.answer or ""
    values: dict[str, gateway.Scalar] = {
        "scale": "\n".join(f"{step}: {_quoted(label)}" for step, label in found.scale),
        "question": _quoted(item.question),
        "guide": _quoted(f"{item.guide_title}\n{item.guide_text}"),
        "criteria": "\n".join(
            f"{code}, {weight}: {_quoted(text)}" for code, weight, text in item.criteria
        ),
        "facts": _quoted(item.facts),
        "answer": _quoted(answer),
    }
    mock_answer: BaseModel = AssessmentOutput(score=mock_score(answer))
    if feedback:
        templates = found.narration_templates if item.fact_set is not None else None
        values |= {
            # The fact the question is about stays as in v1; these are what a sentence may cite.
            "citable": fact_lines(item.fact_set) if item.fact_set and templates else "",
            "templates": feedback_rules.template_lines(templates),
            "max_sentences": feedback_rules.MAX_FEEDBACK_SENTENCES,
            "max_quote": feedback_rules.MAX_QUOTE,
        }
        mock_answer = feedback_rules.AssessmentFeedbackOutput(
            score=mock_score(answer), feedback=mock_feedback(found, item)
        )
    return gateway.Inputs(
        values=values, caller={"attempt_id": found.attempt_id}, mock_answer=mock_answer
    )


@dataclass(frozen=True)
class _Scored:
    """One item's score and the call it came from, and with a feedback prompt the stored
    feedback or the `dropped` note."""

    score: int
    llm_call_id: uuid.UUID
    feedback: dict[str, Any] | None = None
    note: Literal["dropped"] | None = None


async def _run(
    found: AttemptToAssess, item: ItemToAssess, scope: ai_budget.BudgetScope, *, feedback: bool
) -> gateway.Result[Any] | None:
    """One call (never retried here): its result, or None for a typed failure or any error."""
    schema: type[BaseModel] = (
        feedback_rules.AssessmentFeedbackOutput if feedback else AssessmentOutput
    )
    try:
        result = await gateway.run(
            PURPOSE, scope, _inputs(found, item, feedback=feedback), schema, None
        )
    except gateway.GatewayError as exc:
        log.warning("assessment_item_not_prepared", attempt_id=str(found.attempt_id), code=exc.code)
        return None
    except Exception as exc:  # the type only; the run goes on and is counted (never retried here)
        log.error(
            "assessment_item_call_failed",
            attempt_id=str(found.attempt_id),
            exc_type=type(exc).__name__,
        )
        return None
    if isinstance(result, gateway.Failure):
        log.info("assessment_item_failed", attempt_id=str(found.attempt_id), kind=result.kind)
        return None
    return result


def _feedback(
    found: AttemptToAssess, item: ItemToAssess, result: gateway.Result[Any]
) -> dict[str, Any] | None:
    """The feedback of a call's output as stored (`{text, ai_generated, llm_call_id, parts}`)
    when the validator accepts it, else None (its reason logged, never its text)."""
    output: feedback_rules.AssessmentFeedbackOutput = result.output
    answer = item.answer or ""
    offsets = result.offset_maps.get("answer")
    templates = found.narration_templates if item.fact_set is not None else None
    if offsets is None:  # pragma: no cover - the answer is always a string value
        return None
    verdict = feedback_rules.validate_feedback(
        output,
        answer,
        offsets,
        [code for code, _, _ in item.criteria],
        item.fact_set,
        templates,
    )
    if not verdict.accepted:
        log.info(
            "assessment_feedback_rejected",
            attempt_id=str(found.attempt_id),
            reason=verdict.reason,
        )
        return None
    text, parts = feedback_rules.render_feedback(
        output,
        answer,
        offsets,
        {code: criterion for code, _, criterion in item.criteria},
        item.fact_set,
        templates,
    )
    return {
        "text": text,
        "ai_generated": True,
        "llm_call_id": str(result.llm_call_ids[-1]),
        "parts": parts,
    }


async def _score_item(
    found: AttemptToAssess, item: ItemToAssess, scope: ai_budget.BudgetScope, *, feedback: bool
) -> _Scored | None:
    """One call for one item: its score and call id, or None (the score's call is never retried
    here). With `feedback`, a rejected feedback is asked for once more with a new call; when that
    is rejected too or fails, the feedback is left out (`dropped`). The first call's score is
    kept either way (Story 12.3)."""
    result = await _run(found, item, scope, feedback=feedback)
    if result is None:
        return None
    score, call_id = result.output.score, result.llm_call_ids[-1]
    if not feedback:
        return _Scored(score, call_id)
    given = _feedback(found, item, result)
    if given is None:
        again = await _run(found, item, scope, feedback=True)
        given = None if again is None else _feedback(found, item, again)
    if given is None:
        log.info("assessment_feedback_dropped", attempt_id=str(found.attempt_id))
        return _Scored(score, call_id, note="dropped")
    return _Scored(score, call_id, feedback=given)


async def _store_score(
    assessment_id: uuid.UUID,
    found: AttemptToAssess,
    model_config_id: uuid.UUID | None,
    item_id: str,
    score: int,
    llm_call_id: uuid.UUID | None,
    now: datetime,
    *,
    feedback: dict[str, Any] | None = None,
    note: str | None = None,
) -> None:
    async with get_sessionmaker().begin() as s:
        await s.execute(
            insert(ai_item_scores)
            .values(
                assessment_id=assessment_id,
                item_id=item_id,
                score=score,
                source="ai" if llm_call_id is not None else "blank",
                llm_call_id=llm_call_id,
                scoring_guide_id=found.scoring_guide_id,
                question_set_version=found.question_set_version,
                model_config_id=model_config_id,
                created_at=now,
                feedback=feedback,
                feedback_note=note,
            )
            .on_conflict_do_nothing(constraint="pk_ai_item_scores")
        )


async def _started(
    found: AttemptToAssess, pin: PinnedConfig | None, now: datetime
) -> tuple[uuid.UUID, Status, set[str]]:
    """The attempt's assessment row, made now when it has none (a row from before migration 0204;
    since Story 12.4 `schedule` makes it at the close), with its state and the items scored so
    far. The Scoring guide version the reader found is stored on a row made without it."""
    async with get_sessionmaker().begin() as s:
        await s.execute(
            insert(ai_assessments)
            .values(
                id=uuid.uuid7(),
                attempt_id=found.attempt_id,
                class_session_id=found.class_session_id,
                user_id=found.user_id,
                status="incomplete",
                runs=0,
                scoring_guide_id=found.scoring_guide_id,
                question_set_version=found.question_set_version,
                model_config_id=None if pin is None else pin.model_config_id,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing(constraint="uq_ai_assessments_attempt")
        )
        await s.execute(
            update(ai_assessments)
            .where(
                ai_assessments.c.attempt_id == found.attempt_id,
                ai_assessments.c.scoring_guide_id.is_(None),
                ai_assessments.c.runs == 0,
            )
            .values(scoring_guide_id=found.scoring_guide_id)
        )
        row = (
            await s.execute(
                select(ai_assessments.c.id, ai_assessments.c.status).where(
                    ai_assessments.c.attempt_id == found.attempt_id
                )
            )
        ).one()
        scored = await s.scalars(
            select(ai_item_scores.c.item_id).where(ai_item_scores.c.assessment_id == row.id)
        )
        return row.id, row.status, set(scored)


def backoff(runs: int) -> timedelta:
    """The wait before the next run after `runs` finished runs: the configured minutes, doubled
    per run before."""
    return timedelta(minutes=get_settings().assessment_retry_minutes * 2 ** max(0, runs - 1))


async def _finish(
    assessment_id: uuid.UUID,
    found: AttemptToAssess,
    no_config: bool,
    now: datetime,
) -> Status:
    """Count the run and settle the state under the row lock: `ready` when every item has a
    score, `failed` with no pinned config or after the last allowed run, else `incomplete` with
    one later run deferred (none while the Class session's assessment is stopped: its resume
    defers it).

    Story 12.4, in the same transaction: `ready` records the Student's `assessment_ready` step and
    enqueues their `assessment_ready` notice; `failed` enqueues one `assessment_failed` notice
    per active Admin per Class session. Both are keyed, so nothing is told twice."""
    wanted = {item.item_id for item in found.items}
    async with get_sessionmaker().begin() as s:
        row = (
            await s.execute(
                select(ai_assessments.c.status, ai_assessments.c.runs)
                .where(ai_assessments.c.id == assessment_id)
                .with_for_update()
            )
        ).one()
        if row.status != "incomplete":  # another run settled it meanwhile
            return row.status
        scored = set(
            await s.scalars(
                select(ai_item_scores.c.item_id).where(
                    ai_item_scores.c.assessment_id == assessment_id
                )
            )
        )
        runs = row.runs + 1
        values: dict[str, object] = {"runs": runs, "updated_at": now}
        status: Status
        if no_config:
            status = "failed"
            values |= {"status": status, "reason": "no_model_config"}
        elif wanted <= scored:
            status = "ready"
            values |= {"status": status, "ready_at": now}
        elif runs >= get_settings().assessment_max_runs:
            status = "failed"
            values |= {"status": status, "reason": "runs_exhausted"}
        else:
            status = "incomplete"
            if (await switch_of(s, found.class_session_id)).stopped:
                log.info("assessment_rerun_not_deferred", attempt_id=str(found.attempt_id))
            elif not await _defer(s, found.attempt_id, schedule_at=now + backoff(runs)):
                # A run of the attempt waits already: that one goes on.
                log.warning("assessment_rerun_not_deferred", attempt_id=str(found.attempt_id))
        await s.execute(
            update(ai_assessments).where(ai_assessments.c.id == assessment_id).values(**values)
        )
        await events.emit(s, "user", str(found.user_id))
        if status == "ready":
            await _tell_ready(s, found, now)
        elif status == "failed":
            await _tell_failed(s, found.class_session_id)
    log.info(
        "assessment_run_finished",
        attempt_id=str(found.attempt_id),
        status=status,
        runs=runs,
        missing=len(wanted - scored),
    )
    return status


READY_NOTICE = "assessment_ready"
"""The Student's notice that their assessment is ready (Story 12.4, a digest kind)."""

FAILED_NOTICE = "assessment_failed"
"""Each Admin's notice that an assessment of a Class session failed (Story 12.4, a digest
kind), once per Class session."""


async def _tell_ready(s: AsyncSession, found: AttemptToAssess, now: datetime) -> None:
    """The `ready` transition's two records, in its transaction (FR-55, AD-9, AD-16)."""
    await progress.record_step(
        found.user_id,
        found.class_session_id,
        progress.Step.ASSESSMENT_READY,
        now,
        within=s,
    )
    await notify.enqueue(
        s,
        found.user_id,
        READY_NOTICE,
        f"{READY_NOTICE}:{found.attempt_id}",
        ref=found.class_session_id,
    )


async def _tell_failed(s: AsyncSession, class_session_id: uuid.UUID) -> None:
    """One `assessment_failed` notice per active Admin, keyed by the Class session and the
    Admin: a second failed assessment of the session tells no one again."""
    told = 0
    for admin_id in await _admins(s):
        told += await notify.enqueue(
            s,
            admin_id,
            FAILED_NOTICE,
            f"{FAILED_NOTICE}:{class_session_id}:{admin_id}",
            ref=class_session_id,
        )
    if told:
        log.warning(
            "assessment_failed_notified", class_session_id=str(class_session_id), admins=told
        )


async def _stopped(class_session_id: uuid.UUID) -> bool:
    async with get_sessionmaker()() as s:
        return (await switch_of(s, class_session_id)).stopped


async def assess(attempt_id: uuid.UUID) -> str:
    """The `assessment.assess` job's work (idempotent on `attempt_id`): what this run did, as a
    code (`not_closed`, `not_due`, `stopped`, or the state it left: `ready`, `incomplete`,
    `failed`). A `ready` or `failed` assessment is left as it is; every other run makes at most
    one call per item still without a score. Never raises for a provider or config problem.

    Story 12.4: while the Class session's assessment is stopped, a run makes no call: it ends
    before the first one, or before the next one when the stop comes during the run, without
    counting the run or deferring another (`resume_for_session` does)."""
    found = await _reader()(attempt_id)
    if found is None or not found.closed:
        log.info("assessment_skipped", attempt_id=str(attempt_id), reason="not_closed")
        return "not_closed"
    async with get_sessionmaker()() as s:
        switch = await switch_of(s, found.class_session_id)
        if not (switch.pinned and switch.enabled):
            log.info("assessment_skipped", attempt_id=str(attempt_id), reason="not_due")
            return "not_due"
        if switch.stopped:
            log.info("assessment_skipped", attempt_id=str(attempt_id), reason="stopped")
            return "stopped"
        pin = await pinned_config(s, found.class_session_id)
    now = auth.utcnow()
    assessment_id, status, scored = await _started(found, pin, now)
    if status != "incomplete":
        return status
    scope = (
        None
        if pin is None
        else ai_budget.BudgetScope.class_session(
            found.class_session_id,
            effort_level=pin.effort_level,
            model_config_id=pin.model_config_id,
        )
    )
    config_id = None if pin is None else pin.model_config_id
    feedback = await _gives_feedback(config_id)
    for item in found.items:
        if item.item_id in scored:
            continue
        if await _stopped(found.class_session_id):
            log.info("assessment_run_stopped", attempt_id=str(attempt_id))
            return "stopped"
        try:
            await _assess_item(assessment_id, found, item, scope, config_id, feedback=feedback)
        except Exception as exc:  # the type only: the item stays without a score, the run counts
            log.error(
                "assessment_item_not_stored",
                attempt_id=str(attempt_id),
                exc_type=type(exc).__name__,
            )
    return await _finish(assessment_id, found, scope is None, auth.utcnow())


async def _assess_item(
    assessment_id: uuid.UUID,
    found: AttemptToAssess,
    item: ItemToAssess,
    scope: ai_budget.BudgetScope | None,
    config_id: uuid.UUID | None,
    *,
    feedback: bool,
) -> None:
    """Score one item still without a score: step 0 by code for an empty answer, else one call
    (two when its feedback is rejected once), and only with a pinned config and the item's
    Scoring guide entry."""
    if item.answer is None or not item.answer.strip():
        # Nothing to read: step 0 of the scale, by code, with no call.
        await _store_score(assessment_id, found, config_id, item.item_id, 0, None, auth.utcnow())
        return
    if scope is None:
        return
    if not item.guide_text:  # no Scoring guide entry to score against: no call, no score
        log.warning("assessment_item_without_guide", attempt_id=str(found.attempt_id))
        return
    made = await _score_item(found, item, scope, feedback=feedback)
    if made is not None:
        await _store_score(
            assessment_id,
            found,
            config_id,
            item.item_id,
            made.score,
            made.llm_call_id,
            auth.utcnow(),
            feedback=made.feedback,
            note=made.note,
        )


async def _gives_feedback(config_id: uuid.UUID | None) -> bool:
    """Whether the pinned config names prompt `assessment/v2` or later, whose output holds
    written feedback (Story 12.3); a config naming v1 keeps the score-only output."""
    if config_id is None:
        return False
    found = await ai_config.get(config_id)
    version = None if found is None else found.spec.prompts.get(PURPOSE)
    return version is not None and version >= FEEDBACK_VERSION


# Story 12.4: the stop mark, and the sweep's overdue action.

STOPPED = "assessment.stopped"
"""The audit action of `stop_for_session`."""

RESUMED = "assessment.resumed"
"""The audit action of `resume_for_session`."""


async def _users_of(s: AsyncSession, class_session_id: uuid.UUID) -> list[uuid.UUID]:
    found = await s.scalars(
        select(ai_assessments.c.user_id)
        .where(ai_assessments.c.class_session_id == class_session_id)
        .distinct()
    )
    return list(found)


async def _announce(s: AsyncSession, class_session_id: uuid.UUID) -> None:
    """A stop or a resume changes what the Students of the Class session read: their pages and
    the session's read it again (AD-8)."""
    await events.emit(s, "session", str(class_session_id))
    for user_id in await _users_of(s, class_session_id):
        await events.emit(s, "user", str(user_id))


async def stop_for_session(
    class_session_id: uuid.UUID,
    actor: uuid.UUID | None,
    *,
    now: datetime,
    within: AsyncSession | None = None,
) -> bool:
    """Stop the AI assessment of a Class session (the cost limit is reached, or the Admin leaves
    it out; FR-61, FR-69, AD-9): set the stop mark with its time and actor, audited, in `within`
    or a transaction of its own. From then on `schedule` defers no job, a running job ends before
    its next call, the sweep's overdue action skips the session, and an assessment that is not
    ready reads as switched off; a ready one stays readable. True when this call stopped it; a
    session already stopped is left as it is, with no audit row."""
    if within is None:
        async with get_sessionmaker().begin() as s:
            return await stop_for_session(class_session_id, actor, now=now, within=s)
    s = within
    statement = insert(assessment_switches).values(
        class_session_id=class_session_id,
        enabled=True,
        updated_at=now,
        stopped_at=now,
        stopped_by=actor,
    )
    stopped = await s.execute(
        statement.on_conflict_do_update(
            index_elements=[assessment_switches.c.class_session_id],
            set_={"stopped_at": now, "stopped_by": actor},
            where=assessment_switches.c.stopped_at.is_(None),
        ).returning(assessment_switches.c.class_session_id)
    )
    if stopped.first() is None:
        return False
    await audit.record(s, actor, STOPPED, {"class_session_id": class_session_id}, {}, now)
    await _announce(s, class_session_id)
    log.info("assessment_stopped", class_session_id=str(class_session_id))
    return True


async def resume_for_session(
    class_session_id: uuid.UUID,
    actor: uuid.UUID | None,
    *,
    now: datetime,
    within: AsyncSession | None = None,
) -> int:
    """Restart the AI assessment of a Class session, after the cost limit was raised (FR-61,
    FR-69, AD-9), audited, in `within` or a transaction of its own: clear the stop mark, reset
    every `incomplete` and `failed` assessment of the session to `incomplete` with no run, and,
    while the pinned switch is on, defer each one's job again. Every closed attempt of such a
    session has its row from its close (`schedule`), so this reaches the attempts closed while it
    was stopped too. Returns how many assessments it deferred (a run already waiting counts)."""
    if within is None:
        async with get_sessionmaker().begin() as s:
            return await resume_for_session(class_session_id, actor, now=now, within=s)
    s = within
    await s.execute(
        select(assessment_switches.c.class_session_id)
        .where(assessment_switches.c.class_session_id == class_session_id)
        .with_for_update()
    )
    await s.execute(
        update(assessment_switches)
        .where(
            assessment_switches.c.class_session_id == class_session_id,
            assessment_switches.c.stopped_at.is_not(None),
        )
        .values(stopped_at=None, stopped_by=None)
    )
    reset = list(
        await s.scalars(
            update(ai_assessments)
            .where(
                ai_assessments.c.class_session_id == class_session_id,
                ai_assessments.c.status.in_(("incomplete", "failed")),
            )
            .values(status="incomplete", runs=0, reason=None, updated_at=now)
            .returning(ai_assessments.c.attempt_id)
        )
    )
    deferred = 0
    if reset and await assessment_due(class_session_id, session=s):
        for attempt_id in sorted(reset):
            await _defer(s, attempt_id)
            deferred += 1
    await audit.record(
        s,
        actor,
        RESUMED,
        {"class_session_id": class_session_id},
        {"reset": len(reset), "deferred": deferred},
        now,
    )
    await _announce(s, class_session_id)
    log.info(
        "assessment_resumed",
        class_session_id=str(class_session_id),
        reset=len(reset),
        deferred=deferred,
    )
    return deferred


OVERDUE_PER_SWEEP = 200
"""The most overdue assessments one sweep handles; the next minute's sweep takes the rest."""


async def due_overdue(now: datetime) -> list[uuid.UUID]:
    """The sweep's `assessment.overdue` finder (FR-54, AD-9, NFR-8): the attempts whose
    assessment is still `incomplete` `assessment_overdue_hours` after its `due_at`, in a Class
    session whose pinned switch is on and that is not stopped, either not yet logged as overdue
    or untouched for `assessment_retry_minutes` (so a job that keeps failing is deferred again at
    that pace, never each minute, and one with no runs left is settled `failed`), the oldest
    first."""
    settings = get_settings()
    late = now - timedelta(hours=settings.assessment_overdue_hours)
    quiet = now - timedelta(minutes=settings.assessment_retry_minutes)
    async with get_sessionmaker()() as s:
        found = await s.scalars(
            select(ai_assessments.c.attempt_id)
            .join(
                assessment_switches,
                assessment_switches.c.class_session_id == ai_assessments.c.class_session_id,
            )
            .where(
                ai_assessments.c.status == "incomplete",
                ai_assessments.c.due_at <= late,
                assessment_switches.c.pinned_at.is_not(None),
                assessment_switches.c.enabled,
                assessment_switches.c.stopped_at.is_(None),
                (ai_assessments.c.overdue_at.is_(None)) | (ai_assessments.c.updated_at <= quiet),
            )
            .order_by(ai_assessments.c.due_at, ai_assessments.c.id)
            .limit(OVERDUE_PER_SWEEP)
        )
        return list(found)


async def overdue_due(attempt_id: object, now: datetime) -> bool:
    """The sweep's `assessment.overdue` action, one assessment per transaction, ids only: log
    `assessment_overdue` once (`overdue_at`), and defer its job again when it has no live job
    (`todo` or `doing`), runs left and no run or re-defer for `assessment_retry_minutes`. A
    re-defer counts as a run, so a job that keeps failing before it settles is deferred at most
    `assessment_max_runs` times. With no runs left and no live job `assessment_retry_minutes`
    after the last run or re-defer, the lost runs settle it: `failed` (`runs_exhausted`), with the
    Admins' `assessment_failed` notice, as `_finish` would have. Every look stamps `updated_at`,
    so the finder returns the row again only after `assessment_retry_minutes`. True when a job
    was deferred."""
    assert isinstance(attempt_id, uuid.UUID)
    settings = get_settings()
    async with get_sessionmaker().begin() as s:
        row = (
            (
                await s.execute(
                    select(ai_assessments)
                    .where(ai_assessments.c.attempt_id == attempt_id)
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None or row["status"] != "incomplete":
            return False
        if (await switch_of(s, row["class_session_id"])).stopped:
            return False
        values: dict[str, object] = {}
        if row["overdue_at"] is None:
            log.warning(
                "assessment_overdue",
                attempt_id=str(attempt_id),
                assessment_id=str(row["id"]),
                class_session_id=str(row["class_session_id"]),
                runs=row["runs"],
            )
            values["overdue_at"] = now
        quiet = now - timedelta(minutes=settings.assessment_retry_minutes)
        deferred = exhausted = False
        if row["updated_at"] <= quiet:
            values["updated_at"] = now
            if not await jobs.live_locks(s, [assessment_key(attempt_id)]):
                if row["runs"] < settings.assessment_max_runs:
                    deferred = await _defer(s, attempt_id)
                    values["runs"] = row["runs"] + 1
                    log.info("assessment_redeferred", attempt_id=str(attempt_id), runs=row["runs"])
                else:
                    exhausted = True
                    values |= {"status": "failed", "reason": "runs_exhausted"}
        if values:
            await s.execute(
                update(ai_assessments).where(ai_assessments.c.id == row["id"]).values(**values)
            )
        if exhausted:
            log.warning("assessment_runs_exhausted", attempt_id=str(attempt_id))
            await events.emit(s, "user", str(row["user_id"]))
            await _tell_failed(s, row["class_session_id"])
    return deferred


# Story 12.5: the Student's flags, and the staff list.


async def set_flag(attempt_id: uuid.UUID, item_id: str, flagged: bool, *, now: datetime) -> bool:
    """Store (`flagged`) or remove the Student's «Marker som feil» on the written feedback of one
    item of the attempt's assessment (FR-55), idempotently, in a transaction of its own; it emits
    `user:<student>` and `session:<id>` so the Student's other tabs and the Class's staff read it
    again (AD-8). False when the attempt has no assessment or the item no stored score (nothing
    is stored). A flag is stored only while the Student's view shows that feedback, judged again in
    this transaction with the switch row share-locked (a stop waits for it): the item has written
    feedback, the switch is on, and the assessment has a finished run and is ready, or incomplete
    and not stopped. Removing a flag needs only the stored score."""
    async with get_sessionmaker().begin() as s:
        row = (
            await s.execute(
                select(
                    ai_assessments.c.id,
                    ai_assessments.c.user_id,
                    ai_assessments.c.class_session_id,
                    ai_assessments.c.status,
                    ai_assessments.c.runs,
                    ai_item_scores.c.feedback,
                )
                .join(ai_item_scores, ai_item_scores.c.assessment_id == ai_assessments.c.id)
                .where(
                    ai_assessments.c.attempt_id == attempt_id, ai_item_scores.c.item_id == item_id
                )
            )
        ).first()
        if row is None:
            return False
        if flagged:
            switch = await switch_of(s, row.class_session_id, share=True)
            shown = (
                row.feedback is not None
                and switch.enabled
                and row.runs > 0
                and (row.status == "ready" or (row.status == "incomplete" and not switch.stopped))
            )
            if not shown:
                return False
            changed = await s.execute(
                insert(ai_feedback_flags)
                .values(assessment_id=row.id, item_id=item_id, flagged_at=now)
                .on_conflict_do_nothing()
                .returning(ai_feedback_flags.c.item_id)
            )
        else:
            changed = await s.execute(
                delete(ai_feedback_flags)
                .where(
                    ai_feedback_flags.c.assessment_id == row.id,
                    ai_feedback_flags.c.item_id == item_id,
                )
                .returning(ai_feedback_flags.c.item_id)
            )
        if changed.first() is not None:
            await events.emit(s, "user", str(row.user_id))
            await events.emit(s, "session", str(row.class_session_id))
            log.info("assessment_flag_set", assessment_id=str(row.id), flagged=flagged)
    return True


@dataclass(frozen=True)
class AssessmentSummary:
    """One Student's assessment in a Class session as a list reads it (Story 12.5): the attempt
    it belongs to, its state, finished runs and how many pieces of feedback the Student flagged."""

    attempt_id: uuid.UUID
    status: Status
    runs: int
    flags: int


async def summaries_for_session(
    s: AsyncSession, class_session_id: uuid.UUID
) -> dict[uuid.UUID, AssessmentSummary]:
    """Every assessment of the Class session by the Student's user id, read in `s` (Story 12.5:
    the Klasseøkt's list; Epic 13 reads the same). A Student with no row has no assessment yet.
    The caller judges access and the switch (`switch_of`)."""
    counted = (
        select(ai_feedback_flags.c.assessment_id, func.count().label("flags"))
        .group_by(ai_feedback_flags.c.assessment_id)
        .subquery()
    )
    found = await s.execute(
        select(
            ai_assessments.c.user_id,
            ai_assessments.c.attempt_id,
            ai_assessments.c.status,
            ai_assessments.c.runs,
            func.coalesce(counted.c.flags, 0).label("flags"),
        )
        .outerjoin(counted, counted.c.assessment_id == ai_assessments.c.id)
        .where(ai_assessments.c.class_session_id == class_session_id)
    )
    return {
        row.user_id: AssessmentSummary(
            attempt_id=row.attempt_id, status=row.status, runs=row.runs, flags=int(row.flags)
        )
        for row in found
    }


# Blind human scoring of a Control test (Story 12.9, FR-82, AD-27). Every function runs in the
# caller's transaction; the caller judges access and audits.


async def name_scorer(
    s: AsyncSession,
    class_session_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    named_by: uuid.UUID,
    now: datetime,
) -> bool:
    """Name `user_id` a scorer of the Control test; False when they are named already (nothing
    written)."""
    found = await s.execute(
        insert(control_test_scorers)
        .values(class_session_id=class_session_id, user_id=user_id, named_by=named_by, named_at=now)
        .on_conflict_do_nothing(constraint="pk_control_test_scorers")
        .returning(control_test_scorers.c.user_id)
    )
    return found.first() is not None


async def remove_scorer(s: AsyncSession, class_session_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Take `user_id` off the Control test's scorers; their submitted scores stay. False when
    they were not named."""
    found = await s.execute(
        delete(control_test_scorers)
        .where(
            control_test_scorers.c.class_session_id == class_session_id,
            control_test_scorers.c.user_id == user_id,
        )
        .returning(control_test_scorers.c.user_id)
    )
    return found.first() is not None


async def scorers_of(
    s: AsyncSession, class_session_id: uuid.UUID
) -> list[tuple[uuid.UUID, datetime]]:
    """The named scorers of the Control test with when they were named, in that order."""
    found = await s.execute(
        select(control_test_scorers.c.user_id, control_test_scorers.c.named_at)
        .where(control_test_scorers.c.class_session_id == class_session_id)
        .order_by(control_test_scorers.c.named_at, control_test_scorers.c.user_id)
    )
    return [(row.user_id, row.named_at) for row in found]


async def insert_human_score(
    s: AsyncSession, answer_id: uuid.UUID, scorer_id: uuid.UUID, score: int, *, now: datetime
) -> bool:
    """Store the scorer's score of one answer, once; False (nothing written) when they scored it
    already. There is no way to change it afterwards."""
    if not 0 <= score <= SCALE_TOP:
        raise ValueError("a human score is a step on the five-step scale")
    found = await s.execute(
        insert(human_scores)
        .values(answer_id=answer_id, scorer_id=scorer_id, score=score, submitted_at=now)
        .on_conflict_do_nothing(constraint="pk_human_scores")
        .returning(human_scores.c.answer_id)
    )
    return found.first() is not None


@dataclass(frozen=True)
class HumanScore:
    score: int
    submitted_at: datetime


async def human_scores_by(
    s: AsyncSession, scorer_id: uuid.UUID, answer_ids: list[uuid.UUID]
) -> dict[uuid.UUID, HumanScore]:
    """The scorer's own scores of these answers, by answer id."""
    if not answer_ids:
        return {}
    found = await s.execute(
        select(human_scores.c.answer_id, human_scores.c.score, human_scores.c.submitted_at).where(
            human_scores.c.scorer_id == scorer_id, human_scores.c.answer_id.in_(answer_ids)
        )
    )
    return {row.answer_id: HumanScore(row.score, row.submitted_at) for row in found}


async def score_counts(
    s: AsyncSession, scorer_ids: list[uuid.UUID], answer_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """How many of these answers each scorer has scored."""
    if not scorer_ids or not answer_ids:
        return {}
    found = await s.execute(
        select(human_scores.c.scorer_id, func.count())
        .where(human_scores.c.scorer_id.in_(scorer_ids), human_scores.c.answer_id.in_(answer_ids))
        .group_by(human_scores.c.scorer_id)
    )
    return {scorer: int(count) for scorer, count in found.all()}


class ScorerNotNamed(Exception):
    """The scorer was taken off the Control test before their score was stored (403)."""


@dataclass(frozen=True)
class RecordedScore:
    """What `record_human_score` (or `settle_after_removal`) did: whether the score was stored
    (False: scored already), whether the Control test is now complete, and whether that wrote the
    pair's check (False when another Control test checked the pair first)."""

    stored: bool
    complete: bool = False
    checked: bool = False


async def hold_scorers(s: AsyncSession, class_session_id: uuid.UUID) -> set[uuid.UUID]:
    """The Control test's named scorers, their rows held until the transaction ends (Story
    12.10): a score submit and a removal take this first, so two last steps never miss each
    other. The caller reads the listed answers after it."""
    return set(
        await s.scalars(
            select(control_test_scorers.c.user_id)
            .where(control_test_scorers.c.class_session_id == class_session_id)
            .with_for_update()
        )
    )


async def _settle(
    s: AsyncSession,
    class_session_id: uuid.UUID,
    named: set[uuid.UUID],
    *,
    listed: list[uuid.UUID],
    settled: bool,
    scoring_guide_id: uuid.UUID,
    model_config_id: uuid.UUID | None,
    now: datetime,
) -> tuple[bool, bool]:
    """(complete, checked): when the Control test has a named scorer, a listed answer, no open
    attempt (`settled`), a pinned model config and every named scorer's score of every listed
    answer, the pinned guide version is marked checked for the config."""
    if not named or not listed or not settled or model_config_id is None:
        return False, False
    counts = await score_counts(s, list(named), listed)
    unique = len(set(listed))
    if any(counts.get(each, 0) < unique for each in named):
        return False, False
    marked = await content.mark_checked(
        s, scoring_guide_id, model_config_id, control_test_id=class_session_id, now=now
    )
    return True, marked


async def record_human_score(
    s: AsyncSession,
    class_session_id: uuid.UUID,
    answer_id: uuid.UUID,
    scorer_id: uuid.UUID,
    score: int,
    *,
    named: set[uuid.UUID],
    listed: list[uuid.UUID],
    settled: bool,
    scoring_guide_id: uuid.UUID,
    model_config_id: uuid.UUID | None,
    now: datetime,
) -> RecordedScore:
    """Store the scorer's score of one answer of the Control test, once, in the caller's
    transaction (Story 12.9, Story 12.10, FR-81, AD-27). `named` comes from `hold_scorers`, taken
    before the caller read `listed` (every answer to score) and `settled` (no attempt open).
    Raises `ScorerNotNamed` when `scorer_id` is no longer named (nothing written). When this
    score completes the Control test, the pinned Scoring guide version is marked checked for the
    model config (`content.service.mark_checked`)."""
    if scorer_id not in named:
        raise ScorerNotNamed
    if not await insert_human_score(s, answer_id, scorer_id, score, now=now):
        return RecordedScore(stored=False)
    complete, checked = await _settle(
        s,
        class_session_id,
        named,
        listed=listed,
        settled=settled,
        scoring_guide_id=scoring_guide_id,
        model_config_id=model_config_id,
        now=now,
    )
    return RecordedScore(stored=True, complete=complete, checked=checked)


async def settle_after_removal(
    s: AsyncSession,
    class_session_id: uuid.UUID,
    *,
    listed: list[uuid.UUID],
    settled: bool,
    scoring_guide_id: uuid.UUID,
    model_config_id: uuid.UUID | None,
    now: datetime,
) -> RecordedScore:
    """After a scorer was taken off, in the same transaction: when the scorers left have scored
    every listed answer, the Control test is complete and its guide checked, as after a last
    score (Story 12.10). Removing the last scorer completes nothing."""
    named = await hold_scorers(s, class_session_id)
    complete, checked = await _settle(
        s,
        class_session_id,
        named,
        listed=listed,
        settled=settled,
        scoring_guide_id=scoring_guide_id,
        model_config_id=model_config_id,
        now=now,
    )
    return RecordedScore(stored=False, complete=complete, checked=checked)


async def scores_of(
    s: AsyncSession, answer_ids: list[uuid.UUID]
) -> dict[uuid.UUID, dict[uuid.UUID, int]]:
    """Every human score of these answers: answer id → scorer id → step (Story 12.10)."""
    if not answer_ids:
        return {}
    found: dict[uuid.UUID, dict[uuid.UUID, int]] = {}
    rows = await s.execute(
        select(human_scores.c.answer_id, human_scores.c.scorer_id, human_scores.c.score).where(
            human_scores.c.answer_id.in_(answer_ids)
        )
    )
    for row in rows:
        found.setdefault(row.answer_id, {})[row.scorer_id] = row.score
    return found


async def erase_feedback_of_user(s: AsyncSession, user_id: uuid.UUID) -> None:
    """Story 15.2 (FR-76, AD-14) after Epic 12, in the erasure's transaction: the written feedback
    of the User's AI assessments is emptied (it may quote their answer), and so are the bodies of
    the AI calls that assessed them (they hold the answer). The scores, the flags and the cost rows
    stay, so every id still holds. Idempotent."""
    attempts = list(
        (
            await s.execute(
                select(ai_assessments.c.attempt_id).where(ai_assessments.c.user_id == user_id)
            )
        ).scalars()
    )
    await s.execute(
        update(ai_item_scores)
        .where(
            ai_item_scores.c.assessment_id.in_(
                select(ai_assessments.c.id).where(ai_assessments.c.user_id == user_id)
            ),
            ai_item_scores.c.feedback.is_not(None),
        )
        .values(feedback=None)
    )
    await ai_calls.clear_bodies_by_ref(s, "attempt_id", attempts)


# «Mine data» (Story 15.1, FR-75): the Student's own rows of this module, by their own id.
from app.modules.assessment.own_data import own_records  # noqa: E402
