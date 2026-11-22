"""The Student's Individual test as their page reads it (Story 11.3, FR-51, FR-5, AD-12, AD-16).

`read` answers the state: `statement` before the Student has accepted the own-work statement (no
item is served), `open` with the items of their attempt in its frozen order, `closed` when their
Test deadline has passed with no attempt. `open_` accepts the statement through
`commands.open_attempt`. Only the Student's own locked Class session is reached; every other
caller gets None (the route's 403 `forbidden`), whether or not an attempt exists."""

import uuid
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from app.modules.content import service as content
from app.modules.content.schemas import QuestionSet
from app.modules.progress import service as progress
from app.modules.sessions import service as sessions
from app.modules.tests import commands
from app.modules.tests.schemas import IndividualItemOut, MyTestOut
from app.platform import authz
from app.platform.db import get_sessionmaker

__all__ = ["read", "open_"]


async def _items(attempt: Mapping[str, Any]) -> list[IndividualItemOut]:
    question_set: QuestionSet = await content.get(
        content.Kind.QUESTION_SET, attempt["question_set_version"]
    )
    titles = {item.id: item.title for item in question_set.items}
    return [
        IndividualItemOut(id=item["id"], number=number, type=item["type"], title=titles[item["id"]])
        for number, item in enumerate(attempt["items"], start=1)
    ]


async def _open(attempt: Mapping[str, Any]) -> MyTestOut:
    return MyTestOut(
        state="open",
        test_deadline=attempt["effective_deadline"],
        opened_at=attempt["statement_accepted_at"],
        items=await _items(attempt),
    )


async def read(
    user: authz.Principal, class_session_id: uuid.UUID, now: datetime
) -> MyTestOut | None:
    """The Student's Individual test; None for every caller but the Student of the Class session
    (FR-5). Raises `commands.ReplayRequired` before the `replay` step (AD-16)."""
    async with get_sessionmaker()() as s:
        found = await sessions.individual_test_session_of(s, user, class_session_id)
        if found is None:
            return None
        attempt = await commands.attempt_of(s, user.id, class_session_id)
    if attempt is not None:
        return await _open(attempt)
    if not await progress.has_step(user.id, class_session_id, progress.Step.REPLAY):
        raise commands.ReplayRequired
    deadline = sessions.effective_test_deadline(user, found.row)
    passed = deadline is not None and deadline <= now
    return MyTestOut(
        state="closed" if passed else "statement", test_deadline=deadline, opened_at=None, items=[]
    )


async def open_(
    user: authz.Principal, class_session_id: uuid.UUID, now: datetime
) -> tuple[MyTestOut, bool] | None:
    """Accept the own-work statement: (the open test, whether this call made the attempt); None
    for every caller but the Student (FR-5). Raises `commands.ReplayRequired` and
    `commands.DeadlinePassed`."""
    opened = await commands.open_attempt(user, class_session_id, now)
    if opened is None:
        return None
    return await _open(opened.attempt), opened.created
