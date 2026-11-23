"""The Student's own `replay` rows for «Mine data» (Story 15.1, FR-75): their Replay, their
answer to «another round» and the stored walkthrough narration of their Replay. By the caller's
own id only."""

import uuid

from sqlalchemy import select

from app.modules.replay.models import replay_another_round, replay_walkthroughs, replays
from app.platform.db import get_sessionmaker
from app.platform.own_data import OwnRecord, record


async def own_records(user_id: uuid.UUID) -> dict[str, list[OwnRecord]]:
    r, a, w = replays, replay_another_round, replay_walkthroughs
    async with get_sessionmaker()() as s:
        found_replays = (await s.execute(select(r).where(r.c.user_id == user_id))).mappings().all()
        answers = (await s.execute(select(a).where(a.c.user_id == user_id))).mappings().all()
        walks = (await s.execute(select(w).where(w.c.user_id == user_id))).mappings().all()
    found = [
        record("replay", [], class_session_id=row["class_session_id"], at=row["created_at"])
        for row in found_replays
    ]
    found += [
        record(
            "another_round",
            [("answer", "bool", row["answer"])],
            class_session_id=row["class_session_id"],
            at=row["created_at"],
        )
        for row in answers
    ]
    found += [
        record(
            "walkthrough",
            [
                ("narration", "text", row["narration_text"]),
                ("ai_generated", "bool", row["narration_ai_generated"]),
            ],
            class_session_id=row["class_session_id"],
            at=row["created_at"],
        )
        for row in walks
    ]
    return {"game": found}
