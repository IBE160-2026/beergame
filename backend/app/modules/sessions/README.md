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
  (`service.EDITABLE_SETTINGS`), laid over the stored settings. Any other key (the chain) is
  `not_editable`. The
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
- Capacity (Story 5.15, cut list): `game_settings.capacity` is the engine's `{role: units}` or
  null; the screen caps one Role or every Role. Errors are `capacity.<role>` (`out_of_range`,
  `not_a_number`, range 1 to 100) or `capacity` `invalid` (unknown Role, not a map); below peak
  demand the engine warns (`capacity_below_peak_demand`). `ClassSessionOut.capacity_enabled` is
  `FEATURE_CAPACITY`. Off, a non-empty capacity that differs from the stored one answers 422
  `feature_disabled` (`{"capacity": "feature_disabled"}`; in a check, an error with that code;
  409 `session_locked` first once locked) and the screen shows nothing about capacity. A
  capacity stored while the flag was on is kept (left out or sent back unchanged), does not block
  other settings, and is frozen by the lock like every setting; null clears it.
- Information visibility (Story 5.16, cut list, FR-83): `game_settings.info_visibility` is the
  engine's `{upstream, downstream}`, two booleans, both off by default (`GameSettings` schema
  version 2; settings stored as version 1 read with both off). Anything else is
  `info_visibility` `invalid`. `ClassSessionOut.info_visibility_enabled` is
  `FEATURE_INFO_VISIBILITY`. Off, a view switched on that differs from the stored value answers
  422 `feature_disabled` (`{"info_visibility": "feature_disabled"}`; 409 `session_locked` first
  once locked) and the screen shows nothing about it; switching views off is always allowed. The
  lock freezes it into every Class game's snapshot, which `seat_state`, the LLM prompt and the
  Decision log read; filling the neighbour numbers is Story 6.21's.
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

## Obligatory mark and Inactivity limit (Story 5.7)

- `class_sessions.required_share_percent` (migration 0036): «Andel uker som kreves», a whole
  percent, CHECK 1 to 100. A new session gets `COMPLETION_DEFAULT_SHARE_PERCENT` (placeholder 80).
- «Lagre Klasseøkt» takes `obligatory`, `required_share_percent` and `inactivity_limit_hours`;
  each left out keeps its value. A changed share outside 1 to 100 or limit under 20 answers 422
  `invalid_session_values` (`out_of_range`, `below_minimum`); once locked a changed one answers
  409 `session_locked`. Unchanged values are never judged.
- Switching the mark on enqueues one `class_session_obligatory` notice per registered Student
  (`ref` = the Class session, the moment in its key), a digest kind whose mail reads
  `service.obligatory_mail_context` at send time and is left out when the mark is off again, the
  Class is archived or the User is no longer a registered Student. Switching off tells nobody.
- `service.required_share(class_session)` is the one source of the share for Story 8.9 and
  Epic 13; this module computes no Completion with it.

## Allocation draft (Story 5.8)

- `allocation.allocate(student_ids, seed)` is pure and deterministic: the ids sorted, shuffled with
  the seed, four at a time into games 1, 2, …, each group with its own shuffle of the Roles. When
  the count is not divisible by four, only the last group has one to three Students.
- `allocation_drafts` (migration 0037): one current draft per Class session (unique), with its id,
  `revision` (1 when drawn), seed, assignments (`user_id`, game number, Role; ids only) and who drew
  it. The preview always shows this row; it is never recomputed.
- `GET …/allocation` reads it (staff, Assistant lecturers too) with `registered_count`,
  `missing_count` (registered after the draw) and the Students' names resolved now through
  `classes.service.student_names`. `POST …/allocation` returns the stored draft or draws one;
  `POST …/allocation/redraw` replaces it under a new id. With no registered Student nothing is
  stored. Once locked both answer 409 `session_locked`; an archived Class 409 `class_archived`.
- A draw emits `session:<id>` only: no Game, Seat or notice exists before Story 5.9 confirms it.

## Confirming the allocation (Story 5.9)

- `POST …/allocation/confirm` with `{draft_id, revision}` commits the draft the Lecturer is looking
  at under the Class session's row lock, in one transaction: one Class game per group through
  `games.commands.create` (purpose `class`, the session id and game number, no settings; the
  snapshot comes at the lock) and one `student` Seat per Student through `games.commands.assign_seat`
  (`within=` the transaction). Empty Seats stay free until the lock. The draft gets `confirmed_at`
  and `confirmed_by` (migration 0038), each Student an `allocation_confirmed` digest notice (ids
  only; the mail names the Class, never the game or Role), and the staff `session:<id>`.
- 409 `allocation_changed` commits no Game: `{"draft": "changed"}` for another id or revision,
  `{"draft": "students_removed"}` when Students left the Roster since the preview; their Seats are
  then taken out of the draft (emptied games dropped, the rest numbered from 1, revision + 1; with
  nobody left the draft is removed). A second confirm of the confirmed draft changes nothing. Once
  locked 409 `session_locked`; a redraw of a confirmed allocation 409 `allocation_confirmed`.
- The Lærerhjem's «Venter» names each session by what it lacks (`lacks`: `dates`, `allocation`); a
  session lacks its allocation until it is confirmed or the session is locked.

## Moving and swapping Students (Story 5.10)

- `POST …/allocation/move` with `{draft_id, revision, from_game, from_role, to_game, to_role}`: the
  Student of the first Seat takes the second; a Student there takes the first (a swap). The draft
  keeps its id, its revision rises by one, and `session:<id>` is emitted. It works before and after
  the confirmation, until the lock (409 `session_locked`). A stale id or revision answers 409
  `allocation_changed`; a move the draft cannot take 422 `invalid_move` (`fields`: `to: same`,
  `from|to: unknown`, `from: empty`, `from: last_student` — a game is never left without a
  Student).
- Once confirmed, the same transaction runs `games.commands.move_seat` on the Class games (locked
  in id order; a Seat left free gets an occupancy row with no kind and reason `moved`, migration
  0039), and each Student who moved gets the `allocation_confirmed` notice again, keyed
  `allocation_confirmed:{draft}:{revision}:{user}`. The draft is always what the Seats hold. A
  refusal of the command answers its own code (such as 409 `game_already_started`).
- `AllocationOut.confirmed_at` gives the panel «Fordelingen er bekreftet {dato}.».

## The Start-date lock (Story 5.11)

- `class_sessions.locked_at` and `snapshot` (migration 0040, set together by a CHECK). The sweep's
  due action `sessions.lock` finds the sessions whose Start date has passed and that are not locked
  (`service.due_locks`) and runs `service.lock_due` on each, one per transaction with its id.
- `service.lock(class_session_id, now=)` locks whatever the date (Epic 8's early start calls it):
  under the row lock it stores `build_snapshot` (keyed like `games.SNAPSHOT_COLUMNS`: `settings`,
  `demand_series`, `demand_seed`, `rules_version`, `session_runtime`), marks the model config
  referenced (LLM players), sets `locked_at` and emits `session:<id>`. A second call changes nothing.
- `session_runtime` is a `games.SessionRuntime` built by `games.commands.default_runtime`: AI mode,
  Effort level, model config id, its `prompt_versions`, the Inactivity limit, today's Rule-based and
  Play guard sets, and `pins`, filled by every provider registered with
  `service.register_pin_provider(name, provider)` (Epics 6, 9, 10 and 11 add theirs; Story 6.3
  registers `starting_task` → `{"version": N}` from `content`).
- `service.own_game_session(user, game_id)` (Story 6.3): the Class session of the Student's own
  locked game and its pinned Starting task version, under `student_game_of`'s checks; the
  Starting task routes in `modules/tests` use it.
- With LLM players and a config that may not answer here (`ai.config.may_answer`: in production
  the mock config, or a provider whose key is not set) the lock raises `ProviderKeyMissing`
  (`provider_key_missing`) and stores nothing. Each owner of the Class and each active Admin gets
  one immediate `class_session_lock_refused` notice (key per session and User); the mail is left
  out once the session has locked. The next sweep tries again; it never falls back to Rule-based.
  The first refusal sets `lock_refused_at` (migration 0044); the read's `lock_refused` is true
  while it is set and `locked_at` is not, and the Klasseøkt says so to the owner. A refused session
  of an archived Class is left out of `due_locks` until the Class is restored (GitHub issue 109).
- `is_locked` is true from `locked_at` as well as from a passed Start date. The read adds
  `locked_at`.
- The sweep also runs `identity.purge_expired_roster_uploads` each minute.

## Opening the Class games (Story 5.12)

- With no confirmed allocation, the lock's own transaction first draws one from the registered
  Students (`allocation.allocate`, fresh seed, a new draft with `drawn_by` NULL, an unconfirmed
  preview replaced) and commits it as «Bekreft fordeling» does (`confirmed_by` NULL, the
  allocation notices). Not for an archived Class, and not with no registered Student.
- After the lock commits, `service.open_games` hands the session's `snapshot` to each Class game
  without one through `games.commands.set_snapshot`, one Game per transaction, by game number.
  That command fills every free Seat, and every Seat of a Student no longer registered, with the
  AI mode's player (`llm` or `rule_based`, reason `initial`) in the same transaction. A Game that
  has its snapshot is never changed.
- `lock` runs `open_games` also when the session was locked already, and `due_locks` also returns
  locked sessions with a Class game still waiting, so an open cut short is finished next minute.
- `GET …/allocation` answers `opened: true` once every Class game has its snapshot; its games are
  then the Class games as their Seats hold them (a Student, or none for «KI-spiller») with each
  game's `lifecycle`.

## Late registrants and removed Students (Story 5.13)

- Two more sweep due actions, after `sessions.lock` (the removal first, so a late registrant can
  take the Seat it frees in the same minute), one Student per transaction with
  `(class_session_id, user_id)` only. `classes` imports nothing from here.
- `sessions.seat_late_registrant` (`service.late_registrants` → `seat_late_registrant`): a
  registered Student without a Seat in a Class session whose allocation is confirmed. Before the
  lock: a random free Role of a random Class game with a free Seat, or, when every Seat is taken,
  a new Class game (next number, no settings) whose other Seats get AI players at the open. After
  the lock: a random Seat an AI player holds in an opened Class game that has not started,
  through `games.commands.assign_seat` with `replace` (the AI row stays). A game that started
  meanwhile refuses under its row lock and is skipped. Between the Start date and the open
  nobody is seated. The draft gains the Seat (revision + 1), the Student gets the
  `allocation_confirmed` notice keyed by that revision, they and the game's other Students get
  `user:<id>`, the staff `session:<id>`. The finder returns only Students it can seat now, so
  no item fails or repeats each minute; it still reads the Class games and the Roster of every
  confirmed session that is not locked or has an opened game not started.
- `sessions.replace_removed_student` (`service.removed_students` → `replace_removed_student`):
  once locked, a Student no longer registered who holds a Seat in an opened Class game that has
  not started; the Seat gets the AI mode's player (`llm` with a model config in the snapshot,
  else `rule_based`, reason `initial`). Before the lock the open does it (Story 5.12). A game
  that has started is left for the Lecturer's Takeover (Epic 8).
- Neither acts for an archived Class, an unconfirmed allocation or a Student already handled.
- `service.students_without_seat(class_session_id)`: the registered Students holding no Seat in
  the session's Class games (Epic 13's make-up). Once locked, `GET …/allocation` names them in
  `without_seat`; a removed Student's Seat in a started game keeps its id with no name.

## Deadline reminders (Story 5.14)

- `deadline_reminders` (migration 0041): one row per deadline time the Students were reminded
  of, unique on `(class_session_id, deadline, deadline_at)`. Ids and times only.
- The sweep's last due action, `sessions.send_deadline_reminder`
  (`service.due_deadline_reminders` → `send_deadline_reminder(class_session_id, deadline, now=)`),
  takes `(class_session_id, deadline)` for each Play, Debrief or Test deadline at most 24 hours
  ahead (`now < at <= now + 24 h`) with no row at its current time, in a Class that is not
  archived. Under the session's row lock it records the row and enqueues one `deadline_reminder`
  notice per Student of `reminder_recipients`, keyed
  `deadline_reminder:{session}:{play|debrief|test}:{deadline time}:{user}` with the row as `ref`.
  A second sweep finds nothing. A moved deadline has a new time, so it is reminded again.
- `service.reminder_recipients(class_session_id, deadline)`: every registered Student of the
  Class, sorted. The one place recipients are chosen; Epic 11 (extensions) and Epic 13
  (`progress.has_step`) narrow it without changing the sweep.
- The kind is `digest` in `messaging.delivery`; `deadline_reminder_mail_context` reads at send
  time the Class's name, the deadline, its Europe/Oslo time and the obligatory mark, and drops the
  notice when the deadline moved from the reminded time or has passed, the Class is archived or
  the User is no longer registered. Template `kinds/deadline_reminder.{txt,html}.j2` (draft copy).
- A Student who registers after a reminder went out gets none for that deadline. Reminders go out
  whether or not the session is locked.

## Student choice (Story 5.17, cut list)

- `class_sessions.allocation_method` (migration 0042): `random` (Stories 5.8 to 5.13, the default)
  or `student_choice`. «Lagre Klasseøkt» takes `allocation_method`; left out it stays. A change to
  `student_choice` answers 422 `feature_disabled` while `FEATURE_STUDENT_CHOICE` is off, 409
  `session_locked` once locked and 409 `allocation_confirmed` once an allocation is confirmed, so
  Student choice is final once saved. `ClassSessionOut` carries `allocation_method` and
  `student_choice_enabled` (the flag).
- Saving it, in one transaction: a confirmed draft with no Seat replaces any preview (the
  Lærerhjem, the lock and Story 5.13 then see a confirmed allocation), `ceil(registered / 4)`
  empty Class games through `games.commands.create`, and one `student_choice_open` digest notice
  per registered Student (key per session and User; mail read at send time by
  `student_choice_mail_context`, left out once locked). The draft mirrors the Seats from then on;
  a Seat the lock or Story 5.13 drew is marked `drawn` in it.
- `GET|PUT /api/me/class-sessions/{id}/seat-choice` («Velg spill og sete», `read_enrolled`): 404
  `not_found` while the flag is off, for a random session and for anyone not a registered Student
  of its Class. The PUT takes `{game_number, role}` under the session's row lock: a free Seat
  through `assign_seat`, or a move through `move_seat` for a Student who holds one; 409
  `seat_taken`, 422 `invalid_seat`, 409 `session_locked`. Each change emits `user:<id>` for every
  registered Student and `session:<id>`.
- The sweep's `sessions.offer_student_choice` (after the late registrants): each registered
  Student of an unlocked Student-choice session without the notice gets it, with more empty Class
  games while the registered and seated Students outnumber the Seats. Story 5.13 seats nobody in
  such a session before the lock. Nothing is offered while the flag is off.
- The lock draws each registered Student without a Seat into a random free Seat (a new Class game
  when none is free), with the allocation notice; the open then fills the rest with AI players.
  `GET /api/me/class-sessions` carries `seat_choice_open` and, once locked, `drawn_seat`.
- `GET …/allocation` answers `method`; with Student choice its games are the Class games as their
  Seats hold them from the save on, empty ones included.

## Rerun (Story 5.18, cut list)

- `GET /api/classes/{class_id}/class-sessions/copy-sources` (`class_sessions.manage` on the
  Class): every Class session of every Class the User is staff of (`authz.classes_visible_to`),
  archived Classes included, newest first, with Class name, number, Start date and `archived`.
- `POST /api/classes/{class_id}/class-sessions/copy` `{source_id, keep_seed}` («Lag kopi»):
  `service.copy_from` makes a new Class session in the Class, in one transaction as «Lag
  Klasseøkt»: the source's stored `game_settings` (never its snapshot) with a fresh demand seed
  unless `keep_seed`, its AI mode, Debrief mode and Inactivity limit; the active default model
  config with its budget row, never the source's. With LLM players the source's Effort level is
  kept when the new config offers it, else the config's default is taken and the source's level
  is stored in `effort_level_replaced` (migration 0043); with no active default the copy gets
  Rule-based players. A capacity or a view whose flag is off now is left out, and the engine
  judges the result again (422 `invalid_settings`). Not copied: dates, Lab hours, the Roster, the
  allocation (method `random`, no draft), the obligatory mark and its share. `copied_from` names
  the source (SET NULL when it goes).
- A source the User may not read, or an id that names nothing, answers 403 `forbidden`; an
  archived target 409 `class_archived`. While `FEATURE_RERUN` is off both routes answer 422
  `feature_disabled` (`{"rerun": "feature_disabled"}`) and `ClassSessionListOut.rerun_enabled`
  is false.
- `ClassSessionOut` carries `copied_from` (`{id, class_name, number}`, null once the source is
  gone or no longer readable) and `effort_level_replaced` (`{name, label}`, the label from the
  source's config). `copy_from` copies Epic 5's settings only; the later stories that own more
  session settings add theirs to it.

## The Student's Hjem (Story 6.1)

`GET /api/me/class-sessions` is the Student's home endpoint. Besides the dates, Lab hours and
Obligatorisk mark it carries, per Class session:

- `game`: the Student's Class game once the session `is_locked` (also after a confirmed
  allocation, never before the Start date): number, Role and the four Seats Fabrikk first, read
  through `games.service.student_game` (the one way any module finds a Student's game) and
  `games.service.table_status`, with names from `classes.service.student_names` at read time. An
  AI player is `ai`, with no name and no kind.
- `steps`: Stegene's six steps (`class_game`, `debrief`, `quiz`, `replay`, `test`, `report`) with
  `done` / `current` / `locked`, computed by `service.stegene` from `progress.steps_of`. With no
  game every step not done is `locked`.

`GET /api/me/games/{game_id}` (`games.read_own`) answers the same card for the Student's game (the
one `student_game` gives, joined through `authz.own_seat`) in a locked session of a Class that is
not archived; any other id, also a game the Student left in a move before the start, answers 403
`forbidden`, the same whether or not the game exists.

## «Regler før første ordre» (Story 6.2)

The game card (both endpoints above) also carries `briefing_first`, true until `progress` has
`starting_task` for the Student in that Class session (nothing is stored for "briefing read"), and
`rules`: the order, shipping and production delays, the number of Veiledede uker and the two cost
rates, read by `service.game_rules` from the session's frozen `snapshot['settings']` (or its
`game_settings` until the lock has stored the snapshot; a locked session no longer changes them).
Never the number of Weeks, the demand, its seed or the largest Order (FR-14, AD-3).
