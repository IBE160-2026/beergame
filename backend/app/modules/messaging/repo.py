"""SQL for `mail_deliveries`. Only `messaging.service` calls it."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import RowMapping, and_, any_, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.messaging.models import mail_deliveries
from app.platform.notify import notices


async def insert_delivery(
    session: AsyncSession,
    *,
    delivery_id: uuid.UUID,
    user_id: uuid.UUID | None,
    mode: str,
    notice_ids: Sequence[uuid.UUID],
    claimed_at: datetime,
) -> None:
    await session.execute(
        mail_deliveries.insert().values(
            id=delivery_id,
            user_id=user_id,
            mode=mode,
            notice_ids=list(notice_ids),
            claimed_at=claimed_at,
        )
    )


async def lock_user_digest(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Serialise digest claims for one User until the transaction ends."""
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": f"digest:{user_id}"},
    )


async def digest_claimed_between(
    session: AsyncSession, user_id: uuid.UUID, start: datetime, end: datetime
) -> bool:
    result = await session.execute(
        select(mail_deliveries.c.id)
        .where(
            mail_deliveries.c.user_id == user_id,
            mail_deliveries.c.mode == "digest",
            mail_deliveries.c.claimed_at >= start,
            mail_deliveries.c.claimed_at < end,
        )
        .limit(1)
    )
    return result.first() is not None


async def lock_delivery(session: AsyncSession, delivery_id: uuid.UUID) -> RowMapping | None:
    """The delivery, locked for this transaction; None when it is gone or another transaction
    holds it (a second `mail` job for the same delivery)."""
    result = await session.execute(
        select(mail_deliveries)
        .where(mail_deliveries.c.id == delivery_id)
        .with_for_update(skip_locked=True)
    )
    return result.mappings().one_or_none()


async def mark_sent(
    session: AsyncSession, delivery_id: uuid.UUID, *, sent_at: datetime, provider_id: str
) -> None:
    await session.execute(
        update(mail_deliveries)
        .where(mail_deliveries.c.id == delivery_id)
        .values(
            sent_at=sent_at,
            provider_message_id=provider_id,
            attempts=mail_deliveries.c.attempts + 1,
        )
    )


async def mark_failed(session: AsyncSession, delivery_id: uuid.UUID, *, give_up: bool) -> None:
    values: dict = {"attempts": mail_deliveries.c.attempts + 1}
    if give_up:
        values["skipped_reason"] = "send_failed"
    await session.execute(
        update(mail_deliveries).where(mail_deliveries.c.id == delivery_id).values(**values)
    )


async def mark_skipped(session: AsyncSession, delivery_id: uuid.UUID, reason: str) -> None:
    await session.execute(
        update(mail_deliveries)
        .where(mail_deliveries.c.id == delivery_id)
        .values(skipped_reason=reason)
    )


async def unsent_claimed_before(session: AsyncSession, cutoff: datetime) -> list[RowMapping]:
    """Deliveries neither sent nor given up, claimed at or before `cutoff`, with their mode and
    attempts: their `mail` job was lost or failed, and the sweep may defer it again."""
    result = await session.execute(
        select(
            mail_deliveries.c.id,
            mail_deliveries.c.mode,
            mail_deliveries.c.attempts,
            mail_deliveries.c.claimed_at,
        )
        .where(
            and_(
                mail_deliveries.c.sent_at.is_(None),
                mail_deliveries.c.skipped_reason.is_(None),
                mail_deliveries.c.claimed_at <= cutoff,
            )
        )
        .order_by(mail_deliveries.c.id)
    )
    return list(result.mappings())


async def latest_sent_for(
    session: AsyncSession, user_id: uuid.UUID | None, refs: Sequence[uuid.UUID]
) -> RowMapping | None:
    """The most recently sent delivery to the User `user_id`, or for a notice addressed by
    reference to one of `refs` (an address's Invitations)."""
    conditions = []
    if user_id is not None:
        conditions.append(mail_deliveries.c.user_id == user_id)
    if refs:
        by_ref = (
            select(notices.c.id)
            .where(
                notices.c.id == any_(mail_deliveries.c.notice_ids),
                notices.c.ref.in_(list(refs)),
            )
            .exists()
        )
        conditions.append(and_(mail_deliveries.c.user_id.is_(None), by_ref))
    if not conditions:
        return None
    result = await session.execute(
        select(mail_deliveries)
        .where(mail_deliveries.c.sent_at.is_not(None), or_(*conditions))
        .order_by(mail_deliveries.c.sent_at.desc(), mail_deliveries.c.id.desc())
        .limit(1)
    )
    return result.mappings().one_or_none()
