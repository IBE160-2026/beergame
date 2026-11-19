"""Accounts and login (FR-4, AD-11, Story 3.2). Other modules import only this file.

`authenticate` checks the rate limits, the password and the account state and returns one
outcome; it never says whether an account exists, except that a deactivated account is named
once its right password is given (FR-3). `load_user` is the loader `platform/authz` calls on every
request (registered in `create_app()`), so a role change or a deactivation takes effect at once.
"""

import asyncio
import base64
import math
import uuid
from collections.abc import Awaitable, Callable, Mapping, Set
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity import repo, roster_file
from app.modules.identity.schemas import (
    ROSTER_PREVIEW_ROWS,
    AccessRequestListOut,
    AccessRequestOut,
    AccountRole,
    InstitutionListOut,
    InstitutionOut,
    InvalidRosterColumn,
    InvitationKind,
    InvitationListItem,
    InvitationListOut,
    InvitationOut,
    InvitationStatus,
    RosterColumn,
    RosterInvalidRow,
    RosterPasteTooLong,
    RosterPreviewRow,
    RosterRegistration,
    RosterSource,
    RosterUploadOut,
    UserListItem,
    UserListOut,
    UserOut,
    address_problem,
    email_is_valid,
    institution_name,
    normalise_email,
)
from app.modules.identity.schemas import (
    RosterColumnIn as RosterColumnIn,  # re-exported for `classes.routes`
)
from app.modules.identity.schemas import (
    RosterPasteIn as RosterPasteIn,  # re-exported for `classes.routes`
)
from app.modules.identity.schemas import (
    RosterStagingOut as RosterStagingOut,  # re-exported for `classes.routes`
)
from app.platform import audit, auth, email, events, notify, ratelimit
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

log = structlog.get_logger(__name__)

LOGIN_IP = "login_ip"
LOGIN_ACCOUNT = "login_account"
RESET_IP = "password_reset_ip"
RESET_ACCOUNT = "password_reset_account"

PASSWORD_RESET = "password_reset"
"""The notice kind of a reset mail; `messaging` delivers it at once (Story 3.6)."""
RESET_LINK_PATH = "/nytt-passord"

INVITATION = "invitation"
"""The notice kind of an Invitation mail, addressed by reference to the Invitation (Story 3.7)."""
INVITATION_LINK_PATH = "/invitasjon"
"""Where an Invitation link leads: «Du er invitert» (Story 3.8)."""
INVITATION_SENT = "invitation.sent"
"""The audit action of an Invitation the Admin sends (FR-3)."""


@dataclass(frozen=True)
class LoginOk:
    """A User who may be given a session: the cookie carries `session_version` (Story 3.10)."""

    user: UserOut
    session_version: int


@dataclass(frozen=True)
class LoginRefused:
    code: str  # invalid_credentials | account_deactivated | rate_limited
    retry_after: int | None = None


def _user_out(row, roles: list[str]) -> UserOut:
    return UserOut(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        roles=[AccountRole(role) for role in roles],
    )


async def authenticate(
    email: str, password: str, *, ip: str, now: datetime
) -> LoginOk | LoginRefused:
    settings = get_settings()
    window = timedelta(minutes=settings.login_rate_limit_window_minutes)
    email = normalise_email(email)
    ip_key = f"ip:{ip}"
    account_key = f"account:{email}"

    # Count the attempt before the password is checked, in one atomic upsert per key, so parallel
    # guesses cannot all slip under the limit. A successful attempt is given back below.
    async with get_sessionmaker().begin() as s:
        ip_count = await ratelimit.hit(s, LOGIN_IP, ip_key, window=window, now=now)
        account_count = await ratelimit.hit(s, LOGIN_ACCOUNT, account_key, window=window, now=now)
        limited = (
            ip_count > settings.login_rate_limit_per_ip
            or account_count > settings.login_rate_limit_per_account
        )
        row = None if limited else await repo.user_by_email(s, email)
        roles = await repo.roles_of(s, row["id"]) if row else []
    if limited:
        log.info("login_refused", error_code="rate_limited")
        return LoginRefused("rate_limited", ratelimit.seconds_left(now, window))

    # bcrypt is CPU work: off the event loop, and outside any transaction. An unknown e-mail
    # checks a dummy hash, so it takes as long as a wrong password; so does an account that has no
    # password yet (a manually registered Student, Story 4.8), which never logs in.
    has_password = row is not None and row["password_hash"] is not None
    stored = row["password_hash"] if has_password else await asyncio.to_thread(auth.dummy_hash)
    matches = await asyncio.to_thread(auth.verify_password, password, stored)
    ok = has_password and matches

    if ok and row["is_active"]:
        # The same lock order as the count above (IP, then account): parallel logins to one
        # account from one address would otherwise deadlock.
        async with get_sessionmaker().begin() as s:
            await ratelimit.give_back(s, LOGIN_IP, ip_key, window=window, now=now)
            await ratelimit.reset(s, LOGIN_ACCOUNT, account_key)
            if await _grant_bootstrap_admin(s, row["id"], email, now):
                roles = sorted([*roles, AccountRole.admin.value])

    if not ok:
        log.info("login_refused", error_code="invalid_credentials")
        return LoginRefused("invalid_credentials")
    if not row["is_active"]:
        log.info("login_refused", error_code="account_deactivated", user_id=str(row["id"]))
        return LoginRefused("account_deactivated")
    log.info("login", user_id=str(row["id"]))
    return LoginOk(_user_out(row, roles), row["session_version"])


async def load_user(user_id: uuid.UUID, session_version: int) -> UserOut | None:
    """The active User with their roles, or None when the User is gone or deactivated, or the
    session predates the User's session version (a deactivation or a password reset since)."""
    async with get_sessionmaker().begin() as s:
        row = await repo.user_by_id(s, user_id)
        if row is None or not row["is_active"] or row["session_version"] != session_version:
            return None
        return _user_out(row, await repo.roles_of(s, user_id))


async def create_user(
    *,
    email: str,
    name: str,
    password: str,
    roles: list[AccountRole] | tuple[AccountRole, ...] = (),
    is_active: bool = True,
    session: AsyncSession | None = None,
) -> uuid.UUID:
    """Create a User. Callers so far: the local demo seed and the tests; the Invitation flow
    (Story 3.8) adds the audited path."""
    user_id = uuid.uuid7()
    password_hash = await asyncio.to_thread(auth.hash_password, password)
    values = {
        "user_id": user_id,
        "email": normalise_email(email),
        "name": name,
        "password_hash": password_hash,
        "is_active": is_active,
        "roles": [AccountRole(role).value for role in roles],
    }
    if session is not None:
        await repo.insert_user(session, **values)
    else:
        async with get_sessionmaker().begin() as s:
            await repo.insert_user(s, **values)
    return user_id


async def mail_recipient(session: AsyncSession, user_id: uuid.UUID) -> email.Recipient | None:
    """Where a mail to `user_id` goes, for `messaging` at send time (AD-9, AD-14): the address
    and name, or None when the User is gone or deactivated. Never stored or logged."""
    row = await repo.user_by_id(session, user_id)
    if row is None or not row["is_active"]:
        return None
    return email.Recipient(email=row["email"], name=row["name"])


async def user_id_for_email(session: AsyncSession, address: str) -> uuid.UUID | None:
    """The id of the User with this e-mail, or None. For the local dev mailbox only."""
    row = await repo.user_by_email(session, normalise_email(address))
    return None if row is None else row["id"]


# Password reset (Story 3.6, FR-4, AD-11). The answers never say whether an account exists.


def _usable(reset, user, now: datetime) -> bool:
    return (
        reset is not None
        and reset["used_at"] is None
        and reset["voided_at"] is None
        and now < reset["expires_at"]
        and user is not None
        and user["is_active"]
    )


async def request_password_reset(address: str, *, ip: str, now: datetime) -> int | None:
    """Ask for a reset link. Returns None when the request was taken (whether or not the address
    has an account), or the seconds until the window ends when a rate limit refused it. For an
    active User it stores the token hash and enqueues the `password_reset` notice in one
    transaction; a deactivated User or an unknown address gets nothing."""
    settings = get_settings()
    window = timedelta(minutes=settings.password_reset_rate_limit_window_minutes)
    address = normalise_email(address)
    async with get_sessionmaker().begin() as s:
        ip_count = await ratelimit.hit(s, RESET_IP, f"ip:{ip}", window=window, now=now)
        account_count = await ratelimit.hit(
            s, RESET_ACCOUNT, f"account:{address}", window=window, now=now
        )
        if (
            ip_count > settings.password_reset_rate_limit_per_ip
            or account_count > settings.password_reset_rate_limit_per_account
        ):
            limited = True
        else:
            limited = False
            row = await repo.user_by_email(s, address)
            if row is not None and row["is_active"]:
                reset_id = uuid.uuid7()
                await repo.insert_password_reset(
                    s,
                    reset_id=reset_id,
                    user_id=row["id"],
                    token_hash=auth.token_hash(auth.link_token(PASSWORD_RESET, reset_id)),
                    created_at=now,
                    expires_at=now + timedelta(minutes=settings.password_reset_valid_minutes),
                )
                await notify.enqueue(
                    s, row["id"], PASSWORD_RESET, f"{PASSWORD_RESET}:{reset_id}", ref=reset_id
                )
                log.info("password_reset_requested", user_id=str(row["id"]))
    if limited:
        log.info("password_reset_refused", error_code="rate_limited")
        return ratelimit.seconds_left(now, window)
    return None


async def check_password_reset(token: str, *, now: datetime) -> str | None:
    """The e-mail a usable reset link belongs to, or None for an unknown, used, voided or
    expired link, or one whose User is deactivated."""
    async with get_sessionmaker().begin() as s:
        reset = await repo.password_reset_by_hash(s, auth.token_hash(token))
        user = await repo.user_by_id(s, reset["user_id"]) if reset else None
        return user["email"] if _usable(reset, user, now) else None


async def confirm_password_reset(token: str, password: str, *, now: datetime) -> str | None:
    """Set a new password through a usable link: the link is marked used, the User's other open
    links are voided, every session of the User ends (Story 3.10) and the failed-login count of the
    account is cleared. Returns the e-mail, or
    None when the link is not usable (nothing changes then).

    The link is checked before the costly hash, so a made-up token costs one lookup. The write
    then locks the User row and reads the link again: two links of one User confirmed at once
    run one after the other, and the second finds itself voided."""
    if await check_password_reset(token, now=now) is None:
        log.info("password_reset_refused", error_code="reset_link_invalid")
        return None
    password_hash = await asyncio.to_thread(auth.hash_password, password)
    async with get_sessionmaker().begin() as s:
        found = await repo.password_reset_by_hash(s, auth.token_hash(token))
        user = await repo.lock_user(s, found["user_id"]) if found else None
        reset = await repo.password_reset_by_hash(s, auth.token_hash(token)) if user else None
        if not _usable(reset, user, now):
            log.info("password_reset_refused", error_code="reset_link_invalid")
            return None
        await repo.set_password_hash(s, user["id"], password_hash, now)
        # Every session the User had ends, also one a thief holds (Issue #73).
        await repo.bump_session_version(s, user["id"])
        await repo.close_password_resets(s, used_id=reset["id"], user_id=user["id"], now=now)
        await ratelimit.reset(s, LOGIN_ACCOUNT, f"account:{user['email']}")
    log.info("password_reset_done", user_id=str(user["id"]))
    return user["email"]


async def password_reset_mail_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    """The template variables of a reset mail, for `messaging` at send time: the link path with
    its token and the validity in minutes. None when the link is no longer usable, so no dead
    link is mailed. Never stored or logged."""
    if ref is None:
        return None
    reset = await repo.password_reset_by_id(session, ref)
    user = await repo.user_by_id(session, user_id)
    if reset is None or reset["user_id"] != user_id or not _usable(reset, user, now):
        return None
    return {
        "link": f"{RESET_LINK_PATH}#{auth.link_token(PASSWORD_RESET, ref)}",
        # What is left of the link's time, so a mail sent late never promises the full hour.
        "valid_minutes": math.ceil((reset["expires_at"] - now) / timedelta(minutes=1)),
    }


# Invitations to an account role (Story 3.7, FR-1, AD-11, AD-15).


class InvalidEmail(ValueError):
    """The address is not one an Invitation can go to."""


class AddressDeactivated(Exception):
    """The address belongs to a deactivated User: its link would never work (Story 3.10)."""


async def _address_deactivated(s: AsyncSession, address: str) -> bool:
    """Inside a transaction holding the address's `lock_invitation_address`, which
    `deactivate_user` also takes: whether the address belongs to a deactivated User."""
    user = await repo.user_by_email(s, address)
    return user is not None and not user["is_active"]


def _days_left(expires_at: datetime, now: datetime) -> int:
    return max(1, math.ceil((expires_at - now) / timedelta(days=1)))


def _invitation_open(row, now: datetime) -> bool:
    return (
        row is not None
        and row["accepted_at"] is None
        and row["voided_at"] is None
        and now < row["expires_at"]
    )


async def send_invitation(
    actor: uuid.UUID,
    address: str,
    role: AccountRole,
    *,
    now: datetime,
    access_request_id: uuid.UUID | None = None,
) -> InvitationOut:
    """Invite `address` to `role`. In one transaction: void the open Invitation to the same address
    and role, store the new one (its token only as a hash), enqueue its `invitation` notice and
    write the audit row. Raises `InvalidEmail` for a malformed address, and `AddressDeactivated`
    for the address of a deactivated User, before anything is stored. The caller's policy has
    already checked that `actor` may manage Users.

    With `access_request_id` naming an open request for lecturer access (Story 3.13), and a
    Lecturer Invitation to that request's own address, the request is closed as invited in the
    same transaction, and the one audit row is `access_request.invited` with both ids. A request
    that is not open, or another address or role, leaves the request as it is."""
    address = normalise_email(address)
    if not email_is_valid(address):
        raise InvalidEmail
    role = AccountRole(role)
    async with get_sessionmaker().begin() as s:
        await repo.lock_invitation_address(s, address, role.value)
        if await _address_deactivated(s, address):
            log.info("invitation_refused", error_code="account_deactivated")
            raise AddressDeactivated
        request = (
            await repo.lock_open_access_request(s, access_request_id)
            if access_request_id is not None
            else None
        )
        # Only a Lecturer Invitation to the request's own address answers it.
        if request is not None and (request["email"] != address or role is not ACCESS_REQUEST_ROLE):
            request = None
        if request is None:
            sent, voided = await _issue_invitation(
                s, actor, address, role, INVITATION_SENT, {}, now
            )
        else:
            sent, voided = await _issue_invitation(
                s,
                actor,
                address,
                role,
                ACCESS_REQUEST_INVITED,
                {},
                now,
                targets={"access_request_id": request["id"]},
            )
            await repo.close_access_request(
                s, request["id"], status="invited", actor=actor, now=now, invitation_id=sent.id
            )
    log.info(
        "invitation_sent",
        invitation_id=str(sent.id),
        actor_user_id=str(actor),
        role=role.value,
        voided_count=voided,
        access_request_id=str(request["id"]) if request is not None else None,
    )
    return sent


async def _issue_invitation(
    s: AsyncSession,
    actor: uuid.UUID,
    address: str,
    role: AccountRole,
    action: str,
    change: dict[str, object],
    now: datetime,
    *,
    targets: dict[str, uuid.UUID] | None = None,
) -> tuple[InvitationOut, int]:
    """Inside the caller's transaction, which holds `lock_invitation_address`: void the open
    Invitation to the address and role, store a new one (its token only as a hash), clear the
    requests for a new one (Story 3.10), enqueue its mail and write the audit row `action`.
    Returns the new Invitation and how many were voided."""
    invitation_id = uuid.uuid7()
    expires_at = now + timedelta(days=get_settings().role_invitation_valid_days)
    voided = await repo.void_open_invitations(s, email=address, role=role.value, now=now)
    await repo.insert_invitation(
        s,
        invitation_id=invitation_id,
        email=address,
        role=role.value,
        token_hash=auth.token_hash(auth.link_token(INVITATION, invitation_id)),
        created_at=now,
        expires_at=expires_at,
        invited_by=actor,
    )
    await repo.clear_renewal_requests(s, address, role.value)
    await notify.enqueue(s, None, INVITATION, f"{INVITATION}:{invitation_id}", ref=invitation_id)
    change = {"role": role.value, **change}
    if voided:
        change["voided_invitation_ids"] = voided
    await audit.record(
        s, actor, action, {"invitation_id": invitation_id, **(targets or {})}, change, now
    )
    sent = InvitationOut(
        id=invitation_id,
        email=address,
        role=role,
        expires_at=expires_at,
        valid_days=_days_left(expires_at, now),
    )
    return sent, len(voided)


async def invitation_mail_recipient(
    session: AsyncSession, ref: uuid.UUID, now: datetime
) -> email.Recipient | None:
    """Where an Invitation mail goes, for `messaging` at send time (AD-9, AD-14): the address,
    with the link (path and token), the role and the whole days left. None when the Invitation is
    gone, accepted, voided or expired, so no dead link is mailed. Never stored or logged."""
    row = await repo.invitation_by_id(session, ref)
    if not _invitation_open(row, now):
        return None
    context: dict[str, object] = {
        "kind": row["kind"],
        "link": f"{INVITATION_LINK_PATH}#{auth.link_token(INVITATION, ref)}",
        "role": row["role"],
        "valid_days": _days_left(row["expires_at"], now),
    }
    if row["kind"] == InvitationKind.student:
        name = await _class_name(session, row["class_id"])
        if name is None:
            return None
        context |= {"class_name": name, "last_valid_day": last_valid_day(row["expires_at"])}
    return email.Recipient(email=row["email"], name=None, context=context)


async def invitation_ids_for_email(session: AsyncSession, address: str) -> list[uuid.UUID]:
    """The ids of every Invitation to this address. For the local dev mailbox only."""
    return await repo.invitation_ids_for_email(session, normalise_email(address))


# Accepting an Invitation (Story 3.8, FR-1, FR-4, AD-11). The token is never logged; a link that
# is unknown, accepted, voided, expired, or whose address belongs to a deactivated User, is one
# answer: `invitation_link_invalid`.

INVITATION_ACCEPTED = "invitation.accepted"
"""The audit action of an accepted Invitation: the role it grants (FR-3)."""
INVITATION_BOOTSTRAP = "invitation.bootstrap"
"""The audit action of the first Admin's Invitation, sent by the system at startup (AD-17)."""
ROLE_BOOTSTRAP_GRANTED = "role.bootstrap_granted"
"""The audit action of the Admin role a listed address gains at its first login (AD-17)."""
ACCEPT_IP = "invitation_accept_ip"
ACCEPT_INVITATION = "invitation_accept_invitation"
RENEWAL_IP = "invitation_renewal_ip"
RENEWAL_INVITATION = "invitation_renewal_invitation"


@dataclass(frozen=True)
class InvitationChecked:
    id: uuid.UUID
    kind: InvitationKind
    email: str
    role: AccountRole | None
    valid_days: int
    has_account: bool
    class_label: ClassLabel | None = None
    invited_by: str | None = None


@dataclass(frozen=True)
class AcceptRefused:
    # invitation_link_invalid | account_exists | invalid_credentials | rate_limited
    code: str
    retry_after: int | None = None


ACCEPTED_KINDS = frozenset({InvitationKind.role.value, InvitationKind.student.value})
"""The Invitation kinds «Du er invitert» takes: account roles (3.8) and Student places (4.5)."""


async def _usable_invitation(
    session: AsyncSession, row, now: datetime
) -> tuple[RowMapping, RowMapping | None, ClassLabel | None] | None:
    """The open Invitation, the User its address has (or None) and, for a Student Invitation, its
    Class; or None when the link is not usable: not open, of a kind not taken here, its address
    belongs to a deactivated User, or (Student) its Roster entry was removed or its Class is
    gone."""
    if not _invitation_open(row, now) or row["kind"] not in ACCEPTED_KINDS:
        return None
    user = await repo.user_by_email(session, row["email"])
    if user is not None and not user["is_active"]:
        return None
    label = None
    if row["kind"] == InvitationKind.student:
        entry = await repo.roster_entry_by_id(session, row["roster_entry_id"])
        if entry is None or entry["removed_at"] is not None:
            return None
        label = await _class_label(session, row["class_id"])
        if label is None:
            return None
    return row, user, label


def _student_days_left(expires_at: datetime, now: datetime) -> int:
    """The days from today to a Student link's last valid day, in Europe/Oslo: a sending valid
    for 14 days reads «14 dager» on the day it is sent, and the last day reads «én dag»."""
    return max(1, (last_valid_day(expires_at) - now.astimezone(OSLO).date()).days)


async def check_invitation(token: str, *, now: datetime) -> InvitationChecked | None:
    """What «Du er invitert» shows for a usable link, or None."""
    async with get_sessionmaker().begin() as s:
        row = await repo.invitation_by_hash(s, auth.token_hash(token))
        usable = await _usable_invitation(s, row, now)
        if usable is None:
            return None
        row, user, label = usable
        inviter = None
        if label is not None and row["invited_by"] is not None:
            found = await repo.user_by_id(s, row["invited_by"])
            inviter = found["name"] if found is not None else None
    student = row["kind"] == InvitationKind.student
    return InvitationChecked(
        id=row["id"],
        kind=InvitationKind(row["kind"]),
        email=row["email"],
        role=None if student else AccountRole(row["role"]),
        valid_days=(
            _student_days_left(row["expires_at"], now)
            if student
            else _days_left(row["expires_at"], now)
        ),
        has_account=user is not None,
        class_label=label,
        invited_by=inviter,
    )


def _invitation_window() -> timedelta:
    return timedelta(minutes=get_settings().invitation_rate_limit_window_minutes)


async def _count_acceptance(token: str, ip: str, now: datetime) -> int | None:
    """Count one acceptance attempt per client address and per link, in its own transaction so
    the count stays when the attempt fails. The seconds left when a limit is passed, else None."""
    settings = get_settings()
    window = _invitation_window()
    async with get_sessionmaker().begin() as s:
        ip_count = await ratelimit.hit(s, ACCEPT_IP, f"ip:{ip}", window=window, now=now)
        link_count = await ratelimit.hit(
            s, ACCEPT_INVITATION, f"invitation:{auth.token_hash(token)}", window=window, now=now
        )
    if (
        ip_count > settings.invitation_accept_rate_limit_per_ip
        or link_count > settings.invitation_accept_rate_limit_per_invitation
    ):
        log.info("invitation_accept_refused", error_code="rate_limited")
        return ratelimit.seconds_left(now, window)
    return None


async def _locked_open_invitation(s: AsyncSession, token: str, now: datetime):
    """The Invitation of `token`, locked, if it is still open; else None."""
    found = await repo.invitation_by_hash(s, auth.token_hash(token))
    row = await repo.lock_invitation(s, found["id"]) if found else None
    return row if _invitation_open(row, now) else None


async def accept_invitation_new(
    token: str, name: str, password: str, *, ip: str, now: datetime
) -> LoginOk | AcceptRefused:
    """Create the account an Invitation offers: in one transaction the User with the Invitation's
    role, the Invitation marked accepted, and one audit row. The caller logs the User in.
    `account_exists` when the address has a User by then (nothing changes)."""
    retry_after = await _count_acceptance(token, ip, now)
    if retry_after is not None:
        return AcceptRefused("rate_limited", retry_after)
    checked = await check_invitation(token, now=now)
    if checked is None:
        log.info("invitation_accept_refused", error_code="invitation_link_invalid")
        return AcceptRefused("invitation_link_invalid")
    if checked.has_account:
        log.info("invitation_accept_refused", error_code="account_exists")
        return AcceptRefused("account_exists")
    password_hash = await asyncio.to_thread(auth.hash_password, password)
    user_id = uuid.uuid7()
    async with get_sessionmaker().begin() as s:
        row = await _locked_open_invitation(s, token, now)
        if row is None:
            log.info("invitation_accept_refused", error_code="invitation_link_invalid")
            return AcceptRefused("invitation_link_invalid")
        student = row["kind"] == InvitationKind.student
        await repo.lock_user_address(s, row["email"])
        if await repo.user_by_email(s, row["email"]) is not None:
            log.info("invitation_accept_refused", error_code="account_exists")
            return AcceptRefused("account_exists")
        # Checked before anything is written, so a refusal leaves nothing behind.
        if student and not await _roster_entry_open(s, row):
            log.info("invitation_accept_refused", error_code="invitation_link_invalid")
            return AcceptRefused("invitation_link_invalid")
        await repo.insert_user(
            s,
            user_id=user_id,
            email=row["email"],
            name=name,
            password_hash=password_hash,
            is_active=True,
            # A Student is no account role: the Roster entry makes them one (Story 4.5).
            roles=[] if student else [row["role"]],
        )
        await repo.mark_invitation_accepted(s, row["id"], now)
        if student:
            await _join_class(s, row, user_id)
        else:
            await audit.record(
                s,
                user_id,
                INVITATION_ACCEPTED,
                {"invitation_id": row["id"], "user_id": user_id},
                {"role": row["role"], "account": "created"},
                now,
            )
    log.info("invitation_accepted", invitation_id=str(row["id"]), user_id=str(user_id))
    roles = [] if student else [AccountRole(row["role"])]
    return LoginOk(UserOut(id=user_id, name=name, email=row["email"], roles=roles), 0)


async def _roster_entry_open(s: AsyncSession, invitation: RowMapping) -> bool:
    """Lock a Student Invitation's Roster entry; whether it is still on the Roster."""
    entry = await repo.roster_entry_by_id(s, invitation["roster_entry_id"], lock=True)
    return entry is not None and entry["removed_at"] is None


async def _join_class(s: AsyncSession, invitation: RowMapping, user_id: uuid.UUID) -> None:
    """Inside the acceptance transaction, which holds the entry's lock: link the Roster entry to
    the User and mark it registered (FR-8), and tell the User's open pages (`user:<id>`)."""
    linked = await repo.register_roster_entry(
        s, invitation["roster_entry_id"], user_id, RosterRegistration.registered.value
    )
    if not linked:  # the entry's lock rules this out; never accept without the link
        raise RuntimeError("the Roster entry of a Student Invitation was not linked")
    await events.emit(s, "user", str(user_id))


async def accept_invitation_existing(
    token: str, password: str, *, ip: str, now: datetime
) -> LoginOk | AcceptRefused:
    """Add an Invitation's role to the account its address already has, proven by that account's
    password (the login limits apply). In one transaction: the role, the Invitation marked
    accepted, one audit row. The caller logs the User in."""
    retry_after = await _count_acceptance(token, ip, now)
    if retry_after is not None:
        return AcceptRefused("rate_limited", retry_after)
    checked = await check_invitation(token, now=now)
    if checked is None or not checked.has_account:
        log.info("invitation_accept_refused", error_code="invitation_link_invalid")
        return AcceptRefused("invitation_link_invalid")
    outcome = await authenticate(checked.email, password, ip=ip, now=now)
    if isinstance(outcome, LoginRefused):
        if outcome.code == "account_deactivated":
            return AcceptRefused("invitation_link_invalid")
        return AcceptRefused(outcome.code, outcome.retry_after)
    async with get_sessionmaker().begin() as s:
        row = await _locked_open_invitation(s, token, now)
        user = await repo.lock_user(s, outcome.user.id) if row else None
        if (
            row is None
            or user is None
            or not user["is_active"]
            or user["email"] != row["email"]
            or (row["kind"] == InvitationKind.student and not await _roster_entry_open(s, row))
        ):
            log.info("invitation_accept_refused", error_code="invitation_link_invalid")
            return AcceptRefused("invitation_link_invalid")
        await repo.mark_invitation_accepted(s, row["id"], now)
        if row["kind"] == InvitationKind.student:
            # The same account becomes a Student in this Class too; never a second User (FR-4).
            await _join_class(s, row, user["id"])
        else:
            granted = await repo.grant_role(s, user["id"], row["role"])
            await audit.record(
                s,
                user["id"],
                INVITATION_ACCEPTED,
                {"invitation_id": row["id"], "user_id": user["id"]},
                {"role": row["role"], "account": "existing", "role_added": granted},
                now,
            )
        roles = await repo.roles_of(s, user["id"])
    log.info("invitation_accepted", invitation_id=str(row["id"]), user_id=str(user["id"]))
    return LoginOk(_user_out(user, roles), user["session_version"])


async def request_invitation_renewal(token: str, *, ip: str, now: datetime) -> int | None:
    """Ask for a new Invitation from a link that no longer works. The answer is the same for any
    link (None), or the seconds left when a rate limit refused it. Marks `renewal_requested_at` on
    an Invitation that is expired or voided, never on an accepted or open one."""
    settings = get_settings()
    window = _invitation_window()
    hashed = auth.token_hash(token)
    async with get_sessionmaker().begin() as s:
        ip_count = await ratelimit.hit(s, RENEWAL_IP, f"ip:{ip}", window=window, now=now)
        link_count = await ratelimit.hit(
            s, RENEWAL_INVITATION, f"invitation:{hashed}", window=window, now=now
        )
        limited = (
            ip_count > settings.invitation_renewal_rate_limit_per_ip
            or link_count > settings.invitation_renewal_rate_limit_per_invitation
        )
        if not limited:
            row = await repo.invitation_by_hash(s, hashed)
            if row is not None and row["accepted_at"] is None and not _invitation_open(row, now):
                await repo.set_renewal_requested(s, row["id"], now)
                log.info("invitation_renewal_requested", invitation_id=str(row["id"]))
    if limited:
        log.info("invitation_renewal_refused", error_code="rate_limited")
        return ratelimit.seconds_left(now, window)
    return None


# «Brukere og roller»: the User list and the account roles (Story 3.9, FR-2, FR-3, AD-8, AD-15).

ROLE_GRANTED = "role.granted"
"""The audit action of a role the Admin grants (FR-3)."""
ROLE_REVOKED = "role.revoked"
"""The audit action of a role the Admin revokes (FR-3)."""
ROLES_KEEP_ONE_ACTIVE = frozenset({AccountRole.admin.value})
"""Roles at least one active User always holds: the product is never left without an Admin."""

RevokeBlocker = Callable[[AsyncSession, uuid.UUID], Awaitable[int]]
"""Asked inside the revoke transaction: how many Classes the User owns that keep the role. Epic 4
registers the one that reads Class ownership."""
_REVOKE_BLOCKERS: dict[str, list[RevokeBlocker]] = {}


def register_revoke_blocker(role: AccountRole, blocker: RevokeBlocker) -> None:
    """Called by the module that owns what a revoke of `role` must not orphan, at import."""
    _REVOKE_BLOCKERS.setdefault(AccountRole(role).value, []).append(blocker)


class InvalidCursor(ValueError):
    """A `cursor` this api did not hand out."""


@dataclass(frozen=True)
class RoleRefused:
    code: str  # not_found | last_admin | role_revoke_blocked
    classes: int = 0


def _list_item(row, roles: list[str]) -> UserListItem:
    return UserListItem(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        roles=[AccountRole(role) for role in roles],
        is_active=row["is_active"],
    )


def _encode_cursor(user_id: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(user_id.bytes).decode().rstrip("=")


def _decode_cursor(cursor: str) -> uuid.UUID:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        return uuid.UUID(bytes=raw)
    except ValueError as error:
        raise InvalidCursor from error


async def list_users(search: str, cursor: str | None, limit: int) -> UserListOut:
    """A page of Users for the Admin, searched in `users` only. The search text is never logged
    (AD-14). Raises `InvalidCursor` for a cursor this api did not hand out."""
    after = _decode_cursor(cursor) if cursor else None
    async with get_sessionmaker().begin() as s:
        rows = await repo.list_users(s, search=search.strip(), after=after, limit=limit + 1)
    if rows is None:  # the cursor names no User
        raise InvalidCursor
    page = rows[:limit]
    return UserListOut(
        items=[_list_item(row, row["roles"] or []) for row in page],
        next_cursor=_encode_cursor(page[-1]["id"]) if len(rows) > limit else None,
    )


async def grant_role(
    actor: uuid.UUID, user_id: uuid.UUID, role: AccountRole, *, now: datetime
) -> UserListItem | RoleRefused:
    """Give the User `role`. In one transaction: the role, one audit row and `user:<id>`, so the
    User's next request carries it. A role already held changes and writes nothing."""
    role = AccountRole(role)
    async with get_sessionmaker().begin() as s:
        user = await repo.lock_user(s, user_id)
        if user is None:
            return RoleRefused("not_found")
        if await repo.grant_role(s, user_id, role.value):
            await audit.record(
                s, actor, ROLE_GRANTED, {"user_id": user_id}, {"role": role.value}, now
            )
            await events.emit(s, "user", str(user_id))
            granted = True
        else:
            granted = False
        roles = await repo.roles_of(s, user_id)
    if granted:
        log.info("role_granted", user_id=str(user_id), action=ROLE_GRANTED)
    return _list_item(user, roles)


async def revoke_role(
    actor: uuid.UUID, user_id: uuid.UUID, role: AccountRole, *, now: datetime
) -> UserListItem | RoleRefused:
    """Take `role` from the User. In one transaction: the role, one audit row and `user:<id>`, so
    the User's next request is held to it. Refused, with nothing changed, when it would leave no
    active holder of a role in `ROLES_KEEP_ONE_ACTIVE` (`last_admin`) or when a registered revoke
    blocker reports owned Classes (`role_revoke_blocked`). A role not held writes nothing."""
    role = AccountRole(role)
    async with get_sessionmaker().begin() as s:
        # Every revoke of one role runs in turn, so two Admins revoking each other cannot both
        # pass the count below.
        await repo.lock_role(s, role.value)
        user = await repo.lock_user(s, user_id)
        if user is None:
            return RoleRefused("not_found")
        roles = await repo.roles_of(s, user_id)
        if role.value not in set(roles):
            return _list_item(user, roles)
        # Only an active holder can be the last active Admin; a deactivated one never is.
        if (
            role.value in ROLES_KEEP_ONE_ACTIVE
            and user["is_active"]
            and await repo.count_active_holders(s, role.value, excluding=user_id) == 0
        ):
            log.info("role_revoke_refused", user_id=str(user_id), error_code="last_admin")
            return RoleRefused("last_admin")
        classes = 0
        for blocker in _REVOKE_BLOCKERS.get(role.value, ()):
            classes += max(0, await blocker(s, user_id))
        if classes > 0:
            log.info("role_revoke_refused", user_id=str(user_id), error_code="role_revoke_blocked")
            return RoleRefused("role_revoke_blocked", classes)
        await repo.remove_role(s, user_id, role.value)
        await audit.record(s, actor, ROLE_REVOKED, {"user_id": user_id}, {"role": role.value}, now)
        await events.emit(s, "user", str(user_id))
        roles = await repo.roles_of(s, user_id)
    log.info("role_revoked", user_id=str(user_id), action=ROLE_REVOKED)
    return _list_item(user, roles)


# Deactivating and reactivating Users (Story 3.10, FR-3, AD-8, AD-11, AD-15).

USER_DEACTIVATED = "user.deactivated"
"""The audit action of a User the Admin deactivates (FR-3)."""
USER_REACTIVATED = "user.reactivated"
"""The audit action of a User the Admin reactivates (FR-3)."""


@dataclass(frozen=True)
class StatusRefused:
    code: str  # not_found | last_admin


async def deactivate_user(
    actor: uuid.UUID, user_id: uuid.UUID, *, now: datetime
) -> UserListItem | StatusRefused:
    """Deactivate the User. In one transaction: `is_active` false, every session of theirs ended
    (the session version), their open reset links and Invitations voided, one audit row and
    `user:<id>`. Nothing
    else of theirs changes: roles, name, e-mail and password stay. Refused with `last_admin` for
    the actor themselves, and when it would leave no active holder of a role in
    `ROLES_KEEP_ONE_ACTIVE`. An inactive User changes and writes nothing."""
    async with get_sessionmaker().begin() as s:
        # The role locks first, as `revoke_role` takes them: a deactivation and a revoke of the
        # last two Admins run in turn, so they cannot both pass the count below.
        for role in sorted(ROLES_KEEP_ONE_ACTIVE):
            await repo.lock_role(s, role)
        user = await repo.lock_user(s, user_id)
        if user is None:
            return StatusRefused("not_found")
        roles = await repo.roles_of(s, user_id)
        if not user["is_active"]:
            return _list_item(user, roles)
        if user_id == actor:
            log.info("user_deactivate_refused", user_id=str(user_id), error_code="last_admin")
            return StatusRefused("last_admin")
        for role in sorted(ROLES_KEEP_ONE_ACTIVE & set(roles)):
            if await repo.count_active_holders(s, role, excluding=user_id) == 0:
                log.info("user_deactivate_refused", user_id=str(user_id), error_code="last_admin")
                return StatusRefused("last_admin")
        await repo.set_active(s, user_id, False, now)
        await repo.bump_session_version(s, user_id)
        await repo.void_open_password_resets(s, user_id, now)
        # Their open Invitations too: the list then shows them as expired, and none works again
        # after a reactivation. The address locks first, as a send or resend holds them: one
        # that read the User as active finishes before the void, and one after it sees the
        # deactivation, so no open Invitation to a deactivated address is left.
        for role in sorted(r.value for r in AccountRole):
            await repo.lock_invitation_address(s, user["email"], role)
        await repo.void_open_invitations_to(s, user["email"], now)
        await audit.record(s, actor, USER_DEACTIVATED, {"user_id": user_id}, {}, now)
        await events.emit(s, "user", str(user_id))
        user = await repo.user_by_id(s, user_id)
    log.info("user_deactivated", user_id=str(user_id), action=USER_DEACTIVATED)
    return _list_item(user, roles)


async def reactivate_user(
    actor: uuid.UUID, user_id: uuid.UUID, *, now: datetime
) -> UserListItem | StatusRefused:
    """Reactivate the User: they log in again with the same password and roles. In one
    transaction with one audit row and `user:<id>`. An active User changes and writes nothing.
    Sessions from before the deactivation stay ended."""
    async with get_sessionmaker().begin() as s:
        user = await repo.lock_user(s, user_id)
        if user is None:
            return StatusRefused("not_found")
        roles = await repo.roles_of(s, user_id)
        if user["is_active"]:
            return _list_item(user, roles)
        await repo.set_active(s, user_id, True, now)
        await audit.record(s, actor, USER_REACTIVATED, {"user_id": user_id}, {}, now)
        await events.emit(s, "user", str(user_id))
        user = await repo.user_by_id(s, user_id)
    log.info("user_reactivated", user_id=str(user_id), action=USER_REACTIVATED)
    return _list_item(user, roles)


# The Invitation list and resending (Story 3.10, FR-1, FR-3).

INVITATION_RESENT = "invitation.resent"
"""The audit action of an Invitation the Admin sends again (FR-3)."""


@dataclass(frozen=True)
class ResendRefused:
    code: str  # not_found | invitation_accepted | invitation_superseded | account_deactivated


def _invitation_status(row, now: datetime) -> InvitationStatus:
    if row["accepted_at"] is not None:
        return InvitationStatus.accepted
    return InvitationStatus.open if _invitation_open(row, now) else InvitationStatus.expired


def _link_end(row) -> datetime:
    """When the link stops or stopped working: its expiry, or the moment it was voided."""
    voided = row["voided_at"]
    return voided if voided is not None and voided < row["expires_at"] else row["expires_at"]


async def list_invitations(cursor: str | None, limit: int, *, now: datetime) -> InvitationListOut:
    """A page of the newest Invitation per address and role, newest first. Raises
    `InvalidCursor` for a cursor this api did not hand out."""
    after = _decode_cursor(cursor) if cursor else None
    async with get_sessionmaker().begin() as s:
        rows = await repo.list_invitations(s, after=after, limit=limit + 1)
    if rows is None:
        raise InvalidCursor
    page = rows[:limit]
    return InvitationListOut(
        items=[
            InvitationListItem(
                id=row["id"],
                email=row["email"],
                role=AccountRole(row["role"]),
                status=_invitation_status(row, now),
                expires_at=_link_end(row),
                accepted_at=row["accepted_at"],
                account_deactivated=row["account_deactivated"],
                renewal_requested=row["renewal_requested"],
            )
            for row in page
        ],
        next_cursor=_encode_cursor(page[-1]["id"]) if len(rows) > limit else None,
    )


async def resend_invitation(
    actor: uuid.UUID, invitation_id: uuid.UUID, *, now: datetime
) -> InvitationOut | ResendRefused:
    """Send an open or expired Invitation again: its link stops working and a new Invitation to the
    same address and role, with a new token and expiry, is mailed; the requests for a new one are
    cleared; one audit row. Refused for an accepted Invitation, one a newer Invitation to the
    address and role replaced, and an address whose account is deactivated."""
    async with get_sessionmaker().begin() as s:
        found = await repo.invitation_by_id(s, invitation_id)
        if found is None or found["kind"] != InvitationKind.role:
            return ResendRefused("not_found")
        address, role = found["email"], AccountRole(found["role"])
        await repo.lock_invitation_address(s, address, role.value)
        # Locked as an acceptance locks it, so an acceptance under way finishes first.
        row = await repo.lock_invitation(s, invitation_id)
        refusal = None
        if row["accepted_at"] is not None:
            refusal = "invitation_accepted"
        elif await repo.newest_invitation_id(s, address, role.value) != invitation_id:
            refusal = "invitation_superseded"
        elif await _address_deactivated(s, address):
            refusal = "account_deactivated"
        if refusal is not None:
            log.info(
                "invitation_resend_refused", invitation_id=str(invitation_id), error_code=refusal
            )
            return ResendRefused(refusal)
        sent, _ = await _issue_invitation(
            s,
            actor,
            address,
            role,
            INVITATION_RESENT,
            {"resent_invitation_id": invitation_id},
            now,
        )
    log.info(
        "invitation_resent",
        invitation_id=str(sent.id),
        resent_invitation_id=str(invitation_id),
        actor_user_id=str(actor),
    )
    return sent


# Institutions (Story 3.11, FR-3). Other modules read them through `list_institutions` and
# `get_institution`; there is no delete in v1.

INSTITUTION_CREATED = "institution.created"
INSTITUTION_RENAMED = "institution.renamed"
"""The audit actions of an Institution the Admin creates or renames (FR-3, AD-15)."""


@dataclass(frozen=True)
class InstitutionRefused:
    code: str  # not_found | institution_name_taken


def _institution_out(row) -> InstitutionOut:
    return InstitutionOut(id=row["id"], name=row["name"], created_at=row["created_at"])


async def create_institution(
    actor: uuid.UUID, name: str, *, now: datetime
) -> InstitutionOut | InstitutionRefused:
    """Store a new Institution with one audit row, in one transaction. Raises
    `InvalidInstitutionName` for a name the rule refuses; refused with `institution_name_taken`
    when another Institution has the name, compared case-insensitively."""
    name = institution_name(name)
    async with get_sessionmaker().begin() as s:
        await repo.lock_institution_names(s)
        if await repo.institution_name_taken(s, name):
            log.info("institution_refused", error_code="institution_name_taken")
            return InstitutionRefused("institution_name_taken")
        row = await repo.insert_institution(s, uuid.uuid7(), name, now)
        await audit.record(
            s, actor, INSTITUTION_CREATED, {"institution_id": row["id"]}, {"name": name}, now
        )
    log.info("institution_created", institution_id=str(row["id"]), actor_user_id=str(actor))
    return _institution_out(row)


async def rename_institution(
    actor: uuid.UUID, institution_id: uuid.UUID, name: str, *, now: datetime
) -> InstitutionOut | InstitutionRefused:
    """Give an Institution a new name, with one audit row holding the old and the new name. The
    exact current name changes and writes nothing; a change of case only is a rename. Raises
    `InvalidInstitutionName`; refused with `not_found` or `institution_name_taken`."""
    name = institution_name(name)
    async with get_sessionmaker().begin() as s:
        await repo.lock_institution_names(s)
        row = await repo.lock_institution(s, institution_id)
        if row is None:
            return InstitutionRefused("not_found")
        old = row["name"]
        if name == old:
            return _institution_out(row)
        if await repo.institution_name_taken(s, name, excluding=institution_id):
            log.info(
                "institution_refused",
                institution_id=str(institution_id),
                error_code="institution_name_taken",
            )
            return InstitutionRefused("institution_name_taken")
        row = await repo.rename_institution(s, institution_id, name, now)
        await audit.record(
            s,
            actor,
            INSTITUTION_RENAMED,
            {"institution_id": institution_id},
            {"old_name": old, "new_name": name},
            now,
        )
    log.info("institution_renamed", institution_id=str(institution_id), actor_user_id=str(actor))
    return _institution_out(row)


async def institution_page(cursor: str | None, limit: int) -> InstitutionListOut:
    """A page of Institutions for the Admin, newest first. Raises `InvalidCursor` for a cursor
    this api did not hand out."""
    after = _decode_cursor(cursor) if cursor else None
    async with get_sessionmaker().begin() as s:
        rows = await repo.list_institutions(s, after=after, limit=limit + 1)
    if rows is None:
        raise InvalidCursor
    page = rows[:limit]
    return InstitutionListOut(
        items=[_institution_out(row) for row in page],
        next_cursor=_encode_cursor(page[-1]["id"]) if len(rows) > limit else None,
    )


async def list_institutions() -> list[InstitutionOut]:
    """Every Institution, by name: for the modules that let a User choose one (Epic 4 on)."""
    async with get_sessionmaker().begin() as s:
        rows = await repo.all_institutions(s)
    return [_institution_out(row) for row in rows]


DEMO_INSTITUTION = "Demohøgskolen"
"""The Institution of the local demo Class (AD-17, Story 4.1)."""


async def ensure_demo_institution(session: AsyncSession, now: datetime) -> uuid.UUID:
    """For the local demo seed only (`classes.seed`, `APP_ENV=local`): the id of the Institution
    «Demohøgskolen», created in the caller's transaction when no Institution has the name. No
    audit row: the system seeds it, no Admin acts."""
    await repo.lock_institution_names(session)  # as a create by an Admin takes it
    found = await repo.institution_id_by_name(session, DEMO_INSTITUTION)
    if found is not None:
        return found
    row = await repo.insert_institution(session, uuid.uuid7(), DEMO_INSTITUTION, now)
    return row["id"]


async def get_institution(institution_id: uuid.UUID) -> InstitutionOut | None:
    """One Institution, or None when there is none with that id."""
    async with get_sessionmaker().begin() as s:
        row = await repo.institution_by_id(s, institution_id)
    return _institution_out(row) if row else None


# Requests for lecturer access from the Landing (Story 3.13, FR-1, FR-3). A request never
# creates a User or an Invitation; the Admin invites from it (`send_invitation`) or dismisses it.

ACCESS_REQUEST_IP = "access_request_ip"
ACCESS_REQUEST_ROLE = AccountRole.lecturer
"""The role a request for lecturer access asks for: only an Invitation to it answers the request
(a data rule of the request, not an access check)."""
ACCESS_REQUEST_INVITED = "access_request.invited"
"""The audit action of an Invitation the Admin sends from a request: one row for both."""
ACCESS_REQUEST_DISMISSED = "access_request.dismissed"
"""The audit action of a request the Admin dismisses."""


async def request_access(
    name: str, address: str, institution: str, *, ip: str, now: datetime
) -> int | None:
    """Store a request for lecturer access, or update the open request of the same address.
    Returns None when it was taken, or the seconds until the window ends when the per-IP limit
    refused it (nothing is stored then). The answer never says whether the address has an
    account. The caller has already checked and normalised the fields (`AccessRequestIn`)."""
    settings = get_settings()
    window = timedelta(minutes=settings.access_request_rate_limit_window_minutes)
    async with get_sessionmaker().begin() as s:
        count = await ratelimit.hit(s, ACCESS_REQUEST_IP, f"ip:{ip}", window=window, now=now)
        limited = count > settings.access_request_rate_limit_per_ip
        request_id = None
        if not limited:
            request_id = await repo.upsert_access_request(
                s,
                request_id=uuid.uuid7(),
                name=name,
                email=address,
                institution=institution,
                now=now,
            )
    if limited:
        log.info("access_request_refused", error_code="rate_limited")
        return ratelimit.seconds_left(now, window)
    log.info("access_request_received", access_request_id=str(request_id))
    return None


def _access_request_out(row) -> AccessRequestOut:
    return AccessRequestOut(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        institution=row["institution"],
        requested_at=row["requested_at"],
    )


async def access_request_page(cursor: str | None, limit: int) -> AccessRequestListOut:
    """A page of the open requests, newest first. Raises `InvalidCursor` for a cursor this api
    did not hand out."""
    after = _decode_cursor(cursor) if cursor else None
    async with get_sessionmaker().begin() as s:
        rows = await repo.list_open_access_requests(s, after=after, limit=limit + 1)
    if rows is None:
        raise InvalidCursor
    page = rows[:limit]
    return AccessRequestListOut(
        items=[_access_request_out(row) for row in page],
        next_cursor=_encode_cursor(page[-1]["id"]) if len(rows) > limit else None,
    )


async def dismiss_access_request(actor: uuid.UUID, request_id: uuid.UUID, *, now: datetime) -> bool:
    """Close an open request as dismissed, with one audit row. False when no open request has the
    id (unknown, invited or already dismissed)."""
    async with get_sessionmaker().begin() as s:
        row = await repo.lock_open_access_request(s, request_id)
        if row is None:
            return False
        await repo.close_access_request(s, request_id, status="dismissed", actor=actor, now=now)
        await audit.record(
            s, actor, ACCESS_REQUEST_DISMISSED, {"access_request_id": request_id}, {}, now
        )
    log.info(
        "access_request_dismissed", access_request_id=str(request_id), actor_user_id=str(actor)
    )
    return True


# Labels for the audit page (Story 3.12, AD-14): audit rows hold ids, names are read here.


async def _labels(table: str, ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    async with get_sessionmaker().begin() as s:
        return await repo.labels_of(s, table, ids)


async def user_labels(ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    """The Users' names now; registered with `platform/audit` for the target key `user_id`."""
    return await _labels("users", ids)


async def invitation_labels(ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    """The Invitations' addresses; registered for the target key `invitation_id`."""
    return await _labels("invitations", ids)


async def institution_labels(ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    """The Institutions' names now; registered for the target key `institution_id`."""
    return await _labels("institutions", ids)


async def access_request_labels(ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    """The names the requests for lecturer access were sent with; registered for the target key
    `access_request_id` (Story 3.13)."""
    return await _labels("access_requests", ids)


# The first Admin (AD-17, Story 3.8).


def bootstrap_addresses() -> list[str]:
    """The valid, normalised addresses of `BOOTSTRAP_ADMIN_EMAILS`, each once, in list order."""
    found: list[str] = []
    for position, part in enumerate(get_settings().bootstrap_admin_emails.split(",")):
        address = normalise_email(part)
        if not address:
            continue
        if not email_is_valid(address):
            log.warning("bootstrap_address_invalid", position=position)
            continue
        if address not in found:
            found.append(address)
    return found


async def ensure_bootstrap_invitations(now: datetime) -> list[uuid.UUID]:
    """At api start in production: an Admin Invitation for every listed address that has no User
    and no open, unexpired Admin Invitation, with its mail and an audit row with the system as
    actor. Safe to run on every start and from parallel starts. Returns the new ids."""
    created: list[uuid.UUID] = []
    role = AccountRole.admin.value
    for address in bootstrap_addresses():
        async with get_sessionmaker().begin() as s:
            await repo.lock_invitation_address(s, address, role)
            if await repo.user_by_email(s, address) is not None:
                continue
            existing = await repo.open_invitation(s, address, role)
            if existing is not None and now < existing["expires_at"]:
                continue
            voided = await repo.void_open_invitations(s, email=address, role=role, now=now)
            invitation_id = uuid.uuid7()
            await repo.insert_invitation(
                s,
                invitation_id=invitation_id,
                email=address,
                role=role,
                token_hash=auth.token_hash(auth.link_token(INVITATION, invitation_id)),
                created_at=now,
                expires_at=now + timedelta(days=get_settings().role_invitation_valid_days),
                invited_by=None,
            )
            await notify.enqueue(
                s, None, INVITATION, f"{INVITATION}:{invitation_id}", ref=invitation_id
            )
            change: dict[str, object] = {"role": role}
            if voided:
                change["voided_invitation_ids"] = voided
            await audit.record(
                s, None, INVITATION_BOOTSTRAP, {"invitation_id": invitation_id}, change, now
            )
        log.info("bootstrap_invitation_sent", invitation_id=str(invitation_id))
        created.append(invitation_id)
    return created


async def _grant_bootstrap_admin(
    s: AsyncSession, user_id: uuid.UUID, address: str, now: datetime
) -> bool:
    """In production, give a listed address the Admin role at its first login, once: the audit
    row marks it done, so a later revoke in the Admin-område sticks. The mark is written also when
    the User already holds the role (`role_added: false`). True when the role was granted now."""
    # The Given of the bootstrap AC is production; elsewhere the list grants nothing.
    if get_settings().app_env != "production" or address not in bootstrap_addresses():
        return False
    # One login of the User at a time here, so parallel logins write one mark.
    await repo.lock_user(s, user_id)
    events = await audit.events_for_target(s, "user_id", user_id)
    if any(event.action == ROLE_BOOTSTRAP_GRANTED for event in events):
        return False
    granted = await repo.grant_role(s, user_id, AccountRole.admin.value)
    await audit.record(
        s,
        None,
        ROLE_BOOTSTRAP_GRANTED,
        {"user_id": user_id},
        {"role": "admin", "role_added": granted},
        now,
    )
    log.info("bootstrap_admin_checked", user_id=str(user_id), role_added=granted)
    return granted


# Staged Roster uploads (Story 4.2, FR-7, AD-14). `classes.service` checks that the User may
# manage the Class and calls these; the file is parsed in memory and only its cells are staged.
# Logs carry ids and counts only, never a file name, a cell or an address.


RosterUnreadable = roster_file.RosterUnreadable
"""Raised by `stage_roster_upload` for a file that cannot be used."""


async def purge_expired_roster_uploads(now: datetime) -> int:
    """Delete every staged upload past its `expires_at`. Idempotent; runs on every upload and
    every staging read, and can be called from `ops.sweep` unchanged."""
    async with get_sessionmaker().begin() as s:
        purged = await repo.purge_expired_roster_uploads(s, now)
    if purged:
        log.info("roster_uploads_purged", count=purged)
    return purged


async def stage_roster_upload(
    class_id: uuid.UUID, uploader: uuid.UUID, file_name: str, data: bytes, *, now: datetime
) -> RosterUploadOut:
    """Parse the file and stage its rows for the Class, replacing any earlier staged upload in
    the same transaction. Raises `roster_file.RosterUnreadable`; nothing is staged then, and an
    earlier staged upload stays."""
    await purge_expired_roster_uploads(now)
    settings = get_settings()
    # Parsing is CPU work: off the event loop, so other requests are not held up.
    parsed = await asyncio.to_thread(
        roster_file.parse, file_name, data, max_rows=settings.roster_max_rows
    )
    counts = await asyncio.to_thread(
        roster_file.address_counts, [cells for _, cells in parsed.rows], parsed.column_count
    )
    suggested = roster_file.suggested_column(counts)
    upload_id = uuid.uuid7()
    async with get_sessionmaker().begin() as s:
        # Two uploads for one Class at once: the second waits, then replaces the first.
        await repo.lock_roster_staging(s, class_id)
        await repo.delete_roster_upload(s, class_id)
        on_roster = await repo.roster_addresses(s, class_id)
        await repo.insert_roster_upload(
            s,
            upload_id=upload_id,
            class_id=class_id,
            uploaded_by=uploader,
            file_name=file_name,
            headers=parsed.headers,
            has_header=parsed.has_header,
            rows=parsed.rows,
            chosen_column=suggested,
            now=now,
            expires_at=now + timedelta(hours=settings.roster_staging_ttl_hours),
        )
    log.info(
        "roster_upload_staged",
        class_id=str(class_id),
        upload_id=str(upload_id),
        user_id=str(uploader),
        rows=len(parsed.rows),
        columns=parsed.column_count,
    )
    return await asyncio.to_thread(
        _roster_upload_out,
        upload_id=upload_id,
        on_roster=on_roster,
        source=RosterSource.file,
        file_name=file_name,
        headers=parsed.headers,
        has_header=parsed.has_header,
        rows=parsed.rows,
        counts=counts,
        chosen=suggested,
    )


async def stage_roster_paste(
    class_id: uuid.UUID, uploader: uuid.UUID, text: str, *, now: datetime
) -> RosterUploadOut:
    """Stage pasted addresses for the Class as one-column rows, numbered by their place in the
    text, replacing any earlier staged upload (Story 4.3). Raises `RosterPasteTooLong` for text
    over `ROSTER_MAX_FILE_MB` or more addresses than `ROSTER_MAX_ROWS`; nothing is staged then.
    Empty text stages no rows."""
    await purge_expired_roster_uploads(now)
    settings = get_settings()
    if len(text.encode("utf-8", errors="replace")) > settings.roster_max_file_mb * 1024 * 1024:
        raise RosterPasteTooLong
    pieces = await asyncio.to_thread(roster_file.split_paste, text, limit=settings.roster_max_rows)
    if len(pieces) > settings.roster_max_rows:
        raise RosterPasteTooLong
    rows = [(n, [piece]) for n, piece in enumerate(pieces, start=1)]
    upload_id = uuid.uuid7()
    async with get_sessionmaker().begin() as s:
        await repo.lock_roster_staging(s, class_id)
        await repo.delete_roster_upload(s, class_id)
        on_roster = await repo.roster_addresses(s, class_id)
        await repo.insert_roster_upload(
            s,
            upload_id=upload_id,
            class_id=class_id,
            uploaded_by=uploader,
            file_name="",
            headers=[""],
            has_header=False,
            rows=rows,
            chosen_column=0,
            now=now,
            expires_at=now + timedelta(hours=settings.roster_staging_ttl_hours),
            source=RosterSource.paste,
        )
    log.info(
        "roster_paste_staged",
        class_id=str(class_id),
        upload_id=str(upload_id),
        user_id=str(uploader),
        rows=len(rows),
    )
    return await asyncio.to_thread(
        _roster_upload_out,
        upload_id=upload_id,
        on_roster=on_roster,
        source=RosterSource.paste,
        file_name="",
        headers=[""],
        has_header=False,
        rows=rows,
        counts=roster_file.address_counts([cells for _, cells in rows], 1),
        chosen=0,
    )


def evaluate_roster_rows(
    rows: list[tuple[int, list[str]]],
    column: int,
    on_roster: Set[str] = frozenset(),
) -> tuple[int, list[RosterInvalidRow]]:
    """Judge each row's cell in `column` with `schemas.address_problem` (Story 4.3, FR-7): how
    many rows get an Invitation, and every other row with its reason, in row order. Addresses are
    compared trimmed and case-insensitively; an address already on the Class's Roster
    (`on_roster`, normalised) is `on_roster` (Story 4.4); otherwise the first occurrence of an
    address is valid and each later one is a `duplicate` naming the first row."""
    valid = 0
    invalid: list[RosterInvalidRow] = []
    first_seen: dict[str, int] = {}
    for number, cells in sorted(rows, key=lambda r: r[0]):
        value = cells[column] if column < len(cells) else ""
        address = normalise_email(value)
        problem = address_problem(address)
        if problem is not None:
            invalid.append(RosterInvalidRow(row_number=number, value=value, reason=problem))
        elif address in on_roster:
            invalid.append(RosterInvalidRow(row_number=number, value=value, reason="on_roster"))
        elif address in first_seen:
            invalid.append(
                RosterInvalidRow(
                    row_number=number,
                    value=value,
                    reason="duplicate",
                    first_row=first_seen[address],
                )
            )
        else:
            first_seen[address] = number
            valid += 1
    return valid, invalid


def _roster_upload_out(
    *,
    upload_id: uuid.UUID,
    on_roster: Set[str],
    source: RosterSource,
    file_name: str,
    headers: list[str],
    has_header: bool,
    rows: list[tuple[int, list[str]]],
    counts: list[int],
    chosen: int | None,
) -> RosterUploadOut:
    suggested = roster_file.suggested_column(counts)
    valid, invalid = (
        evaluate_roster_rows(rows, chosen, on_roster) if chosen is not None else (0, [])
    )
    return RosterUploadOut(
        id=upload_id,
        source=source,
        file_name=file_name,
        row_count=len(rows),
        has_header=has_header,
        columns=[
            RosterColumn(index=i, letter=roster_file.column_letter(i), header=h)
            for i, h in enumerate(headers)
        ],
        suggested_column=suggested,
        suggested_count=counts[suggested] if suggested is not None else 0,
        chosen_column=chosen,
        chosen_count=counts[chosen] if chosen is not None else 0,
        valid_count=valid,
        invalid_rows=invalid,
        preview=[
            RosterPreviewRow(row_number=n, cells=cells) for n, cells in rows[:ROSTER_PREVIEW_ROWS]
        ],
    )


async def _staged_out(s: AsyncSession, row: RowMapping) -> RosterUploadOut:
    """The staged upload, evaluated again from its staged cells."""
    rows = await repo.roster_rows(s, row["id"])
    on_roster = await repo.roster_addresses(s, row["class_id"])
    # Evaluating up to `ROSTER_MAX_ROWS` rows is CPU work: off the event loop.
    counts = await asyncio.to_thread(
        roster_file.address_counts, [cells for _, cells in rows], row["column_count"]
    )
    return await asyncio.to_thread(
        _roster_upload_out,
        upload_id=row["id"],
        on_roster=on_roster,
        source=RosterSource(row["source"]),
        file_name=row["file_name"],
        headers=row["headers"],
        has_header=row["has_header"],
        rows=rows,
        counts=counts,
        chosen=row["chosen_column"],
    )


async def roster_upload(class_id: uuid.UUID, *, now: datetime) -> RosterUploadOut | None:
    """The Class's staged upload, or None when it has none or it has expired."""
    await purge_expired_roster_uploads(now)
    async with get_sessionmaker().begin() as s:
        row = await repo.roster_upload_for_class(s, class_id, now)
        return await _staged_out(s, row) if row else None


async def choose_roster_column(
    class_id: uuid.UUID, column: int, *, now: datetime
) -> RosterUploadOut | None:
    """Store the chosen e-mail column and evaluate the staged rows against it, with no new
    upload. None when the Class has no staged upload; raises `InvalidRosterColumn` for a column
    the upload does not have."""
    await purge_expired_roster_uploads(now)
    async with get_sessionmaker().begin() as s:
        row = await repo.roster_upload_for_class(s, class_id, now, lock=True)
        if row is None:
            return None
        if column >= row["column_count"]:
            raise InvalidRosterColumn
        await repo.set_roster_column(s, row["id"], column)
        out = await _staged_out(s, {**row, "chosen_column": column})
    log.info("roster_column_chosen", class_id=str(class_id), upload_id=str(row["id"]))
    return out


async def delete_roster_upload(class_id: uuid.UUID) -> bool:
    """Delete the Class's staged upload («Bytt fil»). Whether there was one."""
    async with get_sessionmaker().begin() as s:
        deleted = await repo.delete_roster_upload(s, class_id)
    if deleted:
        log.info("roster_upload_deleted", class_id=str(class_id))
    return deleted


# The Roster and Student Invitations (Story 4.4, FR-7, FR-8, AD-9, AD-14). `classes.service` runs
# the send as one command in its own transaction and hands its session here; the addresses never
# leave this module, and log lines carry ids and counts only.

OSLO = ZoneInfo("Europe/Oslo")


@dataclass(frozen=True)
class ClassLabel:
    """How a Student Invitation names its Class: «class-of-1994», course code «IBE160»."""

    name: str
    course_code: str | None


ClassLabelResolver = Callable[[AsyncSession, uuid.UUID], Awaitable[ClassLabel | None]]
"""`(session, class_id)` → the Class's name and course code, or None when it is gone."""

_class_label_resolver: list[ClassLabelResolver] = []


def register_class_label(resolver: ClassLabelResolver) -> None:
    """`classes.service` names its Classes here at import, so a Student Invitation's mail and
    «Du er invitert» can name its Class while `identity` imports no `classes` code (AD-14)."""
    _class_label_resolver[:] = [resolver]


async def _class_label(session: AsyncSession, class_id: uuid.UUID | None) -> ClassLabel | None:
    if class_id is None:
        return None
    if not _class_label_resolver:
        raise RuntimeError("no Class-label resolver is registered (import classes.service)")
    return await _class_label_resolver[0](session, class_id)


async def _class_name(session: AsyncSession, class_id: uuid.UUID | None) -> str | None:
    label = await _class_label(session, class_id)
    return None if label is None else label.name


def student_invitation_expiry(now: datetime, valid_days: int) -> datetime:
    """When a Student Invitation sent at `now` for `valid_days` stops working: the end of the
    `valid_days`-th day after today in Europe/Oslo, so «gyldig til og med» names a whole day."""
    last = now.astimezone(OSLO).date() + timedelta(days=valid_days)
    return datetime.combine(last + timedelta(days=1), time(0), OSLO).astimezone(UTC)


def last_valid_day(expires_at: datetime) -> date:
    """The last Europe/Oslo day on which a link that stops at `expires_at` works."""
    return (expires_at - timedelta(microseconds=1)).astimezone(OSLO).date()


class RosterStagingGone(Exception):
    """The staged upload to send is gone, has expired, or was replaced by another one."""


class NothingToSend(Exception):
    """The staged upload has no row that gets an Invitation."""


@dataclass(frozen=True)
class RosterSent:
    sent: int
    expires_at: datetime


async def send_roster_invitations(
    s: AsyncSession,
    class_id: uuid.UUID,
    actor: uuid.UUID,
    upload_id: uuid.UUID,
    valid_days: int,
    *,
    now: datetime,
) -> RosterSent:
    """Inside the caller's transaction: write the staged upload's valid addresses to the Class's
    Roster, delete the staging, and create and enqueue one Student Invitation per address that
    was not on the Roster before (FR-7, FR-8). Raises `RosterStagingGone` when the Class's
    staging is not `upload_id` (sent already, replaced or expired) and `NothingToSend` when no
    row is valid; nothing changes then. Idempotent: the staging lock serialises sends, an address
    already on the Roster is left as it is, and each Invitation's notice has its own
    `dedupe_key`."""
    await repo.lock_roster_staging(s, class_id)
    row = await repo.roster_upload_for_class(s, class_id, now, lock=True)
    if row is None or row["id"] != upload_id:
        raise RosterStagingGone
    column = row["chosen_column"]
    rows = await repo.roster_rows(s, row["id"])
    on_roster = await repo.roster_addresses(s, class_id)
    addresses = (
        await asyncio.to_thread(_valid_addresses, rows, column, on_roster)
        if column is not None
        else []
    )
    if not addresses:
        raise NothingToSend
    entries = await repo.insert_roster_entries(
        s, class_id, addresses, RosterRegistration.invited.value, now
    )
    # A removed address sent again is back on the Roster (Story 4.8): a registered Student has
    # access again with no Invitation; any other gets one, its old links void.
    back = [e for e in entries if e["registration"] in REGISTERED]
    for entry in back:
        if entry["user_id"] is not None:
            await events.emit(s, "user", str(entry["user_id"]))
    added = [(e["id"], e["email"]) for e in entries if e["registration"] not in REGISTERED]
    if added:  # an entry put back may still hold an open link from before its removal
        await repo.void_open_entry_invitations(s, class_id, [i for i, _ in added], now)
    await repo.delete_roster_upload(s, class_id)
    expires_at = student_invitation_expiry(now, valid_days)
    invitations = [
        {
            "id": uuid.uuid7(),
            "kind": InvitationKind.student.value,
            "email": address,
            "role": None,
            "class_id": class_id,
            "roster_entry_id": entry_id,
            "created_at": now,
            "expires_at": expires_at,
            "invited_by": actor,
        }
        for entry_id, address in added
    ]
    for invitation in invitations:
        invitation["token_hash"] = auth.token_hash(auth.link_token(INVITATION, invitation["id"]))
    await repo.insert_student_invitations(s, invitations)
    await notify.enqueue_by_ref(
        s, INVITATION, [(f"{INVITATION}:{i['id']}", i["id"]) for i in invitations]
    )
    log.info(
        "roster_invitations_sent",
        class_id=str(class_id),
        upload_id=str(upload_id),
        user_id=str(actor),
        sent=len(invitations),
        valid_days=valid_days,
    )
    return RosterSent(sent=len(invitations), expires_at=expires_at)


def _valid_addresses(
    rows: list[tuple[int, list[str]]], column: int, on_roster: Set[str]
) -> list[str]:
    """The normalised addresses `evaluate_roster_rows` finds valid, in row order."""
    _, invalid = evaluate_roster_rows(rows, column, on_roster)
    skip = {row.row_number for row in invalid}
    return [
        normalise_email(cells[column] if column < len(cells) else "")
        for number, cells in sorted(rows, key=lambda r: r[0])
        if number not in skip
    ]


async def seed_registered_student(
    s: AsyncSession, class_id: uuid.UUID, email: str, name: str, password: str, now: datetime
) -> bool:
    """For the local seed only (AD-17): the User of `email` (made, without an account role, when
    missing; an existing User is never changed) as a registered Student of the Class, unless the
    address is on its Roster already. True when an entry was added."""
    address = normalise_email(email)
    user = await repo.user_by_email(s, address)
    user_id = (
        user["id"]
        if user is not None
        else await create_user(email=address, name=name, password=password, session=s)
    )
    return await repo.ensure_registered_entry(
        s, class_id, address, user_id, RosterRegistration.registered.value, now
    )


async def roster_counts(class_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    """How many addresses are on each Class's Roster (UX-DR56); a Class with none is left out."""
    async with get_sessionmaker().begin() as s:
        return await repo.roster_counts(s, class_ids)


@dataclass(frozen=True)
class ClassInvitation:
    """A Student Invitation of a Class as `classes` counts it (Story 4.6, FR-8): whether it was
    accepted, or has expired unaccepted at the time asked, and its Roster entry's address and
    standing. The address leaves `identity` only for the Lecturer's own page."""

    id: uuid.UUID
    roster_entry_id: uuid.UUID
    email: str
    accepted: bool
    expired: bool
    entry_registered: bool
    entry_removed: bool


async def class_student_invitations(class_id: uuid.UUID, *, now: datetime) -> list[ClassInvitation]:
    """Every Student Invitation of the Class, oldest first. Expired is read from `expires_at` at
    `now` (the api's clock): neither accepted nor voided, and past its last valid day."""
    async with get_sessionmaker().begin() as s:
        rows = await repo.class_student_invitations(s, class_id)
    return [
        ClassInvitation(
            id=row["id"],
            roster_entry_id=row["roster_entry_id"],
            email=row["email"],
            accepted=row["accepted_at"] is not None,
            expired=row["accepted_at"] is None
            and row["voided_at"] is None
            and row["expires_at"] <= now,
            entry_registered=row["registration"] in REGISTERED,
            entry_removed=row["removed_at"] is not None,
        )
        for row in rows
    ]


# Registration status and reminders (Story 4.7, FR-9).

REGISTERED = frozenset({RosterRegistration.registered, RosterRegistration.registered_manually})
"""The stored registrations that make an address a Student in the Class."""


@dataclass(frozen=True)
class RosterFacts:
    """A Roster entry that has not been removed, as `classes` reads its status (Story 4.7): its
    stored registration, its newest Student Invitation (None when it has none) and whether the
    Student asked for a new one. The address leaves `identity` only for the Lecturer's own page."""

    entry_id: uuid.UUID
    email: str
    registration: RosterRegistration
    invitation_id: uuid.UUID | None
    expires_at: datetime | None
    open: bool
    """The newest Invitation is neither accepted nor voided, and still valid at the time asked."""
    renewal_requested: bool


async def class_roster(class_id: uuid.UUID, *, now: datetime) -> list[RosterFacts]:
    """Every Roster entry of the Class that has not been removed, by address."""
    async with get_sessionmaker().begin() as s:
        rows = await repo.class_roster_facts(s, class_id)
    return [
        RosterFacts(
            entry_id=row["id"],
            email=row["email"],
            registration=RosterRegistration(row["registration"]),
            invitation_id=row["invitation_id"],
            expires_at=row["expires_at"],
            open=row["invitation_id"] is not None and _invitation_open(row, now),
            renewal_requested=row["renewal_requested"],
        )
        for row in rows
    ]


async def registered_users(class_id: uuid.UUID) -> list[uuid.UUID]:
    """The Users who are Students in the Class: registered through an Invitation or by hand,
    and not removed (FR-9). An address unregistered after its Invitation expired is not one."""
    async with get_sessionmaker().begin() as s:
        return await repo.registered_user_ids(s, class_id, [r.value for r in REGISTERED])


async def send_entry_reminders(
    s: AsyncSession,
    class_id: uuid.UUID,
    actor: uuid.UUID,
    entry_ids: list[uuid.UUID],
    valid_days: int,
    *,
    now: datetime,
) -> RosterSent:
    """Inside the caller's transaction: send each of these Roster entries that is still invited
    and on the Roster a new Student Invitation valid for `valid_days` (FR-9). Its open Invitations
    are voided first, so their links stop working, and its requests for a new one are answered.
    Entries are read again after the void: one whose Student accepted meanwhile, or that is
    registered, removed or of another Class, gets nothing. Serialised per Class with the Roster
    send by the staging lock. Each mail is an `immediate` `invitation` notice with its own
    `dedupe_key`."""
    await repo.lock_roster_staging(s, class_id)
    expires_at = student_invitation_expiry(now, valid_days)
    if not entry_ids:
        return RosterSent(sent=0, expires_at=expires_at)
    await repo.void_open_entry_invitations(s, class_id, entry_ids, now)
    targets = await repo.remindable_entries(
        s, class_id, entry_ids, RosterRegistration.invited.value
    )
    if not targets:
        return RosterSent(sent=0, expires_at=expires_at)
    await repo.clear_entry_renewals(s, class_id, [entry_id for entry_id, _ in targets])
    invitations = [
        {
            "id": uuid.uuid7(),
            "kind": InvitationKind.student.value,
            "email": address,
            "role": None,
            "class_id": class_id,
            "roster_entry_id": entry_id,
            "created_at": now,
            "expires_at": expires_at,
            "invited_by": actor,
        }
        for entry_id, address in targets
    ]
    for invitation in invitations:
        invitation["token_hash"] = auth.token_hash(auth.link_token(INVITATION, invitation["id"]))
    await repo.insert_student_invitations(s, invitations)
    await notify.enqueue_by_ref(
        s, INVITATION, [(f"{INVITATION}:{i['id']}", i["id"]) for i in invitations]
    )
    log.info(
        "roster_reminders_sent",
        class_id=str(class_id),
        user_id=str(actor),
        sent=len(invitations),
        valid_days=valid_days,
    )
    return RosterSent(sent=len(invitations), expires_at=expires_at)


# Single addresses and manual registration (Story 4.8, FR-7, FR-9, AD-8, AD-9, AD-14). Each runs in
# the caller's transaction under the Class's Roster staging lock, so it never interleaves with a
# Roster send or a reminder. Locks are taken in the order an acceptance takes them (Invitation,
# then address, then Roster entry): the open Invitations are voided before the entry is locked.

MANUAL_REGISTRATION = "manual_registration"
"""The notice kind of the mail a manually registered Student gets (Story 4.8)."""


class RosterRefused(Exception):
    """The address is refused, with the reason the form shows beside it: an `address_problem`,
    `on_roster` (add) or `already_registered` (manual registration)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _checked_address(address: str) -> str:
    address = normalise_email(address)
    problem = address_problem(address)
    if problem is not None:
        raise RosterRefused(problem.value)
    return address


async def _remove_entry(s: AsyncSession, entry: RowMapping, now: datetime) -> None:
    """Inside a transaction that voided the entry's open Invitations and holds its lock. Its
    requests for a new Invitation go too, so an address put back later starts afresh."""
    await repo.remove_roster_entry(s, entry["id"], now)
    await repo.clear_entry_renewals(s, entry["class_id"], [entry["id"]])
    if entry["user_id"] is not None:
        await events.emit(s, "user", str(entry["user_id"]))


async def add_roster_entry(
    s: AsyncSession, class_id: uuid.UUID, address: str, *, now: datetime
) -> uuid.UUID:
    """Add one address to the Class's Roster, checked by the one validation of an upload (FR-7):
    a new entry is not yet invited (no Invitation; a reminder sends its first). A removed one is
    put back as it was, and a registered Student has access again. Raises `RosterRefused` with an
    `address_problem` or `on_roster`. The entry's id."""
    address = _checked_address(address)
    await repo.lock_roster_staging(s, class_id)
    entry = await repo.roster_entry_by_email(s, class_id, address, lock=True)
    if entry is None:
        entry_id = await repo.insert_roster_entry(
            s, class_id, address, RosterRegistration.invited.value, now
        )
        log.info("roster_entry_added", class_id=str(class_id), roster_entry_id=str(entry_id))
        return entry_id
    if entry["removed_at"] is None:
        raise RosterRefused("on_roster")
    await repo.restore_roster_entry(s, entry["id"])
    if entry["user_id"] is not None:
        await events.emit(s, "user", str(entry["user_id"]))
    log.info("roster_entry_restored", class_id=str(class_id), roster_entry_id=str(entry["id"]))
    return entry["id"]


async def remove_roster_entry(
    s: AsyncSession, class_id: uuid.UUID, entry_id: uuid.UUID, *, now: datetime
) -> bool:
    """Take an address off the Class's Roster (FR-7): the entry is marked removed, its open
    Invitations stop working, and a registered Student loses access from their next request
    (`user:<id>`); the User and their other Classes are untouched. False when the entry is not
    the Class's or is removed already."""
    await repo.lock_roster_staging(s, class_id)
    await repo.void_open_entry_invitations(s, class_id, [entry_id], now)
    entry = await repo.class_roster_entry(s, class_id, entry_id, lock=True)
    if entry is None or entry["removed_at"] is not None:
        return False
    await _remove_entry(s, entry, now)
    log.info("roster_entry_removed", class_id=str(class_id), roster_entry_id=str(entry_id))
    return True


async def register_manually(
    s: AsyncSession,
    class_id: uuid.UUID,
    address: str,
    name: str,
    *,
    replaces: uuid.UUID | None = None,
    upload_row: tuple[uuid.UUID, int] | None = None,
    now: datetime,
) -> uuid.UUID:
    """Register a Student by hand (FR-9): the User of the address (an existing one is reused and
    never changed; a new one gets `name`, no password and no account role), and its Roster entry
    (new, waiting, or removed and put back) linked to it and set `registered_manually`, so the
    Student is in the Class at once. The entry's open Invitations are voided and its requests for a
    new one answered. `replaces` names the entry the form was opened from: when that is another
    address, not registered, it is removed (a wrong address corrected). `upload_row` names the
    staged row the form was opened from, which is deleted. The Student is mailed
    (`manual_registration`, `immediate`): a User without a password with a single-use link to
    «Nytt passord», valid to the end of the `MANUAL_REGISTRATION_LINK_DAYS`-th day. Raises
    `RosterRefused` with an `address_problem` or `already_registered`. The entry's id."""
    address = _checked_address(address)
    await repo.lock_roster_staging(s, class_id)
    found = await repo.roster_entry_by_email(s, class_id, address)
    if found is not None:
        await repo.void_open_entry_invitations(s, class_id, [found["id"]], now)
    old = None
    if replaces is not None and (found is None or replaces != found["id"]):
        await repo.void_open_entry_invitations(s, class_id, [replaces], now)
        old = await repo.class_roster_entry(s, class_id, replaces, lock=True)
    await repo.lock_user_address(s, address)
    entry = await repo.roster_entry_by_email(s, class_id, address, lock=True)
    if (
        entry is not None
        and entry["removed_at"] is None
        and RosterRegistration(entry["registration"]) in REGISTERED
    ):
        raise RosterRefused("already_registered")
    user = await repo.user_by_email(s, address)
    if user is None:
        user_id = uuid.uuid7()
        await repo.insert_user(
            s,
            user_id=user_id,
            email=address,
            name=name,
            password_hash=None,
            is_active=True,
            roles=[],
        )
    else:
        user_id = user["id"]
    manual = RosterRegistration.registered_manually.value
    if entry is None:
        entry_id = await repo.insert_roster_entry(s, class_id, address, manual, now, user_id)
    else:
        entry_id = entry["id"]
        await repo.register_entry_manually(s, entry_id, user_id, manual)
        await repo.clear_entry_renewals(s, class_id, [entry_id])
    if (
        old is not None
        and old["removed_at"] is None
        and RosterRegistration(old["registration"]) not in REGISTERED
    ):
        await _remove_entry(s, old, now)
    if upload_row is not None:
        await repo.delete_staged_row(s, class_id, *upload_row)
    if user is None or (user["password_hash"] is None and user["is_active"]):
        reset_id = uuid.uuid7()
        await repo.insert_password_reset(
            s,
            reset_id=reset_id,
            user_id=user_id,
            token_hash=auth.token_hash(auth.link_token(PASSWORD_RESET, reset_id)),
            created_at=now,
            expires_at=student_invitation_expiry(now, get_settings().manual_registration_link_days),
        )
    await notify.enqueue(
        s, user_id, MANUAL_REGISTRATION, f"{MANUAL_REGISTRATION}:{uuid.uuid7()}", ref=entry_id
    )
    await events.emit(s, "user", str(user_id))
    log.info(
        "roster_registered_manually",
        class_id=str(class_id),
        roster_entry_id=str(entry_id),
        user_id=str(user_id),
        replaced=old is not None,
    )
    return entry_id


async def manual_registration_mail_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    """The template variables of a manual registration's mail, for `messaging` at send time: the
    Class's name and, for a User with no password yet, the set-password link (path with token) and
    its last valid day. None when no mail is needed any more: the entry was removed or is no
    longer this User's manual registration, or the link was used or has expired. Never stored or
    logged."""
    if ref is None:
        return None
    entry = await repo.roster_entry_by_id(session, ref)
    if (
        entry is None
        or entry["removed_at"] is not None
        or entry["user_id"] != user_id
        or entry["registration"] != RosterRegistration.registered_manually
    ):
        return None
    label = await _class_label(session, entry["class_id"])
    user = await repo.user_by_id(session, user_id)
    if label is None or user is None:
        return None
    context: dict[str, object] = {"class_name": label.name, "link": None, "last_valid_day": None}
    if user["password_hash"] is None:
        reset = await repo.newest_open_password_reset(session, user_id, now)
        if reset is None:
            return None
        context["link"] = f"{RESET_LINK_PATH}#{auth.link_token(PASSWORD_RESET, reset['id'])}"
        context["last_valid_day"] = last_valid_day(reset["expires_at"])
    return context
