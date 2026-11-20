# Epic 5 Context: Class session setup and allocation

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Let a Lecturer set up a Class session in a few minutes and have its Class games open by themselves at the Start date. When this epic is done, a Lecturer can create a Class session already filled with the Classic defaults, change any Game setting, the Demand pattern and seed, AI mode, Effort level and Debrief mode, mark it obligatory, set the Inactivity limit, the four dates and Lab hours, and preview, confirm and adjust a random allocation of registered Students into Class games of four. At the Start date the sweeper locks the Class session and gives every Class game the same frozen snapshot, with AI players in the empty Seats. The epic owns `backend/app/modules/sessions/` and `frontend/src/modules/sessions/`. It adds due actions to the existing per-minute `ops.sweep` and adds the `class` row to `games.policy`. Epics 6, 8, 9, 10, 11 and 13 build on its service functions.

## Stories

- Story 5.1: Create a Class session with the Classic defaults
- Story 5.2: Set the four dates on the Datolinje
- Story 5.3: Change Game settings with range errors and warnings
- Story 5.4: Choose a Demand pattern and its seed
- Story 5.5: Choose AI mode, Effort level and Debrief mode
- Story 5.6: Add Lab hours
- Story 5.7: Mark the Class session obligatory and set the Inactivity limit
- Story 5.8: Preview a random allocation and run it again
- Story 5.9: Confirm the allocation I am looking at
- Story 5.10: Move or swap Students in the allocation
- Story 5.11: Lock the Class session at the Start date
- Story 5.12: Open the Class games on the frozen snapshot
- Story 5.13: Seat Students who register after the allocation
- Story 5.14: Remind Students 24 hours before each deadline
- Story 5.15: Set a shipping capacity (cut list, `FEATURE_CAPACITY`)
- Story 5.16: Set Information visibility (cut list, `FEATURE_INFO_VISIBILITY`)
- Story 5.17: Let Students choose a Class game and a Seat (cut list, `FEATURE_STUDENT_CHOICE`)
- Story 5.18: Create a Class session from an earlier one (cut list, `FEATURE_RERUN`)

## Requirements & Constraints

- **Defaults:** a new Class session uses the engine's Classic `GameSettings`: inventory 12, 4 per supply-line slot, delays 2/2/2, demand 4 stepping to 8 in Week 5, costs 0.50/1.00, 36 Weeks, Guided Weeks 1 to 4. It also gets AI mode LLM players, Debrief mode Group debrief, an Inactivity limit of 24 h, not obligatory, and a server-drawn demand seed. Saving it unchanged must work. A Playwright flow from the Klasse page to a saved session with no edits is the product's part of the under-10-minutes target.
- **No pinned model in production:** the session is created without a model config or budget row, its AI mode is stored as Rule-based, and the API returns a flag with the reason. Choosing LLM players is refused with a stable code until a default exists. When the pinned provider has no key, the API returns a flag so the screen can warn before the Start date.
- **Validation is the engine's.** All `GameSettings` and Demand pattern validation and warnings come from the engine, with stable codes and allowed ranges in `fields`. Errors block saving; warnings never block.
- **Dates:** Start date < Play deadline < Debrief deadline < Test deadline. They are stored UTC and shown in Europe/Oslo. Testfrist is prefilled 7 days after Debrieffrist. New dates in the past are rejected. After the start only deadlines that have not passed can move (`409 deadline_passed`), and the Start date cannot move once it has passed. A minimum-playing-time warning stays hidden while its config value is unset.
- **Inactivity limit:** whole hours, at least 20 (default 24), enforced by the API.
- **Obligatory:** the switch label «Ja, står i emneplanen» is the whole confirmation. «Andel uker som kreves» is a whole percent from 1 to 100, defaulting to `COMPLETION_DEFAULT_SHARE_PERCENT` (placeholder 80). Completion itself belongs to Epic 13.
- **Lock points:** once the session is locked, Game settings, Demand pattern, seed, AI mode, Effort level, Debrief mode, obligatory mark, share and Inactivity limit are read-only, and their routes answer `409 session_locked`. Deadlines and Lab hours stay editable.
- **Allocation:** only registered Students are allocated, placed at random in groups of four with random Roles. At most one group has 1 to 3 Students. Every empty Seat gets «KI-spiller». A Student holds at most one Seat per Class session. After confirmation only move and swap are offered. If nothing is confirmed by the Start date, the lock allocates at random by itself.
- **Late registrants and removals:** a late registrant is seated within about a minute. Before the Start date they go into a free Seat, or a new Class game is created if none is free. After the lock they take an AI-held Seat in a game that has not started, or are listed as without a Seat when none remains. A removed Student's Seat in a game that has not started goes to an AI player. A game that has started is left for the Lecturer's Takeover in Epic 8.
- **Student-facing data** (`GET /api/me/class-sessions`) returns dates, the next deadline, upcoming Lab hours and the obligatory flag. It never returns Game settings, the number of Weeks, the demand series or the seed.
- **Mail:** Lab hour, obligatory, allocation and deadline-reminder notices are `digest` kinds: at most one mail per User per day and none between 22:00 and 07:00 Europe/Oslo. Templates are in Norwegian bokmål and never name the number of Weeks or use «Beer Game» or «bullwhip».
- **Accessibility:** Playwright with axe at 320, 360 and 1440 px, and at 400 % zoom for the Klasseøkt. The screen is one column below 1024 px with no page-level horizontal scroll, every state is in text and never colour alone, and tap targets are at least 44 px.

## Technical Decisions

- **Tables owned by `sessions`:** `class_sessions` (UUIDv7; `GameSettings` JSONB with `schema_version`; seed; model config id; dates; `locked_at`; frozen snapshot), `lab_hours` and `allocation_drafts` (draft id, `revision`, seed, assignments as `user_id`/game number/Role, drawn-by; ids only, no names or emails).
- **Single sources:** default values come only from the engine's Classic preset. The web app holds no demand logic, no validation rules and no second copy of the defaults. Effort levels, their default and their effect lines are data in the model config, read through `ai.config.offered_effort_levels`. AI player descriptions come from `players.service.describe(kind)`.
- **Guards:** one write guard asks `classes.service.is_writable` before every mutation (`class_archived`). `sessions.service.is_locked` is the one lock predicate: true once the Start date has passed or `locked_at` is set.
- **Service functions other epics call:** `effective_debrief_deadline`, `effective_test_deadline` (Epic 11 adds per-Student extensions inside them), `current_lab_hour` (Epic 8), `required_share` (Story 8.9 and Epic 13), `lock` (Epic 8's early start), `build_snapshot`, `students_without_seat` (Epic 13), `reminder_recipients` (later narrowed with `progress.has_step`) and `copy_from`.
- **Budget:** creating the session also creates its budget row through `ai.budget` in the same transaction. `games.service.budget_scope` answers the Class session for Class games.
- **Allocation:** `sessions.allocation.allocate(student_ids, seed)` is pure and deterministic. The preview is the stored server-side draft and is never recomputed. Confirm takes the draft id and `revision` and answers `409 allocation_changed` when they are stale. Edits raise `revision`. A Student removed since the preview updates the draft and commits nothing. Confirm is idempotent.
- **Games changes (AD-2):** only `games.commands` touch games. Games are created with `purpose=class` and no settings. A new `games.policy` column says whether a game takes its snapshot at creation or at the lock, and the `class` row takes it at the lock. `start` answers `409 game_not_ready` until a snapshot exists. Additions:
  - a `student` occupant kind, with a nullable `user_id`, in Seat occupancy
  - `class_session_id` and `game_number` on `games`
  - `move_seat`, which locks games in id order
  - `set_snapshot`, one game per transaction, which fills empty Seats with the AI occupants the AI mode gives (reason `initial`)
  - an explicit replace argument on `assign_seat`, accepted only while a game is `not_started`
- **Lock (AD-4, AD-23):** in one transaction the lock sets `locked_at` and freezes `GameSettings`, the demand series with its seed, `rules_version` and `SessionRuntime` (AI mode, Effort level, Inactivity limit, model config id, prompt versions). It also includes an open map of pinned content versions filled from registered pin providers. With LLM mode in production and no provider key, the lock is refused (`provider_key_missing`) and retried each minute, and Lecturer and Admin are notified once; it never falls back to Rule-based. A lock interrupted half way is finished by the next sweep without changing games that already have a snapshot.
- **Sweeper (AD-9):** add due actions to `ops.sweep` only: `sessions.lock`, `identity.purge_expired_roster_uploads`, `seat_late_registrant`, `replace_removed_student` and `send_deadline_reminder`. Each takes one item per transaction with id-only arguments and is idempotent. No other cron or sweeper is added.
- **Notices and events:** notices go only through `platform/notify.enqueue` with dedupe keys. The deadline reminder key includes the deadline time, so a moved deadline gets a new reminder. Every mutation emits `session:<id>`, `user:<id>` or `game:<id>` with entries in the event registry. Authorization uses `platform/authz` policies and scope helpers; Assistant lecturers see the Klasseøkt read-only and get permission-denied on create.
- **Cut-list stories** sit behind `FEATURE_*` flags. When a flag is off, the API answers `feature_disabled` (or not found for the Student-choice route) and nothing else changes. Story 5.16 adds the Information visibility field to `engine.GameSettings` with a `schema_version` bump, read as off for older rows.

## UX & Interaction Patterns

- **Klasseøkt:** the title is «Klasseøkt for {klassenavn}», with «Alt er fylt ut med standardene.» (hidden once anything differs from Classic), «Spillinnstillinger: Klassisk» and the delay-source line. «Lagre Klasseøkt» is the primary button. While the allocation panel is open, «Bekreft fordeling» is primary and «Lagre Klasseøkt» shows as secondary. Choices take effect only on save. A failed save shows «Det ble ikke lagret. Prøv igjen.» with `role="alert"`, keeps focus and keeps the values. All copy is in `nb.ts`, with draft copy marked for review.
- **New shared components in `frontend/src/components/`:** Valgknapper (active segment `ink` with `paper` text, inactive segments with an `ink-muted` border), the two-segment Visningsbryter and Bryter (on in `ink`, `rounded.full`, text label beside it). All have keyboard operation, the shared focus ring and 44 px targets. A Norwegian number formatter goes in `frontend/src/lib/`: space thousands separator, decimal comma, true minus sign. Cost rates are entered with a decimal comma and sent as decimal strings.
- **Errors and warnings:** shown inline under the setting. Errors get a `restordre` border and the allowed range. Warnings are text only.
- **Diagrams of this slice** use hand-made SVG with no chart library and are not AD-18 charts:
  - «Kjeden ved start»: upstream on the left, delay boxes on the pipe, «Varer mot høyre, ordre mot venstre», with a text equivalent.
  - Datolinje: one tick per date, Lab hours as `lager` squares with the legend «Blå firkant: Labtime, {sted}.». It scrolls in its own region below 1024 px, and the fields and the Labtimer list are its text alternative.
  - Fordelingsforhåndsvisning: one column per game by four Role rows in `bar-base`, Fabrikk at the top, the selected column framed in `ink`, under the heading «Fordeling: N Klassespill à 4» and «Tomme seter får KI-spiller.». «Vis som liste» is the alternative view.
- **Allocation panel:** closed, it shows a state line («Ikke bekreftet.» / «Fordelingen er bekreftet.», draft copy) and a Lenke that opens it in place with focus inside. Secondary «Kjør fordeling på nytt». «Ingen får beskjed før du bekrefter.» sits beside confirm. After confirm, focus moves to the state line. Move and swap are labelled buttons naming Student, Role and Klassespill, need no drag, and return focus to the changed row.
- **Lab hours:** the «Legg til Labtime» Lenke opens an in-place form (date, start, end, place).
- **Inactivity limit:** help text «Minst 20 timer. Kortere ventetid kan bare gjelde spill som er i rommet i en Labtime.» The error «Skriv et helt antall timer, 20 eller mer.» uses `role="alert"`.
- **Lærerhjem:** fills the «what is waiting» part (sessions lacking dates or a confirmed allocation) and «next deadline», which Epic 4 left empty.
- **Velg spill og sete** (Student choice): Seats show as «Grossist, ledig» or the holder's name, with primary «Ta setet Grossist i Spill 17». On a conflict, focus moves to «Setet ble tatt av en annen. Velg et annet.» (`tabindex="-1"`).

## Cross-Story Dependencies

- **Within the epic:**
  - 5.1 creates `class_sessions`, the write guard, the screen and the budget link, and everything builds on it.
  - 5.2 adds `is_locked` (used by 5.3 to 5.10 and 5.16), the Student read and the Datolinje that 5.6 extends.
  - 5.3 adds the settings block and number formatter that 5.4, 5.15 and 5.18 reuse.
  - 5.5 adds Valgknapper and Visningsbryter, and 5.7 adds Bryter (used by 5.8 and 5.16).
  - 5.8 creates the draft that 5.9 confirms and 5.10 edits.
  - 5.9 adds the `games` columns, the policy column and the `student` occupant. 5.10 adds `move_seat`, which 5.17 reuses.
  - 5.11 adds `lock`, `build_snapshot` and pin providers. 5.12 adds `set_snapshot` and the replace argument that 5.13 uses.
- **Builds on earlier epics:**
  - Epic 1: engine `GameSettings`, Classic preset, validation, demand, and `games.commands` create/assign_seat/start.
  - Epic 2: `ai.config` and its mock seed, `ai.budget`, `budget_scope` and `llm` occupants.
  - Epic 3: `ops.sweep`, `platform/notify`, the digest delivery, `authz`, events and shared states.
  - Epic 4: `classes.service.registered_students`, `is_writable`, the Lærerhjem slots and Roster removal.
- **Feeds later epics:**
  - Epic 6: `/api/me/class-sessions`, the number formatter, Student start, refetch on events (topic map in Story 6.4), and Starting-task pins.
  - Epic 8: `current_lab_hour`, `lock` for early start, Takeover with the Inactivity limit, `required_share`.
  - Epics 9, 10 and 11: pin providers and `copy_from` additions. Epic 11 also adds per-Student deadline extensions.
  - Epic 13: Completion and `students_without_seat`.
