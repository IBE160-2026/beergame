---
title: 'Story 6.7: See Netto lager, Posisjon and cost as a graph over the table'
type: 'feature'
created: '2026-11-20'
status: 'done'
baseline_revision: '6f4d036b3bb817d4b6a6054e10dfb429424ca65f'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-6-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The play screen shows the Seat's numbers only as a table (6.6). There is no chart module, no Graf over tabell, no now-line, and the AD-18 spike (alignment at 320/360/1440 px, WeasyPrint `pdf/ua-1`) has not run. The Uke row prints every Week number in `ink`, while mockup 05 greys all but nå (Issue #124).

**Approach:** Create `frontend/src/components/charts` (hand-made SVG with d3-scale/d3-shape, after the spike showed Recharts 3 renders an empty wrapper on the server) with the Netto lager/Posisjon graph and the Kost per uke bars, and `frontend/src/components/graph-over-table.tsx`: one scroll region whose `<table>` carries the graph fields as `aria-hidden` rows over the caller's week rows, so marks share the columns. The engine adds the per-Week cost split to `history` (`SeatState` v3). A CI step renders an internal print page through WeasyPrint 70.0 in `worker-batch` and checks it.

## Boundaries & Constraints

**Always:**
- Web computes no game quantity. Lines use `history[].net_inventory`/`position` and nå's `net_inventory`/`position`; bars use new engine fields `WeekValues.holding_cost`/`backorder_cost` (history) and nå's `cost_lines[].amount`; the key uses `cost_lines[].rate`. `SeatState.schema_version` 3; versions 1 and 2 upgrade on read (amount = rate from the state's own `cost_lines` × units), so `checks._decision_log` still matches. Engine coverage 100 %.
- Chart scales are display logic in the chart module: net y-range = multiples of 20 holding 0, every drawn Netto lager and Posisjon value; tick labels every 20 × k with the smallest k whose spacing is ≥ 1.4 × label font size. Cost axis top = 40 × ceil(max(highest Uke so far incl. nå, 1)/40), minimum 40 (34→40, 40→40, 41→80, 62→80, 121→160); it can only grow because it reads every Uke so far; when top(≤ nå) > top(≤ nå − 1) the line «Aksen går nå til 80 kr.» [ASSUMPTION] shows by the key.
- Netto lager: one 2 px line, `lager` above a true zero with `lager-fill` to zero, `restordre` below with `restordre-fill` (clip at the zero y). Posisjon: 1.5 px `ink-secondary`, 4 px square at every Uke, no fill. Both stop at nå; now-dot on Netto lager; direct labels «Restordre 13»/«Lager 12»/«Netto lager 0» and «Posisjon 3» right of nå, pushed apart to never overlap. Cost bars: holding below, backlog on top, 1.5 px apart, key «Kost per uke ■ restordre 1,00 ■ lager 0,50» (rates from `cost_lines`), one tick «40 kr». Now-line 1.4 px `ink` labelled «Nå», through graph and table; `future-tint` right of it to nå + 4. Field title «Lager over null, restordre under» [ASSUMPTION, as drawn].
- Colours in SVG come from `@/theme/tokens.json` as presentation attributes (lint-safe, self-contained for WeasyPrint). Every chart SVG has `<title>`. Fixed width/height from the caller, never `ResponsiveContainer`; in the browser the caller measures the `th[scope=col]` centres (ResizeObserver) and passes x positions; with a `fixed` layout (print) widths are given in px and nothing is measured. Graph rows are `aria-hidden`; the table is the alternative. No projection unless the `projection` option is passed (only Epic 10).
- Phone draws the phone columns (nå − 7 … nå + 4), ≥ 1024 px all columns; each field has a phone row and a laptop row shown by CSS. Y-axis tick labels sit in the sticky row-label cell of the field row. The region keeps 6.6's scroll-to-nå, «Sveip», one scroll position.
- Uke row: nå number bold `ink`; every other Week number `ink-muted` (Issue #124).
- Print page `frontend/src/app/print/graf-over-tabell/page.tsx`: server-rendered, Demodata Uke 11 fixture, fixed layout; `/print/*` is already 404 at the proxy. `backend/app/platform/chart_print_check.py` (run in `worker-batch`: `python -m app.platform.chart_print_check http://frontend:3000/print/graf-over-tabell`) converts with WeasyPrint 70.0 `pdf/ua-1`, fails if the chart SVG is missing, clipped (outside page or a clipping ancestor), any mark centre is > 1 px from its `th[scope=col]` centre, the title is missing, or any fetched URL leaves the page's origin. Pango libs in `backend/Dockerfile`; `weasyprint==70.0` in backend deps; CI e2e job runs the step.
- Copy in `nb.games.play.graph`, drafts [ASSUMPTION].

**Never:** No Recharts dependency (spike failed, see README); no mark/axis/label at or beyond the game end, no axis past nå + 4; no Kjedebånd, Ordrefelt, typed preview, order-to-arrival line, Setestatus, «Alle rader og kostnad» (later stories); no second number formatter; no browser arithmetic on game quantities; no change to `sprint-status.yaml` or «class-of-1994».

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Uke 1 | no history | one point per line at nå, bar at nå, axis 40 kr | — |
| Middle | Uke 11 fixture | lines Uke 4 … 11 on phone, 1 … 11 laptop; «Restordre 20», «Posisjon −4» | — |
| Late, costly | Uke 30 fixture, highest Uke > 40 kr | axis at the 40-step holding it; no bar cut; ticks thinned to multiples of 20 | — |
| Axis grows now | nå's cost lifts the step | key line «Aksen går nå til N kr.» | — |
| Stored v1/v2 state | Decision log row | reads as v3, cost split filled from its rates; finished-game check ok | malformed refused |

</intent-contract>

## Code Map

- `backend/app/engine/view.py:152` `WeekValues`, `:211` `seat_detail` -- add `holding_cost`, `backorder_cost` (settings rate × units); `backend/tests/engine/test_view.py`.
- `backend/app/modules/games/schemas.py:161` `SeatState` + `_upgrade_version_1` -- v3; upgrade 1→3 and 2→3; `backend/tests/games/test_seat_state_version.py`.
- `backend/tests/games/test_play_fixture.py` -- builder; extend to Uke 3 and 30 (ORDERS tail after Week 10 so Uke 11 is unchanged); fixtures in `frontend/src/modules/games/fixtures/`.
- `frontend/src/modules/games/week-table-view.tsx` -- region logic moves to `components/graph-over-table.tsx`; WeekTable becomes the play screen's use of it (graph fields + rows). `week-table.ts` -- add series model (`graphSeries`) beside `cellFor`.
- `frontend/src/lib/number-format.ts` -- the one formatter (labels, ticks).
- `frontend/e2e/week-table.spec.ts` -- `withPlay`, `visibleWeeks`, `textReadable`; `support/classes.ts` `expectAccessible`, `VIEWPORTS`.
- `proxy/Caddyfile:16` -- `/print/*` 404; `docker-compose.yml` -- worker-batch reaches `frontend:3000`.
- `.github/workflows/ci.yml` e2e job -- add the print-check step after the smoke test.

## Tasks & Acceptance

**Execution:**
- `backend/app/engine/view.py` + test -- cost split on `WeekValues`.
- `backend/app/modules/games/schemas.py` + tests -- v3 with upgrades.
- `backend/tests/games/test_play_fixture.py`, fixtures `play-week-{1,3,11,30}.json` -- regenerate/new.
- `frontend/src/lib/api/{openapi.json,schema.ts}` -- regenerate.
- `frontend/src/components/charts/{scales.ts,scales.test.ts,net-graph.tsx,cost-bars.tsx,axis.tsx,README.md}` -- module.
- `frontend/src/components/graph-over-table.tsx` (+ SSR test) -- region, field rows, measurement, now-line, fixed layout.
- `frontend/src/modules/games/{week-table.ts,week-table.test.ts,week-table-view.tsx}`, `copy/nb.ts` -- series, fields, grey Uke numbers.
- `frontend/src/app/print/graf-over-tabell/page.tsx` -- print page.
- `backend/app/platform/chart_print_check.py` (+ pure-geometry test), `backend/pyproject.toml`/`uv.lock`, `backend/Dockerfile`, `.github/workflows/ci.yml` -- WeasyPrint check.
- `frontend/e2e/graph-over-table.spec.ts` (new) -- alignment, labels, axe, 200 % text, early/middle/late.

**Acceptance Criteria:**
- Given the Uke 11 fixture at 320, 360 and 1440 px, when the play page renders, then every Netto lager vertex, Posisjon marker and cost bar centre is within 1 px of its `th[scope=col]` centre, and the now-line sits at the nå column's right edge.
- Given Uke 3, 11 and 30 at 320/360/1440 px and at 320/360 px with 200 % text, then no graph label overlaps another, no text < 13 px, no clipped cell, no page-level horizontal scroll, axe clean; the graph adds no accessible text (rows `aria-hidden`).
- Given 360 px, when the region is scrolled, then the y-axis labels stay in the sticky label column and marks stay over their columns.
- Given the Uke row, then nå is bold `ink` and every other Week number `ink-muted`.
- Given Vitest, then the cost axis gives 40/40/80/80/160 for 34/40/41/62/121, the net range/tick thinning, the series model, and that the SVG has `<title>` and no projection path unless asked.
- Given the stack, when `chart_print_check` runs in `worker-batch`, then it exits 0, and it fails on a mark moved 2 px or an off-origin font URL (unit-tested on its geometry/fetcher functions).

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 31 findings — high 0, medium 0, low 22, false 9, maybe-false 0
- findings:
  - `[low]` `[reject]` blind: the cost split has no text alternative. The table holds Kost, kr and Netto lager; an end-of-Week balance is either stock or backlog, so the row's sign says which part a Uke's cost is, and the key gives the rates. The AC names the visible table as the alternative.
  - `[low]` `[reject]` blind: the split formula sits in the engine view and in the upgrade. The engine test pins `holding_cost + backorder_cost == cost` for every Week, Role and delay set; the upgrade reads the state's own rates and is tested equal to a rebuild.
  - `[low]` `[patch]` blind + edge: `_rates` let a non-finite rate through, and `Infinity × 0` raised `InvalidOperation` (a 500, not a ValidationError). Non-finite rates now leave the split missing, so the field check refuses the state; tests for «Infinity» and «sNaN».
  - `[low]` `[reject]` blind + edge: `amountOf`/`rateOf` default to «0»/«» when a cost line is missing. `engine.seat_detail` always emits both lines; unreachable.
  - `[false]` `[reject]` blind: bar height and axis top read different fields. The engine test pins that the split sums to `cost`, so they cannot disagree.
  - `[low]` `[patch]` blind: a stacked bar stood 1.5 px above its value (the gap moved the top). The gap now comes out of the backlog part; the test asserts the top at the value.
  - `[low]` `[patch]` blind: the CostBars test did not check stacking, gap or tops (and its regex caught the tint rect). It now asserts lager at the bottom, restordre on top, 1.5 px apart, top at the value and under the axis top.
  - `[low]` `[reject]` blind: the PDF check does not check labels, the now-line or bar tops. The AC asks it for missing, clipped, out of line and foreign fonts; the browser checks cover labels and the now-line on the same chart code.
  - `[false]` `[reject]` blind: print tooling in every backend image. AD-24 builds one image for api and workers, and AD-18 puts WeasyPrint in that worker.
  - `[false]` `[reject]` blind: charts are read in the PDF besides the table. AD-18 makes the SVG `<title>` the PDF's alternative text on purpose; the report's reading order is Epic 13's veraPDF check.
  - `[low]` `[reject]` blind: the direct-label width is estimated. A wrong estimate only moves the label; the e2e label check fails on overlap or a label leaving its chart at every size.
  - `[low]` `[reject]` blind: the Recharts result is not a committed script. The README gives the exact call and output; reproducing it means adding a dependency the spike rejected.
  - `[low]` `[reject]` blind: the e2e scroll test names «Graf og tabell» literally inside `page.evaluate`. As in `week-table.spec.ts`; a rename fails the test loudly, not silently.
  - `[low]` `[reject]` blind: `measure` leaves `variants` out of its dependencies; charts re-render on scroll state. `variants` derives from `columnKey`; a re-render on «Sveip» toggling is cheap.
  - `[low]` `[reject]` intent (a): the composed graph-and-table (`WeekTable`) lives in `modules/games`, the shared shell in `components/`. The shell is what Epics 7/9/10/13 reuse with their own rows; the Landing (6.8) can render `WeekTable` over Demodata with no second chart implementation.
  - `[low]` `[reject]` intent (b): the PDF check runs the fixed layout, Playwright the measured one. AD-18 asks for a fixed width in print; both paths draw with the same chart components and are each checked.
  - `[false]` `[reject]` intent (c): Recharts never went through the two checks. A server render without an SVG fails the PDF check before alignment can be measured.
  - `[false]` `[reject]` intent (d): rates from `cost_lines`, not the game's rules. `cost_lines[].rate` is the Game settings' rate as the play envelope returns it (the one number source, AD-10).
  - `[false]` `[reject]` intent (e): scope beyond the story. Each addition serves an AC (cost split, PDF check, print page); the proxy's `/print/*` 404 is covered by `test_proxy_config.py` and the smoke script.
  - `[false]` `[reject]` intent (f): captions add a reading. They add the field title and the rates, not a second reading of the table's numbers.
  - `[low]` `[reject]` intent (f): ticks thin to multiples of 40/60 when labels would collide. Recorded as a founder-level call; ticks stay multiples of 20 and never overlap.
  - `[low]` `[reject]` intent (f): Issue #124 asserted at 360 px only. The class is the same at every width (SSR test and e2e).
  - `[low]` `[patch]` edge: with no nå column, the measured path threw (`found[-1]`) and the fixed path drew the now-line at the first column. Guarded: nowX past the last column, no now-line; Vitest case added. (Grouped with the next row.)
  - `[low]` `[patch]` edge: fixed layout with no nå column. Same fix.
  - `[low]` `[reject]` edge: fixed layout at ≥ 1024 px uses the phone variant's now-line. The print page is A4 portrait (643 px), always the phone variant.
  - `[low]` `[reject]` edge: mismatched `data-weeks`/`data-x` raises in the check. The check then exits non-zero with a traceback: it still fails.
  - `[low]` `[reject]` edge: a mark without x/width crashes the check. Same: a loud failure on markup the module never emits.
  - `[false]` `[reject]` edge: key without rates. As the `amountOf` row.
  - `[low]` `[patch]` edge (claim): WeasyPrint's anonymous line/text boxes inside a `th` carry its tag, so the column centre came from the glyph run. Only `TableCellBox` counts now (verified: the anonymous boxes exist; centres matched here).
  - `[false]` `[reject]` edge (claim): vertical clipping unchecked. The check fails when the page breaks over more than one PDF page, and no ancestor of the charts hides overflow in print.
  - `[low]` `[patch]` edge (claim) + verification-gap: the scroll test ran at 320 px, and no test re-measured after a layout change. The scroll test now runs at 360 px with 200 % text; a new e2e loads at 1440 px, switches to 320 px and then 200 % text, and asserts every mark back over its column and labels apart.

## Design Notes

Spike outcome (record in charts README): `renderToStaticMarkup(<LineChart width=300 height=100 …>)` with recharts 3.11.0 and `<BarChart>` both yield `<div class="recharts-wrapper" …></div>` with no SVG, so both chart types fail the server-render/WeasyPrint check before alignment; both are hand-made SVG. Graph fields as table rows make column sharing structural; SVGs are absolutely placed in their cell in the browser so they never widen a column. Founder-level calls: cost split as engine fields (v3) rather than browser arithmetic; tick thinning rule; label texts by sign («Lager n» / «Restordre n» / «Netto lager 0»); `ink-muted` for non-nå Week numbers; print page at an internal route with Demodata; WeasyPrint in the shared backend image. Fixed layout cells are content-box with explicit padding, because WeasyPrint sizes table cells by their content box whatever `box-sizing` says (the first PDF run caught a 2.6 px-per-column drift).

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/engine tests/games/test_seat_state_version.py tests/games/test_play_fixture.py tests/platform -q` -- pass
- `cd frontend && npx vitest run src/components src/modules/games` -- pass
- `docker compose exec -T worker-batch python -m app.platform.chart_print_check http://frontend:3000/print/graf-over-tabell` -- exit 0
- full: backend pytest + ruff; frontend typecheck, Vitest, check:copy, build, Playwright `--workers=2` -- pass

## Auto Run Result

Status: done

**Summary.** The play screen's week table now has Graf over tabell: a Netto lager field (one 2 px line, `lager` with `lager-fill` above a true zero, `restordre` with `restordre-fill` below, now-dot, direct labels «Restordre 20»/«Posisjon −4») with the Posisjon line (1.5 px `ink-secondary`, 4 px squares, no fill), and a Kost per uke field (stacked bars, lager below and restordre above 1.5 px apart, key «Kost per uke ■ restordre 1,00 / ■ lager 0,50» from `cost_lines` rates, one tick «40 kr» that grows 40 kr at a time, «Aksen går nå til 80 kr.» in the Uke it grows), the «Nå» line through graph and table and `future-tint` right of it. The fields are `aria-hidden` rows of the table itself, so marks sit on the week columns (measured in the browser, ≤ 1 px at 320/360/1440 px and 200 % text); y-axis labels sit in the sticky label column. Week numbers other than nå are `ink-muted` (Issue #124). The AD-18 spike: Recharts 3.11.0 renders an empty wrapper on the server, so every chart type is hand-made SVG (d3-scale, d3-shape) in the new `components/charts` module (README records it); the server-rendered `/print/graf-over-tabell` goes through WeasyPrint 70.0 `pdf/ua-1` in `worker-batch` and passes the new check. The engine adds `holding_cost`/`backorder_cost` to each history row; `SeatState` is version 3, with stored versions 1 and 2 upgraded on read.

**Files.**
- `backend/app/engine/view.py`, `backend/tests/engine/test_view.py` -- cost split per history Week.
- `backend/app/modules/games/schemas.py`, `backend/tests/games/test_seat_state_version.py`, `test_views.py`, `backend/tests/sessions/test_play.py` -- `SeatState` v3 and upgrades.
- `backend/tests/games/test_play_fixture.py`, `frontend/src/modules/games/fixtures/play-week-{1,3,11,14,30}.json` -- engine-pinned stand-ins (3, 14, 30 new).
- `backend/app/platform/chart_print_check.py`, `backend/tests/platform/test_chart_print_check.py`, `backend/pyproject.toml`, `uv.lock`, `backend/Dockerfile` (Pango), `.github/workflows/ci.yml` (e2e step) -- WeasyPrint check.
- `frontend/src/components/charts/{net-graph,cost-bars,axis-labels}.tsx`, `scales.ts`, `palette.ts`, `charts.test.tsx`, `README.md` -- chart module.
- `frontend/src/components/graph-over-table.tsx` (+ test) -- shared Graf over tabell shell (scroll region moved here from 6.6).
- `frontend/src/modules/games/{week-table.ts,week-table-view.tsx,week-table.test.tsx}`, `frontend/src/copy/nb.ts` -- series, fields, grey Week numbers, copy.
- `frontend/src/app/print/graf-over-tabell/page.tsx` -- internal print page (Demodata).
- `frontend/e2e/graph-over-table.spec.ts` -- alignment, labels, readability, axe, scroll, re-measure.
- `frontend/package.json`/lock (d3-scale, d3-shape), `frontend/src/lib/api/{openapi.json,schema.ts}`.

**Review.** One pass, four layers, 31 findings (high 0, medium 0, low 22, false 9). Patched (all low): non-finite stored rates refused; bar top at its value; CostBars test; no-nå guard; TableCellBox-only column centres in the PDF check; 360 px/200 % scroll test and a re-measure e2e. Deferred: none. Rejections with reasons in the triage log.

**Follow-up review:** false. No high or medium entry was patched (patched: 6 low entries).

**Founder-level decisions taken (no human in the loop).** Recharts dropped after the spike (server render empty) and all charts hand-made SVG; cost split added to the engine/`SeatState` (v3, stored rows upgraded on read) instead of browser arithmetic; graph fields as `aria-hidden` rows of the week table, captions read; tick labels thinned to multiples of 40/60… when 20-steps would collide; direct labels «Lager n»/«Restordre n»/«Netto lager 0» by sign; field title «Lager over null, restordre under» (as drawn); `ink-muted` for non-nå Week numbers; SVG `<title>` texts and «Aksen går nå til … kr.» as draft copy [ASSUMPTION]; internal print page with Demodata at `/print/graf-over-tabell`; WeasyPrint and Pango in the shared backend image; the check run as a CI step in the e2e job; the shared component is the generic shell in `components/`, the Seat's composed graph-and-table stays `WeekTable` in `modules/games` (6.8 and the briefing's graph strip can reuse it). The implementation ran in the orchestrating agent's own context (caller's runbook).

**Verification.**
- Backend: 2693 passed (62 s), engine coverage 100 %, ruff clean, `prompts check` ok.
- Frontend: typecheck, Vitest 523 passed (+ new), `check:copy`, build; compose rebuilt; chart PDF check `ok` in `worker-batch`; Playwright full run `--workers=2`: 349 passed (5.7 min). New e2e tests ≈ 0.6–1.2 s each (axe at 200 % text); no fixed sleeps.
- No migration.

**Residual risks.** At 360 px with 200 % text only about 3.5 future columns show, so the direct labels right of nå can be partly scrolled out of view (the numbers are in the table). The PDF check exercises the fixed layout and the browser checks the measured one. Draft copy awaits the founder (#31).
