---
title: 'Story 3.14: Prepare a strict production configuration in the repo'
type: 'chore'
created: '2026-11-18'
status: 'done'
baseline_revision: '519a950227f2dd386e9cdbba4a92fe6d10ca2589'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-3-context.md'
  - '{project-root}/.docs/planning-artifacts/architecture/architecture-beergame-2026-11-12/SETUP-GUIDE.md'
warnings: [oversized]
deferred:
  - summary: >-
      The client-IP chain behind Railway's edge is verified only locally, where every peer is private.
    evidence: |-
      Caddy trusts X-Real-IP from private_ranges and 100.0.0.0/8 (Railway's own Caddy guide; Railway publishes no edge range). If the edge hop is outside these ranges, or a request arrives without X-Real-IP, every caller resolves to the edge address and shares one rate-limit bucket. Settle in Story 3.15: through the public domain, two clients on different networks each fail a login; the second must not be refused by the first's per-IP count, and a forged X-Real-IP or X-Forwarded-For from a client must not change its bucket.
    location: >-
      proxy/Caddyfile:5-11
    severity: medium (unverified)
  - summary: >-
      The railway.toml files are checked against the repo only, not against Railway's parser.
    evidence: |-
      Railway marks config-as-code deprecated (existing files honoured until 2026-12-01) in favour of Infrastructure as Code. The region key europe-west4-drams3a (EU West, Amsterdam), integer overlapSeconds/drainingSeconds, the per-service config file path /railway/<service>/railway.toml and the repo-root build context with dockerfilePath are taken from Railway's docs and not tried. Settle in Story 3.15 when the services are created: each service shows EU West, the start and pre-deploy commands, health check, overlap and draining from these files, or the project moves to the IaC form.
    location: >-
      railway/
    severity: medium (unverified)
  - summary: >-
      backend and frontend listen on IPv4 (0.0.0.0, SETUP-GUIDE §1); Railway's private network is IPv6-only in environments created before mid-October 2025.
    evidence: |-
      A new project should get IPv4 and IPv6 private networking, so the guide's commands work. Settle in Story 3.15: if proxy cannot reach backend.railway.internal or frontend.railway.internal, start uvicorn with --host :: and set HOSTNAME=:: on frontend.
    location: >-
      railway/backend/railway.toml, railway/frontend/railway.toml
    severity: medium (unverified)
---

<intent-contract>

## Intent

**Problem:** The repo cannot be deployed safely yet: there is no per-service Railway config, the production startup guard only checks `DATABASE_URL`, the connection budget is unwritten, there is no smoke test, and the client IP used for rate limits is the last `X-Forwarded-For` entry from whoever sent it, which behind Railway's edge would be the edge's own address (deferred from Story 3.2).

**Approach:** Add `railway/<service>/railway.toml` for the five services, widen the AD-17 guard in `platform/config` to every secret and production-only rule from Epics 1–3 (one message naming each bad variable, never its value), make Caddy the single place that decides the client IP and have the backend trust `X-Forwarded-For` only from a trusted proxy peer, write `docs/ops/connection-budget.md`, and add `scripts/smoke` run by CI against `docker compose`. No cloud account, login, deploy or production call: what needs one is written down for Story 3.15.

## Boundaries & Constraints

**Always:**
- `railway/{proxy,frontend,backend,worker-ai,worker-batch}/railway.toml` (config-as-code; the service's «config file path» points at it): `builder = "DOCKERFILE"`; `dockerfilePath` `proxy/Dockerfile`, `frontend/Dockerfile`, and `backend/Dockerfile` for all three Python services; `[deploy.multiRegionConfig."europe-west4-drams3a"] numReplicas = 1` (EU West, Amsterdam); `startCommand` from SETUP-GUIDE §1 (backend `uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log`, worker-ai `python -m app.worker --queues ai-orders`, worker-batch `python -m app.worker --queues llm-batch,mail --sweeper` — only the queues that exist today, as compose; frontend `node server.js`; proxy `caddy run --config /etc/caddy/Caddyfile --adapter caddyfile`); `healthcheckPath` `/api/health` (backend, proxy) and `/` (frontend), none for workers; `watchPatterns` (`/backend/**` for the three Python services, `/frontend/**`, `/proxy/**`, each plus its own `/railway/<service>/**`); `overlapSeconds` and `drainingSeconds` on every service; `restartPolicyType = "ON_FAILURE"`. Only `backend` has `preDeployCommand = ["alembic upgrade head"]`.
- `backend/docker-entrypoint.sh`: with `APP_ENV=production` and no `RUN_MIGRATIONS`, migrations are skipped (only the pre-deploy migrates, AD-24); local default unchanged.
- Guard (`Settings.production_problems()` → list of variable names, `check_production` raises `ConfigError` naming all of them): with `APP_ENV=production` refuse when
  - `DATABASE_URL` missing/default, or its `sslmode` is not `require`, `verify-ca` or `verify-full` (NFR-7);
  - `JWT_SECRET` missing, the local default, shorter than 32 characters, or with fewer than 8 distinct characters;
  - `RESEND_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` missing (new settings `supabase_url`, `supabase_service_role_key`, empty default, unused until `platform/storage`);
  - `EMAIL_FROM` or `PUBLIC_BASE_URL` at the local default; `PUBLIC_BASE_URL` not `https://`;
  - `BOOTSTRAP_ADMIN_EMAILS` empty, or any non-empty entry not shaped like an address (one `@`, dotted domain, no whitespace);
  - `BCRYPT_ROUNDS` below 12; any `*_RATE_LIMIT_PER_*` setting above ten times its built-in default (the compose file's raised limits);
  - `TRUSTED_PROXY_CIDRS` containing a network with prefix length 0.
  The message is `Refusing to start with APP_ENV=production: missing, default or unsafe value for A, B` and never contains a value.
- The api (import of `app.main`), `worker-ai` and `worker-batch` refuse before opening a connection; a test starts each real process command in a subprocess with `APP_ENV=production`, a full valid secret set minus one, and asserts a non-zero exit and the variable's name on stderr.
- Client IP: Caddy (`servers { trusted_proxies static private_ranges 100.0.0.0/8; client_ip_headers X-Real-IP }`) resolves `{client_ip}` — the edge's `X-Real-IP` only when the peer is a trusted proxy, else the socket peer — and sends it to `backend` as the sole `X-Forwarded-For` value (`header_up X-Forwarded-For {client_ip}`, `header_up -X-Real-IP`). `ratelimit.client_ip` uses the last `X-Forwarded-For` entry only when the socket peer is inside `TRUSTED_PROXY_CIDRS` (setting `trusted_proxy_cidrs`, default loopback + RFC 1918 + `100.64.0.0/10` + `fc00::/7`) and the entry parses as an IP; otherwise the peer.
- Dev mailbox (`/api/dev/*`) is not mounted and the demo seed does not run in production — existing tests kept; the guard additionally blocks the local raised limits and low bcrypt cost.
- `docs/ops/connection-budget.md`: per process SQLAlchemy `DB_POOL_SIZE` with `max_overflow=0`, procrastinate pool (`concurrency + 1`, today 2), one LISTEN connection reserved for `backend`, one migration connection during a deploy, total, doubled for overlap, the pooler pool size it needs, and the formula to redo it.
- `scripts/smoke BASE_URL [--watch SECONDS] [--interval S]` (stdlib Python 3, executable): checks `GET /api/health` → 200 with `{"status":"ok"}`, `GET /print/smoke` → 404 without a Next.js body, `GET /` → 200 HTML with `/_next/`; prints every failed request with a UTC timestamp as it happens; with `--watch` repeats until the time is up; exit 0 only if no request failed. CI's `e2e` job runs it against the compose stack.
- `.env.example` lists every new variable name, no values; SETUP-GUIDE-style docs stay names only.

**Never:** no cloud account, login, deploy or call to a production service; no secret or real-looking key in any file; no `.env` read or edit; no change to `sprint-status.yaml`; no guard message that echoes a value; no new runtime dependency.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Full prod set | all required vars valid, `sslmode=require` | settings load | — |
| One missing | each required var removed in turn | `ConfigError` naming it | process exits ≠ 0 |
| Weak JWT | `JWT_SECRET=aaaa…` (40×a) or 20 chars | names `JWT_SECRET` | — |
| No TLS | `DATABASE_URL` without `sslmode` / `sslmode=prefer` | names `DATABASE_URL` | — |
| Raised limit | `PASSWORD_RESET_RATE_LIMIT_PER_IP=10000` | names it | — |
| Bad bootstrap | `BOOTSTRAP_ADMIN_EMAILS=ola` | names it | — |
| Local | `APP_ENV=local`, nothing set | loads with defaults | — |
| XFF from proxy | peer `10.1.2.3`, XFF `192.0.2.44` | `192.0.2.44` | — |
| XFF from outside | peer `203.0.113.7`, XFF `192.0.2.44` | `203.0.113.7` | — |
| Junk XFF | peer `10.1.2.3`, XFF `not-an-ip` | `10.1.2.3` | — |
| Smoke, good stack | compose up | three checks pass, exit 0 | — |
| Smoke, broken | `/print/x` served 200 | failure line, exit 1 | — |

</intent-contract>

## Code Map

- `backend/app/platform/config.py` -- `PRODUCTION_REQUIRED` (L20) and `check_production` (L106) to replace; `load_settings` raises `ConfigError` (SystemExit). Rate-limit fields L59-81, `bcrypt_rounds` L56, `bootstrap_admin_emails` L84, mail L88-90.
- `backend/app/main.py` -- `get_settings()` at import (L105) runs the guard before uvicorn binds; dev mailbox mounted only outside production (L87); bootstrap invitations at startup (L44).
- `backend/app/worker.py` -- `main()` calls `get_settings()` (L78) before any connection.
- `backend/app/platform/ratelimit.py` -- `client_ip` (L112); callers in `modules/identity/routes.py` (6 sites, unchanged).
- `backend/app/platform/db.py` -- engine `pool_size=DB_POOL_SIZE`, `max_overflow=0`; `platform/jobs/__init__.py` `_connector` pool `max(2, concurrency+1)`; `migrations/env.py` uses the same URL (NullPool).
- `backend/app/modules/identity/seed.py` (local only), `modules/messaging/routes.py` (dev mailbox) -- already production-safe; tests `tests/identity/test_seed.py::test_production_never_seeds`, `tests/messaging/test_dev_mailbox.py::test_it_is_not_routed_in_production`.
- Tests that set `APP_ENV=production` and then load settings (must get a valid production env or a bypass fixture): `tests/ai/test_gateway.py` L266/L299, `tests/identity/test_invitation_accept.py` L414/L437, `tests/identity/test_seed.py` L43, `tests/messaging/test_cli.py` L38, `tests/messaging/test_dev_mailbox.py` L37, `tests/test_sim_endpoint.py` L97/L109, `tests/messaging/test_delivery.py` L200.
- `backend/tests/identity/test_ratelimit.py` L82 and `tests/identity/test_login.py` L200 -- XFF tests; `helpers.client(ip)` default peer `203.0.113.7` (public).
- `backend/tests/test_config.py`, `tests/test_proxy_config.py` (Caddyfile parsing helpers) -- extend.
- `proxy/Caddyfile`, `proxy/Dockerfile`, `docker-compose.yml`, `backend/Dockerfile`, `backend/docker-entrypoint.sh`, `frontend/Dockerfile` (`node server.js`, `poweredByHeader: false` so `/` is recognised by `/_next/`), `.github/workflows/ci.yml` (`e2e` job), `.env.example`.

## Tasks & Acceptance

**Execution:**
- `backend/app/platform/config.py` -- new settings (`supabase_url`, `supabase_service_role_key`, `trusted_proxy_cidrs`), `production_problems()`, message -- AD-17, NFR-7.
- `backend/app/platform/ratelimit.py` -- trusted-peer `client_ip` -- Story 3.2 deferral.
- `backend/tests/conftest.py` -- `production` fixture (sets `APP_ENV=production`, bypasses the guard via `config.production_problems`, clears caches) for tests that test other production behaviour; update the tests listed in the Code Map to use it.
- `backend/tests/test_config.py` -- every matrix guard row; `backend/tests/test_production_startup.py` (new) -- three subprocess starts; `tests/identity/test_ratelimit.py`, `tests/identity/test_login.py` -- XFF rows.
- `proxy/Caddyfile`; `backend/tests/test_proxy_config.py` -- trusted proxies, client IP header.
- `backend/docker-entrypoint.sh` -- production skips migrations.
- `railway/*/railway.toml` (5 new); `backend/tests/test_railway_config.py` (new) -- AC 1 checked with `tomllib`.
- `docs/ops/connection-budget.md` (new).
- `scripts/smoke` (new); `backend/tests/test_smoke_script.py` (new, against an in-process stub server); `.github/workflows/ci.yml` -- run it in `e2e`.
- `.env.example` -- new names.

**Acceptance Criteria:**
- Given `railway/`, then each of the five services has a `railway.toml` as in Always, and only `backend` has a pre-deploy command.
- Given `APP_ENV=production` and one required secret removed, when the api, `worker-ai` or `worker-batch` command starts, then it exits non-zero naming the variable.
- Given the compose stack, when `scripts/smoke http://127.0.0.1:8080` runs, then it passes; CI runs it.
- Given `docs/ops/connection-budget.md`, then it holds the per-process table, the doubled total and the pooler size.
- Given the full suites, then everything passes and no new test takes over 1 s except the subprocess start test (reported).

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 43 findings — high 0, medium 1, low 25, false 9, maybe-false 8
- note: the four reviewers ran as background subagents (the run's brief); their final reports were read from their transcripts once each had ended its turn.
- findings:
  - Blind Hunter:
    - `[false]` `reject` Two sweepers during the worker-batch overlap. procrastinate defers each periodic tick once (unique `task_name, periodic_id, defer_timestamp` in `procrastinate_periodic_defers`); the toml comment now says so.
    - `[low]` `reject` Caddy trusts all of 100.0.0.0/8. Public traffic reaches Caddy only through Railway's edge; a peer outside it exists only inside Railway. Narrowing risks distrusting the edge itself (Railway's guide uses /8). Covered by the first deferred item.
    - `[maybe-false]` `defer` Backend binds IPv4 only. Third deferred item: new environments have IPv4 private networking.
    - `[low]` `patch` IPv4-mapped peers not trusted. `client_ip` maps `::ffff:a.b.c.d` to IPv4 before the check; test added.
    - `[low]` `reject` Guard accepts a split-halves list (0.0.0.0/1). Deliberate misconfiguration only; a prefix threshold would refuse the default `fc00::/7`.
    - `[low]` `patch` Empty TRUSTED_PROXY_CIDRS passes. Production refuses an empty list; test row added.
    - `[low]` `patch` Smoke crashes on HTTPException. Catches `http.client.HTTPException` and `ValueError`; malformed-answer and scheme-less tests added.
    - `[low]` `reject` Smoke does not check forged headers or the dev mailbox. Outside the AC's three rules; the forged-header case cannot be observed from outside (first deferred item); the mailbox is tested in-process.
    - `[low]` `reject` Smoke follows redirects. A redirected health check must still return `{"status":"ok"}`; a redirected `/` still lands on a frontend page.
    - `[false]` `reject` Services deploy from different commits. Only a change under `/railway/<service>/**` redeploys one service alone, and then `backend/` is identical in both commits, so the code is the same (AD-24 holds).
    - `[low]` `patch` `.dockerignore` changes trigger no redeploy. `/.dockerignore` added to every service's watchPatterns; test updated.
    - `[low]` `reject` `.dockerignore` blocks secrets by `.env` name only. backend and proxy copy named paths; frontend ships only the `.next` output from its build stage.
    - `[false]` `reject` Entrypoint safeguard may not run on Railway. If Railway's start command bypasses the entrypoint, nothing migrates at start either, which is the wanted outcome; otherwise the new default applies.
    - `[low]` `patch` Startup test can leave processes running. All three are killed in `finally` before asserting; the env-inheritance part rejected (the guard still names the removed variable).
    - `[low]` `reject` `enter_production` hides the guard. Deliberate (Design Notes): the guard is tested without bypass in `test_config.py` and the subprocess test.
    - `[low]` `reject` PGSSLMODE not seen. Fails closed with `DATABASE_URL` named; the toml comment says to put `sslmode=require` in the URL.
    - `[false]` `reject` Budget undercounts. backend defers on the request's session (`jobs.defer`), so 0 procrastinate pool is right; a restarted process has released its connections; 15 is SETUP-GUIDE §5's figure.
  - Edge Case Hunter:
    - `[low]` `patch` IPv4-mapped peer (same entry as Blind Hunter).
    - `[medium]` `patch` IPv6 client steps through its /64 to bypass per-IP limits. IPv6 addresses now count as their /64; test added.
    - `[maybe-false]` `defer` Trusted hop without X-Real-IP gives every client the edge address. First deferred item.
    - `[low]` `reject` 100.0.0.0/8 (same as Blind Hunter).
    - `[low]` `reject` Split-halves list (same as Blind Hunter).
    - `[low]` `patch` `PUBLIC_BASE_URL=https://` with no host. Guard requires scheme https and a host; test row added.
    - `[low]` `patch` `EMAIL_FROM` arbitrary text. Guard parses the address and applies the address rule; test rows added.
    - `[false]` `reject` Uppercase `sslmode=REQUIRE` refused. libpq accepts only lower-case sslmode values, so refusing is right; PGSSLMODE as Blind Hunter.
    - `[low]` `patch` Scheme-less base URL crashes smoke (same entry as HTTPException).
    - `[low]` `patch` Malformed response aborts watch (same entry).
    - `[low]` `reject` Negative `--interval`. Operator typo that fails loudly at once.
    - `[low]` `patch` Startup test leaves processes (same entry as Blind Hunter).
    - `[low]` `reject` IndexError instead of an assertion message in the compose test. Cosmetic.
  - Intent Alignment (divergences):
    - `[false]` `reject` Guard wider than the AC's five variables. The run's brief asks for BOOTSTRAP_ADMIN_EMAILS, the raised limits and a weak JWT_SECRET.
    - `[low]` `reject` DATABASE_URL and SUPABASE_URL never removed from a started process. The AC asks for each process with one secret removed; every variable is removed in-process in `test_config.py`.
    - `[low]` `reject` No test passes the real guard and shows production behaviour. Needs a TLS database locally; deliberate (Design Notes).
    - `[maybe-false]` `defer` Client IP behind Railway unverified. First deferred item. Sibling services as trusted peers are this repo's own code.
    - `[maybe-false]` `defer` Railway's parser, region id and config path not exercised. Second deferred item.
    - `[false]` `reject` Start commands differ from SETUP-GUIDE. Only flags the images already use and the queues that exist today; documented in the toml.
    - `[false]` `reject` Workers have no health check path. They serve no HTTP; Railway restarts them on exit.
    - `[maybe-false]` `reject` TLS read as a URL check, not forced in connect args. A fail-closed refusal naming the variable gives the same outcome.
    - `[maybe-false]` `reject` Smoke `--watch` not run against a real deploy. No deploy in this story; Story 3.15 runs it.
    - `[maybe-false]` `reject` Repo-root build context goes beyond the story. Needed for `dockerfilePath = "backend/Dockerfile"` and repo-root watchPatterns; compose, the smoke run and Playwright pass on the rebuilt images.
    - `[false]` `reject` No account or deploy taken. Conforms to the brief.
  - Verification Gap:
    - `[low]` `patch` Production branch of `docker-entrypoint.sh` untested. New `tests/test_entrypoint.py` runs the script with a stub `alembic` for local, production, production with `RUN_MIGRATIONS=true`, and `RUN_MIGRATIONS=false`.
    - `[maybe-false]` `defer` Caddy's client-IP rule pinned only by source text. A manual runtime check ran locally (an echo upstream behind the real proxy image): a client `X-Forwarded-For: 6.6.6.6` was replaced, `X-Real-IP` from a trusted peer arrived as the one `X-Forwarded-For`, and `X-Real-IP` was stripped. The untrusted-peer case cannot be made locally: first deferred item.

## Design Notes

- **Client IP, decided:** Railway's edge overwrites `X-Real-IP` with the caller's address on public requests; Railway publishes no edge CIDR, and its own Caddy guide trusts `private_ranges 100.0.0.0/8`. So Caddy is the one trust boundary: it reads `X-Real-IP` only from those peers and hands `backend` exactly one value. `backend` is not public, but it still ignores `X-Forwarded-For` from a non-private peer, so a request that reached it some other way cannot pick its address. Residual risk (for 3.15): if the edge's hop is outside those ranges, every caller shares one bucket — the smoke run in production should check a login 429 does not hit two different clients.
- **Guard bypass in tests:** tests of production behaviour (no mock AI, no dev mailbox, bootstrap) run against the local test database without TLS, so they patch the guard rather than fake a TLS URL; the guard itself is tested without bypass.
- **Railway config-as-code** is marked deprecated in Railway's docs (existing files honoured until 2026-12-01) in favour of «Infrastructure as Code»; the AC asks for `railway.toml`, so they are written and the 3.15 runbook must check whether the project needs the IaC form instead.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/test_config.py tests/test_production_startup.py tests/test_railway_config.py tests/test_smoke_script.py tests/test_proxy_config.py tests/identity/test_ratelimit.py` -- expected: pass
- `cd backend && uv run pytest --durations=15 && uv run ruff check . && uv run ruff format --check .` -- expected: pass
- `docker compose up -d --build --wait proxy && python scripts/smoke http://127.0.0.1:8080` -- expected: exit 0


## Auto Run Result

Status: done

**Summary.** The repo now holds a strict production configuration, with no account touched. `railway/<service>/railway.toml` exists for `proxy`, `frontend`, `backend`, `worker-ai` and `worker-batch`. Each file sets:
- a Dockerfile builder from the repo root (the three Python services all use `backend/Dockerfile`);
- EU West (`europe-west4-drams3a`) with one replica;
- the start commands of SETUP-GUIDE §1 (worker-batch with today's queues);
- health checks (`/api/health` for backend and proxy, `/` for frontend);
- watchPatterns, overlap and draining seconds, and restart on failure.

Only `backend` has `preDeployCommand = ["alembic upgrade head"]`, and the image's entrypoint no longer migrates under `APP_ENV=production`.

The AD-17 guard stops the api and both workers from starting. Its message names every bad variable and never a value. It refuses when:
- `DATABASE_URL` is the default or lacks `sslmode=require|verify-ca|verify-full`;
- `JWT_SECRET` is missing, the default, shorter than 32 characters, or has fewer than 8 distinct characters;
- `RESEND_API_KEY`, `SUPABASE_URL` or `SUPABASE_SERVICE_ROLE_KEY` is missing;
- `BOOTSTRAP_ADMIN_EMAILS` is empty or malformed;
- `EMAIL_FROM` is the local default or not an address;
- `PUBLIC_BASE_URL` is not https with a host;
- `BCRYPT_ROUNDS` is below 12;
- a per-IP or per-account rate limit is above ten times its default (the compose file's raised limits);
- `TRUSTED_PROXY_CIDRS` is empty or contains a /0.

The dev mailbox and the demo seed were already off in production, and their tests stay.

Client IP: Caddy believes Railway's `X-Real-IP` only from `private_ranges 100.0.0.0/8`, and sends the result as the only `X-Forwarded-For`. The api believes that header only from a peer in `TRUSTED_PROXY_CIDRS` (private ranges, 100.64/10, fc00::/7). It maps IPv4-mapped addresses to IPv4 and counts each IPv6 client per /64.

`docs/ops/connection-budget.md` gives 25 connections per deploy, 51 during an overlap including the migration, and the formula. `scripts/smoke` checks the three proxy rules and prints each failed request with a UTC time. It can `--watch` a deploy, and CI runs it against compose.

**Implementation note.** The run's brief said to implement in this context, not through a step-03 subagent; only the review used subagents.

**Files changed:**
- `backend/app/platform/config.py` (guard, storage keys, trusted proxies) and `backend/app/platform/ratelimit.py` (`client_ip`).
- `backend/docker-entrypoint.sh`.
- `backend/Dockerfile`, `frontend/Dockerfile`, `proxy/Dockerfile` and `docker-compose.yml` (repo-root build context).
- Root `.dockerignore`, which replaces `backend/.dockerignore` and `frontend/.dockerignore`.
- `proxy/Caddyfile`.
- `railway/*/railway.toml` (5 new).
- `docs/ops/connection-budget.md` (new).
- `scripts/smoke` (new, executable).
- `.github/workflows/ci.yml` (smoke step).
- `.env.example`.
- New tests: `test_production_startup.py`, `test_railway_config.py`, `test_smoke_script.py`, `test_entrypoint.py`.
- Changed tests: `test_config.py`, `test_proxy_config.py`, `identity/test_ratelimit.py`, `identity/test_login.py`, and `conftest.py` (`enter_production`).
- Production-behaviour tests moved onto `enter_production`: `ai/test_gateway.py`, `ai/test_effort.py`, `identity/test_invitation_accept.py`, `identity/test_seed.py`, `messaging/test_cli.py`, `messaging/test_delivery.py`, `messaging/test_dev_mailbox.py`, `test_sim_endpoint.py`.

**Review.** 43 findings: 0 high, 1 medium, 25 low, 9 false, 8 maybe-false.
- Patched: the medium entry (the IPv6 /64 key) and these low entries: IPv4-mapped peers, an empty trusted list, the `PUBLIC_BASE_URL` host, the `EMAIL_FROM` address, smoke robustness, the `.dockerignore` watch pattern, startup-test cleanup, and the entrypoint test.
- Deferred to Story 3.15, all medium and unverified: the client-IP chain behind Railway's edge, how Railway parses the toml files, and IPv4 private networking.
- Every rejection has its reason in the triage log.

**Follow-up review recommended: false.** Patched: 0 high, 1 medium entry, 8 low entries.

**Verification:**
- Backend `pytest`: 1962 passed in 65 s; ruff check and format are clean. One new test takes over 1 s: `test_production_startup.py`, at about 2 s. It starts three real processes in parallel, which costs one interpreter start with the app's imports. All other new tests take under 0.2 s.
- The stack was rebuilt with the repo-root build context (`docker compose up -d --build --wait proxy worker-batch`). On it:
  - `scripts/smoke http://127.0.0.1:8080` passes, also with `--watch 4`;
  - Playwright `logg-inn.spec.ts` and `landing.spec.ts` pass 19/19;
  - `caddy validate` passes on the new Caddyfile.
- `docker compose run backend` with `APP_ENV=production` refuses to start, and the variables it names include the compose file's raised limits and bcrypt cost. With `APP_ENV=production` the entrypoint skips migrations.
- A local runtime check of the proxy's client IP, with an echo upstream:
  - a forged `X-Forwarded-For` was replaced;
  - a trusted `X-Real-IP` arrived as the only `X-Forwarded-For`;
  - `X-Real-IP` was stripped.
- No migration was added, and the shared test databases were not changed.

**Decisions taken in place of the founder:**
- Client IP: Caddy is the trust boundary. It reads `X-Real-IP` from `private_ranges 100.0.0.0/8`, the range in Railway's guide, since Railway publishes no edge range. The api trusts `X-Forwarded-For` only from private peers (`TRUSTED_PROXY_CIDRS`) and keys IPv6 clients per /64.
- `JWT_SECRET` counts as weak below 32 characters or 8 distinct characters. `BCRYPT_ROUNDS` must be at least 12 in production.
- A rate limit above ten times its built-in default is refused in production, which catches the local raised limits. Tuning up to that point is allowed.
- `BOOTSTRAP_ADMIN_EMAILS`, `EMAIL_FROM` and an https `PUBLIC_BASE_URL` are required in production.
- TLS is required by refusing a `DATABASE_URL` without `sslmode=require` or stricter. `PGSSLMODE` is not read.
- Every image builds from the repo root with one root `.dockerignore`, so `dockerfilePath` and `watchPatterns` are repo-root paths. The service settings point at `/railway/<service>/railway.toml`.
- worker-batch runs today's queues (`llm-batch,mail`); the report queues come with their epic. Workers run with concurrency 1, and the budget doc shows how a higher value raises the pool.
- Overlap and draining seconds:

  | Service | Overlap | Draining |
  | --- | --- | --- |
  | proxy | 30 | 30 |
  | frontend | 30 | 30 |
  | backend | 60 | 30 |
  | worker-ai | 30 | 60 |
  | worker-batch | 30 | 120 |
- Production-behaviour tests set the guard aside (`enter_production`), since the local test database has no TLS.

**For Story 3.15 (needs accounts):**
1. Create the services from these files and check the three deferred items.
2. Set the variables named in each toml header: `API_UPSTREAM=backend.railway.internal:8000`, `WEB_UPSTREAM=frontend.railway.internal:3000`, `API_INTERNAL_URL=http://backend.railway.internal:8000`, and the secrets.
3. Set the Supabase pooler pool size to at least 51, or lower `DB_POOL_SIZE` as the budget shows.
4. Run `scripts/smoke https://<domain> --watch 600` across a second deploy.
5. Remove one secret from one service once and record the refusal.

**Residual risks:**
- Railway marks config-as-code as deprecated, so the files may need the IaC form.
- The client-IP rule depends on Railway's edge setting `X-Real-IP` from a hop inside the trusted ranges.
