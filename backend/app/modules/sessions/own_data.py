"""The Student's own `sessions` rows for «Mine data» (Story 15.1, FR-75): their Tilrettelegging
(time factor and share), their own Test and Debrief deadlines (Story 11.13) and the deadline
reminders sent to them alone. By the caller's own id only."""

import uuid

from sqlalchemy import select

from app.modules.sessions.models import (
    deadline_reminders,
    student_adjustments,
    student_deadline_extensions,
)
from app.platform.db import get_sessionmaker
from app.platform.own_data import OwnRecord, record


async def own_records(user_id: uuid.UUID) -> dict[str, list[OwnRecord]]:
    a, e, r = student_adjustments, student_deadline_extensions, deadline_reminders
    async with get_sessionmaker()() as s:
        adjustments = (await s.execute(select(a).where(a.c.user_id == user_id))).mappings().all()
        extensions = (await s.execute(select(e).where(e.c.user_id == user_id))).mappings().all()
        reminders = (
            (await s.execute(select(r).where(r.c.user_id == user_id).order_by(r.c.created_at)))
            .mappings()
            .all()
        )
    adjusted = [
        record(
            "adjustment",
            [
                ("time_factor", "number", row["time_factor"]),
                ("share_percent", "number", row["share_percent"]),
            ],
            class_session_id=row["class_session_id"],
            at=row["updated_at"],
        )
        for row in adjustments
    ]
    adjusted += [
        record(
            "extension",
            [
                ("test_deadline", "datetime", row["test_deadline"]),
                ("debrief_deadline", "datetime", row["debrief_deadline"]),
            ],
            class_session_id=row["class_session_id"],
            at=row["updated_at"],
        )
        for row in extensions
    ]
    return {
        "adjustments": adjusted,
        "messages": [
            record(
                "reminder",
                [
                    ("deadline", "code", row["deadline"]),
                    ("deadline_at", "datetime", row["deadline_at"]),
                ],
                class_session_id=row["class_session_id"],
                at=row["created_at"],
            )
            for row in reminders
        ],
    }
