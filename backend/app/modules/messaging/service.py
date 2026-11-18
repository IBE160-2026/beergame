"""Claim notices into mails and send them (AD-9, AD-14, Story 3.5).

- `claim_notice(notice_id, now)`: the claim job `platform/notify.enqueue` defers. A due notice of
  an `immediate` kind becomes one delivery at once, at any hour. A digest notice, one whose
  `not_before` lies ahead, an unknown kind and a claimed notice are left alone.
- `due_items(now)` and `claim(item, now)`: the sweep's due action, one item per transaction. An
  item is an overdue immediate notice, a User with due digest notices, or a delivery whose `mail`
  job was lost or failed.
- `send(delivery_id)`: the `mail` job. It locks the delivery, resolves the address through the
  owning module, renders, sends and stores the provider's id. A delivery that is sent, given up
  or held by another job is left alone, so a job that runs twice sends one mail.

Claiming writes the `mail_deliveries` row and defers the `mail` job in one transaction. Job
arguments, log lines and rows hold ids only; the address exists only inside `send`.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity import service as identity
from app.modules.messaging import delivery, repo
from app.platform import email, jobs, notify
from app.platform.db import get_sessionmaker

__all__ = [
    "MAX_ATTEMPTS",
    "SEND_MAIL",
    "DueItem",
    "claim",
    "claim_notice",
    "due_items",
    "send",
]

log = structlog.get_logger(__name__)

SEND_MAIL = "messaging.send_mail"
"""The `mail` job, keyed by its delivery."""

MAX_ATTEMPTS = 6
"""Sends tried for one delivery before it is given up (`send_failed`)."""
RETRY_AFTER = timedelta(minutes=2)
"""A delivery unsent this long after its claim is deferred again. The wait is counted from the
claim and doubled per failed try, so the tries fall about 2 (a lost job), 4, 8, 16, 32 and 64
minutes after the claim: the last one about an hour later."""


def utcnow() -> datetime:
    """This process's clock; tests replace it to run jobs at a controlled time."""
    return datetime.now(UTC)


@dataclass(frozen=True)
class DueItem:
    """One piece of due work for the sweep: exactly one of the three ids is set."""

    notice_id: uuid.UUID | None = None
    digest_user_id: uuid.UUID | None = None
    delivery_id: uuid.UUID | None = None


async def _defer_send(session: AsyncSession, delivery_id: uuid.UUID) -> bool:
    return await jobs.defer(
        session,
        SEND_MAIL,
        queue=jobs.MAIL,
        queueing_lock=f"delivery:{delivery_id}",
        delivery_id=str(delivery_id),
    )


async def _create_delivery(
    session: AsyncSession,
    *,
    mode: delivery.Mode,
    claimed: list[notify.Notice],
    now: datetime,
) -> uuid.UUID:
    delivery_id = uuid.uuid7()
    await repo.insert_delivery(
        session,
        delivery_id=delivery_id,
        user_id=claimed[0].user_id,
        mode=mode,
        notice_ids=[n.id for n in claimed],
        claimed_at=now,
    )
    await _defer_send(session, delivery_id)
    log.info(
        "mail_claimed",
        delivery_id=str(delivery_id),
        kind=claimed[0].kind if mode == delivery.IMMEDIATE else delivery.DIGEST,
        notice_count=len(claimed),
    )
    return delivery_id


async def _claim_immediate(
    session: AsyncSession, notice_id: uuid.UUID, now: datetime
) -> uuid.UUID | None:
    claimed = await notify.claim_due(
        session, now, kinds=delivery.kinds_of(delivery.IMMEDIATE), notice_id=notice_id
    )
    if not claimed:
        return None
    return await _create_delivery(session, mode=delivery.IMMEDIATE, claimed=claimed, now=now)


async def _claim_digest(
    session: AsyncSession, user_id: uuid.UUID, now: datetime
) -> uuid.UUID | None:
    if not delivery.digest_allowed(now):
        return None
    await repo.lock_user_digest(session, user_id)
    start, end = delivery.oslo_day(now)
    if await repo.digest_claimed_between(session, user_id, start, end):
        return None
    claimed = await notify.claim_due(
        session, now, kinds=delivery.kinds_of(delivery.DIGEST), user_id=user_id
    )
    if not claimed:
        return None
    return await _create_delivery(session, mode=delivery.DIGEST, claimed=claimed, now=now)


async def claim_notice(notice_id: uuid.UUID, now: datetime) -> uuid.UUID | None:
    """The claim job: the delivery made for `notice_id`, or None when it is not due now, not of
    an immediate kind, or already claimed."""
    async with get_sessionmaker().begin() as session:
        return await _claim_immediate(session, notice_id, now)


def _retry_due(attempts: int, claimed_at: datetime, now: datetime) -> bool:
    return attempts < MAX_ATTEMPTS and claimed_at + RETRY_AFTER * (2**attempts) <= now


async def due_items(now: datetime) -> list[DueItem]:
    """What the sweep should claim or send again at `now`. Reads only; each item is claimed in
    its own transaction by `claim`."""
    table = delivery.table()
    async with get_sessionmaker().begin() as session:
        due = await notify.due(session, now, kinds=table.keys())
        unsent = await repo.unsent_claimed_before(session, now - RETRY_AFTER)
    items: list[DueItem] = []
    users: set[uuid.UUID] = set()
    digest_open = delivery.digest_allowed(now)
    for notice in due:
        if table[notice.kind].mode == delivery.IMMEDIATE:
            items.append(DueItem(notice_id=notice.id))
        elif digest_open and notice.user_id is not None and notice.user_id not in users:
            users.add(notice.user_id)
            items.append(DueItem(digest_user_id=notice.user_id))
    items += [
        DueItem(delivery_id=row["id"])
        for row in unsent
        if _retry_due(row["attempts"], row["claimed_at"], now)
        and (digest_open or row["mode"] != delivery.DIGEST)
    ]
    return items


async def claim(item: DueItem, now: datetime) -> uuid.UUID | None:
    """Act on one `DueItem` in one transaction; returns the delivery it made or deferred again."""
    async with get_sessionmaker().begin() as session:
        if item.notice_id is not None:
            return await _claim_immediate(session, item.notice_id, now)
        if item.digest_user_id is not None:
            return await _claim_digest(session, item.digest_user_id, now)
        if item.delivery_id is not None:
            if await _defer_send(session, item.delivery_id):
                log.info("mail_send_deferred_again", delivery_id=str(item.delivery_id))
            return item.delivery_id
    raise ValueError("an empty DueItem")


async def _recipient(
    session: AsyncSession, row, first: notify.Notice, entry: delivery.Delivery
) -> email.Recipient | None:
    if entry.resolve_ref is not None:
        return None if first.ref is None else await entry.resolve_ref(session, first.ref)
    if row["user_id"] is None:
        return None
    return await identity.mail_recipient(session, row["user_id"])


async def _failed(session: AsyncSession, row, exc: Exception, notice_count: int) -> str:
    """Count one failed try in the job's transaction (given up after `MAX_ATTEMPTS`). Only the
    exception's type and a `SendRefused` code are logged: its text may hold an address."""
    give_up = row["attempts"] + 1 >= MAX_ATTEMPTS
    await repo.mark_failed(session, row["id"], give_up=give_up)
    log.error(
        "mail_send_failed",
        delivery_id=str(row["id"]),
        exc_type=type(exc).__name__,
        error_code=str(exc) if isinstance(exc, email.SendRefused) else None,
        notice_count=notice_count,
    )
    return "failed"


async def send(delivery_id: uuid.UUID, now: datetime | None = None) -> str:
    """The `mail` job. Returns what happened: `sent`, `skipped`, `failed`, `held` (a digest in
    the quiet hours), or `none` when the delivery is gone, held by another job, or already sent
    or given up."""
    table = delivery.table()
    async with get_sessionmaker().begin() as session:
        row = await repo.lock_delivery(session, delivery_id)
        if row is None or row["sent_at"] is not None or row["skipped_reason"] is not None:
            log.info("mail_not_needed", delivery_id=str(delivery_id))
            return "none"
        now = now or utcnow()
        if row["mode"] == delivery.DIGEST and not delivery.digest_allowed(now):
            # A digest that was late or failed is never sent at night; the sweep defers it
            # again from 07:00 (Europe/Oslo).
            log.info("mail_held_for_quiet_hours", delivery_id=str(delivery_id))
            return "held"
        carried = [n for n in await notify.get(session, row["notice_ids"]) if n.kind in table]
        if not carried:
            await repo.mark_skipped(session, delivery_id, "unknown_kind")
            log.warning("mail_skipped", delivery_id=str(delivery_id), error_code="unknown_kind")
            return "skipped"
        first = carried[0]
        try:
            recipient = await _recipient(session, row, first, table[first.kind])
        except Exception as exc:
            return await _failed(session, row, exc, len(carried))
        if recipient is None:
            await repo.mark_skipped(session, delivery_id, "no_recipient")
            log.info("mail_skipped", delivery_id=str(delivery_id), error_code="no_recipient")
            return "skipped"
        try:
            mail = email.render(
                recipient,
                [email.Section(table[n.kind].template) for n in carried],
                digest=row["mode"] == delivery.DIGEST,
            )
            provider_id = await email.get_sender().send(mail, idempotency_key=str(delivery_id))
        except Exception as exc:
            return await _failed(session, row, exc, len(carried))
        await repo.mark_sent(session, delivery_id, sent_at=now, provider_id=provider_id)
    log.info(
        "mail_sent",
        delivery_id=str(delivery_id),
        kind=first.kind if row["mode"] == delivery.IMMEDIATE else delivery.DIGEST,
        notice_count=len(carried),
        provider_ref=provider_id,
    )
    return "sent"
