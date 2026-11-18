---
title: 'Story 3.6: Reset a forgotten password by e-mail'
type: 'feature'
created: '2026-11-18'
status: 'done'
baseline_revision: '1f2635eabadea44efefc99ead01e3a428c6f1a09'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-3-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-3-5-send-every-mail-through-one-pipeline.md'
warnings: [oversized]
deferred:
  - summary: >-
      A password reset does not end the User's other sessions.
    evidence: |-
      The session is a JWT that carries only user_id (AD-11), and load_user checks only that the User exists and is active. A thief who is logged in stays logged in after the owner resets the password. Nothing in the product could revoke a session before this story either. A fix needs a per-User session epoch or password_changed_at that load_user compares with the token's iat.
    location: >-
      backend/app/modules/identity/service.py (confirm_password_reset), backend/app/platform/auth.py
    severity: medium
---

<intent-contract>

## Intent

**Problem:** A Lecturer who forgets the password must ask the Admin; the «Glemt passord?» link on `/logg-inn` leads nowhere, and the mail pipeline of Story 3.5 cannot give a User-addressed mail its own variables (the reset link).

**Approach:** `identity` gets a `password_resets` table and three public endpoints (request, check, confirm). A request for an active User stores a token hash and enqueues an `immediate` `password_reset` notice; `messaging` gains a per-kind context resolver so the mail renders the link at send time. The web app gets «Glemt passord» and «Nytt passord». A local-only dev mailbox endpoint lets Playwright read the mock mail.

## Boundaries & Constraints

**Always:**
- `POST /api/auth/password-reset` `{email}` answers `202` with no body for an active User, a deactivated User and an unknown address alike. Rate limits through `platform/ratelimit`, counted before anything else: bucket `password_reset_ip` (key IP) and `password_reset_account` (key normalised e-mail, whether or not it exists); over a limit → `429 rate_limited` with `Retry-After`. Settings `PASSWORD_RESET_VALID_MINUTES`=60, `PASSWORD_RESET_RATE_LIMIT_PER_IP`=50, `PASSWORD_RESET_RATE_LIMIT_PER_ACCOUNT`=5, `PASSWORD_RESET_RATE_LIMIT_WINDOW_MINUTES`=60 (placeholders).
- For an active User, in one transaction: insert a `password_resets` row (`id` uuid7, `user_id`, `token_hash`, `created_at`, `expires_at` = host now + validity, `used_at`, `voided_at`) and `notify.enqueue(user_id, "password_reset", dedupe_key=f"password_reset:{reset_id}", ref=reset_id)`. Deactivated or unknown: nothing stored, nothing enqueued.
- The token is `base64url(HMAC-SHA256(JWT_SECRET, "password_reset:" + reset_id))`; the table holds only `sha256(token)`. So `messaging` can rebuild the link at send time and no token is ever in a row, notice, job argument or log line.
- `password_reset` is an `immediate` kind in `delivery.KINDS`, addressed to the User, with a new optional `Delivery.context` resolver `(session, user_id, ref) -> Mapping | None` that `identity.service.password_reset_mail_context` implements: `{"link": "/nytt-passord#<token>", "valid_minutes": N}`, or None when the reset is used, voided, expired (host clock) or the User is inactive → the delivery is skipped with the new `skipped_reason` `stale`. Templates `kinds/password_reset.{txt,html}.j2`.
- `POST /api/auth/password-reset/check` `{token}` → `200 {email}` for a usable token; `410 reset_link_invalid` for an unknown, used, voided or expired token or an inactive User.
- `POST /api/auth/password-reset/confirm` `{token, password}` (8 ≤ length ≤ 1024, else `422 invalid_request`) → in one transaction with the reset row locked: re-check usable, store the new hash, set `used_at`, set `voided_at` on every other open reset of that User, reset the `login_account` counter → `200 {email}`; otherwise `410 reset_link_invalid`. All three routes are `authz.public` and on `PUBLIC_ROUTES`. Time comes from `auth.utcnow()`; never the DB clock (Issue #63).
- Web: `/glemt-passord` (E-post field, primary «Send lenke», shows «Hvis adressen har en konto, har vi sendt en lenke. Lenken virker i én time.» after any 202) and `/nytt-passord` (reads the token from the URL fragment, checks it: usable → «Nytt passord» field and primary «Lagre passord»; invalid → «Lenken er utløpt eller brukt.» with link «Send ny lenke» to `/glemt-passord`; done → «Passordet er endret.» followed by the «Logg inn» form with the e-mail prefilled). Same shell, tokens and components as `/logg-inn`; copy in `nb.ts`.
- Dev mailbox: `GET /api/dev/mailbox/latest?to=<email>` in `modules/messaging/routes.py`, mounted only when `APP_ENV` is `local`, `test` or `ci`, public and on `PUBLIC_ROUTES`: re-renders the newest sent delivery to that User and returns `{subject, text, html, sent_at}`, or `404 not_found`. The request log keeps the path only.
- CI's Playwright job also starts `worker-batch`, so mails really flow.

**Never:** No real mail, no session revocation of other devices, no password strength meter or second password field, no change to `sprint-status.yaml`, `.env` or `.claude/settings*.json`, no comparison of database time with host time, no name/e-mail/token/link in logs.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Active | Request for an active User | 202; one reset row, one notice; after the mail jobs one `[email:mock]`, mail holds `PUBLIC_BASE_URL/nytt-passord#…`, headed «ØL-spillet» | — |
| Deactivated / nobody | Request for either | 202, same body; no row, no notice, no mail | — |
| Rate limit | 6th request for one address in the window; 51st from one IP | 429 `rate_limited` + `Retry-After` | — |
| Confirm | Valid token + new password | 200 `{email}`; login works with new password, not old; token `used_at`; other open tokens `voided_at` | — |
| Single use | Same token confirmed twice; voided token | second → 410 `reset_link_invalid`; check → 410 | — |
| Expired | Clock past `expires_at` | check and confirm → 410; a mail not yet sent → skipped `stale` | — |
| Deactivated later | User deactivated after the request | check/confirm 410; mail skipped `no_recipient` | — |
| Short password | 7 characters | 422 `invalid_request`; token stays usable | — |

</intent-contract>

## Code Map

- `backend/app/modules/identity/{models,repo,service,routes,schemas}.py` -- add `password_resets`, repo SQL, `request_password_reset`, `check_reset`, `confirm_reset`, `password_reset_mail_context`, the three routes, `PasswordResetIn`/`ResetTokenIn`/`NewPasswordIn`/`ResetEmailOut`, `PASSWORD_MIN_LENGTH = 8`. `authenticate` shows the rate-limit pattern (`ratelimit.hit` in a `begin()` block; `seconds_left`).
- `backend/app/platform/auth.py` -- `utcnow`, `hash_password` (bcrypt off-loop via `asyncio.to_thread`).
- `backend/app/platform/config.py` -- add the four reset settings.
- `backend/app/modules/messaging/delivery.py` -- `Delivery` gets `context: ContextResolver | None`; `KINDS` gets `password_reset` (import `identity.service` only).
- `backend/app/modules/messaging/service.py:205-252` `send` -- resolve each carried notice's context into `email.Section(template, context)`; all None → `mark_skipped(..., "stale")`. Extract the compose part so the dev mailbox re-renders a sent delivery the same way.
- `backend/app/modules/messaging/{models,repo}.py` -- `SKIP_REASONS` + `stale`; `latest_sent_for_user`.
- `backend/app/modules/messaging/routes.py` (new) and `backend/app/main.py` -- dev mailbox router, mounted only outside production. `identity.service.user_id_for_email`.
- `backend/migrations/versions/0017_password_resets.py` (new), `migrations/env.py` unchanged (identity models already imported) -- create `password_resets` (index on `user_id`, unique `token_hash`), replace `ck_mail_deliveries_skipped_reason`.
- `backend/tests/test_migrations.py` (`HEAD`, `HEAD_TABLES`, downgrade test), `tests/test_authz_rules.py` (`PUBLIC_ROUTES`), `tests/test_imports.py:97` (allow `app/main.py` → `app.modules.messaging.routes`), `tests/conftest.py` (`IDENTITY_TABLES`, `MAIL_TABLES` + `password_resets`).
- `backend/app/platform/email/templates/kinds/` -- pattern from `test_immediate.*`; `subject` set in the `.txt.j2`.
- `frontend/src/modules/identity/{api.ts,login-form.tsx}` -- add the three hooks; `LoginForm` gets `defaultEmail`. `frontend/src/app/(auth)/logg-inn/page.tsx` is the page shell to mirror. Regenerate `src/lib/api/{openapi.json,schema.ts}` (`npm run api:generate` after dumping the schema).
- `frontend/e2e/support/auth.ts` -- add `latestMail(page, email)`; `frontend/e2e/logg-inn.spec.ts` shows the axe/reflow/tap-target checks.
- `.github/workflows/ci.yml:115` -- `docker compose up -d --build --wait proxy worker-batch`.

## Tasks & Acceptance

**Execution:**
- `backend/app/platform/config.py` -- reset settings.
- `backend/app/modules/identity/*` + `migrations/versions/0017_password_resets.py` -- table, service, routes.
- `backend/app/modules/messaging/{delivery,service,models,repo,routes}.py`, `app/main.py`, `app/platform/email/templates/kinds/password_reset.{txt,html}.j2` -- kind, context resolver, `stale`, dev mailbox.
- `backend/tests/identity/test_password_reset.py` (new) -- every matrix row through the api and `drain()`, plus "no name/e-mail/token in log lines or job args" (structlog capture + `procrastinate_jobs.args`). Update the four guard tests and fixtures.
- `backend/tests/messaging/test_dev_mailbox.py` (new) -- returns the rendered latest mail; 404 for an unknown address; not mounted with `APP_ENV=production`.
- `frontend/src/copy/nb.ts` -- `auth.forgot` and `auth.reset` sections.
- `frontend/src/app/(auth)/{glemt-passord,nytt-passord}/page.tsx`, `frontend/src/modules/identity/{forgot-form,reset-form}.tsx` -- the pages.
- `frontend/src/modules/identity/*.test.ts(x)` -- Vitest for the token-from-fragment helper and the error mapping.
- `frontend/e2e/password-reset.spec.ts` (new) -- full flow per viewport (320 admin, 360 lecturer, 1440 admin-faglaerer, new password = demo password), axe and reflow on every state, used link shows the invalid state and «Send ny lenke» goes back.
- `.github/workflows/ci.yml` -- start `worker-batch` for e2e.

**Acceptance Criteria:**
- Given `/logg-inn`, when «Glemt passord?» is followed, an address entered and «Send lenke» pressed, then the sent line shows for a demo User and for an unknown address alike, and the reset mail arrives in the dev mailbox within seconds on the compose stack.
- Given the mail link, when opened, a new password set and saved, then «Passordet er endret.» and the «Logg inn» form with the e-mail prefilled show, and logging in with it reaches the User's home.
- Given both pages at 320, 360 and 1440 px, then axe (WCAG 2.1 AA) finds nothing and nothing scrolls sideways.
- Given `APP_ENV=production`, then `/api/dev/mailbox/latest` is not routed.
- Given the full suites, then everything passes and no new test takes over 1 s.

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 49 findings — high 0, medium 9, low 31, false 4, maybe-false 5
- findings:
  - Blind Hunter:
    - `[false]` `reject` The dev mailbox is mounted for any APP_ENV except production, so staging or a typo would expose it. `Settings.app_env` is `Literal["local","test","ci","production"]`, and any other value fails at start, so `!= "production"` is the allow-list `{local, test, ci}`.
    - `[medium]` `defer` A reset does not end other sessions. The JWT design (AD-11) has no revocation, and nothing before this story could revoke a session either. Deferred with the fix it needs.
    - `[medium]` `patch` `confirm` ran bcrypt before it checked the token, on a public route with no limit. It now checks the link first, so a made-up token costs one lookup and no hash.
    - `[low]` `reject` Anyone can use up an address's per-account limit. The story requires per-account limits, and login has the same trade-off.
    - `[maybe-false]` `reject` The response time reveals whether an account exists (one insert and enqueue more). A timing measurement through the proxy would settle it. If true it is low: a few ms against network jitter.
    - `[low]` `patch` The session key also keyed the link HMAC. The link key is now derived from `JWT_SECRET` with its own label.
    - `[low]` `reject` The token stays in the address bar and history. Removing it would make a reload show the dead-link state for a working link. The page sets `no-referrer`.
    - `[low]` `reject` `password_resets` and the counter rows have no retention. `ops.sweep` already purges counter rows (`ratelimit.purge`). Reset rows exist only for active accounts and are capped by the account limit.
    - `[low]` `reject` «én time» and «8 tegn» are fixed in the copy while the values are settings. The story gives the exact sentence; the settings are placeholders.
    - `[low]` `reject` A server 422, or a password over 1024 characters, shows only the general line. The client checks the minimum. A 1024-character password does not happen in everyday use.
    - `[low]` `patch` The reset form said «Vent noen minutter» for a one-hour window. It now has its own line: «For mange forespørsler. Prøv igjen om en time.»
    - `[medium]` `patch` Repeated local Playwright runs would hit the 5-per-hour address limit. Compose now sets high reset limits for the local stack, as it does for `BCRYPT_ROUNDS`. The api tests check the real limits.
    - `[low]` `reject` «Glemt passord» has no resend after the sent line. «Til innlogging» and «Glemt passord?» lead back; the spine gives no resend state.
    - `[medium]` `patch` Concurrent confirmations were untested. Added `test_parallel_confirmations_let_exactly_one_through`.
    - `[low]` `reject` The dev mailbox gives up when the newest mail is stale, and two mails with the same `sent_at` look like one. It is a dev-only aid, and the tests read the mail before using it.
    - `[low]` `patch` A comment in `forgot-form.tsx` was indented wrong. Fixed.
    - `[low]` `reject` The hidden `username` input uses `hidden`. Common managers read it. No failure was named.
    - `[low]` `patch` `latest_mail` had no return type. Added.
  - Edge Case Hunter:
    - `[low]` `patch` Two open links of one User confirmed at once could both succeed. `confirm` now locks the User row and reads the link again, so the second finds itself voided. Covered by the parallel test.
    - `[medium]` `patch` bcrypt runs before the token check (duplicate). Fixed above.
    - `[low]` `reject` A victim can be blocked through the account limit (duplicate).
    - `[maybe-false]` `reject` Timing leak (duplicate).
    - `[medium]` `defer` Sessions survive a reset (duplicate). Deferred.
    - `[low]` `reject` Rotating `JWT_SECRET` voids open links. This is intended (Design Notes); rotation already ends every session.
    - `[low]` `patch` A late mail said «én time» when less was left. The mail now states the time left, rounded up. Test: `test_a_late_mail_states_the_time_left`.
    - `[low]` `patch` `valid_minutes == 1` read «1 minutter». The templates now say «ett minutt», which the late-mail fix can reach.
    - `[low]` `reject` The sent line promises one hour whatever the setting (duplicate of the fixed-copy row).
    - `[maybe-false]` `reject` A non-production APP_ENV deployed in public would expose the mailbox. Deploying needs `APP_ENV=production` (Story 3.14). Whether anyone would deploy local mode settles it; if true it is low.
    - `[low]` `reject` The mailbox answers 404 for a stale newest mail (duplicate).
    - `[low]` `patch` "Latest" was ordered by claim id, not by send time. Now ordered by `sent_at`, then id.
    - `[low]` `reject` A second link pasted into the same tab changes only the fragment. A mail link opens the page anew; a listener adds code for a rare path.
    - `[low]` `reject` Token in history (duplicate).
    - `[low]` `reject` Over 1024 characters (duplicate).
    - `[low]` `reject` A 422 field error shows the general line (duplicate).
    - `[low]` `patch` Rate-limit copy (duplicate). Fixed above.
  - Verification Gap:
    - `[medium]` `patch` No parallel-confirmation test (duplicate). Added.
    - `[low]` `patch` The branch for a link spent while the form is open was untested. Added the Playwright test `a link spent while the form is open shows the expired state on save`.
    - `[low]` `patch` The new `Delivery` rule had no test. Added `test_a_kind_by_reference_takes_no_context_resolver`.
    - `[low]` `patch` The account limit was not tested with case and space variants. `test_requests_are_limited_per_account` now mixes them.
    - `[medium]` `patch` bcrypt before the token check (duplicate). Fixed above.
    - `[low]` `reject` Fixed «én time» copy (duplicate).
    - `[medium]` `patch` Playwright limits (duplicate). Fixed above.
    - `[low]` `reject` The reset form's `rate_limited` mapping has no UI test. It is one table entry; the api tests cover the 429.
  - Intent Alignment (descriptive divergences):
    - `[false]` `reject` The mailbox is mounted on `!= production`, not on `local|test|ci` as the spec says. With the `Literal` type these are the same set.
    - `[false]` `reject` The expired-link page state is never shown in a browser. The page has one invalid state for every 410. Playwright shows it for a used link, and the api tests show that expiry returns that 410.
    - `[false]` `reject` The deactivated-address answer is never shown in a browser. The api returns the identical empty 202 (tested), and the page reacts only to the status.
    - `[low]` `reject` The unknown-address and no-token tests run at one width without axe. Both pages and all their states pass axe at 320, 360 and 1440 px in the flow tests, which is what the story asks.
    - `[maybe-false]` `reject` The "random token" is an HMAC of a UUIDv7 under a server secret, not separate CSPRNG bytes. The founder's meaning settles it. If true it is low: the token is unguessable without the secret, and only its hash is stored.
    - `[maybe-false]` `reject` «Logg inn» follows on the same page, not on `/logg-inn`. EXPERIENCE.md supports both readings. An inline form keeps the address out of the URL.

## Design Notes

- **Why an HMAC token.** The mail is rendered at send time (Story 3.5), but the table may keep only a hash. Deriving the token from the reset id with the server secret lets `messaging` rebuild the link without storing it anywhere. Rotating `JWT_SECRET` voids open links, as it already ends sessions.
- **Fragment, not query.** `/nytt-passord#<token>`: a fragment never reaches a server log or a `Referer` header.
- **No auto-login after reset.** The spine says «Logg inn» follows with the e-mail prefilled; logging in once proves the new password.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/identity tests/messaging tests/test_authz_rules.py tests/test_imports.py tests/test_migrations.py` -- expected: pass
- `cd backend && uv run pytest --durations=15 && uv run ruff check . && uv run ruff format --check .` -- expected: pass
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run build` -- expected: pass
- `docker compose up -d --build --wait proxy worker-batch && cd frontend && npx playwright test` -- expected: pass

## Auto Run Result

Status: done

**Summary.**
- `identity` owns `password_resets`: id, User, SHA-256 of the token, `expires_at`, `used_at`, `voided_at`. It has three public routes:
  - `POST /api/auth/password-reset` always answers an empty `202`, or `429` from the IP or account limit.
  - `POST /api/auth/password-reset/check` answers `{email}` or `410 reset_link_invalid`.
  - `POST /api/auth/password-reset/confirm` checks the link, then hashes, locks the User, stores the password, uses the link, voids the User's other links and clears the failed-login count.
- An active User gets a reset row and a `password_reset` notice in one transaction. A deactivated User or an unknown address gets nothing.
- The token is an HMAC of the reset id under a key derived from `JWT_SECRET`. `messaging` rebuilds the link at send time, so no token is stored, logged or put in a job.
- `messaging`:
  - `Delivery.context` lets a User-addressed kind pass template variables. This closes the 3.5 residual risk.
  - When that context is gone (the link was used or expired before the send), the mail is skipped as `stale`.
  - `password_reset` is the first product kind. Its mail is «Nytt passord til ØL-spillet», with `PUBLIC_BASE_URL/nytt-passord#<token>` and the time left.
- Web:
  - `/glemt-passord` has «Send lenke» and the fixed sent line.
  - `/nytt-passord` reads the token from the fragment and shows the Skjelett while it checks the link. Then it shows one of three states:
    - the form, with «Minst 8 tegn.»;
    - «Lenken er utløpt eller brukt.» with «Send ny lenke»;
    - «Passordet er endret.», then the «Logg inn» form with the e-mail prefilled.
  - «Glemt passord?» on `/logg-inn` now leads somewhere.
- The dev mailbox `GET /api/dev/mailbox/latest?to=` renders the newest sent mail again. It is not mounted in production and not in OpenAPI.
- CI's e2e job now starts `worker-batch`.

**Files changed:**
- Backend:
  - `app/platform/{auth,config}.py`: the link token and the settings.
  - `app/modules/identity/{models,repo,service,routes,schemas}.py`.
  - `app/modules/messaging/{delivery,service,models,repo}.py` and the new `routes.py`.
  - `app/main.py`.
  - `kinds/password_reset.{txt,html}.j2`.
  - Migration `0017_password_resets.py`.
- Backend tests:
  - new: `tests/identity/test_password_reset.py`, `tests/messaging/test_dev_mailbox.py`;
  - updated: `test_delivery.py`, `test_migrations.py`, `test_authz_rules.py`, `test_imports.py`.
- Frontend:
  - `copy/nb.ts`;
  - `components/text-field.tsx` (`hint`);
  - `modules/identity/{api.ts,login-form.tsx,forgot-form.tsx,reset-password.tsx,password-reset.ts,password-reset.test.ts}`;
  - the pages `app/(auth)/{glemt-passord,nytt-passord}/page.tsx`;
  - the regenerated `lib/api/{openapi.json,schema.ts}`;
  - `e2e/password-reset.spec.ts`, and `e2e/support/auth.ts` (`latestMail`, `nextMail`).
- Other: `docker-compose.yml` (high reset limits locally), `.github/workflows/ci.yml` (`worker-batch`).

**Review.** 49 findings: 9 medium, 31 low, 4 false, 5 maybe-false.
- Patched, as entries:
  - medium: bcrypt before the token check;
  - medium: Playwright hitting the limits;
  - medium: no concurrency test;
  - low: the concurrent-links lock;
  - low: the derived link key;
  - low: the time left and «ett minutt»;
  - low: sort by send time;
  - low: the reset-specific 429 copy;
  - low: three missing tests;
  - low: indentation;
  - low: the return type.
- Deferred: sessions survive a reset (medium).
- Rejected: the rest, each with its reason in the triage log.

**Follow-up review recommended: true.** Three medium entries were patched. The risk not yet re-reviewed is the new order inside `confirm`. It checks the link, hashes, locks the User, then reads the link again. The parallel test covers this order, but no reviewer has looked at it.

**Verification:**
- Backend:
  - `uv run pytest`: 1706 passed in 72 s.
  - `ruff check` and `ruff format --check` are clean.
  - New backend tests each take under 1 s; the slowest is 0.54 s.
- Frontend:
  - `typecheck`, Vitest (250 passed), `check:copy` (9 templates) and `build` pass.
  - Playwright: 59 passed on the compose stack with `worker-batch`.
  - The three reset flow tests take 4–10 s each. Each is one full flow: a real mail through the worker, six axe runs and a login.
- Migration 0017 is new. It ran once on the shared `olspillet_test*` databases and was not changed after that.
- Matrix audit, one row per test:
  - Active: `test_an_active_user_gets_one_mail…`.
  - Deactivated or nobody: `test_a_deactivated_user_or_an_unknown_address…`.
  - Rate limit: `…limited_per_account` and `…per_ip_address`.
  - Confirm: `test_an_active_user…` and `test_using_one_link_voids…`.
  - Single use: `test_an_active_user…` and `test_parallel_confirmations…`.
  - Expired: `test_an_expired_link…`.
  - Deactivated later: `test_a_user_deactivated_after_the_request…`.
  - Short password: `test_a_short_password…`.

**Decisions taken in place of the founder:**
- Token: an HMAC of the reset id under a key derived from `JWT_SECRET`, so the mail can be rendered at send time while only the hash is stored. Rotating the secret voids open links.
- The link carries the token in its fragment (`/nytt-passord#…`), not in the query.
- Limits (placeholders):
  - 5 per address and 50 per IP per 60 minutes, counted for every address, known or not;
  - over the limit, the reply is `429` and the page shows «For mange forespørsler. Prøv igjen om en time.»;
  - compose raises both limits locally.
- The minimum password is 8 characters, with no repeat field.
- A reset clears the failed-login count. It does not log the User in, and it does not end other sessions (deferred).
- «Logg inn» is shown inline on «Nytt passord», prefilled; no address goes in a URL. `/check` returns the e-mail, and the lead line shows it.
- Playwright reads mail through a local-only dev mailbox route. CI starts `worker-batch`.
- Draft copy is marked [ASSUMPTION] in `nb.ts`: «Send lenke», «Lagre passord», «Minst 8 tegn.», the leads and the 429 line. The mail text is also a draft.
- The implementation and the review fixes were done in this context, as the caller instructed. The four reviewers ran as subagents. Their completion notices never arrived, so their reports were read from their transcripts.

**Residual risks:**
- Sessions survive a reset (deferred).
- A request for an existing account takes slightly longer than one for an unknown address.
- `/logg-inn`'s form has the same blur layout shift. A reason that vanishes on blur moves the button out from under the click. It was fixed here with `onChange`, but not in the login form.
