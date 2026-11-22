"""The Individual test as the AI assessment reads it, and the Student's «KI-vurdering» (Story 12.2,
FR-54, FR-55, FR-61, FR-80, AD-6, AD-9, AD-23).

`assessment` imports no other module, so `tests` hands it the attempt: `read_for_assessment`,
registered with `assessment.service` at import, gives a closed attempt's long-answer and Adapted
items with the question as the Student read it, their answer, the pinned Scoring guide entry and,
for an Adapted item, the lines of the fact it cites from its stored facts set (read by id, never
rebuilt, AD-7), plus the versions the attempt was frozen and is scored with.

`read` is the Student's view (`GET /api/me/class-sessions/{id}/test/assessment`): its state, and
once a run of the assessment has finished each item in the test's order with its Item weight, the
computed score `tests` stored at the hand-in (never recomputed) or the AI's step on the five-step
scale, and the weighted total from `analysis.total_score` only, never a partial one. Only the
Student of their own locked Class session reads it; every other caller gets None (403).

Story 12.3 (FR-54, FR-81, AD-7): the reader also hands over an Adapted item's stored facts set
and the Class session's pinned narration templates, which written feedback may cite; the view
adds each AI item's feedback, its quotes cut from the Student's original answer by the stored
spans, the note where feedback was left out, and `checked` from `content.service.is_checked`.

Story 12.4 (FR-61, FR-69): while the Class session's assessment is stopped, an assessment that is
not ready reads as switched off; a ready one stays readable.

Story 12.5 (FR-55, FR-5, AD-12): each AI item carries `flagged`; `set_flag` is the Student's
«Marker som feil» and «Angre» on a piece of feedback their view shows (`NotFlaggable` for any
other item). `staff_read` is the same view for the staff of the Class (`ai_assessments.read`:
owners and Assistant lecturers) under its own schema, and `staff_list` each Student of the Class
with the state of their assessment and their flag count. Every other caller gets None (403)."""

import uuid
from collections.abc import Mapping
from typing import Any

import structlog
from sqlalchemy import select

from app.analysis import adapted as adapted_rules
from app.analysis.facts import FactSet
from app.analysis.narration import NarrationTemplates
from app.analysis.total import SCALE_TOP, total_score
from app.modules.assessment import service as assessment
from app.modules.content import service as content
from app.modules.content.schemas import GuideQuestion, QuestionSet
from app.modules.games import service as games
from app.modules.sessions import service as sessions
from app.modules.tests import adapted, commands, guide
from app.modules.tests.adapted import ADAPTED
from app.modules.tests.models import test_answers, test_attempts
from app.modules.tests.schemas import (
    AiScoreOut,
    AssessedItemOut,
    AssessmentListOut,
    AssessmentRowOut,
    ComputedCriterionOut,
    ComputedScoreOut,
    FeedbackOut,
    FeedbackPartOut,
    MyAssessmentOut,
    StaffAssessmentOut,
    WordingOut,
)
from app.platform import auth, authz
from app.platform.db import get_sessionmaker

__all__ = [
    "AI_TYPES",
    "NotFlaggable",
    "read",
    "read_for_assessment",
    "set_flag",
    "staff_list",
    "staff_read",
]

log = structlog.get_logger(__name__)

AI_TYPES = frozenset({"long", ADAPTED})
"""The item types the AI assesses against the Scoring guide; every other type is computed."""


async def _fact_lines(frozen: Mapping[str, Any]) -> tuple[str, FactSet | None]:
    """The fact an Adapted item cites, as `id: name=value, …` from its stored facts set and its
    template (`""` when either cannot be read: the question text carries the same numbers), and
    the stored facts set itself, read by the item's `fact_set_id` and never rebuilt (Story 12.3:
    what its feedback may cite)."""
    stored = await games.fact_set_by_id(str(frozen.get("fact_set_id")))
    if stored is None:
        log.warning("assessment_facts_unavailable", item_id=frozen["id"])
        return "", None
    _, templates = await content.adapted_templates(frozen.get("template_version"))
    template = next((t for t in templates.templates if t.id == frozen["id"]), None)
    if template is None:
        return "", stored.facts
    names = await adapted.pattern_names(stored) if template.fact == "pattern" else {}
    picked = adapted_rules.picked(template, stored.facts, names)
    if picked is None:
        return "", stored.facts
    fact_id, values = picked
    line = f"{fact_id}: " + ", ".join(f"{name}={value}" for name, value in values.items())
    return line, stored.facts


async def _narration_templates(pins: Any) -> NarrationTemplates | None:
    """The narration templates the Class session pinned (the latest for a session locked before
    the pin existed), which a feedback sentence about the Student's game uses; None when they
    cannot be read (the feedback then cites no fact)."""
    try:
        _, templates = await content.narration_templates(
            content.pinned_version(pins, content.Kind.NARRATION_TEMPLATES)
        )
    except Exception as exc:  # the type only: the feedback goes on without facts
        log.warning("assessment_templates_unavailable", exc_type=type(exc).__name__)
        return None
    return templates


def _entry(question: GuideQuestion | None) -> dict[str, Any]:
    if question is None:
        return {"guide_title": "", "guide_text": "", "criteria": ()}
    return {
        "guide_title": question.title,
        "guide_text": question.guide,
        "criteria": tuple((c.code, c.weight, c.text) for c in question.criteria),
    }


async def read_for_assessment(attempt_id: uuid.UUID) -> assessment.AttemptToAssess | None:
    """The attempt as `assessment.assess` needs it; None when it is gone."""
    async with get_sessionmaker()() as s:
        attempt = (
            (await s.execute(select(test_attempts).where(test_attempts.c.id == attempt_id)))
            .mappings()
            .one_or_none()
        )
        if attempt is None:
            return None
        in_force = await guide.in_force(s, attempt["class_session_id"])
        saved = await s.execute(
            select(test_answers.c.item_id, test_answers.c.value).where(
                test_answers.c.attempt_id == attempt_id
            )
        )
        answers = {item_id: value for item_id, value in saved.all()}
        pins = await sessions.locked_pins(s, attempt["class_session_id"])
    question_set: QuestionSet = await content.get(
        content.Kind.QUESTION_SET, attempt["question_set_version"]
    )
    by_id = {item.id: item for item in (*question_set.items, *question_set.replacements)}
    entries = {question.id: question for question in in_force.record.guide.questions}
    items = []
    for frozen in attempt["items"]:
        if frozen["type"] not in AI_TYPES:
            continue
        value = answers.get(frozen["id"])
        answer = value if isinstance(value, str) else None
        fact_set: FactSet | None = None
        fact_ids: tuple[str, ...] = ()
        if frozen["type"] == ADAPTED:
            question = frozen["text"]["text"]
            entry = entries.get(frozen["id"])
            facts, fact_set = await _fact_lines(frozen)
            fact_ids = tuple(frozen.get("fact_ids") or ())
        else:
            found = by_id.get(frozen["id"])
            question = found.title if found is not None else ""
            entry = entries.get(found.scoring_rule) if found and found.scoring_rule else None
            facts = ""
        items.append(
            assessment.ItemToAssess(
                item_id=frozen["id"],
                question=question,
                answer=answer,
                facts=facts,
                fact_set=fact_set,
                fact_ids=fact_ids,
                **_entry(entry),
            )
        )
    templates = await _narration_templates(pins) if any(i.fact_set for i in items) else None
    return assessment.AttemptToAssess(
        attempt_id=attempt["id"],
        user_id=attempt["user_id"],
        class_session_id=attempt["class_session_id"],
        closed=attempt["closed_at"] is not None,
        question_set_version=attempt["question_set_version"],
        scoring_guide_id=in_force.record.id,
        scale=tuple((step.step, step.label) for step in in_force.record.guide.scale),
        items=tuple(items),
        narration_templates=templates,
    )


assessment.register_attempt_reader(read_for_assessment)


def _state(state: str) -> MyAssessmentOut:
    return MyAssessmentOut(state=state, items=[], unassessed=[], total=None, total_max=None)  # type: ignore[arg-type]


def _computed(score: Mapping[str, Any] | None) -> tuple[float, ComputedScoreOut]:
    """The stored computed score as the view reads it, and its credit (0 with no score stored:
    an item not answered)."""
    if not score or not score.get("answered"):
        return 0.0, ComputedScoreOut(result="not_answered", criteria=[])
    credit = float(score.get("credit") or 0.0)
    result = "right" if credit >= 1 else "wrong" if credit <= 0 else "partly"
    criteria = [
        ComputedCriterionOut(code=c["code"], met=bool(c["met"]), explanation=c["explanation"])
        for c in score.get("criteria") or []
    ]
    return credit, ComputedScoreOut(result=result, criteria=criteria)


def _feedback_of(
    stored: assessment.ItemFeedback | None, answer: Any
) -> dict[str, FeedbackOut | bool | None]:
    """An item's written feedback as the view shows it (Story 12.3): each quote cut from the
    Student's original answer by its stored span, so the LLM never retypes their words; or the
    `dropped` mark; nothing for an item without feedback."""
    if stored is None:
        return {}
    if stored.dropped or stored.text is None:
        return {"feedback": None, "feedback_dropped": stored.dropped}
    text = answer if isinstance(answer, str) else ""
    parts: list[FeedbackPartOut] = []
    for part in stored.parts:
        if "quote" in part:
            start, end = part["quote"]
            if not 0 <= start < end <= len(text):  # never for a closed attempt's own answer
                log.warning("assessment_feedback_span_unreadable")
                return {"feedback": None, "feedback_dropped": True}
            parts.append(FeedbackPartOut(kind="quote", text=text[start:end]))
        else:
            parts.append(FeedbackPartOut(kind="text", text=str(part.get("text", ""))))
    return {
        "feedback": FeedbackOut(ai_generated=True, text=stored.text, parts=parts),
        "feedback_dropped": False,
    }


async def read(user: authz.Principal, class_session_id: uuid.UUID) -> MyAssessmentOut | None:
    """The Student's «KI-vurdering»; None for every caller but the Student of the Class session
    (FR-5)."""
    async with get_sessionmaker()() as s:
        found = await sessions.individual_test_session_of(s, user, class_session_id)
    if found is None:
        return None
    view, _ = await _view(class_session_id, user.id)
    return view


def _state_of(
    switch: assessment.Switch,
    closed: bool,
    status: str | None,
    runs: int,
) -> str:
    """The state a view reads before its items (shared by the view and the staff list): switched
    off, stopped and not ready, not ready (open, no row, or no finished run), failed, or the
    row's own state (`incomplete` or `ready`, which the view may still read as not ready)."""
    if not switch.enabled:
        return "switched_off"
    if switch.stopped and status != "ready":
        return "switched_off"
    if not closed or status is None or (status == "incomplete" and runs == 0):
        return "not_ready"
    # Only the states a view knows; anything else reads as not ready, never a 500 for the list.
    return status if status in ("incomplete", "ready", "failed") else "not_ready"


async def _view(
    class_session_id: uuid.UUID, user_id: uuid.UUID
) -> tuple[MyAssessmentOut, uuid.UUID | None]:
    """The «KI-vurdering» of the Student `user_id` in the Class session, and their attempt's id
    (None with no attempt). The caller has judged access."""
    async with get_sessionmaker()() as s:
        attempt = await commands.attempt_of(s, user_id, class_session_id)
        if attempt is None:
            return _state("no_test"), None
        switch = await assessment.switch_of(s, class_session_id)
        closed = attempt["closed_at"] is not None
        record = await assessment.assessment_of(s, attempt["id"]) if closed else None
        # Story 12.4 (FR-61, FR-69): a stopped assessment reads as switched off until it is
        # resumed; one that was ready before the stop stays readable.
        state = _state_of(
            switch,
            closed,
            None if record is None else record.status,
            0 if record is None else record.runs,
        )
        if state in ("switched_off", "not_ready", "failed"):
            return _state(state), attempt["id"]
        assert record is not None
        in_force = await guide.in_force(s, class_session_id)
        saved = (
            await s.execute(
                select(test_answers.c.item_id, test_answers.c.score, test_answers.c.value).where(
                    test_answers.c.attempt_id == attempt["id"]
                )
            )
        ).all()
        stored = {each.item_id: each.score for each in saved}
        answers = {each.item_id: each.value for each in saved}
    checked = record.scoring_guide_id is not None and await content.is_checked(
        record.scoring_guide_id, record.model_config_id
    )
    question_set: QuestionSet = await content.get(
        content.Kind.QUESTION_SET, attempt["question_set_version"]
    )
    by_id = {item.id: item for item in (*question_set.items, *question_set.replacements)}
    labels = {step.step: step.label for step in in_force.record.guide.scale}
    items: list[AssessedItemOut] = []
    computed: dict[str, float] = {}
    ai_items: dict[str, int] = {}
    weights: dict[str, int] = {}
    unassessed: list[int] = []
    for number, frozen in enumerate(attempt["items"], start=1):
        item_id, kind, weight = frozen["id"], frozen["type"], int(frozen["weight"])
        weights[item_id] = weight
        wording = WordingOut.model_validate(frozen["text"]) if kind == ADAPTED else None
        title = wording.text if wording is not None else by_id[item_id].title
        points: float | None
        if kind in AI_TYPES:
            step = record.scores.get(item_id)
            ai = AiScoreOut(
                assessed=step is not None,
                step=step,
                top=SCALE_TOP,
                label=labels.get(step) if step is not None else None,
                **_feedback_of(record.feedback.get(item_id), answers.get(item_id)),
            )
            ai.flagged = ai.feedback is not None and item_id in record.flags
            if step is None:
                unassessed.append(number)
                points = None
            else:
                ai_items[item_id] = step
                points = round(weight * step / SCALE_TOP, 2)
            computed_out = None
        else:
            credit, computed_out = _computed(stored.get(item_id))
            computed[item_id] = credit
            points = round(weight * credit, 2)
            ai = None
        items.append(
            AssessedItemOut(
                id=item_id,
                number=number,
                type=kind,
                title=title,
                wording=wording,
                weight=weight,
                points=points,
                computed=computed_out,
                ai=ai,
            )
        )
    total = total_score(computed, ai_items, weights) if not unassessed else None
    ready = record.status == "ready" and total is not None
    if not ready and not unassessed:
        # A later run stored the last score and has not settled the state yet: no list to show.
        return _state("not_ready"), attempt["id"]
    return MyAssessmentOut(
        state="ready" if ready else "incomplete",
        items=items,
        unassessed=unassessed,
        total=total if ready else None,
        total_max=sum(weights.values()) if ready else None,
        checked=checked,
    ), attempt["id"]


class NotFlaggable(Exception):
    """409 `feedback_not_flaggable`: the Student's view shows no written feedback for that item
    now (a computed item, feedback left out or not given, an unknown item, or a state with no
    items)."""

    code = "feedback_not_flaggable"


async def set_flag(
    user: authz.Principal, class_session_id: uuid.UUID, item_id: str, flagged: bool
) -> MyAssessmentOut | None:
    """«Marker som feil» (`flagged`) or «Angre» on the written feedback of one item of the
    Student's own assessment (Story 12.5, FR-55), idempotent; answers the view as it now stands.
    None (403) for every caller but the Student of the Class session; raises `NotFlaggable`."""
    async with get_sessionmaker()() as s:
        found = await sessions.individual_test_session_of(s, user, class_session_id)
    if found is None:
        return None
    view, attempt_id = await _view(class_session_id, user.id)
    item = next((each for each in view.items if each.id == item_id), None)
    shown = item is not None and item.ai is not None and item.ai.feedback is not None
    # «Angre» also takes back a flag the view hides now (a stop while not ready): the Student's
    # own mark never stays against their will.
    if attempt_id is None or (flagged and not shown):
        raise NotFlaggable
    if not await assessment.set_flag(attempt_id, item_id, flagged, now=auth.utcnow()):
        raise NotFlaggable  # no stored score for that item
    after, _ = await _view(class_session_id, user.id)
    return after


async def staff_read(
    user: authz.Principal, class_session_id: uuid.UUID, student_id: uuid.UUID
) -> StaffAssessmentOut | None:
    """The «KI-vurdering» of the Student `student_id` for the staff of the Class (Story 12.5,
    `ai_assessments.read`: its owners and Assistant lecturers): what the Student reads, with the
    flags they set. None, one answer, for anyone else, a User who is not a Student of the Class
    now and an unknown Class session (FR-5, AD-12)."""
    if (
        await sessions.student_target(user, class_session_id, student_id, "ai_assessments.read")
        is None
    ):
        return None
    view, _ = await _view(class_session_id, student_id)
    # Field by field: whatever only the Student's own view carries stays out (AD-12).
    return StaffAssessmentOut.model_validate(view.model_dump())


async def staff_list(
    user: authz.Principal, class_session_id: uuid.UUID
) -> AssessmentListOut | None:
    """Each Student of the Class with the state of their AI assessment (as their own view reads
    it, before its items) and how many pieces of feedback they flagged, by name (Story 12.5), for
    the staff of the Class (`ai_assessments.read`); None for anyone else (FR-5)."""
    if not await sessions.class_staff_may(user, class_session_id, "ai_assessments.read"):
        return None
    names = await sessions.session_students(class_session_id)
    async with get_sessionmaker()() as s:
        switch = await assessment.switch_of(s, class_session_id)
        summaries = await assessment.summaries_for_session(s, class_session_id)
        attempts = {
            row.user_id: row.closed_at is not None
            for row in await s.execute(
                select(test_attempts.c.user_id, test_attempts.c.closed_at).where(
                    test_attempts.c.class_session_id == class_session_id
                )
            )
        }
    rows: list[AssessmentRowOut] = []
    for student_id, name in sorted(names.items(), key=lambda each: (each[1].casefold(), each[0])):
        summary = summaries.get(student_id)
        if student_id not in attempts:
            state = "no_test"
        else:
            state = _state_of(
                switch,
                attempts[student_id],
                None if summary is None else summary.status,
                0 if summary is None else summary.runs,
            )
        rows.append(
            AssessmentRowOut(
                user_id=student_id,
                name=name,
                state=state,  # type: ignore[arg-type]
                flags=summary.flags
                if summary is not None and state in ("ready", "incomplete")
                else 0,
            )
        )
    return AssessmentListOut(students=rows)
