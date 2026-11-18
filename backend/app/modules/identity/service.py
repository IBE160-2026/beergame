"""Accounts and login (FR-4, AD-11, Story 3.2). Other modules import only this file.

`authenticate` checks the rate limits, the password and the account state and returns one
outcome; it never says whether an account exists, except that a deactivated account is named
once its right password is given (FR-3). `load_user` is the loader `platform/authz` calls on every
request (registered in `create_app()`), so a role change or a deactivation takes effect at once.
"""

import asyncio
import math
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity import repo
from app.modules.identity.schemas import (
    AccountRole,
    InvitationOut,
    UserOut,
    email_is_valid,
    normalise_email,
)
from app.platform import audit, auth, email, notify, ratelimit
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
    user: UserOut


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

    if not ok:
        log.info("login_refused", error_code="invalid_credentials")
        return LoginRefused("invalid_credentials")
    if not row["is_active"]:
        log.info("login_refused", error_code="account_deactivated", user_id=str(row["id"]))
        return LoginRefused("account_deactivated")
    log.info("login", user_id=str(row["id"]))
    return LoginOk(_user_out(row, roles))


async def load_user(user_id: uuid.UUID) -> UserOut | None:
    """The active User with their roles, or None when the User is gone or deactivated."""
    async with get_sessionmaker().begin() as s:
        row = await repo.user_by_id(s, user_id)
        if row is None or not row["is_active"]:
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
    links are voided and the failed-login count of the account is cleared. Returns the e-mail, or
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
    actor: uuid.UUID, address: str, role: AccountRole, *, now: datetime
) -> InvitationOut:
    """Invite `address` to `role`. In one transaction: void the open Invitation to the same address
    and role, store the new one (its token only as a hash), enqueue its `invitation` notice and
    write the audit row. Raises `InvalidEmail` for a malformed address, before anything is
    stored. The caller's policy has already checked that `actor` may manage Users."""
    address = normalise_email(address)
    if not email_is_valid(address):
        raise InvalidEmail
    role = AccountRole(role)
    invitation_id = uuid.uuid7()
    expires_at = now + timedelta(days=get_settings().role_invitation_valid_days)
    async with get_sessionmaker().begin() as s:
        await repo.lock_invitation_address(s, address, role.value)
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
        await notify.enqueue(
            s, None, INVITATION, f"{INVITATION}:{invitation_id}", ref=invitation_id
        )
        change: dict[str, object] = {"role": role.value}
        if voided:
            change["voided_invitation_ids"] = voided
        await audit.record(s, actor, INVITATION_SENT, {"invitation_id": invitation_id}, change, now)
    log.info(
        "invitation_sent",
        invitation_id=str(invitation_id),
        actor_user_id=str(actor),
        role=role.value,
        voided_count=len(voided),
    )
    return InvitationOut(
        id=invitation_id,
        email=address,
        role=role,
        expires_at=expires_at,
        valid_days=_days_left(expires_at, now),
    )


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
