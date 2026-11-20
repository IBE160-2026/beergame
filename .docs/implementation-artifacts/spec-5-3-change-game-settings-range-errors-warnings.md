---
title: 'Story 5.3: Change Game settings with range errors and warnings'
type: 'feature'
created: '2026-11-19'
status: 'done'
baseline_revision: '4bdcd1d48224bf618fa06a8d98ed78080250c734'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-5-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-5-2-set-four-dates-on-datolinje.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Klasseøkt shows the Game settings read-only, so a Lecturer cannot run the game their way (FR-12), and nothing tells them what is out of range or unusual.

**Approach:** The save route takes the Game settings and a new check route judges a draft; both use the engine's `validate` and `warnings` and answer stable codes with the allowed range. The screen opens the settings block in place as Tekstfelt fields, checks on leaving a field, shows errors and warnings under each field, and adds the shared Norwegian number formatter.

## Boundaries & Constraints

**Always:**
- Editable here (each a Tekstfelt, label above): `starting_inventory`, `starting_backlog`, `supply_line`, `order_delay`, `shipping_delay`, `production_delay`, `holding_cost`, `backorder_cost`, `weeks`, `guided_weeks`, `max_order`. The engine has one starting value for every Role, so "per Role" is one field each for Startlager and Startrestordre that holds for all four Roles.
- `ClassSessionSaveIn.game_settings: dict[str, Any] | None` (omitted = unchanged). The server lays it over the stored settings (so demand and seed stay unless sent), then `GameSettings.model_validate` and `engine.validate(capacity_enabled=FEATURE_CAPACITY)`. Any failure → 422 `invalid_settings`, nothing stored, `fields: {field: {code, minimum, maximum, decimal_places}}` (bounds as decimal strings or null). Pydantic errors map per top-level field: `greater_than_equal` → `out_of_range`, otherwise `not_a_number` (`invalid` for a field outside `RANGES`), each with `RANGES` bounds when the field has them.
- Engine: the two Guided-Weeks errors carry their allowed range (0 to change Week − 1; 0 to Weeks − 1), so every error has one.
- `POST /api/class-sessions/{id}/settings-check` (policy `class_sessions.manage`), body `{game_settings}`: 200 `{errors, warnings}`, same shapes; stores and emits nothing. 403 as the save route.
- Locked (`is_locked`): a save whose settings differ from the stored ones, and every check call, answer 409 `session_locked` with `fields: {"game_settings": "locked"}`. An unchanged resend still saves.
- Order in the save transaction: archived → locked AI mode / settings → `invalid_settings` → dates (5.2).
- `ClassSessionOut` adds `settings_warnings: [{code, field, values}]` (engine `warnings` of the stored settings) and `calibrated_settings: GameSettings` (the Classic preset, the one source of the calibration line).
- Web: the settings list stays as the read view. Owners of an unlocked session get the Lenke-styled button «Endre spillinnstillinger» (`aria-expanded`), which turns the list into the fields in place with focus on the first. Leaving a changed field calls the check route with the whole draft. Errors show under the field (TextField `error`, `restordre` border, the allowed range in words); warnings show under the field as text starting «Advarsel:», never colour alone. «Lagre Klasseøkt» sends the draft; a 422 shows the field reasons and the alert line. Locked: a line says the settings can no longer change and no button shows.
- Not Classic (`is_classic` false): «Alt er fylt ut med standardene.» hidden, a line names the calibrated values from `calibrated_settings`, and «Kjeden ved start» draws the saved values.
- `frontend/src/lib/number-format.ts`: `formatNumber(value: number | string, {decimals?})` (no-break space thousands, decimal comma, true minus «−») and `parseNumber(text)` (Norwegian input to a decimal string, or null). Costs are shown with two decimals and sent as decimal strings; unreadable text is sent as typed and the server answers `not_a_number`. Vitest for both.
- All copy in `nb.ts` → `sessions.edit` (new strings marked [ASSUMPTION]).

**Never:** Demand pattern or seed editing (5.4), Inactivity limit editing (5.7), capacity UI (5.15), validation rules or defaults in the web app, a chart library, comparing DB time with host time in tests, touching the demo Class.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Change a setting | owner, `order_delay: 3` | 200; stored; `is_classic` false | – |
| Out of range | `order_delay: 4` | nothing stored | 422 `{order_delay: {out_of_range, 1, 3}}` |
| Below zero / text | `weeks: -1`, `weeks: "x"` | nothing stored | 422 `out_of_range` / `not_a_number` with range |
| Too many decimals | `holding_cost: "0.505"` | nothing stored | 422 `too_many_decimal_places` |
| Guided Weeks | `guided_weeks: 5` (change Week 5); `weeks: 4` | nothing stored | 422 with range 0–4 / 0–3 |
| Inventory and backlog | both > 0 | nothing stored | 422 `starting_inventory_and_backlog` |
| Each warning | supply 5; backorder ≤ holding; weeks 20; max_order 50 | 200; `settings_warnings` lists it under its field | never blocks |
| Check | draft with errors and warnings | 200 `{errors, warnings}`, nothing stored | – |
| Locked | Start date passed | changed settings or check | 409 `session_locked` |

</intent-contract>

## Code Map

- `backend/app/engine/settings.py:221-280` -- `validate`, `warnings`, `RANGES`; add ranges to the Guided-Weeks errors. `backend/tests/engine/` has its tests.
- `backend/app/modules/games/commands.py:115` -- `_effective_settings`: the ValidationError → fields pattern to follow.
- `backend/app/modules/sessions/{schemas,service,routes,repo}.py` -- `save_session` (service.py:327), `get_session`, `is_classic`, `repo.save` (add `game_settings`); README.md.
- `backend/app/platform/errors.py` -- `fields: dict[str, Any]`; `config.get_settings().feature_capacity`.
- `backend/tests/sessions/test_dates.py` -- helpers `new_session`, `save`, `refusal`, `at`, fixtures `klass`, `clock`; new `tests/sessions/test_settings.py`.
- `frontend/src/modules/sessions/{class-session-page,sessions,api,chain-diagram}.tsx?` -- read view, `settingRows`, `decimalComma` (replace by the formatter), save call.
- `frontend/src/components/text-field.tsx`; `src/modules/classes/roster-entry-forms.tsx:30` `LINK_BUTTON`; `src/lib/api/mutation.ts` `useAction`, `ApiRequestError.fields`.
- `frontend/e2e/class-session-dates.spec.ts`, `e2e/class-session.spec.ts` (`SIZES` with 400 % zoom), `e2e/support/classes.ts`.
- API types: `cd backend && uv run python -m app.openapi ../frontend/src/lib/api/openapi.json`, then `npm run api:generate`.

## Tasks & Acceptance

**Execution:**
- `backend/app/engine/settings.py` + engine test -- ranges on the two Guided-Weeks errors.
- `backend/app/modules/sessions/{schemas,service,routes,repo}.py`, `README.md` -- save with settings, check route, mapping, lock, warnings and calibration in the read.
- `backend/tests/sessions/test_settings.py` -- every matrix row through the routes.
- `frontend/src/lib/number-format.ts`, `number-format.test.ts` -- formatter and parser.
- `frontend/src/modules/sessions/{settings-form.tsx,settings.ts,settings.test.ts}` -- fields, draft ↔ body, error and warning copy; `class-session-page.tsx`, `sessions.ts`, `api.ts`, `src/copy/nb.ts`, regenerated `lib/api/{openapi.json,schema.ts}`.
- `frontend/e2e/class-session-settings.spec.ts` -- edit, range error on blur, warning, save, calibration line and redraw, locked read-only (fulfilled GET), axe at 320, 360, 1440 px and 400 % zoom with error and warning showing.

**Acceptance Criteria:**
- Given an unlocked Klasseøkt, when the Lecturer opens the settings block, then the eleven settings are Tekstfelt fields with labels above, and costs show a decimal comma.
- Given a delay of 4, when the Lecturer leaves the field, then «1 til 3» shows under it with a `restordre` border, and a save is refused.
- Given a backorder cost equal to the holding cost, when the Lecturer leaves the field, then a text warning shows under «Restordrekost», and the save succeeds.
- Given a saved non-Classic setting, then the defaults line is gone, the calibration line shows, and «Kjeden ved start» draws the new values.
- Given a locked session, then no field is editable and the check route answers 409 `session_locked`.

## Spec Change Log

## Review Triage Log

### 2026-11-19 — Review pass
- verdicts: 33 findings — high 0, medium 6, low 23, false 4, maybe-false 0
- findings:
  - `[medium]` `[patch]` (blind) Engine errors on settings with no field (`demand.change_week` when Weeks drop below the change) leave «Se feltene» with no reason shown. `SettingsBlock` now shows them under «Etterspørsel» (or under the list), with copy for `demand_change_week_outside_game`; e2e sets Weeks 4 and sees it.
  - `[low]` `[patch]` (blind) Warnings on rows without a field were suppressed in the open block. The `only` suppression is gone; capacity warnings cannot arise while capacity is not editable.
  - `[medium]` `[patch]` (blind) `game_settings` overwrote any field (seed, roles, demand, capacity). Only `EDITABLE_SETTINGS` (the `RANGES` keys) are taken; any other key is 422 `not_editable`; `test_settings_this_screen_does_not_own_are_refused`.
  - `[false]` `[reject]` (blind) A lock refusal shows the dates copy. `copy.dates.locked` reads «Innstillingene kan ikke endres lenger», which is about settings.
  - `[low]` `[reject]` (blind) Co-owners' saves overwrite each other. As in Story 5.2: last save wins; refetch on events is Story 6.4.
  - `[low]` `[reject]` (blind) The check route skips the archived guard. It stores nothing, and the screen offers no editor for an archived Class (now asserted in e2e).
  - `[false]` `[reject]` (blind) The pydantic mapping is too broad. The editable fields carry only `ge` constraints and strict int/Decimal types; no `le` or digit errors can occur.
  - `[false]` `[reject]` (blind) A loc-less error hides all others. Validating a dict model always yields a `loc`; the fallback key is never used.
  - `[low]` `[reject]` (blind) Stored warnings do not drop fields in error. Stored settings passed validation; only a later flag change could differ.
  - `[low]` `[reject]` (blind) A pre-existing error (capacity after the flag is off) blocks unrelated edits. Capacity cannot be set before Story 5.15.
  - `[low]` `[reject]` (blind) «1.000» in a cost field reads as 1. Costs top out at 100 and the hint says «med komma»; a thousands dot is unlikely here.
  - `[low]` `[patch]` (blind) `aria-expanded` on opener and cancel was misleading. Removed: neither button is a toggle (the opener is replaced by the fields).
  - `[low]` `[patch]` (blind) Warning keys could collide. Keys are now by index.
  - `[low]` `[patch]` (blind) Missing tests. Added: refused server-owned keys, ranges for every editable setting, notes in `aria-describedby`, the opener absent on an archived Class. A component test of `checkDraft` ordering was rejected (no component-test setup in the module; the save re-judges).
  - `[low]` `[reject]` (blind) The check route documents FastAPI's 422. A malformed body gets the same 422 on every route of the api.
  - `[medium]` `[patch]` (intent) The api took more settings than the story owns (R6). Same root cause and fix as the `not_editable` row.
  - `[low]` `[reject]` (intent) The locked screen state is tested with a fulfilled GET. The real lock is pinned at the api; the screen reads only `locked`.
  - `[low]` `[patch]` (intent) Range errors were not covered for every setting (R7b). Added `production_delay`, `supply_line`, `starting_backlog`, negative `guided_weeks` and cost out of range.
  - `[low]` `[reject]` (intent) The `restordre` border is not asserted. It follows `aria-invalid` by the shared TextField class, asserted in `components.test.tsx`.
  - `[false]` `[reject]` (intent) The engine contract changed. Intended: the story asks for the range with every rejection, and the spec names the change.
  - `[medium]` `[patch]` (edge) Errors on `demand.change_week` are dropped. As blind row 1.
  - `[low]` `[patch]` (edge) Warnings without a row are dropped. As blind row 2.
  - `[low]` `[patch]` (edge) The Guided Weeks maximum could itself be invalid when the change falls after the Game. The engine now states `min(change, weeks) - 1`; engine test.
  - `[medium]` `[patch]` (edge) Server-owned keys are accepted. As blind row 3.
  - `[low]` `[patch]` (edge) A stale open draft was sent after the session locked or was archived on refetch. Settings are sent only while `can_manage` and not `locked`.
  - `[low]` `[reject]` (edge) A change in another tab is reverted by an open draft. As blind row 5.
  - `[low]` `[reject]` (edge) A cost typed as «1e1» is stored as `1E+1`. Unlikely input; it is within range and stays 10.
  - `[low]` `[patch]` (edge) Duplicate React keys. As blind row 13.
  - `[medium]` `[patch]` (edge, claim) A refused save with no reason on screen. As blind row 1.
  - `[low]` `[patch]` (verification-gap) Notes in `aria-describedby` were untested. `components.test.tsx` case and an e2e accessible-description check on «Restordrekost».
  - `[low]` `[patch]` (verification-gap) The opener on an archived Class was untested. Asserted absent in `class-session.spec.ts`.
  - `[low]` `[reject]` (verification-gap) Stale check answers are not tested. The guard is a single comparison; the module has no component-test setup, and the save re-judges on the server.
  - `[low]` `[reject]` (verification-gap, other) `test_sim.py` checks only «allowed». The engine test pins the values.

## Design Notes

- One check route rather than client rules: AD-1/AD-10 keep validation in the engine; the blur check is one cheap call.
- `fields` values are objects so the range travels with the code; the 5.2 date codes stay strings.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/sessions tests/engine -q` -- pass, each test under 1 s.
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass.
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- pass.
- `cd frontend && npx playwright test` against `timeout 900 docker compose up -d --build --wait proxy worker-batch` -- pass.

## Auto Run Result

Status: done

**Summary.** A Faglærer opens «Endre spillinnstillinger» on the Klasseøkt and changes the eleven Game settings in Tekstfelt fields. Leaving a field asks the api (`POST /api/class-sessions/{id}/settings-check`) to judge the whole draft with the engine; errors show under the field with a `restordre` border and the allowed range, warnings as «Advarsel: …» text. «Lagre Klasseøkt» stores the settings or answers 422 `invalid_settings` with `{code, minimum, maximum, decimal_places}` per setting. Once locked, changed settings and the check answer 409 `session_locked`. A non-Classic session hides the defaults line, names the calibrated Classic values from the api, and redraws «Kjeden ved start». The shared Norwegian number formatter is in `frontend/src/lib/number-format.ts`.

**Files changed**
- Backend: `engine/settings.py` (ranges on both Guided-Weeks errors); `sessions/{schemas,service,routes,repo}.py` and `README.md` (settings in the save, check route, `judge_settings`, `EDITABLE_SETTINGS`, `settings_warnings`, `calibrated_settings`); tests `sessions/test_settings.py` (new), `engine/test_validation.py`, `test_sim.py`.
- Frontend: `lib/number-format.ts` + test (new); `sessions/{settings.ts,settings.test.ts,settings-form.tsx}` (new); `sessions/{class-session-page,sessions,sessions.test,api}.ts(x)`; `components/text-field.tsx` (`notes`) + test; `copy/nb.ts`; regenerated `lib/api/{openapi.json,schema.ts}`; e2e `class-session-settings.spec.ts` (new), `class-session.spec.ts`.

**Review findings.** 33: 0 high, 6 medium, 23 low, 4 false. Patched: errors on settings without a field shown (3 medium rows, one root cause), server-owned keys refused (3 medium rows, one root cause), Guided-Weeks maximum, stale draft after lock, ARIA, keys, and added tests. Deferred: none. Rejected: the rest, each with its reason in the triage log. Two reviewers (edge case, verification gap) were cut off on the first launch and were run again; all four reports were read from their transcripts.

**Follow-up review recommended: false.** Two medium entries were patched, but both now have covering tests (api `not_editable` test; e2e error under «Etterspørsel»), so no unverified risk can be named.

**Verification**
- Backend: 2347 passed in 60 s; ruff check and format clean. New tests each under 1 s.
- Frontend: typecheck, Vitest (391), `check:copy`, `lint:colours`, `build` pass. Playwright 200/200 on the rebuilt stack.
- Screenshots at 390 and 1280 px (open block with error and warnings; saved non-Classic list) checked by eye.
- No migration.
- Implementation was done in this context (caller's instruction), not by a step-03 subagent.

**Decisions taken in place of the founder**
- «Per Role» starting inventory/backlog: the engine has one value for every Role, so one field each with «Gjelder hvert ledd.».
- Leaving a field calls a separate check route; nothing is stored until «Lagre Klasseøkt».
- The api takes only the settings with an engine range; seed, roles, Demand pattern and capacity are `not_editable` until their stories.
- After the lock an unchanged resend still saves (so deadlines move); changes answer 409.
- The settings block opens in place and closes after a save; Startrestordre and Største ordre join the read list.
- The calibration line names the Classic values from the api; the Play guard is worded «kontrollen av KI-spillerne».
- Thousands separator is a no-break space; costs show two decimals.
- Draft copy marked [ASSUMPTION] in `nb.ts`.

**Residual risks**
- Two co-owners editing at once: last save wins.
- An exotic number form («1e1») in a cost field is accepted as typed.
