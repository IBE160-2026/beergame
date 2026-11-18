"""SQL for the identity tables. Only `identity.service` and `identity.seed` call it."""

import uuid

from sqlalchemy import RowMapping, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import user_roles, users


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
