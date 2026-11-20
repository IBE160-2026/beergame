"""Class sessions (Story 5.1, FR-5, FR-11, AD-12): created under their Class
(`/api/classes/{class_id}/class-sessions`) and read and saved by id (`/api/class-sessions/{id}`).

A Class or Class session the User may not reach, one that does not exist and an id that is not
one all answer the same 403 `forbidden` (FR-5). A change to a Class session of an archived Class
answers 409 `class_archived` (`classes.service.ClassArchived`, mapped in `main.py`).

Story 5.2 adds the four dates to the save, the Student's read `/api/me/class-sessions` and the
Lærerhjem's read `/api/lecturer-home/class-sessions`. Story 5.3 adds the Game settings to the
save and the check of a draft, `/api/class-sessions/{id}/settings-check`. Story 5.4 adds the
Demand pattern and seed to both and the staff's read of the series,
`/api/class-sessions/{id}/demand-series`. Story 5.5 adds the Effort level and Debrief mode to the
save and the offered levels, AI player descriptions and provider flag to the read. Story 5.6 adds
the Lab hours, `/api/class-sessions/{id}/lab-hours[/{lab_hour_id}]`, saved on their own. Story
5.7 adds the obligatory mark, its required share and the Inactivity limit to the save. Story 5.8
adds the allocation draft, `/api/class-sessions/{id}/allocation[/redraw]`, and Story 5.9 its
confirmation, `/api/class-sessions/{id}/allocation/confirm`, and Story 5.10 moving and swapping
Students in it, `/api/class-sessions/{id}/allocation/move`."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response

from app.modules.sessions import service
from app.modules.sessions.schemas import (
    AllocationConfirmIn,
    AllocationMoveIn,
    AllocationOut,
    ClassSessionListOut,
    ClassSessionOut,
    ClassSessionSaveIn,
    DemandSeriesOut,
    EnrolledSessionListOut,
    LabHourIn,
    LabHourOut,
    LecturerOverviewOut,
    SettingsCheckIn,
    SettingsCheckOut,
)
from app.platform import auth, authz
from app.platform.errors import documented, error_response

router = APIRouter(prefix="/api", tags=["sessions"])

LLM_UNAVAILABLE = "llm_unavailable"


def _id(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise authz.Forbidden from None


@router.post(
    "/classes/{class_id}/class-sessions",
    status_code=201,
    response_model=ClassSessionOut,
    responses=documented(401, 403, 409),
    operation_id="createClassSession",
)
async def create_class_session(
    class_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.manage"))],
) -> Response:
    """«Lag Klasseøkt»: a Class session filled in with the Classic defaults (FR-11). When no model
    config is pinned as the default, it gets Rule-based players and `llm_unavailable` says why."""
    created = await service.create_session(user, _id(class_id), now=auth.utcnow())
    if created is None:
        raise authz.Forbidden
    return JSONResponse(created.model_dump(mode="json"), status_code=201)


@router.get(
    "/classes/{class_id}/class-sessions",
    response_model=ClassSessionListOut,
    responses=documented(401, 403),
    operation_id="listClassSessions",
)
async def list_class_sessions(
    class_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.read"))],
) -> Response:
    """The Class's sessions, newest first, for the Klasse page."""
    found = await service.list_sessions(user, _id(class_id))
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.get(
    "/class-sessions/{session_id}",
    response_model=ClassSessionOut,
    responses=documented(401, 403),
    operation_id="getClassSession",
)
async def get_class_session(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.read"))],
) -> Response:
    """One Class session, for the Klasseøkt screen. Its Class's Assistant lecturers read it too."""
    found = await service.get_session(user, _id(session_id))
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.put(
    "/class-sessions/{session_id}",
    response_model=ClassSessionOut,
    responses=documented(401, 403, 409, 422),
    operation_id="saveClassSession",
)
async def save_class_session(
    session_id: str,
    body: ClassSessionSaveIn,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.manage"))],
) -> Response:
    """«Lagre Klasseøkt»: saves the Class session as it stands. LLM players while no model config
    is pinned as the default answer 409 `llm_unavailable`, and nothing changes.

    With `dates` the four dates are replaced (FR-18). `fields` names each date in question:
    422 `invalid_dates` (`past`, `order` for the later date of a pair out of order, `before` for
    the earlier one when only it changed, `required` once locked), 409 `deadline_passed`
    (`passed`). Dates count to the whole minute.

    `effort_level` and `debrief_mode` (FR-16, FR-78), left out, keep their values. With LLM
    players a changed Effort level the model config does not offer answers 422
    `invalid_effort_level` (`{"effort_level": "not_offered"}`); with Rule-based players no level
    is in force and a sent one is ignored. Once the Start date has passed, a changed AI mode,
    Effort level or Debrief mode answers 409 `session_locked`, `fields` naming each.

    With `game_settings` (the editable settings, laid over the stored ones; `demand` and
    `demand_seed` too) the engine judges the settings (FR-12, FR-13): 422 `invalid_settings` with
    `fields` mapping each setting (`demand.<field>` inside the Demand pattern) to
    `{code, minimum, maximum, decimal_places}`. Once locked, changed settings answer 409
    `session_locked` (`{"game_settings": "locked"}`).

    `game_settings.capacity` (Story 5.15) is `{role: units}` or null: one Role or every Role
    capped per Week, `capacity.<role>` from 1 to 100. While `FEATURE_CAPACITY` is off a
    non-empty capacity answers 422 `feature_disabled` (`{"capacity": "feature_disabled"}`).

    `game_settings.info_visibility` (Story 5.16) is `{upstream, downstream}`, two booleans that
    let each Seat see its neighbour's inventory and backlog; anything else is `info_visibility`
    `invalid`. While `FEATURE_INFO_VISIBILITY` is off a view switched on answers 422
    `feature_disabled` (`{"info_visibility": "feature_disabled"}`).

    `obligatory`, `required_share_percent` and `inactivity_limit_hours` (Story 5.7, FR-17,
    FR-36), left out, keep their values. A changed share outside 1 to 100 or Inactivity limit
    under 20 hours answers 422 `invalid_session_values` (`out_of_range`, `below_minimum`); once
    locked a changed one answers 409 `session_locked`. Switching the mark on tells each
    registered Student through the day's digest mail."""
    try:
        saved = await service.save_session(
            user,
            _id(session_id),
            body.ai_mode,
            now=auth.utcnow(),
            effort_level=body.effort_level,
            debrief_mode=body.debrief_mode,
            dates=body.dates,
            game_settings=body.game_settings,
            obligatory=body.obligatory,
            required_share_percent=body.required_share_percent,
            inactivity_limit_hours=body.inactivity_limit_hours,
        )
    except service.InvalidSettings as refused:
        return error_response(
            422,
            refused.code,
            "The Game settings break the engine's rules.",
            {field: problem.model_dump() for field, problem in refused.problems.items()},
        )
    except service.LlmUnavailableError:
        return error_response(
            409, LLM_UNAVAILABLE, "LLM players are unavailable until a default model is pinned."
        )
    except service.InvalidDates as refused:
        return error_response(422, refused.code, "The dates break a rule.", refused.fields)
    except service.InvalidSessionValues as refused:
        return error_response(
            422, refused.code, "The share or the Inactivity limit breaks a rule.", refused.fields
        )
    except service.InvalidEffortLevel as refused:
        return error_response(
            422, refused.code, "The model config offers no such Effort level.", refused.fields
        )
    except service.FeatureDisabled as refused:
        return error_response(422, refused.code, "This setting is switched off.", refused.fields)
    except (service.DeadlinePassed, service.SessionLocked) as refused:
        return error_response(409, refused.code, "This can no longer change.", refused.fields)
    if saved is None:
        raise authz.Forbidden
    return JSONResponse(saved.model_dump(mode="json"))


def _lab_hour_refused(refused: service.InvalidLabHour | service.LabHourEnded) -> Response:
    if isinstance(refused, service.LabHourEnded):
        return error_response(409, refused.code, "The Lab hour has ended.")
    return error_response(422, refused.code, "The Lab hour breaks a rule.", refused.fields)


@router.post(
    "/class-sessions/{session_id}/lab-hours",
    status_code=201,
    response_model=LabHourOut,
    responses=documented(401, 403, 409, 422),
    operation_id="addLabHour",
)
async def add_lab_hour(
    session_id: str,
    body: LabHourIn,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.manage"))],
) -> Response:
    """«Legg til Labtime» (Story 5.6, FR-19): stores the Lab hour at once and tells each
    registered Student through the day's digest mail. The Start-date lock does not apply.

    A refusal is 422 `invalid_lab_hour` with `fields`: `place` `required` or `too_long` (over 120
    characters); `ends_at` `not_after_start`, `too_long` (over 12 hours after the start) or
    `past`. Times count to the whole minute."""
    try:
        added = await service.add_lab_hour(user, _id(session_id), body, now=auth.utcnow())
    except service.InvalidLabHour as refused:
        return _lab_hour_refused(refused)
    if added is None:
        raise authz.Forbidden
    return JSONResponse(added.model_dump(mode="json"), status_code=201)


@router.put(
    "/class-sessions/{session_id}/lab-hours/{lab_hour_id}",
    response_model=LabHourOut,
    responses=documented(401, 403, 409, 422),
    operation_id="changeLabHour",
)
async def change_lab_hour(
    session_id: str,
    lab_hour_id: str,
    body: LabHourIn,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.manage"))],
) -> Response:
    """Changes a Lab hour and tells each registered Student; unchanged values tell nobody. A Lab
    hour that has ended answers 409 `lab_hour_ended`; the other refusals are those of adding one
    (422 `invalid_lab_hour`)."""
    try:
        changed = await service.change_lab_hour(
            user, _id(session_id), _id(lab_hour_id), body, now=auth.utcnow()
        )
    except (service.InvalidLabHour, service.LabHourEnded) as refused:
        return _lab_hour_refused(refused)
    if changed is None:
        raise authz.Forbidden
    return JSONResponse(changed.model_dump(mode="json"))


@router.delete(
    "/class-sessions/{session_id}/lab-hours/{lab_hour_id}",
    status_code=204,
    responses=documented(401, 403, 409),
    operation_id="removeLabHour",
)
async def remove_lab_hour(
    session_id: str,
    lab_hour_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.manage"))],
) -> Response:
    """Removes a Lab hour and tells each registered Student it is cancelled. A Lab hour that has
    ended answers 409 `lab_hour_ended`."""
    try:
        removed = await service.remove_lab_hour(
            user, _id(session_id), _id(lab_hour_id), now=auth.utcnow()
        )
    except service.LabHourEnded as refused:
        return _lab_hour_refused(refused)
    if not removed:
        raise authz.Forbidden
    return Response(status_code=204)


@router.get(
    "/class-sessions/{session_id}/allocation",
    response_model=AllocationOut,
    responses=documented(401, 403),
    operation_id="getAllocation",
)
async def get_allocation(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.read"))],
) -> Response:
    """The «Fordeling» block (Story 5.8, FR-20): the registered Students, those not in the draft,
    and the stored draft (None until one is drawn) with the Students' names read now. For the
    Class's staff, Assistant lecturers too."""
    found = await service.allocation_of(user, _id(session_id))
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


async def _draw(user: authz.Principal, session_id: str, *, again: bool) -> Response:
    try:
        drawn = await service.draw_allocation(user, _id(session_id), now=auth.utcnow(), again=again)
    except service.SessionLocked as refused:
        return error_response(409, refused.code, "The Class session has started.", refused.fields)
    except service.AllocationConfirmed as refused:
        return error_response(
            409, refused.code, "The allocation is confirmed; it is not drawn again.", refused.fields
        )
    if drawn is None:
        raise authz.Forbidden
    return JSONResponse(drawn.model_dump(mode="json"))


@router.post(
    "/class-sessions/{session_id}/allocation",
    response_model=AllocationOut,
    responses=documented(401, 403, 409),
    operation_id="openAllocation",
)
async def open_allocation(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.manage"))],
) -> Response:
    """Opening «Fordeling»: the stored draft unchanged, or, when none is stored, a draft drawn at
    random from the registered Students in groups of four with a random Role each. With no
    registered Student nothing is stored. No Game or Seat is created and no Student is told.
    Once the Start date has passed a stored draft is still returned, and a draw answers 409
    `session_locked` (`{"allocation": "locked"}`). An archived Class answers 409
    `class_archived`."""
    return await _draw(user, session_id, again=False)


@router.post(
    "/class-sessions/{session_id}/allocation/redraw",
    response_model=AllocationOut,
    responses=documented(401, 403, 409),
    operation_id="redrawAllocation",
)
async def redraw_allocation(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.manage"))],
) -> Response:
    """«Kjør fordeling på nytt»: a new seed and a new draft under a new id, revision 1. The
    refusals are those of opening it, and 409 `allocation_confirmed` (`{"allocation":
    "confirmed"}`) once the allocation is confirmed."""
    return await _draw(user, session_id, again=True)


@router.post(
    "/class-sessions/{session_id}/allocation/confirm",
    response_model=AllocationOut,
    responses=documented(401, 403, 409, 422),
    operation_id="confirmAllocation",
)
async def confirm_allocation(
    session_id: str,
    body: AllocationConfirmIn,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.manage"))],
) -> Response:
    """«Bekreft fordeling» (Story 5.9, FR-20): commits the draft named by `draft_id` and
    `revision`, and nothing else: one Class game per group and one Seat per Student, and each
    Student is told through the day's digest mail. Pressing it again changes nothing.

    409 `allocation_changed` commits no Game: `{"draft": "changed"}` when the draft is no longer
    the current one (drawn again or changed), `{"draft": "students_removed"}` when Students in it
    have left the Roster, whose Seats the draft now leaves free under a raised revision. 409
    `session_locked` (`{"allocation": "locked"}`) once the Start date has passed; 409
    `class_archived` for an archived Class."""
    try:
        confirmed = await service.confirm_allocation(user, _id(session_id), body, now=auth.utcnow())
    except service.SessionLocked as refused:
        return error_response(409, refused.code, "The Class session has started.", refused.fields)
    except service.AllocationChanged as refused:
        return error_response(
            409, refused.code, "The allocation is not the one confirmed.", refused.fields
        )
    if confirmed is None:
        raise authz.Forbidden
    return JSONResponse(confirmed.model_dump(mode="json"))


@router.post(
    "/class-sessions/{session_id}/allocation/move",
    response_model=AllocationOut,
    responses=documented(401, 403, 404, 409, 422),
    operation_id="moveInAllocation",
)
async def move_in_allocation(
    session_id: str,
    body: AllocationMoveIn,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.manage"))],
) -> Response:
    """Move a Student to a free Seat, or swap two (Story 5.10, FR-20), in the draft named by
    `draft_id` and `revision`: the Student of `from_game`/`from_role` takes
    `to_game`/`to_role`, and a Student there takes the first Seat. The draft keeps its id and
    its revision rises by one. Once the allocation is confirmed the Class games change in the
    same transaction and the Students who moved are told through the day's digest mail.

    409 `allocation_changed` (`{"draft": "changed"}`) when the draft is no longer the current
    one; 422 `invalid_move` with `fields` `{"to": "same"}`, `{"from"|"to": "unknown"}`,
    `{"from": "empty"}` or `{"from": "last_student"}`; 409 `session_locked` (`{"allocation":
    "locked"}`) once the Start date has passed; 409 `class_archived` for an archived Class.
    A confirmed allocation's Games refusing the move answer the command's code (such as 409
    `game_already_started`). Nothing is committed on any refusal."""
    try:
        moved = await service.move_allocation(user, _id(session_id), body, now=auth.utcnow())
    except service.SessionLocked as refused:
        return error_response(409, refused.code, "The Class session has started.", refused.fields)
    except service.AllocationChanged as refused:
        return error_response(
            409, refused.code, "The allocation is not the one shown.", refused.fields
        )
    except service.InvalidMove as refused:
        return error_response(422, refused.code, "The move does not fit the draft.", refused.fields)
    except service.SeatCommandRefused as refused:
        return error_response(
            refused.status, refused.code, "The Class games refused the move.", refused.fields
        )
    if moved is None:
        raise authz.Forbidden
    return JSONResponse(moved.model_dump(mode="json"))


@router.post(
    "/class-sessions/{session_id}/settings-check",
    response_model=SettingsCheckOut,
    responses=documented(401, 403, 409),
    operation_id="checkClassSessionSettings",
)
async def check_class_session_settings(
    session_id: str,
    body: SettingsCheckIn,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.manage"))],
) -> Response:
    """The engine's errors and warnings on a draft of the Game settings, as the Lecturer leaves a
    field (FR-12, AD-1). Stores nothing. Once locked it answers 409 `session_locked`."""
    try:
        found = await service.check_settings(
            user, _id(session_id), body.game_settings, now=auth.utcnow()
        )
    except service.SessionLocked as refused:
        return error_response(409, refused.code, "This can no longer change.", refused.fields)
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.get(
    "/class-sessions/{session_id}/demand-series",
    response_model=DemandSeriesOut,
    responses=documented(401, 403),
    operation_id="getClassSessionDemandSeries",
)
async def get_class_session_demand_series(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.read"))],
) -> Response:
    """The customer demand Week by Week, materialised by the engine from the stored Demand
    pattern and seed (FR-13, AD-1). For the Class's staff; the same settings and seed always give
    the same series."""
    found = await service.demand_series_of(user, _id(session_id))
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.get(
    "/me/class-sessions",
    response_model=EnrolledSessionListOut,
    responses=documented(401),
    operation_id="listMyClassSessions",
)
async def list_my_class_sessions(
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.read_enrolled"))],
) -> Response:
    """The Class sessions of the Classes the User is a Student in: dates and the next deadline,
    never the Game settings (FR-18). Empty for a User who is no Student."""
    found = await service.enrolled_sessions(user)
    return JSONResponse(found.model_dump(mode="json"))


@router.get(
    "/lecturer-home/class-sessions",
    response_model=LecturerOverviewOut,
    responses=documented(401, 403),
    operation_id="lecturerHomeClassSessions",
)
async def lecturer_home_class_sessions(
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.read"))],
) -> Response:
    """The Lærerhjem's «Venter» and «Neste frist» over the User's Classes that are not archived
    (UX-DR56)."""
    found = await service.lecturer_overview(user)
    return JSONResponse(found.model_dump(mode="json"))
