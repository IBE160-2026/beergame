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
from sqlalchemy import RowMapping
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
            if await _grant_bootstrap_admin(s, row["id"], email, now):
                roles = sorted([*roles, AccountRole.admin.value])

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
) -> UserOut | AcceptRefused:
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
    return UserOut(id=user_id, name=name, email=row["email"], roles=[AccountRole(row["role"])])


async def accept_invitation_existing(
    token: str, password: str, *, ip: str, now: datetime
) -> UserOut | AcceptRefused:
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
    return _user_out(user, roles)


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
