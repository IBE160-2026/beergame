"""The Student's own `messaging` data for «Mine data» (Story 15.1, FR-75): every Message stored
with the User among its recipients (`message_recipients`, resolved when it was sent), also from
an archived Class or one they have left and with no inbox limit, the sender (staff) by name as
«Meldinger» names them; how many notices, and each mail sent to them (no mail text is stored).
By the caller's own id only."""

import uuid

from sqlalchemy import func, select

from app.modules.identity import service as identity
from app.modules.messaging.models import mail_deliveries, message_recipients, messages
from app.platform.db import get_sessionmaker
from app.platform.notify import notices
from app.platform.own_data import OwnRecord, record


async def own_records(user_id: uuid.UUID) -> dict[str, list[OwnRecord]]:
    async with get_sessionmaker()() as s:
        rows = (
            (
                await s.execute(
                    select(
                        messages.c.class_session_id,
                        messages.c.sender_id,
                        messages.c.created_at,
                        messages.c.text,
                    )
                    .join(message_recipients, message_recipients.c.message_id == messages.c.id)
                    .where(message_recipients.c.user_id == user_id)
                    .order_by(messages.c.created_at.desc(), messages.c.id.desc())
                )
            )
            .mappings()
            .all()
        )
        senders = await identity.people(s, list({r["sender_id"] for r in rows if r["sender_id"]}))
        notice_count = (
            await s.execute(select(func.count()).where(notices.c.user_id == user_id))
        ).scalar_one()
        mails = (
            (
                await s.execute(
                    select(mail_deliveries)
                    .where(mail_deliveries.c.user_id == user_id)
                    .order_by(mail_deliveries.c.created_at)
                )
            )
            .mappings()
            .all()
        )
    found = [
        record(
            "message",
            [
                (
                    "sender",
                    "text",
                    senders[r["sender_id"]].name if r["sender_id"] in senders else None,
                ),
                ("text", "text", r["text"]),
            ],
            class_session_id=r["class_session_id"],
            at=r["created_at"],
        )
        for r in rows
    ]
    found.append(record("notices", [("notices", "number", notice_count)]))
    found += [
        record(
            "mail",
            [
                ("mode", "code", m["mode"]),
                ("sent_at", "datetime", m["sent_at"]),
                ("delivery_state", "code", m["delivery_state"]),
                ("skipped_reason", "code", m["skipped_reason"]),
            ],
            at=m["created_at"],
        )
        for m in mails
    ]
    return {"messages": found}
