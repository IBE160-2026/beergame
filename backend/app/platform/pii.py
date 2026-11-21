"""The personal-data terms the AI gateway scrubs from free text (AD-6, C-1, Story 9.15).

`terms(scope)` is called by the gateway only (an import test keeps it so). For a Class session it
is a read-only query over the `identity` tables, by table name only (`platform` imports no
module): the Class's Roster, whether still on it or removed, and the Class's staff give

- every User's name, whole and each of its words of three letters or more (a first name typed
  alone; shorter words and digits would scrub «de», «av» or a Week out of every question),
- every e-mail address and its local part (`kari.nordmann`),
- every non-empty cell of 3 characters or more of a Roster upload the Class still has staged
  (the only place a student number, or a name before the Student registered, is stored).

The gateway's scrub adds a backstop to these terms: any e-mail address and any long digit run
(`app.ai.scrub`). An evaluation scope (simulation runs, the Control test) has no Roster: its list
is empty, as is the list of a scope id that is no Class session.
"""

import re
import uuid
from typing import Protocol

from sqlalchemy import column, select, table, union

from app.platform.db import get_sessionmaker

__all__ = ["terms"]

_class_sessions = table("class_sessions", column("id"), column("class_id"))
_roster_entries = table("roster_entries", column("class_id"), column("user_id"), column("email"))
_class_staff = table("class_staff", column("class_id"), column("user_id"))
_users = table("users", column("id"), column("name"), column("email"))
_roster_uploads = table("roster_uploads", column("id"), column("class_id"))
_roster_upload_rows = table("roster_upload_rows", column("upload_id"), column("cells"))
"""`sessions`, `identity` and `classes` tables by name only."""

_WORD = re.compile(r"[^\W\d_]{3,}")

MIN_CELL = 3
"""The shortest staged Roster cell scrubbed: shorter ones (a «1», a «Ja») would scrub ordinary
words and numbers out of every question."""


class Scope(Protocol):
    @property
    def kind(self) -> str: ...

    @property
    def id(self) -> uuid.UUID: ...


def _name_terms(name: str) -> set[str]:
    found = {name.strip()}
    found.update(_WORD.findall(name))
    return found


def _email_terms(email: str) -> set[str]:
    address = email.strip()
    return {address, address.split("@", 1)[0]} if address else set()


async def terms(scope: Scope) -> list[str]:
    """The terms to scrub for `scope`; empty for an evaluation scope."""
    if scope.kind == "evaluation":
        return []
    async with get_sessionmaker()() as session:
        class_id = await session.scalar(
            select(_class_sessions.c.class_id).where(_class_sessions.c.id == scope.id)
        )
        if class_id is None:
            return []
        people = union(
            select(_roster_entries.c.user_id).where(_roster_entries.c.class_id == class_id),
            select(_class_staff.c.user_id).where(_class_staff.c.class_id == class_id),
        ).subquery()
        users = (
            await session.execute(
                select(_users.c.name, _users.c.email).where(_users.c.id.in_(select(people)))
            )
        ).all()
        addresses = await session.scalars(
            select(_roster_entries.c.email).where(_roster_entries.c.class_id == class_id)
        )
        cells = await session.scalars(
            select(_roster_upload_rows.c.cells)
            .join(_roster_uploads, _roster_uploads.c.id == _roster_upload_rows.c.upload_id)
            .where(_roster_uploads.c.class_id == class_id)
        )
        found: set[str] = set()
        for name, email in users:
            found |= _name_terms(name or "")
            found |= _email_terms(email or "")
        for address in addresses:
            found |= _email_terms(address or "")
        for row in cells:
            for cell in row or []:
                text = str(cell).strip()
                if len(text) >= MIN_CELL:
                    found.add(text)
    return sorted(term for term in found if term)
