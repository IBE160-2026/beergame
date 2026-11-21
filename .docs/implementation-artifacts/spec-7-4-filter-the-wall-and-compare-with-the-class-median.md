---
title: "Story 7.4: Filter the wall and compare with the class median"
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '6167abb0daadba1aee2de413077d37bb5c8cb5b8'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-7-context.md'
warnings: ['multiple-goals', 'oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Oversikt's Matrisevegg (7.2) and its table (7.3) always show every game's Fabrikk Netto lager; a Lecturer cannot pick a Role, a cell value or a status group, and has no class median to compare a game against (UX-DR40, UX-DR41, UX-DR43). Story 7.3's visual check also left three layout defects: the «Visning» toggle stretches into a big block above the wall, the table is narrower than the wall, and «Venter på» wraps to 3–4 lines.

**Approach:** Veggfiltre (Rolle, Celler, Status) above the wall filter and redraw the rows the web app already holds; a new endpoint `GET /api/class-sessions/{id}/overview/aggregates?role=&cells=&status=` serves per Uke the median, middle half and mean chain cost from a pure `analysis.wall_aggregates`; the wall draws them as a class median graph over the Uke columns and two bottom rows, the table as two footer rows. The toggle becomes a compact inline control at the right of the wall's heading line, the table spans the region, «Venter på» stays on one line.

## Boundaries & Constraints

**Always:**
- **Veggfiltre** (`modules/games/wall-filters.tsx`): three groups (`role="group"`, names «Rolle», «Celler», «Status»), each a visible label then text buttons with `aria-pressed`, one pressed per group; active weight 600 and underlined, counts after the word in `ink-secondary`; `caption` text, no pills or fills, 44 px tap height, rows wrap at narrow widths. Rolle: Detaljist, Grossist, Distributør, Fabrikk (default Fabrikk). Celler: Netto lager (default), Ordre, Kost per uke. Status: «Alle n», then «Venter n», «Pågår n», «Ikke startet n», «Ferdig n», «Med KI-spiller n» — each shown when its count > 0 or it is the pressed one. Counts are the number of received rows per status (and with an AI-held Seat); they follow live data. Filters live in component state only.
- A filter applies at once to wall and table: Status keeps only the matching games (groups and their header counts follow), Rolle and Celler change the values; no week request is made for a filter (weeks already fetched per game stay keyed by version). Empty result: «Ingen spill i dette utvalget.» [ASSUMPTION] instead of the wall.
- **Cells:** Netto lager = `net_inventory`; Ordre = `order` (values stop before the first Week without an Order); Kost per uke = `cost` (decimal string read as a number for display only). Ordre and Kost per uke use the `flow-*` scale: under 5 no fill (`paper`), 5–9, 10–19, 20–29, 30+ = `flow-1…4`, text `ink` on none/1–2, `paper` on 3–4; the legend switches to «Under 5 · 5 til 9 · 10 til 19 · 20 til 29 · 30 og over» [ASSUMPTION copy] without the minus line. The cell name, the SVG title and the line above the wall name the measure («Spill 2, Uke 14: Ordre 8.», «Ordre, Fabrikk»).
- **Endpoint** `GET /api/class-sessions/{id}/overview/aggregates?role=retailer|wholesaler|distributor|factory&cells=net|order|cost&status=all|waiting|running|not_started|finished|with_ai`, policy `class_sessions.overview`, same 403 for non-staff and unknown sessions, 422 for a bad parameter. Games = the overview's listed Games (AD-13) matching `status` (`with_ai`: any occupant not a Student and not free). Response: `role`, `cells`, `status`, `games` (number matched), `weeks: [{week, games, median, lower_quartile, upper_quartile, chain_cost_mean}]` with decimal strings (null when no value). `ETag` from the parameters and the matched Games' `(game_id, version)`, `If-None-Match` → 304 before any Week is read. Fixed query count whatever the number of Games. The overview response is unchanged (no aggregates in it).
- **`analysis.wall_aggregates`** (`backend/app/analysis/wall.py`, pure, stdlib + engine): input per Game its stored `WeekState`s and placed Orders by (week, role); per Uke over the Games that have a value there: median, quartiles by linear interpolation between order statistics (inclusive method; one Game → all three equal), count; chain cost mean = mean over Games that reached the Uke of the sum of the four Seats' `cost`. Finished states are skipped. Decimal arithmetic, means quantized to 0.01 half-up. Golden tests: odd, even, single, zero Games, games reaching different Uker, Ordre missing in an open Week.
- **Median graph and rows** inside the wall's SVG and its «Alle spill» region, on the same Uke columns: above the Uke header a graph (median line `ink` 1.5 px, middle-half band `hairline`, zero line `axis`, y ticks in the sticky game column), `aria-hidden`; a key line above the region names line and band («Median», «Midterste halvdel av spillene» [ASSUMPTION]). After the last group two rows «Median, Fabrikk» and «Kjedekost/uke, snitt» (whole numbers, printed when they fit the cell with 1 px to spare, else blank), each a grid `row` with `rowheader` and named `gridcell`s («Uke 14: median −13, midterste halvdel −20 til −5, 12 spill.» / «Uke 14: kjedekost per uke, snitt 48 kr.») that are not keyboard stops. The Uke header still sticks under scrolling. Rendered only from the endpoint's response (AD-10). While a new combination loads the previous one stays; on failure an inline `role="status"` line «Medianen kunne ikke hentes.» [ASSUMPTION] and the wall stays. The table gets the same two rows in a `tfoot` (median to one decimal, mean in whole kroner).
- **Layout fixes:** the view toggle is inline (legend «Visning» left of its two segments, segments sized to their text, 44 px high) and sits at the right of the heading line «Netto lager, Fabrikk» + key, wrapping under it at narrow widths (total height ≤ 60 px at 1280 px); the table is at least the region's width; «Venter på» does not wrap.
- Copy in `nb.ts` (`nb.wall.filters`, `nb.wall.median`, flow bins, measure names), new copy `[ASSUMPTION]`. Spine Deferred item «Wall filter aggregates» gets the decision; chart README documents graph, rows and flow scale.

**Never:** no aggregate in the overview response; no median, mean, quartile or cost computed in the web app; no pills or filled filter buttons; no persistence of filters; no Pause status (Epic 8), no live toggle (7.5), no right rail (7.6); no change to the Landing's wall output; no page-level horizontal scroll; no table text under 13 px.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Odd games | 3 Games at Uke 1 net 4, −2, 10 | median 4, q1 1, q3 7, games 3 | — |
| Even games | 2 Games 4, 10 | median 7, q1 5.5, q3 8.5 | — |
| Single | 1 Game 5 | median = q1 = q3 = 5 | — |
| None | no Game matches | `games: 0`, `weeks: []`; wall shows «Ingen spill i dette utvalget.» | — |
| Uneven reach | A at Uke 3, B at Uke 5 | Uke 4–5 counted over B only (`games` 1) | — |
| Open-week Ordre | open Week, Order not placed | that Game left out of the Uke's Ordre median, still in the chain cost mean | — |
| Bad parameter | `cells=foo` | 422 | — |
| Same version | repeat with ETag | 304, no Week read | — |
| Filter change | Status «Ferdig» | only Ferdig group; aggregates refetched for the new combination; old rows shown until it arrives | failure: inline line, wall kept |

</intent-contract>

## Code Map

- `backend/app/modules/sessions/routes.py:191-245` -- overview and weeks routes, `_not_modified`, `_id`; add the aggregates route beside them.
- `backend/app/modules/sessions/overview.py` -- `class_overview` (staff check via `_class_for(user, class_id, "class_sessions.overview")`), `etag_of`, `game_weeks`; add `wall_aggregates(user, session_id, role, cells, status)` + its ETag.
- `backend/app/modules/sessions/schemas.py:804-846` -- `ClassOverviewOut`, `GameWeeksOut`; add `WallAggregatesOut`, `WallWeekOut`, enums for cells/status.
- `backend/app/modules/games/service.py:560-668` -- `class_overview` (summaries), `class_game_weeks` (WeekState parse, `net_inventory = inventory - backlog`); add a fixed-query read of states and orders for many games.
- `backend/app/modules/games/repo.py:415,550,888` -- `week_states`, `placed_orders`, `class_summaries`; add multi-game variants.
- `backend/app/analysis/__init__.py`, `play_guard.py` -- pure-module conventions; new `wall.py`.
- `backend/app/engine/state.py:13-53` -- `SeatState`/`WeekState`.
- `backend/tests/sessions/test_game_weeks.py`, `test_overview.py:148` -- fixtures (`short_game`, `play_weeks`, `klass`), refusal pattern, fixed-query-count pattern; `backend/tests/analysis/` for golden tests.
- `backend/app/openapi.py` -- export `openapi.json`, then `npm run api:generate`.
- `frontend/src/modules/games/overview-wall.tsx` -- owns view, position, sort; add filters, aggregates query, compact toggle row.
- `frontend/src/modules/games/overview.ts` -- `netValues`, `wallGroups`, `tableRows`, `STATUS_WORD`; generalise to a cell measure, add status filtering, counts, summary mapping.
- `frontend/src/modules/games/api.ts` -- `classOverviewKey`, `useGameWeeks`; add `useWallAggregates` under the overview key prefix (so `topics.ts` `session` invalidation covers it), `keepPreviousData`, `cache: "no-cache"`.
- `frontend/src/modules/games/wall-copy.ts` -- `wallCopy`; take the measure and scale.
- `frontend/src/components/charts/matrix-wall.tsx`, `matrix-wall-layout.ts` -- steps/legend (generalise to `net`/`flow` scale), sizes, sticky `stick()` (offset by graph height), rows; add graph + summary rows.
- `frontend/src/components/charts/matrix-table.tsx:70,207,250` -- `WEEK`, table class, wrap column; add `tfoot` rows, full width, no wrap.
- `frontend/src/components/segmented-choice.tsx`, `view-toggle.tsx` -- add an inline/compact layout.
- `frontend/src/copy/nb.ts:2090` -- `nb.wall`.
- `frontend/e2e/overview.spec.ts` -- wall/table e2e (`liveClassGame`, `VIEWPORTS`, `expectAccessible`, `textReadable`).
- `.docs/planning-artifacts/architecture/architecture-beergame-2026-11-12/ARCHITECTURE-SPINE.md:569` -- Deferred «Wall filter aggregates».

## Tasks & Acceptance

**Execution:**
- `backend/app/analysis/wall.py` (+ `tests/analysis/test_wall_aggregates.py`) -- pure aggregates with golden tests -- AD-1, NFR-9.
- `backend/app/modules/games/repo.py`, `service.py` -- multi-game states/orders read in fixed queries.
- `backend/app/modules/sessions/schemas.py`, `overview.py`, `routes.py` (+ `tests/sessions/test_overview_aggregates.py`) -- endpoint, ETag/304, refusals, status filter, fixed query count, values equal to `wall_aggregates` over stored states.
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerate.
- `frontend/src/components/charts/matrix-wall-layout.ts`, `matrix-wall.tsx`, `matrix-median.tsx` (new) (+ `matrix-wall.test.tsx`) -- flow scale, graph, summary rows from a fixture.
- `frontend/src/components/charts/matrix-table.tsx` (+ test) -- `tfoot`, width, no-wrap.
- `frontend/src/components/segmented-choice.tsx`, `view-toggle.tsx` -- inline layout.
- `frontend/src/modules/games/overview.ts` (+ `overview.test.ts`), `wall-copy.ts`, `api.ts`, `wall-filters.tsx` (new), `overview-wall.tsx`, `fixtures/wall-aggregates.json` (new).
- `frontend/src/copy/nb.ts`; `frontend/src/components/charts/README.md`; spine Deferred note.
- `frontend/e2e/overview.spec.ts` -- filters with `aria-pressed`, flow legend, median rows and graph, aggregates request per combination, toggle height/position, table width, axe at 1440/320/200 %.

**Acceptance Criteria:**
- Given the Oversikt, when it is shown, then Rolle, Celler and Status filter groups with counts stand above the wall as `aria-pressed` text buttons, and pressing one changes wall and table at once without any `/weeks` request.
- Given Celler Ordre or Kost per uke, when the wall redraws, then cells carry `flow-*` steps and the legend shows the flow bins.
- Given a filter combination, when the wall renders, then the median graph sits over the Uke columns inside the «Alle spill» region and the rows «Median, Fabrikk» and «Kjedekost/uke, snitt» print the endpoint's values in the Uke columns; a Vitest renders them from a fixture response.
- Given the endpoint, when called for a combination, then it answers the values of `analysis.wall_aggregates` over the stored states of the matching Games with an `ETag`, in a fixed number of queries.
- Given 1280 px, then the «Visning» toggle is ≤ 60 px tall beside the wall's heading, the table is as wide as its region, and «Venter på» is one line; axe passes at 1440 px, 320 px and 200 % text with no page-level horizontal scroll.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- Layers: blind hunter and edge-case hunter only (Sonnet), as the orchestrator asked for this lane; verification-gap and intent-alignment were skipped on that instruction. Both reports came back through files (`review-blind-7-4.md`, `review-edge-7-4.md` in the session scratchpad), because the handback channel dropped them.
- verdicts: 20 findings — high 0, medium 0, low 15, false 5, maybe-false 0
- findings:
  - `[false]` `[reject]` (blind) «Med KI-spiller» means different things on client and server — `_game_out` makes `holder = "ai"` exactly when `occupant_kind` is neither None nor Student, the same test as `overview._matches`; both read the same summary row.
  - `[low]` `[patch]` (blind) A filter change shows the previous combination's median under the new heading — patched: the last answer stays only while it measures the same cells (`overview-wall.tsx`); the rows name their own Role, so a Role or Status change keeps them as the spec says, a Celler change hides them until the new answer arrives.
  - `[low]` `[reject]` (blind) No retry on a failed aggregates read — a `session:` event or any filter change asks again; a retry action is new UI the spec does not ask for, for a failure of the local api only.
  - `[low]` `[patch]` (blind) A one-Uke run draws a zero-area band; the dot re-parses a point string — patched: a lone Uke gets a band half a cell wide, and the dot takes its numbers from the run (`matrix-median.tsx`); Vitest «draws a lone Uke's middle half».
  - `[low]` `[reject]` (blind) Uker without a median have no named cell — only the open Week's Ordre can lack one; `aria-colindex` keeps the column positions, and the game rows end the same way after their last Uke.
  - `[low]` `[reject]` (blind) The open Uke is a partial sample in the median — this is the AC's rule («over the Games that have reached that Uke»); Netto lager and cost are settled when the Week opens, and the Ordre median's base is read in each cell's name.
  - `[low]` `[reject]` (blind) Flow bins for kroner and whole numbers in the wall vs one decimal in the table — the bins are DESIGN.md's for the Celler filter; a 9 px cell has room for whole numbers only, and the table and the cell names carry the decimal; the formatter never prints «−0».
  - `[false]` `[reject]` (blind) Ordre cells stop at the first gap on the client but not on the server — a Week advances only when every Seat has ordered, so only the open Week can lack an Order; the two agree.
  - `[low]` `[patch]` (blind) Full Week states read per request; ETag ignores the response shape — the volume is 60 × 36 states at most (the fixed query count is tested); the shape is now part of the ETag (`WALL_SHAPE`), so a deploy that changes it never answers 304.
  - `[low]` `[reject]` (blind) Dropping `wrap` and adding `min-w-full` changes the shared table — the intent asks for exactly this (the table at the wall's width, «Venter på» on one line); the table scrolls in its own region (no page scroll, e2e at 320 px).
  - `[low]` `[reject]` (blind) «Kjedekost/uke, snitt» widens the sticky game column — it is about as wide as «Spill 12» plus «Kjedekost, kr», which the column already held; the 320 px screenshot shows the Uker in view.
  - `[low]` `[reject]` (blind) Filter interactions are tested only at 1280 px; no `WallFilters` unit test — the layout, axe and median rows run at every width; the choice list (hidden zero counts, «Alle») is checked by the e2e's exact button texts and `statusCounts`/`filterGroups` Vitest cases.
  - `[false]` `[reject]` (blind) Generated client and docs missing from the review diff; no session log — `openapi.json`/`schema.ts` were regenerated and are in the change set (left out of the diff for size only); session logs and issues are the orchestrator's, not this build's (runbook).
  - `[low]` `[patch]` (edge) Previous combination's rows under new cells — duplicate of the stale-median finding, same patch.
  - `[low]` `[patch]` (edge) One-Uke band has zero area — duplicate, same patch.
  - `[low]` `[patch]` (edge) With no Uke reached the two summary rows render with labels and no cells — patched: `wallSummary` and `tableFooter` give no graph and no rows when the api has no Uke; Vitest «has no graph and no rows».
  - `[false]` `[reject]` (edge) Before the Start date the endpoint serves costs the overview hides — Class games open when the session locks, so before it no Game has a Week state and `weeks` is empty.
  - `[low]` `[reject]` (edge) Removed `wrap` widens the wait cell — duplicate of the intent-driven change above.
  - `[false]` `[reject]` (edge) `cellValues` truncates Netto lager or cost at a gap — every stored Week has all four Seats and an integer Netto lager; cost is the api's decimal string, never NaN.
  - `[low]` `[reject]` (edge) `retry: false` leaves the median missing after one failure — duplicate of the retry finding.
- Matrix audit: Odd, Even, Single, None (api), Uneven reach, Open-week Ordre — `tests/analysis/test_wall_aggregates.py` golden cases and `test_overview_aggregates.py` (order Week 3 with `games` 0, `status=finished` → `games` 0, `weeks` []); Bad parameter (422), Same version (304) — `test_overview_aggregates.py`; Filter change and failure line — `overview.spec.ts` «Veggfiltre…» (aggregates request per combination, no `/weeks` request, routed 500 shows «Medianen kunne ikke hentes.» with the table kept). The «Ingen spill i dette utvalget.» line is covered only through `filterGroups` returning no group (Vitest); the e2e cannot reach it, since a Status choice with no game is not offered. All listed tests ran and passed.

## Design Notes

- **Decision (spine Deferred «Wall filter aggregates»):** one endpoint per filter combination, ETag over the matched Games' versions; the overview stays lean and the Class report reuses `wall_aggregates`.
- **Graph inside the SVG:** the spec puts graph, wall and table in one scroll region with shared Uke columns; drawing the graph in the wall's SVG is the only way the columns line up while the region scrolls sideways. The sticky header offset becomes `max(0, scrollTop − graphHeight)`.
- **Quartiles:** inclusive linear interpolation (`q = x[⌊p(n−1)⌋] + frac·(x[⌈⌉] − x[⌊⌋])`) — the same for any n ≥ 1, no special cases beyond zero Games.

## Verification

**Commands:**
- `cd backend && uv run pytest -q tests/analysis/test_wall_aggregates.py tests/sessions/test_overview_aggregates.py` -- pass
- `cd frontend && npx vitest run src/components/charts src/modules/games` -- pass
- Before commit: `cd backend && uv run pytest -q -n auto`; `cd frontend && npm run typecheck && npx vitest run && npm run lint:colours && npm run check:copy && npm run build`; `npx playwright test e2e/overview.spec.ts e2e/homes.spec.ts e2e/order-confirm.spec.ts e2e/landing.spec.ts` -- pass

## Auto Run Result

Status: done

**Summary.** Veggfiltre and the class median on the Oversikt, plus the three layout fixes from 7.3.
- Rolle / Celler / Status text-button filters with `aria-pressed` (weight 600, underlined, counts in `ink-secondary`, no pills) above the wall; they filter the rows already received and change wall and table at once; no `/weeks` request for a filter.
- Ordre and Kost per uke draw in the `flow-*` steps, with the legend switched to the flow bins and no minus line.
- `GET /api/class-sessions/{id}/overview/aggregates?role=&cells=&status=` (staff only, same 403, 422 on a bad parameter, ETag/304 before any Week is read, fixed query count) serves per Uke the median, middle half and mean chain cost from the pure `analysis.wall_aggregates`. The overview response is unchanged.
- The class median graph (median line, middle-half band, zero line) sits inside the wall's SVG over the Uke columns in the «Alle spill» region; «Median, Fabrikk» and «Kjedekost/uke, snitt» rows under the wall (named cells), and the same rows in the table's `tfoot`.
- Layout: «Visning» is an inline control at the right of the heading line (50 px high at 1280 px); the table is at least the region's width; «Venter på» never wraps.
- Spine Deferred «Wall filter aggregates» records the decision.

**Files.**
- `backend/app/analysis/wall.py` (new: `wall_aggregates`, `quartiles`), `analysis/__init__.py`.
- `backend/app/modules/games/repo.py` (`week_states_of`, `placed_orders_of`), `service.py` (`class_played`).
- `backend/app/modules/sessions/schemas.py` (`WallAggregatesOut`, `WallWeekOut`, `WallCells`, `WallStatus`), `overview.py` (`wall_games`, `wall_aggregates_out`, ETag), `routes.py` (the route).
- `backend/tests/analysis/test_wall_aggregates.py`, `backend/tests/sessions/test_overview_aggregates.py` (new).
- `frontend/src/components/charts/matrix-median.tsx` (new), `matrix-wall.tsx` (scale, graph, summary rows), `matrix-wall-layout.ts` (flow steps, `spans`), `matrix-table.tsx` (`footer`, full width, no wrap), `README.md`, `matrix-wall.test.tsx`.
- `frontend/src/components/segmented-choice.tsx`, `view-toggle.tsx` (`inline`).
- `frontend/src/modules/games/wall-filters.tsx` (new), `overview-wall.tsx`, `overview.ts` (`cellValues`, `filterGroups`, `statusCounts`, `wallSummary`, `tableFooter`), `api.ts` (`useWallAggregates`), `wall-copy.ts`, `overview-page.tsx`, `fixtures/wall-aggregates.json`, `wall-summary.test.tsx`, `overview.test.ts`.
- `frontend/src/copy/nb.ts` (`nb.wall.filters`, `nb.wall.median`, flow legend), `frontend/src/lib/api/openapi.json` + `schema.ts` (regenerated), `frontend/e2e/overview.spec.ts`.
- `.docs/planning-artifacts/architecture/.../ARCHITECTURE-SPINE.md` (Deferred decision), `.docs/implementation-artifacts/screenshots/7.4/` (6 screenshots).

**Review.** 20 findings (blind 13, edge-case 7; Sonnet): 0 high, 0 medium, 15 low, 5 false. Patched: 4 entries, all low (6 rows): the stale median after a Celler change, the one-Uke band, the empty summary rows and the ETag shape. Nothing deferred. Rejected: 5 false and 9 low, with reasons in the triage log. Follow-up review: not recommended (no high, no medium patched).

**Verification.**
- Backend: the full suite passed (2809 tests) in 74 s and 94 s on two runs. A third run had one failure I could not name: a rerun passed and the failure did not come back. In my own test file, `test_overview_aggregates.py` depended on which Role the Student held; that is fixed and passed 3 out of 3 runs. Slowest five, all pre-existing: `test_migrations` 13.3 s and the `test_sim`/`test_sim_golden` batches at 9–12.6 s. New tests: the 4 api tests take about 2.7 s setup each (`short_game`/`confirmed`), and the 8 golden tests are fast.
- Frontend: typecheck, Vitest (59 files, 762 tests, none over 1 s), `lint:colours`, `check:copy` and the build pass.
- Playwright: `overview`, `landing`, `homes` and `order-confirm` ran as one run of 55 tests after the patches: 54 passed and 1 failed (`homes` «student opens the product», 360 px). The failing test passed when `homes` was rerun alone (23 passed), and this story does not touch that screen. Before the patches, `class-session-choices` and `admin-invite` were run (17 passed) because they use the shared Valgknapper. The new e2e runs axe once at 1280 px, 320 px, 200 % text and 1440 px.
- I checked screenshots at 1280 px and 320 px of the wall, Ordre and the table (`screenshots/7.4/`).

**Decisions taken instead of the founder.**
- Status filter choices: Alle, Venter, Pågår, Ikke startet, Ferdig and «Med KI-spiller» (from the mockup). A choice with count 0 is hidden unless pressed. Single choice per group.
- One endpoint per filter combination. The ETag covers the filter, a shape tag and the matched Games' versions.
- Quartiles use the inclusive linear interpolation method. Each Uke counts the Games that have a value. For Ordre, the open Week's games without an Order are left out of the median but stay in the chain-cost mean.
- The graph is drawn inside the wall's SVG so the columns line up. It has a median line in `ink`, a `hairline` band and a zero line in `axis`, and is `aria-hidden` because the numbers are in the rows. A key line above names the line and the band. The graph shows with the wall only, and the table gets `tfoot` rows.
- Summary rows print whole numbers in the wall, only where they fit. The table prints the median to one decimal and the mean in whole kroner. The cell names read the median, the middle half and the number of games.
- Kost per uke cells print up to two decimals and use the flow bins.
- Copy marked `[ASSUMPTION]`: flow legend «Under 5 · 5 til 9 · 10 til 19 · 20 til 29 · 30 og over», «Median», «Midterste halvdel av spillene», «Ingen spill i dette utvalget.», «Medianen kunne ikke hentes.» and the cell readings.
- «Venter på» does not wrap at all; the table scrolls in its own region.
- The toggle keeps the 50 px control height for tap targets.
- Filters are not remembered across page loads.
- While another combination loads, the previous median rows stay only for the same Celler.
- The builder implemented the story in its own context, as the orchestrator instructed.

**Residual risks.**
- The empty-selection line («Ingen spill i dette utvalget.») has no browser test.
- Filter interactions run in the browser at 1280 px only. Other widths get the layout, axe and median-row checks.
- With one game the graph's band is flat (the median equals both quartiles), so the screenshots do not show a band of real width.
- One unnamed backend failure (1 of 3 full runs) and one `homes` e2e failure (1 of 2 runs) appeared once each and passed on rerun.
