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
    EnrolledClassListOut,
    EnrolledClassOut,
    InstitutionChoice,
    InstitutionChoicesOut,
    InvalidClass,
    InvitationBounce,
    InvitationSummaryOut,
    RosterSendOut,
    StaffRole,
    class_name,
    course_code,
)
from app.modules.identity import service as identity
from app.modules.messaging import service as messaging
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
        roster_count=0,
    )


async def list_classes(user: authz.Principal) -> ClassListOut:
    """The Classes `user` is staff of, by name: «Klassene dine»."""
    async with get_sessionmaker().begin() as s:
        rows = await repo.classes_of(s, user)
    readable = [row for row in rows if authz.can(user, "classes.read", _StaffOf(row["staff_role"]))]
    counts = await identity.roster_counts([row["id"] for row in readable])
    return ClassListOut(
        items=[
            ClassListItem(
                id=row["id"],
                name=row["name"],
                course_code=row["course_code"],
                roster_count=counts.get(row["id"], 0),
            )
            for row in readable
        ]
    )


async def get_class(user: authz.Principal, class_id: uuid.UUID) -> ClassOut | None:
    """The Class, or None when `user` may not read it, or it does not exist: one answer (FR-5)."""
    async with get_sessionmaker().begin() as s:
        row = await repo.class_for(s, user, class_id)
    if row is None or not authz.can(user, "classes.read", _StaffOf(row["staff_role"])):
        return None
    institution = await identity.get_institution(row["institution_id"])
    counts = await identity.roster_counts([row["id"]])
    return ClassOut(
        id=row["id"],
        name=row["name"],
        course_code=row["course_code"],
        institution_id=row["institution_id"],
        institution_name=institution.name if institution else None,
        staff_role=StaffRole(row["staff_role"]),
        created_at=row["created_at"],
        archived=row["archived_at"] is not None,
        roster_count=counts.get(row["id"], 0),
    )


async def may_manage(user: authz.Principal, class_id: uuid.UUID) -> bool:
    """Whether `user` may manage the Class (its owner). A Class outside the User's scope and one
    that does not exist both answer False."""
    async with get_sessionmaker().begin() as s:
        row = await repo.class_for(s, user, class_id)
    return row is not None and authz.can(user, "classes.manage", _StaffOf(row["staff_role"]))


# The staged Roster upload of a Class (Story 4.2, FR-7). The cells live in `identity`
# (AD-14); this module checks the User may manage the Class and hands over. Each answers None when
# the User may not, which the route turns into 403 `forbidden`.


@dataclass(frozen=True)
class Staging:
    upload: identity.RosterUploadOut | None


async def upload_roster(
    user: authz.Principal, class_id: uuid.UUID, file_name: str, data: bytes, *, now: datetime
) -> identity.RosterUploadOut | None:
    """Stage the file's rows for the Class. Raises `identity.RosterUnreadable`."""
    if not await may_manage(user, class_id):
        return None
    return await identity.stage_roster_upload(class_id, user.id, file_name, data, now=now)


async def paste_roster(
    user: authz.Principal, class_id: uuid.UUID, text: str, *, now: datetime
) -> identity.RosterUploadOut | None:
    """Stage pasted addresses for the Class (Story 4.3). Raises `identity.RosterPasteTooLong`."""
    if not await may_manage(user, class_id):
        return None
    return await identity.stage_roster_paste(class_id, user.id, text, now=now)


async def roster_staging(
    user: authz.Principal, class_id: uuid.UUID, *, now: datetime
) -> Staging | None:
    if not await may_manage(user, class_id):
        return None
    return Staging(await identity.roster_upload(class_id, now=now))


async def choose_roster_column(
    user: authz.Principal, class_id: uuid.UUID, column: int, *, now: datetime
) -> Staging | None:
    """Raises `identity.InvalidRosterColumn`; `Staging(None)` when nothing is staged."""
    if not await may_manage(user, class_id):
        return None
    return Staging(await identity.choose_roster_column(class_id, column, now=now))


async def discard_roster_upload(user: authz.Principal, class_id: uuid.UUID) -> bool | None:
    if not await may_manage(user, class_id):
        return None
    return await identity.delete_roster_upload(class_id)


class NothingToSend(Exception):
    """The staged upload has no row that gets an Invitation (`nothing_to_send`)."""


async def send_invitations(
    user: authz.Principal,
    class_id: uuid.UUID,
    upload_id: uuid.UUID,
    valid_days: int,
    *,
    now: datetime,
) -> RosterSendOut | Staging | None:
    """«Send N Invitasjoner» (Story 4.4, FR-7, FR-8): one command, one transaction. Through
    `identity.service` it writes the staged valid addresses to the Roster, deletes the staging,
    and creates and enqueues one Invitation per new address; the request returns once the rows
    commit and `worker-batch` sends the mails. None when the User may not manage the Class;
    `Staging(None)` when the staging `upload_id` is gone (sent already, replaced or expired).
    Raises `NothingToSend`."""
    if not await may_manage(user, class_id):
        return None
    await identity.purge_expired_roster_uploads(now)
    try:
        async with get_sessionmaker().begin() as s:
            sent = await identity.send_roster_invitations(
                s, class_id, user.id, upload_id, valid_days, now=now
            )
    except identity.RosterStagingGone:
        log.info("roster_send_refused", class_id=str(class_id), error_code="not_found")
        return Staging(None)
    except identity.NothingToSend:
        log.info("roster_send_refused", class_id=str(class_id), error_code="nothing_to_send")
        raise NothingToSend from None
    return RosterSendOut(
        sent=sent.sent,
        valid_days=valid_days,
        last_valid_day=identity.last_valid_day(sent.expires_at),
        expires_at=sent.expires_at,
    )


async def invitation_summary(
    user: authz.Principal, class_id: uuid.UUID, *, now: datetime
) -> InvitationSummaryOut | None:
    """The counts of the Class's Student Invitations and the bounced addresses (Story 4.6, FR-8,
    AD-10): the Invitations from `identity`, the state of their mails from `messaging` (never its
    table), combined here at `now`, the api's clock. None when the User may not manage the
    Class."""
    if not await may_manage(user, class_id):
        return None
    found = await identity.class_student_invitations(class_id, now=now)
    mails = await messaging.invitation_deliveries([i.id for i in found])
    sent = bounced = 0
    newest: dict[uuid.UUID, identity.ClassInvitation] = {}
    for invitation in found:  # oldest first, so the last one per entry is its newest
        newest[invitation.roster_entry_id] = invitation
        mail = mails.get(invitation.id)
        if mail is not None and mail.sent:
            sent += 1
            bounced += mail.state == "bounced"
    bounces = []
    for invitation in newest.values():
        mail = mails.get(invitation.id)
        if mail is None or mail.state != "bounced" or mail.bounce_class is None:
            continue
        if invitation.entry_registered or invitation.entry_removed:
            continue
        bounces.append(
            InvitationBounce(
                email=invitation.email, registration="bounced", bounce_class=mail.bounce_class
            )
        )
    return InvitationSummaryOut(
        sent=sent,
        bounced=bounced,
        accepted=sum(i.accepted for i in found),
        expired=sum(i.expired for i in found),
        bounces=sorted(bounces, key=lambda b: b.email),
    )


async def label_of_class(session: AsyncSession, class_id: uuid.UUID) -> identity.ClassLabel | None:
    """How a Student Invitation names its Class, in its mail and on «Du er invitert»
    (`identity`'s resolver)."""
    row = await repo.class_label(session, class_id)
    return None if row is None else identity.ClassLabel(row["name"], row["course_code"])


# The Classes a Student is in (Story 4.5, FR-5, FR-7, AD-12): read through the Student scope only.


async def enrolled_classes(user: authz.Principal) -> EnrolledClassListOut:
    """The Classes `user` is a Student in, by name: what Hjem names."""
    async with get_sessionmaker().begin() as s:
        rows = await repo.enrolled_classes(s, user)
    return EnrolledClassListOut(items=[EnrolledClassOut(**row) for row in rows])


async def enrolled_class(user: authz.Principal, class_id: uuid.UUID) -> EnrolledClassOut | None:
    """The Class, or None when `user` is not a Student in it (another Class, a removed address,
    or none at all): one answer (FR-5)."""
    async with get_sessionmaker().begin() as s:
        row = await repo.enrolled_class(s, user, class_id)
    return None if row is None else EnrolledClassOut(**row)


async def owned_active_classes(session: AsyncSession, user_id: uuid.UUID) -> int:
    """The revoke blocker of the Lecturer role (FR-2, Story 3.9's registry): how many Classes
    that are not archived the User owns, read in the revoke's own transaction."""
    return await repo.count_owned_active(session, user_id)


identity.register_revoke_blocker(identity.AccountRole.lecturer, owned_active_classes)
identity.register_class_label(label_of_class)
