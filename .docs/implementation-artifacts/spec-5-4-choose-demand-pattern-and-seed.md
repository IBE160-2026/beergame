---
title: 'Story 5.4: Choose a Demand pattern and its seed'
type: 'feature'
created: '2026-11-19'
status: 'done'
baseline_revision: '583be70a32d18148562924fc0ce87afbc673136d'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-5-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-5-3-change-game-settings-range-errors-warnings.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Klasseøkt refuses the Demand pattern and seed (`not_editable` since 5.3), so a Lecturer cannot choose the demand every Class game faces (FR-13), cannot see the series, and «Kjeden ved start» does not name the demand under «Kundene» as mockup 03 does (Issue #98, last item).

**Approach:** Make `demand` and `demand_seed` editable through the same save and check routes, judged by the engine alone; add a staff-only read of the series materialised by `engine.demand_series`. On the screen, the open settings block gets a Demand-pattern part (pattern select, the pattern's fields, the seed for seeded patterns), the read view gets «Vis etterspørselen uke for uke» with an HTML table, and the chain diagram names the demand under «Kundene».

## Boundaries & Constraints

**Always:**
- `EDITABLE_SETTINGS` adds `demand` and `demand_seed`. Pydantic errors inside `demand` map to `demand.<name>` (`demand.values`, `demand.start`, `demand.new_level`, `demand.change_week`, `demand.mean`, `demand.spread`): `greater_than_equal` → `out_of_range`, else `not_a_number`, with the `DEMAND_RANGES` bounds (`change_week`: 1 to the draft's Weeks). A missing/unknown `kind`, an unknown key or a non-object is `demand` `invalid`. A non-integer seed is `demand_seed` `not_a_number` with 0–`SEED_MAX`. Every other rule and range is the engine's `validate`/`warnings` (`fixed_series_length` with min = max = Weeks, `demand_change_week_outside_game` 1–Weeks, `demand_seed_required`, `guided_weeks_not_before_demand_change` under Veiledede uker).
- A draft that does not parse is still judged on its other settings, the unreadable top-level setting at its stored value (as 5.3).
- `GET /api/class-sessions/{id}/demand-series` (policy `class_sessions.read`, staff of the Class incl. Assistant): 200 `{demand: [int, …]}` from `engine.demand_series` of the stored settings; 403 `forbidden` otherwise (a Student, another Class, a bad id). No Student-facing endpoint returns the series, seed or Weeks.
- Locked: a changed pattern or seed answers 409 `session_locked` (5.3 path), and the screen shows no editor.
- Web: the open block shows, under the eleven fields, a «Etterspørsel» group: SelectField «Mønster» (Fast serie / Trinn / Tilfeldig / Trinn med tilfeldig variasjon) and the pattern's Tekstfelt fields; seeded patterns show «Frø» prefilled with the stored seed (drawn at creation) and a hint that the same seed gives the same series. Switching pattern carries over the levels that map (start ↔ mean) and leaves others empty; the api names what is missing. A fixed series is typed as whole numbers separated by spaces or commas. Field errors show under their field with the range; `demand`/`demand.kind` under the select. The body sends `demand` built from the kind's fields and `demand_seed` only for seeded kinds; unreadable text is sent as typed.
- Read view: the «Etterspørsel» row words every kind; a Lenke-styled button «Vis etterspørselen uke for uke» (`aria-expanded`) fetches the series and shows a `<table>` with caption, headers «Uke» and «Etterspørsel»; it is refetched after a save.
- Chain diagram: under «Kundene» two short lines in `lager` (step «4, så 8» / «fra Uke 5»; step+noise «4, så 8 ± 2» / «fra Uke 5»; random «8 ± 2» / «tilfeldig»; fixed «Fast serie» / «36 uker»), and the figcaption text names the demand too.
- All copy in `nb.ts` (new strings marked [ASSUMPTION]); no demand arithmetic in the web app.

**Never:** demand logic or validation in the web app, a chart library, capacity UI (5.15), AI/Debrief choices (5.5), comparing DB time with host time, touching the demo Class, editing `sprint-status.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Each pattern | fixed 36 values; step; random mean 8 spread 2 + seed; step+noise | 200; stored; series route returns the engine's series | – |
| Same seed twice | random, seed 42, series read twice | identical, equal to `engine.demand.series` | – |
| Keep seed | random without `demand_seed` | stored seed (from creation) used | – |
| Fixed wrong length | 10 values, 36 Weeks | nothing stored | 422 `demand.values` `fixed_series_length` 36–36 |
| Negative level | step start −1 | nothing stored | 422 `demand.start` `out_of_range` 0–100 |
| Week outside | change_week 40 / 0 | nothing stored | 422 `demand.change_week` 1–36 |
| Change in Guided Weeks | change_week 3, guided 4 | nothing stored | 422 `guided_weeks` 0–2 |
| Bad seed | `"x"` / −1 | nothing stored | 422 `demand_seed` `not_a_number` / `out_of_range` 0–999999999 |
| Bad kind | `{kind: "wave"}` | nothing stored | 422 `demand` `invalid` |
| Locked | pattern or seed changed | nothing stored | 409 `session_locked`; check 409 |
| Series access | Student / outsider | – | 403 |

</intent-contract>

## Code Map

- `backend/app/engine/settings.py` -- `DEMAND_RANGES`, `validate_demand`, `demand_series` (read-only; all rules are here).
- `backend/app/engine/demand.py` -- pattern models (`kind`: fixed/step/random/step+noise), `SEED_MAX`, `series`.
- `backend/app/modules/sessions/service.py:163-212` -- `EDITABLE_SETTINGS`, `_problem`, `judge_settings` (extend loc mapping; fallback rejudge must drop the top-level key of a nested error); add `demand_series(user, id)`.
- `backend/app/modules/sessions/{schemas,routes}.py`, `README.md` -- `DemandSeriesOut`, GET route, docstrings.
- `backend/tests/sessions/test_settings.py:229-258` -- `test_settings_this_screen_does_not_own_are_refused`: drop the `demand`/`demand_seed` cases. New `tests/sessions/test_demand.py` reusing `save`, `check`, `stored`, `problem` from test_settings and `new_session`, `PLAN`, `at`, `refusal`, `student_of` from test_dates.
- `frontend/src/modules/sessions/settings.ts` -- `EDITABLE`, `SettingsDraft`, `draftOf`, `settingsBody`, `problemText`; add demand draft/body and codes.
- `frontend/src/modules/sessions/settings-form.tsx` -- open block; `otherErrors` routes `demand.*`; add the demand fields and the series view.
- `frontend/src/modules/sessions/sessions.ts` -- `demandText`, `chainText`; `chain-diagram.tsx` customers group (END_W).
- `frontend/src/modules/sessions/api.ts`, `class-session-page.tsx` (draft state, `openSettings`), `src/copy/nb.ts` `sessions.values/chain/edit`.
- `frontend/src/components/select-field.tsx`, `text-field.tsx`; `LINK_BUTTON` from `modules/classes/roster-entry-forms`.
- `frontend/e2e/class-session-settings.spec.ts` (helpers `openSession`, `field`; uses `edit.errors.demandChangeOutside`), `e2e/support/classes.ts` (`freshLecturer`, `freshClass`, `expectAccessible`).
- API types: `cd backend && uv run python -m app.openapi ../frontend/src/lib/api/openapi.json`, then `npm run api:generate`.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/sessions/service.py`, `schemas.py`, `routes.py`, `README.md` -- editable demand and seed, nested error mapping, series read.
- `backend/tests/sessions/test_demand.py` (new), `test_settings.py` -- every matrix row through the routes; series twice equals the engine.
- `frontend/src/modules/sessions/settings.ts`, `settings.test.ts` -- demand draft ↔ body, fixed-series parsing, error copy.
- `frontend/src/modules/sessions/sessions.ts`, `sessions.test.ts`, `chain-diagram.tsx` -- demand words for all kinds, Kundene lines, chain text.
- `frontend/src/modules/sessions/settings-form.tsx`, `class-session-page.tsx`, `api.ts`, `src/copy/nb.ts`, regenerated `lib/api/{openapi.json,schema.ts}` -- demand fields, series table.
- `frontend/e2e/class-session-demand.spec.ts` (new) -- choose random with the shown seed, error on a fixed series of wrong length, save, series table, Kundene line, locked read-only (fulfilled GET), axe at 320/360/1440 and 400 % zoom.

**Acceptance Criteria:**
- Given an unlocked Klasseøkt, when the Lecturer opens the settings block, then «Mønster» offers the four patterns and each shows its fields.
- Given a random pattern, when the block renders, then «Frø» holds the seed the server drew at creation and can be changed to another whole number.
- Given a saved pattern, when the Lecturer clicks «Vis etterspørselen uke for uke», then a table of Week and demand from the api shows.
- Given a fixed series of the wrong length, when the Lecturer saves, then the reason with «36» shows under the series field and nothing is stored.
- Given mockup 03, then «Kundene» in «Kjeden ved start» has «4, så 8» and «fra Uke 5» under it for Classic, and the chosen pattern otherwise.
- Given a locked session, then no demand field shows and the api answers 409.

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 36 findings — high 0, medium 4, low 20, false 12, maybe-false 0
- findings:
  - `[medium]` `[patch]` (blind) A comma splits «4,5» in a fixed series into two Weeks. The series now splits on spaces, semicolons and a comma before a space or the end; «4,5» stays one value and the api refuses it (`settings.test.ts`); the hint names «komma og mellomrom».
  - `[false]` `[reject]` (blind) Errors on Demand fields the chosen pattern hides are dropped. The body holds only the chosen pattern's fields and no seed for a pattern that does not draw; the stored seed is always valid, so the api cannot name a hidden field.
  - `[false]` `[reject]` (blind) Demand warnings have nowhere to show while editing. The engine has no warning keyed on `demand` or `demand.*`; `supply_line_differs_from_demand` stands under «I hvert ledd ved start», which is shown.
  - `[low]` `[patch]` (blind) The pattern select reads a `demand.kind` key the api never sends. The dead lookup is deleted.
  - `[low]` `[reject]` (blind) With an unreadable pattern, the Guided-Weeks rule and warnings are judged on the stored pattern. The Lecturer already sees the pattern's own error; the next check after fixing it judges the draft. Fixing needs new branches for a rare, short-lived state.
  - `[low]` `[patch]` (blind) The change Week's upper bound came from an out-of-range draft Weeks (1–500). Draft Weeks outside the engine's range fall back to the stored Weeks; `test_demand.py` row.
  - `[low]` `[patch]` (blind) `DEMAND_FIELDS` copied the engine's field names by hand. It is now derived from the engine's pattern models.
  - `[low]` `[patch]` (blind) A missing pattern field reads as `not_a_number`; an empty series as `not_a_number` 0–100. The empty series is now `fixed_series_length` with the Weeks (`test_demand.py` row); a missing field cannot come from the screen, which sends every field as typed.
  - `[false]` `[reject]` (blind) The series read 500s on stored settings that do not parse, documents a 422, answers 403 for an unknown session. Stored settings are only written through `GameSettings`; the 422 is FastAPI's on every route; 403 for anything unreachable is FR-5.
  - `[false]` `[reject]` (blind) No preview of a draft series. The story asks for the series of a saved pattern.
  - `[low]` `[patch]` (blind) The seed hint said the seed was drawn at creation even after it was changed. Reworded: the server drew one; keep it or type another.
  - `[low]` `[reject]` (blind) Switching to «Fast serie» starts empty. Prefilling would need the series fetched into the form; the spec chose an empty field and the api names the length.
  - `[low]` `[reject]` (blind) A failed series fetch has no retry button. Hiding and showing the table asks again; a local api failing here is rare.
  - `[low]` `[reject]` (blind) The region label repeats the table caption. Both give the table and its scroll region a name axe requires; a repeat is negligible.
  - `[medium]` `[patch]` (blind) Long demand lines («100, så 100 ± 20») run past the chain SVG. The diagram widens to the longest line under «Kundene».
  - `[false]` `[reject]` (blind) `problemText` falls back to generic text without bounds. The engine always sends bounds for both codes.
  - `[low]` `[reject]` (blind) Test gaps (Weeks bound, unreadable pattern, hidden errors, back to step keeps seed, unparseable rows, real lock on screen). The Weeks bound is now tested; the rest follow the rejections above; a step keeping the seed is pinned by `test_each_pattern_is_stored...` (seed unchanged) and `settings.test.ts` (no seed in a step body).
  - `[low]` `[patch]` (edge) An empty fixed series gave `not_a_number` 0–100. As blind row 8.
  - `[low]` `[reject]` (edge) Unreadable pattern skews Guided-Weeks rule and warnings. As blind row 5.
  - `[low]` `[reject]` (edge) An unreadable seeded pattern hides `demand_seed_required`. The seed field is prefilled with the server's seed and the pattern error shows first.
  - `[low]` `[patch]` (edge) Change Week bound from an out-of-range Weeks. As blind row 6.
  - `[low]` `[patch]` (edge) Changing «Mønster» runs no check, so stale errors and warnings stay. The select now checks the draft on leaving it.
  - `[medium]` `[patch]` (edge) «4,5» becomes two values. As blind row 1.
  - `[medium]` `[patch]` (edge) Long demand lines clipped. As blind row 15.
  - `[false]` `[reject]` (edge) Hidden-field errors show no reason. As blind row 2.
  - `[low]` `[reject]` (edge, claim) `withKind` keeps fields typed for another pattern rather than clearing them. Those values were saved or typed by the Lecturer and are visible before sending; the spec's "leaves others empty" meant the web app invents no value, which holds.
  - `[low]` `[patch]` (intent) The seed was not shown when the block is closed or locked (story: "when the block renders, the seed is shown"; locked: both read-only). The settings list now has a «Frø» row for a pattern that draws (`sessions.test.ts`, e2e).
  - `[false]` `[reject]` (intent) Assistants read the series. «For the Lecturer only» is set against Students in the story; Assistants already read the settings and seed.
  - `[false]` `[reject]` (intent) The Guided-Weeks conflict stands under «Veiledede uker». The engine names that setting, with its range, in the same open block, which is inline.
  - `[low]` `[reject]` (intent) The locked screen is tested with a fulfilled GET. As in 5.3: the real lock is pinned at the api; the screen reads only `locked`.
  - `[false]` `[reject]` (intent) Nothing compares the chain to the mockup. Checked by eye on screenshots at 390 and 1280 px.
  - `[false]` `[reject]` (intent) The web app knows which fields each pattern has. It holds no rule or series arithmetic; the api judges and materialises.
  - `[false]` `[reject]` (intent) Only one Student-facing endpoint is checked. It is the only one in Epic 5 so far.
  - `[low]` `[patch]` (verification-gap) Nothing checked that the table refreshes after a save. The e2e reads the Classic series, saves a random one and reads the table again.
  - `[low]` `[patch]` (verification-gap) No test of a seed error under «Frø». Unit test of `demandProblemKey` and an e2e seed −1 with the range in the field's description.
  - `[false]` `[patch]` (verification-gap, other) Dead `demand.kind` fallback. Same fix as blind row 4 (code deleted; no behaviour changed).

## Design Notes

- A select rather than Valgknapper for four patterns: four segments do not fit 320 px on one line.
- The seed is sent only for seeded patterns, so switching to a step never clears the server's seed.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/sessions -q` -- pass, each test under 1 s.
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass.
- `cd frontend && npm run typecheck && npm test && npm run check:copy && npm run lint:colours && npm run build` -- pass.
- `cd frontend && npx playwright test` against `timeout 900 docker compose up -d --build --wait proxy worker-batch` -- pass.

## Auto Run Result

Status: done

**Summary.** The Demand pattern and its seed are editable on the Klasseøkt. «Endre spillinnstillinger» now opens an «Etterspørsel» part under the eleven settings: «Mønster» (Trinn, Fast serie, Tilfeldig, Trinn med tilfeldig variasjon) and the pattern's Tekstfelt fields; a pattern that draws shows «Frø», prefilled with the seed the server drew. The save and check routes take `demand` and `demand_seed`, judged by the engine alone; errors inside the pattern come back as `demand.<field>` with the allowed range. `GET /api/class-sessions/{id}/demand-series` gives the Class's staff the series `engine.demand_series` materialises, and «Vis etterspørselen uke for uke» shows it as a table of Uke and Etterspørsel. The settings list words every pattern and lists «Frø» for a pattern that draws. «Kjeden ved start» names the demand under «Kundene» in two lines as mockup 03 («4, så 8» / «fra Uke 5»), and its text alternative names it too (Issue #98, last item).

**Files changed**
- Backend: `sessions/service.py` (`demand`/`demand_seed` editable, `range_of`, `_parse_problem` for errors inside the pattern, `demand_series_of`), `schemas.py` (`DemandSeriesOut`), `routes.py` (series route), `README.md`; tests `sessions/test_demand.py` (new), `test_settings.py` (the demand cases left the `not_editable` list).
- Frontend: `sessions/settings.ts` (demand draft, body, `withKind`, error codes) + test; `sessions/sessions.ts` (`demandText` for every pattern, `customerLines`, seed row, chain text) + test; `settings-form.tsx` (demand fields, series table); `chain-diagram.tsx` (lines under «Kundene», width); `api.ts` (`useDemandSeries`); `copy/nb.ts`; regenerated `lib/api/{openapi.json,schema.ts}`; e2e `class-session-demand.spec.ts` (new), `class-session-settings.spec.ts` (change-Week error now under its field).

**Review findings.** 36: 0 high, 4 medium, 20 low, 12 false. Patched: the fixed series no longer splits «4,5» (medium), the chain widens for long demand lines (medium), change-Week bound from an out-of-range Weeks, empty series as `fixed_series_length`, `DEMAND_FIELDS` derived from the engine, select runs the check on leaving, seed hint wording, seed row in the read view, dead lookup removed, and tests for table refresh after save and the seed error. Deferred: none. Rejected: the rest, each with its reason in the triage log.

**Follow-up review recommended: false.** Two medium entries were patched; both are verified (unit test of the split; a screenshot of «100, så 100 ± 20» shows the whole line inside the diagram's own scroll region), so no unverified risk can be named.

**Verification**
- Backend: 2376 passed in 58 s; ruff check and format clean. New tests each under 1 s (slowest 0.42 s).
- Frontend: typecheck, Vitest (398), `check:copy`, `lint:colours`, `build` pass. Playwright 207/207 on the rebuilt stack; one unrelated test (`invitation.spec.ts` 360 px) passed only on retry in the final run and passed on its own after.
- Screenshots at 390 and 1280 px (Classic with the series table; open block with step+noise and an error; long demand line) checked by eye.
- No migration.
- Implementation and review fixes were done in this context (caller's instruction), not by a step-03 subagent.

**Decisions taken in place of the founder**
- The Demand pattern sits inside the existing settings editor, not as a block of its own; four patterns in a select (Valgknapper do not fit 320 px).
- Norwegian names: «Mønster», «Trinn», «Fast serie», «Tilfeldig», «Trinn med tilfeldig variasjon», «Startnivå», «Nytt nivå», «Endres fra uke», «Snitt», «Spredning», «Frø»; words for each pattern in the list and under «Kundene»; all marked [ASSUMPTION].
- The seed is sent only for a pattern that draws, so a step keeps the server's seed; the seed shows in the list for such a pattern.
- A fixed series is typed in one field as whole numbers separated by spaces or «komma og mellomrom».
- The series table is for the Class's staff (Assistants too), read from the saved pattern only; no draft preview.
- The Guided-Weeks conflict stays under «Veiledede uker», where the engine names it.
- The chain's text alternative adds «Kundenes etterspørsel: …».

**Residual risks**
- With an unreadable pattern in a draft, the Guided-Weeks rule and warnings are judged on the stored pattern until it parses.
- The locked screen is tested with a fulfilled GET; the real lock is pinned at the api.
