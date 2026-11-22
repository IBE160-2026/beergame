"""The Lecturer's preview of the Adapted item templates, filled for a sample Student (Story 11.9,
FR-53, AD-7, AD-12, UX-DR70).

The sample is one static facts set shipped in the repo (`files/sample_facts.json`): the Retailer
Seat of Story 9.1's golden Takeover Game, where a Student placed the Orders of Weeks 3-14 before a
Rule-based player took over. It is built by `analysis.facts` from that Game's `seat_weeks` rows
(the fixture `tests/golden/facts/takeover-seat-weeks.json`), with the Detected patterns of
version 1 and no «Simulert, samme kunder» rows; a test rebuilds it from the fixture and compares,
so it cannot drift from `analysis.facts` (rewrite it with `UPDATE_GOLDEN=1`). Every template
reads this one set, whichever Game (`game` or `replay`) it names.

Each template of the version the Class session pins (the lock's pin, the latest version before
the lock) is filled by `analysis.adapted.fill`, the code renderer of Story 11.7, and weighted by
its share of the Adapted total in force (the pinned selection, else the selection «Spørsmål og
vekter» shows). The preview reads content and the selection only: no Game row, no stored facts
set (`games.facts`), no LLM call, no write. It is for the Class's staff (`class_sessions.read`);
every other caller gets None (403)."""

import json
import uuid
from functools import cache
from pathlib import Path

from app.analysis.adapted import AdaptedTemplates, apportion, fill
from app.analysis.facts import FactSet
from app.modules.content import service as content
from app.modules.sessions import service as sessions
from app.modules.tests import selection
from app.modules.tests.schemas import AdaptedPreviewItemOut, AdaptedPreviewOut
from app.platform import authz
from app.platform.db import get_sessionmaker

__all__ = ["SAMPLE", "SAMPLE_ROLE", "preview_items", "read_preview", "sample"]

SAMPLE = Path(__file__).parent / "files" / "sample_facts.json"
"""The sample Student's facts set: `{"patterns_version": n, "facts": <FactSet>}`."""
SAMPLE_ROLE = "retailer"
"""The sample Student's Role in the Takeover Game."""


@cache
def sample() -> tuple[int, FactSet]:
    """The shipped sample facts set and the Detected pattern version it was built with."""
    found = json.loads(SAMPLE.read_text(encoding="utf-8"))
    return int(found["patterns_version"]), FactSet.model_validate(found["facts"])


def preview_items(
    templates: AdaptedTemplates, facts: FactSet, pattern_names: dict[str, str], total: int
) -> list[AdaptedPreviewItemOut]:
    """Each template filled from `facts` with its weight of `total`; text None for a template
    whose fact the set does not hold."""
    weights = apportion(total, [template.share for template in templates.templates])
    items = []
    for template, weight in zip(templates.templates, weights, strict=True):
        filled = fill(template, facts, pattern_names)
        items.append(
            AdaptedPreviewItemOut(
                id=template.id,
                source=template.source,
                fact=template.fact,
                weight=weight,
                text=filled.text if filled is not None else None,
            )
        )
    return items


async def read_preview(
    user: authz.Principal, class_session_id: uuid.UUID
) -> AdaptedPreviewOut | None:
    """The preview for the Class's owners and Assistant lecturers; None for every other caller
    and for a session that does not exist alike (FR-5)."""
    found = await sessions.question_set_session(user, class_session_id)
    if found is None:
        return None
    pinned_version = content.pinned_version(found.pins, content.Kind.ADAPTED_TEMPLATES)
    version, templates = await content.adapted_templates(pinned_version)
    pinned = selection.pinned_selection(found.pins)
    if pinned is not None:
        total = pinned.adapted_weight
    else:
        async with get_sessionmaker()() as s:
            in_force, _, _ = await selection.effective(s, class_session_id)
        total = in_force.adapted_weight
    patterns_version, facts = sample()
    names: dict[str, str] = {}
    if any(template.fact == "pattern" for template in templates.templates):
        _, patterns = await content.detected_patterns(patterns_version)
        names = {pattern.id: pattern.name for pattern in patterns.patterns}
    return AdaptedPreviewOut(
        version=version,
        draft=templates.status == "draft",
        pinned=pinned_version is not None,
        adapted_weight=total,
        items=preview_items(templates, facts, names, total),
    )
