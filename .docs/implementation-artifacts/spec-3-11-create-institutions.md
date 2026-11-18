---
title: 'Story 3.11: Create Institutions'
type: 'feature'
created: '2026-11-18'
status: 'done'
baseline_revision: '01368f3e82e3ebd34938e220c49ae81e8c63046c'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-3-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-3-10-deactivate-reactivate-users-resend-invitations.md'
warnings: [oversized]
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Admin cannot create the Institutions that Classes will belong to (FR-3), and other modules have no way to read them.

**Approach:** `identity` gets an `institutions` table (migration `0021`), list/create/rename routes under `/api/admin/institutions` behind the existing `institutions.manage` policy with one audit row per change, and `service.list_institutions()` / `get_institution(id)` for other modules. The Admin-område links to a new page «Institusjoner» (`/admin/institusjoner`) with a create form and the list, each row renamable inline.

## Boundaries & Constraints

**Always:**
- Table `institutions(id uuid pk, name text not null, created_at timestamptz not null, updated_at timestamptz not null)`, unique index `uq_institutions_name` on `lower(name)`, check `name <> ''`. Times from the api clock (`auth.utcnow()`), never the DB clock. Id `uuid.uuid7()`.
- Name rule (one function in `schemas.py`, mirrored in the web app): trim and collapse inner whitespace; empty → `name_empty`; > 200 chars → `name_too_long`; a control character or `@` → `name_invalid` (`@` because `audit.record` refuses it, and an Institution name never needs it). A bad name answers `422 invalid_request` with `fields.name = <code>`.
- `GET /api/admin/institutions?cursor=&limit=` → `200 {"items": [{id, name, created_at}], "next_cursor"}`, newest first (id desc), keyset cursor as Story 3.10 (bad → `422 invalid_request`, `fields.cursor`), `limit` 1–100 default 50.
- `POST /api/admin/institutions {name}` → `201` item. `PATCH /api/admin/institutions/{id} {name}` → `200` item; unknown → `404 not_found`. Both: one transaction under an advisory lock `institution_names`; a name equal case-insensitively to another Institution's → `409 institution_name_taken`, nothing stored; else write and `audit.record(actor, "institution.created", {institution_id}, {name})` / `("institution.renamed", {institution_id}, {old_name, new_name})`. A rename to the exact current name → `200`, nothing written; a case-only change of the own name is a rename.
- All three routes use policy `institutions.manage` (Admin only). No delete route. No event topic (nothing listens).
- `service.list_institutions() -> list[InstitutionOut]` (all, by name) and `service.get_institution(id) -> InstitutionOut | None`.
- Web: `/admin/institusjoner`, crumbs Admin-område → Institusjoner; the Admin-område list gets a second Lenke «Institusjoner» under «Brukere og roller». Section «Ny Institusjon»: Tekstfelt «Navn» and the one primary button «Opprett Institusjon»; success clears the field and shows result line «USN er opprettet.» (`role="status"`, focused); the line goes when the field changes; an invalid or taken name shows the Tekstfelt invalid state with the reason under it; after the first press the reason updates as typed (a taken-name reason goes on typing); other failures `ActionError` «Institusjonen ble ikke opprettet. Prøv igjen.». The list re-reads after a create.
- Section «Institusjoner»: table Navn / Opprettet (Oslo date «18. nov. 2026») / Endre, reflowing to labelled blocks below 60em like the User list. Each row: secondary button «Gi USN nytt navn»; pressing it replaces the button with an inline form: Tekstfelt «Nytt navn på USN» prefilled, secondary «Lagre navnet» and Lenke-styled button «Avbryt»; success closes the form, focus returns to the row button, row line «USN heter nå USN Bø.»; refusals as for create (reason under the field; general «Navnet ble ikke endret. Prøv igjen.»). Empty list: «Ingen Institusjoner ennå. Opprett den første over.» «Vis flere Institusjoner», Skjelett and page-error as Story 3.10's list.
- Copy in `nb.ts` under `admin.institutions` (and `admin.sections.institutions`), drafts marked [ASSUMPTION].

**Never:** no delete; no confirmation dialogs; no DB-clock vs host-clock comparison in tests; no change to Users/Invitations behaviour or the audit page (3.12); no edits to `sprint-status.yaml`, `.env`, `.claude/settings*.json`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Create | Admin posts `"  USN   Bø "` | 201 name `USN Bø`; one row; one `institution.created` row with `{name}` | — |
| Duplicate | `usn bø` when `USN Bø` exists | 409 `institution_name_taken`; nothing stored, no audit | — |
| Bad name | `""`, `"   "`, 201 chars, `a@b` | 422 `fields.name` = `name_empty` / `name_too_long` / `name_invalid` | — |
| Rename | `USN` → `USN Bø` | 200; one `institution.renamed` row `{old_name, new_name}`; `updated_at` from api clock | unknown id → 404 |
| Rename same | exact current name | 200, no audit row | case-only change → renamed |
| Rename taken | to another's name (any case) | 409 `institution_name_taken`, unchanged | — |
| Race | two creates of `USN` at once | one 201, one 409 | advisory lock + unique index |
| List | 3 rows, limit 2 | newest first, `next_cursor`, second page the rest | bad cursor → 422 |
| Not Admin | Lecturer / no session on any route | 403 / 401 | — |

</intent-contract>

## Code Map

- `backend/app/platform/authz.py:67` -- `institutions.manage` already exists (Admin only); `tests/platform/test_authz.py:39` already covers it.
- `backend/app/modules/identity/models.py` -- add `institutions` Table (pattern: `invitations`, functional `Index` on `func.lower`).
- `backend/migrations/versions/0020_user_session_version.py` -- pattern for `0021_institutions.py`; `tests/test_migrations.py:41-53` HEAD sets and `HEAD = "0020"` → add `INSTITUTION_TABLES`, HEAD 0021, a downgrade-to-0020 test.
- `backend/app/modules/identity/repo.py` -- `lock_role` (L306) advisory-lock pattern; `list_users` keyset pattern (L244).
- `backend/app/modules/identity/service.py` -- `_encode_cursor`/`_decode_cursor`/`InvalidCursor` (L634-663) reuse; `audit.record` usage (L738); dataclass refusal pattern `StatusRefused` (L754).
- `backend/app/modules/identity/{schemas,routes}.py` -- `AcceptInvitationIn._name` validator pattern; `admin_router` routes and `error_response(status, code, message, fields)`; `documented(...)`.
- `backend/tests/conftest.py:129` -- `IDENTITY_TABLES` truncate list: add `institutions`.
- `backend/tests/identity/test_user_status.py` -- helpers `make`, `as_user`, `audit_rows`, `clock` fixture, `client`, `CSRF` from `tests/identity/helpers`.
- `frontend/src/modules/identity/{homes.ts,home-page.tsx}` -- `ADMIN_USERS_PATH`, `AdminSections` (add second `<li>`).
- `frontend/src/modules/admin/{users-page.tsx,api.ts,invite-form.tsx,invitation-list.tsx,invitations.ts,user-list.tsx}` -- page shell + crumbs, `useAction`/`useInfiniteQuery`/`request`, form error-on-typing pattern, list/Skeleton/page-error pattern, `formatDate`, `Cell`/`RowMessage`/`RowLine`.
- `frontend/src/lib/api/client.ts` -- `ApiRequestError.fields`.
- `frontend/src/app/(app)/admin/brukere/page.tsx` -- route-page pattern.
- `frontend/e2e/admin-users.spec.ts` -- `expectAccessible`, `VIEWPORTS`; `e2e/support/auth.ts` `loginByApi`.
- Regenerate client: `cd backend && uv run python -m app.openapi ../frontend/src/lib/api/openapi.json`, then `cd frontend && npm run api:generate`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0021_institutions.py`, `backend/app/modules/identity/models.py` -- the table.
- `backend/app/modules/identity/{schemas,repo,service,routes}.py` -- name rule, `InstitutionIn/Out/ListOut`, repo functions, service (create, rename, page, `list_institutions`, `get_institution`), routes.
- `backend/tests/identity/test_institutions.py` (new) -- every matrix row (race: two concurrent creates via `asyncio.gather`), service read functions; `tests/conftest.py`, `tests/test_migrations.py` updated.
- `frontend/src/copy/nb.ts`; `frontend/src/modules/identity/{homes.ts,home-page.tsx}`; `frontend/src/modules/admin/{api.ts,institutions.ts (new: name rule, reason/refusal lines),institution-form.tsx (new),institution-list.tsx (new),institutions-page.tsx (new)}`; `frontend/src/app/(app)/admin/institusjoner/page.tsx` (new); regenerated `lib/api/{openapi.json,schema.ts}`.
- `frontend/src/modules/admin/institutions.test.ts` (new) -- name rule and lines.
- `frontend/e2e/admin-institutions.spec.ts` (new) -- Admin-område link; create (unique name), duplicate in other case shows the reason and it clears on typing; result line clears on change; rename inline with row line; empty state via route-fulfilled empty list; Lecturer gets permission denied; axe at 320 and 1440 px with no sideways scroll and one primary button.

**Acceptance Criteria:**
- Given the Admin-område, when the Admin follows «Institusjoner», then the list shows name and creation date, or the empty line with the create form as the one action.
- Given a taken or empty name, when the Admin presses «Opprett Institusjon», then the Tekstfelt is invalid with the reason under it and the list is unchanged.
- Given «Institusjoner» at 320 and 1440 px, then axe finds nothing and nothing scrolls sideways.
- Given the full suites, then everything passes and no new backend test takes over 1 s.

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 33 findings — high 0, medium 2, low 26, false 5, maybe-false 0 (the two medium rows are one entry: the lower() mismatch)
- note: the four reviewers ran as background subagents (the run's brief); their final reports were read from their transcripts after each ended its turn.
- findings:
  - Blind Hunter:
    - `[low]` `reject` Web name rule differs from the api's at Unicode edges (`\x1c`–`\x1f`, `\x85`, U+200B, U+FEFF). The api decides and its reason still lands under the field via `refusalForField`; both docstrings now say the web check is a pre-check, not the same rule. Full parity would need a Unicode table in the web app.
    - `[low]` `reject` No NFC normalisation and no test of zero-width look-alikes. Not asked by the story; zero-width characters are already refused by the api (`isprintable`).
    - `[low]` `reject` Names over 800 raw characters get pydantic's 422 and the general line. Nobody types 800 characters into a name field.
    - `[low]` `reject` DB enforces only `name <> ''`. Every writer goes through `institution_name`; `identity` owns the table.
    - `[low]` `reject` `IntegrityError` from the index is not mapped to 409. Only a writer that skips the lock can reach it; the lower() mismatch that could reach it is patched below.
    - `[low]` `patch` The race test may not overlap. Run with the lock removed: the create race test failed in 2 of 3 runs (500 from the index), so it does exercise the lock, though not deterministically. Added a rename-vs-create race test.
    - `[false]` `reject` `institutions.manage` not in the diff. It already exists in `platform/authz.py:67` and `tests/platform/test_authz.py:39`.
    - `[low]` `reject` Three functions named `list_institutions`. The service name is set by the story (AC5); route and repo follow module convention.
    - `[low]` `patch` A 200-character unbroken name can overflow the row button and the rename label at 320 px. Added `[overflow-wrap:anywhere]` to both.
    - `[low]` `patch` Esc and «Avbryt» close the form during a save, losing its result line. Both now wait while `rename.isPending`.
    - `[false]` `reject` Rename errors refetch and move the open form. Invalidation refetches in the background with data kept; `usePageState` stays `ready`, the form keeps its key and state (the taken-rename e2e shows the reason under the still-open field).
    - `[low]` `reject` Refused-rename log lines lack actor / not_found has no log. Matches the Story 3.9/3.10 refusal logs.
    - `[low]` `patch` «Vis flere Institusjoner» untested in the browser. Added the cursor paging e2e (same as the User list's).
    - `[low]` `reject` `limit` bounds and long cursors untested. Declared in FastAPI `Query` constraints, same as the tested User and Invitation lists.
    - `[false]` `reject` List order (UUIDv7) and `created_at` from different clocks. Both are the api host's clock in production; only tests fix `auth.utcnow`.
  - Edge Case Hunter:
    - `[medium]` `patch` Python `str.lower()` and Postgres `lower()` disagree (e.g. «İ»): the check passed and the unique index answered 500. The check now uses `func.lower(literal(name))`; test `test_names_are_compared_with_the_databases_lower_case` failed with the old line and passes now.
    - `[low]` `reject` Unhandled `IntegrityError` (same as the Blind Hunter row).
    - `[low]` `reject` Over-800 raw names (same as the Blind Hunter row).
    - `[low]` `patch` Esc/«Avbryt» while pending (same patch as above).
    - `[low]` `reject` Prefilled rename field stale after another Admin renames the same row meanwhile. Needs two Admins on one row at once; the api compares against the stored name anyway.
    - `[low]` `reject` Web/api rule parity claim (same as the first Blind Hunter row; docstrings corrected).
  - Verification Gap:
    - `[low]` `patch` Well-formed unknown cursor untested. Added to the list test (422, `fields.cursor`).
    - `[low]` `patch` «Vis flere» untested (same patch as above).
    - `[low]` `patch` Rename race untested. Added `test_a_rename_and_a_create_of_one_name_at_once_store_it_once`.
    - `[low]` `reject` Other finding: rule parity (same as above).
  - Intent Alignment (divergences):
    - `[low]` `reject` Name rules beyond empty/taken (length, `@`, control characters). Needed so every change can write its audit row (`platform/audit` refuses `@`); recorded as a founder decision below.
    - `[low]` `reject` Empty state is a line pointing at the always-present form. The form is the one action on the page (e2e: one button in `main`).
    - `[low]` `reject` Empty-name refusal tested in the browser only client-side. Server side covered at the api.
    - `[low]` `reject` Atomicity not proven by a failing audit write. One `begin()` block, as Stories 3.9 and 3.10.
    - `[low]` `reject` Read functions open their own transaction. AC5 names only the functions; a session-taking variant can come with the first caller (Epic 4).
    - `[medium]` `patch` Case-insensitive check in two places can disagree (same patch as the Edge Case row; counted there).
    - `[false]` `reject` No-op rename writes no audit row. A choice the story leaves open; tested.
    - `[false]` `reject` Generated client files outside the reviewed diff. Excluded on purpose (generated by `npm run api:generate`); typecheck and build passed against them.

## Design Notes

- **Newest first**, not by name: the row just created stands at the top of page one, and e2e runs that add rows to the shared dev database never push it to page two.
- **Advisory lock plus unique index:** the lock gives a clean `409` in a race; the index is the last guard if a future writer skips the lock.
- **`@` refused in names:** `platform/audit` refuses any `@` string as a possible e-mail; refusing it at input keeps "one audit row per change" always possible.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/identity/test_institutions.py tests/test_migrations.py` -- expected: pass
- `cd backend && uv run pytest --durations=15 && uv run ruff check . && uv run ruff format --check .` -- expected: pass
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- expected: pass
- `docker compose up -d --build --wait proxy worker-batch && cd frontend && npx playwright test` -- expected: pass

## Auto Run Result

Status: done

**Summary.** `identity` owns a new `institutions` table (migration `0021`, unique on `lower(name)`). `GET/POST /api/admin/institutions` and `PATCH /api/admin/institutions/{id}` sit behind the existing `institutions.manage` policy (Admin only; no delete route). Create and rename run under an advisory lock, compare names with Postgres `lower()` (`409 institution_name_taken`), refuse bad names with `422 fields.name` (`name_empty`, `name_too_long`, `name_invalid`), and write one audit row in the same transaction (`institution.created {name}`, `institution.renamed {old_name, new_name}`). Saving the exact current name writes nothing. `service.list_institutions()` and `get_institution(id)` are there for other modules. The Admin-område links to «Institusjoner» (`/admin/institusjoner`): a create form with the page's one primary button, then a newest-first table (Navn / Opprettet / Endre) with an inline rename per row. It reflows like the User list. Result lines clear when the form changes, and reasons clear as you type.

**Implementation note.** The run's brief said to implement in this context, not through a step-03 subagent: background subagents stop when the turn ends. Only the review used subagents.

**Files changed:** backend `identity/{models,schemas,repo,service,routes}.py`, migration `0021_institutions.py`, tests `identity/test_institutions.py` (new), `conftest.py` (truncate list), `test_migrations.py` (head 0021 + downgrade test); frontend `copy/nb.ts`, `modules/identity/{homes.ts,home-page.tsx}` (link), `modules/admin/{api.ts,institutions.ts,institution-form.tsx,institution-list.tsx,institutions-page.tsx}` (new except api.ts), `app/(app)/admin/institusjoner/page.tsx` (new), unit test `institutions.test.ts` (new), regenerated `lib/api/{openapi.json,schema.ts}`, e2e `admin-institutions.spec.ts` (new), `homes.spec.ts` (Admin-område now lists two links).

**Review.** 33 findings: 0 high, 2 medium (one entry), 26 low, 5 false.
- Patched: the medium entry (Python vs Postgres `lower()`, which caused a 500 for names like «İzmir»; proven by a test that fails on the old line).
- Patched lows: the rename/save guards for Esc and «Avbryt», overflow-wrap for long names, the unknown-cursor test, the rename race test, the «Vis flere» e2e, and the rule-parity docstrings.
- Deferred: none. Every rejection has its reason in the triage log.

**Follow-up review recommended: false.** One medium entry was patched and no high.

**Lock proof:** with `lock_institution_names` removed, the create race test failed (500 from the unique index) in 2 of 3 runs. With the lock, it passes every time. The overlap is likely, not guaranteed.

**Verification:**
- Backend `pytest` 1837 passed in 71 s; ruff check and format are clean. The slowest new test takes 0.36 s.
- During the first full run, `players/test_rescue.py::test_time_per_attempt_…` failed once under load. It touches no changed code and passed alone.
- Frontend: typecheck, Vitest 288, check:copy, lint:colours and build all pass.
- Playwright on the compose stack: 95/96. The failure was the known `system-states.spec.ts` offline test at 1440 px, which passed 54/54 when repeated alone (pre-existing load flakiness, also seen in Story 3.10).
- The new spec passed 18/18 twice. It failed once right after the frontend container restarted (warm-up).
- Migration `0021` ran in the shared `olspillet_test` databases during this run and was not changed afterwards.

**Decisions taken in place of the founder:**
- The list is newest first, page size 50 (the new row lands on page one).
- Names are trimmed and their whitespace collapsed. Names over 200 characters are refused. Names with `@` or a control character are refused, because the audit row holds the name and `platform/audit` refuses `@`.
- Names are compared by Postgres `lower()`. A change of case only counts as a rename. Saving an identical name is a no-op with no audit row.
- One policy, `institutions.manage`, covers list, create and rename.
- No event topic, since nothing listens.
- Rename is an inline form in the row (no dialog), with «Lagre navnet» and a Lenke-styled «Avbryt»; Esc also cancels.
- [ASSUMPTION] copy: «Institusjoner», «Ny Institusjon» and its lead line, «Navn», «Opprett Institusjon», «USN er opprettet.», the four reasons, «Alle Institusjoner», the columns «Navn / Opprettet / Endre», «Ingen Institusjoner ennå. Opprett den første over.», «Gi USN nytt navn», «Nytt navn på USN», «Lagre navnet», «Avbryt», «USN heter nå USN Bø.», «Navnet ble ikke endret. Prøv igjen.», «Vis flere Institusjoner».

**Residual risks:**
- The web pre-check and the api rule differ at Unicode edges; the api's reason still shows under the field.
- The e2e runs add Institutions to the shared dev database, so the visual check will show many test rows.
- The `system-states.spec.ts` flake under full-suite load remains.
