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
  (`service.EDITABLE_SETTINGS`), laid over the stored settings. Any other key (the chain,
  capacity until 5.15) is `not_editable`. The
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

## Demand pattern and seed (Story 5.4)

- `game_settings` takes `demand` (the engine's pattern: `fixed`, `step`, `random`,
  `step+noise`) and `demand_seed`, judged like the rest. Errors inside the pattern are keyed
  `demand.<field>` with the `DEMAND_RANGES` bounds (the change Week: 1 to the Weeks); a pattern
  with no known `kind` or an unknown key is `demand` `invalid`. The seed is the one drawn at
  creation until the Lecturer sends another (0 to `SEED_MAX`).
- `GET /api/class-sessions/{id}/demand-series` (`class_sessions.read`): `{demand: [...]}`, the
  series `engine.demand_series` materialises from the stored settings. No Student-facing answer
  carries the series, the seed or the Weeks.

## AI mode, Effort level and Debrief mode (Story 5.5)

- `class_sessions.effort_level` (migration 0034) holds a level name of the session's model
  config; a CHECK keeps it NULL unless the AI mode is `llm`. Creation stores the default level
  (the first of `ai.config.offered_effort_levels`). A row with LLM players stored before 0034
  reads the default.
- «Lagre Klasseøkt» takes `effort_level` and `debrief_mode` (`group`, `personal`); left out, they
  keep their values. With `rule_based` the level becomes NULL and a sent one is ignored. With
  `llm` the level is the sent one, else the one in force, else the default; a changed level the
  config does not offer is 422 `invalid_effort_level` (`{"effort_level": "not_offered"}`). Once
  locked, a changed AI mode, Effort level or Debrief mode is 409 `session_locked` with each named.
- The read adds `effort_level`, `effort_levels` (offered by the session's config, or by the active
  default while it has none: `name`, the config's `label` and `effect` line, `default`, and the
  newest counting measurement's median seconds per Order and cost per game), `ai_descriptions`
  (`players.service.describe` of `llm` and `rule_based`) and `provider_unavailable` (LLM players
  on a config that offers no level here: in production, a provider key that is not set).
- No level name, label or effect line and no description is written here or in the web app.

## Lab hours (Story 5.6)

- `lab_hours` (migration 0035): `starts_at`, `ends_at` (UTC; CHECK end after start), `place`
  (1 to 120 characters), `revision`, `cancelled_at`. A removed Lab hour is kept, cancelled, and
  never listed again, so its cancellation notice (ids only) can still name it.
- `POST /api/class-sessions/{id}/lab-hours` (201), `PUT …/lab-hours/{lab_hour_id}` (200) and
  `DELETE …/lab-hours/{lab_hour_id}` (204) save on their own, not with «Lagre Klasseøkt», for the
  Class's owners, before and after the Start date. The rules: 403 `forbidden`, then 409
  `class_archived`, 409 `lab_hour_ended` (it has ended), then 422 `invalid_lab_hour` with
  `place` `required`/`too_long` and `ends_at` `not_after_start`/`too_long` (over 12 h)/`past`.
  Times count to the whole minute and the place is trimmed. An unchanged PUT changes nothing.
- Each change emits `session:<id>` and enqueues one notice per registered Student
  (`classes.service.registered_students`) with `ref` = the Lab hour: `lab_hour_added`,
  `lab_hour_changed` (its key holds the revision) or `lab_hour_cancelled`. All three are digest
  kinds in `messaging.delivery`; their mail reads the Lab hour at send time through
  `service.lab_hour_mail_context`, which leaves a notice out when the User is no longer a
  registered Student, the Class is archived, the Lab hour has ended, or an added or changed one
  was removed.
- The staff read carries `lab_hours` (`ended` marks those over); `GET /api/me/class-sessions`
  carries each session's Lab hours that have not ended.
- `service.current_lab_hour(class_session_id, now)` is the Lab hour on at `now` (the earliest
  started if several), or None: Epic 8's «I rommet» asks this, never the table.
