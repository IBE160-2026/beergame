"""The personal-data registry (AD-14, Stories 15.1 and 15.2): every table, with how the erasure of
a User handles it, so access and deletion cannot drift apart.

`tests/identity/test_personal_data_registry.py` reads the database metadata and fails unless every
table is listed here; unless every table with a column that names a User has a handling other
than `none`; and unless every `delete` and `clear` table is erased by a part registered with
`identity.erasure`. Story 15.1 («Mine data») is to add each table's «Mine data» category in
`category`; until then it is None.

Handlings:

- `anonymise`: the `users` row stays under the same id, with no name, e-mail or password;
- `delete`: the User's rows are deleted;
- `clear`: the User's text in the rows is emptied, the rows stay (counts and costs hold);
- `keep`: the rows stay and keep the User's id, which now names the anonymous User; they hold no
  name, address or free text of the User (Orders, choices, times, marks);
- `none`: the table holds no personal data.
"""

from dataclasses import dataclass
from typing import Literal

from app.ai.calls import CALL_TABLE, TABLES_WITHOUT_PERSONAL_DATA

Handling = Literal["anonymise", "delete", "clear", "keep", "none"]


@dataclass(frozen=True)
class Entry:
    handling: Handling
    note: str
    category: str | None = None
    """The «Mine data» category (Story 15.1); None until that story lists it."""


def _e(handling: Handling, note: str) -> Entry:
    return Entry(handling, note)


REGISTRY: dict[str, Entry] = {
    # identity
    "users": _e(
        "anonymise",
        "Name, e-mail and password replaced; the id stays, and so does `is_test_student` (Story "
        "12.8), a mark of how the account was made, not of the person.",
    ),
    "test_student_consents": _e(
        "keep",
        "A test student's consent decision (Story 12.8): `given` or `declined`, the text version "
        "and the time by User id, kept as the record of the consent; no text of the User.",
    ),
    "user_roles": _e("delete", "The User's account roles."),
    "password_resets": _e("delete", "The User's reset links."),
    "invitations": _e("delete", "Every Invitation to the User's address; `invited_by` is an id."),
    "roster_entries": _e("delete", "The User's Roster entries (address and User id)."),
    "roster_uploads": _e("keep", "A staged upload's header; `uploaded_by` is a staff id."),
    "roster_upload_rows": _e("delete", "Staged rows holding the User's address (student number)."),
    "access_requests": _e("delete", "Requests for lecturer access from the User's address."),
    "institutions": _e("none", "Institution names only."),
    # classes
    "classes": _e("keep", "`created_by` is an id."),
    "class_staff": _e("delete", "The User's place on Class staff."),
    # sessions
    "class_sessions": _e("keep", "`created_by` is an id."),
    "allocation_drafts": _e("keep", "Seat assignments by User id."),
    "lab_hours": _e("keep", "`created_by` is an id; the place is the Lecturer's text."),
    "student_adjustments": _e("delete", "The Student's Tilrettelegging."),
    "deadline_reminders": _e(
        "keep",
        "Which deadline reminder went out per Class session; a Student's own Test deadline "
        "(Story 11.13) names the Student by id.",
    ),
    "student_deadline_extensions": _e(
        "delete", "The Student's own Test and Debrief deadlines (Story 11.13), an accommodation."
    ),
    # games
    "games": _e("keep", "Settings and lifecycle; `started_by` and `paused_by` are ids."),
    "seats": _e("none", "Seats by Role."),
    "seat_occupancy": _e("keep", "Append-only occupancy rows by User id (AD-5)."),
    "seat_reclaims": _e("delete", "The Student's queued Reclaims, before the Takeover."),
    "seat_turns": _e("none", "Turn times per Seat and Week."),
    "seat_weeks": _e("keep", "The Decision log: Orders by Seat, never changed (AD-4)."),
    "game_weeks": _e("none", "Stored Week states (AD-4)."),
    "game_checks": _e("none", "Verification results."),
    "game_summaries": _e("keep", "Occupants and waits by User id."),
    "time_proposals": _e("keep", "`proposed_by` is an id."),
    "time_acceptances": _e("keep", "Acceptances by User id."),
    "believability_ratings": _e("keep", "A one-to-five rating by User id."),
    "fact_sets": _e("none", "Computed facts of a Seat."),
    # debrief
    "debrief_sessions": _e("keep", "`opener_id` is an id."),
    "debrief_members": _e("keep", "Group membership by User id."),
    "debrief_step_marks": _e("keep", "Steps done by User id."),
    "debrief_alone": _e("keep", "Why a Student went on alone, a code."),
    "debrief_releases": _e("none", "When a Debrief was released."),
    "debrief_fact_sets": _e("keep", "Which facts set a Student's Debrief cites."),
    "debrief_explanations": _e("delete", "The Student's Forklaring (free text)."),
    "debrief_reflection_answers": _e("delete", "The Student's reflection answers (free text)."),
    "debrief_follow_ups": _e("delete", "Follow-up questions and the AI answers quoting them."),
    "debrief_follow_up_closures": _e("keep", "When the follow-up closed, by User id."),
    "debrief_summaries": _e("clear", "The copied reflection is emptied; the summary counts."),
    "debrief_ai_texts": _e("none", "AI narration of computed facts, per facts set."),
    "quiz_attempts": _e("keep", "Debrief quiz choices by User id."),
    "quiz_exclusions": _e("keep", "Questions a Lecturer excluded; who excluded is an id."),
    # tests (Starting task)
    "starting_task_answers": _e("keep", "Starting task choices by User id."),
    # tests (Individual test, Epic 11)
    "test_selections": _e(
        "keep", "A Class session's question set selection; `updated_by` is an id."
    ),
    "test_scoring_guides": _e(
        "keep", "The Scoring guide in force per Class session; `updated_by` is an id."
    ),
    "test_sittings": _e("keep", "A Class session's timed sitting; `updated_by` is an id."),
    "test_attempts": _e(
        "keep",
        "The Student's Individual test attempt by User id: the frozen items, times and status; no "
        "text of the Student.",
    ),
    "test_answers": _e(
        "clear",
        "The text of the Student's long and Adapted answers is emptied; the row, its computed "
        "score and its id stay, so the AI and human scores that name it hold.",
    ),
    "test_prepared_items": _e(
        "keep",
        "The Student's prepared Adapted items by User id: wordings of computed facts of their "
        "Game, no text of the Student.",
    ),
    # assessment (AI assessment and Control test, Epic 12)
    "assessment_switches": _e(
        "keep", "The «KI-vurdering» switch and its pin; `stopped_by` is a staff id (Story 12.4)."
    ),
    "ai_assessments": _e(
        "keep",
        "The AI assessment of an attempt by User id: status, a failure code, times and the "
        "Student's own letter opt-in (`letter_chosen`); no text.",
    ),
    "ai_item_scores": _e(
        "clear",
        "The written feedback, which may quote the Student's answer, is emptied; the score and "
        "the row stay.",
    ),
    "ai_feedback_flags": _e(
        "keep", "Which pieces of feedback the Student marked as wrong, a mark per item."
    ),
    "control_test_scorers": _e(
        "keep", "A named scorer of a Control test by User id; `named_by` is an id."
    ),
    "human_scores": _e("keep", "A scorer's score of an answer by `scorer_id`, a number."),
    "scoring_guide_checks": _e("none", "Which Scoring guide a Control test checked, by ids."),
    # progress
    "progress_steps": _e("keep", "Steps reached by User id."),
    # replay
    "replays": _e("keep", "The Student's Replay Game by User id."),
    "replay_another_round": _e("keep", "A yes or no by User id."),
    "replay_walkthroughs": _e("keep", "AI narration of computed facts; no text of the Student."),
    "replay_narrations": _e("none", "AI narration of computed facts."),
    # content
    "content_records": _e(
        "keep",
        "Pinned content. An edited Scoring guide (Story 11.2) is the Lecturer's text about the "
        "questions, made for one Class session (`class_session_id`); it names no Student and "
        "goes with its Class session.",
    ),
    # messaging and notify
    "messages": _e("delete", "Messages written to the Student alone."),
    "message_recipients": _e("delete", "The Student among a Message's recipients."),
    "notices": _e("delete", "The User's notices."),
    "mail_deliveries": _e("delete", "The User's mail deliveries."),
    # ai
    CALL_TABLE: _e("clear", "Scrubbed bodies of calls made for the User; cost rows stay."),
    **{name: _e("none", note) for name, note in TABLES_WITHOUT_PERSONAL_DATA.items()},
    "simulation_batches": _e("none", "Simulation batches."),
    # ops (Story 15.4)
    "evaluation_agreements": _e(
        "keep",
        "An Institution agreement per Class session: who agreed and the controller are the "
        "Admin's text about the Institution; `recorded_by` is an id.",
    ),
    "pseudonym_key_fingerprints": _e("keep", "The key's fingerprint; `set_by` is an id."),
    # ops (Story 15.8): kept when retention runs for the Class session.
    "error_events": _e(
        "none",
        "Per-session error counts: a source, a fixed code, the Class session and a request or "
        "job id; no User, name or text. Kept at retention.",
    ),
    # ops (Story 15.9): not tied to a User or a Class session.
    "db_connection_reports": _e(
        "none",
        "Connection counts per process start (backend and workers); no User, name or text. "
        "The newest ten per process are kept.",
    ),
    # platform
    "audit_events": _e("keep", "Ids and codes only (AD-14)."),
    "rate_limit_counters": _e("none", "Hashed keys in a short window."),
}
