---
title: 'Rubric review: ARCHITECTURE-SPINE.md (ØL-spillet v1)'
reviewed: ARCHITECTURE-SPINE.md (status draft, 2026-11-12)
also-read: .memlog.md, SETUP-GUIDE.md, ../technology.md, PRD prd-beergame-2026-10-29 (§3, §4, §5, §6, §8, §10)
date: '2026-11-12'
---

# Rubric review: ARCHITECTURE-SPINE.md

## Verdict

The spine is strong and close to ready. It is terse, it is organised around real divergence points (one write path, one information boundary, one LLM boundary, facts-only narration, one reporting scope), and it adapts the founder's stack sensibly. One rule as written produces wrong gameplay (Guided Weeks). A handful of cross-unit contracts are missing or split between two ADs: retry ownership, the cost-limit switch, the report data path, content versioning and migration compatibility. Several operational decisions live only in SETUP-GUIDE.md, although the guide itself says the spine wins. Fix the critical and high items before epics are cut.

## Scorecard

| # | Criterion | Result | Notes |
| --- | --- | --- | --- |
| 1 | Fixes the real divergence points, misses none | Mostly | 19 ADs hit the right seams. Missed: content and item versioning (H-6), Group debrief shared progress (M-1), migration compatibility (H-7), and which commands emit which events (M-6). |
| 2 | Each Rule is enforceable and prevents its divergence | Mostly | AD-2 with AD-5 breaks FR-24 (C-1). AD-5 and AD-6 both own retries (H-1). AD-14's key-custody rule cannot be enforced as written (H-4). Most other rules are checkable in code review or CI. |
| 3 | Nothing under Deferred lets units diverge | Mostly | Provider, parameters, staging and monitoring are deferred safely behind interfaces. "MVP relies on daily backups" conflicts with NFR-4 (H-8). The Play guard and Rule-based function signatures should be fixed now, even though their parameters are deferred (L-5). |
| 4 | Named tech verified-current | Yes, with small gaps | Every version in the Stack table matches the memlog, except openpyxl 3.1.5 and @fontsource/source-sans-3 5.3.1, which are missing from it. Both were spot-checked during this review and are current: PyPI openpyxl is 3.1.5 (no newer release since 2024-06), npm `latest` is 5.3.1. procrastinate 3.11.0 and pydantic-ai 2.68.0 were re-checked and also match. Jinja2, httpx and the axe integration are used but not listed (L-1). |
| 5 | Covers the spec's capabilities | Mostly | The Capability map covers FR-1 to FR-89 by range. Thin or missing: FR-8 and NFR-10 bounce intake (only in the guide), FR-69 session-wide switch semantics (H-2), NFR-3 rate limits (H-3), NFR-8 per-session error counts (M-2), and FR-52, FR-65 and FR-81 content versions (H-6). |
| 6 | Every owned dimension is decided, deferred or open | Partly | Deployment and environments are decided. Secrets, CI gating, RPO and backups, connection budget, abuse controls, domain and DNS, and the Admin bootstrap are either missing or only in SETUP-GUIDE.md (H-5, H-7, H-8, M-3, M-4, M-7). |
| — | Right-sized | Yes | About 410 lines, with Binds, Prevents and Rule in each AD and almost no rationale. A few seed-level details sit inside Rules (the CSRF header value, the WeasyPrint variant name), which is harmless. The Capability map partly repeats the Binds lines, which is acceptable. |
| — | technology.md adapted sensibly | Yes, with silent drops | It keeps what fits: FastAPI and uv, async SQLAlchemy and Alembic, Next 16, React 19, Tailwind 4, shadcn, TanStack Query, Caddy as single origin, Railway, Supabase, Resend and Jinja, WeasyPrint, pydantic-ai, the mock fallback, the startup guard and the `production` branch. It correctly drops payments, Redis, the content service, the editors, cutover and plugins. Two deviations are justified: Postgres-backed procrastinate instead of Redis, and a real Postgres in CI instead of aiosqlite. Some deviations are tagged only in the memlog (M-8). Per-IP rate limiting, CSP and DOMPurify, and the `ADMIN_EMAILS` bootstrap were dropped without a word (H-5, M-7). |

---

## Critical

### C-1. Guided Weeks cascade through AD-2 and AD-5, which breaks FR-24

- **Where:** AD-2 says: "When the last Order of a Week arrives, the same transaction advances the Week and opens the next one." AD-5 says: "In Guided Weeks, and for `rule_based` Seats, `open_week` places the Order itself in the same transaction."
- **Problem:** In Guided Weeks every Seat's Order is fixed. If `open_week` places all four Orders, the last one triggers the advance, which calls `open_week` again. All Guided Weeks then run in one transaction the moment the Game starts. FR-24 says a Guided Week advances "once every Student in the Class game has opened it", and that the Inactivity clock does not run. No command records that a Student has opened a Week, so the games team and the players team will each invent their own advance condition. The same recursion also runs a whole playout (FR-38) inside one transaction that holds the Game lock. That may be what we want, but the spine should say so explicitly.
- **Fix:** Amend AD-2 and AD-5:
  1. Add an `acknowledge_week(seat, week)` command, written when a Student's Seat view for that Week is first served after the Week opened.
  2. State the advance condition as one predicate in `games.commands`: every Seat has an Order **and**, in a Guided Week, every Student-occupied Seat has acknowledged it.
  3. State that playout and all-AI chains advance one Week per transaction, by re-enqueueing a command or a job, never by recursing inside one transaction. This keeps lock time bounded and lets the sweeper resume a playout that was cut off.

---

## High

### H-1. Retry ownership is split between AD-5 and AD-6

- **Where:** AD-5 says the `ai-orders` job "retries at most 5 times". AD-6 step 4 says the gateway "applies the per-attempt timeout and the retry rule".
- **Problem:** If both layers retry, one Order can make up to 36 attempts. Budget and timeout accounting then disagree, and `llm_call` rows can no longer be read as "one row per attempt of one Order". FR-32 and NFR-2 depend on a single count.
- **Fix:** Give retries to one owner. Recommended: the gateway owns attempts, timeouts and the total time budget. It takes `deadline` (absolute) and `max_attempts` as inputs and returns `Ok(output) | Failed(reason ∈ {schema, range, timeout, budget, provider})`. The job only maps `Failed` to the Rule-based fallback and calls `place_order`. Delete the retry wording from AD-5. Range validation (FR-32: a value out of range counts as a schema failure) must happen inside the gateway's retry loop, so `output_schema` must carry the bounds from GameSettings.

### H-2. The cost-limit switch (FR-69) has no defined path

- **Where:** AD-6 step 2 "checks and charges the budget, with a reservation". AD-5 lists `switch_to_rule_based` only for the Play guard.
- **Problem:** FR-69 says that when the limit is reached, every LLM player in the whole Class session becomes Rule-based for the rest of that session. FR-68 says reports record when the limit took effect. As written, an implementer can let the gateway refuse the call. The job then marks a per-Week fallback, the Seat stays `llm`, and later Weeks keep asking. Fallback rates in SM-3a would then be polluted by budget refusals.
- **Fix:** Add to AD-5:
  1. The gateway returns `Failed(budget)` for player purposes once only the reservation is left.
  2. On the first `Failed(budget)` in a Class session, the players module calls `games.commands.switch_to_rule_based(reason=cost_limit)` for every `llm` Seat in that session's running Games. This appends occupancy rows and keeps the change permanent for the session, as with the Play guard.
  3. The Lecturer notice and the report marker read from those occupancy rows.

  Also name the Debrief and AI assessment behaviour when the reservation runs out: the Debrief renders from code, and the AI assessment is held for an Admin decision.

### H-3. The AI-order latency path cannot meet NFR-2 or NFR-3 as written

- **Where:** AD-5 (job enqueued after commit), AD-9 (1-minute sweeper), and Deferred (load test).
- **Problem:**
  - (a) A job lost between commit and enqueue, or stuck behind a busy queue, is caught only by the sweeper, up to about 60 s later. NFR-2 says a Student waits *at most the budget*, which the PRD expects to be around 8 s.
  - (b) Nothing in the spine limits concurrency or the request rate against the pinned endpoint. With 250 Students in Replays, about 750 AI Seats ask at once each Week. NFR-3 says explicitly that "rate-limit errors do not cause mass fallback". If this is left to each module, every module will improvise.
- **Fix:**
  - Add to AD-6: the gateway holds a per-endpoint concurrency and rate limiter, configured in the pinned model config. A rate-limit wait counts against the Order's deadline, and 429 responses are logged as their own outcome.
  - Add to AD-5: the job's deadline is `opened_at + budget`, not the time the job started. A job that starts after its deadline places the fallback at once.
  - Make the enqueue transactional, by deferring the procrastinate job on the same connection and transaction as the command. Or make `ops.sweep` check AI-order deadlines more often (for example every 5 s, in its own loop).
  - Give `ai-orders` dedicated worker concurrency, so `llm-batch` and `reports` cannot starve it.

### H-4. AD-14 key custody cannot be enforced as written

- **Where:** AD-14 says `PSEUDONYM_SECRET` is "held outside the founder's sole control". AD-17 says production refuses to start without `PSEUDONYM_SECRET`. SETUP-GUIDE §3.1 says it is generated by someone else but stored as a Railway variable.
- **Problem:** A Railway variable in the founder's project can be read by the founder, so the PRD §10 pilot precondition is not met. Two developers would also build the export differently: one with an env key, one with a key typed in at export time.
- **Fix:** Decide now:
  - (a) The FR-71 export takes the key as an input at export time from the key holder. It is never stored, and AD-17 drops it from the startup list. Or:
  - (b) The key lives in a secret store the founder cannot read, administered by the Institution. Check whether Railway supports this before choosing it.

  Either way, add a check-value (`HMAC(key, "check")` stored in the DB), so a wrong key is rejected rather than silently producing new pseudonyms.

### H-5. There are no abuse controls on public endpoints

- **Where:** AD-11 and AD-12. technology.md §2 had "Per-IP rate limiting on auth and AI routes", and the spine dropped it silently.
- **Problem:** Login, password reset, Invitation acceptance and the Debrief follow-up endpoint are reachable from the internet. Follow-up spends LLM budget in the api process. Without a shared rule, each module will add its own limit or none at all. Behind Railway and Caddy, the client IP is only correct if trusted-proxy headers are configured once.
- **Fix:** Add to AD-11:
  1. One `platform/ratelimit` dependency, backed by Postgres or in-process, since one replica is assumed. It is applied per IP and per account on auth, reset and Invitation routes, and per User and Class session on every route that calls `ai.run`.
  2. Uvicorn runs with `--proxy-headers` and only Caddy's address is trusted.
  3. Set a CSP for `web`.
  4. LLM text is rendered as plain text or through one sanitising component, never as raw HTML.

### H-6. There is no AD for content identity and versioning

- **Where:** The spine is silent. The PRD needs this in FR-46, FR-52, FR-53, FR-65 ("labelled when question set, Item weights or Scoring guide version differ"), FR-81 (guide version in force at the Test deadline), FR-85 (Starting task items repeated in the test) and FR-44 (approved sentence templates and Detected patterns reviewed by two lecturers).
- **Problem:** Several modules reference the same items by id: `tests`, `assessment`, `debrief`, `reports` and `analysis` for Class report results per question. Without one rule, item ids, versions and snapshot points will diverge, and Cross-class comparability (FR-65) cannot be computed.
- **Fix:** Add a new AD, "Content is versioned data with stable ids":
  1. Product content lives as versioned files in the repo with stable ids, loaded at startup: question set, Debrief quiz, Starting task, Interactive item definitions, Adapted item templates, Detected pattern catalogue, sentence templates and the default Scoring guide.
  2. A Class session snapshots `content_version` at the Start date, alongside AD-4's settings snapshot.
  3. Lecturer edits are stored as new versions in the DB: exclusions, Item weights and Scoring guide edits. The Scoring guide version is frozen at the Test deadline.
  4. Every answer, score and `llm_call` row records the item id and version.

### H-7. Migration compatibility and deploy ordering are not fixed

- **Where:** Consistency Conventions, Migrations: "Alembic only, forward-only in production, run as the Railway pre-deploy command of `api`".
- **Problem:** `api` and `worker` are separate Railway services built from the same image, and they deploy independently with overlap. During a deploy, old and new code run against the new schema. If the worker deploys before the api pre-deploy finishes, new code runs against the old schema. Story authors will write breaking migrations, such as a rename or a NOT NULL without a default, during Lab hours. procrastinate's own schema migrations have no owner.
- **Fix:** Amend the Migrations convention:
  - Every migration is expand/contract. Each release's schema must work with the previous release's code.
  - Destructive steps go in a later release.
  - The worker waits on startup until `alembic current` matches head.
  - procrastinate's schema SQL is applied through Alembic revisions, never by `procrastinate schema --apply` in production.
  - No migrations run during scheduled Lab hours.

### H-8. The backup posture contradicts NFR-4, and the plan tier is undecided

- **Where:** Deferred says "The MVP relies on Supabase daily backups". SETUP-GUIDE §5 says "consider point-in-time recovery".
- **Problem:** NFR-4 says "Game state is never lost once a Week has been shown". Daily backups mean up to 24 h of lost Orders, Explanations and test answers if the database is lost. This is an operational-envelope decision, it is cheap to make now, and it affects the DPIA text and the Railway and Supabase plan choice. Availability of 99.5% during Lab hours also depends on the plan tier, for both Supabase and Railway.
- **Fix:** In the spine, set RPO and RTO targets, for example RPO ≤ 5 min and RTO ≤ 2 h. Choose Supabase Pro with PITR from the rehearsal onward, and state the Railway plan tier. Keep offsite backup and the restore drill under Deferred, with the trigger "before pilot".

---

## Medium

### M-1. Group debrief and Test sittings have shared progress with no single write path

AD-2 covers only the Game. A Group debrief "moves on when every joined Student has finished it, or when the opener moves it on" (FR-43), which has the same race as a Week advance. The Test has a similar race between autosave and auto-submit at the deadline, driven by the sweeper (FR-51). **Fix:** Widen AD-2 into a general rule: aggregates with shared progression (`Game`, `GroupDebrief`, `TestAttempt`) change only through their module's `commands`, each command running in one transaction with `SELECT … FOR UPDATE` on the aggregate row. A submitted TestAttempt rejects later saves.

### M-2. NFR-8 per-session error counts have no mechanism

The Capability map points NFR-8 to AD-6 only. `llm_call` gives fallback rate, latency and cost, but not "error counts" per Class session. FR-29 conservation failures are "logged as an error", and logs go to Railway with no error tracker. **Fix:** Add one `platform/ops_events.record(kind, class_session_id, game_id?, detail)` table, written by the conservation check, by job failures after their final retry and by gateway failures. The Admin view reads from it. Error tracking (Deferred) can be added on top later.

### M-3. The database connection budget is not an invariant

The Supabase session pooler limits clients to the plan's pool size. The total is the SQLAlchemy pool in api, plus the LISTEN connection, plus the procrastinate pool and the SQLAlchemy pool in worker, plus Alembic, plus staging. Each team will size its own pool. SETUP-GUIDE §3.1 gives a hint (10 + 5), but procrastinate's own psycopg pool is not counted. **Fix:** Add a Conventions row: a named budget per process (for example api ≤ 10 including LISTEN, worker ≤ 8 including procrastinate), set from env, and a startup check that the sum fits the documented plan limit. Also state that the direct connection or IPv4 add-on is the escape route.

### M-4. CI gating and promotion to production are undefined

The `production` branch auto-deploys, but nothing says it deploys only after CI is green, or who merges `main` into `production`. The planned staging environment needs an `APP_ENV` value, and AD-17 only knows `{local, test, ci, production}`, so staging would either run with mocks or pretend to be production. **Fix:** State in the spine that Railway deploys only after GitHub checks pass ("Wait for CI"), and that `production` is fast-forwarded from `main` by a PR. Add `APP_ENV=staging` with the same strict guard as production.

### M-5. The tagged-PDF claim for NFR-6 is unverified

The memlog says WeasyPrint's `pdf/ua-1` output is "not guaranteed valid". The spine does not carry this caveat, yet NFR-6 is a pilot precondition. FR-59 needs 250 PDFs in 10 minutes, and at about 2–4 s per WeasyPrint render that only works with parallel `reports` workers. **Fix:** Add to AD-18:
- A veraPDF or PAC check of a golden report in CI.
- Fonts are embedded from the worker image.
- The `reports` queue concurrency is sized so the ZIP target holds.
- Under Open questions: the fallback if PDF/UA validation fails.

### M-6. Event emission per command is not fixed

AD-8 lists topics but not who emits what. A developer can update a Game and forget `session:<id>`, so the Lecturer overview (FR-39, 5 s) or a Student's home screen (`user:<id>`, FR-25) goes stale. **Fix:** Add to AD-8: each command declares its topic set in one registry. Every `games.commands` command always emits `game:<id>` and `session:<id>`, and emits `user:<id>` for each Student whose waiting status changed. A test asserts that every command has a registry entry.

### M-7. Load-bearing operational decisions live only in SETUP-GUIDE.md

The guide says "the spine wins", but only the guide has these:
- Caddy blocks `/print/*`. The spine's AD-11 routes "everything else to web", which contradicts AD-18's "reachable only from the internal network".
- The `/api/webhooks/resend` bounce intake with `RESEND_WEBHOOK_SECRET` (FR-8, NFR-10).
- The Admin bootstrap through `BOOTSTRAP_ADMIN_EMAILS`. There is no open sign-up, so this is the only way in.
- The domain and DNS provider for SPF, DKIM and DMARC.
- The paid Supabase plan.
- The signed URL TTL.

AD-17's startup list also omits `INTERNAL_TOKEN`, `RESEND_WEBHOOK_SECRET` and `SUPABASE_SERVICE_ROLE_KEY` by name. **Fix:** Promote these to spine Rules: AD-11 for the proxy block and the bootstrap, AD-9 or a new email rule for the bounce webhook, AD-17 for the full required-secret list. Add a Stack or Structural Seed row for the domain and DNS.

### M-8. The report generation data path bypasses AD-12

Worker → `web /print/report/<id>` → (server-side) `api`. To render, `web` must read a Student's full report data, but the spine never says with what credential. In practice `INTERNAL_TOKEN` becomes a token that bypasses every scope check. **Fix:** Add to AD-18:
- The report request is authorised by AD-12 at enqueue time and stored as a `report_job`.
- The print route calls `GET /api/internal/report-jobs/<job_id>/data` with `INTERNAL_TOKEN`. The api serves data only for an open job, and the AI-assessment section only if the job says to include it (FR-58, FR-59).
- Caddy blocks `/api/internal/*` as well as `/print/*`.

### M-9. Deviations from technology.md are tagged inconsistently

The spine tags only AD-11 and AD-17 `[ADOPTED]` and AD-18 `[ASSUMPTION]`. These choices are explained only in the memlog: psycopg instead of asyncpg, Supabase eu-central-1 as an assumption, procrastinate and structlog as new additions, Node 24 when 26 is the current LTS, and TypeScript 6 when 7 exists. **Fix:** Add a short "Deviations from technology.md" line set under Stack, tagging each item `[DEVIATION]`, `[ADOPTED]` or `[ASSUMPTION]` with a one-clause reason. List the silent drops explicitly too (rate limiting, CSP and DOMPurify, `ADMIN_EMAILS`), and say whether each is replaced or truly dropped.

### M-10. AD-14's personal-data inventory is incomplete

AD-14 lists Explanations, reflection and follow-up text, and test answers. Other things also contain Student text or quotes:
- AI assessment feedback, which quotes answers (FR-54).
- Debrief summaries (FR-47).
- Follow-up answers.
- `llm_call` prompt and response bodies, if stored. The spine does not say whether they are.

Supabase backups keep deleted data for the backup window. **Fix:** State that `llm_call` stores no prompt or response bodies, or that it stores them in a free-text table subject to the same retention. Add AI assessment feedback and Debrief summaries to the retention sweep. Note the backup window in the DPIA data flow.

### M-11. AD-4's replay at `rules_version` has no mechanics

"Replays the engine at that `rules_version`" requires older rule versions to stay executable. The spine does not say how. A developer fixing an engine bug mid-pilot would break conservation checks on finished Games. **Fix:** Add to AD-4:
- Any change that alters engine output bumps `rules_version` and keeps the previous version selectable, via `engine.rules[v]`.
- Golden traces per version run in CI.
- No `rules_version` change is deployed while a Class session is between Start date and Play deadline, unless it is a recorded correction.

---

## Low

- **L-1. Stack table gaps.** Jinja2 (AD-19), httpx (worker fetches the print route), `@axe-core/playwright` (Testing), ruff (SETUP-GUIDE CI) and pytest-asyncio are used or implied but not listed. Add them with versions, and add openpyxl and @fontsource to the memlog's verified list. Both were spot-checked current on 2026-11-12.
- **L-2. Runtime choices to revisit.** Node 24 is in maintenance LTS now that 26 is the active LTS (supported to April 2028, so it is fine for v1). Add a review date for Node 26 and TypeScript 7 after the pilot.
- **L-3. AD-7's quote check against scrubbed text.** The LLM sees scrubbed text, so its quotes may contain placeholders and fail the substring check against the original. **Fix:** Validate against the scrubbed text, and render the quote from the original by span offsets.
- **L-4. SSE robustness.** Add a heartbeat (for example a comment every 15 s) and state that streams may be cut by Railway or proxy request limits. EventSource reconnect plus AD-8's refetch-all already covers correctness.
- **L-5. Fix the pure-function signatures now, defer only the parameters.** Examples: `rule_based_order(settings, seat_view, history) -> int`, `near_optimal_order(settings, full_state) -> int`, `play_guard(history_with_refs, params) -> GuardDecision`. This stops players and analysis from each shaping their own inputs while issues #8 and #20 settle the numbers.
- **L-6. Session lifetime.** Thirty-day JWTs (SETUP-GUIDE) on shared lab laptops (FR-74) are risky. Set an idle expiry, and state that logout clears the cookie on the server side through a `token_version` on the User.
- **L-7. Interactive item answer format.** Fix one canonical JSON shape per item kind (table, number, later drawing). Computed scoring (FR-80), the PDF image and table alternative (FR-58) and the AI assessment explanation must all read the same shape.
- **L-8. Capability map omission.** FR-22's "propose and accept a time to play" aid has no home. Assign it to `games` or `sessions`, and it must emit on `game:<id>`.
- **L-9. Cross-region round trips.** With Railway in Amsterdam and Supabase in Frankfurt, every query in the locked Week-advance transaction is a round trip of several milliseconds. Measure lock hold time in the load test against the NFR-1 2 s target.

---

## What is good and should stay

- **The core seams are the right ones:** AD-1/AD-4 (pure, replayable engine), AD-2 (one write path), AD-3 (one Seat view feeding both the UI and the LLM prompt), AD-6/AD-7 (one LLM boundary, facts-only text with code fallback), AD-13 (one reporting scope) and AD-16 (Completion without AI input). Each one closes a divergence the PRD would otherwise invite.
- **The Debrief is kept separate from LLM players** (AD-7: `debrief` never imports `players`). This honours PRD §9.1 structurally rather than by convention.
- **Push invalidates, pull reads** (AD-8) avoids a second data path for live state and makes reconnection (NFR-5) trivial.
- **Timers are data with one sweeper** (AD-9). This is the right answer to lost scheduled jobs.
- **Deferred items carry triggers and owners** (issues #8, #9, #17, #20; "before the pilot").
- **The size is right:** rules are terse, there is almost no rationale prose, and structure is clearly marked as seed.
