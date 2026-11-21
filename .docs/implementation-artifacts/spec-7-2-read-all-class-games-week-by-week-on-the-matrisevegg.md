---
title: "Story 7.2: Read all Class games week by week on the Matrisevegg"
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '87d8f17a0edbe81dc247be1f1ef858e061ff60e7'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-7-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Oversikt (Story 7.1) lists Class games as text rows only; a Lecturer cannot see the Netto lager pattern of the whole class Uke by Uke (FR-39), and the Landing still lacks its second figure (UX-DR70).

**Approach:** A staff-only `GET /api/games/{id}/weeks` serves the stored per-Week, per-Role values with an `ETag` on the Game's `version`; a hand-made SVG Matrisevegg in `components/charts` draws one row per Class game, grouped by status, readable cell by cell as an ARIA grid with one Tab stop; the Oversikt shows it above the 7.1 game list, and the Landing shows it with bundled demo data.

## Boundaries & Constraints

**Always:**
- **Endpoint** `GET /api/games/{game_id}/weeks` (`operation_id="getGameWeeks"`, route in `sessions/routes.py`, service `sessions/overview.game_weeks`): authorised by `class_sessions.overview` on the Game's Class session through `_class_for`; a Game with no Class session, a purpose without `policy.lecturer_overview`, an unknown or malformed id and any non-staff User all get the same 403 `forbidden`. Body `GameWeeksOut`: `game_id`, `version`, `weeks [{week, seats [{role, net_inventory:int, order:int|null, cost:decimal string}]}]`, opened Weeks only (no finished state), Week 1 first, seats in chain order. `net_inventory = inventory − backlog` and `cost` = the Seat's `cost` of that Week from the stored `WeekState`; `order` from `seat_weeks`, null while not placed. Strong `ETag` `"v<version>"`, `Cache-Control: private, no-cache`, `If-None-Match` (weak comparison, `*`) → 304 with no body, checked after authorisation and before the Week states are read.
- **Web app (AD-10):** `useGameWeeks(items)` uses `useQueries` keyed `["games","weeks",gameId,version]`, `staleTime: Infinity`, previous data kept as placeholder, so only Games whose `version` changed refetch; it reads `net_inventory` for the chosen Role and computes no quantity.
- **Matrisevegg** (`components/charts/matrix-wall.tsx` + pure `matrix-wall-layout.ts`): props `width`, `fontSize`, `groups [{key,title,rows [{id, label, detail?, rowName, game, values (number|null)[]}]}]`, `title`, `measure`, copy functions; Role is chosen by the caller (`role` prop on the Oversikt wrapper, default `factory`). Cells are square-cornered rects in `net-*` steps (`netStep`, moved here from `week-table.ts` and imported back), text 9 px or larger (`matrix-cell-min`); a cell prints its signed number via `formatNumber` when `textWidth + 2 ≤ cell width` (1 px each side), else «−» centred for below zero, else nothing; text `ink` on zero and steps 1–2, `paper` on 3–4.
- **Legend** always visible above the wall: nine swatches in step order with the bins «−35 og lavere · −34 til −20 · −19 til −10 · −9 til −1 · 0 · 1 til 9 · 10 til 19 · 20 til 34 · 35 og over» and the line «− i en celle: restordre (under null).»
- **A11y:** one scroll region (`role="region"`, name «Alle spill», `tabindex="0"`); SVG `role="grid"` with `<title>`, a header row of `columnheader`s («Uke n»), group header rows («Venter 4»), and per game a `row` with a `rowheader` (accessible text «Spill 2, venter på Noah (Grossist), 23 t, kjedekost 1 058 kr») and `gridcell`s named «Spill 2, Uke 14: Netto lager −13.». Roving tabindex: one cell in the Tab order; arrows move cell by cell (Up/Down to the nearest game row, Uke clamped to its last), Home/End to the row's first/last Uke; focus kept by Game id and Uke across re-renders and re-focused after a row moves; the focused cell draws `focus-ring-inset` (2 px `ink` frame, 1 px `paper` line inside). Game column and Uke header stay sticky by moving with the region's scroll (CSS variables), with the cells clipped under them. Never `aria-hidden`.
- **Oversikt:** groups and order exactly as `groupsOf` (Venter, Pågår, Ikke startet, «Ferdig, lavest kjedekost øverst»); row label «Spill n» + kjedekost visible; status/wait text in `detail` («Venter på Noah (Grossist), 23 t», «Pågår», «Ferdig»). Skjelett rows while week data loads; a failed week fetch shows the row with no cells. The 7.1 list stays below the wall under h2 «Spill og seter». Before the Start date: no wall.
- **Landing:** section «Alle spillene på én skjerm» (h2) with the Matrisevegg fed by bundled `demo-wall.json` (no api call), labelled «Demodata»; rows «Spill n» only, no names, no per-row Uke, no Uke total, no finished game.
- README of the chart module records: wall exposed as ARIA grid roles on the SVG (not an HTML table), and the sticky mechanism. All copy in `nb.ts`, new copy marked `[ASSUMPTION]`.

**Never:** no Visningsbryter/table view (7.3), no filters or class median rows (7.4), no live toggle (7.5), no row activation to Spillinnsikt or «Melding» link (7.7/7.9), no `flow-*` cells; no quantity or cost computed in the web app; no `ResponsiveContainer`; no page-level horizontal scroll.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Running game | Weeks 1–3 opened, Week 3 open | 3 weeks; Week 3 `order` null for Seats that have not ordered | — |
| Not started | Game not started | `weeks: []`; wall row with no cells | — |
| Repeat | `If-None-Match` = ETag | 304, empty body | — |
| Refused | Student, other Class's Lecturer, unattached Admin, test Game, unknown/malformed id | 403 `forbidden`, same body | — |
| Cell fit | −13 at 15 px wide cell, 9 px font | «−» only; 8 → «8»; 0 → «0»; 13 → blank | — |

</intent-contract>

## Code Map

- `backend/app/modules/sessions/routes.py:189` -- overview route with ETag/304 pattern; add `/games/{game_id}/weeks`, share the If-None-Match check.
- `backend/app/modules/sessions/overview.py` -- `class_overview` authz pattern (`repo.session_row` → `_class_for`); add `game_weeks`.
- `backend/app/modules/games/repo.py:415,550,95` -- `week_states`, `placed_orders`, `get_game`; `policy.purposes_with`.
- `backend/app/modules/games/service.py:556` -- add `class_game_weeks(session, game_id)` returning class_session_id, purpose, version, weeks.
- `backend/app/engine/state.py:13` -- `SeatState.inventory/backlog/cost`, `WeekState.finished`.
- `backend/tests/sessions/test_overview.py`, `test_game_end.py:41,57` -- `short_game`, `play_weeks`, `call`, `confirmed` fixtures to reuse.
- `frontend/src/components/charts/` -- `palette.ts` (`colour`, `CHART_FONT`), `chain-band-layout.ts:133` `textWidth`, `README.md`.
- `frontend/src/modules/games/week-table.ts:99` -- `netStep` (move to charts layout).
- `frontend/src/modules/games/overview.ts`, `overview-page.tsx`, `api.ts:24` -- grouping, row texts, hook pattern.
- `frontend/src/lib/box-size.ts` -- `useBoxSize` for width/fontSize.
- `frontend/src/modules/landing/landing-page.tsx` -- add the second figure.
- `frontend/e2e/overview.spec.ts`, `support/live-game.ts` (`liveClassGame`, `orderByApi`), `support/classes.ts` (`VIEWPORTS`, `expectAccessible`).

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/games/service.py`, `schemas.py` -- `GameWeeks` read -- stored values only (AD-1).
- `backend/app/modules/sessions/schemas.py`, `overview.py`, `routes.py` -- endpoint, authz, ETag/304 -- AD-25.
- `backend/tests/sessions/test_game_weeks.py` -- values equal stored state, open-Week null order, ETag/304 then change, refusals identical, not-started empty.
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerate.
- `frontend/src/components/charts/matrix-wall-layout.ts` (+ test), `matrix-wall.tsx`, `README.md` -- layout, fit/text rules, grid, keyboard, sticky.
- `frontend/src/modules/games/week-table.ts` -- import `netStep` from charts.
- `frontend/src/modules/games/api.ts`, `overview.ts` (+ test), `overview-wall.tsx`, `overview-page.tsx` -- hook and wall rows.
- `frontend/src/modules/landing/demo-wall.json`, `demo-wall.ts`, `landing-page.tsx` -- Landing figure.
- `frontend/src/copy/nb.ts` -- `nb.wall`, landing copy.
- `frontend/e2e/overview.spec.ts`, `landing.spec.ts` -- wall at 1440/320, keyboard reading, axe, no horizontal scroll.

**Acceptance Criteria:**
- Given a started Class game, when the Lecturer opens the Oversikt, then the wall shows its row under its group with cells for each opened Uke, the legend above, and the focused cell's name «Spill 1, Uke 1: Netto lager n.».
- Given keyboard focus in the wall, when the Lecturer presses arrows/Home/End, then focus moves cell by cell and stays one Tab stop.
- Given the Landing, when a visitor opens it, then «Alle spillene på én skjerm» shows the wall labelled «Demodata» with no api call for it.
- Given Vitest, when it runs, then the number-or-minus rule and the text-on-step rule are covered; given Playwright with axe at 1440 and 320 px, then no violations and no page-level horizontal scroll.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- Layers: blind hunter and edge-case hunter only (Sonnet), as the orchestrator asked for this lane; verification-gap and intent-alignment were skipped on that instruction. Both reports came back through files, because the handback channel dropped them. The diff left out the regenerated `openapi.json`/`schema.ts`.
- verdicts: 23 findings — high 0, medium 2, low 16, false 5, maybe-false 0
- findings:
  - `[low]` `[patch]` (blind) No game with a Uke yet: a phantom «Uke 1» header and a one-cell Skjelett — `wallSizes` keeps 0 columns, the Skjelett is 8 cells and the drawing has room for it; Vitest case added.
  - `[medium]` `[patch]` (blind) `keepPreviousData` does nothing in `useQueries` with the version in the key, so a row empties to the Skjelett on every version bump — `useGameWeeks` keeps the last weeks per game in a ref and uses them until the new version arrives.
  - `[low]` `[reject]` (blind) A failed week fetch is silent — the spec's chosen behaviour (row with no cells), rare on one stack, and stale or error display is Story 7.5's, as in 7.1.
  - `[low]` `[reject]` (blind) The client never uses the 304 and refetches every Week — the query key holds the version, so each version is fetched once; the payload is at most 36 Weeks × 4 Seats.
  - `[low]` `[patch]` (blind) One request per game, including games not started — the Oversikt now asks only for started games. One request per game is the story's own rule (AD-10, «per Game on demand»).
  - `[low]` `[patch]` (blind) The wall does not say on screen which Role it shows — a line «Netto lager, Fabrikk» above the wall (`nb.wall.shown`, [ASSUMPTION]); e2e asserts it.
  - `[low]` `[reject]` (blind) The Landing's 22 Uke columns tell a game's length — no demo game has finished and the rows differ in length, so no Uke total shows (UX-DR71); the Landing test still finds no «n uker».
  - `[low]` `[reject]` (blind) `labelProblems`/`textReadable` skip the wall — the 9 px cells are the design's one exception; label and figure widths come from the `textWidth` estimate that `chain-band.spec.ts` holds to the font; e2e checks no wall text under 9 px.
  - `[low]` `[reject]` (blind) A row name with several waits joins them with «;» and its wait ticks — readable as is; the name follows the 30 s tick of the 7.1 rows.
  - `[false]` `[reject]` (blind) Keyboard misses Ctrl+Home/PageUp, and the region plus the cell are two Tab stops — the story fixes the key set (arrows, Home, End) and asks for the region's `tabindex="0"` itself.
  - `[false]` `[reject]` (blind) The open Week is drawn as if complete — the engine settles a Week's Netto lager and cost when it opens; Orders cannot change them (`SeatState` docstring).
  - `[low]` `[patch]` (blind) The public Landing imports the Oversikt's module with the query client — `wallCopy`/`formatCell` moved to `modules/games/wall-copy.ts`, which holds no api code.
  - `[low]` `[reject]` (blind) Authorisation and the Week read are two transactions — the Oversikt's own pattern; a staff change in between is a microsecond race that shows only what was readable a moment earlier.
  - `[false]` `[reject]` (blind) `stepFill` casts to `ColourToken` — all nine `net-*` tokens exist in `tokens.json`, and the Vitest render and the e2e draw them.
  - `[low]` `[patch]` (blind) The kjedekost column has no unit — header now «Kjedekost, kr». A running game always has a cost, so a blank means not started: that part is false.
  - `[medium]` `[patch]` (edge) Version bump empties the row — duplicate of the `keepPreviousData` finding, patched there.
  - `[low]` `[patch]` (edge) Arrow keys with Alt/Ctrl/Meta/Shift are swallowed (Alt+Left) — the wall now ignores keys with a modifier.
  - `[low]` `[reject]` (edge) A failed fetch never retries — duplicate of the silent-failure finding, same reason.
  - `[false]` `[reject]` (edge) `netValues` shifts columns on a gap — the api sends every opened Week from Week 1 with every Seat; there is no gap.
  - `[low]` `[patch]` (edge) Zero columns gives a phantom header — duplicate, patched above.
  - `[low]` `[patch]` (edge) Requests for not-started games — duplicate, patched above; no concurrency cap is needed (the browser limits requests per host).
  - `[low]` `[patch]` (edge) Focus is lost if a browser fires blur when the row is moved — `onBlur` now ignores a blur from a cell no longer in the DOM, so focus is put back.
  - `[false]` `[reject]` (edge) The cache key holds data of a newer version — harmless by the reviewer's own account: one extra fetch when the newer version is listed.
- Matrix audit: the «Cell fit» row's «13 → blank» is read as a cell too narrow for «13» (at 15 px «13» fits by the spec's own rule and the story's); Vitest covers −13 at 15 and 16 px, 8, 0, and 13 at 11 px. Every other row is covered by `test_game_weeks.py`.

## Design Notes

- **Grid, not table role:** a table with one Tab stop and arrow keys is the ARIA grid pattern (a grid is a table to assistive technology); `role="table"` would leave screen readers in browse mode fighting the arrow keys.
- **Sticky inside one SVG:** CSS `position: sticky` cannot act on SVG children and splitting the SVG breaks the grid's row ownership, so the region's scroll offsets are written to CSS variables that translate the row headers and the Uke header, while a clip path keeps cells out from under them.
- **Fit rule:** `textWidth` (upper-bound estimate already held to the font by `chain-band.spec.ts`) plus 1 px each side must not exceed the cell width.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/sessions/test_game_weeks.py -q` -- passes
- `cd backend && uv run pytest -q -n auto` -- full suite passes once before commit
- `cd frontend && npm run typecheck && npx vitest run && npm run lint:colours && npm run build` -- pass
- `cd frontend && npx playwright test e2e/overview.spec.ts e2e/landing.spec.ts e2e/homes.spec.ts e2e/order-confirm.spec.ts` -- pass

## Auto Run Result

Status: done

**Summary.** The Matrisevegg on the Oversikt and the Landing.
- `GET /api/games/{id}/weeks` (staff of the Class, `class_sessions.overview`): per opened Week and Role the stored Netto lager, Order (null until placed) and Kost per uke (decimal string); `ETag` `"v<version>"`, 304 checked before any Week is read; one 403 for non-staff, test Games and unknown ids.
- `components/charts/matrix-wall.tsx` (+ `matrix-wall-layout.ts`): hand-made SVG, square cells in the `net-*` steps, number-or-minus rule, ink/paper text rule, legend with bins and the minus line, ARIA grid with one Tab stop, arrows/Home/End, `focus-ring-inset`, focus kept by game and Uke, sticky game column and Uke header inside the «Alle spill» region.
- Oversikt: the wall above the 7.1 list (now under «Spill og seter»), Fabrikk by default and named on screen; weeks fetched per started game and again only on a new `version`.
- Landing: «Alle spillene på én skjerm» with bundled Demodata, no api call.

**Files.**
- Backend: `games/service.py` (`class_game_head`, `class_game_weeks`), `sessions/schemas.py` (`GameWeeksOut`), `sessions/overview.py` (`readable_game`, `game_weeks`, ETag), `sessions/routes.py` (route, shared `_not_modified`), `tests/sessions/test_game_weeks.py`.
- Frontend: `components/charts/matrix-wall*.ts(x)` + test + README; `modules/games/api.ts` (`useGameWeeks`), `overview.ts` (+ test), `overview-wall.tsx`, `wall-copy.ts`, `overview-page.tsx`, `week-table.ts` (imports `netStep`); `modules/landing/demo-wall.*`, `wall-figure.tsx`, `landing-page.tsx`; `copy/nb.ts`; regenerated `openapi.json`/`schema.ts`; e2e `overview.spec.ts`, `landing.spec.ts`, `support/graph.ts`.

**Review.** 23 findings. Patch rows: 11 (2 medium rows forming one entry, 9 low rows forming 7 entries). None deferred. 12 rejected: 5 false and 7 low, with reasons in the triage log. Patched entries by verdict: high 0, medium 1, low 7. Follow-up review: not recommended (one medium entry, no high).

**Verification.**
- Backend: full suite 2797 passed in 78 s; Ruff clean. New tests over 1 s: each spends 2.7 s in the shared `short_game` fixture setup; one call is 2.0 s because it plays the 6-Week game to the end.
- Frontend: typecheck, Vitest (57 files, 736 tests), `lint:colours`, `check:copy` and the build pass.
- Playwright: `overview`, `landing`, `homes`, `order-confirm`, `week-table` and `class-session` (72 tests) pass after the patches, with axe at 1440 px, 320 px and 200 % text on the Oversikt and at four widths on the Landing. The builder checked screenshots of the Oversikt (1440 px, 320 px) and the Landing.

**Decisions taken instead of the founder.**
- The wall is an ARIA `grid` on the SVG (not `table`, not an HTML table under it); recorded in the chart README.
- Sticky by CSS variables and clip paths inside one SVG.
- Fit rule: `textWidth` + 1 px each side.
- The 7.1 game list stays under the wall as «Spill og seter»; its group headings became h3.
- Row label: «Spill n» and kjedekost in whole kroner; status or wait after the cells; the Uke header prints every number when it fits, else 1 and every fifth.
- A line «Netto lager, Fabrikk» names the Role and measure above the wall.
- The Landing figure names no Role, shows only waiting and running demo games, and the Graf-over-tabell text checks skip the wall (9 px cells).
- The endpoint's route lives in `sessions`, like the Oversikt's.
- The builder implemented the story in its own context, as the orchestrator instructed.

**Residual risks.**
- Up and Down skip the group header rows. Screen reader behaviour of SVG grid roles was checked only through Chromium's accessibility tree (Playwright roles and names), not with a real screen reader.
- A failed week fetch leaves the row empty until the game changes (Story 7.5 owns error and stale display).
