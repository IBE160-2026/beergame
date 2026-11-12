---
title: 'Review: technology currency of ARCHITECTURE-SPINE.md'
reviews: ../ARCHITECTURE-SPINE.md
companion-checked: ../SETUP-GUIDE.md, ../.memlog.md
reviewed: '2026-11-12'
method: 'PyPI JSON API and npm registry queries; wheels for fastapi, procrastinate, sqlalchemy, alembic, weasyprint and pydantic-ai-slim downloaded and their source read; npm dependency resolution dry runs; official docs and web search'
---

# Review: technology currency

## Verdict

Every pinned version exists and matches the registry's latest on 2026-11-12, with TypeScript as the one deliberate exception. The `.memlog.md` shows the versions were checked against npm, PyPI and endoflife.date, not taken from memory. Each named feature exists in the pinned version. Two things break as written: `openapi-typescript` 7.13.0 does not install next to TypeScript 6.0.3, and the Supabase pooler's default pool size of 15 is smaller than the connection count the spine and setup guide imply. A further set of capability caveats (Railway's 15-minute SSE cap, OpenRouter's EU base URL, per-attempt LLM logging, bcrypt 5's 72-byte limit and the SQLAlchemy 2.1 greenlet extra) need a line in the spine or the setup guide before anyone builds.

Status legend: **confirmed** (checked against a registry, the source or official docs) · **outdated** (a newer line exists and matters) · **unverified** (no authoritative evidence found) · **wrong** (contradicted by evidence, will fail as written).

## Summary table

| # | Item | Status | Severity |
| --- | --- | --- | --- |
| 1 | `openapi-typescript` 7.13.0 + TypeScript 6.0.3 | **wrong** (peer conflict, `npm ci` fails) | high |
| 2 | Supavisor session pooler: connection budget | **wrong** (setup-guide numbers exceed default pool size 15) | high |
| 3 | SSE through Railway edge (AD-8, AD-11) | confirmed, with a platform cap the spine does not mention | high |
| 4 | SSE route and DB session dependency lifetime | confirmed (risk in FastAPI's default yield scope) | medium-high |
| 5 | pydantic-ai 2.68.0: providers, structured output, retries, usage | confirmed, with 3 caveats | medium |
| 6 | procrastinate 3.11.0 with psycopg 3 async; periodic; in-transaction defer | confirmed (in-transaction defer **is** supported) | medium (spine under-uses it) |
| 7 | SQLAlchemy 2.1.8 + psycopg async + Alembic 1.20.1 | confirmed, install needs the `asyncio` extra | medium |
| 8 | bcrypt 5.0.0 | confirmed, raises on passwords over 72 bytes | medium |
| 9 | FastAPI 0.162.5 native SSE (`fastapi.sse.EventSourceResponse`) | confirmed | — |
| 10 | Python 3.14 `uuid.uuid7()` | confirmed | — |
| 11 | WeasyPrint 70.0 `pdf/ua-1`, SVG, Debian slim deps | confirmed, output not guaranteed valid | medium |
| 12 | Supabase Supavisor session mode LISTEN/NOTIFY, eu-central-1, Postgres 17 | confirmed (Postgres 17 default from secondary sources) | — |
| 13 | Next.js 16.4.6, React 19.3.1, TypeScript 6.0.3, standalone output | confirmed; TS 7.0.2 is the latest | low |
| 14 | Tailwind 4.3.5 + shadcn 4.23.0 | confirmed | — |
| 15 | Caddy 2.11.9 `reverse_proxy` `flush_interval -1` | confirmed | — |
| 16 | Railway EU West (Amsterdam) | confirmed region; plan eligibility unverified | low |
| 17 | Resend eu-west-1 sending region | confirmed | — |
| 18 | Node.js 24 LTS | outdated (Node 26 is Active LTS) | low |
| 19 | Remaining pins (Uvicorn, Pydantic, PyJWT, resend, supabase, openpyxl, structlog, pytest, uv, TanStack Query, zod, d3, fontsource, Vitest, Playwright) | confirmed | low (Vitest needs `vite`) |
| 20 | Railway private networking bind address | confirmed for new environments | low |

---

## Findings

### 1. openapi-typescript 7.13.0 with TypeScript 6.0.3: **wrong**

- **Evidence:**
  - `npm view openapi-typescript@7.13.0 peerDependencies` gives `{"typescript": "^5.x"}`. 7.13.0 is `latest` (published 2026-02-11), and no 8.x exists (`dist-tags`: `latest 7.13.0`, `next 7.0.0-rc.1`).
  - A dry run in a clean folder, `npm install --package-lock-only typescript@6.0.3 openapi-typescript@7.13.0 openapi-fetch@0.17.0 next@16.4.6 react@19.3.1 …` (npm 11.4.1), fails with:
    ```
    npm error Could not resolve dependency:
    npm error peer typescript@"^5.x" from openapi-typescript@7.13.0
    npm error Fix the upstream dependency conflict, or retry this command with --force or --legacy-peer-deps
    ```
  - An open upstream PR widens the peer range to `^5.x || ^6.x` and reports that no code changes were needed: https://github.com/openapi-ts/openapi-typescript/pull/2818 (seen through a mirror; still open).
  - The same dry run **succeeds** with `"overrides": {"openapi-typescript": {"typescript": "6.0.3"}}` in `package.json`.
- **Impact:** SETUP-GUIDE §6 step 2 runs `npm ci`, and AD-10's CI drift check runs on top of it. Both fail on a fresh lockfile.
- **Fix:** Add the npm `overrides` entry above to `web/package.json`, plus a comment pointing at PR #2818. Remove it once a release widens the peer range. Do not use `--legacy-peer-deps` globally, because it hides real conflicts. The alternative is to run the generator in CI with `npx openapi-typescript@7.13.0` and keep it out of `devDependencies`.

### 2. Supabase session pooler connection budget: **wrong**

- **Evidence:**
  - Supabase compute table (https://supabase.com/docs/guides/platform/compute-and-disk): the default pool size is **15** for Nano, Micro, Small and Medium, and 20 for Large. Pooler max clients is 200 to 800. Direct `max_connections` is 60, 60, 90 and 120.
  - In session mode, each client connection holds one server connection for as long as it is open. Pool size applies "per database user (role)" and can be raised to about 80% of `max_connections` (https://supabase.com/docs/guides/database/connection-management).
  - procrastinate's `PsycopgConnector` creates **its own** `psycopg_pool.AsyncConnectionPool`, separate from SQLAlchemy's (`procrastinate/psycopg_connector.py` lines 100-175; psycopg_pool's default `min_size` is 4). `listen_notify` opens one more standalone connection (`_get_standalone_connection`, line 320).
- **Count, as the guide is written:** api: SQLAlchemy 10 (+ `max_overflow` 10 by default) + the AD-8 `LISTEN` connection 1 + procrastinate's pool for deferring 4. worker: SQLAlchemy 5 (+ overflow) + procrastinate's pool of 4 or more + procrastinate's `LISTEN` 1. Add the `alembic upgrade head` pre-deploy connection, and a second `api` instance during an overlapping zero-downtime deploy. That is about 25 to 45 connections against a cap of 15. Clients beyond the pool size queue in Supavisor, and the stuck-connection symptoms land in Lab hours (NFR-1, NFR-4).
- **Fix (setup guide, plus a line in the spine's Consistency Conventions or AD-8/AD-9):**
  1. Write down a connection budget per process and per deploy overlap.
  2. Raise the Supabase pool size for the app role, for example to 40 on Small, and pick the compute size by that number.
  3. Set SQLAlchemy `max_overflow=0` and size procrastinate's pool explicitly (`PsycopgConnector(min_size=…, max_size=…)`).
  4. In `api`, defer jobs on the SQLAlchemy transaction's own driver connection (see finding 6) so `api` needs no procrastinate pool beyond `min_size=1`.
  5. Or use the direct connection (port 5432 on `db.<ref>.supabase.co`). It is IPv6, or IPv4 with the add-on, and has `max_connections` 60 or more, but it needs IPv6 egress from Railway or the IPv4 add-on. Verify that before choosing it.

### 3. SSE through Railway's edge: confirmed, with a cap the spine does not state

- **Evidence:** Railway Specs & Limits (https://docs.railway.com/networking/public-networking/specs-and-limits): "HTTP requests can run for up to 15 minutes if data keeps transferring … otherwise closed after 5 minutes with no data transferred." WebSockets are exempt. Railway's own streaming guide says SSE connections are terminated after 15 minutes (https://docs.railway.com/guides/ai-chatbot-streaming). A forum thread reports a 300-second cut in one case (https://station.railway.com/community/requests-cut-at-exactly-5-minutes-with-h-88503c0c).
- **Mitigation already present:** FastAPI's SSE sends `: ping` keep-alive comments every 15 seconds (`fastapi/sse.py`: `KEEPALIVE_COMMENT`, `_PING_INTERVAL = 15.0`), so the 5-minute idle limit is not hit. The 15-minute hard cap still applies, and Caddy behind Railway's edge does not remove it.
- **Impact:** Every live view (Lecturer overview, game screen) gets a forced reconnect at least every 15 minutes during a Lab hour. NFR-5's refetch-on-reconnect makes this correct but adds a refetch burst. With 250 players (NFR-3), reconnects synchronised by a deploy or by the cap could spike load.
- **Fix:** In AD-8, state that the stream is closed by the server every ~10 minutes with a jittered `retry:` value. The client reconnects and refetches only the visible queries. Include reconnect storms in the NFR-3 load test.

### 4. SSE route and dependencies with `yield`: confirmed, with a lifetime risk

- **Evidence:** In FastAPI 0.162.5, `Depends(..., scope=...)` takes `"function"` or `"request"`. A `"request"`-scoped dependency with `yield` ends "**after** the response is sent back to the client" (`fastapi/param_functions.py` lines 2424-2445). For an SSE response, "after the response is sent" means after the stream closes.
- **Impact:** If `/api/events` uses the usual `get_db` dependency to load the User (AD-11 "every request loads the User"), every open stream holds a pooled DB connection for up to 15 minutes. At 250 players that pool is gone, and with finding 2 it is gone much sooner.
- **Fix:** Add a rule to AD-8: the events endpoint authenticates with a short-lived session that is opened and closed before the generator starts, never with a `yield` DB dependency. It then re-checks deactivation (FR-3) on the in-memory fan-out, or forces a reconnect when the User changes. Add a test that the DB pool's checked-out count stays flat while N streams are open.

### 5. pydantic-ai 2.68.0: confirmed, with caveats

- **Evidence (wheel `pydantic_ai_slim-2.68.0`, uploaded 2026-11-12T02:30, a few hours before this review):**
  - Providers in `pydantic_ai/providers/`: `openrouter.py`, `bedrock.py`, `google_cloud.py` ("Provider for Google Cloud (formerly known as Vertex AI)", with `eu` multi-region routed to the `aiplatform.eu.rep.googleapis.com` data-residency endpoint), `azure.py` and `mistral.py`. All five listed providers exist.
  - Structured output: `ToolOutput`, `NativeOutput` and `PromptedOutput` in `pydantic_ai/output.py`. Retries: `output_retries` on `Agent` (`agent/__init__.py` line 526). Timeout: `ModelSettings.timeout` (`settings.py` line 265).
  - Usage: `RequestUsage.output_reasoning_tokens: int = 0`, documented as "Number of reasoning (thinking) tokens the model generated. Included in `output_tokens`" (`usage.py` line 168). Each `ModelResponse` carries its own `usage` (`messages.py` line 4928). Cost pricing comes from the `genai-prices` dependency.
  - OpenRouter routing knobs exist in `models/openrouter.py`: `allow_fallbacks`, `data_collection` and `zdr` (lines 305-314).
- **Caveat 5a: the OpenRouter EU base URL is hardcoded.** `OpenRouterProvider.base_url` returns `'https://openrouter.ai/api/v1'`, and the constructor takes no `base_url` and reads no `OPENROUTER_BASE_URL`. The setup guide's `OPENROUTER_BASE_URL=https://eu.openrouter.ai/api/v1` is therefore ignored unless the gateway builds `AsyncOpenAI(base_url=…, api_key=…)` itself and passes `OpenRouterProvider(openai_client=…)`. EU in-region routing on the Business and Enterprise plans is confirmed at https://openrouter.ai/docs/guides/features/in-region-routing.
- **Caveat 5b: retries are inside one run.** pydantic-ai's `output_retries` re-prompts the model inside one `agent.run()`. AD-6 asks for "one `llm_call` row per attempt", a per-attempt timeout and at most 5 retries (AD-5). That works only if the gateway sets `output_retries=0` and loops itself, or splits `result.all_messages()` into one row per `ModelResponse` (each has its own `usage`). A run-level timeout is not a per-attempt timeout.
- **Caveat 5c: reasoning-token coverage depends on the provider adapter.** The field always exists but defaults to 0. Whether each adapter (Bedrock, Mistral, Azure) fills it in was not verified. Also, `pydantic_ai/models/fallback.py` (`FallbackModel`) exists and must never be used (FR-68).
- **Fix:** Write 5a and 5b into AD-6 (gateway-owned retry loop with `output_retries=0`, `openai_client` injection for regional endpoints, no `FallbackModel`). The prototype (issues #8, #9) should check that `output_reasoning_tokens` is filled for the chosen provider. Version 2.68.0 is hours old and pydantic-ai releases almost daily, so pin it through `uv.lock` and upgrade on purpose.

### 6. procrastinate 3.11.0: confirmed; in-transaction defer is supported

- **Evidence (wheel `procrastinate-3.11.0`, uploaded 2026-11-11):**
  - It depends on `psycopg[pool]`. `PsycopgConnector(BaseAsyncConnector)` is built on `psycopg_pool.AsyncConnectionPool`, and `open_async(pool=…)` accepts an existing **psycopg** pool. The `sqlalchemy` extra is `sqlalchemy~=2.0`, so 2.1 is allowed, but `contrib/sqlalchemy` is only the **sync psycopg2** connector. The async path is plain `PsycopgConnector`, which suits this spine.
  - Periodic tasks are cron-based through `croniter` (`periodic.py`), so `@app.periodic(cron="* * * * *")` gives 1-minute granularity. `MAX_DELAY = 600` means missed ticks up to 10 minutes old are caught up. Python 3.10 and newer is supported (`Requires-Python: >=3.10`).
  - In-transaction defer: `Task.configure(connection=…)` → `JobManager.batch_defer_jobs_async(connection=…)` → `PsycopgConnector.execute_query_all_async_with_connection(connection: psycopg.AsyncConnection, …)` (`manager.py` lines 60-81; `psycopg_connector.py` lines 250-276). The docs say: "The job INSERT will execute on your connection, inside your transaction", and they advise savepoints to isolate queueing-lock errors: https://procrastinate.readthedocs.io/en/stable/howto/production/external_connection.html
- **Spine impact:** AD-5 and the Jobs convention say "enqueued after commit" and rely on the sweeper to repair lost enqueues. That is valid but weaker than necessary. With SQLAlchemy async on psycopg, `(await session.connection()).get_raw_connection().driver_connection` is the `psycopg.AsyncConnection`, so `ai-orders` can be deferred **inside** the `open_week` transaction. That means no lost-job window, it reduces the `ai-orders` sweeper fallback to a true safety net (NFR-2 latency), and it removes the need for a procrastinate pool in `api` (finding 2).
- **Fix:** Change AD-5 and the Jobs convention to "deferred in the same transaction through the SQLAlchemy driver connection, wrapped in a savepoint". Keep the sweeper as the repair path. Add the procrastinate schema to Alembic: run `procrastinate schema --apply` or its migrations from an Alembic revision, so the "Alembic only" convention holds.

### 7. SQLAlchemy 2.1.8 + psycopg async + Alembic 1.20.1: confirmed, install detail

- **Evidence:**
  - `sqlalchemy/dialects/postgresql/psycopg.py`: `class PGDialectAsync_psycopg` and `dialect_async = PGDialectAsync_psycopg` (lines 765, 800). The URL `postgresql+psycopg://` works with `create_async_engine`.
  - Alembic 1.20.1 `Requires-Dist: SQLAlchemy>=2.0` and classifiers include Python 3.14 and 3.15. The templates include `async/` and `pyproject_async/`.
  - psycopg-binary 3.3.9 has cp314 wheels, and greenlet 3.5.6 has cp314 wheels.
  - **greenlet:** SQLAlchemy 2.1.8 metadata has `greenlet>=1; extra == "asyncio"`, and its `postgresql-psycopg` extra does **not** pull in greenlet. SQLAlchemy 2.0.40 installed greenlet automatically only when `python_version < "3.14"`. On Python 3.14 with SQLAlchemy 2.1, the async engine fails at runtime without the extra.
- **Fix:** In the setup guide or `pyproject.toml`, specify `sqlalchemy[asyncio,postgresql-psycopgbinary]==2.1.8` (or `psycopg[binary,pool]==3.3.9` separately). Use `alembic init -t pyproject_async`.

### 8. bcrypt 5.0.0: confirmed, behaviour change

- **Evidence:** pyca/bcrypt README: "Passing hashpw a password longer than 72 bytes now raises a ValueError" (previously silently truncated). https://github.com/pyca/bcrypt
- **Impact:** AD-11 login and registration. Norwegian letters æ, ø and å take 2 bytes each in UTF-8, so a password of 40 or more such letters can exceed 72 bytes and return a 500 error.
- **Fix:** Validate the password at registration as at most 72 UTF-8 bytes, with a stable error code under AD-19 and Norwegian copy. Otherwise pre-hash with HMAC-SHA256 and base64 before bcrypt, and record that choice in AD-11.

### 9. FastAPI 0.162.5 native SSE: confirmed

- **Evidence:** PyPI latest is 0.162.5. In the wheel, `fastapi/sse.py` defines `class EventSourceResponse(StreamingResponse)` with `media_type = "text/event-stream"`, plus `ServerSentEvent` and `format_sse_event`. `routing.py` (line 422) detects `response_class=EventSourceResponse` on generator path operations and serialises the yielded items. There is a built-in keep-alive ping every 15 seconds. `.memlog.md` notes native SSE "since 0.135", which matches.
- **Fix:** None. Use `from fastapi.sse import EventSourceResponse, ServerSentEvent` and `response_class=EventSourceResponse`, not the third-party `sse-starlette`.

### 10. Python 3.14 `uuid.uuid7()`: confirmed

- **Evidence:** https://docs.python.org/3.14/library/uuid.html: `uuid.uuid7()` was "Added in version 3.14", per RFC 9562 §5.7, with a 48-bit ms timestamp and a 42-bit counter that keeps it monotonic within a millisecond. endoflife.date: 3.14.10 is current and 3.15.2 the newest. Docker `python:3.14-slim` (trixie) exists.
- **Note:** Postgres 17 has no native `uuidv7()` (it arrived in 18), so generating ids in the app is the right choice.

### 11. WeasyPrint 70.0: confirmed, compliance not guaranteed

- **Evidence:**
  - Wheel `weasyprint-70.0` (2026-09-08), `pdf/pdfua.py`: `VARIANTS = {'pdf/ua-1': (…, {'pdf_version': '1.7', 'pdf_tags': True}), 'pdf/ua-2': (…, {'pdf_version': '2.0', 'pdf_tags': True})}`. The classifiers include Python 3.14.
  - SVG is rendered as vectors (`weasyprint/svg/`). In `pdf/tags.py` (lines 118, 199-218), inline `<svg>` is tagged `Figure`, and its `Alt` text comes **only from a child `<title>` element**. Otherwise it logs "has no required alt description".
  - The docs (https://doc.courtbouillon.org/weasyprint/stable/api_reference.html) say "the generated documents are not guaranteed to be valid".
  - Debian ≥ 11 packages when installing from wheels: `libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0`, with Pango ≥ 1.44 (https://doc.courtbouillon.org/weasyprint/stable/first_steps.html). All three exist in Debian trixie (packages.debian.org returns 200).
- **Fix:**
  1. Put the exact apt line in the setup guide, and add a fallback font package (for example `fonts-dejavu-core`) or make sure Source Sans 3 loads through `@font-face` from the print page. fonttools[woff] is present, so WOFF2 works.
  2. The AD-18 chart module must render `<title>` as the first child of every `<svg>`, because `aria-label` is ignored for PDF Alt text.
  3. Add a veraPDF PDF/UA-1 check of a sample report to CI (NFR-6).
  4. WeasyPrint fetches subresources (CSS, fonts) itself, so either inline the print page's CSS or make sure `/_next/static/*` is reachable at `WEB_INTERNAL_URL`. If a custom `url_fetcher` adds `INTERNAL_TOKEN`, restrict it to the `web` host.

### 12. Supabase: confirmed

- **Session pooler and LISTEN/NOTIFY:** Supabase docs say session mode on port 5432 is meant for persistent clients that need "SET statements, prepared statements, LISTEN/NOTIFY, or advisory locks". Session mode on 6543 was deprecated on 2025-02-28 and 6543 is transaction-only (https://supabase.com/docs/reference/postgres/connection-strings, https://supabase.com/changelog/32755-supabase-connection-pooler-deprecating-session-mode-on-port-6543-on-february-28-2025). The shared pooler is IPv4 on every plan, which suits Railway. Long-lived connections are supported but each one holds a pool slot (finding 2).
- **eu-central-1:** listed as "Central EU (Frankfurt), `eu-central-1`" (https://supabase.com/docs/guides/platform/regions). eu-north-1 (Stockholm) also exists, but Frankfurt is closer to Railway's Amsterdam region.
- **Postgres 17 default:** Supabase's changelog says Postgres 17 is "what we currently default to on the Supabase platform". No official Postgres 18 announcement was found. This status rests on secondary sources: https://supabase.com/changelog/46080-self-hosted-supabase-upgrading-from-pg-15-to-17-breaking-change. endoflife.date has 18.7 as the newest Postgres and 17.12 as supported until 2029-11.
- **Fix:** None for the version. Keep the guide's "17 or the project default if higher". Measure the Amsterdam to Frankfurt round trip early: AD-2 commands make several round trips per transaction (NFR-1 allows 2 seconds, so it should be fine, but it is not verified).

### 13. Next.js 16.4.6 / React 19.3.1 / TypeScript 6.0.3: confirmed

- **Evidence:**
  - npm `latest`: next 16.4.6, react 19.3.1, typescript **7.0.2** (6.0.3 is the newest 6.x, published 2026-04-16). Next 16.4.6 peers accept `react ^19.0.0` and need `node >=20.9.0`.
  - The Next.js 16.4 blog (2026-10-06): "Next.js 16.4 ships with React 19.3", and `create-next-app` now enables **Cache Components by default**.
  - TypeScript 7 has no JS compiler API, so Next needs `experimental.useTypeScriptCli` to type-check with it (https://nextjs.org/docs/app/api-reference/config/next-config-js/useTypeScriptCli, Next 16.3 notes). Pinning 6.0.3 is a sound, documented choice (`.memlog.md` assumption line).
  - Standalone output is still supported: `output: 'standalone'`, `server.js`, with `public/` and `.next/static` copied by hand, and `PORT` and `HOSTNAME` env vars (https://nextjs.org/docs/app/api-reference/config/next-config-js/output, updated 2026-09-18).
- **Fix:**
  1. Keep TypeScript 6.0.3, with finding 1's override.
  2. Have the setup guide's `web/Dockerfile` copy `public` and `.next/static` into the standalone folder.
  3. Decide whether to keep Cache Components on, since the scaffold enables it. AD-10 makes the app client-fetch heavy and the print route must be dynamic, so turn it off or mark the print route dynamic explicitly.

### 14. Tailwind 4.3.5 + shadcn 4.23.0: confirmed

- **Evidence:** npm `latest` is tailwindcss 4.3.5 (published 2026-11-06) and shadcn 4.23.0 (`engines.node >=20.18.1`). shadcn docs: "The CLI can now initialize projects with Tailwind v4" and "All components are updated for Tailwind v4 and React 19". `tailwindcss-animate` is replaced by `tw-animate-css` (https://ui.shadcn.com/docs/tailwind-v4).
- **Fix:** None. Add `@tailwindcss/postcss` 4.3.5 to the stack table, since it is required with Next.

### 15. Caddy 2.11.9 `flush_interval -1`: confirmed

- **Evidence:** GitHub's latest release is v2.11.9 (2026-11-05), and the Docker tag `caddy:2.11.9` exists. The docs (https://caddyserver.com/docs/caddyfile/directives/reverse_proxy) say a negative value "suggests 'low-latency mode' which disables response buffering completely". They also say responses with `Content-Type: text/event-stream` are flushed immediately anyway, and that `-1` "does not cancel the request to the backend even if the client disconnects early".
- **Fix:** None for correctness. The `-1` is redundant for SSE but harmless; scope it to `/api/events` if you want buffering elsewhere. Since the backend is not cancelled on client disconnect, the SSE generator should still check `request.is_disconnected()` or rely on the keep-alive write failing.

### 16. Railway EU West (Amsterdam): confirmed region, plan eligibility unverified

- **Evidence:** https://docs.railway.com/reference/deployment-regions lists "EU West Metal, Amsterdam, Netherlands, `europe-west4-drams3a`". The page does not say which plans may use which region. A forum thread reports egress through a California NAT IP from this region (https://station.railway.com/questions/service-in-europe-west4-drams3a-egresses-48eafba3). If confirmed, that affects any provider IP allow-listing, not data residency of the compute.
- **Fix:** Pin the region in each `railway.toml` (current config-as-code uses `multiRegionConfig`; per a forum thread, `region` is deprecated). Confirm plan eligibility when creating the project. Treat egress IP as non-EU for any allow-list.

### 17. Resend eu-west-1: confirmed

- **Evidence:** Resend docs list Ireland (`eu-west-1`) among the sending regions (us-east-1, eu-west-1, sa-east-1, ap-northeast-1). The region is set per domain when it is added, and changing it means deleting and re-adding the domain. Account data stays in the US (https://resend.com/docs/dashboard/domains/regions). This matches the spine's Deferred note. The resend Python SDK 2.53.2 is the PyPI latest.
- **Fix:** None. Pick eu-west-1 when the domain is **first** added (SETUP-GUIDE §7 item 4).

### 18. Node.js 24 LTS: outdated (still supported)

- **Evidence:** endoflife.date: Node 26 (26.13.1) is LTS from 2026-10. Node 24 (24.22.3) is in maintenance LTS until 2028-04-30. Vitest 5.1.0 engines `^22.12.0 || ^24.0.0 || >=26.0.0`, and Next needs `>=20.9`.
- **Fix:** Optional. Node 24 is fine through the pilot. Note the Next 16.4 remark that Node ≥ 24.13.1 falls back from the experimental worker-threads plugin runtime (not used here). Choose 26 if you want the longer runway.

### 19. Remaining pins: confirmed

PyPI latest equals the pin for uvicorn 0.54.0, pydantic 2.14.3, pydantic-settings 2.16.2, psycopg 3.3.9, PyJWT 2.15.1, bcrypt 5.0.0, resend 2.53.2, supabase 2.34.1, openpyxl 3.1.5, structlog 26.1.0, pytest 9.2.0 and uv 0.13.7 (GitHub release 2026-11-03). npm latest equals the pin for @tanstack/react-query 5.107.1 (peer `react ^18 || ^19`), zod 4.6.7, openapi-fetch 0.17.0, d3-scale 4.0.3, d3-shape 3.2.1, @fontsource/source-sans-3 5.3.1, vitest 5.1.0 and @playwright/test 1.65.0 (Next peer `^1.51.1`).
- **Fix:** Vitest 5 needs `vite` (`^6.4 || ^7 || ^8`) as a peer, so add `vite` and `jsdom` or `happy-dom` to the web devDependencies. `supabase` 2.34.1 pulls in auth, realtime and postgrest clients the app does not use. Consider depending only on `storage3`, or keep it for simplicity.

### 20. Railway private networking bind address: confirmed

- **Evidence:** Railway docs: environments created before 2025-10-16 have IPv6-only private networking, and newer environments are dual-stack (https://docs.railway.com/networking/private-networking/how-it-works). A new `olspillet` project gets dual-stack, so `uvicorn --host 0.0.0.0` works.
- **Fix:** Use `--host ::` for uvicorn and `HOSTNAME=::` for Next if the services are ever placed in an older environment.

---

## Not checked

- Whether Railway's IPv6 egress can reach Supabase's direct (IPv6) endpoint (only relevant to finding 2 option 5).
- Actual `output_reasoning_tokens` population per provider adapter (finding 5c). The prototype should check this.
- The full web dependency tree: a dry run with `vitest`, `@playwright/test`, `shadcn` and `@tailwindcss/postcss` added hit an internal npm 11.4.1 error (`Cannot read properties of null (reading 'edgesOut')`) unrelated to finding 1. Re-run with a real `npm install` when scaffolding.
