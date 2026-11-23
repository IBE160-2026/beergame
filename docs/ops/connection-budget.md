# Connection budget

Story 3.14 (NFR-7, SETUP-GUIDE §5). Every process connects to Supabase Postgres through the **session pooler on port 5432** (never the transaction pooler on 6543, which breaks LISTEN/NOTIFY and procrastinate). In session mode each open client connection holds one pooler slot for as long as it is open, so the pooler's pool size must cover every connection the services can hold at once, including a deploy overlap. Revise this file in place when a number below changes (Story 15.x revises it after the load test).

## What each process holds

| Process | SQLAlchemy pool | procrastinate pool | LISTEN | Total |
| --- | --- | --- | --- | --- |
| `backend` | `DB_POOL_SIZE` = 10, `max_overflow=0` | 0: jobs are deferred on the request's own connection | 1, reserved for the SSE listener (AD-8) | **11** |
| `worker-ai` | `DB_POOL_SIZE` = 5, `max_overflow=0` | `concurrency + 1` = 2 (the worker's jobs and its LISTEN for new jobs) | inside the procrastinate pool | **7** |
| `worker-batch` | `DB_POOL_SIZE` = 5, `max_overflow=0` | `concurrency + REPORTS_SINGLE_RESERVED + 1 + 1` = 5 (Story 13.7: `reports-single` has 2 slots of its own; the close-out of Epic 13: `reports-bulk` has 1) | inside the procrastinate pool | **10** |
| `backend` pre-deploy `alembic upgrade head` | one connection (NullPool), only while it runs | — | — | **1** |

- `DB_POOL_SIZE` is set per Railway service; it is the SQLAlchemy pool of that process (`backend/app/platform/db.py`, no overflow, a 5-second pool timeout, so a full pool refuses rather than opening more).
- The procrastinate pool is `max(2, concurrency + 1)` (`backend/app/platform/jobs/__init__.py`), plus `REPORTS_SINGLE_RESERVED` (2) in a worker that runs `reports-single` beside other queues (Story 13.7), plus 1 in a worker that runs `reports-bulk` beside other queues (its own slot, so a long ZIP never holds the sweep or the mail). The workers run with the default `--concurrency 1` today. Raising it raises this pool one for one, so raise the budget first.
- `proxy` and `frontend` never connect to the database.

## Total

| | Connections |
| --- | --- |
| One deploy of each service running | 11 + 7 + 10 = **28** |
| During a deploy overlap, old and new side by side (`overlapSeconds` in `railway/<service>/railway.toml`) | 28 × 2 = **56** |
| Plus the migration of the new `backend` | **57** |

**Pooler pool size needed: at least 57.** Supabase's default pool size on the small plans is 15, so it must be raised in Supabase (Database → Settings → Connection pooling → Pool size), and the compute size must allow it: the pool size plus Supabase's own reserved connections must stay below the database's `max_connections` for that compute size. If the compute size cannot allow 57, lower the numbers instead, for example `DB_POOL_SIZE` 6 for `backend` and 3 for each worker: (7 + 5 + 8) × 2 + 1 = **41**.

## The formula

```
per deploy  = (backend DB_POOL_SIZE + 1)
            + Σ over workers (DB_POOL_SIZE + max(2, concurrency + reserved + 1))
pool size  >= 2 × per deploy + 1
```

Story 3.15 sets the pooler's pool size to fit this and records the chosen compute size in its runbook.
