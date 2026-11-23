"""The results of a Control test (Story 12.10, FR-82, FR-81, AD-1, AD-12, AD-27).

Admin-område → «Kontrolltest» → «Resultater»: every listed answer (the same list the scorers
read, `blind.entries`) with each named scorer's step and the AI's step side by side, the five
FR-82 measures from `analysis.agreement` (the only source), and whether the Control test is
complete and its pinned Scoring guide version checked for its pinned model config
(`content.is_checked`). Only the Admin reads it (`control_tests.manage`, checked by the route);
each read is an audit row.

Measures use the scores of the currently named scorers (a removed scorer's kept scores are left
out) and only answers with an AI step. While anything is missing they are preliminary; the page
says so. An Admin who is also a named scorer and still has answers to score gets no AI step and
no measures (`withheld`): the AI score stays hidden from a scorer until their own (AD-27).

Logs carry ids and counts only."""

import uuid
from datetime import datetime

import structlog

from app.ai import config as ai_config
from app.analysis.agreement import agreement
from app.modules.assessment import service as assessment
from app.modules.content import service as content
from app.modules.identity import service as identity
from app.modules.sessions import service as sessions
from app.modules.tests import blind, guide
from app.modules.tests.schemas import (
    AgreementOut,
    ControlResultsOut,
    LengthBandOut,
    ResultsConfigOut,
    ResultsGuideOut,
    ResultsRowOut,
    ResultsScorerOut,
    ScoringTestOut,
)
from app.platform import audit, authz
from app.platform.db import get_sessionmaker

__all__ = ["RESULTS_READ", "results"]

log = structlog.get_logger(__name__)

RESULTS_READ = "control_test.results_read"
"""The audit action of each read of a Control test's results (Story 12.10, AD-12): ids only."""


async def results(
    user: authz.Principal, class_session_id: uuid.UUID, now: datetime
) -> ControlResultsOut:
    """The Control test's results for the Admin; raises `blind.ControlTestNotFound` for no Control
    test of that id. Before the Test deadline there are no rows."""
    async with get_sessionmaker().begin() as s:
        found = await sessions.control_test_facts(s, [class_session_id])
        facts = found.get(class_session_id)
        if facts is None:
            raise blind.ControlTestNotFound
        await audit.record(
            s, user.id, RESULTS_READ, {"class_session_id": class_session_id}, {}, now
        )
        in_force = await guide.in_force(s, class_session_id)
        config_id = facts.model_config_id
        checked = await content.is_checked(in_force.record.id, config_id, session=s)
        named = [user_id for user_id, _ in await assessment.scorers_of(s, class_session_id)]
        people = await identity.people(s, named)
        is_open = facts.is_open(now)
        listed = await blind.entries(s, class_session_id) if is_open else []
        still_open = await blind.open_attempts(s, class_session_id, now)
        given = await assessment.scores_of(s, [e.answer_id for e in listed])
        ai_steps: dict[uuid.UUID, int] = {}
        records: dict[uuid.UUID, assessment.AssessmentRecord | None] = {}
        for entry in listed:
            if entry.attempt_id not in records:
                records[entry.attempt_id] = await assessment.assessment_of(s, entry.attempt_id)
            record = records[entry.attempt_id]
            if record is not None and entry.item_id in record.scores:
                ai_steps[entry.answer_id] = record.scores[entry.item_id]
        found_config = await ai_config.get(config_id, session=s) if config_id else None
    owed = sum(1 for e in listed for scorer in named if scorer not in given.get(e.answer_id, {}))
    withheld = user.id in named and any(user.id not in given.get(e.answer_id, {}) for e in listed)
    complete = bool(named) and bool(listed) and still_open == 0 and owed == 0
    rows = [
        ResultsRowOut(
            number=e.number,
            type=e.type,  # type: ignore[arg-type]
            question=e.question,
            words=e.words,
            human=[given.get(e.answer_id, {}).get(scorer) for scorer in named],
            ai=None if withheld else ai_steps.get(e.answer_id),
        )
        for e in listed
    ]
    measures: AgreementOut | None = None
    if listed and not withheld:
        pairs = [
            (e.answer_id, step)
            for e in listed
            for scorer, step in given.get(e.answer_id, {}).items()
            if scorer in named
        ]
        computed = agreement(pairs, ai_steps, words={e.answer_id: e.words for e in listed})
        measures = AgreementOut(
            pairs=computed.pairs,
            exact=computed.exact,
            within_one=computed.within_one,
            offset=computed.offset,
            compression=computed.compression,
            by_length=[
                LengthBandOut(
                    band=band.band,  # type: ignore[arg-type]
                    min_words=band.min_words,
                    max_words=band.max_words,
                    pairs=band.pairs,
                    exact=band.exact,
                    within_one=band.within_one,
                )
                for band in computed.by_length
            ],
        )
    log.info(
        "control_test_results_read",
        class_session_id=str(class_session_id),
        answers=len(listed),
        missing=owed,
        withheld=withheld,
    )
    return ControlResultsOut(
        test=ScoringTestOut(
            id=facts.id, name=facts.name, test_deadline=facts.test_deadline, open=is_open
        ),
        scoring_guide=ResultsGuideOut(
            version=in_force.record.version,
            edited=in_force.record.class_session_id is not None,
        ),
        ai_config=None
        if found_config is None
        else ResultsConfigOut(
            name=found_config.spec.name, model_version=found_config.spec.model_version
        ),
        scorers=[
            ResultsScorerOut(name=people[scorer].name if scorer in people else "")
            for scorer in named
        ],
        rows=rows,
        missing=owed,
        ai_missing=0 if withheld else sum(1 for e in listed if e.answer_id not in ai_steps),
        open_attempts=still_open,
        complete=complete,
        checked=checked,
        withheld=withheld,
        measures=measures,
    )
