"""The Student's own `progress` rows for «Mine data» (Story 15.1, FR-75): the steps they reached
and the corrections of their Completion status with the Lecturer's reason (Story 13.3). By the
caller's own id only; the Lecturer who corrected is not named."""

import uuid

from sqlalchemy import select

from app.modules.progress.models import completion_corrections, progress_steps
from app.platform.db import get_sessionmaker
from app.platform.own_data import OwnRecord, record


async def own_records(user_id: uuid.UUID) -> dict[str, list[OwnRecord]]:
    p, c = progress_steps, completion_corrections
    async with get_sessionmaker()() as s:
        steps = (
            (await s.execute(select(p).where(p.c.user_id == user_id).order_by(p.c.at)))
            .mappings()
            .all()
        )
        corrections = (
            (await s.execute(select(c).where(c.c.user_id == user_id).order_by(c.c.at)))
            .mappings()
            .all()
        )
    found = [
        record(
            "step",
            [("step", "code", row["step"])],
            class_session_id=row["class_session_id"],
            at=row["at"],
        )
        for row in steps
    ]
    found += [
        record(
            "correction",
            [
                ("step", "code", row["step"]),
                ("done", "bool", row["done"]),
                ("reason", "text", row["reason"]),
            ],
            class_session_id=row["class_session_id"],
            at=row["at"],
        )
        for row in corrections
    ]
    return {"completion": found}
