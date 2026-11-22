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
Student of their own locked Class session reads it; every other caller gets None (403)."""

import uuid
from collections.abc import Mapping
from typing import Any

import structlog
from sqlalchemy import select

from app.analysis import adapted as adapted_rules
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
    ComputedCriterionOut,
    ComputedScoreOut,
    MyAssessmentOut,
    WordingOut,
)
from app.platform import authz
from app.platform.db import get_sessionmaker

__all__ = ["AI_TYPES", "read", "read_for_assessment"]

log = structlog.get_logger(__name__)

AI_TYPES = frozenset({"long", ADAPTED})
"""The item types the AI assesses against the Scoring guide; every other type is computed."""


async def _fact_lines(frozen: Mapping[str, Any]) -> str:
    """The fact an Adapted item cites, as `id: name=value, …` from its stored facts set and its
    template; `""` when either cannot be read (the question text carries the same numbers)."""
    stored = await games.fact_set_by_id(str(frozen.get("fact_set_id")))
    if stored is None:
        log.warning("assessment_facts_unavailable", item_id=frozen["id"])
        return ""
    _, templates = await content.adapted_templates(frozen.get("template_version"))
    template = next((t for t in templates.templates if t.id == frozen["id"]), None)
    if template is None:
        return ""
    names = await adapted.pattern_names(stored) if template.fact == "pattern" else {}
    picked = adapted_rules.picked(template, stored.facts, names)
    if picked is None:
        return ""
    fact_id, values = picked
    return f"{fact_id}: " + ", ".join(f"{name}={value}" for name, value in values.items())


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
        if frozen["type"] == ADAPTED:
            question = frozen["text"]["text"]
            entry = entries.get(frozen["id"])
            facts = await _fact_lines(frozen)
        else:
            found = by_id.get(frozen["id"])
            question = found.title if found is not None else ""
            entry = entries.get(found.scoring_rule) if found and found.scoring_rule else None
            facts = ""
        items.append(
            assessment.ItemToAssess(
                item_id=frozen["id"], question=question, answer=answer, facts=facts, **_entry(entry)
            )
        )
    return assessment.AttemptToAssess(
        attempt_id=attempt["id"],
        user_id=attempt["user_id"],
        class_session_id=attempt["class_session_id"],
        closed=attempt["closed_at"] is not None,
        question_set_version=attempt["question_set_version"],
        scoring_guide_id=in_force.record.id,
        scale=tuple((step.step, step.label) for step in in_force.record.guide.scale),
        items=tuple(items),
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


async def read(user: authz.Principal, class_session_id: uuid.UUID) -> MyAssessmentOut | None:
    """The Student's «KI-vurdering»; None for every caller but the Student of the Class session
    (FR-5)."""
    async with get_sessionmaker()() as s:
        found = await sessions.individual_test_session_of(s, user, class_session_id)
        if found is None:
            return None
        attempt = await commands.attempt_of(s, user.id, class_session_id)
        if attempt is None:
            return _state("no_test")
        if not (await assessment.switch_of(s, class_session_id)).enabled:
            return _state("switched_off")
        record = (
            await assessment.assessment_of(s, attempt["id"])
            if attempt["closed_at"] is not None
            else None
        )
        if record is None or (record.status == "incomplete" and record.runs == 0):
            return _state("not_ready")
        if record.status == "failed":
            return _state("failed")
        in_force = await guide.in_force(s, class_session_id)
        saved = await s.execute(
            select(test_answers.c.item_id, test_answers.c.score).where(
                test_answers.c.attempt_id == attempt["id"]
            )
        )
        stored = {item_id: score for item_id, score in saved.all()}
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
            )
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
        return _state("not_ready")
    return MyAssessmentOut(
        state="ready" if ready else "incomplete",
        items=items,
        unassessed=unassessed,
        total=total if ready else None,
        total_max=sum(weights.values()) if ready else None,
    )
