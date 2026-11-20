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
    BounceClass,
    ClassIn,
    ClassListItem,
    ClassListOut,
    ClassOut,
    EnrolledClassListOut,
    EnrolledClassOut,
    InstitutionChoice,
    InstitutionChoicesOut,
    InvalidClass,
    InvalidRosterAddress,
    InvitationBounce,
    InvitationSummaryOut,
    ManualRegistrationIn,
    RegistrationOut,
    RegistrationsOut,
    RegistrationStatus,
    RegistrationTotals,
    ReminderOut,
    RosterEntryIn,
    RosterSendOut,
    StaffAssistant,
    StaffEmailIn,
    StaffLecturer,
    StaffOut,
    StaffRefused,
    StaffRole,
    StaffStatus,
    class_name,
    course_code,
)
from app.modules.identity import service as identity
from app.modules.messaging import service as messaging
from app.platform import audit, authz, events
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
        can_manage=True,
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
                archived=row["archived_at"] is not None,
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
        can_manage=authz.can(user, "classes.manage", _StaffOf(row["staff_role"])),
        created_at=row["created_at"],
        archived=row["archived_at"] is not None,
        roster_count=counts.get(row["id"], 0),
    )


async def may_read(user: authz.Principal, class_id: uuid.UUID) -> bool:
    """Whether `user` may read the Class and its Roster: an owner or an Assistant lecturer of it
    (Story 4.9). Outside the User's scope and not existing both answer False."""
    async with get_sessionmaker().begin() as s:
        row = await repo.class_for(s, user, class_id)
    return row is not None and authz.can(user, "classes.read", _StaffOf(row["staff_role"]))


async def may_manage(user: authz.Principal, class_id: uuid.UUID) -> bool:
    """Whether `user` may manage the Class (its owner). A Class outside the User's scope and one
    that does not exist both answer False."""
    async with get_sessionmaker().begin() as s:
        row = await repo.class_for(s, user, class_id)
    return row is not None and authz.can(user, "classes.manage", _StaffOf(row["staff_role"]))


# Archived Classes are read-only (Story 4.10, FR-6). Every change to a Class passes the one check
# below: first whether the User may manage the Class (403 otherwise, so an archived Class is never
# revealed to anyone else), then whether it is archived (`ClassArchived`, 409 `class_archived`).
# Inside a change's own transaction the Class row is held under a lock and checked again, so an
# archive never commits in the middle of a Roster or staff change.


class ClassArchived(Exception):
    """The Class is archived: it takes no change (`class_archived`)."""


def _refuse_archived(class_id: uuid.UUID, archived_at: datetime | None) -> None:
    """The one check every mutation of a Class goes through."""
    if archived_at is not None:
        log.info("class_change_refused", class_id=str(class_id), error_code="class_archived")
        raise ClassArchived


async def manageable(user: authz.Principal, class_id: uuid.UUID) -> bool:
    """Whether `user` may change the Class now: False when they may not manage it (or it does not
    exist); raises `ClassArchived` when they may but it is archived."""
    async with get_sessionmaker().begin() as s:
        row = await repo.class_for(s, user, class_id)
    if row is None or not authz.can(user, "classes.manage", _StaffOf(row["staff_role"])):
        return False
    _refuse_archived(class_id, row["archived_at"])
    return True


async def _hold(s: AsyncSession, class_id: uuid.UUID, *, exclusive: bool = False) -> bool:
    """In a change's transaction: lock the Class row and check it again. False when it is gone;
    raises `ClassArchived` when it was archived meanwhile."""
    state = await repo.class_state(s, class_id, exclusive=exclusive)
    if state is repo.GONE:
        return False
    _refuse_archived(class_id, state)
    return True


async def is_writable(class_id: uuid.UUID, session: AsyncSession | None = None) -> bool:
    """Whether the Class takes changes: it exists and is not archived. Later epics ask this before
    changing what belongs to a Class (Epic 5's Class sessions). With the caller's `session` the row
    is read under a share lock, so an archive cannot commit until that transaction ends."""
    if session is not None:
        state = await repo.class_state(session, class_id, exclusive=False)
        return state is None
    async with get_sessionmaker().begin() as s:
        state = await repo.class_state(s, class_id, exclusive=False)
    return state is None


async def writable_class_ids(class_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    """Those of `class_ids` that take changes now, in one read and without a lock: for the sweep's
    finders, whose actions ask `is_writable` again under their own lock."""
    if not class_ids:
        return set()
    async with get_sessionmaker().begin() as s:
        return await repo.active_class_ids(s, class_ids)


CLASS_ARCHIVED = "class.archived"


async def archive_class(
    user: authz.Principal, class_id: uuid.UUID, *, now: datetime
) -> ClassOut | None:
    """«Arkiver Klassen» (Story 4.10, FR-6, AD-8, AD-15): in one transaction holding the Class
    row's lock, `archived_at` is set, every open Invitation of the Class is voided and its staged
    upload deleted (`identity.close_class`), one audit row is written (ids and a count only) and
    every staff member's open pages are told (`user:<id>`). None when the User may not manage the
    Class; raises `ClassArchived` when it is archived already."""
    if not await manageable(user, class_id):
        return None
    async with get_sessionmaker().begin() as s:
        if not await _hold(s, class_id, exclusive=True):
            return None
        await repo.set_archived(s, class_id, now)
        voided = await identity.close_class(s, class_id, now)
        staff_rows = await repo.staff_of(s, class_id)
        await audit.record(
            s, user.id, CLASS_ARCHIVED, {"class_id": class_id}, {"voided_invitations": voided}, now
        )
        for row in sorted(staff_rows, key=lambda r: r["user_id"]):
            await events.emit(s, "user", str(row["user_id"]))
    log.info("class_archived", class_id=str(class_id), voided_invitations=voided)
    return await get_class(user, class_id)


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
    if not await manageable(user, class_id):
        return None
    return await identity.stage_roster_upload(class_id, user.id, file_name, data, now=now)


async def paste_roster(
    user: authz.Principal, class_id: uuid.UUID, text: str, *, now: datetime
) -> identity.RosterUploadOut | None:
    """Stage pasted addresses for the Class (Story 4.3). Raises `identity.RosterPasteTooLong`."""
    if not await manageable(user, class_id):
        return None
    return await identity.stage_roster_paste(class_id, user.id, text, now=now)


async def roster_staging(
    user: authz.Principal, class_id: uuid.UUID, *, now: datetime
) -> Staging | None:
    """A read: an archived Class answers too, with nothing staged (the archive deleted it)."""
    if not await may_manage(user, class_id):
        return None
    return Staging(await identity.roster_upload(class_id, now=now))


async def choose_roster_column(
    user: authz.Principal, class_id: uuid.UUID, column: int, *, now: datetime
) -> Staging | None:
    """Raises `identity.InvalidRosterColumn`; `Staging(None)` when nothing is staged."""
    if not await manageable(user, class_id):
        return None
    return Staging(await identity.choose_roster_column(class_id, column, now=now))


async def discard_roster_upload(user: authz.Principal, class_id: uuid.UUID) -> bool | None:
    if not await manageable(user, class_id):
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
    if not await manageable(user, class_id):
        return None
    await identity.purge_expired_roster_uploads(now)
    try:
        async with get_sessionmaker().begin() as s:
            if not await _hold(s, class_id):
                return None
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
    table), combined here at `now`, the api's clock. None when the User may not read the Class
    (its owners and Assistant lecturers may, Story 4.9)."""
    if not await may_read(user, class_id):
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
    # A voided link that is still its address's newest, of an address still waiting (an archive
    # voids them, Story 4.10), reads «Uregistrert, Invitasjonen er utløpt» on its row: it counts as
    # expired too, so the row and the counts agree (Issue #93). One a reminder replaced does not.
    stopped = sum(
        i.voided and not i.entry_registered and not i.entry_removed for i in newest.values()
    )
    return InvitationSummaryOut(
        sent=sent,
        bounced=bounced,
        accepted=sum(i.accepted for i in found),
        expired=sum(i.expired for i in found) + stopped,
        bounces=sorted(bounces, key=lambda b: b.email),
    )


def _status(
    facts: identity.RosterFacts, mail: messaging.InvitationDelivery | None
) -> RegistrationOut:
    """One address's status (Story 4.7): the first of registered, registered manually, asked for
    a new Invitation, bounced, invited, unregistered that applies."""
    bounce = (
        mail.bounce_class
        if mail is not None and mail.state == "bounced" and mail.bounce_class is not None
        else None
    )
    last_day = (
        identity.last_valid_day(facts.expires_at) if facts.open and facts.expires_at else None
    )
    if facts.registration in identity.REGISTERED:
        status = RegistrationStatus(facts.registration.value)
    elif facts.renewal_requested:
        status = RegistrationStatus.renewal_requested
    elif bounce is not None:
        status = RegistrationStatus.bounced
    elif facts.open:
        status = RegistrationStatus.invited
    elif facts.invitation_id is None:
        status = RegistrationStatus.not_invited
    else:
        status = RegistrationStatus.unregistered
    registered = facts.registration in identity.REGISTERED
    return RegistrationOut(
        id=facts.entry_id,
        email=facts.email,
        status=status,
        last_valid_day=last_day if status is RegistrationStatus.invited else None,
        bounce_class=BounceClass(bounce) if status is RegistrationStatus.bounced else None,
        remindable=not registered and bounce != BounceClass.hard,
    )


async def _statuses(class_id: uuid.UUID, now: datetime) -> list[RegistrationOut]:
    roster = await identity.class_roster(class_id, now=now)
    mails = await messaging.invitation_deliveries(
        [f.invitation_id for f in roster if f.invitation_id is not None]
    )
    return [
        _status(f, mails.get(f.invitation_id) if f.invitation_id is not None else None)
        for f in roster
    ]


async def registrations(
    user: authz.Principal, class_id: uuid.UUID, *, now: datetime
) -> RegistrationsOut | None:
    """«Status etter utsending» (Story 4.7, FR-9, UX-DR47): every Roster address with its status,
    read now from `identity`'s Roster and Invitations and `messaging`'s delivery state, and the
    totals. None when the User may not read the Class (its owners and Assistant lecturers may,
    Story 4.9)."""
    if not await may_read(user, class_id):
        return None
    items = await _statuses(class_id, now)
    registered = sum(i.status is RegistrationStatus.registered for i in items)
    manual = sum(i.status is RegistrationStatus.registered_manually for i in items)
    unregistered = len(items) - registered - manual
    return RegistrationsOut(
        totals=RegistrationTotals(
            registered=registered, registered_manually=manual, unregistered=unregistered
        ),
        reminder_count=unregistered,
        items=items,
    )


class NoReminderTarget(Exception):
    """Nothing to remind: every address is registered, or the one named is not on the Roster,
    registered, or of another Class (`nothing_to_send`)."""


async def send_reminders(
    user: authz.Principal,
    class_id: uuid.UUID,
    valid_days: int,
    *,
    entry_id: uuid.UUID | None = None,
    now: datetime,
) -> ReminderOut | None:
    """«Send påminnelse til N» (Story 4.7, FR-9, NFR-10): a new Invitation valid for
    `valid_days` to every address that has not registered, or to `entry_id` alone, voiding the
    old links, in one transaction; the mails leave from `worker-batch`. An address whose newest
    Invitation bounced hard is left out and named in the answer. None when the User may not
    manage the Class. Raises `NoReminderTarget`."""
    if not await manageable(user, class_id):
        return None
    items = await _statuses(class_id, now)
    if entry_id is not None:
        items = [i for i in items if i.id == entry_id]
    waiting = [
        i
        for i in items
        if i.status not in (RegistrationStatus.registered, RegistrationStatus.registered_manually)
    ]
    targets = [i.id for i in waiting if i.remindable]
    left_out = sorted(i.email for i in waiting if not i.remindable)
    async with get_sessionmaker().begin() as s:
        if not await _hold(s, class_id):
            return None
        sent = await identity.send_entry_reminders(
            s, class_id, user.id, targets, valid_days, now=now
        )
    if sent.sent == 0 and not left_out:
        log.info("reminders_refused", class_id=str(class_id), error_code="nothing_to_send")
        raise NoReminderTarget
    log.info(
        "reminders_answered",
        class_id=str(class_id),
        sent=sent.sent,
        left_out=len(left_out),
    )
    return ReminderOut(
        sent=sent.sent,
        valid_days=valid_days,
        last_valid_day=identity.last_valid_day(sent.expires_at),
        expires_at=sent.expires_at,
        left_out=left_out,
    )


# Single addresses and manual registration (Story 4.8, FR-7, FR-9, AD-8, AD-12). Each is one
# command for the Class's owners and one transaction through `identity.service`; the answer is
# the entry's status as «Status etter utsending» reads it right after.


async def _entry_status(
    class_id: uuid.UUID,
    entry_id: uuid.UUID,
    email: str,
    fallback: RegistrationStatus,
    now: datetime,
) -> RegistrationOut:
    """The entry's status as the list reads it now; the status the command wrote when another
    request removed the entry in the meantime (the command has committed: never a 500)."""
    for item in await _statuses(class_id, now):
        if item.id == entry_id:
            return item
    return RegistrationOut(id=entry_id, email=email, status=fallback, remindable=False)


async def add_roster_entry(
    user: authz.Principal, class_id: uuid.UUID, body: RosterEntryIn, *, now: datetime
) -> RegistrationOut | None:
    """«Legg til adresse» (FR-7): one address on the Roster, not yet invited, or a removed one
    put back. None when the User may not manage the Class. Raises `InvalidRosterAddress`."""
    if not await manageable(user, class_id):
        return None
    try:
        async with get_sessionmaker().begin() as s:
            if not await _hold(s, class_id):
                return None
            entry_id = await identity.add_roster_entry(s, class_id, body.email, now=now)
    except identity.RosterRefused as refused:
        log.info("roster_entry_refused", class_id=str(class_id), error_code=refused.reason)
        raise InvalidRosterAddress(refused.reason) from None
    return await _entry_status(
        class_id,
        entry_id,
        identity.normalise_email(body.email),
        RegistrationStatus.not_invited,
        now,
    )


async def register_manually(
    user: authz.Principal, class_id: uuid.UUID, body: ManualRegistrationIn, *, now: datetime
) -> RegistrationOut | None:
    """«Registrer manuelt» (FR-9): the Student is in the Class at once and gets a mail to set a
    password. None when the User may not manage the Class. Raises `InvalidRosterAddress`."""
    if not await manageable(user, class_id):
        return None
    row = (body.upload_row.upload_id, body.upload_row.row_number) if body.upload_row else None
    try:
        async with get_sessionmaker().begin() as s:
            if not await _hold(s, class_id):
                return None
            entry_id = await identity.register_manually(
                s,
                class_id,
                body.email,
                body.name,
                replaces=body.roster_entry_id,
                upload_row=row,
                now=now,
            )
    except identity.RosterRefused as refused:
        log.info("manual_registration_refused", class_id=str(class_id), error_code=refused.reason)
        raise InvalidRosterAddress(refused.reason) from None
    return await _entry_status(
        class_id,
        entry_id,
        identity.normalise_email(body.email),
        RegistrationStatus.registered_manually,
        now,
    )


async def remove_roster_entry(
    user: authz.Principal, class_id: uuid.UUID, entry_id: uuid.UUID, *, now: datetime
) -> bool | None:
    """Take an address off the Roster (FR-7). None when the User may not manage the Class; False
    when the entry is not on its Roster."""
    if not await manageable(user, class_id):
        return None
    async with get_sessionmaker().begin() as s:
        if not await _hold(s, class_id):
            return None
        return await identity.remove_roster_entry(s, class_id, entry_id, now=now)


async def registered_students(class_id: uuid.UUID) -> list[uuid.UUID]:
    """The Users who are Students in the Class (FR-9), for Epic 5's allocation: registered
    through an Invitation or by hand, and not removed. An address unregistered after its
    Invitation expired, a bounced or a removed one is never among them."""
    return await identity.registered_users(class_id)


async def registered_students_of(class_ids: list[uuid.UUID]) -> dict[uuid.UUID, set[uuid.UUID]]:
    """`registered_students` of many Classes in one read, by Class id; a Class with no Student is
    left out. For the sweep's finders."""
    return await identity.registered_users_of(class_ids)


async def student_names(class_id: uuid.UUID, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    """The scope helper by which Epic 5 names the Students of an allocation at read time
    (Story 5.8, AD-12, AD-14): the names of those of `user_ids` who are Students in the Class now.
    An id that is no longer one (removed from the Roster) or never was is left out. The caller has
    checked that the User may read the Class."""
    return await identity.student_names(class_id, user_ids)


async def owners_of(session: AsyncSession, class_id: uuid.UUID) -> list[uuid.UUID]:
    """The ids of the Class's owners and co-owners (Story 5.11: who is told that a Class session
    cannot lock). Assistant lecturers are not among them."""
    return sorted(
        row["user_id"]
        for row in await repo.staff_of(session, class_id)
        if row["role"] == StaffRole.owner.value
    )


async def label_of_class(session: AsyncSession, class_id: uuid.UUID) -> identity.ClassLabel | None:
    """How a Student Invitation names its Class, in its mail and on «Du er invitert»
    (`identity`'s resolver)."""
    row = await repo.class_label(session, class_id)
    if row is None:
        return None
    return identity.ClassLabel(row["name"], row["course_code"], row["archived_at"] is not None)


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


# The Class's staff (Story 4.9, FR-10, AD-8, AD-12, AD-15): co-owners are `owner` rows with
# exactly the owner's rights; Assistant lecturers join through an Invitation of kind `assistant`.
# Every change is one transaction holding the Class row's lock, with an audit row (ids only) and
# `user:<id>` so the person's open pages read again.

STAFF_ADDED = "class_staff.added"
STAFF_INVITED = "class_staff.invited"
STAFF_INVITATION_VOIDED = "class_staff.invitation_voided"
STAFF_JOINED = "class_staff.joined"
STAFF_REMOVED = "class_staff.removed"


def _checked(address: str) -> str:
    try:
        return identity.checked_address(address)
    except identity.RosterRefused as refused:
        raise StaffRefused(refused.reason) from None


def _sort_key(name: str | None, email: str) -> tuple[str, str]:
    return ((name or email).casefold(), email)


async def staff(user: authz.Principal, class_id: uuid.UUID, *, now: datetime) -> StaffOut | None:
    """«Faglærere og assistenter»: the owners, and the Assistants with their status: active, or
    an Invitation not accepted (invited with its last valid day, or expired). None when the User
    may not manage the Class. A read: an archived Class's staff is listed too."""
    if not await may_manage(user, class_id):
        return None
    async with get_sessionmaker().begin() as s:
        rows = await repo.staff_of(s, class_id)
        pending = await identity.assistant_invitations(s, class_id)
        people = await identity.people(s, [row["user_id"] for row in rows])
    lecturers: list[StaffLecturer] = []
    assistants: list[StaffAssistant] = []
    for row in rows:
        person = people.get(row["user_id"])
        if person is None:
            continue
        if StaffRole(row["role"]) is StaffRole.owner:
            lecturers.append(StaffLecturer(user_id=person.id, name=person.name, email=person.email))
        else:
            assistants.append(
                StaffAssistant(
                    user_id=person.id,
                    name=person.name,
                    email=person.email,
                    status=StaffStatus.active,
                )
            )
    on_staff = {person.email for person in people.values()}
    for invitation in pending:
        if invitation.email in on_staff:
            continue
        still_open = now < invitation.expires_at
        assistants.append(
            StaffAssistant(
                invitation_id=invitation.id,
                email=invitation.email,
                status=StaffStatus.invited if still_open else StaffStatus.expired,
                last_valid_day=(
                    identity.last_valid_day(invitation.expires_at) if still_open else None
                ),
            )
        )
    return StaffOut(
        lecturers=sorted(lecturers, key=lambda p: _sort_key(p.name, p.email)),
        assistants=sorted(assistants, key=lambda p: _sort_key(p.name, p.email)),
    )


async def add_lecturer(
    user: authz.Principal, class_id: uuid.UUID, body: StaffEmailIn, *, now: datetime
) -> StaffLecturer | None:
    """«Legg til Faglærer»: an active User with the Lecturer role becomes an owner of the Class
    (an Assistant of it is promoted). None when the User may not manage the Class. Raises
    `StaffRefused`: an address problem, `not_lecturer` (no account, a deactivated one or no
    Lecturer role: one reason, so nothing about the account is revealed) or `already_staff`."""
    if not await manageable(user, class_id):
        return None
    address = _checked(body.email)
    async with get_sessionmaker().begin() as s:
        if not await _hold(s, class_id, exclusive=True):
            return None
        found = await identity.active_user_for_email(s, address)
        if found is None or not authz.can(found, "classes.manage"):
            log.info("staff_refused", class_id=str(class_id), error_code="not_lecturer")
            raise StaffRefused("not_lecturer")
        before = await repo.staff_role(s, class_id, found.id)
        if before is not None and StaffRole(before) is StaffRole.owner:
            log.info("staff_refused", class_id=str(class_id), error_code="already_staff")
            raise StaffRefused("already_staff")
        await repo.put_staff(s, class_id, found.id, StaffRole.owner, now, replace=True)
        await identity.void_assistant_invitations(s, class_id, now, email=found.email)
        await audit.record(
            s,
            user.id,
            STAFF_ADDED,
            {"class_id": class_id, "user_id": found.id},
            {"role": StaffRole.owner.value, "previous_role": before},
            now,
        )
        await events.emit(s, "user", str(found.id))
    log.info("staff_added", class_id=str(class_id), user_id=str(found.id))
    return StaffLecturer(user_id=found.id, name=found.name, email=found.email)


async def invite_assistant(
    user: authz.Principal, class_id: uuid.UUID, body: StaffEmailIn, *, now: datetime
) -> StaffAssistant | None:
    """«Inviter Assistent»: an Invitation of kind `assistant` for this Class only, mailed from
    `worker-batch` (an open one to the same address is voided). None when the User may not manage
    the Class. Raises `StaffRefused`: an address problem or `already_staff`."""
    if not await manageable(user, class_id):
        return None
    address = _checked(body.email)
    async with get_sessionmaker().begin() as s:
        if not await _hold(s, class_id, exclusive=True):
            return None
        members = await identity.people(s, [r["user_id"] for r in await repo.staff_of(s, class_id)])
        if any(person.email == address for person in members.values()):
            log.info("staff_refused", class_id=str(class_id), error_code="already_staff")
            raise StaffRefused("already_staff")
        sent = await identity.send_assistant_invitation(s, class_id, user.id, address, now=now)
        await audit.record(
            s,
            user.id,
            STAFF_INVITED,
            {"class_id": class_id, "invitation_id": sent.id},
            {"role": StaffRole.assistant.value},
            now,
        )
    log.info("assistant_invited", class_id=str(class_id), invitation_id=str(sent.id))
    return StaffAssistant(
        invitation_id=sent.id,
        email=sent.email,
        status=StaffStatus.invited,
        last_valid_day=identity.last_valid_day(sent.expires_at),
    )


async def remove_staff(
    user: authz.Principal, class_id: uuid.UUID, member: uuid.UUID, *, now: datetime
) -> bool | None:
    """Take a Faglærer or an Assistant off the Class: their access ends from their next request.
    None when the User may not manage the Class; False when `member` is not staff of it. Raises
    `StaffRefused("last_owner")` for the Class's last owner: a Class always keeps a Lecturer."""
    if not await manageable(user, class_id):
        return None
    async with get_sessionmaker().begin() as s:
        if not await _hold(s, class_id, exclusive=True):
            return None
        rows = await repo.staff_of(s, class_id)
        role = next((StaffRole(r["role"]) for r in rows if r["user_id"] == member), None)
        if role is None:
            return False
        owners = sum(StaffRole(r["role"]) is StaffRole.owner for r in rows)
        if role is StaffRole.owner and owners <= 1:
            log.info("staff_refused", class_id=str(class_id), error_code="last_owner")
            raise StaffRefused("last_owner", field=None)
        await repo.remove_staff(s, class_id, member)
        person = (await identity.people(s, [member])).get(member)
        if person is not None:
            await identity.void_assistant_invitations(s, class_id, now, email=person.email)
        await audit.record(
            s,
            user.id,
            STAFF_REMOVED,
            {"class_id": class_id, "user_id": member},
            {"role": role.value},
            now,
        )
        await events.emit(s, "user", str(member))
    log.info("staff_removed", class_id=str(class_id), user_id=str(member))
    return True


async def withdraw_assistant_invitation(
    user: authz.Principal, class_id: uuid.UUID, invitation_id: uuid.UUID, *, now: datetime
) -> bool | None:
    """Void an Assistant Invitation of the Class that is not accepted: its link stops working.
    None when the User may not manage the Class; False when there is no such open Invitation."""
    if not await manageable(user, class_id):
        return None
    async with get_sessionmaker().begin() as s:
        if not await _hold(s, class_id, exclusive=True):
            return None
        voided = await identity.void_assistant_invitations(
            s, class_id, now, invitation_id=invitation_id
        )
        if not voided:
            return False
        await audit.record(
            s,
            user.id,
            STAFF_INVITATION_VOIDED,
            {"class_id": class_id, "invitation_id": invitation_id},
            {"role": StaffRole.assistant.value},
            now,
        )
    log.info("assistant_invitation_withdrawn", class_id=str(class_id))
    return True


async def join_as_assistant(
    session: AsyncSession, place: identity.AcceptedPlace, now: datetime
) -> None:
    """The acceptance handler of an `assistant` Invitation, inside `identity`'s acceptance
    transaction: the User joins this Class's staff as Assistant lecturer (one already owner stays
    owner), with an audit row and `user:<id>`."""
    # The acceptance took the Class row's lock first (`lock_class_for_acceptance`), before the
    # Invitation's. An archived Class never gets here: the archive voids its Invitations under that
    # lock, and «Du er invitert» refuses its links (Story 4.10).
    joined = await repo.put_staff(
        session, place.class_id, place.user_id, StaffRole.assistant, now, replace=False
    )
    await audit.record(
        session,
        place.user_id,
        STAFF_JOINED,
        {
            "class_id": place.class_id,
            "user_id": place.user_id,
            "invitation_id": place.invitation_id,
        },
        {"role": StaffRole.assistant.value, "joined": joined},
        now,
    )
    await events.emit(session, "user", str(place.user_id))


async def lock_class_for_acceptance(
    session: AsyncSession, class_id: uuid.UUID, exclusive: bool
) -> None:
    """`identity`'s Class lock: an acceptance takes the Class row first, as an archive and a staff
    change do, before the Invitation row (Issue #93)."""
    await repo.class_state(session, class_id, exclusive=exclusive)


async def assistant_session_role(session: AsyncSession, user_id: uuid.UUID) -> set[str]:
    """The session role `assistant` while the User is Assistant lecturer of any Class."""
    return {authz.ASSISTANT} if await repo.is_assistant_anywhere(session, user_id) else set()


identity.register_revoke_blocker(identity.AccountRole.lecturer, owned_active_classes)
identity.register_class_label(label_of_class)
identity.register_acceptance_handler(identity.InvitationKind.assistant, join_as_assistant)
identity.register_class_lock(lock_class_for_acceptance)
identity.register_session_roles(assistant_session_role)
