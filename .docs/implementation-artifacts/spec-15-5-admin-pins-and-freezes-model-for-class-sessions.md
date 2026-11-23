---
title: 'Story 15.5: The Admin pins and freezes a model for Class sessions'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: '79e0e28d2767ff6036256d11a10d16f3d08f9c85'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-15-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      During a freeze of a mock config that lacks a newer MOCK_SPEC purpose, every process start derives and pins a new mock row.
    evidence: |-
      app/ai/seed.py _missing_prompts reads config.active_default, which now names the frozen config; ensure_zero_config derives and pins a new row each start while the freeze stands, but the default stays the frozen config. Mock environments only (local, test, ci). Read from the code, not run; settle by starting the stack twice with such a freeze.
    location: >-
      backend/app/ai/seed.py _missing_prompts, ensure_zero_config
    severity: low
  - summary: >-
      The Admin's lists are unpaginated: every saved Class session and every measurement row is read per page load.
    evidence: |-
      sessions.model_settings and config.catalogue read all rows; offered_effort_levels runs once per config. Bounded at pilot scale (a few dozen Class sessions, a handful of configs); not measured at Story 15.10 load.
    location: >-
      backend/app/modules/ops/ai_models.py list_sessions, backend/app/ai/config.py catalogue
    severity: low
---

<intent-contract>

## Intent

**Problem:** A Class session gets the active default model config when it is created (Story 5.1) and the lock freezes it (AD-4), but the Admin cannot see the configs with their measured figures, cannot choose a config for one Class session, and cannot hold one config across the Class sessions of a learning study (FR-68, FR-78, UX-DR57).

**Approach:** A new Admin page «KI-kostnad» (`/admin/ki-kostnad`), the first page of the area 15.6/15.7 extend, owned by `modules/ops`: it lists every model config with its facts and the stored `effort_measurements` figures, every saved Class session with its model setting (pin before the lock, read-only after), and a study freeze. All model-config reads and writes go through `app/ai/config.py`; the Class session row is changed only by `sessions.service`.

## Boundaries & Constraints

**Always:**
- Policy `ai_models.manage` (role `admin`) in `platform/authz` on every route under `/api/admin/ai`; a Lecturer gets 403 `forbidden`.
- Config list (`GET /api/admin/ai/model-configs`): per config id, name, provider, endpoint, region, model version, quantisation, prompts map, whether referenced, whether it may answer here (`config.may_answer`), whether it is the active default, and per Effort level (config order): name, label, offered here, and the newest measurement that counts here (`games`, `cost_per_game_usd`, `fallback_share`, `switched_share`, `time_per_order_p95_s`, `mock`, `approved_at`) as stored — decimal strings, no arithmetic. Read through a new `config.catalogue()`.
- Pin (`PUT /api/admin/ai/class-sessions/{id}/model-config {model_config_id}`): in one transaction under the session row lock (`repo.session_row(lock=True)`) `sessions.service.pin_model_config` refuses 409 `model_config_frozen` when `is_locked(row, now)` (locked or Start date passed); otherwise sets `model_config_id`; with LLM players keeps the Effort level if the new config offers it, else its first offered level, else NULL; creates the budget row if none exists (`budget.state` then `set_budget`); marks the config referenced; emits `session:<id>`; audits `model_config.pinned` (target `class_session_id`, change `{model_config_id, previous_model_config_id}`). Pinning the config already pinned is a no-op without audit.
- A config is pinnable only if at least one of its Effort levels has a measurement that counts in this environment (`config.measured_levels`), else 409 `no_measured_level`; unknown config 404 `config_not_found`; unknown session 404 `not_found`.
- A pin answer and the session list carry `warnings: ["provider_key_missing"]` when the session has LLM players, is not locked and its config may not answer here (AD-17); the page shows «Klasseøkten kan ikke låses uten nøkkelen til leverandøren.» style copy.
- Locked session row in the list: read-only model version, endpoint and prompt versions taken from the snapshot's `session_runtime` (`model_config_id`, `prompt_versions`), the config facts read through `config.get`.
- Freeze (`POST /api/admin/ai/freezes {model_config_id, class_session_ids (1–50)}`): table `ai_model_freezes` (id, model_config_id FK, class_session_ids uuid[], frozen_at, lifted_at), at most one with `lifted_at IS NULL` (partial unique index). Refusals: 409 `freeze_active`, `no_measured_level`, 404 `config_not_found`, 404 `not_found` (fields.class_session_ids), 409 `model_config_frozen` when a chosen session is locked with another config (fields.class_session_ids). Each chosen unlocked session is pinned as above, all in one transaction; audit `model_config.frozen` (target `model_config_id`, change `{class_session_ids}`). `POST /api/admin/ai/freezes/{id}/lift` sets `lifted_at`, audits `model_config.freeze_lifted`; lifting a lifted freeze is 409 `freeze_lifted`.
- While a freeze is active, `config.active_default()` returns its config if it offers a level here, else None (never another pin): new Class sessions get it; a session in the active freeze refuses a pin to another config with 409 `study_frozen`.
- Labels: audit target `model_config_id` labelled «name · model version» via `audit.register_labels`; nb.ts audit action names for the three actions.
- All copy in `frontend/src/copy/nb.ts` marked `[ASSUMPTION] Story 15.5`; one primary button on the page (the freeze); Pins and lift are secondary; tables reflow at 60em like `/admin/evaluering`.
- Seam (Epic 12): the AI assessment pins its model through the lock's pin providers from `class_sessions.model_config_id`, like `debrief_ai_text`; nothing assessment-specific here.

**Never:**
- No code outside `app/ai` touches `ai_model_configs`, `effort_measurements`, `ai_default_pins` or `ai_model_freezes`.
- No config editing UI; no new provider values; no change to how games read `SessionRuntime` at play time; no cost page (15.6).
- No user id in `ai_model_freezes` (the actor is in the audit only).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Pin before Start | unlocked LLM session, config B measured | 200; row has B, level kept or B's first; audit row; Lecturer GET lists B's offered levels | — |
| Pin after lock | `locked_at` set (or Start date passed) | 409 `model_config_frozen` | row unchanged, no audit |
| Unmeasured config | no counting measurement | 409 `no_measured_level` | nothing stored |
| Key missing | LLM session, `may_answer` false | 200 with `warnings: ["provider_key_missing"]` | — |
| Lecturer | any route | 403 `forbidden` | — |
| Freeze | config A, two unlocked sessions | both pinned to A; new session created gets A; audit | — |
| Second freeze | a freeze is active | 409 `freeze_active` | — |
| Study re-pin | session in active freeze, other config | 409 `study_frozen` | — |
| Lift then create | freeze lifted | new sessions take the newest pin again | — |
| Edit frozen config | `config.derive(A)` | new row; A unchanged | trigger refuses UPDATE of A |

</intent-contract>

## Code Map

- `backend/app/ai/config.py` -- `get`, `list_all`, `measurements`, `_counts`, `offered_effort_levels`, `may_answer`, `mark_referenced`, `pin`, `active_default` (add freeze preference), `derive`. Add `measured_levels`, `catalogue`, `freeze`, `lift_freeze`, `active_freeze`, `config_labels`.
- `backend/app/ai/models.py` -- tables; add `model_freezes`. `backend/app/ai/calls.py:23` `TABLES_WITHOUT_PERSONAL_DATA` -- add it (no personal data).
- `backend/app/ai/budget.py:114,182` -- `set_budget` resets the limit, so check `state` first.
- `backend/app/modules/sessions/service.py:573` `is_locked`; `:800` `create_session` (uses `active_default`); `:886` `get_session` (Lecturer's `effort_levels` from the row's config); `:3868` `lock` (row lock, `may_answer`, snapshot); `:5315` `evaluation_sessions` pattern. `sessions/repo.py:99` `evaluation_rows`, `session_row(lock=True)`.
- `backend/app/modules/ops/routes.py`, `evaluation.py` -- route/service/audit pattern; `class_session_labels`.
- `backend/app/platform/authz.py:82` `POLICIES`; `platform/audit.py:90,181` `record`, `register_labels`; `backend/app/main.py:116,129` router and labels.
- `backend/tests/sessions/test_ai_mode.py:50` `two_levels` (mock config, two measured levels, pinned); `tests/sessions/test_lock.py:52` `dated`; `tests/sessions/test_dates.py` `new_session`, `save`, `START`; `tests/conftest.py:176` `AI_TABLES`; `tests/test_migrations.py:112,141,275`.
- `frontend/src/modules/admin/evaluation-page.tsx`, `api.ts:343`, `src/app/(app)/admin/evaluering/page.tsx`, `modules/identity/{homes.ts,home-page.tsx:80}`, `src/lib/number-format.ts` `formatNumber`, `e2e/admin-evaluation.spec.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0067_model_freezes.py` -- table `ai_model_freezes` + partial unique index; `tests/test_migrations.py` HEAD and round trip.
- `backend/app/ai/{models,config,calls}.py` -- table, catalogue, measured levels, freeze/lift/active, `active_default` preference, labels.
- `backend/app/modules/sessions/{repo,service}.py` -- `model_setting_rows`, `set_model_config`; `ModelSetting` dataclass, `model_settings()`, `pin_model_config()` with `ModelConfigFrozen`.
- `backend/app/modules/ops/{ai_models,ai_schemas,ai_routes}.py` -- service (pin with study check, freeze, lift, list), schemas, routes under `/api/admin/ai`.
- `backend/app/platform/authz.py`, `backend/app/main.py`, `identity/personal_data.py` (via `TABLES_WITHOUT_PERSONAL_DATA`), `tests/conftest.py` `AI_TABLES`.
- `backend/tests/ops/test_model_pinning.py` -- every matrix row, audit rows, Lecturer's offered levels after a pin, snapshot holds the pinned config after the lock.
- `frontend/src/copy/nb.ts`, `src/modules/admin/{ai-models-page.tsx,ai-models.ts,ai-models.test.ts,api.ts}`, `src/app/(app)/admin/ki-kostnad/page.tsx`, `modules/identity/{homes.ts,home-page.tsx}`, `src/lib/api/*` (regenerated) -- page and link.
- `frontend/e2e/admin-ai-models.spec.ts` -- configs with figures, pin, locked read-only, freeze and lift, axe at 320/1440.

**Acceptance Criteria:**
- Given the Admin on «KI-kostnad», when the page loads, then each config shows provider, endpoint, region, model version and per Effort level the stored cost per Game, fallback share and Play-guard switched share (or «Ikke målt»).
- Given a pinned session, when its Lecturer opens the Klasseøkt, then «Innsatsnivå» offers only the pinned config's offered levels.
- Given a pinned LLM session, when it locks, then `snapshot.session_runtime.model_config_id` is the pinned config and the page shows it read-only with its prompt versions.
- Given an active freeze over sessions S1, S2, when a Lecturer creates a new Class session, then it holds the frozen config; after lifting, it holds the newest pin.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
- verdicts: 39 findings — high 0, medium 6, low 25, false 5, maybe-false 3
- findings:
  - `[medium]` `[patch]` Blind: the freeze form says «Ingen Klasseøkt kan få en ny modell nå.» while the session list is loading or failed — the form now renders only when the list succeeded; a skeleton or the page error shows otherwise.
  - `[low]` `[reject]` Blind: audit change values `model_config_id`/`previous_model_config_id` show as raw ids — the audit holds ids and codes by rule (AD-14); the targets are labelled (`class_session_id`, `model_config_id`).
  - `[low]` `[reject]` Blind: a frozen config that cannot answer turns new sessions Rule-based with no warning — the config entry already shows «Fryst for en studie» beside the «Leverandøren har ingen nøkkel her …» line; a second warning adds surface.
  - `[low]` `[reject]` Blind: the one-active-freeze guarantee is tested only sequentially — the partial unique index enforces it in the database (asserted in `test_migrations.py`); a concurrency test adds a slow test for a rare double submit.
  - `[low]` `[patch]` Blind: the 403 loop missed the PUT pin and the lift — both added.
  - `[low]` `[patch]` Blind: the freeze's 1–50 limit is untested — 0 and 51 ids now answer 422 in the test.
  - `[medium]` `[patch]` Blind: the e2e freeze leaks into later specs when it fails midway — the steps run in `try/finally` that lifts any freeze.
  - `[low]` `[defer]` Blind: unbounded session and measurement lists — deferred (frontmatter), bounded at pilot scale.
  - `[low]` `[reject]` Blind: a freeze cannot be amended; sessions created during it are not study members — by design: a study is a fixed set, new sessions only take the default; lift and freeze again to change it (audited).
  - `[low]` `[patch]` Blind: `api.ts` lacks a trailing newline — added.
  - `[low]` `[patch]` Blind: a row's model choice stays stale after a refetch — rows are keyed on the session id and its pinned config, so a change re-seeds the choice.
  - `[low]` `[reject]` Blind: the lift button's name is two sentences and `LLM = "llm"` duplicates `AiMode` — consequence-labelled buttons are the UX rule; `ops` does not import the sessions enum for one string.
  - `[false]` `[reject]` Blind: `openapi.json`/`schema.ts` and the root files are missing from the diff — the generated files were left out of the review diff on purpose (regenerated by `app.openapi` and `npm run api:generate`); `policy.py` and `walkthrough-chart.tsx` are not this change's and are never committed.
  - `[medium]` `[patch]` Edge: an LLM session pinned to a measured config whose provider has no key stores no Effort level, and the lock would later freeze the config's first level, measured or not — the pin now falls back to the config's measured levels (`config.measured_levels`); the key-missing test asserts the stored level.
  - `[low]` `[reject]` Edge: the study check is read before the session row lock, so a freeze committed in between could be overwritten — needs two Admins acting within milliseconds; the audit records both.
  - `[false]` `[reject]` Edge: a locked Rule-based session wrongly blocks a freeze — a locked session's model can no longer change, so it cannot get the study's config; refusing with `model_config_frozen` is the rule.
  - `[false]` `[reject]` Edge: `config.freeze` may raise `ConfigNotFound` as a 500 — `_pinnable` checks the config in the same transaction, and a referenced config row can never be deleted (trigger).
  - `[low]` `[defer]` Edge: unpaginated list — same as the Blind row.
  - `[medium]` `[patch]` Edge: freeze form on a pending or failed list — same as the Blind row.
  - `[low]` `[patch]` Edge: a refused lift loses its reason when the refetch hides the freeze block — the lift's error line now sits outside that block.
  - `[low]` `[patch]` Edge: stale row choice — same as the Blind row.
  - `[low]` `[reject]` Edge: the freeze form's model stays seeded from the first render — configs only gain rows and a measured config stays measured, so the seeded id stays valid.
  - `[low]` `[patch]` Verification gap: the `model_config_id` audit label was never exercised — the freeze test reads the audit page for `model_config.frozen` and `model_config.freeze_lifted` and asserts «studie · studie-v1».
  - `[medium]` `[patch]` Verification gap: the newest counting measurement was not pinned — a second, newer real measurement with another cost is added and the newer one is asserted.
  - `[medium]` `[patch]` Verification gap: figures were never rendered under their columns — `ai-models-page.test.tsx` renders `ConfigEntry` with a real measurement and asserts each cell by column.
  - `[low]` `[patch]` Verification gap: freeze with a locked session holding the config, and with a Start date passed — new test `test_a_freeze_takes_a_locked_session_only_when_it_holds_the_config`.
  - `[low]` `[patch]` Verification gap: the saved-only listing filter was not asserted — an unsaved draft is shown to be absent.
  - `[low]` `[patch]` Verification gap: the stored level after a key-missing pin was not asserted — asserted (with the Edge patch).
  - `[maybe-false]` `[defer]` Verification gap (other): the zero-config seed derives a new mock row at every start during a freeze — deferred (frontmatter) with what would settle it; low if true.
  - `[low]` `[reject]` Verification gap (other): `config.pin` from the CLI has no effect during a freeze — `active_default`'s docstring states the freeze wins; the CLI is the operator's.
  - `[maybe-false]` `[reject]` Intent: the Lecturer's rendered «Innsatsnivå» is not exercised, only its API — the Lecturer's page is unchanged and reads `effort_levels` from that same API, which the test asserts; low if true.
  - `[low]` `[reject]` Intent: `active_default` is shared with other callers and only the creation path is asserted — the lock reads the session row, not the default; the copy path (5.18) calls the same function and is covered by its own tests in the full suite.
  - `[maybe-false]` `[reject]` Intent: the key warning is tested by monkeypatching `may_answer`, and its UI text is not asserted in e2e — the stack runs the mock in `local`, so a real missing key cannot be staged; the render test asserts the config's no-key line.
  - `[low]` `[reject]` Intent: the page has no component tests beyond helpers — patched in part (the config entry); the rest runs in Playwright at two widths.
  - `[low]` `[patch]` Intent: the freeze flow had no axe check — `expectAccessible` added while the freeze is shown.
  - `[false]` `[reject]` Intent: the audit target label is unasserted — same as the Verification row, now asserted.
  - `[low]` `[reject]` Intent: pins apply to Rule-based sessions too — the story says «a Class session»; a later switch to LLM players then uses the pinned config.
  - `[low]` `[reject]` Intent: `study_frozen`, `freeze_active`, no default when the frozen config cannot answer, and Start-date-passed as locked go beyond the AC — each makes «no model change during a Class session or a study» hold; recorded in Design Notes.
  - `[false]` `[reject]` Intent: the e2e specs may not have been run — they ran: 63 passed on the local stack.

## Design Notes

One active freeze at a time keeps «the default» singular; a frozen config that cannot answer here yields no default rather than silently another model (FR-68: no model change during a study). The study check (`study_frozen`) is made in `ops` before `sessions.pin_model_config` within the same transaction, reading `config.active_freeze(session=s)`.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/ops/test_model_pinning.py tests/test_migrations.py tests/identity/test_personal_data_registry.py tests/test_authz_rules.py -q` -- expected: pass
- `cd backend && uv run pytest -q -n 8 --maxprocesses=8` -- expected: pass
- `cd frontend && npm run typecheck && npx vitest run && npm run lint:colours && npm run check:copy && npm run build` -- expected: pass
- `cd frontend && npx playwright test admin-ai-models homes class-session --workers=4` -- expected: pass

## Auto Run Result

Status: done

**Summary.** «KI-kostnad» (`/admin/ki-kostnad`, linked from the Admin-område), the first page of the area Stories 15.6 and 15.7 extend. It lists every model config with provider, endpoint, region, model version, its standing (default, frozen, no key here) and per Effort level the newest counting measurement as stored (cost per Game, reserve-order share, Play-guard switched share, games and date; «Ikke målt» / «Testmåling uten tall»), read through the new `ai.config.catalogue`. Each saved Class session shows its model and level; before its Start date the Admin pins a measured config (`PUT /api/admin/ai/class-sessions/{id}/model-config`, under the session row lock, audited `model_config.pinned`), which keeps the level in force when offered, else the first offered (or measured) one, creates the budget row and marks the config referenced; the Lecturer's «Innsatsnivå» then offers that config's levels. Once locked or past the Start date the pin is refused `409 model_config_frozen` and the row shows the frozen model version, endpoint and prompt versions from `SessionRuntime`. A study freeze (`POST /api/admin/ai/freezes`, table `ai_model_freezes`, one active) pins one config to the chosen Class sessions in one transaction and makes it `active_default` until lifted (`/lift`); sessions of the study refuse another config (`study_frozen`); audited `model_config.frozen` / `freeze_lifted`. A key-missing provider gives `warnings: ["provider_key_missing"]`.

**Decisions taken in place of the founder.** One active freeze at a time; while frozen, a config that cannot answer here gives no default (new sessions Rule-based) rather than another model; a passed Start date counts as locked; Rule-based sessions can be pinned; freeze capped at 50 Class sessions; a config is pinnable only with a measurement that counts here, but a missing key only warns; all copy `[ASSUMPTION] Story 15.5`.

**Seam.** Epic 12's assessment takes its model through a lock pin provider reading `class_sessions.model_config_id` (as `debrief_ai_text`); nothing assessment-specific was added.

**Personal data.** New table `ai_model_freezes` holds ids and times only (no `user_id`; the actor is in the audit), listed as `none` via `ai.calls.TABLES_WITHOUT_PERSONAL_DATA`.

**Files.**
- `backend/migrations/versions/0067_model_freezes.py` — the freeze table and its one-active index.
- `backend/app/ai/{models,config,calls}.py` — table, catalogue, measured levels, freeze/lift/active, `active_default` preference, audit labels, registry name.
- `backend/app/modules/sessions/{repo,service}.py` — `model_settings`, `pin_model_config`, `ModelConfigFrozen`.
- `backend/app/modules/ops/{ai_models,ai_schemas,ai_routes}.py` — service, envelopes, routes under `/api/admin/ai`.
- `backend/app/platform/authz.py`, `backend/app/main.py` — policy `ai_models.manage`, router, `model_config_id` labels.
- `backend/tests/ops/test_model_pinning.py`, `tests/{conftest,test_imports,test_migrations}.py`.
- `frontend/src/modules/admin/{ai-models-page.tsx,ai-models-page.test.tsx,ai-models.ts,ai-models.test.ts,api.ts}`, `src/app/(app)/admin/ki-kostnad/page.tsx`, `modules/identity/{homes.ts,home-page.tsx}`, `src/copy/nb.ts`, `src/lib/api/*` (regenerated), `e2e/{admin-ai-models,homes}.spec.ts`.

**Review.** Four sonnet sub-agents (blind, edge case, verification gap, intent alignment); 39 findings. Patched: 6 medium entries (freeze form on a pending list, e2e freeze cleanup, unmeasured level after a key-missing pin, newest measurement, figure columns render test — and the Edge duplicate) and 13 low rows. Deferred: 2 (seed re-derive during a freeze, unbounded lists). Rejected: the rest, each with its reason in the triage log.

**Follow-up review: recommended.** Patched medium entries: 5 root causes; patched low: 9. Unverified risk: the measured-level fallback of a pin is not exercised with an endpoint that offers nothing (the mock endpoint always offers here), so `measured_levels` as the fallback ran only by reading.

**Verification.**
- Backend full suite (`-n 8 --maxprocesses=8`, DB `olspillet_e15`): 3452 passed, 4 skipped; ruff check and format clean.
- Frontend: typecheck ok; Vitest 1132 passed; `lint:colours`, `check:copy` passed; `next build` compiled.
- Playwright (`--workers=4`, stack on `olspillet_e15stack`): `admin-ai-models`, `homes`, `admin-audit`, `admin-evaluation`, `order-field`, `playout`, `class-session-lock`, `class-session` — 63 passed; axe at 320 and 1440 px. Screenshots at 360 and 1440 px checked: one column on phone, tables reflow to labelled blocks, one primary button (the freeze).
- Matrix: every row covered by `test_model_pinning.py` (pin before Start, after lock and Start passed, unmeasured, key missing, Lecturer 403, freeze, second freeze, study re-pin, lift then create, derive of a frozen config).
- New tests over 1 s: `test_a_study_freeze_holds_one_config_until_it_is_lifted` about 1.6 s, `test_a_pin_before_the_start_date_replaces_the_config_and_its_levels` about 1.1 s.

**Residual risks.**
- A pin and a freeze by two Admins at the same instant can race past the study check (audited).
- During a freeze whose config cannot answer, new Class sessions are Rule-based until the key is set or the freeze is lifted.
