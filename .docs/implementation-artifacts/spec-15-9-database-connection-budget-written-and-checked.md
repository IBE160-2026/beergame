---
title: 'Story 15.9: The database connection budget is written and checked'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: 'd025650cea3ea137137c13b7dd10b7c73999a3e9'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-15-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Story 3.14 wrote a connection budget (`docs/ops/connection-budget.md`), but nothing checks the running system against it: no process says what it holds, the Admin cannot see the sum, the pooler size is never compared, a `DATABASE_URL` on the transaction pooler (6543) would start, and no test shows a deploy overlap survives.

**Approach:** Put the written budget in code (`ops/connection_budget.py`, kept equal to the document by a test). Each process logs its configured connections at start and records them in a small table; «Drift» shows the latest report per process against the budget and the pooler check `ops.service.check_connection_budget()` (`DB_POOLER_SIZE` against twice the total plus the migration's one, unset = not checked). Production refuses port 6543. A script against Docker Compose scales a second set of processes while scripted Games are played through `python -m app.sim`.

## Boundaries & Constraints

**Always:**
- Budget in code = the document: `backend` SQLAlchemy 10 + procrastinate 0 + LISTEN 1 = 11; `worker-ai` and `worker-batch` 5 + `max(2, concurrency + 1)` = 2 + 0 = 7 each; total 25; overlap 50; pooler needed `2 × total + 1` = 51 (the `backend` pre-deploy migration's one connection, as Story 3.14 counted). Values are placeholders to tune under load (issue #28), stated so in code and document.
- `Settings.db_pooler_size: int | None` (env `DB_POOLER_SIZE`, empty = unset, ≥ 1). `ops.service.check_connection_budget(settings=None) -> BudgetCheck(status, pooler_size, required, budget_total)`: `not_checked` when unset (never `passed`), `failed` when `pooler_size < required`, else `passed`; pure, no database. The backend logs the result once at start.
- At start each process computes its configured connections (`backend`: `db_pool_size`, 0, 1; worker: `db_pool_size`, `jobs.procrastinate_pool_size(concurrency)`, 0; process name `worker-ai` when its queues include `ai-orders`, else `worker-batch`), logs `db_connections_configured` (process, the three parts, total, budget total of that process, `within_budget`) and records it through `ops.service.report_connections(...)` into new table `db_connection_reports` (migration `0070`, owned by ops: `id` uuid7, `process` CHECK in the three names, `sqlalchemy_pool`, `procrastinate_pool`, `listen` smallint ≥ 0, `reported_at` timestamptz writer's clock). Keeps the newest 10 rows per process. A failure to record is logged by type and never stops the process.
- `GET /api/admin/operations/connections` (policy `operations.read`): per process its budget parts and total, the latest report (parts, total, `reported_at`) or null, `over_budget`; `budget_total`, `overlap_total`, `configured_total` (sum of the latest reports) and `running` (`within`, `over`, `incomplete` when a process never reported); the pooler check (`status`, `pooler_size`, `required`).
- «Drift» list page (`/admin/drift`) gains a section «Databasetilkoblinger»: a table (Prosess, Budsjett, Konfigurert, Rapportert) with a sum row, a line on the running sum and a line on the pooler check with both numbers; read with the page every 30 s. Copy in `nb.ts`, `[ASSUMPTION] Story 15.9`.
- `production_problems()` lists `database_url` and `check_production` says why when the URL's port is 6543 (transaction pooler breaks LISTEN/NOTIFY and procrastinate), for api and workers alike (both load settings at start).
- `docker-compose.yml`: workers' `DB_POOL_SIZE` default 5 (`WORKER_DB_POOL_SIZE`), `PGAPPNAME` per service (`olspillet-backend`, `olspillet-worker-ai`, `olspillet-worker-batch`) so connections can be counted by process.
- `scripts/deploy-overlap` (stdlib Python, like `scripts/smoke`): with the stack up, scales `backend`, `worker-ai`, `worker-batch` to 2 (the new set beside the old), plays a batch of scripted Games with `python -m app.sim run` in a backend container (`PGAPPNAME=olspillet-sim`), sends parallel `/api/health` requests through the proxy, samples `pg_stat_activity` by `application_name`, then scales back to 1. Pass: sim exits 0, every request 200, peak connections of the three services ≤ the pooler need, no pool-timeout or "too many clients" line in the services' logs. Prints pass or fail per line; exit 0 only on pass.
- `docs/ops/connection-budget.md` revised in place: how it is checked (start log, «Drift», `check_connection_budget`, `DB_POOLER_SIZE`, 6543 refusal), operator commands outside the budget, the overlap check and its measured result, the ops values chosen by the independent review (below).

**Never:**
- No cloud account, no production service touched, no reading `.env`.
- No live measure of the pooler (it cannot be read over the session pooler); no personal data in the new table; no change to the pool sizes' meaning (`max_overflow=0`, 5 s timeout stay).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Pooler unset | `DB_POOLER_SIZE` empty | `not_checked`, required 51 | — |
| Pooler too small | 15 | `failed`, 15 and 51 reported | — |
| Pooler enough | 60 | `passed` | — |
| Transaction pooler | production URL `…:6543/…?sslmode=require` | process refuses to start, message names port 6543 | `ConfigError` |
| Start report | worker-ai, pool 5, concurrency 1 | log total 7 within budget; row recorded | record failure logged, start continues |
| Over budget | backend `DB_POOL_SIZE=20` | `within_budget` false in log; view `over` | — |
| No report yet | worker-batch never started | its configured null, `running` `incomplete` | — |
| Not Admin | Lecturer GET | 403 | — |

</intent-contract>

## Code Map

- `docs/ops/connection-budget.md` -- Story 3.14's budget; revise in place.
- `backend/app/platform/config.py:56` `db_pool_size`; `production_problems`/`check_production` -- add `db_pooler_size`, 6543 rule; `_unset_alert` pattern for empty env.
- `backend/app/platform/db.py:22` engine (`max_overflow=0`, `pool_timeout=5`) -- read only.
- `backend/app/platform/jobs/__init__.py:224` `max(2, concurrency + 1)` -- extract `procrastinate_pool_size(concurrency)`.
- `backend/app/platform/events/hub.py:128` the one LISTEN connection of `backend` -- read only.
- `backend/app/main.py:56` lifespan -- log and report; `app/worker.py:93` `_start` -- same for workers.
- `backend/app/modules/ops/{models,service,operations_routes,operations_schemas}.py` -- table, `report_connections`, `check_connection_budget`, route; new `ops/connection_budget.py` (budget constants, read).
- `backend/migrations/versions/0069_error_events.py` -- migration pattern; head 0069 → 0070.
- `backend/app/modules/identity/personal_data.py:117` -- registry entry `none`.
- `backend/tests/{test_migrations.py:118,150,284, conftest.py, test_imports.py}`, `tests/ops/test_error_events.py:228` (`admin`, `get`, `client`, `as_user`) -- table lists and test helpers.
- `backend/app/sim.py` `run` (batch JSON: `seed`, `games`, `seats` `scripted:<id>`, `settings`), `backend/batches/classic-scripted.json`, `scripts/smoke` -- driver and script pattern.
- `docker-compose.yml` workers `&worker-env` anchor; `railway/*/railway.toml` overlap seconds.
- `frontend/src/modules/ops/{api.ts,operations-page.tsx}` `ListContent`, `liveLines`, `TABLE`/`ROW` classes; `src/copy/nb.ts:2307`; `e2e/admin-operations.spec.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/app/platform/config.py`, `platform/jobs/__init__.py` -- setting, 6543 rule, pool size helper.
- `backend/migrations/versions/0070_db_connection_reports.py`, `app/modules/ops/models.py` -- table.
- `backend/app/modules/ops/connection_budget.py`, `ops/service.py` -- budget, configured, report, check, read.
- `backend/app/main.py`, `app/worker.py` -- start log and report.
- `backend/app/modules/ops/{operations_routes,operations_schemas}.py` -- route.
- `backend/app/modules/identity/personal_data.py`, `tests/{conftest,test_migrations,test_imports}.py` -- registry, lists, head `0070`.
- `backend/tests/ops/test_connection_budget.py` -- every matrix row, doc equals code, worker naming, log fields.
- `frontend/src/copy/nb.ts`, `src/modules/ops/{api.ts,operations-page.tsx,connections.tsx}`, `src/lib/api/*` (regenerated), `e2e/admin-operations.spec.ts` -- section and its check on the stack.
- `docker-compose.yml`, `scripts/deploy-overlap`, `backend/tests/test_deploy_overlap_script.py` -- overlap check (parse/verdict logic unit-tested; the script run once against the stack).
- `docs/ops/connection-budget.md` -- revised.

**Acceptance Criteria:**
- Given the revised document, when the test compares it with the code, then each process line, the total, the overlap and the pooler need match.
- Given the local stack, when the Admin opens «Drift», then «Databasetilkoblinger» shows 11, 7, 7 against the budget, sum 25 within, and the pooler line says not checked with the need 51.
- Given the stack, when `scripts/deploy-overlap` runs, then every line passes and its output is recorded in the document.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
- layers: Blind Hunter and Edge Case Hunter (sonnet); Verification Gap and Intent Alignment skipped, as the lead asked for two reviewers. The Edge Case Hunter also chose the ops values (in Auto Run Result and in `docs/ops/connection-budget.md`).
- verdicts: 34 findings — high 0, medium 4, low 26, false 4, maybe-false 0
- findings:
  - `[false]` `[reject]` Blind: "configured" is derived from settings, not measured — the story asks each process to log its configured connections; the pooler cannot be read over the session pooler, and `max_overflow=0` makes the setting the ceiling.
  - `[low]` `[patch]` Blind: one row per service undercounts replicas; stale reports show only a time — the document now says the budget assumes one replica per service (`numReplicas = 1`) and a second adds its line; the "time only" half is false (`formatTime` shows date and time).
  - `[low]` `[patch]` Blind: `running`, `status`, `process` are plain `str`, so an unknown state reads as "within" — the schemas are `Literal`, the client is regenerated, `runningText` is an exhaustive switch.
  - `[low]` `[reject]` Blind: a hand-copied `DB_POOLER_SIZE` can go stale and ignores Supavisor's client limit — the story defines the check as `DB_POOLER_SIZE` against twice the budget; confirming it in Supabase is a readiness item (Story 15.14).
  - `[false]` `[reject]` Blind: a failed or unset pooler check does not stop production — the story asks to report it (failed with both numbers, unset as not checked), not to refuse a start; Story 15.14's preflight prints it.
  - `[low]` `[patch]` Blind: `DB_POOLER_SIZE` missing from `.env.example` and SETUP-GUIDE; `WORKER_DB_POOL_SIZE` undocumented — added to `.env.example` and the SETUP-GUIDE variable table; the compose comment names the workers' variable.
  - `[low]` `[patch]` Blind: the 6543 check is a duplicated port heuristic, and `65x3` is blamed on the pooler — one `_ports` helper reads the host port and a libpq `port` query parameter; a test shows an unreadable port is refused without naming the pooler.
  - `[medium]` `[patch]` Blind: the overlap check compares the services' peak with 51 although no migration runs, counts the second set before it is up, and may miss bursts — the limit is now the overlap budget (50, `overlap_total()`) and `scale` waits (`--wait`); sampling every 0.5 s is kept (no pool can pass its size between samples, which is the bound checked); "health takes no connection" is false (`/api/health` runs `db.ping()`). Rerun: pass, peak 33 ≤ 50.
  - `[low]` `[patch]` Blind: the log pattern matches any `TimeoutError` — it now matches only `QueuePool limit`, `PoolTimeout`, "too many clients" and "remaining connection slots"; a test shows an AI provider timeout passes.
  - `[medium]` `[patch]` Blind: `scripts/deploy-overlap` is staged as mode 100644 — committed with mode 100755, like `scripts/smoke`.
  - `[low]` `[patch]` Blind: ordering by id while the index is on `reported_at`; a dead `PROCESSES` filter — the filter is removed; ordering by UUIDv7 id is the project's rule, both come from the writer's clock, and the table holds at most 30 rows.
  - `[low]` `[patch]` Blind: the document test checks only the pool and the total — it now checks each process line's pool, procrastinate pool, LISTEN cell and total.
  - `[low]` `[patch]` Blind: generic log keys (`total`, `budget`, `required`, `listen`) widen the AD-14 allowlist — the new keys are `db_total`, `db_budget`, `db_listen`, `pooler_required`; a test reads them through the real JSON logging.
  - `[low]` `[patch]` Blind: an unknown process raises `KeyError` although the docstring says never raises; the start has no timeout — an unknown process is logged and returns False (test); the timeout half is false (the 5 s pool and connect timeouts bound the insert).
  - `[false]` `[reject]` Blind: layering and a circular-import risk — no caller diverges; the full suite imports every path, and `ops.service` re-exports only what the story names (`check_connection_budget`) and the start hook.
  - `[false]` `[reject]` Blind: the diff holds a Story 11.8 log and migration 0070 collides with epic-11 — the log is the orchestrator's commit on the branch after the baseline; migration numbers are relinked at merge (lead's brief).
  - `[low]` `[patch]` Blind: frontend gaps — the Skeleton has 4 columns; a failed background read keeps the figures and says from when (`role="status"`); the column labels follow the spec («Konfigurert», «Rapportert»). Rejected parts: the `[ASSUMPTION]` marker is the project's copy convention; `DB_POOLER_SIZE` is the name the founder copies; e2e and helper tests cover the section.
  - `[low]` `[reject]` Edge: the pooler check passes while a process runs over its line — the story compares with twice the budget; «Drift» shows the over line beside it, so the Admin sees both.
  - `[low]` `[patch]` Edge: replicas and a rolled-back deploy's report — same as Blind 2, patched with it.
  - `[low]` `[reject]` Edge: a worker started before migration 0070 loses its report; smallint overflow — the loss is logged and «Drift» shows "Ikke rapportert" until the next start, never a false pass; it can happen only on the first deploy of 0070; a pool of 32 768 is not a real setting.
  - `[low]` `[patch]` Edge: `?port=6543` in the query passes the guard — patched with Blind 7 (test row added).
  - `[low]` `[reject]` Edge: a multi-host URL is refused — Supabase's pooler URL names one host; refusing an unreadable URL is the safe side.
  - `[low]` `[patch]` Edge: a failing `scale(1)` in `finally` hangs the sampler — the sampler is a daemon thread, `scale(1)` is caught and reported, and the sampler is joined with a timeout.
  - `[medium]` `[patch]` Edge: the second set is counted before it is up — same as Blind 8, patched with it.
  - `[low]` `[patch]` Edge: log window by host clock; unrelated timeouts fail the check — logs are read from 60 s before the start; the pattern is narrowed (Blind 9).
  - `[low]` `[patch]` Edge: an `HTTPException` kills a load thread uncounted — caught and counted as a failed request.
  - `[low]` `[patch]` Edge: compose calls have no timeout and inherit stdin — 900 s timeout, stdin from the null device when none is given.
  - `[medium]` `[patch]` Edge: the script is staged as an empty 100644 blob — same as Blind 10; committed with its content and mode 100755.
  - `[low]` `[patch]` Edge: an unknown state reads as "within" in the client — same as Blind 3.
  - `[low]` `[patch]` Edge: a failed background read of the budget is silent — same as Blind 17.
  - `[low]` `[reject]` Edge: an exported `DB_POOL_SIZE` no longer reaches the workers locally — intended: the workers' line is 5, set by `WORKER_DB_POOL_SIZE`, named in the compose comment.
  - `[low]` `[patch]` Edge: the document points at a margin that does not exist — «Values for the pilot» now holds the margin (10) and the chosen `DB_POOLER_SIZE` (105).
  - `[low]` `[reject]` Edge: the overlap check loads only `/api/health` and scripted Games defer no AI Orders — that is the story's stated method (scripted Games through `python -m app.sim`); the document now says the workers stayed near idle and that Story 15.10 runs the overlap with AI Orders.
  - `[low]` `[patch]` Edge: spec and code diverge on the column labels and the `procrastinate_pool` column — labels follow the spec; the column is `job_pool` because `alembic check` skips names starting `procrastinate_` (`migrations/env.py`), noted in the model.

## Design Notes

The pooler cannot be read over the session pooler, so the system checks what it can: each process's configured connections (reported, latest per process) against the written budget, and the founder-copied `DB_POOLER_SIZE` against the need. The budget is constants, not each process's setting, so a process set above its line shows as over rather than silently raising the budget.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/ops/test_connection_budget.py tests/test_migrations.py tests/test_imports.py tests/platform -q` -- expected: pass
- `cd backend && uv run pytest -q -n 8 --maxprocesses=8` -- expected: pass
- `cd frontend && npm run typecheck && npx vitest run && npm run lint:colours && npm run check:copy && npm run build` -- expected: pass
- `python scripts/deploy-overlap` (stack up) -- expected: every line pass, exit 0
- `cd frontend && npx playwright test admin-operations homes play --workers=4` -- expected: pass

## Auto Run Result

Status: done

**Summary.** The connection budget of Story 3.14 is revised in place (`docs/ops/connection-budget.md`) and checked. `ops/connection_budget.py` holds the same table (`BUDGET`: backend 10 + 0 + 1, workers 5 + 2 + 0; total 25, overlap 50, pooler need 51), kept equal to the document by a test. Each process logs `db_connections_configured` at start and records its counts in `db_connection_reports` (migration 0070, newest ten per process); a worker is `worker-ai` when it runs `ai-orders`, else `worker-batch`. `ops.service.check_connection_budget()` compares `DB_POOLER_SIZE` (new setting, empty = unset) with twice the budget plus the migration's connection: `failed` with both numbers, `not_checked` when unset, never passed; the backend logs it at start. «Drift» (`/admin/drift`) gains «Databasetilkoblinger» (`GET /api/admin/operations/connections`, Admin only): per process the budget, what its latest start configured and when, the sum and its state (within, over, incomplete), the pooler line and the need. In production every process refuses a `DATABASE_URL` on port 6543 (host part or `port` parameter), naming the reason. `docker-compose.yml` gives the workers pool 5 and each service a `PGAPPNAME`; `scripts/deploy-overlap` scales a second set beside the first while scripted Games are played through `python -m app.sim run` and health requests run through the proxy. It passed: peak 33 ≤ 50, 24 175 of 24 175 requests answered 200, sim exit 0, no pool errors.

**Ops values (chosen by the independent review in place of the founder; placeholders until Story 15.10, issue #28).** `DB_POOL_SIZE` 10 / 5 / 5 kept. Proposed for the load test: `worker-ai --concurrency 20`, `worker-batch --concurrency 4`, since concurrency 1 cannot meet NFR-2 for 250 Students. `DB_POOLER_SIZE` 105: (11 + 26 + 10) × 2 + 1 = 95, plus a margin of 10 for one operator command. Supabase compute Large (`max_connections` about 160, pooler up to about 80 % = 128; Medium at about 96 is too small); the figures are from the reviewer's memory and must be confirmed against Supabase's docs. Fallback: `worker-ai` concurrency 8, need 71 (81 with the margin), fits Medium. The code budget stays at concurrency 1, which is what the start commands run; raising it changes the start commands, `BUDGET` and the document together (Story 15.10).

**Other decisions taken in place of the founder.** Pooler need = twice the budget plus 1 for the pre-deploy migration (Story 3.14's 51, stricter than "twice the total"); the overlap check's limit is 50 since no migration runs in it; reports kept 10 per process; the section sits on the «Drift» list page; the running sum uses the latest start report per service (one replica each); a process over its line still starts; all copy `[ASSUMPTION] Story 15.9`.

**Personal data.** New table `db_connection_reports`: no `user_id`, no free text (a service name and counts); registry entry `none`.

**Files.**
- `backend/app/platform/config.py`: `DB_POOLER_SIZE`, the 6543 refusal; `platform/jobs/__init__.py`: `procrastinate_pool_size`; `platform/logging.py`: allowlisted count keys.
- `backend/migrations/versions/0070_db_connection_reports.py`, `app/modules/ops/models.py`, `migrations/env.py` (imports the ops tables for `alembic check`).
- `backend/app/modules/ops/{connection_budget,service,operations_routes,operations_schemas}.py`, `app/main.py`, `app/worker.py`: budget, start report, check, route.
- `backend/app/modules/identity/personal_data.py`: registry entry.
- `backend/tests/ops/test_connection_budget.py`, `tests/test_deploy_overlap_script.py` (new); `tests/{test_config,test_worker,test_migrations}.py`.
- `frontend/src/modules/ops/{connections.tsx,connection-budget.ts,connection-budget.test.ts,api.ts,operations-page.tsx}`, `src/copy/nb.ts`, `src/lib/api/*` (regenerated), `e2e/admin-operations.spec.ts`.
- `docker-compose.yml`, `.env.example`, `scripts/deploy-overlap` (new), `docs/ops/connection-budget.md`, the SETUP-GUIDE variable table.

**Review.** Two sonnet sub-agents (blind, edge case); 34 findings. Patched: 2 medium entries (overlap check limit and wait; script mode) and 15 low entries, as listed in the triage log. Deferred: none. Rejected: 12 (4 false, 8 low), each with its reason in the triage log.

**Follow-up review: not recommended.** Patched by entry verdict: high 0, medium 2, low 15. Both medium entries are verified: the overlap check was rerun with the new limit and `--wait` (pass), and the script's mode is checked at commit (`git ls-files -s`).

**Verification.**
- Backend full suite (`-n 8 --maxprocesses=8`, DB `olspillet_e15`): 3502 passed. ruff check and format clean.
- Frontend: typecheck ok, Vitest 1144 passed, `lint:colours` and `check:copy` passed, `next build` compiled.
- Playwright (`--workers=4`, stack on `olspillet_e15stack`): `admin-operations`, `homes`, `order-field`, `playout` 38 passed, axe at 320, 360 and 1440 px. Screenshots at 360 and 1440 px checked: one table, no horizontal page scroll.
- `scripts/deploy-overlap` against the stack: every line pass (recorded in the document).
- Matrix: pooler unset, 15 and 51 (`test_the_pooler_check_compares…`); 6543 and `port=6543` (`test_config.py`); start report and log (`test_a_start_logs…`, worker naming in `test_worker.py`); over budget and no report (`test_drift_…`); Lecturer 403.
- New tests over 1 s: none.

**Residual risks.**
- The overlap check ran with scripted Games, so the workers' job pools stayed near idle; AI Orders at the pilot's concurrency are Story 15.10's run.
- `DB_POOLER_SIZE` is hand-copied; a later change in Supabase is not seen until it is copied again.
- During the build, the shared test databases `olspillet_e15_test_gw1`–`gw3` had the first draft of 0070's column renamed in place (`procrastinate_pool` to `job_pool`); no database was dropped.
