"""The User's own `identity` rows for «Mine data» (Story 15.1, FR-75): the account, its roles,
the test student consent and the Roster entries naming them. By the caller's own id only."""

import uuid

from sqlalchemy import select

from app.modules.identity.models import roster_entries, test_student_consents, user_roles, users
from app.platform.db import get_sessionmaker
from app.platform.own_data import OwnRecord, record


async def own_records(user_id: uuid.UUID) -> dict[str, list[OwnRecord]]:
    async with get_sessionmaker()() as s:
        user = (
            (
                await s.execute(
                    select(users.c.name, users.c.email, users.c.created_at).where(
                        users.c.id == user_id
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        roles = (
            (
                await s.execute(
                    select(user_roles.c.role, user_roles.c.granted_at)
                    .where(user_roles.c.user_id == user_id)
                    .order_by(user_roles.c.granted_at, user_roles.c.role)
                )
            )
            .mappings()
            .all()
        )
        consents = (
            (
                await s.execute(
                    select(test_student_consents)
                    .where(test_student_consents.c.user_id == user_id)
                    .order_by(test_student_consents.c.decided_at)
                )
            )
            .mappings()
            .all()
        )
        entries = (
            (
                await s.execute(
                    select(roster_entries)
                    .where(roster_entries.c.user_id == user_id)
                    .order_by(roster_entries.c.added_at)
                )
            )
            .mappings()
            .all()
        )
    found: list[OwnRecord] = []
    if user is not None:
        found.append(
            record(
                "profile",
                [
                    ("name", "text", user["name"]),
                    ("email", "text", user["email"]),
                    ("created_at", "datetime", user["created_at"]),
                ],
            )
        )
    found += [
        record("role", [("role", "code", r["role"]), ("granted_at", "datetime", r["granted_at"])])
        for r in roles
    ]
    found += [
        record(
            "consent",
            [
                ("decision", "code", c["decision"]),
                ("text_version", "text", c["text_version"]),
                ("decided_at", "datetime", c["decided_at"]),
            ],
            at=c["decided_at"],
        )
        for c in consents
    ]
    found += [
        record(
            "roster_entry",
            [
                ("email", "text", e["email"]),
                ("registration", "code", e["registration"]),
                ("added_at", "datetime", e["added_at"]),
                ("removed_at", "datetime", e["removed_at"]),
            ],
            class_id=e["class_id"],
            at=e["added_at"],
        )
        for e in entries
    ]
    return {"account": found}
