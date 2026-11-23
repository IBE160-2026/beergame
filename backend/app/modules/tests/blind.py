"""Blind human scoring of a Control test (Story 12.9, FR-82, AD-12, AD-27).

The Admin names scorers among the existing Users for one Control test (`name_scorer`,
`remove_scorer`, audited). After the Control test's Test deadline a named scorer reads its
answers to score (`answers`): one entry per long-answer and Adapted item of each closed attempt
whose saved text is not blank, numbered «Svar N» (grouped by question, ordered within by a keyed
hash of the answer id, which is also the only handle scorers get: `ref`), never with a name, an
e-mail address, a user id, an attempt id or the answer id itself (a UUIDv7 carries its time).
An answer (`answer`) shows the question, the original text, an Adapted item's facts and the
pinned Scoring guide entry with its criteria and five-step scale; the AI's step for it is
included only once the reader's own score of that answer is submitted (`submit`, once:
`HumanScoreExists` for a second one, and `human_scores` has no update path).

Who reads is decided by `platform/authz`: a named scorer (`control_tests_scored_by`) or the Admin
(`control_tests.manage`), who reads without scoring unless named too; each read by a User with
the Admin role is an audit row. Everyone else gets None (403), whether or not the Control test or
the answer exists. Blank answers are not listed: the AI scores them 0 by code, so a human score
there compares nothing.

Logs carry ids and codes only, never answer text or a score."""

import hashlib
import hmac
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assessment import service as assessment
from app.modules.content import service as content
from app.modules.content.schemas import QuestionSet
from app.modules.identity import service as identity
from app.modules.sessions import service as sessions
from app.modules.tests import assessed, guide
from app.modules.tests.adapted import ADAPTED
from app.modules.tests.models import test_answers, test_attempts
from app.modules.tests.schemas import (
    AiStepOut,
    MyScoringOut,
    OwnScoreOut,
    ScaleStepOut,
    ScorerOut,
    ScorersOut,
    ScoringCriterionOut,
    ScoringEntryOut,
    ScoringFactOut,
    ScoringItemOut,
    ScoringListOut,
    ScoringTestOut,
)
from app.platform import audit, authz
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

__all__ = [
    "ANSWERS_READ",
    "GUIDE_CHECKED",
    "SCORER_NAMED",
    "SCORER_REMOVED",
    "AnswerNotFound",
    "ControlTestNotFound",
    "HumanScoreExists",
    "ScorerRefused",
    "answer",
    "answers",
    "entries",
    "my_tests",
    "open_attempts",
    "name_scorer",
    "remove_scorer",
    "scorers",
    "submit",
]

log = structlog.get_logger(__name__)

SCORER_NAMED = "control_test.scorer_named"
SCORER_REMOVED = "control_test.scorer_removed"
ANSWERS_READ = "control_test.answers_read"
"""The audit actions of Story 12.9 (AD-15): ids only."""
GUIDE_CHECKED = "control_test.checked"
"""Story 12.10: the last score (or a removal) made the Control test complete and its Scoring
guide version checked for its model config (ids only; `first` False when the pair was checked by
another Control test before)."""


class AnswerNotFound(Exception):
    """404 `not_found`: a reader of the Control test asked for an answer it has no entry for (not
    one of its answers, blank, its attempt not closed, or before the Test deadline)."""


class HumanScoreExists(Exception):
    """409 `human_score_exists`: the scorer has scored this answer already; a score is never
    changed."""


class ControlTestNotFound(Exception):
    """404 `not_found`: no Control test has that id."""


class ScorerRefused(Exception):
    """422 `invalid_request` with `fields.email`: `unknown` (no active User has the address) or
    `test_student` (a test student never scores)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.fields = {"email": reason}


@dataclass(frozen=True)
class _Entry:
    answer_id: uuid.UUID
    attempt_id: uuid.UUID
    item_id: str
    type: str
    question: str
    frozen: Mapping[str, Any]
    words: int = 0
    """The answer's word count (Story 12.10: agreement by answer length)."""
    number: int = 0

    @property
    def ref(self) -> str:
        return _ref(self.answer_id)


@dataclass(frozen=True)
class _Reader:
    test: sessions.ControlTestFacts
    scorer: bool
    admin: bool


def _test_out(facts: sessions.ControlTestFacts, now: datetime) -> ScoringTestOut:
    return ScoringTestOut(
        id=facts.id,
        name=facts.name,
        test_deadline=facts.test_deadline,
        open=now >= facts.test_deadline,
    )


def _ref(answer_id: uuid.UUID) -> str:
    """The answer as scorers know it: a keyed hash of its id (the id itself is a UUIDv7, which
    carries the time it was first saved and so would link one student's answers). It also orders
    the answers within a question, saying nothing about who wrote them or when."""
    key = get_settings().jwt_secret.encode()
    keyed = hmac.new(key, b"control-test-answer:" + answer_id.bytes, hashlib.sha256)
    return keyed.hexdigest()[:32]


async def _entries(s: AsyncSession, class_session_id: uuid.UUID) -> list[_Entry]:
    """Every long-answer and Adapted answer with text of the Control test's closed attempts,
    numbered from 1: by item id, then by the hash of the answer id."""
    attempts = {
        row["id"]: row
        for row in (
            await s.execute(
                select(
                    test_attempts.c.id,
                    test_attempts.c["items"],
                    test_attempts.c.question_set_version,
                ).where(
                    test_attempts.c.class_session_id == class_session_id,
                    test_attempts.c.closed_at.is_not(None),
                )
            )
        ).mappings()
    }
    if not attempts:
        return []
    saved = (
        await s.execute(
            select(
                test_answers.c.id,
                test_answers.c.attempt_id,
                test_answers.c.item_id,
                test_answers.c.value,
            ).where(test_answers.c.attempt_id.in_(list(attempts)))
        )
    ).all()
    sets: dict[int, QuestionSet] = {}
    found: list[_Entry] = []
    for row in saved:
        if not isinstance(row.value, str) or not row.value.strip():
            continue
        attempt = attempts[row.attempt_id]
        frozen = next((each for each in attempt["items"] if each["id"] == row.item_id), None)
        if frozen is None or frozen["type"] not in assessed.AI_TYPES:
            continue
        if frozen["type"] == ADAPTED:
            question = str(frozen["text"]["text"])
        else:
            version = attempt["question_set_version"]
            if version not in sets:
                sets[version] = await content.get(content.Kind.QUESTION_SET, version)
            by_id = {i.id: i for i in (*sets[version].items, *sets[version].replacements)}
            item = by_id.get(row.item_id)
            question = item.title if item is not None else ""
        found.append(
            _Entry(
                row.id,
                row.attempt_id,
                row.item_id,
                frozen["type"],
                question,
                frozen,
                len(row.value.split()),
            )
        )
    found.sort(key=lambda each: (each.item_id, each.ref))
    return [
        _Entry(e.answer_id, e.attempt_id, e.item_id, e.type, e.question, e.frozen, e.words, number)
        for number, e in enumerate(found, start=1)
    ]


async def entries(s: AsyncSession, class_session_id: uuid.UUID) -> list[_Entry]:
    """The Control test's listed answers, numbered (Story 12.10's results read the same list)."""
    return await _entries(s, class_session_id)


async def open_attempts(s: AsyncSession, class_session_id: uuid.UUID) -> int:
    """How many attempts of the Control test are still open (an extension, a timed sitting): its
    answers are not listed yet, so the Control test is not complete (Story 12.10)."""
    found = await s.scalar(
        select(func.count()).where(
            test_attempts.c.class_session_id == class_session_id,
            test_attempts.c.closed_at.is_(None),
        )
    )
    return int(found or 0)


async def _reader(
    s: AsyncSession, user: authz.Principal, class_session_id: uuid.UUID
) -> _Reader | None:
    """The Control test and how `user` may read it, or None when they may not (or it is no
    Control test): the `control_test_answers.read` scope of `platform/authz`."""
    named = set(await s.scalars(authz.control_tests_scored_by(user)))
    scorer = class_session_id in named
    if not authz.reads_control_test_answers(user, scorer):
        return None
    facts = (await sessions.control_test_facts(s, [class_session_id])).get(class_session_id)
    if facts is None:
        return None
    return _Reader(facts, scorer, authz.can(user, "control_tests.manage"))


async def _audit_read(
    s: AsyncSession,
    reader: _Reader,
    user: authz.Principal,
    now: datetime,
    entry: _Entry | None = None,
) -> None:
    """One audit row for each read of a Control test's answers by a User with the Admin role."""
    if not reader.admin:
        return
    target: dict[str, Any] = {"class_session_id": reader.test.id}
    if entry is not None:
        target["answer_id"] = entry.answer_id
    await audit.record(s, user.id, ANSWERS_READ, target, {}, now)


async def my_tests(user: authz.Principal, now: datetime) -> MyScoringOut:
    """The Control tests `user` is a named scorer of, by name (none: their home shows no Lenke)."""
    async with get_sessionmaker()() as s:
        named = list(await s.scalars(authz.control_tests_scored_by(user)))
        facts = await sessions.control_test_facts(s, named)
    tests = [_test_out(each, now) for each in facts.values()]
    tests.sort(key=lambda each: (each.name.casefold(), str(each.id)))
    return MyScoringOut(tests=tests)


async def answers(
    user: authz.Principal, class_session_id: uuid.UUID, now: datetime
) -> ScoringListOut | None:
    """The Control test's answers to score, each marked scored or not by the reader; none before
    its Test deadline. None (403) for everyone but its scorers and the Admin."""
    async with get_sessionmaker().begin() as s:
        reader = await _reader(s, user, class_session_id)
        if reader is None:
            return None
        await _audit_read(s, reader, user, now)
        test = _test_out(reader.test, now)
        entries = await _entries(s, class_session_id) if test.open else []
        own = await assessment.human_scores_by(s, user.id, [e.answer_id for e in entries])
    return ScoringListOut(
        test=test,
        can_score=reader.scorer,
        entries=[
            ScoringEntryOut(
                ref=e.ref,
                number=e.number,
                type=e.type,  # type: ignore[arg-type]
                question=e.question,
                scored=e.answer_id in own,
            )
            for e in entries
        ],
    )


async def _item(
    s: AsyncSession, reader: _Reader, user: authz.Principal, entry: _Entry, now: datetime
) -> ScoringItemOut:
    """The answer as its reader sees it, read in `s`."""
    own = (await assessment.human_scores_by(s, user.id, [entry.answer_id])).get(entry.answer_id)
    ai_step: int | None = None
    if own is not None:
        record = await assessment.assessment_of(s, entry.attempt_id)
        ai_step = None if record is None else record.scores.get(entry.item_id)
    found = await assessed.read_for_assessment(entry.attempt_id)
    if found is None:  # pragma: no cover - the attempt was just read in `s`
        raise AnswerNotFound
    item = next(each for each in found.items if each.item_id == entry.item_id)
    labels = dict(found.scale)
    facts = await assessed.adapted_facts(entry.frozen) if entry.type == ADAPTED else []
    return ScoringItemOut(
        test=_test_out(reader.test, now),
        ref=entry.ref,
        number=entry.number,
        type=entry.type,  # type: ignore[arg-type]
        question=entry.question,
        answer=item.answer or "",
        facts=[ScoringFactOut(name=name, value=value) for name, value in facts],
        guide_title=item.guide_title,
        guide_text=item.guide_text,
        criteria=[ScoringCriterionOut(code=c, weight=w, text=t) for c, w, t in item.criteria],
        scale=[ScaleStepOut(step=step, label=label) for step, label in found.scale],
        can_score=reader.scorer,
        own_score=None
        if own is None
        else OwnScoreOut(score=own.score, submitted_at=own.submitted_at),
        ai=None if ai_step is None else AiStepOut(step=ai_step, label=labels.get(ai_step)),
    )


async def _entry(s: AsyncSession, reader: _Reader, ref: str, now: datetime) -> _Entry:
    if now < reader.test.test_deadline:
        raise AnswerNotFound
    entry = next((e for e in await _entries(s, reader.test.id) if e.ref == ref), None)
    if entry is None:
        raise AnswerNotFound
    return entry


async def answer(
    user: authz.Principal, class_session_id: uuid.UUID, ref: str, now: datetime
) -> ScoringItemOut | None:
    """One answer to score; the AI's step only after the reader's own score of it (AD-27). None
    (403) for everyone but the Control test's scorers and the Admin; raises `AnswerNotFound`."""
    async with get_sessionmaker().begin() as s:
        reader = await _reader(s, user, class_session_id)
        if reader is None:
            return None
        entry = await _entry(s, reader, ref, now)
        await _audit_read(s, reader, user, now, entry)
        return await _item(s, reader, user, entry, now)


async def _audit_complete(
    s: AsyncSession,
    user: authz.Principal,
    test: sessions.ControlTestFacts,
    scoring_guide_id: uuid.UUID,
    recorded: assessment.RecordedScore,
    now: datetime,
) -> None:
    """One `control_test.checked` audit row when the Control test became complete (`first`:
    whether it wrote the pair's check, False when another Control test checked it before)."""
    if not recorded.complete:
        return
    await audit.record(
        s,
        user.id,
        GUIDE_CHECKED,
        {"class_session_id": test.id},
        {
            "scoring_guide_id": str(scoring_guide_id),
            "model_config_id": str(test.model_config_id),
            "first": recorded.checked,
        },
        now,
    )
    log.info(
        "scoring_guide_checked",
        class_session_id=str(test.id),
        scoring_guide_id=str(scoring_guide_id),
        model_config_id=str(test.model_config_id),
        first=recorded.checked,
    )


async def submit(
    user: authz.Principal,
    class_session_id: uuid.UUID,
    ref: str,
    score: int,
    now: datetime,
) -> ScoringItemOut | None:
    """The scorer's score of one answer, stored once (`human_scores`); answers the item, now with
    the AI's step. None (403) for everyone but the Control test's named scorers (the Admin too,
    unless named); raises `AnswerNotFound` and `HumanScoreExists` (nothing written)."""
    async with get_sessionmaker().begin() as s:
        reader = await _reader(s, user, class_session_id)
        if reader is None or not reader.scorer:
            return None
        if now < reader.test.test_deadline:
            raise AnswerNotFound
        # The scorer rows first, then the answers: a concurrent last score waits here and then
        # reads this one.
        named = await assessment.hold_scorers(s, class_session_id)
        listed = await _entries(s, class_session_id)
        entry = next((e for e in listed if e.ref == ref), None)
        if entry is None:
            raise AnswerNotFound
        answer_id = entry.answer_id
        in_force = await guide.in_force(s, class_session_id)
        try:
            recorded = await assessment.record_human_score(
                s,
                class_session_id,
                answer_id,
                user.id,
                score,
                named=named,
                listed=[e.answer_id for e in listed],
                settled=await open_attempts(s, class_session_id) == 0,
                scoring_guide_id=in_force.record.id,
                model_config_id=reader.test.model_config_id,
                now=now,
            )
        except assessment.ScorerNotNamed:
            return None
        if not recorded.stored:
            log.info(
                "human_score_refused", answer_id=str(answer_id), error_code="human_score_exists"
            )
            raise HumanScoreExists
        log.info(
            "human_score_submitted",
            class_session_id=str(class_session_id),
            answer_id=str(answer_id),
        )
        await _audit_complete(s, user, reader.test, in_force.record.id, recorded, now)
        # The answer it gives back is a read too: an Admin who is a named scorer is audited.
        await _audit_read(s, reader, user, now, entry)
        return await _item(s, reader, user, entry, now)


# Naming the scorers: Admin-område → «Kontrolltest» (`control_tests.manage`, checked by the route).


async def _scorers_out(
    s: AsyncSession, facts: sessions.ControlTestFacts, now: datetime
) -> ScorersOut:
    named = await assessment.scorers_of(s, facts.id)
    ids = [user_id for user_id, _ in named]
    people = await identity.people(s, ids)
    entries = await _entries(s, facts.id)
    counts = await assessment.score_counts(s, ids, [e.answer_id for e in entries])
    return ScorersOut(
        test=_test_out(facts, now),
        answers=len(entries),
        scorers=[
            ScorerOut(
                user_id=user_id,
                name=people[user_id].name if user_id in people else "",
                email=people[user_id].email if user_id in people else "",
                named_at=named_at,
                scored=counts.get(user_id, 0),
            )
            for user_id, named_at in named
        ],
    )


async def _control_test(s: AsyncSession, class_session_id: uuid.UUID) -> sessions.ControlTestFacts:
    facts = (await sessions.control_test_facts(s, [class_session_id])).get(class_session_id)
    if facts is None:
        raise ControlTestNotFound
    return facts


async def scorers(class_session_id: uuid.UUID, now: datetime) -> ScorersOut:
    """The Control test's named scorers with how many answers each has scored; raises
    `ControlTestNotFound`."""
    async with get_sessionmaker()() as s:
        return await _scorers_out(s, await _control_test(s, class_session_id), now)


async def name_scorer(
    user: authz.Principal, class_session_id: uuid.UUID, address: str, now: datetime
) -> ScorersOut:
    """Name the active User of `address` a scorer of the Control test, with one audit row;
    naming one already named writes nothing. Raises `ControlTestNotFound` and `ScorerRefused`."""
    async with get_sessionmaker().begin() as s:
        facts = await _control_test(s, class_session_id)
        found = await identity.active_user_for_email(s, address.strip())
        if found is None:
            log.info("scorer_refused", class_session_id=str(class_session_id), error_code="unknown")
            raise ScorerRefused("unknown")
        if await identity.is_test_student(s, found.id):
            log.info(
                "scorer_refused", class_session_id=str(class_session_id), error_code="test_student"
            )
            raise ScorerRefused("test_student")
        if await assessment.name_scorer(s, class_session_id, found.id, named_by=user.id, now=now):
            await audit.record(
                s,
                user.id,
                SCORER_NAMED,
                {"class_session_id": class_session_id, "user_id": found.id},
                {},
                now,
            )
            log.info("scorer_named", class_session_id=str(class_session_id), user_id=str(found.id))
        return await _scorers_out(s, facts, now)


async def remove_scorer(
    user: authz.Principal, class_session_id: uuid.UUID, user_id: uuid.UUID, now: datetime
) -> ScorersOut:
    """Take a scorer off the Control test, with one audit row; their submitted scores stay.
    Removing one not named writes nothing. Raises `ControlTestNotFound`."""
    async with get_sessionmaker().begin() as s:
        facts = await _control_test(s, class_session_id)
        await assessment.hold_scorers(s, class_session_id)
        if await assessment.remove_scorer(s, class_session_id, user_id):
            await audit.record(
                s,
                user.id,
                SCORER_REMOVED,
                {"class_session_id": class_session_id, "user_id": user_id},
                {},
                now,
            )
            log.info("scorer_removed", class_session_id=str(class_session_id), user_id=str(user_id))
            # The scorers left may now have scored everything (Story 12.10).
            if now >= facts.test_deadline:
                in_force = await guide.in_force(s, class_session_id)
                settled = await assessment.settle_after_removal(
                    s,
                    class_session_id,
                    listed=[e.answer_id for e in await _entries(s, class_session_id)],
                    settled=await open_attempts(s, class_session_id) == 0,
                    scoring_guide_id=in_force.record.id,
                    model_config_id=facts.model_config_id,
                    now=now,
                )
                await _audit_complete(s, user, facts, in_force.record.id, settled, now)
        return await _scorers_out(s, facts, now)
