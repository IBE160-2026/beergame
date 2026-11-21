"""Bounded follow-up questions about the Student's own Game (Story 9.15, FR-45, FR-15, FR-34,
AD-6, AD-7, AD-11, AD-14).

The field stands under the reflection questions, before step 4. A question is one call on the
api's request: `app.ai.text.worded("debrief_follow_up", <Class session scope>, …)` with the
question and the Student's Explanation (free text, scrubbed against the Roster by the gateway),
the Seat's stored facts set and the pinned hint templates, bounded by
`follow_up_deadline_seconds`. The answer is a decline (stored, shown as a fixed line) or hint
sentences that `analysis.follow_up.validate_follow_up` accepts and code renders (stored, shown
marked «KI-generert, kan ta feil:»). A failure, a rejection or a spent budget stores nothing and
the Student is told no answer could be given; nothing is retried and no Debrief step waits on it.

`state` says whether the field shows: `off` with the Class session's Debrief AI text off, no
provider that may answer on the pinned config, pinned templates without hints (a session locked
before this story) or a Seat with no moments (played mostly by AI players); `closed` once
`commands.close_follow_up` has run for the Student or the database time is past their Test
deadline (the backstop); else `open`. Every question counts against a per-account and a
per-address limit (`platform/ratelimit`, placeholder settings).

The service's gates (own Debrief, the Explanation, the Group pointer, every reflection question
answered) run before anything here."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import func, select

from app.ai import budget as ai_budget
from app.ai import gateway
from app.ai import text as ai_text
from app.analysis import follow_up as follow_up_rules
from app.analysis import narration as narration_rules
from app.analysis.facts import FactSet
from app.modules.content import service as content
from app.modules.debrief import commands, narration
from app.modules.debrief.models import (
    FOLLOW_UP_ANSWERED,
    FOLLOW_UP_DECLINED,
    debrief_explanations,
    debrief_follow_up_closures,
    debrief_follow_ups,
)
from app.modules.debrief.schemas import FollowUpAnswerOut, RenderedTextOut
from app.modules.games import service as games
from app.modules.sessions import service as sessions
from app.platform import ratelimit
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

__all__ = [
    "PURPOSE",
    "Closed",
    "InvalidQuestion",
    "Off",
    "Prepared",
    "RateLimited",
    "ask",
    "asked",
    "closed",
    "judge_question",
    "prepare",
]

log = structlog.get_logger(__name__)

PURPOSE = "debrief_follow_up"

ACCOUNT_BUCKET = "follow_up_account"
IP_BUCKET = "follow_up_ip"


class Off(Exception):
    """No follow-up in this Debrief (409 `follow_up_off`): the field is not shown."""


class Closed(Exception):
    """The Student's follow-up is closed (409 `follow_up_closed`)."""


class InvalidQuestion(Exception):
    """A question that may not be sent: `blank` (white space only) or `too_long`."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class RateLimited(Exception):
    """Too many questions in the window (429 `rate_limited`); `retry_after` in seconds."""

    def __init__(self, retry_after: int) -> None:
        super().__init__(retry_after)
        self.retry_after = retry_after


@dataclass(frozen=True)
class Prepared:
    """What a question needs: the Class session scope's config and Effort level, the stored facts
    set and the pinned templates."""

    model_config_id: str
    effort_level: str | None
    fact_set_id: uuid.UUID
    seat_id: uuid.UUID
    facts: FactSet
    templates: narration_rules.NarrationTemplates


async def prepare(game_id: uuid.UUID, role: str) -> Prepared | None:
    """The follow-up of the Seat `role` of the finished Class game, or None when it is off."""
    game = await games.get_game(str(game_id))
    if game is None or game.class_session_id is None or game.session_runtime is None:
        return None
    pins = game.session_runtime.pins or {}
    pin = narration.enabled_pin(pins)
    if pin is None or not await ai_text.can_word(PURPOSE, pin["model_config_id"]):
        return None
    _, templates = await content.narration_templates(
        content.pinned_version(pins, content.Kind.NARRATION_TEMPLATES)
    )
    if not templates.has_hints():
        return None
    stored = await games.fact_set(str(game_id), role)
    if not stored.facts.seat.moments:
        # A Seat played mostly by AI players (fewer than 10 Student Orders) has no moments: the
        # Student decided too little for hints to point to, as for the narration.
        return None
    return Prepared(
        model_config_id=str(pin["model_config_id"]),
        effort_level=pin.get("effort_level"),
        fact_set_id=uuid.UUID(stored.id),
        seat_id=uuid.UUID(stored.seat_id),
        facts=stored.facts,
        templates=templates,
    )


async def closed(user_id: uuid.UUID, class_session_id: uuid.UUID) -> bool:
    """Closed by `commands.close_follow_up`, or the database time is past the Student's
    effective Test deadline (`sessions.student_deadlines`), the backstop."""
    _, test_deadline = await sessions.student_deadlines(user_id, class_session_id)
    async with get_sessionmaker()() as session:
        found = await session.scalar(
            select(debrief_follow_up_closures.c.user_id).where(
                debrief_follow_up_closures.c.user_id == user_id,
                debrief_follow_up_closures.c.class_session_id == class_session_id,
            )
        )
        if found is not None:
            return True
        if test_deadline is None:
            return False
        return bool(await session.scalar(select(func.now() > test_deadline)))


def _out(row: commands.FollowUpRow) -> FollowUpAnswerOut:
    answered = row.outcome == FOLLOW_UP_ANSWERED and row.answer is not None
    return FollowUpAnswerOut(
        outcome="answered" if answered else "declined",
        question=row.question,
        answer=(
            RenderedTextOut(text=row.answer, ai_generated=True, llm_call_id=row.llm_call_id)
            if answered and row.answer is not None
            else None
        ),
        asked_at=row.asked_at,
    )


async def asked(user_id: uuid.UUID, class_session_id: uuid.UUID) -> list[FollowUpAnswerOut]:
    """The Student's own stored questions in the Class session, oldest first (AD-14)."""
    async with get_sessionmaker()() as session:
        found = (
            await session.execute(
                select(debrief_follow_ups)
                .where(
                    debrief_follow_ups.c.user_id == user_id,
                    debrief_follow_ups.c.class_session_id == class_session_id,
                )
                .order_by(debrief_follow_ups.c.asked_at, debrief_follow_ups.c.id)
            )
        ).mappings()
        return [_out(commands.follow_up_of(row)) for row in found]


def _quoted(text: str) -> str:
    """Free text as the prompt quotes it: angle brackets become look-alikes, so a question or an
    Explanation cannot close its `<question>` or `<explanation>` block and pose as the prompt's
    own words. What is stored and shown stays as typed."""
    return text.replace("<", "‹").replace(">", "›")


def judge_question(text: str) -> None:
    """Raises `InvalidQuestion` for white space only or more than `QUESTION_MAX` characters."""
    if not text.strip():
        raise InvalidQuestion("blank")
    if len(text) > follow_up_rules.QUESTION_MAX:
        raise InvalidQuestion("too_long")


async def _count(user_id: uuid.UUID, ip: str, now: datetime) -> None:
    """Count the question against the account's and the address's limits; raises
    `RateLimited` once either is passed (the count stays: a refused question counts too)."""
    settings = get_settings()
    window = timedelta(minutes=settings.follow_up_rate_limit_window_minutes)
    async with get_sessionmaker().begin() as session:
        mine = await ratelimit.hit(
            session, ACCOUNT_BUCKET, f"account:{user_id}", window=window, now=now
        )
        address = await ratelimit.hit(session, IP_BUCKET, f"ip:{ip}", window=window, now=now)
    if (
        mine > settings.follow_up_rate_limit_per_account
        or address > settings.follow_up_rate_limit_per_ip
    ):
        log.info("debrief_follow_up_refused", error_code="rate_limited")
        raise RateLimited(ratelimit.seconds_left(now, window))


async def _explanation(user_id: uuid.UUID, class_session_id: uuid.UUID) -> str:
    async with get_sessionmaker()() as session:
        found = await session.scalar(
            select(debrief_explanations.c.text).where(
                debrief_explanations.c.user_id == user_id,
                debrief_explanations.c.class_session_id == class_session_id,
            )
        )
    return found or ""


async def ask(
    user_id: uuid.UUID,
    class_session_id: uuid.UUID,
    game_id: uuid.UUID,
    prepared: Prepared,
    question: str,
    *,
    ip: str,
    now: datetime,
) -> FollowUpAnswerOut:
    """One follow-up question (FR-45): judged, counted, then one call that is never retried.
    Raises `InvalidQuestion` or `RateLimited`; the caller has checked `Off` and `Closed`."""
    judge_question(question)
    await _count(user_id, ip, now)
    facts, templates = prepared.facts, prepared.templates
    scope = ai_budget.BudgetScope.class_session(
        class_session_id,
        effort_level=prepared.effort_level,
        model_config_id=prepared.model_config_id,
    )
    caller = {
        "game_id": game_id,
        "seat_id": prepared.seat_id,
        "fact_set_id": prepared.fact_set_id,
        "user_id": user_id,
    }

    def validate(output: follow_up_rules.FollowUpOutput) -> str | None:
        verdict = follow_up_rules.validate_follow_up(output, facts, templates)
        if not verdict.accepted:
            log.info("debrief_follow_up_rejected", reason=verdict.reason)
            return None
        # A decline is an accepted answer with no text: the web app shows a fixed line.
        return "" if verdict.declined else verdict.text

    worded = await ai_text.worded(
        PURPOSE,
        scope,
        gateway.Inputs(
            values={
                "role": str(facts.seat.role),
                "facts": narration.fact_lines(facts),
                "templates": "\n".join(templates.lines(narration_rules.HINT_TEMPLATES)),
                "max_sentences": narration_rules.MAX_SENTENCES,
                "explanation": _quoted(await _explanation(user_id, class_session_id)),
                "question": _quoted(question),
            },
            caller=caller,
            mock_answer=follow_up_rules.mock_output(question, facts),
        ),
        follow_up_rules.FollowUpOutput,
        validate=validate,
        fallback=lambda: "",
        deadline=datetime.now(UTC) + timedelta(seconds=get_settings().follow_up_deadline_seconds),
    )
    if not worded.ai_generated or worded.llm_call_id is None:
        return FollowUpAnswerOut(outcome="unanswered", question=question)
    if await closed(user_id, class_session_id):
        # Closed while the model answered (the Individual test opened): nothing is stored.
        raise Closed
    saved = await commands.store_follow_up(
        user_id,
        class_session_id,
        prepared.fact_set_id,
        question,
        outcome=FOLLOW_UP_ANSWERED if worded.text else FOLLOW_UP_DECLINED,
        answer=worded.text or None,
        llm_call_id=worded.llm_call_id,
    )
    return _out(saved)
