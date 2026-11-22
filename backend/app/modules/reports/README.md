# `modules/reports`: Completion and Student reports (Epic 13)

Story 13.1 adds the shared pieces, Story 13.2 the Studentside's record, Story 13.3 corrections;
later stories add the Student report and the exports.

- `service.completion_status(user_id, class_session_id)` is the one Completion assembler (FR-17,
  AD-16). It gathers the inputs through `progress.service.step_events`,
  `sessions.service.completion_terms` / `get_adjustment`, `games.service.student_game` /
  `seat_log`, `debrief.service.explanation_length` and `tests.service.attempt_status` /
  `parts_with_content`, and calls the pure `app.analysis.completion`. None for an unknown Class
  session or a User outside `scope.reporting_students`. A Lecturer's corrections
  (`progress.service.corrections`, Story 13.3) are passed oldest first; the latest per step
  applies.
- `service.funnel(class_session_id)` is the Oversikt's Trakt: `progress.funnel` over
  `scope.reporting_students`. It counts step events, never the requirement.
- `scope.reporting_games(session, class_session_id, purposes=None)` and
  `scope.reporting_students(session, class_session_id)` leave out `lecturer_test` and `simulation`
  Games, Control test Class sessions and test students (AD-13, AD-27). A Replay is a reporting
  Game, with its `end_reason`.
- `sessions` imports nothing of `reports`: Hjem and the Oversikt reach the assembler and the
  funnel through `sessions.service.register_completion`, called when this module is imported
  (`app/main.py` imports it). `tests/test_imports.py` holds the rule.

The minimums are configuration, `COMPLETION_EXPLANATION_MIN_LENGTH` (50 characters, trimmed) and
`COMPLETION_TEST_REQUIRED_PARTS` (`choice,interactive,long,adapted`), both placeholders
[ASSUMPTION: these minimums].

## The Studentside's record (Story 13.2)

- `GET /api/class-sessions/{id}/students/{user_id}/record` (`routes.py`, `studentside.py`), policy
  `student_page.read`: the Lecturers and Assistant lecturers of the Class, reached through
  `sessions.service.student_target(..., "student_page.read")`. 403 `forbidden` is one answer for
  everyone else, an Admin without a staff role included, and for a User who is no Student of the
  Class now (FR-5). `Cache-Control: no-store`.
- It reads each part through the owning module's `service.py`: `completion_status` (above), the
  game (`games.student_game`, `play_status`, `finished_at`, `seat_timing`), the Explanation, the
  Debrief summary and the quiz attempts (`debrief.staff_summary`), the Replay
  (`replay.replay_game_of`), the Individual test (`tests.attempt_summary`: status, time, which
  parts hold content, never an answer) and the AI assessment's switch (`assessment.switch_of`).
- Participation (time on own Orders, constant Orders) is the pure `app.analysis.participation`:
  information only, never an input of `analysis.completion` (FR-17).
- `assessment` is `off` or `not_ready` on this branch. At the merge with Epic 12, Story 12.5's
  «KI-vurdering» block takes this part's place on the page (`frontend/src/modules/reports/
  record-blocks.tsx`); no Indicative letter is ever in this response (FR-56, AD-12).
- `report` is always None: the slot Story 13.12 fills with the Student report link.

## Corrections (Story 13.3)

- `POST /api/class-sessions/{id}/students/{user_id}/corrections` (`correctCompletion`,
  `corrections.py`), policy `completion.correct`: the Lecturers of the Class only. Body `{step,
  done, reason}`; 422 `invalid_correction` (`fields.reason` `required` or `too_long`, over 1000
  characters after trimming), 409 `not_obligatory`, 409 `class_archived`, 403 `forbidden` for
  everyone else. Answers the Studentside's record.
- One transaction: a new row through `progress.service.record_correction`, one audit row
  `completion.corrected` (target `class_session_id`, `user_id`, `correction_id`; change `step`,
  `done`, `was_done`: ids and codes, never the reason), and `user:<student>` and `session:<id>`
  (registry `reports.correct_completion`). No step event: gates and the funnel stay as they are.
- The record carries the latest correction per step (`correction`: status, reason, time, the
  Lecturer's name now) and `can_correct`. Hjem's Stegene gets only `corrected` (no reason).
- The reason is free text about a Student: personal data in `completion_corrections`.

## Oppfølgingsspill (Story 13.4)

- `POST /api/class-sessions/{id}/students/{user_id}/makeup` (`giveMakeup`, `makeup.py`), policy
  `makeup.give`: the Lecturers of the Class only. 409 `session_not_locked` (no frozen snapshot),
  `no_test_deadline`, `test_deadline_passed` (the Student's effective one, app clock),
  `class_archived`; 403 `forbidden` for everyone else. Answers the Studentside's record.
- One transaction under the session row's share lock: `games.commands.create("makeup",
  snapshot=<the session's frozen snapshot, unchanged>)`, `assign_seat` (the Student's Class game
  Role or a drawn one; AI players of the session's AI mode in the others), a `makeup_games` row
  (this module's table, `repo.py`; one per Student and Class session, a second press answers it),
  audit `makeup.given` (target `class_session_id`, `user_id`, `game_id`; change `role`), the digest
  notice `makeup_given`, and `user:<student>`, `session:<id>` (registry `reports.give_makeup`).
- Not started: the Student starts it from Hjem (`EnrolledSessionOut.makeup`) after the pre-play
  gate. `games.policy` `makeup` closes it at the Test deadline through the sweep's
  `games.close_at_test_deadline`; it records no `class_game` step until Story 13.5.
- Completion: `completion_status` passes the make-up's Decision log beside the Class game's
  (`reporting_games(…, [Purpose.MAKEUP])`); `share_game` names the game the figures come from.
- `service.py` registers `repo.makeup_game_of` with `sessions` (Hjem, the mail); the worker loads
  `reports.service` through `jobs.TASK_MODULES`.
- `makeup_games` holds `user_id` and `given_by`: personal data.

## Waiting for Epic 12 on this branch

Control test Class sessions (`kind=control_test`, Story 12.7) and test students
(`is_test_student`, Story 12.8) are built in Epic 12. `scope` reads them through two hooks,
`register_control_test_sessions` and `register_test_students`, that default to "none". At the
merge with Epic 12, register the real reads from `sessions.service` and `identity.service` here
(in `scope.py`). The staff list of AI assessments (Story 12.5) should then read its Students
through `scope.reporting_students`.
