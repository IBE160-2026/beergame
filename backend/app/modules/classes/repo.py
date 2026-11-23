"""SQL for the classes tables. Only `classes.service` and `classes.seed` call it.

Every query on Class rows for a User joins through `authz.classes_visible_to` (AD-12): a Class
outside the User's scope is never read, so it cannot be told apart from one that does not exist.
"""

import uuid
from datetime import datetime

from sqlalchemy import RowMapping, delete, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.classes.models import class_staff, classes
from app.modules.classes.schemas import StaffRole
from app.platform import authz
from app.platform.collation import nb_sort_sql


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


_control_test = classes.c.id.in_(authz.control_test_classes())
"""Whether a Class is a Control test Class (Story 12.7, AD-27): it holds a `control_test` Class
session."""


def _visible(user: authz.Principal | uuid.UUID):
    """The Class columns with the User's staff role, inside the User's scope."""
    user_id = user if isinstance(user, uuid.UUID) else user.id
    return (
        select(classes, class_staff.c.role.label("staff_role"), _control_test.label("control_test"))
        .join(
            class_staff,
            (class_staff.c.class_id == classes.c.id) & (class_staff.c.user_id == user_id),
        )
        .where(classes.c.id.in_(authz.classes_visible_to(user)))
    )


async def classes_of(session: AsyncSession, user: authz.Principal) -> list[RowMapping]:
    """The Classes the User is staff of, by name (Norwegian order), then id. A Control test
    Class is never among them (Story 12.7, AD-13): it is reached from the Admin-område only."""
    result = await session.execute(
        _visible(user).where(~_control_test).order_by(nb_sort_sql(classes.c.name), classes.c.id)
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
        .where(
            class_staff.c.role == StaffRole.owner.value,
            classes.c.archived_at.is_(None),
            ~_control_test,
        )
    )
    return result.scalar_one()


async def any_class_of(session: AsyncSession, user_id: uuid.UUID) -> bool:
    """Whether the User is staff of any Class, archived or not. For the local seed."""
    result = await session.execute(_visible(user_id).with_only_columns(classes.c.id).limit(1))
    return result.first() is not None


async def class_label(session: AsyncSession, class_id: uuid.UUID) -> RowMapping | None:
    """The Class's name, course code, archive time and whether it is a Control test, for its
    Invitations' mail, «Du er invitert» and its Roster rule (no User's scope: the Invitation names
    the Class by id)."""
    result = await session.execute(
        select(
            classes.c.name,
            classes.c.course_code,
            classes.c.archived_at,
            _control_test.label("control_test"),
        ).where(classes.c.id == class_id)
    )
    return result.mappings().one_or_none()


async def labels_of(session: AsyncSession, class_ids: list[uuid.UUID]) -> list[RowMapping]:
    """The name, course code and Institution of these Classes, for the Admin's evaluation export
    (Story 15.4): no User's scope, the Admin names Class sessions by id."""
    result = await session.execute(
        select(classes.c.id, classes.c.name, classes.c.course_code, classes.c.institution_id).where(
            classes.c.id.in_(class_ids)
        )
    )
    return list(result.mappings())


async def class_rows(session: AsyncSession, class_ids: list[uuid.UUID]) -> list[RowMapping]:
    """The Classes with these ids, no User's scope (Story 12.7: the Admin's Kontrolltest list,
    behind its own policy)."""
    if not class_ids:
        return []
    result = await session.execute(
        select(classes.c.id, classes.c.name, classes.c.institution_id, classes.c.archived_at).where(
            classes.c.id.in_(class_ids)
        )
    )
    return list(result.mappings())


def _enrolled(user: authz.Principal | uuid.UUID):
    """The Classes the User is a Student in, through the Student scope (Story 4.5, AD-12). An
    archived Class is left out: nothing in it is open to a Student (Story 4.10)."""
    return select(classes.c.id, classes.c.name, classes.c.course_code).where(
        classes.c.id.in_(authz.classes_enrolled_by(user)), classes.c.archived_at.is_(None)
    )


async def enrolled_classes(session: AsyncSession, user: authz.Principal) -> list[RowMapping]:
    """The Classes the User is a Student in, by name (Norwegian order), then id."""
    result = await session.execute(
        _enrolled(user).order_by(nb_sort_sql(classes.c.name), classes.c.id)
    )
    return list(result.mappings())


async def enrolled_class(
    session: AsyncSession, user: authz.Principal, class_id: uuid.UUID
) -> RowMapping | None:
    """The Class, or None when the User is not a Student in it or it does not exist."""
    result = await session.execute(_enrolled(user).where(classes.c.id == class_id))
    return result.mappings().one_or_none()


async def demo_class_of(session: AsyncSession, owner: uuid.UUID, name: str) -> uuid.UUID | None:
    """For the local seed: the id of the Class called `name` the User owns."""
    result = await session.execute(
        _visible(owner)
        .with_only_columns(classes.c.id)
        .where(classes.c.name == name, class_staff.c.role == StaffRole.owner.value)
        .order_by(classes.c.id)
        .limit(1)
    )
    return result.scalar_one_or_none()


# The Class's staff (Story 4.9). Called only after the caller's policy let the User manage the
# Class (or, for the acceptance handler and the session role, for a User's own rows).


class Gone:
    """The Class row does not exist."""


GONE = Gone()


async def class_state(
    session: AsyncSession, class_id: uuid.UUID, *, exclusive: bool
) -> datetime | None | Gone:
    """Lock the Class row until the transaction ends and read its `archived_at` (None while
    active), or `GONE`. `exclusive` takes the row lock (staff changes and the archive run in turn,
    so two removals cannot both pass the last-owner check); otherwise a share lock, which keeps an
    archive from committing while a Roster change is under way (Story 4.10)."""
    query = select(classes.c.archived_at).where(classes.c.id == class_id)
    query = query.with_for_update() if exclusive else query.with_for_update(read=True)
    row = (await session.execute(query)).first()
    return GONE if row is None else row[0]


async def active_class_ids(session: AsyncSession, class_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    """Those of `class_ids` that exist and are not archived, read without a lock."""
    result = await session.execute(
        select(classes.c.id).where(classes.c.id.in_(class_ids), classes.c.archived_at.is_(None))
    )
    return set(result.scalars())


async def set_archived(session: AsyncSession, class_id: uuid.UUID, now: datetime) -> None:
    await session.execute(update(classes).where(classes.c.id == class_id).values(archived_at=now))


async def staff_of(session: AsyncSession, class_id: uuid.UUID) -> list[RowMapping]:
    """Every staff row of the Class: `user_id`, `role`."""
    result = await session.execute(
        select(class_staff.c.user_id, class_staff.c.role).where(class_staff.c.class_id == class_id)
    )
    return list(result.mappings())


async def staff_role(session: AsyncSession, class_id: uuid.UUID, user_id: uuid.UUID) -> str | None:
    result = await session.execute(
        select(class_staff.c.role).where(
            class_staff.c.class_id == class_id, class_staff.c.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def put_staff(
    session: AsyncSession,
    class_id: uuid.UUID,
    user_id: uuid.UUID,
    role: StaffRole,
    now: datetime,
    *,
    replace: bool,
) -> bool:
    """Add the User to the Class's staff as `role`. A User already staff keeps their row unless
    `replace` (then the role changes). True when a row was written."""
    query = pg_insert(class_staff).values(
        class_id=class_id, user_id=user_id, role=role.value, added_at=now
    )
    if replace:
        query = query.on_conflict_do_update(
            index_elements=[class_staff.c.class_id, class_staff.c.user_id],
            set_={"role": role.value},
            where=class_staff.c.role != role.value,
        )
    else:
        query = query.on_conflict_do_nothing()
    result = await session.execute(query.returning(class_staff.c.user_id))
    return result.scalar_one_or_none() is not None


async def remove_staff(session: AsyncSession, class_id: uuid.UUID, user_id: uuid.UUID) -> None:
    await session.execute(
        delete(class_staff).where(
            class_staff.c.class_id == class_id, class_staff.c.user_id == user_id
        )
    )


async def is_assistant_anywhere(session: AsyncSession, user_id: uuid.UUID) -> bool:
    """Whether the User is Assistant lecturer of any Class: the session role `assistant`."""
    result = await session.execute(
        select(class_staff.c.class_id)
        .where(
            class_staff.c.user_id == user_id,
            class_staff.c.role == StaffRole.assistant.value,
        )
        .limit(1)
    )
    return result.first() is not None


async def delete_staff_rows_of(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Story 15.2 (FR-76): an erased User is no Lecturer or Assistant lecturer of any Class."""
    await session.execute(delete(class_staff).where(class_staff.c.user_id == user_id))
