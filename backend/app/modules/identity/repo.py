"""SQL for the identity tables. Only `identity.service` and `identity.seed` call it."""

import uuid
from datetime import datetime

from sqlalchemy import RowMapping, delete, func, literal, or_, select, text, tuple_, update
from sqlalchemy.dialects.postgresql import aggregate_order_by, array_agg, distinct_on, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import (
    access_requests,
    institutions,
    invitations,
    password_resets,
    roster_entries,
    roster_upload_rows,
    roster_uploads,
    user_roles,
    users,
)


async def user_by_email(session: AsyncSession, email: str) -> RowMapping | None:
    result = await session.execute(select(users).where(users.c.email == email))
    return result.mappings().one_or_none()


async def user_by_id(session: AsyncSession, user_id: uuid.UUID) -> RowMapping | None:
    result = await session.execute(select(users).where(users.c.id == user_id))
    return result.mappings().one_or_none()


async def roles_of(session: AsyncSession, user_id: uuid.UUID) -> list[str]:
    result = await session.execute(
        select(user_roles.c.role).where(user_roles.c.user_id == user_id).order_by(user_roles.c.role)
    )
    return list(result.scalars())


async def insert_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    email: str,
    name: str,
    password_hash: str | None,
    is_active: bool,
    roles: list[str],
) -> None:
    await session.execute(
        users.insert().values(
            id=user_id, email=email, name=name, password_hash=password_hash, is_active=is_active
        )
    )
    if roles:
        await session.execute(
            user_roles.insert(), [{"user_id": user_id, "role": role} for role in roles]
        )


async def insert_password_reset(
    session: AsyncSession,
    *,
    reset_id: uuid.UUID,
    user_id: uuid.UUID,
    token_hash: str,
    created_at: datetime,
    expires_at: datetime,
) -> None:
    await session.execute(
        password_resets.insert().values(
            id=reset_id,
            user_id=user_id,
            token_hash=token_hash,
            created_at=created_at,
            expires_at=expires_at,
        )
    )


async def password_reset_by_id(session: AsyncSession, reset_id: uuid.UUID) -> RowMapping | None:
    result = await session.execute(select(password_resets).where(password_resets.c.id == reset_id))
    return result.mappings().one_or_none()


async def password_reset_by_hash(session: AsyncSession, token_hash: str) -> RowMapping | None:
    result = await session.execute(
        select(password_resets).where(password_resets.c.token_hash == token_hash)
    )
    return result.mappings().one_or_none()


async def lock_user(session: AsyncSession, user_id: uuid.UUID) -> RowMapping | None:
    """The User, locked until the transaction ends: password changes of one User run in turn."""
    result = await session.execute(select(users).where(users.c.id == user_id).with_for_update())
    return result.mappings().one_or_none()


async def set_password_hash(
    session: AsyncSession, user_id: uuid.UUID, password_hash: str, now: datetime
) -> None:
    await session.execute(
        update(users)
        .where(users.c.id == user_id)
        .values(password_hash=password_hash, updated_at=now)
    )


async def close_password_resets(
    session: AsyncSession, *, used_id: uuid.UUID, user_id: uuid.UUID, now: datetime
) -> None:
    """Mark `used_id` used and void every other open reset of the User."""
    await session.execute(
        update(password_resets).where(password_resets.c.id == used_id).values(used_at=now)
    )
    await session.execute(
        update(password_resets)
        .where(
            password_resets.c.user_id == user_id,
            password_resets.c.id != used_id,
            password_resets.c.used_at.is_(None),
            password_resets.c.voided_at.is_(None),
        )
        .values(voided_at=now)
    )


async def lock_invitation_address(session: AsyncSession, email: str, role: str) -> None:
    """Serialise Invitations to one address and role until the transaction ends."""
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": f"invitation:{email}:{role}"},
    )


async def void_open_invitations(
    session: AsyncSession, *, email: str, role: str, now: datetime
) -> list[uuid.UUID]:
    """Void every open Invitation to `email` for `role`; returns their ids."""
    result = await session.execute(
        update(invitations)
        .where(
            invitations.c.email == email,
            invitations.c.role == role,
            invitations.c.accepted_at.is_(None),
            invitations.c.voided_at.is_(None),
        )
        .values(voided_at=now)
        .returning(invitations.c.id)
    )
    return sorted(result.scalars())


async def insert_invitation(
    session: AsyncSession,
    *,
    invitation_id: uuid.UUID,
    email: str,
    role: str,
    token_hash: str,
    created_at: datetime,
    expires_at: datetime,
    invited_by: uuid.UUID | None,
) -> None:
    await session.execute(
        invitations.insert().values(
            id=invitation_id,
            email=email,
            role=role,
            token_hash=token_hash,
            created_at=created_at,
            expires_at=expires_at,
            invited_by=invited_by,
        )
    )


async def invitation_by_id(session: AsyncSession, invitation_id: uuid.UUID) -> RowMapping | None:
    result = await session.execute(select(invitations).where(invitations.c.id == invitation_id))
    return result.mappings().one_or_none()


async def invitation_by_hash(session: AsyncSession, token_hash: str) -> RowMapping | None:
    result = await session.execute(
        select(invitations).where(invitations.c.token_hash == token_hash)
    )
    return result.mappings().one_or_none()


async def lock_invitation(session: AsyncSession, invitation_id: uuid.UUID) -> RowMapping | None:
    """The Invitation, locked until the transaction ends: one acceptance at a time."""
    result = await session.execute(
        select(invitations).where(invitations.c.id == invitation_id).with_for_update()
    )
    return result.mappings().one_or_none()


async def lock_user_address(session: AsyncSession, email: str) -> None:
    """Serialise account creation for one address until the transaction ends."""
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": f"user:{email}"}
    )


async def mark_invitation_accepted(
    session: AsyncSession, invitation_id: uuid.UUID, now: datetime
) -> None:
    await session.execute(
        update(invitations).where(invitations.c.id == invitation_id).values(accepted_at=now)
    )


async def set_renewal_requested(
    session: AsyncSession, invitation_id: uuid.UUID, now: datetime
) -> None:
    await session.execute(
        update(invitations)
        .where(invitations.c.id == invitation_id)
        .values(renewal_requested_at=now)
    )


async def open_invitation(session: AsyncSession, email: str, role: str) -> RowMapping | None:
    """The Invitation to `email` for `role` that is neither accepted nor voided (it may be
    expired), or None."""
    result = await session.execute(
        select(invitations).where(
            invitations.c.email == email,
            invitations.c.role == role,
            invitations.c.accepted_at.is_(None),
            invitations.c.voided_at.is_(None),
        )
    )
    return result.mappings().one_or_none()


async def grant_role(session: AsyncSession, user_id: uuid.UUID, role: str) -> bool:
    """Give the User `role`; False when they already hold it."""
    result = await session.execute(
        insert(user_roles)
        .values(user_id=user_id, role=role)
        .on_conflict_do_nothing()
        .returning(user_roles.c.role)
    )
    return result.scalar_one_or_none() is not None


def _like_pattern(search: str) -> str:
    """A case-insensitive substring pattern for `search`, with LIKE's own characters literal."""
    escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


async def list_users(
    session: AsyncSession,
    *,
    search: str,
    after: uuid.UUID | None,
    limit: int,
) -> list[RowMapping] | None:
    """Up to `limit` Users ordered by `(lower(name), id)`, after the User `after` when given (an
    unknown `after` gives None), each with its roles (sorted). `search` (may be empty) matches
    a substring of the e-mail or the name, case-insensitively."""
    sort_name = func.lower(users.c.name)
    if after is not None:
        found = await session.execute(select(sort_name).where(users.c.id == after))
        after_name = found.scalar_one_or_none()
        if after_name is None:
            return None
    roles = (
        select(array_agg(aggregate_order_by(user_roles.c.role, user_roles.c.role)))
        .where(user_roles.c.user_id == users.c.id)
        .scalar_subquery()
    )
    query = select(
        users.c.id,
        users.c.name,
        users.c.email,
        users.c.is_active,
        roles.label("roles"),
    )
    if search:
        pattern = _like_pattern(search)
        query = query.where(
            or_(users.c.email.ilike(pattern, escape="\\"), users.c.name.ilike(pattern, escape="\\"))
        )
    if after is not None:
        query = query.where(
            tuple_(sort_name, users.c.id) > tuple_(literal(after_name), literal(after))
        )
    query = query.order_by(sort_name, users.c.id).limit(limit)
    result = await session.execute(query)
    return list(result.mappings())


async def remove_role(session: AsyncSession, user_id: uuid.UUID, role: str) -> bool:
    """Take `role` from the User; False when they did not hold it."""
    result = await session.execute(
        delete(user_roles)
        .where(user_roles.c.user_id == user_id, user_roles.c.role == role)
        .returning(user_roles.c.role)
    )
    return result.scalar_one_or_none() is not None


async def count_active_holders(session: AsyncSession, role: str, *, excluding: uuid.UUID) -> int:
    """How many active Users other than `excluding` hold `role`."""
    result = await session.execute(
        select(func.count())
        .select_from(user_roles.join(users, users.c.id == user_roles.c.user_id))
        .where(user_roles.c.role == role, users.c.is_active, users.c.id != excluding)
    )
    return result.scalar_one()


async def lock_role(session: AsyncSession, role: str) -> None:
    """Serialise changes to who holds `role` until the transaction ends."""
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": f"role:{role}"}
    )


async def invitation_ids_for_email(session: AsyncSession, email: str) -> list[uuid.UUID]:
    result = await session.execute(
        select(invitations.c.id).where(invitations.c.email == email).order_by(invitations.c.id)
    )
    return list(result.scalars())


# Deactivation and reactivation (Story 3.10).


async def set_active(
    session: AsyncSession, user_id: uuid.UUID, is_active: bool, now: datetime
) -> None:
    await session.execute(
        update(users).where(users.c.id == user_id).values(is_active=is_active, updated_at=now)
    )


async def bump_session_version(session: AsyncSession, user_id: uuid.UUID) -> None:
    """End every session issued to the User so far."""
    await session.execute(
        update(users)
        .where(users.c.id == user_id)
        .values(session_version=users.c.session_version + 1)
    )


async def void_open_password_resets(
    session: AsyncSession, user_id: uuid.UUID, now: datetime
) -> None:
    """Void every unused reset link of the User, so none works again after a reactivation."""
    await session.execute(
        update(password_resets)
        .where(
            password_resets.c.user_id == user_id,
            password_resets.c.used_at.is_(None),
            password_resets.c.voided_at.is_(None),
        )
        .values(voided_at=now)
    )


async def void_open_invitations_to(session: AsyncSession, email: str, now: datetime) -> None:
    """Void every open Invitation to `email`, whatever its role."""
    await session.execute(
        update(invitations)
        .where(
            invitations.c.email == email,
            invitations.c.accepted_at.is_(None),
            invitations.c.voided_at.is_(None),
        )
        .values(voided_at=now)
    )


# The Invitation list and resending (Story 3.10).


async def list_invitations(
    session: AsyncSession, *, after: uuid.UUID | None, limit: int
) -> list[RowMapping] | None:
    """The newest Invitation of each address and role, newest first, after the Invitation `after`
    when given (an unknown `after` gives None). Each row has `renewal_requested`: whether any
    Invitation of its address and role holds a renewal request, and `account_deactivated`:
    whether its address belongs to a deactivated User."""
    if after is not None:
        found = await session.execute(
            select(invitations.c.id).where(invitations.c.id == after, invitations.c.kind == "role")
        )
        if found.scalar_one_or_none() is None:
            return None
    newest = (
        select(invitations)
        .where(invitations.c.kind == "role")
        .ext(distinct_on(invitations.c.email, invitations.c.role))
        .order_by(invitations.c.email, invitations.c.role, invitations.c.id.desc())
        .subquery()
    )
    asked = invitations.alias("asked")
    requested = (
        select(asked.c.id)
        .where(
            asked.c.email == newest.c.email,
            asked.c.role == newest.c.role,
            asked.c.renewal_requested_at.is_not(None),
        )
        .exists()
    )
    deactivated = (
        select(users.c.id)
        .where(users.c.email == newest.c.email, users.c.is_active.is_(False))
        .exists()
    )
    query = select(
        newest, requested.label("renewal_requested"), deactivated.label("account_deactivated")
    )
    if after is not None:
        query = query.where(newest.c.id < after)
    result = await session.execute(query.order_by(newest.c.id.desc()).limit(limit))
    return list(result.mappings())


async def newest_invitation_id(session: AsyncSession, email: str, role: str) -> uuid.UUID | None:
    """The id of the newest Invitation to `email` for `role` (ids are UUIDv7: time-ordered)."""
    result = await session.execute(
        select(invitations.c.id)
        .where(invitations.c.email == email, invitations.c.role == role)
        .order_by(invitations.c.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def clear_renewal_requests(session: AsyncSession, email: str, role: str) -> None:
    """A new Invitation answers every request for one to this address and role."""
    await session.execute(
        update(invitations)
        .where(
            invitations.c.email == email,
            invitations.c.role == role,
            invitations.c.renewal_requested_at.is_not(None),
        )
        .values(renewal_requested_at=None)
    )


# Institutions (Story 3.11).


async def lock_institution_names(session: AsyncSession) -> None:
    """Serialise creating and renaming Institutions until the transaction ends, so two writes of
    one name cannot both pass the check for a taken name."""
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": "institution_names"},
    )


async def institution_name_taken(
    session: AsyncSession, name: str, *, excluding: uuid.UUID | None = None
) -> bool:
    """Whether another Institution has `name`, compared case-insensitively by Postgres's own
    `lower()`, the function `uq_institutions_name` uses (Python's `str.lower` differs for some
    letters, such as «İ»)."""
    query = select(institutions.c.id).where(
        func.lower(institutions.c.name) == func.lower(literal(name))
    )
    if excluding is not None:
        query = query.where(institutions.c.id != excluding)
    result = await session.execute(query.limit(1))
    return result.scalar_one_or_none() is not None


async def institution_id_by_name(session: AsyncSession, name: str) -> uuid.UUID | None:
    """The id of the Institution named `name`, compared as `institution_name_taken` does."""
    result = await session.execute(
        select(institutions.c.id)
        .where(func.lower(institutions.c.name) == func.lower(literal(name)))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def insert_institution(
    session: AsyncSession, institution_id: uuid.UUID, name: str, now: datetime
) -> RowMapping:
    result = await session.execute(
        insert(institutions)
        .values(id=institution_id, name=name, created_at=now, updated_at=now)
        .returning(institutions)
    )
    return result.mappings().one()


async def lock_institution(session: AsyncSession, institution_id: uuid.UUID) -> RowMapping | None:
    result = await session.execute(
        select(institutions).where(institutions.c.id == institution_id).with_for_update()
    )
    return result.mappings().one_or_none()


async def rename_institution(
    session: AsyncSession, institution_id: uuid.UUID, name: str, now: datetime
) -> RowMapping:
    result = await session.execute(
        update(institutions)
        .where(institutions.c.id == institution_id)
        .values(name=name, updated_at=now)
        .returning(institutions)
    )
    return result.mappings().one()


async def institution_by_id(session: AsyncSession, institution_id: uuid.UUID) -> RowMapping | None:
    result = await session.execute(select(institutions).where(institutions.c.id == institution_id))
    return result.mappings().one_or_none()


async def all_institutions(session: AsyncSession) -> list[RowMapping]:
    """Every Institution, by name (case-insensitively), then id."""
    result = await session.execute(
        select(institutions).order_by(func.lower(institutions.c.name), institutions.c.id)
    )
    return list(result.mappings())


async def list_institutions(
    session: AsyncSession, *, after: uuid.UUID | None, limit: int
) -> list[RowMapping] | None:
    """Up to `limit` Institutions, newest first (ids are UUIDv7), after the Institution `after`
    when given (an unknown `after` gives None)."""
    if after is not None and await institution_by_id(session, after) is None:
        return None
    query = select(institutions)
    if after is not None:
        query = query.where(institutions.c.id < after)
    result = await session.execute(query.order_by(institutions.c.id.desc()).limit(limit))
    return list(result.mappings())


async def labels_of(
    session: AsyncSession, table: str, ids: list[uuid.UUID]
) -> dict[uuid.UUID, str]:
    """`id → name` of Users, Institutions and access requests' senders, `id → e-mail address` of
    Invitations, for the audit page (Stories 3.12, 3.13)."""
    source, column = {
        "users": (users, users.c.name),
        "invitations": (invitations, invitations.c.email),
        "institutions": (institutions, institutions.c.name),
        "access_requests": (access_requests, access_requests.c.name),
    }[table]
    result = await session.execute(select(source.c.id, column).where(source.c.id.in_(ids)))
    return {row[0]: row[1] for row in result}


# Requests for lecturer access (Story 3.13).


async def upsert_access_request(
    session: AsyncSession,
    *,
    request_id: uuid.UUID,
    name: str,
    email: str,
    institution: str,
    now: datetime,
) -> uuid.UUID:
    """Store an open request, or update the open request of the same address (name, Institution
    and time); returns the id of the open row."""
    statement = (
        insert(access_requests)
        .values(
            id=request_id,
            name=name,
            email=email,
            institution=institution,
            requested_at=now,
            status="open",
        )
        .on_conflict_do_update(
            index_elements=[access_requests.c.email],
            index_where=access_requests.c.status == "open",
            set_={"name": name, "institution": institution, "requested_at": now},
        )
        .returning(access_requests.c.id)
    )
    return (await session.execute(statement)).scalar_one()


async def list_open_access_requests(
    session: AsyncSession, *, after: uuid.UUID | None, limit: int
) -> list[RowMapping] | None:
    """Up to `limit` open requests, newest first by `(requested_at, id)`, after the request
    `after` when given (an unknown `after` gives None)."""
    query = select(access_requests).where(access_requests.c.status == "open")
    if after is not None:
        anchor = (
            await session.execute(
                select(access_requests.c.requested_at).where(access_requests.c.id == after)
            )
        ).scalar_one_or_none()
        if anchor is None:
            return None
        query = query.where(
            tuple_(access_requests.c.requested_at, access_requests.c.id)
            < tuple_(literal(anchor), literal(after))
        )
    result = await session.execute(
        query.order_by(access_requests.c.requested_at.desc(), access_requests.c.id.desc()).limit(
            limit
        )
    )
    return list(result.mappings())


async def lock_open_access_request(
    session: AsyncSession, request_id: uuid.UUID
) -> RowMapping | None:
    """The open request `request_id`, locked for the caller's transaction, or None."""
    result = await session.execute(
        select(access_requests)
        .where(access_requests.c.id == request_id, access_requests.c.status == "open")
        .with_for_update()
    )
    return result.mappings().one_or_none()


async def close_access_request(
    session: AsyncSession,
    request_id: uuid.UUID,
    *,
    status: str,
    actor: uuid.UUID,
    now: datetime,
    invitation_id: uuid.UUID | None = None,
) -> None:
    await session.execute(
        update(access_requests)
        .where(access_requests.c.id == request_id)
        .values(status=status, closed_at=now, closed_by=actor, invitation_id=invitation_id)
    )


# Staged Roster uploads (Story 4.2).


async def purge_expired_roster_uploads(session: AsyncSession, now: datetime) -> int:
    """Delete every staged upload whose `expires_at` has passed; the rows go with it (CASCADE)."""
    result = await session.execute(delete(roster_uploads).where(roster_uploads.c.expires_at <= now))
    return result.rowcount or 0


async def lock_roster_staging(session: AsyncSession, class_id: uuid.UUID) -> None:
    """Hold the Class's staging lock until the caller's transaction ends."""
    await session.execute(
        select(func.pg_advisory_xact_lock(func.hashtextextended(f"roster:{class_id}", 0)))
    )


async def delete_roster_upload(session: AsyncSession, class_id: uuid.UUID) -> bool:
    result = await session.execute(
        delete(roster_uploads).where(roster_uploads.c.class_id == class_id)
    )
    return bool(result.rowcount)


async def insert_roster_upload(
    session: AsyncSession,
    *,
    upload_id: uuid.UUID,
    class_id: uuid.UUID,
    uploaded_by: uuid.UUID,
    file_name: str,
    headers: list[str],
    has_header: bool,
    rows: list[tuple[int, list[str]]],
    chosen_column: int | None,
    now: datetime,
    expires_at: datetime,
    source: str = "file",
) -> None:
    await session.execute(
        insert(roster_uploads).values(
            id=upload_id,
            source=source,
            class_id=class_id,
            uploaded_by=uploaded_by,
            file_name=file_name,
            headers=headers,
            has_header=has_header,
            column_count=len(headers),
            row_count=len(rows),
            chosen_column=chosen_column,
            created_at=now,
            expires_at=expires_at,
        )
    )
    batch = 1000
    for start in range(0, len(rows), batch):
        await session.execute(
            insert(roster_upload_rows),
            [
                {"upload_id": upload_id, "row_number": number, "cells": cells}
                for number, cells in rows[start : start + batch]
            ],
        )


async def roster_upload_for_class(
    session: AsyncSession, class_id: uuid.UUID, now: datetime, *, lock: bool = False
) -> RowMapping | None:
    """The Class's staged upload, unless it has expired."""
    query = select(roster_uploads).where(
        roster_uploads.c.class_id == class_id, roster_uploads.c.expires_at > now
    )
    if lock:
        query = query.with_for_update()
    result = await session.execute(query)
    return result.mappings().one_or_none()


async def set_roster_column(session: AsyncSession, upload_id: uuid.UUID, column: int) -> None:
    await session.execute(
        update(roster_uploads).where(roster_uploads.c.id == upload_id).values(chosen_column=column)
    )


async def roster_rows(session: AsyncSession, upload_id: uuid.UUID) -> list[tuple[int, list[str]]]:
    """(row number, cells) of every staged row, in the file's order."""
    result = await session.execute(
        select(roster_upload_rows.c.row_number, roster_upload_rows.c.cells)
        .where(roster_upload_rows.c.upload_id == upload_id)
        .order_by(roster_upload_rows.c.row_number)
    )
    return [(row.row_number, row.cells) for row in result]


# The Roster and Student Invitations (Story 4.4).

ROSTER_BATCH = 1000
"""Rows per INSERT statement when a Roster is written."""


async def roster_addresses(session: AsyncSession, class_id: uuid.UUID) -> set[str]:
    """Every address on the Class's Roster that has not been removed."""
    result = await session.execute(
        select(roster_entries.c.email).where(
            roster_entries.c.class_id == class_id, roster_entries.c.removed_at.is_(None)
        )
    )
    return set(result.scalars())


async def insert_roster_entries(
    session: AsyncSession, class_id: uuid.UUID, emails: list[str], registration: str, now: datetime
) -> list[RowMapping]:
    """Add each address to the Roster. An address on it that was removed is put back as it was
    (Story 4.8); one on it and not removed is left as it is. The `id`, `email`, `registration` and
    `user_id` of each entry added or put back."""
    added: list[RowMapping] = []
    batch = ROSTER_BATCH
    for start in range(0, len(emails), batch):
        stmt = insert(roster_entries).values(
            [
                {
                    "id": uuid.uuid7(),
                    "class_id": class_id,
                    "email": email,
                    "registration": registration,
                    "added_at": now,
                }
                for email in emails[start : start + batch]
            ]
        )
        result = await session.execute(
            stmt.on_conflict_do_update(
                index_elements=[roster_entries.c.class_id, roster_entries.c.email],
                set_={"removed_at": None},
                where=roster_entries.c.removed_at.is_not(None),
            ).returning(
                roster_entries.c.id,
                roster_entries.c.email,
                roster_entries.c.registration,
                roster_entries.c.user_id,
            )
        )
        added.extend(result.mappings())
    return added


async def insert_student_invitations(session: AsyncSession, values: list[dict]) -> None:
    """Store Student Invitations, each a dict of `invitations` columns."""
    batch = ROSTER_BATCH
    for start in range(0, len(values), batch):
        await session.execute(insert(invitations), values[start : start + batch])


async def roster_entry_by_id(
    session: AsyncSession, entry_id: uuid.UUID, *, lock: bool = False
) -> RowMapping | None:
    """The Roster entry; with `lock`, locked until the transaction ends."""
    query = select(roster_entries).where(roster_entries.c.id == entry_id)
    result = await session.execute(query.with_for_update() if lock else query)
    return result.mappings().one_or_none()


async def register_roster_entry(
    session: AsyncSession, entry_id: uuid.UUID, user_id: uuid.UUID, registration: str
) -> bool:
    """Link a Roster entry that is not removed to its User and mark it registered (Story 4.5).
    False when the entry is gone or removed (nothing changes)."""
    result = await session.execute(
        update(roster_entries)
        .where(roster_entries.c.id == entry_id, roster_entries.c.removed_at.is_(None))
        .values(user_id=user_id, registration=registration)
        .returning(roster_entries.c.id)
    )
    return result.scalar_one_or_none() is not None


async def ensure_registered_entry(
    session: AsyncSession,
    class_id: uuid.UUID,
    email: str,
    user_id: uuid.UUID,
    registration: str,
    now: datetime,
) -> bool:
    """For the local seed: a registered Roster entry linked to the User, unless the address is
    on the Roster already (left as it is). True when added."""
    result = await session.execute(
        insert(roster_entries)
        .values(
            id=uuid.uuid7(),
            class_id=class_id,
            email=email,
            user_id=user_id,
            registration=registration,
            added_at=now,
        )
        .on_conflict_do_nothing(index_elements=[roster_entries.c.class_id, roster_entries.c.email])
        .returning(roster_entries.c.id)
    )
    return result.scalar_one_or_none() is not None


async def roster_counts(session: AsyncSession, class_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    """How many addresses each Class has on its Roster (removed ones left out)."""
    if not class_ids:
        return {}
    result = await session.execute(
        select(roster_entries.c.class_id, func.count())
        .where(roster_entries.c.class_id.in_(class_ids), roster_entries.c.removed_at.is_(None))
        .group_by(roster_entries.c.class_id)
    )
    return {row[0]: row[1] for row in result}


async def class_student_invitations(session: AsyncSession, class_id: uuid.UUID) -> list[RowMapping]:
    """Every Student Invitation of the Class with its Roster entry's address and standing
    (Story 4.6), by Invitation id (a UUIDv7, so in the order they were made)."""
    result = await session.execute(
        select(
            invitations.c.id,
            invitations.c.roster_entry_id,
            invitations.c.accepted_at,
            invitations.c.voided_at,
            invitations.c.expires_at,
            roster_entries.c.email,
            roster_entries.c.registration,
            roster_entries.c.removed_at,
        )
        .join(roster_entries, roster_entries.c.id == invitations.c.roster_entry_id)
        .where(invitations.c.class_id == class_id, invitations.c.kind == "student")
        .order_by(invitations.c.id)
    )
    return list(result.mappings())


# Registration status and reminders (Story 4.7).


async def class_roster_facts(session: AsyncSession, class_id: uuid.UUID) -> list[RowMapping]:
    """Every Roster entry of the Class that has not been removed, by address, with its newest
    Student Invitation (by id, a UUIDv7: the last one made; NULL columns when none) and whether
    a Student asked for a new one from any of its links that was not accepted."""
    newest = (
        select(
            invitations.c.roster_entry_id,
            invitations.c.id.label("invitation_id"),
            invitations.c.expires_at,
            invitations.c.accepted_at,
            invitations.c.voided_at,
        )
        .where(invitations.c.class_id == class_id, invitations.c.kind == "student")
        .ext(distinct_on(invitations.c.roster_entry_id))
        .order_by(invitations.c.roster_entry_id, invitations.c.id.desc())
        .subquery()
    )
    asked = (
        select(invitations.c.roster_entry_id)
        .where(
            invitations.c.class_id == class_id,
            invitations.c.kind == "student",
            invitations.c.accepted_at.is_(None),
            invitations.c.renewal_requested_at.is_not(None),
        )
        .distinct()
        .subquery()
    )
    result = await session.execute(
        select(
            roster_entries.c.id,
            roster_entries.c.email,
            roster_entries.c.registration,
            newest.c.invitation_id,
            newest.c.expires_at,
            newest.c.accepted_at,
            newest.c.voided_at,
            asked.c.roster_entry_id.is_not(None).label("renewal_requested"),
        )
        .outerjoin(newest, newest.c.roster_entry_id == roster_entries.c.id)
        .outerjoin(asked, asked.c.roster_entry_id == roster_entries.c.id)
        .where(roster_entries.c.class_id == class_id, roster_entries.c.removed_at.is_(None))
        .order_by(roster_entries.c.email)
    )
    return list(result.mappings())


async def void_open_entry_invitations(
    session: AsyncSession, class_id: uuid.UUID, entry_ids: list[uuid.UUID], now: datetime
) -> None:
    """Void every Student Invitation of these entries that is neither accepted nor voided. The
    update waits for an acceptance that holds an Invitation's lock, and then leaves it out."""
    await session.execute(
        update(invitations)
        .where(
            invitations.c.class_id == class_id,
            invitations.c.roster_entry_id.in_(entry_ids),
            invitations.c.accepted_at.is_(None),
            invitations.c.voided_at.is_(None),
        )
        .values(voided_at=now)
    )


async def clear_entry_renewals(
    session: AsyncSession, class_id: uuid.UUID, entry_ids: list[uuid.UUID]
) -> None:
    """Answer the requests for a new Invitation of these entries: a new one is on its way."""
    await session.execute(
        update(invitations)
        .where(
            invitations.c.class_id == class_id,
            invitations.c.roster_entry_id.in_(entry_ids),
            invitations.c.renewal_requested_at.is_not(None),
        )
        .values(renewal_requested_at=None)
    )


async def remindable_entries(
    session: AsyncSession, class_id: uuid.UUID, entry_ids: list[uuid.UUID], registration: str
) -> list[tuple[uuid.UUID, str]]:
    """The `(id, email)` of those entries of the Class that are still `registration` and not
    removed, by id: read after the void, so an acceptance that committed meanwhile is seen."""
    if not entry_ids:
        return []
    result = await session.execute(
        select(roster_entries.c.id, roster_entries.c.email)
        .where(
            roster_entries.c.class_id == class_id,
            roster_entries.c.id.in_(entry_ids),
            roster_entries.c.registration == registration,
            roster_entries.c.removed_at.is_(None),
        )
        .order_by(roster_entries.c.id)
    )
    return [(row.id, row.email) for row in result]


async def registered_user_ids(
    session: AsyncSession, class_id: uuid.UUID, registrations: list[str]
) -> list[uuid.UUID]:
    """The Users of the Class's entries that are in `registrations`, not removed, by User id."""
    result = await session.execute(
        select(roster_entries.c.user_id)
        .where(
            roster_entries.c.class_id == class_id,
            roster_entries.c.registration.in_(registrations),
            roster_entries.c.removed_at.is_(None),
            roster_entries.c.user_id.is_not(None),
        )
        .order_by(roster_entries.c.user_id)
    )
    return list(result.scalars())


# Single addresses and manual registration (Story 4.8).


async def roster_entry_by_email(
    session: AsyncSession, class_id: uuid.UUID, email: str, *, lock: bool = False
) -> RowMapping | None:
    """The Class's Roster entry for the address, removed or not; with `lock`, locked until the
    transaction ends."""
    query = select(roster_entries).where(
        roster_entries.c.class_id == class_id, roster_entries.c.email == email
    )
    result = await session.execute(query.with_for_update() if lock else query)
    return result.mappings().one_or_none()


async def class_roster_entry(
    session: AsyncSession, class_id: uuid.UUID, entry_id: uuid.UUID, *, lock: bool = False
) -> RowMapping | None:
    """The Roster entry if it belongs to the Class; with `lock`, locked until the transaction
    ends."""
    query = select(roster_entries).where(
        roster_entries.c.class_id == class_id, roster_entries.c.id == entry_id
    )
    result = await session.execute(query.with_for_update() if lock else query)
    return result.mappings().one_or_none()


async def insert_roster_entry(
    session: AsyncSession,
    class_id: uuid.UUID,
    email: str,
    registration: str,
    now: datetime,
    user_id: uuid.UUID | None = None,
) -> uuid.UUID:
    entry_id = uuid.uuid7()
    await session.execute(
        insert(roster_entries).values(
            id=entry_id,
            class_id=class_id,
            email=email,
            user_id=user_id,
            registration=registration,
            added_at=now,
        )
    )
    return entry_id


async def restore_roster_entry(session: AsyncSession, entry_id: uuid.UUID) -> None:
    """Put a removed entry back on the Roster as it was."""
    await session.execute(
        update(roster_entries).where(roster_entries.c.id == entry_id).values(removed_at=None)
    )


async def register_entry_manually(
    session: AsyncSession, entry_id: uuid.UUID, user_id: uuid.UUID, registration: str
) -> None:
    """Link the entry to its User, set its registration and put it back if it was removed."""
    await session.execute(
        update(roster_entries)
        .where(roster_entries.c.id == entry_id)
        .values(user_id=user_id, registration=registration, removed_at=None)
    )


async def remove_roster_entry(session: AsyncSession, entry_id: uuid.UUID, now: datetime) -> None:
    await session.execute(
        update(roster_entries).where(roster_entries.c.id == entry_id).values(removed_at=now)
    )


async def delete_staged_row(
    session: AsyncSession, class_id: uuid.UUID, upload_id: uuid.UUID, row_number: int
) -> bool:
    """Delete one row of the Class's staged upload `upload_id`. Whether it was there."""
    result = await session.execute(
        delete(roster_upload_rows)
        .where(
            roster_upload_rows.c.upload_id == upload_id,
            roster_upload_rows.c.row_number == row_number,
            roster_upload_rows.c.upload_id.in_(
                select(roster_uploads.c.id).where(roster_uploads.c.class_id == class_id)
            ),
        )
        .returning(roster_upload_rows.c.row_number)
    )
    return result.scalar_one_or_none() is not None


async def newest_open_password_reset(
    session: AsyncSession, user_id: uuid.UUID, now: datetime
) -> RowMapping | None:
    """The User's newest reset link that is neither used, voided nor expired at `now` (by id, a
    UUIDv7: the last one made)."""
    result = await session.execute(
        select(password_resets)
        .where(
            password_resets.c.user_id == user_id,
            password_resets.c.used_at.is_(None),
            password_resets.c.voided_at.is_(None),
            password_resets.c.expires_at > now,
        )
        .order_by(password_resets.c.id.desc())
        .limit(1)
    )
    return result.mappings().one_or_none()


# Assistant lecturer Invitations (Story 4.9). Their Class is `class_id`; they name no Roster entry
# and no account role.


def _open_assistant(class_id: uuid.UUID):
    return (
        invitations.c.kind == "assistant",
        invitations.c.class_id == class_id,
        invitations.c.accepted_at.is_(None),
        invitations.c.voided_at.is_(None),
    )


async def void_assistant_invitations(
    session: AsyncSession,
    class_id: uuid.UUID,
    now: datetime,
    *,
    email: str | None = None,
    invitation_id: uuid.UUID | None = None,
) -> list[uuid.UUID]:
    """Void the Class's open Assistant Invitations, to `email` or the one `invitation_id` when
    given; returns their ids."""
    query = update(invitations).where(*_open_assistant(class_id))
    if email is not None:
        query = query.where(invitations.c.email == email)
    if invitation_id is not None:
        query = query.where(invitations.c.id == invitation_id)
    result = await session.execute(query.values(voided_at=now).returning(invitations.c.id))
    return sorted(result.scalars())


async def void_class_invitations(
    session: AsyncSession, class_id: uuid.UUID, now: datetime
) -> list[uuid.UUID]:
    """Void every open Invitation of the Class, of any kind (an archived Class, Story 4.10); returns
    their ids. One that has expired already is left as it is, so it still counts as expired."""
    result = await session.execute(
        update(invitations)
        .where(
            invitations.c.class_id == class_id,
            invitations.c.accepted_at.is_(None),
            invitations.c.voided_at.is_(None),
            invitations.c.expires_at > now,
        )
        .values(voided_at=now)
        .returning(invitations.c.id)
    )
    return sorted(result.scalars())


async def insert_assistant_invitation(
    session: AsyncSession,
    *,
    invitation_id: uuid.UUID,
    class_id: uuid.UUID,
    email: str,
    token_hash: str,
    created_at: datetime,
    expires_at: datetime,
    invited_by: uuid.UUID,
) -> None:
    await session.execute(
        invitations.insert().values(
            id=invitation_id,
            kind="assistant",
            class_id=class_id,
            email=email,
            token_hash=token_hash,
            created_at=created_at,
            expires_at=expires_at,
            invited_by=invited_by,
        )
    )


async def assistant_invitations(session: AsyncSession, class_id: uuid.UUID) -> list[RowMapping]:
    """The Class's Assistant Invitations that are neither accepted nor voided (open or expired),
    at most one per address by the partial unique index."""
    result = await session.execute(
        select(invitations.c.id, invitations.c.email, invitations.c.expires_at)
        .where(*_open_assistant(class_id))
        .order_by(invitations.c.email, invitations.c.id)
    )
    return list(result.mappings())


async def people(session: AsyncSession, ids: list[uuid.UUID]) -> list[RowMapping]:
    """Name and address of these Users."""
    if not ids:
        return []
    result = await session.execute(
        select(users.c.id, users.c.name, users.c.email).where(users.c.id.in_(ids))
    )
    return list(result.mappings())
