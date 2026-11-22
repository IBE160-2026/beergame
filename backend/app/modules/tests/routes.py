"""The Starting task routes (Story 6.3, FR-85): `/api/me/games/{game_id}/starting-task`. Any game
that is not the Student's own locked Class game answers 403 `forbidden`, the same for one that
does not exist (FR-5).

The question set selection, «Spørsmål og vekter» (Story 11.1, FR-52):
`GET /api/class-sessions/{id}/question-set` for the Class's owners and Assistant lecturers and
`PUT …` («Lagre vekter») for its owners; 403 `forbidden` for every other caller and for a session
that does not exist.

The Scoring guide, «Sensorveiledning» (Story 11.2, FR-81): `GET
/api/class-sessions/{id}/scoring-guide` for the Class's owners and Assistant lecturers and `PUT …`
(«Lagre sensorveiledning») for its owners, likewise.

The Adapted item preview (Story 11.9, FR-53): `GET /api/class-sessions/{id}/adapted-preview`
for the Class's owners and Assistant lecturers, likewise.

The Student's Individual test (Story 11.3, FR-51): `GET /api/me/class-sessions/{id}/test` and
`POST …` (accepting the own-work statement). Any session that is not the Student's own locked
Class session answers 403 `forbidden`, whether or not an attempt exists (FR-5). `PUT
…/test/answers/{item_id}` autosaves one answer (Story 11.4, AD-10).

A Student's own Test deadline (Story 11.13, FR-18): `PUT
/api/class-sessions/{id}/students/{user_id}/deadline` («Lagre frist» on the Studentside) for the
Lecturers of the Class only (`class_sessions.manage`); 403 `forbidden` for every other caller."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response

from app.modules.sessions import service as sessions
from app.modules.tests import assessed, attempt, commands, guide, preview, selection, service
from app.modules.tests.schemas import (
    AdaptedPreviewOut,
    AnswerIn,
    AssessmentListOut,
    DeadlineExtensionIn,
    FinalIn,
    MyAssessmentOut,
    MyTestOut,
    QuestionSetIn,
    QuestionSetOut,
    SavedAnswerOut,
    ScoringGuideIn,
    ScoringGuideOut,
    StaffAssessmentOut,
    StartingTaskOut,
    TestAnswerIn,
)
from app.platform import auth, authz
from app.platform.errors import documented, error_response

router = APIRouter(prefix="/api", tags=["tests"])

_PERSONAL = {"Cache-Control": "no-store"}
"""A Student's own deadline is personal data: no cache keeps it (Story 11.13)."""

_PATH = "/me/games/{game_id}/starting-task"


def _state(found: StartingTaskOut) -> Response:
    return JSONResponse(found.model_dump(mode="json"))


@router.get(
    _PATH,
    response_model=StartingTaskOut,
    responses=documented(401, 403),
    operation_id="getMyStartingTask",
)
async def get_starting_task(
    game_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("games.read_own"))],
) -> Response:
    """The Student's Starting task: the items in order, each answered one with its result, the
    final question's choice and whether the task is done."""
    return _state(await service.read(user, game_id))


@router.post(
    f"{_PATH}/answers",
    response_model=StartingTaskOut,
    responses=documented(401, 403, 422),
    operation_id="answerStartingTaskItem",
)
async def answer_starting_task_item(
    game_id: str,
    body: AnswerIn,
    user: Annotated[authz.Principal, Depends(authz.require("starting_task.answer_own"))],
) -> Response:
    """Send the answer to one item: scored by computed rules and stored once (a repeat keeps
    the first answer). 422 `unknown_item` for an item the task does not have."""
    try:
        found = await service.answer(user, game_id, body.item_id, body.answer, auth.utcnow())
    except service.UnknownItem:
        return error_response(422, "unknown_item", "The Starting task has no such item.")
    return _state(found)


@router.post(
    f"{_PATH}/final",
    response_model=StartingTaskOut,
    responses=documented(401, 403, 409, 422),
    operation_id="finishStartingTask",
)
async def finish_starting_task(
    game_id: str,
    body: FinalIn,
    user: Annotated[authz.Principal, Depends(authz.require("starting_task.answer_own"))],
) -> Response:
    """Answer or skip the final question; the task is then done and `starting_task` recorded.
    409 `items_open` while an item has no answer."""
    try:
        found = await service.finish(user, game_id, body.choice, auth.utcnow())
    except service.ItemsOpen:
        return error_response(409, "items_open", "Answer every item first.")
    return _state(found)


def _id(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise authz.Forbidden from None


_SET = "/class-sessions/{session_id}/question-set"


@router.get(
    _SET,
    response_model=QuestionSetOut,
    responses=documented(401, 403),
    operation_id="getSessionQuestionSet",
)
async def get_session_question_set(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.read"))],
) -> Response:
    """The Klasseøkt's «Spørsmål og vekter» block (Story 11.1, FR-52, FR-53): every Core item of
    the question set with its type, weight in force and whether it is taken out, the Adapted
    items' total weight, the sum, whether the set is a draft and whether it can still change
    (before the Start date). Once locked, the selection the lock pinned."""
    found = await selection.read_block(user, _id(session_id), auth.utcnow())
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.put(
    _SET,
    response_model=QuestionSetOut,
    responses=documented(401, 403, 409, 422),
    operation_id="setSessionQuestionSet",
)
async def set_session_question_set(
    session_id: str,
    body: QuestionSetIn,
    user: Annotated[authz.Principal, Depends(authz.require("question_set.change"))],
) -> Response:
    """«Lagre vekter» (Story 11.1, FR-52, AD-15): the whole selection, stored on the latest
    question set version and recorded in the audit log. 422 `weights_not_100` when the weights
    of the items left in plus the Adapted total are not 100, `validation_error` for an unknown
    item, a missing weight or every item taken out; 409 `session_locked` from the Start date,
    `class_archived` for an archived Class; 403 `forbidden` for an Assistant lecturer and every
    other caller."""
    try:
        found = await selection.save(user, _id(session_id), body, auth.utcnow())
    except selection.WeightsNot100 as refused:
        return error_response(
            422,
            "weights_not_100",
            f"The weights sum to {refused.total}, not 100.",
            {"weights": "sum"},
        )
    except selection.UnknownItems as refused:
        return error_response(
            422, "validation_error", "The selection does not fit the question set.", refused.fields
        )
    except sessions.SessionLocked as refused:
        return error_response(409, refused.code, "The Class session has started.", refused.fields)
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.get(
    "/class-sessions/{session_id}/adapted-preview",
    response_model=AdaptedPreviewOut,
    responses=documented(401, 403),
    operation_id="getAdaptedPreview",
)
async def get_adapted_preview(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.read"))],
) -> Response:
    """The Adapted item preview (Story 11.9, FR-53, UX-DR70): each template of the version the
    Class session pins, filled by code from the static sample facts set («Demodata»), with its
    weight of the Adapted total in force. No Game, no stored facts set, no LLM call."""
    found = await preview.read_preview(user, _id(session_id))
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


_GUIDE = "/class-sessions/{session_id}/scoring-guide"


@router.get(
    _GUIDE,
    response_model=ScoringGuideOut,
    responses=documented(401, 403),
    operation_id="getSessionScoringGuide",
)
async def get_session_scoring_guide(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.read"))],
) -> Response:
    """The Klasseøkt's «Sensorveiledning» block (Story 11.2, FR-81): the Scoring guide in force,
    each question's guide text marked «Standard» or «Endret», its coded criteria (read-only), the
    one five-step scale, whether a Control test has checked the version, and whether it can still
    change (before the original Test deadline). Once pinned, the version pinned."""
    found = await guide.read_block(user, _id(session_id), auth.utcnow())
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.put(
    _GUIDE,
    response_model=ScoringGuideOut,
    responses=documented(401, 403, 409, 422),
    operation_id="setSessionScoringGuide",
)
async def set_session_scoring_guide(
    session_id: str,
    body: ScoringGuideIn,
    user: Annotated[authz.Principal, Depends(authz.require("scoring_guide.change"))],
) -> Response:
    """«Lagre sensorveiledning» (Story 11.2, FR-81, AD-23): the changed guide texts, stored as a
    new Scoring guide version made for the Class session and recorded in the audit log; the
    earlier version is unchanged. 422 `validation_error` for a question the guide does not have
    or a text the record refuses (`fields` by question id); 409 `scoring_guide_locked` from the
    original Test deadline, `class_archived` for an archived Class; 403 `forbidden` for an
    Assistant lecturer and every other caller."""
    try:
        found = await guide.save(user, _id(session_id), body, auth.utcnow())
    except guide.UnknownQuestions as refused:
        return error_response(
            422, "validation_error", "The guide texts do not fit the Scoring guide.", refused.fields
        )
    except sessions.ScoringGuideLocked as refused:
        return error_response(409, refused.code, "The Test deadline has passed.", refused.fields)
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


_TEST = "/me/class-sessions/{session_id}/test"


@router.get(
    _TEST,
    response_model=MyTestOut,
    responses=documented(401, 403),
    operation_id="getMyTest",
)
async def get_my_test(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("tests.take_own"))],
) -> Response:
    """The Student's Individual test (Story 11.3, FR-51): `statement` until they accept the
    own-work statement, with no item; `open` with their items in order once they have; `closed`
    when their Test deadline passed with no attempt. 403 `replay_required` before the Replay is
    completed, `forbidden` for any session that is not theirs."""
    try:
        found = await attempt.read(user, _id(session_id), auth.utcnow())
    except commands.ReplayRequired:
        return error_response(403, "replay_required", "Complete the Replay first.")
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.get(
    f"{_TEST}/assessment",
    response_model=MyAssessmentOut,
    responses=documented(401, 403),
    operation_id="getMyAssessment",
)
async def get_my_assessment(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("tests.take_own"))],
) -> Response:
    """The Student's «KI-vurdering» of their Individual test (Story 12.2, FR-54, FR-55, FR-61):
    `no_test`, `not_ready`, `switched_off`, `incomplete` (items, the unassessed item numbers, no
    total), `failed`, or `ready` (items and the weighted total). Counts toward nothing; no pass
    or fail, no letter. `forbidden` for any session that is not theirs."""
    found = await assessed.read(user, _id(session_id))
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


async def _flag(user: authz.Principal, session_id: str, item_id: str, flagged: bool) -> Response:
    try:
        found = await assessed.set_flag(user, _id(session_id), item_id, flagged)
    except assessed.NotFlaggable:
        return error_response(
            409, assessed.NotFlaggable.code, "There is no written feedback to flag for that item."
        )
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.put(
    f"{_TEST}/assessment/items/{{item_id}}/flag",
    response_model=MyAssessmentOut,
    responses=documented(401, 403, 409),
    operation_id="flagFeedback",
)
async def flag_feedback(
    session_id: str,
    item_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("tests.take_own"))],
) -> Response:
    """«Marker som feil» (Story 12.5, FR-55): the Student marks the written feedback of one item of
    their own «KI-vurdering» as wrong, stored at once; the staff of the Class see it. Idempotent.
    Answers the view as it now stands. 409 `feedback_not_flaggable` when the view shows no written
    feedback for that item; `forbidden` for any session that is not theirs."""
    return await _flag(user, session_id, item_id, True)


@router.delete(
    f"{_TEST}/assessment/items/{{item_id}}/flag",
    response_model=MyAssessmentOut,
    responses=documented(401, 403, 409),
    operation_id="unflagFeedback",
)
async def unflag_feedback(
    session_id: str,
    item_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("tests.take_own"))],
) -> Response:
    """«Angre» (Story 12.5, FR-55): the Student takes their flag on one item's feedback back.
    Idempotent; answers and refuses as `flagFeedback`."""
    return await _flag(user, session_id, item_id, False)


@router.get(
    "/class-sessions/{session_id}/students/{user_id}/assessment",
    response_model=StaffAssessmentOut,
    responses=documented(401, 403),
    operation_id="getStudentAssessment",
)
async def get_student_assessment(
    session_id: str,
    user_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("ai_assessments.read"))],
) -> Response:
    """A Student's «KI-vurdering» for the staff of the Class (Story 12.5, FR-55, AD-12): the block
    on the Studentside. What the Student reads (states, scores, feedback, the notes, `checked`)
    and which pieces they flagged; never a choice only the Student sees. 403 `forbidden` for
    anyone but the owners and Assistant lecturers of the Class (the Admin too), a User who is no
    Student of it now and an unknown Class session (FR-5)."""
    found = await assessed.staff_read(user, _id(session_id), _id(user_id))
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"), headers=_PERSONAL)


@router.get(
    "/class-sessions/{session_id}/assessments",
    response_model=AssessmentListOut,
    responses=documented(401, 403),
    operation_id="listStudentAssessments",
)
async def list_student_assessments(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("ai_assessments.read"))],
) -> Response:
    """The Klasseøkt's list of AI assessments (Story 12.5): each Student of the Class by name,
    the state of their assessment and how many pieces of feedback they flagged. 403 `forbidden`
    as `getStudentAssessment`."""
    found = await assessed.staff_list(user, _id(session_id))
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"), headers=_PERSONAL)


@router.post(
    _TEST,
    status_code=201,
    response_model=MyTestOut,
    responses={**documented(401, 403, 409), 200: {"model": MyTestOut}},
    operation_id="openMyTest",
)
async def open_my_test(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("tests.take_own"))],
) -> Response:
    """Accept the own-work statement and open the Individual test (Story 11.3, FR-51): 201 with
    the attempt this request made, 200 with the one the Student has (also when two opens run at
    once). 403 `replay_required` before the Replay is completed, 409 `test_deadline_passed` after
    the Student's Test deadline with no attempt, 403 `forbidden` for any session that is not
    theirs."""
    try:
        found = await attempt.open_(user, _id(session_id), auth.utcnow())
    except commands.ReplayRequired:
        return error_response(403, "replay_required", "Complete the Replay first.")
    except commands.DeadlinePassed:
        return error_response(409, "test_deadline_passed", "Your Test deadline has passed.")
    if found is None:
        raise authz.Forbidden
    opened, created = found
    return JSONResponse(opened.model_dump(mode="json"), status_code=201 if created else 200)


@router.post(
    f"{_TEST}/submit",
    response_model=MyTestOut,
    responses=documented(401, 403, 409),
    operation_id="submitMyTest",
)
async def submit_my_test(
    session_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("tests.take_own"))],
) -> Response:
    """«Lever testen» (Story 11.10, FR-51, AD-9, AD-16): the Student hands in their Individual
    test once; their saved answers are scored and stored and `test_submitted` is recorded. 200
    with the test as handed in (state `submitted`). 409 `attempt_submitted` when it was handed in
    already (nothing changes), 409 `test_deadline_passed` after the Student's Test deadline, 409
    `sitting_ended` once their timed sitting has ended (Story 11.12), 403
    `forbidden` for any session that is not theirs or a test not yet opened."""
    try:
        found = await attempt.submit(user, _id(session_id), auth.utcnow())
    except commands.AttemptSubmitted:
        return error_response(409, "attempt_submitted", "The test is handed in.")
    except commands.DeadlinePassed:
        return error_response(409, "test_deadline_passed", "Your Test deadline has passed.")
    except commands.SittingEnded:
        return error_response(409, "sitting_ended", "Your time limit has run out.")
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


@router.put(
    f"{_TEST}/answers/{{item_id}}",
    response_model=SavedAnswerOut,
    responses=documented(401, 403, 409, 422),
    operation_id="saveMyTestAnswer",
)
async def save_my_test_answer(
    session_id: str,
    item_id: str,
    body: TestAnswerIn,
    user: Annotated[authz.Principal, Depends(authz.require("tests.take_own"))],
) -> Response:
    """Autosave the Student's answer to one item (Story 11.4, FR-51, AD-10): the answer stored
    after the save. It is replaced only when `revision` is above the stored one; otherwise the
    stored answer comes back unchanged, without an error. 409 `attempt_submitted` once the test is
    handed in, 409 `test_deadline_passed` after the Student's Test deadline, 409 `sitting_ended`
    once their timed sitting has ended (Story 11.12), 422 `unknown_item`
    for an item the attempt does not have, 422 `invalid_answer` for a value that does not answer
    the item, 403 `forbidden` for any session that is not theirs or a test not yet opened."""
    try:
        saved = await attempt.save(
            user, _id(session_id), item_id, body.value, body.revision, auth.utcnow()
        )
    except commands.AttemptSubmitted:
        return error_response(409, "attempt_submitted", "The test is handed in.")
    except commands.DeadlinePassed:
        return error_response(409, "test_deadline_passed", "Your Test deadline has passed.")
    except commands.SittingEnded:
        return error_response(409, "sitting_ended", "Your time limit has run out.")
    except commands.UnknownItem:
        return error_response(422, "unknown_item", "The test has no such item.")
    except commands.InvalidAnswer:
        return error_response(422, "invalid_answer", "The value does not answer the item.")
    if saved is None:
        raise authz.Forbidden
    return JSONResponse(saved.model_dump(mode="json"))


@router.put(
    "/class-sessions/{session_id}/students/{user_id}/deadline",
    response_model=sessions.StudentDeadlinesOut,
    responses=documented(401, 403, 409, 422),
    operation_id="extendTestDeadline",
)
async def extend_test_deadline(
    session_id: str,
    user_id: str,
    body: DeadlineExtensionIn,
    user: Annotated[authz.Principal, Depends(authz.require("class_sessions.manage"))],
) -> Response:
    """«Lagre frist» on the Studentside (Story 11.13, FR-18, AD-9): the Student's own Test
    deadline, later than the Class session's, and their Debrief deadline moved by the same amount;
    an open Individual test attempt takes it at once (a timed sitting keeps its end). Recorded in
    the audit log. Answers the block «Frister». 422 `invalid_extension` with `fields.test_deadline`
    (`not_later`, `passed`, `no_test_deadline`); 409 `attempt_submitted` when the Student has
    handed the test in; 409 `class_archived`; 403 `forbidden` for anyone but a Lecturer of the
    Class (an Assistant lecturer too) and for a User who is no Student of it."""
    try:
        found = await commands.extend_deadline(
            user, _id(session_id), _id(user_id), body.test_deadline, auth.utcnow()
        )
    except commands.AttemptSubmitted:
        return error_response(409, "attempt_submitted", "The test is handed in.")
    except sessions.InvalidExtension as refused:
        return error_response(422, refused.code, "The deadline must be later.", refused.fields)
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"), headers=_PERSONAL)
