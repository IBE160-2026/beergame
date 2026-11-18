"""SQL for the classes tables. Only `classes.service` and `classes.seed` call it.

Every query on Class rows for a User joins through `authz.classes_visible_to` (AD-12): a Class
outside the User's scope is never read, so it cannot be told apart from one that does not exist.
"""

import uuid
from datetime import datetime

from sqlalchemy import RowMapping, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.classes.models import class_staff, classes
from app.modules.classes.schemas import StaffRole
from app.platform import authz


async def insert_class(
    session: AsyncSession,
    *,
    class_id: uuid.UUID,
    name: str,
    course_code: str | None,
    institution_id: uuid.UUID,
    owner: uuid.UUID,
    now: datetime,
) -> None:
    """The Class and its owner, in the caller's transaction."""
    await session.execute(
        insert(classes).values(
            id=class_id,
            name=name,
            course_code=course_code,
            institution_id=institution_id,
            created_by=owner,
            created_at=now,
        )
    )
    await session.execute(
        insert(class_staff).values(
            class_id=class_id, user_id=owner, role=StaffRole.owner.value, added_at=now
        )
    )


def _visible(user: authz.Principal | uuid.UUID):
    """The Class columns with the User's staff role, inside the User's scope."""
    user_id = user if isinstance(user, uuid.UUID) else user.id
    return (
        select(classes, class_staff.c.role.label("staff_role"))
        .join(
            class_staff,
            (class_staff.c.class_id == classes.c.id) & (class_staff.c.user_id == user_id),
        )
        .where(classes.c.id.in_(authz.classes_visible_to(user)))
    )


async def classes_of(session: AsyncSession, user: authz.Principal) -> list[RowMapping]:
    """The Classes the User is staff of, by name (case-insensitively), then id."""
    result = await session.execute(
        _visible(user).order_by(func.lower(classes.c.name), classes.c.id)
    )
    return list(result.mappings())


async def class_for(
    session: AsyncSession, user: authz.Principal, class_id: uuid.UUID
) -> RowMapping | None:
    """The Class with the User's staff role, or None when it is outside the User's scope or
    does not exist (the same answer)."""
    result = await session.execute(_visible(user).where(classes.c.id == class_id))
    return result.mappings().one_or_none()


async def count_owned_active(session: AsyncSession, user_id: uuid.UUID) -> int:
    """How many Classes that are not archived the User owns."""
    result = await session.execute(
        _visible(user_id)
        .with_only_columns(func.count())
        .where(class_staff.c.role == StaffRole.owner.value, classes.c.archived_at.is_(None))
    )
    return result.scalar_one()


async def any_class_of(session: AsyncSession, user_id: uuid.UUID) -> bool:
    """Whether the User is staff of any Class, archived or not. For the local seed."""
    result = await session.execute(_visible(user_id).with_only_columns(classes.c.id).limit(1))
    return result.first() is not None
