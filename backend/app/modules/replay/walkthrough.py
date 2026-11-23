"""The Replay walkthrough (Story 10.7, FR-50, FR-44, FR-34, FR-15, AD-6, AD-7, AD-9, AD-12).

`walkthrough(user, game_id)` sets the Student's finished Replay beside their own Class game: the
Week rows of both Games (each Seat's Decision log, `state_seen`), the stored facts sets of both
Seats (`games.service.fact_set`, `analysis.facts` unchanged), and the Replay's own moments
rendered by `analysis.moments.render` with the moment templates the Class session pinned. The game
compared with is read only through `games.service.student_game`. The first ready view stores a
`replay_walkthroughs` row with both `fact_set_id`s and the line shown then; every later view
shows that line.

The line (AD-6, AD-7, AD-9): when a Replay finishes in a Class session whose pinned Debrief AI
text is on, the finish hook defers one idempotent `llm-batch` job (`NARRATE_TASK`, queueing lock
`replay-walkthrough:<game>`, ids only: the facts set does not exist yet inside the finishing
transaction). The job (`narrate`) words it through the shared `app.ai.text.worded` with purpose
`replay_walkthrough`, `analysis.validate_ai_text` as validator and this module's own code
renderer (`code_text`) as fallback, stores it once per Replay facts set in `replay_narrations`
and emits `user:<id>`, so a waiting page reads again. While the job is live, within
`replay_walkthrough_wait_seconds` of the finish (database time only), the walkthrough is
`pending`; after it, or with AI text off, the code line shows, unmarked.

A Replay closed at the Test deadline (Story 10.6) has no walkthrough (`replay_closed`); an
unfinished one neither (`replay_not_finished`). Only the Replay's own Student reads it."""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Literal

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import budget as ai_budget
from app.ai import gateway
from app.ai import text as ai_text
from app.analysis import moments as moment_text
from app.analysis import narration as narration_rules
from app.analysis.facts import FactSet, Moment
from app.analysis.sentences import format_money, format_number
from app.engine import GameSettings, Role
from app.modules.content import service as content
from app.modules.games import service as games_service
from app.modules.replay import repo
from app.modules.replay.models import replay_narrations, replay_walkthroughs
from app.modules.replay.schemas import (
    ReplayWalkthroughOut,
    WalkthroughClassGameOut,
    WalkthroughMomentOut,
    WalkthroughRunOut,
    WalkthroughTextOut,
    WalkthroughWeekOut,
)
from app.modules.sessions import service as sessions
from app.platform import authz, events, jobs
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

__all__ = [
    "NARRATE_TASK",
    "PURPOSE",
    "ReplayReport",
    "Unavailable",
    "code_output",
    "code_text",
    "enabled_pin",
    "narrate",
    "narration_key",
    "report",
    "shown_moments",
    "walkthrough",
]

log = structlog.get_logger(__name__)

NARRATE_TASK = "replay.narrate_walkthrough"
"""The `llm-batch` task that words a finished Replay's walkthrough line."""

PURPOSE = "replay_walkthrough"

SHOWN = 2
"""Moments a walkthrough shows: «one or two specific moments» (FR-50)."""


class Unavailable(Exception):
    """The Replay has no walkthrough: `replay_closed` (closed at the Test deadline, Story 10.6)
    or `replay_not_finished`; both 409."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def narration_key(game_id: object) -> str:
    return f"replay-walkthrough:{game_id}"


def enabled_pin(pins: object) -> Mapping[str, Any] | None:
    """The Class session's pinned Debrief AI-text switch when it is on with a model config; None
    otherwise (off, or a session locked before the pin existed: code only, FR-15)."""
    if not isinstance(pins, Mapping):
        return None
    pin = pins.get(sessions.DEBRIEF_AI_TEXT_PIN)
    if not isinstance(pin, Mapping) or pin.get("enabled") is not True:
        return None
    return pin if pin.get("model_config_id") else None


async def _defer_on_finish(session: AsyncSession, finished: games_service.FinishedGame) -> None:
    """The finish hook: one narration job for a Student's Replay (the Game a `replays` row
    names) when the Class session's pin is on. Any other Game: nothing."""
    if enabled_pin(finished.pins) is None:
        return
    if await repo.replay_owner(session, finished.game_id) is None:
        return
    await jobs.defer(
        session,
        NARRATE_TASK,
        queue=jobs.LLM_BATCH,
        queueing_lock=narration_key(finished.game_id),
        game_id=str(finished.game_id),
    )


games_service.on_game_finished("replay.walkthrough", _defer_on_finish)


def _rank(moment: Moment) -> tuple[int, Any, int]:
    """A moment with a Detected pattern first, then the higher later cost, then the earlier Uke."""
    return (0 if moment.chosen_by == "pattern" else 1, -moment.later_cost, moment.week)


def shown_moments(facts: FactSet, mostly_ai: bool) -> list[Moment]:
    """The Replay moments the walkthrough shows, by Uke: the `SHOWN` ranked first; every one
    (at least three, `analysis.facts.MOMENTS`) when the Class game was played mostly by AI
    players (FR-44)."""
    ranked = sorted(facts.seat.moments, key=_rank)
    chosen = ranked if mostly_ai else ranked[:SHOWN]
    return sorted(chosen, key=lambda moment: moment.week)


def _top(facts: FactSet) -> list[Moment]:
    """The `SHOWN` moments ranked first, by Uke: the ones every walkthrough shows, and the only
    facts its line may cite, so it never names an Uke the page leaves out."""
    return shown_moments(facts, mostly_ai=False)


def code_output(facts: FactSet) -> narration_rules.AiTextOutput | None:
    """The walkthrough's own choice of sentences: the two moments ranked first side by side, then
    the supply line of the one with more on the way; one moment alone gets the supply-line
    sentence. None when the Replay Seat has no moments."""
    top = _top(facts)
    if not top:
        return None
    sentence = narration_rules.AiSentence
    if len(top) == 1:
        return narration_rules.AiTextOutput(
            sentences=(sentence(template_id="narration-supply-line", fact_ids=(top[0].id,)),)
        )
    most = max(top, key=lambda moment: (moment.state_seen.supply_line, -moment.week))
    return narration_rules.AiTextOutput(
        sentences=(
            sentence(template_id="narration-orders", fact_ids=(top[0].id, top[1].id)),
            sentence(template_id="narration-supply-line", fact_ids=(most.id,)),
        )
    )


def code_text(facts: FactSet, templates: narration_rules.NarrationTemplates) -> str | None:
    """The code-rendered walkthrough line (the fallback of the job and of every view that does
    not wait for it): `code_output` rendered by `analysis.narration.render_output`."""
    output = code_output(facts)
    return None if output is None else narration_rules.render_output(output, facts, templates).text


def _fact_lines(facts: FactSet) -> str:
    """The facts the line may cite (the shown moments, `_top`), one per line: the id, then its
    numbers (no names)."""
    lines = []
    for fact in _top(facts):
        fact_id, seen = fact.id, fact.state_seen
        lines.append(
            f"{fact_id}: uke={format_number(fact.week)}, bestilling={format_number(fact.order)}, "
            f"på_vei={format_number(seen.supply_line)}, "
            f"ordre_inn={format_number(seen.incoming_order)}, "
            f"senere_kostnad={format_money(fact.later_cost)}"
        )
    return "\n".join(lines)


def _validator(facts: FactSet, templates: narration_rules.NarrationTemplates):
    shown = {moment.id for moment in _top(facts)}

    def validate(output: narration_rules.AiTextOutput) -> str | None:
        if any(fact_id not in shown for s in output.sentences for fact_id in s.fact_ids):
            log.info("replay_walkthrough_rejected", reason="not_shown")
            return None
        verdict = narration_rules.validate_ai_text(output, facts, templates)
        if not verdict.accepted:
            log.info("replay_walkthrough_rejected", reason=verdict.reason)
            return None
        return verdict.text

    return validate


async def _stored_narration(fact_set_id: uuid.UUID) -> WalkthroughTextOut | None:
    async with get_sessionmaker()() as s:
        found = (
            await s.execute(
                select(
                    replay_narrations.c.text,
                    replay_narrations.c.ai_generated,
                    replay_narrations.c.llm_call_id,
                ).where(replay_narrations.c.fact_set_id == fact_set_id)
            )
        ).one_or_none()
    if found is None:
        return None
    return WalkthroughTextOut(
        text=found.text, ai_generated=found.ai_generated, llm_call_id=found.llm_call_id
    )


def _student_seat(game: games_service.GameOverview) -> tuple[str, str] | None:
    """The Replay's Student Seat: its id and Role."""
    for seat in game.seats:
        if seat.user_id is not None:
            return str(seat.id), str(seat.role)
    return None


async def _templates(pins: object) -> narration_rules.NarrationTemplates:
    _, templates = await content.narration_templates(
        content.pinned_version(pins, content.Kind.NARRATION_TEMPLATES)
    )
    return templates


async def narrate(game_id: str) -> bool:
    """Word the walkthrough line of a finished Replay and store it once; True when this call
    stored it. Nothing for a Game that is not a Student's finished Replay, with AI text off, or a
    line already stored. Never raises for a provider or validation problem: the code text is
    stored instead, unmarked (AD-7)."""
    game = await games_service.get_game(game_id)
    if game is None or game.class_session_id is None or game.session_runtime is None:
        return False
    if game.lifecycle != "finished" or game.end_reason is not None:
        return False
    async with get_sessionmaker()() as s:
        owner = await repo.replay_owner(s, uuid.UUID(game_id))
    seat = _student_seat(game)
    pins = game.session_runtime.pins or {}
    pin = enabled_pin(pins)
    if owner is None or seat is None or pin is None:
        return False
    stored = await games_service.fact_set(game_id, seat[0])
    fact_set_id = uuid.UUID(stored.id)
    if await _stored_narration(fact_set_id) is not None:
        return False
    facts = stored.facts
    templates = await _templates(pins)
    own = code_output(facts)
    if own is None:
        # No moments (a Replay too short for ten own Orders): nothing to connect, no call.
        return await _store(fact_set_id, owner[0], "", False, None)
    code = code_text(facts, templates) or ""
    scope = ai_budget.BudgetScope.class_session(
        game.class_session_id,
        effort_level=pin.get("effort_level"),
        model_config_id=pin["model_config_id"],
    )
    worded = await ai_text.worded(
        PURPOSE,
        scope,
        gateway.Inputs(
            values={
                "role": str(facts.seat.role),
                "facts": _fact_lines(facts),
                "templates": "\n".join(templates.lines(narration_rules.NARRATION_TEMPLATES)),
                "max_sentences": narration_rules.MAX_SENTENCES,
            },
            caller={
                "game_id": uuid.UUID(game_id),
                "seat_id": uuid.UUID(seat[0]),
                "fact_set_id": fact_set_id,
            },
            mock_answer=own,
        ),
        narration_rules.AiTextOutput,
        validate=_validator(facts, templates),
        fallback=lambda: code,
    )
    return await _store(fact_set_id, owner[0], worded.text, worded.ai_generated, worded.llm_call_id)


async def _store(
    fact_set_id: uuid.UUID,
    user_id: uuid.UUID,
    text: str,
    ai_generated: bool,
    llm_call_id: uuid.UUID | None,
) -> bool:
    """Store the line once (`replay.store_narration`); a waiting walkthrough reads again on
    `user:<id>` (AD-8). False, storing nothing, when it is stored already."""
    async with get_sessionmaker().begin() as s:
        result = await s.execute(
            insert(replay_narrations)
            .values(
                fact_set_id=fact_set_id,
                text=text,
                ai_generated=ai_generated,
                llm_call_id=llm_call_id,
            )
            .on_conflict_do_nothing(index_elements=[replay_narrations.c.fact_set_id])
            .returning(replay_narrations.c.fact_set_id)
        )
        if result.first() is None:
            return False
        await events.emit(s, "user", str(user_id))
    log.info("replay_walkthrough_stored", ai_generated=ai_generated)
    return True


def _run(log_rows: tuple, role: str) -> list[WalkthroughWeekOut]:
    own = sorted((row for row in log_rows if str(row.role) == role), key=lambda row: row.week)
    return [
        WalkthroughWeekOut(
            week=row.week,
            net_inventory=row.state_seen.net_inventory,
            order=row.order,
            total_cost=row.state_seen.total_cost,
        )
        for row in own
    ]


def _role_total(facts: FactSet, role: str) -> Any:
    return next(each.total_cost for each in facts.chain.by_role if str(each.role) == role)


async def _moments(
    stored: games_service.StoredFactSet, pins: object, mostly_ai: bool
) -> list[WalkthroughMomentOut]:
    """The shown moments, rendered with the moment templates the Class session pinned and the
    pattern names of the version the facts were built with (as the Debrief's step 4)."""
    _, templates = await content.moment_templates(
        content.pinned_version(pins, content.Kind.MOMENT_TEMPLATES)
    )
    _, patterns = await content.detected_patterns(stored.patterns_version)
    rendered = {m.id: m for m in moment_text.render(stored.facts, templates, patterns).moments}
    return [
        WalkthroughMomentOut(
            id=moment.id,
            week=moment.week,
            order=moment.order,
            heading=rendered[moment.id].heading.text,
            reckoning=rendered[moment.id].reckoning.text,
            later=rendered[moment.id].later.text,
            patterns=[text.text for text in rendered[moment.id].patterns],
        )
        for moment in shown_moments(stored.facts, mostly_ai)
    ]


async def _recorded(game_id: uuid.UUID) -> Any:
    async with get_sessionmaker()() as s:
        return (
            await s.execute(
                select(replay_walkthroughs).where(replay_walkthroughs.c.replay_game_id == game_id)
            )
        ).one_or_none()


async def _pending_for(game_id: uuid.UUID, fact_set_id: uuid.UUID) -> int | None:
    """Seconds left to wait for the job's line: None when it is stored or the wait limit since
    the finish has passed (both database time, Issue #63)."""
    if await _stored_narration(fact_set_id) is not None:
        return None
    wait = timedelta(seconds=get_settings().replay_walkthrough_wait_seconds)
    async with get_sessionmaker()() as s:
        finished = await games_service.finished_at(s, game_id)
        now = await games_service.database_now(s)
    if finished is None:
        return None
    left = finished + wait - now
    return max(1, int(left.total_seconds() + 0.999)) if left > timedelta(0) else None


async def walkthrough(user: authz.Principal, game_id: str) -> ReplayWalkthroughOut | None:
    """The Student's walkthrough of their Replay, or None when `game_id` is not their Replay (the
    route's 403, FR-5, AD-12). Raises `Unavailable` for a closed or unfinished Replay and
    `games_service.ViewError` when a facts set cannot be built."""
    try:
        game_uuid = uuid.UUID(game_id)
    except ValueError:
        return None
    async with get_sessionmaker()() as s:
        owner = await repo.replay_owner(s, game_uuid)
    if owner is None or owner[0] != user.id:
        return None
    user_id, class_session_id = owner
    game = await games_service.get_game(game_id)
    seat = _student_seat(game) if game is not None else None
    if game is None or seat is None:
        return None
    if game.end_reason is not None:
        raise Unavailable("replay_closed")
    if game.lifecycle != "finished":
        raise Unavailable("replay_not_finished")
    role = seat[1]
    pins = game.session_runtime.pins if game.session_runtime else None
    replay_facts = await games_service.fact_set(game_id, seat[0])
    found = await _recorded(game_uuid)
    if found is None:
        pending = (
            await _pending_for(game_uuid, uuid.UUID(replay_facts.id))
            if enabled_pin(pins) is not None
            else None
        )
        if pending is not None:
            return ReplayWalkthroughOut(
                game_id=game_uuid, role=Role(role), state="pending", retry_after_seconds=pending
            )
        found = await _record(user_id, class_session_id, game_uuid, role, replay_facts, pins)
        if found is None:
            return None
    compared = await games_service.fact_set(str(found.compared_game_id), role)
    if compared.id != str(found.compared_fact_set_id):
        raise RuntimeError(f"the walkthrough of {game_id} cites another facts set")
    mostly_ai = compared.facts.seat.sm_excluded
    replay_log = await games_service.decision_log(game_id)
    class_log = await games_service.decision_log(str(found.compared_game_id))
    class_game = await games_service.get_game(str(found.compared_game_id))
    narration = (
        WalkthroughTextOut(
            text=found.narration_text,
            ai_generated=found.narration_ai_generated,
            llm_call_id=found.narration_llm_call_id,
        )
        if found.narration_text
        else None
    )
    return ReplayWalkthroughOut(
        game_id=game_uuid,
        role=Role(role),
        state="ready",
        replay=WalkthroughRunOut(
            weeks=_run(replay_log, role), total_cost=_role_total(replay_facts.facts, role)
        ),
        class_game=(
            None
            if mostly_ai
            else WalkthroughClassGameOut(
                weeks=_run(class_log, role),
                total_cost=_role_total(compared.facts, role),
                game_number=class_game.game_number if class_game else None,
            )
        ),
        mostly_ai=mostly_ai,
        moments=await _moments(replay_facts, pins, mostly_ai),
        narration=narration,
    )


async def _record(
    user_id: uuid.UUID,
    class_session_id: uuid.UUID,
    game_id: uuid.UUID,
    role: str,
    replay_facts: games_service.StoredFactSet,
    pins: object,
) -> Any:
    """Store the walkthrough at the Student's first ready view (`replay.record_walkthrough`):
    the game compared with (`games.service.student_game`), both facts sets, and the line shown
    now: the job's when stored, else the code's. The compared Seat is the Replay's Role, the Role
    the Replay was made in (Story 10.3), the same one every later view reads. A view at the same
    moment finds the first one's row. None when the Student has no game of their own in the
    Class session."""
    async with get_sessionmaker()() as s:
        own = await games_service.student_game(s, user_id, class_session_id)
    if own is None:
        return None
    compared = await games_service.fact_set(str(own.game_id), role)
    line = await _stored_narration(uuid.UUID(replay_facts.id))
    if line is None:
        code = code_text(replay_facts.facts, await _templates(pins))
        line = WalkthroughTextOut(text=code) if code else None
    async with get_sessionmaker().begin() as s:
        await s.execute(
            insert(replay_walkthroughs)
            .values(
                replay_game_id=game_id,
                user_id=user_id,
                class_session_id=class_session_id,
                replay_fact_set_id=uuid.UUID(replay_facts.id),
                compared_game_id=own.game_id,
                compared_fact_set_id=uuid.UUID(compared.id),
                narration_text=line.text if line and line.text else None,
                narration_ai_generated=bool(line and line.text and line.ai_generated),
                narration_llm_call_id=line.llm_call_id if line and line.text else None,
            )
            .on_conflict_do_nothing(index_elements=[replay_walkthroughs.c.replay_game_id])
        )
    return await _recorded(game_id)


@dataclass(frozen=True)
class ReplayReport:
    """What the Student report documents of the Replay (Story 13.10, FR-58, FR-50, UX-DR70):
    `finished` (played to its last Uke), `closed` (ended at the Test deadline, Story 10.6) or
    `open`; the Student's Role and the Replay's own settings (its scenario as drawn for them); the
    Uker played; the Replay's run with its Totalkostnad; and, for a finished Replay, the Class
    game it is set beside as the walkthrough sets it (None when that game was played mostly by AI
    players, `mostly_ai`, or cannot be read)."""

    state: Literal["finished", "closed", "open"]
    role: str
    settings: GameSettings
    replay: WalkthroughRunOut
    class_game: WalkthroughClassGameOut | None
    mostly_ai: bool


def _total(weeks: list[WalkthroughWeekOut]) -> Any:
    """The last Uke's «Kostnad så langt»: the run's Totalkostnad (0 before the first Order)."""
    return weeks[-1].total_cost if weeks else 0


async def _compared(
    user_id: uuid.UUID, class_session_id: uuid.UUID, game_id: uuid.UUID, role: str
) -> tuple[WalkthroughClassGameOut | None, bool]:
    """The Class game the walkthrough sets the Replay beside: the one its record names, else
    `games.service.student_game` (as `_record` would choose it); and whether it was played mostly
    by AI players. (None, False) when there is none or it has no facts set yet."""
    found = await _recorded(game_id)
    if found is not None:
        compared_id = found.compared_game_id
    else:
        async with get_sessionmaker()() as s:
            own = await games_service.student_game(s, user_id, class_session_id)
        if own is None:
            return None, False
        compared_id = own.game_id
    try:
        compared = await games_service.fact_set(str(compared_id), role)
    except games_service.ViewError:
        return None, False
    if compared.facts.seat.sm_excluded:
        return None, True
    weeks = _run(await games_service.decision_log(str(compared_id)), role)
    class_game = await games_service.get_game(str(compared_id))
    return (
        WalkthroughClassGameOut(
            weeks=weeks,
            total_cost=_total(weeks),
            game_number=class_game.game_number if class_game else None,
        ),
        False,
    )


async def report(user_id: uuid.UUID, class_session_id: uuid.UUID) -> ReplayReport | None:
    """The Student's Replay for their Student report, or None when they have none. Takes ids
    only: the `reports-single` job calls it after the api's policy allowed the download (AD-12,
    AD-18). Reads the Student's own Replay and own Class game only."""
    async with get_sessionmaker()() as s:
        game_id = await repo.replay_game(s, user_id, class_session_id)
    if game_id is None:
        return None
    game = await games_service.get_game(str(game_id))
    seat = _student_seat(game) if game is not None else None
    if game is None or seat is None or game.settings is None:
        return None
    role = seat[1]
    if game.end_reason is not None:
        state: Literal["finished", "closed", "open"] = "closed"
    elif game.lifecycle == "finished":
        state = "finished"
    else:
        state = "open"
    weeks = _run(await games_service.decision_log(str(game_id)), role)
    class_game, mostly_ai = (
        await _compared(user_id, class_session_id, game_id, role)
        if state == "finished"
        else (None, False)
    )
    return ReplayReport(
        state=state,
        role=role,
        settings=game.settings,
        replay=WalkthroughRunOut(weeks=weeks, total_cost=_total(weeks)),
        class_game=class_game,
        mostly_ai=mostly_ai,
    )
