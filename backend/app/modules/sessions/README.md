# `modules/sessions`: Class sessions

Owns `class_sessions` (Story 5.1). Other modules import only `sessions.service`.

## Create and save (Story 5.1)

- `POST /api/classes/{class_id}/class-sessions` («Lag Klasseøkt») stores one Class session in one
  transaction. It holds the engine's Classic `GameSettings()` with a demand seed drawn by
  `engine.demand.new_seed` (JSONB with `schema_version`), AI mode `llm`, Debrief mode `group`, an
  Inactivity limit of 24 h and not obligatory. When `ai.config.active_default()` finds a config,
  that config id is stored and `ai.budget.set_budget(BudgetScope.class_session(id))` creates the
  budget row. Without one, AI mode is `rule_based` with no config and no budget, and the answer
  carries `llm_unavailable: "no_default_model"`.
- `PUT /api/class-sessions/{id}` («Lagre Klasseøkt») takes `{ai_mode}`, sets `saved_at` and emits
  `session:<id>`. When `llm` is asked for a session with no config, it attaches the active default
  and its budget in the same transaction. If there is no default, it answers 409
  `llm_unavailable` and changes nothing.
- `GET /api/class-sessions/{id}` and `GET /api/classes/{class_id}/class-sessions` are for the
  Class's owners and Assistant lecturers.

## Rules

- No Classic value is written here or in the web app. `service.is_classic` compares with
  `GameSettings()` and ignores the seed.
- One guard, `service._writable`, asks `classes.service.is_writable(class_id, session=s)` inside
  every mutating transaction and raises `classes.service.ClassArchived` (409 `class_archived`).
- Who may do what: the `platform/authz` actions `class_sessions.read` (owner, Assistant lecturer)
  and `class_sessions.manage` (owner), checked against the User's staff role in the Class.
  Answers come in this order: 403 `forbidden` (one answer for everything the User may not reach),
  then 409.
- The model config is referenced by id only. It is frozen (`ai.config.mark_referenced`) by the
  Start-date lock (Story 5.11), not here.

## Dates (Story 5.2)

- `class_sessions` holds `start_at`, `play_deadline`, `debrief_deadline` and `test_deadline`
  (migration 0033), UTC and NULL until set. A CHECK keeps every pair that is set in order.
- «Lagre Klasseøkt» takes `dates` with all four (instants with an offset, or null). Without
  `dates` they stay. The rules, in this order: 409 `session_locked` for a changed AI mode once
  locked; 409 `deadline_passed` for a changed date that has passed (the Start date too); 422
  `invalid_dates` for a changed date not in the future (`past`) or cleared once locked
  (`required`); 422 `invalid_dates` for the later date of a pair out of order (`order`).
  Unchanged dates are never judged.
- A save that changes a date emits `user:<id>` for each registered Student of the Class.
- `service.is_locked(class_session)` is the one lock predicate: the Start date has passed.
  `effective_debrief_deadline` and `effective_test_deadline` are the only way another module
  reads a Student's deadline (Epic 11 adds per-Student values inside them).
- `play_time_warning` needs `MIN_PLAY_MINUTES_PER_WEEK` (unset until SM-11), and is false
  while it is unset.
- `GET /api/me/class-sessions`: a Student's sessions with dates and `next_deadline`, scoped by
  `authz.classes_enrolled_by`; never the Game settings.
- `GET /api/lecturer-home/class-sessions`: the Lærerhjem's «Venter» (sessions lacking a date)
  and «Neste frist» (the next date), over the User's Classes that are not archived, scoped by
  `authz.classes_visible_to`.
- Each session has a `number` within its Class, oldest first (Issue #98).

## Game settings (Story 5.3)

- «Lagre Klasseøkt» takes `game_settings`: the settings with an engine range
  (`service.EDITABLE_SETTINGS`), laid over the stored settings. Any other key (the seed, the
  chain, the Demand pattern until Story 5.4, capacity until 5.15) is `not_editable`. The
  engine alone judges the rest (`GameSettings.model_validate`, then `engine.validate` with
  `FEATURE_CAPACITY`). A refusal is
  422 `invalid_settings` with `fields: {setting: {code, minimum, maximum, decimal_places}}`, the
  bounds as decimal strings or null. A value of the wrong type is `not_a_number`, one below zero
  `out_of_range`, both with the setting's `RANGES` bounds.
- `POST /api/class-sessions/{id}/settings-check` judges a draft the same way and answers
  `{errors, warnings}`; it stores and emits nothing. The screen calls it as the Lecturer leaves a
  field.
- Once locked, changed settings and every check answer 409 `session_locked`
  (`{"game_settings": "locked"}`); settings resent unchanged still save.
- The order of a save: archived, locked, `invalid_settings`, then the dates.
- `ClassSessionOut` carries `settings_warnings` (the engine's warnings on the stored settings;
  a setting with an error gets no warning in a check) and `calibrated_settings` (the Classic
  preset, which the screen names as what content and Play guard were calibrated for).
