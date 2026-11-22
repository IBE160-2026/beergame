# Connection budget

Story 3.14 wrote this budget; Story 15.9 checks the running system against it (NFR-3, NFR-4, AD-24, SETUP-GUIDE §5). Every process connects to Supabase Postgres through the **session pooler on port 5432**, never the transaction pooler on 6543, which breaks LISTEN/NOTIFY and procrastinate: in production every process refuses to start when `DATABASE_URL` names port 6543. In session mode each open client connection holds one pooler slot for as long as it is open, so the pooler's pool size must cover every connection the services can hold at once, including a deploy overlap. Revise this file in place when a number below changes, together with `BUDGET` in `backend/app/modules/ops/connection_budget.py`; a test (`backend/tests/ops/test_connection_budget.py`) fails when the two differ.

The pool sizes are **placeholders, to be tuned under load (issue #28)**: the load test of Story 15.10 measures them and revises this file.

## What each process holds

| Process | SQLAlchemy pool | procrastinate pool | LISTEN | Total |
| --- | --- | --- | --- | --- |
| `backend` | `DB_POOL_SIZE` = 10, `max_overflow=0` | 0: jobs are deferred on the request's own connection | 1, reserved for the SSE listener (AD-8) | **11** |
| `worker-ai` | `DB_POOL_SIZE` = 5, `max_overflow=0` | `max(2, concurrency + 1)` = 2 (the worker's jobs and its LISTEN for new jobs) | inside the procrastinate pool | **7** |
| `worker-batch` | `DB_POOL_SIZE` = 5, `max_overflow=0` | `max(2, concurrency + 1)` = 2 | inside the procrastinate pool | **7** |
| `backend` pre-deploy `alembic upgrade head` | one connection (NullPool), only while it runs | — | — | **1** |

- `DB_POOL_SIZE` is set per Railway service; it is the SQLAlchemy pool of that process (`backend/app/platform/db.py`, no overflow, a 5-second pool timeout, so a full pool refuses rather than opening more).
- The procrastinate pool is `max(2, concurrency + 1)` (`procrastinate_pool_size` in `backend/app/platform/jobs/__init__.py`). The workers run with the default `--concurrency 1`. Raising it raises this pool one for one, so raise the budget first.
- `proxy` and `frontend` never connect to the database.
- One replica per service (`numReplicas = 1` in `railway/<service>/railway.toml`). A second replica adds its whole line again; «Drift» shows the latest start of each service, not one line per replica, so raise the budget before adding one.
- Operator commands (`python -m app.sim`, `python -m app.ai.cli`, a manual `alembic`) open a pool of their own (`DB_POOL_SIZE`, at most 10) while they run. They are outside this budget: run them outside Lab hours, or count them against the margin in "Values for the pilot" below.

## Total

| | Connections |
| --- | --- |
| One deploy of each service running | 11 + 7 + 7 = **25** |
| During a deploy overlap, old and new side by side (`overlapSeconds` in `railway/<service>/railway.toml`) | 25 × 2 = **50** |
| Plus the migration of the new `backend` | **51** |

**Pooler pool size needed: at least 51.** Supabase's default pool size on the small plans is 15, so it must be raised in Supabase (Database → Settings → Connection pooling → Pool size), and the compute size must allow it: the pool size plus Supabase's own reserved connections must stay below the database's `max_connections` for that compute size. If the compute size cannot allow 51, lower the numbers instead, for example `DB_POOL_SIZE` 6 for `backend` and 3 for each worker: (7 + 5 + 5) × 2 + 1 = **35**.

## The formula

```
per deploy  = (backend DB_POOL_SIZE + 1)
            + Σ over workers (DB_POOL_SIZE + max(2, concurrency + 1))
pool size  >= 2 × per deploy + 1
```

Story 3.15 sets the pooler's pool size to fit this and records the chosen compute size in its runbook.

## How it is checked (Story 15.9)

- **At start.** Each process logs `db_connections_configured` with its SQLAlchemy pool, procrastinate pool, LISTEN connection, total, its budget line and `within_budget`, and records the same numbers in `db_connection_reports` (the newest ten per process are kept). A process set above its line still starts; it shows as over.
- **«Drift» (`/admin/drift`).** The Admin sees «Databasetilkoblinger»: per process its budget and what its latest start reported, the sum against the budget (25) and a deploy overlap (50), and the pooler check.
- **The pooler check.** The pooler's pool size cannot be read over the session pooler, so the founder copies it into `DB_POOLER_SIZE` (Supabase → Database → Connection pooling). `ops.service.check_connection_budget()` compares it with twice the budget total plus the migration's connection (51) and reports `failed` with both numbers when the pool is too small. Unset, it reports **not checked**, never passed. The `backend` logs the result at start (`db_pooler_check`); the pre-pilot preflight of Story 15.14 prints it.
- **Transaction pooler.** With `APP_ENV=production`, a `DATABASE_URL` on port 6543 stops `backend`, `worker-ai` and `worker-batch` at start, naming the port and the reason.

## Values for the pilot

Chosen on 2026-11-22 by an independent review in place of the founder (no human in the loop), for NFR-3 (250 Students at once). **All are placeholders until the load test of Story 15.10 (issue #28) measures them.** The Supabase figures are from the reviewer's memory and must be confirmed against Supabase's current documentation before they are used.

| Setting | Value | Reason |
| --- | --- | --- |
| `DB_POOL_SIZE` `backend` | 10 (kept) | A request holds a pooled connection for milliseconds and the event streams share the one LISTEN connection; 10 absorbs a burst when a Week opens. |
| `DB_POOL_SIZE` `worker-ai`, `worker-batch` | 5, 5 (kept) | A job holds its connection for its short reads and writes, not during the model call. No evidence yet to move them. |
| `--concurrency` `worker-ai` | 20 (proposed for the load test) | At 1, one AI Order at a time (about 4 s each) cannot meet NFR-2 for 250 Students; about 5 Orders a second at about 4 s is about 20 in flight. |
| `--concurrency` `worker-batch` | 4 (proposed for the load test) | Room for reports, play-outs, mail and the sweep without pushing the pooler need up. |
| `DB_POOLER_SIZE` (Supabase pool size) | 105 | The need at those concurrencies, (11 + 26 + 10) × 2 + 1 = 95, plus a margin of 10 for one operator command at a time. It also covers today's need of 51. |
| Supabase compute | Large (`max_connections` about 160) | The pooler may use about 80 % of `max_connections` with the Data API off (128 ≥ 105); Medium (about 120, so about 96) is too small. |

The workers run `--concurrency 1` today, and `BUDGET` and the table above count that. Raising the concurrency is a change of the budget: change the start commands (`railway/worker-*/railway.toml`, `docker-compose.yml`), `BUDGET` and this file together (the test holds the last two equal), and run `scripts/deploy-overlap` again. Story 15.10 makes that change if the load test confirms it. A cheaper fallback is `worker-ai` at concurrency 8: need (11 + 14 + 10) × 2 + 1 = 71, with the margin 81, which fits Medium.

## Deploy overlap check

`scripts/deploy-overlap` runs against Docker Compose (the local stack, every service up). It starts a second set of processes beside the first (`docker compose up --scale backend=2 --scale worker-ai=2 --scale worker-batch=2`), plays a batch of scripted Games through `python -m app.sim run` in a `backend` container while it sends parallel `GET /api/health` requests through the proxy, samples `pg_stat_activity` by `application_name` (each service sets `PGAPPNAME`), then stops the second set. It passes when the simulation exits 0, every request answers 200, the peak connections of the services stay within the overlap budget (50; no migration runs during the check) and no service logs a pool timeout or "too many clients".

Locally there is no pooler: Postgres' own `max_connections` (100) is the limit, so the check shows that the processes keep within the budget during an overlap, not what Supabase does with it.

Result, 2026-11-22, Story 15.9, on the local stack (`DB_POOL_SIZE` 10, 5, 5; `--concurrency 1`; 6 scripted Games, 16 parallel requests). Scripted Games defer no AI Orders, so the workers' pools stayed near idle; the load test of Story 15.10 runs the overlap again with AI Orders and the pilot's concurrency:

```
pass second set started: backend 2, worker-ai 2, worker-batch 2
pass simulation exited 0
pass requests answered 200: 24175 of 24175
pass peak connections 33 <= 50 (backend 18, worker-ai 7, worker-batch 8; sim 1 outside the budget; 72 samples)
pass pool timeouts or refused connections in the logs: 0
deploy overlap ok
```
