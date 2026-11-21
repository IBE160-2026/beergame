---
title: "Story 6.16: See what my Seat has cost so far"
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '3379ea4c2b2bc2ad3fec58a21556315ffbe33469'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-6-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Student sees only the running Totalkostnad as plain text in the Topplinje. There is no «Kostnad så langt» panel (Lagerkostnad, Restordrekostnad, Totalkostnad over tid, the Uke's sum), no phone screen «Alle rader og kostnad» with every row and the column sums, and the Landing's right half is empty at 1440 px. The api has no running cost split per Uke, and the web app may not add it up (AD-10).

**Approach:** Add the running cost split to `SeatState` (version 4) in the engine's `seat_detail`. Build a `CostPanel` with a hand-made stacked-area chart (`components/charts/cost-area.tsx`). Pin the panel under the Ordrefelt from 1024 px, open it from the Totalkostnad button, the Lenke «Alle rader og kostnad» or the Uke-overgang's «Kostnad så langt» inside a full-screen «Alle rader» view on phone, and put it beside or under the Landing's Demodata figure.

## Boundaries & Constraints

**Always:**
- Backend: `engine.view.WeekValues` gains `total_cost`, `total_holding_cost` and `total_backorder_cost` (running through that Uke). `SeatDetail` and `games.schemas.SeatState` gain `total_holding_cost` and `total_backorder_cost` (running through nå, nå included; together they equal `total_cost`). `SeatState.schema_version` becomes 4. A stored version 1–3 state reads as version 4: the running sums come from its history rows' costs plus nå's `cost_lines` amounts. A version 1–3 object that already holds them is refused. The LLM prompt inputs (`players/llm.build_inputs`) stay the same. Regenerate `openapi.json` + `schema.ts` and the engine-held fixtures (`play-week-*.json`, `demo-seat.json`).
- Topplinje: below 1024 px, the Totalkostnad pair is one `<button>` named «Totalkostnad 68,00 kr, vis alle rader og kostnad», at least 44 px tall. From 1024 px it is plain text.
- Above the Ordrefelt, below 1024 px only, a right-aligned Lenke «Alle rader og kostnad» shows in every Ordrefelt state.
- «Alle rader» (phone view, any width once open): it replaces the Topplinje and the play content on the same route. It has no overlay, sits on `paper`, has the h1 «Alle rader, Uke 11» with «Grossist, Spill 17» under it and the Lenke «Lukk» at the top right. Below that it shows `WeekTable` with all rows at every width: Uke, Ordre inn, Levering, Sendt, Lager, Restordre, Netto lager, På vei, Posisjon, Din ordre, Kost per uke, «Sum, kr». It keeps the typed preview. Under the table stand «Netto lager i kolonne 11» with «−9 + 4 − 8 = −13» (the previous `history` row's `net_inventory`, nå's `incoming_delivery`, nå's `incoming_order` and nå's `net_inventory`), then «Posisjon i kolonne 11» with «−13 + 16 = 3» (`net_inventory`, `supply_line`, `position`), then `CostPanel`. In Uke 1 the Netto lager line is left out because there is no earlier column. On open, focus goes to the h1, or to the panel's heading (scrolled into view) when «Kostnad så langt» opened it. «Lukk» brings the play screen back with the typed text kept and focus on the opener.
- `CostPanel` («Kostnad så langt», h2 in `label`): rows «Lagerkostnad» and «Restordrekostnad», each with a 3 px bar (`lager` / `restordre`) under the label. The bar's width is that part's share of `total_cost`, and the amount is right-aligned in weight 600. Then an `axis` rule and «Totalkostnad» in weight 700. Then «Totalkostnad over tid» as a stacked area of Uke 1…nå: holding below, backlog above, true zero, ticks 0 / half / top, «Uke 1» and bold «Uke {nå}» under the chart. The SVG is `aria-hidden` and has a `<title>`. The panel ends with the Uke's sum line (`weekSummary`'s cost line, `caption`). It reads `seat_state` only, so typing never changes it. It shows the own Seat only and never what to order.
- Table alternative: in the pinned and Landing panels, the Lenke button «Vis som tabell» (`aria-expanded`) swaps the chart in place for a table Uke / Lager / Restordre / «Sum, kr» (running sums from the api). The button then reads «Vis som graf». In Alle rader there is no toggle; a sr-only line points to the «Sum, kr» row.
- Uke-overgang: the Lenke «Kostnad så langt» shows below 1024 px only and opens Alle rader at the panel.
- Laptop (≥ 1024 px): `CostPanel` is pinned directly under the Ordrefelt in the right column, before Setestatus.
- Landing: `CostPanel` over `DEMO_SEAT`, labelled «Demodata». It stands right of the figure where the row has room and under it otherwise. It comes last in the phone stack, after the figure and before the class-curves line.
- Cost axis top (Issue #126): the smallest multiple of 20 kr that holds the costliest Uke, and never below 20 kr. It still never shrinks.
- Strings go in `nb.ts`; draft ones are marked [ASSUMPTION]. Charts live only in `components/charts`. Numbers use `formatNumber`.

**Never:** another Seat's or the chain's cost in the panel; a reference or suggested Order; client sums of game quantities (bar widths and chart scales are display ratios only); a modal overlay; changing «class-of-1994»; fixed sleeps in tests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Phone, Uke 11 fixture | total 82,00, holding 40,00, backlog 42,00 | button «Totalkostnad 82,00 kr, vis alle rader og kostnad»; panel rows match the api | — |
| Open via Totalkostnad, type 24 first | typed 24 | Alle rader shows the preview; «Lukk» → field still 24, focus on the button | — |
| Uke 1 | no history, total 6,00 | no Netto lager column line; area chart draws a single Uke; table one row | — |
| Total 0 | all zero | bars width 0, chart flat at zero, top 50 | — |
| Laptop 1440 | — | panel pinned under the Ordrefelt; no «Alle rader og kostnad» or «Kostnad så langt» link | — |
| Stored v3 `state_seen` | Decision log row | validates as v4 with the same running sums; finished-game check passes | v3 holding the new fields → refused |

</intent-contract>

## Code Map

- `backend/app/engine/view.py:152` `WeekValues`, `:187` `SeatDetail`, `:219` `seat_detail` -- running sums in the loop (`seat.cost` = holding × inventory + backorder × backlog).
- `backend/app/modules/games/schemas.py:189` `SeatState` + `_upgrade_stored_versions` -- v4 and the upgrade; `checks.py:156` compares stored states field by field (read-only).
- `backend/tests/games/test_seat_state_version.py`, `tests/engine/test_view.py`, `tests/games/test_play_fixture.py` (fixture generators: `wholesaler_in_week`, `landing_demo_seat`) -- extend and regenerate.
- `backend/app/openapi.py` → `frontend/src/lib/api/openapi.json`, then `npm run api:generate`.
- `frontend/src/modules/games/play-page.tsx:112` `Topplinje`, `:139` `Running` -- button, open state lifted into `PlayView`, pinned panel, link above `OrderField`.
- `frontend/src/modules/games/week-table.ts:49` `ROWS`, `cellFor` -- the `all` row set (inventory, backlog, totalCost); `graphSeries` uses `costAxisTop`.
- `frontend/src/modules/games/week-table-view.tsx:174` `WeekTable` -- `allRows` shows every row at every width.
- `frontend/src/modules/games/week-summary.ts` (cost line), `week-summary-view.tsx` -- the «Kostnad så langt» Lenke (`onCost`).
- `frontend/src/components/charts/scales.ts` -- `COST_STEP` 20, `totalAxisTop` (50 · 1-2-5); `cost-bars.tsx`, `net-graph.tsx` -- style reference; `palette.ts`; `README.md` gets a row.
- `frontend/src/modules/landing/landing-page.tsx`, `seat-figure.tsx`, `demo-seat.ts` -- landing panel.
- `frontend/src/copy/nb.ts:1499` `games.play` -- `allRows`, `costPanel` strings; `terms.totalCost`, `costPerWeek`.
- `frontend/e2e/support/play.ts` (`openPlay`, `week12` -- add the new fields), `graph.ts` (`alignment`, `textReadable`), `classes.ts` (`VIEWPORTS`, `expectAccessible`).

## Tasks & Acceptance

**Execution:**
- `backend/app/engine/view.py`, `backend/app/modules/games/schemas.py` -- the v4 fields and the upgrade; tests in `test_seat_state_version.py` (v1–3 → v4, refusals) and `tests/engine/test_view.py` (running sums equal the sum of the rows; holding + backorder = total).
- Regenerate the fixtures through `test_play_fixture.py`'s generators, plus `openapi.json` and `schema.ts`.
- `frontend/src/components/charts/scales.ts` (+ test) -- 20-kr step and `totalAxisTop`; `cost-area.tsx` (new, + test in `charts.test.tsx`).
- `frontend/src/modules/games/cost-panel-view.tsx` (new) + `cost-panel.ts` (pure model: rows, shares, series, column lines) + `cost-panel.test.tsx` -- including a check over every fixture that previous net + Levering − Ordre inn = Netto lager.
- `frontend/src/modules/games/week-table.ts`, `week-table-view.tsx` -- all rows.
- `frontend/src/modules/games/all-rows-view.tsx` (new) -- the Alle rader screen.
- `play-page.tsx`, `week-summary-view.tsx`, `nb.ts`, landing files -- wiring.
- `frontend/e2e/cost-panel.spec.ts` (new, stubbed play + Landing) -- open and close by each control with typed text and focus kept, rows and column lines, laptop pin and «Vis som tabell», Uke-overgang link, graph alignment in Alle rader, axe + no page scroll + text ≥ 13 px at 320, 360, 1440 and 360 @ 200 %.

**Acceptance Criteria:**
- Given the phone play screen, when the Student presses the Totalkostnad button or «Alle rader og kostnad», then Alle rader opens as specified, and «Lukk» returns with the typed Order and focus on the opener.
- Given 1440 px, then «Kostnad så langt» is visible under the Ordrefelt and «Vis som tabell» shows the Uke / Lager / Restordre / «Sum, kr» table in place.
- Given the Landing at 1440 px, then the panel stands right of the figure with «Demodata»; at 360 px it comes after the figure.
- Given 320, 360, 1440 and 360 px at 200 % text, then only the graph-and-table region scrolls sideways, no text is below 13 px and axe finds no violation.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- layers: blind hunter and edge-case hunter only (the orchestrator caps reviewers at two); verification-gap and intent-alignment skipped.
- verdicts: 23 findings — high 0, medium 2, low 12, false 9, maybe-false 0
- findings:
  - `[medium]` `[patch]` blind: the Uke-overgang's polite region sat inside the hidden play screen, so an advance while Alle rader is open was not heard. It now stands outside the hidden wrapper.
  - `[low]` `[patch]` blind: «Lukk» focused an opener that may have been replaced meanwhile (a new Uke, the Order sent). Focus now falls back to the visible «Alle rader og kostnad» or Totalkostnad button, else the Uke heading.
  - `[low]` `[patch]` blind: there was no Escape or Back to close Alle rader. Escape now closes it as «Lukk» does (e2e). Back is unchanged: in-page state is a founder-level call recorded in the Design Notes.
  - `[low]` `[reject]` blind: on phone the chart's split per Uke has no text equivalent. EXPERIENCE.md names the «Sum, kr» row as that table on phone, and the split so far is in the panel's rows.
  - `[false]` `[reject]` blind: stored v4 sums are not checked to add up. `checks._decision_log` compares every `state_seen` field with the recomputed state, so an inconsistent stored state is flagged.
  - `[false]` `[reject]` blind: `seat_detail` might sum Weeks after `week`. `week = len(states)` and `seats` come from the same `states`, so there are none.
  - `[false]` `[reject]` blind: the 20 kr step is bundled in and the e2e baselines are untouched. The caller asked for the Issue 126 fix here, and `graph-over-table.spec.ts` and the unit tests were updated.
  - `[false]` `[reject]` blind: the LLM prompt grows. `players/llm.build_inputs` picks named fields, so the prompt is unchanged.
  - `[false]` `[reject]` blind: Alle rader on laptop is untested. From 1024 px the Totalkostnad pair is plain text and the Lenker are hidden, so there is no way to open it on laptop.
  - `[low]` `[patch]` blind: `aria-expanded` on a view swap. Removed; the button's label («Vis som tabell» / «Vis som graf») says the state.
  - `[low]` `[reject]` blind: a hidden copy of the play screen stays mounted. Deliberate, so the typed Order and the send state survive; ids come from `useId`.
  - `[low]` `[patch]` blind: the upgrade with empty history was untested. Added `test_an_older_uke_1_state_reads_as_version_4`. Duplicate cost-line kinds never come from the engine (not patched).
  - `[low]` `[reject]` blind: nothing shows that Totalkostnad is a button. It is plain as drawn in `05-spill.png`, and `globals.css` gives every control a `:focus-visible` outline.
  - `[false]` `[reject]` blind: an empty header band above Alle rader. `PageShell` renders `header` with no wrapper chrome.
  - `[low]` `[reject]` blind: the Landing at 1024–1279 px is untested. Checked on a screenshot at 1024 px (the panel wraps under the figure); another e2e width is not worth its cost.
  - `[low]` `[patch]` edge: «Lukk» leaves no focus when the opener was replaced. Same fix as the blind row above.
  - `[low]` `[reject]` edge: the Alle rader state survives a game that stops running. A finished game never runs again, so this cannot happen in use.
  - `[medium]` `[patch]` edge: the announcement is hidden while Alle rader is open. Same fix as the first row.
  - `[false]` `[reject]` edge: a Guided Week with no Order drops the Lenke. A Guided Week's turn holds its fixed Order from the moment it opens (`test_play_fixture`).
  - `[false]` `[reject]` edge: a stored v1–3 `total_cost` that differs from the upgraded sums. The finished-game check compares the upgraded state with the engine's, so a mismatch is reported.
  - `[low]` `[reject]` edge: a duplicate `kind` in stored `cost_lines`. The engine always writes exactly one holding line and one backorder line.
  - `[false]` `[reject]` edge: a NaN share. The amounts are validated `Money` decimals from the api.
  - `[false]` `[reject]` edge: a chart narrower than its tick column. At 320 px, and at 360 px with 200 % text, the box is far wider than the ticks (the e2e label checks pass).

## Design Notes

Founder-level calls: Alle rader is in-page state on the same route (no URL change; Back leaves the page as before; Escape closes it). Below 1024 px the Totalkostnad pair is a button; from 1024 px it is plain text. «Vis som tabell» swaps the chart for the table and reads «Vis som graf» to go back. The area chart's axis top steps 50 / 100 / 200 / 500 ×10ⁿ. In Uke 1 the Netto lager column line is omitted. The Landing panel stands beside the figure and wraps under it when the row is too narrow. New strings are drafts.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/games/test_seat_state_version.py tests/engine/test_view.py tests/games/test_play_fixture.py -q` -- pass
- `cd frontend && npx tsc --noEmit && npx vitest run src/modules/games src/components src/modules/landing` -- pass
- `cd frontend && npx playwright test e2e/cost-panel.spec.ts e2e/landing.spec.ts e2e/homes.spec.ts e2e/week-transition.spec.ts e2e/graph-over-table.spec.ts e2e/week-table.spec.ts` -- pass

## Auto Run Result

Status: done

**Summary.** `SeatState` is now version 4. The engine's `seat_detail` adds the running cost split: `total_holding_cost` and `total_backorder_cost` on the Week, and `total_cost`, `total_holding_cost` and `total_backorder_cost` on each history row. A stored v1–3 state upgrades to v4 with the same numbers.

«Kostnad så langt» (`CostPanel`) shows:
- Lagerkostnad and Restordrekostnad, each with a thin share bar
- Totalkostnad
- «Totalkostnad over tid», a hand-made stacked-area SVG (`aria-hidden`, with a `<title>`)
- the Uke's sum line

From 1024 px the panel is pinned under the Ordrefelt. Its «Vis som tabell» / «Vis som graf» button swaps in the Uke / Lager / Restordre / «Sum, kr» table.

On phone, three controls open «Alle rader, Uke 11»:
- the Totalkostnad pair, now one button named «Totalkostnad 82,00 kr, vis alle rader og kostnad»
- the Lenke «Alle rader og kostnad» on the Ordrefelt's label line
- the Uke-overgang's «Kostnad så langt», which opens the screen at the panel

Alle rader is a full screen with «Lukk» (Escape also closes it). It shows every row, including Lager, Restordre and «Sum, kr». Under the table stand the column sums «Netto lager i kolonne 11 −14 + 4 − 10 = −20» and «Posisjon i kolonne 11 −20 + 16 = −4», then the panel. The play screen stays mounted underneath, so the typed Order and focus come back on «Lukk».

The Landing gets the panel, labelled «Demodata», beside the Demodata figure; it wraps under the figure when the row is narrow. The Kost per uke axis now steps 20 kr (Issue #126).

**Files.**
- `backend/app/engine/view.py`, `backend/app/modules/games/schemas.py` -- the running sums; v4 and its upgrade.
- `backend/tests/engine/test_view.py`, `tests/games/test_seat_state_version.py`, `test_views.py`, `tests/sessions/test_play.py` -- the sums, the column identity, the upgrades, version 4.
- `frontend/src/lib/api/openapi.json`, `schema.ts`, `src/modules/games/fixtures/play-week-*.json`, `src/modules/landing/demo-seat.json` -- regenerated.
- `frontend/src/components/charts/cost-area.tsx` (new), `scales.ts` (the 20 kr step, `totalAxisTop`), `README.md`, `charts.test.tsx`.
- `frontend/src/components/link.tsx` -- the shared `LINK_BUTTON`.
- `frontend/src/modules/games/cost-panel.ts`, `cost-panel-view.tsx`, `all-rows-view.tsx`, `cost-panel.test.tsx` (new).
- `frontend/src/modules/games/week-table.ts`, `week-table-view.tsx` (`ALL_ROWS`, `allRows`), `week-summary.ts` (`weekCostLine`), `week-summary-view.tsx` (the cost Lenke), `order-field.tsx` (`aside`), `play-page.tsx` (wiring), `week-table.test.tsx`.
- `frontend/src/modules/landing/landing-page.tsx`, `frontend/src/copy/nb.ts` (`totalCostButton`, `allRows`, `costPanel`, `summary.costLink`, `table.sum`).
- `frontend/e2e/cost-panel.spec.ts` (new); `support/play.ts` and the `week-transition`, `week-table`, `order-field`, `order-confirm`, `order-failures`, `landing` and `graph-over-table` specs -- adjusted for the button, the Lenke and the 20 kr axis.

**Review.** Two layers (blind, edge case) reported 23 findings: high 0, medium 2 (the same defect, found by both), low 12, false 9.
- Patched: the live region moved out of the hidden play screen (medium); a focus fallback after «Lukk»; Escape closes Alle rader; `aria-expanded` dropped from the view swap; a Uke 1 upgrade test.
- Deferred: none.
- Rejected: the rest, each with its reason in the triage log.

**Follow-up review:** false. This pass patched one medium and four low entries, and no high.

**Founder-level decisions taken (no human in the loop).**
- Alle rader is in-page state on the same route: there is no URL, Back leaves the page, and Escape closes it. The play screen stays mounted under it.
- The Lenke «Alle rader og kostnad» sits on the Ordrefelt's label line in every state, phone only.
- The Totalkostnad pair is a button below 1024 px and plain text from 1024 px.
- «Vis som tabell» swaps the chart and the table in place and then reads «Vis som graf». The Landing's panel has the same button.
- Each bar shows its part's share of the Totalkostnad.
- The area chart's axis top is 50, 100, 200 or 500 × 10ⁿ kr, with ticks at 0, half and top.
- In Uke 1 the Netto lager column line is left out.
- In the stacked area, the backlog edge is drawn under the holding edge where the two meet.
- The Landing panel is 20 rem wide. It stands beside the figure from 1280 px and under it below that.
- Kost per uke steps 20 kr (Issue #126; the orchestrator's decision).
- Draft copy: `sumRowNote`, «Vis som graf», the table caption and the chart title. The Lager cost part stays «12 lager × 0,50» (the 6.15 draft), not the mockup's «12 på lager».

**Verification.**
- Backend: the full suite passed (2742 tests, 63–69 s); ruff check and format are clean. No migration: the JSON shape changed, and stored states upgrade on read.
- Frontend: `tsc`, Vitest (669 passed), `check:copy`, the colour lint and the Next build (compose image) all passed.
- Playwright: `cost-panel` plus every play-screen spec, `landing` and `homes` passed after the patches (155 tests). Two failures along the way were environmental:
  - `week-advance` (AI players) needs `worker-ai`, which the runbook's compose line does not start. It passed with `worker-ai` up.
  - `student-home` failed once under load and passed when run alone.
- New `cost-panel.spec.ts` tests take about 0.5–1.3 s each (axe at four widths). No fixed sleeps.

**Residual risks.**
- The pinned panel makes the laptop right column longer, which pushes Setestatus further down.
- On phone, the chart's only text alternative is the «Sum, kr» row, as EXPERIENCE.md specifies.
- Nobody has tested with Students whether an always-visible «Kostnad så langt» tempts overreaction (Issue #24).

Visible screens changed: the play screen (phone and laptop) and the Landing.
