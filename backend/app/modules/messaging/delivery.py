"""The one table of delivery per notice kind (AD-9).

`immediate` kinds leave at once, at any hour: Invitations, password resets, Messages a person
sends, Takeover notices. Every other kind is `digest`: at most one mail per User per calendar day
in Europe/Oslo, never between 22:00 and 07:00 there (founder decision 2026-11-12).

A kind addressed to a User resolves the address through `identity.service.mail_recipient`. A kind
addressed by reference (the notice's `user_id` is None, its `ref` the record holding the address)
names the owning module's `service.py` resolver here; it gets the job's clock and returns the
address with the kind's template variables, or None when no mail is needed any more (the
Invitation was accepted, voided or has expired), and the mail is then skipped as
`no_recipient`. A digest kind is always addressed to a User.
A kind whose mail carries its own variables (a link with a token) names the owning module's context
resolver; it returns None when the notice no longer needs a mail (the link is used or expired), and
the mail is then skipped as `stale`.

Stories add their kinds to `KINDS` (3.6 `password_reset`, 3.7 `invitation`, …). The two dummy
kinds exist only outside production, for the `send-test` command and the tests.
"""

import uuid
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from types import MappingProxyType
from typing import Literal
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

# Imported for its registration: a Student Invitation's mail names its Class through the resolver
# `classes.service` registers with `identity` at import (Story 4.4), also in the worker.
from app.modules.classes import service as classes  # noqa: F401
from app.modules.identity import service as identity

# `sessions.service` imports `classes.service`, which imports `messaging.service` and so this
# module: its attributes are read when a mail is composed, never at import (Story 5.6).
from app.modules.sessions import service as sessions
from app.platform.config import Settings, get_settings
from app.platform.email import Recipient

IMMEDIATE = "immediate"
DIGEST = "digest"
Mode = Literal["immediate", "digest"]

OSLO = ZoneInfo("Europe/Oslo")
QUIET_FROM = time(22, 0)
"""No digest mail is claimed from 22:00 …"""
QUIET_UNTIL = time(7, 0)
"""… until 07:00, Europe/Oslo."""

RefResolver = Callable[[AsyncSession, uuid.UUID, datetime], Awaitable[Recipient | None]]
"""`(session, ref, now)` → the recipient with the kind's template variables, or None for no mail."""
ContextResolver = Callable[
    [AsyncSession, uuid.UUID, uuid.UUID | None, datetime],
    Awaitable[Mapping[str, object] | None],
]
"""`(session, user_id, ref, now)` → the kind's template variables, or None for no mail."""


@dataclass(frozen=True)
class Delivery:
    mode: Mode
    template: str
    """The name of the kind's templates in `platform/email/templates/kinds/`."""
    resolve_ref: RefResolver | None = None
    """For a kind addressed by reference: the owning module's resolver of the notice's `ref`."""
    context: ContextResolver | None = None
    """For a User-addressed kind with its own variables: the owning module's resolver."""

    def __post_init__(self) -> None:
        if self.mode not in (IMMEDIATE, DIGEST):
            raise ValueError(f"unknown delivery mode {self.mode!r}")
        if self.mode == DIGEST and self.resolve_ref is not None:
            raise ValueError("a digest kind is addressed to a User, not by reference")
        if self.resolve_ref is not None and self.context is not None:
            raise ValueError("a kind by reference gets its variables from its ref resolver")


LAB_HOUR_KINDS = ("lab_hour_added", "lab_hour_changed", "lab_hour_cancelled")
"""`sessions.service.LAB_HOUR_KINDS`, named here because that module may still be loading when
this one is (a test keeps the two equal)."""


def _lab_hour_context(kind: str) -> ContextResolver:
    async def resolve(
        session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
    ) -> Mapping[str, object] | None:
        return await sessions.lab_hour_mail_context(kind, session, user_id, ref, now)

    return resolve


OBLIGATORY_KIND = "class_session_obligatory"
"""`sessions.service.OBLIGATORY_NOTICE` (Story 5.7), named here for the same reason."""


async def _obligatory_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    return await sessions.obligatory_mail_context(session, user_id, ref, now)


ALLOCATION_KIND = "allocation_confirmed"
"""`sessions.service.ALLOCATION_NOTICE` (Story 5.9), named here for the same reason."""


async def _allocation_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    return await sessions.allocation_mail_context(session, user_id, ref, now)


LOCK_REFUSED_KIND = "class_session_lock_refused"
"""`sessions.service.LOCK_REFUSED_NOTICE` (Story 5.11), named here for the same reason."""


async def _lock_refused_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    return await sessions.lock_refused_mail_context(session, user_id, ref, now)


KINDS: Mapping[str, Delivery] = MappingProxyType(
    {
        **{
            kind: Delivery(DIGEST, kind, context=_lab_hour_context(kind)) for kind in LAB_HOUR_KINDS
        },
        OBLIGATORY_KIND: Delivery(DIGEST, OBLIGATORY_KIND, context=_obligatory_context),
        ALLOCATION_KIND: Delivery(DIGEST, ALLOCATION_KIND, context=_allocation_context),
        # Immediate: the Start date has passed and the Class games wait for the lock.
        LOCK_REFUSED_KIND: Delivery(IMMEDIATE, LOCK_REFUSED_KIND, context=_lock_refused_context),
        identity.PASSWORD_RESET: Delivery(
            IMMEDIATE, "password_reset", context=identity.password_reset_mail_context
        ),
        identity.INVITATION: Delivery(
            IMMEDIATE, "invitation", resolve_ref=identity.invitation_mail_recipient
        ),
        identity.MANUAL_REGISTRATION: Delivery(
            IMMEDIATE,
            "manual_registration",
            context=identity.manual_registration_mail_context,
        ),
    }
)
"""The product's kinds: `password_reset` (Story 3.6), `invitation` (Story 3.7),
`manual_registration` (Story 4.8), the Lab hour notices (Story 5.6, digest), the obligatory
notice (Story 5.7, digest), the allocation notice (Story 5.9, digest) and the refused lock
(Story 5.11, immediate)."""

TEST_KINDS: Mapping[str, Delivery] = MappingProxyType(
    {
        "test_immediate": Delivery(IMMEDIATE, "test_immediate"),
        "test_digest": Delivery(DIGEST, "test_digest"),
    }
)
"""The dummy kinds of Story 3.5, outside production only."""


def table(settings: Settings | None = None) -> Mapping[str, Delivery]:
    """Every kind this process delivers."""
    settings = settings or get_settings()
    kinds = dict(KINDS)
    if settings.app_env != "production":
        kinds |= TEST_KINDS
    return MappingProxyType(kinds)


def kinds_of(mode: Mode, settings: Settings | None = None) -> tuple[str, ...]:
    return tuple(kind for kind, entry in table(settings).items() if entry.mode == mode)


def digest_allowed(now: datetime) -> bool:
    """Whether a digest may be claimed at `now`: 07:00 to 22:00 Europe/Oslo."""
    local = now.astimezone(OSLO).time()
    return QUIET_UNTIL <= local < QUIET_FROM


def oslo_day(now: datetime) -> tuple[datetime, datetime]:
    """The start and end of the Europe/Oslo calendar day that holds `now`."""
    day = now.astimezone(OSLO).date()
    start = datetime.combine(day, time(0), OSLO)
    end = datetime.combine(day + timedelta(days=1), time(0), OSLO)
    return start, end
