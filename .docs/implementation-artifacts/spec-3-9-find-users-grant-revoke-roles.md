---
title: 'Story 3.9: Find Users and grant or revoke roles'
type: 'feature'
created: '2026-11-18'
status: 'done'
baseline_revision: 'de1ac8d98769cfc8fd5c897c67c47130e4a3c91c'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-3-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-3-8-create-account-from-invitation.md'
warnings: [oversized]
deferred: []
---

<intent-contract>

## Intent

**Problem:** «Brukere og roller» (`/admin/brukere`) only has the invite form: the Admin cannot see or search the Users, and cannot grant or revoke the Lecturer or Admin role on an existing account. There is no guard against revoking the last active Admin and no hook for Epic 4 to block revoking a Lecturer who owns Classes.

**Approach:** `identity` gets an Admin list route (search, cursor, list envelope) and grant/revoke routes that lock the User, write one audit row and emit `user:<id>` in the same transaction; revoke asks a revoke-blocker registry and the last-Admin rule first. The page gets a search field and a table of Users (reflowing to labelled blocks below laptop width) with one grant-or-revoke button per role per User. Also: raise the local Invitation accept/renewal limits in `docker-compose.yml`.

## Boundaries & Constraints

**Always:**
- `GET /api/admin/users?q=&cursor=&limit=` (policy `users.list`) → `200 {"items": [{id, name, email, roles, is_active}], "next_cursor": str | null}`. Order `lower(name), id`; keyset cursor (opaque base64url of the last row's sort key); `limit` 1–100, default 50; `q` trimmed, ≤ 200 chars, matches a case-insensitive substring of e-mail or name (`%`, `_`, `\` escaped), only in `users`. A malformed cursor → `422 invalid_request`. `q` never reaches a log line (the request log already logs the path without query string; add a test).
- `POST /api/admin/users/{user_id}/roles {role}` and `DELETE /api/admin/users/{user_id}/roles/{role}` (policy `users.manage`) → `200` with the updated list item. Unknown User → `404 not_found`. Granting a held role or revoking one not held → `200`, nothing written. Otherwise one transaction: lock the User row, change `user_roles`, `audit.record(actor, "role.granted" | "role.revoked", {user_id}, {role})`, `events.emit("user", <id>)`. Register `identity.grant_role` and `identity.revoke_role` (topic `user`) in `COMMAND_TOPICS`.
- Revoke order: advisory lock `role:<role>`, lock User, then (a) the last-Admin rule: revoking a role in `ROLES_KEEP_ONE_ACTIVE = {admin}` that would leave no other active holder → `409 last_admin`; (b) the revoke-blocker registry `identity.service.register_revoke_blocker(role, blocker)`, where `blocker(session, user_id) -> int` returns owned Classes; a positive sum → `409 role_revoke_blocked`, `fields: {"classes": n}`. Nothing changes on a 409. No blocker is registered in this story (Epic 4 registers Class ownership).
- No role comparison in `app/modules/` (the `test_authz_rules.py` AST check): role-keyed rules are dict/set lookups.
- Web (`users-page.tsx`, below the invite section): section «Brukere» with a search field (label «Søk etter navn eller e-post», runs 250 ms after typing stops, no button), a table Navn / E-post / Roller / Status with tabular figures and hairline rules; below `lg` each row is one block with each field labelled, no sideways scroll at 320 px or 200 % text. Roles read «Faglærer», «Admin» or «Ingen rolle»; status «Aktiv» / «Deaktivert». «Ingen treff.» when the search finds nothing. «Vis flere» (secondary) loads the next page. Skjelett while the first page loads, page-error line on failure.
- Per User, one button per role, labelled with its effect and the User's first name: «Gi Bård rollen Faglærer» / «Fjern rollen Faglærer fra Bård» (same for Admin); no confirmation dialog; secondary variant (the invite button stays the only primary). The pressed button keeps focus; its label flips when the row updates. A result line in the row (`role="status"`) states the change; a refusal shows in the row with `role="alert"`: blocked → «Bård eier 2 Klasser. Legg til en annen Faglærer eller arkiver Klassene først.» (1 → «Bård eier 1 Klasse. … arkiver Klassen først.»), `last_admin` → «Bård er den eneste aktive Admin. Gi en annen bruker rollen Admin først.», other → «Rollen ble ikke endret. Prøv igjen.». Result and refusal lines clear when the search changes or another role button is pressed. Revoking one's own Admin role refreshes `meKey`.
- Copy in `nb.ts` under `admin.users.list`, drafts marked [ASSUMPTION].
- `docker-compose.yml` backend: `INVITATION_ACCEPT_RATE_LIMIT_PER_IP` 10000, `…_PER_INVITATION` 1000, `INVITATION_RENEWAL_RATE_LIMIT_PER_IP` 10000, `…_PER_INVITATION` 1000, with a comment like the Story 3.6 one.

**Never:** No deactivate/reactivate, resend or Invitation list (Story 3.10); no audit page (3.12); no Class tables or real blocker (Epic 4); no confirmation dialogs; no name, e-mail or query text in log lines, audit rows or events; no edits to `sprint-status.yaml`, `.env`, `.claude/settings*.json`; no DB-clock vs host-clock comparisons.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| List | 3 Users, no `q` | 200, items by name with roles and `is_active`, `next_cursor` null | — |
| Paging | 5 Users, `limit=2` | pages 2+2+1 by cursor, no repeats, last `next_cursor` null | bad cursor → 422 |
| Search | `q=" KARI "`, `q="example.com"`, `q="%"` | matching Users only; `%` matches literally | none → `items: []` |
| Not Admin | Lecturer calls any route | 403 `forbidden`; no session → 401 | — |
| Grant | User without lecturer | 200 roles incl. lecturer; one `role.granted` row; `user:<id>` emitted; User's next `/me` shows it | already held → 200, no row |
| Revoke | User with lecturer | 200; one `role.revoked` row; emitted; next `/me` lacks it | not held → 200, no row |
| Last Admin | only active Admin revokes own Admin | 409 `last_admin`; role kept; no row | — |
| Other Admin | two active Admins, one revokes own | 200 | — |
| Parallel | two Admins revoke each other's Admin at once | exactly one succeeds, one 409 `last_admin` | advisory lock |
| Blocked | test blocker reports 2 for the User | 409 `role_revoke_blocked`, `fields.classes = 2`; role kept; no row | — |
| Unknown | random user_id / bad role | 404 `not_found` / 422 | — |

</intent-contract>

## Code Map

- `backend/app/modules/identity/service.py` -- add `list_users`, `grant_role`, `revoke_role`, `register_revoke_blocker`, `RoleRefused`. Reuse `_user_out` (L62), `repo.lock_user` (L83 repo), `repo.grant_role` (L227 repo, ON CONFLICT), advisory-lock pattern `repo.lock_invitation_address` (L118 repo), `audit.record`.
- `backend/app/modules/identity/repo.py` -- add `list_users(q, after, limit)` (ILIKE with escape, keyset on `(lower(name), id)`, roles aggregated), `remove_role`, `count_active_holders(role, excluding)`, `lock_role(role)`.
- `backend/app/modules/identity/schemas.py` -- `UserListItem`, `UserListOut` (`items`, `next_cursor`), `RoleIn`.
- `backend/app/modules/identity/routes.py` -- three routes on `admin_router` (`/api/admin`), errors via `error_response` (`platform/errors.py`).
- `backend/app/platform/events/{__init__.py (emit),registry.py (COMMAND_TOPICS)}`; `platform/authz.py` POLICIES has `users.list`, `users.manage` already.
- `backend/app/platform/logging.py:124` -- request log uses `scope["path"]` (no query string); Caddy has no access log; uvicorn runs `--no-access-log`.
- Tests: `backend/tests/identity/helpers.py` (`client`, `login`, `CSRF`), `tests/identity/test_invitations.py` (`clock` fixture pattern), `tests/messaging/helpers.py` (`rows`), `tests/platform/test_notify.py` (LISTEN pattern for emitted events), `tests/conftest.py` `identity_db`.
- `frontend/src/modules/admin/{users-page.tsx,api.ts,invite-form.tsx}`; `components/{button.tsx,text-field.tsx,skeleton.tsx,action-error.tsx}`; `lib/page-state.ts` (`usePageState`); `lib/api/mutation.ts` (`request`, `useAction`, `errorCode`); `modules/identity/api.ts` (`meKey`).
- `frontend/e2e/admin-invite.spec.ts` -- `expectOneColumnWithOnePrimary` counts `main button` == 1: scope to the invite form. `e2e/invitation.spec.ts` shows how to make a fresh account by api invite + accept.
- Regenerate: `cd backend && uv run python -m app.openapi ../frontend/src/lib/api/openapi.json`, then `npm run api:generate`.

## Tasks & Acceptance

**Execution:**
- `docker-compose.yml` -- raise local Invitation accept/renewal limits.
- `backend/app/modules/identity/{schemas,repo,service,routes}.py`, `backend/app/platform/events/registry.py` -- list, grant, revoke, blocker registry, last-Admin rule.
- `backend/tests/identity/test_user_roles.py` (new) -- every matrix row; event emitted; query text absent from captured logs; audit rows hold ids only.
- `frontend/src/copy/nb.ts` -- `admin.users.list`.
- `frontend/src/modules/admin/{api.ts,user-list.tsx (new),user-list.ts (new: firstName, role-button label, refusal text),users-page.tsx}`; regenerate `lib/api/{openapi.json,schema.ts}`.
- `frontend/src/modules/admin/user-list.test.ts` (new) -- first name, labels, refusal lines (plural).
- `frontend/e2e/admin-users.spec.ts` (new) -- search + «Ingen treff.»; grant Lecturer to a fresh Admin-only account, which then opens `/laererhjem`; revoke Admin, which then gets the permission-denied page on `/admin`; blocked and last-Admin lines (route-fulfilled 409s); axe at 320 px, 200 % text and 1440 px with no sideways scroll. `e2e/admin-invite.spec.ts` -- scope the one-primary check to the form.

**Acceptance Criteria:**
- Given the Admin on «Brukere og roller» at 320 px, 200 % text and 1440 px, then the User list shows Navn, E-post, Roller and Status (labelled blocks below laptop width), axe finds nothing and nothing scrolls sideways.
- Given a grant or revoke pressed, then no dialog appears, focus stays on the pressed button, the row shows the new roles, and the affected User's next page load follows the new role.
- Given the full suites, then everything passes and no new backend test takes over 1 s.

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 44 findings — high 0, medium 4, low 37, false 3, maybe-false 0 (the 4 medium rows form 2 groups)
- note: the four reviewers ran as background subagents; their final reports were read from their transcripts after they went idle.
- findings:
  - Blind Hunter:
    - `[low]` `reject` Cursor holds only the id; a rename between pages re-sorts. No rename exists in the product; the id-cursor keeps names out of URLs (Design Notes). The unknown-id part is patched below.
    - `[low]` `patch` Last-Admin rule refused revoking a deactivated Admin's role. Rule now applies only to an active target; test `test_a_deactivated_admin_loses_the_role_even_with_no_other_active_holder`.
    - `[low]` `patch` `role_granted` logged before commit. Logged after the transaction, like revoke.
    - `[low]` `patch` Role buttons' secondary variant unpinned. E2e asserts one `bg-ink` (primary) button in `main`.
    - `[low]` `patch` Too-long `q` not tested for echo. Test: 201 chars → 422, text in neither body nor logs (the handler returns field names only).
    - `[low]` `patch` limit 0/101, default 50, `_` and `\` literal matches untested. Tests added.
    - `[medium]` `patch` Parallel-revoke test passed without the lock. An admin-role test blocker now holds each revoke until the other has counted (0.3 s cap); verified to fail with `lock_role` removed.
    - `[low]` `reject` Old search rows stay pressable while a new search loads. Each row is a real User with correct labels; the action names the User; keeping rows avoids a Skjelett per key.
    - `[low]` `patch` A refusal leaves the row stale. `onError` re-reads the list; the general line covers 404 (no delete exists yet).
    - `[low]` `patch` «Vis flere» untested in the browser. E2e `paging` route-fulfils two pages and checks the cursor and the appended row. Skjelett/page-error/250 ms states reuse `usePageState` (tested in Story 3.4); reject the rest.
    - `[low]` `reject` Narrow layout drops table semantics. Each field is labelled in place; axe passes at 320 px and 200 % text in `admin-users.spec.ts`.
    - `[low]` `patch` Skjelett had 3 columns. Now 4 data columns.
    - `[low]` `reject` `RoleRefused.code` is a plain str. Three codes, all mapped; same pattern as `AcceptRefused` (3.8).
    - `[low]` `reject` No index for search/order. Hundreds of Users; an index is new schema for no measured need.
    - `[low]` `reject` A blocker can register twice. Modules import once; tests reset the registry.
    - `[low]` `reject` E2e accounts pile up. Same pattern as 3.7/3.8 fresh addresses; the local DB is disposable.
  - Edge Case Hunter:
    - `[low]` `reject` Rename re-sorts the cursor (duplicate of the Blind Hunter row).
    - `[low]` `patch` A well-formed cursor naming no User gave 200 `[]`. Now 422 `invalid_request`; case added to the cursor test.
    - `[low]` `reject` `q` over 200 only by padding is refused. Nobody pads 200 spaces; the field now stops at 200.
    - `[low]` `patch` Typing over 200 chars gave the page-error line. Search field `maxLength=200`.
    - `[medium]` `patch` A failed «Vis flere» hid all rows. Next-page errors keep the rows and show «Flere brukere kunne ikke lastes. Prøv igjen.» under them.
    - `[low]` `reject` Actor loses Admin between policy and lock. Authz runs per request; the window is milliseconds and the actor was an Admin when they pressed.
    - `[low]` `patch` A negative blocker count cancels another. Counts are clamped at 0; test `test_a_negative_count_cannot_cancel_another_blocker`.
    - `[low]` `patch` Grant log before commit (duplicate, patched).
    - `[low]` `patch` E2e contexts leak. The demo-Admin context is closed after the invite.
    - `[low]` `reject` Claim: cursor is id, not sort key (duplicate; Design Notes record it).
    - `[false]` `reject` Claim: padded `q` refused contradicts the spec. The spec says trimmed and ≤ 200; the raw cap is the transport limit, and the field caps input.
    - `[false]` `reject` Claim: helpers live in `user-roles.ts`, not `user-list.ts`. Renamed because `user-list.ts` and `user-list.tsx` collide in module resolution; recorded in the Auto Run Result.
    - `[medium]` `patch` Claim: failed later page discards the list (duplicate of the «Vis flere» row).
  - Verification Gap:
    - `[low]` `patch` Own-Admin revoke never shows `meKey` refresh. E2e `own role`: a fresh Admin revokes their own Admin role and sees the permission-denied page without a reload.
    - `[low]` `patch` «Vis flere» untested (duplicate, patched).
    - `[medium]` `patch` Parallel test timing-dependent (duplicate, patched).
    - `[low]` `patch` Tied sort names untested. Paging test now has «Bo» and «bo».
    - `[low]` `patch` One-primary unpinned (duplicate, patched).
  - Intent Alignment (divergences):
    - `[low]` `reject` Playwright blocked state uses a faked 409, not the registry. No Class exists before Epic 4; the api tests drive a real registered blocker; Design Notes record it.
    - `[low]` `reject` The «2» in Playwright comes from the stub. The server count is asserted in the api test.
    - `[low]` `reject` Lecturer revoke next-request proved only at the api. Same `load_user` path as the Admin revoke proved in the browser.
    - `[low]` `reject` Grant to a role-less User not exercised. Same code path as the tested grant.
    - `[low]` `reject` Logging tested in-process only. uvicorn runs `--no-access-log`, Caddy has no access log, and the request log uses the path without the query string.
    - `[low]` `reject` «Deaktivert» never rendered in a test. `is_active: false` is asserted at the api; the cell is a plain ternary.
    - `[low]` `patch` «Vis flere» page coverage (duplicate, patched).
    - `[low]` `reject` Block layout at 320 px not asserted directly. No sideways scroll, axe and 44 px targets pass there; screenshots checked.
    - `[false]` `reject` Last-Admin rule not in the intent. The story's AC (epics.md:1872) requires `last_admin`.
    - `[low]` `reject` `docker-compose.yml` limits not in the story. A separate task from the coordinator for this run.

## Design Notes

- **No-op grant/revoke writes nothing.** An audit row records a change; pressing a stale button that changes nothing is not one.
- **Last-Admin under a role lock.** Without `pg_advisory_xact_lock('role:admin')` two Admins revoking each other could both pass the count. Story 3.10's deactivation must take the same lock.
- **The cursor is the last row's id** (base64url of its 16 bytes): the api looks up that User's sort name, so no name travels in a URL.
- **Reflow by container query in `em`** (`@container`, `@max-[60em]:`): a media query does not see 200 % text, so the table would scroll sideways at 1280 px with doubled text.
- **Playwright blocked state by a route-fulfilled 409**, since no Class exists yet to make a real blocker report; the api tests register a real test blocker through `register_revoke_blocker`.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/identity/test_user_roles.py tests/test_authz_rules.py` -- expected: pass
- `cd backend && uv run pytest --durations=15 && uv run ruff check . && uv run ruff format --check .` -- expected: pass
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- expected: pass
- `docker compose up -d --build --wait proxy worker-batch && cd frontend && npx playwright test` -- expected: pass

## Auto Run Result

Status: done

**Summary.** `GET /api/admin/users` (search by part of e-mail or name in `users` only, `(lower(name), id)` keyset cursor, list envelope), `POST /api/admin/users/{id}/roles` and `DELETE /api/admin/users/{id}/roles/{role}`: grant and revoke lock the User and write one audit row (`role.granted`/`role.revoked`) and emit `user:<id>` in one transaction; revoke refuses `last_admin` under a `role:<role>` advisory lock and asks a revoke-blocker registry (`409 role_revoke_blocked`, `fields.classes`). «Brukere og roller» gets a «Brukere» section: search field (250 ms), table Navn/E-post/Roller/Status/Endre rolle that reflows to labelled blocks by container width in `em`, one grant-or-revoke button per role with the first name, row result/refusal lines, «Vis flere». Local compose raises the Invitation accept/renewal limits.

**Files changed:** backend `identity/{schemas,repo,service,routes}.py`, `platform/events/registry.py`, `tests/identity/test_user_roles.py` (new); frontend `copy/nb.ts`, `lib/api/client.ts` (`ApiRequestError.fields`), regenerated `lib/api/{openapi.json,schema.ts}`, `modules/admin/{api.ts,users-page.tsx,user-list.tsx (new),user-roles.ts (new),user-roles.test.ts (new)}`, `e2e/admin-users.spec.ts` (new), `e2e/admin-invite.spec.ts` (selectors scoped to the form); `docker-compose.yml`. The spec's `user-list.ts` became `user-roles.ts` (it collided with `user-list.tsx`).

**Review.** 44 findings: 0 high, 4 medium (2 groups), 37 low, 3 false. Patched by entry verdict: 2 medium, the rest low. Patched: failed «Vis flere» keeps rows; deterministic lock test (fails without the lock); unknown-id cursor → 422; last-Admin rule only for an active target; blocker counts clamped; grant log after commit; list re-read on refusal; search `maxLength`; Skjelett columns; e2e for own-Admin revoke, «Vis flere», one primary button; tests for tied names, limits, literal `_`/`\`, long `q`. Nothing deferred; every rejection has its reason in the triage log.

**Follow-up review recommended: true.** Two medium entries were patched. Unverified risk: the «Vis flere» failure path (rows kept, `moreFailed` line) has no automated test; only the success path is covered by the e2e `paging` test.

**Verification:** backend `pytest` 1794 passed in 69 s, ruff clean, slowest new test 0.54 s (50-User page); frontend typecheck, Vitest 267, check:copy, lint:colours, build pass; Playwright 83 passed on the compose stack. No migration added.

**Decisions taken in place of the founder:** no-op grant/revoke writes nothing; first-name button labels «Gi Bård rollen Faglærer» / «Fjern rollen Faglærer fra Bård»; [ASSUMPTION] copy incl. «1 Klasse», the last-Admin and «Vis flere» failure lines; page size 50 (max 100); id cursor; 250 ms search; Playwright blocked/last-Admin states by route-fulfilled 409s; a deactivated Admin's role can be revoked even when no other active Admin is needed for it.

**Residual risks:** Story 3.10's deactivation must take the same `role:admin` lock to keep the last-Admin guarantee.
