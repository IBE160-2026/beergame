# `modules/reports`: Completion and Student reports (Epic 13)

Story 13.1 adds the shared pieces; later stories add the Studentside, corrections, the Student
report and the exports.

- `service.completion_status(user_id, class_session_id)` is the one Completion assembler (FR-17,
  AD-16). It gathers the inputs through `progress.service.step_events`,
  `sessions.service.completion_terms` / `get_adjustment`, `games.service.student_game` /
  `seat_log`, `debrief.service.explanation_length` and `tests.service.attempt_status` /
  `parts_with_content`, and calls the pure `app.analysis.completion`. None for an unknown Class
  session or a User outside `scope.reporting_students`. Corrections (Story 13.3) are not stored
  yet, so none are passed.
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

## Waiting for Epic 12 on this branch

Control test Class sessions (`kind=control_test`, Story 12.7) and test students
(`is_test_student`, Story 12.8) are built in Epic 12. `scope` reads them through two hooks,
`register_control_test_sessions` and `register_test_students`, that default to "none". At the
merge with Epic 12, register the real reads from `sessions.service` and `identity.service` here
(in `scope.py`). The staff list of AI assessments (Story 12.5) should then read its Students
through `scope.reporting_students`.
