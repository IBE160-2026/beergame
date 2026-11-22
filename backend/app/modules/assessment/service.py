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

No answer text, guide text or score is logged: ids, counts and codes only.

This module imports no feature module: `sessions` and `tests` call it, never the other way round."""

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Annotated, Any, Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import budget as ai_budget
from app.ai import config as ai_config
from app.ai import gateway
from app.analysis import feedback as feedback_rules
from app.analysis.facts import FactSet
from app.analysis.narration import NarrationTemplates, citable, fact_lines
from app.analysis.total import SCALE_TOP
from app.modules.assessment.models import ai_assessments, ai_item_scores, assessment_switches
from app.platform import auth, events, jobs
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

__all__ = [
    "ASSESS_TASK",
    "DEFAULT_SWITCH",
    "PURPOSE",
    "FEEDBACK_VERSION",
    "AssessmentOutput",
    "AssessmentRecord",
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
    "mock_feedback",
    "mock_score",
    "pin_switch",
    "pinned_config",
    "register_attempt_reader",
    "schedule",
    "set_switch",
    "switch_of",
]

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class Switch:
    """The «KI-vurdering» switch of a Class session: on or off, and when the Test-deadline lock
    pinned it (None while it can still change)."""

    enabled: bool
    pinned_at: datetime | None

    @property
    def pinned(self) -> bool:
        return self.pinned_at is not None


DEFAULT_SWITCH = Switch(enabled=True, pinned_at=None)
"""A Class session with no row: on, not pinned (FR-61: on by default)."""


class SwitchPinned(Exception):
    """The switch was pinned at the Test deadline and no longer changes."""


async def switch_of(session: AsyncSession, class_session_id: uuid.UUID) -> Switch:
    """The Class session's switch as stored, or `DEFAULT_SWITCH` when nothing is stored."""
    row = (
        await session.execute(
            select(assessment_switches.c.enabled, assessment_switches.c.pinned_at).where(
                assessment_switches.c.class_session_id == class_session_id
            )
        )
    ).first()
    return DEFAULT_SWITCH if row is None else Switch(enabled=row.enabled, pinned_at=row.pinned_at)


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
    statement = insert(assessment_switches).values(
        class_session_id=class_session_id, enabled=True, **values
    )
    pinned = await session.execute(
        statement.on_conflict_do_update(
            index_elements=[assessment_switches.c.class_session_id],
            set_=values,
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


async def schedule(s: AsyncSession, attempt_id: uuid.UUID, class_session_id: uuid.UUID) -> bool:
    """`tests.commands.close_attempt`'s call, in its transaction, once per attempt: defer the
    attempt's assessment when the pinned switch is on (`assessment_due`); True when deferred.
    The one place a first assessment is enqueued (AD-9)."""
    if not await assessment_due(class_session_id, session=s):
        return False
    return await jobs.defer(
        s,
        ASSESS_TASK,
        queue=jobs.LLM_BATCH,
        queueing_lock=assessment_key(attempt_id),
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
    """The attempt's assessment row, made now when it has none, with its state and the items
    scored so far."""
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
    one later run deferred."""
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
            deferred = await jobs.defer(
                s,
                ASSESS_TASK,
                queue=jobs.LLM_BATCH,
                queueing_lock=assessment_key(found.attempt_id),
                schedule_at=now + backoff(runs),
                attempt_id=str(found.attempt_id),
            )
            if not deferred:  # a run of the attempt waits already: that one goes on
                log.warning("assessment_rerun_not_deferred", attempt_id=str(found.attempt_id))
        await s.execute(
            update(ai_assessments).where(ai_assessments.c.id == assessment_id).values(**values)
        )
        await events.emit(s, "user", str(found.user_id))
    log.info(
        "assessment_run_finished",
        attempt_id=str(found.attempt_id),
        status=status,
        runs=runs,
        missing=len(wanted - scored),
    )
    return status


async def assess(attempt_id: uuid.UUID) -> str:
    """The `assessment.assess` job's work (idempotent on `attempt_id`): what this run did, as a
    code (`not_closed`, `not_due`, or the state it left: `ready`, `incomplete`, `failed`). A
    `ready` or `failed` assessment is left as it is; every other run makes at most one call per
    item still without a score. Never raises for a provider or config problem."""
    found = await _reader()(attempt_id)
    if found is None or not found.closed:
        log.info("assessment_skipped", attempt_id=str(attempt_id), reason="not_closed")
        return "not_closed"
    async with get_sessionmaker()() as s:
        if not await assessment_due(found.class_session_id, session=s):
            log.info("assessment_skipped", attempt_id=str(attempt_id), reason="not_due")
            return "not_due"
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
