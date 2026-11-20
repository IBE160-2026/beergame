---
title: 'Story 5.1: Create a Class session with the Classic defaults'
type: 'feature'
created: '2026-11-19'
status: 'done'
baseline_revision: '7a196e6c5c8865afffc481cf72bdd873269daa2d'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-5-context.md'
  - '{project-root}/.docs/planning-artifacts/ux-designs/ux-beergame-2026-11-05/DESIGN.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Lecturer has a Class with a Roster but no way to set up the exercise itself. There is no `sessions` module, no `class_sessions` table and no Klasseøkt screen.

**Approach:** Create the `sessions` module. «Lag Klasseøkt» on the Klasse page stores one Class session with the engine's Classic `GameSettings` plus a server-drawn demand seed, the session defaults and, when a default model config is active, that config and a budget row, all in one transaction. The Klasseøkt screen shows the defaults and «Kjeden ved start» from what the API returned. «Lagre Klasseøkt» saves it unchanged.

## Boundaries & Constraints

**Always:**
- Table `class_sessions` (migration `0032`, owned by `modules/sessions`):
  - `id` UUIDv7.
  - `class_id` FK `classes` ON DELETE CASCADE, indexed.
  - `game_settings` JSONB: `GameSettings(demand_seed=engine.demand.new_seed(secrets.token_bytes(16))).model_dump(mode="json")`, which carries `schema_version`.
  - `ai_mode` ∈ {`llm`, `rule_based`}; `debrief_mode` ∈ {`group`, `personal`}.
  - `inactivity_limit_hours` int, CHECK ≥ 20, default 24 from a module constant.
  - `obligatory` bool false.
  - `model_config_id` uuid NULL, with no FK into `ai` tables. CHECK: `ai_mode = 'llm'` implies a config.
  - `created_by` FK users SET NULL, `created_at`, `saved_at` NULL.
- Defaults come from `GameSettings()` only. No Classic value is written in `sessions` or the web app. `is_classic` is computed by the server: the stored settings equal `GameSettings()` apart from `demand_seed`.
- Create: `POST /api/classes/{class_id}/class-sessions` → 201 `ClassSessionOut`. It runs in one transaction:
  1. The guard: `classes.service.is_writable(class_id, session=s)`; if False it raises `classes.service.ClassArchived`, which `main.py` already maps to 409 `class_archived`.
  2. `ai.config.active_default(session=s)`.
  3. Insert the row.
  4. If a default exists: `ai.budget.set_budget(BudgetScope.class_session(id), session=s)`.
  5. `events.emit(s, "session", id)`.
- No active default: `ai_mode = rule_based`, no config and no budget. `ClassSessionOut.llm_unavailable = "no_default_model"`, otherwise null.
- Save: `PUT /api/class-sessions/{id}` with body `{ai_mode}` → 200. It locks the row `FOR UPDATE`, runs the same guard, sets `saved_at` and emits `session:<id>`. When `ai_mode = llm` and no config is attached, it asks `active_default`. If there is one, it attaches the config and creates the budget in the same transaction. If not, it answers 409 `llm_unavailable` and changes nothing.
- Reads: `GET /api/class-sessions/{id}` and `GET /api/classes/{class_id}/class-sessions` (list, newest first by id), for owners and Assistant lecturers.
- Authz:
  - New policies `class_sessions.read` ({LECTURER, ASSISTANT}; staff {owner, assistant}) and `class_sessions.manage` ({LECTURER}; staff {owner}) in `platform/authz`.
  - `sessions.service` checks `authz.can(user, action, classes.get_class(...))`. It never compares roles.
  - Order of answers: 403 (no policy, not staff, wrong staff role, missing), then 409 `class_archived`, then 422.
- Events registry: `sessions.create` and `sessions.save` → {`session`}.
- `ClassSessionOut` fields: `id`, `class_id`, `class_name`, `game_settings` (the stored dict), `is_classic`, `ai_mode`, `debrief_mode`, `inactivity_limit_hours`, `obligatory`, `llm_unavailable`, `saved_at`, `created_at`, `can_manage` (owner and Class not archived).
- Web, route `/klasseokter/[sessionId]`:
  - Title «Klasseøkt for {klassenavn}». Breadcrumbs: Lærerhjem → Class → Klasseøkt.
  - «Alt er fylt ut med standardene.» (only when `is_classic`).
  - «Spillinnstillinger: Klassisk» with a read-only list of the settings.
  - The delay-sources line.
  - KI-modus, Debrief-modus, Inaktivitetsgrense and Obligatorisk as read-only text.
  - The `llm_unavailable` line.
  - «Kjeden ved start»: hand-made SVG in `frontend/src/modules/sessions/` with no chart library. Upstream on the left (Fabrikk … Detaljist, then Kundene), delay boxes on the pipe, Lager per Role, the caption «Varer mot høyre, ordre mot venstre», and a visible text sentence with the same values that labels the SVG (`role="img"` with `aria-labelledby`).
  - «Lagre Klasseøkt» is the primary button for `can_manage`, with «Du kan lagre uten å endre noe.» beside it. On success: a `role="status"` line «Klasseøkten er lagret.». On failure: `ActionError` with `nb.system.actionFailed`, focus kept, values kept. `llm_unavailable` has its own message.
  - Assistant lecturers see the screen read-only, with no button.
- Klasse page: a section «Klasseøkter» lists the sessions, each a Lenke with its created date (Europe/Oslo) and «Lagret» or «Ikke lagret ennå». Owners of an active Class get a secondary button «Lag Klasseøkt», which creates the session and navigates to it. Assistants and archived Classes get no button.
- All copy goes in `nb.ts` → `sessions`. Strings that the story does not give are marked [ASSUMPTION].

**Never:** editing Game settings, AI mode, Effort level, Debrief mode, obligatory or the Inactivity limit on screen (Stories 5.3, 5.5 and 5.7); dates, Lab hours or allocation; deleting a Class session; `games.policy` changes; `mark_referenced` (that is the lock's job); importing `ai` tables or private `ai` modules in `sessions`; a second copy of the Classic values; touching the demo Class in tests; comparing DB time with host time.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Create, default active | owner or co-owner | 201; row with Classic settings + seed, `llm`, group, 24, false, config id; budget row; `session:<id>` | – |
| Create, no default | no pin offering a level | 201; `rule_based`, no config, no budget; `llm_unavailable: no_default_model` | – |
| Create by Assistant / outsider / Student | – | 403 `forbidden`; nothing stored | – |
| Create on archived Class | owner | 409 `class_archived`; nothing stored | – |
| Save unchanged | owner, `ai_mode` as stored | 200; `saved_at` set; `session:<id>` | – |
| Save `llm`, no config, default now active | owner | config attached + budget row in same txn | – |
| Save `llm`, still no default | owner | 409 `llm_unavailable`; unchanged | – |
| Save after archive | owner | 409 `class_archived` | – |
| Read | Assistant of the Class | 200, `can_manage: false` | outsider 403 |

</intent-contract>

## Code Map

- `backend/app/engine/settings.py:43` -- `GameSettings()` is the Classic preset; `model_dump(mode="json")` gives decimal strings.
- `backend/app/engine/demand.py:176` -- `new_seed(entropy: bytes)`.
- `backend/app/ai/config.py:801` -- `active_default(session=)`; `backend/app/ai/budget.py:105` -- `set_budget(scope, session=)` (the limit defaults for `class_session`); `BudgetScope.class_session`.
- `backend/app/modules/classes/service.py:137,182,214` -- `get_class` (a `ClassOut` with `staff_role`, the resource for `authz.can`), `ClassArchived`, `is_writable(class_id, session)`.
- `backend/app/platform/authz.py:73,111` -- `POLICIES`, `CLASS_STAFF_ROLES`.
- `backend/app/platform/events/registry.py` -- add `sessions.*`.
- `backend/app/main.py` -- include the `sessions` router; `ClassArchived` is already handled.
- `backend/migrations/env.py` -- import `app.modules.sessions.models`; `tests/test_migrations.py:66` sets `HEAD = "0032"`.
- `backend/tests/conftest.py:156` -- `IDENTITY_TABLES` gets `class_sessions`. Test helpers come from `tests/classes/test_classes.py` (`make`, `institution`, `as_user`), `tests/classes/test_staff.py` (`put_staff`) and `tests/classes/test_student_registration.py` (`emitted`); `ai_db` fixture; `app.ai.seed.ensure_zero_config` gives an active mock default.
- `backend/tests/test_imports.py` -- `AI_TABLES` regex: `sessions` must not name `ai_*` tables.
- Frontend:
  - `src/modules/classes/class-page.tsx` (where the section goes), `api.ts` (`request` pattern), `archive-class.tsx` (`useAction` pattern).
  - `src/lib/api/mutation.ts`, `src/components/{button,action-error,link}.tsx`, `src/modules/identity/{homes.ts,page-shell}`.
  - `src/theme/theme.css`: tokens `lager`, `ink`, `axis`, `bar-base`.
  - Regenerate the API types: `uv run python -m app.openapi ../frontend/src/lib/api/openapi.json`, then `npm run api:generate`.
- e2e: `frontend/e2e/support/classes.ts` (`freshLecturer`, `expectAccessible`, `VIEWPORTS`); `class-archive.spec.ts` `freshClass` pattern.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/sessions/{__init__,models,schemas,repo,service,routes}.py` and `README.md` -- the module as specified.
- `backend/migrations/versions/0032_class_sessions.py` -- the table and its checks.
- `backend/app/platform/{authz.py,events/registry.py}`, `backend/app/main.py`, `backend/migrations/env.py`, `backend/tests/conftest.py`, `backend/tests/test_migrations.py` -- wiring.
- `backend/tests/sessions/test_class_sessions.py` -- every row of the matrix through the routes: the stored row and settings equal to `GameSettings()` plus the seed, the budget row, emits, 403/409 order, roles, logs carry ids only.
- `frontend/src/modules/sessions/{api.ts,sessions.ts,sessions.test.ts,chain-diagram.tsx,class-session-page.tsx,class-sessions.tsx}`, `src/app/(app)/klasseokter/[sessionId]/page.tsx`, `homes.ts` (`classSessionPath`), `class-page.tsx`, `copy/nb.ts`, regenerated `lib/api/{openapi.json,schema.ts}`.
- `frontend/e2e/class-session.spec.ts`:
  - The flow from the Klasse page to a saved session with no field edited, then listed as «Lagret».
  - A save failure (route aborted) shows the alert with focus kept.
  - An Assistant sees no create button.
  - axe and no horizontal scroll at 320, 360 and 1440 px, and at 400 % zoom (1280 px wide with zoom, i.e. a 320 px CSS viewport).

**Acceptance Criteria:**
- Given an owner on the Klasse page, when they press «Lag Klasseøkt» and then «Lagre Klasseøkt» without editing anything, then the session is saved and the Klasse page lists it as «Lagret».
- Given the Klasseøkt screen, then it shows the four strings of UX-DR48 and «Kjeden ved start» with values from the API, plus a text equivalent.
- Given a failed save, then «Det ble ikke lagret. Prøv igjen.» is announced with `role="alert"` and focus stays on «Lagre Klasseøkt».
- Given Playwright at 320, 360 and 1440 px and at 400 % zoom, then the screen is one column below 1024 px, has no page-level horizontal scroll, passes axe, and `check:copy` passes.

## Spec Change Log

## Review Triage Log

### 2026-11-19 — Review pass
- verdicts: 40 findings — high 0, medium 1, low 25, false 10, maybe-false 4
- findings:
  - `[low]` `[reject]` (blind) Other staff are not told about a new Class session (only `session:<id>`). AD-8 names `session:<id>` for every `sessions` mutation. Refetch on events comes with the topic map of Story 6.4 (see Story 5.2's AC).
  - `[low]` `[reject]` (blind) Nothing in the web app listens to `session`. There is no topic consumer in the product yet (Story 6.4). The story asks only for the emit and its registry entry.
  - `[low]` `[reject]` (blind) Create and save write no audit row. The story asks for none. Adding new audit actions and labels would be extra public surface.
  - `[low]` `[reject]` (blind) The list order (UUIDv7 wall clock) and `created_at` (api clock) are different clocks. In production both are the server's clock; only tests fix the api clock.
  - `[low]` `[patch]` (blind) No test checks the list order or the empty list. `test_two_class_sessions_draw_their_own_seeds_and_list_newest_first` now covers both.
  - `[medium]` `[patch]` (blind) The chain diagram's labels shrink to about 6 px on a phone. The SVG now keeps its natural width inside its own focusable scroll region (`role="group"`, labelled by «Kjeden ved start»), as the Datolinje does. The page still has no horizontal scroll (axe and the scroll check pass at 320/360 px and 400 %).
  - `[low]` `[reject]` (blind) Screen readers read the text twice (the image name, then the caption). The spec requires `role="img"` labelled by the visible text. The repetition is short and harmless.
  - `[false]` `[reject]` (blind) A delay of 0 draws wrongly. The engine's `Delay` is `ge=1`, so 0 never reaches the screen.
  - `[low]` `[reject]` (blind) `starting_backlog` and `max_order` are missing from the list. The list follows mockup 03. A non-Classic value turns `is_classic` false, so «Alt er fylt ut med standardene.» is not shown falsely. Story 5.3 adds every setting.
  - `[false]` `[reject]` (blind) «1–N» assumes Guided Weeks start at Week 1. That is the engine's rule (the first N Weeks are guided), and mockup 03 draws «1–4».
  - `[low]` `[patch]` (blind) The Klasse page list had no error state. It now shows «Siden kunne ikke lastes.» with «Prøv igjen».
  - `[false]` `[reject]` (blind) «Lag Klasseøkt» stays «Lager …» after success. The page navigates away, and coming back mounts a new mutation.
  - `[low]` `[reject]` (blind) The settings take half the desktop width. This is deliberate: the right column holds Datoer and Fordeling (Stories 5.2 and 5.8), as in mockup 03.
  - `[low]` `[reject]` (blind) The element ids are hard-coded. Each component appears once per page, the same as on the existing pages.
  - `[maybe-false]` `[reject]` (blind) Older `schema_version` rows would fail validation. Only version 1 exists. A bump (Story 5.16) brings its own reading rule. If true, the impact is only low.
  - `[low]` `[reject]` (blind) Several transactions per request, and a post-commit read could answer 403. This needs the owner to be removed in the same instant; the same residual risk was accepted in Story 4.10.
  - `[false]` `[reject]` (blind) The AI mode is half-handled, and an unpinned config gives no warning. AD-6: a Class session keeps the config it references ("scopes created before keep their config"). Saving Rule-based keeps the binding by design.
  - `[low]` `[reject]` (blind) The inactivity floor is written in two places. Migrations hold literal values by project convention, and `alembic check` passes.
  - `[low]` `[reject]` (blind) The tests import helpers from other test modules. This is the established pattern (`test_archive.py`).
  - `[low]` `[patch]` (blind) The 422 on save was not tested. `test_a_save_body_that_is_not_valid_is_refused_and_changes_nothing` now covers it (an empty body, an unknown mode, an extra field).
  - `[low]` `[reject]` (blind) No e2e shows `llmUnavailable` or `llmRefused`. The local stack has the mock default, the api tests pin both, and the AI mode choice that would reach `llmRefused` comes in Story 5.5.
  - `[low]` `[patch]` (blind) The owner of an archived Class was told «Du er Assistent …». The screen now reads the Class (`useClass`) and shows the archived notice for an archived Class, and the Assistant line only to Assistants. A new e2e covers it.
  - `[low]` `[reject]` (edge) An owner demoted between the check and the insert. A same-instant race, accepted as in Story 4.10.
  - `[low]` `[reject]` (edge) The same race on save. As the row above.
  - `[false]` `[reject]` (edge) A deleted Class answers 409 instead of 403. Classes are never deleted (Story 4.10).
  - `[low]` `[reject]` (edge) A create commits, then the re-read answers 403. As blind row 16.
  - `[false]` `[reject]` (edge) Saving LLM keeps a config that is no longer the default. That is the AD-6 binding (see blind row 17).
  - `[false]` `[reject]` (edge) `llm_unavailable` ignores a stored config that is no longer usable. As the row above.
  - `[maybe-false]` `[reject]` (edge) An older schema leads to a 500. As blind row 15.
  - `[low]` `[patch]` (edge) The list had no loading or error state. The same fix as blind row 11.
  - `[low]` `[patch]` (edge) After a `class_archived` save refusal, `can_manage` stayed true. The query client now also reads the `class-sessions` queries again on `class_archived` (`providers.tsx`).
  - `[low]` `[patch]` (intent) Only the offline save failure was tested. The e2e now also fulfils a 500 and checks the same alert and focus.
  - `[low]` `[reject]` (intent) The one-column check is a proxy. Below `lg` every grid is `grid-cols-1`. The proxy (save x ≤ settings x) together with the no-scroll check is enough.
  - `[maybe-false]` `[reject]` (intent) The no-default copy is not checked on screen. The api tests pin the flag. The copy is a plain render of the flag.
  - `[false]` `[reject]` (intent) The session-level defaults are constants in `sessions` (R2′). "No second copy" concerns the engine's Classic `GameSettings`. AI mode, Debrief mode, Inactivity limit and obligatory are not in the engine.
  - `[maybe-false]` `[reject]` (intent) The `assistantLead` line is not asked for. It follows the Story 4.9 pattern for read-only staff views and is marked [ASSUMPTION].
  - `[false]` `[reject]` (intent) The emit has no staff fan-out (R5b). As blind row 1: refetching is Story 6.4's job.
  - `[low]` `[patch]` (verification-gap) No check that «Lag Klasseøkt» is hidden on an archived Class. `class-archive.spec.ts` now asserts it.
  - `[low]` `[patch]` (verification-gap) The registry entries were never compared with what is emitted. The api tests now compare the emitted topics with `COMMAND_TOPICS["sessions.create"]` and `["sessions.save"]`.
  - `[low]` `[patch]` (verification-gap, other) The owner of an archived Class saw the Assistant text. The same fix as blind row 22.

## Design Notes

- `saved_at` separates a created session from a saved one. The list shows both, so a session the Lecturer left unsaved is never lost from sight.
- The `ai_mode` body on save exists for the AC «later saves with LLM players». Until Story 5.5 adds the Valgknapper, the screen sends the stored mode.
- 409 for `llm_unavailable`: the request is valid, but it conflicts with the current model state.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/sessions -q` -- pass, each test under 1 s.
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass.
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- pass.
- `cd frontend && npx playwright test` against `timeout 900 docker compose up -d --build --wait proxy worker-batch` -- pass.

## Auto Run Result

Status: done

**Summary.** A Faglærer who owns a Class creates a Class session from the Klasse page («Lag Klasseøkt»), and it is already filled in with the Classic defaults. The Klasseøkt screen shows the defaults and «Kjeden ved start», and «Lagre Klasseøkt» saves the session unchanged. Assistant lecturers read it with no action.

- **Backend.**
  - New module `sessions` with the table `class_sessions` (migration 0032, UUIDv7).
  - Create stores `GameSettings()` with a seed from `engine.demand.new_seed`, plus `llm`, `group`, 24 h, not obligatory. When `ai.config.active_default` finds a config, the same transaction stores that config id and creates the budget row through `ai.budget.set_budget`. With no default the session gets `rule_based`, no config and no budget, and the answer carries `llm_unavailable: "no_default_model"`.
  - Save (`PUT`, `{ai_mode}`) sets `saved_at`. LLM with no config attaches the default and its budget, or answers 409 `llm_unavailable`.
  - One guard (`classes.is_writable`) answers 409 `class_archived`. New authz actions `class_sessions.read` and `class_sessions.manage`. `session:<id>` is emitted on create and save, with registry entries.
- **Web.**
  - The `/klasseokter/[id]` screen: title, «Alt er fylt ut med standardene.», «Spillinnstillinger: Klassisk» with the settings list, the delay-sources line, the hand-made SVG «Kjeden ved start» with the same values as text, KI-modus, Debrief-modus and Obligatorisk as text, and the primary «Lagre Klasseøkt» with an alert on failure.
  - «Klasseøkter» on the Klasse page.

**Files changed**
- Backend:
  - `app/modules/sessions/{__init__,models,schemas,repo,service,routes}.py` and `README.md` (new).
  - `migrations/versions/0032_class_sessions.py` (new).
  - `app/platform/authz.py`: the policies.
  - `app/platform/events/registry.py`: the topics.
  - `app/main.py`: the router.
  - `migrations/env.py`.
  - `tests/conftest.py`: `class_sessions` added to the identity truncate.
  - `tests/test_migrations.py`: HEAD 0032, `SESSION_TABLES`, and a downgrade test to 0031.
  - `tests/sessions/test_class_sessions.py` (new, 17 tests).
- Frontend:
  - `src/modules/sessions/{api,sessions,sessions.test,chain-diagram,class-session-page,class-sessions}.ts(x)` (new).
  - `src/app/(app)/klasseokter/[sessionId]/page.tsx` (new).
  - `src/modules/classes/class-page.tsx`: the section.
  - `src/modules/identity/homes.ts`: `classSessionPath`.
  - `src/app/providers.tsx`: reads `class-sessions` again on `class_archived`.
  - `src/copy/nb.ts`: `sessions`, with [ASSUMPTION] marks.
  - Regenerated `src/lib/api/{openapi.json,schema.ts}`.
  - `e2e/class-session.spec.ts` (new, 8 tests).
  - `e2e/class-archive.spec.ts` (+1 assertion).

**Review findings.** 40 findings: 0 high, 1 medium, 25 low, 10 false, 4 maybe-false.
- **Patched (12 rows):**
  - the medium one: the phone diagram now sits in its own scroll region;
  - the list's newest-first order and the empty list;
  - the 422 tests;
  - the list's error state (2 rows);
  - the archived owner's line on the Klasseøkt (2 rows);
  - reading `class-sessions` again on `class_archived`;
  - the e2e for a server failure (500);
  - the archived Klasse page hides «Lag Klasseøkt»;
  - the comparisons with the registry.
- **Deferred:** none.
- **Rejected:** the rest, each with its reason in the Review Triage Log.

**Follow-up review recommended: false.** One medium entry was patched, and none were high.

**Verification**
- Backend: the full pytest suite passed 2296 tests in 56 s. Ruff check and format are clean. Each new test takes under 1 s; only the first test's setup, which migrates the test database, is longer.
- Frontend:
  - typecheck, Vitest (372), `check:copy`, `lint:colours` and `build` pass.
  - Playwright passed 182/182 on the rebuilt stack with `worker-batch`.
- Screenshots of the Klasseøkt and the Klasse page at 390 and 1280 px were checked by eye. That check found «Kundene» cut off, which is now fixed.
- Migration 0032 is new. The shared test database `olspillet_test` was migrated to it during this run.
- The caller asked that the implementation be done in this context instead of by an implementation subagent. The four review layers ran as subagents, and their reports were read from their transcripts.

**Decisions taken in place of the founder**
- **Saved state.** `saved_at` separates a created session from a saved one. The Klasse page lists every session as «Klasseøkt opprettet {dato}», marked «Lagret» or «Ikke lagret ennå», so an unsaved session never disappears from view. There is no limit on the number of sessions per Class, and there is no delete.
- **Route.** The screen lives at `/klasseokter/{id}`, with breadcrumbs Lærerhjem → Klasse → Klasseøkt.
- **Create button.** «Lag Klasseøkt» is a secondary button on the Klasse page. It creates the session and opens it.
- **Save body.** Save takes `{ai_mode}`, and the screen sends the stored mode until Story 5.5. `llm_unavailable` is a read-time flag (no row has a config, and no default exists now). The refusal is 409 `llm_unavailable`.
- **Settings on screen.** The Klasseøkt shows the settings as a read-only list in mockup 03's order. KI-modus, Debrief-modus and Obligatorisk are shown as text; Stories 5.3, 5.5 and 5.7 make them editable.
- **Diagram.** «Kjeden ved start» draws the production delay into Fabrikk and the shipping delay between the Roles, with one box per Week. Order dots (one per Week of order delay) sit under the pipes between Roles. On a phone the diagram scrolls in its own region.
- **Inactivity floor.** The database enforces the 20 h floor with a CHECK constraint.
- **Model config and budget.** There is no foreign key into the `ai` tables, and the config is not frozen at create; Story 5.11's lock freezes it.
- **Copy.** All new copy that is not in EXPERIENCE.md or mockup 03 is [ASSUMPTION]: the no-default line, the refusal, «Klasseøkten er lagret.», the Assistant line, the list strings and «Eget mønster».
- **Local data.** The local Docker database held a stale `mock` config from before Story 2.12, with no measurement and no pin. The seed skips a database that already holds a config, so the local stack had no active default. I added the mock measurement and pinned that config (local data only, no code change). A fresh database or CI is seeded and pinned as Story 2.12 intends.

**Residual risks**
- Authorization is checked before the transaction. An owner removed in the same instant could still create or save once (the same accepted race as Story 4.10).
- No screen refetches on `session:<id>` until Story 6.4.
