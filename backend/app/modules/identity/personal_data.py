"""The personal-data registry (AD-14, Stories 15.1 and 15.2): every table, with how the erasure of
a User handles it, so access and deletion cannot drift apart.

`tests/identity/test_personal_data_registry.py` reads the database metadata and fails unless every
table is listed here; unless every table with a column that names a User has a handling other
than `none`; and unless every `delete` and `clear` table is erased by a part registered with
`identity.erasure`. Story 15.1 («Mine data», FR-75): every table that holds personal data (its
handling is not `none`) is either shown on «Mine data» under one category (`SHOWN`, the
categories of `platform.own_data`, read by its module's `own_records`), or says why it is not
(`NOT_SHOWN`); the test fails for a table with neither or both.

Handlings:

- `anonymise`: the `users` row stays under the same id, with no name, e-mail or password;
- `delete`: the User's rows are deleted;
- `clear`: the User's text in the rows is emptied, the rows stay (counts and costs hold);
- `keep`: the rows stay and keep the User's id, which now names the anonymous User; they hold no
  name, address or free text of the User (Orders, choices, times, marks);
- `none`: the table holds no personal data.
"""

from dataclasses import dataclass, replace
from typing import Literal

from app.ai.calls import CALL_TABLE, TABLES_WITHOUT_PERSONAL_DATA
from app.platform.own_data import Category

Handling = Literal["anonymise", "delete", "clear", "keep", "none"]


@dataclass(frozen=True)
class Entry:
    handling: Handling
    note: str
    category: Category | None = None
    """The «Mine data» category the table's rows are shown under (Story 15.1)."""
    outside: str | None = None
    """Why the table, though it names a User, is not shown on «Mine data» (Story 15.1)."""


def _e(handling: Handling, note: str) -> Entry:
    return Entry(handling, note)


_HANDLED: dict[str, Entry] = {
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
    "invitations": _e(
        "delete",
        "Every Invitation to the User's address; `invited_by` is an id. Retention (Story 15.3): "
        "once every Class session of the Class is deleted (or an archived Class with none has "
        "passed its archive time plus the period), its Student Invitations not accepted go, "
        "through `classes.service.purge_unregistered_roster`.",
    ),
    "roster_entries": _e(
        "delete",
        "The User's Roster entries (address and User id). Retention (Story 15.3): the entries of "
        "addresses that never registered (no User) go with the Class's retention, as above.",
    ),
    "roster_uploads": _e("keep", "A staged upload's header; `uploaded_by` is a staff id."),
    "roster_upload_rows": _e("delete", "Staged rows holding the User's address (student number)."),
    "access_requests": _e("delete", "Requests for lecturer access from the User's address."),
    "institutions": _e(
        "keep",
        "Institution names, who signed its data processing agreement (Story 15.12) and its "
        "retention period (Story 15.3): the Admin's text about the Institution, no User's data.",
    ),
    # classes
    "classes": _e("keep", "`created_by` is an id."),
    "class_staff": _e("delete", "The User's place on Class staff."),
    # sessions
    "class_sessions": _e(
        "keep",
        "`created_by` is an id; `deletion_date` and `data_deleted_at` (Story 15.3) are dates.",
    ),
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
    "completion_corrections": _e(
        "delete",
        "A Lecturer's corrections of the Student's Completion status (Story 13.3): the reason is "
        "free text about the Student. Append-only but for `actor_user_id`, which is an id.",
    ),
    # reports (Epic 13)
    "makeup_games": _e(
        "keep",
        "The Student's Oppfølgingsspill by User id (Story 13.4); `given_by` is an id; no text.",
    ),
    "report_requests": _e(
        "delete",
        "Each Student report request about the Student (Story 13.7); `requested_by` is an id. "
        "The PDFs in the `reports` bucket go first, then the rows.",
    ),
    "report_snapshots": _e(
        "delete",
        "A report's content (the Student's name and work) between the assembler and the print "
        "route, deleted when its render ends; the Student's go with their requests.",
    ),
    "report_zips": _e(
        "keep",
        "A ZIP of all Student reports per Class session (Story 13.13): `requested_by` is an id, "
        "no text. At an erasure the stored ZIPs of the Student's Class sessions are deleted and "
        "their paths cleared.",
    ),
    # reports (Story 14.3): Cross-class statistics, kept when retention runs.
    "class_aggregates": _e(
        "none",
        "A Class session's anonymised aggregate header: when it was written, group sizes and the "
        "comparability keys (settings and ids); no User, Seat, Game, name or text. Kept at "
        "retention, which writes it first.",
    ),
    "class_aggregate_measures": _e(
        "none",
        "Scalar figures per measure code over groups of 10 or more Students (smaller groups "
        "withheld, no value); no User, Seat, Game, name or text. Kept at retention.",
    ),
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


SHOWN: dict[str, Category] = {
    # account
    "users": "account",
    "user_roles": "account",
    "test_student_consents": "account",
    "roster_entries": "account",
    # orders and the game
    "seat_weeks": "orders",
    "seat_occupancy": "game",
    "seat_reclaims": "game",
    "believability_ratings": "game",
    "time_proposals": "game",
    "time_acceptances": "game",
    "replays": "game",
    "replay_another_round": "game",
    "replay_walkthroughs": "game",
    "makeup_games": "game",
    # debrief
    "debrief_explanations": "explanation",
    "debrief_reflection_answers": "reflection",
    "debrief_follow_ups": "follow_ups",
    "debrief_follow_up_closures": "follow_ups",
    "debrief_summaries": "debrief",
    "debrief_members": "debrief",
    "debrief_step_marks": "debrief",
    "debrief_alone": "debrief",
    "quiz_attempts": "quiz",
    # tests and assessment
    "starting_task_answers": "starting_task",
    "test_attempts": "test",
    "test_answers": "test",
    "test_prepared_items": "test",
    "ai_assessments": "assessment",
    "ai_item_scores": "assessment",
    "ai_feedback_flags": "assessment",
    "human_scores": "assessment",
    # sessions
    "student_adjustments": "adjustments",
    "student_deadline_extensions": "adjustments",
    "deadline_reminders": "messages",
    # messaging
    "messages": "messages",
    "message_recipients": "messages",
    "notices": "messages",
    "mail_deliveries": "messages",
    # progress
    "progress_steps": "completion",
    "completion_corrections": "completion",
}
"""The tables «Mine data» shows, by category (Story 15.1, FR-75)."""

_STAFF = "Names a User only as the staff member who acted (an id); the Student's data is not here."
NOT_SHOWN: dict[str, str] = {
    "password_resets": "A hashed one-time link and its times; no content of the User.",
    "invitations": "Invitation links to the address; the Class it led to is shown by the Roster "
    "entry under the account.",
    "roster_uploads": _STAFF,
    "roster_upload_rows": "A staff member's staged upload, purged within the day; the entry it "
    "made is shown under the account.",
    "access_requests": "A request for lecturer access, not a Student's data.",
    "institutions": "The Institution and who signed its agreement: the Admin's text, no Student.",
    "classes": _STAFF,
    "class_staff": "A staff role in a Class, not a Student's data.",
    "class_sessions": _STAFF,
    "allocation_drafts": "The Lecturer's draft of the Seats before the lock; the Seats the "
    "Student held are shown under the game.",
    "lab_hours": _STAFF,
    "games": "The Game itself (settings, lifecycle); the Student's Seats and Orders are shown.",
    "game_summaries": "A cache of every Seat's occupant, rebuilt from `seat_occupancy`, which "
    "is shown.",
    "debrief_sessions": "The Debrief of a Game; the Student's membership and steps are shown.",
    "debrief_fact_sets": "Which computed facts set the Debrief cites: no data the Student gave.",
    "quiz_exclusions": _STAFF,
    "test_selections": _STAFF,
    "test_scoring_guides": _STAFF,
    "test_sittings": _STAFF,
    "assessment_switches": _STAFF,
    "control_test_scorers": "A named scorer of a Control test: a staff role.",
    "content_records": "Pinned content of the product and the Lecturer's Scoring guide text.",
    CALL_TABLE: "The AI calls' scrubbed bodies and costs; what an answer said is shown in its "
    "category (follow-ups, AI assessment, narration).",
    "evaluation_agreements": _STAFF,
    "pseudonym_key_fingerprints": _STAFF,
    "report_requests": "The Student report's requests by ids; the report itself is downloaded at "
    "the top of «Mine data».",
    "report_snapshots": "A report's content between the assembler and the print route, deleted "
    "when its render ends; one a killed render left is purged by the sweep once its token expires "
    "(`reports.render.TOKEN_LIFETIME`, five minutes). The report is downloaded at the top.",
    "report_zips": _STAFF,
    "audit_events": "Ids and codes of actions (AD-14): the audit trail, no content.",
}
"""The tables that hold personal data and are not shown, each with the reason (Story 15.1)."""

REGISTRY: dict[str, Entry] = {
    name: replace(entry, category=SHOWN.get(name), outside=NOT_SHOWN.get(name))
    for name, entry in _HANDLED.items()
}
