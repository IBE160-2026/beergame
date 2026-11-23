# `modules/reports`: Completion and Student reports (Epic 13)

Story 13.1 adds the shared pieces, Story 13.2 the Studentside's record, Story 13.3 corrections,
Story 13.7 the Student report's pipeline; later stories add its sections and the exports.

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
- `service.requirement_not_met(class_session_id)` (Story 13.6) is the reporting Students of an
  Obligatory class session whose `completion_status` has not met the requirement, with that
  status; empty when the Class session is not obligatory. `messaging` calls it (on use, not at
  import) for the Message recipient `requirement_not_met`, when the form is read and again when
  the Message is sent, so the Oversikt's Lenke, the form's table and the recipients agree.
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
  `student_pages.read`: the Lecturers and Assistant lecturers of the Class, reached through
  `sessions.service.student_target(..., "student_pages.read")`. 403 `forbidden` is one answer for
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
- The record has no report field: the Studentside's report block reads `getStudentReport` (Story
  13.12).

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
  `makeup.give`: the Lecturers of the Class only. 409 `not_counted` (a Student outside
  `scope.reporting_students`; `refusal` also decides `can_give_makeup`), `session_not_locked` (no frozen snapshot),
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
  `games.close_at_test_deadline`.
- Completion: `completion_status` passes the make-up's Decision log beside the Class game's
  (`games.class_game_of`, then `reporting_games(…, [Purpose.MAKEUP])`); `share_game` names the
  game the figures come from.
- Story 13.5: finished by its last Week, the make-up is the Student's game
  (`games.service.student_game`): its finish records `class_game`, and the Debrief, the Replay,
  the Adapted items and the record's game read it. The record marks it `game.makeup`.
- `service.py` registers `repo.makeup_game_of` with `sessions` (Hjem, the mail); the worker loads
  `reports.service` through `jobs.TASK_MODULES`.
- `makeup_games` holds `user_id` and `given_by`: personal data.

## The Student report (Story 13.7)

- `GET|POST /api/me/class-sessions/{id}/report` (`getMyReport`, `requestMyReport`) and `GET
  …/report/file` (`downloadMyReport`), policy `reports.download_own`: the Student's own locked
  Class session (`sessions.own_report_session`), one 403 for everything else. It opens at the
  Student's effective Test deadline (`sessions.report_opens_at`): before it, or with none, 409
  `report_not_open`; 409 `not_counted` outside `scope.reporting_students`; `/file` 409
  `report_not_ready` without a ready PDF, else 303 to a signed URL (`SIGNED_URL_TTL_SECONDS`).
- `report.py`: a press inserts a `report_requests` row (one `pending` per Student, Class session
  and variant, a partial unique index) and defers `reports.render_report(request_id)` on
  `reports-single` in the same transaction; it emits `user:<student>`. A pending request older
  than `REPORT_STALE_SECONDS` reads `failed` and gives way to the next press (failure `stale`).
- `render.py` (the job): `report_data.build_report_data`, the only assembler, then a
  `report_snapshots` row (the data, the SHA-256 of a single-use token, 5 minutes), WeasyPrint
  `pdf/ua-1` of `WEB_INTERNAL_URL/print/report/<id>?token=…` (same origin only), the PDF to
  `platform/storage` at `class-sessions/<cs>/<user_id>/student-report.pdf` in the `reports`
  bucket, the request `ready` or `failed` (`render_failed`, `not_reportable`), the snapshot
  deleted in every case, and `user:<student>`. Logs carry ids and the error type only.
- `snapshot.py` and `GET /api/internal/report-snapshots/{id}` (header `X-Render-Token`): the print
  route's one read, once; 404 for anything else. The proxy refuses `/api/internal/*`.
- Sections: `report_data.SECTIONS` (`kind` → builder) in step with the print route's `SECTIONS` in
  `frontend/src/app/print/report/sections.tsx`. This story has the header and `completion`;
  Story 13.8 adds `game`, 13.10 `debrief`, `replay`, `test`, 13.11 the AI assessment option and
  its variant (stored under its own object name).
- Personal data: `report_requests` (`user_id`, `requested_by`), `report_snapshots` (the name and
  the content, for one render only).

## The staff's download of one Student's report (Story 13.12)

- `GET|POST /api/class-sessions/{id}/students/{user_id}/report` (`getStudentReport`,
  `requestStudentReport`) and `GET …/report/file` (`downloadStudentReport`), policy
  `reports.download` (owners and Assistant lecturers of the Class), reached through
  `sessions.student_target(…, "reports.download")`: one 403 for everyone else, nothing written.
  Open at any time (`open` true, `opens_at` None); 409 `not_counted`, `report_not_ready`,
  `ai_assessment_unavailable` as for the Student's own.
- Same press (`report._press`) and job. Variants `staff` and `staff_ai`, shared by the staff of
  the Class and apart from the Student's own requests and objects. `staff_ai` adds the AI section
  when the reader may `ai_assessments.read` and the assessment is ready; never the Indicative
  letter (`ReportOptions.letter` is `ai_letter` only, and the render asks the gate as not the
  Student).
- A staff press writes the audit row `report.requested` (target `class_session_id`, `user_id`,
  `request_id`; change `variant`) and emits the requester's `user` topic; the render's end emits
  the requester's only, never the Student's.

## The ZIP of all Student reports (Story 13.13)

`bundle.py`, routes `getReportsZip`, `requestReportsZip`, `downloadReportsZip` under
`/api/class-sessions/{id}/reports/zip`, for the Klasseøkt's «Eksport» block.

- Policy `reports.download` on the Class (Lecturer, Assistant lecturer) through
  `sessions.staff_session_row`: one 403 for everyone else, nothing written. 409 `no_students`
  when reports count no Student, `data_deleted` once the deletion date has come,
  `zip_not_ready` for the file without a ready ZIP.
- Table `report_zips` (one pending per Class session, `REPORT_ZIP_STALE_SECONDS` 900 before a
  pending one reads failed); job `reports.build_zip(zip_id)` on `reports-bulk`. It renders every
  Student of `scope.reporting_students` with `bundle.OPTIONS` (variant `staff`: never the AI
  section or the letter, whatever the press sent), `REPORT_ZIP_CONCURRENCY` (3) at once, through
  the snapshot (`report_snapshots.zip_id`), print route and converter of the single report.
- Files inside are named by the Student's name (`bundle.file_names`); the object path
  `class-sessions/<id>/bundles/student-reports-<zip_id>.zip` and the download name
  `studentrapporter-klasseokt-<n>.zip` hold none. Once ready the earlier ZIPs' objects go.
- A Student no longer reportable is left out; any other failure fails the ZIP
  (`render_failed`), never a partial one. A job for a ZIP no longer pending is skipped.
- Audit rows `report_zip.requested` and `report_zip.downloaded`; the press and the job's end
  emit the requester's `user` topic; a ready ZIP enqueues `reports_zip_ready` (immediate mail)
  to the requester.

## The Completion export (Story 13.14)

`GET /api/class-sessions/{id}/completion-export?format=csv|xlsx` (`downloadCompletionExport`,
`completion_export.py`), for the Lecturers of the Class only (`completion.export`; an Assistant
lecturer, anyone else and an unknown session get 403; 409 `data_deleted`). One row per Student in
`scope.reporting_students`, every status value from `service.completion_statuses` (the one
assembler per Student), names and addresses from `identity.service.student_contacts` at the time
of the download. The columns are the fixed allow-list `COLUMNS` (no AI data, C-2). The CSV is
UTF-8 with BOM, `;`, `dd.mm.yyyy` and the decimal comma; the .xlsx holds date and number cells;
a formula-like text stays text in both. Built now and sent, never stored (AD-14); one audit row
`completion_export.downloaded` with the format and the number of Students. `ZipStateOut.completion_export` tells the
«Eksport» block whether to offer it.

## The Game data export (Story 14.8, cut list)

`GET /api/class-sessions/{id}/game-data-export` (`downloadGameDataExport`, `game_data_export.py`)
exists only while `FEATURE_GAME_DATA_EXPORT` is on (AD-17): off, it answers what an unknown route
answers, before any policy. For the Lecturers of the Class only (`game_data.export`; 403 for
everyone else; 409 `data_deleted`). One row per Decision log row (Game, Week, Seat) of every Game
`scope.reporting_games` counts: Class games, make-up games and Replays, the purpose in its own
column; a make-up game or a Replay is numbered within its purpose. The columns are the fixed
allow-list `COLUMNS` (no AI data, no name or id). The quantities and `cost` are what the Seat saw
when it ordered (`state_seen`: the Week's cost on its end-of-Week balances); `mark` is the one
AD-15 mapping (`games.seat_mark`) of the row, so a Seat taken over carries its mark on every Week
the AI player ordered in, not only the first. Headers and values are stored codes; the dialect is the Completion export's
(`completion_export.csv_lines`). Read in one query whatever the number of Games
(`games.game_data_rows`), streamed, never stored; one audit row `game_data_export.downloaded` with
the number of Games and rows. `ZipStateOut.game_data_export` tells the block whether to offer it.

## Waiting for Epic 12 on this branch

Control test Class sessions (`kind=control_test`, Story 12.7) and test students
(`is_test_student`, Story 12.8) are built in Epic 12. `scope` reads them through two hooks,
`register_control_test_sessions` and `register_test_students`, that default to "none". At the
merge with Epic 12, register the real reads from `sessions.service` and `identity.service` here
(in `scope.py`). The staff list of AI assessments (Story 12.5) should then read its Students
through `scope.reporting_students`.
