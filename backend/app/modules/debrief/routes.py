"""The Debrief routes (Stories 9.2, 9.3, FR-41, FR-42, AD-3, AD-12).

- `POST /api/me/class-sessions/{id}/debrief`: «Gå til Debrief» and Stegene's Debrief step open
  the Student's Debrief session (created at step 1 the first time) and answer it.
- `GET /api/debriefs/{id}`: the same Debrief session by its id.
- Step 1 (Story 9.3): `GET /api/debriefs/{id}/net-inventory` (the Student's own Netto lager),
  `GET`/`POST /api/debriefs/{id}/explanation` (their own Explanation; sent once, 409
  `explanation_exists`).
- `GET /api/debriefs/{id}/steps/{step}` (2 to 5): every step after step 1, behind the
  Explanation gate (403 `explanation_required`). Step 2 is the reveal of customer demand
  (Story 9.4), step 3 the whole chain (Story 9.5); later stories add each other step's content
  here.
- `GET /api/class-sessions/{id}/students/{user_id}/explanation`: a Student's Explanation for the
  Class's owners and Assistant lecturers (`explanations.read`).

Every Debrief route answers 403 `debrief_not_open` while the Student's Class game has not
finished and 403 `debrief_held` while the Lecturer holds the Debriefs and a Class game has not
finished, with the error envelope only: no demand series, number of Weeks or other Seats' data
(FR-14). A Class session that is not the Student's own locked one, another Student's Debrief and
an id that is not one all answer the same 403 `forbidden` (FR-5)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse, Response

from app.modules.debrief import commands, service
from app.modules.debrief.models import STEPS
from app.modules.debrief.schemas import (
    DebriefOut,
    DebriefStepOut,
    ExplanationIn,
    ExplanationOut,
    MyExplanationOut,
    NetInventoryOut,
)
from app.platform import authz
from app.platform.errors import documented, error_response

router = APIRouter(prefix="/api", tags=["debrief"])

MESSAGES = {
    "debrief_not_open": "The Debrief opens when the Class game has finished.",
    "debrief_held": "The Debrief opens when all Class games have finished.",
}

OWN = Annotated[authz.Principal, Depends(authz.require("debriefs.own"))]


def _id(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise authz.Forbidden from None


def _refused(refused: service.NotAvailable) -> Response:
    return error_response(403, refused.code, MESSAGES[refused.code])


@router.post(
    "/me/class-sessions/{session_id}/debrief",
    response_model=DebriefOut,
    responses=documented(401, 403),
    operation_id="openMyDebrief",
)
async def open_my_debrief(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("debriefs.own"))],
) -> Response:
    """Opens the Student's Debrief in the Class session (FR-42): the Debrief session of their
    game, created with its step pointer at step 1 if none exists, and answered as it stands.
    403 `debrief_not_open`, `debrief_held` or `forbidden`."""
    try:
        found = await service.open_mine(user, _id(session_id))
    except service.NotAvailable as refused:
        return _refused(refused)
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.get(
    "/debriefs/{debrief_id}",
    response_model=DebriefOut,
    responses=documented(401, 403),
    operation_id="getMyDebrief",
)
async def get_my_debrief(
    debrief_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("debriefs.own"))],
) -> Response:
    """The Student's own Debrief session by id. 403 `debrief_not_open`, `debrief_held` or
    `forbidden`, as above."""
    try:
        found = await service.mine(user, _id(debrief_id))
    except service.NotAvailable as refused:
        return _refused(refused)
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


async def _answer(read, status: int = 200) -> Response:
    """Runs a read or write on the Student's own Debrief and answers it, or its refusal."""
    try:
        found = await read
    except service.NotAvailable as refused:
        return _refused(refused)
    except service.ExplanationRequired:
        return error_response(
            403, "explanation_required", "Send your Explanation before this step."
        )
    except service.InvalidExplanation as invalid:
        return error_response(
            422,
            "validation_error",
            "The Explanation is empty or too long.",
            {"text": invalid.reason},
        )
    except commands.ExplanationExists:
        return error_response(409, "explanation_exists", "Your Explanation is already sent.")
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"), status_code=status)


@router.get(
    "/debriefs/{debrief_id}/net-inventory",
    response_model=NetInventoryOut,
    responses=documented(401, 403),
    operation_id="getMyNetInventory",
)
async def get_my_net_inventory(debrief_id: str, user: OWN) -> Response:
    """«Ditt netto lager, hele spillet» (Story 9.3, step 1): the Netto lager of the Student's own
    Seat in every Uke, oldest first. Never demand or another Seat (FR-14)."""
    return await _answer(service.own_net_inventory(user, _id(debrief_id)))


@router.get(
    "/debriefs/{debrief_id}/explanation",
    response_model=MyExplanationOut,
    responses=documented(401, 403),
    operation_id="getMyExplanation",
)
async def get_my_explanation(debrief_id: str, user: OWN) -> Response:
    """The Student's own Explanation, `explanation` null before it is sent."""
    return await _answer(service.own_explanation(user, _id(debrief_id)))


@router.post(
    "/debriefs/{debrief_id}/explanation",
    status_code=201,
    response_model=ExplanationOut,
    responses=documented(401, 403, 409, 422),
    operation_id="sendMyExplanation",
)
async def send_my_explanation(debrief_id: str, body: ExplanationIn, user: OWN) -> Response:
    """«Send Forklaring» (FR-41): stores the Explanation once, as typed, and records the
    `explanation` step. 409 `explanation_exists` when it is sent already (unchanged), 422
    `validation_error` for white space only or more than 5000 characters."""
    return await _answer(service.save_mine(user, _id(debrief_id), body.text), status=201)


@router.get(
    "/debriefs/{debrief_id}/steps/{step}",
    response_model=DebriefStepOut,
    responses=documented(401, 403),
    operation_id="getDebriefStep",
)
async def get_debrief_step(
    debrief_id: str,
    step: Annotated[int, Path(ge=2, le=STEPS)],
    user: OWN,
) -> Response:
    """A Debrief step after step 1 (FR-41, FR-43): 403 `explanation_required` until the Student's
    Explanation is saved, checked here and not only in the web app. Step 2 carries `reveal`: the
    heading rendered from the demand series and Kundene, Ordre inn and Din ordre per Uke of the
    Student's own Seat (Story 9.4, FR-44). Step 3 carries `chain`: every Role's Orders and Week
    states, Fabrikk first, with Forsterkning and the first large Order from the stored facts set
    (Story 9.5, FR-44, AD-7)."""
    return await _answer(service.step(user, _id(debrief_id), step))


@router.get(
    "/class-sessions/{session_id}/students/{student_id}/explanation",
    response_model=ExplanationOut,
    responses=documented(401, 403, 404),
    operation_id="getStudentExplanation",
)
async def get_student_explanation(
    session_id: str,
    student_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("explanations.read"))],
) -> Response:
    """A Student's Explanation for the Class's owners and Assistant lecturers (AD-12). 404
    `not_found` when the Student has not sent one; 403 `forbidden` for every other caller."""
    try:
        found = await service.staff_explanation(user, _id(session_id), _id(student_id))
    except service.NoExplanation:
        return error_response(404, "not_found", "No Explanation is sent.")
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))
