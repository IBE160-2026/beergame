---
title: "Story 7.8: See all four Roles' Orders, inventory and backlog as charts in Spillinnsikt"
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: 'e93af9a2c782b371c2acfd67131020154837b074'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-7-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Spillinnsikt (Story 7.7) shows one game only as four per-Role tables; a Lecturer cannot see at a glance how the Orders, inventory and backlog swung and grew up the chain against customer demand (FR-62, UX-DR33, UX-DR55).

**Approach:** Above the per-Role tables, a section «Kjeden i grafer» with two charts, both Rolle × Uke with Fabrikk at the top and sharing the week columns of their numbers: (1) Ordrestolper over the Rolle × Uke Order table — epic-9's shared `OrderBarsTable` brought over unchanged except one additive, optional Forsterkning — with customer demand as the bottom row «Kundene»; (2) a new shared chart «Lager og restordre»: per Role a stock bar up (`lager`) and a backlog bar down (`restordre`) per Uke, on one scale for the game. Under each chart a «Vis som tabell» link-button swaps it in place for a plain Rolle × Uke table of the same numbers, and back («Vis som graf»). Every number is the insight endpoint's; the endpoint gains `first_large_order_week` per Role.

## Boundaries & Constraints

**Always:**
- **Api:** `InsightRoleOut` gains `first_large_order_week: int | None` — the first Week whose stored Decision log Order is ≥ 10 (`LARGE_ORDER = 10` in `games/insight.py`, named like 9.1's `analysis.facts.LARGE_ORDER`), else null. No other api change; demand, orders, inventory, backlog are 7.7's fields.
- **Epic-9 files** taken with `git checkout origin/epic-9 -- frontend/src/components/charts/order-bars.tsx frontend/src/components/order-bars-table.tsx`. `order-bars.tsx` unchanged. `order-bars-table.tsx`: one additive change only — `OrderBarsRole.amplification` becomes optional (`amplification?: string | null`) and the Forsterkning header and cells render only when some Role defines it (`!== undefined`); with it defined the output is byte-identical to epic-9's. 9.5's Ordrestolper tests are copied verbatim into a new `charts/order-bars.test.tsx`. No Ukeskrubber, no four-Role Kjedebånd, no Forsterkning value (9.5 wires them into Spillinnsikt after the merge).
- **Ordre chart:** roles Fabrikk, Distributør, Grossist, Detaljist (api order reversed), then «Kundene» (`demand`); orders are each Week's placed Order (a null Order of the open Week is left out); `firstLargeWeek` from the api (Kundene: null); `ownRole` unset (staff); `chosenWeek` unset.
- **Lager og restordre chart** (`frontend/src/components/charts/stock-backlog.tsx`, shared, hand-made SVG, fixed width/height/fontSize and `xs` from `GraphOverTable`, `<title>`, `aria-hidden` via the field row): one band per Role in the order given; within a band a zero line at the split of the band by the game's largest stock vs largest backlog; stock bars up in `lager`, backlog bars down in `restordre`; one scale for all bands. Wrapper `frontend/src/components/stock-backlog-table.tsx` puts it in a `GraphOverTable` field with sticky Role labels (`OrderBarsLabels`-style axis) and the Uke header row; no numbers body (its table is «Vis som tabell»).
- **«Vis som tabell»** (`LINK_BUTTON`, `aria-expanded` not used; label swaps to «Vis som graf»): Ordre → table rows Fabrikk…Detaljist, Kundene, one cell per Uke with the Order (empty for none); Lager og restordre → two rows per Role «Fabrikk, lager», «Fabrikk, restordre». Plain HTML table in its own `ScrollRegion`, sticky row header, `th` scopes, numbers via `formatNumber`. Focus stays on the toggle after a swap.
- Not started → neither chart (7.7's «Spillet har ikke startet.» stays). Running game: charts refetch with the page (same query, `game:<id>`).
- Scroll: only the chart/table regions scroll sideways; no page-level horizontal scroll at 320 px. Copy in `nb.insight.charts` (`[ASSUMPTION]`). Fixed px only from measurement (no `ResponsiveContainer`).

**Never:** no number computed in the web app beyond drawing scale and `flowStep` (AD-10); no edit of `order-bars.tsx`, `graph-over-table.tsx`, `scroll-region.tsx`; no Ukeskrubber, Kjedebånd, Forsterkning value, `analysis` function or migration; no change to the per-Role tables.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Finished/running | Weeks 1–n | both charts, 5 Order rows and 4 stock rows, Uke 1…n columns | — |
| Open Week | Week n order null | no bar and empty cell for Week n; stock/backlog of Week n drawn | — |
| No large Order | all Orders < 10 | `first_large_order_week` null; no dot, no diagonal | — |
| First large | Orders 4,4,12,15 | `first_large_order_week` = 3 | — |
| No backlog ever | backlog 0 everywhere | zero line at band bottom; stock bars only | — |
| Not started | no Weeks | no chart section | — |
| Forsterkning absent | `amplification` undefined on all roles | no Forsterkning header or cells | — |

</intent-contract>

## Code Map

- `backend/app/modules/games/insight.py:154-198` -- per-Role loop; add `first_large_order_week` to `InsightRole`.
- `backend/app/modules/sessions/schemas.py:950` `InsightRoleOut`; `overview.py` `game_insight` (`InsightRoleOut(...)` ~:306) -- pass it through.
- `backend/tests/sessions/test_game_insight.py` -- add assertion: equals first stored Order ≥ 10 per Role, null when none.
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerate (`npm run` script used in 7.7).
- `origin/epic-9:frontend/src/components/charts/order-bars.tsx` (`OrderBars`, `OrderBarsLabels`, `orderRows`, `flowStep`), `order-bars-table.tsx` (`OrderBarsTable`, `OrderBarsRole`) -- reuse; imports only `chain-band-layout.textWidth`, `palette`, `graph-over-table`, `number-format`, `utils` (all on epic-7).
- `frontend/src/components/graph-over-table.tsx` -- field API (`GraphField.render(size)`, `head` with `th[scope=col][data-col]`).
- `frontend/src/components/charts/palette.ts` `colour`, `theme/theme.css` tokens `lager`, `restordre`, `axis`, `order-history`, `flow-*`, `row-label-*`.
- `frontend/src/components/link.tsx` `LINK_BUTTON`; `net-over-game-chart.tsx` on epic-9 -- toggle pattern.
- `frontend/src/modules/games/insight-page.tsx` `InsightBody`, `insight.ts` -- add chart section and pure row builders (`orderRoles`, `stockRoles`, `chartWeeks`).
- `frontend/e2e/game-insight.spec.ts` -- extend with charts, toggle, axe and scroll checks.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/games/insight.py`, `sessions/schemas.py`, `sessions/overview.py`, `tests/sessions/test_game_insight.py` -- `first_large_order_week` and its test.
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerate.
- `frontend/src/components/charts/order-bars.tsx`, `order-bars-table.tsx` -- from `origin/epic-9`; additive optional Forsterkning in the table; `charts/order-bars.test.tsx` (9.5's tests verbatim + table test without and with Forsterkning).
- `frontend/src/components/charts/stock-backlog.tsx`, `components/stock-backlog-table.tsx` (+ test in `charts/stock-backlog.test.tsx`) -- new chart and its wrapper.
- `frontend/src/modules/games/insight.ts` (+ `insight.test.ts`) -- pure builders from the api's rows.
- `frontend/src/modules/games/insight-page.tsx`, `frontend/src/copy/nb.ts` -- chart section, «Vis som tabell» tables, copy.
- `frontend/src/components/charts/README.md` -- note the new chart and the Spillinnsikt reuse.
- `frontend/e2e/game-insight.spec.ts` -- charts visible with 5 + 4 rows; the Ordre table's numbers equal the api's Orders; toggle swaps both ways with focus kept; axe at 1440 and 320 px with no page-level horizontal scroll.

**Acceptance Criteria:**
- Given a game with played Weeks, when Spillinnsikt opens, then «Ordre» (Ordrestolper over Rolle × Uke, Fabrikk top, Kundene bottom) and «Lager og restordre» charts show above the per-Role tables, each with «Vis som tabell» under it.
- Given «Vis som tabell» under a chart, when pressed, then a Rolle × Uke table with the api's numbers replaces the chart and the button reads «Vis som graf».
- Given a new Week in a running game, when `game:<id>` arrives, then the charts gain its column without reload.
- Given 1440 and 320 px, when axe runs, then it passes and only the chart/table regions scroll sideways.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- Layers: blind hunter and edge-case hunter only (Sonnet), as the orchestrator asked for this lane; verification-gap and intent-alignment skipped on that instruction. Both hand-backs dropped; findings read from `review-blind-7-8.md` and `review-edge-7-8.md` in the session scratchpad.
- verdicts: 14 findings — high 0, medium 0, low 10, false 4, maybe-false 0
- findings:
  - `[low]` `[reject]` (blind 1) `LARGE_ORDER = 10` is a copy of 9.1's `analysis.facts.LARGE_ORDER`, not an import — `analysis.facts` does not exist on this branch (Epic 9); the merge can point the constant at it. Listed as a residual risk.
  - `[low]` `[reject]` (blind 2) Epic-9 files and tests copied with no tracking issue — the orchestrator's instruction (bring them over unchanged, list any edit); issues are not this lane's to open; the additive change is listed under the decisions for the merge.
  - `[low]` `[patch]` (blind 3) The key says the dot marks «første ordre på 10 eller mer» while the customers' row never gets one — patched: the key reads «hver rolles første ordre på 10 eller mer»; demand is not an Order.
  - `[false]` `[reject]` (blind 4) Chart and table weeks come from different sources and could diverge — `demand` is built from the same opened Week states as every Role's rows (`insight.py`, `demand=tuple(... for state in states)`), so the sets are equal.
  - `[low]` `[patch]` (blind 5) Both «Vis som tabell» buttons share one name; the swap drops the scroll position — patched: each button is `aria-describedby` its chart's heading. Scroll position: rejected, a fresh table starting at Uke 1 is a correct view and keeping both mounted doubles the DOM.
  - `[low]` `[reject]` (blind 6) «Lager og restordre» has no axis ticks or swatches — the chart compares Roles on one scale; the key names both bars and «Vis som tabell» gives every number (the pattern of the other staff charts); the visual check is a separate agent's.
  - `[low]` `[reject]` (blind 7) `restordre` means backlog in one chart and the first-large dot in the other — both are DESIGN.md's own (`order-bars`: «a red dot … a thin red diagonal»); the dot always carries its «Uke n» text.
  - `[false]` `[reject]` (blind 8) Dead copy (`own`, `none`, `amplification`) and duplicated class constants — the copy fills `OrderBarsTable`'s required `texts` (component unchanged by rule); the constants are duplicated so epic-9's file stays unedited.
  - `[low]` `[patch]` (blind 9) The 320 px e2e never asserts the page does not scroll; `expectCharts` takes an inline type — the first half is false (`expectAccessible` and `expectReflow` assert no page-level scroll, with the chart and then the table shown); patched the type to `GameInsight`.
  - `[low]` `[reject]` (blind 10) Edge cases untested (unit 0, empty rows, brittle HTML split) — `stockBands` with no backlog and no rows is guarded by `Math.max`; the split uses `copy.weeksTitle`, not a literal; more cases add tests for no user gain.
  - `[low]` `[reject]` (edge 1) The open Week shows a Kundene bar with no Role bar — the demand of the open Week is stored and true; the matrix row is about the Roles' Orders.
  - `[low]` `[reject]` (edge 2) Same as blind 1.
  - `[low]` `[reject]` (edge 3) Same scroll-reset point as blind 5.
  - `[false]` `[reject]` (edge 4) `demand` empty while Weeks exist gives an empty Kundene row — impossible: `demand` has one entry per opened Week state whenever the game has a Seat.
- Matrix audit: Finished/running — e2e `expectCharts` (5 Order rows, 4 stock bands, Uke columns) and Vitest «puts both charts…»; Open Week — Vitest `orderRoles` (Week 3 left out), `orderTableRows` (empty cell), `stockRoles` (Week 3 drawn), e2e Fabrikk row with an empty open-Week cell; No large Order — `test_every_reason…` (`first_ai` None) and Vitest (Detaljist null); First large — `test_every_reason…` (4, 9, 10, 15 → 3); No backlog ever — `stock-backlog.test.tsx` «zero line at the band's foot»; Not started — Vitest «none before the start»; Forsterkning absent — `order-bars.test.tsx`. All ran and passed.

## Design Notes

- Customer demand as the Ordrestolper's bottom row «Kundene» puts demand on the same scale and columns as the four Roles' Orders, so the swing growing upstream is read in one picture; the diagonal already runs from the customers' end.
- Stock up / backlog down per Role is the four-Role Kjedebånd's convention (9.5) and needs no web-side net figure (AD-10). No numbers body under it: its two rows per Role would double the height; «Vis som tabell» holds them.
- The Ordre chart keeps its Rolle × Uke numbers underneath (UX-DR33) and also gets «Vis som tabell» for UX-DR55's rule «each chart with Vis som tabell».

## Verification

**Commands:**
- `cd backend && uv run pytest -q tests/sessions/test_game_insight.py` -- pass
- `cd frontend && npx vitest run src/components src/modules/games` -- pass
- Before commit: full backend suite `--maxprocesses=8`; `npm run typecheck`, `npx vitest run`, `npm run lint:colours`, `npm run build`; Playwright `--workers=4` `game-insight`, `overview`, `homes`, play-screen specs.

## Auto Run Result

Status: done

**Summary.** Spillinnsikt now shows «Kjeden i grafer» above the per-Role tables: «Ordre», Story 9.5's Ordrestolper over the Rolle × Uke Order numbers (Fabrikk at the top, the customers' demand as a fifth row «Kundene», a dot with «Uke n» at each Role's first Order of 10 or more, joined by a diagonal), and «Lager og restordre», a new shared chart with a band per Role (stock up in `lager`, backlog down in `restordre`, one scale). Under each chart «Vis som tabell» swaps it for a Rolle × Uke table and back («Vis som graf»). Every number is the insight endpoint's, which gains `first_large_order_week` per Role; the charts refetch with the page on `game:<id>`.

**Files.**
- `backend/app/modules/games/insight.py` (`LARGE_ORDER`, `first_large_order_week`), `sessions/schemas.py`, `sessions/overview.py`; `tests/sessions/test_game_insight.py` (assertions, tampered Orders).
- `frontend/src/lib/api/openapi.json`, `schema.ts` (regenerated).
- `frontend/src/components/charts/order-bars.tsx` (from `origin/epic-9`, unchanged); `components/order-bars-table.tsx` (from `origin/epic-9`, one additive change: `amplification` optional, Forsterkning column only when a Role gives it).
- `frontend/src/components/charts/stock-backlog.tsx`, `components/stock-backlog-table.tsx` (new); `charts/order-bars.test.tsx` (9.5's tests verbatim + the Forsterkning column), `charts/stock-backlog.test.tsx` (new); `charts/README.md`.
- `frontend/src/modules/games/insight-charts.tsx` (new), `insight.ts` (+ `insight.test.ts`), `insight-page.tsx`; `copy/nb.ts` (`nb.insight.charts`); `e2e/game-insight.spec.ts`.

**Review.** 14 findings (blind 10, edge case 4; Sonnet): 0 high, 0 medium, 10 low, 4 false. Patched 3 low (key copy, button descriptions, e2e type). Rejected 7 low and 4 false, reasons above. Deferred: none. Follow-up review: not recommended (no high or medium patched).

**Verification.** After the patches: backend full suite 2835 passed (104 s, `--maxprocesses=8`; no new test, two 7.7 tests gained assertions); ruff check and format; frontend typecheck, Vitest 806 passed (none over 1 s), `lint:colours`, `check:copy`, `next build`; Playwright `--workers=4` `game-insight`, `overview`, `homes`, `order-confirm`, `week-advance`, `live-updates` — 50 passed, no flaky reruns. Axe at 1440 px and 320 px (also reflow with a «Vis som tabell» table shown).

**Decisions taken instead of the founder.**
- Customer demand as the Ordrestolper's bottom row «Kundene» (same scale and columns as the Roles' Orders).
- Inventory and backlog as one chart «Lager og restordre» (stock up, backlog down per Role, the four-Role Kjedebånd's convention) rather than a Netto lager matrix, so the web app computes no net figure.
- «Vis som tabell» under both charts, also under the Ordrestolper, whose Rolle × Uke numbers stay underneath (UX-DR33 and UX-DR55 both hold).
- Forsterkning column hidden until a Role gives one: an additive change to epic-9's `order-bars-table.tsx` (`amplification?:`; output with it unchanged).
- `first_large_order_week` computed by the api with its own `LARGE_ORDER = 10`.
- Draft copy `[ASSUMPTION]`: «Kjeden i grafer», «Ordre», «Lager og restordre», both keys, region names, «Vis som graf», «Fabrikk, lager» / «…, restordre».
- Implemented in the builder's own context, as the orchestrator instructed.

**Residual risks.**
- Merge with epic-9: `order-bars-table.tsx` differs by the additive change; 9.5's Ordrestolper tests exist twice (`charts.test.tsx` there, `order-bars.test.tsx` here); README table rows sit next to each other; `LARGE_ORDER` should import `analysis.facts.LARGE_ORDER` after the merge.
- Verification-gap and intent-alignment reviews skipped by instruction.
