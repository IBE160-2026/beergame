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
