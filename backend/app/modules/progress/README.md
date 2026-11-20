# `modules/progress`: the steps a Student has done (AD-16)

One table, `progress_steps`: one row per User, Class session and step from the closed catalogue
`starting_task`, `class_game`, `explanation`, `debrief`, `quiz_passed`, `replay`,
`test_submitted`, `assessment_ready` (Story 6.1).

- A module records a step only through `service.record_step(user_id, class_session_id, step, at,
  within=...)`. It is idempotent on `(user, class_session, step)`: the first call stores the row
  and emits `user:<id>` and `session:<id>` (registry `progress.record_step`); a repeat stores and
  emits nothing and returns False.
- Gates are read only through `service.has_step(...)`, or `service.steps_of(session, user_id,
  class_session_ids)` for many sessions at once.
- `progress` imports no feature module (`tests/test_imports.py`), so every module may call it.
- Which step Stegene shows as open is computed in the api (`sessions.service.stegene`), never in
  the web app (AD-10).
