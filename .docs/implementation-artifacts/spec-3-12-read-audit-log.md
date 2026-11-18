---
title: 'Story 3.12: Read the audit log'
type: 'feature'
created: '2026-11-18'
status: 'done'
baseline_revision: '69f4b37b13ecd4ff26cb2b16da5044633be7cc39'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-3-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-3-11-create-institutions.md'
warnings: [oversized]
deferred: []
---

<intent-contract>

## Intent

**Problem:** Every Admin action writes one `audit_events` row (Stories 3.7–3.11), but nobody can read them: there is no read route, no page, and no proof that each action leaves exactly one row (FR-3, NFR-7).

**Approach:** `platform/audit` gains read functions (a filtered keyset page, the distinct actors) and a label-resolver registry that owning modules fill at app start (`identity` labels `user_id`, `invitation_id`, `institution_id`). A new `modules/admin` serves `GET /api/admin/audit` and `GET /api/admin/audit/actors` behind the existing `audit.read` policy. The Admin-område links to «Revisjonslogg» (`/admin/revisjonslogg`): filters (actor, action, date range) above a table that reflows into labelled blocks below 60em.

## Boundaries & Constraints

**Always:**
- `platform/audit` keeps no update/delete; it imports no `app.modules` code. New: `register_labels(key, fn)` where `fn(ids: list[UUID]) -> dict[UUID, str]` (async, own read transaction); `labels(key, ids)` → `{}` for an unregistered key; `page(session, *, actor, action, since, until, after, limit)`; `actors(session) -> list[UUID | None]` (distinct, `None` = system). A test asserts the module's public names are `record`, read functions and the registry only, and its source contains no `.update(`/`.delete(` on `audit_events`.
- `identity.service` gets `user_labels(ids)` (name), `invitation_labels(ids)` (e-mail address), `institution_labels(ids)` (current name); `create_app()` registers them for `user_id`, `invitation_id`, `institution_id`. Names are read at request time; rows keep ids only.
- `GET /api/admin/audit?actor=&action=&since=&until=&cursor=&limit=` → `200 {"items": [{id, occurred_at, action, actor_id|null, actor_name|null, targets: [{key, id, label|null}], change}], "next_cursor"}` newest first by `(occurred_at, id)` desc; limit 1–100 default 50. `actor` = a UUID or `system` (rows with no actor); other → 422 `fields.actor = invalid_actor`. `action` ≤ 64 chars, exact match. `since`/`until` are ISO dates, inclusive Europe/Oslo days; `until < since` → 422 `fields.until = range_reversed`. Bad cursor → 422 `fields.cursor = invalid_cursor`. `targets` follow the row's `target_ids` key order; a value that is not a UUID or has no label gives `label: null`. `change` is returned as stored.
- `GET /api/admin/audit/actors` → `200 {"items": [{id|null, name|null}]}`: the system first (if present), then Users by name.
- Both routes: policy `audit.read` (Admin only; exists in `platform/authz.py`).
- One api test performs each action of the epic — Invitation sent, resent, accepted (new and existing account), bootstrap Invitation, role granted, revoked, deactivated, reactivated, Institution created, renamed — and asserts exactly one row with that action exists afterwards.
- Web `/admin/revisjonslogg`, crumbs Admin-område → Revisjonslogg; third Lenke «Revisjonslogg» in the Admin-område list. Filters (no submit button; the list re-reads on change): select «Utført av» («Alle», «Systemet», then names from `/actors`), select «Handling» («Alle» + every action in `nb.ts`), date fields «Fra og med» / «Til og med»; a reversed range shows the reason under «Til og med» and does not query.
- Table columns Tidspunkt («18. nov. 2026 kl. 13:01», Oslo) / Utført av / Handling / Gjelder / Endring. No actor → «Systemet». Action label from `nb.admin.audit.actions[action]`, else the raw code. Targets rendered by key via `nb.admin.audit.targets[key](label)`, unknown key or null label → «Ukjent». Change rendered generically: each key → `nb.admin.audit.fields[key]` label with a formatted value (roles via role names, booleans Ja/Nei, arrays as their count, `account` created/existing as copy); keys listed as hidden (ids already shown as targets: `resent_invitation_id`) are skipped; unknown keys show the raw key and JSON value. Empty change → «–».
- No filter and no rows: «Ingen hendelser ennå.»; filters and no rows: «Ingen treff.» (`role="status"`). «Vis flere hendelser», Skjelett, page-error, more-failed as the Institution list.
- Copy under `nb.admin.audit` and `nb.admin.sections.audit`, drafts marked [ASSUMPTION].

**Never:** no write route; no migration; no names or e-mails stored in audit rows; no DB-clock vs host-clock comparison in tests; no edits to `sprint-status.yaml`, `.env`, `.claude/settings*.json`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| List | 3 rows, limit 2 | newest first, `next_cursor`; second page the third | bad cursor → 422 |
| Names | role grant by Kari to Ola | `actor_name` Kari, target `{key:"user_id", label:"Ola"}` | unknown id → label null |
| System | bootstrap Invitation | `actor_id` null, `actor_name` null | — |
| Actor filter | `actor=<kari>` / `actor=system` | only Kari's / only actor-less rows | `actor=x` → 422 |
| Action filter | `action=role.granted` | only those rows; none → `items: []` | — |
| Date range | `since=until=2026-11-18` | rows on that Oslo day only (23:30 UTC on 17th counts as 18th) | until<since → 422 |
| Actors | rows by Kari, system | `[{null,null},{kari,"Kari"}]` | — |
| Not Admin | Lecturer / no session | 403 / 401 | — |

</intent-contract>

## Code Map

- `backend/app/platform/audit.py` -- table, `record`, `events_for_target`; add reads and registry here.
- `backend/app/platform/authz.py:68` -- `audit.read` policy exists (Admin only).
- `backend/app/main.py:70-90` -- `create_app()`: include new router, register labelers next to `register_principal_loader`.
- `backend/app/modules/identity/service.py` -- `_encode_cursor`/`_decode_cursor` (L657) pattern; action constants L56, L413-418, L619-622, L750-753, L824, L920-921; `ensure_bootstrap_invitations` (L1036); `get_sessionmaker().begin()` read pattern (`get_institution`, L1011).
- `backend/app/modules/identity/routes.py:460` -- list route + `error_response` + `documented` pattern.
- `backend/tests/identity/test_institutions.py`, `test_invitation_accept.py` -- fixtures `clock`, `admin`, helpers `client`, `login`, `CSRF`, `rows`; `test_authz_rules.api_routes`.
- `backend/tests/test_imports.py` -- `imports()` helper; platform imports no module.
- `backend/tests/platform/test_audit.py` -- existing audit tests.
- `frontend/src/modules/admin/{institutions-page.tsx,institution-list.tsx,api.ts,invitations.ts(formatDate),user-list.tsx(Cell,RowMessage)}` -- page/list patterns.
- `frontend/src/modules/identity/{homes.ts,home-page.tsx:49}` -- paths and `AdminSections`.
- `frontend/src/components/text-field.tsx` -- Tekstfelt styles to mirror for the select.
- `frontend/e2e/admin-institutions.spec.ts`, `e2e/support/auth.ts` -- e2e patterns.
- Regenerate client: `cd backend && uv run python -m app.openapi ../frontend/src/lib/api/openapi.json`, then `cd frontend && npm run api:generate`.

## Tasks & Acceptance

**Execution:**
- `backend/app/platform/audit.py` -- reads, registry, docstring update.
- `backend/app/modules/identity/service.py` -- three label functions.
- `backend/app/modules/admin/{__init__,schemas,routes}.py` (new) -- envelope schemas, cursor, Oslo date bounds, routes.
- `backend/app/main.py` -- router and registrations.
- `backend/tests/admin/{__init__,test_audit_log}.py` (new) -- every matrix row, the one-row-per-action test, policy test; `backend/tests/platform/test_audit.py` -- no-update/delete and public-names test.
- `frontend/src/copy/nb.ts`; `frontend/src/modules/identity/{homes.ts,home-page.tsx}`; `frontend/src/modules/admin/{api.ts,audit.ts (new: formatting),audit-filters.tsx (new),audit-list.tsx (new),audit-page.tsx (new)}`; `frontend/src/app/(app)/admin/revisjonslogg/page.tsx` (new); regenerated `lib/api/{openapi.json,schema.ts}`.
- `frontend/src/modules/admin/audit.test.ts` (new) -- time format, change formatting, unknown action/key fallbacks, range check.
- `frontend/e2e/admin-audit.spec.ts` (new) -- Admin-område link; a fresh action appears at the top with names; action filter; «Ingen treff.» via a date range with no rows; reversed range reason; Lecturer gets permission denied; axe at 320 and 1440 px with no sideways scroll. `frontend/e2e/homes.spec.ts` -- three links.

**Acceptance Criteria:**
- Given the Admin-område, when the Admin follows «Revisjonslogg», then events show newest first with Oslo time, actor name (or «Systemet»), action, target and change.
- Given a filter by actor, action or date range, when it matches nothing, then «Ingen treff.» shows.
- Given an action string not in `nb.ts` and an unknown change key, when listed, then the row still renders (raw code, raw key) with no page change.
- Given «Revisjonslogg» at 320 and 1440 px, then axe finds nothing and nothing scrolls sideways.
- Given the full suites, then everything passes and no new test takes over 1 s.

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 33 findings — high 0, medium 0, low 27, false 2, maybe-false 4 (counted per row below; maybe-false rows are claims that depend on scale or future writers)
- note: the four reviewers ran as background subagents (the run's brief); their final reports were read from their transcripts once each had ended its turn.
- findings:
  - Blind Hunter:
    - `[low]` `patch` `until=9999-12-31` overflows `until + 1 day` and answers 500 (and `since=0001-01-01` near the edge). The service now treats `date.min`/`date.max` as no bound; test `test_an_empty_actor_and_the_outermost_dates_filter_nothing` covers both ends.
    - `[low]` `reject` A target value that is not a UUID shows «Ukjent». The spec sets `label: null` for it, and every writer stores ids only (`_plain` turns UUIDs into text; no writer stores free text in `target_ids`).
    - `[low]` `reject` Two unlabelled targets look the same. Users are never deleted and every current key has a labeler; a later epic registers its own.
    - `[low]` `reject` The «Handling» filter lists only actions with an `nb.ts` entry. The story asks a later epic to add one copy entry per action; that entry also puts it in the filter.
    - `[maybe-false]` `reject` The actor list may be stale or fail silently. It is read on each page load; a failure leaves «Alle», which still works. Would need an Admin keeping the page open while a new Admin acts; impact low.
    - `[maybe-false]` `reject` No index for the filters and `DISTINCT actor_user_id`. The ordering uses `ix_audit_events_occurred_at`; the table holds Admin actions only (hundreds of rows a year). Would need a measured slow query to matter; a migration is out of proportion now.
    - `[low]` `reject` Labels are read in separate transactions from the rows. Names only, read-only; a rename between the two reads shows the newer name, which is what the story wants.
    - `[false]` `reject` `role.bootstrap_granted` is missing from the one-row test. The story's list names the bootstrap Invitation, not the production-only first-login grant; Story 3.8's tests cover that row.
    - `[low]` `reject` The AST guard is brittle and incomplete. It pins the public functions and bans update/delete names in the module; the database trigger (migration 0018) is the real guard and is tested.
    - `[low]` `reject` Unknown array fields show their length. A generic fallback; a later epic can add its field to `nb.ts`.
    - `[low]` `reject` Missing tests for `limit` bounds, long `action`, DST days, reused cursors. Declared FastAPI constraints as in the other lists; `day_start` uses `zoneinfo`, so DST is the library's.
    - `[low]` `reject` Labelers are registered only in `create_app()`. Same pattern as `register_principal_loader`; every api path builds the app.
    - `[low]` `reject` `formatTime` reuses the Invitation list's month names. `formatDate` (Story 3.10) already shares them across the Admin pages.
  - Edge Case Hunter:
    - `[low]` `patch` `until=9999-12-31` → 500 (same entry as the first Blind Hunter row).
    - `[low]` `patch` `since=0001-01-01` near the overflow edge (same entry, same fix).
    - `[low]` `reject` A year above 9999 in the date field compares wrong as text. Needs a six-digit year typed by hand; the api then answers 422 and the page error offers retry.
    - `[low]` `patch` With a reversed range, a change of actor or action was ignored. `AuditLog.change` now applies the new actor/action with the last valid dates; the e2e test checks the request carries `action` and the last `since`, and that no reversed range is ever sent.
    - `[low]` `reject` The actor list fails silently (same as the Blind Hunter row).
    - `[low]` `patch` `actor=` (empty) answered 422 while `action=` meant no filter. The route now treats an empty actor as no filter; covered by the same parametrised test.
    - `[low]` `reject` A list or null in `target_ids` would show a Python repr as `id`. No writer stores one; `record` callers pass ids.
    - `[low]` `patch` The one-row test leaked its psycopg connection on failure. It is now a fixture with `with`.
    - `[low]` `reject` (claim) A labelled target with a key not in `nb.ts` shows its label, not «Ukjent». The only fix would be to edit this spec or to hide a known name; the label serves the story's "no change to this page" AC better.
    - `[low]` `patch` (claim) Filters do not re-read while the range is reversed (same entry as the reversed-range row).
  - Intent Alignment (divergences):
    - `[false]` `reject` Bootstrap is driven through the service, not HTTP. There is no HTTP route for it: it runs at api start.
    - `[low]` `reject` `register_labels` mutates, and `audit_events` is exported. The registry holds functions, not rows; the Table export predates this story and the trigger refuses update/delete.
    - `[low]` `reject` Names depend on app wiring (same as the Blind Hunter registration row).
    - `[maybe-false]` `reject` Oslo time is applied on the client. The AC is about what the Admin reads; the page shows Oslo time (unit and e2e tests).
    - `[low]` `reject` «Ingen treff.» on the page is exercised only by the date filter. The api tests cover actor and action filters returning nothing; the page's empty line does not depend on which filter.
    - `[maybe-false]` `reject` Later epics' rows are tested with a stubbed response in e2e. The api test writes an unknown action and key through the real `record` and lists them.
    - `[low]` `reject` The 320 px block layout is not asserted directly. It reuses the User list's `Cell`; axe, no sideways scroll and tap sizes run at 320 px, and the screenshot shows labelled blocks.
  - Verification Gap:
    - `[low]` `patch` Invitation targets were never checked to resolve to the address. Added `test_an_invitation_is_named_by_its_address`.
    - `[low]` `patch` The reversed-range e2e test did not prove the query was skipped. It now asserts «Ingen treff.» stays, no page error, and no request with the reversed `until`.
    - `[low]` `patch` The «Vis flere hendelser» failure path had no test. Added an e2e test: rows stay, the more-failed line shows, no page error.

## Design Notes

- **Target order:** `target_ids` is JSONB, which keeps no key order (shorter keys come first). The api returns targets in the order the database gives them; the web app orders change fields by their `nb.ts` order, so «Gammelt navn» precedes «Nytt navn».

- **Label registry in `platform/audit`:** the page renders targets generically; a later epic that records `class_session_id` registers its labeler and the page shows names with no change here. `platform/audit` still imports no module.
- **New `modules/admin`:** the architecture lists `admin` for the Admin area; the audit read reads no `identity` table directly.
- **Filters apply on change:** no submit button, so the page keeps no competing primary; date inputs are native `type="date"`.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/admin tests/platform/test_audit.py tests/test_authz_rules.py` -- expected: pass
- `cd backend && uv run pytest --durations=15 && uv run ruff check . && uv run ruff format --check .` -- expected: pass
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- expected: pass
- `docker compose up -d --build --wait proxy worker-batch && cd frontend && npx playwright test` -- expected: pass

## Auto Run Result

Status: done

**Summary.** `platform/audit` gains read functions (`page` with actor/system, action and date filters on a `(occurred_at, id)` keyset; `actors`) and a label registry (`register_labels`, `labels`); it still offers no update or delete and imports no module. `create_app()` registers `identity`'s labelers for `user_id` (name), `invitation_id` (address) and `institution_id` (current name), so names are read at request time and rows keep ids only. A new `modules/admin` serves `GET /api/admin/audit` (list envelope, newest first, 422 for a bad cursor, actor or reversed range) and `GET /api/admin/audit/actors`, both behind the existing `audit.read` policy. The Admin-område links to «Revisjonslogg» (`/admin/revisjonslogg`): four filters that apply on change (Utført av, Handling, Fra og med, Til og med), then a table Tidspunkt / Utført av / Handling / Gjelder / Endring that reflows into labelled blocks below 60em. Actions, targets and change fields render from `nb.ts` entries with raw fallbacks, so a later epic's action shows without a page change. «Systemet» marks rows with no actor; «Ingen treff.» shows when filters match nothing, «Ingen hendelser ennå.» when the log is empty.

**Implementation note.** The run's brief said to implement in this context, not through a step-03 subagent: background subagents stop when the turn ends. Only the review used subagents.

**Files changed:** backend `platform/audit.py` (reads, registry), `main.py` (router, registrations), `identity/{repo,service}.py` (label reads), `modules/admin/{__init__,schemas,service,routes}.py` (new), tests `admin/test_audit_log.py` (new: every matrix row, one row per action of the epic, policy) and `platform/test_audit.py` (no update/delete, public functions); frontend `copy/nb.ts`, `modules/identity/{homes.ts,home-page.tsx}` (third link), `modules/admin/{api.ts,audit.ts,audit-filters.tsx,audit-list.tsx,audit-page.tsx}` (new except api.ts), `app/(app)/admin/revisjonslogg/page.tsx` (new), unit test `audit.test.ts` (new), regenerated `lib/api/{openapi.json,schema.ts}`, e2e `admin-audit.spec.ts` (new), `homes.spec.ts` (three links).

**Review.** 33 findings: 0 high, 0 medium, 27 low, 2 false, 4 maybe-false.
- Patched (all low): outermost dates no longer overflow (500 → no bound); an empty `actor` is no filter; a reversed range keeps actor/action changes applying; the test connection is a fixture; new tests for the invitation label, the skipped reversed query and the failed «Vis flere».
- Deferred: none. Every rejection has its reason in the triage log.

**Follow-up review recommended: false.** No high or medium entry was patched (patched: 0 high, 0 medium, 6 low entries).

**Verification:**
- Backend `pytest` 1859 passed in 71 s; ruff check and format clean. Slowest new test 0.39 s (none over 1 s).
- Frontend: typecheck, Vitest 295, check:copy, lint:colours and build pass.
- Playwright on the compose stack: 102/104 on the last full run; the two failures were the known `system-states.spec.ts` tests at 1440 px under full-suite load (Story 3.10/3.11 note), which passed when rerun alone. `admin-audit.spec.ts` 8/8 and `homes.spec.ts` pass.
- No migration was added or changed.

**Decisions taken in place of the founder:**
- Page name and path «Revisjonslogg», `/admin/revisjonslogg`, third link in the Admin-område.
- Reads live in a new `modules/admin` (the architecture's Admin-area module); names come through a label registry in `platform/audit` filled by `identity` at app start, so later epics register their own target keys.
- Actor filter is a select of everyone in the log («Systemet» first, then names), via `/api/admin/audit/actors`; action filter is a select of the actions named in `nb.ts`, exact match; dates are inclusive Europe/Oslo days. Filters apply on change, no submit button.
- Targets: Users by name, Invitations as «Invitasjon til <adresse>», Institutions by current name; unknown → «Ukjent». Change fields render as «Felt: verdi» with role names, Ja/Nei, list lengths; `resent_invitation_id` is hidden.
- Page size 50, max 100; time shown as «18. nov. 2026 kl. 13:01».
- [ASSUMPTION] copy: all of `nb.admin.audit` (lead, filter labels, «Til og med-datoen kan ikke være før fra og med-datoen.», column names, «Systemet», «Ukjent», «Ingen hendelser ennå.», «Vis flere hendelser», the eleven action names, field labels).

**Residual risks:**
- Native date inputs show the browser's locale format (mm/dd/yyyy in an English Chromium).
- An action of a later epic without an `nb.ts` entry shows its code and cannot be picked in the action filter.
- The `system-states.spec.ts` flake under full-suite load remains.
