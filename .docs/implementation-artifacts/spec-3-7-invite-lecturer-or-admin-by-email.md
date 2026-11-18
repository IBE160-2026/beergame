---
title: 'Story 3.7: Invite a Lecturer or Admin by e-mail'
type: 'feature'
created: '2026-11-18'
status: 'done'
baseline_revision: 'ce9d93828ba744e3807d52b91b3cf64f76541006'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-3-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-3-6-reset-forgotten-password-by-email.md'
warnings: [oversized]
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Admin has no way to bring a new Lecturer or Admin in: there is no `invitations` table, no `invitation` mail kind, no audit trail for Admin actions, and the «Admin-område» has no «Brukere og roller» page.

**Approach:** `identity` gets an `invitations` table and an Admin-only `POST /api/admin/invitations`; it stores a token hash, voids an open Invitation for the same address and role, enqueues an `invitation` notice addressed by reference, and writes one row through the new `platform/audit` in the same transaction. `messaging` registers `invitation` as an `immediate` kind whose ref resolver (in `identity.service`) gives address and link at send time. The web app gets `/admin/brukere` («Brukere og roller») with the invite form, linked from the «Admin-område».

## Boundaries & Constraints

**Always:**
- `POST /api/admin/invitations` `{email, role}` (`role` ∈ `lecturer`, `admin`), policy `authz.require("users.manage")` → `201 {id, email, role, expires_at, valid_days}`. The e-mail is trimmed and lower-cased, then checked with the web app's rules (non-empty, no whitespace, exactly one `@`, a local part, a domain of ≥ 2 non-empty labels); a bad one → `422 invalid_request` with `fields.email = "invalid_email"` and nothing stored. No session → 401; any non-Admin → 403 `forbidden`, and no row, notice, mail or audit row.
- One transaction: `pg_advisory_xact_lock` on `invitation:<email>:<role>`; set `voided_at` on every Invitation for that address and role with `accepted_at` and `voided_at` NULL; insert the new row (`id` uuid7, `email`, `role`, `token_hash`, `created_at`, `expires_at` = host now + `ROLE_INVITATION_VALID_DAYS` (default 14, placeholder), `accepted_at`, `voided_at`, `invited_by` → `users.id`, nullable for the system actor of Story 3.8); `notify.enqueue(session, None, "invitation", dedupe_key=f"invitation:{id}", ref=id)`; `audit.record(...)`. A partial unique index on `(email, role)` where `accepted_at IS NULL AND voided_at IS NULL` guarantees one open Invitation per address and role.
- Token = `auth.link_token("invitation", id)` (the 3.6 HMAC pattern); only `auth.token_hash(token)` is stored. Link `/invitasjon#<token>` on `PUBLIC_BASE_URL` (the page comes in Story 3.8).
- `delivery.RefResolver` becomes `(session, ref, now)`; `KINDS["invitation"] = Delivery(IMMEDIATE, "invitation", resolve_ref=identity.invitation_mail_recipient)`. The resolver returns `Recipient(email, None, context={"link", "role", "valid_days"})` for an open, unexpired Invitation (host clock `now`), else None → skipped `no_recipient`. `valid_days` = days left, rounded up. Templates `kinds/invitation.{txt,html}.j2`, subject «Invitasjon til ØL-spillet».
- `platform/audit.py` owns `audit_events` (`id` uuid7, `actor_user_id` uuid NULL = system, no FK, `action` text, `target_ids` jsonb, `change` jsonb, `occurred_at` timestamptz from the caller's clock) with an index on `occurred_at` and a trigger that refuses UPDATE and DELETE. `record(session, actor, action, target, change, at)` raises `ValueError` on any string value holding `@`. It imports no module. Sending writes action `invitation.sent`, target `{"invitation_id"}`, change `{"role"}` plus `{"voided_invitation_ids"}` when it voided any.
- Dev mailbox `GET /api/dev/mailbox/latest?to=` also finds Invitation mails: newest sent delivery whose `user_id` is that User or whose notice `ref` is an Invitation of that address (`identity.service.invitation_ids_for_email`).
- Web: `/admin` («Admin-område») shows the Lenke «Brukere og roller» → `/admin/brukere`. That page: breadcrumb «Admin-område / Brukere og roller», h1 «Brukere og roller», one-column form: Tekstfelt «E-post», Valgknapper «Rolle» (Faglærer selected / Admin; native radios in a `fieldset`), one primary button «Send Invitasjon». A bad address shows the Tekstfelt's invalid state with its reason; after the first press the reason updates as the user types (never on blur). Success → result line «Invitasjonen er sendt til <e-post> som <Faglærer|Admin>. Den er gyldig i <N> dager.» receives focus, the e-mail field is emptied. Failure → `ActionError` «Invitasjonen ble ikke sendt. Prøv igjen.», input kept. A non-Admin sees «Du har ikke tilgang til denne siden.»; logged out goes to «Logg inn» and back. Copy in `nb.ts`.

**Never:** No real mail; no name, e-mail, token or link in a log line, job argument, notice or audit row; no acceptance page (3.8), user list, resend button (3.10) or rate limit on the Admin route; no edits to `sprint-status.yaml`, `.env`, `.claude/settings*.json`; no DB-clock vs host-clock comparison; no `if role ==` in `app/modules/`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Send | Admin, `  Ny.Faglaerer@Example.com `, lecturer | 201; one row (normalised e-mail, hash only, `expires_at` = now + 14 d, `invited_by` = Admin); one notice (`user_id` NULL, `ref` = id); one audit row; after the jobs one mail to the address, headed «ØL-spillet», with `…/invitasjon#<token>` whose hash is the row's, «gyldig i 14 dager» | — |
| Validity setting | `ROLE_INVITATION_VALID_DAYS=3` | `expires_at` = now + 3 d; response and mail say 3 | — |
| Malformed | `kari`, `a@b`, `a b@c.no`, `@c.no`, `a@@c.no`, `` | 422 `invalid_request`, `fields.email`; nothing stored or enqueued | — |
| Send again, same role | second send for same address and role | first `voided_at` set, exactly one open; first mail (if unsent) skipped `no_recipient`, second sent | — |
| Other role | lecturer then admin for one address | two open Invitations | — |
| Parallel | two sends at once, same address and role | exactly one open | lock + partial unique index |
| Not Admin | Lecturer session; no session | 403 `forbidden`; 401 | nothing created |
| Expired before send | mail job runs after `expires_at` | skipped `no_recipient` | — |

</intent-contract>

## Code Map

- `backend/app/modules/identity/{models,repo,service,routes,schemas}.py` -- add `invitations`; repo SQL (insert, void open, by id, ids for e-mail, advisory lock); `service.send_invitation(actor, email, role, now)`, `invitation_mail_recipient(session, ref, now)`, `invitation_ids_for_email(session, address)`, `INVITATION`, `INVITATION_LINK_PATH = "/invitasjon"`, `email_is_valid`; `admin_router = APIRouter(prefix="/api/admin")`; `InvitationIn`/`InvitationOut`. Pattern: `request_password_reset` (one `begin()` block, notify in same tx, ids-only log).
- `backend/app/platform/audit.py` (new) -- table, append-only trigger DDL lives in the migration; `record`, `events_for_target` (read helper for tests/3.12).
- `backend/app/platform/config.py` -- `role_invitation_valid_days: int = Field(14, ge=1)`.
- `backend/app/platform/authz.py` -- `users.manage` already exists (Admin only).
- `backend/app/modules/messaging/delivery.py` -- `RefResolver` gets `now`; `KINDS` + `invitation`. `service.py:_recipient` passes `now`; `latest_sent_mail` includes Invitation refs. `repo.latest_sent_for_user` → `latest_sent_for(session, user_id, refs)` joining `notices` by `notice_ids`.
- `backend/app/main.py` -- include `identity_routes.admin_router`.
- `backend/migrations/versions/0018_invitations_audit.py` (new); `migrations/env.py` -- import `app.platform.audit`.
- `backend/app/platform/email/templates/kinds/invitation.{txt,html}.j2` -- from `password_reset.*`.
- Tests: `tests/test_migrations.py` (`HEAD`="0018", tables), `tests/conftest.py` (`IDENTITY_TABLES`, `MAIL_TABLES` + `invitations, audit_events`), `tests/messaging/test_delivery.py` (three test resolvers take `now`), `tests/identity/helpers.py` (`client`, `login`, `CSRF`), `tests/messaging/helpers.py` (`drain`, `mails`, `rows`, `deliveries`).
- `frontend/src/modules/identity/home-page.tsx` -- extract the guard (Skjelett, redirect to «Logg inn», AccessDenied) for reuse; `page-shell.tsx` gets optional `crumbs`; `components/breadcrumb.tsx` exists.
- `frontend/src/components/segmented-choice.tsx` (new) -- Valgknapper per DESIGN.md `segmented-choice` tokens; `globals.css:33` focus-visible.
- `frontend/src/modules/identity/forgot-form.tsx` -- form pattern to mirror; `validate-login.ts` `validateEmail`.
- `frontend/src/lib/api/{openapi.json,schema.ts}` -- `uv run python -m app.openapi ../frontend/src/lib/api/openapi.json`, then `npm run api:generate`.
- `frontend/e2e/support/auth.ts` (`loginByApi`, `latestMail`, `nextMail`), `e2e/password-reset.spec.ts` (`expectAccessible`).

## Tasks & Acceptance

**Execution:**
- `backend/app/platform/config.py`, `platform/audit.py`, `migrations/versions/0018_invitations_audit.py`, `migrations/env.py` -- setting, audit, schema.
- `backend/app/modules/identity/*`, `app/main.py` -- table, service, admin route.
- `backend/app/modules/messaging/{delivery,service,repo}.py`, `kinds/invitation.{txt,html}.j2` -- kind, resolver with `now`, dev mailbox lookup.
- `backend/tests/identity/test_invitations.py` (new) -- every matrix row through the api and `drain()`, plus no e-mail/token in logs, job args or audit rows; `backend/tests/platform/test_audit.py` (new) -- `@` refused, UPDATE/DELETE refused; `tests/messaging/test_dev_mailbox.py` -- Invitation mail found by address. Update guard tests and fixtures.
- `frontend/src/copy/nb.ts` -- `admin.area` link, `admin.users` section.
- `frontend/src/components/segmented-choice.tsx`, `src/modules/identity/{home-page,page-shell}.tsx`, `src/modules/admin/{api.ts,invite-form.tsx,users-page.tsx}`, `src/app/(app)/admin/brukere/page.tsx`, `src/app/(app)/admin/page.tsx` -- the page.
- `frontend/src/modules/admin/invite-form.test.tsx`, `src/components/components.test.tsx` -- Vitest for validation copy mapping and the segmented choice.
- `frontend/e2e/admin-invite.spec.ts` (new) -- 320 px, 320 × 256 (400 % zoom), 1280 px at 200 % text, 1440 px: axe + no page scroll on form, invalid and result states; one test follows the mail to the dev mailbox; a Lecturer gets the denied page with no form.

**Acceptance Criteria:**
- Given an Admin on «Brukere og roller», when an e-mail and a role are entered and «Send Invitasjon» pressed, then the result line shows and the Invitation mail with an `/invitasjon#…` link arrives in the dev mailbox within seconds on the compose stack.
- Given the page at 320 px, 320 × 256, 200 % text and 1440 px, then axe (WCAG 2.1 AA) finds nothing, nothing scrolls sideways, there is one primary button, and the form is one column.
- Given the full suites, then everything passes and no new test takes over 1 s.

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 38 findings — high 0, medium 0, low 23, false 11, maybe-false 4
- findings:
  - Blind Hunter:
    - `[low]` `reject` The invite route has no rate limit. It is Admin-only and every send is audited; the story asks for no limit.
    - `[false]` `reject` An address that already has an account gets an Invitation. FR-4 and Story 3.8 say an Invitation to an existing account adds the role at acceptance, so sending is right.
    - `[low]` `reject` `/invitasjon#…` opens no page until Story 3.8 builds «Du er invitert». The story order puts the page in 3.8; a placeholder would be thrown away.
    - `[maybe-false]` `reject` Python and Postgres lower-casing could disagree and break `ck_invitations_email_normalised` (500). Python lower-cases at least as much as Postgres, so a Python-lowered value stays equal under `lower()`; a non-ASCII address test against the DB collation would settle it. If true it is low, and `users.email` has had the same rule since 3.2.
    - `[low]` `reject` `TRUNCATE` bypasses the append-only trigger. Same as `seat_occupancy`; the app never truncates, and the test fixtures rely on it.
    - `[low]` `reject` The `@` guard does not keep names out, and `bytes` would pass as a sequence. The guard is a backstop; callers pass ids and codes only.
    - `[low]` `reject` `events_for_target` has no JSON index. The table is tiny; Story 3.12 designs the read path.
    - `[low]` `reject` A server 422, a > 320-character address or a 401/403 mid-form shows the general line. Client and server check the same rules; the rest is rare.
    - `[low]` `patch` An earlier result line stayed beside a new invalid-address reason. `onSubmit` now clears it on every press.
    - `[low]` `patch` The result line was focused and also `role="status"`, so it could be read twice. `role="status"` removed; focus reads it, as on «Glemt passord».
    - `[low]` `reject` Admins cannot list or cancel open Invitations. Stories 3.9 and 3.10 add the list and resend.
    - `[low]` `reject` An expired, unaccepted row still counts as open for the unique index. Intended: sending again voids it; Story 3.8 reads `expires_at` (no background job).
    - `[low]` `reject` Segments that wrap (320 px and 200 % text together) keep a −1 px offset and square corners. A combination the story does not test; cosmetic.
    - `[false]` `reject` `AccountRole(role)` repeats the type's validation. Harmless; the service is also called with plain strings (tests, Story 3.8).
    - `[low]` `patch` The `InvitationIn` docstring put an internal note into OpenAPI. Moved to a code comment.
    - `[low]` `reject` Limit tests (320 chars, `ge=1`) and «én dag» for a few hours left are missing. Rounding up matches 3.6's late-mail rule.
  - Edge Case Hunter:
    - `[low]` `patch` An address with NUL passed the check and Postgres refused it (500). `email_is_valid` now refuses control characters; the malformed test has `a\x00@c.no`.
    - `[maybe-false]` `reject` Unicode lower-casing mismatch (duplicate). See above.
    - `[low]` `reject` Other DB errors in `send_invitation` answer 500. No reachable one was shown besides NUL, which is fixed.
    - `[low]` `reject` Over 320 characters gives the general line (duplicate).
    - `[low]` `reject` A server `fields.email` is not shown on the field (duplicate).
    - `[false]` `reject` A User who holds the role is invited again (duplicate of the existing-account row).
    - `[false]` `reject` The template's role map raises for another role. `AccountRole` has only `admin` and `lecturer`, and `ck_invitations_role` enforces it.
    - `[low]` `reject` A huge `ROLE_INVITATION_VALID_DAYS` overflows. A configuration mistake no one makes.
    - `[false]` `reject` The acting Admin deleted mid-request. Users are never deleted (deactivation only), and the FK is `SET NULL`.
    - `[false]` `reject` The dev mailbox returns nothing when the newest sent mail belongs to a voided Invitation. The newer Invitation's mail, once sent, is the newest; Playwright polls until it is.
    - `[low]` `reject` The spec names `invite-form.test.tsx`; the file is `.ts`. The fix is a spec edit.
    - `[low]` `reject` The spec names an `admin.area` copy key; the key is `admin.sections`. The fix is a spec edit.
  - Verification Gap:
    - `[low]` `patch` The form's failure path was untested. Added the Playwright test `a send that fails says so beside the button and keeps the address` (500 via `route.fulfill`).
  - Intent Alignment (descriptive divergences):
    - `[maybe-false]` `reject` The token is an HMAC of the id under a server secret, not separate random bytes. As in 3.6; the founder's meaning of "random" settles it. If true it is low: unguessable without the secret, stored only as a hash.
    - `[false]` `reject` `audit.record` takes `session` and `at` besides `(actor, action, target, change)`. The four named parameters are there; the transaction and the clock must come from the caller (Issue #63).
    - `[low]` `reject` The link opens no page yet (duplicate).
    - `[false]` `reject` "An api test finds exactly one open Invitation" is done by SQL after the api calls. The test drives the api and checks the stored outcome, as every api test here does.
    - `[low]` `reject` The Playwright malformed-address test does not prove no request left. The api test proves the server stores nothing; the client returns before `mutate`.
    - `[maybe-false]` `reject` Same-transaction audit is shown only indirectly. Code inspection shows one `begin()` block; a forced-rollback test would settle it. If true it is low.
    - `[false]` `reject` 400 % zoom and 200 % text are emulated. A 320 × 256 viewport is what 400 % of 1280 px is, and the root font size is what text size scales (rem layout); `logg-inn.spec.ts` does the same.
    - `[false]` `reject` "One primary button" is checked as one button in `main`. The page has exactly one button, and it is primary.
    - `[false]` `reject` `messaging` asks `identity` for Invitation ids by address. Only the local dev mailbox does, through `identity.service`, as `test_imports` requires.

## Design Notes

- **HMAC token, as in 3.6.** The mail is rendered at send time, so the link must be rebuildable from the id without storing the token. Rotating `JWT_SECRET` voids open Invitations.
- **`now` for ref resolvers.** The Invitation's expiry is read from `expires_at`; the resolver needs the job's clock, so the 3.5 signature grows one argument rather than reading a global clock.
- **Audit without FK.** History must outlive any later cleanup of `users`, and `platform` stays free of module tables.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/identity tests/messaging tests/platform/test_audit.py tests/test_authz_rules.py tests/test_imports.py tests/test_migrations.py` -- expected: pass
- `cd backend && uv run pytest --durations=15 && uv run ruff check . && uv run ruff format --check .` -- expected: pass
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- expected: pass
- `docker compose up -d --build --wait proxy worker-batch && cd frontend && npx playwright test` -- expected: pass

## Auto Run Result

Status: done

**Summary.**
- `identity` owns `invitations` (address, role, SHA-256 of the token, `created_at`, `expires_at`, `accepted_at`, `voided_at`, `invited_by`). A partial unique index keeps one open Invitation per address and role.
- `POST /api/admin/invitations` `{email, role}` (policy `users.manage`, Admin only) answers `201 {id, email, role, expires_at, valid_days}`, or `422 invalid_request` with `fields.email = invalid_email`. One transaction: an advisory lock on address and role, void the open Invitation, insert the new one, enqueue the `invitation` notice by reference, write one audit row.
- `platform/audit.py`: `audit_events` with an append-only trigger and `record(session, actor, action, target, change, at)`, which refuses any string holding `@`. Sending writes `invitation.sent` with the Invitation id, the role and any voided ids.
- `messaging`: `invitation` is an `immediate` kind. `RefResolver` now gets the job's clock. `identity.invitation_mail_recipient` gives the address, the link `/invitasjon#<token>`, the role and the days left, or None for an accepted, voided or expired Invitation (skipped `no_recipient`). The mail is «Invitasjon til ØL-spillet».
- The dev mailbox also finds Invitation mails by address.
- Web: the Admin-område lists «Brukere og roller» (`/admin/brukere`): breadcrumb, h1, «Inviter» with a lead stating the consequence, Tekstfelt «E-post», Valgknapper «Rolle» (Faglærer / Admin, a new `SegmentedChoice` of native radios) and the primary «Send Invitasjon». The reason updates as the address is typed; the result line takes focus; a failure reads «Invitasjonen ble ikke sendt. Prøv igjen.» A non-Admin gets the permission-denied page. `HomePage`'s guard is now `GuardedPage`; `PageShell` takes `crumbs`.

**Files changed:**
- Backend: `app/platform/{audit.py (new),config.py}`, `app/modules/identity/{models,repo,service,routes,schemas}.py`, `app/modules/messaging/{delivery,service,repo}.py`, `app/main.py`, `kinds/invitation.{txt,html}.j2`, `migrations/versions/0018_invitations_audit.py`, `migrations/env.py`.
- Backend tests: new `tests/identity/test_invitations.py`, `tests/platform/test_audit.py`; updated `test_dev_mailbox.py`, `test_delivery.py` (resolvers take `now`), `test_migrations.py`, `conftest.py`.
- Frontend: `copy/nb.ts` (`admin`), `components/segmented-choice.tsx`, `modules/admin/{api.ts,invite-form.tsx,users-page.tsx,invite-form.test.ts}`, `app/(app)/admin/brukere/page.tsx`, `modules/identity/{home-page.tsx,page-shell.tsx,homes.ts}`, regenerated `lib/api/{openapi.json,schema.ts}`, `components/components.test.tsx`, `e2e/admin-invite.spec.ts` (new), `e2e/homes.spec.ts` (the Admin home now has one link).

**Review.** 38 findings: 0 high, 0 medium, 23 low, 11 false, 4 maybe-false. Patched (all low): the stale result line, the double announcement, the OpenAPI docstring, NUL in an address, the untested failure path. Nothing deferred. Every rejection has its reason in the triage log.

**Follow-up review recommended: false.** Only low entries were patched (5 low, 0 medium, 0 high).

**Verification:**
- Backend `uv run pytest`: 1734 passed in 72 s; `ruff check` and `ruff format --check` clean. New backend tests each under 1 s (slowest 0.43 s).
- Frontend: `typecheck`, Vitest (255 passed), `check:copy` (11 templates), `lint:colours` and `build` pass. Playwright: 67 passed on the compose stack with `worker-batch`. The new UI tests take 2–4 s each (login and three axe runs per viewport); one test waits for a real mail.
- Migration 0018 is new. It ran on the shared `olspillet_test*` databases and was not changed afterwards.
- Matrix audit: Send → `test_the_admin_sends_one_invitation…`; Validity setting → `test_an_admin_invitation_and_the_validity_follow_the_setting`; Malformed → `test_a_malformed_address_is_refused…` (9 cases); Send again → `test_sending_again_voids_the_earlier_link…`; Other role → `test_an_invitation_for_another_role_stays_open_beside_it`; Parallel → `test_parallel_sends_leave_exactly_one_open_invitation`; Not Admin → `test_only_an_admin_may_invite` (3 cases); Expired before send → `test_an_invitation_that_expires_before_its_mail_leaves_is_not_mailed`.
- Builder's visual check (screenshots at 390 and 1280 px of the Admin-område, the invalid state and the sent state): one column, the tokens and type of `/logg-inn`, no sideways scroll.

**Decisions taken in place of the founder:**
- Route `/admin/brukere` for «Brukere og roller»; the Admin-område lists it as a Lenke row (`09-alle-sider.png`).
- The link is `/invitasjon#<token>` (the page comes in Story 3.8). The token is an HMAC of the Invitation id, as in 3.6; only its hash is stored.
- Sending again voids only the open Invitation for the same address *and* role; an address may hold one open Invitation per role.
- An Invitation to an address that already has an account, or the role, is sent anyway (Story 3.8 adds the role at acceptance).
- No rate limit on the Admin route.
- Audit rows: action `invitation.sent`, target `{invitation_id}`, change `{role, voided_invitation_ids?}`; no FK; append-only trigger.
- Faglærer is preselected. After a send the address is emptied and the role kept.
- Draft copy marked [ASSUMPTION] in `nb.ts`: «Inviter», the lead, «Send Invitasjon», the result line, «Skriv e-postadressen.», the failure line. The mail text is also a draft.
- The implementation and the review fixes were done in this context, as the caller instructed. The four reviewers ran as subagents; their reports were read from their transcripts.

**Residual risks:**
- Until Story 3.8 the mailed link opens «Fant ikke siden.».
- The `SegmentedChoice` segments can wrap at 320 px with 200 % text (cosmetic).
