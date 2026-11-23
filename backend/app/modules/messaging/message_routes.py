"""The Meldingsskjema's endpoints (Story 7.9, FR-40, AD-9, AD-12): the form of a Message to a
Student, a Class game or a whole Class session, and its send.

- `GET /api/class-sessions/{id}/messages/form?game_id=&student_id=`: whom the Message goes to,
  how many Students that is now and how many Messages went to the same recipient before.
- `POST /api/class-sessions/{id}/messages`: «Send Melding», with a client-made `key`; a repeated
  request answers as the first did and sends nothing.

The recipient comes from the params: a Student when `student_id` is given (a `game_id` then only
names the game in the title), a Class game when only `game_id` is, else the whole Class session.
Story 13.6: `recipient=requirement_not_met` (with neither id) writes to the Students of an
Obligatory class session who have not met the requirement, judged again when the Message is sent;
the form then lists them with their shares.
Anyone who is not staff of the Class, a Class session that does not exist and a recipient outside
it all answer the same 403 `forbidden` (FR-5). There is no route by which a Student writes.

Story 7.10 adds the reads:

- `GET /api/me/messages`: a Student's own Messages for Hjem, newest first, held to
  `authz.messages_addressed_to`.
- `GET /api/class-sessions/{id}/messages`: «Meldinger», the Messages the Class session was sent,
  for its staff.
"""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.modules.messaging import messages
from app.platform import authz
from app.platform.errors import documented, error_response

router = APIRouter(prefix="/api", tags=["messaging"])

TEXT_HARD_LIMIT = 100_000
"""A request body bound far above any configured `message_max_length`; the configured limit is
the one a Message is held to (`message_too_long`)."""


def _id(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise authz.Forbidden from None


def _optional_id(value: str | None) -> uuid.UUID | None:
    return None if value is None else _id(value)


RecipientParam = Literal["requirement_not_met"]
"""A recipient the api names by kind rather than by id (Story 13.6)."""


class NotMetStudentOut(BaseModel):
    """One Student who has not met the requirement (Story 13.6, FR-17), from
    `reports.service.completion_status`."""

    user_id: uuid.UUID
    name: str | None
    """The Student's name now; None when the api no longer has it."""
    ordered_share: int | None
    """The share of Weeks after the Guided Weeks the Student ordered, in percent; None without a
    game."""
    required_share: int
    """The share required of this Student (their Tilrettelegging share where there is one)."""
    playout_share: int | None
    """The share of Weeks the Play deadline's playout played, in percent; None with no game."""
    share_game: Literal["class", "makeup"] | None
    """Which game the share comes from when the Student has an Oppfølgingsspill."""


class MessageFormOut(BaseModel):
    """What the Meldingsskjema shows before a send (UX-DR46)."""

    kind: Literal["student", "class_game", "class_session", "requirement_not_met"]
    class_session_id: uuid.UUID
    class_id: uuid.UUID
    class_name: str
    session_number: int
    game_id: uuid.UUID | None
    game_number: int | None
    """The Class game the Message is written to, or from (a Student's title)."""
    student_name: str | None
    """The Student's name for a Message to one Student; else None."""
    students: int
    """The Students the Message would go to now; 0 when there is none to send to."""
    sent_before: int
    """Messages of this Class session to the same recipient so far."""
    max_length: int
    """The most characters a Message may hold."""
    not_met: list[NotMetStudentOut] = []
    """For `requirement_not_met`: the Students it would go to now, by name; else empty."""


class MessageIn(BaseModel):
    key: uuid.UUID
    """Made by the client once per text: a repeat with the same key sends nothing new."""
    game_id: uuid.UUID | None = None
    student_id: uuid.UUID | None = None
    recipient: RecipientParam | None = None
    """`requirement_not_met` (Story 13.6), with neither id."""
    text: str = Field(max_length=TEXT_HARD_LIMIT)


class MessageSentOut(BaseModel):
    message_id: uuid.UUID
    students: int
    """The Students the Message went to."""
    sent_before: int
    """Messages of this Class session to the same recipient, this one included."""


@router.get(
    "/class-sessions/{session_id}/messages/form",
    response_model=MessageFormOut,
    responses=documented(401, 403),
    operation_id="getMessageForm",
)
async def get_message_form(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require(messages.SEND))],
    game_id: Annotated[str | None, Query(max_length=64)] = None,
    student_id: Annotated[str | None, Query(max_length=64)] = None,
    recipient: RecipientParam | None = None,
) -> MessageFormOut:
    """The Meldingsskjema's recipient (Story 7.9): its title's parts, the Students it reaches now,
    the earlier Messages to it and the length limit. 403 `forbidden`, one answer, for anyone who
    is not staff of the Class and for a Class session, game or Student outside it (FR-5)."""
    found = await messages.message_form(
        user,
        _id(session_id),
        game_id=_optional_id(game_id),
        student_id=_optional_id(student_id),
        requirement_not_met=recipient == "requirement_not_met",
    )
    if found is None:
        raise authz.Forbidden
    return MessageFormOut(
        kind=found.kind.value,
        class_session_id=found.session.id,
        class_id=found.session.class_id,
        class_name=found.session.class_name,
        session_number=found.session.number,
        game_id=found.game_id,
        game_number=found.game_number,
        student_name=found.student_name,
        students=found.students,
        sent_before=found.sent_before,
        max_length=found.max_length,
        not_met=[
            NotMetStudentOut(
                user_id=row.user_id,
                name=row.name,
                ordered_share=row.ordered_share,
                required_share=row.required_share,
                playout_share=row.playout_share,
                share_game=row.share_game,
            )
            for row in found.not_met
        ],
    )


MESSAGES = {
    "message_empty": "The Message has no text.",
    "message_too_long": "The Message is longer than the limit.",
    "no_recipients": "No Student would get the Message.",
    "message_key_conflict": "That key was used for another Message.",
}


@router.post(
    "/class-sessions/{session_id}/messages",
    status_code=201,
    response_model=MessageSentOut,
    responses=documented(401, 403, 409, 422),
    operation_id="sendMessage",
)
async def send_message(
    session_id: str,
    body: MessageIn,
    user: Annotated[authz.Principal, Depends(authz.require(messages.SEND))],
) -> MessageSentOut | JSONResponse:
    """«Send Melding» (Story 7.9, FR-40, AD-9): stores the Message with one recipient row per
    Student and tells each of them in the product and by e-mail. A repeat with the same `key`
    answers as the first and sends nothing. 422 `message_empty`, `message_too_long` (with
    `fields.max_length`) or `no_recipients`; 409 `message_key_conflict` or `class_archived`; 403
    `forbidden` as the form's read."""
    try:
        sent = await messages.send(
            user,
            _id(session_id),
            key=body.key,
            game_id=body.game_id,
            student_id=body.student_id,
            text=body.text,
            requirement_not_met=body.recipient == "requirement_not_met",
        )
    except messages.MessageRefused as refused:
        return error_response(
            refused.status, refused.code, MESSAGES[refused.code], fields=refused.fields
        )
    if sent is None:
        raise authz.Forbidden
    return MessageSentOut(
        message_id=sent.message_id, students=sent.students, sent_before=sent.sent_before
    )


class MyMessageOut(BaseModel):
    """One Message on the Student's Hjem (Story 7.10): plain text, shown as written."""

    id: uuid.UUID
    class_id: uuid.UUID
    class_name: str
    sender_name: str | None
    """The sender's name now; None when the account is gone."""
    sent_at: datetime
    text: str


class MyMessagesOut(BaseModel):
    items: list[MyMessageOut]
    """Newest first, at most 100."""


@router.get(
    "/me/messages",
    response_model=MyMessagesOut,
    responses=documented(401),
    operation_id="listMyMessages",
)
async def list_my_messages(
    user: Annotated[authz.Principal, Depends(authz.require("messages.read_own"))],
) -> MyMessagesOut:
    """The Messages written to the User, newest first (Story 7.10, FR-40, FR-73): only those
    addressed to them in a Class they are a Student in (AD-12). Read-only: there is no route by
    which a Student writes, replies to or forwards a Message."""
    found = await messages.my_messages(user)
    return MyMessagesOut(
        items=[
            MyMessageOut(
                id=m.id,
                class_id=m.class_id,
                class_name=m.class_name,
                sender_name=m.sender_name,
                sent_at=m.sent_at,
                text=m.text,
            )
            for m in found
        ]
    )


class SentMessageOut(BaseModel):
    """One Message in «Meldinger» (Story 7.10): its recipient, sender, time and reach."""

    id: uuid.UUID
    kind: Literal["student", "class_game", "class_session", "list", "requirement_not_met"]
    game_id: uuid.UUID | None
    game_number: int | None
    """The Class game it was written to, or from (a Student's title)."""
    student_id: uuid.UUID | None
    student_name: str | None
    """The Student's name while they are a registered Student of the Class; else None."""
    sender_name: str | None
    sent_at: datetime
    students: int
    """The Students it went to."""
    text: str


class SentMessagesOut(BaseModel):
    class_session_id: uuid.UUID
    class_id: uuid.UUID
    class_name: str
    session_number: int
    items: list[SentMessageOut]
    """Newest first, at most 200."""


@router.get(
    "/class-sessions/{session_id}/messages",
    response_model=SentMessagesOut,
    responses=documented(401, 403),
    operation_id="listSentMessages",
)
async def list_sent_messages(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require(messages.READ_SENT))],
) -> SentMessagesOut:
    """«Meldinger» (Story 7.10): every Message of the Class session, newest first, with its
    recipient, sender, time and the number of Students it went to. 403 `forbidden`, one answer,
    for anyone who is not staff of the Class and for a Class session that does not exist."""
    found = await messages.sent_messages(user, _id(session_id))
    if found is None:
        raise authz.Forbidden
    return SentMessagesOut(
        class_session_id=found.session.id,
        class_id=found.session.class_id,
        class_name=found.session.class_name,
        session_number=found.session.number,
        items=[
            SentMessageOut(
                id=m.id,
                kind=m.kind.value,
                game_id=m.game_id,
                game_number=m.game_number,
                student_id=m.student_id,
                student_name=m.student_name,
                sender_name=m.sender_name,
                sent_at=m.sent_at,
                students=m.students,
                text=m.text,
            )
            for m in found.items
        ],
    )
