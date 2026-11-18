"""SQL for the identity tables. Only `identity.service` and `identity.seed` call it."""

import uuid
from datetime import datetime

from sqlalchemy import RowMapping, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import password_resets, user_roles, users


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
