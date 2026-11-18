---
title: 'Story 4.1: Create a Class from the Lærerhjem'
type: 'feature'
created: '2026-11-18'
status: 'done'
baseline_revision: '0bffd937fe96a78f70d211be5dbad7c9209c8a12'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-4-context.md'
  - '{project-root}/.docs/planning-artifacts/ux-designs/ux-beergame-2026-11-05/DESIGN.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Lecturer lands on an empty Lærerhjem and has nowhere to put Students: there is no Class, no `classes` module, no Class-scoped authorization, and the Story 3.9 revoke-blocker registry has nothing registered, so a Lecturer who owns Classes could lose the role.

**Approach:** Add `modules/classes` (tables `classes`, `class_staff`, routes, service, repo, local seed), Class-scoped authz in `platform/authz` (`classes_visible_to(user)`, `classes.*` policies), the revoke blocker, and on the web the Lærerhjem list/empty state, «Lag Klasse» and a minimal Class page.

## Boundaries & Constraints

**Always:**
- Class + owner row are written in one transaction; the creator is `class_staff.role = 'owner'`.
- Every `classes` repository query on Class rows joins through `authz.classes_visible_to(user)`; `platform/authz` imports no `app.modules` code (it uses lightweight `sqlalchemy.table()` for `class_staff`).
- Every new route declares an authz policy; `tests/test_authz_rules.py` passes unchanged in substance.
- A Class that does not exist, a malformed id, and a Class the Lecturer is not staff of all give the same 403 `forbidden` / permission-denied page.
- `classes` reaches Institutions and Users only through `identity.service`; `identity` imports nothing from `classes` (registry only).
- Revoke blocker counts the User's owned Classes with `archived_at IS NULL`.
- UI copy only in `frontend/src/copy/nb.ts`; reuse `TextField`, `Button`, `Link`, `PageShell`, `GuardedPage`. Errors clear as the user types; nothing is stored on a refused save.
- Seed only with `APP_ENV=local`, idempotent, under an advisory lock.

**Never:** Roster, upload, Invitations, co-owners, Assistants, archive UI (Stories 4.2–4.10); audit rows for Class creation (not asked); role comparisons in modules; resetting or deactivating demo accounts in tests; DB-vs-host time comparisons or ordering by timestamps in tests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Create | Lecturer, name «class-of-1994», existing Institution, course code «IBE160» | 201 `ClassOut`; one `classes` row and one `class_staff` owner row | – |
| Name rule | name `"  a   b "` | stored `"a b"` (trimmed, inner whitespace collapsed) | – |
| No course code | `course_code` absent, `""` or blanks | stored NULL, answered `null` | – |
| Missing name | name blank | 422 `invalid_request`, `fields.name = name_empty`, nothing stored | field invalid state |
| Long / bad name | > 200 chars, or a control char | `fields.name = name_too_long` / `name_invalid` | same |
| No Institution | `institution_id` null/absent | `fields.institution_id = institution_missing` | same; several fields reported at once |
| Unknown Institution | random uuid | `fields.institution_id = institution_unknown` | same |
| Bad course code | > 50 chars or control char | `fields.course_code = course_code_too_long` / `course_code_invalid` | same |
| Read own Class | owner GETs `/api/classes/{id}` | 200 with name, course code, Institution name | – |
| Foreign / unknown Class | non-staff Lecturer, or unknown uuid | 403 `forbidden` (identical) | permission-denied page |
| Non-Lecturer | Admin-only or no-role User on any `/api/classes*` | 403 `forbidden` | – |
| Revoke | Admin revokes Lecturer from a User owning 1 active Class | 409 `role_revoke_blocked`, `fields.classes = 1`, role kept | – |
| Seed | `APP_ENV=local`, demo Lecturer owns no Class | Institution «Demohøgskolen» (if missing) + Class «class-of-1994», «IBE160» owned by demo Lecturer; second run adds nothing | DB error logged, not raised |

</intent-contract>

## Code Map

- `backend/app/platform/authz.py` -- POLICIES (l.62), `can` (l.80). Add `classes.create|read|manage` → {LECTURER}; class-scoped check via resource `staff_role`; `classes_visible_to(user)` select of `class_staff.class_id`. Docstring l.17-21 promises this.
- `backend/app/modules/identity/service.py` -- `register_revoke_blocker` (l.689), `RevokeBlocker(session, user_id) -> int`; `list_institutions` (l.1065), `get_institution` (l.1072), `user_id_for_email` (l.182). Add `institution_id_by_name(session, name)` for the seed.
- `backend/app/modules/identity/seed.py` -- `ensure_demo_users` pattern (advisory lock, local only) to copy for the Class seed; add the demo Institution here (identity owns Institutions).
- `backend/app/modules/identity/schemas.py` l.204 -- `institution_name` rule to mirror for Class names (without the `@` ban).
- `backend/app/modules/identity/routes.py` l.489-546 -- route/refusal/`error_response` pattern; `documented()` in `platform/errors.py`.
- `backend/app/main.py` -- include `classes` router; lifespan calls the Class seed after `ensure_demo_users_logged`.
- `backend/migrations/versions/0022_access_requests.py` -- migration style; new `0023_classes.py`. `migrations/env.py` imports module models.
- `backend/tests/conftest.py` l.129 `IDENTITY_TABLES` (TRUNCATE … CASCADE clears Classes too); `tests/identity/helpers.py` (`client`, `login`, `CSRF`); `tests/identity/test_user_roles.py` l.336 blocker test style; `tests/test_migrations.py` table sets + downgrade tests; `tests/test_authz_rules.py`.
- `frontend/src/modules/identity/home-page.tsx` -- `HomePage`, `GuardedPage`, `AccessDenied`; Lærerhjem content goes here via a `classes` component.
- `frontend/src/modules/admin/institution-form.tsx` + `institutions.ts` -- form/validation/refusal pattern to mirror.
- `frontend/src/modules/admin/audit-filters.tsx` l.14 -- `SelectField`; move to `frontend/src/components/select-field.tsx` with `error`/`hint` and reuse.
- `frontend/src/modules/identity/homes.ts` -- paths; add `NEW_CLASS_PATH = "/klasser/ny"`, `classPath(id)`.
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerate via `uv run python -m app.openapi …` + `npm run api:generate`.
- `frontend/e2e/admin-status.spec.ts` l.46-73 -- fresh-Lecturer-by-Invitation pattern; `e2e/admin-institutions.spec.ts` -- axe/scroll/target-size helper.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0023_classes.py` -- create `classes` (id, name, course_code NULL, institution_id FK institutions RESTRICT, created_by FK users SET NULL, created_at, archived_at NULL) and `class_staff` (class_id FK CASCADE, user_id FK CASCADE, role CHECK IN ('owner'), added_at; PK class_id+user_id; index user_id) -- FR-6 storage.
- `backend/app/modules/classes/{__init__,models,schemas,repo,service,routes,seed}.py` -- tables; `ClassIn/ClassOut/ClassListOut/ClassInstitutionsOut`; name/course-code rules; repo queries via `classes_visible_to`; `create_class`, `list_classes`, `get_class`, `owned_active_classes` blocker registered at import; routes `GET /api/classes`, `POST /api/classes`, `GET /api/classes/institutions`, `GET /api/classes/{class_id}`; seed -- the module.
- `backend/app/platform/authz.py` -- policies + `classes_visible_to` + resource-aware `can` -- AD-12.
- `backend/app/modules/identity/{service,seed}.py` -- `institution_id_by_name`; demo Institution in seed -- seed support.
- `backend/app/main.py`, `migrations/env.py` -- wire router, seed, models.
- `backend/tests/classes/test_classes.py` -- api tests for the I/O matrix, scope, revoke block end to end, seed; update `tests/test_migrations.py`, `tests/test_authz_rules.py` (policy for `can` with resource), `tests/conftest.py`.
- `frontend/src/components/select-field.tsx` -- shared native select with error/hint; `audit-filters.tsx` uses it.
- `frontend/src/modules/classes/{api.ts,classes.ts,classes.test.ts,lecturer-home.tsx,class-form.tsx,new-class-page.tsx,class-page.tsx}` + `frontend/src/app/(app)/klasser/ny/page.tsx`, `klasser/[classId]/page.tsx`, `laererhjem/page.tsx` -- UI.
- `frontend/src/copy/nb.ts` -- `classes` section ([ASSUMPTION] copy).
- `frontend/e2e/classes.spec.ts` -- empty and filled Lærerhjem, Lag Klasse create + validation, foreign Class denied; axe at 320 px, 1440 px, 200 % text.

**Acceptance Criteria:**
- Given a Lecturer with no Classes, when they open the Lærerhjem, then they see a short empty-state line and «Ny Klasse» as the only action in `main`.
- Given a Lecturer with Classes, when they open the Lærerhjem, then «Klassene dine» lists each Class as a Lenke «name, course code» to `/klasser/{id}`, «Ny Klasse» stays, and the «Venter» and «Neste frist» places show that nothing is there yet.
- Given «Lag Klasse», when the Lecturer saves a valid form, then the Class is created and they land on the Class page, whose h1 is the Class name.
- Given «Lag Klasse», when saved with no name and no Institution, then both fields show their invalid state with the reason under them, focus goes to the first invalid field, nothing is stored, and each reason clears as that field changes.
- Given another Lecturer's Class or an unknown id, when a Lecturer opens `/klasser/{id}`, then the permission-denied page shows with «Til Lærerhjem».
- Given Playwright with axe, then the empty and filled Lærerhjem and «Lag Klasse» pass at 320 px, 1440 px and 200 % text with no page-level horizontal scroll.

## Spec Change Log

## Review Triage Log

### 2026-11-18 — Review pass
- verdicts: 37 findings — high 0, medium 6, low 17, false 14, maybe-false 0
- findings:
  - `[low]` `[reject]` (blind) A Class create can commit after a concurrent Lecturer-role revoke counted 0 — real but needs an Admin revoke in the same instant as the create; the fix adds a role re-check under a user lock through a new `identity.service` function. Recorded under residual risks.
  - `[false]` `[reject]` (blind) Institution check and insert in separate transactions give a 500 if the Institution is deleted — Institutions have no delete in v1 (`identity.service` docs, Story 3.11).
  - `[false]` `[reject]` (blind) Deleting an Institution with Classes is unhandled — no Institution delete path exists.
  - `[false]` `[reject]` (blind) Deleting the owning User leaves an unreachable Class — no User delete path exists before Epic 15's retention work.
  - `[low]` `[patch]` (blind) Web rule and api rule differ on U+001C–U+001F and U+0085 — `clean()` in `classes.ts` now splits on them as Python's `str.split` does; unit test added. The reverse case (format characters the api refuses) already shows the api's reason beside the field.
  - `[false]` `[reject]` (blind) Class creation writes no audit row — the story asks for none; audit in this epic covers staff changes and archive.
  - `[false]` `[reject]` (blind) The list does not mark archived Classes — nothing can be archived before Story 4.10, which owns that view.
  - `[false]` `[reject]` (blind) Double submit or retry duplicates a Class — the button is unavailable while pending and after success, and the mutation has `retry: false`; two tabs creating two Classes is the User's own act.
  - `[low]` `[reject]` (blind) `ClassIn` max lengths are 4× and unknown fields pass — the same convention as `InstitutionIn`; the form checks 200/50 before sending, so the UI never reaches the Pydantic path.
  - `[low]` `[reject]` (blind) OpenAPI lists a 422 for `getClass` it never returns — FastAPI's automatic entry, cosmetic; removing it needs a route-level override.
  - `[low]` `[reject]` (blind) `_visible` joins `class_staff` and also filters through `classes_visible_to` — the join supplies `staff_role`, the filter is the AD-12 rule the story requires; the extra index lookup is negligible.
  - `[low]` `[reject]` (blind) `lower(name)` ordering depends on the database collation — the same convention as the Institution list; not a defect of this story.
  - `[low]` `[patch]` (blind) e2e assumes the demo Lecturer holds exactly the seeded Class and picks the first listed Class — `homes.spec.ts` now checks that every Lærerhjem link is in «Klassene dine», the seeded Class is among them and «Ny Klasse» is last; `classes.spec.ts` picks the seeded Class by name.
  - `[low]` `[reject]` (blind) Missing tests (seed race, revoke race, deletes, mismatches, >800 chars, `can` without `staff_role` for manage) — the deletes do not exist, the mismatch and seed-reuse tests were added by other rows, the rest guard paths the UI cannot reach.
  - `[false]` `[reject]` (blind) `ensure_demo_class_logged` lets an `IntegrityError` escape — `IntegrityError` is a `DBAPIError` subclass; non-database errors propagate as in `identity.seed`.
  - `[low]` `[reject]` (edge) Create-versus-revoke race — same as the first blind row.
  - `[low]` `[reject]` (edge) The seed gives a Class to a deactivated or role-less demo Lecturer — local only; the demo Lecturer is seeded with the role and tests never change demo accounts.
  - `[medium]` `[patch]` (edge) `classKey("institutions")` collides with `classInstitutionsKey` — keys now `["classes", "detail", id]`.
  - `[medium]` `[patch]` (edge) A segment that decodes to another path reaches another api route — the Class page now refuses any id that is not UUID-shaped with the permission-denied page and never calls the api; e2e covers `/klasser/institutions`. (`%2E%2E` is normalised by the browser before any request, so it lands on `/`.)
  - `[low]` `[patch]` (edge) Web form refuses names with U+001C–U+001F/U+0085 — same fix as the blind row.
  - `[low]` `[reject]` (edge) `name: null` or a malformed `institution_id` get Pydantic codes — the form always sends a string and an id from the api.
  - `[low]` `[reject]` (edge) `getClass` OpenAPI lists 422 — same as the blind row.
  - `[medium]` `[patch]` (edge) `/klasser/institutions` shows a blank Class page, not permission-denied — fixed by the UUID guard above; e2e added.
  - `[low]` `[patch]` (edge) The spec put the resource-aware `can` test in `test_authz_rules.py`, the code in `test_classes.py` — moved to `tests/test_authz_rules.py`.
  - `[low]` `[reject]` (edge) Spec names `ClassInstitutionsOut` and `identity/seed.py`; code uses `InstitutionChoicesOut` and `identity.service.ensure_demo_institution` — the fix would edit this build's spec.
  - `[medium]` `[patch]` (verification-gap) The form's handling of a 422 field refusal is never exercised — e2e added: a routed 422 `institution_unknown` shows the reason under Institusjon, sets `aria-invalid`, focuses the select and shows no failure line.
  - `[medium]` `[patch]` (verification-gap) The seed's reuse of an existing «Demohøgskolen» is untested — `test_the_seed_reuses_an_institution_with_the_demo_name_in_any_case` added.
  - `[false]` `[reject]` (intent) `archived_at` added before 4.10 and tested by SQL — the story's own words ("active Classes") need it; a defensible reading, not a defect.
  - `[false]` `[reject]` (intent) `classes.manage` is used by no route — the story asks for the policy; no managing route exists in 4.1.
  - `[medium]` `[patch]` (intent) UI refusal and storage are not checked together — grouped with the 422 e2e row above.
  - `[false]` `[reject]` (intent) The Institution check is outside the insert transaction — the story's "one transaction" is the Class and its owner, which share one.
  - `[low]` `[reject]` (intent) No test forces future repo queries through the helper — a guard for code not yet written; an AST rule adds complexity with no named regression today.
  - `[low]` `[patch]` (intent) The empty Lærerhjem was reached by direct navigation, not by login landing — the e2e now opens `/` and asserts the landing on `/laererhjem`.
  - `[false]` `[reject]` (intent) 320 px as the 400 % zoom stand-in and injected 200 % text — the project's established NFR-6 method (`admin-users.spec.ts`, `admin-invite.spec.ts`).
  - `[false]` `[reject]` (intent) The seed adds «Demohøgskolen» with no audit row — documented, local only, no Admin acts.
  - `[false]` `[reject]` (intent) Changes beyond the story's surfaces (shared `SelectField`, `HomePage` children, h1 wrap) — reuse and enabling changes, covered by the existing audit and homes e2e that pass.
  - `[false]` `[reject]` (intent) The phone h1 is not `title-page` — `PageShell` uses the phone step of the title scale on every page by design.

## Auto Run Result

Status: done

**Summary.** Story 4.1 is built end to end. `modules/classes` adds the `classes` and `class_staff` tables (migration 0023), `GET/POST /api/classes`, `GET /api/classes/institutions` and `GET /api/classes/{class_id}`. `platform/authz` gains the `classes.create|read|manage` policies, a staff-role check in `can(user, action, resource)`, and `classes_visible_to(user)`, which every `classes` query on Class rows joins through. `classes.service` registers the Lecturer revoke blocker (it counts owned Classes that are not archived), so the Admin's revoke answers 409 `role_revoke_blocked` with the real count. The local seed adds «Demohøgskolen» and «class-of-1994, IBE160» for the demo Lecturer. On the web: the empty and filled Lærerhjem, «Lag Klasse» at `/klasser/ny`, and a minimal Class page at `/klasser/{id}` with the permission-denied state for a foreign, unknown or malformed id.

**Process note.** The workflow asks for an implementation subagent. The caller's instructions (subagents run in the background and stop when the turn ends) required the implementation to be done in the orchestrating context instead. The four review layers ran as subagents. Their reports never arrived as notifications, so they were read from their transcripts.

**Files changed**
- `backend/migrations/versions/0023_classes.py`: the `classes` and `class_staff` tables.
- `backend/app/modules/classes/{__init__,models,schemas,repo,service,routes,seed}.py`: the new module, its rules, the scoped queries, the revoke blocker and the demo seed.
- `backend/app/platform/authz.py`: the Class policies, `CLASS_STAFF_ROLES`, the resource-aware `can`, and `classes_visible_to`.
- `backend/app/modules/identity/{repo,service}.py`: `institution_id_by_name` and `ensure_demo_institution`, for the seed.
- `backend/app/main.py`, `backend/migrations/env.py`: wiring for the router, the seed and the models.
- `backend/tests/classes/test_classes.py`: api, scope, revoke-block, seed and seed-error tests.
- `backend/tests/{conftest,test_imports,test_migrations,test_authz_rules}.py`: truncation, an import boundary check, revision 0023, and the resource-aware `can` test.
- `frontend/src/components/select-field.tsx`: the shared native select with invalid state and hint; `modules/admin/audit-filters.tsx` now uses it.
- `frontend/src/modules/classes/*`: the api hooks, rules and unit tests, the Lærerhjem content, the form, «Lag Klasse» and the Class page.
- `frontend/src/app/(app)/klasser/{ny,[classId]}/page.tsx` and `laererhjem/page.tsx`: the routes.
- `frontend/src/modules/identity/{home-page.tsx,homes.ts,page-shell.tsx}`: `HomePage` takes children, the Class paths are added, and the h1 wraps long names.
- `frontend/src/copy/nb.ts`: the `classes` copy ([ASSUMPTION] where EXPERIENCE.md has none).
- `frontend/src/lib/api/{openapi.json,schema.ts}`: regenerated.
- `frontend/e2e/classes.spec.ts`: new. `frontend/e2e/homes.spec.ts`: updated for the filled Lærerhjem.

**Review findings.** 37 findings: 0 high, 6 medium, 17 low, 14 false, 0 maybe-false.
- Patched: 3 medium entries and 4 low ones.
  - Medium: the Class-page id guard together with the namespaced cache key; the 422 field-refusal e2e test; the seed's Institution-reuse test.
  - Low: whitespace parity with Python, robust e2e expectations, the `can` test moved to `test_authz_rules.py`, and the login landing in e2e.
- Deferred: none.
- Rejected: each with its reason in the Review Triage Log above.

**Follow-up review recommended: false.** Three medium entries were patched, and each fix now has its own passing test. No specific unverified risk remains to name.

**Verification**
- Backend: `ruff check` and `ruff format --check` are clean. The full `pytest` suite passed (1992 tests, about 73 s with the compose stack running). No new test call takes over 1 s; the 1.9 s shown for the first classes test is the session's migration setup.
- Frontend: `typecheck`, `npm test` (335 tests), `check:copy`, `lint:colours` and `build` all pass. Playwright passes (130 tests) against the rebuilt compose stack.
- Shared test databases: revision 0023 was added and migrated once. It was not changed after it ran.

**Decisions taken in place of the founder**
- Class URLs: «Lag Klasse» is at `/klasser/ny`, and a Class is at `/klasser/{id}`. After a create the browser opens the Class page, and Story 4.2 builds on from there.
- The Class page is minimal in 4.1: its name, course code and Institution.
- Name rule: 1–200 characters, whitespace collapsed, no control characters, `@` allowed. Course code: optional, up to 50 characters.
- The revoke blocker counts owned Classes where `archived_at IS NULL`. The column is added now and is set by 4.10.
- `class_staff.role` allows `owner` only; 4.9 widens it.
- No audit row for creating a Class.
- Demo seed: the Institution is «Demohøgskolen»; the Class is «class-of-1994» with the course code «IBE160».
- Lærerhjem: «Ny Klasse» is a Lenke, as in the mockup. «Venter» and «Neste frist» read «Ingenting venter ennå.» and «Ingen frist ennå.» until Epic 5.
- Draft copy ([ASSUMPTION]): the empty-state line, the «Lag Klasse» lead, «Emnekode (valgfri)», «Velg Institusjon», the error reasons, and «Klassen ble ikke laget. Prøv igjen.».

**Residual risks**
- An Admin revoke that runs at the same moment as a create can leave a Class whose owner lacks the Lecturer role. This was rejected as low; Story 4.9 or 4.10 can add a re-check under a user lock.
- The seed is local only and does not check that the demo Lecturer still holds the role.

## Design Notes

- Class-scoped `can`: `can(user, "classes.read", resource)` with `resource.staff_role` checks `CLASS_STAFF_ROLES[action]` (all `owner` in 4.1) on top of the account role. Repo returns the user's `staff_role` with each Class row; no row → `Forbidden`.
- `classes_visible_to(user)` returns `select(class_staff.c.class_id).where(class_staff.c.user_id == user.id)`; accepts a Principal or a bare user id (the blocker passes the id).
- Course code max 50 characters; name max 200, `@` allowed (no audit row holds it).
- After a create the browser goes to the Class page (`/klasser/{id}`); Story 4.2 extends from there.
- `GET /api/classes/institutions` is declared before `/{class_id}`.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/classes tests/test_authz_rules.py tests/test_migrations.py tests/identity/test_user_roles.py tests/identity/test_seed.py -q` -- pass.
- `cd backend && uv run pytest -q -n auto` -- full suite passes.
- `cd backend && uv run ruff check . && uv run ruff format --check .` -- clean.
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- pass.
- `cd frontend && npx playwright test` against the compose stack -- pass.
