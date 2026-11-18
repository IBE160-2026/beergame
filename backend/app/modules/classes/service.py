"""Classes (Story 4.1, FR-6, AD-12, AD-14). Other modules import only this file.

A Lecturer creates a Class with a name, an Institution and an optional course code, and is stored
as its owner in the same transaction. Reads go through the User's scope (`repo`), so a Class the
User is not staff of reads as one that does not exist. At import this module registers the
Lecturer-revoke blocker with `identity` (FR-2): an Admin cannot take the Lecturer role from a User
who owns active Classes.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.classes import repo
from app.modules.classes.schemas import (
    ClassIn,
    ClassListItem,
    ClassListOut,
    ClassOut,
    InstitutionChoice,
    InstitutionChoicesOut,
    InvalidClass,
    StaffRole,
    class_name,
    course_code,
)
from app.modules.identity import service as identity
from app.platform import authz
from app.platform.db import get_sessionmaker

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class _StaffOf:
    """A Class as `authz.can` sees it."""

    staff_role: str


async def institution_choices() -> InstitutionChoicesOut:
    """Every Institution, by name, for «Lag Klasse» (`identity.service.list_institutions`)."""
    found = await identity.list_institutions()
    return InstitutionChoicesOut(items=[InstitutionChoice(id=i.id, name=i.name) for i in found])


async def create_class(user: authz.Principal, body: ClassIn, *, now: datetime) -> ClassOut:
    """Store a Class with `user` as its owner, in one transaction. Raises `InvalidClass` with every
    refused field before anything is stored. The route's policy has checked the account role."""
    name, name_reason = class_name(body.name)
    code, code_reason = course_code(body.course_code)
    refused: dict[str, str] = {}
    if name_reason:
        refused["name"] = name_reason
    institution = None
    if body.institution_id is None:
        refused["institution_id"] = "institution_missing"
    else:
        institution = await identity.get_institution(body.institution_id)
        if institution is None:
            refused["institution_id"] = "institution_unknown"
    if code_reason:
        refused["course_code"] = code_reason
    if refused or institution is None:
        log.info("class_refused", error_code="invalid_request", fields=sorted(refused))
        raise InvalidClass(refused)
    class_id = uuid.uuid7()
    async with get_sessionmaker().begin() as s:
        await repo.insert_class(
            s,
            class_id=class_id,
            name=name,
            course_code=code,
            institution_id=institution.id,
            owner=user.id,
            now=now,
        )
    log.info("class_created", class_id=str(class_id), user_id=str(user.id))
    return ClassOut(
        id=class_id,
        name=name,
        course_code=code,
        institution_id=institution.id,
        institution_name=institution.name,
        staff_role=StaffRole.owner,
        created_at=now,
        archived=False,
    )


async def list_classes(user: authz.Principal) -> ClassListOut:
    """The Classes `user` is staff of, by name: «Klassene dine»."""
    async with get_sessionmaker().begin() as s:
        rows = await repo.classes_of(s, user)
    return ClassListOut(
        items=[
            ClassListItem(id=row["id"], name=row["name"], course_code=row["course_code"])
            for row in rows
            if authz.can(user, "classes.read", _StaffOf(row["staff_role"]))
        ]
    )


async def get_class(user: authz.Principal, class_id: uuid.UUID) -> ClassOut | None:
    """The Class, or None when `user` may not read it, or it does not exist: one answer (FR-5)."""
    async with get_sessionmaker().begin() as s:
        row = await repo.class_for(s, user, class_id)
    if row is None or not authz.can(user, "classes.read", _StaffOf(row["staff_role"])):
        return None
    institution = await identity.get_institution(row["institution_id"])
    return ClassOut(
        id=row["id"],
        name=row["name"],
        course_code=row["course_code"],
        institution_id=row["institution_id"],
        institution_name=institution.name if institution else None,
        staff_role=StaffRole(row["staff_role"]),
        created_at=row["created_at"],
        archived=row["archived_at"] is not None,
    )


async def owned_active_classes(session: AsyncSession, user_id: uuid.UUID) -> int:
    """The revoke blocker of the Lecturer role (FR-2, Story 3.9's registry): how many Classes
    that are not archived the User owns, read in the revoke's own transaction."""
    return await repo.count_owned_active(session, user_id)


identity.register_revoke_blocker(identity.AccountRole.lecturer, owned_active_classes)
