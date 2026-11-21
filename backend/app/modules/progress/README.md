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
- The Trakt reads `service.funnel(session, class_session_id, student_ids)` (Story 7.6): the number
  of Students the caller gives (it passes the registered Students; `progress` never looks them up)
  and how many of them have each of `FUNNEL_STEPS` recorded. Step events only, no AI score or text.
  Cached per Class session in the process; `record_step` drops the entry, and a stamp (number of
  the session's rows and the newest id) shows a step recorded by another process.
- `progress` imports no feature module (`tests/test_imports.py`), so every module may call it.
- Which step Stegene shows as open is computed in the api (`sessions.service.stegene`), never in
  the web app (AD-10).
