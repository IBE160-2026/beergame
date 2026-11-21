# Epic 10 Context: Replay

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

After passing the Debrief quiz, a Student plays one Replay alone, in the same Role, against three AI players, under a Replay scenario that differs per Student (harder than the Class game, not playable from memory). It runs on the existing play screen with an added projection line, ends with Total cost, and is followed by a short walkthrough comparing it with the Class game. A Lecturer can keep the default Replay scenario or set every Game setting. The epic owns `backend/app/modules/replay/` and `frontend/src/modules/replay/`, creates `purpose=replay` Games through `games.commands`, and reuses Epic 6's play screen and Epic 9's facts, renderer and validator.

## Stories

- Story 10.1: Get a default Replay scenario that differs per Student
- Story 10.2: Set the Replay scenario freely
- Story 10.3: Start the Replay after passing the Debrief quiz
- Story 10.4: Play the Replay with the projection line
- Story 10.5: Finish the Replay and unlock the next step
- Story 10.6: Close unfinished Replays at the Test deadline
- Story 10.7: Read the Replay walkthrough
- Story 10.8: Rate how believable the AI players were
- Story 10.9: Let Information visibility differ in the Replay (cut list, behind `FEATURE_INFO_VISIBILITY`)

## Requirements & Constraints

- A Student who has passed the Debrief quiz can start the Replay any time before their Test deadline, in the same Role as in the Class game, with three AI players in the Class session's AI mode. They can leave and resume on any device; nobody else holds them up, they wait only for AI answers.
- Default scenario: Class demand levels (4, then 8) with per-Week discrete uniform variation, spread 2; step Week ranged 5-12; Weeks ranged 30-40; no Guided Weeks. Step Week, Week count and future demand stay hidden during play (axis stops at nå + 4). Every Replay draws a fresh demand seed per Student, stored with the Game.
- A Lecturer can accept the default or set every Game setting freely (starting from the Class session's), including the Class game's exact settings. The setup gives non-blocking warnings for changes likely to make the Replay easier (shorter delays, lower or less variable demand, Guided Weeks, more starting inventory, more Information visibility). Settings lock at the Start date; assistant lecturers read only.
- Replay end: last Week runs in full with no earlier hint, then «Replay er ferdig», Totalkostnad, «Gå til gjennomgangen». Finishing records the `replay` step once, idempotently, which unlocks the Individual test.
- Walkthrough: Total cost, a run chart, a Class-game comparison on one axis, one or two specific moments from the Student's own Orders; every number matches the stored Week rows. It must say «Ikke like for like.» (AI neighbours, different demand, possibly shorter run) and never rank, praise or declare a better run. AI text is prefixed «KI-generert, kan ta feil:». With fewer than 10 own Class-game Orders, show at least three Replay moments and omit the Class-order comparison. Code-rendered fallback when AI is off, rejected or slow.
- Two optional questions after the walkthrough: believability (five-point) and wanting another round (yes/no); the believability question is also offered once on «Spillet er ferdig» if a Class game Seat was AI-held. Never blocking; ratings never visible to staff next to a Student name; aggregation is Epic 14.
- Unfinished Replays are closed (not played out by AI) at the Student's Test deadline; no `replay` step is recorded and the Decision log stays intact.
- Accessibility and layout: pass axe at 320/360/1440 px (200 % text), all copy from `frontend/src/copy/nb.ts`, charts have «Vis som tabell».

## Technical Decisions

- `engine.ReplayTemplate` (Pydantic, `schema_version`) holds every `GameSettings` field as a fixed value or whole-number range; `engine.replay_settings(template, seed) -> GameSettings` is the one pure function (no I/O, no clock, all randomness from the seed). `engine.default_replay_template(game_settings)` derives the default, with one rule per Demand pattern kind. Templates are validated with the same validation as Game settings. Closes the spine's deferred "Replay scenario as a template" entry.
- The Class session stores only the choice `default` (a column on `class_sessions`) or an own `ReplayTemplate` (JSONB column); the default is never stored as a copy. A pin provider registered at `sessions.lock` freezes the template into `SessionRuntime`'s open map; Replays read only that frozen template. Copy-from (Story 5.18) also copies the scenario when `FEATURE_RERUN` is on.
- Replay Games snapshot at creation (AD-4): `GameSettings`, demand series, seed, `rules_version` and the Class session's `SessionRuntime` (via `sessions.service.build_snapshot`); only settings, series and seed are the Replay's own. `games.commands.create` may need extending to take a Class session id and a ready snapshot. Seed stored so the engine can replay the Decision log; the finished-game check (FR-29) runs for Replays as for Class games.
- `games.policy` gets a `replay` row: no inactivity Takeover, no Pause, no Play deadline playout, Guided Weeks only if the scenario sets them, not on the Lecturer overview, snapshot at creation, does not record the Class game step, pre-play gate off, and a new `projection` column (on only for replay). `ops.sweep` skips replay Games for Takeover and playout. Commands and views ask policy, never branch on purpose.
- `modules/replay` writes no game table and imports other slices only via their `service.py`. Student's Role and Class game come from `games.service.student_game(user, class_session)`; seats via `games.commands.assign_seat`, then `games.commands.start`; orders only via `place_order`. Cost-limit state makes the AI Seats `rule_based` with reason `cost_limit`. Unique key on Student and Class session gives idempotent start.
- Gates and steps through `progress.has_step` / `progress.record_step(...)` (`quiz_passed` gate, `replay` step); Test deadline only via `sessions.service.effective_test_deadline(user, class_session)` (start refused with `409 test_deadline_passed`, `403 quiz_required` without the quiz).
- New command `games.commands.close(game, reason)` plus a new AD-9 sweep due action: locks the Game row, sets `lifecycle = finished` with `end_reason = test_deadline` (new column on `games`, empty for `finish`), bumps `version`, emits `game:<id>` and `user:<id>`; idempotent, ids only, registry-tested. Running `ai-orders` jobs get `409` and end without an Order. `end_reason` is returned through `games.service` so reports never treat a closed Replay as finished. Closes the spine's deferred "closing Replays at the Test deadline".
- Projection value is display arithmetic in `frontend/src/lib/preview.ts` from `SeatState` fields (Posisjon, incoming order, delay horizon) plus the typed Order; missing fields are added to `games.schemas.SeatState`; Vitest checks against engine-produced golden values. The delay horizon (4 with Classic delays) drives the sentence and the dot column since the Lecturer can change delays.
- Walkthrough: facts from `games.facts.get_or_create` (unchanged `analysis.facts`), moments rendered by `analysis.render` with pinned templates; the walkthrough record stores both `fact_set_id`s. Narration is one idempotent `llm-batch` job keyed by the Replay's `fact_set_id`, via the shared `app/ai` helper (Story 9.14) with purpose `replay_walkthrough`, taking `analysis.validate_ai_text` and a code renderer as arguments. Versioned prompt under `backend/app/ai/prompts/replay_walkthrough/`; a new immutable config row (Story 2.2 command) adds the purpose to the `prompts` map. Page shows a pending state, then falls back to code after a configured wait.
- Simulation: `python -m app.sim` runs on resolved default Replay settings; a `replay_default` profile is added in a new Play guard parameter set version so `analysis.play_guard.is_calibrated` counts the default Replay as calibrated and own scenarios as not.
- Ratings: believability stored once per Student and Game through `games.service` (with purpose and AI mode; second answer `409`); another-round answer stored once per Student and Class session by `modules/replay`; in tables this epic creates.
- Information visibility (Story 10.9) is behind `FEATURE_INFO_VISIBILITY` and Story 5.16; it only extends the template, the form, the warning list and the snapshot; no earlier story depends on it.

## UX & Interaction Patterns

- Klasseøkt Replay block: Valgknapper switch between default and own scenario; the default is described in words (hidden values stay hidden); form reuses the Epic 5 Game settings fields and inline range validation; one column at narrow widths; read-only after Start date, edit controls absent for assistants.
- Stegene wording: locked «Replay, åpnes når du har bestått Debrief-quizen.»; in progress «Fortsett Replay, Uke 9.»; AI-held Seats named «KI-spiller» from first view; finished shows done plus next step available. After the Test deadline a closed Replay says it was closed at the Testfrist and is not finished.
- Replay uses the Epic 6 play screen unchanged (Kjedebånd, Graf over tabell, Ordrefelt, Setestatus), with no Pausevalg or «Sett inn KI-spiller»; AI rows show «venter» while waiting. Posisjon row and line show in both Class game and Replay; only the Replay adds the dashed `projection` line ending in a hollow dot at nå + 4, with the sentence «Den stiplede linja viser netto lager om fire uker: 3 + 24 − 4 × 8 = −5 hvis ordre inn holder seg. Ikke garantert.» The line is `aria-hidden`, distinguished by dash and marker, not colour alone; the sentence is the text alternative.
- Only a Retailer sees customer demand, one Week at a time. Replay-gjennomgang states: pending «Gjennomgangen lages.» in a Skjelett of the chart; ready; code fallback with the same chart and numbers. Rating scale is a labelled radio group, keyboard operable, options at least 44 px, end points labelled in words. Finish screen has one primary button and uses the shared number formatter.

## Cross-Story Dependencies

- 10.1 (template model, default derivation, pin provider) underpins 10.2, 10.3 and 10.9; 10.2 reuses Epic 5's settings form and `sessions.service.copy_from` (5.18, flagged).
- 10.3 needs Epic 5 (5.9 policy snapshot column, 5.11 `sessions.lock`/`build_snapshot`, `effective_test_deadline`), Epic 6 (6.1 `student_game`, 6.18 policy columns), and Epic 2.10 for guard calibration; it adds the `replay` policy row and `projection` column that 10.4 reads.
- 10.4 reuses the Epic 6 play screen; 10.5 relies on Epic 6's finished-game check and `progress`; 10.6 adds `games.commands.close` and the `end_reason` column, which 10.7 and 10.8 rely on (closed Replays get no walkthrough or rating prompt).
- 10.7 depends on Epic 9 (`analysis.facts`, `analysis.render`, `analysis.validate_ai_text`, Story 9.14 shared `app/ai` helper); 10.8 aggregates later in Epic 14 and adds a shared component on the «Spillet er ferdig» screen; 10.9 depends on cut-list Stories 5.16 and 6.21 and is skippable.
