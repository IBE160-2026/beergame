"""The Debrief routes (Stories 9.2 to 9.9, FR-41, FR-42, FR-44 to FR-47, AD-3, AD-12).

- `POST /api/me/class-sessions/{id}/debrief`: «Gå til Debrief» and Stegene's Debrief step open
  the Student's Debrief session (created at step 1 the first time) and answer it.
- `GET /api/debriefs/{id}`: the same Debrief session by its id.
- Step 1 (Story 9.3): `GET /api/debriefs/{id}/net-inventory` (the Student's own Netto lager),
  `GET`/`POST /api/debriefs/{id}/explanation` (their own Explanation; sent once, 409
  `explanation_exists`).
- `GET /api/debriefs/{id}/steps/{step}` (2 to 5): every step after step 1, behind the
  Explanation gate (403 `explanation_required`). Step 2 is the reveal of customer demand
  (Story 9.4), step 3 the whole chain (Story 9.5), step 4 the Student's own moments (Story
  9.7); later stories add step 5's content here.
- Between steps 3 and 4 (Story 9.6): `GET /api/debriefs/{id}/reflection` (the reflection
  questions with the Student's own answers) and `POST /api/debriefs/{id}/reflection/{question_id}`
  (one answer, stored once, in order; 409 `reflection_out_of_order`), behind the same gate.
- `GET /api/class-sessions/{id}/students/{user_id}/explanation`: a Student's Explanation for the
  Class's owners and Assistant lecturers (`explanations.read`).
- Story 9.8: step 4 also carries `bill`; `POST /api/debriefs/{id}/finish` («Fullfør Debriefen»,
  409 `debrief_incomplete`, `test_deadline_passed`) and `GET /api/debriefs/{id}/summary` (the
  Student's own summary); `GET /api/class-sessions/{id}/students/{user_id}/debrief-summary`, the
  Explanation and Debrief summary for the Class's staff (`debrief_summaries.read`).
- Story 9.9, step 5: `GET /api/debriefs/{id}/quiz` (the Debrief quiz) and
  `POST /api/debriefs/{id}/quiz/attempts` (one scored attempt; 409 `quiz_passed`,
  `test_deadline_passed`), both 403 `debrief_required` until the Debrief is finished.

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
    MySummaryOut,
    NetInventoryOut,
    QuizAttemptIn,
    QuizAttemptOut,
    QuizOut,
    ReflectionAnswerIn,
    ReflectionOut,
    ReflectionQuestionOut,
    StaffSummaryOut,
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
    except service.InvalidAnswer as invalid:
        return error_response(
            422, "validation_error", "The answer is empty or too long.", {"text": invalid.reason}
        )
    except service.UnknownQuestion:
        return error_response(404, "not_found", "No such reflection question.")
    except commands.AnswerOutOfOrder:
        return error_response(
            409, "reflection_out_of_order", "Answer the reflection questions in order."
        )
    except commands.DebriefIncomplete:
        return error_response(
            409,
            "debrief_incomplete",
            "Answer every reflection question and read your moments before you finish.",
        )
    except commands.TestDeadlinePassed:
        return error_response(409, "test_deadline_passed", "The Test deadline has passed.")
    except service.DebriefRequired:
        return error_response(403, "debrief_required", "Finish the Debrief before the quiz.")
    except service.InvalidQuizAnswers as invalid:
        return error_response(
            422,
            "validation_error",
            "Answer every question once with one of its choices.",
            {"answers": invalid.reason},
        )
    except commands.QuizPassed:
        return error_response(409, "quiz_passed", "You have passed the quiz already.")
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
    (Story 9.5, FR-44, AD-7). Step 4 carries `moments`: the Student's own moments rendered by
    code from their Seat's stored facts set, whose id is recorded at the first view (Story 9.7,
    FR-44, AD-7); none and `mostly_ai` with fewer than 10 own Orders. Only the caller's own Seat:
    no route serves another Student's moments (FR-43)."""
    return await _answer(service.step(user, _id(debrief_id), step))


@router.get(
    "/debriefs/{debrief_id}/reflection",
    response_model=ReflectionOut,
    responses=documented(401, 403),
    operation_id="getMyReflection",
)
async def get_my_reflection(debrief_id: str, user: OWN) -> Response:
    """The reflection questions between steps 3 and 4 (Story 9.6, FR-45): the Class session's
    pinned version, feelings, then evidence, then structure, each with the Student's own answer
    (null until answered); never another Student's (FR-43). 403 `explanation_required` until the
    Explanation is saved."""
    return await _answer(service.own_reflection(user, _id(debrief_id)))


@router.post(
    "/debriefs/{debrief_id}/reflection/{question_id}",
    response_model=ReflectionQuestionOut,
    responses=documented(401, 403, 404, 409, 422),
    operation_id="answerReflectionQuestion",
)
async def answer_reflection_question(
    debrief_id: str, question_id: str, body: ReflectionAnswerIn, user: OWN
) -> Response:
    """«Fortsett»: stores the Student's answer to one reflection question once, as typed, and
    answers the question with it. The questions are answered in order: any other than the first
    unanswered one is 409 `reflection_out_of_order`; an answered one answers its stored answer
    unchanged. 404 `not_found` for an id not in the pinned version, 422 `validation_error` for
    white space only or more than 2000 characters, 403 `explanation_required` before the
    Explanation."""
    return await _answer(service.answer_mine(user, _id(debrief_id), question_id, body.text))


@router.get(
    "/debriefs/{debrief_id}/summary",
    response_model=MySummaryOut,
    responses=documented(401, 403),
    operation_id="getMyDebriefSummary",
)
async def get_my_debrief_summary(debrief_id: str, user: OWN) -> Response:
    """The Student's own Debrief summary (Story 9.8), `summary` null until «Fullfør Debriefen».
    403 `explanation_required` before the Explanation."""
    return await _answer(service.own_summary(user, _id(debrief_id)))


@router.post(
    "/debriefs/{debrief_id}/finish",
    response_model=MySummaryOut,
    responses=documented(401, 403, 409),
    operation_id="finishMyDebrief",
)
async def finish_my_debrief(debrief_id: str, user: OWN) -> Response:
    """«Fullfør Debriefen» (Story 9.8, FR-47, AD-16): stores the Student's Debrief summary once
    (the key moments by fact id, the reflection answers, the facts set they cite and the time)
    and records the `debrief` step with it; a finished Debrief answers its stored summary
    unchanged. 409 `debrief_incomplete` while a reflection question is unanswered or step 4 was
    not read, 409 `test_deadline_passed` after the Student's Test deadline, 403
    `explanation_required` before the Explanation."""
    return await _answer(service.finish_mine(user, _id(debrief_id)))


@router.get(
    "/debriefs/{debrief_id}/quiz",
    response_model=QuizOut,
    responses=documented(401, 403),
    operation_id="getMyQuiz",
)
async def get_my_quiz(debrief_id: str, user: OWN) -> Response:
    """Step 5, the Debrief quiz (Story 9.9, FR-46): the version the Class session pinned, the
    questions of the Student's next attempt without the answer key (none once passed; the order
    may change between attempts), the number of attempts, when it was passed and the latest
    attempt's result. 403 `debrief_required` until the Student has finished the Debrief."""
    return await _answer(service.own_quiz(user, _id(debrief_id)))


@router.post(
    "/debriefs/{debrief_id}/quiz/attempts",
    status_code=201,
    response_model=QuizAttemptOut,
    responses=documented(401, 403, 409, 422),
    operation_id="submitQuizAttempt",
)
async def submit_quiz_attempt(debrief_id: str, body: QuizAttemptIn, user: OWN) -> Response:
    """An attempt at the Debrief quiz (Story 9.9, FR-46, AD-16): scored by the answer key on the
    server and stored once, with each question's result and, for a wrong answer, the explanation;
    every question right records the `quiz_passed` step. Retries are unlimited until the Test
    deadline. 422 `validation_error` unless every asked question is answered once with one of
    its choices, 409 `quiz_passed` once passed, 409 `test_deadline_passed` after the Student's
    Test deadline, 403 `debrief_required` before the Debrief is finished."""
    answers = [(each.question_id, each.choice_id) for each in body.answers]
    return await _answer(service.submit_quiz_mine(user, _id(debrief_id), answers), status=201)


@router.get(
    "/class-sessions/{session_id}/students/{student_id}/debrief-summary",
    response_model=StaffSummaryOut,
    responses=documented(401, 403),
    operation_id="getStudentDebriefSummary",
)
async def get_student_debrief_summary(
    session_id: str,
    student_id: str,
    user: Annotated[authz.Principal, Depends(authz.require("debrief_summaries.read"))],
) -> Response:
    """A Student's Explanation and Debrief summary for the Class's owners and Assistant
    lecturers (Story 9.8, FR-47, AD-12), each null while not sent or not finished: the key
    moments, the reflection answers, the completion time and whether it was after the Debrief
    deadline. 403 `forbidden` for every other caller."""
    found = await service.staff_summary(user, _id(session_id), _id(student_id))
    if found is None:
        raise authz.Forbidden
    return JSONResponse(found.model_dump(mode="json"))


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
