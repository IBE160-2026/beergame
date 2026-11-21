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
- `send_message(session, …)` (Story 7.9, `messages.py`): a staff member's Message to Students,
  stored and told through `platform/notify` as kind `message`. A calling module passes a
  `Recipient` (Epic 13: an explicit list of Students).
- `receive_webhook(body, headers, now)` (Story 4.6): a signed provider event about a sent mail,
  stored on its delivery. `invitation_deliveries(refs)` reads what was stored per Invitation, for
  `classes`; `simulate_bounce` is the local stand-in for the provider's bounce.

Claiming writes the `mail_deliveries` row and defers the `mail` job in one transaction. Job
arguments, log lines and rows hold ids only; the address exists only inside `send`.
"""

import json
import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity import service as identity
from app.modules.messaging import delivery, repo, signature
from app.platform import email, jobs, notify
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

__all__ = [
    "MAX_ATTEMPTS",
    "SEND_MAIL",
    "DueItem",
    "EventUnreadable",
    "InvitationDelivery",
    "SignatureInvalid",
    "claim",
    "claim_notice",
    "due_items",
    "invitation_deliveries",
    "latest_sent_mail",
    "receive_webhook",
    "send",
    "simulate_bounce",
]

log = structlog.get_logger(__name__)

_MESSAGES = frozenset(
    {"MESSAGE_KIND", "MessageRefused", "Recipient", "RecipientKind", "SentMessage", "send_message"}
)
"""`messages.py`'s names, served from here (Story 7.9). Read on first use, not imported here:
`messages` imports `classes.service`, which imports this module."""


def __getattr__(name: str) -> object:
    if name in _MESSAGES:
        from app.modules.messaging import messages

        return getattr(messages, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
    session: AsyncSession, row, first: notify.Notice, entry: delivery.Delivery, now: datetime
) -> email.Recipient | None:
    if entry.resolve_ref is not None:
        return None if first.ref is None else await entry.resolve_ref(session, first.ref, now)
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


async def _sections(
    session: AsyncSession, row, carried: list[notify.Notice], table, now: datetime
) -> list[email.Section]:
    """One part per carried notice, with the variables its kind's owner gives at `now`. A notice
    whose owner says no mail is needed any more (a used or expired link) is left out."""
    sections = []
    for notice in carried:
        entry = table[notice.kind]
        context: object = {}
        if entry.context is not None:
            context = await entry.context(session, row["user_id"], notice.ref, now)
            if context is None:
                continue
        sections.append(email.Section(entry.template, context))
    return sections


async def _compose(
    session: AsyncSession, row, carried: list[notify.Notice], table, now: datetime
) -> email.Mail | str:
    """The mail for a delivery, or the reason it has none (`no_recipient`, `stale`)."""
    first = carried[0]
    recipient = await _recipient(session, row, first, table[first.kind], now)
    if recipient is None:
        return "no_recipient"
    sections = await _sections(session, row, carried, table, now)
    if not sections:
        return "stale"
    return email.render(recipient, sections, digest=row["mode"] == delivery.DIGEST)


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
            # In a savepoint: a resolver whose SQL fails aborts only the savepoint, so the failed
            # try can still be counted below (else the job's transaction rolls back with
            # `attempts` at 0, and the sweep defers the delivery again forever).
            async with session.begin_nested():
                mail = await _compose(session, row, carried, table, now)
        except Exception as exc:
            return await _failed(session, row, exc, len(carried))
        if isinstance(mail, str):
            await repo.mark_skipped(session, delivery_id, mail)
            log.info("mail_skipped", delivery_id=str(delivery_id), error_code=mail)
            return "skipped"
        try:
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


async def latest_sent_mail(address: str) -> tuple[email.Mail, datetime] | None:
    """The newest mail sent to this e-mail (to its User, or for one of its Invitations), rendered
    again on its send time, with that time; None when there is none, or when its content is gone
    (a link used since). For the local dev mailbox only (`routes.py`): it lets the Playwright
    tests read a link from the `[email:mock]` mail, which logs ids only."""
    table = delivery.table()
    async with get_sessionmaker().begin() as session:
        user_id = await identity.user_id_for_email(session, address)
        refs = await identity.invitation_ids_for_email(session, address)
        row = await repo.latest_sent_for(session, user_id, refs)
        if row is None:
            return None
        carried = [n for n in await notify.get(session, row["notice_ids"]) if n.kind in table]
        if not carried:
            return None
        mail = await _compose(session, row, carried, table, row["sent_at"])
    return None if isinstance(mail, str) else (mail, row["sent_at"])


# What the provider reports about sent mails (Story 4.6, AD-11, AD-14, NFR-10). Resend posts a
# signed event per delivery, delay and bounce; the event names the mail by the provider's message
# id, which `send` stored. Logs hold the event type and ids only, never an address.

SignatureInvalid = signature.SignatureInvalid

STATE_OF_EVENT = {
    "email.delivery_delayed": "delayed",
    "email.delivered": "delivered",
    "email.bounced": "bounced",
}
"""The event types stored; every other type is acknowledged and ignored."""
_RANK = {
    (None, None): 0,
    ("delayed", None): 1,
    ("bounced", "soft"): 2,
    ("delivered", None): 3,
    ("bounced", "hard"): 4,
}
"""How far a mail has got: a temporary failure (a delay, a soft bounce) gives way to a later
delivery, and nothing undoes a hard bounce."""
HARD_BOUNCE_TYPE = "Permanent"
"""Resend's `data.bounce.type` of a permanent bounce; `Transient` and `Undetermined` are soft."""
_EVENT_TYPE = re.compile(r"[a-z][a-z._]{0,63}")


class EventUnreadable(Exception):
    """A correctly signed body that is not an event this handler can read."""


def _loggable_type(value: object) -> str:
    return value if isinstance(value, str) and _EVENT_TYPE.fullmatch(value) else "unreadable"


def _bounce_class(data: Mapping[str, object]) -> str:
    bounce = data.get("bounce")
    kind = bounce.get("type") if isinstance(bounce, Mapping) else None
    return "hard" if kind == HARD_BOUNCE_TYPE else "soft"


def _moves_forward(row, state: str, bounce_class: str | None) -> bool:
    """Whether an event moves the stored state forward (`_RANK`); a repeated, older or late
    event does not, and changes nothing."""
    return _RANK[(state, bounce_class)] > _RANK[(row["delivery_state"], row["bounce_class"])]


async def receive_webhook(body: bytes, headers: Mapping[str, str], now: datetime) -> str:
    """Verify and store one provider event. Returns `stored`, `repeated` (this event id was the
    last one stored) or `ignored` (a type not stored, or a mail this system does not know).
    An event that does not move the mail's state forward is `unchanged` and stores nothing.
    Raises `SignatureInvalid` before reading the body, and `EventUnreadable`."""
    event_id = signature.verify(get_settings().resend_webhook_secret, headers, body, now)
    try:
        event = json.loads(body)
    except ValueError:
        raise EventUnreadable from None
    if not isinstance(event, dict):
        raise EventUnreadable
    kind = event.get("type")
    state = STATE_OF_EVENT.get(kind) if isinstance(kind, str) else None
    if state is None:
        log.info("webhook_event_ignored", event_type=_loggable_type(kind), reason="type")
        return "ignored"
    data = event.get("data")
    if not isinstance(data, dict):
        raise EventUnreadable
    provider_id = data.get("email_id")
    if not isinstance(provider_id, str) or not provider_id or len(provider_id) > 200:
        raise EventUnreadable
    async with get_sessionmaker().begin() as session:
        row = await repo.lock_by_provider_id(session, provider_id)
        if row is None:
            log.info("webhook_event_ignored", event_type=kind, reason="unknown_mail")
            return "ignored"
        if row["last_event_id"] == event_id:
            log.info("webhook_event_repeated", delivery_id=str(row["id"]), event_type=kind)
            return "repeated"
        bounce_class = _bounce_class(data) if state == "bounced" else None
        if not _moves_forward(row, state, bounce_class):
            log.info("webhook_event_unchanged", delivery_id=str(row["id"]), event_type=kind)
            return "unchanged"
        await repo.store_event(
            session, row["id"], state=state, bounce_class=bounce_class, event_id=event_id
        )
    log.info(
        "webhook_event_stored",
        delivery_id=str(row["id"]),
        event_type=kind,
        delivery_state=state,
        bounce_class=bounce_class,
    )
    return "stored"


@dataclass(frozen=True)
class InvitationDelivery:
    """What is known of the newest mail of an Invitation: whether it was handed to the provider,
    and what the provider reported since (None before any report)."""

    sent: bool
    state: str | None
    bounce_class: str | None


async def invitation_deliveries(refs: Sequence[uuid.UUID]) -> dict[uuid.UUID, InvitationDelivery]:
    """Per Invitation id in `refs` with a mail claimed, its newest delivery (Story 4.6). Other
    modules read delivery state here, never from `mail_deliveries` (AD-14)."""
    async with get_sessionmaker().begin() as session:
        found = await repo.deliveries_for_refs(session, refs)
    return {
        ref: InvitationDelivery(
            sent=row["sent_at"] is not None,
            state=row["delivery_state"],
            bounce_class=row["bounce_class"],
        )
        for ref, row in found.items()
    }


async def simulate_bounce(address: str, bounce_class: str, now: datetime) -> uuid.UUID | None:
    """The local stand-in for the provider's bounce (Story 4.6, AD-17): sign an `email.bounced`
    event for the newest mail sent to `address` with the configured secret and pass it through
    `receive_webhook`, as the provider would post it. Returns that mail's delivery id; None when
    no mail was sent there. Refused in production, where the dev routes are not mounted."""
    if get_settings().app_env == "production":
        raise RuntimeError("the bounce simulation exists outside production only")
    async with get_sessionmaker().begin() as session:
        user_id = await identity.user_id_for_email(session, address)
        refs = await identity.invitation_ids_for_email(session, address)
        row = await repo.latest_sent_for(session, user_id, refs)
    if row is None or not row["provider_message_id"]:
        return None
    body = json.dumps(
        {
            "type": "email.bounced",
            "created_at": now.isoformat(),
            "data": {
                "email_id": row["provider_message_id"],
                "bounce": {
                    "type": HARD_BOUNCE_TYPE if bounce_class == "hard" else "Transient",
                    "message": "Simulated locally.",
                },
            },
        }
    ).encode("utf-8")
    event_id = f"msg_local_{uuid.uuid7().hex}"
    stamp = int(now.timestamp())
    secret = get_settings().resend_webhook_secret
    headers = {
        signature.ID: event_id,
        signature.TIMESTAMP: str(stamp),
        signature.SIGNATURE: signature.sign(secret, event_id, stamp, body),
    }
    await receive_webhook(body, headers, now)
    return row["id"]
