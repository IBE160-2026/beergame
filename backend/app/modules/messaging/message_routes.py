"""The Meldingsskjema's endpoints (Story 7.9, FR-40, AD-9, AD-12): the form of a Message to a
Student, a Class game or a whole Class session, and its send.

- `GET /api/class-sessions/{id}/messages/form?game_id=&student_id=`: whom the Message goes to,
  how many Students that is now and how many Messages went to the same recipient before.
- `POST /api/class-sessions/{id}/messages`: «Send Melding», with a client-made `key`; a repeated
  request answers as the first did and sends nothing.

The recipient comes from the params: a Student when `student_id` is given (a `game_id` then only
names the game in the title), a Class game when only `game_id` is, else the whole Class session.
Anyone who is not staff of the Class, a Class session that does not exist and a recipient outside
it all answer the same 403 `forbidden` (FR-5). There is no route by which a Student writes.
"""

import uuid
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


class MessageFormOut(BaseModel):
    """What the Meldingsskjema shows before a send (UX-DR46)."""

    kind: Literal["student", "class_game", "class_session"]
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


class MessageIn(BaseModel):
    key: uuid.UUID
    """Made by the client once per text: a repeat with the same key sends nothing new."""
    game_id: uuid.UUID | None = None
    student_id: uuid.UUID | None = None
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
) -> MessageFormOut:
    """The Meldingsskjema's recipient (Story 7.9): its title's parts, the Students it reaches now,
    the earlier Messages to it and the length limit. 403 `forbidden`, one answer, for anyone who
    is not staff of the Class and for a Class session, game or Student outside it (FR-5)."""
    found = await messages.message_form(
        user, _id(session_id), game_id=_optional_id(game_id), student_id=_optional_id(student_id)
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
