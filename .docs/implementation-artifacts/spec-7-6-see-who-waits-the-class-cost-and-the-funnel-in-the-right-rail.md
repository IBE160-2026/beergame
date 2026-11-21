---
title: "Story 7.6: See who waits, the class's cost and the funnel in the right rail"
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: 'd03f4f32446d8dd9c7f51319cb4760554ed59b9e'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-7-context.md'
warnings: ['oversized']
deferred:
  - summary: >-
      A loading wall row draws its note at the start of the cells, over its Skjelett bar.
    evidence: |-
      `MatrixWall` places a row's note at `labelWidth + values.length * cellWidth`; a loading row has no values but draws an 8-cell Skjelett bar, so the note overlaps it until the weeks arrive. Pre-existing since Story 7.2; the new `notes` layout keeps the same placement.
    location: >-
      frontend/src/components/charts/matrix-wall.tsx
    severity: low
---

<intent-contract>

## Intent

**Problem:** The Oversikt has the wall, filters and live updates (7.1–7.5) but no right rail: a Lecturer cannot see the other waiting games at a glance, how much the finished games cost (distribution and per Role), or how far the class has come through the steps (FR-39, UX-DR40/51/69/72). Also, at 390 px the wall row note «Venter på …» runs past the wall region's right edge (`screenshots/7.4/oversikt-standard-390.png`).

**Approach:** The overview answer gains three api-computed blocks — `ai` (AI-held Seats, games with one), `cost` (median, quartiles, per-Role lager/restordre means over finished Class games, from a pure `analysis` function) and `funnel` (from a new `progress.service.funnel`) — and the page renders them in a right rail beside the wall at ≥ 1024 px, stacked under the wall below it. The wall draws a short note when the full one would make the drawing wider than its box.

## Boundaries & Constraints

**Always:**
- **Api (`ClassOverviewOut`):** `ai: {seats, games}` counted over the listed Class games' current occupants (kind not Student and not free). `cost: ClassCostOut | null` — null before the Start date or when no listed game has finished; else `games` (finished count), `median`, `lower_quartile`, `upper_quartile` of finished chain costs (`analysis.wall.quartiles`), `holding_cost`/`backorder_cost` (chain means per finished game) and `roles` Detaljist→Fabrikk each with `holding_cost`, `backorder_cost`, `total_cost` means. Means quantized to øre; money as decimal strings. `funnel: [{stage, count}]` in the order registered, class_game, debrief, quiz_passed, replay, test_submitted, assessment_ready, always present.
- **Cost split source:** each finished game's per-Role split = holding rate × Σ inventory and backorder rate × Σ backlog over its opened (not finished) Week states, rates from the Game's snapshot settings — what `views.chain_result` gives. Read in a fixed number of queries for all finished games (no per-Game query, NFR-3). No migration.
- **Pure `analysis.class_cost`** (new `backend/app/analysis/class_cost.py`): takes per finished game its chain cost and per-Role (holding, backorder); returns the quartiles and means; None for no game. Golden tests: one, two (even), three (odd) games, zero.
- **`progress.service.funnel(class_session_id, student_ids)`**: registered = number of ids; each later stage = distinct given Students with that step recorded in the session. One grouped query; cached per Class session in process, keyed by the id set and a stamp (`count(*)`, `max(id)` of the session's `progress_steps`), so a step recorded by another process is seen on the next read; `record_step` drops the session's entry when it stores a row. Reads steps only, no AI score or text. `progress` still imports no feature module. The overview passes `classes.registered_students(class_id)`.
- **Test data:** `reports.scope` does not exist yet (Story 13.1 adds it); the cost block and AI counts use the Games the overview lists (`purposes_with("lecturer_overview")`, which excludes lecturer test and simulation Games), the funnel the `class_game` step that only those Games record.
- **Rail (`overview-rail.tsx`)** in order: «Venter ellers» (waiting games longest wait first, row «Spill 30» + «Ida, Detaljist, 18 t» per waited Seat; a line when none waits; then the AI line), «Klassens kostnad» (not rendered before the Start date; a line when none finished; else intro, Kostnadsfordeling, axis caption, text summary «Median 1 954. Midterste halvdel 1 500–2 600.», «Vis som tabell»/«Vis som graf» toggling a table Spill / Kjedekost sorted lowest first; then «Snitt per ferdig spill, per Rolle» bars split lager/restordre with the total printed and a key «lager 949» «restordre 1 063 kr»), «Trakt» (`<ol>` of stage name + count, bars `aria-hidden`). Before the Start date the rail shows beside the allocation without the cost block. It reads the shown answer, so «Oppdater automatisk» off freezes it.
- **Kostnadsfordeling** `frontend/src/components/charts/cost-distribution.tsx`: hand-made SVG, width/fontSize passed in, `<title>`, `aria-hidden` (summary text and table carry it), one tick per game, box lower→upper quartile, median line labelled «Median 1 954», axis from 0 with labelled ticks; labels never overlap or leave the SVG at 320 px and 200 % text.
- **Layout:** ≥ 1024 px a two-column grid, wall (and list below it) left, rail right (fixed ~22 rem); below, DOM order wall → rail → list, one column; no page-level horizontal scroll at 320 px.
- **Wall note fix:** `MatrixWall` rows take an optional `shortDetail`; when label column + cells at their minimum + the widest full note exceed the passed width, every row draws its short note («Venter, 18 t» for a waiting game: the longest wait; others their status word). The row header's accessible name keeps the full text.
- Copy in `nb.overview.rail` with `[ASSUMPTION]` on wording not in the mockup or epic; money via `formatNumber` only; AD-10: the web app only formats, sorts and scales what it got.

**Never:** no «Send Melding»/«Melding» links or Varselbånd (7.9, 7.11); no Pause rows (Epic 8); no «Fjoråret» mark (Epic 14); no «Kjedekost per uke, snitt per spill» chart; no Message-to-unmet link; no new migration; no change to SSE/topics.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| None finished | games running | `cost` null; rail line «Ingen spill er ferdige ennå.» | — |
| Before start | `before_start` | `cost` null, cost block absent; rail with Venter ellers + Trakt beside allocation | — |
| One finished | 1 game, 800 kr | median = both quartiles = 800; one tick; summary prints | — |
| Nothing waits | no waiting game | «Ingen spill venter nå.» | — |
| Step recorded | game finishes | `class_game` count +1 on the next overview read (≤ 5 s live) | — |
| Test game | lecturer test Game finished | not in cost, AI counts or funnel | — |
| 390 px, short game | note wider than room | short note drawn inside the region's width | — |

</intent-contract>

## Code Map

- `backend/app/modules/sessions/overview.py:46` `class_overview` -- add `ai`, `cost`, `funnel`; names already resolved here.
- `backend/app/modules/sessions/schemas.py:795-822` -- `OverviewCountsOut`, `ClassOverviewOut`; add `OverviewAiOut`, `ClassCostOut`, `RoleCostOut`, `FunnelStageOut`.
- `backend/app/modules/games/service.py:562` `class_overview`; add `finished_cost_splits(session, game_ids)` returning per game per Role (holding, backorder); `repo.py` new grouped SQL over `game_weeks` (`jsonb_array_elements(state->'seats')`, `NOT finished`) and `games.settings` rates. Compare `views.py:161` `chain_result` (truth for the split).
- `backend/app/analysis/wall.py:58` `quartiles` -- reuse; new `analysis/class_cost.py`.
- `backend/app/modules/progress/service.py`, `README.md` -- `funnel`, cache, `record_step` invalidation; `models.py` `Step`.
- `backend/app/modules/classes/service.py:616` `registered_students`.
- `backend/tests/sessions/test_overview.py`, `tests/progress/test_progress.py`, new `tests/analysis/test_class_cost.py`; `tests/games/helpers.py`, `tests/test_imports.py` (progress imports nothing).
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerate (`backend/app/openapi.py`, `npm run api:generate`).
- `frontend/src/modules/games/overview-page.tsx:205` `OverviewBody`, `:344` `Allocation` -- grid layout and rail.
- `frontend/src/modules/games/overview.ts` -- pure rail helpers; `waitLines`, `groupsOf`, `costText` reuse; `wallGroups:246` gets `shortDetail`.
- `frontend/src/components/charts/matrix-wall.tsx:22-31,133-141,501-512`, `matrix-wall-layout.ts:108` -- short note choice.
- `frontend/src/modules/games/cost-panel-view.tsx` -- pattern for bars as top borders, table toggle with `LINK_BUTTON`.
- `frontend/src/components/charts/cost-area.tsx`, `scales.ts` `totalAxisTop` -- axis/tick patterns; `palette.ts` `colour()`; `README.md` chart table.
- `frontend/src/copy/nb.ts:2039` `nb.overview`.
- `frontend/e2e/overview.spec.ts`, `e2e/support/live-game.ts` `liveClassGame` (`gameSettings: { weeks: 2 }`, `aiMode: "rule_based"`), `orderByApi`.

## Tasks & Acceptance

**Execution:**
- `backend/app/analysis/class_cost.py` (+ `tests/analysis/test_class_cost.py`) -- pure function, golden cases.
- `backend/app/modules/progress/service.py`, `README.md` (+ `tests/progress/test_progress.py`) -- `funnel` with cache and invalidation; stamp sees a row added outside.
- `backend/app/modules/games/repo.py`, `service.py` -- cost split read; test that it equals `chain_result` per Role for a finished game.
- `backend/app/modules/sessions/schemas.py`, `overview.py` (+ `tests/sessions/test_overview.py`) -- new fields; tests: AI counts, cost null/filled and excluding a lecturer test Game, funnel counts and a recorded step changing it and the ETag; query count stays fixed.
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerate.
- `frontend/src/components/charts/cost-distribution.tsx` (+ `charts.test.tsx`), `README.md` -- chart.
- `frontend/src/components/charts/matrix-wall.tsx`, `matrix-wall-layout.ts` (+ `matrix-wall.test.tsx`) -- short note.
- `frontend/src/modules/games/overview.ts` (+ `overview.test.ts`) -- `waitingElsewhere`, `aiLine`, `costSummary`, `costTable`, `roleBars`, `funnelRows`, `shortDetail` in `wallGroups`.
- `frontend/src/modules/games/overview-rail.tsx` (new), `overview-page.tsx` -- rail and grid.
- `frontend/src/copy/nb.ts` -- `nb.overview.rail`.
- `frontend/e2e/overview.spec.ts` -- rail test (2 Students, 2-week rule-based game): Venter ellers lists the game, AI line, Trakt counts, none-finished line; both finish → Kostnadsfordeling, summary, table toggle, role bars, «Klassespill ferdig 2» live; 390 px note inside the region; axe at 1440, 320 and 200 % text.

**Acceptance Criteria:**
- Given the Oversikt at ≥ 1024 px, then «Venter ellers», «Klassens kostnad» and «Trakt» sit in a rail right of the wall; at 320 px they stack under the wall with no page-level horizontal scroll and their numbers printed.
- Given finished Class games, then the rail shows the Kostnadsfordeling with one tick per game and «Median n», the summary line, «Vis som tabell» with Spill/Kjedekost lowest first, and per Role lager/restordre bars with amounts and the key — all values from the api.
- Given waiting games, then «Venter ellers» lists them longest wait first with game, Student, Role and duration, and the AI line gives the real counts.
- Given the Trakt, then the seven stages show in order with counts as list items and `aria-hidden` bars; a newly recorded step shows on the next live read.
- Given 390 px and a short game, then no wall note extends past the wall region's visible width.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- Layers: blind hunter and edge-case hunter only (Sonnet), as the orchestrator asked for this lane; verification-gap and intent-alignment were skipped on that instruction. Both handbacks dropped; the findings were read from `review-blind-7-6.md` and `review-edge-7-6.md` in the session scratchpad.
- verdicts: 27 findings — high 0, medium 2, low 19, false 6, maybe-false 0
- findings:
  - `[medium]` `[patch]` (blind) `distributionAxis` loops forever when no step leaves room for the labels — patched: the search is bounded and falls back to 0 and the lowest 1–2–2,5–5 top; Vitest covers widths 20 and 0.
  - `[low]` `[patch]` (blind) The axis test uses a constant label width and no too-narrow width — patched with the same narrow-width cases.
  - `[low]` `[patch]` (blind) «In øre» docstrings on kroner values — patched to «in kroner, rounded to the øre» (`class_cost.py`, `RoleCostOut`).
  - `[low]` `[reject]` (blind) Chain means rounded apart from the Role means may differ by an øre — the rail prints whole kroner; a 1-øre gap is never visible.
  - `[false]` `[reject]` (blind) A finished game with no split rows dilutes the means; the two sources can drift — a finished Game always has stored opened Weeks, and `test_a_finished_game_fills_the_cost_block…` asserts the split equals `views.chain_result` per Role.
  - `[low]` `[reject]` (blind) Raw `_COST_PARTS` SQL can drift and expands every finished game's Weeks on every read — equality with `chain_result` is tested; the read is one grouped query (NFR-3 test with 50 finished games); storing the split needs a migration the parallel lane would collide with (Design Notes).
  - `[low]` `[reject]` (blind) The funnel cache never evicts and saves little — one small entry per Class session read by the process; the stamp keeps it correct; the epic names the cache.
  - `[false]` `[reject]` (blind) `waitingElsewhere` prints NaN for an unparsable `since` — the api types `since` as an aware datetime, always ISO; `waitLines` reads it the same way.
  - `[low]` `[reject]` (blind) «Venter ellers» has no cap — the mockup lists every waiting game; a class has few waiting at once.
  - `[low]` `[patch]` (blind) No test that a test Game stays out of the cost block (the non-null `chain_cost` part is false: a finished summary always has one) — patched: the finished test adds a finished `lecturer_test` summary row and asserts cost and AI counts are unchanged.
  - `[low]` `[reject]` (blind) Funnel stages are listed in three places — the running test asserts the api's list; a stage missing from `nb.ts` fails the typecheck.
  - `[low]` `[reject]` (blind) `registered_students` reads outside the overview's session — the function takes no session; a registration emits its own event and the next read sees it.
  - `[low]` `[patch]` (blind) No test that a step alone moves the ETag — patched: the finished test records a `debrief` step and asserts 200 with the new count.
  - `[low]` `[patch]` (blind) The chart test checks only where labels start — patched: every label's right edge (by `textWidth`) stays inside the SVG at 288 and 352 px.
  - `[low]` `[reject]` (blind) The «Vis som tabell» toggle has no `aria-pressed`; its state resets on remount — the same link-button pattern as «Kostnad så langt» (6.16); axe passes at every width.
  - `[low]` `[reject]` (blind) Copy assumptions not recorded — each is marked `[ASSUMPTION]` in `nb.ts` and listed under the decisions below.
  - `[low]` `[defer]` (blind) A loading row's note overlaps its Skjelett bar — pre-existing since 7.2; deferred.
  - `[low]` `[reject]` (blind) README/doc gaps for `cost_parts` and the new fields — `modules/games` has no README; the fields are documented in the schema docstrings and OpenAPI; the chart README has its row.
  - `[medium]` `[patch]` (edge) `distributionAxis` unbounded loop — duplicate of the first finding, same patch.
  - `[false]` `[reject]` (edge) NaN for an unparsable `since` — duplicate; the api's type rules it out.
  - `[low]` `[patch]` (edge) A waiting game with no named wait shows a blank row — patched: it reads «Venter» (Vitest).
  - `[low]` `[reject]` (edge) Funnel cache grows without bound — duplicate of the cache finding.
  - `[false]` `[reject]` (edge) Empty split rows understate the means — duplicate; a finished Game always has Weeks.
  - `[false]` `[reject]` (edge) `cost.games` may differ from the table's rows — both count the listed finished games with a chain cost, from the same answer.
  - `[false]` `[reject]` (edge) The stamp query breaks «one grouped query» — the spec names the stamp beside the grouped count.
  - `[low]` `[reject]` (edge) The rail is 20 rem from 1024 px, 22 rem from 1280 px — the spec says about 22 rem; the narrower rail leaves the wall room on a 1024 px screen.
  - `[low]` `[patch]` (edge) Test-game exclusion and a funnel-only ETag change untested — duplicate of the two test patches above.
- Matrix audit: None finished — `test_overview.py` running test (`cost` null) and the e2e rail test («Ingen spill er ferdige ennå.»); Before start — before-start api test and the e2e before-start test (Trakt, no cost region); One finished — `test_a_finished_game_fills…` and the e2e (one tick, summary, table); Nothing waits — e2e after the finish and Vitest `waitingElsewhere`; Step recorded — the api test's `debrief` step and the e2e «Klassespill ferdig2» within 5 s; Test game — the api test's `lecturer_test` row; 390 px — the e2e note-inside-region check and Vitest `wallSizes` notes. All ran and passed.

## Design Notes

- No migration: a second lane builds other epics in parallel and also adds revisions; reading the split for finished games in one grouped query keeps the overview at a fixed query count without a revision race. A finished game's split never changes, so it could move into `game_summaries` later.
- The funnel cache's stamp makes it correct across processes (a game finished by a worker records `class_game` there); the in-process drop on `record_step` is the epic's named invalidation.

## Verification

**Commands:**
- `cd backend && uv run pytest -q tests/analysis/test_class_cost.py tests/progress tests/sessions/test_overview.py` -- pass
- `cd frontend && npx vitest run src/modules/games src/components` -- pass
- Before commit: full backend suite; `npm run typecheck && npx vitest run && npm run lint:colours && npm run check:copy && npm run build`; Playwright `overview`, `live-updates`, `homes`, play-screen specs -- pass

## Auto Run Result

Status: done

**Summary.** The Oversikt has its right rail.
- The overview answer carries `ai` (AI-held Seats and games with one), `cost` (median, quartiles, per-Role and chain lager/restordre means over finished Class games, from the new pure `analysis.class_cost`; null before the Start date or while none finished) and `funnel` (seven stages, from the new `progress.service.funnel`, cached per Class session with a stamp and dropped by `record_step`).
- The per-Role split is read for all finished games in one grouped SQL query over their stored Weeks and snapshot rates (`games.service.cost_parts`), equal to `views.chain_result`; no migration.
- The rail: «Venter ellers» (longest wait first, the AI line), «Klassens kostnad» (Kostnadsfordeling SVG with ticks, box and «Median n», axis caption, the summary line, «Vis som tabell»/«Vis som graf», per-Role lager/restordre bars with amounts and the key), «Trakt» (`<ol>` with counts, `aria-hidden` bars). Beside the wall from 1024 px (20 rem, 22 rem from 1280 px), under the wall below; before the Start date beside the allocation without the cost block. It reads the shown answer, so «Oppdater automatisk» off freezes it.
- Wall fix: rows carry a short note («Venter, 18 t»); when a full note would end past the box at the narrowest cells, the wall draws the short ones, each after its own row's cells, so at 390 px nothing runs past the region.

**Files.**
- `backend/app/analysis/class_cost.py` (new) + `tests/analysis/test_class_cost.py` (new); `analysis/__init__.py`.
- `backend/app/modules/progress/service.py`, `README.md` (`funnel`, cache), `tests/progress/test_progress.py`.
- `backend/app/modules/games/repo.py` (`cost_parts_of`), `service.py` (`cost_parts`).
- `backend/app/modules/sessions/schemas.py` (`OverviewAiOut`, `ClassCostOut`, `RoleCostOut`, `FunnelStageOut`), `overview.py`, `tests/sessions/test_overview.py`.
- `frontend/src/lib/api/openapi.json`, `schema.ts` (regenerated).
- `frontend/src/components/charts/cost-distribution.tsx` (new), `matrix-wall.tsx`, `matrix-wall-layout.ts` (`notes`, `shortDetail`), `charts.test.tsx`, `matrix-wall.test.tsx`, `README.md`.
- `frontend/src/modules/games/overview-rail.tsx` (new), `overview-page.tsx` (`RailLayout`), `overview.ts` (rail helpers, `shortDetail`), `overview.test.ts`, `api.test.ts`.
- `frontend/src/copy/nb.ts` (`nb.overview.rail`, `waitingShort`); `frontend/e2e/overview.spec.ts` (rail test; before-start rail check).

**Review.** 27 findings (blind 18, edge case 9; Sonnet): 0 high, 2 medium, 19 low, 6 false. Patched: one medium entry (the axis loop, found by both) and 6 low (narrow-axis test, øre docstrings, test-game exclusion test, step-only ETag test, label right-edge test, a waiting game without a named wait). Deferred: 1 low (pre-existing loading-row note overlap). Rejected: 6 false and 12 low, with reasons in the triage log. Follow-up review: not recommended (one medium entry patched and unit-tested, no high).

**Verification.**
- Backend: full suite 2815 passed in 71.0 s after the patches (76.3 s before). New tests: the finished-game overview test 2.1 s (plays a two-Week game; over 1 s), the others under 1 s.
- Frontend: typecheck, Vitest (61 files, 785 tests, none over 1 s), `lint:colours`, `check:copy`, build pass.
- Playwright after the last change: `overview`, `live-updates`, `homes`, `order-confirm`, `week-advance` — 48 passed. Before the patches, `week-advance` «four Students … within 2 s» failed once on its 2 s timing limit while two review agents ran, and passed on the rerun (flaky under load; this story does not touch it). The new rail test runs axe at 1440 px (finished state), 320 px and 200 % text; the first test runs axe at all three widths with the rail in its waiting state.

**Decisions taken instead of the founder.**
- No migration: the per-Role split is read from stored Weeks per overview read rather than stored in `game_summaries`, to avoid a revision race with the parallel lane.
- `reports.scope` does not exist yet (Story 13.1); cost, AI counts and funnel use the overview's listed purposes (no lecturer test or simulation Games) and the registered Students of the Class.
- Funnel cache validated by a stamp (row count and newest id of the session's steps) so a step recorded by a worker is seen; `record_step` drops the entry in-process.
- Rail copy `[ASSUMPTION]`: «Klassen samlet» (rail landmark name), «Ingen spill venter nå.», «Ingen spill er ferdige ennå.», «1 KI-spiller i 1 spill, merket.», «Ingen KI-spillere.», «Kroner. Boksen er midterste halvdel.», «Vis som graf», the table caption, the Role bars' read text, the wall's short note «Venter, 18 t».
- A waiting game lists every waited-for Seat («Ida, Detaljist, 18 t; Fabrikk, 2 t»); a waiting game with no named wait reads «Venter».
- Rail width 20 rem from 1024 px, 22 rem from 1280 px; before the Start date the rail shows «Venter ellers» and the Trakt beside the allocation.
- The Kostnadsfordeling axis: 0 to the lowest 1–2–2,5–5 multiple, labels at least 1.6 label widths apart; ticks come from the finished games' `chain_cost` in the answer.
- Not built: «Send Melding» links (7.9/7.11), Pause rows (Epic 8), «Fjoråret» (Epic 14), «Kjedekost per uke, snitt per spill» (not in the story's criteria).
- The builder implemented in its own context, as the orchestrator instructed.

**Residual risks.**
- The cost split query expands every finished game's stored Weeks on each overview read; untimed at 100 played games (the query-count test uses summary rows only).
- The funnel cache is process-local and unbounded (one small entry per Class session read).
- Verification-gap and intent-alignment reviews were skipped by instruction.
