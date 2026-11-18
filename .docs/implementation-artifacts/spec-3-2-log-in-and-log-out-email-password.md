---
title: 'Story 3.2: Log in and log out with e-mail and password'
type: 'feature'
created: '2026-11-18'
status: 'done'
baseline_revision: '2b314f063cbe74e3ed62983cc7a49ca8000f8b85'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-3-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-3-1-see-logg-inn-in-product-design.md'
warnings: [oversized]
deferred:
  - summary: >-
      Production can start with the repo's default JWT_SECRET, so anyone could forge a session.
    evidence: |-
      config.py has a local default for jwt_secret, and PRODUCTION_REQUIRED does not list it yet. epics.md puts the JWT_SECRET production guard in Story 3.14, and the production deploy (3.15) comes after it. The README now says to set it outside local.
    location: >-
      backend/app/platform/config.py
    severity: medium
  - summary: >-
      client_ip trusts the last X-Forwarded-For entry with no trusted-proxy check, and on Railway Caddy's peer may be the platform edge.
    evidence: |-
      Locally only Caddy reaches the backend (no published port), and Caddy replaces an untrusted header. In production, if Caddy's peer is Railway's edge, every client shares one IP for the per-IP limit. Unless Caddy's trusted_proxies is set, a reachable backend lets a client choose its own IP. Settle it with the production proxy config in Story 3.14.
    location: >-
      backend/app/platform/ratelimit.py (client_ip), proxy/Caddyfile
    severity: medium
---

<intent-contract>

## Intent

**Problem:** «Logg inn» validates but sends nothing. There are no accounts, no session, no CSRF guard, no rate limit, no typed API client and no server-state layer, and every later story needs them. Later Playwright tests and visual checks also need a known login per Role.

**Approach:** The `identity` module gets `users` and `user_roles`. `platform/auth` hashes passwords (SHA-256 → base64 → bcrypt) and issues an HS256 JWT cookie. `platform/ratelimit` counts failed logins in Postgres, per IP and per account. A CSRF middleware requires `X-Requested-With: olspillet` on every mutation. The web app gets a generated `openapi-fetch` client and one TanStack `QueryClient`, and the form logs in through a mutation. A local-only seed adds a demo Admin and a demo Lecturer, and a shared e2e helper logs in as either.

## Boundaries & Constraints

**Always:**
- API routes: `POST /api/auth/login` (`{email, password}` → 200 `{user}` and `Set-Cookie`), `POST /api/auth/logout` (204, clears the cookie, needs no session) and `GET /api/auth/me` (200 `{user}` or 401 `not_authenticated`). `user` is `{id, name, email, roles}`.
- E-mail is matched trimmed and lower-cased. `users.email` is stored lower-case, with `CHECK (email = lower(email))` and `UNIQUE (email)`. Roles are `admin` and `lecturer` (CHECK).
- Cookie `olspillet_session`: `HttpOnly; Secure; SameSite=Lax; Path=/`, with Max-Age = `SESSION_MAX_AGE_HOURS` (default 168). JWT claims: `user_id`, `iat`, `exp`. No name, e-mail or role.
- `GET /api/auth/me` loads the User and roles from the database on every call. An inactive User or a bad, expired or tampered token gives 401.
- Login: a deactivated User with the right password gets 403 `account_deactivated`. With a wrong password the answer is `invalid_credentials`, so existence is not revealed. An unknown e-mail still runs one bcrypt check against a dummy hash.
- Rate limit: fixed windows of `LOGIN_RATE_LIMIT_WINDOW_MINUTES` (default 15). The limits are `LOGIN_RATE_LIMIT_PER_IP` (default 300) and `LOGIN_RATE_LIMIT_PER_ACCOUNT` (default 5). Only failed logins count. A success resets that account's counter. Once a count reaches its limit, every attempt gets 429 `rate_limited` with `Retry-After`, and the password is not checked. Keys are stored as SHA-256 of `ip:<addr>` and `account:<email>`, never in plain text. Time comes from the app clock, passed in (injectable in tests).
- Client IP: the last `X-Forwarded-For` entry (the one Caddy writes), otherwise the socket peer.
- Hashing cost is `BCRYPT_ROUNDS` (default 12, minimum 4). The tests set 4.
- Errors use the AD-19 envelope. The web app maps `invalid_credentials`, `account_deactivated`, `rate_limited` and any other failure to `nb.ts` strings. They show in one `role="alert"` line above the button. Input is kept, and focus moves to the e-mail field.
- Logs carry `user_id` and `error_code` only. Never an e-mail, IP or password.
- Exact new versions, each at least two weeks old: PyJWT 2.15.1, bcrypt 5.0.0, openapi-fetch 0.17.0, @tanstack/react-query 5.105.3 (5.106+ are under two weeks old).

**Never:**
- No `platform/authz`, no homes and no role routing (Story 3.3). No Skjelett and no offline line (3.4). No password reset or Invitation (3.6–3.8). No production guard for `JWT_SECRET` (3.14).
- `app/platform` imports no `app.modules`. No seed outside `APP_ENV=local`.
- No edits to `sprint-status.yaml`, `.env` or `.claude/settings*.json`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Right login | Seeded Admin, right password, email in mixed case | 200, cookie set, web goes to `/`, which shows the User's name and «Logg ut» | — |
| Wrong password / unknown e-mail | Either | 401 `invalid_credentials`. The page shows «Feil e-post eller passord.» | The fields keep their values |
| Rate-limited | The account or IP count is at its limit | 429 `rate_limited` with `Retry-After`, even with the right password | «For mange forsøk. Vent noen minutter og prøv igjen.» |
| Deactivated | `is_active=false`, right password | 403 `account_deactivated` | The `deactivated` string |
| No CSRF header | POST/PUT/PATCH/DELETE under `/api` without the header (except `/api/webhooks/*`) | 403 `csrf_header_missing`, and the handler does not run | — |
| Logout | «Logg ut» pressed | 204, cookie cleared, web goes to `/logg-inn`. `/api/auth/me` then gives 401 | — |
| Bad cookie | Tampered, expired or wrong-secret JWT, or the User is gone or inactive | `/api/auth/me` 401 `not_authenticated` | — |

</intent-contract>

## Code Map

- `backend/app/main.py` -- `create_app()` and `error_response()` (the AD-19 envelope), with the lifespan running the AI seed. Include the identity router, add the CSRF middleware, and call the identity seed in the lifespan, logged and never raised (like `app/ai/seed.py:71`).
- `backend/app/platform/config.py` -- Settings. Add `jwt_secret` (local default, guard deferred to 3.14), `session_max_age_hours`, `bcrypt_rounds` (ge=4), and the three `login_rate_limit_*` settings.
- `backend/app/platform/db.py` -- `metadata`, `get_sessionmaker()`. Tables register on `metadata`, as in `modules/games/models.py`.
- `backend/app/ai/db.py` -- `transaction(session)` pattern to copy.
- `backend/migrations/env.py` -- imports the model modules for `alembic check`. Add identity and ratelimit.
- `backend/migrations/versions/0014_*.py` -- latest revision. The new one is `0015`.
- `backend/tests/conftest.py` -- `test_database` is migrated once per session. Add `BCRYPT_ROUNDS=4` and an `identity_db` truncate fixture.
- `backend/tests/test_migrations.py` -- `HEAD`/`HEAD_TABLES`. Bump to 0015 and add a downgrade test.
- `backend/tests/test_imports.py:62` -- the platform-imports-no-module rule.
- `backend/tests/test_health.py` -- the ASGI client pattern for route tests.
- `backend/app/platform/logging.py` -- `ALLOWED_FIELDS`. `user_id` and `error_code` are already allowed.
- `frontend/src/modules/identity/login-form.tsx` -- the 3.1 form. Wire the mutation here.
- `frontend/src/copy/nb.ts` -- `auth.login.invalidCredentials` and `deactivated` exist. Add `rateLimited`, `failed`, and a `session` group (signed-in line, «Logg ut»).
- `frontend/src/components/{button,text-field}.tsx` -- reuse. `Button unavailable` while pending.
- `frontend/src/app/layout.tsx`, `src/app/page.tsx` -- the shell gets the provider. `/` is an empty `<main />` today.
- `frontend/e2e/logg-inn.spec.ts`, `playwright.config.ts` -- the 3.1 axe/viewport patterns.
- `.github/workflows/ci.yml` -- add an `api-client` drift job.

## Tasks & Acceptance

**Execution:**
- `backend/pyproject.toml`, `uv.lock` -- add `pyjwt==2.15.1` and `bcrypt==5.0.0`.
- `backend/app/platform/config.py` -- the new settings.
- `backend/app/platform/auth.py` -- `hash_password`, `verify_password`, `DUMMY_HASH`, `issue_token(user_id, now)`, `read_token(token, now) -> UUID|None`, `set_session_cookie`, `clear_session_cookie`, and `CsrfMiddleware` (a pure ASGI middleware).
- `backend/app/platform/ratelimit.py` -- the `rate_limit_counters` table (bucket, key_hash, window_start, count; PK of the first three), `client_ip(request)`, `check(session, bucket, key, limit, window, now) -> retry_after|None`, `hit(...)` and `reset(...)`. Old windows for the same key are deleted on hit.
- `backend/app/modules/identity/{__init__,models,schemas,repo,service,routes,seed}.py` -- the tables, the `UserOut`/`LoginIn` schemas, the queries, and `authenticate`, `create_user` and `current_user`. Also the three routes, and `ensure_demo_users()` (local only, empty `users` table, advisory lock).
- `backend/migrations/versions/0015_identity_users_ratelimit.py`, `migrations/env.py` -- the three tables.
- `backend/app/main.py` -- router, middleware and seed.
- `backend/app/openapi.py` -- `python -m app.openapi` prints the schema JSON (sorted, stable).
- `backend/tests/identity/` -- tests for hashing (including >72-byte passwords), the token (tamper, expiry, wrong secret), every matrix row through the ASGI app, the rate limit with an injected clock, the seed (local only, idempotent, no-op in test), and CSRF. Also update `test_migrations.py` and `conftest.py`.
- `frontend/package.json`, `package-lock.json` -- openapi-fetch and @tanstack/react-query (pin `@tanstack/query-core` with an override). Add the `api:generate` script.
- `frontend/src/lib/api/{openapi.json,schema.ts,client.ts}` -- the committed schema and the generated types. `client.ts` adds `X-Requested-With: olspillet` to every non-GET/HEAD request, with credentials `same-origin`.
- `frontend/src/app/providers.tsx`, `layout.tsx` -- one `QueryClient` provider.
- `frontend/src/modules/identity/{api.ts,login-errors.ts,login-form.tsx,signed-in.tsx,logout-button.tsx}`, `src/app/page.tsx` -- the `useLogin`, `useMe` and `useLogout` hooks, the code-to-copy map, the form wiring, and `/` showing the signed-in placeholder when `me` succeeds.
- `frontend/src/copy/nb.ts` -- the new strings, marked `[ASSUMPTION]`.
- Vitest -- the client header middleware and the error mapping.
- `frontend/e2e/support/auth.ts`, `frontend/e2e/login-flow.spec.ts` -- `DEMO_USERS` and `loginAs(page, role)`. The flow at 320, 360 and 1440 by keyboard with axe: wrong password, rate-limited, right password, «Logg ut».
- `.github/workflows/ci.yml` -- an `api-client` job that runs `uv run python -m app.openapi`, then `npm run api:generate`, then `git diff --exit-code frontend/src/lib/api`.
- `README.md` -- demo logins, the e2e helper, the API client regeneration and the rate-limit variables.

**Acceptance Criteria:**
- Given an empty database and `APP_ENV=local`, when the backend starts, then exactly one demo Admin and one demo Lecturer exist. With any other `APP_ENV`, or with users present, nothing is added.
- Given revision 0015, when it runs, then it adds `users`, `user_roles` and `rate_limit_counters` only, `alembic check` passes, and downgrade to 0014 removes them.
- Given a mutating `/api` request without `X-Requested-With: olspillet`, when it is sent, then it gets 403 `csrf_header_missing`. The generated client sends the header on every mutation.
- Given the stack at `http://127.0.0.1:8080`, when Playwright runs the login flow at 320, 360 and 1440 px by keyboard alone, then wrong password, rate-limited, right password and «Logg ut» behave as in the matrix, and axe reports no WCAG 2.1 AA violation in any state.
- Given the backend schema changes, when the CI `api-client` job regenerates the client, then it fails on any difference.

## Design Notes

- **Where a logged-in User lands.** Story 3.3 owns the homes. Until then, `/` shows a signed-in placeholder: the product header with «Logg ut» (secondary, because logging out commits nothing irreversible), and an h1 with the User's name. Anonymous `/` stays empty until the Landing (3.13).
- **Deactivated copy.** It is shown only after a correct password, so it reveals nothing to someone who does not hold the password. This settles the 3.1 deferral. The staff wording («faglæreren din») stays with Issue #31.
- **Per-IP default 300.** A whole class behind one NAT logs in at once, so the IP limit must stay well above class size. The account limit stops guessing.
- **Test login.** `admin@example.com` and `faglaerer@example.com`, password `olspillet-demo`. RFC 2606 domain, local seed only.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/identity tests/test_migrations.py tests/test_config.py tests/test_imports.py` -- expected: pass
- `cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check .` -- expected: pass
- `cd frontend && npm run typecheck && npx vitest run && npm run check:copy && npm run build` -- expected: pass
- `docker compose up -d --build --wait proxy && cd frontend && npx playwright test` -- expected: pass, each test under about 1 s per viewport

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 41 findings — high 0, medium 5, low 33, false 3, maybe-false 0
- findings:
  - Blind Hunter:
    - `[medium]` `patch` Parallel guesses passed `check` before any `hit`, so the account limit could be beaten. Patch: each attempt is counted first, in one atomic upsert (`ratelimit.hit`), and refused when the count passes the limit. A successful attempt is given back (`give_back` on the IP) and resets the account. Tested with 11 parallel `authenticate` calls, and with parallel `hit`s that each get their own count.
    - `[low]` `reject` Anyone can lock an account for 15 minutes with five wrong passwords. The AC requires a per-account limit. The window is short, and a success resets it. Keying on account plus IP would weaken the limit the AC asks for.
    - `[medium]` `defer` The production guard for `JWT_SECRET` is missing. epics.md assigns it to Story 3.14, and the README now says to set the secret outside local (see `deferred`).
    - `[medium]` `defer` `client_ip` trusts `X-Forwarded-For`. The backend is not reachable except through Caddy, and Caddy replaces an untrusted header. The production proxy setup is Story 3.14 (see `deferred`).
    - `[low]` `reject` Logout cannot revoke a copied token. AD-11 chose a stateless JWT, and deactivation blocks it. This is now stated in the README.
    - `[low]` `patch` The generated files were missing from the diff, and the CI drift check ignored untracked files. The files were deliberately left out of the staged diff and are committed, and `openapi-typescript` was already a devDependency (3.1). The CI half is real. Patch: the job fails on `git status --porcelain` output for `frontend/src/lib/api`, which covers new and deleted files.
    - `[low]` `reject` An anonymous `/`, a failing `useMe` and an expired session show a blank page. Story 3.4 owns the system states and session-expired. The Landing is 3.13.
    - `[low]` `reject` `users.updated_at` never changes. Nothing updates a User yet. The first story that does (3.6, 3.9 or 3.10) sets it.
    - `[low]` `patch` The seed error test asserted nothing. Patch: it captures the logs and asserts `demo_users_failed` with `db_error`. The settings-cache-leak part is false, because the autouse `_fresh_settings` clears the cache before and after every test.
    - `[low]` `reject` Coverage gaps: Retry-After for the IP limit, a malformed-JSON field key, and component tests for the form, logout and SignedIn. The behaviours are covered end to end by Playwright (server error line, focus, logout). The rest is rare and cosmetic. Logout without a session is already tested in `test_csrf.py`.
    - `[low]` `patch` WebKit may drop a `Secure` cookie on http loopback. Patch: a README note to log in locally with Chromium or Firefox. Playwright runs Chromium only.
    - `[low]` `reject` The form ignores `Retry-After`. A minute count would need a copy function in `nb.ts` and a copy review. «Vent noen minutter» is concrete enough for a 15-minute window.
  - Edge Case Hunter:
    - `[medium]` `patch` The race between check and hit (the same root cause as the Blind Hunter's first row). Patched as above.
    - `[medium]` `defer` `X-Forwarded-For` without a trusted proxy (the same as the Blind Hunter row). Deferred.
    - `[low]` `patch` A signed token with an absurd `exp` or a numeric `user_id` raised OverflowError or AttributeError, which gives a 500. Patch: `read_token` catches OverflowError and OSError and accepts only a string `user_id`. Test added.
    - `[low]` `patch` The first `dummy_hash()` call hashed on the event loop. Patch: it is called through `asyncio.to_thread`.
    - `[low]` `patch` A deactivated User's right password reset the account count. Patch: the reset and give-back happen only for an active User. Test added.
    - `[low]` `reject` SignedIn shows nothing while loading or on error (Story 3.4's states).
    - `[low]` `reject` `fetchMe` does not wrap a network TypeError. No caller reads its error until 3.4.
    - `[low]` `reject` Logout does not wrap a network error. `LogoutButton` shows `logoutFailed` for any error.
    - `[low]` `patch` The Secure cookie on Safari (the same as the Blind Hunter row). README note.
    - `[low]` `patch` The CI drift check missed untracked files (the same as the Blind Hunter row). Patched.
    - `[low]` `reject` Repeated e2e runs reach the per-IP limit. Each run adds about 25 failures against 300 per 15 minutes, so a developer would need about 12 runs in one window.
    - `[low]` `reject` A test that fails midway locks the demo accounts. Every flow run logs in successfully, which resets the account, and the window is 15 minutes.
    - `[low]` `reject` Two validation errors on one joined key overwrite each other. That needs two errors at the same location. The developer message is enough.
    - `[false]` `reject` The query-core override was claimed but is missing. `@tanstack/react-query` 5.105.3 depends on `@tanstack/query-core` 5.105.3 exactly (npm ls), so nothing floats and no override is needed.
    - `[low]` `patch` The spec says "fails on any difference", but the job missed new files (a duplicate of the CI drift row). Patched.
    - `[low]` `patch` `DUMMY_HASH` is a lazily computed function, not a constant. Covered by the to_thread patch; the function is kept.
  - Verification Gap:
    - `[low]` `patch` Nothing tested that a refused CSRF request is still logged with its request id. Patch: `test_a_request_the_csrf_guard_refuses_is_logged_with_its_request_id` in `tests/test_logging.py`.
    - `[low]` `patch` Clearing the cache on logout was checked only after a full reload. Patch: the e2e flow uses `page.goBack()` after «Logg ut», then asserts that the name and «Logg ut» are gone.
  - Intent Alignment (descriptive divergences):
    - `[low]` `reject` No surface is gated by the session yet ("only I can reach my part"). Story 3.3 adds authz and the homes.
    - `[low]` `patch` Axe did not run after logout. Patch: `expectAccessible` on «Logg inn» after logout.
    - `[false]` `reject` The webhook CSRF exemption goes beyond the story. AD-11 names `/api/webhooks/*` as the one exemption, and the epic context repeats it.
    - `[low]` `reject` The JWT carries `iat` and `exp` beside `user_id`. They are registered time claims needed for expiry, and they hold no personal data. This decision is recorded.
    - `[low]` `reject` `account_deactivated` names an existing account. FR-3 and EXPERIENCE.md give that message. It shows only after the right password, so it reveals nothing to someone without the password (Design Notes).
    - `[low]` `reject` The rate-limited state is set up through the API. The ACs are judged on what the User does: the keyboard submission and the message. Fifty keyboard submissions would only slow the test.
    - `[low]` `reject` The seed is tested by direct call, not by starting compose. The e2e suite logs in with the seeded accounts on compose, which exercises the compose path.
    - `[low]` `patch` No test inserted e-mails that differ only in case. Patch: `test_two_emails_that_differ_only_in_case_are_one_account`, which checks both the unique constraint and the CHECK.
    - `[low]` `patch` The drift guard ignored untracked files (a duplicate). Patched.
    - `[false]` `reject` The copy is not "from Story 3.1". `invalidCredentials` and `deactivated` are 3.1's strings. The new strings cover codes 3.1 did not have, and they are marked `[ASSUMPTION]` for Issue #31.
    - `[low]` `reject` Compose sets `BCRYPT_ROUNDS=4`, and a 3.1 e2e assertion changed. The low cost is local only; the app's default (12) applies wherever it is not set. The 3.1 test asserted "valid input sends nothing", which this story's AC replaces with a login.

## Auto Run Result

Status: done

**Summary.** Accounts, login and logout:
- **Backend.**
  - `identity` gets `users` and `user_roles` (revision 0015).
  - `platform/auth`: SHA-256 → base64 → bcrypt, an HS256 JWT in an `HttpOnly; Secure; SameSite=Lax` cookie, and a CSRF middleware.
  - `platform/ratelimit`: Postgres fixed windows with hashed keys, counted atomically before the password check.
  - `/api/auth/login`, `/logout` and `/me` answer with AD-19 envelopes (`invalid_credentials`, `account_deactivated`, `rate_limited` with `Retry-After`, `not_authenticated`, `csrf_header_missing`, `invalid_request`).
  - A local-only demo seed.
- **Frontend.**
  - A generated `openapi-fetch` client that adds the CSRF header on mutations.
  - One TanStack `QueryClient`.
  - The login mutation wired into the 3.1 form.
  - A signed-in placeholder at `/` with «Logg ut».
- **Test login.**
  - `admin@example.com` (Admin) and `faglaerer@example.com` (Faglærer), password `olspillet-demo`. They are seeded only with `APP_ENV=local` on an empty `users` table.
  - `frontend/e2e/support/auth.ts` exports `DEMO_USERS`, `DEMO_PASSWORD`, `loginAs(page, role)` and `loginByApi(page, role)`.
  - Both are documented in `README.md`.

**Files changed:**
- `backend/app/platform/{auth,ratelimit,errors}.py`: the session, CSRF, rate limits and the error envelope.
- `backend/app/platform/config.py`: the JWT, session, bcrypt and rate-limit settings.
- `backend/app/modules/identity/{models,schemas,repo,service,routes,seed}.py`: accounts, login and the seed.
- `backend/app/main.py`: router, middleware, the 401 and 422 envelope handlers, and the seed at start.
- `backend/app/openapi.py`: schema export.
- `backend/migrations/versions/0015_identity_users_ratelimit.py`, `migrations/env.py`.
- `backend/pyproject.toml`, `uv.lock`: PyJWT 2.15.1 and bcrypt 5.0.0.
- `backend/tests/identity/*` (new), `tests/conftest.py` (`BCRYPT_ROUNDS=4`, `identity_db`), `tests/test_migrations.py` (head 0015), `tests/test_logging.py`.
- `frontend/src/lib/api/{openapi.json,schema.ts,client.ts,client.test.ts}`: the generated client.
- `frontend/src/app/{providers.tsx,layout.tsx,page.tsx}`: the QueryClient and `/`.
- `frontend/src/modules/identity/{api.ts,login-errors.ts,login-errors.test.ts,login-form.tsx,logout-button.tsx,signed-in.tsx}`.
- `frontend/src/copy/nb.ts`: `rateLimited`, `failed` and `session.*`, marked `[ASSUMPTION]`.
- `frontend/e2e/{login-flow.spec.ts,support/auth.ts}` (new). `logg-inn.spec.ts`: valid input now sends the login.
- `frontend/package.json`, `package-lock.json`: openapi-fetch 0.17.0, @tanstack/react-query 5.105.3, and the `api:generate` script.
- `.github/workflows/ci.yml`: the `api-client` drift job.
- `docker-compose.yml`: `BCRYPT_ROUNDS=4` for the local stack.
- `README.md`: demo logins, the e2e helper, the session and rate-limit settings, and API client regeneration.

**Review.**
- 41 findings: 18 patch rows, 13 distinct patches (1 medium and 12 low).
- 2 deferred (medium): the `JWT_SECRET` production guard, and trusted-proxy client IP. Both belong to Story 3.14.
- The other findings were rejected, with reasons in the triage log.

**Follow-up review recommended: false.** One medium entry was patched (the rate-limit race), and no high. The patch has unit and service-level concurrency tests.

**Verification:**
- Backend `uv run pytest`: 1599 passed in 67 s, with the compose stack running. `ruff check` and `ruff format --check` are clean.
- The new identity tests run in about 4.7 s with `-n0`. Every one is under 1 s. The slowest new test is the 0014 downgrade test at 0.7 s.
- Frontend:
  - `npm run typecheck`: passed.
  - Vitest: 197 passed.
  - `check:copy`: passed.
  - `npm run build`: the colour lint passed and the build succeeded.
- `docker compose up -d --build --wait proxy`, then `npx playwright test`: 15 passed. With one worker, these new tests are over 1 s:
  - each login-flow keyboard test: about 1.4 s (two logins, three axe runs and logout);
  - each rate-limited test: about 0.9 s.
- Regenerating `openapi.json` and `schema.ts` gives the committed files.
- Matrix audit:
  - right login: `test_the_right_login…` and the e2e flow;
  - wrong password and unknown e-mail: `test_a_wrong_login…` (both) and e2e;
  - rate-limited: `test_the_account_limit…`, the IP tests, the parallel test and e2e;
  - deactivated: `test_a_deactivated_user…` and `loginErrorMessage`;
  - no CSRF header: `test_csrf.py` and e2e;
  - logout: `test_logout_clears_the_cookie` and e2e;
  - bad cookie: the tampered, gone, expired and deactivated `/me` tests.

**Decisions taken in place of the founder:**
- **Routes.** `/api/auth/login`, `/logout` and `/me`. A logged-in User goes to `/`, which shows their name and «Logg ut» until Story 3.3 adds the homes.
- **Deactivated account.** It gets `account_deactivated` (403) only after the right password. With a wrong password the answer is `invalid_credentials`. This settles the 3.1 deferral; the staff wording stays with Issue #31.
- **E-mail.** Stored trimmed and lower-cased, with CHECK plus UNIQUE (no citext).
- **JWT.** The claims are `user_id`, `iat` and `exp`. The session lasts 168 h. The cookie is `olspillet_session`.
- **Rate-limit defaults.** 300 per IP and 5 per account per 15-minute fixed window, as placeholders. Every attempt counts, and a success gives back its IP count and resets the account. Keys are stored as SHA-256. The client IP is the last `X-Forwarded-For` entry.
- **Bcrypt cost.** 12, with 4 in the tests and the local compose stack.
- **Test login.** `admin@example.com` and `faglaerer@example.com` with `olspillet-demo`. The domain is RFC 2606.
- **New copy, marked `[ASSUMPTION]`.** «For mange forsøk. Vent noen minutter og prøv igjen.», «Innloggingen gikk ikke. Prøv igjen.», «Du er logget inn.», «Logg ut», «Utloggingen gikk ikke. Prøv igjen.»
- **Dependency pin.** @tanstack/react-query is pinned to 5.105.3, because 5.106+ are under two weeks old.
- **Deferred to Story 3.14.** The `JWT_SECRET` production guard.
- **Error envelopes.** Validation errors (422) answer in the AD-19 envelope as `invalid_request`, with field names only.
- **Who implemented it.** The implementation was done in the orchestrating context, not in a subagent, as the caller instructed. The review fixes were applied the same way.

**Residual risks:**
- The CI `api-client` and e2e jobs have not run on GitHub yet.
- The production client IP behind Railway is not settled (deferred).
- The test databases picked up revision 0015 as a new revision. No earlier migration was changed.
