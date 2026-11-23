"""«Lagre retting»: a Lecturer corrects one step of a Student's Completion status with a reason
(Story 13.3, FR-17, FR-3, AD-8, AD-12, AD-15, AD-16).

Only the Lecturers of the Class (`completion.correct`), and only in an Obligatory class session,
since the requirement exists only there. In one transaction: the Class still takes changes, a new
row in `progress`'s `completion_corrections` (never an update: the latest per step applies), one
audit row by ids and codes (the reason stays in the corrections table, which the audit row names
by `correction_id`, AD-14), and `user:<student>` and `session:<id>` so the open Studentside and the
Student's Hjem read it again. A correction records no step event: gates read through
`progress.has_step` and the funnel stay as they are."""

import uuid

from app.modules.classes import service as classes
from app.modules.progress import service as progress
from app.modules.reports import service, studentside
from app.modules.reports.schemas import REASON_MAX_LENGTH, CorrectionIn, StudentRecordOut
from app.modules.reports.studentside import CORRECT
from app.modules.sessions import service as sessions
from app.platform import audit, auth, authz, events
from app.platform.db import get_sessionmaker

__all__ = ["CORRECT", "CORRECTED", "InvalidCorrection", "NotObligatory", "correct"]

CORRECTED = "completion.corrected"
"""The audit action: target the Class session, the Student and the correction; change the step,
the new status and the status before (`was_done`)."""


class InvalidCorrection(Exception):
    """422 `invalid_correction`: `fields.reason` is `required` (empty after trimming) or
    `too_long`."""

    code = "invalid_correction"

    def __init__(self, fields: dict[str, str]) -> None:
        super().__init__(self.code)
        self.fields = fields


class NotObligatory(Exception):
    """409 `not_obligatory`: the Class session has no requirement to correct [ASSUMPTION]."""

    code = "not_obligatory"


def judge(body: CorrectionIn) -> str:
    """The reason to store, trimmed, or `InvalidCorrection`."""
    reason = body.reason.strip()
    if not reason:
        raise InvalidCorrection({"reason": "required"})
    if len(reason) > REASON_MAX_LENGTH:
        raise InvalidCorrection({"reason": "too_long"})
    return reason


async def correct(
    user: authz.Principal, class_session_id: uuid.UUID, user_id: uuid.UUID, body: CorrectionIn
) -> StudentRecordOut | None:
    """Store the correction and answer the Studentside's record as it now stands; None (403) for
    anyone but a Lecturer of the Class and for a User who is no Student of it (FR-5). Raises
    `InvalidCorrection`, `NotObligatory` or `classes.ClassArchived`; nothing is written then."""
    reached = await sessions.student_target(user, class_session_id, user_id, CORRECT)
    if reached is None:
        return None
    reason = judge(body)
    now = auth.utcnow()
    async with get_sessionmaker().begin() as s:
        if not await classes.is_writable(reached.class_id, session=s):
            raise classes.ClassArchived
        terms = await sessions.completion_terms(s, class_session_id)
        if terms is None:
            return None
        if not terms.obligatory:
            raise NotObligatory
        was = await service.completion_status(user_id, class_session_id, session=s)
        correction_id = await progress.record_correction(
            s,
            user_id=user_id,
            class_session_id=class_session_id,
            step=body.step,
            done=body.done,
            reason=reason,
            actor_user_id=user.id,
            at=now,
        )
        await audit.record(
            s,
            user.id,
            CORRECTED,
            {
                "class_session_id": class_session_id,
                "user_id": user_id,
                "correction_id": correction_id,
            },
            {
                "step": body.step,
                "done": body.done,
                "was_done": None if was is None else was.step(body.step).done,
            },
            now,
        )
        await events.emit(s, "user", str(user_id))
        await events.emit(s, "session", str(class_session_id))
    return await studentside.student_record(user, class_session_id, user_id)
