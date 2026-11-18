---
title: 'Story 3.10: Deactivate and reactivate Users and resend Invitations'
type: 'feature'
created: '2026-11-18'
status: 'done'
baseline_revision: '9a7b4d2fee3a9449fef1162ebbd1bdacd7a8448b'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-3-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-3-9-find-users-grant-revoke-roles.md'
warnings: [oversized]
deferred:
  - summary: >-
      The invite form (Story 3.7) still sends a new Invitation to the address of a deactivated
      User, while resend refuses it with account_deactivated.
    evidence: |-
      send_invitation has no account check (pre-existing since Story 3.7); the mailed link then
      answers 410 at check because _usable_invitation refuses a deactivated address. Fails safe,
      but the Admin gets a success line for a dead link.
    location: >-
      backend/app/modules/identity/service.py send_invitation
    severity: low
---

<intent-contract>

## Intent

**Problem:** On «Brukere og roller» the Admin cannot deactivate or reactivate a User, cannot see the Invitations sent, and cannot resend one. A stolen session also survives a password reset (Issue #73) and would survive a deactivate-then-reactivate.

**Approach:** `identity` gets deactivate/reactivate routes (deactivate under the same `role:admin` advisory lock as revoke, so the last-Admin rule holds against both), a per-User `session_version` that the session cookie carries and every request checks (bumped on deactivation and on password reset), an Invitation list route (latest Invitation per address and role, with status and the renewal request), and a resend route. The page gets a status button per User row and an «Invitasjoner» section.

## Boundaries & Constraints

**Always:**
- Migration `0020`: `users.session_version integer NOT NULL DEFAULT 0`. The JWT gains claim `sv` (int; a token without it reads as 0, so cookies issued before the migration stay valid). `authz.current_principal` passes `(user_id, sv)` to the loader; `identity.service.load_user` returns None when the User is gone, deactivated or `sv != users.session_version`. Every place that sets the cookie (login, both Invitation accepts) issues the User's current version.
- `POST /api/admin/users/{user_id}/deactivate` and `POST /api/admin/users/{user_id}/reactivate` (policy `users.manage`) → `200` updated `UserListItem`. Unknown → `404 not_found`; already in the target state → `200`, nothing written. Deactivate: one transaction in this order — `repo.lock_role` for every role in `ROLES_KEEP_ONE_ACTIVE` (same lock and order as `revoke_role`), lock User; refuse `409 last_admin` when the target is the actor, or when the target is an active holder of a keep-one-active role and `count_active_holders(... excluding=target) == 0`; else set `is_active=false`, `session_version += 1`, `updated_at`, void the User's open `password_resets` (`voided_at`), `audit.record(actor, "user.deactivated", {user_id}, {})`, `events.emit("user", id)`. Roles, name, e-mail and password are untouched. Reactivate: lock User, set `is_active=true`, audit `user.reactivated`, emit. Register `identity.deactivate_user`, `identity.reactivate_user` (topic `user`) in `COMMAND_TOPICS`.
- Password reset confirm also bumps `session_version` (closes Issue #73: other sessions end).
- `GET /api/admin/invitations?cursor=&limit=` (policy `users.list`) → `200 {"items": [{id, email, role, status, expires_at, renewal_requested}], "next_cursor"}`: one item per (email, role) — its newest Invitation — newest first, keyset cursor on that id (base64url, unknown/malformed → `422 invalid_request`), `limit` 1–100 default 50. `status`: `accepted` if `accepted_at`; `open` if not voided and `now < expires_at` (api clock); else `expired`. `renewal_requested` true when any Invitation of that (email, role) has `renewal_requested_at` set.
- `POST /api/admin/invitations/{invitation_id}/resend` (policy `users.manage`) → `201 InvitationOut`. Unknown → `404 not_found`; accepted → `409 invitation_accepted`; not the newest of its (email, role) → `409 invitation_superseded`; address of a deactivated User → `409 account_deactivated`. Else, in one transaction under `lock_invitation_address`: void open ones of the (email, role), insert a new Invitation (new id, so a new token, new `expires_at`), clear `renewal_requested_at` on every Invitation of the (email, role), enqueue the `invitation` notice, `audit.record(actor, "invitation.resent", {invitation_id: new}, {role, resent_invitation_id: old, voided_invitation_ids?})`. `send_invitation` (invite form) clears the request mark too.
- Web, user row: the actions cell (heading «Endre») gets, after the role buttons, one status button (secondary, no dialog): active → «Deaktiver Bård. Bård kan ikke logge inn, og dataene blir værende.»; deactivated → «Aktiver Bård igjen». Result line (`role="status"`) «Bård er deaktivert.» / «Bård er aktiv igjen.»; refusal (`role="alert"`): own row «Du kan ikke deaktivere deg selv.», `last_admin` → the Story 3.9 last-Admin line, else «Statusen ble ikke endret. Prøv igjen.». Shares the row line of the role buttons, so any press or search change clears it.
- Web, section «Invitasjoner» below «Brukere»: table E-post / Rolle / Status / Utløper (date in Europe/Oslo, «2. des. 2026») reflowing like the User table; status «Åpen», «Akseptert», «Utløpt»; a renewal request adds the line «Mottakeren har bedt om en ny invitasjon.» under the status. Open and expired rows have a secondary button «Send ny invitasjon til kari@example.com»; accepted rows have none. Result line «Ny invitasjon sendt til kari@example.com. Den er gyldig i 14 dager.»; refusal «Invitasjonen ble ikke sendt på nytt. Prøv igjen.»; the list re-reads after a resend. «Ingen invitasjoner ennå.» when empty; «Vis flere», Skjelett and page-error as the User list. Sending from the invite form re-reads the Invitation list.
- Copy in `nb.ts` (`admin.users.list` and new `admin.users.invitations`), drafts marked [ASSUMPTION]. The invite button stays the only primary button.

**Never:** no deletion of any data on deactivation; no confirmation dialogs; no name, e-mail or token in log lines, audit rows or events; no background job for expiry; no DB-clock vs host-clock comparison in tests; no change to the audit page (3.12) or Institutions (3.11); no edits to `sprint-status.yaml`, `.env`, `.claude/settings*.json`; never deactivate the demo accounts in Playwright (fresh accounts only).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Deactivate | active Lecturer with a live cookie and an open reset link | 200 `is_active:false`; one `user.deactivated` row; `user:<id>` emitted; roles kept; their next request 401; reset link 410; login with right password 403 `account_deactivated` | already deactivated → 200, no row |
| Invitation of deactivated | open Invitation to a deactivated User's address | check → 410 `invitation_link_invalid` | — |
| Reactivate | deactivated User | 200; one `user.reactivated` row; login works with the same password and roles; the cookie from before deactivation stays rejected | already active → 200, no row |
| Self | Admin deactivates self (another Admin active) | 409 `last_admin`, nothing changes | — |
| Other Admin | two active Admins, one deactivates the other | 200 | — |
| Race | two Admins: A deactivates B while B revokes A's Admin role | exactly one succeeds, the other 409 `last_admin` | role lock; test fails without it |
| Reset ends sessions | User with a live cookie confirms a reset | that cookie → 401 | — |
| Old cookie | token without `sv`, User at version 0 | accepted | — |
| Invitation list | open, accepted, expired, voided-then-renewed rows | one item per (email, role), newest first, right status, `renewal_requested` | bad cursor → 422 |
| Resend | expired Invitation with a renewal request | 201; old link 410; new link works; mail sent; request cleared; one `invitation.resent` row | accepted → 409 `invitation_accepted`; older one → 409 `invitation_superseded`; unknown → 404 |
| Not Admin | Lecturer calls any new route | 403; no session → 401 | — |

</intent-contract>

## Code Map

- `backend/app/platform/auth.py` -- `issue_token` (L86), `read_token` (L93), `set_session_cookie` (L120): add `sv` claim and a `read_session` returning `(user_id, version)`; keep `read_token` for existing tests.
- `backend/app/platform/authz.py` -- `PrincipalLoader` (L85), `current_principal` (L95): pass the version to the loader.
- `backend/app/modules/identity/service.py` -- `load_user` (L123); `confirm_password_reset` (L240) bump version; `send_invitation` (L305) clear request mark (reuse for resend); `revoke_role` (L677) lock pattern and `ROLES_KEEP_ONE_ACTIVE`; `_invitation_open` (L296); `_encode_cursor`/`_decode_cursor` (L626) reuse for the Invitation cursor; `RoleRefused` pattern.
- `backend/app/modules/identity/repo.py` -- `lock_user`, `lock_role`, `count_active_holders`, `void_open_invitations`, `set_password_hash`; add `set_active`, `bump_session_version`, `void_open_password_resets`, `list_invitations`, `clear_renewal_requests`, `newest_invitation_id(email, role)`.
- `backend/app/modules/identity/models.py` -- `users` table: add `session_version`.
- `backend/migrations/versions/0019_invitation_renewal.py` -- pattern for `0020_user_session_version.py`.
- `backend/app/modules/identity/{schemas,routes}.py` -- `InvitationListItem`, `InvitationListOut`, `InvitationStatus`; routes on `admin_router`; login/accept routes set cookie with version (`_invitation_answer` L150, `login` L53).
- `backend/app/platform/events/registry.py` -- `COMMAND_TOPICS`.
- Tests: `backend/tests/identity/test_user_roles.py` (helpers `make`, `as_user`, `audit_rows`, the parallel-revoke hold pattern L305), `tests/identity/test_invitations.py` and `test_invitation_accept.py` (tokens via `auth.link_token`), `tests/identity/test_auth.py` (token tests), `tests/identity/test_password_reset.py`.
- `frontend/src/modules/admin/{api.ts,user-list.tsx,user-roles.ts,users-page.tsx,invite-form.tsx}`; `src/lib/connection.ts:52` (Oslo `Intl.DateTimeFormat` pattern); `frontend/e2e/admin-users.spec.ts` (`freshAdmin`, `expectAccessible`, `VIEWPORTS`), `e2e/support/auth.ts` (`latestMail`, `nextMail`).
- Regenerate client: `cd backend && uv run python -m app.openapi ../frontend/src/lib/api/openapi.json`, then `cd frontend && npm run api:generate`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0020_user_session_version.py`, `backend/app/modules/identity/models.py` -- add `session_version`.
- `backend/app/platform/{auth,authz}.py` -- `sv` claim, version-aware loader.
- `backend/app/modules/identity/{repo,service,schemas,routes}.py`, `backend/app/platform/events/registry.py` -- deactivate, reactivate, version bump on reset, Invitation list, resend.
- `backend/tests/identity/test_user_status.py` (new) -- every matrix row incl. the forced-overlap race (wrap `repo.count_active_holders` to hold each transaction after counting until the other has counted, ≤0.3 s; verify it fails with the deactivate lock removed); `tests/identity/test_invitation_list.py` (new) -- list and resend rows; `tests/identity/test_password_reset.py` -- reset ends other sessions; `tests/identity/test_auth.py` -- `sv` round trip and missing `sv`.
- `frontend/src/copy/nb.ts`; `frontend/src/modules/admin/{api.ts,user-list.tsx,user-roles.ts,invitation-list.tsx (new),invitations.ts (new: status text, Oslo date, labels),users-page.tsx,invite-form.tsx}`; regenerate `lib/api/{openapi.json,schema.ts}`.
- `frontend/src/modules/admin/{user-roles.test.ts,invitations.test.ts (new)}` -- labels, lines, status text, date.
- `frontend/e2e/admin-status.spec.ts` (new) -- deactivate a fresh account: its live context gets the session-expired state and login shows «Kontoen er deaktivert. …»; reactivate, login works; Invitation list shows a fresh Invitation, resend mails a new link that works and the old one does not; accepted row has no resend; axe at 320 and 1440 px with no sideways scroll.

**Acceptance Criteria:**
- Given an active User row, then its status button reads «Deaktiver Bård. Bård kan ikke logge inn, og dataene blir værende.», and pressing it shows no dialog, keeps focus on the button and flips it to «Aktiver Bård igjen».
- Given «Brukere og roller» at 320 and 1440 px with both lists, then axe finds nothing and nothing scrolls sideways.
- Given the full suites, then everything passes and no new backend test takes over 1 s.

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 28 findings — high 0, medium 4, low 23, false 1, maybe-false 0
- note: the four reviewers ran as background subagents; their final reports were read from their transcripts.
- findings:
  - Blind Hunter:
    - `[low]` `patch` Resend offered on rows of deactivated accounts, always refused with a general line. `account_deactivated` now has its own line («Kontoen med denne adressen er deaktivert. …»), and deactivation voids the open Invitations, so such rows read «Utløpt».
    - `[low]` `defer` The invite form still sends to a deactivated account's address. Pre-existing Story 3.7 path; fails safe (link 410). Deferred in frontmatter.
    - `[medium]` `patch` Dead Invitations to a deactivated User listed as «Åpen». `deactivate_user` now voids open Invitations to the address (`repo.void_open_invitations_to`); `useChangeStatus` re-reads the Invitation list; the api test asserts voided_at and status `expired`.
    - `[medium]` `patch` The self-deactivate e2e pressed the real button for the demo Admin. The test now route-fulfils the 409, so a broken server check cannot deactivate the demo account.
    - `[low]` `reject` `accept_invitation_new` returns version 0. The row is inserted in that same transaction with the column default 0; nothing bumps it there. The cookie path is now covered by the version > 0 test below.
    - `[medium]` `patch` No test of the accept-with-existing-account cookie for a User at version > 0. Test `test_an_account_whose_sessions_were_ended_gets_a_working_cookie` (deactivate + reactivate, then accept-login, `/me` 200).
    - `[low]` `patch` Only deactivate-vs-revoke raced. Added `test_two_admins_deactivating_each_other_at_once_leave_one_active_admin`. The deactivate-vs-revoke test was run with the deactivate lock removed and failed (recorded below).
    - `[low]` `reject` No index for the Invitation list query. Hundreds of rows; same reasoning as Story 3.9's list.
    - `[low]` `reject` Accepted rows crowd out open ones. Newest first keeps recent action items on page one; a filter is new surface with no measured need.
    - `[low]` `patch` «Utløpt» beside a future date for a voided Invitation (now reachable via deactivation). `expires_at` in the list is the link's end: the voiding time when earlier (`_link_end`).
    - `[low]` `reject` Resend when the address already holds the role. Rare; accepting then simply adds nothing.
    - `[low]` `reject` The Invitation row line does not clear on unrelated list re-reads. It clears on the next press; the row keeps its key, so the line still describes that row.
    - `[low]` `patch` Role names duplicated in `nb.ts`. Removed `invitations.roles`; the cell uses `list.roles` (`roleText`).
    - `[false]` `reject` Login racing a reset issues an already-dead cookie. That login used the old password; ending it with the reset is the intended Issue #73 behaviour.
  - Edge Case Hunter:
    - `[low]` `patch` Resend read the Invitation unlocked while an acceptance commits. Resend now takes `repo.lock_invitation` (FOR UPDATE) after the address lock, as acceptance does.
    - `[low]` `reject` Deactivation racing a resend. Milliseconds window; the mailed link answers 410 for a deactivated address, so it fails safe.
    - `[low]` `patch` Repeated refusal «Prøv igjen» for a deactivated address (duplicate of the first Blind Hunter row, same patch).
    - `[low]` `reject` «Vis flere invitasjoner» instead of «Vis flere». Deliberate: two buttons with one accessible name on one page are ambiguous; the fix would be a spec edit.
  - Verification Gap:
    - `[medium]` `patch` Accept-login cookie at version > 0 untested (same group as the Blind Hunter row, same test).
    - `[low]` `patch` The list re-read after a send or resend untested. E2e now presses resend twice on the same row (second succeeds, third token works) and sends from the form, expecting the row without a reload.
  - Intent Alignment (divergences):
    - `[low]` `patch` Invitations not voided at deactivation, unlike reset links (same patch as the «Åpen» row).
    - `[low]` `reject` Atomicity not proven by a failure test. One `begin()` block, same as Story 3.9's audited actions.
    - `[low]` `reject` Renewal line checked in the browser only from a fulfilled response. The flag is proven at the api; the line is a plain conditional.
    - `[low]` `reject` Expired-Invitation resend only tested at the api. Same code path as the open resend tested in the browser.
    - `[low]` `patch` Added refusals had no specific copy. `account_deactivated` has its own line; `invitation_superseded` keeps the general line and the list re-reads.
    - `[low]` `patch` axe not run on the deactivated row state. `expectAccessible` now also runs after the deactivation at 320 and 1440 px.
    - `[low]` `reject` One row per address and role, not every Invitation. Design Notes; superseded rows would offer resends that are refused.
    - `[low]` `reject` Changes beyond the story (reset ends sessions, JWT `sv`). Asked for by the run's brief (Issue #73); covered by tests.

## Design Notes

- **Session version, not a timestamp.** A `sessions_valid_after` time would compare the api clock (token `iat`) with a DB value; an integer avoids clocks (Issue #63) and makes a cookie from before a deactivation stay dead after reactivation. It closes Issue #73 at no extra cost.
- **Deactivate takes `role:admin` before the User row**, the order `revoke_role` uses, so the two can never deadlock and the last-Admin count is serialised across both.
- **Self-deactivation is always `last_admin`** (epics.md: «deactivates themselves or the last active Admin → `last_admin`»). Since only an Admin can call the route, deactivating another active Admin can only leave none in a race, which the lock prevents.
- **Resend makes a new Invitation row**: the token is derived from the id (`auth.link_token`), so a new token needs a new id; the list shows the newest row per address and role.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/identity` -- expected: pass
- `cd backend && uv run pytest --durations=15 && uv run ruff check . && uv run ruff format --check .` -- expected: pass
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- expected: pass
- `docker compose up -d --build --wait proxy worker-batch && cd frontend && npx playwright test` -- expected: pass

## Auto Run Result

Status: done

**Summary.** `POST /api/admin/users/{id}/deactivate|reactivate`: deactivation takes the `role:admin` advisory lock before the User row (the same lock and order as `revoke_role`), refuses `409 last_admin` for oneself or the last active Admin, then sets `is_active=false`, raises the new `users.session_version`, voids the User's open reset links and Invitations, writes `user.deactivated` and emits `user:<id>` in one transaction; reactivation writes `user.reactivated` and emits. The session cookie now carries `sv`; every request checks it, so a deactivation or a **password reset ends every older session** (closes the Issue #73 risk; tokens without `sv` read as 0). `GET /api/admin/invitations` lists the newest Invitation per address and role with status (open/accepted/expired from `expires_at`, no job) and the renewal request; `POST /api/admin/invitations/{id}/resend` voids the old link, mails a new token and expiry, clears the request marks and writes `invitation.resent`. «Brukere og roller» gets a status button per User row and an «Invitasjoner» section.

**Files changed:** backend `identity/{models,repo,service,schemas,routes}.py`, `platform/{auth,authz}.py`, `platform/events/registry.py`, migration `0020_user_session_version.py`; tests `identity/test_user_status.py` (new), `identity/test_invitation_list.py` (new), `test_auth.py`, `test_password_reset.py`, `test_invitation_accept.py`, `test_migrations.py` (head 0020 + downgrade test); frontend `copy/nb.ts`, `modules/admin/{api.ts,user-list.tsx,user-roles.ts,users-page.tsx,invitation-list.tsx (new),invitations.ts (new)}`, unit tests `user-roles.test.ts`, `invitations.test.ts` (new), regenerated `lib/api/{openapi.json,schema.ts}`, e2e `admin-status.spec.ts` (new), `admin-users.spec.ts` and `admin-invite.spec.ts` (selectors scoped to their section; routes pass the list GET through).

**Review.** 28 findings: 0 high, 4 medium, 23 low, 1 false. Patched: 3 medium entries (Invitations voided at deactivation and listed as expired; demo-safe self-deactivate e2e; accept-login cookie test at version > 0) and 9 low (refusal copy for deactivated accounts, `_link_end`, locked resend read, mutual-deactivation race test, duplicated role copy, list re-read e2e, axe after deactivation). Deferred 1 (invite form still sends to a deactivated address, pre-existing). Every rejection has its reason in the triage log.

**Follow-up review recommended: true.** Three medium entries were patched. Unverified risk: voiding a deactivated User's Invitations and the `_link_end` date are proven at the api only; no browser test shows the «Utløpt» row after a deactivation.

**Lock proof:** `test_a_deactivation_and_a_revoke_at_once_leave_one_active_admin` holds each transaction after its last-Admin count; with the two `lock_role` lines removed from `deactivate_user` it failed (both 200, no active Admin), with them it passes.

**Verification:** backend `pytest` 1815 passed in 68 s, ruff check/format clean; slowest new test 0.62 s. Frontend typecheck, Vitest 277, check:copy, lint:colours, build pass. Playwright on the compose stack: 89/89 before the review patches; after them 88/89 twice, each time a different `system-states.spec.ts` test (offline / page error, 1440 px) that touches no changed code and passed 30/30 when repeated alone: pre-existing load flakiness. Migration `0020` was added before the first test session of this run and not changed after it ran.

**Decisions taken in place of the founder:** self-deactivation is always `409 last_admin` (epics: «deactivates themselves or the last active Admin»), shown as «Du kan ikke deaktivere deg selv.»; a per-User session version (raised by deactivation and password reset) instead of a timestamp (no clock comparison, Issue #63), so a reactivated User's old cookies stay dead; deactivation voids open reset links and Invitations; the Invitation list shows one row per address and role (newest), newest first, page size 50; resend makes a new Invitation row and is refused for accepted (`invitation_accepted`), superseded (`invitation_superseded`) and deactivated addresses (`account_deactivated`); the invite form also clears renewal marks; [ASSUMPTION] copy: «Aktiver Bård igjen», result/refusal lines, «Invitasjoner», «Åpen/Akseptert/Utløpt», «Mottakeren har bedt om en ny invitasjon.», «Send ny invitasjon til …», «Vis flere invitasjoner», column «Endre»; Oslo date «2. des. 2026».

**Residual risks:** flaky `system-states.spec.ts` tests under full-suite load; the invite form can still mail a dead link to a deactivated address (deferred).
