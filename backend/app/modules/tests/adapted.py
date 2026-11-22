"""The Student's Adapted items, built when they open the Individual test (Story 11.7, FR-53, AD-7,
AD-15, AD-23).

`build` runs in `commands.open_attempt`'s transaction and returns the items that join the frozen
list after the Core items, so opening never waits on a job or an LLM call:

- The Adapted item templates are the version the Class session's lock pinned
  (`pins["adapted_templates"]`), so every Student of the Class session gets the same templates;
  a session locked before that pin existed reads the latest version when each Student opens.
- Each template is filled by `analysis.adapted.fill` from one stored facts set: the Student's
  Seat in their own Class game (`games.service.student_game`, the one way to find it, never a
  query on Class games) or in their Replay (`replay.service.replay_game_of`, the same Role), read
  through `games.service.fact_set` (`games.facts.get_or_create`, AD-7). An item stores its
  `fact_set_id` and fact ids, and its text travels as `{text, ai_generated, llm_call_id}`.
- The items carry the Class session's Adapted total weight between them, split by the templates'
  shares (`analysis.adapted.apportion`).
- A Student with fewer than `MIN_STUDENT_ORDERS` own Orders in their own game (the facts set's
  `decided_by = student` count, AD-15) gets the question set's replacement Core items instead,
  scaled to the same total. So does a Student whose own game, Replay or facts set cannot be read,
  or for whom a template finds no fact: the templates stay the same for everyone who gets them.
- An Adapted total of 0 serves neither.

This module writes no attempt: the caller freezes what `build` returns. A facts set read for the
first time is built and stored by `games.facts.get_or_create` in its own short transaction (AD-7).
No answer text, no fact value and no rendered text is logged."""

import uuid
from collections.abc import Mapping
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.adapted import AdaptedTemplates, apportion, fill
from app.analysis.facts import MIN_STUDENT_ORDERS
from app.modules.content import service as content
from app.modules.content.schemas import QuestionSet
from app.modules.games import service as games
from app.modules.replay import service as replay

__all__ = ["ADAPTED", "build"]

log = structlog.get_logger(__name__)

ADAPTED = "adapted"
"""The type of an Adapted item in the frozen list: answered as a long answer (Story 11.6)."""


async def _sources(
    s: AsyncSession, user_id: uuid.UUID, class_session_id: uuid.UUID
) -> tuple[games.StudentGame | None, uuid.UUID | None]:
    """The Student's own game (`games.service.student_game`, the one way to find it) and their
    Replay Game, read in `s`."""
    own = await games.student_game(s, user_id, class_session_id)
    return own, await replay.replay_game_of(s, user_id, class_session_id)


async def _facts(game_id: uuid.UUID, role: str) -> games.StoredFactSet | None:
    try:
        return await games.fact_set(str(game_id), role)
    except games.ViewError:
        return None


def _replacements(question_set: QuestionSet, total: int, reason: str) -> list[dict[str, Any]]:
    items = question_set.replacements
    weights = apportion(total, [item.weight for item in items])
    return [
        {"id": item.id, "type": item.type, "weight": weight, "replaces": reason}
        for item, weight in zip(items, weights, strict=True)
    ]


async def _pattern_names(stored: games.StoredFactSet) -> dict[str, str]:
    _, patterns = await content.detected_patterns(stored.patterns_version)
    return {pattern.id: pattern.name for pattern in patterns.patterns}


async def _adapted(
    templates_version: int,
    templates: AdaptedTemplates,
    sets: Mapping[str, games.StoredFactSet],
    total: int,
) -> list[dict[str, Any]] | None:
    """The filled Adapted items, or None when a template finds no fact in its set."""
    weights = apportion(total, [template.share for template in templates.templates])
    items = []
    names: dict[str, dict[str, str]] = {}
    for template, weight in zip(templates.templates, weights, strict=True):
        stored = sets[template.source]
        if template.fact == "pattern" and template.source not in names:
            names[template.source] = await _pattern_names(stored)
        filled = fill(template, stored.facts, names.get(template.source, {}))
        if filled is None:
            return None
        items.append(
            {
                "id": template.id,
                "type": ADAPTED,
                "weight": weight,
                "template_version": templates_version,
                "source": template.source,
                "fact": template.fact,
                "fact_set_id": stored.id,
                "fact_ids": list(filled.fact_ids),
                "text": {"text": filled.text, "ai_generated": False, "llm_call_id": None},
            }
        )
    return items


async def build(
    s: AsyncSession,
    user_id: uuid.UUID,
    class_session_id: uuid.UUID,
    pins: Any,
    adapted_weight: int,
    question_set: QuestionSet,
) -> list[dict[str, Any]]:
    """The Student's Adapted items (or the replacement items) for the frozen list, read in `s`,
    the opening transaction; empty when the Adapted total weight is 0."""
    if adapted_weight <= 0:
        return []
    version, templates = await content.adapted_templates(
        content.pinned_version(pins, content.Kind.ADAPTED_TEMPLATES)
    )
    reason: str
    sets: dict[str, games.StoredFactSet] = {}
    own, replay_game = await _sources(s, user_id, class_session_id)
    if own is None:
        reason = "no_game"
    elif (game_facts := await _facts(own.game_id, own.role)) is None:
        reason = "facts_unavailable"
    elif game_facts.facts.seat.student_orders < MIN_STUDENT_ORDERS:
        reason = "few_orders"
    else:
        sets["game"] = game_facts
        needs_replay = any(t.source == "replay" for t in templates.templates)
        replay_facts = None
        if needs_replay and replay_game is not None:
            replay_facts = await _facts(replay_game, own.role)
        if needs_replay and replay_game is None:
            reason = "no_replay"
        elif needs_replay and replay_facts is None:
            reason = "facts_unavailable"
        else:
            if replay_facts is not None:
                sets["replay"] = replay_facts
            items = await _adapted(version, templates, sets, adapted_weight)
            if items is not None:
                log.info(
                    "adapted_items_built",
                    class_session_id=str(class_session_id),
                    templates_version=version,
                    items=len(items),
                    fact_set_ids=sorted({item["fact_set_id"] for item in items}),
                )
                return items
            reason = "unfilled"
    log.info(
        "adapted_items_replaced",
        class_session_id=str(class_session_id),
        user_id=str(user_id),
        reason=reason,
    )
    return _replacements(question_set, adapted_weight, reason)
