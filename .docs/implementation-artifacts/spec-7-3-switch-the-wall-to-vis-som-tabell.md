---
title: "Story 7.3: Switch the wall to «Vis som tabell»"
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: 'e0287dcb3222de336abe6136aa24d2edb3625ad4'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-7-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Matrisevegg (Story 7.2) prints a number only where it fits in a 9 px cell; an Assistant lecturer cannot read exact values, sort the games or read them as a plain table (UX-DR42, NFR-6).

**Approach:** A Visningsbryter «Vegg» / «Vis som tabell» above the Oversikt's wall swaps the SVG wall for an HTML `<table>` fed by the same rows and week data, in the same «Alle spill» scroll region, with sortable headers (game number, status, wait, kjedekost) and focus held by Game id across both views and data updates. Frontend only; no api change.

## Boundaries & Constraints

**Always:**
- **Toggle:** the existing `ViewToggle` (Valgknapper: native radios in a `fieldset`, legend «Visning», segments «Vegg» and «Vis som tabell», active `ink` with `paper` text), always visible above the wall when the wall is shown (not before the Start date, not with no games). «Vegg» is the default; the choice lives in component state only. The «Netto lager, Fabrikk» line stays above both views; the legend and its minus line show with the wall only.
- **Table** (`components/charts/matrix-table.tsx`, generic, reusable by «Vis i plenum»): HTML `<table>` with a `<caption>` (sr-only, the wall's title), a `thead` row of `th scope="col"` (game column, the caller's extra columns, then «Uke n» per Uke, printing the number with sr-only «Uke »), and per game a `tr` whose first cell is `th scope="row"` («Spill 2»), then the extra columns, then one `td` per Uke with the signed number from the one formatter (true minus) — every cell that has a value prints it; Uker a game has not reached are empty `td`s; a loading row shows a Skjelett bar (`aria-hidden`) across its Uke cells. Text `table-cell` 13 px, `table-cell-laptop` 15 px from 1024 px, tabular figures; never shrinks; plain cells (hairline rules, no fills). Inside its own `role="region"` named «Alle spill», `tabindex="0"`, `overflow-auto`, same `maxHeight` as the wall; game column (`sticky left-0`) and header row (`sticky top-0`) stay put, the corner both, all on `paper`.
- **Extra columns on the Oversikt:** «Status» (Venter / Pågår / Ikke startet / Ferdig), «Venter på» («Noah (Grossist), 23 t», several joined by «; », a gone Student named by Role, blank when not waiting), «Kjedekost, kr» (whole kroner, blank before start). All from the api's rows (AD-10).
- **Sorting:** each sortable header holds a `button` with the header text; activating sorts by that column, again reverses it. The sorted header carries `aria-sort` (`ascending`/`descending`), others none; the active one shows weight 600 and a «↑»/«↓» glyph (`aria-hidden`). Sort keys are numbers given by the caller per row; rows without a key (not waiting, no cost) stay last in both directions; ties keep the default order. First direction: Spill ascending, Status ascending (= the wall's group order, with each group's own order), Venter på descending (longest wait first), Kjedekost ascending. Default sort: Status ascending, so the table opens in the wall's order. Cost sorting exists only because the Oversikt passes the column; the generic table sorts nothing it is not given.
- **Focus by Game id:** one row header in the Tab order (roving `tabindex`), ArrowUp/ArrowDown move between game rows, focus ring `focus-ring-inset` (2 px `ink` inset, 1 px `paper` inside). The current game is shared with the wall: `MatrixWall` takes an optional controlled `position`/`onPosition` (game id and Uke); switching views keeps the same game as the one Tab stop in the other view (wall: the same Uke, clamped). On data updates focus stays on the same game's row header (re-focused after a DOM move); while focus is inside the table, rows keep their order (values update in place, new games appended) and re-sort when focus leaves or a header is activated (EXPERIENCE.md → Oppdater automatisk).
- Screen-reader path: the wall stays the 7.2 grid, never `aria-hidden`; the table is read by its `th` scopes (each `td` gets its game and Uke from the headers).
- Copy in `nb.ts` under `nb.wall.table`, new copy marked `[ASSUMPTION]` where EXPERIENCE.md does not give it («Vegg» and «Vis som tabell» are its own). README records the table view.

**Never:** no api or schema change; no filters or median rows (7.4), no live toggle (7.5), no row activation or «Melding» (7.7/7.9); no quantity, median or cost computed in the web app (sorting received numbers only); no page-level horizontal scroll; no text below 13 px in the table; no persistence of the chosen view.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default | Oversikt with games | Wall shown, «Vegg» checked, toggle above | — |
| Table | «Vis som tabell» | Table with every game in wall order, `aria-sort="ascending"` on Status | — |
| Sort cost | Activate «Kjedekost, kr» twice | Lowest first, then highest first; not-started games last both times | — |
| Sort wait | Activate «Venter på» | Longest wait first; non-waiting games after, in default order | — |
| Short game | Game with 2 Uker, other with 4 | Its Uke 3–4 cells empty | — |
| Loading | Weeks not yet received | Skjelett bar in its Uke cells | Failed fetch: row with empty cells |
| Focus kept | Focus on Spill 1 row header, game changes group | Row stays in place, focus stays on Spill 1 | — |
| Switch | Wall cell Spill 2 Uke 3 focused, switch to table, Tab in | Spill 2's row header is the table's Tab stop; back to wall → Spill 2 Uke 3 | — |

</intent-contract>

## Code Map

- `frontend/src/components/view-toggle.tsx` -- `ViewToggle` (two-option Valgknapper); usage example `modules/sessions/allocation-panel.tsx:408`.
- `frontend/src/components/charts/matrix-wall.tsx:86-114` -- `MatrixWall`, internal `active` position state and `target`; add optional controlled `position`/`onPosition`; `WallRow`, `MatrixWallCopy`; region markup (line 194) to mirror; `Legend` (line 440) shown with the wall only (it is inside `MatrixWall`, so nothing to do).
- `frontend/src/components/charts/matrix-wall-layout.ts` -- `WallPosition`; new pure `matrix-table-sort.ts` beside it for the sort.
- `frontend/src/modules/games/overview-wall.tsx` -- owns the view state, the shared position, renders toggle + wall or table.
- `frontend/src/modules/games/overview.ts:93-142` -- `wallGroups`, `STATUS_WORD`, `waitLines`, `costText`, `netValues`; add `tableRows` + `tableColumns` built from the same groups.
- `frontend/src/modules/games/wall-copy.ts` -- `formatCell` (true minus).
- `frontend/src/modules/games/week-table-view.tsx:56,236-275` -- sticky `th scope` table pattern and sr-only «Uke ».
- `frontend/src/theme/theme.css:73-78` -- `text-table-cell` 13 px / `text-table-cell-laptop` 15 px.
- `frontend/src/copy/nb.ts:2090` -- `nb.wall`; `nb.overview.waitingFor` (2064) for the wait wording.
- `frontend/e2e/overview.spec.ts:47` -- wall e2e with `liveClassGame`, `orderByApi`, `VIEWPORTS`, `expectAccessible`; add the table test here.
- `frontend/src/components/charts/README.md` -- add «Vis som tabell» section.

## Tasks & Acceptance

**Execution:**
- `frontend/src/copy/nb.ts` -- `nb.wall.table` (view legend, segment labels, column headers, wait text) -- copy only in nb.ts.
- `frontend/src/components/charts/matrix-table-sort.ts` (+ `matrix-table-sort.test.ts`) -- pure `sortRows(rows, sort)` and `nextSort(sort, column)` with nulls last and stable ties -- unit-testable sort rules.
- `frontend/src/components/charts/matrix-table.tsx` (+ cases in `matrix-wall.test.tsx` or a new `matrix-table.test.tsx`) -- generic table, sorting headers, roving row-header focus, order freeze while focused, Skjelett.
- `frontend/src/components/charts/matrix-wall.tsx` -- optional controlled `position`/`onPosition`.
- `frontend/src/modules/games/overview.ts` (+ `overview.test.ts`) -- `tableRows` and the Oversikt's columns with sort keys.
- `frontend/src/modules/games/overview-wall.tsx` -- toggle, shared position, switch.
- `frontend/src/components/charts/README.md` -- the table view.
- `frontend/e2e/overview.spec.ts` -- toggle, table at 1440/320/200 % text with axe, sort with `aria-sort`, cell header association, focus kept across switch and update, no cell text < 13 px, no page-level horizontal scroll.

**Acceptance Criteria:**
- Given the Oversikt, when it is shown, then the «Visning» toggle with «Vegg» checked and «Vis som tabell» stands above the wall and can be switched from the keyboard (arrow keys on the radios).
- Given «Vis som tabell», when the table renders, then it is a `<table>` in the region «Alle spill» with a `columnheader` per Uke and a `rowheader` per game, and a cell's accessible headers are its game and «Uke n» with the signed number printed at ≥ 13 px.
- Given the table, when the Lecturer activates «Kjedekost, kr», then the rows sort by it and that header has `aria-sort`, and activating it again reverses it.
- Given keyboard focus on a game's row header, when the data updates or the view is switched, then focus (or the view's one Tab stop) stays on the same Game id.
- Given Playwright with axe at 1440 px, 320 px and 200 % text, then no violations, no table text below 13 px and no page-level horizontal scroll.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- Layers: blind hunter and edge-case hunter only (Sonnet), as the orchestrator asked for this lane; verification-gap and intent-alignment were skipped on that instruction. Both reports came back through files (`review-blind-7-3.md`, `review-edge-7-3.md` in the session scratchpad), as the handback channel dropped them.
- verdicts: 21 findings — high 0, medium 2, low 15, false 4, maybe-false 0
- findings:
  - `[low]` `[reject]` (blind) Any focus inside the region, also on a sort button, freezes the row order — intended: EXPERIENCE.md → Oppdater automatisk says rows do not re-sort while keyboard focus is inside the table; `aria-sort` still names the chosen column and the order catches up on blur. Restricting it to row headers would contradict the source.
  - `[false]` `[reject]` (blind) Refs read during render break under strict/concurrent mode — both renders of a strict-mode pass read the same last committed order and sort (the effect has not run between them), so the output is identical; no state is derived from a torn read.
  - `[low]` `[reject]` (blind) With every game still loading the table has no Uke column and no Skjelett; a failed fetch is silent — the view opens on «Vegg», which fetches the same weeks into the shared cache before anyone switches; the failed-fetch display is Story 7.5's, as recorded in 7.2.
  - `[low]` `[patch]` (blind) The shared Tab stop cannot hold a game with no Uke in the wall — the wall has no cell for such a game, so it falls back to its first game with a cell; README now says so (the table keeps the game).
  - `[low]` `[patch]` (blind) The e2e has one game, so sorting never reorders and Up/Down is untested; five bare Tabs — Up/Down moved into the pure `nextRow` with Vitest cases; the reordering itself is covered by Vitest (`tableRows` and `sortRows` cases); the e2e's last assertion fails if the Tab count drifts. A second Class game would need a five-Student fixture (slow).
  - `[low]` `[patch]` (blind) The rendered-table sort test passed rows already in the expected order — rows now come in as 7, 9, 2 and must come out 2, 9, 7.
  - `[low]` `[reject]` (blind) No Home/End in the table; `choose` runs twice on an arrow key — the spec fixes the key set (Up/Down between games); the second `choose` sets the same id, an idempotent no-op.
  - `[medium]` `[patch]` (blind) The chosen sort resets on every switch to «Vegg» and back — `MatrixTable` takes optional controlled `sort`/`onSort`; `OverviewWall` keeps the sort beside the shared position.
  - `[false]` `[reject]` (blind) `NaN` from a malformed `since` or `chain_cost` breaks the sort — the api schema serves `since` as an ISO datetime and `chain_cost` as a decimal string (`OverviewGame` in `schema.ts`); neither can be malformed.
  - `[low]` `[reject]` (blind) Status descending reverses the order inside each group — descending is defined as the exact reverse of the wall's order, which is what the header promises.
  - `[low]` `[patch]` (blind) Clarity: a pointless `satisfies WallGroup[]`; `useId` in the radio name; the status key as an index; toggle copy under `nb.wall.table` — `satisfies` removed; `useId` names are the allocation panel's pattern, the index is documented on `tableRows`, the copy key groups the table view's words (rejected parts).
  - `[low]` `[reject]` (blind) At 320 px the extra columns push the Uker to the right — the spec's column order; the game column is sticky, «Venter på» wraps within 10–16 em, and the region scrolls on its own (no page scroll, e2e).
  - `[low]` `[reject]` (edge) A focused row removed from the DOM leaves `rowFocused`/`inside` set — games never leave the Oversikt in this story (filters are 7.4); if one did, focus is put on the first row header, which is then true.
  - `[low]` `[reject]` (edge) All rows loading gives no Uke headers and no Skjelett — duplicate of the loading finding, same reason.
  - `[low]` `[patch]` (edge) The table's game with no cells is not the wall's Tab stop after a switch — duplicate, documented in the README.
  - `[medium]` `[patch]` (edge) Sort lost on switching views — duplicate, patched above.
  - `[false]` `[reject]` (edge) `Number(chain_cost)` can be `NaN` — duplicate, same refutation.
  - `[low]` `[reject]` (edge) Home/End/PageUp/PageDown do not move between games — duplicate, the spec's key set.
  - `[false]` `[reject]` (edge) The stored Uke can exceed a game's cells — the wall clamps it (`Math.min(active.week, row.cells)`, `matrix-wall.tsx`), and keeping it lets a switch back return to the Uke the user left.
  - `[low]` `[patch]` (edge) Claim «focus stays on the same Game id» fails for games without cells — duplicate, documented.
  - `[low]` `[reject]` (edge) Claim: no separate `matrix-table-sort.test.ts` — the sort tests live in `matrix-table.test.tsx`; file layout only.
- Matrix audit: Default, Table, Switch and Focus kept — `overview.spec.ts` «Vis som tabell» test (1440 px for sort, update and switch); Sort cost, Sort wait — `overview.test.ts` `tableRows` cases and `matrix-table.test.tsx`; Short game, Loading — `matrix-table.test.tsx` (empty Uke cells, Skjelett) and `overview.test.ts` (failed fetch empty, pending loading). All ran and passed.

## Design Notes

- **Two regions, one name:** only one view is in the DOM at a time, so the table's own region named «Alle spill» is the same region to the user and assistive technology; sharing one `div` across an SVG grid and a table would couple 7.2's scroll-to-sticky handler to the table, which gets real CSS `sticky`.
- **Row headers as the focus target:** a table read by screen-reader table navigation needs no grid keys; one roving Tab stop on the row headers gives the keyboard user «a Class game» to keep focus on without turning 2 160 cells into Tab stops.
- **Sort keys from the caller:** each row carries `cells` (printed text) and `keys` (numbers by column key, null sorts last); a column is sortable when it has `first`; the table never parses text. Status key = row index in the wall's order.

## Verification

**Commands:**
- `cd frontend && npx vitest run src/components/charts src/modules/games/overview.test.ts` -- pass
- `cd frontend && npm run typecheck && npx vitest run && npm run lint:colours && npm run check:copy && npm run build` -- pass
- `cd backend && uv run pytest -q -n auto` -- full suite passes once before commit (no backend change)
- `cd frontend && npx playwright test e2e/overview.spec.ts e2e/landing.spec.ts e2e/homes.spec.ts e2e/order-confirm.spec.ts` -- pass

## Auto Run Result

Status: done

**Summary.** «Vis som tabell» on the Oversikt (frontend only, no api change).
- A Visningsbryter «Vegg» / «Vis som tabell» (the existing `ViewToggle`, legend «Visning») above the wall; «Vegg» by default.
- `components/charts/matrix-table.tsx`: an HTML `<table>` with a caption, `th scope="col"` for Spill, Status, Venter på, Kjedekost, kr and each Uke, `th scope="row"` per game, a signed number in every cell at `table-cell` 13 px (15 px from 1024 px), in a region named «Alle spill» with the game column and header row sticky. Sortable headers (buttons, `aria-sort`, «↑/↓» glyph); keys come from the caller, rows without a key last, ties stable; opens in the wall's order (Status ascending).
- Focus by Game id: one roving row header, Up/Down between games, `focus-ring-inset`; `MatrixWall` takes an optional controlled `position`, shared with the table, so switching views keeps the same game as the Tab stop; while focus is in the table rows keep their places and values update in place; the sort outlasts a switch.

**Files.**
- `frontend/src/components/charts/matrix-table.tsx` (new), `matrix-table-sort.ts` (new: `sortRows`, `nextSort`, `nextRow`, `keepOrder`), `matrix-table.test.tsx` (new), `matrix-wall.tsx` (controlled `position`/`onPosition`), `README.md` (table section).
- `frontend/src/modules/games/overview.ts` (`tableRows`, `TABLE_COLUMNS`, `TABLE_SORT`) + `overview.test.ts`; `overview-wall.tsx` (toggle, shared position and sort).
- `frontend/src/copy/nb.ts` (`nb.wall.table`); `frontend/e2e/overview.spec.ts` (new table test).

**Review.** 21 findings (blind and edge-case hunters, Sonnet). Patch rows: 7 (2 medium rows forming one entry, 5 low rows forming 4 entries). None deferred. 14 rejected: 4 false and 10 low, with reasons in the triage log. Patched entries by verdict: high 0, medium 1, low 4. Follow-up review: not recommended (one medium entry, no high).

**Verification.**
- Backend: full suite 2797 passed in 79 s (no backend change).
- Frontend: typecheck, Vitest (58 files, 750 tests), `lint:colours`, `check:copy` and the build pass.
- Playwright: `overview`, `landing`, `homes`, `order-confirm` (54 tests) pass after the patches; the new test runs axe once at 320 px, 200 % text and 1440 px, checks no text under 13 px or clipped cell (`textReadable`) and no page-level horizontal scroll; it takes about 8 s, of which most is the shared `liveClassGame` setup. No new Vitest test over 1 s. The builder checked screenshots of the table at 1440 and 320 px.

**Decisions taken instead of the founder.**
- Table columns: Spill, Status, «Venter på» («Noah (Grossist), 23 t»), «Kjedekost, kr», then the Uker; Uke header prints the number with a hidden «Uke».
- A plain table (no step fills), numbers right-aligned in even columns; the legend and its minus line show with the wall only.
- Default sort Status ascending = the wall's order; first direction: Spill and Kjedekost ascending, Venter på longest first; status descending is the exact reverse.
- Sort indicator «↑/↓» after the active header, which is also semibold and underlined.
- The keyboard place is one roving row header (Up/Down); no Home/End.
- Two regions with the same name (only one in the DOM) instead of one shared scroll element.
- Row order freezes while any focus is in the table (EXPERIENCE.md's rule), including a sort button.
- The chosen view is not remembered across page loads.
- The builder implemented the story in its own context, as the orchestrator instructed.

**Residual risks.**
- Up/Down between two or more games and the reordering are covered only by Vitest on pure functions, not by a browser test (the e2e fixture has one game).
- A game without a Uke cannot hold the wall's Tab stop; the wall falls back to its first game with a cell.
- Screen reader behaviour of the table was checked through Chromium's accessibility tree only.
