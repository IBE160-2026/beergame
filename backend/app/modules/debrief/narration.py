"""The Debrief's AI text (Story 9.14, FR-44, FR-46, FR-34, AD-6, AD-7, AD-9).

Timing (the spine's deferred decision, closed here): narration is generated on `llm-batch` in
`worker-batch`, deferred when a Class game finishes, inside the `finish` transaction through the
`games.service.on_game_finished` hook this module registers on import (so `games` imports nothing
from `debrief`). One idempotent job per Seat a Student ever held (`narration:<game>:<seat>`, ids
only), which covers every Student assigned to it: the narration is the Seat's facts set's, the
same for each of them. Nothing is deferred when the Class session's pinned `debrief_ai_text` is
off. The sweep re-enqueues the job of a Seat with no stored narration ten minutes after the Game
finished (`due_narrations`, `narrate_due`).

The job (`narrate`): the Seat's facts set (`games.fact_set`, stored once), then one
`quiz_explanation` call per pinned quiz question with an own-game sentence, then the
`debrief_narration` call, each through `app.ai.text.worded` with `analysis.validate_ai_text` as
validator and the code text as fallback; each result stored once in `debrief_ai_texts` by
`commands.store_ai_text`. The narration row is stored last and marks the Seat done. No Debrief
step waits on it: step 4 shows the code text until it is stored, and what a Student first sees
stays (`service._moments`)."""

import uuid
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import budget as ai_budget
from app.ai import gateway
from app.ai import text as ai_text
from app.analysis import narration as narration_rules
from app.analysis.facts import FactSet
from app.modules.content import service as content
from app.modules.debrief import commands
from app.modules.debrief.models import debrief_ai_texts
from app.modules.games import service as games
from app.platform import jobs
from app.platform.db import get_sessionmaker

__all__ = [
    "AI_TEXT_PIN",
    "NARRATE_TASK",
    "NARRATION",
    "SWEEP_AFTER",
    "due_narrations",
    "enabled_pin",
    "fact_lines",
    "narrate",
    "narrate_due",
    "narration_is_ai",
    "narration_key",
    "quiz_subject",
]

log = structlog.get_logger(__name__)

NARRATE_TASK = "debrief.narrate"
"""The `llm-batch` task that words a Seat's narration and quiz lines."""

AI_TEXT_PIN = "debrief_ai_text"
"""The Class session's pin of the AI-text switch (`sessions.debrief_ai_text_pin`)."""

NARRATION = "narration"
"""The subject of a facts set's narration row."""

SWEEP_AFTER = timedelta(minutes=10)
"""How long after the finish a Seat with no narration counts as lost and is deferred again."""

SWEEP_WINDOW = timedelta(hours=48)
"""Games that finished longer ago than this are not looked at again (a Seat whose job keeps
failing is given up, and every finished Game of the past is not read every minute)."""

SWEEP_BATCH = 50
"""The most Seats one sweep defers again; the next minute's sweep takes the rest."""


def quiz_subject(question_id: str) -> str:
    return f"quiz:{question_id}"


def narration_key(game_id: object, seat_id: object) -> str:
    return f"narration:{game_id}:{seat_id}"


def enabled_pin(pins: object) -> Mapping[str, Any] | None:
    """The Class session's `debrief_ai_text` pin when it turns AI text on with a model config;
    None otherwise (off, or a session locked before the pin existed: code-only)."""
    if not isinstance(pins, Mapping):
        return None
    pin = pins.get(AI_TEXT_PIN)
    if not isinstance(pin, Mapping) or pin.get("enabled") is not True:
        return None
    return pin if pin.get("model_config_id") else None


async def _defer_on_finish(session: AsyncSession, finished: games.FinishedGame) -> None:
    """The finish hook: one narration job per Seat a Student held in a Class game, when the pin
    is on. A Replay or a Lecturer's test Game has no Debrief (Story 10.5, AD-13)."""
    if finished.class_session_id is None or enabled_pin(finished.pins) is None:
        return
    if not games.policy(finished.purpose).lecturer_overview:
        return
    for seat_id in finished.student_seat_ids:
        await jobs.defer(
            session,
            NARRATE_TASK,
            queue=jobs.LLM_BATCH,
            queueing_lock=narration_key(finished.game_id, seat_id),
            game_id=str(finished.game_id),
            seat_id=str(seat_id),
        )


games.on_game_finished("debrief.narration", _defer_on_finish)


fact_lines = narration_rules.fact_lines
"""The facts a narration or a follow-up answer may cite (`analysis.narration.fact_lines`)."""


def _template_lines(templates: narration_rules.NarrationTemplates) -> str:
    """The narration's own templates (version 2 also holds the follow-up's hints, which a
    narration never cites)."""
    return "\n".join(templates.lines(narration_rules.NARRATION_TEMPLATES))


def _validator(facts: FactSet, templates: narration_rules.NarrationTemplates, most: int):
    def validate(output: narration_rules.AiTextOutput) -> str | None:
        if len(output.sentences) > most:
            return None
        verdict = narration_rules.validate_ai_text(output, facts, templates)
        if not verdict.accepted:
            log.info("debrief_ai_text_rejected", reason=verdict.reason)
            return None
        return verdict.text

    return validate


async def _stored(fact_set_id: uuid.UUID) -> set[str]:
    async with get_sessionmaker()() as session:
        rows = await session.scalars(
            select(debrief_ai_texts.c.subject).where(debrief_ai_texts.c.fact_set_id == fact_set_id)
        )
        return set(rows)


async def narration_is_ai(fact_set_id: uuid.UUID) -> bool:
    """Whether the facts set's stored narration is AI text (the dev narration's check)."""
    async with get_sessionmaker()() as session:
        found = await session.scalar(
            select(debrief_ai_texts.c.ai_generated).where(
                debrief_ai_texts.c.fact_set_id == fact_set_id,
                debrief_ai_texts.c.subject == NARRATION,
            )
        )
    return bool(found)


async def narrate(game_id: str, seat_id: str) -> bool:
    """Word the narration and quiz lines of a finished Class game's Seat and store them; True
    when this call stored the narration. Nothing for a Game outside a Class session, with AI text
    off, or a Seat already done. Never raises for a provider or validation problem: each line
    falls back to its code text (AD-7)."""
    game = await games.get_game(game_id)
    if game is None or game.class_session_id is None or game.session_runtime is None:
        return False
    pins = game.session_runtime.pins or {}
    pin = enabled_pin(pins)
    if pin is None:
        return False
    stored = await games.fact_set(game_id, seat_id)
    fact_set_id = uuid.UUID(stored.id)
    done = await _stored(fact_set_id)
    if NARRATION in done:
        return False
    facts = stored.facts
    _, templates = await content.narration_templates(
        content.pinned_version(pins, content.Kind.NARRATION_TEMPLATES)
    )
    scope = ai_budget.BudgetScope.class_session(
        game.class_session_id,
        effort_level=pin.get("effort_level"),
        model_config_id=pin["model_config_id"],
    )
    caller = {
        "game_id": uuid.UUID(game_id),
        "seat_id": uuid.UUID(seat_id),
        "fact_set_id": fact_set_id,
    }
    shared = {
        "role": str(facts.seat.role),
        "facts": fact_lines(facts),
        "templates": _template_lines(templates),
    }
    own = narration_rules.code_output(facts)
    if own is not None:
        await _quiz_lines(pins, facts, templates, scope, caller, shared, own, fact_set_id, done)
    code = narration_rules.render(facts, templates)
    if code is None:
        # No moments (a game played mostly by AI players): nothing to connect, no call.
        return await commands.store_ai_text(
            fact_set_id, NARRATION, "", ai_generated=False, llm_call_id=None
        )
    worded = await ai_text.worded(
        "debrief_narration",
        scope,
        gateway.Inputs(
            values={**shared, "max_sentences": narration_rules.MAX_SENTENCES},
            caller=caller,
            mock_answer=own,
        ),
        narration_rules.AiTextOutput,
        validate=_validator(facts, templates, narration_rules.MAX_SENTENCES),
        fallback=lambda: code.text,
    )
    return await commands.store_ai_text(
        fact_set_id,
        NARRATION,
        worded.text,
        ai_generated=worded.ai_generated,
        llm_call_id=worded.llm_call_id,
    )


async def _quiz_lines(
    pins: Mapping[str, Any],
    facts: FactSet,
    templates: narration_rules.NarrationTemplates,
    scope: ai_budget.BudgetScope,
    caller: Mapping[str, uuid.UUID],
    shared: Mapping[str, str],
    own: narration_rules.AiTextOutput,
    fact_set_id: uuid.UUID,
    done: set[str],
) -> None:
    """One `quiz_explanation` call per pinned quiz question that has an own-game sentence; a
    failure stores an empty code line, so the content's explanation stands alone (FR-46)."""
    _, quiz = await content.debrief_quiz(content.pinned_version(pins, content.Kind.DEBRIEF_QUIZ))
    mock = narration_rules.AiTextOutput(sentences=own.sentences[-1:])
    for question in quiz.questions:
        subject = quiz_subject(question.id)
        if question.in_your_game is None or subject in done:
            continue
        worded = await ai_text.worded(
            "quiz_explanation",
            scope,
            gateway.Inputs(
                values={**shared, "question": question.prompt, "explanation": question.explanation},
                caller=caller,
                mock_answer=mock,
            ),
            narration_rules.AiTextOutput,
            validate=_validator(facts, templates, 1),
            fallback=lambda: "",
        )
        await commands.store_ai_text(
            fact_set_id,
            subject,
            worded.text,
            ai_generated=worded.ai_generated,
            llm_call_id=worded.llm_call_id,
        )


async def due_narrations(now: datetime) -> list[tuple[str, str]]:
    """The sweep's finder: `(game_id, seat_id)` of each Seat a Student held in a Class game that
    finished more than `SWEEP_AFTER` ago with AI text on, whose facts set has no narration row
    (the job was lost, or never ran). At most `SWEEP_BATCH`."""
    seats = await games.finished_student_seats(now - SWEEP_WINDOW, now - SWEEP_AFTER)
    candidates = [seat for seat in seats if enabled_pin(seat.pins) is not None]
    with_facts = [seat.fact_set_id for seat in candidates if seat.fact_set_id is not None]
    narrated: set[uuid.UUID] = set()
    if with_facts:
        async with get_sessionmaker()() as session:
            narrated = set(
                await session.scalars(
                    select(debrief_ai_texts.c.fact_set_id).where(
                        debrief_ai_texts.c.fact_set_id.in_(with_facts),
                        debrief_ai_texts.c.subject == NARRATION,
                    )
                )
            )
    due = [
        (str(seat.game_id), str(seat.seat_id))
        for seat in candidates
        if seat.fact_set_id is None or seat.fact_set_id not in narrated
    ]
    return due[:SWEEP_BATCH]


async def narrate_due(item: object, now: datetime) -> bool:
    """Defer the Seat's narration job again (idempotent: a waiting job is not doubled)."""
    game_id, seat_id = item  # type: ignore[misc]
    async with get_sessionmaker().begin() as session:
        return await jobs.defer(
            session,
            NARRATE_TASK,
            queue=jobs.LLM_BATCH,
            queueing_lock=narration_key(game_id, seat_id),
            game_id=str(game_id),
            seat_id=str(seat_id),
        )
