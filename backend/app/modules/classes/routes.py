"""`/api/classes`: the Lecturer's Classes (Story 4.1, FR-5, FR-6, AD-12), and under
`/api/classes/enrolled` the Classes a Student is in (Story 4.5)."""

import uuid
from typing import Annotated
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response

from app.modules.classes import service
from app.modules.classes.schemas import (
    ClassIn,
    ClassListOut,
    ClassOut,
    EnrolledClassListOut,
    EnrolledClassOut,
    InstitutionChoicesOut,
    InvalidClass,
    InvitationSummaryOut,
    RegistrationsOut,
    ReminderIn,
    ReminderOut,
    RosterSendIn,
    RosterSendOut,
)
from app.modules.identity import service as identity
from app.platform import auth, authz
from app.platform.config import get_settings
from app.platform.errors import documented, error_response

router = APIRouter(prefix="/api/classes", tags=["classes"])


@router.get(
    "",
    response_model=ClassListOut,
    responses=documented(401, 403),
    operation_id="listClasses",
)
async def list_classes(
    user: Annotated[authz.Principal, Depends(authz.require("classes.read"))],
) -> Response:
    """The Classes the User is staff of, by name: «Klassene dine» on the Lærerhjem."""
    return JSONResponse((await service.list_classes(user)).model_dump(mode="json"))


@router.post(
    "",
    status_code=201,
    response_model=ClassOut,
    responses=documented(401, 403, 422),
    operation_id="createClass",
)
async def create_class(
    body: ClassIn,
    user: Annotated[authz.Principal, Depends(authz.require("classes.create"))],
) -> Response:
    """Create a Class with the User as its owner (FR-6). A refused field answers 422
    `invalid_request` with every refused field in `fields`, and nothing is stored."""
    try:
        created = await service.create_class(user, body, now=auth.utcnow())
    except InvalidClass as error:
        return error_response(422, "invalid_request", "The Class is not valid.", error.fields)
    return JSONResponse(created.model_dump(mode="json"), status_code=201)


# Declared before `/{class_id}`, so the path is never read as a Class id.
@router.get(
    "/institutions",
    response_model=InstitutionChoicesOut,
    responses=documented(401, 403),
    operation_id="listClassInstitutions",
)
async def list_institutions(
    _: Annotated[authz.Principal, Depends(authz.require("classes.create"))],
) -> Response:
    """The Institutions a new Class may belong to, by name."""
    return JSONResponse((await service.institution_choices()).model_dump(mode="json"))


@router.get(
    "/enrolled",
    response_model=EnrolledClassListOut,
    responses=documented(401),
    operation_id="listEnrolledClasses",
)
async def list_enrolled_classes(
    user: Annotated[authz.Principal, Depends(authz.require("classes.read_enrolled"))],
) -> Response:
    """The Classes the User is a Student in, by name (Story 4.5): Hjem names them. Empty for a
    User on no Roster."""
    return JSONResponse((await service.enrolled_classes(user)).model_dump(mode="json"))


@router.get(
    "/enrolled/{class_id}",
    response_model=EnrolledClassOut,
    responses=documented(401, 403),
    operation_id="getEnrolledClass",
)
async def get_enrolled_class(
    class_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("classes.read_enrolled"))],
) -> Response:
    """One Class the User is a Student in. Another Class, one whose Roster no longer holds the
    User's address, one that does not exist and an id that is not one all answer the same 403
    `forbidden` (FR-5, FR-7)."""
    found = await service.enrolled_class(user, _class_id(class_id))
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.get(
    "/{class_id}",
    response_model=ClassOut,
    responses=documented(401, 403),
    operation_id="getClass",
)
async def get_class(
    class_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("classes.read"))],
) -> Response:
    """One Class. A Class the User is not staff of, one that does not exist and an id that is not
    one all answer the same 403 `forbidden` (FR-5)."""
    try:
        parsed = uuid.UUID(class_id)
    except ValueError:
        raise authz.Forbidden from None
    found = await service.get_class(user, parsed)
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


def _class_id(class_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(class_id)
    except ValueError:
        raise authz.Forbidden from None


# The staged Roster upload of a Class (Story 4.2, FR-7). The file travels as the raw request body
# with its name, percent-encoded, in `X-File-Name`; it is read into memory up to
# `ROSTER_MAX_FILE_MB` and never stored. Every refusal of the file is one code,
# `roster_unreadable`, and stages nothing.

FILE_NAME_HEADER = "X-File-Name"
FILE_NAME_MAX = 255
UNREADABLE = "roster_unreadable"


async def _capped_body(request: Request, limit: int) -> bytes | None:
    """The body, or None as soon as it is longer than `limit` bytes."""
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit:
        return None
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > limit:
            return None
    return bytes(body)


def _file_name(request: Request) -> str:
    """The file's own name, without any path, trimmed; "" when none was sent."""
    raw = unquote(request.headers.get(FILE_NAME_HEADER, ""), errors="strict")
    name = raw.replace("\\", "/").rsplit("/", 1)[-1].strip()
    if any(not ch.isprintable() for ch in name):
        return ""
    if len(name) > FILE_NAME_MAX:  # cut the stem, so the type stays readable
        stem, dot, ext = name.rpartition(".")
        keep = FILE_NAME_MAX - len(ext) - 1
        name = stem[:keep] + dot + ext if dot and keep > 0 else name[:FILE_NAME_MAX]
    return name


def _unreadable() -> Response:
    return error_response(422, UNREADABLE, "The file cannot be read as a Roster.")


@router.post(
    "/{class_id}/roster-upload",
    status_code=201,
    response_model=identity.RosterUploadOut,
    responses=documented(401, 403, 422),
    operation_id="uploadRoster",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
            },
        },
        "parameters": [
            {
                "name": FILE_NAME_HEADER,
                "in": "header",
                "required": True,
                "schema": {"type": "string"},
                "description": "The file's name, percent-encoded; .xlsx or .csv.",
            }
        ],
    },
)
async def upload_roster(
    class_id: str,
    request: Request,
    user: Annotated[authz.Principal, Depends(authz.require("classes.manage"))],
) -> Response:
    """Read a Roster file (.xlsx or .csv) in memory and stage its rows for the Class, replacing
    any earlier staged upload. A file that cannot be used answers 422 `roster_unreadable` and
    stages nothing (the earlier staged upload stays)."""
    parsed_id = _class_id(class_id)
    # The Class first: a User who may not manage it is refused before the body is read.
    if not await service.may_manage(user, parsed_id):
        raise authz.Forbidden
    limit = get_settings().roster_max_file_mb * 1024 * 1024
    data = await _capped_body(request, limit)
    try:
        name = _file_name(request)
    except UnicodeDecodeError:
        name = ""
    if data is None or not name:
        return _unreadable()
    try:
        staged = await service.upload_roster(user, parsed_id, name, data, now=auth.utcnow())
    except identity.RosterUnreadable:
        return _unreadable()
    if staged is None:
        raise authz.Forbidden
    return JSONResponse(staged.model_dump(mode="json"), status_code=201)


@router.post(
    "/{class_id}/roster-paste",
    status_code=201,
    response_model=identity.RosterUploadOut,
    responses=documented(401, 403, 422),
    operation_id="pasteRoster",
)
async def paste_roster(
    class_id: str,
    body: identity.RosterPasteIn,
    user: Annotated[authz.Principal, Depends(authz.require("classes.manage"))],
) -> Response:
    """«Lim inn adresser i stedet» (Story 4.3): split the text on line breaks, commas, semicolons
    and whitespace and stage the pieces as one-column rows, replacing any earlier staged upload;
    `Navn <adresse>` is read as the address. Text over the size limit or with more addresses than
    the row limit answers 422 `roster_paste_too_long` and stages nothing."""
    try:
        staged = await service.paste_roster(user, _class_id(class_id), body.text, now=auth.utcnow())
    except identity.RosterPasteTooLong:
        return error_response(422, "roster_paste_too_long", "The pasted text is too long.")
    if staged is None:
        raise authz.Forbidden
    return JSONResponse(staged.model_dump(mode="json"), status_code=201)


@router.get(
    "/{class_id}/roster-upload",
    response_model=identity.RosterStagingOut,
    responses=documented(401, 403),
    operation_id="getRosterUpload",
)
async def get_roster_upload(
    class_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("classes.manage"))],
) -> Response:
    """The Class's staged upload, evaluated against its chosen column; `upload` is null when
    there is none or it has expired."""
    staging = await service.roster_staging(user, _class_id(class_id), now=auth.utcnow())
    if staging is None:
        raise authz.Forbidden
    return JSONResponse(identity.RosterStagingOut(upload=staging.upload).model_dump(mode="json"))


@router.put(
    "/{class_id}/roster-upload/column",
    response_model=identity.RosterUploadOut,
    responses=documented(401, 403, 404, 422),
    operation_id="chooseRosterColumn",
)
async def choose_roster_column(
    class_id: str,
    body: identity.RosterColumnIn,
    user: Annotated[authz.Principal, Depends(authz.require("classes.manage"))],
) -> Response:
    """Choose the e-mail column; the staged rows are evaluated against it at once, from the staged
    cells. 404 `not_found` when nothing is staged (or it expired); 422 `invalid_request` with
    `fields.column = column_unknown` for a column the file does not have."""
    try:
        staging = await service.choose_roster_column(
            user, _class_id(class_id), body.column, now=auth.utcnow()
        )
    except identity.InvalidRosterColumn:
        return error_response(
            422, "invalid_request", "The file has no such column.", {"column": "column_unknown"}
        )
    if staging is None:
        raise authz.Forbidden
    if staging.upload is None:
        return error_response(404, "not_found", "Nothing is staged for the Class.")
    return JSONResponse(staging.upload.model_dump(mode="json"))


@router.delete(
    "/{class_id}/roster-upload",
    status_code=204,
    responses=documented(401, 403),
    operation_id="deleteRosterUpload",
)
async def delete_roster_upload(
    class_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("classes.manage"))],
) -> Response:
    """«Bytt fil»: delete the Class's staged upload. 204 whether or not there was one."""
    if await service.discard_roster_upload(user, _class_id(class_id)) is None:
        raise authz.Forbidden
    return Response(status_code=204)


@router.post(
    "/{class_id}/invitations",
    status_code=201,
    response_model=RosterSendOut,
    responses=documented(401, 403, 404, 422),
    operation_id="sendRosterInvitations",
)
async def send_invitations(
    class_id: str,
    body: RosterSendIn,
    user: Annotated[authz.Principal, Depends(authz.require("classes.manage"))],
) -> Response:
    """«Send N Invitasjoner» (Story 4.4): write the staged upload's valid addresses to the Roster
    and send each new address a Student Invitation valid through the `valid_days`-th day after
    today (Europe/Oslo), in one transaction; the mails leave from `worker-batch`. 404
    `not_found` when `upload_id` is not the Class's staging (sent already, replaced or expired);
    422 `nothing_to_send` when no staged row is valid; 422 `invalid_request` with
    `fields.valid_days` for a validity outside 1–60 days. Nothing changes on a refusal."""
    try:
        sent = await service.send_invitations(
            user, _class_id(class_id), body.upload_id, body.valid_days, now=auth.utcnow()
        )
    except service.NothingToSend:
        return error_response(422, "nothing_to_send", "No staged row gets an Invitation.")
    if sent is None:
        raise authz.Forbidden
    if isinstance(sent, service.Staging):
        return error_response(404, "not_found", "The staged upload is gone.")
    return JSONResponse(sent.model_dump(mode="json"), status_code=201)


@router.get(
    "/{class_id}/invitations",
    response_model=InvitationSummaryOut,
    responses=documented(401, 403),
    operation_id="getInvitationSummary",
)
async def get_invitation_summary(
    class_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("classes.manage"))],
) -> Response:
    """What became of the Class's Student Invitations (Story 4.6, FR-8): how many were sent,
    bounced, accepted and expired, computed now, and the Roster addresses whose newest Invitation
    bounced, with the bounce's class. A Class the User may not manage, one that does not exist
    and an id that is not one all answer the same 403 `forbidden`."""
    summary = await service.invitation_summary(user, _class_id(class_id), now=auth.utcnow())
    if summary is None:
        raise authz.Forbidden
    return JSONResponse(summary.model_dump(mode="json"))


@router.get(
    "/{class_id}/registrations",
    response_model=RegistrationsOut,
    responses=documented(401, 403),
    operation_id="getRegistrations",
)
async def get_registrations(
    class_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("classes.manage"))],
) -> Response:
    """«Status etter utsending» (Story 4.7, FR-9): every Roster address with its status, read now
    (registered, registered manually, asked for a new Invitation, bounced with its class, invited
    with its last valid day, unregistered), the totals and how many have not registered. A Class
    the User may not manage, one that does not exist and an id that is not one all answer the
    same 403 `forbidden`."""
    found = await service.registrations(user, _class_id(class_id), now=auth.utcnow())
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.post(
    "/{class_id}/reminders",
    status_code=201,
    response_model=ReminderOut,
    responses=documented(401, 403, 422),
    operation_id="sendReminders",
)
async def send_reminders(
    class_id: str,
    body: ReminderIn,
    user: Annotated[authz.Principal, Depends(authz.require("classes.manage"))],
) -> Response:
    """«Send påminnelse» (Story 4.7, FR-9, NFR-10): a new Invitation valid through the
    `valid_days`-th day after today (Europe/Oslo) to every address that has not registered, or
    with `roster_entry_id` to that one alone; their old links stop working. Addresses whose last
    mail bounced hard are left out and named in `left_out`. 422 `nothing_to_send` when nothing
    would be sent or left out (all registered, or the entry is registered or not on the Roster);
    422 `invalid_request` with `fields.valid_days` for a validity outside 1–60 days."""
    try:
        sent = await service.send_reminders(
            user,
            _class_id(class_id),
            body.valid_days,
            entry_id=body.roster_entry_id,
            now=auth.utcnow(),
        )
    except service.NoReminderTarget:
        return error_response(422, "nothing_to_send", "No address gets a reminder.")
    if sent is None:
        raise authz.Forbidden
    return JSONResponse(sent.model_dump(mode="json"), status_code=201)
