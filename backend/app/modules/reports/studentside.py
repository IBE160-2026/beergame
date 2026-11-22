"""The Studentside's record of one Student (Story 13.2, FR-63, FR-17, FR-5, AD-12, AD-16).

One page per Student for the Lecturers and Assistant lecturers of the Class: the Completion status
per step from the one assembler (`service.completion_status`), the participation signals (pure
`analysis.participation`, information only), and each part read through its owning module's
`service.py`: the game (`games`), the Explanation, the Debrief summary and the quiz attempts
(`debrief.staff_summary`), the Replay (`replay`), the Individual test (`tests`) and the AI
assessment's state (`assessment`). `reports` reads no table itself.

Reach: `sessions.service.student_target` with `student_page.read`; None (403) is one answer for a
Class session that does not exist, a Class outside the caller's scope, an Admin without a staff
role, and a User who is no Student of the Class now (FR-5)."""

import uuid

from app.analysis.participation import TimedOrder, participation
from app.modules.assessment import service as assessment
from app.modules.debrief import service as debrief
from app.modules.games import service as games
from app.modules.replay import service as replay
from app.modules.reports import service
from app.modules.reports.schemas import (
    CompletionOut,
    CompletionStepOut,
    ParticipationOut,
    RecordAssessmentOut,
    RecordDebriefOut,
    RecordGameOut,
    RecordQuizAttemptOut,
    RecordReplayOut,
    RecordTestOut,
    StudentRecordOut,
)
from app.modules.sessions import service as sessions
from app.modules.tests import service as tests
from app.platform import authz
from app.platform.db import get_sessionmaker

__all__ = ["READ", "student_record"]

READ = "student_page.read"
"""The Class action of the Studentside's record (Story 13.2): owners and Assistant lecturers."""


def _completion(found, adjusted: bool) -> CompletionOut:
    return CompletionOut(
        obligatory=found.obligatory,
        requirement_met=found.requirement_met,
        required_share=found.required_share,
        adjusted=adjusted,
        ordered_share=found.ordered_share,
        playout_share=found.playout_share,
        steps=[
            CompletionStepOut(
                step=step.step,
                recorded=step.recorded,
                recorded_at=step.recorded_at,
                done=step.done,
                corrected=step.corrected,
            )
            for step in found.steps
        ],
    )


def _game_state(status: games.PlayStatus) -> str:
    if status.status == "finished" and status.end_reason is not None:
        return "ended"
    return status.status


async def student_record(
    user: authz.Principal, class_session_id: uuid.UUID, user_id: uuid.UUID
) -> StudentRecordOut | None:
    """The Studentside's record of `user_id` in the Class session, or None (403)."""
    reached = await sessions.student_target(user, class_session_id, user_id, READ)
    if reached is None:
        return None
    staffed = await sessions.staffed_session(user, class_session_id, READ)
    if staffed is None:
        return None
    can_manage = await sessions.class_staff_may(user, class_session_id, "class_sessions.manage")
    game_out = participation_out = replay_out = None
    async with get_sessionmaker()() as s:
        adjustment = await sessions.get_adjustment(s, class_session_id, user_id)
        switch = await assessment.switch_of(s, class_session_id)
        game = await games.student_game(s, user_id, class_session_id)
        if game is not None:
            status = await games.play_status(s, game.game_id)
            game_out = RecordGameOut(
                game_id=game.game_id,
                number=game.number,
                role=game.role,
                state=_game_state(status),
                played_out=status.played_out,
                finished_at=await games.finished_at(s, game.game_id),
            )
            timing = await games.seat_timing(s, game.game_id, game.role)
            if timing is not None:
                signals = participation(
                    [TimedOrder(*row) for row in timing.rows], timing.guided_weeks
                )
                participation_out = ParticipationOut(
                    own_orders=signals.own_orders,
                    seconds=signals.seconds,
                    constant=signals.constant,
                    after_guided=signals.after_guided,
                )
        replay_game = await replay.replay_game_of(s, user_id, class_session_id)
        if replay_game is not None:
            replay_out = RecordReplayOut(
                game_id=replay_game, finished_at=await games.finished_at(s, replay_game)
            )
    completion = await service.completion_status(user_id, class_session_id)
    staff = await debrief.staff_summary(user, class_session_id, user_id)
    if staff is None:
        return None
    attempt = await tests.attempt_summary(user_id, class_session_id)
    explanation = staff.explanation
    summary = staff.summary
    return StudentRecordOut(
        class_session_id=class_session_id,
        class_id=staffed.class_id,
        class_name=staffed.class_name,
        session_number=staffed.number,
        user_id=user_id,
        name=reached.name,
        can_manage=can_manage,
        completion=(
            None
            if completion is None
            else _completion(
                completion, adjustment is not None and adjustment.share_percent is not None
            )
        ),
        participation=participation_out,
        game=game_out,
        debrief=RecordDebriefOut(
            explanation=explanation.text if explanation else None,
            explanation_saved_at=explanation.saved_at if explanation else None,
            finished_at=summary.finished_at if summary else None,
            late=summary.late if summary else False,
            moments=len(summary.moments) if summary else 0,
        ),
        quiz=[
            RecordQuizAttemptOut(number=a.number, submitted_at=a.submitted_at, passed=a.passed)
            for a in staff.quiz.attempts
        ],
        replay=replay_out,
        test=(
            None
            if attempt is None
            else RecordTestOut(
                status=attempt.status, submitted_at=attempt.submitted_at, parts=attempt.parts
            )
        ),
        assessment=RecordAssessmentOut(state="not_ready" if switch.enabled else "off"),
    )
