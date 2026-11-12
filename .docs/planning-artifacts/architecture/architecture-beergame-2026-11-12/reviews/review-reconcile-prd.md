---
title: 'Review: spine reconciled against PRD'
reviews: ../ARCHITECTURE-SPINE.md
against:
  - ../../../prds/prd-beergame-2026-10-29/prd.md
  - ../../../prds/prd-beergame-2026-10-29/addendum.md (§A, §B)
date: '2026-11-12'
lens: reconcile-prd
---

# Review: ARCHITECTURE-SPINE.md reconciled against the PRD

## Verdict

The spine's core is sound: one write path (AD-2), one information boundary (AD-3), self-contained Games (AD-4), interchangeable occupants (AD-5), one LLM boundary (AD-6) and one reporting scope (AD-13). But it does not yet cover several PRD rules the architecture has to own. The biggest gaps are these:

- the prototype and all-AI test runs (build-order step 1);
- when Game settings are snapshotted, given the lock points;
- the Group debrief state machine;
- how AI Orders get placed during Guided Weeks and after a mid-Week Takeover;
- worker isolation and provider rate limits under NFR-2 and NFR-3;
- where personal data actually ends up, and who controls the pseudonym key.

None of these needs a paradigm change. They are new ADs, tighter rules or explicit Deferred entries.

Counts: 1 critical, 9 high, 13 medium, 9 low.

Each finding gives its severity, the PRD reference, the spine reference, the problem and a suggested fix.

---

## Critical

### F1 — The prototype and all-AI test runs have no place in the architecture

- **Severity:** critical
- **PRD:** §10.1 (the prototype comes first and gates FR-32, FR-78, FR-79, NFR-2, SM-3, SM-6 and SM-11), §8.1 build order step 1, FR-68 ("Admin selects the model … after a check on all-AI test runs"), FR-78 (prompt calibrated per Effort level), FR-79 (band calibrated on Classic and on the default Replay), SM-1 (baseline from "scripted no-learning players run through both scenarios"), SM-3b (run-to-run variation on fixed all-AI runs), §10 pilot precondition (prototype evidence), addendum §A.
- **Spine:** AD-1, AD-5 and AD-6 define the slots the prototype fills. The Deferred section names the numbers the prototype settles. Nothing says what the prototype *is* or where it runs.
- **Problem:**
  - Seven requirements and the pilot depend on evidence from all-AI runs on real, §6.1-compliant endpoints. If the prototype is a throwaway script, its numbers do not carry over: tokens, latency, retries, guard band and cost all depend on the exact prompt, schema, retry loop and gateway timeouts that production uses.
  - The spine has no Game `purpose` for simulation runs. AD-13 knows only `class`, `replay`, `makeup`, `lecturer_test` and `control_test`.
  - There is no occupant kind for a scripted no-learning player (needed for the SM-1 baseline).
  - There is no budget pool for evaluation spend.
  - There is no headless runner that plays a whole Game without waiting on humans or on the sweeper.
  - FR-68's "check on all-AI test runs" before pinning a model is the same mechanism, run again later. It is not a one-off.
- **Fix:** add a new AD, "Simulation runs use the production engine, players and gateway":
  - A headless runner (`modules/sim`, CLI plus `llm-batch` jobs) creates Games with `purpose=simulation`. The occupants are `llm`, `rule_based` or a new `scripted` kind (constant or no-learning ordering for the SM-1 baseline).
  - It drives each Game Week by Week through `games.commands` (AD-2), so it uses the same Decision log (AD-15) and the same `ai.run` (AD-6) with a separate evaluation budget.
  - Runs are tagged with the candidate model config, and AD-13 excludes them from reporting.
  - The runner writes a pass-line report: cost per Game, p95 per Order, fallback share, guard-switch share and the coefficient of variation of chain Total cost.
  - The candidate model config that passes is the immutable config row the Admin later pins (see F14).
  - State explicitly that the prototype is built on `engine` + `players` + `ai`, so that §10.1's evidence is evidence about the production code path.

---

## High

### F2 — The Game settings snapshot is taken too early (AD-4 contradicts FR-12, FR-18 and FR-20)

- **Severity:** high
- **PRD:** FR-12 ("Game settings are locked from the Start date"), FR-18 (lock points: the Start date for Game settings, AI mode, Effort level, Debrief mode, Replay scenario and Inactivity limit), FR-20 (allocation happens "in the last week before the Start date"; the Lecturer can re-run or move Students until the Start date), FR-21 (Students choose Seats before the Start date), FR-13 (seed stored with the Class session).
- **Spine:** AD-4: "When a Game is created it copies a frozen snapshot of its settings … and stores its materialised demand series."
- **Problem:**
  - Class games are created at allocation, up to a week before the Start date. The Lecturer may still edit Game settings until the Start date.
  - Under AD-4 as written, every Class game keeps the settings it had at allocation. This silently breaks "the change applies to every Class game" (§4.3) and FR-13 ("every Class game in the Class session uses the same demand series").
  - The same applies to AI mode, Effort level and Inactivity limit, if those are copied into the Game.
- **Fix:** tighten AD-4.
  - Class games created before the Start date hold no settings snapshot.
  - A `sessions.lock` command runs at the Start date (sweeper) or at the first Class game start, whichever comes first. In one transaction it freezes the Class session config, materialises the demand series from the stored seed, and writes the snapshot into every Class game of the session.
  - Games created after the lock (make-up, late registration, Replays) copy the locked snapshot. A Replay additionally materialises its per-Student scenario draw (see F28).
  - The Lecturer test Game (FR-87) snapshots at creation, as today.

### F3 — Lock points have no single mechanism

- **Severity:** high
- **PRD:**
  - FR-18 last bullet, the three lock tiers: the Start date for Game settings, AI mode, Effort level, Debrief mode, Replay scenario, question set, obligatory mark and Inactivity limit; the Test deadline for the Scoring guide and the AI assessment switch-off; deadlines and Lab hours at any time.
  - FR-17 (the obligatory mark can be set until the Start date).
  - FR-56 (letter thresholds editable "before the Individual test opens").
  - FR-81 (the Scoring guide version in force at the Test deadline scores the whole Class session).
  - FR-18 (a Student with an extended deadline is scored with "the Scoring guide as it was at the original Test deadline").
  - FR-68 (the model is fixed for the whole Class session).
  - FR-52 (question set changes before the Start date).
- **Spine:** AD-4 locks Game settings at the Start date. No other lock point is stated.
- **Problem:**
  - About ten fields lock at four different events, and several later behaviours depend on those frozen values: per-Student AI assessment after an extension, comparability in FR-65, and the Control test of an edited guide in FR-82.
  - Without one rule, every module will implement its own "is it too late?" check, and those checks will drift.
  - Dates that can change "any time" also interact with actions the sweeper has already fired. Examples:
    - The Test deadline is extended after the auto-submit has run.
    - The Play deadline is moved earlier than now.
    - The Debrief deadline moves after reminders went out.
- **Fix:** add a new AD, "Class session config declares its lock points":
  - Each config field carries a lock event (`start_date`, `first_test_open`, `original_test_deadline`, `never`). `sessions.service` is the only place that enforces it, with error code `locked_after_<event>`.
  - At the original Test deadline the session pins the Scoring guide version (and the letter thresholds once the first test opens) by id. Later per-Student assessments use the pinned ids.
  - Date changes are validated against what has already happened. For example, the Play deadline cannot move into the past while games are unfinished, and moving the Test deadline after an auto-submit does not reopen a submitted test unless a per-Student extension exists.
  - The sweeper re-reads columns, so the lock rules decide what may change, not the sweeper.

### F4 — Guided Weeks: AD-5 would advance them instantly (contradicts FR-24)

- **Severity:** high
- **PRD:** FR-24 ("In Guided Weeks the Order is fixed and placed automatically, the Week advances once every Student in the Class game has opened it, and the clock for the Inactivity limit does not run"), FR-31 (no model call in Guided Weeks), FR-35 (records when each Week opened for a Seat), FR-11 (Guided Weeks also bind AI players).
- **Spine:**
  - AD-5: "In Guided Weeks … `open_week` places the Order itself in the same transaction."
  - AD-2: "When the last Order of a Week arrives, the same transaction advances the Week and opens the next one."
  - AD-2's command list has no "Student opened the Week" command.
- **Problem:**
  - If `open_week` places every Seat's fixed Order, the last Order arrives inside `open_week`, and Guided Weeks 1 to 4 cascade through in one transaction. No Student ever sees them.
  - The PRD gates each Guided Week on every Student *opening* it, which needs a per-Seat acknowledgement that AD-2 does not provide.
  - The spine also does not say what happens when a Student never opens a Guided Week. The Inactivity clock does not run, so FR-36 cannot fire, and the game can stall until the Play deadline. That is acceptable per FR-36, but it should be stated.
- **Fix:**
  - Add `acknowledge_week(seat)` to AD-2's commands. It records `seen_at` and is idempotent.
  - In Guided Weeks, `open_week` writes the fixed Orders for AI Seats only. The fixed Order of a Student Seat is placed by `acknowledge_week`, and the Week advances when every Student Seat has acknowledged.
  - Define `opened_at` (when the Week opened in the Game) and `seen_at` (when the Seat first loaded it) in AD-15, so FR-35 and SM-11 are unambiguous.
  - State that an unacknowledged Guided Week waits for manual Takeover (FR-37) or for playout.

### F5 — No Order path after a mid-Week Takeover, and the takeover actors are not separated

- **Severity:** high
- **PRD:**
  - FR-36: the automatic Takeover fires only when at least one other Student has ordered and waited the limit; nothing happens while paused; the clock starts at the first other Student's Order; the shorter limit applies only to games marked in the room; per-Student adjustments.
  - FR-37: a Lecturer can take over at any time, and can fill all absent Seats in one game or in all games.
  - FR-89: during a Pause, a Student may put in an AI player once that Seat's time has run out (the agreed time if one is set, otherwise the limit, counted whether paused or not), and no Student can shorten another's time.
  - FR-39: games approaching Takeover are highlighted.
  - NFR-4.
  - FR-67: the Order source is recorded.
- **Spine:**
  - AD-5 places or enqueues AI Orders only in `open_week`. The sweeper fallback fires for `llm` Seats "whose budget has passed".
  - AD-2 lists a single `takeover` command.
- **Problem:**
  - Takeover happens in the middle of a Week, after `open_week` has run.
  - For a `rule_based` occupant, no rule places the Order, so the game stalls. This breaks NFR-4.
  - For an `llm` occupant, nothing enqueues a job either. The sweeper sees a budget measured from the Week's opening, which expired hours ago, so it immediately writes a Rule-based `llm_fallback`. That corrupts the Share of LLM Orders (FR-68, §9.1) and SM-3a.
  - Three actors have three different eligibility rules: the sweeper (automatic, blocked by Pause), a Student (time run out, allowed during Pause, agreed time takes precedence) and staff (any time, bulk). The overview's "approaching Takeover" highlight needs the same computation. If each of the four computes "is this Seat's time up?" separately, they will disagree.
- **Fix:**
  - **Tighten AD-5:** every command that changes a Seat's occupant to AI for the current Week (`takeover`, `playout`, `switch_to_rule_based`, the cost-limit switch) places the Order in the same transaction for `rule_based`, or enqueues `ai-orders` with a budget starting at the command's commit time. The sweeper fallback measures the budget from the Order request time, not from the Week's opening.
  - **Add a pure function** to `analysis`, `takeover_eligibility(seat_week_events, pause, agreed_time, limits, adjustments, now) -> {auto_due_at, student_allowed_at}`. The sweeper, the Student's "put in an AI player" action, the staff bulk fill and the FR-39 highlight all call it.
  - **Split the `takeover` command** by actor (`auto`, `student`, `staff`) so audit (FR-3) and occupancy `reason` are exact.

### F6 — The Group debrief is a concurrent state machine with no AD

- **Severity:** high
- **PRD:**
  - FR-43, step sync:
    - All joined Students see the same step.
    - The step moves on when every joined Student has finished it, or when the opener moves it on after a short wait.
    - A late joiner writes the Explanation first, then enters at the current step.
    - A joined Student who drops out continues in a Personal debrief from where they were.
    - The Personal debrief fallback opens after 48 hours.
    - One active Student uses the Personal debrief.
  - FR-41: no progress without a saved Explanation; Explanations are not visible to others.
  - FR-74: one shared screen shows only the shared charts.
  - FR-42: hold or open Debriefs.
  - FR-44: per-Student content stays on the Student's own device.
- **Spine:** AD-8 binds FR-43 for push. AD-3 says Debrief endpoints check the gates. Nothing owns the shared step pointer, the joined set, or presence.
- **Problem:**
  - Several Students finishing a step at the same moment, the opener pressing "next" and a late joiner arriving together form the same race AD-2 solves for Weeks. The spine leaves it unsolved.
  - "Dropped out" needs presence detection. The spine has a per-User SSE stream but no heartbeat or last-seen rule.
  - The FR-74 shared screen needs a principal. If it runs under one Student's session, it can show that Student's private moments. If it is a Lecturer screen, AD-12 has no "show shared charts only" scope.
  - The reveal gate is per Student, while the step pointer is shared, so a late joiner who is physically in the room can see the reveal on the shared screen. The architecture should at least state the rule.
- **Fix:** add a new AD, "The Debrief session has one write path":
  - `debrief.commands` (`open`, `join`, `save_explanation`, `finish_step`, `advance`, `leave`, `fallback_to_personal`) each run as one transaction with `SELECT … FOR UPDATE` on the `debrief_sessions` row, a version bump and `NOTIFY debrief:<id>`.
  - Per-Student progress is a row that survives the switch from Group to Personal.
  - The short minimum wait is checked against the server clock.
  - Presence is the SSE connection plus a heartbeat with a stated timeout. On timeout, the sweeper fires `leave` / `fallback_to_personal`, and it also handles the 48-hour fallback.
  - The shared screen is a display-only, debrief-scoped principal (a staff session or a short-lived display token). It is served only the shared-chart projection, and AD-12 gets a policy for it.

### F7 — One worker process cannot meet NFR-2, FR-57 and FR-59 together

- **Severity:** high
- **PRD:** NFR-2 (a Student waits at most the per-Order budget, about 8 s at p95), FR-57 (a single report within 30 s), FR-59 (a ZIP for 250 Students within 10 minutes), FR-54 (all AI assessments within 24 h), NFR-3 (a 250-player Lab hour, 5 sessions at once).
- **Spine:** AD-9 defines queues but one `worker` service runs them all. AD-18 runs WeasyPrint in that worker.
- **Problem:**
  - WeasyPrint is synchronous and CPU-bound. A ZIP for 250 Students run in the same process and event loop as `ai-orders` blocks latency-critical AI Orders.
  - Replays (each Week waits on three LLM Seats) run until the Test deadline, overlapping report generation, make-up games, and AI assessment batches for other sessions.
  - A single report queued behind a ZIP breaks 30 s.
  - 250 sequential renders, each fetching the Next.js print route, are close to the 10-minute ceiling.
- **Fix:** tighten AD-9 and AD-18 to say lanes are separate processes.
  - **`worker-ai`:** `ai-orders` only, async, concurrency sized to the provider limit (F8). It also runs `ops.sweep`, or the sweep moves to a small `worker-ops`.
  - **`worker-batch`:** `llm-batch` and `mail`.
  - **`worker-reports`:** WeasyPrint in a process pool. Single-report jobs have priority over ZIP fan-out. A ZIP is one job per Student plus one assemble job, with cached per-Student PDFs reused when the inputs have not changed.
  - All three lanes are the same image with different `procrastinate --queues` arguments. Record this in the deployment seed.

### F8 — No admission control for provider rate limits (NFR-3 against NFR-2)

- **Severity:** high
- **PRD:** NFR-3 ("a load test that includes the LLM provider's rate limits; rate-limit errors do not cause mass fallback"), NFR-2, FR-32 (5 retries, then fallback), §10 pilot precondition ("a named provider, plan, region, terms and rate limit, confirmed in writing"), addendum §A (AI Seats order in parallel; worst case 6 calls per Order).
- **Spine:** AD-6 steps 1 to 6 have no rate limiting. The Deferred section covers only the load-test *method*.
- **Problem:**
  - At the start of a Lab hour, or at a cost-limit or playout spike, many `llm` Seats call at once.
  - A 429 with a `Retry-After` longer than the per-Order budget turns directly into fallback. That is the "mass fallback" NFR-3 forbids.
  - The spine also does not say whether a 429 is a "schema failure" that consumes one of the 5 retries (FR-32), or whether `llm-batch` work (AI assessment, Debrief narration) can starve `ai-orders` of provider quota.
  - None of this can be left to the load test. The load test can only measure a policy that exists.
- **Fix:** add a step to AD-6.
  - A gateway-wide limiter per pinned endpoint (a Postgres-backed token bucket or a fixed share per worker process) with priorities: `ai-orders` above interactive Debrief follow-up, which is above `llm-batch`.
  - A 429 or 5xx is a transport failure, not a schema failure. It does not consume the 5 retries but does count against the time budget.
  - `llm-batch` yields while `ai-orders` demand is high, for example during scheduled Lab hours.
  - The endpoint's contracted rate limit is a field of the pinned model config (F14), so the limiter and the load test read the same number.
  - Add a Deferred entry for sizing it after the prototype.

### F9 — Personal data lives in more places than AD-14 says

- **Severity:** high
- **PRD:** §6.1 (free text sent to an LLM "stays personal data"; quotes come from the original text), FR-77 (automatic deletion after a set period), FR-76 (deletion on request), FR-75 (a Student sees all data stored about them), FR-71 (pseudonymised exports follow retention), FR-57 (reports downloadable "until the data is deleted").
- **Spine:** AD-14: "Names, emails and student numbers live only in `identity` tables. Every other table references `user_id` or `seat_id`." The retention sweep deletes "that free text".
- **Problem:** the rule is false for stores the spine itself introduces.
  - **Student report PDFs and ZIPs** in the `reports` bucket (AD-18) hold names, Explanations and answers.
  - **`llm_call` rows** (AD-6), if they keep request and response bodies: scrubbed free text plus outputs that quote it.
  - **AI-written text about a Student:** AI assessment feedback (it quotes the Student, FR-54), Debrief narration, follow-up questions and answers, and Debrief summaries (FR-47).
  - **Message bodies** (FR-40), which staff may write about named Students.
  - **`audit_event.change` payloads**, for example an email change or a role grant.
  - **procrastinate job arguments and event tables**: mail jobs carry recipients and names.
  - **The Roster**: emails of people who never registered.
  - **Student numbers**: the spine scrubs them but never says where they come from. If they are not collected, the scrubber cannot use them; if they are, they are a new store.
  - **Supabase daily backups.**
  - **FR-71 export files.**

  The retention sweep and FR-75 data access cannot find what is not registered.
- **Fix:** replace AD-14's first bullet with a personal-data register, one row per store, each giving its key (`user_id` and/or `class_session_id`), its FR-75 read path and its FR-76 / FR-77 deletion path.
  - Storage objects use a `class_session/<id>/user/<id>/` prefix and are deleted by `ops.retention`.
  - Job arguments carry ids only. The mail job loads the recipient at send time, and finished procrastinate jobs are pruned on a short horizon.
  - Audit payloads reference ids, not values.
  - `llm_call` stores metadata only. Bodies, if kept at all, go to a user-keyed table with the same retention.
  - Messages are tagged with the Class session and fall under its retention.
  - Supabase backups are listed in the DPIA pack with their window.
  - Decide whether student numbers are collected at all, and record the decision.

### F10 — The pseudonym key is under the founder's sole control (contradicts a §10 pilot precondition)

- **Severity:** high
- **PRD:** §10 pilot precondition ("someone other than the founder holding the pseudonym key"), FR-71 ("stable pseudonyms"), §6.1 (pseudonymous IDs towards LLM providers), §2.1 risk "The founder has several roles".
- **Spine:** AD-14 computes `HMAC(PSEUDONYM_SECRET, user_id)` and says the key "is held outside the founder's sole control". AD-17 requires `PSEUDONYM_SECRET` as a production environment variable.
- **Problem:**
  - An environment variable in the founder's Railway project is readable by the founder, who is the sole operator, Admin, Lecturer and evidence scorer. The rule as written cannot be met by the mechanism it names.
  - The spine also uses one key for two jobs: identifying people in LLM inputs (AD-6) and making evaluation exports (FR-71). The first needs no key. The second needs a key the founder does not hold.
- **Fix:**
  - **LLM inputs** use Role labels and random, per-Game opaque ids stored in the database. No HMAC is involved.
  - **FR-71 exports** compute pseudonyms with a key supplied by the Institution's key holder at export time. The key is entered for the export run, used in memory and never stored or logged. Using the same key gives stable pseudonyms across exports.
  - Remove `PSEUDONYM_SECRET` from AD-17's startup guard, or redefine it as the opaque-id salt only.
  - If the Institution declines to hold a key, list that as a Deferred decision for the DPIA dialogue rather than claim it in an AD.

---

## Medium

### F11 — AD-2's version check is ambiguous and could reject legitimate Orders in the same Week

- **Severity:** medium
- **PRD:** FR-24, FR-26, NFR-1, NFR-4.
- **Spine:** AD-2: "checks the Game's `version`, increments it".
- **Problem:**
  - If `version` is an optimistic-concurrency guard compared against what the caller last saw, two Students (or a Student and an AI job) ordering in the same Week will conflict. Every Order bumps `version`, so the second request is rejected or retried for no reason, and AI jobs built from an older Seat view fail.
  - It is also not stated that no external I/O (LLM call, near-optimal computation, email) happens while the Game row is locked.
- **Fix:**
  - State that the row lock is the concurrency guard and `version` only orders events (AD-8) and caches.
  - `place_order` takes the `week` the caller saw and returns `409 week_closed` if it does not match. A stale `version` does not cause a rejection.
  - No network I/O happens inside a command transaction. LLM calls, and any expensive near-optimal reference, are computed before the command (at `open_week`, stored) and passed in.

### F12 — The semantics of the Play deadline playout are undefined

- **Severity:** medium
- **PRD:** FR-38 (every unfinished Class game is played to its last Week with AI in all Seats; SM-4), FR-32 ("No limit applies in the playout … when no Student is waiting"), FR-89 (a Pause does not move the Play deadline), FR-17 (playout Weeks count as not ordered), §6.3 (playout makes four Seats AI, 144 calls per game, addendum §A).
- **Spine:** AD-2 lists `playout`. AD-5 enforces the Effort time budget on every `llm` Order, and the sweeper falls back when the budget passes. AD-9 lists playout as a sweep action.
- **Problem:**
  - AD-5's budget and the sweeper fallback both contradict FR-32's "no limit in playout". Applied as written, they would turn a slow playout into Rule-based fallbacks.
  - Nothing says that a Student Order arriving after the Play deadline is rejected, or how that race is settled.
  - Playout must override a Pause.
  - Playout can be 100 games × 5 sessions × up to 36 Weeks × 4 LLM Seats. It should not run on the latency-critical lane, and it needs a cost reservation.
- **Fix:**
  - `playout` sets the game state `playing_out` and overrides Pause.
  - `place_order` from a Student checks `now() >= play_deadline` against the database clock under the row lock and returns `play_deadline_passed`.
  - Playout Orders run on `llm-batch` with no per-Order budget and no sweeper fallback (the fallback stays only for provider failure). Week-by-Week chaining runs through jobs.
  - The occupancy reason is `playout`.
  - Define "finished at the Play deadline" for SM-4 as finished within a stated time after it.

### F13 — Hidden information can leak outside the Seat view

- **Severity:** medium
- **PRD:** FR-14 (no number of Weeks and no demand series while playing), FR-31 (the prompt holds the game rules, and the AI player is not told it plays a game, nor the number of Seats), FR-49 (Replay length and step Week stay hidden), FR-17 (the Takeover warning must not reveal the number of Weeks), FR-79 (the near-optimal reference uses information the LLM never sees).
- **Spine:** AD-3 covers the play endpoint, the LLM prompt and `state_seen`. AD-16 says the Student home screen calls `analysis.completion`.
- **Problem:** several paths bypass `seat_view`.
  - **(a) Completion on the Student home screen.** If it shows the Class game step as a share of Weeks ordered during an unfinished game, the denominator reveals the number of Weeks.
  - **(b) Prompt rules.** The LLM prompt's "game rules" will be built from `GameSettings`, which contains `weeks` and the Demand pattern. AD-3 constrains only state, not rules.
  - **(c) The near-optimal reference.** The Play guard's reference is computed in the same `ai-orders` job that builds the prompt.
  - **(d) Error codes and messages,** for example "week out of range".
  - **(e) Emails** (FR-27 turn reminders, the FR-17 Takeover warning) rendered from Game data.
- **Fix:** extend AD-3.
  - Add a `seat_rules(settings, seat)` projection (delays, max Order, capacity, visibility, but no horizon or demand). It is the only settings-derived prompt input.
  - Student-facing `CompletionStatus` for an unfinished Game exposes no ratio or denominator.
  - Emails and errors read from `seat_view` / `seat_rules`.
  - A CI test asserts that the schemas of `seat_view` and `seat_rules` contain no horizon or demand-series fields, and that prompt builders import only those.

### F14 — The caller picks the prompt version, which contradicts FR-68 pinning; the pinned config is not immutable

- **Severity:** medium
- **PRD:** FR-68 (model version, endpoint *and prompt versions* stay the same for the whole Class session and its Replays; the Admin can freeze a model across sessions), FR-67 (log quantisation, Effort level, seed and temperature), FR-78 (only levels the pinned endpoint supports and that were measured).
- **Spine:** AD-6: `ai.run(purpose, class_session_id, prompt_id@version, …)`. Step 1 resolves the pinned config. The `llm_call` fields omit quantisation, Effort level and seed/temperature.
- **Problem:**
  - If modules pass `prompt_id@version`, a deploy that bumps a prompt file changes the prompt in the middle of a Class session, which FR-68 forbids.
  - "Pinned config" is not said to be an immutable, versioned record. Editing it in place would change a running session.
  - The Admin's "freeze across sessions" needs sessions to share a config id.
  - The spine does not say what happens if a pinned model is retired in the middle of a session.
- **Fix:**
  - Introduce a `model_config` row that is immutable once referenced. It holds provider, endpoint, region, model version, quantisation, the Effort levels offered with their timeouts and budgets, prices, the contracted rate limit, and a `prompts` map from purpose to version.
  - A Class session references one config. It locks at the Start date (F3) or at the first LLM call.
  - `ai.run(purpose, class_session_id, inputs, output_schema)` resolves the prompt version from that map. Callers never pass one.
  - A retired endpoint produces per-call failures handled by the FR-32 and FR-44 fallbacks, never by switching models.
  - `llm_call` logs every FR-67 field.

### F15 — Spending checks race under concurrency, and the cost-limit switch has no path

- **Severity:** medium
- **PRD:** FR-69 (limit per Class session; at the limit, LLM players switch to Rule-based "for the rest of the Class session"; a reserve for the Debrief and AI assessment; the Admin is alerted on daily spend), FR-68 (reports record when a cost limit took effect), §6.3.
- **Spine:** AD-6 step 2: "checks and charges the budget, with a reservation". AD-2 has `switch_to_rule_based` per Game.
- **Problem:**
  - Cost is known only after the call (tokens, reasoning tokens). A check-then-charge under hundreds of parallel calls overshoots the limit.
  - The switch is session-wide and must reach every running and future Game and every in-flight `ai-orders` job. The spine models it only per Game, with no occupancy `reason` and no session-level flag.
  - The size of the reserve is a policy with no home.
- **Fix:**
  - Reserve, then settle, on one budget row per session with an atomic conditional update. The estimate is `max_tokens × price` per attempt; the actual cost is settled afterwards.
  - Add a session flag `cost_limit_reached_at`, which `open_week` and the `ai-orders` job read.
  - The switch appends occupancy with `reason=cost_limit` and is reported per FR-68.
  - The reserve is sized per Student (a Deferred number from the prototype). Debrief and assessment purposes may draw on the reserve; player purposes may not.

### F16 — `ai-orders` retries conflict with procrastinate's retries and the budget clock

- **Severity:** medium
- **PRD:** NFR-2 (a time budget per Order, retries included), FR-32 (at most 5 retries, then fallback; the fallback applies to that Week only).
- **Spine:** the Jobs convention says "retried by procrastinate". AD-5 says the job retries at most 5 times. AD-6 step 4 says the gateway applies the retry rule. pydantic-ai has its own output retries.
- **Problem:**
  - Up to three layers can retry. A procrastinate-level retry of a crashed `ai-orders` job restarts the 5 gateway attempts, which exceeds both the cap and the budget and spends more money.
  - The budget's start is unstated. If it starts when the job is picked up rather than when the Order was requested, queueing delay is invisible.
- **Fix:**
  - `ai-orders` jobs have zero procrastinate retries. Any exception leads to fallback.
  - The gateway is the single owner of attempts (pydantic-ai's own output retries are disabled, or counted in the 5).
  - The budget is measured from the Order request time (F5), and the job checks the remaining budget before each attempt.

### F17 — The Control test is modelled only as a Game purpose

- **Severity:** medium
- **PRD:**
  - FR-82:
    - A separate run of the Individual test.
    - Test students play a Class game and a Replay, so their Adapted items rest on a real Decision log.
    - Blind human scoring, then a side-by-side comparison: exact agreement, within one step, offset, compression, and agreement by answer length.
    - The default or a Lecturer's edited Scoring guide.
    - The operator is controller for test students' data, with consent.
    - The Admin runs it.
  - SM-7 (at least 30 tests before the pilot).
  - FR-81 (an edited guide is "checked" only through a Control test).
  - §10.
- **Spine:** AD-13 `purpose=control_test` on Games, and `is_test_student`.
- **Problem:**
  - A Control test needs Class games and Replays for test students. Their natural purpose is `class` / `replay`, so `control_test` on the Game is the wrong level.
  - It needs the Individual test, AI assessment, a human-score entity, a blind-scoring authz rule (the scorer cannot see the AI score) and comparison statistics.
  - It needs a different controller, so a different retention policy and a consent record (AD-14 retention is "per Institution").
  - To be a valid check (FR-81 "checked" status, SM-7) it must bind to the exact Scoring guide version and model config it validates.
- **Fix:**
  - Model a Control test as a Class session with `kind=control_test`, owned by an operator-owned Institution with its own retention policy and consent records, and referencing the `model_config` and Scoring guide version under test.
  - Add a `human_score` entity and an AD-12 policy: an AI score is hidden from a scorer until that scorer submits.
  - The comparison metrics live in `analysis`.
  - A guide version is marked checked when a Control test on that version (and model config) passes.
  - AD-13's helpers exclude by session `kind` plus `is_test_student`, and `purpose=control_test` on Games is dropped.

### F18 — Quote validation clashes with PII scrubbing

- **Severity:** medium
- **PRD:** §6.1 (free text is filtered for Roster names, emails and numbers before an LLM sees it; quotes shown to the Student come from the original text), FR-54 (feedback quotes the Student's answer from the original text).
- **Spine:** AD-6 step 3 scrubs inputs. AD-7's validator rejects "any quote that is not a substring of the Student's original text".
- **Problem:** the LLM sees scrubbed text. Any quote that spans a scrubbed token, or that the model normalises, will fail a substring match against the original text, causing spurious rejections and fallbacks. The opposite fix, matching against scrubbed text, would show scrubbed text to the Student.
- **Fix:** the output schema cites quotes as character spans (or verbatim snippets) over the scrubbed text. The scrubber returns an offset map, the validator checks the span against the scrubbed text, and the renderer shows the corresponding span of the original text.

### F19 — Test and Debrief content has no versioning model

- **Severity:** medium
- **PRD:** FR-52 (the Lecturer excludes questions and changes Item weights before the Start date), FR-53 (Adapted item templates), FR-46 (fixed quiz questions; the Lecturer can exclude one), FR-81 (an editable Scoring guide; the version in force at the deadline scores everything), FR-65 (comparisons labelled by question set, Item weights and Scoring guide version), FR-66 (rerun copies them), FR-82, FR-85.
- **Spine:** `GameSettings` has `schema_version` (AD-4). There is nothing equivalent for the question set, Item weights, Debrief quiz, Starting task, Adapted templates or Scoring guide.
- **Problem:** FR-65 comparability, the FR-81 freeze, the FR-82 "checked" status and the FR-66 copy all need content addressed by an immutable version id. Without one, an edit to the default question set changes past sessions' reports.
- **Fix:** add a new AD, or extend AD-4.
  - Content documents (question set with weights, quiz, Starting task, Adapted templates, Scoring guide) are immutable, versioned rows. Product defaults are seeded versions.
  - A Class session references version ids, and an edit creates a new version.
  - Reports, comparisons and Control tests key on those ids.

### F20 — Deploys and migrations can break Lab hours (NFR-4)

- **Severity:** medium
- **PRD:** NFR-4 (99.5% availability during Lab hours, no Game state lost), FR-19 (Lab hours are scheduled data), NFR-5.
- **Spine:** the `production` branch auto-deploys. Migrations run as the Railway pre-deploy command, forward-only. One `api` replica is assumed.
- **Problem:** a push during a Lab hour restarts `api` (dropping all SSE connections) and `worker` (killing in-flight `ai-orders`). A table-rewriting migration on `seat_weeks` can lock play. The spine has no rule that prevents this.
- **Fix:**
  - A deploy guard: CI, or a pre-deploy check, refuses a production deploy while any Lab hour is in progress or about to start, unless it is overridden as a hotfix.
  - Migrations are expand-then-contract and must not take long locks on the game tables.
  - Workers shut down gracefully, and the sweeper repairs aborted `ai-orders` (AD-9 already allows this; state it).

### F21 — The Debrief and Adapted-item LLM work has no timing rule

- **Severity:** medium
- **PRD:** FR-43 (joined Students move through steps together), FR-44 (narration, with a code fallback), FR-53 (Adapted items generated from the Class game and Replay; the test opens once the Replay is complete), FR-51.
- **Spine:** AD-7 defines validation but not *when* generation runs. The deployment shows `api → llm` for follow-up only.
- **Problem:**
  - Generating narration synchronously when a group reaches a step makes everyone wait on one Student's LLM call, plus retries.
  - Generating Adapted items when the test opens adds LLM latency and a failure path at the moment the Student starts.
  - Once shown, an Adapted item must never change, because answers refer to it.
- **Fix:**
  - Per-Student narration that does not depend on the Explanation is generated on `llm-batch` when the Game ends (it can run while Debriefs are held).
  - Text that depends on the Explanation is generated after the Explanation is saved, and the code-rendered version is shown until it is ready.
  - Adapted items are generated when the Replay finishes, frozen on first display, and fall back to Core items on failure (FR-53's rule for few Orders shows the pattern).

### F22 — Provider webhooks clash with the CSRF rule

- **Severity:** medium
- **PRD:** NFR-10 ("bounces are reported to the Lecturer"), FR-8 (counts of sent, bounced, accepted and expired).
- **Spine:** AD-11 requires `X-Requested-With: olspillet` on "every mutating request". No inbound webhook is designed.
- **Problem:** bounce data arrives as Resend webhooks (and possibly provider callbacks later). These cannot send the header, so under AD-11 they are rejected.
- **Fix:**
  - Add `/api/webhooks/<provider>` routes, exempt from the header rule and authenticated by the provider's signature (Svix for Resend).
  - Make them idempotent on the event id. They write delivery status through the `messaging` service.

### F23 — Cross-class statistics have two data sources over time

- **Severity:** medium
- **PRD:** FR-65 (an anonymised aggregate over groups of at least 10 survives FR-77 deletion; comparisons labelled by settings, model, prompt version and Effort level), FR-77, FR-64.
- **Spine:** AD-14 writes aggregates "per Class session before deletion".
- **Problem:** if Cross-class statistics read live data for sessions that still exist and aggregates for deleted ones, the same session's numbers change on the day of deletion, and the two code paths can disagree. Corrections after the aggregate is written (FR-17) also go stale.
- **Fix:**
  - Write the aggregate at a defined point, for example when all AI assessments are ready, and rewrite it on any later correction until deletion.
  - Cross-class statistics always read aggregates, never live tables, so there is one code path.
  - The aggregate carries the comparability keys (config id, content version ids).

---

## Low

### F24 — A 1-minute sweeper resolution against a 2-minute in-room limit

- **Severity:** low
- **PRD:** FR-36 (in-room limit 2 to 120 minutes, default 10), NFR-4 ("no Student who has ordered waits longer than the Inactivity limit").
- **Spine:** AD-9 (1-minute resolution, "inside the 2-minute floor").
- **Problem:** at a 2-minute limit, Takeover lands between 2:00 and 3:00, which is up to 50% late and strictly outside NFR-4.
- **Fix:** either state the tolerance ("limits are honoured to within 1 minute") in AD-9, or have commands that start an in-room clock also defer a procrastinate job at the exact due time, with the sweeper as backstop.

### F25 — The Lecturer overview can cause refetch storms

- **Severity:** low
- **PRD:** FR-39 (updates within 5 s), NFR-3 (100 games, 250 concurrent players, 5 sessions).
- **Spine:** AD-8 (every change NOTIFYs; clients invalidate and refetch).
- **Problem:** every Order in 100 games invalidates the `session:<id>` overview for every staff viewer, so a full overview refetch can run several times per second.
- **Fix:** coalesce `session:*` events server-side (at most one per 1 to 2 s per topic) within the 5 s budget. The overview reads a single read-model query.

### F26 — Machine-readable AI marking is not specified

- **Severity:** low
- **PRD:** FR-34 (AI text marked "for people and in machine-readable form, including in PDF files"), §6.2 (Art. 50).
- **Spine:** AD-7 ("marked AI-generated"), AD-18.
- **Fix:**
  - AI-produced text travels in the API as `{text, ai_generated: true, provenance: llm_call_id}`.
  - The web app renders a data attribute.
  - The PDF tags AI sections in the structure tree and states AI provenance in XMP metadata.

### F27 — The print route and report variants

- **Severity:** low
- **PRD:**
  - FR-56: a letter a Student turned on is never shown to Lecturers.
  - FR-58:
    - The AI section appears only if the person downloading adds it.
    - Other Students appear by Role only, and their Explanations are never included.
  - FR-59: the ZIP never holds the AI section.
  - NFR-7.
- **Spine:** AD-18 (`/print/report/<id>` behind `INTERNAL_TOKEN`, "reachable only from the internal network"). Caddy sends "everything else" to `web`.
- **Problem:**
  - As specified, Caddy also proxies `/print/*` publicly, so only the token protects it.
  - The variant rules (viewer role, AI section, letter) are not assigned to any layer. If the print page decides, staff PDFs can include the Student-only letter.
- **Fix:**
  - Caddy denies `/print/*`.
  - `reports.service` composes a variant-specific report model (viewer, `include_ai`, `include_letter`), checked against AD-12. The print page renders only that model.
  - The PDF cache key includes the variant.

### F28 — The Replay scenario is a template, not a settings object

- **Severity:** low
- **PRD:** FR-49 (the default step Week and number of Weeks vary per Student, between Weeks 5 and 12 and 30 to 40 Weeks; a fresh seed per Student; the Lecturer may set every setting).
- **Spine:** the Settings convention says `engine.GameSettings` is "the single schema for Game settings and the Replay scenario".
- **Problem:** a scenario contains ranges that a concrete Game's settings do not.
- **Fix:** add `engine.ScenarioTemplate` (`GameSettings` with ranged fields) plus a pure `materialise(template, seed) -> GameSettings`. The Replay Game stores the materialised settings and the seed (AD-4).

### F29 — No sub-processor register and no data processing agreement gate

- **Severity:** low
- **PRD:** §6.1 (providers and routers listed as sub-processors; a data processing agreement signed "before any Institution's Students are invited"; a DPIA pack with data flows).
- **Spine:** the Deferred section mentions Resend residency only. Railway, Supabase, the LLM provider and any future error-tracking tool are also sub-processors.
- **Fix:**
  - Add a short sub-processor table (service, data, region, transfer basis) to the spine or the setup guide as the DPIA input.
  - Add `institutions.dpa_signed_at`. Sending Invitations to Students of an Institution without it is refused (`dpa_missing`).

### F30 — Seat claims and allocation fall outside the single write path

- **Severity:** low
- **PRD:** FR-20 (allocate, re-run, move and swap before the Start date; a late registrant goes into a free AI-held Seat), FR-21 (Student choice: one Seat per session; random allocation of the rest at the Start date).
- **Spine:** AD-2's command list covers play only, yet says "only `games.commands` mutates a Game".
- **Problem:** two Students claiming the same free Seat at the same moment, or a move racing a re-run, are unguarded.
- **Fix:** add `allocate`, `move_student`, `claim_seat` and `place_late_registrant` to the commands (session-level lock for allocation, Game row lock for Seats), with a unique constraint `(class_session_id, user_id)` on Student Seats.

### F31 — Per-session error counts have no store

- **Severity:** low
- **PRD:** NFR-8 (per Class session: error counts, fallback rate, AI response times, AI cost).
- **Spine:** structlog to Railway logs. `llm_call` covers the AI metrics.
- **Problem:** error counts per Class session cannot be queried from Railway logs.
- **Fix:** keep a small `ops_error_counts(class_session_id, day, kind, n)` table, incremented by the error handler and by jobs, and read it on the Admin screen.

### F32 — No database connection budget

- **Severity:** low
- **PRD:** NFR-3, NFR-4.
- **Spine:** both processes use the Supabase session pooler on :5432; each `api` holds a `LISTEN` connection; procrastinate also uses `LISTEN`.
- **Problem:** with three worker lanes (F7), one or more `api` replicas and the SQLAlchemy pools, session-mode pooler limits on the chosen Supabase compute tier can be reached in a Lab hour.
- **Fix:** add a line to the Deferred load-test entry: size `pool_size` per process against the tier's pooler limit, and confirm that `LISTEN` works through the session pooler, or use a direct connection for the listeners.

---

## Covered adequately (no action)

- FR-26 Week sequence and FR-29 conservation, through AD-1 and AD-4.
- FR-23 and FR-83 visibility, through AD-3 (see F13 for the gaps).
- FR-60 and FR-59: no AI in the Completion export or the ZIP (AD-16, AD-18).
- FR-56: a Student-only letter is hidden from staff (AD-12; see F27 for PDFs).
- FR-13 test Games excluded (AD-13), apart from F17.
- NFR-5 reconnection through refetch (AD-8).
- §9.1 Debrief separable from the players (AD-7).
- FR-79 Play guard switch permanence (AD-5).
- §8.1 cut list behind feature flags (AD-17).

## Suggested Deferred additions

- Sizing of the limiter and priority shares per provider plan (F8).
- Reserve size per Student for the Debrief and AI assessment (F15).
- The Institution's pseudonym-key arrangement, if it declines to hold the key (F10).
- The SM-4 tolerance after the Play deadline for completing the playout (F12).
- Whether student numbers are collected at all (F9).
