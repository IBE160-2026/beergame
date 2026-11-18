"""SQL for the identity tables. Only `identity.service` and `identity.seed` call it."""

import uuid
from datetime import datetime

from sqlalchemy import RowMapping, delete, func, literal, or_, select, text, tuple_, update
from sqlalchemy.dialects.postgresql import aggregate_order_by, array_agg, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import invitations, password_resets, user_roles, users


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
    password_hash: str,
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
