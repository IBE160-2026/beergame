---
title: 'Story 5.15: Set a shipping capacity (cut list, FEATURE_CAPACITY)'
type: 'feature'
created: '2026-11-20'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 'd7534dbc8c4cf553f5c8739f83beb8e783e4c778'
context:
  - '{project-root}/.docs/implementation-artifacts/epic-5-context.md'
  - '{project-root}/backend/app/modules/sessions/README.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The engine can cap what a Seat ships per Week (`GameSettings.capacity`, Story 1.12), but the Klasseøkt refuses `capacity` as `not_editable` (Story 5.3), so a Lecturer cannot teach a chain with a bottleneck.

**Approach:** Behind `FEATURE_CAPACITY` (`get_settings().feature_capacity`), make `capacity` an editable Game setting of the Klasseøkt: judged by the engine (range 1–100 per Role, warning `capacity_below_peak_demand`), stored in the session's `GameSettings`, frozen by the lock. The API tells the screen whether the flag is on (`capacity_enabled`); the screen shows a «Kapasitet» setting (off by default; one Role or all), a help line, and marks the capped Role in «Kjeden ved start».

## Boundaries & Constraints

**Always:**
- Draft shape is the engine's: `game_settings.capacity` = `{role: int}` or `null`/`{}` (no cap). "All Roles" = one key per Role of the chain with the same value.
- Flag off: a draft whose `capacity` is non-empty → check answers error `capacity: {code: "feature_disabled"}`; save answers **422 `feature_disabled`** with `fields: {"capacity": "feature_disabled"}` and stores nothing. `capacity: null`/`{}` or no key is accepted. A capacity already stored (flag switched off later) is kept and does not block saving other settings. `ClassSessionOut.capacity_enabled` is false and the screen shows no capacity field, row, help line or chain mark. Every other behaviour unchanged.
- Flag on: errors per Role keyed `capacity.<role>` with `CAPACITY_RANGE` (1–100): a non-integer (`"abc"`, `2.5`, `true`) → `not_a_number` with the range; ≤0 or >100 → `out_of_range` with the range. Unknown Role key or a Role outside the chain → `capacity` `invalid`. Warnings `capacity_below_peak_demand` never block.
- Locked session: changed capacity → 409 `session_locked` (existing `_settings_to_store` path); the lock's snapshot carries the capacity (`build_snapshot` dumps the settings).
- All copy in `nb.ts` marked `[ASSUMPTION]` draft copy. Web app holds no range or rule.

**Never:** No change to `backend/app/engine/` (100 % gate), the briefing or the play screen (Story 6.22), the Debrief (Epic 9). No migration. No change to the demo Class. No edit of `sprint-status.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default | new session, flag on | `capacity` absent from `game_settings`; `capacity_enabled: true`; row «Kapasitet: Ingen» | — |
| One Role | save `{"retailer": 6}` | stored; GET shows it; `is_classic` false | — |
| All | save 4 roles × 6 | stored; row «6 per uke for alle roller» | — |
| Below peak | 6 with peak 8 | saved; warning under the setting | non-blocking |
| Range | `{"retailer": 0}` / `101` / `"x"` | nothing stored | 422 `invalid_settings`, `capacity.retailer` with 1–100 |
| Bad key | `{"boss": 5}` | nothing stored | 422 `invalid_settings`, `capacity` `invalid` |
| Flag off | save `{"retailer": 6}` | nothing stored | 422 `feature_disabled` |
| Flag off, null | save `capacity: null` + other change | saved | — |
| Locked | capacity set, lock runs | snapshot `settings.capacity` = stored; change → 409 `session_locked` | — |

</intent-contract>

## Code Map

- `backend/app/modules/sessions/service.py:372` `EDITABLE_SETTINGS`; `:377` `judge_settings` (flag gate, `feature_disabled`, validate with `capacity_enabled = flag or judged.capacity == stored.capacity`); `:342` `_parse_problem` (map `capacity.<role>` int errors to `not_a_number` + range; other capacity errors `capacity` `invalid`); `:305` `range_of` (add `capacity.<role>` → `CAPACITY_RANGE`); `:892` `_settings_to_store` raises new `FeatureDisabled(_FieldsError)` (code `feature_disabled`) when a problem has that code; `:630` `get_session` adds `capacity_enabled`. Pattern for flag handling: `sim.py:333` and `:367`.
- `backend/app/modules/sessions/schemas.py:146` `ClassSessionOut` -- add `capacity_enabled: bool`.
- `backend/app/modules/sessions/routes.py:160` -- catch `FeatureDisabled` → 422; docstring.
- `backend/app/modules/sessions/README.md` -- settings section: capacity and the flag.
- `backend/tests/sessions/test_settings.py` -- existing settings tests (reuse its helpers, `monkeypatch` of `get_settings().feature_capacity` as `tests/games/test_create.py:262`); `backend/tests/sessions/test_lock*.py` for a snapshot assertion.
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerate (`npm run api:generate` after dumping openapi; see how others did it).
- `frontend/src/modules/sessions/settings.ts` -- `CapacityDraft`, `draftOf(settings, capacityEnabled)`, `settingsBody` (adds `capacity` only when the draft has it), `capacityProblem`, warning text, `warningsBySetting` folds `capacity.*` into `capacity` and dedupes.
- `frontend/src/modules/sessions/settings-form.tsx` -- `CapacityFields` section after `DemandFields`: `Switch` (`@/components/switch`), `SegmentedChoice` («Alle roller»/«Én rolle»), `SelectField` Role, `TextField` units; help line; `otherErrors` skips `capacity*`.
- `frontend/src/modules/sessions/sessions.ts` -- `settingRows(..., capacityEnabled)` row `capacity`; `chainText` capacity sentence; `capacityText`.
- `frontend/src/modules/sessions/chain-diagram.tsx` -- «maks N» under a capped Role; text via `chainText`.
- `frontend/src/modules/sessions/class-session-page.tsx:138,209` -- pass `item.capacity_enabled` to `draftOf`, `SettingsBlock`, `ChainDiagram`.
- `frontend/src/copy/nb.ts:708–863` -- copy.
- Tests: `frontend/src/modules/sessions/settings.test.ts`, `frontend/e2e/class-session-settings.spec.ts` (fresh data via `frontend/e2e/support/classes.ts`).

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/sessions/{service,schemas,routes}.py`, `README.md` -- flag gate, judging, `capacity_enabled`, 422 `feature_disabled`.
- `backend/tests/sessions/test_settings.py` (+ lock test) -- every matrix row.
- `frontend/src/lib/api/*` -- regenerate.
- `frontend/src/copy/nb.ts`, `sessions.ts`, `settings.ts`, `settings-form.tsx`, `chain-diagram.tsx`, `class-session-page.tsx` -- UI.
- `settings.test.ts`, `class-session-settings.spec.ts` -- unit tests of draft/body/rows/text; one e2e: set capacity for one Role below peak, see warning, save, see row, help line and chain mark; axe clean.

**Acceptance Criteria:**
- Given the flag on and an unlocked session, when the Lecturer opens the settings, then «Kapasitet» is off; switching it on, choosing «Én rolle» Detaljist and 6, and saving stores `{"retailer": 6}` and shows the warning under the setting without blocking.
- Given a capacity is set, when the screen renders, then the help line «En rolle med kapasitet kan ha lager og restordre samtidig. Studentene får vite kapasiteten i briefingen.» shows and «Kjeden ved start» names the capped Role and its capacity in text.
- Given the flag off, when the screen renders, then no capacity text appears, and a PUT with a capacity answers 422 `feature_disabled`.

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 30 findings — high 0, medium 7, low 16, false 7, maybe-false 0
- findings:
  - `[medium]` `[patch]` blind: a stored map that is neither one Role nor all alike (set via the api) opened as one Role, so any save with the block open dropped the other caps. Fixed: `CapacityDraft.kept` holds that map and `capacityBody` sends it back unchanged until the Lecturer changes the capacity; unit test added.
  - `[medium]` `[patch]` blind: with the flag off, a stored capacity sent back unchanged got 422. Fixed: only a capacity that differs from the stored one is `feature_disabled`; test added.
  - `[low]` `[reject]` blind: with the flag off, null or `{}` clears a stored capacity. That is intended (it lets a stored cap be removed). The engine turns `{}` into None, so no empty-map error can occur.
  - `[medium]` `[patch]` blind: a locked session sent a capacity with the flag off answered 422 rather than 409. Fixed: a locked session answers `session_locked` first; test added, README updated.
  - `[false]` `[reject]` blind: the `capacity` invalid comment is wrong on a short chain. `roles` is not editable (`not_editable`), and every Class session has the Classic four-Role chain.
  - `[low]` `[reject]` blind: with the flag off the screen hides a cap that is still in force. This needs the flag to be switched off while a session holds a cap, which is rare. Recorded as a design decision (hidden, frozen, still played).
  - `[low]` `[patch]` blind: switching on (or changing scope) before typing showed `not_a_number` at once. Fixed: no check runs while the units field is empty.
  - `[low]` `[reject]` blind: the capacity warning does not name the Role. This is deliberate, so that four Roles capped alike warn once; the list row names the Roles.
  - `[low]` `[reject]` blind: the hint «Et helt tall over 0.» gives no upper limit. It is the story's own wording, and the api's error states the full 1–100 range.
  - `[low]` `[reject]` blind: the list (downstream first) and the chain text (upstream first) give capped Roles in opposite orders. Each follows the order of its own surface.
  - `[low]` `[reject]` blind: `settingsBody` falls back to the Classic chain by default. Every caller passes the session's chain, and the chain is always Classic.
  - `[low]` `[reject]` blind: test gaps (an «Alle ledd» e2e test, a check on a locked session, lax coercion). «Alle ledd» is covered by the api and unit tests, and the locked check is the existing Story 5.3 path. Coercion was checked: the engine's fields are `strict=True`, so `"6"` and `true` are refused.
  - `[low]` `[reject]` blind: `capacityProblem` shows only one Role's error. With «Alle ledd» every Role has the same value, so the same error.
  - `[low]` `[reject]` blind: in the diagram, `capacityOf` is called repeatedly and has a dead `?? 0`. This is cosmetic. «Maks N» at y=113 fits within the 130 height, and the e2e test renders it.
  - `[medium]` `[patch]` edge: the mixed-map loss. Same root cause and fix as the first blind row.
  - `[medium]` `[patch]` edge: a save of another setting rewrites a mixed capacity. Same root cause and fix as the first blind row.
  - `[medium]` `[patch]` edge: with the flag off, a stored capacity sent back unchanged got 422. Same fix as the second blind row.
  - `[low]` `[patch]` edge: a locked session with the flag off answered 422 rather than 409. Same fix as the fourth blind row.
  - `[low]` `[patch]` edge: switching on with empty units showed `not_a_number` at once. Same fix as the seventh blind row.
  - `[false]` `[reject]` edge: the chosen Role can lie outside the chain. The chain is fixed at the four Classic Roles.
  - `[low]` `[reject]` edge: with the flag off, `settings_warnings` still carries capacity warnings. The screen shows no capacity row, so nothing is displayed, and this is rare (see the hidden-cap row).
  - `[false]` `[reject]` edge (claim): a stored capacity blocks saves with the flag off. Already fixed by the patch above; the test covers the resend.
  - `[false]` `[reject]` edge (claim): 422 rather than 409 when locked. Already fixed by the patch above.
  - `[low]` `[patch]` verification-gap: the «Maks N» mark in the diagram was not asserted. Added e2e assertions: «Maks 6» once with the flag on, no «Maks» with the flag off.
  - `[medium]` `[patch]` verification-gap (other): the mixed-map loss. Same fix as the first blind row.
  - `[false]` `[reject]` intent: the flag-off screen is tested by rewriting the api's answer, not with a real flag-off server. The screen reads only `capacity_enabled`, so the rewrite exercises the same path; the real flag is tested at the api.
  - `[low]` `[reject]` intent: the screen edits one Role or all, while the api accepts any map. That is the story's "for one Role or for all", and a stored map is now kept (patch above).
  - `[false]` `[reject]` intent: the screen does not show the capacity read-only once locked. A locked session already shows the settings list read-only (Story 5.11), and that list includes the capacity row.
  - `[low]` `[reject]` intent: a locked session with the flag off hides the frozen cap. Same as the hidden-cap row.
  - `[false]` `[reject]` intent: the help line promises a briefing that does not exist yet. The story asks for this line, and Story 6.22 delivers the briefing.

The first set of reviewers never reported (they were stopped when the turn ended); all four were rerun and their reports are triaged above. No independent visual reviewer was run by this builder; the orchestrator runs its own visual check of `frontend/`.

## Design Notes

Founder-level decisions taken here:
- Flag-off refusal on save is a top-level 422 `feature_disabled` (not inside `invalid_settings`); on the check route it is a per-setting error with code `feature_disabled`, since that route returns errors by setting.
- A capacity stored while the flag was on survives a later flag-off: it is kept, frozen at the lock and played (same principle as `RULES_VERSIONS.md`: a stored setting runs whatever the flag says now), but the screen no longer shows it.
- The UI offers one Role or all Roles. A stored map that is neither (only possible via the API) opens as «Én rolle» with the first capped Role, downstream first.
- «Kjeden ved start» marks a capped Role with «maks N» under its Lager line and a sentence in the figure's text.
- `capacity_below_peak_demand` for all four Roles shows once (deduped text without the Role name).

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/sessions/test_settings.py -q` -- pass
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass
- `cd frontend && npm run typecheck && npm test && npm run build && npx playwright test` -- pass

## Auto Run Result

Status: done

**Summary.** `capacity` is now an editable Game setting of the Klasseøkt behind `FEATURE_CAPACITY`.
- **Flag on:** the engine judges each Role's value (1–100, `capacity.<role>` errors) and warns below peak demand without blocking. The value is stored in the session's `GameSettings` and frozen into the snapshot by the lock; a change after the lock is 409 `session_locked`.
- **Flag off:** `ClassSessionOut.capacity_enabled` is false and the screen shows nothing about capacity. A capacity that differs from the stored one answers 422 `feature_disabled`. A stored capacity is kept and never blocks other settings.
- **Screen:**
  - A «Kapasitet» Bryter (off by default), «Alle ledd» or «Ett ledd», the Role, and the units with inline error and warning.
  - A help line.
  - A capacity row in the list.
  - «Maks N» under the capped Role in «Kjeden ved start», plus a sentence in its text.

**Files.**
- `backend/app/modules/sessions/{service,schemas,routes}.py`, `README.md`: the flag gate, judging, `capacity_enabled` and `FeatureDisabled`.
- `backend/tests/sessions/test_capacity.py` (new, 13 tests) and `test_settings.py` (capacity removed from the not-editable case).
- `frontend/src/lib/api/{openapi.json,schema.ts}`: regenerated.
- `frontend/src/copy/nb.ts`: draft copy marked `[ASSUMPTION]`.
- `frontend/src/modules/sessions/{settings,sessions}.ts`, `settings-form.tsx`, `chain-diagram.tsx`, `class-session-page.tsx`: the UI.
- `settings.test.ts`, `sessions.test.ts`, `frontend/e2e/class-session-capacity.spec.ts`: tests.

**Review.**
- 30 findings: medium 7, low 16, false 7.
- Patched, as four root causes:
  - A mixed stored map is kept.
  - With the flag off, a stored capacity sent back unchanged is accepted.
  - A locked session answers 409 before `feature_disabled`.
  - No check runs while the units field is empty.
- Added an e2e assertion for the «Maks N» mark.
- Nothing was deferred. Every rejected finding has its reason in the triage log.
- Follow-up review: false. By entry, 3 medium entries were patched (the mixed map, the resend with the flag off, the locked order), with no high, and each is pinned by a new test.

**Verification.**
- Backend: 2562 passed (70 s), and ruff check and format are clean.
- Frontend: typecheck passed, Vitest 441 passed, the build passed, `check:copy` passed, and Playwright 265 of 265 passed (2.4 min).
- No new test runs over 1 s, apart from the shared database setup on the first backend test.
- No migration.

**Residual risks.** If the flag is switched off while a session holds a capacity, the cap is still frozen and played, but the Klasseøkt no longer shows it.
