---
title: 'Story 12.7: Set up a Control test in the operator''s own Institution'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '349a815e542d0c5eaa9fe6d258f722021028c005'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-12-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      A Control test can run with Rule-based players (created so when the chosen model config offers no Effort level, or switched by its owner on the Klasseøkt); the Start-date lock then puts no model config into `SessionRuntime`.
    evidence: |-
      `control_tests.create` picks `ai_mode` from the config's offered levels and `save_session` lets the owner change `ai_mode`; the trigger keeps only `class_sessions.model_config_id`. Whether this matters depends on Story 12.2: if the `assess` job reads the model config from the row's `model_config_id` (as `content.is_checked` and the Kontrolltest list do), nothing is lost; if it reads `SessionRuntime.model_config_id` from the lock's snapshot, a Rule-based Control test has none. Settle it when 12.2 decides where the assessment's pinned model config is read.
    location: >-
      backend/app/modules/sessions/control_tests.py:create
    severity: medium (unverified)
---

<intent-contract>

## Intent

**Problem:** The AI assessment cannot be checked on real answers, because there is no way to run a Control test: a Class session that never enters a course's results, in the operator's own Institution, pinned to the Scoring guide version and model config under test (FR-82, AD-27).

**Approach:** The Admin marks one Institution as the operator's own («Institusjoner», `institutions.operator_owned` through `identity.service`). Admin-område → «Kontrolltest» creates, in one transaction, a Class in that Institution with the Admin as owner and in it a Class session with `kind=control_test`, pinning the chosen Scoring guide version and model config. The Admin then uses the ordinary Epic 4/5 screens as owner: `platform/authz` lets an Admin hold the Epic 4/5 Class actions only on a `control_test` Class they own. Control tests are left out of every staff list and cannot be reached by anyone else.

## Boundaries & Constraints

**Always:**
- Migration `0201` (Revises `0130`): `institutions.operator_owned` (bool, default false, partial unique index: at most one true); `class_sessions.kind` (text, default `course`, check `course|control_test`); a trigger that refuses changing `kind`, and changing `model_config_id` of a `control_test` row.
- Mark: `PUT /api/admin/institutions/{id}/operator-owned` (`institutions.manage`); marking moves the mark (the old one is cleared) in one transaction holding the Institution names lock, audit `institution.operator_marked` (ids, `previous_institution_id`); marking the marked one again writes nothing. `identity.service.operator_institution()` and `InstitutionOut.operator_owned`.
- Create: `GET/POST /api/admin/control-tests` (new policy `control_tests.manage`, Admin only). POST `{name, scoring_guide_id, model_config_id}`: one transaction inserts the Class (`classes.service.create_class_in`, owner = Admin) and the session (`kind=control_test`, `model_config_id` = chosen, `ai_mode` llm when the config offers an Effort level else rule_based, budget row, `config.mark_referenced`), pins the guide through a hook `tests` registers (a `test_scoring_guides` row with `pinned_at` = now, `base_id` from the version's own session row or itself), one audit row `control_test.created` (ids, versions), `user:<admin>` event. Refusals: 409 `operator_institution_missing`; 422 `invalid_request` with `fields.name` (Class name rule), `fields.scoring_guide_id`/`fields.model_config_id` `unknown`.
- GET answers `{operator_institution, scoring_guides, model_configs, items}`: guide choices = latest default plus every edited version (version number, created date, `edited`, `draft`); config choices = `config.list_all()` with name, model version, `default`; items newest first with Class/session ids, name, Institution name, created, guide version, config name and model version, `can_open` (the viewer owns the Class).
- authz: `classes.read`, `classes.manage`, `class_sessions.read`, `class_sessions.manage` also list `ADMIN`; `can(user, action, resource)` refuses when the only role that grants it is `ADMIN` and `resource.control_test` is not true. `classes.service` resources (`_StaffOf`, `ClassOut`) carry `control_test` (an `authz.control_test_classes()` subquery over `class_sessions` by name). `add_lecturer` checks the Lecturer role with `classes.create`.
- Control test Class: `list_classes` (Lærerhjem, its sessions list, copy sources) leaves it out; `count_owned_active` (Lecturer revoke blocker) leaves it out; `add_lecturer`/`invite_assistant` refuse 409 `control_test_class`; `create_session` and `copy_from` into it, and `copy_from` of a control-test source, refuse 409 `control_test_class`.
- «Sensorveiledning» is read-only for a Control test (pinned at creation); `lock_test` pins the same version (its pinner finds it pinned). The 11.1 draft block applies unchanged.
- `sessions.service.kind_of(session, id)` and `control_test_session_ids()` (subquery) for Epic 13; `ClassSessionOut.kind`; `ClassOut.control_test`.
- UI: Admin-område link «Kontrolltest» → `/admin/kontrolltest`: «Teller aldri med i en Klasseøkt.», the operator Institution (or what to do first, linking «Institusjoner»), the create form (Navn, Sensorveiledning and Modellkonfigurasjon as Valgknapper, «Opprett Kontrolltest»), the list with each test's pinned guide version and model config and Lenker to the Class and the Klasseøkt. «Institusjoner»: label «Operatørens egen» on the marked row, «Merk som operatørens egen» on the others. Class page and Klasseøkt open for an Admin (guard `classStaff`); a Control test Class shows «Kontrolltest. Teller aldri med i en Klasseøkt.», no «Faglærere og assistenter», no «Lag Klasseøkt»/«Lag kopi», and crumbs Admin-område → Kontrolltest for a User without a staff role. New copy in `nb.ts` marked `[ASSUMPTION]`.

**Never:** test students, consent, Roster restriction (12.8); scorers, human scores (12.9); `mark_checked` (12.10); `reports.scope` (Epic 13); editing a Control test's guide or config after creation; a second set of Class screens; changes to the demo Class; edits of `sprint-status.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Mark | Admin marks B while A is marked | B marked, A cleared, one audit row | Lecturer: 403 |
| No operator | POST control test, none marked | nothing stored | 409 `operator_institution_missing` |
| Create | valid body | Class in operator Institution, Admin owner, session `control_test`, guide pinned, config referenced | bad name/ids: 422 with fields |
| Lecturer | POST control test | — | 403 `forbidden` |
| Admin as owner | GET/PUT Class, session, roster, allocation of own Control test | allowed | ordinary Class of others: 403 |
| Second session | POST session or copy into the Control test Class | nothing stored | 409 `control_test_class` |
| Staff | add Faglærer / invite Assistent | nothing stored | 409 `control_test_class` |
| Exclusion | ordinary Lecturer, Assistant, Student; admin-lecturer | Control test in no list; its Class/session/overview 403 | — |
| Guide | save «Sensorveiledning»; `lock_test` | refused; pin stays the created version | 409 `scoring_guide_locked` |
| Config | UPDATE `model_config_id`/`kind` in SQL | refused by trigger | — |

</intent-contract>

## Code Map

- `backend/app/platform/authz.py` -- POLICIES (~93–99), `can` (~220), add `control_tests.manage`, `control_test_classes()` (pattern: `class_sessions_staffed_by` ~305).
- `backend/app/modules/identity/{models,repo,service,routes,schemas}.py` -- `institutions` (~171), `create/rename_institution` (~1220), `InstitutionOut` (~275), admin routes (~523).
- `backend/app/modules/classes/{repo,service,schemas,routes}.py` -- `_visible` (~47), `insert_class` (~19), `count_owned_active` (~77), `_StaffOf`/`get_class`/`list_classes`/`add_lecturer`/`invite_assistant` (service ~58–850), `ClassOut` schema; `_staff_refused` route (~564).
- `backend/app/modules/sessions/control_tests.py` (new) -- `overview`, `create`; routes `admin_router` in `sessions/routes.py`, mounted in `main.py`.
- `backend/app/modules/sessions/{models,repo,service,routes,schemas}.py` -- `class_sessions` table, `create_session` (~863), `get_session` (~949), `copy_from` (~5830), `register_test_pinner` (~4542, pattern for the guide hook); new `sessions/control_tests.py`.
- `backend/app/modules/tests/guide.py` -- `pin_guide` (~117): add `pin_for_control_test`, register it.
- `backend/app/modules/content/service.py` -- `scoring_guide_record`, `latest_scoring_guide` (~443): add `scoring_guide_choices(session)`.
- `backend/app/ai/config.py` -- `list_all`, `get`, `mark_referenced`, `active_default`; `app/ai/budget.set_budget`.
- `backend/migrations/versions/0201_control_test.py`; `backend/tests/test_migrations.py` (HEAD).
- Frontend: `src/modules/identity/{homes.ts,home-page.tsx}` (`canView`, `AdminSections`), `src/modules/admin/{api.ts,institution-list.tsx}`, new `src/modules/admin/control-tests*.tsx`, `src/app/(app)/admin/kontrolltest/page.tsx`, `src/modules/classes/class-page.tsx`, `src/modules/sessions/{class-session-page.tsx,class-sessions.tsx}`, `src/copy/nb.ts`; reuse `src/components/{radio-group or valgknapper,text-field,button,link}.tsx`.
- E2E helpers: `frontend/e2e/support/{auth,classes}.ts`; backend fixtures `backend/tests/games/helpers.py`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0201_control_test.py` -- columns, index, trigger -- storage and DB guard.
- `backend/app/platform/authz.py` -- Admin on Control test Class actions, policy, subquery -- AC 3.
- `backend/app/modules/identity/*` -- mark command, route, `operator_institution`, `InstitutionOut.operator_owned` -- AC 1.
- `backend/app/modules/classes/*` -- `control_test` on resources, list/blocker exclusion, staff refusal, `create_class_in` -- AC 2, 3, 5.
- `backend/app/modules/sessions/*`, `tests/guide.py`, `content/service.py` -- kind, create/list Control tests, refusals, `kind_of`, `control_test_session_ids` -- AC 2, 4, 5.
- `backend/tests/sessions/test_control_test.py` -- matrix rows, exclusion for Lecturer/Assistant/Student/admin-lecturer, trigger, `lock_test` keeps the pin, draft lock refusal in production, audit rows; migrations test.
- Frontend files above, `npm run api:generate` -- screens -- AC 6.
- `frontend/e2e/control-test.spec.ts` -- mark and setup at 320/360/1440 with axe, serial.

**Acceptance Criteria:**
- Given an ordinary Lecturer, Assistant lecturer or Student, when they open any existing list, overview or Class/session read, then no Control test Class, session or Game appears or opens (api tests).
- Given the Kontrolltest screen, when it loads, then it shows «Teller aldri med i en Klasseøkt.», each test's pinned guide version and model config, and every Admin action is in the audit log.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Layers: blind hunter, edge-case hunter, verification gap, intent alignment (four sonnet reviewers, per the runbook's rule for data model and access changes). The implementation ran in the builder's own context (the brief's rule), so patches were applied directly.
- verdicts: 43 findings — high 0, medium 4, low 26, false 10, maybe-false 3
- findings:
  - `[low]` `[patch]` Blind: the four Class actions now list ADMIN, so a pure Admin passed `GET /api/lecturer-home/class-sessions` (200 with nothing) — every handler under those policies passes the User to a resource check (scripted walk of the routes); the Lærerhjem read now takes `lecturer_home.view`, as `GET /api/classes` does; the api test asserts 403 for the Admin on both and on an ordinary Class's reads.
  - `[false]` `[reject]` Blind: Control tests are not left out of retention, PII, sweeps or reminders — test students must get the ordinary reminders and sweeps (the Control test runs unchanged, AD-27); reports and statistics leave it out through `reports.scope` in Epic 13, which the story names.
  - `[maybe-false]` `[defer]` Blind: a Control test can be Rule-based, and `ai_mode`/Effort level are not pinned — depends on where Story 12.2 reads the pinned model config; deferred (frontmatter).
  - `[medium]` `[patch]` Blind: choosing and pinning an edited Scoring guide is untested (`base_id or record.id`) — new api test saves a Lecturer's edit, finds it among the choices, pins it, checks `base_id` is the default and the block shows «Endret». Provenance in the label (no Class name) is kept short by design.
  - `[low]` `[reject]` Blind: the mark moves with no confirm, undo or clear — the product uses no dialogs (UX-DR9); marking the other Institution moves it back; clearing adds a command for no AC.
  - `[low]` `[reject]` Blind: no lifecycle beyond creation; downgrade of 0201 turns Control tests into courses — archive works on the ordinary route; a downgrade is a developer action on a dev database.
  - `[low]` `[reject]` Blind: `overview` reads per row and is not paged — a handful of Control tests exist; paging adds surface for no gain.
  - `[false]` `[reject]` Blind: an over-long name maps to «Valget finnes ikke lenger» — a body over the schema's limit answers `validation_error`, which the form words with its general line; the form checks 200 characters before sending.
  - `[false]` `[reject]` Blind: `openapi.json`/`schema.ts` not regenerated — they are regenerated (`npm run api:generate`) and left out of the review diff on purpose; `tsc` passes over them.
  - `[low]` `[patch]` Blind: weak assertions and missing write check — allocation read must be 200, Invitations are sent by the Admin owner (201), another Admin who lectures gets 403 on a save, the emitted topics are asserted with the `emitted` spy.
  - `[false]` `[reject]` Blind: `granted == {ADMIN}` is fragile — a second granting role (Lecturer, Assistant) needs its own staff role in the Class, checked first; the Admin-only path fails closed on a resource without `control_test`.
  - `[low]` `[reject]` Edge: an Admin+Lecturer owner keeps access after the Admin role is revoked — they are the person who set it up; a revoke blocker for the Admin role is a new rule no AC asks for.
  - `[false]` `[reject]` Edge: an Admin+Assistant bypasses the Control test gate on reads — the staff-role check still applies, and only the creating Admin holds a staff row on a Control test Class.
  - `[low]` `[reject]` Edge: a Control test whose only owner loses the Admin role is orphaned — rare (the operator's Admins), and a transfer command is new surface; noted under residual risks.
  - `[maybe-false]` `[defer]` Edge: a config with no offered level makes a Rule-based Control test — same root as the deferred Blind row.
  - `[maybe-false]` `[defer]` Edge: the owner can switch the Control test to Rule-based on the Klasseøkt — same root as the deferred Blind row.
  - `[low]` `[reject]` Edge: two concurrent creates make two Control tests — the button is unavailable while pending; two Classes may share a name anywhere in the product.
  - `[low]` `[reject]` Edge: a mark moved during a create leaves the new test in the old Institution — the documented outcome of moving the mark (Design Notes).
  - `[false]` `[reject]` Edge: no Scoring guide stored gives 500 — migration 0122 stores version 1 on every database.
  - `[low]` `[reject]` Edge: the guide choices grow without bound — few edited versions exist; paging adds surface.
  - `[low]` `[reject]` Edge: a draft guide can be pinned — every guide is a draft until issue #16; the label says «(utkast)».
  - `[low]` `[reject]` Edge: a rostered ordinary Student would see the Control test in Hjem — restricting the Roster to test students is Story 12.8, which the intent excludes from this build.
  - `[false]` `[reject]` Edge: existing aggregates and reminder sweeps include Control tests — no cross-class statistic exists yet; reminders must reach test students.
  - `[low]` `[reject]` Edge: the one-session rule is not in the database — every insert path goes through the guarded service, pinned by the api test.
  - `[low]` `[reject]` Edge: downgrade with Control test rows — developer-only.
  - `[low]` `[reject]` Edge: no index for the `control_test_classes()` subquery — `class_sessions` is small; an index is a migration for no measured gain.
  - `[low]` `[patch]` Edge: the create form keeps an empty choice when the choices arrive after it mounted — the chosen ids now fall back to the first choice whenever the stored one is not among the options.
  - `[low]` `[reject]` Edge: copy sources answer for a Control test Class — read-only and unused (the UI shows no «Lag kopi» there); the copy itself is refused.
  - `[low]` `[reject]` Edge: the Admin can archive a Control test Class with no way back — as for every Class (Story 4.10).
  - `[false]` `[reject]` Edge claim: «cannot be reached by anyone else» fails for the Admin+Lecturer owner — that User is the owner who set it up.
  - `[false]` `[reject]` Edge claim: matrix row says the admin-lecturer gets 403 — the row is about an Admin who lectures and does not own it; the owner reads it (test asserts both).
  - `[medium]` `[patch]` Verification: no test adds an Admin-only account as Faglærer — `admin_only` case added to `test_an_address_that_is_no_lecturer_gets_one_reason`.
  - `[low]` `[patch]` Verification: the `user:<admin>` event is never observed — the setup test asserts the emitted topics and id with the `emitted` spy.
  - `[medium]` `[patch]` Verification: the session's `ai_mode`/Effort level are never asserted — the setup test asserts `llm` and the config's first offered level.
  - `[medium]` `[patch]` Verification: the edited-guide choice and pin are untested — same root and fix as the Blind row.
  - `[low]` `[patch]` Verification: the Class page hiding «Lag Klasseøkt»/«Lag kopi» is not asserted — the e2e asserts both buttons absent.
  - `[low]` `[patch]` Verification (other): the allocation read is asserted only as `!= 403` — same fix as the Blind test-quality row.
  - `[low]` `[reject]` Verification (other): `control_test_session_ids()` has no caller or test — Epic 13 consumes it; a one-line subquery.
  - `[low]` `[reject]` Verification (other): an Admin who also lectures gets the Lærerhjem crumb on a Control test — the spec's rule; their Lærerhjem still links to the Admin-område.
  - `[low]` `[patch]` Intent: the Epic 4/5 routes the Admin uses are barely exercised — the api test now sends Invitations and reads the allocation as the Admin owner.
  - `[low]` `[reject]` Intent: no test names Games in the exclusion — every Game read goes through its Class session's staff scope or the Student's own Seat, and the Class and session reads are proven closed.
  - `[false]` `[reject]` Intent: creation does not go through a `sessions.service` function — it lives in `modules/sessions` (`control_tests.py`), the owner of `class_sessions`, and calls `classes.service` for the Class.
  - `[low]` `[reject]` Intent: the 409 `operator_institution_missing` and its wording are not linked in one e2e — the api test pins the code and the unit test its words; the form is hidden in that state.

## Design Notes

- Why `ADMIN` in four policies instead of a session role: only an Admin creates a Control test and staff changes on it are refused, so "Admin who owns a control-test Class" is exactly the owner the AC means; `can` fails closed when a resource lacks `control_test`.
- Moving the operator mark is allowed; Control tests made before keep their Class's Institution (decision recorded; a refusal would make the mark impossible to correct).

## Verification

**Commands:**
- `uv run pytest tests/sessions/test_control_test.py tests/test_migrations.py tests/test_authz_rules.py tests/test_imports.py` -- pass
- `npm run typecheck && npm run test && npm run lint:colours && npm run check:copy && npm run build` -- pass
- `npx playwright test e2e/control-test.spec.ts --workers=4` -- pass

## Auto Run Result

Status: done

**Summary.** The Admin marks one Institution as the operator's own on «Institusjoner» (`institutions.operator_owned`, partial unique index, `PUT /api/admin/institutions/{id}/operator-owned`, audit `institution.operator_marked`; the mark moves). Admin-område → «Kontrolltest» (`/admin/kontrolltest`, `GET/POST /api/admin/control-tests`, policy `control_tests.manage`) shows «Teller aldri med i en Klasseøkt.», the operator Institution, a create form (Class name, Scoring guide version and model config as Valgknapper) and every Control test with its pinned guide version and model config. Creating makes, in one transaction, a Class in the operator Institution owned by the Admin and a `control_test` Class session (`class_sessions.kind`, migration 0201) with the model config under test (referenced, kept by a trigger), its own budget row, the Scoring guide version pinned at creation (so «Sensorveiledning» is read-only and `lock_test` keeps it), and audit `control_test.created`. The Admin holds the Epic 4/5 Class actions only on a Control test Class they own (`authz.CONTROL_TEST_ACTIONS`); the Class page and Klasseøkt open for them with crumbs through «Kontrolltest». A Control test Class is in no staff list, not counted by the Lecturer revoke blocker, and takes no other staff or Class session (409 `control_test_class`). `sessions.service.kind_of` and `control_test_session_ids()` are there for Epic 13.

**Files.**
- `backend/migrations/versions/0201_control_test.py` — `operator_owned`, `kind`, trigger.
- `backend/app/platform/authz.py` — `control_tests.manage`, Admin on Control test Classes, `control_test_classes()`.
- `backend/app/modules/identity/{models,repo,service,routes,schemas}.py` — the mark, `operator_institution`.
- `backend/app/modules/classes/{repo,service,routes,schemas}.py`, `README.md` — `control_test` on resources, exclusion, staff refusal, `create_class_in`, `class_facts`; `GET /api/classes` on `lecturer_home.view`.
- `backend/app/modules/sessions/control_tests.py` (new), `{models,repo,service,routes,schemas}.py`, `README.md` — kind, create/list, refusals, `kind_of`; Lærerhjem sessions on `lecturer_home.view`.
- `backend/app/modules/tests/guide.py`, `backend/app/modules/content/service.py` — pin at creation, guide choices.
- `backend/app/main.py`, `backend/app/platform/events/registry.py` — router, 409 mapping, topics.
- `backend/tests/sessions/test_control_test.py` (new), `tests/classes/test_staff.py`, `tests/identity/test_institutions.py`, `tests/test_migrations.py`.
- `frontend/src/modules/admin/{control-tests-page.tsx,control-tests.ts,control-tests.test.ts}` (new), `admin/{api.ts,institution-list.tsx,institutions-page.tsx}`, `src/app/(app)/admin/kontrolltest/page.tsx` (new), `identity/{homes.ts,homes.test.ts,home-page.tsx}`, `classes/class-page.tsx`, `sessions/class-session-page.tsx`, `tests/scoring-guide-block.tsx`, `copy/nb.ts`, `lib/api/{openapi.json,schema.ts}` (generated).
- `frontend/e2e/control-test.spec.ts` (new), `e2e/homes.spec.ts` (the new Admin-område link).

**Review.** 43 findings from four sonnet reviewers. Patched: 3 medium entries (Admin-only account as Faglærer, `ai_mode`/Effort level asserted, edited guide choice and pin), 7 low (Lærerhjem sessions policy, tighter Admin-owner route test with Invitations and allocation, emitted topics, «Lag Klasseøkt»/«Lag kopi» absent in e2e, create form choice fallback). Deferred: 1 (Rule-based Control test vs Story 12.2's reading of the pinned model config, three rows). Rejected: 19 low and 10 false, each with its reason in the triage log.

**Follow-up review: recommended.** Three medium entries were patched (counts: high 0, medium 3, low 7). Unverified risk: whether Story 12.2 reads a Control test's model config from the row (kept by the trigger) or from the lock's `SessionRuntime` (empty for Rule-based players), and the access rule `can()` applies to the Admin role on every Class route, which the api tests sample rather than walk route by route.

**Verification.** Backend: full suite with `--maxprocesses=8`: 3683 passed, 4 skipped; `ruff check` and `ruff format --check` clean; the new test file's slowest call 0.71 s (no new test over 1 s). Frontend: `tsc` clean, Vitest 1174 passed, `lint:colours` and `check:copy` pass, `next build` ok (`/admin/kontrolltest`). Playwright on the lane-3 stack (8082): `control-test` (mark and setup, no-operator state, at 320/360/1440 with axe), `admin-institutions`, `homes`, `classes`, `class-session`, `class-staff`, `scoring-guide`, `ai-assessment-switch`, `class-session-rerun`, `game-start`, `order-field`, `week-table`, `guided-week`: 102 passed and 3 `homes` failures (the new Admin-område link), fixed; `homes` and `control-test` re-run: 29 passed.

**Decisions taken in place of the founder.** (1) The operator mark moves on one click; Control tests made before keep their Class's Institution; there is no unmark. (2) The Admin role, not a new session role, carries the Epic 4/5 Class actions, held to Control test Classes the Admin owns. (3) A Control test Class takes no other staff and no other Class session, and is hidden from every Lærerhjem list, also the owner's own (they reach it from «Kontrolltest»). (4) Guide choices are the latest default and every Lecturer-edited version, labelled by number and «endret av en Faglærer» with no Class name. (5) A new Control test gets LLM players at the config's first offered level, as «Lag Klasseøkt» does. All new copy is [ASSUMPTION] draft except «Teller aldri med i en Klasseøkt.».

**Residual risks.** A Control test whose only owner loses the Admin role or is deactivated cannot be opened by another Admin (no transfer). Personal data: no new table; `class_sessions.kind` and `institutions.operator_owned` hold no personal data.
