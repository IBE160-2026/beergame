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
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta

import structlog
from sqlalchemy import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity import repo
from app.modules.identity.schemas import (
    AccessRequestListOut,
    AccessRequestOut,
    AccountRole,
    InstitutionListOut,
    InstitutionOut,
    InvitationListItem,
    InvitationListOut,
    InvitationOut,
    InvitationStatus,
    UserListItem,
    UserListOut,
    UserOut,
    email_is_valid,
    institution_name,
    normalise_email,
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
    # checks a dummy hash, so it takes as long as a wrong password.
    stored = row["password_hash"] if row else await asyncio.to_thread(auth.dummy_hash)
    matches = await asyncio.to_thread(auth.verify_password, password, stored)
    ok = row is not None and matches

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
    write the audit row. Raises `InvalidEmail` for a malformed address, before anything is
    stored. The caller's policy has already checked that `actor` may manage Users.

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
    return email.Recipient(
        email=row["email"],
        name=None,
        context={
            "link": f"{INVITATION_LINK_PATH}#{auth.link_token(INVITATION, ref)}",
            "role": row["role"],
            "valid_days": _days_left(row["expires_at"], now),
        },
    )


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
    email: str
    role: AccountRole
    valid_days: int
    has_account: bool


@dataclass(frozen=True)
class AcceptRefused:
    # invitation_link_invalid | account_exists | invalid_credentials | rate_limited
    code: str
    retry_after: int | None = None


async def _usable_invitation(
    session: AsyncSession, row, now: datetime
) -> tuple[RowMapping, RowMapping | None] | None:
    """The open Invitation and the User its address has (or None), or None when the link is not
    usable: not open, or its address belongs to a deactivated User."""
    if not _invitation_open(row, now):
        return None
    user = await repo.user_by_email(session, row["email"])
    if user is not None and not user["is_active"]:
        return None
    return row, user


async def check_invitation(token: str, *, now: datetime) -> InvitationChecked | None:
    """What «Du er invitert» shows for a usable link, or None."""
    async with get_sessionmaker().begin() as s:
        row = await repo.invitation_by_hash(s, auth.token_hash(token))
        usable = await _usable_invitation(s, row, now)
    if usable is None:
        return None
    row, user = usable
    return InvitationChecked(
        id=row["id"],
        email=row["email"],
        role=AccountRole(row["role"]),
        valid_days=_days_left(row["expires_at"], now),
        has_account=user is not None,
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
        await repo.lock_user_address(s, row["email"])
        if await repo.user_by_email(s, row["email"]) is not None:
            log.info("invitation_accept_refused", error_code="account_exists")
            return AcceptRefused("account_exists")
        await repo.insert_user(
            s,
            user_id=user_id,
            email=row["email"],
            name=name,
            password_hash=password_hash,
            is_active=True,
            roles=[row["role"]],
        )
        await repo.mark_invitation_accepted(s, row["id"], now)
        await audit.record(
            s,
            user_id,
            INVITATION_ACCEPTED,
            {"invitation_id": row["id"], "user_id": user_id},
            {"role": row["role"], "account": "created"},
            now,
        )
    log.info("invitation_accepted", invitation_id=str(row["id"]), user_id=str(user_id))
    user = UserOut(id=user_id, name=name, email=row["email"], roles=[AccountRole(row["role"])])
    return LoginOk(user, 0)


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
        if row is None or user is None or not user["is_active"] or user["email"] != row["email"]:
            log.info("invitation_accept_refused", error_code="invitation_link_invalid")
            return AcceptRefused("invitation_link_invalid")
        granted = await repo.grant_role(s, user["id"], row["role"])
        await repo.mark_invitation_accepted(s, row["id"], now)
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
        # after a reactivation.
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
        if found is None:
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
        else:
            user = await repo.user_by_email(s, address)
            if user is not None and not user["is_active"]:
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
