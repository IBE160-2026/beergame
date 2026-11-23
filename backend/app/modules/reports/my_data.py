"""«Mine data» (Story 15.1, FR-75, FR-5, AD-12, AD-14): everything the product stores about the
calling User, by category, for the right of access.

`my_data(user)` asks the own-data reader of every owning module (`<module>.service.own_records`,
`platform.own_data`) with the principal's own id, never an id from the request, and names each
row's Class and Klasseøkt through `sessions` and `classes`. Other Students never appear: the
readers filter by the caller's id, `authz.own_seat` or `authz.messages_addressed_to`. The page
reads it once; each «Vis» opens a category. Reading one's own data is not audited (as `/me`)."""

import uuid

from sqlalchemy import select

from app.modules.assessment import service as assessment
from app.modules.classes import service as classes
from app.modules.debrief import service as debrief
from app.modules.games import service as games
from app.modules.identity import service as identity
from app.modules.messaging import service as messaging
from app.modules.progress import service as progress
from app.modules.replay import service as replay
from app.modules.reports.models import makeup_games
from app.modules.reports.schemas import MyDataCategoryOut, MyDataFieldOut, MyDataItemOut, MyDataOut
from app.modules.sessions import service as sessions
from app.modules.tests import service as tests
from app.platform import authz
from app.platform.db import get_sessionmaker
from app.platform.own_data import CATEGORIES, OwnRecord, merge, record

__all__ = ["READ_OWN", "my_data"]

READ_OWN = "my_data.read_own"
"""The policy: any logged-in User, for their own data only (FR-5)."""

SHOWN_WHEN_ANY: frozenset[str] = frozenset({"adjustments"})
"""Categories listed only when they hold something (UX-DR67: «tilrettelegging if any»)."""


async def _makeups(user_id: uuid.UUID) -> dict[str, list[OwnRecord]]:
    """The Student's Oppfølgingsspill (Story 13.4); who gave it is not named."""
    async with get_sessionmaker()() as s:
        rows = (
            (await s.execute(select(makeup_games).where(makeup_games.c.user_id == user_id)))
            .mappings()
            .all()
        )
    return {
        "game": [
            record("makeup", [], class_session_id=row["class_session_id"], at=row["given_at"])
            for row in rows
        ]
    }


async def my_data(user: authz.Principal) -> MyDataOut:
    me = user.id
    found = merge(
        await identity.own_records(me),
        await games.own_records(me),
        await replay.own_records(me),
        await _makeups(me),
        await debrief.own_records(me),
        await tests.own_records(me),
        await assessment.own_records(me),
        await sessions.own_records(me),
        await messaging.own_records(me),
        await progress.own_records(me),
    )
    every = [r for records in found.values() for r in records]
    session_ids = sorted({r.class_session_id for r in every if r.class_session_id}, key=str)
    class_ids = sorted({r.class_id for r in every if r.class_id}, key=str)
    async with get_sessionmaker()() as s:
        listed = {item.id: item for item in await sessions.evaluation_sessions(s, session_ids)}
        labels = await classes.class_labels(s, class_ids)

    def item(each: OwnRecord) -> MyDataItemOut:
        session = listed.get(each.class_session_id) if each.class_session_id else None
        label = labels.get(each.class_id) if each.class_id else None
        return MyDataItemOut(
            kind=each.kind,
            class_name=session.class_name if session else (label.name if label else None),
            session_number=session.number if session else None,
            at=each.at,
            fields=[MyDataFieldOut(key=f.key, kind=f.kind, value=f.value) for f in each.fields],
        )

    return MyDataOut(
        categories=[
            MyDataCategoryOut(key=key, items=[item(each) for each in found.get(key, [])])
            for key in CATEGORIES
            if key not in SHOWN_WHEN_ANY or found.get(key)
        ]
    )
