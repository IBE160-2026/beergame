---
title: 'Story 3.8: Create an account from an Invitation'
type: 'feature'
created: '2026-11-18'
status: 'done'
baseline_revision: 'ebb778193fe46080b78e0f5403ed8a0a1a7c0818'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-3-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-3-7-invite-lecturer-or-admin-by-email.md'
warnings: [oversized, multiple-goals]
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Invitation mail of Story 3.7 links to `/invitasjon#<token>`, which opens «Fant ikke siden.»: nobody can turn an Invitation into an account, an existing account cannot pick up the invited role, an expired link offers no way forward, and the first production Admin has no way in. Also (Issue #74): on `/admin/brukere` the result line of an earlier send stays visible after the form changes.

**Approach:** `identity` gets public routes to check an Invitation link, accept it (new account, or existing account by password), and ask for a new one (`renewal_requested_at`, migration 0019), each rate-limited through `platform/ratelimit`; acceptance runs in one transaction and logs the User in. Startup in production creates the bootstrap Admin Invitations; login grants Admin once to a listed address. The web app gets «Du er invitert» at `/invitasjon`. The invite form clears its result line on any change.

## Boundaries & Constraints

**Always:**
- Routes (all `authz.public`, CSRF header as usual), under `/api/auth/invitation`:
  - `POST /check {token}` → `200 {email, role, valid_days, has_account}`, or `410 invitation_link_invalid` for an unknown, accepted, voided or expired link, or one whose address belongs to a deactivated User.
  - `POST /accept {token, name, password}` (new account; name trimmed, 1–200 chars, else `422 invalid_request` `fields.name`; password 8–1024) → `200 SessionOut` + session cookie. One transaction: lock the Invitation row, re-check it is open, advisory lock `user:<email>`, insert User + the Invitation's role, set `accepted_at`, audit `invitation.accepted` (actor = new User, target `{invitation_id, user_id}`, change `{role, account: "created"}`). If a User with the address exists by then → `409 account_exists`, nothing changes.
  - `POST /accept-login {token, password}` (existing account) → checks the password through `service.authenticate` (login limits apply; wrong → `401 invalid_credentials`, limited → 429), then one transaction: lock Invitation, re-check open, add the role (no-op if held), set `accepted_at`, audit (change `account: "existing"`); `200 SessionOut` + cookie.
  - `POST /renewal {token}` → always `202` for any token when not rate-limited; sets `renewal_requested_at = now` on the matching Invitation when it is not accepted and not open (expired or voided); never says whether the Invitation or an account exists.
- Rate limits (`platform/ratelimit`, placeholders in `config.py`): accept attempts (both accept routes) per IP (`INVITATION_ACCEPT_RATE_LIMIT_PER_IP`=50) and per Invitation key = token hash (`…_PER_INVITATION`=10) in a 60-min window, counted before the work, `429 rate_limited` + `Retry-After`; renewal per IP (20) and per token (3) per 60 min.
- Token checks are cheap lookups before bcrypt; the token is never logged; log lines hold ids only.
- Bootstrap: `BOOTSTRAP_ADMIN_EMAILS` (comma list, default empty). With `APP_ENV=production`, api startup calls `identity.service.ensure_bootstrap_invitations(now)`: for each valid listed address with no User and no open unexpired Admin Invitation, under the 3.7 advisory lock, void any stale open one, insert an Admin Invitation (`invited_by` NULL), enqueue its `invitation` notice and audit `invitation.bootstrap` with actor None — once (a second start does nothing). At any login (`authenticate` success), a listed address without Admin gets it, once: guarded by an existing `role.bootstrap_granted` audit row for that User; audited with actor None.
- Web `/invitasjon` (in `(auth)`, like `/nytt-passord`, `referrer: no-referrer`, token from the fragment via `tokenFromHash`): Skjelett while checking; h1 «Du er invitert».
  - New account: lead naming the role, Tekstfelt «Navn», «E-post» (read-only, prefilled), «Velg passord» with the help line «Minst 8 tegn.» shown before typing, primary «Opprett konto og gå videre», validity line «Invitasjonen er gyldig i N dager.» («én dag» for 1). Reasons show after the first press and update as the user types, never on blur. Success → `meKey` set, go to `HOME_PATH[homeOf(user)]` (Lecturer → `/laererhjem`, Admin → `/admin`). `409` → the existing-account state.
  - Existing account: a lead saying the address has an account and that logging in adds the role; «E-post» read-only, «Passord», primary «Logg inn og legg til rollen», «Glemt passord?» link; wrong password → «Feil e-post eller passord.»
  - Invalid link: «Lenken er utløpt eller brukt.» and one secondary button «Be om ny Invitasjon»; after pressing, one result line that is the same for every link; 429 → rate-limited line. Copy in `nb.ts`, drafts marked [ASSUMPTION].
- Issue #74: in `invite-form.tsx` the result line disappears as soon as the e-mail is typed into or the role changes.

**Never:** No real mail; no e-mail, name, token or link in a log line, audit row, notice or job argument; no Student Invitation sentence or Class name (Epic 4); no Admin list/resend UI (3.10); no edits to `sprint-status.yaml`, `.env`, `.claude/settings*.json`; no DB-clock vs host-clock comparison; no `if role ==` in `app/modules/`; no second User for one address.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Check valid | open lecturer Invitation, 14 d left, no User | 200 `{email, role: lecturer, valid_days: 14, has_account: false}` | — |
| Check invalid | unknown / accepted / voided / expired token; address of a deactivated User | 410 `invitation_link_invalid` | — |
| Accept new | valid token, «  Ny Faglærer », good password | 200, cookie; one User (normalised e-mail, name trimmed, role lecturer); `accepted_at` set; one audit row; `/api/auth/me` works | — |
| Accept twice | same token again | 410; still one User | — |
| Admin Invitation | role admin | User has admin | — |
| Account appeared | User created for the address after check | 409 `account_exists`; Invitation still open | — |
| Accept existing | User exists, right password | 200, cookie; role added; one User; `accepted_at` set | wrong password → 401, Invitation open |
| Parallel accept | two accepts of one token at once | one 200, one 410; one User | row lock |
| Bad name / password | name `"   "`; password 7 chars | 422 `fields.name` / `fields.password`; nothing stored | — |
| Accept rate limit | 11th attempt on one token in the window | 429 `rate_limited` | Retry-After |
| Renewal | expired token; unknown token; open token | 202 for all; mark set only on the expired one | 429 past the limit |
| Bootstrap | production, listed address, no User | one Admin Invitation, notice, audit (actor NULL); second call adds nothing | invalid address skipped |
| Bootstrap login | listed User without Admin logs in | gains Admin once; after revoke-by-SQL and re-login, not again | — |

</intent-contract>

## Code Map

- `backend/app/modules/identity/service.py` -- add `check_invitation`, `accept_invitation_new`, `accept_invitation_existing`, `request_invitation_renewal`, `ensure_bootstrap_invitations`, bootstrap grant inside `authenticate` (after `ok and is_active`, in the give-back tx). Reuse `_invitation_open` (L290), `_days_left` (L286), `create_user` pattern (L126), `confirm_password_reset` pattern (L234: cheap check → hash outside tx → lock + re-check), `send_invitation` (L299) for bootstrap insert.
- `backend/app/modules/identity/repo.py` -- `invitation_by_hash`, `lock_invitation(id)` (FOR UPDATE), `lock_user_address(email)` (advisory), `mark_invitation_accepted`, `set_renewal_requested`, `grant_role` (ON CONFLICT DO NOTHING), `open_invitation(email, role)`.
- `backend/app/modules/identity/models.py` -- `renewal_requested_at` column. `schemas.py` -- `InvitationTokenIn`, `InvitationCheckOut`, `AcceptInvitationIn` (name validator), `AcceptExistingIn`; `PASSWORD_MIN_LENGTH` (L20).
- `backend/app/modules/identity/routes.py` -- four public routes on `router` (prefix `/api/auth`); errors via `error_response`, cookie via `auth.set_session_cookie`.
- `backend/app/platform/config.py` -- `bootstrap_admin_emails: str = ""`, invitation accept/renewal limits.
- `backend/app/platform/audit.py` -- `events_for_target` reads by target key (for the bootstrap-grant guard).
- `backend/app/main.py` -- lifespan calls `ensure_bootstrap_invitations` when `app_env == "production"`.
- `backend/migrations/versions/0019_invitation_renewal.py` (new) -- add column.
- Tests: `tests/test_authz_rules.py` (`PUBLIC_ROUTES` + 4), `tests/test_migrations.py` (`HEAD`="0019"), `tests/identity/test_invitations.py` helpers (`invite`, `LINK`, `clock`, `drain`, `mails`, `rows`).
- `frontend/src/modules/identity/{api.ts,password-reset.ts (tokenFromHash, PASSWORD_MIN_LENGTH),reset-password.tsx (page-state pattern),login-form.tsx,homes.ts}`; `components/{text-field.tsx (read-only style exists),button.tsx,link.tsx,action-error.tsx}`; `app/(auth)/nytt-passord/page.tsx` (page shell to mirror).
- `frontend/src/modules/admin/invite-form.tsx` -- Issue #74 fix; `e2e/admin-invite.spec.ts` L86 test to extend.
- `frontend/e2e/support/auth.ts` -- `latestMail`, `nextMail`, `loginByApi`, `DEMO_USERS`; `e2e/password-reset.spec.ts` -- `expectAccessible`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0019_invitation_renewal.py`, `identity/models.py`, `platform/config.py` -- column and settings.
- `backend/app/modules/identity/{repo,schemas,service,routes}.py`, `app/main.py` -- check, accept (new, existing), renewal, bootstrap, login grant.
- `backend/tests/identity/test_invitation_accept.py` (new) -- every matrix row through the api; no token/e-mail/name in logs or audit rows. Update `test_authz_rules.py`, `test_migrations.py`.
- `frontend/src/copy/nb.ts` -- `auth.invitation`.
- `frontend/src/modules/identity/{invitation.ts,invitation-page.tsx,api.ts}`, `src/app/(auth)/invitasjon/page.tsx` -- the page; regenerate `lib/api/{openapi.json,schema.ts}`.
- `frontend/src/modules/identity/invitation.test.ts` -- name validation and validity line.
- `frontend/e2e/invitation.spec.ts` (new) -- one test follows a mailed link and creates an account (Lecturer lands on Lærerhjem); existing-account flow on a unique address per run (Lecturer account made by api invite + accept, then an Admin Invitation opened in the page; demo Users are never changed); expired/used state and renewal; axe at 320, 360, 1440 px.
- `frontend/src/modules/admin/invite-form.tsx`, `e2e/admin-invite.spec.ts` -- Issue #74 fix and test.

**Acceptance Criteria:**
- Given a mailed Invitation link on the compose stack, when the person opens it, fills Navn and passord and presses «Opprett konto og gå videre», then they land logged in on Lærerhjem (Lecturer) or Admin-område (Admin).
- Given «Du er invitert» in its new-account, existing-account and invalid states at 320, 360 and 1440 px, then axe finds nothing, nothing scrolls sideways, there is one primary button, and the password rule is visible before typing.
- Given «Brukere og roller» after a send, when the e-mail is typed into or the role changed, then the result line is gone.
- Given the full suites, then everything passes and no new test takes over 1 s (except Playwright UI tests).

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 42 findings — high 0, medium 0, low 36, false 5, maybe-false 1
- note: the four reviewers ran as background subagents and the builder handed back before their notifications arrived; their final reports were read from their transcripts on resume.
- findings:
  - Blind Hunter:
    - `[low]` `reject` `/invitation/check` has no rate limit. The story limits acceptance attempts; the token is a 256-bit HMAC, so the check is no useful oracle.
    - `[low]` `patch` The name limit was checked on the raw value. The 200-character limit now runs in the validator after trimming (raw cap 800); tests `ø`×201 → 422 and padded `ø`×200 → 200.
    - `[low]` `patch` The client let a control character through, then showed only the general line. `validateName` now refuses `\p{Cc}`; Vitest case added.
    - `[low]` `patch` «Prøv igjen om en time.» named a fixed wait though login limits use 15 min. Now «For mange forsøk. Vent litt og prøv igjen.»
    - `[low]` `reject` The renewal line says Admin sees the request though no screen shows it yet. Story 3.10 shows `renewal_requested_at` in the same epic; the copy is [ASSUMPTION].
    - `[low]` `reject` «Glemt passord?» leaves the Invitation. The mail still holds the link; adding a return path is new surface.
    - `[low]` `reject` Issue #74 fix leaves a failed-send `ActionError` after the form changes. The issue names the result line; the error line clears on the next press by the Story 3.4 rule.
    - `[low]` `reject` Bootstrap at startup is unguarded and re-sends after expiry. A DB fault at startup already stops the api (seeds run there too); re-sends are at most one per expiry window.
    - `[false]` `reject` `audit.events_for_target` missing from the diff. It exists since Story 3.7 (`platform/audit.py:101`).
    - `[low]` `reject` `bootstrap_addresses()` reparses on every login. Microseconds per successful login; the list is short.
    - `[low]` `patch` The first-login grant ran outside production. `_grant_bootstrap_admin` now returns at once unless `APP_ENV=production`; test `test_the_list_grants_nothing_outside_production`.
    - `[false]` `reject` Unknown `LoginRefused` codes would 500. `authenticate` returns only `invalid_credentials`, `account_deactivated`, `rate_limited`, all mapped.
    - `[low]` `reject` `accept-login` resets login counters before the Invitation re-check. The password was right; resetting its failure count is the login rule anyway.
    - `[low]` `patch` Secret-in-log checks covered one path. `assert_no_secrets` now also wraps `accept-login`, renewal and bootstrap (with the invalid list entry).
    - `[low]` `patch` Renewal tests missed voided, accepted and per-IP. Added voided and accepted cases (and a voided one whose address has a newer open one) and `…_rate_limited_per_address`; dropped the unused fixture.
    - `[low]` `reject` The e2e copies `expectAccessible` and never closes the admin context. Same pattern as `admin-invite.spec.ts`; contexts close with the browser.
    - `[low]` `reject` The token stays in the address bar. Same as `/nytt-passord` (3.6); `no-referrer` keeps it off other sites.
    - `[low]` `reject` A 409 briefly shows the general line before the refetch remounts. The remount replaces it within one request.
    - `[low]` `patch` `account_exists` refusals were not logged. Both returns now log `invitation_accept_refused` with the code.
    - `[low]` `patch` `_accepted` also built the check's 410. Renamed `_invitation_answer`.
  - Edge Case Hunter:
    - `[low]` `patch` Parallel logins of a listed User could write two marks. The User row is now locked before the audit check; test `test_a_listed_admin_is_marked_once_without_a_second_grant` (3 parallel logins, one row).
    - `[low]` `patch` Raw-length name check (duplicate of the Blind Hunter row).
    - `[low]` `patch` Control character in the name passes the client (duplicate).
    - `[low]` `patch` A server `fields.name` is not mapped to the field. Same root cause: the client now refuses the only name the server refuses that it took.
    - `[false]` `reject` A token over 128 chars shows the page error. `tokenFromHash` returns "" for anything over 128, which shows the invalid state.
    - `[low]` `reject` A second link opened in the same tab by hash change keeps the old token. Rare; reload fixes it.
    - `[low]` `reject` Renewal marks a voided link whose address has a newer open Invitation. The Admin's resend (3.10) clears the mark; filtering is a new branch.
    - `[low]` `patch` Fixed wait in the rate-limit copy (duplicate).
  - Intent Alignment (divergences):
    - `[maybe-false]` `reject` Existing account logs in on the page, not through «Logg inn». Both readings fit "asks them to log in"; the page keeps the fragment token. The founder's reading would settle it.
    - `[low]` `reject` A used (accepted) link does not get `renewal_requested_at`. An accepted Invitation offers no resend (Story 3.10), so the mark could not lead anywhere; the answer is the same.
    - `[false]` `reject` The bootstrap guard is role-scoped. An open Lecturer Invitation must not block the first Admin's; "no open Invitation" read per the Admin role.
    - `[low]` `patch` The first-login grant applied in every environment (duplicate of the Blind Hunter row).
    - `[false]` `reject` An existing Lecturer accepting Admin lands on the Lærerhjem. That is the Story 3.3 home rule for Admin+Lecturer; a new Admin lands on `/admin` (e2e).
    - `[low]` `reject` The browser tests a used link, not a time-expired one. One state and one screen serve both; expiry is tested at the api.
  - Verification Gap:
    - `[low]` `patch` The in-transaction `account_exists` re-check was unreachable by tests. `test_an_account_made_during_acceptance_is_409_not_a_second_user` inserts the User while the password is hashed.
    - `[low]` `patch` No backend name-length test (added, see above).
    - `[low]` `patch` No renewal per-IP test (added).
    - `[low]` `patch` Login lockout through `accept-login` untested. `test_a_login_lockout_through_the_invitation_says_when_to_retry` checks 429 and `Retry-After`.
    - `[low]` `patch` The page's switch on 409 was untested. E2e `account made meanwhile` makes the account in another context, presses submit and sees the existing-account form.
    - `[low]` `patch` Log-secret checks on one path only (duplicate, patched above).
    - `[low]` `patch` Raw-length name (duplicate).
    - `[low]` `patch` `role_added: false` mark untested (covered by the new parallel-login test).

## Design Notes

- **Existing account logs in on the page.** The acceptance needs proof of the account; the password on the same page avoids a round-trip through «Logg inn» and losing the fragment token. `authenticate` keeps the login limits and the timing guard.
- **`has_account` is revealed only to a holder of a valid token**, who already controls the mailbox; the renewal answer, which takes any token, is identical for every link.
- **Bootstrap grant once** is keyed on an audit row, so revoking the Admin role later sticks without a new column.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/identity tests/test_authz_rules.py tests/test_migrations.py` -- expected: pass
- `cd backend && uv run pytest --durations=15 && uv run ruff check . && uv run ruff format --check .` -- expected: pass
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- expected: pass
- `docker compose up -d --build --wait proxy worker-batch && cd frontend && npx playwright test` -- expected: pass

## Auto Run Result

Status: done

**Summary.**
- `/api/auth/invitation/{check,accept,accept-login,renewal}` (public). `check` gives the address, the role, the days left and `has_account`; `accept` creates the User with the role, marks the Invitation accepted and writes `invitation.accepted` in one transaction, then sets the session cookie; `accept-login` adds the role to the existing account after its password (login limits apply); `renewal` answers 202 for any link and sets `renewal_requested_at` (migration 0019) on an expired or voided Invitation. Accept and renewal are rate-limited per IP and per link.
- Bootstrap: with `APP_ENV=production` the api start sends an Admin Invitation (audited `invitation.bootstrap`, actor NULL) to each listed address with no User and no open Admin Invitation; a listed User gains Admin at first login, marked once by `role.bootstrap_granted`.
- «Du er invitert» at `/invitasjon`: new-account form (Navn, read-only E-post, Velg passord with «Minst 8 tegn.», «Opprett konto og gå videre», validity line), existing-account form («Logg inn og legg til rollen», «Glemt passord?»), and the expired/used state with «Be om ny Invitasjon». Lands on `HOME_PATH[homeOf(user)]`.
- Issue #74: the result line on `/admin/brukere` clears when the address is typed or the role changes.

**Files changed:** backend `identity/{models,repo,schemas,service,routes}.py`, `platform/config.py`, `main.py`, `migrations/versions/0019_invitation_renewal.py`; tests `tests/identity/test_invitation_accept.py` (new), `test_authz_rules.py`, `test_migrations.py`. Frontend `copy/nb.ts` (`auth.invitation`), `modules/identity/{api.ts,invitation.ts,invitation-page.tsx,invitation.test.ts}`, `app/(auth)/invitasjon/page.tsx`, `modules/admin/invite-form.tsx`, regenerated `lib/api/{openapi.json,schema.ts}`, `e2e/invitation.spec.ts` (new), `e2e/admin-invite.spec.ts`.

**Review.** 42 findings: 0 high, 0 medium, 36 low, 5 false, 1 maybe-false. Patched (all low): name limit after trimming, client control-character check, window-neutral rate-limit copy, bootstrap grant only in production and serialised, `account_exists` logged, `_invitation_answer` rename, and the missing tests (in-transaction 409, name length, renewal voided/accepted/per-IP, login lockout via `accept-login`, log secrets on every path, e2e 409 switch). Nothing deferred. Every rejection has its reason in the triage log.

**Follow-up review recommended: false.** Only low entries were patched.

**Verification:**
- Backend `uv run pytest`: 1763 passed in 63–68 s; ruff check and format clean. New tests each under 1 s (slowest 0.36 s call).
- One full run failed `test_parallel_acceptances_make_one_account` with a 409 for the losing request: `check_invitation` reads the Invitation and the User in two statements, so under Read Committed the loser can see the open Invitation and then the winner's User. That answer is correct (no second User, no 500); the test now accepts 409 or 410 for the loser. Two later full runs passed.
- Frontend: typecheck, Vitest (261), check:copy, lint:colours, build pass. Playwright 74 passed on the compose stack with `worker-batch` (UI tests 1–3 s each; they wait for real mails).
- Migration 0019 is new; it ran on the shared `olspillet_test*` databases and was not changed afterwards.
- Matrix audit: Check valid → `test_a_usable_link_shows…`; Check invalid → `test_a_link_that_no_longer_works_is_one_answer` (5 cases); Accept new and Accept twice → `test_accepting_creates_the_account…`; Admin Invitation → `test_an_admin_invitation_makes_an_admin`; Account appeared → `test_an_account_made_meanwhile…` and `…during_acceptance_is_409…`; Accept existing → `test_an_existing_account_logs_in…`; Parallel → `test_parallel_acceptances_make_one_account`; Bad name/password → `test_a_bad_name_or_password_is_refused` (4 cases); Accept rate limit → `…rate_limited_per_link` / `…per_address`; Renewal → `test_asking_for_a_new_invitation_answers_the_same…` and both renewal limit tests; Bootstrap → `test_the_bootstrap_invitation_is_made_once…`, `test_the_api_makes_bootstrap_invitations_only_in_production`; Bootstrap login → `test_a_listed_user_gains_admin_at_first_login_only` and the two new listed-User tests.
- The founder's checks (Playwright with axe at 320, 360 and 1440 px on the three states) are done by `e2e/invitation.spec.ts`; the review was done by four independent reviewer agents.

**Decisions taken in place of the founder:**
- An existing account accepts on the same page with its password; only a holder of a valid link learns `has_account`.
- Renewal marks only expired or voided Invitations, and always answers 202.
- Rate-limit placeholders: accept 50/IP and 10/link per hour; renewal 20/IP and 3/link per hour.
- `invitation.accepted` audit row on acceptance.
- Bootstrap grant only in production, once per User, marked in the audit log.
- Password minimum 8 (as «Nytt passord»), not the mockup's 10. No «Har du konto?» link on the new-account form.
- Draft copy marked [ASSUMPTION] in `nb.ts`.

**Residual risks:**
- The renewal line promises that the Admin sees the request; that screen comes with Story 3.10.
