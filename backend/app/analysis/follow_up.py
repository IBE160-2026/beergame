"""Bounded follow-up questions about a Student's own Game (Story 9.15, FR-45, AD-7).

The LLM's answer (`FollowUpOutput`) is either a decline (`decline` true, no sentences: the
question is outside the Game and its concepts, and the Student sees a fixed line) or one to
`MAX_SENTENCES` hint sentences: ids of the pinned version's hint templates (`HINT_TEMPLATES`)
with the facts each points to. A hint says where to look (a Uke, a row, Varer på vei, the cost of
the following Uker) and fills only the cited facts' numbers, never a worked answer.
`validate_follow_up` accepts only those two shapes and checks the hints with Story 9.14's
`validate_ai_text`; code renders every word.

`mock_output` is what the deterministic mock answers (AD-17): a decline for a question that names
no game word, else one row hint on the Seat's first moment.

Pure (AD-1): stdlib, pydantic and `app.analysis` only."""

import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.analysis.facts import FactSet
from app.analysis.narration import (
    HINT_TEMPLATES,
    MAX_SENTENCES,
    AiSentence,
    AiTextOutput,
    NarrationTemplates,
    Verdict,
    validate_ai_text,
)

__all__ = [
    "GAME_WORDS",
    "QUESTION_MAX",
    "FollowUpOutput",
    "FollowUpVerdict",
    "mock_output",
    "validate_follow_up",
]

_FROZEN = ConfigDict(frozen=True, extra="forbid")

QUESTION_MAX = 500
"""The longest follow-up question, in characters."""

GAME_WORDS = re.compile(
    r"uke|bestil|ordre|lager|kost|varer|på vei|lever|rolle|kjede|spill|etterspør|kunde"
    r"|fabrikk|grossist|distribut|detaljist|butikk|svingn|forsink|mønster",
    re.IGNORECASE,
)
"""The mock's test of whether a question is about the Game (the mock only; a real model judges by
the prompt's rule)."""


class FollowUpOutput(BaseModel):
    """The output schema of a follow-up answer: a decline flag, or hint sentences of template
    ids and fact ids only (AD-7)."""

    model_config = _FROZEN

    decline: bool
    sentences: Annotated[tuple[AiSentence, ...], Field(max_length=MAX_SENTENCES)] = ()


class FollowUpVerdict(BaseModel):
    """`validate_follow_up`'s answer: accepted as a decline, accepted with the rendered hint text,
    or rejected with the reason."""

    model_config = _FROZEN

    accepted: bool
    declined: bool = False
    text: str | None = None
    reason: str | None = None


def validate_follow_up(
    output: FollowUpOutput, fact_set: FactSet, templates: NarrationTemplates
) -> FollowUpVerdict:
    """Accept a decline with no sentences, or one to three hint sentences that `validate_ai_text`
    accepts with the hint templates only (FR-45, AD-7). A decline that also hints, an answer
    with no sentence, a version without hint templates and any narration template are
    rejected."""
    if output.decline:
        if output.sentences:
            return FollowUpVerdict(accepted=False, reason="inconsistent")
        return FollowUpVerdict(accepted=True, declined=True)
    if not output.sentences:
        return FollowUpVerdict(accepted=False, reason="empty")
    if not templates.has_hints():
        return FollowUpVerdict(accepted=False, reason="unknown_template")
    verdict: Verdict = validate_ai_text(
        AiTextOutput(sentences=output.sentences), fact_set, templates, allowed=HINT_TEMPLATES
    )
    if not verdict.accepted:
        return FollowUpVerdict(accepted=False, reason=verdict.reason)
    return FollowUpVerdict(accepted=True, text=verdict.text)


def mock_output(question: str, fact_set: FactSet) -> FollowUpOutput:
    """The deterministic mock's answer (AD-17): a decline when the question names no game word or
    the Seat has no moment to point to, else the row hint on its earliest moment."""
    moments = sorted(fact_set.seat.moments, key=lambda moment: moment.week)
    if not moments or GAME_WORDS.search(question) is None:
        return FollowUpOutput(decline=True)
    return FollowUpOutput(
        decline=False, sentences=(AiSentence(template_id="hint-row", fact_ids=(moments[0].id,)),)
    )
