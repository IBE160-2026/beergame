---
title: 'Story 2.5: Place LLM Orders as jobs, with the Rule-based Order as fallback'
type: 'feature'
created: '2026-11-18'
baseline_revision: '6d5b57e1f0da5b7e293352479c5e75e740ba3131'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-2-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      An ai-orders job that fails on a database or lock error inside place_order is not retried, so that Seat's Order waits.
    evidence: |-
      procrastinate runs the task without retries; the job now places a fallback for every gateway or refusal failure, but a transient DB error while writing the Order still fails the job. Story 2.6's worker-ai rescue loop and the later sweeper are the planned repair.
    location: >-
      backend/app/modules/players/jobs.py place_llm_order
    severity: medium
---

<intent-contract>

## Intent

**Problem:** An `llm` Seat gets no Order: `ensure_order` returns None for it, there is no job platform, no worker process, no way to give a Game a model config, and the Decision log cannot hold `llm_call` ids or a fallback reason (FR-31, FR-32, FR-67, FR-78, NFR-4, AD-4, AD-5, AD-9, AD-15, AD-22, AD-24).

**Approach:** Add `app/platform/jobs` (procrastinate 3.11.0, schema through Alembic), `python -m app.worker --queues …` and the `worker-ai`/`worker-batch` compose services; freeze a model config and Effort level into `SessionRuntime`; let `ensure_order` defer one `ai-orders` job per `(game, week, seat)` inside the command's transaction; the job calls `gateway.run` once and places the LLM Order or the stored Rule-based reference Order with the failure type.

## Boundaries & Constraints

**Always:**
- `platform/jobs`: one procrastinate `App` with a `PsycopgConnector` whose pool is opened only by a worker; queue names `ai-orders`, `llm-batch`; `defer(session, task, queue, queueing_lock, **ids)` defers on the raw psycopg connection of the SQLAlchemy session inside a savepoint, so a duplicate `todo` job (same queueing lock) is skipped without aborting the transaction. Job args are ids and ints only. Tasks are never retried by procrastinate.
- Alembic `0008`: runs `procrastinate.schema.SchemaManager.get_schema()` (the SQL procrastinate ships); adds `seat_weeks.llm_call_ids UUID[] NOT NULL DEFAULT '{}'`; widens `ck_seat_weeks_fallback` to `none, timeout, invalid_output, budget_exhausted, provider_error`. Downgrade removes all `procrastinate_*` objects and both changes. `env.py` ignores `procrastinate_*` objects in `alembic check`.
- `python -m app.worker --queues ai-orders` (comma list or repeated) opens a pool from `DATABASE_URL`, imports the task modules and runs a procrastinate worker on those queues; no key needed. `run_until_idle(queues)` (same code, `wait=False`) drives jobs in tests and in `app.sim`.
- `docker-compose.yml`: `worker-ai` and `worker-batch` from `./backend` (same image), `RUN_MIGRATIONS=false`, after `backend` is healthy; no new queue beyond these two, no sweeper.
- `SessionRuntime` gains `model_config_id: str | None`, `effort_level: str | None` (both or neither; `ai_mode = "llm"` when set). `games.commands.create(..., model_config_id=None, effort_level=None)`: unknown config → `config_not_found` 422; level not on the config → `effort_level_unknown` 422; no level → the config's first level; marks the config referenced (`ai.config.mark_referenced`) in the create transaction.
- `games.commands.assign_seat` accepts `llm`; a Game whose runtime has no model config → `model_config_required` 422.
- `games.service.budget_scope(game_id) -> ai.budget.BudgetScope`: simulation Game → `BudgetScope.evaluation(config, effort_level=level)`; no model config → None. `games` may import `app.ai.config` and `app.ai.budget` only (never the gateway or pydantic-ai).
- `games.service.llm_turn(game_id, seat_id, week) -> PendingTurn | None`: the Seat's turn when that Week is the open Week of a running Game, read in its own session.
- `place_order(..., fallback=Fallback.NONE, llm_call_ids=())`: stores both on the row; `fallback != none` needs `decided_by = rule_based`, an `llm` occupant and the turn's reference Order; `decided_by = llm` needs an `llm` occupant; violations → 422 `fallback_invalid` / `decided_by_invalid`. `DecisionLogRow` gains `llm_call_ids`.
- `players.ensure_order`: Guided Week → Guided Order for `llm` too (no call); otherwise `llm` → defer `players.place_llm_order(game_id, seat_id, week)` on `ai-orders`, queueing lock `ai-orders:<game>:<week>:<seat>`.
- `players/jobs.py` task: reads `llm_turn`; returns without a call when there is no such turn, it has ordered, its occupant is not `llm`, or the Week is Guided. Otherwise calls `gateway.run("player_order", budget_scope, llm.request_inputs(...), llm.order_schema(min, max), deadline=None)` exactly once. `Result` → `place_order(decided_by=llm, llm_call_ids)`; `Failure` → reference Order, `decided_by=rule_based`, `fallback=<kind>`, the failure's ids; a `GatewayError` (config/caller mistake) → the same fallback with `provider_error` and no ids, logged with its code. `CommandError` `order_exists`, `week_not_open`, `game_finished` → logged, job ends without error. Occupancy is never changed.
- `app.sim`: Seat spec `llm`; `create --config ID [--effort-level L]`; batch file `model_config`, `effort_level`; `_wait_finished` runs `run_until_idle(["ai-orders"])` before `advance`. Golden batch output unchanged.
- `app.ai.mock.outage()`: while active every mock attempt fails as a provider error.
- Import rules: only `players/llm.py` and `players/jobs.py` may import `app.ai.gateway`; only `players/jobs.py` may import `players.llm`; `players/service.py` never imports either or `procrastinate`.

**Never:** No deadline / rescue loop (2.6), no rate limit or real endpoint (2.7), no reservation or cost-limit switch (2.8), no Play guard or near-optimal reference (2.9/2.10), no sweeper or other queues, no changed golden output, no sleeping on wall-clock in tests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Guided Week | 4 `llm` Seats, Week ≤ guided | `decided_by=guided`, 0 `llm_call` rows, no job | — |
| Defer | open non-Guided Week, `llm` Seat | one `ai-orders` job, args `{game_id, seat_id, week}`, committed with the Week | rollback → no job |
| Valid answer | mock answers reference | `decided_by=llm`, `fallback=none`, ids of every attempt | — |
| Retries then valid | `script(INVALID, INVALID)` | 3 ids on row, one `run` | — |
| Typed failure | `outage()` | reference Order, `decided_by=rule_based`, `fallback=provider_error`, 6 ids; occupancy `llm` | — |
| Duplicate delivery | job run twice | 1 `seat_week` row, 2nd makes no call | — |
| Race | Order placed between read and place | `order_exists` caught, job ok | — |
| Provider down | `sim run` 4 `llm` Seats, `outage()` | finished, every non-Guided row `fallback=provider_error`, check ok | — |
| No config | `assign_seat(llm)` | — | `model_config_required` 422 |
| Bad level | `create(config, "turbo")` | — | `effort_level_unknown` 422 |

</intent-contract>

## Code Map

- `backend/app/modules/players/service.py:21` -- `_order` returns None for `llm`; `ensure_order` gets `OpenGame` (has `.session`).
- `backend/app/modules/players/llm.py:182,200` -- `order_schema`, `request_inputs` (reuse).
- `backend/app/ai/gateway.py:415` -- `run`, `Result`, `Failure`, `GatewayError`; `app/ai/mock.py` -- `script`, steps, add `outage`.
- `backend/app/ai/budget.py:30` -- `BudgetScope.evaluation`; `app/ai/config.py:322,364` -- `get`, `mark_referenced`, `ModelConfig.effort_level`.
- `backend/app/modules/games/commands.py` -- `create` (runtime), `_occupant`/`ASSIGNABLE`, `assign_seat`, `_place` (insert_seat_week), `place_order`.
- `backend/app/modules/games/schemas.py` -- `Fallback`, `SessionRuntime`, `DecisionLogRow`; `models.py` -- `seat_weeks`; `views.py:134` -- `decision_log`; `turns.py` -- `pending_turn`, `OpenGame`; `service.py` -- exports.
- `backend/migrations/versions/0007_llm_call.py` -- revision style; `migrations/env.py` -- add `include_name`.
- `backend/.venv/Lib/site-packages/procrastinate` -- `App.configure_task(name, connection=…)`, `PsycopgConnector`, `schema.SchemaManager.get_schema`, `run_worker_async(wait=False)`.
- `backend/app/worker.py` -- stub to replace; `docker-compose.yml` -- add services.
- `backend/app/sim.py:377,412,492,800-893` -- seat spec, create, `_wait_finished`, batch.
- `backend/tests/conftest.py:92` -- `games_db` truncation (add `procrastinate_jobs`); `tests/test_migrations.py` -- head tables / version; `tests/test_imports.py` -- rules; `tests/players/test_ensure_order.py` -- `created`, `SHORT`, `log` helpers.

## Tasks & Acceptance

**Execution:**
- `backend/pyproject.toml`, `uv.lock` -- add `procrastinate==3.11.0`.
- `backend/app/platform/jobs/__init__.py` (new) -- App, queues, `defer`, `run_until_idle`, `open_pool`.
- `backend/migrations/versions/0008_jobs_llm_orders.py` (new), `migrations/env.py` -- schema changes above.
- `backend/app/modules/games/{schemas,models,commands,service,views,turns}.py` -- runtime, fallback, ids, `budget_scope`, `llm_turn`, assign `llm`.
- `backend/app/modules/players/service.py`, `players/jobs.py` (new) -- defer and job.
- `backend/app/ai/mock.py` -- `outage`.
- `backend/app/worker.py`, `docker-compose.yml` -- worker processes.
- `backend/app/sim.py` -- `llm` Seats, config options, in-process worker.
- Tests: `tests/players/test_llm_jobs.py` (new: matrix rows), `tests/games/test_create.py`/`test_assign_seat.py` (config, level, `model_config_required`), `tests/test_worker.py` (new: arg parsing, `run_until_idle`), update `test_migrations.py`, `test_imports.py`, `conftest.py`, `test_sim.py` (llm batch).

**Acceptance Criteria:**
- Given `docker compose up`, then `worker-ai` and `worker-batch` run and stay up with no keys (checked once by hand, result recorded).
- Given CI commands locally, then ruff is clean, the full suite passes, engine coverage stays 100 %, golden outputs unchanged, and any new test over 1 s is reported.

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 38 findings — high 0, medium 7, low 19, false 9, maybe-false 3
- findings:
  - `[low]` `[patch]` (intent 1) compose workers are separate builds, compose untested — `backend` now tags `olspillet-backend:local` and both workers run that image; compose checked by hand twice (workers start with no keys; `worker-ai` played a 36-Week mock LLM Game, `check ok`).
  - `[low]` `[reject]` (intent 2) commit-with-the-Week tested on `jobs.defer` alone — the Week-opening path defers through the same function on the command's session; the start test reads the jobs committed with the Week.
  - `[false]` `[reject]` (intent 3) queueing lock blocks only `todo` jobs — one Order per key is enforced by `place_order` (`order_exists`) and the turn check.
  - `[false]` `[reject]` (intent 4) duplicate normally never sees 409 — both paths tested; the pre-check saves a paid call, the race test hits the literal 409.
  - `[medium]` `[patch]` (intent 5) only `provider_error` fallbacks exercised — same root as gap 1.
  - `[false]` `[reject]` (intent 6) "never retries itself" unasserted — the task uses procrastinate's default `retry=False`; the gateway's 6 attempts are asserted (6 ids).
  - `[false]` `[reject]` (intent 7) config accepted for non-simulation purposes — only the simulation purpose has a policy; `create` refuses others (`purpose_not_supported`).
  - `[false]` `[reject]` (intent 8) CHECK widening is not expand-only — widening the allowed set invalidates no row.
  - `[false]` `[reject]` (intent 9) sim runs jobs in-process — same job, gateway and fallback code; `worker-ai` ran a Game by hand.
  - `[low]` `[reject]` (intent 10) sim flags and `place_order` checks beyond the AC — needed for the NFR-4 Game and to keep `decided_by`/`fallback` honest; tested.
  - `[medium]` `[patch]` (gap 1) failure-type mapping tested only for `provider_error` — new `test_each_failure_type_is_the_fallback_mark` (`invalid_output` 6 ids, `budget_exhausted` 0 ids).
  - `[low]` `[patch]` (gap 2) early-exit guards untested — new test: finished Game, Guided Week, Rule-based Seat, foreign Seat, Week not open; no call.
  - `[low]` `[patch]` (gap 3) `worker.main` happy path untested — new test checks queues and concurrency handed to `run_worker`.
  - `[medium]` `[patch]` (gap other) other exceptions stall the Game — `_decide` turns any exception into the `provider_error` fallback; a refused LLM Order is replaced by the reference Order marked `invalid_output`; test with a broken gateway.
  - `[medium]` `[patch]` (blind 1) non-ENDED refusal stalls the Game — fixed as gap other.
  - `[medium]` `[patch]` (blind 2) only `GatewayError` caught — fixed as gap other.
  - `[low]` `[reject]` (blind 3) config mistakes stored as `provider_error` — the story fixes four failure types; the log line carries the gateway code.
  - `[false]` `[reject]` (blind 4) config accepted for any purpose — see intent 7.
  - `[low]` `[patch]` (blind 5) no integrity on call ids — an LLM Order without ids is refused; an FK on an array is not possible and the job is the only caller (rest rejected).
  - `[low]` `[reject]` (blind 6) finished-game check ignores marks — the check replays books; marks are guarded at write time.
  - `[low]` `[reject]` (blind 7) downgrade fails with fallback rows — the Decision log is append-only; a comment in `downgrade` states it; dev-only.
  - `[medium]` `[patch]` (blind 8) 0008 depends on installed procrastinate — schema kept as `migrations/sql/procrastinate-3.11.0-schema.sql`; a test fails on drift.
  - `[low]` `[reject]` (blind 9) racing job pays for a call — needs two deliveries in flight; claiming the turn needs new state.
  - `[low]` `[patch]` (blind 10) deferral logged when refused — logs only when `defer` returns True.
  - `[low]` `[patch]` (blind 11) no restart policy — `restart: unless-stopped`; concurrency left at 1 until Story 2.7's rate limit.
  - `[low]` `[patch]` (blind 12) sim works off every Game's jobs — documented in `_work_off_llm_orders`.
  - `[low]` `[reject]` (blind 13) fallbacks hidden in sim output — Epic 1 golden output must stay identical; Story 2.11 adds LLM reporting.
  - `[low]` `[patch]` (blind 14) untested paths, `--queues ","` message — covered by the guard test; message now `no queue given`; empty `llm-batch` and `TASK_MODULES` by design.
  - `[maybe-false]` `[reject]` (edge 1) non-Gateway exception stalls — patched under blind 2.
  - `[maybe-false]` `[defer]` (edge 2) transient DB error in `place_order` — deferred: retries belong to Story 2.6's rescue loop.
  - `[low]` `[patch]` (edge 3) unmarked Rule-based Order on an LLM Seat — refused (`fallback_invalid`).
  - `[low]` `[patch]` (edge 4) LLM Order without call ids — refused (`llm_call_ids_invalid`).
  - `[low]` `[reject]` (edge 5) unknown or foreign ids — see blind 5.
  - `[low]` `[reject]` (edge 6) `ai_mode` llm without an LLM Seat — the runtime records the frozen config, as asked.
  - `[low]` `[reject]` (edge 7) downgrade with fallback rows — see blind 7.
  - `[low]` `[patch]` (edge 8) empty queue list runs every queue — `run_worker` refuses it.
  - `[low]` `[patch]` (edge 9) nested `outage()` resets early — restores the previous state.
  - `[maybe-false]` `[reject]` (edge 10) `open_pool` named in the spec but absent — the fix is a spec edit; `run_worker` opens its own pool.

## Design Notes

Deferring on the session's own psycopg connection (`(await session.connection()).get_raw_connection().driver_connection`) makes the job row part of the command's transaction: a rolled-back Week leaves no job, and the worker cannot see the job before the Week's rows. The savepoint keeps a `queueing_lock` conflict from poisoning the command. The job reads the turn first so a duplicate delivery costs no model call; the `order_exists` catch covers the remaining race. `deadline=None` until Story 2.6 adds the per-Order time budget.

## Verification

**Commands:**
- `cd backend && uv run ruff check . && uv run ruff format --check .` -- expected: clean
- `cd backend && uv run pytest tests/players tests/games tests/test_migrations.py tests/test_imports.py tests/test_worker.py -q` -- expected: pass
- `cd backend && uv run pytest --cov=app/engine --cov=tests/engine --cov-fail-under=100` -- expected: pass, once before commit

## Auto Run Result

Status: done

**Summary:** LLM players now get their Orders from background jobs. `app/platform/jobs` wraps procrastinate 3.11.0. Alembic 0008 installs its schema from the shipped SQL, kept in `migrations/sql`. `defer` puts the job on the caller's own connection inside a savepoint, so the job commits with the Week, and a duplicate key is skipped without breaking the transaction. `python -m app.worker --queues …` runs a worker. `run_until_idle` drives the jobs in tests and in `app.sim`. Compose gains `worker-ai` and `worker-batch`, which run the backend image and need no keys.

`games.commands.create` freezes a model config and an Effort level into `SessionRuntime`, by default the config's first level, and marks the config referenced. `assign_seat` takes `llm`, or refuses with `model_config_required`. `games.service.budget_scope` returns the evaluation budget with that level, and `llm_turn` reads a job's turn.

`ensure_order` places the Guided Order in Guided Weeks and makes no call. In other Weeks it defers `players.place_llm_order`, keyed `ai-orders:<game>:<week>:<seat>`. The job calls `gateway.run` once:
- A valid answer becomes an LLM Order with its call ids.
- On any failure the job places the reference Order as `rule_based`, with the failure type and the failed ids. A failure is a typed gateway failure, a call the gateway cannot prepare, or an unexpected error.
- `order_exists`, `week_not_open` and `game_finished` end the job cleanly.

`place_order` stores `fallback` and `llm_call_ids`, a new `seat_weeks` column, and refuses marks that do not fit the Seat. `app.sim` accepts `llm` Seats, through `--config` and `--effort-level` or the batch fields `model_config` and `effort_level`. `mock.outage()` makes the mock provider fail every attempt.

**Files:**
- `backend/app/platform/jobs/__init__.py` (new): the job platform.
- `backend/app/worker.py`: the worker CLI.
- `docker-compose.yml`: the workers and the shared `olspillet-backend:local` image.
- `backend/migrations/versions/0008_jobs_llm_orders.py` (new), `migrations/sql/procrastinate-3.11.0-schema.sql` (new) and `migrations/env.py`: the job schema, `llm_call_ids`, the fallback CHECK, and procrastinate tables left out of `alembic check`.
- `backend/app/modules/games/{schemas,models,commands,service,turns,views}.py`: the runtime config, fallback types, call ids, `budget_scope`, `llm_turn` and the `llm` occupant.
- `backend/app/modules/players/service.py`: deferring the job.
- `backend/app/modules/players/jobs.py` (new): the job.
- `backend/app/ai/mock.py`: `outage()`.
- `backend/app/sim.py`: `llm` Seats.
- `backend/pyproject.toml` and `uv.lock`: `procrastinate==3.11.0`.
- `README.md`: the workers.
- Tests:
  - New: `tests/players/test_llm_jobs.py`, `tests/test_sim_llm.py`, `tests/test_worker.py`.
  - Updated: `test_migrations.py`, `test_imports.py`, `conftest.py`, `ai/helpers.py`, `games/test_create.py`, `games/test_assign_seat.py`, `test_sim.py`.

**Review:** one pass, 4 layers, 38 findings (medium 7, low 19, false 9, maybe-false 3).
- Patched:
  - The job never stalls on an unexpected error or on a refused LLM Order.
  - Every failure type has a test.
  - The procrastinate schema is vendored, with a test that fails on drift.
  - New guards in `place_order`.
  - Tests for the job's early exits and for `worker.main`.
  - Smaller fixes: `outage` nesting, the deferral log, refusing a worker with no queue, the shared compose image with a restart policy, and the sim docstring.
- Deferred: a transient DB error while writing the Order (Story 2.6's rescue loop).
- Rejected, with reasons in the triage log:
  - Config mistakes stored as `provider_error`.
  - Foreign keys for call ids.
  - Extending the finished-game check.
  - A downgrade with data.
  - A racing job's paid call.
  - The sim output, which must stay golden.
  - `open_pool`, which only the spec claimed.

**Follow-up review recommended:** true. Patched at medium: 4 root causes (job stall, failure-type tests, schema drift, `place_order` guards). Unverified risks:
- The `llm_order_refused` path is untested. In that path `place_order` refuses an LLM Order, and the job places an `invalid_output` fallback. The Order schema keeps it unreachable in normal runs.
- A DB error while writing the Order still fails the job.

**Verification:**
- `ruff check` and `ruff format --check`: clean.
- Full suite with engine coverage: 1307 passed in 55 s, engine coverage 100 %, golden batch outputs unchanged.
- Docker: `docker compose up -d --build backend worker-ai worker-batch` started both workers on `olspillet-backend:local` with no keys. `worker-ai` played a 36-Week Game with four `llm` Seats on the mock against the dev database, and the check passed. The services were then stopped and removed.
- Matrix audit: every row has a passing test in `tests/players/test_llm_jobs.py`, `tests/test_sim_llm.py`, `tests/games/test_create.py` or `tests/games/test_assign_seat.py`.
- New tests over 1 s. Each includes a one-time pydantic-ai import of about 1 s per process:
  - `test_valid_answers_are_placed_as_llm_orders_with_their_call_ids`: 1.8 s.
  - `test_a_job_whose_turn_no_longer_waits_asks_no_model`: 1.25 s.
  - The two tests in `test_sim_llm.py`: 2.2 to 2.6 s each.
  - `test_worker.py::test_the_worker_knows_the_llm_order_task_by_its_name`: 1.0 s.

**Decisions taken in place of the founder:**
1. Player calls run with `deadline=None` until Story 2.6. The job checks the turn first and makes no call when the Seat has ordered, the Week is Guided, the occupant is not `llm`, or the Week is not open.
2. Fallback marks:
   - A call the gateway cannot prepare, an unexpected error, or a missing scope: `provider_error`, with no call ids.
   - An LLM Order that `place_order` refuses: the reference Order, marked `invalid_output`.
3. Imports: `games` may import `app.ai.config` and `app.ai.budget`, never the gateway. Only `players/llm.py` and `players/jobs.py` may import the gateway.
4. `create` without an Effort level freezes the config's first level. It always marks the config referenced, and sets `ai_mode = llm` whenever a config is set.
5. `place_order` refuses:
   - `decided_by = llm` without call ids, or from a Seat that is not `llm`;
   - an unmarked Rule-based Order from an `llm` Seat;
   - a fallback that is not the reference Order;
   - call ids on any other Order.
6. Jobs:
   - The worker deletes successful jobs.
   - Job key: `ai-orders:<game>:<week>:<seat>`.
   - Arguments: `{game_id, seat_id, week}`.
   - Worker concurrency defaults to 1.
7. The sim works off `ai-orders` in its own process for Games with `llm` Seats. A batch with `llm` Seats needs `model_config`.
8. Compose: the workers run the image `backend` builds, with `RUN_MIGRATIONS=false` and `restart: unless-stopped`.

**Residual risks:**
- CI has not run, because nothing was pushed.
- New migration 0008 was applied to the shared test databases (`olspillet_test*`) and to the dev database.
- The dev database holds one mock model config and one finished LLM Game from the hand check.
