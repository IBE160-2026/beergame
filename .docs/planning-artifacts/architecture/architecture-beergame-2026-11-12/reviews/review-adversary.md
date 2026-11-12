---
review: adversary
target: ../ARCHITECTURE-SPINE.md
date: 2026-11-12
method: For each hole, two units one level down (epic or story) that each obey every AD to the letter and still build incompatibly. Each hole names the pair, what each unit builds, how they clash, severity, and the exact AD text that closes it.
verdict: Not ready for parallel epic work. The spine fixes the hot path (one write path, pure engine, push-invalidate) but leaves the data that sits around it with no owner: open-turn state, snapshot scope and timing, Game creation, step events, budget state and personal-data copies. Two epics built side by side will collide on 10 of the 20 holes below.
---

# Adversarial review: ARCHITECTURE-SPINE.md

## Summary

| # | Hole | Pair | Severity | Likelihood |
| --- | --- | --- | --- | --- |
| H1 | The Seat view carries names and table status into the LLM prompt and the Decision log | Gameplay "who we wait for" vs AI players prompt | Critical | High |
| H2 | When the snapshot is taken and what it covers: Games created at allocation keep settings the Lecturer edits later | Allocation vs Class session setup / Takeover / AI players | Critical | High |
| H3 | AD-13 forbids filtering on `purpose`, so the playout plays out Replays and make-ups | Playout vs Replay / Make-up / Lecturer test Game | High | High |
| H4 | Open-turn state (opened, viewed, wait clock, due times) has no table | Gameplay (Guided Weeks) vs Takeover vs AI fallback vs Lecturer overview | High | High |
| H5 | `version` check and `place_order` idempotency allow spurious 409s and orders credited to the wrong occupant | Student order vs Takeover vs `ai-orders` job | High | High |
| H6 | Game creation, Seat assignment and Replay randomisation are outside the closed command list | Allocation vs Replay vs Make-up vs Lecturer test | High | High |
| H7 | Step events have no table, and the funnel has two owners plus an import cycle | Lecturer overview (in `games`) vs Completion export (in `reports`) | High | High |
| H8 | The cost-limit switch has no representation, and the Order `source` mixes two dimensions | Spending controls vs AI players / Play guard / Completion | High | High |
| H9 | Sweeper and job execution model: inline playout, lost post-commit enqueues, queue starvation | Playout vs AI players vs other sessions' sweeps | High | Medium |
| H10 | The print route's `INTERNAL_TOKEN` bypasses AD-12, so the letter and the AI assessment leak into staff PDFs | Reports vs AI assessment / Indicative letter | High | Medium |
| H11 | Retention misses derived copies (PDFs, quotes, summaries, exports) and runs regardless of aggregates | Retention vs Reports / Assessment / Debrief / Cross-class stats | High | Medium |
| H12 | The AI gateway cannot legally reach its config, budget or Roster; the budget race; cost precision | AI gateway vs Model pinning / Spending controls | Medium | High |
| H13 | The Play guard and the references are computed twice, in two transactions | AI players job vs Decision log (`place_order`) | Medium | Medium |
| H14 | Facts sets are rebuilt, not persisted, so ids and values drift between generation and validation | Individual test (Adapted items) vs AI assessment; Debrief vs Student report | Medium | Medium |
| H15 | Game status has two owners; an Order does not end a Pause; a Student cannot legally take over another Seat | Pause vs Gameplay / Lecturer overview | Medium | High |
| H16 | Test-deadline actions are unordered: auto-submit vs assessment enqueue, extensions, guide freeze, double scoring | Individual test vs AI assessment | Medium | Medium |
| H17 | No topic catalogue: who emits `session:` and what `debrief:<id>` refers to | Gameplay vs Lecturer overview vs Group debrief | Medium | High |
| H18 | Multi-actor aggregates other than the Game have no write-path rule | Group debrief vs Personal-debrief fallback | Medium | Medium |
| H19 | Notifications have no owner: instant mails at night, duplicates, a `games` ↔ `messaging` cycle | Takeover notice vs turn reminders/digests vs Messages | Medium | Medium |
| H20 | AD-12's Admin ban contradicts FR-71 and FR-82 | Pseudonymised export / Control test vs authz | Low | Medium |

Recurring root causes, each closed in its own hole: the AD-2 command list is closed and too small (H4, H6, H15); "never reads live session settings" has no defined exceptions (H2, H8); AD-13's prohibition is wider than reporting (H3); the spine never says when jobs are enqueued relative to commit (H9); and the modules have no declared dependency order (H7, H19).

---

## H1 — The Seat view carries names and table status into the LLM prompt and the Decision log

**Severity:** Critical · **Likelihood:** High · **ADs:** AD-3, AD-6, AD-14, AD-15

**Pair:** Gameplay epic, story "Who the game waits for" (FR-25, FR-34) vs AI players epic, story "LLM player prompt" (FR-31), and the Decision log (FR-67).

- **Gameplay builds:** AD-3 says `seat_view` is "the only producer of in-game data for a Seat". FR-25 data is in-game data: which Seats have ordered, Student names or "AI player", time waited, Takeover and Pause banners. So Gameplay adds `table: [{role, occupant_name, ordered, waiting_since}]` to the `seat_view` object, which keeps it the single producer.
- **AI players builds:** AD-3 says "The LLM player's prompt is built only from this object". The prompt serialiser renders the whole object. AD-6's scrubber covers "every free-text input"; `occupant_name` is a structured field, not free text, so it is not scrubbed.
- **Clash:** Student names go to the LLM provider (PRD §6.1, FR-31), and the prompt tells the model there are four Seats and that it is waiting for people (FR-31: it must not be told). The Decision log stores the object as `state_seen` (AD-3, AD-15). That puts names into `seat_weeks`, which breaks AD-14, and the retention sweep cannot remove them because `seat_weeks` is append-only.

**Close with (AD-3, replace the Rule):**

> **Rule:** `games.views.seat_view(game, seat, week) -> SeatState` is the only producer of the numbers a Seat sees. `SeatState` holds only the FR-23 quantities of the Seat itself, the Week number and the neighbour numbers Information visibility allows. It contains no user ids, names, occupant kinds, other Seats' order status, Pause or Takeover notices, and no Week count or demand series. A separate function, `games.views.table_status(game, viewer)`, holds who has ordered, occupants, names, waiting times and Pause/Takeover notices; it is served to people only, never passed to `ai.run`, and never stored. The Student play endpoint returns `{"seat_state": SeatState, "table": TableStatus}`. The LLM player's prompt and the Decision log's `state_seen` are built from `SeatState` only. A unit test asserts that the `SeatState` schema has no string fields other than closed enums. Full-chain data, the demand series and the number of Weeks are served only by Debrief and insight endpoints, which check AD-12 scope and the Debrief gates (FR-42, FR-43).

**And add to AD-6, step 3:**

> Inputs are declared per purpose as a Pydantic model. Fields marked `FreeText` are scrubbed. Every other field must be an int, Decimal, bool, enum, Role or pseudonymous id, and a plain `str` field that is not marked `FreeText` fails the gateway's input validation.

---

## H2 — When the snapshot is taken and what it covers

**Severity:** Critical · **Likelihood:** High · **ADs:** AD-4, AD-5, AD-9

**Pair 1:** Groups and Class games epic, story "Automatic random allocation" (FR-20) vs Class session setup epic, story "Change game settings" (FR-12, lock at Start date).

- **Allocation builds:** FR-20 runs "in the last week before the Start date". Students and Roles must exist as rows so the Lecturer can review, re-run, move and swap them, so allocation creates `games` and `seats` rows. AD-4 says "When a Game is created it copies a frozen snapshot of its settings", so allocation freezes the settings then.
- **Session setup builds:** FR-12 and AD-4 ("they lock at the Start date") let the Lecturer edit settings until the Start date.
- **Clash:** Games run with settings from before the edit. A re-run allocation, or a late registrant's Game, gets a different snapshot than the others, so FR-13 ("every Class game uses the same demand series") breaks silently. Nothing reconciles the two, because both rules were followed.

**Pair 2:** Inactivity and Takeover epic (needs the Inactivity limit) and AI players epic (needs the AI mode, the Effort level and the pinned model) vs Class session setup.

- Per the Glossary, `GameSettings` holds the game parameters only. AI mode, Effort level, Inactivity limit, Debrief mode, the Debrief hold choice and the model config are Class session settings. AD-4 says "A Game never reads live Class session settings."
- **Takeover builds:** it puts `inactivity_limit` into `GameSettings` to stay AD-4-legal. **AI players builds:** it puts `ai_mode` and `effort_level` into `GameSettings` too. The Consistency Conventions table says `GameSettings` is also the Replay scenario schema, so the Replay scenario can now carry its own AI mode and Effort level, which contradicts FR-15 and FR-78 ("applies to every AI player in the Class session's Class games and Replays").
- Alternatively, an epic reads these live from `class_sessions`, which breaks AD-4, and an Admin model change in the middle of a session would switch running Games to another model (FR-68).

**Close with (AD-4, replace the Rule):**

> **Rule:** A Game's frozen snapshot has two parts, each stored as JSONB with a `schema_version`: `GameSettings` (game rules only, as defined in the Glossary) and `SessionRuntime` (`ai_mode`, `effort_level`, `model_config_id`, `inactivity_limit`, `debrief_mode`, `debrief_hold`). The snapshot is written only by `games.commands.freeze`. Class games are frozen by the Start-date lock, `sessions.lock(class_session_id)`. The sweeper runs it at the Start date, and in one transaction it locks the Class session settings, the Replay scenario and the model binding (AD-6) and freezes every Class game of the session with the same materialised demand series. Games created before the lock, for example by allocation, hold Seats and Roles only and cannot be started. Replays, make-ups and Lecturer test Games are frozen when they are created. After freezing, a Game reads exactly three live values, each through one named function: in-room limit and Pause (its own columns, changed only by commands), per-Student accommodations (`sessions.accommodations(user_id, class_session_id)`, FR-17), and the player budget state (`ai.budget.players_allowed(class_session_id)`, H8). Each Game also stores its demand series with the seed and the engine `rules_version`. The finished-game conservation check (FR-29) replays the engine at that `rules_version` over the stored Orders and must reproduce the stored Week states.

---

## H3 — AD-13 forbids filtering on `purpose`, so the playout plays out Replays and make-ups

**Severity:** High · **Likelihood:** High · **ADs:** AD-13, AD-9, AD-2

**Pair 1:** Inactivity, Takeover and deadlines epic, story "Play deadline playout" (FR-38) vs Replay epic (FR-48) and story "Make-up game" (FR-17, open until the Test deadline).

- **Playout builds:** AD-13 says "No query outside these helpers filters on purpose", and the helpers are reporting-only. The `ops.sweep` playout therefore selects "unfinished Games of Class sessions past the Play deadline" with no purpose filter.
- **Replay and make-up build:** with open Debriefs (the FR-42 default), Replays start before the Play deadline. Make-ups run until the Test deadline.
- **Clash:** at the Play deadline the sweeper plays out every Replay in progress and every make-up, wiping out the Student's Replay and make-up. In the same way, an automatic Takeover sweep that does not filter on purpose takes over a Replay Seat or a Lecturer's test Seat.

**Pair 2:** Lecturer overview (FR-39) vs Lecturer test Game (FR-87). The overview is not a "report, statistic, export, funnel or Completion query", so it does not go through `reporting_games()`, and it is not allowed to filter on purpose. The Lecturer's test Games then appear among the Class games, and in waiting and Takeover highlights. FR-42's "hold all Debriefs until every Class game has ended" never releases while a make-up is open, if make-ups count as Class games.

**Close with (AD-13, replace the last sentence; add a lifecycle policy):**

> AD-13 governs reporting only: no reporting query filters on purpose outside `reports.scope`. Lifecycle behaviour is decided by one function, `games.policy(purpose) -> GamePolicy`, with the fields `takeover_allowed`, `pause_allowed`, `playout_at` (`play_deadline` | `none`), `closes_at` (`play_deadline` | `student_test_deadline` | `none`), `in_overview`, `counts_for_debrief_hold` and `completion_step`. Sweeps, commands and views call `games.policy` and never compare `purpose` themselves. v1 values: `class` → takeover, Pause, playout at the Play deadline, in the overview, counts for the hold, step `class_game`. `makeup` → no takeover, no Pause, no playout, closes at the Student's Test deadline (an unfinished make-up leaves the step not done), in the overview, does not count for the hold, step `class_game`. `replay` → no takeover, no playout, closes at the Student's Test deadline, not in the overview, step `replay`. `lecturer_test` and `control_test` → no takeover, no playout, never close, not in the overview, no step. `[ASSUMPTION: the make-up and Replay close rules; confirm with PM]`

---

## H4 — Open-turn state has no table

**Severity:** High · **Likelihood:** High · **ADs:** AD-2, AD-5, AD-9, AD-15

**Pair:** Gameplay epic, stories "Guided Weeks" (FR-24) and "Activity tracking" (FR-35) vs Inactivity and Takeover epic (FR-36 clock) vs AI players (AD-5 sweeper fallback "whose budget has passed") vs Lecturer overview ("how long it has waited", "approaching Takeover", FR-39).

- AD-15: "Each `seat_week` row is written once, by `place_order`" and holds `opened_at`. Before the Order exists, there is no row. AD-9 says timers "are columns", but not on which table.
- **Gameplay builds:** FR-24 says the Guided Week "advances once every Student in the Class game has opened it". "Opened" is a mutation, but AD-2's command list is closed and has no "viewed" command. So Gameplay either (a) writes `seat_viewed` from the GET endpoint directly, which breaks AD-2 ("none writes the game tables directly"), or (b) follows AD-5 to the letter: "In Guided Weeks … `open_week` places the Order itself in the same transaction". Then all four Guided Orders are placed by `open_week`. That is the last Order of the Week, so the same transaction advances and opens the next Week, and Weeks 1–4 pass in one transaction at `start`. That breaks FR-24 and the briefing flow (FR-84).
- **Takeover builds:** `seats.takeover_due_at`, computed when the first other Student orders. **AI players builds:** `seats.ai_due_at`. **Overview builds:** "waited since" from `max(ordered_at)` in its own SQL, and "approaching Takeover" from `now() - waited > 0.8 * limit` using the session limit.
- **Clash:** the overview's highlight ignores in-room limits and per-Student accommodations, so it disagrees with the sweeper. When the Lecturer marks a game "in the room" after `takeover_due_at` was written, the column is stale and the shorter limit never applies (FR-36). Three epics own overlapping timer columns on `seats`.

**Close with (new AD-20 — Open turns):**

> ### AD-20 — Open turns hold all pending state; due times have one writer
> - **Binds:** FR-24, FR-25, FR-27, FR-35, FR-36, FR-37, FR-39, FR-89, NFR-2, NFR-4; `games`, `players`, `ops.sweep`, overview
> - **Rule:** Each open `(game_id, week, seat_id)` has exactly one mutable `seat_turns` row. `open_week` creates it and `place_order` closes it, and only `games.commands` writes it. Columns: `opened_at`, `viewed_at`, `wait_started_at` (the first Order by another Student Seat that Week), `ai_due_at`, `takeover_due_at`, `staged_order` (Guided Weeks), and the two reference Orders (H13). The new command `view_week(game, week, seat, user)` sets `viewed_at` once. The play endpoint calls it on the first read of a Week. In Guided Weeks, `open_week` stages the fixed Order for Student Seats and places it for AI Seats, and `view_week` places the staged Order, so the Week advances once every Student Seat has viewed it. The due columns are written only by `games.timers.recompute(game)`, a pure function of the snapshot, the Pause columns, the in-room limit and the accommodations. Every command calls it, and so does every accommodation change, through `games.commands.recompute_timers`. Sweeps, the overview and the reminder logic read these columns and never compute a due time themselves. `seat_weeks` stays immutable, and `place_order` copies `opened_at`, `viewed_at` and the references from the turn into it.

**And in AD-2, add to the command list:** `view_week`, `recompute_timers` (see also H6 and H15).

---

## H5 — The `version` check and `place_order` idempotency allow spurious 409s and orders credited to the wrong occupant

**Severity:** High · **Likelihood:** High · **ADs:** AD-2, AD-5

**Pair:** Gameplay epic, story "Place an order" (FR-24) vs Inactivity and Takeover epic, stories "Automatic takeover" and "Manual takeover" (FR-36, FR-37) and the AI players `ai-orders` job.

- AD-2: each command "checks the Game's `version`, increments it". It does not say against what.
- **Gameplay builds:** optimistic concurrency. The client sends the `version` from its last fetch, and the command rejects on a mismatch. In a four-Seat Game every Order from another Seat, and every `view_week`, increments the version. A Student who typed for 20 seconds gets `409 stale_version` and must re-enter. In a 250-player Lab hour this happens all the time.
- **The AI job and the sweeper build:** read-then-increment, with no expected version, so the check is a no-op for them.
- AD-2: "`place_order` is idempotent on the unique key `(game_id, week, seat_id)`". **Takeover builds:** at 14:00:00.1 the sweeper takes over Seat W for Week 12 and enqueues `ai-orders`. At 14:00:00.2 the Student's submit (sent before the Takeover) arrives. The key is still free, so the Student's Order is inserted into an AI-occupied Seat. Then the AI job's `place_order` hits the key and, being idempotent, returns success. Or the reverse happens: the AI orders first and the Student's late submit returns 200 with the AI's quantity, so the UI shows "your Order: 9" for an Order the Student never placed.
- **Clash:** Completion (FR-17, "Takeover Weeks count as not ordered") and the Share of LLM Orders (FR-68) both read the wrong occupant for that Week.

**Close with (AD-2, replace from "It then checks the Game's `version`" to "is never updated."):**

> Callers pass the domain precondition, never a version. For example, `place_order(game_id, week, seat_id, quantity, actor)`, where `actor` is a Student `user_id`, the `ai-orders` job or the sweeper. Under the row lock the command checks that the Game is running and not finished, that `week` is the open Week, that the Seat's occupant for that Week matches the actor's kind (and user for a Student), and that no Order exists. If an Order exists from the same actor with the same quantity, the command returns it (an idempotent retry). Any other existing Order returns `409 order_exists`, and an occupant mismatch returns `409 seat_not_yours`, which the web app maps to "an AI player took over this Seat". Every command increments `version` and emits it in AD-8 events, and reads use it as an ETag; no command rejects on `version`. A confirmed Order is never updated.

---

## H6 — Game creation, Seat assignment and Replay randomisation are outside the closed command list

**Severity:** High · **Likelihood:** High · **ADs:** AD-2, AD-4, AD-5, Conventions (Settings)

**Pair 1:** Allocation (FR-20, FR-21, `sessions`) vs Replay (FR-48, `replay`) vs Make-up (FR-17) vs Lecturer test Game (FR-87, `sessions`).

- AD-2's commands do not include create, assign, move or swap. Each epic therefore writes its own code that inserts `games`, `seats` and the first `seat_occupancy` rows, materialises the demand and copies the snapshot. That is four copies of the AD-4 logic. Allocation's "move or swap Students before the Start date" updates `seats` directly. It is not clear whether that breaks AD-2, because AD-2 says "mutates a Game" without saying whether Seats are part of the Game.

**Pair 2:** Replay epic (FR-49) vs Class session setup.

- Conventions: "`engine.GameSettings` … is the single schema for Game settings and the Replay scenario". FR-49's default varies the step Week (5–12) and the number of Weeks (30–40) per Student. A concrete `GameSettings` cannot express ranges.
- **Replay builds:** it draws the step Week and the number of Weeks in `modules/replay` with `random.randint` before creating the Game. That is legal, since AD-1 only restricts `engine`. **Setup builds:** range fields on `GameSettings` so the Lecturer can edit the scenario. Now Class game settings also accept ranges, and two places draw them.

**Pair 3:** Late registrant (FR-20: "placed in a free AI-held Seat of a Class game that has not started") vs AD-5 occupancy. Allocation appends `(seat, from_week=1, student)` after the existing `(seat, 1, llm)`. Gameplay picks "the occupant at Week N" with `max(from_week) <= N`, which returns two rows. One implementer orders by `id` (UUIDv7, time-ordered by app clock across processes), another by `created_at`. The occupancy table also has no `user_id`, so the Student in a Seat has nowhere to be stored.

**Close with (AD-2, append to the command list):**

> … and the lifecycle commands `create_game(purpose, class_session_id, template, seed, seats)`, `assign_seat`, `swap_seats`, `freeze` (H2), `view_week` (H4) and `recompute_timers`. `create_game` is the only code that inserts a Game, its Seats and their first occupancy rows. Seats and occupancy are part of the Game.

**And (Conventions, Settings row, replace):**

> `engine.ScenarioTemplate` (Pydantic; each field a fixed value or, for the Replay scenario only, a range) is the schema the Lecturer edits for Class session settings and the Replay scenario. `engine.materialise(template, seed) -> (GameSettings, demand_series)` is the only place ranges are drawn. A Game stores the concrete `GameSettings`, never a template. Class session templates reject range fields.

**And (AD-5, first bullet, replace):**

> Every Seat has an append-only occupancy history `(seat_id, seq, from_week, occupant_kind ∈ {student, llm, rule_based}, user_id, reason)`, where `seq` is a per-Seat counter assigned under the Game lock. The occupant for Week N is the row with the highest `seq` among rows with `from_week <= N`. `user_id` is set if and only if `occupant_kind = student`. Before `start`, `assign_seat` and `swap_seats` append rows at `from_week = 1`. After `start`, only Takeover, Reclaim, the Play guard switch, the cost-limit switch (H8) and playout append, always at the current or next Week.

---

## H7 — Step events have no table, and the funnel has two owners plus an import cycle

**Severity:** High · **Likelihood:** High · **ADs:** AD-16, AD-13, Conventions (Module layout)

**Pair:** Lecturer overview (FR-39 funnel; the Capability map places it in `games`) vs Completion export (FR-60, in `reports`), with Debrief, Replay and Individual test as the producers.

- AD-16: the inputs are "the Decision log, the step events (Debrief done, quiz passed, Replay done, test submitted) and the logged corrections". No table, owner, writer or definition of "done" is given.
- **Debrief builds:** `debrief_records.completed_at` (when the summary is stored), and `quiz_attempts.passed`. **Replay builds:** "done" means the Replay Game finished, or the walkthrough was viewed, or the FR-50 optional questions were answered; the spine says nothing. **Reports builds:** a `step_events` table it expects others to write, which nobody does. So the export shows everyone as not done.
- **The overview in `games`** must call `analysis.completion` (AD-16: "The funnel … call[s] it") and `reports.scope` (AD-13). `games` therefore imports `debrief.service`, `replay.service`, `tests.service` and `reports.service`. `debrief` and `reports` already import `games` to read the Decision log. The result is Python import cycles, which the module rule ("other modules' `service.py` only") does not forbid.
- **Clash:** the funnel and the export disagree, which is exactly what AD-16 exists to prevent. FR-17's "which Game counts" after a make-up is also undefined.

**Close with (AD-16, replace the Rule):**

> **Rule:** Step events live in one append-only table, `progress_events(user_id, class_session_id, step ∈ {class_game, debrief, quiz, replay, test_submitted}, game_id, at, late)`, owned by the module `progress`. The owning module writes the event in the same transaction as the state change, through `progress.service.record()`: `games.commands.finish` for each Student Seat of a Game whose `games.policy` step is `class_game` or `replay`; `debrief` when the Debrief summary is stored (FR-47) and when the quiz is passed; `tests` on submit and auto-submit. `analysis.completion(progress_events, seat_weeks, corrections, settings) -> CompletionStatus` is the only definition. It has no AI-assessment input, and when a Student has a `class_game` event for both a Class game and a make-up, the better result counts. `reports` owns the funnel, the Class report, the Completion export and the Student home status, and all of them call it. The live overview is served by `reports.overview`, not by `games`.

**And (Conventions, Module layout, append):**

> Modules form a declared DAG, enforced in CI by an `import-linter` contract: `identity` → `classes` → `sessions` → `progress` → `games` → `players` → `debrief` → `replay` → `tests` → `assessment` → `reports` → `messaging` → `ops`. A module imports only `service.py` of modules to its left. When a module needs a later module to react, it does so through a `progress_events` row, an outbox row (H19) or a job, never an import.

---

## H8 — The cost-limit switch has no representation, and the Order `source` mixes two dimensions

**Severity:** High · **Likelihood:** High · **ADs:** AD-4, AD-5, AD-6, AD-15

**Pair:** AI operations epic, story "AI spending controls" (FR-69) vs AI players epic (FR-32 fallback, FR-79 Play guard), with Completion (FR-17) and Share of LLM Orders (FR-68) as readers.

- FR-69: when the limit is reached, LLM players "switch to Rule-based players for the rest of the Class session". AD-5 lists who appends occupancy (Takeover, Reclaim, Guided Weeks, Play guard, playout), and the cost limit is not on the list. AD-4 forbids a Game from reading live Class session state.
- **Spending controls builds:** the gateway refuses the call when the budget is reached, so the `ai-orders` job receives an error, which it treats as a failure and falls back. **AI players builds:** FR-32's "the LLM player is asked again the next Week". The result: every Week, every AI Seat in every Game makes a refused gateway call, logs an `llm_call` row with outcome `budget`, and records the Order as `llm_fallback`. The Seat is still labelled "LLM player" (FR-34). The Play guard excludes fallback Weeks. The Share of LLM Orders collapses, so §9.1 drops these Games for the wrong reason. Nobody owns the Lecturer notification.
- AD-15's `source ∈ {student, llm, llm_fallback, rule_based, guided, playout}` mixes who decided with why. A playout Order decided by an LLM is `playout` to Gameplay and `llm` to AI players. A Takeover Week is `llm` and cannot be told apart from an AI-filled empty Seat. FR-62 ("Takeover marked"), FR-44 (cost share in AI-held Seats) and FR-68 each choose their own mapping.

**Close with (AD-15, replace the source list):**

> … the Order, `decided_by ∈ {student, llm, rule_based, fixed}`, and `cause ∈ {played, guided, ai_seat, takeover, playout, fallback_timeout, fallback_invalid, guard_switch, cost_limit}`. `occupant_kind` and `cause` are copied from the occupancy row in force. The Share of LLM Orders is the count of `decided_by = llm` over all non-guided Orders in AI-held Seats. The Play guard reads `decided_by = llm` rows only. Completion counts `decided_by = student` only.

**And (AD-5, add a bullet):**

> - The cost limit is session state owned by `ai` (H12). When the player budget runs out, the gateway sets `ai_budgets.players_exhausted_at` in the charging transaction and writes a Lecturer notification (H19). It then emits `session:<id>`. Every `open_week` reads `ai.budget.players_allowed(class_session_id)`, which is one of the three permitted live reads (AD-4). When it returns false, `open_week` appends `occupant_kind = rule_based, reason = cost_limit` for each `llm` Seat before it places Orders. A cost-limit switch is permanent for the rest of the Class session, like a Play guard switch, and it applies to Takeovers and Replays created later.

---

## H9 — Sweeper and job execution model

**Severity:** High · **Likelihood:** Medium · **ADs:** AD-9, AD-5, Conventions (Jobs)

**Pair:** Play deadline playout (FR-38) vs AI players (`ai-orders`, NFR-2) and every other session's sweep actions (NFR-3: five sessions at once).

- AD-9: "`ops.sweep` … performs every due action". **Playout builds:** inline. At the Play deadline the sweep loops over up to 100 unfinished Games × the remaining Weeks. With LLM players in playout, each Week waits on four `ai-orders` jobs, and FR-32 sets no time budget in playout. One sweep then runs for hours. The next minute's sweeps either overlap, competing for the same Game locks and duplicating LLM calls, or queue up behind it. Takeovers, Lab-hour in-room limits (2-minute floor) and reminders in the other four sessions stall, which breaks NFR-4.
- The playout's thousands of LLM orders go to `ai-orders`, the "latency-critical" queue, where they starve live Replays. Those Replays hit their budgets and fall back en masse, which NFR-3 forbids.
- **AI players builds:** AD-5's sweeper fallback "for any `llm` Seat whose budget has passed". That fires on playout Seats, contradicting FR-32. If playout Seats are exempted, a playout Game whose provider is down never finishes, which breaks SM-4.
- Conventions: "enqueued after commit". If a process crashes between the commit and the `defer`, the job is lost: the Takeover notice, the conservation check, the Debrief-ready email. The sweeper repairs only timer columns, and these jobs have none.

**Close with (AD-9, replace the second and third bullets):**

> - `ops.sweep` runs every minute, single-flight (procrastinate `lock = "ops.sweep"`). It only selects due rows and defers one job per action, keyed by its natural key (`queueing_lock`, for example `takeover:<game>:<week>:<seat>`). It never calls the LLM, sends mail or loops over Weeks inline, and one sweep finishes in seconds.
> - A job that must follow a state change is deferred inside the same transaction, on the transaction's connection (procrastinate psycopg connector), so the commit and the enqueue are atomic and the job row is visible only after the commit. No job is deferred after the commit on a separate connection.
> - Every job handler re-checks its preconditions under the owning command's lock and is a no-op when they no longer hold.
> - Queues are `ai-orders` (live Seats only), `playout`, `llm-batch`, `reports` and `mail`. Playout advances one Week per job, re-deferring itself. Playout LLM Orders run on `playout` with the per-attempt timeout and the retry rule but no total budget (FR-32). After retries run out the Rule-based Order is used, so a playout always terminates. The sweeper's AI-order fallback skips Seats whose `cause = playout`.

---

## H10 — The print route's `INTERNAL_TOKEN` bypasses AD-12

**Severity:** High · **Likelihood:** Medium · **ADs:** AD-18, AD-12, AD-10

**Pair:** Reports epic, stories "Student downloads the report" (FR-57) and "Lecturer downloads reports" (FR-59) vs AI assessment epic, stories "Indicative letter" (FR-56) and "Seeing the AI assessment" (FR-55).

- AD-18: the print page `/print/report/<id>` is server-rendered, reachable only internally, and requires `INTERNAL_TOKEN`. AD-10: all data comes from the REST API. **Reports builds:** the print page calls `GET /api/internal/report-data/<student>`, authenticated by `INTERNAL_TOKEN` as a service principal. There is no User, so the AD-12 scope helpers have nothing to evaluate, and the endpoint returns everything, controlled by query flags from the job.
- **Assessment builds:** it enforces "An Indicative letter a Student turned on for themselves is never served to staff" (AD-12) in the scope helpers its own endpoints use.
- **Clash:** a Lecturer's single-report download includes the Student-only letter, or the AI assessment section that FR-58 leaves out by default. Reports also caches the PDF under `<id>`, so a PDF the Student generated with the letter is reused for the Lecturer's download. FR-56, FR-58 and §6.2 (staying out of the high-risk category) are breached silently.

**Close with (AD-18, replace the second and third bullets):**

> - A report job carries `{student_id, class_session_id, requested_by, audience ∈ {student, staff, zip}, include_assessment, include_letter}`. The internal data endpoint for the print route authenticates with `INTERNAL_TOKEN` plus the signed job claims and evaluates AD-12 as `requested_by`. The token never grants more than that User could see. `include_letter` is honoured only when `audience = student` and `requested_by = student_id`. `audience = zip` forces `include_assessment = false` and `include_letter = false`.
> - The `reports` worker fetches that page and converts it with WeasyPrint `pdf/ua-1`. Stored PDFs are keyed by `(student_id, class_session_id, audience, include_assessment, include_letter, data_version)` under `reports/<class_session_id>/`. A PDF is never served to a different audience or options set than it was built for.

---

## H11 — Retention misses derived copies

**Severity:** High · **Likelihood:** Medium · **ADs:** AD-14, AD-9, AD-18, AD-6

**Pair:** Data rights epic, story "Retention" (FR-77, `ops.retention`) vs Reports (PDFs and ZIPs in Storage), AI assessment (FR-54 feedback "quotes the part of the Student's answer"), Debrief summary (FR-47 reflection answers, key moments), Pseudonymised export (FR-71) and Cross-class statistics (FR-65 aggregates).

- **Retention builds:** exactly AD-14. It anonymises the User and deletes the free-text tables keyed by `user_id`: `explanations`, `reflection_answers`, `followups`, `test_answers`.
- **The others build, each legally:** Reports stores PDFs containing the name, the Explanation and the answers in the `reports` bucket (AD-18). Storage is not a table, so AD-14 never mentions it. Assessment stores quotes inside `ai_assessments.feedback` JSONB, a copy of free text in a table keyed by `test_attempt_id`. The Debrief summary stores copies of reflection answers. AI players and the gateway keep prompt and response bodies in `llm_calls` for the prototype evidence (issues #8 and #9), and those contain scrubbed but still personal free text. FR-71 export files sit in Storage.
- Ordering: AD-14 says aggregates are "written per Class session before deletion", but the order is not enforced. If the aggregate job (in `reports`) fails or is still queued when the retention sweep fires, the deletion goes ahead and next year's comparison (FR-65) loses that session forever.
- **Clash:** personal data survives its retention date, which breaks the DPA and FR-77, and the FR-76 deletion on request misses the same copies.

**Close with (AD-14, replace the third and fourth bullets):**

> - Every store of personal data or Student free text (a table, a JSONB field, a Storage prefix or an export file) is registered in `platform/retention.registry` together with its owner's purge function. Columns carry `info={"pii": True}` or `{"free_text": True}`, and a CI test fails on a tagged column whose table is not registered.
> - Derived text never copies Student text. It quotes by reference, `(source_table, source_id, start, end)`, and renders the quote at read time. In production `llm_calls` stores no prompt or response text, only hashes.
> - `ops.retention` for a Class session runs only once `class_sessions.aggregates_written_at` is set. It runs every registered purge function in one job keyed by `(class_session_id, "retention")`, deletes `reports/<class_session_id>/` and the FR-71 exports for that session, and then anonymises the Users. Seats stay as anonymous Seats. FR-76 deletion on request calls the same purge functions for one User.
> - Anonymised aggregates for Cross-class statistics are written per Class session by a job that sets `aggregates_written_at`, only over groups of 10 or more Students.

---

## H12 — The AI gateway cannot legally reach its config, budget or Roster; the budget race; cost precision

**Severity:** Medium · **Likelihood:** High · **ADs:** AD-6, Conventions (Numbers), Paradigm table

**Pair:** AI gateway (AD-6) vs Admin story "Model pinned per Class session" (FR-68) and AI operations story "AI spending controls" (FR-69).

- Paradigm table: `ai` "May import: platform". Steps 1–3 of AD-6 need the session's pinned model, its budget and the Roster's names, which live in `sessions`, `ops` or `admin`, and `classes`/`identity`. **The gateway epic builds:** raw SQL into `class_sessions` and `roster_entries`, which goes around the module boundary. **The Admin epic builds:** a `model_configs` table with "freeze across several Class sessions" (FR-68). **Session setup builds:** `class_sessions.model_config` as JSONB. That gives two owners of the pinning.
- **Spending controls builds:** `spent = SUM(llm_calls.cost) WHERE class_session_id = ?`. **The gateway builds:** "check and charge" as a read of that sum before each call. 250 concurrent players read the same headroom and all proceed, so the limit is overshot by up to one call per concurrent Seat. The reservation for the Debrief and AI assessment has no stored form, so player calls spend it.
- Conventions: "Money and cost rates are `NUMERIC(14,4)`." A small-model call of 300 input tokens at USD 0.10 per million costs USD 0.00003. It rounds to 0.0000, so spend is under-reported by up to 100% per call and the cost limit never trips.
- Lecturer test Games (FR-87) and the Control test (FR-82) call `ai.run(purpose, class_session_id, …)`. For the Control test there is no Class session to pin or budget against.

**Close with (AD-6, insert before the numbered list):**

> `ai` owns its tables: `ai_model_configs` (versioned, freezable across Class sessions by the Admin), `ai_session_bindings(class_session_id, model_config_id, locked_at)` (locked by `sessions.lock`, H2), `ai_budgets(class_session_id, limit, core_reserve, spent, players_exhausted_at)` and `llm_calls`. Other modules change them only through `ai.config` and `ai.budget`. Charging is atomic: before the call, `UPDATE ai_budgets SET spent = spent + :estimate WHERE class_session_id = :id AND spent + :estimate <= limit - (CASE WHEN :purpose_is_player THEN core_reserve ELSE 0 END) RETURNING …`, then a settle to the actual cost after the call. Player purposes may never spend `core_reserve`. Scrub terms come from `platform/pii.terms(class_session_id)`, a read-only projection over identity that only the gateway uses. A Control test runs under its own Class session with `kind = control`, so every call has a binding and a budget.

**And (Conventions, Numbers, append):** "LLM token prices and call costs are `NUMERIC(18,8)` USD. Game costs stay `NUMERIC(14,4)`."

---

## H13 — The Play guard and the references are computed twice, in two transactions

**Severity:** Medium · **Likelihood:** Medium · **ADs:** AD-5, AD-15, AD-1

**Pair:** AI players `ai-orders` job (AD-5: "It then runs the Play guard (a pure function) and calls `place_order`") vs the Decision log (AD-15: the `seat_week` row written by `place_order` holds "the Rule-based reference and near-optimal reference Orders").

- **The AI job builds:** it computes both references outside any lock to feed the guard. The near-optimal reference "may use information the LLM player never sees", such as other Seats' state, which may change while the LLM thinks. Then it calls `switch_to_rule_based` as a separate command after `place_order`.
- **Gameplay builds:** `place_order` computes the references again to store them, for every Seat including Students' (FR-67).
- **Clash:** the guard judged against references that differ from the stored ones, so the evidence for issue #20 does not reproduce. If the job crashes between `place_order` and `switch_to_rule_based`, the switch is lost. A retry finds the Order already placed (idempotent), returns early and never re-runs the guard.

**Close with (AD-5, replace the third bullet's last sentence and add one):**

> … It then calls `place_order`. The Rule-based and near-optimal reference Orders are computed once, inside `open_week`, from the state at Week open, and stored on the turn (AD-20). `place_order` copies them into `seat_week`. For `decided_by = llm` Orders, `place_order` runs the Play guard (a pure `analysis` function over this Seat's stored `seat_weeks` plus the new row) in the same transaction, and when it switches it appends the occupancy row with `from_week = week + 1`. No job runs the guard.

---

## H14 — Facts sets are rebuilt, not persisted

**Severity:** Medium · **Likelihood:** Medium · **ADs:** AD-7

**Pair 1:** Individual test, story "Adapted items" (FR-53) vs AI assessment (FR-54). **Pair 2:** Debrief (FR-44, FR-47) vs Student report (FR-58).

- AD-7: "`analysis` builds a facts set … from the Decision log", and the validator checks against "the set". It does not say whether the set is stored.
- **Tests builds:** at test open it builds facts and generates Adapted items that cite `fact_id`s. **Assessment builds:** after the Test deadline, which may be weeks later and after a deploy that changed an `analysis` pattern definition, it rebuilds the set. Ids or values have shifted, so the validator rejects the feedback, "regenerated once and then left out" (FR-54), for every Adapted item in the session.
- **The report builds:** it recomputes the "key moments" with the new `analysis` version, which differ from the moments the Student saw in the Debrief and from the stored Debrief summary.

**Close with (AD-7, replace the first bullet):**

> - `analysis` builds a facts set (ids, values, Detected patterns) from the Decision log, and the shell persists it once, as `fact_sets(id, subject_kind, subject_id, analysis_version, payload)`. Fact ids are deterministic (`<pattern>:<role>:<week>`). Anything that cites facts (Debrief narration, the Debrief summary, the Replay walkthrough, Adapted items, AI assessment feedback, the Student report) stores the `fact_set_id`, and validators and renderers load that set and never rebuild it.

---

## H15 — Game status has two owners; an Order does not end a Pause; peer Takeover has no policy

**Severity:** Medium · **Likelihood:** High · **ADs:** AD-2, AD-12

**Pair:** Inactivity and Takeover epic, story "Pause" (FR-89) vs Gameplay / Lecturer overview (FR-39 statuses: not started, running, waiting, paused, finished).

- **Pause builds:** `games.status = 'paused'` and `resume_at`. **Gameplay builds:** `games.status` set to `running` by `start` and to `finished` by `finish`, and `place_order` sets `running` after every Order. **The overview builds:** a derived "waiting" status.
- **Clash:** `place_order` overwrites `paused` with `running` while `paused_at` stays set, so the overview shows "running" while the sweeper still suppresses Takeover, or the reverse. FR-89 "Any Student can end the pause by ordering" is in nobody's command, because AD-2's `place_order` has no Pause clause.
- FR-89 lets a Student "put an AI player in an absent Seat once that Seat's time has run out". AD-12's `own_seat(user, game)` does not cover another Seat, and AD-12 forbids `if role ==` in modules. The Takeover epic either cannot build the feature or adds an ad-hoc check.

**Close with (AD-2, append):**

> A Game stores `lifecycle ∈ {created, frozen, running, finished}` and the Pause columns `paused_at`, `paused_by`, `resume_at`. The displayed status (FR-39) is computed only by `games.views.game_status(game, turns)`. `pause` and `resume` write only the Pause columns, and a `place_order` by a Student clears them in the same transaction. `takeover` takes `actor` and `reason ∈ {inactivity, staff, peer_after_limit}`.

**And (AD-12, append):**

> Policy `can(user, "peer_takeover", seat)` is true only when the User holds another Student Seat in the same Game and the target turn's `takeover_due_at`, computed ignoring Pause (FR-89), has passed.

---

## H16 — Test-deadline actions are unordered

**Severity:** Medium · **Likelihood:** Medium · **ADs:** AD-9, AD-16, AD-7

**Pair:** Individual test, stories "Test availability" (FR-51 auto-submit) and "Interactive items" (FR-80 computed scoring) vs AI assessment (FR-54; FR-18: an extended Student is assessed later, but "the Scoring guide stays as it was at the original Test deadline"; FR-81).

- AD-9 lists "Test auto-submit" and "AI assessment enqueue" as separate sweep actions. **Tests builds:** auto-submit per attempt. **Assessment builds:** enqueue with "once per session after the deadline, set `assessment_enqueued_at`". In the deadline minute the enqueue query runs before the auto-submits commit, so those tests are never assessed.
- **Assessment builds:** it reads the current Scoring guide and the current `ai_assessment_enabled` when its job runs. For a Student with an extension that is the guide as edited after the original deadline, contradicting FR-18 and FR-81.
- **Tests builds:** answer-key and Interactive scores on submit, because the report shows them even with the AI assessment off (FR-61). **Assessment builds:** its own answer-key re-scoring to compute the weighted total. The two totals disagree.

**Close with (AD-9, add a bullet):**

> - Each Test attempt has `effective_deadline` (the session's or the Student's extension). One sweep action per due attempt defers `tests.close_attempt(attempt_id)`. That command auto-submits if needed and, in the same transaction, defers `assessment.assess(attempt_id, scoring_guide_version, assessment_enabled)`. Both values are taken from the session's freeze at the original Test deadline, `sessions.lock_test`, which the sweep runs first. Answer-key and Interactive scores come only from `analysis.scoring` and are stored by `tests` on submit. `assessment` stores AI item scores only, and every total comes from `analysis.total_score(computed, ai_items, weights)`.

---

## H17 — No topic catalogue

**Severity:** Medium · **Likelihood:** High · **ADs:** AD-8

**Pair:** Gameplay (emits `game:<id>`) vs Lecturer overview (FR-39, under 5 s) vs Group debrief (FR-43) vs Messages (FR-40).

- **Gameplay builds:** each command emits `game:<game_id>`. **The overview builds:** it subscribes to `session:<class_session_id>` and gets nothing from Orders, so it never updates live. Or it subscribes to every `game:` topic, and the SSE stream runs an AD-12 check per Game per event.
- **Group debrief builds:** `debrief:<group_debrief_id>`. **The Debrief UI builds:** `debrief:<game_id>`, because that is the id it has. They never meet.
- `{topic, id, version}`: only Games have a `version`. Session and debrief emitters invent their own counters. A client that drops events with `version <= seen` misses events after a counter reset or when two entities share a topic.
- The SSE scope is checked when? If at connect only, a Student moved by `swap_seats`, or a deactivated User (FR-3), keeps receiving the old topics.

**Close with (AD-8, replace the second bullet and add two):**

> - Topics, emitters and ids: `game:<game_id>` — every `games.commands` command; `session:<class_session_id>` — every `games.commands` command (same transaction), session settings, Messages, progress events, budget state; `debrief:<class_game_id>` — Group debrief commands, keyed by the Class game; `user:<user_id>` — notifications, Messages to one Student, the User's progress events, and `scope_changed`. Only `game:` carries a monotonic `version`. Other topics send `version: null`, and clients always refetch.
> - The SSE stream evaluates scope when it subscribes, and again whenever the User's own `user:<id>` topic carries `scope_changed`. Seat assignment, Takeover, Class staff changes and deactivation emit it.
> - The topic-to-query-key map lives only in `web/src/lib/api/topics.ts`. An api test asserts that each command emits exactly its listed topics.

---

## H18 — Multi-actor aggregates other than the Game have no write-path rule

**Severity:** Medium · **Likelihood:** Medium · **ADs:** AD-2 (scope limited to Games)

**Pair:** Debrief epic, story "Group debrief" (FR-43: "the step moves on when every joined Student has finished it, or when the Student who opened the Group debrief moves it on") vs story "Personal-debrief fallback" (FR-43: a dropped Student "continues in a Personal debrief from where they were").

- AD-2 covers Games only. **Group debrief builds:** `UPDATE group_debriefs SET step = step + 1` from each Student's "finished" request. Two near-simultaneous last finishers plus the opener's "move on" advance two or three steps. **Fallback builds:** the dropped Student's Personal debrief copies the step and writes its own summary, while the group run later writes a summary for all joined Students, including the dropped one. That gives two FR-47 summaries and two `debrief` progress events.

**Close with (AD-2, append a paragraph):**

> The same pattern applies to every aggregate that more than one actor mutates: the Group debrief (`debrief.commands`: `open`, `join`, `finish_step`, `advance(expected_step)`, `drop_to_personal`) and the Test attempt (`tests.commands`). Each command locks the aggregate row, checks the domain precondition (the expected step, the membership), emits its AD-8 topic and is idempotent. A Student is in at most one Debrief per Class game at a time (a unique constraint), and the Debrief summary and its progress event are written once per `(user_id, game_id)`.

---

## H19 — Notifications have no owner

**Severity:** Medium · **Likelihood:** Medium · **ADs:** AD-9 ("Email goes only through `mail`"), Conventions (Module layout)

**Pair:** Inactivity and Takeover epic (FR-36: "The Student, the other Students … and the Lecturer overview are notified at Takeover") vs Gameplay story "Notification when it is your turn" (FR-27: "gathered in one message per day and never at night") vs Messages (FR-40).

- **Takeover builds:** it defers a `mail` job directly from `games`, which is legal because it goes "through `mail`". The Takeover email arrives at 03:00, alongside the FR-27 digest that also mentions the wait. **Turn reminders build:** a digest table in `messaging`. `games` imports `messaging.service` to send, and `messaging` imports `games.service` to resolve "the Students of one Class game" (FR-40), which is a cycle.

**Close with (AD-9, replace "Email goes only through `mail`."):**

> Notifications are rows in `platform/notify.outbox(user_id, kind, dedupe_key, ref, not_before)`, unique on `dedupe_key`, written in the producing transaction. `messaging` is the only reader of the outbox and the only module that defers to `mail`. It applies digesting, quiet hours (22:00–07:00 Europe/Oslo, except Invitations and resets) and the FR-27 schedule. No other module defers a `mail` job. `[ASSUMPTION: quiet-hours window]`

---

## H20 — AD-12's Admin ban contradicts FR-71 and FR-82

**Severity:** Low · **Likelihood:** Medium · **ADs:** AD-12, AD-14

**Pair:** AI operations story "Pseudonymised export for evaluation" (FR-71: the Admin exports Explanations and Individual test answers) and Admin story "Control test" (FR-82: the Admin sees human and AI scores side by side) vs AD-12 ("The Admin sees no Student answers or AI assessments without Class membership").

- **The export builds:** an AD-12-compliant export cannot include free text, so it adds the Admin to the Class as staff, which gives the Admin full named access, or it adds an `if user.is_admin` bypass, which AD-12 forbids. **Control test builds:** the same.

**Close with (AD-12, append):**

> Named exceptions, each a policy in `platform/authz` and recorded with `platform/audit`: `can(admin, "export_pseudonymised", class_session)` holds only when an Institution agreement for that Class session is recorded (FR-71), and it returns pseudonyms only, never names; `can(admin, "read", control_test_data)` covers only Users with `is_test_student`. There are no other Admin exceptions.

---

## Consolidated AD-2 command list after these changes

`create_game`, `assign_seat`, `swap_seats`, `freeze`, `start`, `open_week`, `view_week`, `place_order`, `recompute_timers`, `takeover`, `reclaim`, `pause`, `resume`, `mark_in_room`, `playout`, `switch_to_rule_based` (guard or cost limit), `finish`. Callers pass domain preconditions, not versions (H5). `finish` writes `progress_events` (H7). Every command defers its follow-up jobs in-transaction (H9) and emits `game:` and `session:` (H17).
