"""Accounts and login (FR-4, AD-11, Story 3.2). Other modules import only this file.

`authenticate` checks the rate limits, the password and the account state and returns one
outcome; it never says whether an account exists, except that a deactivated account is named
once its right password is given (FR-3). `load_user` is the loader `platform/authz` calls on every
request (registered in `create_app()`), so a role change or a deactivation takes effect at once.
"""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity import repo
from app.modules.identity.schemas import AccountRole, UserOut, normalise_email
from app.platform import auth, email, ratelimit
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

log = structlog.get_logger(__name__)

LOGIN_IP = "login_ip"
LOGIN_ACCOUNT = "login_account"


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
