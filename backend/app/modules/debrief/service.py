"""What other modules and the routes use of `debrief` (Stories 9.2 to 9.9).

- `open_mine(user, class_session_id)`: the Student's Debrief, opened on first use; raises
  `NotAvailable` with the code the route answers (`debrief_not_open`, `debrief_held`), and None
  for every case the route answers `forbidden` (FR-5).
- `mine(user, debrief_id)`: the same read by the Debrief's id.
- `due_releases(now)` / `release_due(id, now)`: the sweep's Debrief release (AD-9).
- Step 1 (Story 9.3): `own_net_inventory`, `own_explanation`, `save_mine` (raises
  `InvalidExplanation`, `commands.ExplanationExists`).
- `require_explanation(user_id, class_session_id)`: the one gate every Debrief read after step 1
  goes through (raises `ExplanationRequired`, 403 `explanation_required`, FR-41, FR-43);
  `step(user, debrief_id, n)` is the step endpoint behind it; step 2 carries the reveal of
  customer demand (Story 9.4, `reveal`), step 3 the whole chain (Story 9.5, `chain`), step 4
  the Student's own moments (Story 9.7, `moments`).
- Between steps 3 and 4 (Story 9.6): `own_reflection` (the pinned reflection questions with the
  Student's own answers) and `answer_mine` (raises `InvalidAnswer`, `UnknownQuestion`,
  `commands.AnswerOutOfOrder`), both behind the gate.
- `staff_explanation(user, class_session_id, student_id)`: the Explanation for the Class's staff
  (`explanations.read`, AD-12); None for everyone else.
- Story 9.8: step 4 also carries `bill` (the Debrief's lines under Kjedens regning);
  `finish_mine` («Fullfør Debriefen», raises `commands.DebriefIncomplete`,
  `commands.TestDeadlinePassed`), `own_summary`, and `staff_summary(user, class_session_id,
  student_id)`, the Explanation and Debrief summary for the Class's staff
  (`debrief_summaries.read`), the read Studentside and the Student report reuse.
- Story 9.9, step 5: `own_quiz` (the pinned Debrief quiz, the next attempt's questions and the
  latest result) and `submit_quiz_mine` (raises `InvalidQuizAnswers`, `commands.QuizPassed`,
  `commands.TestDeadlinePassed`), both behind `require_debrief` (403 `debrief_required`). The
  summary carries the number of quiz attempts and when the quiz was passed.
- Story 9.11: a Group debrief. `open_mine` makes the first open shared (two or more active
  Students in a Group-debrief session); `DebriefOut.group` carries the shared pointer;
  `join_mine`, `complete_step_mine` and `move_on_mine` are «Bli med», «Ferdig med steget» and
  «Gå videre for alle»; `require_step` refuses a step after the pointer (403 `step_locked`).
- Story 9.12: `leave_mine` («Forlat gruppen», «Ta en Personlig debrief»); a Student who goes on
  alone reads every step as in a Personal debrief and `GroupOut.alone` says why; the sweep's
  `due_dropouts`/`drop_out_due` and `due_fallbacks`/`fallback_due`.
- Story 9.13: `shared_mine` («Delt skjerm: hele kjeden»), the anonymised shared charts for a
  joined Student, locked until every joined Student has sent.
- Story 9.14: step 4 carries `narration` and a wrong quiz answer `ai_explanation`, each the AI
  text stored by `debrief.narration`'s `llm-batch` job before the Student first saw it, else the
  code text; `due_narrations`/`narrate_due` are the sweep's re-enqueue of a lost job.
- Story 9.15: `own_follow_up` and `ask_follow_up_mine`, the bounded follow-up questions under
  the reflection questions (`follow_up`; raise `ReflectionRequired`, `follow_up.Off`,
  `follow_up.Closed`, `follow_up.InvalidQuestion`, `follow_up.RateLimited`), and
  `close_follow_up(user_id, class_session_id)`, the one entry point another slice uses to close
  a Student's follow-up (Epic 11, when their Individual test opens).
- Story 9.10: `staff_quiz(user, class_session_id)` (the Class session's Debrief quiz with its
  answer keys and exclusions, `debrief_quiz.read`) and `set_quiz_exclusions` (raises
  `InvalidExclusions`, `commands.LastQuestion`, `commands.TestDeadlinePassed`); every attempt
  asks the pinned questions that are not taken out. `staff_summary` adds the Student's Roster name
  and their quiz attempts.
"""

import random
import uuid
from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select

from app.analysis import moments as moment_text
from app.analysis import narration as narration_rules
from app.analysis import quiz as quiz_rules
from app.analysis import sentences
from app.analysis.facts import LARGE_ORDER
from app.engine.settings import Role
from app.modules.content import service as content
from app.modules.debrief import commands, follow_up, insight, narration, rules
from app.modules.debrief.models import (
    ANSWER_MAX,
    DROPOUT_AFTER,
    EXPLANATION_MAX,
    INDIVIDUAL_STEP,
    debrief_ai_texts,
    debrief_alone,
    debrief_explanations,
    debrief_fact_sets,
    debrief_members,
    debrief_reflection_answers,
    debrief_releases,
    debrief_sessions,
    debrief_step_marks,
    debrief_summaries,
    quiz_attempts,
)
from app.modules.debrief.schemas import (
    BillOut,
    ChainOut,
    ChainRoleOut,
    ChainWeekOut,
    DebriefOut,
    DebriefStepOut,
    ExplanationOut,
    FollowUpAnswerOut,
    FollowUpOut,
    GroupMemberOut,
    GroupOut,
    LargestOrderOut,
    MomentOut,
    MomentsOut,
    MyExplanationOut,
    MySummaryOut,
    NetInventoryOut,
    NetWeekOut,
    OtherSeenOut,
    QuizAttemptOut,
    QuizChoiceOut,
    QuizOut,
    QuizQuestionOut,
    QuizResultOut,
    ReflectionAnswerOut,
    ReflectionOut,
    ReflectionQuestionOut,
    RenderedTextOut,
    RevealOut,
    RevealWeekOut,
    SharedChainOut,
    SharedOut,
    SharedRoleOut,
    SharedWeekOut,
    SimulatedOut,
    SimulatedRowOut,
    StaffAttemptOut,
    StaffQuizAttemptsOut,
    StaffQuizOut,
    StaffQuizQuestionOut,
    StaffSummaryOut,
    SummaryAnswerOut,
    SummaryMomentOut,
    SummaryOut,
)
from app.modules.games import service as games
from app.modules.progress import service as progress
from app.modules.sessions import service as sessions
from app.platform import authz
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

__all__ = [
    "DebriefRequired",
    "ExplanationRequired",
    "InvalidExclusions",
    "InvalidQuizAnswers",
    "InvalidAnswer",
    "InvalidExplanation",
    "NoExplanation",
    "NotAvailable",
    "ReflectionRequired",
    "StepLocked",
    "UnknownQuestion",
    "answer_mine",
    "ask_follow_up_mine",
    "close_follow_up",
    "own_follow_up",
    "complete_step_mine",
    "join_mine",
    "leave_mine",
    "due_dropouts",
    "drop_out_due",
    "due_fallbacks",
    "fallback_due",
    "move_on_mine",
    "move_on_wait",
    "require_step",
    "due_releases",
    "due_narrations",
    "narrate_due",
    "finish_mine",
    "judge_explanation",
    "mine",
    "open_mine",
    "own_explanation",
    "own_net_inventory",
    "own_quiz",
    "own_reflection",
    "own_summary",
    "release_due",
    "require_debrief",
    "require_explanation",
    "save_mine",
    "set_quiz_exclusions",
    "shared_mine",
    "staff_explanation",
    "staff_quiz",
    "staff_summary",
    "step",
    "submit_quiz_mine",
]

# Spillinnsikt's links to the Explanation and Debrief summary (registered on import).
_LINKS = insight.links

# Story 9.14: the narration's finish hook is registered on import of `narration`; the sweep's
# re-enqueue of a lost job.
due_narrations = narration.due_narrations
narrate_due = narration.narrate_due


class NotAvailable(Exception):
    """The Student's Debrief is not open: `debrief_not_open` (their game has not finished) or
    `debrief_held` (the Lecturer holds every Debrief until all Class games have finished)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ExplanationRequired(Exception):
    """A read after step 1 without the Student's saved Explanation (403 `explanation_required`,
    FR-41): checked here, in the api, never only in the web app."""


class InvalidExplanation(Exception):
    """An Explanation that may not be stored: `blank` (white space only) or `too_long`."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class InvalidAnswer(Exception):
    """A reflection answer that may not be stored: `blank` (white space only) or `too_long`."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class UnknownQuestion(Exception):
    """No reflection question of that id in the Class session's pinned version (404
    `not_found`)."""


class DebriefRequired(Exception):
    """The Debrief quiz before the Student has finished the Debrief (403 `debrief_required`,
    FR-46, AD-16): checked here with `progress.has_step`, never only in the web app."""


class InvalidQuizAnswers(Exception):
    """A quiz attempt that cannot be scored (422 `validation_error`): `incomplete` or
    `unknown_choice`."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class InvalidExclusions(Exception):
    """Quiz exclusions that name a question the Class session's quiz does not have (422
    `validation_error`, `unknown_question`)."""


class StepLocked(Exception):
    """A step after a Group debrief's shared pointer (403 `step_locked`, Story 9.11, FR-43):
    checked in the api, never only in the web app."""


class NoExplanation(Exception):
    """The Student has not sent an Explanation in the Class session (404 `not_found`)."""


class ReflectionRequired(Exception):
    """A follow-up question before every reflection question is answered (403
    `reflection_required`, Story 9.15): the field stands after them (UX-DR31)."""


def _open_or_raise(found: rules.Availability) -> None:
    if found.state == "not_open":
        raise NotAvailable("debrief_not_open")
    if found.state == "held":
        raise NotAvailable("debrief_held")


async def _out(row: commands.DebriefRow, game: games.StudentGame, user_id: uuid.UUID) -> DebriefOut:
    return DebriefOut(
        id=row.id,
        class_session_id=row.class_session_id,
        game_id=row.game_id,
        game_number=game.number,
        role=game.role,
        step=row.step,
        group=await _group(row, user_id) if row.shared else None,
    )


def move_on_wait() -> timedelta:
    """How long a shared step must have been open before its opener may move on (Story 9.11):
    configuration, a placeholder."""
    return timedelta(minutes=get_settings().debrief_move_on_wait_minutes)


async def _group(row: commands.DebriefRow, user_id: uuid.UUID) -> GroupOut:
    """A shared Debrief session's pointer as `user_id` reads it (Story 9.11, FR-43): the joined
    Students with their names read now, and whether each has sent and finished the shared step,
    only for a joined caller (never the text)."""
    async with get_sessionmaker()() as s:
        alone = (
            (
                await s.execute(
                    select(
                        debrief_alone.c.user_id, debrief_alone.c.step, debrief_alone.c.reason
                    ).where(debrief_alone.c.debrief_id == row.id)
                )
            )
            .mappings()
            .all()
        )
        gone = {each["user_id"]: each for each in alone}
        joined = [
            each
            for each in (
                await s.scalars(
                    select(debrief_members.c.user_id)
                    .where(debrief_members.c.debrief_id == row.id)
                    .order_by(debrief_members.c.joined_at, debrief_members.c.user_id)
                )
            ).all()
            if each not in gone
        ]
        sent: set[uuid.UUID] = set()
        marked: set[uuid.UUID] = set()
        if user_id in joined:
            sent = set(
                (
                    await s.scalars(
                        select(debrief_explanations.c.user_id).where(
                            debrief_explanations.c.class_session_id == row.class_session_id,
                            debrief_explanations.c.user_id.in_(joined),
                        )
                    )
                ).all()
            )
            marked = set(
                (
                    await s.scalars(
                        select(debrief_step_marks.c.user_id).where(
                            debrief_step_marks.c.debrief_id == row.id,
                            debrief_step_marks.c.step == row.step,
                        )
                    )
                ).all()
            )
    members: list[GroupMemberOut] = []
    if user_id in joined:
        names = await sessions.student_names(row.class_session_id, joined)
        done = sent if row.step == 1 else marked
        members = [
            GroupMemberOut(
                name=names.get(each), you=each == user_id, sent=each in sent, done=each in done
            )
            for each in joined
        ]
    opened = row.step_opened_at
    mine = gone.get(user_id)
    return GroupOut(
        step=row.step,
        joined=user_id in joined,
        opener=user_id in joined and commands.effective_opener(row.opener_id, joined) == user_id,
        step_opened_at=opened,
        move_on_at=opened + move_on_wait() if opened is not None else None,
        members=members,
        alone=mine["reason"] if mine else None,
        alone_from=mine["step"] if mine else None,
    )


async def _exists(game_id: uuid.UUID) -> bool:
    async with get_sessionmaker()() as s:
        found = await s.scalar(
            select(debrief_sessions.c.id).where(debrief_sessions.c.game_id == game_id)
        )
    return found is not None


async def open_mine(user: authz.Principal, class_session_id: uuid.UUID) -> DebriefOut | None:
    """«Gå til Debrief» and Stegene's Debrief step (FR-42): `debrief.commands.open` for the
    Student's game, through `games.service.student_game` only. Story 9.11: in a Class session
    with Group debrief whose game at least two active Students played (each a Student of the game
    with at least one Order of their own), the first open makes it a shared Group debrief with
    the opener joined, and tells the game's other Students."""
    found = await rules.available(user, class_session_id)
    if found is None:
        return None
    _open_or_raise(found)
    shared, tell = False, []
    if found.group_mode and not await _exists(found.game.game_id):
        # Only for the open that creates it: whether it is shared is fixed then.
        async with get_sessionmaker()() as s:
            students = await games.game_students(s, found.game.game_id)
        shared = sum(1 for each in students if each.student_orders > 0) >= 2
        tell = [each.user_id for each in students if each.user_id != user.id]
    row = await commands.open(found.game.game_id, class_session_id, user.id, shared, tell)
    return await _out(row, found.game, user.id)


async def _own(
    user: authz.Principal, debrief_id: uuid.UUID
) -> tuple[commands.DebriefRow, games.StudentGame] | None:
    """The Debrief session `debrief_id` with the Student's game when it is the one of their own
    game; None for any other id alike. Raises `NotAvailable` while it is not open."""
    async with get_sessionmaker()() as s:
        row = (
            (await s.execute(select(debrief_sessions).where(debrief_sessions.c.id == debrief_id)))
            .mappings()
            .one_or_none()
        )
    if row is None:
        return None
    # Whose it is first: another Game's Debrief reads as one that does not exist (FR-5), never
    # as not open or held.
    found = await rules.available(user, row["class_session_id"])
    if found is None or found.game.game_id != row["game_id"]:
        return None
    _open_or_raise(found)
    debrief = commands.row_of(row)
    if debrief.shared:
        # Story 9.12: a Student who goes on alone reads it as a Personal debrief.
        async with get_sessionmaker()() as s:
            alone = await s.scalar(
                select(debrief_alone.c.user_id).where(
                    debrief_alone.c.debrief_id == debrief.id, debrief_alone.c.user_id == user.id
                )
            )
        debrief = replace(debrief, alone=alone is not None)
    return debrief, found.game


async def mine(user: authz.Principal, debrief_id: uuid.UUID) -> DebriefOut | None:
    """The Debrief session `debrief_id` when it is the one of the Student's own game, under the
    same availability rule; None for any other id alike."""
    found = await _own(user, debrief_id)
    return await _out(*found, user.id) if found else None


def require_step(row: commands.DebriefRow, number: int) -> None:
    """The Group debrief's gate (Story 9.11, FR-43, AD-21): in a shared Debrief session a step
    after the pointer is refused (`StepLocked`, 403 `step_locked`), in the api: steps 2 and 3 by
    their number, the reflection questions and everything after them from `INDIVIDUAL_STEP`. A
    Personal debrief has no such gate, nor has a Student who goes on alone (Story 9.12, `_own`).
    Call after `require_explanation`."""
    if row.shared and not row.alone and min(number, INDIVIDUAL_STEP) > row.step:
        raise StepLocked


async def join_mine(user: authz.Principal, debrief_id: uuid.UUID) -> DebriefOut | None:
    """«Bli med» (Story 9.11): `debrief.commands.join` for the Student's own game's Debrief. Raises
    `NotAvailable` or `commands.NotGroup`."""
    found = await _own(user, debrief_id)
    if found is None:
        return None
    row, game = found
    joined = await commands.join(row.game_id, user.id)
    return await _out(joined, game, user.id)


async def leave_mine(user: authz.Principal, debrief_id: uuid.UUID) -> DebriefOut | None:
    """«Forlat gruppen» / «Ta en Personlig debrief» (Story 9.12): `debrief.commands.leave` for
    the Student's own game's Debrief. Raises `NotAvailable` or `commands.NotGroup`."""
    found = await _own(user, debrief_id)
    if found is None:
        return None
    row, game = found
    left = await commands.leave(row.game_id, user.id)
    return await _out(left, game, user.id)


async def complete_step_mine(
    user: authz.Principal, debrief_id: uuid.UUID, number: int
) -> DebriefOut | None:
    """«Ferdig med steget» on shared step 2 or 3 (Story 9.11): `debrief.commands.complete_step`,
    behind the Explanation gate. Raises `NotAvailable`, `ExplanationRequired`,
    `commands.NotGroup`, `commands.NotJoined` or `commands.StepNotOpen`."""
    found = await _own(user, debrief_id)
    if found is None:
        return None
    row, game = found
    await require_explanation(user.id, row.class_session_id)
    done = await commands.complete_step(row.game_id, row.class_session_id, user.id, number)
    assert isinstance(done, commands.DebriefRow)
    return await _out(done, game, user.id)


async def move_on_mine(user: authz.Principal, debrief_id: uuid.UUID) -> DebriefOut | None:
    """«Gå videre for alle» (Story 9.11): `debrief.commands.move_on` for the opener. Raises
    `NotAvailable`, `commands.NotGroup`, `commands.NotJoined` or `commands.TooEarly`."""
    found = await _own(user, debrief_id)
    if found is None:
        return None
    row, game = found
    moved = await commands.move_on(row.game_id, user.id, move_on_wait())
    return await _out(moved, game, user.id)


async def own_net_inventory(user: authz.Principal, debrief_id: uuid.UUID) -> NetInventoryOut | None:
    """«Ditt netto lager, hele spillet» (Story 9.3): the Netto lager of the Student's own Seat in
    every Uke of the Decision log, as the Seat saw it when ordering. Only rows of the Student's
    own Role go into the answer: no demand, no other Seat (FR-14). Not gated by the Explanation,
    nor is the number of Uker: the finished game has shown them all."""
    found = await _own(user, debrief_id)
    if found is None:
        return None
    row, game = found
    logged = await games.decision_log(str(row.game_id))
    own = sorted((e for e in logged if str(e.role) == str(game.role)), key=lambda e: e.week)
    return NetInventoryOut(
        weeks=[NetWeekOut(week=e.week, net_inventory=e.state_seen.net_inventory) for e in own]
    )


async def _stored(user_id: uuid.UUID, class_session_id: uuid.UUID) -> ExplanationOut | None:
    async with get_sessionmaker()() as s:
        row = (
            (
                await s.execute(
                    select(debrief_explanations).where(
                        debrief_explanations.c.user_id == user_id,
                        debrief_explanations.c.class_session_id == class_session_id,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        return None
    return ExplanationOut(text=row["text"], length=row["length"], saved_at=row["saved_at"])


async def own_explanation(user: authz.Principal, debrief_id: uuid.UUID) -> MyExplanationOut | None:
    """The Student's own Explanation in this Debrief, `explanation` None before it is sent.
    Keyed by the caller: no Student reads another's (FR-41)."""
    found = await _own(user, debrief_id)
    if found is None:
        return None
    row, _ = found
    return MyExplanationOut(explanation=await _stored(user.id, row.class_session_id))


def judge_explanation(text: str) -> None:
    """Raises `InvalidExplanation` for white space only or more than 5000 characters."""
    if not text.strip():
        raise InvalidExplanation("blank")
    if len(text) > EXPLANATION_MAX:
        raise InvalidExplanation("too_long")


async def save_mine(
    user: authz.Principal, debrief_id: uuid.UUID, text: str
) -> ExplanationOut | None:
    """«Send Forklaring»: `debrief.commands.save_explanation` for the Student's own Debrief.
    Raises `NotAvailable`, `InvalidExplanation` or `commands.ExplanationExists`."""
    found = await _own(user, debrief_id)
    if found is None:
        return None
    row, _ = found
    judge_explanation(text)
    saved = await commands.save_explanation(row.game_id, row.class_session_id, user.id, text)
    return ExplanationOut(text=saved.text, length=saved.length, saved_at=saved.saved_at)


async def require_explanation(user_id: uuid.UUID, class_session_id: uuid.UUID) -> None:
    """The gate (FR-41, FR-43, AD-21): every Debrief read after step 1 (the steps, the demand
    series, another Seat's Orders, inventory or backlog) calls this first. Raises
    `ExplanationRequired` until the Student's Explanation is saved."""
    if not await progress.has_step(user_id, class_session_id, progress.Step.EXPLANATION):
        raise ExplanationRequired


async def step(user: authz.Principal, debrief_id: uuid.UUID, number: int) -> DebriefStepOut | None:
    """A step after step 1, behind the gate. Raises `NotAvailable` or `ExplanationRequired`."""
    found = await _own(user, debrief_id)
    if found is None:
        return None
    row, game = found
    await require_explanation(user.id, row.class_session_id)
    require_step(row, number)
    shown = await _reveal(row.game_id, game.role) if number == 2 else None
    chain = await _chain(row.game_id, game.role) if number == 3 else None
    own = bill = None
    if number == 4:
        stored = await games.fact_set(str(row.game_id), game.role)
        own = await _moments(user.id, row, game.role, stored)
        bill = await _bill(row.game_id, game.role, stored)
    return DebriefStepOut(
        debrief_id=row.id, step=number, reveal=shown, chain=chain, moments=own, bill=bill
    )


def _percent(part: Decimal, whole: Decimal) -> int | None:
    """`part` as a whole percent of `whole`, half up; None when `whole` is 0."""
    if not whole:
        return None
    return int((part * 100 / whole).quantize(Decimal(1), rounding=ROUND_HALF_UP))


async def _bill(game_id: uuid.UUID, role: str, stored: games.StoredFactSet) -> BillOut:
    """The Debrief's lines under Kjedens regning (Story 9.8, FR-44, UX-DR36): the restordre share,
    the AI-held share and «Simulert, samme kunder», every number from the stored facts set of the
    Student's own Seat (AD-7). Call only behind `require_explanation`."""
    found = await games.get_game(str(game_id))
    if found is None or found.settings is None:
        raise RuntimeError(f"a finished Game {game_id} has no settings")
    chain = stored.facts.chain
    backorder = sum((each.backorder_cost for each in chain.by_role), Decimal(0))
    simulated = stored.facts.seat.simulated
    return BillOut(
        role=Role(role),
        total_cost=chain.total_cost,
        backorder_cost=backorder,
        backorder_share_percent=_percent(backorder, chain.total_cost),
        backorder_costs_double=found.settings.backorder_cost == 2 * found.settings.holding_cost,
        ai_held_cost=chain.ai_held_cost,
        ai_held_share_percent=_percent(chain.ai_held_cost, chain.total_cost),
        simulated=(
            None
            if simulated is None
            else SimulatedOut(
                params_id=simulated.params_id,
                rows=[
                    SimulatedRowOut(
                        counts_supply_line=each.counts_supply_line,
                        holding_cost=each.holding_cost,
                        backorder_cost=each.backorder_cost,
                        total_cost=each.total_cost,
                    )
                    for each in simulated.rows
                ],
            )
        ),
    )


async def _moments(
    user_id: uuid.UUID, row: commands.DebriefRow, role: str, stored: games.StoredFactSet
) -> MomentsOut:
    """Step 4 (Story 9.7, FR-44, AD-7): the Student's own moments, rendered by code from the facts
    set of their Seat. The set comes from `games.facts.get_or_create` (stored once, never rebuilt
    here) and its id is recorded for the Student at the first view, so every view cites the same
    set. The templates are the ones the Class session pinned at the lock (the latest for a session
    locked before the pin); the pattern names are those of the version the facts were built with.
    Call only behind `require_explanation`."""
    cited = await commands.record_facts(
        row.game_id, row.class_session_id, user_id, uuid.UUID(stored.id)
    )
    if str(cited) != stored.id:
        raise RuntimeError(f"the moments of Debrief {row.id} cite another facts set")
    seat = stored.facts.seat
    rendered = await _rendered(row.game_id, stored)
    logged = {
        e.week: e.state_seen
        for e in await games.decision_log(str(row.game_id))
        if str(e.role) == str(role)
    }
    by_id = {moment.id: moment for moment in seat.moments}

    text = _text
    shown = []
    for each in rendered.moments:
        moment = by_id[each.id]
        shown.append(
            MomentOut(
                id=moment.id,
                week=moment.week,
                order=moment.order,
                chosen_by=moment.chosen_by,
                heading=text(each.heading),
                reckoning=text(each.reckoning),
                later=text(each.later),
                patterns=[text(p) for p in each.patterns],
                others=[
                    OtherSeenOut(
                        role=other.role,
                        incoming_order=other.incoming_order,
                        inventory=other.inventory,
                        backlog=other.backlog,
                        supply_line=other.supply_line,
                    )
                    for other in moment.others_seen
                ],
                seen=logged[moment.week],
            )
        )
    return MomentsOut(
        role=Role(role),
        student_orders=seat.student_orders,
        mostly_ai=seat.sm_excluded,
        heading=text(rendered.heading) if rendered.heading else None,
        moments=shown,
        narration=await _narration(user_id, row, stored) if shown else None,
    )


async def _ai_text(
    fact_set_id: uuid.UUID, subject: str, before: datetime
) -> RenderedTextOut | None:
    """The facts set's stored AI text of `subject` when it was stored at or before `before`
    (database time), so what a reader saw first never changes under them."""
    async with get_sessionmaker()() as s:
        found = (
            await s.execute(
                select(
                    debrief_ai_texts.c.text,
                    debrief_ai_texts.c.ai_generated,
                    debrief_ai_texts.c.llm_call_id,
                ).where(
                    debrief_ai_texts.c.fact_set_id == fact_set_id,
                    debrief_ai_texts.c.subject == subject,
                    debrief_ai_texts.c.created_at <= before,
                )
            )
        ).one_or_none()
    if found is None or not found.text:
        return None
    return RenderedTextOut(
        text=found.text, ai_generated=found.ai_generated, llm_call_id=found.llm_call_id
    )


async def _narration(
    user_id: uuid.UUID, row: commands.DebriefRow, stored: games.StoredFactSet
) -> RenderedTextOut | None:
    """Step 4's narration (Story 9.14, FR-44, AD-7): the stored text (AI, or the code text a
    failed call stored) when it was stored before the Student's first view of the step, the time
    `record_facts` stored; else the code text, from the templates the Class session pinned (the
    latest for a session locked before the pin). Fixed from that first view on."""
    async with get_sessionmaker()() as s:
        first_view = await s.scalar(
            select(debrief_fact_sets.c.recorded_at).where(
                debrief_fact_sets.c.user_id == user_id,
                debrief_fact_sets.c.class_session_id == row.class_session_id,
            )
        )
    if first_view is not None:
        found = await _ai_text(uuid.UUID(stored.id), narration.NARRATION, first_view)
        if found is not None:
            return found
    game = await games.get_game(str(row.game_id))
    pins = game.session_runtime.pins if game and game.session_runtime else None
    _, templates = await content.narration_templates(
        content.pinned_version(pins, content.Kind.NARRATION_TEMPLATES)
    )
    code = narration_rules.render(stored.facts, templates)
    return None if code is None else RenderedTextOut(text=code.text)


def _text(rendered_text: sentences.RenderedText) -> RenderedTextOut:
    return RenderedTextOut(text=rendered_text.text)


async def _rendered(game_id: uuid.UUID, stored: games.StoredFactSet) -> moment_text.RenderedMoments:
    """The own moments of a stored facts set, rendered with the moment templates the Game's Class
    session pinned at the lock (the latest for a session locked before the pin) and the pattern
    names of the version the facts were built with."""
    found = await games.get_game(str(game_id))
    pins = found.session_runtime.pins if found and found.session_runtime else None
    _, templates = await content.moment_templates(
        content.pinned_version(pins, content.Kind.MOMENT_TEMPLATES)
    )
    _, patterns = await content.detected_patterns(stored.patterns_version)
    return moment_text.render(stored.facts, templates, patterns)


async def _chain(game_id: uuid.UUID, role: str) -> ChainOut:
    """Step 3 (Story 9.5, FR-44): every Role's Orders and the Week states it saw, from the
    Decision log, with Forsterkning and the first large Order from the stored facts set (AD-7:
    read, never rebuilt here). The Game's capacity per Role only while `FEATURE_CAPACITY` is on.
    Call only behind `require_explanation`."""
    found = await games.get_game(str(game_id))
    if found is None or found.settings is None:
        raise RuntimeError(f"a finished Game {game_id} has no settings")
    stored = await games.fact_set(str(game_id), role)
    by_role = {str(each.role): each for each in stored.facts.chain.by_role}
    logged = await games.decision_log(str(game_id))
    capped = get_settings().feature_capacity
    roles = []
    # Fabrikk first: the chain is stored the customer's end first.
    for each in reversed(found.settings.roles):
        own = sorted((e for e in logged if str(e.role) == str(each)), key=lambda e: e.week)
        fact = by_role[str(each)]
        roles.append(
            ChainRoleOut(
                role=each,
                amplification=fact.amplification,
                first_large_order_week=fact.first_large_order_week,
                capacity=found.settings.capacity_of(each) if capped else None,
                weeks=[
                    ChainWeekOut(
                        week=e.week,
                        order=e.order,
                        incoming_order=e.state_seen.incoming_order,
                        inventory=e.state_seen.inventory,
                        backlog=e.state_seen.backlog,
                        supply_line=e.state_seen.supply_line,
                    )
                    for e in own
                ],
            )
        )
    return ChainOut(
        own_role=Role(role),
        last_week=stored.facts.chain.weeks,
        large_order=LARGE_ORDER,
        roles=roles,
    )


async def _joined(s, debrief_id: uuid.UUID) -> list[uuid.UUID]:
    """The joined Students of a shared Debrief session: its members without an alone row (Story
    9.12)."""
    gone = select(debrief_alone.c.user_id).where(debrief_alone.c.debrief_id == debrief_id)
    return list(
        (
            await s.scalars(
                select(debrief_members.c.user_id).where(
                    debrief_members.c.debrief_id == debrief_id,
                    debrief_members.c.user_id.not_in(gone),
                )
            )
        ).all()
    )


async def shared_mine(user: authz.Principal, debrief_id: uuid.UUID) -> SharedOut | None:
    """«Delt skjerm: hele kjeden» (Story 9.13, FR-74, AD-21): the shared charts of a Group debrief
    for a Student joined to it, by Role only. None (403 `forbidden`, as for an id that is not one)
    for everyone else: a Personal debrief, a Student who has not joined or goes on alone, another
    game's Debrief. Locked, with no demand and no chain data, while a joined Student has no saved
    Explanation (FR-43)."""
    found = await _own(user, debrief_id)
    if found is None:
        return None
    row, game = found
    if not row.shared or row.alone:
        return None
    async with get_sessionmaker()() as s:
        joined = await _joined(s, row.id)
        if user.id not in joined:
            return None
        sent = await s.scalar(
            select(func.count())
            .select_from(debrief_explanations)
            .where(
                debrief_explanations.c.class_session_id == row.class_session_id,
                debrief_explanations.c.user_id.in_(joined),
            )
        )
    locked = (sent or 0) < len(joined)
    return SharedOut(
        debrief_id=row.id,
        class_session_id=row.class_session_id,
        game_number=game.number,
        step=row.step,
        locked=locked,
        chain=None if locked else await _shared_chain(row.game_id, game.role),
    )


async def _shared_chain(game_id: uuid.UUID, role: str) -> SharedChainOut:
    """The shared screen's chain (Story 9.13): every Role's Uker from the Decision log, Fabrikk
    first, with Forsterkning and the costs from the stored facts set's chain part, which is the
    same for every Seat (AD-7: read, never rebuilt). Call only once the lock is open."""
    found = await games.get_game(str(game_id))
    if found is None or found.settings is None:
        raise RuntimeError(f"a finished Game {game_id} has no settings")
    chain = (await games.fact_set(str(game_id), role)).facts.chain
    by_role = {str(each.role): each for each in chain.by_role}
    logged = await games.decision_log(str(game_id))
    roles = []
    for each in reversed(found.settings.roles):
        own = sorted((e for e in logged if str(e.role) == str(each)), key=lambda e: e.week)
        fact = by_role[str(each)]
        roles.append(
            SharedRoleOut(
                role=each,
                amplification=fact.amplification,
                holding_cost=fact.holding_cost,
                backorder_cost=fact.backorder_cost,
                total_cost=fact.total_cost,
                weeks=[
                    SharedWeekOut(
                        week=e.week,
                        order=e.order,
                        incoming_order=e.state_seen.incoming_order,
                        inventory=e.state_seen.inventory,
                        backlog=e.state_seen.backlog,
                        supply_line=e.state_seen.supply_line,
                        net_inventory=e.state_seen.net_inventory,
                    )
                    for e in own
                ],
            )
        )
    return SharedChainOut(
        last_week=chain.weeks,
        holding_cost=sum((each.holding_cost for each in chain.by_role), Decimal(0)),
        backorder_cost=sum((each.backorder_cost for each in chain.by_role), Decimal(0)),
        total_cost=chain.total_cost,
        roles=roles,
    )


async def _reveal(game_id: uuid.UUID, role: str) -> RevealOut:
    """Step 2 (Story 9.4, FR-44): the heading from the Game's stored demand series with the
    sentence templates its Class session pinned at the lock (the latest for a session locked
    before the pin), and per logged Uke of the own Seat: Kundene, Ordre inn and Din ordre. Call
    only behind `require_explanation`."""
    found = await games.get_game(str(game_id))
    series = await games.demand_series(str(game_id))
    if found is None or found.settings is None or not series:
        raise RuntimeError(f"a finished Game {game_id} has no demand series")
    pins = found.session_runtime.pins if found.session_runtime else None
    _, templates = await content.sentence_templates(
        content.pinned_version(pins, content.Kind.SENTENCE_TEMPLATES)
    )
    heading = sentences.demand_heading(found.settings.demand, series, templates)
    logged = await games.decision_log(str(game_id))
    own = sorted((e for e in logged if str(e.role) == str(role)), key=lambda e: e.week)
    weeks = [
        RevealWeekOut(
            week=e.week,
            demand=series[e.week - 1],
            incoming_order=e.state_seen.incoming_order,
            order=e.order,
        )
        for e in own
    ]
    # The first Uke of the largest Order (max keeps the first of equals); none when every Order
    # was 0, so no label stands on an empty baseline.
    largest = max(weeks, key=lambda w: w.order, default=None)
    if largest is not None and largest.order == 0:
        largest = None
    return RevealOut(
        heading=heading.text,
        template_id=heading.template_id,
        role=Role(role),
        weeks=weeks,
        largest_order=LargestOrderOut(week=largest.week, order=largest.order) if largest else None,
    )


async def _questions(game_id: uuid.UUID) -> tuple[int, content.ReflectionQuestions]:
    """The reflection questions the Game's Class session pinned at the lock (the latest for a
    session locked before the pin)."""
    found = await games.get_game(str(game_id))
    pins = found.session_runtime.pins if found and found.session_runtime else None
    return await content.reflection_questions(
        content.pinned_version(pins, content.Kind.REFLECTION_QUESTIONS)
    )


async def _answers(
    user_id: uuid.UUID, class_session_id: uuid.UUID
) -> dict[str, ReflectionAnswerOut]:
    async with get_sessionmaker()() as s:
        found = (
            await s.execute(
                select(debrief_reflection_answers).where(
                    debrief_reflection_answers.c.user_id == user_id,
                    debrief_reflection_answers.c.class_session_id == class_session_id,
                )
            )
        ).mappings()
        return {
            row["question_id"]: ReflectionAnswerOut(
                text=row["text"], length=row["length"], saved_at=row["saved_at"]
            )
            for row in found
        }


def _question(
    question: content.ReflectionQuestion, answer: ReflectionAnswerOut | None
) -> ReflectionQuestionOut:
    return ReflectionQuestionOut(
        id=question.id,
        kind=question.kind,
        prompt=question.prompt,
        hint=question.hint,
        answer=answer,
    )


async def own_reflection(user: authz.Principal, debrief_id: uuid.UUID) -> ReflectionOut | None:
    """The reflection questions between steps 3 and 4 (Story 9.6, FR-45), in the order asked,
    with the Student's own answers only (FR-43, AD-14). Behind the Explanation gate."""
    found = await _own(user, debrief_id)
    if found is None:
        return None
    row, _ = found
    await require_explanation(user.id, row.class_session_id)
    require_step(row, INDIVIDUAL_STEP)
    version, questions = await _questions(row.game_id)
    answers = await _answers(user.id, row.class_session_id)
    return ReflectionOut(
        version=version, questions=[_question(q, answers.get(q.id)) for q in questions.questions]
    )


def judge_answer(text: str) -> None:
    """Raises `InvalidAnswer` for white space only or more than 2000 characters."""
    if not text.strip():
        raise InvalidAnswer("blank")
    if len(text) > ANSWER_MAX:
        raise InvalidAnswer("too_long")


async def answer_mine(
    user: authz.Principal, debrief_id: uuid.UUID, question_id: str, text: str
) -> ReflectionQuestionOut | None:
    """«Fortsett» on a reflection question: `debrief.commands.complete_step` for the Student's
    own Debrief, behind the gate; answers the question with its stored answer.
    Raises `NotAvailable`, `ExplanationRequired`, `UnknownQuestion`, `InvalidAnswer` or
    `commands.AnswerOutOfOrder`."""
    found = await _own(user, debrief_id)
    if found is None:
        return None
    row, _ = found
    await require_explanation(user.id, row.class_session_id)
    require_step(row, INDIVIDUAL_STEP)
    version, questions = await _questions(row.game_id)
    ids = [q.id for q in questions.questions]
    if question_id not in ids:
        raise UnknownQuestion
    asked = questions.questions[ids.index(question_id)]
    # An answered question answers its stored answer whatever is sent again (a retry, a second
    # device): it never changes, so the new text is not judged.
    stored = (await _answers(user.id, row.class_session_id)).get(question_id)
    if stored is not None:
        return _question(asked, stored)
    judge_answer(text)
    saved = await commands.complete_step(
        row.game_id,
        row.class_session_id,
        user.id,
        INDIVIDUAL_STEP,
        commands.Reflection(version, ids, question_id, text),
    )
    assert isinstance(saved, commands.AnswerRow)
    answer = ReflectionAnswerOut(text=saved.text, length=saved.length, saved_at=saved.saved_at)
    return _question(asked, answer)


async def _past_reflection(
    user: authz.Principal, debrief_id: uuid.UUID
) -> tuple[commands.DebriefRow, games.StudentGame] | None:
    """The Student's own Debrief past the reflection questions (Story 9.15): behind the
    Explanation gate and the Group pointer; raises `ReflectionRequired` while a reflection
    question is unanswered."""
    found = await _own(user, debrief_id)
    if found is None:
        return None
    row, game = found
    await require_explanation(user.id, row.class_session_id)
    require_step(row, INDIVIDUAL_STEP)
    _, questions = await _questions(row.game_id)
    answers = await _answers(user.id, row.class_session_id)
    if any(q.id not in answers for q in questions.questions):
        raise ReflectionRequired
    return row, game


async def own_follow_up(user: authz.Principal, debrief_id: uuid.UUID) -> FollowUpOut | None:
    """The follow-up field under the reflection questions (Story 9.15, FR-45, FR-15): `off`,
    `open` or `closed`, with the Student's own stored questions (AD-14). Behind the Explanation
    gate and the reflection questions."""
    found = await _past_reflection(user, debrief_id)
    if found is None:
        return None
    row, game = found
    prepared = await follow_up.prepare(row.game_id, game.role)
    if prepared is None:
        state = "off"
    elif await follow_up.closed(user.id, row.class_session_id):
        state = "closed"
    else:
        state = "open"
    return FollowUpOut(state=state, asked=await follow_up.asked(user.id, row.class_session_id))


async def ask_follow_up_mine(
    user: authz.Principal, debrief_id: uuid.UUID, question: str, *, ip: str, now: datetime
) -> FollowUpAnswerOut | None:
    """A follow-up question about the Student's own Game (Story 9.15, FR-45): one model call,
    on this request, never retried; the answer, or `unanswered` when none could be given. Raises
    `NotAvailable`, `ExplanationRequired`, `StepLocked`, `ReflectionRequired`, `follow_up.Off`,
    `follow_up.Closed`, `follow_up.InvalidQuestion` or `follow_up.RateLimited`."""
    found = await _past_reflection(user, debrief_id)
    if found is None:
        return None
    row, game = found
    prepared = await follow_up.prepare(row.game_id, game.role)
    if prepared is None:
        raise follow_up.Off
    if await follow_up.closed(user.id, row.class_session_id):
        raise follow_up.Closed
    return await follow_up.ask(
        user.id, row.class_session_id, row.game_id, prepared, question, ip=ip, now=now
    )


async def close_follow_up(user_id: uuid.UUID, class_session_id: uuid.UUID) -> bool:
    """Close the Student's follow-up questions in the Class session (Story 9.15, FR-45): the one
    entry point another slice uses (Epic 11, when the Student's Individual test opens). Returns
    whether this call closed it; closed already is no error."""
    return await commands.close_follow_up(user_id, class_session_id)


async def staff_explanation(
    user: authz.Principal, class_session_id: uuid.UUID, student_id: uuid.UUID
) -> ExplanationOut | None:
    """A Student's Explanation for the staff of the Class (`explanations.read`: its owners and
    Assistant lecturers, AD-12); None for every other caller alike (FR-5). Raises
    `NoExplanation` when the Student has not sent one."""
    if not await sessions.class_staff_may(user, class_session_id, "explanations.read"):
        return None
    found = await _stored(student_id, class_session_id)
    if found is None:
        raise NoExplanation
    return found


async def _summary_row(
    user_id: uuid.UUID, class_session_id: uuid.UUID
) -> commands.SummaryRow | None:
    async with get_sessionmaker()() as s:
        row = (
            (
                await s.execute(
                    select(debrief_summaries).where(
                        debrief_summaries.c.user_id == user_id,
                        debrief_summaries.c.class_session_id == class_session_id,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
    return commands.summary_of(row) if row is not None else None


async def _summary(
    user_id: uuid.UUID, class_session_id: uuid.UUID, role: str, found: commands.SummaryRow
) -> SummaryOut:
    """The stored summary with its key moments rendered by code from the facts set it cites and
    each answer's question prompt; `late` from the stored time against the Student's Debrief
    deadline (FR-18), never against the clock."""
    stored = await games.fact_set(str(found.game_id), role)
    if stored.id != str(found.fact_set_id):
        raise RuntimeError(f"the Debrief summary of {user_id} cites another facts set")
    rendered = {each.id: each for each in (await _rendered(found.game_id, stored)).moments}
    weeks = {moment.id: moment.week for moment in stored.facts.seat.moments}
    _, questions = await _questions(found.game_id)
    prompts = {q.id: q.prompt for q in questions.questions}
    deadline, _ = await sessions.student_deadlines(user_id, class_session_id)
    attempts = await _attempts(user_id, class_session_id)
    passing = next((each for each in attempts if each.passed), None)
    return SummaryOut(
        fact_set_id=found.fact_set_id,
        finished_at=found.finished_at,
        late=deadline is not None and found.finished_at > deadline,
        moments=[
            SummaryMomentOut(
                id=moment_id,
                week=weeks[moment_id],
                heading=_text(rendered[moment_id].heading),
                reckoning=_text(rendered[moment_id].reckoning),
                later=_text(rendered[moment_id].later),
                patterns=[_text(p) for p in rendered[moment_id].patterns],
            )
            for moment_id in found.moment_ids
        ],
        reflection=[
            SummaryAnswerOut(
                question_id=each["question_id"],
                prompt=prompts.get(each["question_id"], ""),
                text=each["text"],
            )
            for each in found.reflection
        ],
        quiz_attempts=passing.number if passing else len(attempts),
        quiz_passed_at=passing.submitted_at if passing else None,
    )


async def own_summary(user: authz.Principal, debrief_id: uuid.UUID) -> MySummaryOut | None:
    """The Student's own Debrief summary (Story 9.8), `summary` None until they finish. Behind
    the Explanation gate."""
    found = await _own(user, debrief_id)
    if found is None:
        return None
    row, game = found
    await require_explanation(user.id, row.class_session_id)
    require_step(row, INDIVIDUAL_STEP)
    stored = await _summary_row(user.id, row.class_session_id)
    if stored is None:
        return MySummaryOut(summary=None)
    return MySummaryOut(summary=await _summary(user.id, row.class_session_id, game.role, stored))


async def finish_mine(user: authz.Principal, debrief_id: uuid.UUID) -> MySummaryOut | None:
    """«Fullfør Debriefen» (Story 9.8, FR-47): `debrief.commands.finish` for the Student's own
    Debrief, behind the gate. Raises `NotAvailable`, `ExplanationRequired`,
    `commands.DebriefIncomplete` or `commands.TestDeadlinePassed`."""
    found = await _own(user, debrief_id)
    if found is None:
        return None
    row, game = found
    await require_explanation(user.id, row.class_session_id)
    require_step(row, INDIVIDUAL_STEP)
    _, questions = await _questions(row.game_id)
    _, test_deadline = await sessions.student_deadlines(user.id, row.class_session_id)

    async def moment_ids(fact_set_id: uuid.UUID) -> list[str]:
        stored = await games.fact_set(str(row.game_id), game.role)
        if stored.id != str(fact_set_id):
            raise RuntimeError(f"Debrief {row.id} cites another facts set")
        return [moment.id for moment in stored.facts.seat.moments]

    saved, _ = await commands.finish(
        row.game_id,
        row.class_session_id,
        user.id,
        [q.id for q in questions.questions],
        moment_ids,
        test_deadline,
    )
    return MySummaryOut(summary=await _summary(user.id, row.class_session_id, game.role, saved))


async def staff_summary(
    user: authz.Principal, class_session_id: uuid.UUID, student_id: uuid.UUID
) -> StaffSummaryOut | None:
    """A Student's Explanation and Debrief summary for the staff of the Class
    (`debrief_summaries.read`: its owners and Assistant lecturers, AD-12), each None while not
    sent or not finished; None for every other caller alike (FR-5). The read Studentside and the
    Student report reuse (FR-47)."""
    if not await sessions.class_staff_may(user, class_session_id, "debrief_summaries.read"):
        return None
    async with get_sessionmaker()() as s:
        game = await games.student_game(s, student_id, class_session_id)
    explanation = await _stored(student_id, class_session_id)
    stored = await _summary_row(student_id, class_session_id)
    summary = (
        await _summary(student_id, class_session_id, game.role, stored)
        if stored is not None and game is not None
        else None
    )
    attempts = await _attempts(student_id, class_session_id)
    passing = next((each for each in attempts if each.passed), None)
    return StaffSummaryOut(
        student_id=student_id,
        name=await sessions.student_name(class_session_id, student_id),
        game_id=game.game_id if game else None,
        game_number=game.number if game else None,
        role=Role(game.role) if game else None,
        explanation=explanation,
        summary=summary,
        quiz=StaffQuizAttemptsOut(
            attempts=[
                StaffAttemptOut(
                    number=each.number, submitted_at=each.submitted_at, passed=each.passed
                )
                for each in attempts
            ],
            passed_at=passing.submitted_at if passing else None,
        ),
    )


async def require_debrief(user_id: uuid.UUID, class_session_id: uuid.UUID) -> None:
    """The quiz's gate (Story 9.9, FR-46, AD-16): raises `DebriefRequired` until the Student has
    finished the Debrief (the `debrief` step)."""
    if not await progress.has_step(user_id, class_session_id, progress.Step.DEBRIEF):
        raise DebriefRequired


async def _quiz(game_id: uuid.UUID) -> tuple[int, quiz_rules.DebriefQuiz]:
    """The Debrief quiz the Game's Class session pinned at the lock (the latest for a session
    locked before the pin)."""
    found = await games.get_game(str(game_id))
    pins = found.session_runtime.pins if found and found.session_runtime else None
    return await content.debrief_quiz(content.pinned_version(pins, content.Kind.DEBRIEF_QUIZ))


async def _attempts(user_id: uuid.UUID, class_session_id: uuid.UUID) -> list[commands.AttemptRow]:
    """The Student's quiz attempts in the Class session, by number."""
    async with get_sessionmaker()() as s:
        found = (
            await s.execute(
                select(quiz_attempts)
                .where(
                    quiz_attempts.c.user_id == user_id,
                    quiz_attempts.c.class_session_id == class_session_id,
                )
                .order_by(quiz_attempts.c.number)
            )
        ).mappings()
        return [commands.attempt_of(row) for row in found]


async def _excluded(class_session_id: uuid.UUID) -> set[str]:
    """The questions the Lecturer took out of the Class session's quiz (Story 9.10)."""
    async with get_sessionmaker()() as s:
        return await rules.excluded_questions(s, class_session_id)


def _asked(quiz: quiz_rules.DebriefQuiz, excluded: set[str]) -> list[str]:
    """The questions an attempt answers (Story 9.10, FR-46): those of the version the Lecturer
    has not taken out, in the content's order. Never empty: the last one cannot be taken out, and
    should rows taken out of another version cover every question of this one, all are asked."""
    asked = [question.id for question in quiz.questions if question.id not in excluded]
    return asked or [question.id for question in quiz.questions]


def _order(
    quiz: quiz_rules.DebriefQuiz, user_id: uuid.UUID, number: int, excluded: set[str]
) -> list[str]:
    """The order attempt `number` asks the questions in (FR-46: they may be reshuffled): the
    content's order the first time, then shuffled with a seed of the Student and the attempt, so
    a reload of the same attempt shows the same order."""
    asked = _asked(quiz, excluded)
    if number > 1:
        random.Random(f"{user_id}:{number}").shuffle(asked)
    return asked


def _choices(question: quiz_rules.QuizQuestion) -> list[QuizChoiceOut]:
    return [QuizChoiceOut(id=choice.id, text=choice.text) for choice in question.choices]


async def _result(game_id: uuid.UUID, role: str, attempt: commands.AttemptRow) -> QuizAttemptOut:
    """A stored attempt with each question's result, read with the quiz version it was scored
    with. A wrong answer gets the explanation, ending with the sentence about the Student's own
    Game rendered from the facts set of their Seat (AD-7)."""
    _, quiz = await content.debrief_quiz(attempt.quiz_version)
    stored = None
    results = []
    for answer in attempt.answers:
        question = quiz.question(answer["question_id"])
        explanation = ai_line = None
        if not answer["correct"]:
            if stored is None and question.in_your_game is not None:
                stored = await games.fact_set(str(game_id), role)
            own = quiz_rules.render_in_your_game(stored.facts, question) if stored else None
            text = question.explanation if own is None else f"{question.explanation} {own.text}"
            explanation = RenderedTextOut(text=text)
            if stored is not None and question.in_your_game is not None:
                # Story 9.14: the AI's own-game line, when stored before this attempt.
                found = await _ai_text(
                    uuid.UUID(stored.id), narration.quiz_subject(question.id), attempt.submitted_at
                )
                ai_line = found if found is not None and found.ai_generated else None
        results.append(
            QuizResultOut(
                question_id=question.id,
                prompt=question.prompt,
                choices=_choices(question),
                chosen=answer["choice_id"],
                right_choice=question.answer,
                correct=answer["correct"],
                explanation=explanation,
                ai_explanation=ai_line,
            )
        )
    return QuizAttemptOut(
        number=attempt.number,
        submitted_at=attempt.submitted_at,
        passed=attempt.passed,
        correct=sum(1 for each in results if each.correct),
        asked=len(results),
        results=results,
    )


async def own_quiz(user: authz.Principal, debrief_id: uuid.UUID) -> QuizOut | None:
    """Step 5, the Debrief quiz (Story 9.9, FR-46): the pinned version, the questions of the
    Student's next attempt without the answer key (none once passed) and the latest attempt's
    result. Behind `require_debrief`."""
    found = await _own(user, debrief_id)
    if found is None:
        return None
    row, game = found
    await require_debrief(user.id, row.class_session_id)
    require_step(row, INDIVIDUAL_STEP)
    version, quiz = await _quiz(row.game_id)
    attempts = await _attempts(user.id, row.class_session_id)
    excluded = await _excluded(row.class_session_id)
    last = attempts[-1] if attempts else None
    passed = last is not None and last.passed
    questions = (
        []
        if passed
        else [
            QuizQuestionOut(id=q.id, prompt=q.prompt, choices=_choices(q))
            for q in map(quiz.question, _order(quiz, user.id, len(attempts) + 1, excluded))
        ]
    )
    return QuizOut(
        version=version,
        placeholder=quiz.placeholder,
        attempts=len(attempts),
        passed_at=last.submitted_at if passed and last else None,
        questions=questions,
        last=await _result(row.game_id, game.role, last) if last else None,
    )


async def submit_quiz_mine(
    user: authz.Principal, debrief_id: uuid.UUID, answers: Sequence[tuple[str, str]]
) -> QuizAttemptOut | None:
    """An attempt at the Debrief quiz (Story 9.9, FR-46): scored here by the answer key of the
    pinned version, never by the web app, and stored by `debrief.commands.submit_quiz`, which
    records `quiz_passed` when every asked question is right. Raises `NotAvailable`,
    `DebriefRequired`, `InvalidQuizAnswers`, `commands.QuizPassed` or
    `commands.TestDeadlinePassed`."""
    found = await _own(user, debrief_id)
    if found is None:
        return None
    row, game = found
    await require_debrief(user.id, row.class_session_id)
    require_step(row, INDIVIDUAL_STEP)
    version, quiz = await _quiz(row.game_id)
    excluded = await _excluded(row.class_session_id)
    # A form opened before the Lecturer took a question out still sends its answer: it is left
    # out, never scored or stored (Story 9.10).
    kept = [(question, choice) for question, choice in answers if question not in excluded]
    try:
        scored = quiz_rules.score(quiz, _asked(quiz, excluded), kept)
    except quiz_rules.WrongAnswers as wrong:
        raise InvalidQuizAnswers(wrong.reason) from None
    _, test_deadline = await sessions.student_deadlines(user.id, row.class_session_id)
    saved = await commands.submit_quiz(
        row.game_id,
        row.class_session_id,
        user.id,
        version,
        [each.model_dump() for each in scored.answers],
        test_deadline,
    )
    return await _result(row.game_id, game.role, saved)


async def _staff_quiz_out(
    found: sessions.QuizSession, version: int, quiz: quiz_rules.DebriefQuiz, excluded: set[str]
) -> StaffQuizOut:
    async with get_sessionmaker()() as s:
        now = await s.scalar(select(func.now()))
    return StaffQuizOut(
        version=version,
        placeholder=quiz.placeholder,
        pinned=content.pinned_version(found.pins, content.Kind.DEBRIEF_QUIZ) is not None,
        can_exclude=found.can_exclude,
        open=found.test_deadline is None or now <= found.test_deadline,
        test_deadline=found.test_deadline,
        questions=[
            StaffQuizQuestionOut(
                id=q.id,
                prompt=q.prompt,
                choices=_choices(q),
                answer=q.answer,
                excluded=q.id in excluded,
            )
            for q in quiz.questions
        ],
    )


async def _session_quiz(pins: object) -> tuple[int, quiz_rules.DebriefQuiz]:
    """The Debrief quiz a Class session uses: the version its lock pinned, the latest before."""
    return await content.debrief_quiz(content.pinned_version(pins, content.Kind.DEBRIEF_QUIZ))


async def staff_quiz(user: authz.Principal, class_session_id: uuid.UUID) -> StaffQuizOut | None:
    """The Klasseøkt's «Debrief-quiz» block (Story 9.10, FR-46, AD-12): the Class session's quiz
    with each question's answer key and whether it is taken out, for its owners and Assistant
    lecturers (`debrief_quiz.read`); None for every other caller alike (FR-5)."""
    found = await sessions.quiz_session(user, class_session_id)
    if found is None:
        return None
    version, quiz = await _session_quiz(found.pins)
    return await _staff_quiz_out(found, version, quiz, await _excluded(class_session_id))


async def set_quiz_exclusions(
    user: authz.Principal, class_session_id: uuid.UUID, wanted: Sequence[str]
) -> StaffQuizOut | None:
    """«Lagre quizvalg» (Story 9.10, FR-46, AD-23): `debrief.commands.set_quiz_exclusions` for an
    owner of the Class (`debrief_quiz.exclude`); None for every other caller alike (FR-5). Raises
    `InvalidExclusions`, `commands.LastQuestion`, `commands.TestDeadlinePassed` or
    `classes.ClassArchived` (an archived Class, refused under the Class session's lock)."""
    if not await sessions.class_staff_may(user, class_session_id, "debrief_quiz.exclude"):
        return None
    found = await sessions.quiz_session(user, class_session_id)
    if found is None:
        return None
    loaded: dict[str, quiz_rules.DebriefQuiz] = {}

    async def resolve(pins: object) -> commands.QuizVersion:
        version, quiz = await _session_quiz(pins)
        loaded["quiz"] = quiz
        return commands.QuizVersion(version, tuple(q.id for q in quiz.questions))

    try:
        saved, excluded = await commands.set_quiz_exclusions(
            class_session_id, user.id, wanted, resolve
        )
    except commands.UnknownQuizQuestion:
        raise InvalidExclusions from None
    return await _staff_quiz_out(found, saved.version, loaded["quiz"], set(excluded))


async def due_releases(now: datetime) -> Sequence[str]:
    """The held Class sessions whose Class games have all finished and that are not released yet
    (Story 9.2): ids only."""
    async with get_sessionmaker()() as s:
        held = await sessions.held_debrief_sessions(s)
        if not held:
            return []
        released = set(
            (
                await s.scalars(
                    select(debrief_releases.c.class_session_id).where(
                        debrief_releases.c.class_session_id.in_(held)
                    )
                )
            ).all()
        )
        waiting = [session_id for session_id in held if session_id not in released]
        found = await games.class_games_of(s, waiting)
    return [
        str(session_id)
        for session_id in waiting
        if found.get(session_id)
        and all(game.lifecycle == games.Lifecycle.FINISHED for game in found[session_id])
    ]


async def release_due(class_session_id: object, now: datetime) -> bool:
    """The sweep's act: `debrief.commands.release` for one Class session id."""
    assert isinstance(class_session_id, str)
    return await commands.release(uuid.UUID(class_session_id), now)


async def due_dropouts(now: datetime) -> Sequence[tuple[str, str]]:
    """The joined Students of shared Debrief sessions still on their shared steps who have been
    silent longer than `DROPOUT_AFTER` (Story 9.12, FR-43), as `(game_id, user_id)`. Judged by
    database time, as `leave` judges it again; the sweep's `now` is not used."""
    alone = (
        select(debrief_alone.c.user_id)
        .where(
            debrief_alone.c.debrief_id == debrief_members.c.debrief_id,
            debrief_alone.c.user_id == debrief_members.c.user_id,
        )
        .exists()
    )
    async with get_sessionmaker()() as s:
        found = await s.execute(
            select(debrief_sessions.c.game_id, debrief_members.c.user_id)
            .join(debrief_members, debrief_members.c.debrief_id == debrief_sessions.c.id)
            .where(
                debrief_sessions.c.shared,
                debrief_sessions.c.step < INDIVIDUAL_STEP,
                debrief_sessions.c.fallback_at.is_(None),
                debrief_members.c.last_seen_at < func.now() - DROPOUT_AFTER,
                ~alone,
            )
        )
        return [(str(game_id), str(user_id)) for game_id, user_id in found]


async def drop_out_due(item: object, now: datetime) -> commands.DebriefRow:
    """The sweep's act: `debrief.commands.leave` as a dropout for one `(game_id, user_id)`."""
    assert isinstance(item, tuple)
    game_id, user_id = item
    return await commands.leave(uuid.UUID(game_id), uuid.UUID(user_id), dropout=True)


async def due_fallbacks(now: datetime) -> Sequence[str]:
    """The shared Debrief sessions whose 48-hour fallback is due at `now` (Story 9.12, FR-43):
    not run yet and the pointer still on the shared steps. Ids only."""
    async with get_sessionmaker()() as s:
        found = await s.scalars(
            select(debrief_sessions.c.id).where(
                debrief_sessions.c.shared,
                debrief_sessions.c.fallback_at.is_(None),
                debrief_sessions.c.step < INDIVIDUAL_STEP,
                debrief_sessions.c.fallback_due_at <= now,
            )
        )
        return [str(each) for each in found.all()]


async def fallback_due(debrief_id: object, now: datetime) -> bool:
    """The sweep's act: `debrief.commands.open_personal_fallback` for one Debrief session id."""
    assert isinstance(debrief_id, str)
    return await commands.open_personal_fallback(uuid.UUID(debrief_id))
