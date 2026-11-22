"""Adapted items prepared before the test opens, in natural wording (Story 11.8, FR-53, FR-34,
AD-6, AD-7, AD-9).

The decision (the Deferred item "Timing of Adapted items"):

- `ops.sweep`'s due action `tests.prepare_adapted` finds each Student with the `replay` step
  (recorded within `PREPARE_WINDOW`), no opened attempt and no prepared set (`due_prepares`), and
  defers the idempotent job `tests.prepare_adapted(user_id, class_session_id)` on `llm-batch`,
  ids only, keyed by both (`prepare_due`).
- The job (`prepare`) builds the Student's items exactly as opening would (Story 11.7,
  `adapted.build_with_sets`), then, when the Class session's pinned Debrief AI-text switch is on
  with a model config, asks `adapted_item_wording` once for each Adapted item whose template has
  approved `wordings`. The output names a wording id and the item's fact id only
  (`analysis.narration.AiTextOutput`); `analysis.adapted.validate_wording` checks it against the
  facts set whose id the item stores, and code renders every number, Week and Role. A rejection
  or a typed failure keeps the code text of Story 11.7; the call is never retried here
  (`app.ai.text.worded`). Text travels as `{text, ai_generated, llm_call_id}`.
- It then stores one prepared set per Student and Class session (`test_prepared_items`), once,
  and not at all when the Student opened the test meanwhile. `commands.open_attempt` freezes the
  prepared set when one exists for the selection it opens on; without one it builds the code
  items as in Story 11.7, so opening never waits on an LLM call. An opened attempt never changes.

No item text, fact value or answer is logged; the prompt gets the facts' numbers and Role only."""

import uuid
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select, tuple_
from sqlalchemy.dialects.postgresql import insert

from app.ai import budget as ai_budget
from app.ai import gateway
from app.ai import text as ai_text
from app.analysis import adapted as adapted_rules
from app.analysis.narration import AiSentence, AiTextOutput
from app.modules.progress import service as progress
from app.modules.sessions import service as sessions
from app.modules.tests import adapted, commands
from app.modules.tests.models import test_attempts, test_prepared_items
from app.platform import jobs
from app.platform.db import get_sessionmaker

__all__ = [
    "PREPARE_TASK",
    "PREPARE_WINDOW",
    "PURPOSE",
    "SWEEP_BATCH",
    "due_prepares",
    "enabled_pin",
    "prepare",
    "prepare_due",
    "prepare_key",
]

log = structlog.get_logger(__name__)

PREPARE_TASK = "tests.prepare_adapted"
"""The `llm-batch` task that prepares a Student's Adapted items."""

PURPOSE = "adapted_item_wording"

PREPARE_WINDOW = timedelta(days=30)
"""Only Students whose `replay` step is this recent are looked at: a Test deadline lies days, not
months, after the Replay, and the sweep does not read every old step every minute."""

SWEEP_BATCH = 50
"""The most jobs one sweep defers; the next minute's sweep takes the rest."""


def prepare_key(user_id: object, class_session_id: object) -> str:
    return f"adapted:{user_id}:{class_session_id}"


def enabled_pin(pins: object) -> Mapping[str, Any] | None:
    """The Class session's pinned Debrief AI-text switch when it is on with a model config; None
    otherwise (off, or a session locked before the pin existed: code text only, FR-15)."""
    if not isinstance(pins, Mapping):
        return None
    pin = pins.get(sessions.DEBRIEF_AI_TEXT_PIN)
    if not isinstance(pin, Mapping) or pin.get("enabled") is not True:
        return None
    return pin if pin.get("model_config_id") else None


async def due_prepares(now: datetime) -> list[tuple[str, str]]:
    """The sweep's finder: `(user_id, class_session_id)` of each Student with the `replay` step
    since `now - PREPARE_WINDOW`, no attempt and no prepared set, oldest step first; at most
    `SWEEP_BATCH`."""
    async with get_sessionmaker()() as s:
        found = await progress.steps_since(s, progress.Step.REPLAY, now - PREPARE_WINDOW)
        if not found:
            return []
        taken: set[tuple[uuid.UUID, uuid.UUID]] = set()
        for table in (test_attempts, test_prepared_items):
            pairs = tuple_(table.c.user_id, table.c.class_session_id)
            result = await s.execute(
                select(table.c.user_id, table.c.class_session_id).where(pairs.in_(found))
            )
            taken.update((user_id, session_id) for user_id, session_id in result.all())
    due = [(str(u), str(c)) for u, c in found if (u, c) not in taken]
    return due[:SWEEP_BATCH]


async def prepare_due(item: object, now: datetime) -> bool:
    """Defer the Student's prepare job (idempotent: a waiting job is not doubled)."""
    user_id, class_session_id = item  # type: ignore[misc]
    async with get_sessionmaker().begin() as s:
        return await jobs.defer(
            s,
            PREPARE_TASK,
            queue=jobs.LLM_BATCH,
            queueing_lock=prepare_key(user_id, class_session_id),
            user_id=str(user_id),
            class_session_id=str(class_session_id),
        )


async def _taken(s: Any, user_id: uuid.UUID, class_session_id: uuid.UUID) -> bool:
    """Whether the Student has an attempt or a prepared set in the Class session."""
    for table in (test_attempts, test_prepared_items):
        found = await s.scalar(
            select(table.c.user_id).where(
                table.c.user_id == user_id, table.c.class_session_id == class_session_id
            )
        )
        if found is not None:
            return True
    return False


def _fact_line(fact_id: str, values: Mapping[str, str]) -> str:
    return f"{fact_id}: " + ", ".join(f"{name}={value}" for name, value in values.items())


async def _word(
    item: dict[str, Any],
    template: adapted_rules.AdaptedTemplate,
    stored: Any,
    scope: ai_budget.BudgetScope,
) -> dict[str, Any]:
    """The item's text: the chosen wording when the call succeeds and the validator accepts it,
    else the code text it has (AD-7)."""
    names = await adapted.pattern_names(stored) if template.fact == "pattern" else {}
    facts = stored.facts
    code = item["text"]["text"]
    fact_ids = tuple(item["fact_ids"])
    picked = adapted_rules.picked(template, facts, names)
    values = {} if picked is None else picked[1]

    def validate(output: AiTextOutput) -> str | None:
        verdict = adapted_rules.validate_wording(output, template, facts, names, fact_ids)
        if not verdict.accepted:
            log.info("adapted_wording_rejected", template_id=template.id, reason=verdict.reason)
            return None
        return verdict.text

    worded = await ai_text.worded(
        PURPOSE,
        scope,
        gateway.Inputs(
            values={
                "role": str(facts.seat.role),
                "facts": "\n".join(_fact_line(fact_id, values) for fact_id in fact_ids),
                "wordings": "\n".join(f"{w.id}: {w.text}" for w in template.wordings),
            },
            caller={
                "game_id": uuid.UUID(stored.game_id),
                "seat_id": uuid.UUID(stored.seat_id),
                "fact_set_id": uuid.UUID(stored.id),
            },
            mock_answer=AiTextOutput(
                sentences=(AiSentence(template_id=template.wordings[0].id, fact_ids=fact_ids),)
            ),
        ),
        AiTextOutput,
        validate=validate,
        fallback=lambda: code,
    )
    call_id = None if worded.llm_call_id is None else str(worded.llm_call_id)
    return {
        **item,
        "text": {"text": worded.text, "ai_generated": worded.ai_generated, "llm_call_id": call_id},
    }


async def prepare(user_id: str, class_session_id: str) -> bool:
    """Prepare the Student's Adapted items and store them once; True when this call stored them.
    Nothing when the Student has opened the test or a set is prepared already. Never raises for a
    provider or validation problem: an item keeps its code text (AD-7)."""
    student, session_id = uuid.UUID(user_id), uuid.UUID(class_session_id)
    async with get_sessionmaker()() as s:
        if await _taken(s, student, session_id):
            return False
        pins = await sessions.locked_pins(s, session_id)
        chosen, question_set = await commands.selection_of(s, session_id, pins)
        built = await adapted.build_with_sets(
            s, student, session_id, pins, chosen.adapted_weight, question_set
        )
    items = [dict(item) for item in built.items]
    pin = enabled_pin(pins)
    worded = 0
    if pin is not None and built.templates is not None:
        by_id = {template.id: template for template in built.templates.templates}
        scope = ai_budget.BudgetScope.class_session(
            session_id,
            effort_level=pin.get("effort_level"),
            model_config_id=pin["model_config_id"],
        )
        for n, item in enumerate(items):
            template = by_id.get(item["id"]) if item.get("type") == adapted.ADAPTED else None
            if template is None or not template.wordings:
                continue
            items[n] = await _word(item, template, built.sets[item["fact_set_id"]], scope)
            worded += items[n]["text"]["ai_generated"]
    async with get_sessionmaker().begin() as s:
        opened = await s.scalar(
            select(test_attempts.c.id).where(
                test_attempts.c.user_id == student,
                test_attempts.c.class_session_id == session_id,
            )
        )
        if opened is not None:
            log.info("adapted_items_not_prepared", class_session_id=class_session_id, opened=True)
            return False
        stored = await s.scalar(
            insert(test_prepared_items)
            .values(
                user_id=student,
                class_session_id=session_id,
                question_set_version=chosen.version,
                adapted_weight=chosen.adapted_weight,
                items=items,
            )
            .on_conflict_do_nothing(constraint="pk_test_prepared_items")
            .returning(test_prepared_items.c.user_id)
        )
    log.info(
        "adapted_items_prepared",
        class_session_id=class_session_id,
        stored=stored is not None,
        items=len(items),
        ai_worded=worded,
    )
    return stored is not None
