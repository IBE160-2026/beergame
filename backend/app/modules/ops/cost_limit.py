"""The cost-limit notice (Story 15.6, FR-69, AD-9).

Epic 2 records when a Class session's players' limit is reached (`players_exhausted_at` on its
budget row) and switches its LLM Seats to Rule-based players; it sends nothing. This due action of
the sweep finds those Class sessions through `ai.budget` (so `app/ai` imports no module, and a lost
event is repaired on the next sweep) and tells every owner of the Class once, through
`platform/notify.enqueue` with the key `ai_cost_limit:<class session>:<owner>`, in the product and
by mail. The kind is a `digest` in `messaging`'s delivery table.
"""

import uuid
from collections.abc import Sequence
from datetime import datetime

from app.ai import budget
from app.modules.sessions import service as sessions
from app.platform import notify
from app.platform.db import get_sessionmaker

COST_LIMIT_NOTICE = "ai_cost_limit"
"""The notice kind, `digest` (`messaging.delivery.KINDS`)."""


def notice_key(class_session_id: uuid.UUID, user_id: uuid.UUID) -> str:
    """One notice per Class session and owner."""
    return f"{COST_LIMIT_NOTICE}:{class_session_id}:{user_id}"


async def due_sessions(now: datetime) -> Sequence[uuid.UUID]:
    """The Class sessions whose players' limit is reached and an owner of whose Class has not
    been told yet."""
    del now
    found = []
    async with get_sessionmaker()() as s:
        for class_session_id in await budget.exhausted_class_sessions(session=s):
            owners = await sessions.class_session_owners(s, class_session_id)
            keys = [notice_key(class_session_id, owner) for owner in owners]
            if len(await notify.used_keys(s, keys)) < len(keys):
                found.append(class_session_id)
    return found


async def notice_due(class_session_id: object, now: datetime) -> int:
    """Tell each owner of the Class not told yet, in one transaction. Returns how many notices
    were stored now."""
    del now
    assert isinstance(class_session_id, uuid.UUID)
    told = 0
    async with get_sessionmaker().begin() as s:
        state = await budget.state(budget.BudgetScope.class_session(class_session_id), session=s)
        if state is None or state.players_exhausted_at is None:
            return 0
        for owner in await sessions.class_session_owners(s, class_session_id):
            key = notice_key(class_session_id, owner)
            if await notify.enqueue(s, owner, COST_LIMIT_NOTICE, key, ref=class_session_id):
                told += 1
    return told
