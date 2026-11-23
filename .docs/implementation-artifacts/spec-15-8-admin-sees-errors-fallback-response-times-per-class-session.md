---
title: 'Story 15.8: The Admin sees errors, fallback and response times per Class session'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '1744768c3750e2511b6d37f9fd484f35d66b2e0e'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-15-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** NFR-8 asks for error counts, fallback rate, AI response times and AI cost per Class session, but the spine defers the store for per-session error counts, and the Admin has no screen to watch a Lab hour.

**Approach:** Settle the store: an `error_events` table owned by `modules/ops`, written only through `ops.service.record_error(source, code, class_session_id, request_id)`, fed by the sweep's finished-game check, a worker middleware for failed jobs and the request-log middleware for 5xx answers. Add «Drift» to the Admin-område: a list of Class sessions and a per-session view with errors by source and hour, fallback by kind, response times per Effort level, the Play guard share and AI cost, each chart with «Vis som tabell», read again every 30 s.

## Boundaries & Constraints

**Always:**
- Table `error_events` (migration `0069`, `ops/models.py`): `id` uuid7, `source` text CHECK in (`conservation_check`, `job_failed`, `api_error`), `code` text (≤ 80, a fixed technical value), `class_session_id` uuid NULL (no FK), `request_id` text NULL, `occurred_at` timestamptz (the writer's clock, `datetime.now(UTC)`). Index `(class_session_id, occurred_at)`. Ids and codes only. Registry entry (`identity/personal_data.py`): handling `none`, note says rows hold no personal data and are kept at retention.
- `ops.service.record_error(source, code, class_session_id=None, request_id=None, *, at=None) -> bool` writes in its own transaction; any exception is caught, logged as `error_record_failed` with `exc_type`, and returns False. Never raises.
- Sources:
  - `conservation_check`: `ops.sweep._verify_finished` records one row (`code="game_check_failed"`) when a newly stored check is not ok, with the Game's `class_session_id` from new `games.service.class_session_of(game_id)`. Covers Class games, played-out games and Replays (all carry `class_session_id`).
  - `job_failed`: `platform/jobs.run_worker(..., on_failure=None)` adds a procrastinate worker middleware that, when a job raises and its task has no retry (`get_retry_exception` is None), awaits `on_failure(task_name, task_kwargs, job_id)` inside try/except and re-raises the job's exception. `worker.py` passes `ops.service.record_job_failure`, which resolves the Class session from a `class_session_id` kwarg or a `game_id` kwarg (through `class_session_of`) and records `code=<task name>`, `request_id=str(job_id)`.
  - `api_error`: `RequestLogMiddleware(app, on_server_error=None)`; after a response with status ≥ 500 (or an unhandled exception) it awaits `on_server_error(status, class_session_id, request_id)` in try/except, `class_session_id` from the route's `path_params` when it is a UUID. `main.py` passes `ops.service.record_api_error` (`code="http_<status>"`).
- `platform` imports no module: both hooks are injected.
- Figures for one Class session, in `ops/operations.py`, read only through owners: errors from `error_events` (ops); AI cost (`usd`, `calls`) and response times per Effort level (`player_order` attempts of the `class_session` scope: `calls`, median and p95 `latency_ms`, nearest-rank via `percentile_disc`) from new `ai.calls.session_figures`; fallback and Play guard from new `games.service.session_ai_figures`, over Games of the session except `lecturer_test`: LLM-path Orders (`seat_weeks.occupant_kind='llm'`, `decided_by<>'guided'`) and per fallback kind (every `Fallback` but `none`, zero included, named by `seat_mark`), LLM Seats (first occupancy `llm`) and those with a `guard_switch` row whose mark is `guard_switch` (AD-15).
- Policy `operations.read` (Admin only). `GET /api/admin/operations/class-sessions` (every saved Class session, newest first: `id`, `label` «class-of-1994 · Klasseøkt 2», `institution_name`, `errors_24h`) and `GET /api/admin/operations/class-sessions/{id}` (404 `not_found`): `label`, `institution_name`, `read_at`, `hours` (24 hour starts ending with the current hour, UTC ISO, each with `conservation_check`, `job_failed`, `api_error` counts), `totals` (same three, all time), `llm_orders`, `fallbacks` [`kind`, `orders`, `share`], `response_times` [`effort_level`, `calls`, `median_ms`, `p95_ms`], `llm_seats`, `switched_seats`, `switched_share`, `cost_usd`, `ai_calls`. Shares are decimal strings 0–1 with 4 places or null when the base is 0; USD with 8 places.
- Frontend `frontend/src/modules/ops/`: `/admin/drift` list and `/admin/drift/[sessionId]` view; Admin-område link «Drift» after «KI-kostnad». Charts are HTML bars (`aria-hidden`) with «Vis som tabell» swapping to a table: «Feil per time» (stacked per source, hour labels in Oslo time), «Reserveordre per type» (share bars), «Svartid per innsatsnivå» (median and p95 bars). Play guard share and AI cost as figures. `refetchInterval` 30 s; `PageShell` gets `updatedAt` = last successful read; a failed background read shows the Tilkoblingslinje via `liveLines.failed` with «Prøv igjen», keeping the last figures. Skjelett while loading. All copy in `nb.ts`, `[ASSUMPTION] Story 15.8`. No primary button.
- Spine `ARCHITECTURE-SPINE.md` Deferred entry «Per-session error counts» marked settled by Story 15.8, noting the counts do not depend on the external tracker (issue #28).

**Never:**
- No name, email, free text, exception message or stack in `error_events` or the answers; no Student names, answers or AI assessments on the view.
- No code outside `app/ai` reads `llm_call`; nothing outside `ops` writes `error_events`; `platform` imports no module.
- No external error tracker (Story 15.11), no connection-budget figure (Story 15.9), no SSE topic.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Violation | finished Class game / playout / Replay with tampered Week | one `conservation_check` row under its session each | — |
| Passing check | clean finished Game | no row | — |
| Failed job | task with `game_id` raises | one `job_failed` row, code = task name, session of the Game; job still failed | — |
| 5xx | route under `/class-sessions/{id}` raises | 500 answered; one `api_error` row with that session and the request id | — |
| Store down | `record_error` cannot write | returns False, caller unaffected | logged `error_record_failed` |
| Empty session | no games, calls or errors | zeros, null shares, empty response times | — |
| Not Admin | Lecturer GET | 403 `forbidden` | — |
| Unknown id | GET view of a random uuid | 404 `not_found` | — |

</intent-contract>

## Code Map

- `backend/app/modules/ops/sweep.py:95` `_verify_finished` -- add the record after a not-ok check.
- `backend/app/modules/games/checks.py:49`, `games/service.py:19,200` -- `GameCheck`; export `class_session_of`, `session_ai_figures` (new, in a new `games/operations.py` using `marks.seat_mark`, `models.seat_weeks`, `seat_occupancy`, `seats`, `games`).
- `backend/app/platform/jobs/__init__.py:160` `run_worker` -- procrastinate 3.11 `run_worker_async(worker_middleware=[...])`; middleware signature `(call_next, context, worker)`, `context.job.task_name/task_kwargs/id`, `worker.app.tasks`.
- `backend/app/worker.py:57` `serve` -- pass `on_failure`.
- `backend/app/platform/logging.py:95` `RequestLogMiddleware` -- `on_server_error`; `main.py:149` add middleware with it; include the new router.
- `backend/app/ai/calls.py:157` `day_spend` pattern; add `session_figures`, `PLAYER_PURPOSE` exists.
- `backend/app/modules/ops/{models,ai_routes,ai_schemas,spend_alert}.py` -- table, route and label patterns (`sessions.evaluation_sessions`).
- `backend/app/platform/authz.py:171` -- add `operations.read`.
- `backend/app/modules/identity/personal_data.py:109` -- registry entry.
- `backend/tests/{conftest.py,test_imports.py,test_migrations.py}` -- table lists, head `0069`; `tests/games/helpers.py` `classic_game`, `tamper`, `execute`; `tests/ops/test_daily_spend_alert.py` for `client`, `as_user`, `make`, `new_session`, `klass`, `spend`.
- `frontend/src/modules/admin/{ai-models-page.tsx,api.ts,evaluation.ts,user-list.tsx}` -- table, `Cell`, `sessionLabel`, query pattern; `modules/games/insight-charts.tsx:71` `ChartBlock`; `components/connection-notice.tsx` `LiveLines`; `modules/identity/{home-page.tsx,homes.ts}`; `e2e/admin-ai-models.spec.ts`, `e2e/support/{auth,classes}.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0069_error_events.py`, `app/modules/ops/models.py` -- table, check, index.
- `backend/app/modules/ops/service.py` -- `record_error`, `record_job_failure`, `record_api_error`, `SOURCES`.
- `backend/app/modules/games/{operations.py,service.py}` -- `class_session_of`, `session_ai_figures`.
- `backend/app/ai/calls.py` -- `session_figures`.
- `backend/app/modules/ops/sweep.py`, `app/platform/jobs/__init__.py`, `app/worker.py`, `app/platform/logging.py`, `app/main.py` -- the three hooks.
- `backend/app/modules/ops/{operations.py,operations_routes.py,operations_schemas.py}`, `app/platform/authz.py` -- read and routes.
- `backend/app/modules/identity/personal_data.py`, `tests/{conftest,test_imports,test_migrations}.py` -- registry and table lists.
- `backend/tests/ops/test_error_events.py` -- every matrix row, each source, figures with seeded `seat_weeks`/occupancy/`llm_call`, no personal data in answers.
- `.docs/planning-artifacts/architecture/architecture-beergame-2026-11-12/ARCHITECTURE-SPINE.md` -- Deferred entry settled.
- `frontend/src/copy/nb.ts`, `src/modules/ops/{api.ts,operations.ts(+test),operations-page.tsx,session-list-page.tsx,ops-charts.tsx}`, `src/app/(app)/admin/drift/{page.tsx,[sessionId]/page.tsx}`, `modules/identity/{homes.ts,home-page.tsx}`, `src/lib/api/*` (regenerated).
- `frontend/e2e/admin-operations.spec.ts` -- list → view of a fresh Class session (zeros), charts and «Vis som tabell» with routed figures, failed refetch line, Lecturer denied; axe at 320/1440.

**Acceptance Criteria:**
- Given the view for a Class session with errors, fallbacks and calls, when the Admin opens it, then it shows errors by source and hour, fallback share by kind, median and p95 per Effort level, the Play guard share and AI cost, each chart with «Vis som tabell».
- Given the view open, when 30 s pass, then it reads again and shows «Sist oppdatert»; when a read fails, the Tilkoblingslinje says so with «Prøv igjen» and the last figures stay.
- Given the spine, when this story lands, then its Deferred entry on per-session error counts says it is settled with `error_events`.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
- layers: Blind Hunter and Edge Case Hunter (sonnet); Verification Gap and Intent Alignment skipped, as the lead asked for two reviewers.
- verdicts: 28 findings — high 0, medium 4, low 19, false 5, maybe-false 0
- findings:
  - `[medium]` `[patch]` Blind: a 5xx is placed only by a `class_session_id` path parameter; most routes name `session_id` or `game_id` — the request log now hands the hook every UUID of `class_session_id`, `session_id` and `game_id`; `record_api_error` takes the session from either name or from the Game; the test fails three routes, one per name.
  - `[low]` `[reject]` Blind: errors with no Class session are stored but shown nowhere — the story asks for counts per Class session; a total for unplaced errors is a new view section, left to Story 15.11's tracker, which sees every error.
  - `[low]` `[patch]` Blind: the list's rolling 24 hours and the view's 24 hour buckets disagree by up to an hour — the list now counts the same buckets (start of the hour 23 hours back to the end of the current hour).
  - `[low]` `[reject]` Blind: the violation count is not in the check's transaction, so a crash between them loses it — `game_checks` is `games`'; one transaction across both would make `games` write `ops`' table. The window is the two statements of one sweep item.
  - `[medium]` `[patch]` Blind: the 5xx hook is awaited on the request with no bound, so a database outage holds each failing answer longer — the hook runs under `asyncio.wait_for` (2 s); the job hook too (5 s).
  - `[low]` `[reject]` Blind: no test of a retried or aborted job — tasks are never retried (platform/jobs), and `JobAborted` passes before the retry check; a test of procrastinate's own retry path adds little.
  - `[false]` `[reject]` Blind: NULL `latency_ms` crashes the percentile — `llm_call.latency_ms` is `NOT NULL`.
  - `[low]` `[reject]` Blind: the played Games are an exclusion list (`!= lecturer_test`) — every purpose today is a Student's Game but the simulation, which has no Class session; a future purpose decides its own place.
  - `[false]` `[reject]` Blind: the first occupant by UUIDv7 id can misorder — the occupancy table's own rule is "the latest row by `id` (UUIDv7) is the current occupant" (games/models.py); the view follows it.
  - `[false]` `[reject]` Blind: the registry says `none`, not `keep` — `keep` means rows that keep a User's id; `error_events` holds no User, so `none`, and its note states the rows are kept.
  - `[low]` `[reject]` Blind: `CONSERVATION_CHECK, JOB_FAILED, API_ERROR = ERROR_SOURCES` unpacks by position — the tuple and the unpacking sit together and the migration test pins the check; a rename is a refactor with no defect now.
  - `[low]` `[patch]` Blind: the chart's comment says counts stand under the columns — the comment now names the lead's counts and «Vis som tabell».
  - `[low]` `[reject]` Blind: an unknown session id shows the page error with «Prøv igjen» — reached only by editing the URL; a not-found branch adds a state for it.
  - `[low]` `[reject]` Blind: raw Effort level names, a two-decimal cost, no date on hour rows, two «02» rows at the autumn shift — the Effort level names are the configs' own (shown so on «KI-kostnad»); the cost and hour formats follow Story 15.7.
  - `[low]` `[reject]` Blind: e2e hard-codes some copy — the same holds in the other Admin specs; the strings are checked against the page.
  - `[false]` `[reject]` Blind: the diff carries a Story 11.7 log entry — that is the orchestrator's commit on the branch after the baseline, not this change; issue tracking is the orchestrator's.
  - `[medium]` `[patch]` Edge: 34 Class session routes name `{session_id}`, so their 5xx count with no session — same as Blind 1, patched with it.
  - `[medium]` `[patch]` Edge: the hook waits during an outage — same as Blind 5, patched with it.
  - `[low]` `[patch]` Edge: a request cancelled before its answer counts as `http_500` — the middleware now skips the hook on `CancelledError`.
  - `[low]` `[reject]` Edge: a failure after a 2xx start of a streamed answer is not counted — only the event stream streams; its failures are logged, and the client reconnects.
  - `[low]` `[patch]` Edge: the list and view windows differ — same as Blind 3, patched with it.
  - `[false]` `[reject]` Edge: two sweeps count one failed check twice — the sweep task holds a queueing lock (one sweep at a time) and its finder takes only Games with no check; the crash half is Blind 4.
  - `[low]` `[reject]` Edge: unbounded growth, no purge — ids and codes only, kept by design (epic context: "Rows survive retention"); a purge needs a founder period.
  - `[low]` `[reject]` Edge: errors with no session are never shown — same as Blind 2.
  - `[low]` `[reject]` Edge: an unsaved Class session is readable by id but not listed — it has no Games, calls or errors; the list follows the saved-only rule of «KI-kostnad».
  - `[low]` `[reject]` Edge: test Game errors count, its Orders do not — a failing check or job of a Lecturer's test Game is still an error in that Class session; the fallback and guard figures are about Students' play.
  - `[low]` `[reject]` Edge: `TaskNotFound` is not counted — raised before the middleware for a task no worker registers; a deploy mismatch, logged by procrastinate. The hook timeout is patched (Blind 5).
  - `[low]` `[reject]` Edge: 404 or 422 shows the generic page error — same as Blind 13.

## Auto Run Result

Status: done

**Summary.** Story 15.8 settles the per-session error counts store: table `error_events` (migration 0069, owned by `modules/ops`), written only through `ops.service.record_error(source, code, class_session_id, request_id)` with `source` in `conservation_check`, `job_failed`, `api_error`, a fixed code and ids only; a failure to count is logged by type and never fails the caller. Three sources feed it: the sweep's finished-game check counts each failed check under its Game's Class session (Class games, played-out games, Replays); a procrastinate worker middleware in `platform/jobs` counts each job that fails for good (hook `ops.service.record_job_failure` passed from `worker.py`, Class session from a `class_session_id` or `game_id` argument); the request log middleware counts each 5xx answer (hook `ops.service.record_api_error` passed from `main.py`, Class session from a `class_session_id`, `session_id` or `game_id` path parameter), each hook bounded by a timeout. `platform` still imports no module. The spine's Deferred entry is marked settled (issue #28 untouched). «Drift per Klasseøkt» in the Admin-område (`/admin/drift`, policy `operations.read`, Admin only) lists every saved Class session with its errors of the last 24 hours; `/admin/drift/<id>` shows errors per source and hour (24 stacked columns, Oslo hours), the share of LLM players' Orders per fallback kind, median and p95 response time per Effort level (`ai.calls.session_figures`, nearest rank), the share of LLM Seats the Play guard switched (`games.service.session_ai_figures`, through `seat_mark`) and AI cost; each chart has «Vis som tabell». It reads again every 30 s, shows «Sist oppdatert», and a failed read keeps the figures with a Tilkoblingslinje line and «Prøv igjen».

**Decisions taken in place of the founder.** Name «Drift per Klasseøkt»; interval 30 s; window of 24 hour buckets ending with the current hour; error codes `game_check_failed`, the task name, `http_<status>`; one row per failed check (not per violation); 5xx includes the health check's 503; response times over `player_order` attempts of every outcome; the Games counted for fallback and guard are every Game of the session but a Lecturer's test Game; errors with no Class session are stored but not shown; rows kept forever (no purge). All copy `[ASSUMPTION] Story 15.8`.

**Personal data.** New table `error_events`: no `user_id`, no free text (code checked by a pattern); registry entry `none`, kept at retention.

**Files.**
- `backend/migrations/versions/0069_error_events.py`, `app/modules/ops/models.py`: the table.
- `backend/app/modules/ops/service.py`: `record_error` and the three source hooks.
- `backend/app/modules/ops/{operations,operations_routes,operations_schemas}.py`, `app/platform/authz.py`, `app/main.py`: the read, its routes, the policy, the 5xx hook.
- `backend/app/modules/games/{operations,service}.py`: `class_session_of`, `session_ai_figures`.
- `backend/app/ai/calls.py`: `session_figures`.
- `backend/app/modules/ops/sweep.py`, `app/platform/{jobs/__init__,logging}.py`, `app/worker.py`: the hooks.
- `backend/app/modules/identity/personal_data.py`: registry entry.
- `backend/tests/ops/test_error_events.py` (new), `tests/{test_imports,test_migrations,test_worker}.py`.
- `.docs/planning-artifacts/architecture/architecture-beergame-2026-11-12/ARCHITECTURE-SPINE.md`: Deferred entry settled.
- `frontend/src/modules/ops/{api,operations,operations.test,ops-charts,operations-page}.ts(x)`, `src/app/(app)/admin/drift/{page,[sessionId]/page}.tsx`, `src/modules/identity/{homes.ts,home-page.tsx}`, `src/copy/nb.ts`, `src/lib/api/*` (regenerated), `e2e/admin-operations.spec.ts` (new), `e2e/homes.spec.ts`.

**Review.** Two sonnet sub-agents (blind, edge case); 28 findings. Patched: 4 medium entries in 2 root causes (5xx placed by `session_id`/`game_id` too; hook timeouts) and low ones (same 24 h window in list and view, cancelled request not counted, chart comment). Deferred: none. Rejected: 20, each with its reason in the triage log.

**Follow-up review: not recommended.** Patched by verdict: high 0, medium 2 entries, low 3. The two medium entries are covered by the extended 5xx test and the full suite.

**Verification.**
- Backend full suite (`-n 8 --maxprocesses=8`, DB `olspillet_e15`): 3472 passed. ruff check and format clean.
- Frontend: typecheck ok, Vitest 1141 passed, `lint:colours` and `check:copy` passed, `next build` compiled.
- Playwright (`--workers=4`, stack on `olspillet_e15stack`): `admin-operations`, `admin-ai-models`, `homes`, `order-field`, `playout` passed with axe at 320 and 1440 px (one transient `ERR_NO_BUFFER_SPACE` on a homes test passed on rerun; `homes` needed the new Admin-område link). Screenshots at 360 and 1440 px checked: one column on phone, tables in a sideways scroll region, no horizontal page scroll.
- Matrix: every row is in `test_error_events.py` (violation in a Class game, a playout and a Replay; clean check; failed job; 5xx; store down; empty session; Lecturer 403; unknown 404).
- New tests over 1 s: the three tests that copy a played Classic game (`classic_game`, played once per run and shared) take 1–9 s in isolation, the first call in a worker paying the play; the rest are under 1 s.

**Residual risks.**
- The busy-hour figures on the page come from a route in e2e (the stack's mock model costs and fails nothing); the store-to-page path is joined only in the backend tests.
- Errors without a Class session (the sweep's own, mail jobs, routes with no session or Game id) are counted but not shown.

## Design Notes

`occurred_at` is the writer's clock, so hour buckets and the 24-hour window use one clock (Issue #63). Buckets are truncated in UTC: Oslo's offset is whole hours, so the frontend labels each start in Oslo time. The job hook is a worker middleware, not a wrapper per task, so new tasks are counted without edits; jobs are never retried (platform/jobs docstring), but the hook still checks the retry decision so "fails for good" stays true if a task gets retries later.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/ops/test_error_events.py tests/test_migrations.py tests/test_imports.py tests/identity/test_personal_data_registry.py -q` -- expected: pass
- `cd backend && uv run pytest -q -n 8 --maxprocesses=8` -- expected: pass
- `cd frontend && npm run typecheck && npx vitest run && npm run lint:colours && npm run check:copy && npm run build` -- expected: pass
- `cd frontend && npx playwright test admin-operations admin-ai-models homes play --workers=4` -- expected: pass
