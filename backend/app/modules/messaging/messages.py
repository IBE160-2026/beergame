"""Messages from staff to Students (Story 7.9, FR-40, AD-9, AD-12, AD-14).

A Lecturer or Assistant lecturer of a Class writes one Message to one Student, a Class game or a
whole Class session; a calling module may also pass an explicit list of Students (Epic 13). Story
13.6 adds the Students of an Obligatory class session who have not met the requirement, a list
`reports.service` resolves when the Message is sent, so a Student who met it meanwhile is left out.
`send_message` stores the Message and one recipient row per Student in the caller's transaction,
asks `platform/notify` to tell each of them (kind `message`, delivered at once by Story 3.5's
pipeline) and emits `session:<id>`. A repeated request carries the same client-made key and finds
the Message it stored: it is never sent twice.

Recipients are resolved when the Message is sent and are always narrowed to the registered
Students of the Class: an AI player or an unregistered Roster address never gets anything.
Messages are one-way; nothing here lets a Student write one.
"""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.completion import CompletionStatus
from app.modules.classes import service as classes
from app.modules.games import service as games
from app.modules.identity import service as identity
from app.modules.messaging.models import message_recipients, messages
from app.modules.sessions import service as sessions
from app.platform import authz, events, notify
from app.platform.config import get_settings
from app.platform.db import get_sessionmaker

__all__ = [
    "MESSAGE_KIND",
    "MY_MESSAGES_LIMIT",
    "SENT_MESSAGES_LIMIT",
    "MyMessage",
    "SentList",
    "SentListItem",
    "MessageForm",
    "MessageRefused",
    "NotMetStudent",
    "Recipient",
    "RecipientKind",
    "SentMessage",
    "message_form",
    "message_mail_context",
    "my_messages",
    "send",
    "send_message",
    "sent_messages",
]

log = structlog.get_logger(__name__)

MESSAGE_KIND = "message"
"""The notice kind of a Message (`delivery.KINDS`, immediate)."""
SEND = "messages.send"
"""The `platform/authz` action: the staff of the Class, Lecturers and Assistant lecturers."""
READ_SENT = "messages.read_sent"
"""The staff's list of a Class session's Messages (Story 7.10), held to the same staff roles."""
MY_MESSAGES_LIMIT = 100
"""The newest Messages a Student's Hjem lists."""
SENT_MESSAGES_LIMIT = 200
"""The newest Messages the staff's «Meldinger» lists."""


class RecipientKind(StrEnum):
    STUDENT = "student"
    CLASS_GAME = "class_game"
    CLASS_SESSION = "class_session"
    LIST = "list"
    """Students a calling module names (Epic 13); never offered by the api."""
    REQUIREMENT_NOT_MET = "requirement_not_met"
    """The Students of an Obligatory class session who have not met the requirement when the
    Message is sent (Story 13.6), through `reports.service.requirement_not_met`."""


@dataclass(frozen=True)
class Recipient:
    """Whom a Message is written to. `game_id` names the Class game of a `class_game` Message, and
    may name the game a `student` Message was written from (its title only)."""

    kind: RecipientKind
    game_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    user_ids: tuple[uuid.UUID, ...] = ()

    def __post_init__(self) -> None:
        if (self.kind == RecipientKind.STUDENT) != (self.user_id is not None):
            raise ValueError("a Message to one Student names that Student, and only then")
        if self.kind == RecipientKind.CLASS_GAME and self.game_id is None:
            raise ValueError("a Message to a Class game names the game")
        if (
            self.kind
            in (RecipientKind.CLASS_SESSION, RecipientKind.LIST, RecipientKind.REQUIREMENT_NOT_MET)
            and self.game_id
        ):
            raise ValueError("a Message to a Class session or a list names no game")


def recipient_of(
    game_id: uuid.UUID | None, student_id: uuid.UUID | None, requirement_not_met: bool = False
) -> Recipient | None:
    """The api's recipient: a Student when one is named (the game, if any, names the title), a
    Class game when only a game is named, else the whole Class session. With
    `requirement_not_met` (Story 13.6) the Students who have not met the requirement, and None,
    refused as any recipient outside the Class session, when a game or a Student is named too."""
    if requirement_not_met:
        if game_id is not None or student_id is not None:
            return None
        return Recipient(RecipientKind.REQUIREMENT_NOT_MET)
    if student_id is not None:
        return Recipient(RecipientKind.STUDENT, game_id=game_id, user_id=student_id)
    if game_id is not None:
        return Recipient(RecipientKind.CLASS_GAME, game_id=game_id)
    return Recipient(RecipientKind.CLASS_SESSION)


class MessageRefused(Exception):
    """A Message that is not stored: `message_empty`, `message_too_long` (with `max_length`),
    `no_recipients` (422) or `message_key_conflict` (409)."""

    def __init__(self, code: str, status: int = 422, fields: Mapping[str, object] | None = None):
        super().__init__(code)
        self.code = code
        self.status = status
        self.fields = dict(fields or {})


@dataclass(frozen=True)
class Target:
    """A recipient resolved in its Class session: the Students who get the Message now, and what
    its title names."""

    students: tuple[uuid.UUID, ...]
    game_number: int | None
    student_name: str | None
    statuses: tuple[tuple[uuid.UUID, CompletionStatus], ...] = ()
    """For `requirement_not_met`: each Student's Completion status, as the form's table shows."""


async def _resolve(
    session: AsyncSession, class_id: uuid.UUID, session_id: uuid.UUID, recipient: Recipient
) -> Target | None:
    """The Students `recipient` means now, or None when it names a game outside the Class session
    (or one the Lecturer overview does not list, AD-13) or a Student not registered in the Class:
    one answer, like a Class session the User may not reach (FR-5)."""
    registered = set(await classes.registered_students(class_id))
    game_number: int | None = None
    game: games.ClassGameStudents | None = None
    if recipient.game_id is not None:
        game = await games.class_game_students(session, recipient.game_id)
        if game is None or game.class_session_id != session_id or not game.listed:
            return None
        game_number = game.game_number
    if recipient.kind == RecipientKind.STUDENT:
        assert recipient.user_id is not None
        if recipient.user_id not in registered:
            return None
        # A game in the title is one the Student is assigned to (as a Message to it would reach).
        if game is not None and recipient.user_id not in game.students:
            return None
        names = await classes.student_names(class_id, [recipient.user_id], session=session)
        return Target((recipient.user_id,), game_number, names.get(recipient.user_id))
    if recipient.kind == RecipientKind.CLASS_GAME:
        assert game is not None
        return Target(tuple(u for u in game.students if u in registered), game_number, None)
    if recipient.kind == RecipientKind.CLASS_SESSION:
        return Target(tuple(sorted(registered, key=str)), None, None)
    if recipient.kind == RecipientKind.REQUIREMENT_NOT_MET:
        # Read on use, not at import: `reports` imports `sessions`, which imports `classes`, which
        # loads this module through `messaging.delivery` (the worker's import order).
        from app.modules.reports import service as reports

        # Judged now, in this transaction: a Student who met it since the form was read is out.
        found = tuple(
            (user_id, status)
            for user_id, status in await reports.requirement_not_met(session_id, session=session)
            if user_id in registered
        )
        return Target(tuple(user_id for user_id, _ in found), None, None, found)
    listed = tuple(dict.fromkeys(u for u in recipient.user_ids if u in registered))
    return Target(listed, None, None)


async def _sent_before(session: AsyncSession, session_id: uuid.UUID, recipient: Recipient) -> int:
    """The Messages of the Class session written to the same recipient (Story 7.9). A list is
    never the same recipient twice: it counts 0."""
    if recipient.kind == RecipientKind.LIST:
        return 0
    query = select(func.count()).where(
        messages.c.class_session_id == session_id,
        messages.c.recipient_kind == recipient.kind.value,
    )
    if recipient.kind == RecipientKind.STUDENT:
        query = query.where(messages.c.recipient_user_id == recipient.user_id)
    elif recipient.kind == RecipientKind.CLASS_GAME:
        query = query.where(messages.c.recipient_game_id == recipient.game_id)
    return (await session.execute(query)).scalar_one()


def _clean(text: str) -> str:
    """The text as stored: line breaks as `\\n`, blank lines and spaces around it removed, and the
    characters a database text cannot hold (NUL, lone surrogates) left out."""
    kept = "".join(c for c in text if c != "\x00" and not 0xD800 <= ord(c) <= 0xDFFF)
    return kept.replace("\r\n", "\n").replace("\r", "\n").strip()


@dataclass(frozen=True)
class SentMessage:
    message_id: uuid.UUID
    students: int
    """The Students it went to."""
    sent_before: int
    """The Messages of the Class session to the same recipient, this one included."""
    repeated: bool = False
    """The key was used before: nothing new was stored or sent."""


async def _stored(
    session: AsyncSession,
    key: uuid.UUID,
    session_id: uuid.UUID,
    sender_id: uuid.UUID,
    recipient: Recipient,
    text: str,
) -> SentMessage | None:
    row = (
        (await session.execute(select(messages).where(messages.c.key == key)))
        .mappings()
        .one_or_none()
    )
    if row is None:
        return None
    same = (
        row["class_session_id"] == session_id
        and row["sender_id"] == sender_id
        and row["recipient_kind"] == recipient.kind.value
        and row["recipient_game_id"] == recipient.game_id
        and row["recipient_user_id"] == recipient.user_id
        and row["text"] == text
    )
    if not same:
        # The key of another Message: a client that reused it is told, and nothing is sent.
        raise MessageRefused("message_key_conflict", status=409)
    count = (
        await session.execute(
            select(func.count()).where(message_recipients.c.message_id == row["id"])
        )
    ).scalar_one()
    stored = Recipient(
        RecipientKind(row["recipient_kind"]),
        game_id=row["recipient_game_id"],
        user_id=row["recipient_user_id"],
    )
    return SentMessage(row["id"], count, await _sent_before(session, session_id, stored), True)


async def send_message(
    session: AsyncSession,
    *,
    class_session_id: uuid.UUID,
    class_id: uuid.UUID,
    sender_id: uuid.UUID,
    key: uuid.UUID,
    recipient: Recipient,
    text: str,
) -> SentMessage | None:
    """Store and send one Message in the caller's transaction. None when the recipient is not of
    this Class session (see `_resolve`). The caller has checked that the sender is staff of the
    Class (`messages.send`). Raises `MessageRefused`."""
    text = _clean(text)
    if not text:
        raise MessageRefused("message_empty")
    limit = get_settings().message_max_length
    if len(text) > limit:
        raise MessageRefused("message_too_long", fields={"max_length": limit})
    found = await _stored(session, key, class_session_id, sender_id, recipient, text)
    if found is not None:
        return found
    target = await _resolve(session, class_id, class_session_id, recipient)
    if target is None:
        return None
    if not target.students:
        raise MessageRefused("no_recipients")
    message_id = uuid.uuid7()
    inserted = await session.execute(
        insert(messages)
        .values(
            id=message_id,
            key=key,
            class_session_id=class_session_id,
            sender_id=sender_id,
            recipient_kind=recipient.kind.value,
            recipient_game_id=recipient.game_id,
            recipient_user_id=recipient.user_id,
            text=text,
        )
        .on_conflict_do_nothing(index_elements=[messages.c.key])
        .returning(messages.c.id)
    )
    if inserted.scalar_one_or_none() is None:
        # Another request with the same key stored it first: answer as that one did.
        found = await _stored(session, key, class_session_id, sender_id, recipient, text)
        assert found is not None
        return found
    await session.execute(
        insert(message_recipients),
        [{"message_id": message_id, "user_id": user_id} for user_id in target.students],
    )
    for user_id in target.students:
        await notify.enqueue(
            session, user_id, MESSAGE_KIND, f"message:{message_id}:{user_id}", ref=message_id
        )
    await events.emit(session, "session", str(class_session_id))
    log.info(
        "message_sent",
        message_id=str(message_id),
        class_session_id=str(class_session_id),
        recipient_kind=recipient.kind.value,
        recipient_count=len(target.students),
    )
    return SentMessage(
        message_id,
        len(target.students),
        await _sent_before(session, class_session_id, recipient),
    )


_NB = str.maketrans({"æ": "{", "ø": "|", "å": "}"})
"""Æ, Ø and Å after Z, in that order, as the Norwegian alphabet has them."""


@dataclass(frozen=True)
class NotMetStudent:
    """One row of the Meldingsskjema's table for `requirement_not_met` (Story 13.6, FR-17): the
    Student, the share of Weeks they ordered against the share required of them, and the share
    the Play deadline's playout played, so a shortfall the playout or the group's pace caused can be
    told from one the Student caused."""

    user_id: uuid.UUID
    name: str | None
    ordered_share: int | None
    required_share: int
    playout_share: int | None
    share_game: Literal["class", "makeup"] | None


async def _not_met_rows(
    session: AsyncSession, class_id: uuid.UUID, target: Target
) -> list[NotMetStudent]:
    """The table's rows, by name now (AD-14) in Norwegian order (Æ, Ø, Å after Z), then by id."""
    names = await classes.student_names(
        class_id, [user_id for user_id, _ in target.statuses], session=session
    )
    rows = [
        NotMetStudent(
            user_id=user_id,
            name=names.get(user_id),
            ordered_share=status.ordered_share,
            required_share=status.required_share,
            playout_share=status.playout_share,
            share_game=status.share_game,
        )
        for user_id, status in target.statuses
    ]
    return sorted(
        rows, key=lambda row: ((row.name or "").casefold().translate(_NB), str(row.user_id))
    )


@dataclass(frozen=True)
class MessageForm:
    """What the Meldingsskjema shows before a send (Story 7.9, UX-DR46)."""

    kind: RecipientKind
    session: sessions.StaffedSession
    game_id: uuid.UUID | None
    game_number: int | None
    student_name: str | None
    students: int
    sent_before: int
    max_length: int
    not_met: tuple[NotMetStudent, ...] = ()
    """For `requirement_not_met` (Story 13.6): the Students it would go to now, with shares."""


async def message_form(
    user: authz.Principal,
    session_id: uuid.UUID,
    *,
    game_id: uuid.UUID | None,
    student_id: uuid.UUID | None,
    requirement_not_met: bool = False,
) -> MessageForm | None:
    """The form for the recipient the params name, or None, one answer, when the User is not
    staff of the Class or the recipient is not of this Class session (FR-5)."""
    staffed = await sessions.staffed_session(user, session_id, SEND)
    if staffed is None:
        return None
    recipient = recipient_of(game_id, student_id, requirement_not_met)
    if recipient is None:
        return None
    async with get_sessionmaker()() as s:
        target = await _resolve(s, staffed.class_id, session_id, recipient)
        if target is None:
            return None
        before = await _sent_before(s, session_id, recipient)
        rows = await _not_met_rows(s, staffed.class_id, target) if target.statuses else []
    return MessageForm(
        kind=recipient.kind,
        session=staffed,
        game_id=game_id,
        game_number=target.game_number,
        student_name=target.student_name,
        students=len(target.students),
        sent_before=before,
        max_length=get_settings().message_max_length,
        not_met=tuple(rows),
    )


async def send(
    user: authz.Principal,
    session_id: uuid.UUID,
    *,
    key: uuid.UUID,
    game_id: uuid.UUID | None,
    student_id: uuid.UUID | None,
    text: str,
    requirement_not_met: bool = False,
) -> SentMessage | None:
    """«Send Melding»: None, one answer, when the User is not staff of the Class or the recipient
    is not of this Class session (FR-5). Raises `MessageRefused` and, for an archived Class,
    `classes.ClassArchived`."""
    staffed = await sessions.staffed_session(user, session_id, SEND)
    if staffed is None:
        return None
    recipient = recipient_of(game_id, student_id, requirement_not_met)
    if recipient is None:
        return None
    if staffed.archived:
        raise classes.ClassArchived
    async with get_sessionmaker().begin() as s:
        return await send_message(
            s,
            class_session_id=session_id,
            class_id=staffed.class_id,
            sender_id=user.id,
            key=key,
            recipient=recipient,
            text=text,
        )


async def message_mail_context(
    session: AsyncSession, user_id: uuid.UUID, ref: uuid.UUID | None, now: datetime
) -> Mapping[str, object] | None:
    """The template variables of a `message` notice, for the mail at send time (AD-9): the text
    by lines and the Class's name. None, so no mail is sent, when the Message is gone, the Class is
    archived or the User is no longer a registered Student of it."""
    if ref is None:
        return None
    row = (
        (
            await session.execute(
                select(messages.c.text, messages.c.class_session_id).where(messages.c.id == ref)
            )
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        return None
    class_id = await sessions.class_id_of(session, row["class_session_id"])
    if class_id is None:
        return None
    label = await classes.label_of_class(session, class_id)
    if label is None or label.archived:
        return None
    if user_id not in await classes.registered_students(class_id):
        return None
    return {"lines": row["text"].split("\n"), "class_name": label.name}


# Reading Messages (Story 7.10, FR-40, FR-73, AD-12, AD-14): a Student's own on Hjem, and the
# staff's list of what a Class session was sent. Names are read now, never stored with a Message.


@dataclass(frozen=True)
class MyMessage:
    id: uuid.UUID
    class_id: uuid.UUID
    class_name: str
    sender_name: str | None
    """The sender's name now; None when the account is gone."""
    sent_at: datetime
    text: str


async def my_messages(user: authz.Principal) -> list[MyMessage]:
    """The Messages written to `user`, newest first, at most `MY_MESSAGES_LIMIT`, read through
    `authz.messages_addressed_to` only: a Message to anyone else, or of a Class the User is no
    longer a Student in, is never read (FR-5). Four queries, whatever the number of Messages."""
    async with get_sessionmaker()() as s:
        rows = (
            (
                await s.execute(
                    select(
                        messages.c.id,
                        messages.c.class_session_id,
                        messages.c.sender_id,
                        messages.c.created_at,
                        messages.c.text,
                    )
                    .where(messages.c.id.in_(authz.messages_addressed_to(user)))
                    .order_by(messages.c.created_at.desc(), messages.c.id.desc())
                    .limit(MY_MESSAGES_LIMIT)
                )
            )
            .mappings()
            .all()
        )
        if not rows:
            return []
        class_of = await sessions.class_ids_of(s, [row["class_session_id"] for row in rows])
        senders = await identity.people(s, list({row["sender_id"] for row in rows}))
        enrolled = await classes.enrolled_classes(user, session=s)
    names = {item.id: item.name for item in enrolled.items}
    found: list[MyMessage] = []
    for row in rows:
        class_id = class_of.get(row["class_session_id"])
        if class_id is None or class_id not in names:
            continue
        sender = senders.get(row["sender_id"])
        found.append(
            MyMessage(
                id=row["id"],
                class_id=class_id,
                class_name=names[class_id],
                sender_name=sender.name if sender else None,
                sent_at=row["created_at"],
                text=row["text"],
            )
        )
    return found


@dataclass(frozen=True)
class SentListItem:
    id: uuid.UUID
    kind: RecipientKind
    game_id: uuid.UUID | None
    game_number: int | None
    student_id: uuid.UUID | None
    student_name: str | None
    """The Student's name while they are a registered Student of the Class; else None."""
    sender_name: str | None
    sent_at: datetime
    students: int
    text: str


@dataclass(frozen=True)
class SentList:
    session: sessions.StaffedSession
    items: list[SentListItem]


async def sent_messages(user: authz.Principal, session_id: uuid.UUID) -> SentList | None:
    """«Meldinger» (Story 7.10): the Messages of the Class session, newest first, at most
    `SENT_MESSAGES_LIMIT`, each with its recipient, sender, time and the number of Students it
    went to. None, one answer, when the User is not staff of the Class (FR-5). A fixed number of
    queries, whatever the number of Messages."""
    staffed = await sessions.staffed_session(user, session_id, READ_SENT)
    if staffed is None:
        return None
    count = (
        select(func.count())
        .where(message_recipients.c.message_id == messages.c.id)
        .scalar_subquery()
    )
    async with get_sessionmaker()() as s:
        rows = (
            (
                await s.execute(
                    select(messages, count.label("students"))
                    .where(messages.c.class_session_id == session_id)
                    .order_by(messages.c.created_at.desc(), messages.c.id.desc())
                    .limit(SENT_MESSAGES_LIMIT)
                )
            )
            .mappings()
            .all()
        )
        if not rows:
            return SentList(staffed, [])
        senders = await identity.people(s, list({row["sender_id"] for row in rows}))
        named = [row["recipient_user_id"] for row in rows if row["recipient_user_id"]]
        students = await classes.student_names(staffed.class_id, list(set(named)), session=s)
        numbers = {
            uuid.UUID(game_id): number
            for number, game_id in (await games.class_game_ids(s, session_id)).items()
        }
    items = []
    for row in rows:
        sender = senders.get(row["sender_id"])
        student_id = row["recipient_user_id"]
        game_id = row["recipient_game_id"]
        items.append(
            SentListItem(
                id=row["id"],
                kind=RecipientKind(row["recipient_kind"]),
                game_id=game_id,
                game_number=numbers.get(game_id) if game_id else None,
                student_id=student_id,
                student_name=students.get(student_id) if student_id else None,
                sender_name=sender.name if sender else None,
                sent_at=row["created_at"],
                students=row["students"],
                text=row["text"],
            )
        )
    return SentList(staffed, items)
