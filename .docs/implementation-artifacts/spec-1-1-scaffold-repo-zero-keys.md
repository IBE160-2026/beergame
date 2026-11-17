---
title: 'Story 1.1: Scaffold the repo so it starts locally with zero keys'
type: 'chore'
created: '2026-11-17'
status: 'done'
baseline_revision: '759b881f982805cbc7066d8de5f45e6ce98efe79'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-1-context.md'
  - '{project-root}/.docs/planning-artifacts/architecture/architecture-beergame-2026-11-12/ARCHITECTURE-SPINE.md'
  - '{project-root}/.docs/planning-artifacts/architecture/architecture-beergame-2026-11-12/SETUP-GUIDE.md'
warnings: ['oversized']
deferred:
  - summary: >-
      The compose stack and the Caddy routing are never built or run in CI; proxy behaviour is checked only by static tests of the Caddyfile text.
    evidence: |-
      .github/workflows/ci.yml has only the api and web jobs required by Story 1.1. A broken Dockerfile, entrypoint, compose default or Caddyfile syntax would pass CI. Verified live locally only (docker compose up with an empty env file; curl through :8080). Settle by adding a compose smoke job (docker compose up --build --wait, curl /api/health, /, /print/x) or caddy validate, at the latest with the Playwright-against-compose story.
    location: >-
      .github/workflows/ci.yml
    severity: medium
---

<intent-contract>

## Intent

**Problem:** The repo is empty of code. Every later story needs one agreed layout, one command to start the stack locally with no keys, and a CI run that guards it.

**Approach:** Scaffold `api/` (uv, Python 3.14, FastAPI), `web/` (Next.js 16 standalone), `proxy/` (Caddy) and `docker-compose.yml` exactly as the spine's Structural Seed and Stack table say, with config, DB engine, Alembic baseline, structlog and a DB-backed health check, plus a GitHub Actions workflow with an `api` and a `web` job.

## Boundaries & Constraints

**Always:**
- Pin every version to the spine Stack table (Python 3.14, FastAPI 0.162.5, Uvicorn 0.54.0, Pydantic 2.14.3, pydantic-settings 2.16.2, SQLAlchemy[asyncio] 2.1.8, psycopg 3.3.9, Alembic 1.20.1, structlog 26.1.0, pytest 9.2.0; Node 24, Next.js 16.4.6, React 19.3.1, TypeScript 6.0.3, Tailwind 4.3.5, shadcn 4.23.0, openapi-typescript 7.13.0; `postgres:17`; Caddy 2.11.9). Exact pins (`==` / no caret). Commit `api/uv.lock` and `web/package-lock.json`. Dev-only tools not in the table (ruff, pytest-asyncio, httpx) are pinned exactly too.
- `docker compose up` must work with no `.env` file: every compose variable has an inline default; `APP_ENV=local`.
- One pydantic-settings class (`app/platform/config.py`) holds `APP_ENV` (`local|test|ci|production`, default `local`), `DATABASE_URL`, `DB_POOL_SIZE`, `LOG_LEVEL` and the seven flags `FEATURE_STUDENT_CHOICE`, `FEATURE_CROSS_INSTITUTION_STATS`, `FEATURE_RERUN`, `FEATURE_INFO_VISIBILITY`, `FEATURE_LECTURER_TEST_GAME`, `FEATURE_GAME_DATA_EXPORT`, `FEATURE_CAPACITY` (default `true`).
- One async SQLAlchemy engine (`app/platform/db.py`) on `postgresql+psycopg`, `max_overflow=0`.
- Alembic owns the schema; the baseline revision is empty. The api container runs `alembic upgrade head` before uvicorn locally.
- The FastAPI app serves its routes under `/api`; Caddy passes the path through unchanged.
- Logs: structlog JSON, one line per request with `request_id`; an allowlist processor drops any key not on the list, and the list contains no name, email or free-text field.

**Never:**
- No auth rules in Caddy, no workers (`worker-ai`, `worker-batch`), no procrastinate, no `railway/`, no seed data, no shadcn components, no contract/copy/Playwright/veraPDF/simulation CI steps.
- No tables created outside Alembic; no `create_all`.
- Never edit `.env`, `.claude/settings*.json`, `sprint-status.yaml`; never commit keys.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Health, DB up | `GET /api/health` via proxy :8080 | `200 {"status":"ok"}` | — |
| Health, DB down | DB unreachable | `503 {"error":{"code":"db_unavailable","message":...,"fields":{}}}` | Caught, logged without secrets |
| Print route | `GET /print/anything` via proxy | `404` from Caddy, never reaches web | — |
| Root | `GET /` via proxy | 200, empty Next.js page | — |
| Prod guard, missing | `APP_ENV=production`, no `DATABASE_URL` | Process refuses to start; message names `DATABASE_URL` | `ConfigError`/`SystemExit` at settings load |
| Prod guard, default | `APP_ENV=production`, `DATABASE_URL` = built-in local default | Same refusal | Same |
| Local, no env | `APP_ENV` unset | Loads with defaults, flags `true` | — |

</intent-contract>

## Code Map

Greenfield: no application code exists yet. Existing files to respect:
- `.gitignore` -- extend with `.local-storage/`, `.next/`, `.pytest_cache/`, `.ruff_cache/`, `next-env.d.ts`; keep `.env.*` / `!.env.example`.
- `.gitattributes` -- `* text=auto eol=lf`; shell entry scripts stay LF.
- `README.md` -- one line today; add a short "Run locally" section.
- Planning sources (read-only): spine Stack table and Structural Seed (`ARCHITECTURE-SPINE.md` lines ~378-525), SETUP-GUIDE §3.7 Caddyfile sketch and §3.8 flag names, §3.9 compose variables (`COMPOSE_PROJECT_NAME=olspillet`, `POSTGRES_USER/PASSWORD/DB`, `HTTP_PORT` default 8080).

## Tasks & Acceptance

**Execution:**
- `api/pyproject.toml`, `api/uv.lock`, `api/.python-version` -- uv project `olspillet-api`, `requires-python ==3.14.*`, pinned deps; ruff + pytest config (`asyncio_mode=auto`) -- one uv project per spine.
- `api/app/{engine,analysis,ai,modules}/__init__.py` -- empty packages -- layer folders (AD-1).
- `api/app/platform/config.py` -- `Settings` class + `get_settings()`; production guard raising a clear error naming `DATABASE_URL` -- AD-17.
- `api/app/platform/db.py` -- `create_async_engine(..., max_overflow=0, pool_size=settings.db_pool_size)`, session factory, `ping()` -- one engine.
- `api/app/platform/logging.py` -- structlog JSON setup, `ALLOWED_FIELDS` allowlist processor, request middleware binding `request_id` (uuid7) and writing one line per request -- logging convention.
- `api/app/main.py` -- FastAPI app, lifespan (settings check, engine dispose), `APIRouter(prefix="/api")` with `GET /health` -- AD-11/AD-17.
- `api/app/worker.py`, `api/app/sim.py` -- stub entry points (`python -m app.worker` / `python -m app.sim` print a one-line notice and exit 0) -- filled in Epic 2 / Story 1.2+.
- `api/alembic.ini`, `api/migrations/{env.py,script.py.mako,versions/0001_baseline.py}` -- async env reading `DATABASE_URL` from settings; empty baseline -- AD-24.
- `api/tests/` -- `test_config.py` (defaults, flags, prod guard both cases), `test_health.py` (200 with DB, 503 with unreachable DB), `test_logging.py` (one JSON line with `request_id`; allowlist excludes names/emails/free text; extra `email=` key dropped), `test_migrations.py` (`alembic upgrade head` on the test DB succeeds and leaves only `alembic_version`) -- I/O matrix.
- `api/Dockerfile`, `api/docker-entrypoint.sh`, `api/.dockerignore` -- `python:3.14-slim` + uv 0.13.7, `uv sync --locked --no-dev`; entrypoint runs `alembic upgrade head` then uvicorn on :8000.
- `web/` -- `package.json` (exact pins, `overrides: {"openapi-typescript": {"typescript": "6.0.3"}}`, scripts `dev`, `build`, `start`, `typecheck`), `package-lock.json`, `next.config.ts` (`output: "standalone"`), `tsconfig.json`, `postcss.config.mjs`, `src/app/{layout.tsx,page.tsx,globals.css}`, `components.json`, `src/lib/utils.ts`, `.gitkeep` in `src/modules`, `src/components`, `src/copy`; `Dockerfile` (multi-stage `node:24`, standalone `node server.js` on :3000), `.dockerignore` -- empty page only.
- `proxy/Caddyfile`, `proxy/Dockerfile` -- `caddy:2.11.9`; `:{$PORT:8080}`; `/api/*` → `{$API_UPSTREAM:api:8000}` with `flush_interval -1`; `/print/*` → 404; rest → `{$WEB_UPSTREAM:web:3000}` -- AD-11.
- `docker-compose.yml` -- `name: olspillet`; `postgres` (`postgres:17`, healthcheck `pg_isready`, volume), `api` (depends on postgres healthy; healthcheck on `/api/health`), `web`, `proxy` (port `${HTTP_PORT:-8080}:8080`, depends on api healthy + web) -- zero keys.
- `.env.example` -- variable names only (no values) for api, web, proxy, compose and the seven flags.
- `.github/workflows/ci.yml` -- on push + pull_request; job `api` (postgres:17 service, setup uv 0.13.7, `uv sync --locked`, `ruff check`, `ruff format --check`, `pytest`); job `web` (Node 24, `npm ci`, `npm run typecheck`, `npm run build`).

**Acceptance Criteria:**
- Given a fresh clone with no `.env`, when `docker compose up` runs, then `postgres`, `api`, `web`, `proxy` start and `curl http://localhost:8080/api/health` returns 200 only after the api reached the database; `/` returns the Next.js page; `/print/x` returns 404.
- Given the repo, when listed, then it holds every folder and file named in Story 1.1 (api layers, `migrations/`, `tests/`, web `src/{app,modules,components,lib,copy}`, `components.json`, `proxy/Caddyfile`, `proxy/Dockerfile`, `docker-compose.yml`, `.env.example`), with `uv.lock` and `package-lock.json` committed.
- Given `uv sync --locked`, `ruff check`, `pytest` (against a Postgres 17) and `npm ci && npm run typecheck && npm run build`, when run locally as CI would, then all pass.

## Spec Change Log

## Review Triage Log

### 2026-11-17 — Review pass
- verdicts: 35 findings — high 0, medium 11, low 22, false 2, maybe-false 0 (duplicates across layers keep their own rows and share the route)
- findings:
  - `[false]` `[reject]` (blind) CI typecheck before build fails without next-env.d.ts — ran `rm -rf .next next-env.d.ts && npm ci && npm run typecheck` locally: passes.
  - `[medium]` `[patch]` (blind) bare `/print` (and `/api`) not matched by `handle /print/*` — Caddyfile now uses named matchers `@print path /print /print/*` and `@api path /api /api/*`; static test added; live curl `/print` → 404.
  - `[false]` `[reject]` (blind) CRLF risk on docker-entrypoint.sh — `.gitattributes` has `* text=auto eol=lf`.
  - `[medium]` `[patch]` (blind) allowlist drops exception tracebacks — added `format_exc_info` and allowed `exception`; test added. Sub-claim that third-party `event` text passes: low, rejected — `event` is the message key and cannot be filtered by key.
  - `[low]` `[reject]` (blind) error envelope only on /api/health — no other endpoint exists yet; global handlers are new surface for the story that adds endpoints.
  - `[low]` `[patch]` (blind) LOG_LEVEL unvalidated — now a case-insensitive Literal; refusal names the variable; test added.
  - `[low]` `[patch]` (blind) .env.example vs compose — added `RUN_MIGRATIONS`; comment says .env feeds compose only. PORT/API_UPSTREAM/WEB_UPSTREAM stay as the proxy's production variables.
  - `[low]` `[patch]` (blind) proxy waits only for web started — now `service_healthy`.
  - `[low]` `[patch]` (blind) health probe can wait 30s on a full pool — `pool_timeout=5`.
  - `[medium]` `[defer]` (blind) CI never builds images or validates the Caddyfile — grouped with the compose-smoke deferral.
  - `[low]` `[reject]` (blind) test gaps (downgrade round trip, lifespan, unneeded fixture, 503 request-id) — empty baseline has no downgrade logic; the rest are cosmetic.
  - `[low]` `[reject]` (blind) base images float — pinned to the Stack table's level (Python 3.14, Node 24, Postgres 17), as the AC asks.
  - `[low]` `[reject]` (blind) no /api rewrite for `next dev` — the web app makes no API calls yet.
  - `[low]` `[patch]` (blind) README local details — README now says `docker compose up -d postgres`, two terminals, api reads env vars not .env.
  - `[low]` `[reject]` (blind) public/ not copied, no openapi script, no web lint — no public/ dir; contract check and lint belong to later stories.
  - `[medium]` `[defer]` (verification-gap) proxy routing checked only by regex — grouped with the compose-smoke deferral.
  - `[medium]` `[defer]` (verification-gap) compose stack never run in CI — deferred (frontmatter); live run done locally with an empty env file.
  - `[medium]` `[patch]` (verification-gap) Alembic CLI default path untested — added a subprocess `python -m alembic upgrade head` test with only DATABASE_URL set.
  - `[medium]` `[defer]` (intent) acceptance lives at the running stack while tests are in-process — grouped with the compose-smoke deferral; verified live locally.
  - `[low]` `[reject]` (intent) prod guard tested via load_settings, not at uvicorn import — `app.main` calls the same `get_settings()` at import.
  - `[low]` `[reject]` (intent) components.json names lucide but lucide-react is not installed — shadcn installs it with the first component.
  - `[medium]` `[patch]` (edge) `postgresql://` URL loads psycopg2 — validator rewrites to `postgresql+psycopg://`; test added.
  - `[low]` `[patch]` (edge) LOG_LEVEL unknown value — same fix as the blind row.
  - `[low]` `[patch]` (edge) DB_POOL_SIZE 0 or negative — `Field(ge=1)`; test added.
  - `[low]` `[patch]` (edge) health blocks on pool_timeout — same fix as the blind row.
  - `[medium]` `[patch]` (edge) exc_info dropped — same fix as the blind row.
  - `[low]` `[reject]` (edge) 500 raised outside the middleware lacks x-request-id — rare; fix adds error-handling surface.
  - `[medium]` `[patch]` (edge) postgres first-boot pg_isready race — healthcheck now `pg_isready -h 127.0.0.1` (the init server listens on the socket only); fresh-volume run passed.
  - `[low]` `[reject]` (edge) special characters in POSTGRES_PASSWORD — local defaults only; overriders can URL-encode.
  - `[medium]` `[patch]` (edge) bare /print and /api — same fix as the blind row.
  - `[low]` `[patch]` (edge) proxy starts before web listens — same fix as the blind row.
  - `[low]` `[reject]` (edge) conftest DB name None or already _test — DATABASE_URL always names a database here.
  - `[low]` `[reject]` (edge) test_logging teardown empties handlers — later tests do not assert on log output.
  - `[low]` `[patch]` (edge) .env not read by local uvicorn — documented in .env.example and README.
  - `[low]` `[reject]` (edge) allowlist claim on `event` free text — `event` is the message key; same reasoning as the blind sub-claim.

## Design Notes

- Health returns 503 on DB failure so compose's api healthcheck (and so proxy startup) gates on a live DB.
- The production guard compares `DATABASE_URL` with the built-in local default constant; later epics add `JWT_SECRET`, `RESEND_API_KEY` and storage keys to the same list.
- Tests needing Postgres read `DATABASE_URL` from the environment (CI service; locally the compose `postgres` exposed on `${POSTGRES_PORT:-5432}`), and use a dedicated test database or schema reset so `alembic upgrade head` starts from empty.

## Verification

**Commands:**
- `cd api && uv sync --locked && uv run ruff check . && uv run ruff format --check . && uv run pytest` -- expected: all pass (Postgres from compose running)
- `cd web && npm ci && npm run typecheck && npm run build` -- expected: success
- `docker compose up -d --build` then `curl -i localhost:8080/api/health` (200), `curl -i localhost:8080/` (200), `curl -i localhost:8080/print/x` (404); `docker compose down` -- expected as stated

## Auto Run Result

Status: done

**Summary:** Repo scaffolded from the Structural Seed: `api/` (uv, Python 3.14, FastAPI under `/api`, pydantic-settings with `APP_ENV` and the seven `FEATURE_*` flags, production guard on `DATABASE_URL`, one async engine with `max_overflow=0`, structlog JSON with `request_id` and a field allowlist, empty Alembic baseline run by the container entrypoint, stub `worker.py` and `sim.py`), `web/` (Next.js 16.4.6 standalone, TS 6.0.3, Tailwind 4, shadcn `components.json`, openapi-typescript override), `proxy/` (Caddy 2.11.9), `docker-compose.yml` (zero keys), `.env.example`, and CI with `api` and `web` jobs.

**Files:** `api/**` (app, migrations, tests, Dockerfile, entrypoint, pyproject and uv.lock), `web/**` (Next app, package.json and package-lock.json, Dockerfile), `proxy/Caddyfile`, `proxy/Dockerfile`, `docker-compose.yml`, `.env.example`, `.github/workflows/ci.yml`, `.gitignore`, `README.md`.

**Review:** 35 findings. Patched 17 rows (5 medium root causes: bare /print and /api matchers, exception tracebacks, Alembic CLI test, postgres:// driver, pg_isready race; plus low fixes for LOG_LEVEL and DB_POOL_SIZE validation, pool timeout, web healthy dependency, env and README notes). Deferred 4 rows as 1 group (compose smoke and Caddy run in CI, medium). Rejected 2 false and 12 low rows, with reasons in the triage log.

**Verification:** `uv sync --locked`, `ruff check`, `ruff format --check`, `pytest` → 25 passed. `npm ci`, `npm run typecheck` (from a tree without next-env.d.ts), `npm run build` → success. `docker compose --env-file <empty> up --wait` from a fresh volume → all four services healthy; `/api/health` 200, `/` 200, `/print` and `/print/x` 404, `/api/nope` 404; api logs one JSON request line with `request_id`.

**Follow-up review recommended:** true — patched medium root causes: 5, high: 0. Named unverified risk: the GitHub Actions workflow has never run (no push in this run); `setup-uv@v7`, the Postgres service and npm caching are checked only by reading.

**Residual risks:** compose and Caddy behaviour are not guarded in CI (deferred). On this machine `localhost:8080` over IPv6 is held by a WSL relay; use `127.0.0.1:8080`.
