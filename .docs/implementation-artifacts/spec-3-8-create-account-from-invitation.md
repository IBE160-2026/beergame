---
title: 'Story 3.8: Create an account from an Invitation'
type: 'feature'
created: '2026-11-18'
status: 'in-review'
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

Status: in-review (run interrupted before review results arrived)
Blocking condition: the four review subagents (blind-hunter-38, edge-case-hunter-38, verification-gap-38, intent-alignment-38) were launched on the diff since `ebb778193fe46080b78e0f5403ed8a0a1a7c0818`, but the builder had to hand back before their reports arrived. Resume at step-04 (status `in-review`).

Verification so far: backend `pytest` 1756 passed in 73 s, ruff clean; frontend typecheck, Vitest (261), check:copy, lint:colours, build pass; Playwright 73 passed on the compose stack. Migration 0019 is new and ran on the shared test databases; it was not changed afterwards.
