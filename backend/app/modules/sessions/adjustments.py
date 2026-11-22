"""The Studentside and its block «Tilrettelegging» (Story 8.9, FR-17, UX-DR53, AD-12, AD-14).

A Lecturer of the Class gives one Student more time before an AI player takes their Seat (a factor
of 1, 1.5, 2 or 3 on the Inactivity limit) and a lower share of Weeks. Only the Lecturers of the
Class read or change it (`class_sessions.manage`); an Assistant lecturer is refused like anyone
outside the Class (FR-5). The adjustment is personal data: it is audited by ids and values, and
never written to a log line, a mail or another Student's view. Saving recomputes the open turn
times of the Student's Class game at once (`games.commands.recompute_turn_times`)."""

import uuid
from decimal import Decimal

from app.modules.games import commands as games_commands
from app.modules.games import service as games_service
from app.modules.sessions import repo
from app.modules.sessions.models import TIME_FACTORS
from app.modules.sessions.schemas import AdjustmentIn, StudentPageOut
from app.modules.sessions.service import (
    StudentTarget,
    _writable,
    adjustment_out,
    deadlines_out,
    get_adjustment,
    required_share,
    student_target,
)
from app.platform import audit, auth, authz, events
from app.platform.db import get_sessionmaker

__all__ = ["ADJUSTMENT_SAVED", "InvalidAdjustment", "save_adjustment", "student_page"]

ADJUSTMENT_SAVED = "student_adjustment.saved"
"""The audit action of «Lagre tilrettelegging»: target the Class session and the Student, change
the factor and the share (ids and values only, AD-15)."""

OFFERED = frozenset(Decimal(factor) for factor in TIME_FACTORS)


class InvalidAdjustment(Exception):
    """422 `invalid_adjustment`: `fields` names each refused field and why (`time_factor`
    `not_offered`, `share_percent` `out_of_range`)."""

    code = "invalid_adjustment"

    def __init__(self, fields: dict[str, str]) -> None:
        super().__init__(self.code)
        self.fields = fields


async def _reach(
    user: authz.Principal, session_id: uuid.UUID, user_id: uuid.UUID
) -> StudentTarget | None:
    """The Studentside's target (`service.student_target`): None, one answer, for anything else
    (FR-5)."""
    return await student_target(user, session_id, user_id)


async def _page(
    reached: StudentTarget, session_id: uuid.UUID, user_id: uuid.UUID
) -> StudentPageOut:
    async with get_sessionmaker()() as s:
        number = await repo.number_of(s, session_id, reached.class_id)
        adjustment = await get_adjustment(s, session_id, user_id)
        deadlines = await deadlines_out(s, reached.row, user_id)
    return StudentPageOut(
        class_session_id=session_id,
        class_id=reached.class_id,
        class_name=reached.class_name,
        session_number=number,
        user_id=user_id,
        name=reached.name,
        class_share=required_share(reached.row),
        adjustment=adjustment_out(adjustment),
        deadlines=deadlines,
    )


async def student_page(
    user: authz.Principal, session_id: uuid.UUID, user_id: uuid.UUID
) -> StudentPageOut | None:
    """The Studentside of `user_id` in the Class session (Story 8.9), or None (403)."""
    reached = await _reach(user, session_id, user_id)
    if reached is None:
        return None
    return await _page(reached, session_id, user_id)


def judge(body: AdjustmentIn, class_share: int) -> tuple[Decimal, int | None]:
    """The factor and the share to store, or `InvalidAdjustment`: the factor is one of those
    offered (it never shortens a limit), the share a whole percent from 0 to the class share (it
    never raises the requirement). A share equal to the class share is stored as the class's own
    (None), so it follows the Class session."""
    problems: dict[str, str] = {}
    try:
        factor = Decimal(str(body.time_factor)).quantize(Decimal("0.1"))
    except ArithmeticError:
        factor = Decimal(0)
    if factor not in OFFERED or Decimal(str(body.time_factor)) != factor:
        problems["time_factor"] = "not_offered"
    share = body.share_percent
    if share is not None and not 0 <= share <= class_share:
        problems["share_percent"] = "out_of_range"
    if problems:
        raise InvalidAdjustment(problems)
    return factor, None if share == class_share else share


async def save_adjustment(
    user: authz.Principal, session_id: uuid.UUID, user_id: uuid.UUID, body: AdjustmentIn
) -> StudentPageOut | None:
    """«Lagre tilrettelegging» (Story 8.9, FR-17, AD-8, AD-15): stores the factor and the share,
    records the change in the audit log and emits `user:<student>` and `session:<id>`, all in one
    transaction; then the Student's Class game recomputes its open turn times, so automatic
    Takeover and the Varselbånd follow at once. Also after the Start date. None (403) as
    `student_page`; raises `InvalidAdjustment` or `ClassArchived`."""
    reached = await _reach(user, session_id, user_id)
    if reached is None:
        return None
    factor, share = judge(body, required_share(reached.row))
    now = auth.utcnow()
    async with get_sessionmaker().begin() as s:
        await _writable(s, reached.class_id)
        was = await get_adjustment(s, session_id, user_id)
        if factor == 1 and share is None:
            # «Som klassen» and the class share: nothing about the Student is kept.
            await repo.delete_adjustment(s, session_id, user_id)
        else:
            await repo.save_adjustment(
                s,
                class_session_id=session_id,
                user_id=user_id,
                time_factor=factor,
                share_percent=share,
                updated_by=user.id,
                updated_at=now,
            )
        await audit.record(
            s,
            user.id,
            ADJUSTMENT_SAVED,
            {"class_session_id": session_id, "user_id": user_id},
            {
                "time_factor": str(factor),
                "share_percent": share,
                "was": None
                if was is None
                else {"time_factor": str(was.time_factor), "share_percent": was.share_percent},
            },
            now,
        )
        await events.emit(s, "user", str(user_id))
        await events.emit(s, "session", str(session_id))
        game = await games_service.student_game(s, user_id, session_id)
    if game is not None:
        try:
            await games_commands.recompute_turn_times(str(game.game_id))
        except games_commands.CommandError:
            pass  # a game gone meanwhile has no turn to recompute
    return await _page(reached, session_id, user_id)
