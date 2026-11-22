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
Students in it, `/api/class-sessions/{id}/allocation/move`. Story 5.17 adds the allocation method
to the save and the Student's «Velg spill og sete», `/api/me/class-sessions/{id}/seat-choice`.
Story 5.18 adds making one from an earlier one, `/api/classes/{class_id}/class-sessions/copy`
with its sources `…/copy-sources`. Story 6.1 adds the Student's game card and Stegene to
`/api/me/class-sessions` and the Student's own game, `/api/me/games/{game_id}`."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, Response

from app.engine.settings import Role
from app.modules.sessions import adjustments, control_tests, overview, service
from app.modules.sessions.schemas import (
    AdjustmentIn,
    AllocationConfirmIn,
    AllocationMoveIn,
    AllocationOut,
    BelievabilityIn,
    BelievabilityOut,
    ClassOverviewOut,
    ClassSessionListOut,
    ClassSessionOut,
    ClassSessionSaveIn,
    ControlTestIn,
    ControlTestOut,
    ControlTestsOut,
    CopyIn,
    CopySourceListOut,
    DemandSeriesOut,
    EnrolledSessionListOut,
    FilledSeatsOut,
    FillSeatsIn,
    GameInsightOut,
    GameResultOut,
    GameWeeksOut,
    InRoomIn,
    LabHourIn,
    LabHourOut,
    LecturerOverviewOut,
    OrderIn,
    PlayOut,
    ReplayScenarioCheckIn,
    SeatChoiceIn,
    SeatChoiceOut,
    SettingsCheckIn,
    SettingsCheckOut,
    StaffPauseIn,
    StartedGamesOut,
    StartedTestGameOut,
    StartGamesIn,
    StartGamesOut,
    StudentGameOut,
    StudentPageOut,
    TestGameIn,
    TimeProposalIn,
    WaitedForSeatsOut,
    WallAggregatesOut,
    WallCells,
    WallStatus,
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


RERUN_OFF = "Making a Class session from an earlier one is switched off."


@router.get(
    "/classes/{class_id}/class-sessions/copy-sources",
    response_model=CopySourceListOut,
    responses=documented(401, 403, 422),
    operation_id="listClassSessionCopySources",
)
async def list_copy_sources(
    class_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.manage"))],
) -> Response:
    """The Class sessions a Faglærer may copy into this Class (Story 5.18, FR-66, AD-12): every
    session of every Class they are staff of, archived Classes included, newest first. While
    `FEATURE_RERUN` is off it answers 422 `feature_disabled` (`{"rerun": "feature_disabled"}`)."""
    try:
        found = await service.copy_sources(user, _id(class_id))
    except service.FeatureDisabled as refused:
        return error_response(422, refused.code, RERUN_OFF, refused.fields)
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.post(
    "/classes/{class_id}/class-sessions/copy",
    status_code=201,
    response_model=ClassSessionOut,
    responses=documented(401, 403, 409, 422),
    operation_id="copyClassSession",
)
async def copy_class_session(
    class_id: str,
    body: CopyIn,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.manage"))],
) -> Response:
    """«Lag kopi» (Story 5.18, FR-66): a new Class session in this Class with the Game settings,
    AI mode, Effort level, Debrief mode and Inactivity limit of `source_id`, a session of any Class
    the User is staff of. It takes the active default model config; an Effort level that config
    does not offer becomes its default (`effort_level_replaced`). Dates, Lab hours, the Roster, the
    allocation and the obligatory mark are not copied; a fresh demand seed is drawn unless
    `keep_seed`. A source the User may not read answers 403 `forbidden`; copied settings the engine
    refuses 422 `invalid_settings`; while `FEATURE_RERUN` is off 422 `feature_disabled`
    (`{"rerun": "feature_disabled"}`)."""
    try:
        created = await service.copy_from(
            user, _id(body.source_id), _id(class_id), now=auth.utcnow(), keep_seed=body.keep_seed
        )
    except service.FeatureDisabled as refused:
        return error_response(422, refused.code, RERUN_OFF, refused.fields)
    except service.InvalidSettings as refused:
        return error_response(
            422,
            refused.code,
            "The Game settings break the engine's rules.",
            {field: problem.model_dump() for field, problem in refused.problems.items()},
        )
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


@router.get(
    "/class-sessions/{session_id}/overview",
    response_model=ClassOverviewOut,
    responses={**documented(401, 403), 304: {"description": "Not modified since the ETag."}},
    operation_id="getClassOverview",
)
async def get_class_overview(
    session_id: str,
    request: Request,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.overview"))],
) -> Response:
    """The Oversikt (Story 7.1, FR-39, AD-25): every Class game of the session with its status,
    Week, whom it waits for, its Seats and chain cost, the headline counts and `server_now`, read
    from the maintained summaries. With an `ETag`; a request whose `If-None-Match` names it is
    answered 304 with no body. 403 `forbidden` for anyone who is not staff of the Class, and for
    a Class session that does not exist (FR-5, NFR-7)."""
    found = await overview.class_overview(user, _id(session_id))
    if found is None:
        raise authz.Forbidden
    etag = overview.etag_of(found)
    headers = {"ETag": etag, "Cache-Control": "private, no-cache"}
    if _not_modified(request, etag):
        return Response(status_code=304, headers=headers)
    return JSONResponse(found.model_dump(mode="json"), headers=headers)


@router.get(
    "/class-sessions/{session_id}/overview/aggregates",
    response_model=WallAggregatesOut,
    responses={**documented(401, 403, 422), 304: {"description": "Not modified since the ETag."}},
    operation_id="getWallAggregates",
)
async def get_wall_aggregates(
    session_id: str,
    request: Request,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.overview"))],
    role: Annotated[Role, Query()] = Role.FACTORY,
    cells: Annotated[WallCells, Query()] = WallCells.NET,
    status: Annotated[WallStatus, Query()] = WallStatus.ALL,
) -> Response:
    """The Matrisevegg's class median rows for one Veggfiltre combination (Story 7.4, AD-10,
    AD-25): per Uke the median of `role`'s `cells` value with the middle half of the Games, and
    the mean chain cost, over the Class games `status` matches that reached the Uke. The overview
    carries no aggregates. With an `ETag` over the filter and the matched Games' versions; a
    request whose `If-None-Match` names it is answered 304 before any Week is read. 403
    `forbidden` for anyone who is not staff of the Class and for a Class session that does not
    exist (FR-5, NFR-7)."""
    wanted = overview.WallFilter(role=role, cells=cells, status=status)
    matched = await overview.wall_games(user, _id(session_id), wanted)
    if matched is None:
        raise authz.Forbidden
    headers = {"ETag": matched.etag, "Cache-Control": "private, no-cache"}
    if _not_modified(request, matched.etag):
        return Response(status_code=304, headers=headers)
    found = await overview.wall_aggregates_out(wanted, matched)
    return JSONResponse(found.model_dump(mode="json"), headers=headers)


def _not_modified(request: Request, etag: str) -> bool:
    """`If-None-Match` names `etag`, by the weak comparison of RFC 9110 (a proxy may have weakened
    the tag), or is `*`."""
    sent = {
        tag.strip().removeprefix("W/")
        for tag in request.headers.get("if-none-match", "").split(",")
    }
    return etag in sent or "*" in sent


@router.get(
    "/games/{game_id}/weeks",
    response_model=GameWeeksOut,
    responses={**documented(401, 403), 304: {"description": "Not modified since the ETag."}},
    operation_id="getGameWeeks",
)
async def get_game_weeks(
    game_id: str,
    request: Request,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.overview"))],
) -> Response:
    """Every opened Week of a Class game (Story 7.2, FR-39, AD-1, AD-25): per Week and Role the
    Netto lager, the Order and the Kost per uke as the engine stored them, for the Matrisevegg.
    The `ETag` is tied to the Game's `version`; a request whose `If-None-Match` names it is
    answered 304 before any Week is read. 403 `forbidden` for anyone who is not staff of the
    Game's Class, and for a Game that does not exist or that the Oversikt does not list (FR-5)."""
    found_id = _id(game_id)
    version = await overview.readable_game(user, found_id)
    if version is None:
        raise authz.Forbidden
    etag = overview.game_weeks_etag(version)
    headers = {"ETag": etag, "Cache-Control": "private, no-cache"}
    if _not_modified(request, etag):
        return Response(status_code=304, headers=headers)
    found = await overview.game_weeks(found_id)
    if found is None:
        raise authz.Forbidden
    # The Week read is a second transaction: a change between the two answers with its version.
    headers["ETag"] = overview.game_weeks_etag(found.version)
    return JSONResponse(found.model_dump(mode="json"), headers=headers)


@router.get(
    "/games/{game_id}/insight",
    response_model=GameInsightOut,
    responses={**documented(401, 403), 304: {"description": "Not modified since the ETag."}},
    operation_id="getGameInsight",
)
async def get_game_insight(
    game_id: str,
    request: Request,
    user: Annotated[authz.Principal, Depends(authz.require("games.insight"))],
) -> Response:
    """Spillinnsikt (Story 7.7, FR-62, AD-3, AD-12): one Class game week by week for the staff of
    its Class — per Role and opened Week the incoming order and delivery, inventory, backlog,
    Order and cost as stored, who held the Seat and its marks (AD-15), the Seats with their link
    slots, the customer demand series and the number of Weeks. With an `ETag`; a request whose
    `If-None-Match` names it is answered 304. 403 `forbidden`, one answer, for anyone who is not
    staff of the Game's Class, a Student included, and for a Game that does not exist or that
    the Oversikt does not list (FR-5, NFR-7)."""
    found = await overview.game_insight(user, _id(game_id))
    if found is None:
        raise authz.Forbidden
    etag = overview.insight_etag(found)
    headers = {"ETag": etag, "Cache-Control": "private, no-cache"}
    if _not_modified(request, etag):
        return Response(status_code=304, headers=headers)
    return JSONResponse(found.model_dump(mode="json"), headers=headers)


@router.post(
    "/games/{game_id}/seats/{role}/takeover",
    response_model=GameInsightOut,
    responses=documented(401, 403, 409),
    operation_id="takeOverSeat",
)
async def take_over_seat(
    game_id: str,
    role: Role,
    user: Annotated[authz.Principal, Depends(authz.require("games.takeover"))],
) -> Response:
    """«Sett inn KI-spiller for …» (Story 8.5, FR-37, AD-2, AD-12): a Lecturer or Assistant
    lecturer of the game's Class puts an AI player in the Student's Seat `role`, from this Uke when
    the Student has not ordered in it, else from the next. One press, no dialog; recorded in the
    audit log. Answers Spillinnsikt as it now stands. 409 `takeover_exists` with `fields.acted_by`
    (`kind` `staff`, `student` or `system`, and `user_id`) and `fields.acted_at` when an AI player
    was put in first; `seat_not_student_held`, `game_not_running` or `takeover_not_allowed`.
    403 `forbidden` for anyone not staff of the game's Class and any Game the Oversikt does not
    list (FR-5)."""
    try:
        found = await overview.take_over_seat(user, _id(game_id), role)
    except overview.TakeoverRefused as refused:
        if refused.code == "seat_not_found":
            raise authz.Forbidden from None
        return error_response(
            refused.status, refused.code, "The AI player was not put in.", refused.fields
        )
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


def _pause_answer(found: GameInsightOut | None) -> Response:
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


def _pause_refused(refused: overview.PauseRefused, message: str) -> Response:
    return error_response(refused.status, refused.code, message, refused.fields)


@router.post(
    "/games/{game_id}/pause",
    response_model=GameInsightOut,
    responses=documented(401, 403, 409, 422),
    operation_id="pauseGame",
)
async def pause_game(
    game_id: str,
    body: StaffPauseIn,
    user: Annotated[authz.Principal, Depends(authz.require("games.pause"))],
) -> Response:
    """«Pause spillet» (Story 8.7, FR-89, AD-2, AD-12): a Lecturer of the game's Class pauses it,
    with the agreed time `resume_at` or without one; no AI player takes a Seat over while it is
    paused, the Play deadline stands, and the agreed time becomes the insert time of every Seat
    that has not ordered this Uke. Recorded in the audit log. Answers Spillinnsikt as it now
    stands. 422 `time_out_of_range` unless the time lies after now and not after the Play
    deadline; 409 `already_paused` with `fields.acted_by` (`kind`, `user_id`) and
    `fields.acted_at`, `game_not_running`, `game_finished` or `pause_not_allowed`. 403 `forbidden`
    for anyone but a Lecturer of the game's Class (an Assistant lecturer included) and any Game
    the Oversikt does not list (FR-5)."""
    try:
        found = await overview.pause_game(user, _id(game_id), body.resume_at)
    except overview.PauseRefused as refused:
        return _pause_refused(refused, "The game was not paused.")
    return _pause_answer(found)


@router.put(
    "/games/{game_id}/pause/agreed-time",
    response_model=GameInsightOut,
    responses=documented(401, 403, 409, 422),
    operation_id="setPauseAgreedTime",
)
async def set_pause_agreed_time(
    game_id: str,
    body: StaffPauseIn,
    user: Annotated[authz.Principal, Depends(authz.require("games.pause"))],
) -> Response:
    """«Endre avtalt tid» (Story 8.7, FR-89): a Lecturer of the game's Class sets, changes or
    (`resume_at` null) clears the agreed time of the Pause in force, also of one a Student set.
    Recorded in the audit log. Answers Spillinnsikt as it now stands. 409 `not_paused`,
    `game_finished`; 422 `time_out_of_range`; 403 `forbidden` as `pauseGame`."""
    try:
        found = await overview.set_agreed_time(user, _id(game_id), body.resume_at)
    except overview.PauseRefused as refused:
        return _pause_refused(refused, "The agreed time was not set.")
    return _pause_answer(found)


@router.delete(
    "/games/{game_id}/pause",
    response_model=GameInsightOut,
    responses=documented(401, 403, 409),
    operation_id="endPause",
)
async def end_pause(
    game_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("games.pause"))],
) -> Response:
    """«Avslutt pausen» (Story 8.7, FR-89): a Lecturer of the game's Class ends the Pause in force,
    whoever set it; every Student reads that it is over. Recorded in the audit log. Answers
    Spillinnsikt as it now stands. 409 `not_paused`, `game_finished`; 403 `forbidden` as
    `pauseGame`."""
    try:
        found = await overview.end_pause(user, _id(game_id))
    except overview.PauseRefused as refused:
        return _pause_refused(refused, "The pause was not ended.")
    return _pause_answer(found)


@router.post(
    "/games/{game_id}/in-room",
    response_model=GameInsightOut,
    responses=documented(401, 403, 409, 422),
    operation_id="markInRoom",
)
async def mark_in_room(
    game_id: str,
    body: InRoomIn,
    user: Annotated[authz.Principal, Depends(authz.require("games.in_room"))],
) -> Response:
    """«Marker som i rommet» (Story 8.11, FR-36, AD-2, AD-12): a Lecturer of the game's Class marks
    the running game as played in the room during the Lab hour on now, with the in-room limit
    `minutes` in place of the Inactivity limit (times each Student's Tilrettelegging factor) until
    the Lab hour ends. Recorded in the audit log. Answers Spillinnsikt as it now stands. 422
    `minutes_out_of_range` unless `minutes` is a whole number from 2 to 120; 409
    `not_in_lab_hour` outside every Lab hour of the Class session, `already_in_room` with
    `fields.acted_by` and `fields.acted_at`, `game_not_running`, `game_finished` or
    `in_room_not_allowed`. 403 `forbidden` for anyone but a Lecturer of the game's Class (an
    Assistant lecturer included) and any Game the Oversikt does not list (FR-5)."""
    try:
        found = await overview.mark_in_room(user, _id(game_id), body.minutes)
    except overview.InRoomRefused as refused:
        return error_response(
            refused.status, refused.code, "The game was not marked.", refused.fields
        )
    return _pause_answer(found)


@router.delete(
    "/games/{game_id}/in-room",
    response_model=GameInsightOut,
    responses=documented(401, 403, 409),
    operation_id="endInRoom",
)
async def end_in_room(
    game_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("games.in_room"))],
) -> Response:
    """«Ikke i rommet lenger» (Story 8.11, FR-36): a Lecturer of the game's Class ends the mark;
    the due times go back to the Inactivity limit from the same wait starts. Recorded in the audit
    log. Answers Spillinnsikt as it now stands. 409 `not_in_room`; 403 `forbidden` as
    `markInRoom`."""
    try:
        found = await overview.end_in_room(user, _id(game_id))
    except overview.InRoomRefused as refused:
        return error_response(
            refused.status, refused.code, "The mark was not ended.", refused.fields
        )
    return _pause_answer(found)


@router.post(
    "/games/{game_id}/start",
    response_model=GameInsightOut,
    responses=documented(401, 403, 409),
    operation_id="startGame",
)
async def start_game(
    game_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("games.start"))],
) -> Response:
    """«Start spillet» in Spillstyring (Story 8.10, FR-22, AD-2, AD-12): a Lecturer of the game's
    Class starts it for all four Seats; the rules for waiting apply from now. Recorded in the
    audit log. Answers Spillinnsikt as it now stands. 409 `game_already_started` with
    `fields.acted_by` (`kind` `student`, `staff` or `system`, and `user_id`) and
    `fields.acted_at` when someone started it first; 409 `game_not_ready` before the lock has
    given it its snapshot. 403 `forbidden` for anyone but a Lecturer of the game's Class (an
    Assistant lecturer included) and any Game the Oversikt does not list (FR-5)."""
    try:
        found = await overview.start_game(user, _id(game_id))
    except overview.StartRefused as refused:
        return error_response(
            refused.status, refused.code, "The game was not started.", refused.fields
        )
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.get(
    "/class-sessions/{session_id}/start-games",
    response_model=StartGamesOut,
    responses=documented(401, 403),
    operation_id="getStartGames",
)
async def get_start_games(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("games.start"))],
) -> StartGamesOut:
    """The «Start spill» page (Story 8.10, FR-22): the Class games a Lecturer of the Class may
    start now, by game number with their Seats; none before the lock. 403 `forbidden` for anyone
    but a Lecturer of the Class (FR-5)."""
    found = await overview.start_games_page(user, _id(session_id))
    if found is None:
        raise authz.Forbidden
    return found


@router.post(
    "/class-sessions/{session_id}/start-games",
    response_model=StartedGamesOut,
    responses=documented(401, 403, 422),
    operation_id="startGames",
)
async def start_games(
    session_id: str,
    body: StartGamesIn,
    user: Annotated[authz.Principal, Depends(authz.require("games.start"))],
) -> StartedGamesOut:
    """«Start 12 spill» (Story 8.10, FR-22, AD-2): starts the listed Class games, one start per
    game in its own transaction, the Lecturer as actor. A game that started meanwhile, is not
    ready yet, is not of this Class session or fails is skipped; the others go on. Answers the
    real counts; a repeat is safe. 403 `forbidden` for anyone but a Lecturer of the Class."""
    found = await overview.start_games(user, _id(session_id), body.game_ids)
    if found is None:
        raise authz.Forbidden
    return found


@router.get(
    "/class-sessions/{session_id}/waited-for-seats",
    response_model=WaitedForSeatsOut,
    responses=documented(401, 403),
    operation_id="getWaitedForSeats",
)
async def get_waited_for_seats(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("games.fill_seats"))],
) -> WaitedForSeatsOut:
    """The «Sett inn KI-spillere» page (Story 8.12, FR-37): the Seats the Class session's games
    wait for now, per game, and those left out for Tilrettelegging. 403 `forbidden` for anyone
    but a Lecturer of the Class (FR-5)."""
    found = await overview.waited_for_page(user, _id(session_id))
    if found is None:
        raise authz.Forbidden
    return found


@router.post(
    "/class-sessions/{session_id}/waited-for-seats",
    response_model=FilledSeatsOut,
    responses=documented(401, 403, 422),
    operation_id="fillWaitedForSeats",
)
async def fill_waited_for_seats(
    session_id: str,
    body: FillSeatsIn,
    user: Annotated[authz.Principal, Depends(authz.require("games.fill_seats"))],
) -> FilledSeatsOut:
    """«Sett inn 9 KI-spillere» (Story 8.12, FR-37, AD-2): puts an AI player in each listed Seat
    the game still waits for, one Takeover per Seat in its own transaction, the Lecturer as actor.
    A Seat that ordered since, is no longer Student-held, now has Tilrettelegging, is not of this
    Class session or fails is skipped with why; the others go on, and a repeat inserts nothing
    twice. Answers the real counts. 403 `forbidden` for anyone but a Lecturer of the Class."""
    found = await overview.fill_waited_for(user, _id(session_id), body.seat_ids)
    if found is None:
        raise authz.Forbidden
    return found


TEST_GAME_REFUSED = {
    "not_found": "Not found.",
    "session_locked": "A test game starts only before the Start date.",
    "test_game_running": "Your test game here has not finished yet.",
    "llm_unavailable": "The LLM players cannot answer now.",
    "unknown_role": "The game settings have no Seat for this Role.",
}


@router.post(
    "/class-sessions/{session_id}/test-game",
    status_code=201,
    response_model=StartedTestGameOut,
    responses=documented(401, 403, 404, 409, 422),
    operation_id="startTestGame",
)
async def start_test_game(
    session_id: str,
    body: TestGameIn,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.manage"))],
) -> Response:
    """«Start testspill» (Story 6.20, FR-87): the Lecturer plays a private test Game on the Class
    session's current settings, in the chosen Role against three AI players; it starts at once.
    404 `not_found` while `FEATURE_LECTURER_TEST_GAME` is off (AD-17); 409 `session_locked` from
    the Start date, `test_game_running` while their last test Game here runs, `llm_unavailable`;
    422 `unknown_role`; 403 `forbidden` for a session the User may not manage (FR-5)."""
    try:
        game_id = await service.start_test_game(user, _id(session_id), body.role.value)
    except service.TestGameRefused as refused:
        return error_response(refused.status, refused.code, TEST_GAME_REFUSED[refused.code])
    if game_id is None:
        raise authz.Forbidden
    return JSONResponse(StartedTestGameOut(id=game_id).model_dump(mode="json"), status_code=201)


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

    `effort_level`, `debrief_mode`, `debrief_release` and `debrief_ai_text` (FR-15, FR-16, FR-42,
    FR-78), left out, keep their values; a changed `debrief_release` or `debrief_ai_text` once
    locked answers 409 `session_locked` too. With LLM
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
    registered Student through the day's digest mail.

    `allocation_method` (Story 5.17, FR-21), left out, keeps the method. `student_choice` creates
    empty Class games for the registered Students and tells each of them through the day's digest
    mail that they may choose a Class game and a Seat. A changed method answers 422
    `feature_disabled` (`{"allocation_method": "feature_disabled"}`) for Student choice while
    `FEATURE_STUDENT_CHOICE` is off, 409 `session_locked` once locked and 409
    `allocation_confirmed` (`{"allocation_method": "confirmed"}`) once an allocation is confirmed:
    Student choice is final once saved.

    `replay_scenario` (Story 10.2, FR-49), left out, keeps the Replay scenario: `default`, or
    `own` with `replay_template`, the own scenario's editable fields (`starting_inventory`,
    `starting_backlog`, `supply_line`, the three delays, `weeks`, `guided_weeks`, `max_order` as
    whole numbers or `{minimum, maximum}`; `holding_cost`, `backorder_cost`; `demand` as `step`
    with a ranged `change_week`, `random` or `fixed`, each with a `spread`; `info_visibility`
    as in the Game settings, the Replay's own, Story 10.9), laid over the Class game's exact
    settings (Information visibility: over a stored own template's). A template the engine
    refuses answers 422 `invalid_replay_scenario` with `fields` as `invalid_settings`; while
    `FEATURE_INFO_VISIBILITY` is off a view switched on there names `info_visibility`
    `feature_disabled`; `own` with no template sent or stored names
    `replay_template` `required`. Once locked, a changed scenario answers 409 `session_locked`
    (`{"replay_scenario": "locked"}`).

    `ai_assessment` (Story 12.1, FR-61), left out, keeps the «KI-vurdering» switch. It can change
    after the Start date too; once the original Test deadline has passed (and the Test-deadline
    lock has pinned it) a changed value answers 409 `ai_assessment_pinned`
    (`{"ai_assessment": "pinned"}`). Only the Class's owners change it (`ai_assessment.change`).

    `test_sitting` (Story 11.12, FR-51), left out, keeps the Individual test's one timed sitting:
    `{"minutes": n}` sets the time limit in whole minutes, `{"minutes": null}` switches it off. A
    limit outside the configured range answers 422 `invalid_session_values`
    (`{"test_sitting_minutes": "out_of_range"}`); once locked a change answers 409
    `session_locked` (`{"test_sitting": "locked"}`)."""
    try:
        saved = await service.save_session(
            user,
            _id(session_id),
            body.ai_mode,
            now=auth.utcnow(),
            effort_level=body.effort_level,
            debrief_mode=body.debrief_mode,
            debrief_release=body.debrief_release,
            debrief_ai_text=body.debrief_ai_text,
            dates=body.dates,
            game_settings=body.game_settings,
            obligatory=body.obligatory,
            required_share_percent=body.required_share_percent,
            inactivity_limit_hours=body.inactivity_limit_hours,
            allocation_method=body.allocation_method,
            replay_scenario=body.replay_scenario,
            replay_template=body.replay_template,
            ai_assessment=body.ai_assessment,
            test_sitting=body.test_sitting,
        )
    except service.InvalidSettings as refused:
        return error_response(
            422,
            refused.code,
            "The Game settings break the engine's rules.",
            {field: problem.model_dump() for field, problem in refused.problems.items()},
        )
    except service.InvalidReplayScenario as refused:
        return error_response(
            422,
            refused.code,
            "The Replay scenario breaks the engine's rules.",
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
            422,
            refused.code,
            "The share, the Inactivity limit or the time limit breaks a rule.",
            refused.fields,
        )
    except service.InvalidEffortLevel as refused:
        return error_response(
            422, refused.code, "The model config offers no such Effort level.", refused.fields
        )
    except service.FeatureDisabled as refused:
        return error_response(422, refused.code, "This setting is switched off.", refused.fields)
    except (
        service.DeadlinePassed,
        service.SessionLocked,
        service.AllocationConfirmed,
        service.AiAssessmentPinned,
    ) as refused:
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
    `game_already_started`). A session with Student choice (Story 5.17) answers 409
    `allocation_confirmed` (`{"allocation": "student_choice"}`). Nothing is committed on any
    refusal."""
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
    except service.AllocationConfirmed as refused:
        return error_response(
            409, refused.code, "The Students choose their own Seats.", refused.fields
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


@router.post(
    "/class-sessions/{session_id}/replay-scenario-check",
    response_model=SettingsCheckOut,
    responses=documented(401, 403, 409),
    operation_id="checkReplayScenario",
)
async def check_replay_scenario(
    session_id: str,
    body: ReplayScenarioCheckIn,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.manage"))],
) -> Response:
    """The engine's errors on a draft of an own Replay scenario and the warnings of changes that
    probably make the Replay easier than the Class game (`replay_*` codes), as the Lecturer
    leaves a field (Story 10.2, FR-12, FR-49). Stores nothing. Once locked it answers 409
    `session_locked`."""
    try:
        found = await service.check_replay_scenario(
            user, _id(session_id), body.replay_template, now=auth.utcnow()
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
    "/me/games/{game_id}",
    response_model=StudentGameOut,
    responses=documented(401, 403),
    operation_id="getMyGame",
)
async def get_my_game(
    game_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("games.read_own"))],
) -> Response:
    """The Student's own Class game (Story 6.1): number, Role and the four Seats, from the Start
    date. Any other game, one that does not exist and an id that is not one all answer the same
    403 `forbidden`, which never says whether the game exists (FR-5)."""
    found = await service.student_game_of(user, game_id)
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.get(
    "/me/games/{game_id}/play",
    response_model=PlayOut,
    responses=documented(401, 403, 409),
    operation_id="getMyGamePlay",
)
async def get_my_game_play(
    game_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("games.read_own"))],
) -> Response:
    """The play screen's one envelope (Story 6.6, AD-3): `seat_state`, what the Student's own Seat
    sees in the open Week (numbers and Roles only), `table_status`, who sits where, and the
    server's clock. Never the number of Weeks, future demand, another Seat's numbers or a
    reference Order (FR-14, FR-23). 409 `game_not_running` before the start and after the end;
    any other game answers 403 `forbidden` (FR-5)."""
    try:
        found = await service.student_play_of(user, game_id)
    except service.GameNotRunning:
        return error_response(409, "game_not_running", "The game is not running.")
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.get(
    "/me/games/{game_id}/result",
    response_model=GameResultOut,
    responses=documented(401, 403, 409),
    operation_id="getMyGameResult",
)
async def get_my_game_result(
    game_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("games.read_own"))],
) -> Response:
    """«Spillet er ferdig» (Story 6.18, FR-28, AD-3): the chain's cost per Role, Detaljist to
    Fabrikk, and per Uke, once the game has finished. Roles, never names, and no demand series.
    409 `game_not_finished` before the end, so no chain number leaks during play (FR-14); any
    other game answers 403 `forbidden` (FR-5)."""
    try:
        found = await service.student_result_of(user, game_id)
    except service.GameNotFinished:
        return error_response(409, "game_not_finished", "The game has not finished.")
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.get(
    "/me/games/{game_id}/believability",
    response_model=BelievabilityOut,
    responses=documented(401, 403),
    operation_id="getMyBelievability",
)
async def get_my_believability(
    game_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("games.read_own"))],
) -> Response:
    """The believability question of the Student's own game (Story 10.8, FR-70): `offered` once
    a Class game with an AI-held Seat, or a Replay, has finished (never a Game closed at the Test
    deadline), and the Student's own answer. Only the Student who gave an answer reads it; any
    other game answers 403 `forbidden` (FR-5, AD-12)."""
    found = await service.student_believability_of(user, game_id)
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


BELIEVABILITY_REFUSED = {
    "not_offered": "This game does not ask how believable the AI players were.",
    "already_answered": "You have answered already.",
}


@router.post(
    "/me/games/{game_id}/believability",
    status_code=201,
    response_model=BelievabilityOut,
    responses=documented(401, 403, 409, 422),
    operation_id="rateMyBelievability",
)
async def rate_my_believability(
    game_id: str,
    body: BelievabilityIn,
    user: Annotated[authz.Principal, Depends(authz.require("games.read_own"))],
) -> Response:
    """«Send svar» on how believable the AI players' ordering felt (Story 10.8, FR-70, AD-15):
    stored once per Student and Game with the Game's purpose and AI mode. 409 `already_answered`
    (the first answer stands) or `not_offered`; 422 outside 1 to 5. Any other game answers 403
    `forbidden` (FR-5)."""
    try:
        found = await service.rate_own_believability(user, game_id, body.rating)
    except service.BelievabilityRefused as refused:
        return error_response(409, refused.code, BELIEVABILITY_REFUSED[refused.code])
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"), status_code=201)


@router.post(
    "/me/games/{game_id}/weeks/{week}/view",
    status_code=204,
    responses=documented(401, 403, 409),
    operation_id="viewMyGameWeek",
)
async def view_my_game_week(
    game_id: str,
    week: int,
    user: Annotated[authz.Principal, Depends(authz.require("games.play_own"))],
) -> Response:
    """The Student has the Guided Week `week` on screen (Story 6.10, FR-24): it counts as their
    Order there, and the view that leaves no Student to wait for opens the next Week. 204 also
    when the Week was viewed already. 409 `week_not_open` (the game has moved on),
    `week_not_guided`, `game_not_started`, `game_finished` or `seat_not_student`; any other
    game, or a Seat the Student no longer holds, answers 403 `forbidden` (FR-5)."""
    try:
        found = await service.view_own_week(user, game_id, week)
    except service.ViewRefused as refused:
        return error_response(409, refused.code, "The Week cannot be viewed.")
    if found is None:
        raise authz.Forbidden
    return Response(status_code=204)


@router.post(
    "/me/games/{game_id}/weeks/{week}/order",
    status_code=204,
    responses=documented(401, 403, 409, 422),
    operation_id="placeMyGameOrder",
)
async def place_my_game_order(
    game_id: str,
    week: int,
    body: OrderIn,
    user: Annotated[authz.Principal, Depends(authz.require("games.play_own"))],
) -> Response:
    """«Bekreft ordre på 24» (Story 6.12, FR-24, AD-2): the Student's Order for the open Week of
    their own Seat, placed once through `games.commands.place_order` with the Student as actor;
    the client sends no `version`. 409 `order_exists` (also in a Guided Week, whose fixed Order
    is placed when it opens), `week_not_open`, `game_not_started`, `game_finished` or
    `seat_not_yours` (the Seat changed hands between the ownership check and the write); 422
    `order_invalid` (not a whole number from 0 to the maximum). Any other game, or a Seat the
    Student no longer holds, answers 403 `forbidden` (FR-5)."""
    try:
        found = await service.place_own_order(user, game_id, week, body.order)
    except service.OrderRefused as refused:
        return error_response(refused.status, refused.code, "The Order was not placed.")
    if found is None:
        raise authz.Forbidden
    return Response(status_code=204)


@router.post(
    "/me/games/{game_id}/start",
    response_model=StudentGameOut,
    responses=documented(401, 403, 409),
    operation_id="startMyGame",
)
async def start_my_game(
    game_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("games.start_own"))],
) -> Response:
    """«Start spillet» (Story 6.5, FR-22): the Student starts their own Class game for all four
    Seats and gets the game as it now stands. A game already started counts as done. 409
    `starting_task_required` before the Starting task is done, 409 `game_not_ready` before the
    lock has given the game its snapshot; any other game answers 403 `forbidden` (FR-5)."""
    try:
        found = await service.start_own_game(user, game_id)
    except service.StartRefused as refused:
        message = (
            "Do the Starting task first."
            if refused.code == "starting_task_required"
            else "The game is not ready to start yet."
        )
        return error_response(409, refused.code, message)
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.post(
    "/me/games/{game_id}/seats/{role}/reclaim",
    response_model=StudentGameOut,
    responses=documented(401, 403, 409),
    operation_id="reclaimMySeat",
)
async def reclaim_my_seat(
    game_id: str,
    role: Role,
    user: Annotated[authz.Principal, Depends(authz.require("games.play_own"))],
) -> Response:
    """«Ta tilbake setet» (Story 8.4, FR-37, AD-2): the Student whose Seat an AI player took over
    asks for it back. The request is queued and the Seat is theirs again when the next Uke opens;
    a second press, or a repeat, changes nothing. Answers the game as it now stands. 409
    `seat_not_yours` (another Student's Seat, or one no AI player took over from this Student),
    `game_finished` or `game_not_running`; any other game answers 403 `forbidden` (FR-5)."""
    try:
        found = await service.reclaim_own_seat(user, game_id, role)
    except service.ReclaimRefused as refused:
        return error_response(refused.status, refused.code, "The Seat was not reclaimed.")
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.post(
    "/me/games/{game_id}/seats/{role}/takeover",
    response_model=StudentGameOut,
    responses=documented(401, 403, 409),
    operation_id="insertAiPlayer",
)
async def insert_ai_player(
    game_id: str,
    role: Role,
    user: Annotated[authz.Principal, Depends(authz.require("games.play_own"))],
) -> Response:
    """«Sett inn KI-spiller for Jonas» (Story 8.8, FR-89, FR-37, AD-2, AD-12): a Student who holds
    another Seat of the Class game puts an AI player in the Seat `role` once its insert time has
    passed, paused or not; no dialog and no body, so no Student sets or shortens a time. Answers
    the game as it now stands. 409 `takeover_exists` with `fields.acted_by` (`kind`, `user_id`;
    no staff id) and `fields.acted_at`, `insert_not_allowed_yet`, `seat_not_yours`,
    `order_exists`, `seat_not_student_held`, `game_not_running` or `takeover_not_allowed`; any
    other game answers 403 `forbidden` (FR-5)."""
    try:
        found = await service.insert_ai_player(user, game_id, role)
    except service.InsertRefused as refused:
        return error_response(
            refused.status, refused.code, "No AI player was put in.", refused.fields
        )
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.post(
    "/me/games/{game_id}/pause",
    response_model=StudentGameOut,
    responses=documented(401, 403, 409),
    operation_id="pauseMyGame",
)
async def pause_my_game(
    game_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("games.play_own"))],
) -> Response:
    """«Ta pause uten avtalt tid» (Story 8.6, FR-89, AD-2): a Student who holds a Seat pauses
    their Class game; no AI player takes a Seat over while it is paused, and any Student's Order
    ends it. No time is taken: only a Lecturer sets an agreed time. Answers the game as it now
    stands. 409 `already_paused` with `fields.acted_by` (`kind`, `user_id`) and
    `fields.acted_at`, `seat_not_yours`, `game_finished`, `game_not_running` or
    `pause_not_allowed`; any other game answers 403 `forbidden` (FR-5)."""
    try:
        found = await service.pause_own_game(user, game_id)
    except service.PauseRefused as refused:
        return error_response(
            refused.status, refused.code, "The game was not paused.", refused.fields
        )
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.post(
    "/me/games/{game_id}/time-proposal",
    response_model=StudentGameOut,
    responses=documented(401, 403, 409, 422),
    operation_id="proposeMyGameTime",
)
async def propose_my_game_time(
    game_id: str,
    body: TimeProposalIn,
    user: Annotated[authz.Principal, Depends(authz.require("games.play_own"))],
) -> Response:
    """«Send forslaget til gruppen» (Story 6.19, FR-22): the Student proposes a time to play, a
    date and a time and nothing else. It replaces the game's open proposal and its acceptances,
    and each other Student of the game is told. Answers the game as it now stands. 422
    `time_out_of_range` unless the time lies after now and not after the Play deadline; 409
    `game_finished`; any other game, or a Seat the Student no longer holds, answers 403
    `forbidden` (FR-5)."""
    try:
        found = await service.propose_own_time(user, game_id, body.at)
    except service.ProposalRefused as refused:
        return error_response(refused.status, refused.code, "The time was not proposed.")
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.post(
    "/me/games/{game_id}/time-proposal/{proposal_id}/accept",
    response_model=StudentGameOut,
    responses=documented(401, 403, 409),
    operation_id="acceptMyGameTime",
)
async def accept_my_game_time(
    game_id: str,
    proposal_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("games.play_own"))],
) -> Response:
    """«Godta tidspunktet» (Story 6.19, FR-22): the Student accepts the game's open proposal with
    one press; an acceptance already stored counts as done. Answers the game as it now stands.
    409 `proposal_gone` (replaced, or its time has passed), `own_proposal` or `game_finished`;
    any other game, or a Seat the Student no longer holds, answers 403 `forbidden` (FR-5)."""
    try:
        found = await service.accept_own_time(user, game_id, proposal_id)
    except service.ProposalRefused as refused:
        return error_response(refused.status, refused.code, "The time was not accepted.")
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.get(
    "/lecturer-home/class-sessions",
    response_model=LecturerOverviewOut,
    responses=documented(401, 403),
    operation_id="lecturerHomeClassSessions",
)
async def lecturer_home_class_sessions(
    user: Annotated[authz.Principal, Depends(authz.require("lecturer_home.view"))],
) -> Response:
    """The Lærerhjem's «Venter» and «Neste frist» over the User's Classes that are not archived
    (UX-DR56). The Lærerhjem's policy holds it: the Admin role alone, which reads a Control test
    Class it owns (Story 12.7), does not reach it, and a Control test is never among them."""
    found = await service.lecturer_overview(user)
    return JSONResponse(found.model_dump(mode="json"))


NOT_FOUND = "not_found"


def _no_seat_choice() -> Response:
    return error_response(404, NOT_FOUND, "No such Student choice.")


def _choice_id(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


@router.get(
    "/me/class-sessions/{session_id}/seat-choice",
    response_model=SeatChoiceOut,
    responses=documented(401, 404),
    operation_id="getSeatChoice",
)
async def get_seat_choice(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.read_enrolled"))],
) -> Response:
    """«Velg spill og sete» (Story 5.17, FR-21, UX-DR62): the Class session's Class games, each
    Seat free, held by a Student (named) or, after the lock, by an AI player, and the reader's own
    Seat. 404 `not_found` while `FEATURE_STUDENT_CHOICE` is off, for a session that does not use
    Student choice, and for a User who is not a registered Student of its Class (AD-17)."""
    found_id = _choice_id(session_id)
    found = (
        await service.seat_choice(user, found_id, now=auth.utcnow())
        if found_id is not None
        else None
    )
    if found is None:
        return _no_seat_choice()
    return JSONResponse(found.model_dump(mode="json"))


@router.put(
    "/me/class-sessions/{session_id}/seat-choice",
    response_model=SeatChoiceOut,
    responses=documented(401, 404, 409, 422),
    operation_id="takeSeat",
)
async def take_seat(
    session_id: str,
    body: SeatChoiceIn,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.read_enrolled"))],
) -> Response:
    """«Ta setet Grossist i Spill 17» (Story 5.17, FR-21): the Student takes the free Seat, or
    moves to it from the Seat they hold, in one request; their own Seat again changes nothing.
    409 `seat_taken` (`{"seat": "taken"}`) when another occupant holds it, 422 `invalid_seat`
    (`{"seat": "unknown"}`) for a game or Role the session does not have, 409 `session_locked`
    (`{"seat": "locked"}`) once locked, 409 `class_archived` for an archived Class; nothing changes
    then. Not found as the read."""
    found_id = _choice_id(session_id)
    try:
        taken = (
            await service.take_seat(user, found_id, body, now=auth.utcnow())
            if found_id is not None
            else None
        )
    except service.InvalidSeat as refused:
        return error_response(422, refused.code, "No such Seat.", refused.fields)
    except (service.SeatTaken, service.SessionLocked) as refused:
        return error_response(409, refused.code, "The Seat cannot be taken.", refused.fields)
    if taken is None:
        return _no_seat_choice()
    return JSONResponse(taken.model_dump(mode="json"))


PERSONAL = {"Cache-Control": "no-store"}
"""A Student's Tilrettelegging is personal data: no cache keeps it (Story 8.9)."""


@router.get(
    "/class-sessions/{session_id}/students/{user_id}",
    response_model=StudentPageOut,
    responses=documented(401, 403),
    operation_id="getStudentPage",
)
async def get_student_page(
    session_id: str,
    user_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("student_pages.read"))],
) -> Response:
    """The Studentside (Story 8.9, UX-DR53): one Student of the Class session, for the staff of
    its Class (Story 12.5: Assistant lecturers too). «Tilrettelegging» and «Frister» only for its
    owners (`can_manage`); null for an Assistant lecturer. 403 `forbidden` for anyone outside the
    Class, a User who is not a Student of the Class now and a Class session that does not exist
    (FR-5, AD-12)."""
    found = await adjustments.student_page(user, _id(session_id), _id(user_id))
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"), headers=PERSONAL)


@router.put(
    "/class-sessions/{session_id}/students/{user_id}/adjustment",
    response_model=StudentPageOut,
    responses=documented(401, 403, 409, 422),
    operation_id="saveAdjustment",
)
async def save_adjustment(
    session_id: str,
    user_id: str,
    body: AdjustmentIn,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.manage"))],
) -> Response:
    """«Lagre tilrettelegging» (Story 8.9, FR-17): the Student's factor on the Inactivity limit
    (1, 1.5, 2 or 3) and the share of Weeks required of them (0 to the class share; null or the
    class share: the class's own). Applies from now, also after the Start date: the open turn times
    of the Student's Class game are recomputed at once. Recorded in the audit log. Answers the
    Studentside. 422 `invalid_adjustment` with `fields` (`time_factor` `not_offered`,
    `share_percent` `out_of_range`); 409 `class_archived`; 403 `forbidden` as `getStudentPage`."""
    try:
        found = await adjustments.save_adjustment(user, _id(session_id), _id(user_id), body)
    except adjustments.InvalidAdjustment as refused:
        return error_response(
            422, refused.code, "The Tilrettelegging breaks a rule.", refused.fields
        )
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"), headers=PERSONAL)


# Admin-område → «Kontrolltest» (Story 12.7, FR-82, AD-27).
admin_router = APIRouter(prefix="/api/admin", tags=["admin"])


@admin_router.get(
    "/control-tests",
    response_model=ControlTestsOut,
    responses=documented(401, 403),
    operation_id="listControlTests",
)
async def list_control_tests(
    user: Annotated[authz.Principal, Depends(authz.require("control_tests.manage"))],
) -> Response:
    """The Kontrolltest page (Story 12.7): the operator's own Institution (null until one is
    marked), the Scoring guide versions and model configs a new Control test may pin, and every
    Control test, newest first, with what it pinned."""
    found = await control_tests.overview(user)
    return JSONResponse(found.model_dump(mode="json"))


@admin_router.post(
    "/control-tests",
    status_code=201,
    response_model=ControlTestOut,
    responses=documented(401, 403, 409, 422),
    operation_id="createControlTest",
)
async def create_control_test(
    body: ControlTestIn,
    user: Annotated[authz.Principal, Depends(authz.require("control_tests.manage"))],
) -> Response:
    """Set up a Control test (Story 12.7, FR-82, AD-27): one transaction makes a Class in the
    operator's own Institution with the Admin as its owner and in it a Class session of kind
    `control_test`, pinned to the Scoring guide version and the model config under test. 409
    `operator_institution_missing` while no Institution is marked; 422 `invalid_request` with
    `fields` `name` (the Class name rule's code), `scoring_guide_id` and `model_config_id`
    (`missing` or `unknown`)."""
    try:
        created = await control_tests.create(user, body, now=auth.utcnow())
    except control_tests.OperatorInstitutionMissing:
        return error_response(
            409,
            "operator_institution_missing",
            "Mark the operator's own Institution first.",
        )
    except control_tests.InvalidControlTest as refused:
        return error_response(
            422, "invalid_request", "The Control test is not valid.", refused.fields
        )
    return JSONResponse(created.model_dump(mode="json"), status_code=201)
