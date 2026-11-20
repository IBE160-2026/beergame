---
title: "Story 6.9: See my link of the chain in the Kjedebånd"
type: 'feature'
created: '2026-11-20'
status: 'done'
baseline_revision: '771447525a9c58010d3210e41e63515e8c602fbf'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-6-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** The play screen (`/spill/{id}`) shows the Topplinje and Graf over tabell but not the Seat's own link of the chain, so a Student cannot see stock, orders, goods and what is on the way as one flow before ordering (FR-23, UX-DR14, UX-DR15, UX-DR73, mockups `05-spill.png`, `06-spilldynamikk.png` A).

**Approach:** A hand-made SVG Kjedebånd in `frontend/src/components/charts` (d3-scale/d3-shape only there), driven by a pure layout function that takes the Seat's `seat_state` numbers, a fixed width and font size, and returns marks and label positions. The play page measures the band's width and text size and renders it between the Topplinje and Graf over tabell, with one screen-reader sentence and the SVG hidden. No backend change; a backend-pinned fixture of every Uke of the Classic game for all four Roles drives the scale test.

## Boundaries & Constraints

**Always:**
- Draws only `seat_state` fields as returned (`incoming_order`, `incoming_delivery`, `shipped`, `inventory`, `backlog`, `supply_line`, `supply_line_slots`, `overdue`, `role`); pixel scale is the only arithmetic (AD-1, AD-10).
- Layout (DESIGN.md `chain-band`): upstream end label left, downstream right (`ink-muted`; Fabrikk's left end «Produksjon», Detaljist's right end «Kundene»); order line on top running left («Ordre inn 8» right of the node, «Din ordre» left, no number — the typed order is 6.11); goods line below running right («Levering 4» left of node, «Sendt 4» right); node = paper box with `axis` border, blue `lager` bar above the baseline and/or red `restordre` bar below, label «Lager 12» / «Restordre 13» (both when both > 0; «Lager 0» when both 0); arrows `ink` 1.1 px.
- På vei: each `supply_line_slots` entry is a box on the pipe left of the node, soonest nearest the node, width = quantity × pipe unit, `lager` 1 px border; label «På vei {supply_line}» under the pipe. `overdue` > 0: a dashed fixed-width box with two slashes, farthest left, its number written above it.
- Scale: pipe unit 1.4 px and stock unit 0.82 px are maxima; one factor k ≤ 1 for both, derived from band width so that a worst-case pipe of 80 units plus the overdue box fits; if a Uke still needs more, k shrinks further for that Uke. Never overflow.
- Labels whose spot is taken or out of bounds wrap into rows under the band; no two label boxes overlap (estimated with a conservative per-character width that Playwright holds to the real font).
- Screen reader: one sentence, e.g. «Ordre inn 8, Levering 4, Sendt 4, Restordre 13, På vei 16» (+ overdue clause); the SVG (with `<title>`) is inside `aria-hidden`. Not interactive, no focus stop.
- Reading/focus order: Topplinje, Kjedebånd, Graf over tabell, then the rest. Phone: chart gutter as the graph (16 px); laptop: left column, max ~28 rem wide.
- Component API leaves a slot for the four-Role variant (Story 9.5) — only the one-Seat variant is built.

**Never:** No typed-order box or «+ 24» preview (6.11); no neighbour numbers (6.21) or capacity UI (6.22); no Posisjon in the band; no number of Weeks or anything past nå + 4; no backend/api change; no edit of `sprint-status.yaml`; no reuse of `ChainDiagram` (Epic 5's settings diagram of all four Roles is a different figure).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Grossist Uke 11 at 360 px | engine fixture | «Distributør» left, «Detaljist» right, «Din ordre», «Ordre inn», «Levering», «Sendt», «Restordre N» red bar below, boxes for each slot, «På vei N» | — |
| Detaljist / Fabrikk | role retailer / factory | right end «Kundene» / left end «Produksjon» | — |
| Overdue > 0 | `overdue` 7 | dashed box with slashes, «7» above it; SR text names it | — |
| Both zero | inventory 0, backlog 0 | no bar, «Lager 0» | — |
| Huge numbers / 200 % text at 320 px | supply line 150, f = 26 | k shrinks, labels wrap under band, nothing overflows or overlaps | — |

</intent-contract>

## Code Map

- `frontend/src/components/charts/` -- only chart-library importer; `palette.ts` `colour()`/`CHART_FONT`; `net-graph.tsx` pattern (fixed width/fontSize props, `<title>`, `data-*` marks); `README.md` records chart types; `charts.test.tsx` style (renderToStaticMarkup).
- `frontend/src/modules/games/play-page.tsx:112` `Running` -- insert band above `WeekTable`; `Topplinje` :94 is the header; `game.seats` (Fabrikk first) gives neighbours; `roleName` from `modules/sessions/sessions.ts`.
- `frontend/src/components/graph-over-table.tsx:246` -- phone chart gutter negative-margin class to mirror.
- `frontend/src/copy/nb.ts:1478` `games.play` -- add `band` copy; `terms` :56 has Lager/Restordre/Ordre inn/Levering/Sendt/På vei; `sessions.chain.customers` «Kundene».
- `backend/app/engine/view.py:127` `SupplyLineSlot`, :197 `overdue`; `backend/app/modules/games/schemas.py:181` `SeatState` (has `inventory`, `backlog`, `supply_line` via `SeatView`).
- `backend/tests/games/test_play_fixture.py:24` `ORDERS`, :36 `wholesaler_in_week` -- generalise per Role; pin new fixture.
- `frontend/e2e/graph-over-table.spec.ts` -- viewport×week loop already runs `labelProblems` (all `svg[data-chart] text`), `textReadable`, axe; `frontend/e2e/support/graph.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/tests/games/test_play_fixture.py` -- `seat_in_week(role, week)`; test that `frontend/src/modules/games/fixtures/chain-band-classic.json` equals the band fields of every Role in Uke 1–30 of the fixture game; generate the file.
- `frontend/src/components/charts/chain-band.ts` -- pure `bandLayout(input, width, fontSize)` → scale k, node, boxes, overdue box, lines, labels (x, y, anchor, estimated width, wrapped), height; `textWidth` estimate.
- `frontend/src/components/charts/chain-band.tsx` -- `ChainBand` SVG (`data-chart="band"`, `<title>`, `data-mark`, `data-est` on texts); `variant` prop typed `"seat"` with comment for 9.5.
- `frontend/src/components/charts/chain-band.test.ts(x)` -- every Role × Uke of the fixture at 288 and 328 px, f 13 and 26: no overflow, no label overlap, boxes inside pipe; end labels per Role; overdue; zero; extremes; SR text.
- `frontend/src/modules/games/chain-band-view.tsx` -- client wrapper: measures width/font (ResizeObserver), SR sentence, neighbour labels from `game.seats`.
- `frontend/src/modules/games/play-page.tsx` -- render it first in `Running`.
- `frontend/src/copy/nb.ts` -- band copy (title, SR sentence parts, overdue clause, end labels) marked [ASSUMPTION] where draft.
- `frontend/src/components/charts/README.md` -- Kjedebånd row.
- `frontend/e2e/chain-band.spec.ts` -- Uke 11 at 360: labels, SR text, SVG hidden, DOM order Topplinje → band → graph region; estimate ≥ real width for every fixture label; 320/360/1440 axe via existing loop.

**Acceptance Criteria:**
- Given the play screen of a running game, when it renders at 320, 360 and 1440 px (and 200 % text), then the band shows only the Seat's own link as specified, no label overlaps another or leaves the SVG, no text < 13 px, and axe finds no violation.
- Given the fixture of every Uke for all four Roles, when laid out at 288 and 328 px (320/360 minus gutters), then nothing overflows and no labels overlap.
- Given a screen reader, then the band reads as one sentence and no SVG mark is exposed.
- Given the play screen, then reading order is Topplinje, Kjedebånd, Graf og tabell; on phone På vei is in the band and not a table row.

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 36 findings — high 0, medium 0, low 22, false 14, maybe-false 0
- findings:
  - `[false]` `[reject]` blind: På vei still a phone table row. `ROWS` marks `supplyLine` `laptopOnly` (`week-table.ts:54`); the e2e assertion runs and passes.
  - `[false]` `[reject]` blind: neighbours depend on API order. The Seats are Fabrikk first by contract (`games/schemas.py:441`, UX-DR73); `bandEnds` documents it.
  - `[low]` `[reject]` blind: a role missing from the Seats gets «Produksjon»/«Kundene». The Student's own Seat is always among the game's Seats; a guard adds a branch for an unreachable state.
  - `[false]` `[reject]` blind: the screen-reader sentence lacks neighbours and «Din ordre». The sentence is the AC's own example («Ordre inn 8, Levering 4, Sendt 4, Restordre 13, På vei 16»).
  - `[low]` `[patch]` blind: the 80-unit worst case is never exercised (fixture pipe peaks near 66). Added a Vitest case with 80 known units plus 40 overdue at 288/328 px and 13/26 px: same scale as an ordinary Uke, no overflow or overlap.
  - `[low]` `[reject]` blind: `forWidth` assumes four boxes. Longer delays only fall back to the per-Uke shrink, which never overflows; Classic has at most four slots.
  - `[low]` `[reject]` blind: right-side wrapped labels come out right to left. Only when several wrap (200 % text); keeping each label on its own side is the point; reordering adds logic for a cosmetic case.
  - `[low]` `[patch]` blind: overdue slashes touch the number above. Slashes now stand 1 px past the box (`chain-band.tsx`).
  - `[low]` `[reject]` blind: a label wider than the band is clipped. The longest label at 26 px (about 180 px) is far below the 288 px narrowest band.
  - `[low]` `[reject]` blind: inconsistent rounding of rect coordinates. Negligible; no visible effect in the screenshots.
  - `[low]` `[reject]` blind: layout shift and NaN font size. `min-h-[6em]` matches the unwrapped band; `getComputedStyle().fontSize` is always px.
  - `[low]` `[patch]` blind: 200 % text not rendered in the band e2e. Grouped with verification-gap: e2e at 320/360 px with 200 % text asserts `font-size="26"`, fit, estimate and label checks.
  - `[low]` `[reject]` blind: colour tests hard-code hex; no dark mode. Same pattern as the existing chart tests; the product has no dark theme.
  - `[low]` `[reject]` blind: zero-quantity slots draw no box. DESIGN draws arrivals at true scale; a 0 box has no width, and box position never encoded the Uke.
  - `[low]` `[patch]` blind: fixture regeneration undocumented. Comment added in `test_play_fixture.py`.
  - `[low]` `[patch]` blind: reflowed doc comment in `play-page.tsx` left a broken line; draft copy untracked. Comment reflowed; draft copy is tracked by the existing draft-copy issue (#31).
  - `[low]` `[reject]` intent: every Uke x Role is checked on the layout model, not rendered. Rendering 240 pages breaks the fast-test rule; the e2e test holds the model's width estimate to the real font for every fixture label, and browser checks run on Uker 3, 11 and 30.
  - `[false]` `[reject]` intent: the api is stubbed in e2e. Same as 6.6–6.8; the fixtures are pinned to the engine by the backend test.
  - `[low]` `[reject]` intent: «worst Uke» is a fixed 80 units, not the game's. Founder-level call in Design Notes; the game's future is hidden, so its worst Uke cannot be known at play time.
  - `[low]` `[reject]` intent: no test that only the Detaljist shows the customers' number. The number is `incoming_order`, the downstream Order for other Roles; the «Kundene» end per Role is tested.
  - `[false]` `[reject]` intent: arrivals not limited to four Uker. `seat_detail` only yields slots arriving within the order and goods delays (at most nå + 4 in Classic).
  - `[false]` `[reject]` intent: the order input is missing from the focus-order check. It does not exist until 6.11; the band holds no focus stop.
  - `[false]` `[reject]` intent: the På vei row behaviour pre-existed. Correct; the requirement is met and now asserted.
  - `[low]` `[reject]` intent: non-interactivity not tested beyond `aria-hidden`. The component has no handler or focusable element.
  - `[false]` `[reject]` intent: the four-Role slot is type-only. That is what the story asks (only the one-Seat variant is built).
  - `[false]` `[reject]` intent: additions beyond the story (overdue clause, «Lager 0», both bars). Draft copy marked [ASSUMPTION]; both bars anticipate 6.22 at no cost.
  - `[low]` `[reject]` edge: huge stock or backlog grows the band without limit. True scale is the design; the fixture's worst backlog (56) gives about 46 px; clipping needs a design decision.
  - `[false]` `[reject]` edge: a text-size change at the same width is not re-measured. The measured box has `min-h-[6em]`, so its height changes with the text size and the ResizeObserver fires.
  - `[low]` `[patch]` edge: the overdue number wraps at 26 px text (x < 0). Centred labels are now clamped into their room; Vitest case at 288 px / 26 px with overdue 56.
  - `[low]` `[reject]` edge: wrapped label wider than the band. As the blind row.
  - `[low]` `[reject]` edge: role not among the Seats. As the blind row.
  - `[false]` `[reject]` edge: a very narrow band overlaps the overdue box. The play page's narrowest band is 288 px; the overlap needs under 120 px.
  - `[low]` `[patch]` edge (claim): 200 % text not rendered. Same fix as the verification-gap row.
  - `[false]` `[reject]` edge (claim): the ResizeObserver misses text-size changes. As above.
  - `[low]` `[reject]` edge (claim): the per-Uke shrink also shrinks the bars that Uke. By design (one factor for pipe and stock, UX-DR15), and only beyond the worst case.
  - `[low]` `[patch]` verification-gap: nothing checks that the rendered band follows 200 % text. e2e added (font-size 26, fit, estimate, labels) at 320 and 360 px.

## Design Notes

Founder-level calls: scale is width-derived with a fixed worst-case of 80 pipe units (DESIGN's «56 + 13» plus room for the typed box), so bars keep one scale across Uker at a given width; a Uke beyond it shrinks only that Uke. Spine over mockup where they differ: both lines `ink` 1.1 px (mockup's goods line is slate 2 px). Overdue box placed apart at the far (upstream) end of the pipe, as it has no known date. Labels with no room wrap under the band but keep their side. Node centred in the band. Stock label weight 700 at caption size, as drawn.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/games/test_play_fixture.py -q` -- pass
- `cd frontend && npx vitest run src/components/charts src/modules/games` -- pass
- `cd frontend && npx playwright test e2e/chain-band.spec.ts e2e/graph-over-table.spec.ts e2e/week-table.spec.ts --workers=2` -- pass
- full: backend pytest; frontend typecheck, Vitest, check:copy, build, Playwright `--workers=2` -- pass

## Auto Run Result

Status: done

**Summary.** The play screen now shows the Seat's own link as the Kjedebånd between the Topplinje and Graf over tabell. `ChainBand` (hand-made SVG in `components/charts`, `data-chart="band"`, `<title>`) draws the upstream neighbour left (or «Produksjon»), the downstream right (or «Kundene»), the order line on top («Din ordre» without a number, «Ordre inn N»), the goods line below («Levering N», «Sendt N»), the node with a blue stock bar above and a red backlog bar below the baseline («Lager N» / «Restordre N»), the known arrivals as boxes at true scale (soonest next to the node, «På vei N») and overdue units as a fixed dashed box with two slashes and its number above. The pure `bandLayout` derives one factor for pipe (1.4) and stock (0.82) from the band width so 80 pipe units plus an overdue box fit, and shrinks only an unusual Uke further; labels with no room wrap under the band on their own side. Screen readers get one sentence; the SVG is `aria-hidden`. Only `seat_state` fields are drawn; no backend change.

**Files.**
- `frontend/src/components/charts/chain-band-layout.ts` (new) -- pure layout, scale, label placement, width estimate.
- `frontend/src/components/charts/chain-band.tsx` (new) -- the SVG; `variant` slot for Story 9.5.
- `frontend/src/components/charts/README.md`, `charts.test.tsx` -- chart-type row and scale notes; render tests.
- `frontend/src/modules/games/chain-band.ts` (new) and `chain-band.test.ts` (new) -- labels, ends, sentence; scale test over every Uke x Role at 288/328 px and 13/26 px.
- `frontend/src/modules/games/chain-band-view.tsx` (new), `play-page.tsx` -- measured client wrapper, first in the left column.
- `frontend/src/modules/games/fixtures/chain-band-classic.json` (new), `backend/tests/games/test_play_fixture.py` -- engine-pinned band fields for all four Roles, Uke 1–30.
- `frontend/src/copy/nb.ts` -- `games.play.band` copy ([ASSUMPTION] overdue clause and SVG title).
- `frontend/e2e/chain-band.spec.ts` (new) -- 320/360/1440 fit, labels, axe; 200 % text; content, sentence and order at Uke 11; width estimate held to the real font.

**Review.** One pass, four layers, 36 findings (high 0, medium 0, low 22, false 14). Patched (all low): 80-unit worst-case test, overdue slashes clear of the number, overdue number clamped at 200 % text, 200 % text e2e, fixture regeneration note, doc comment reflow. Deferred: none. Rejections with reasons in the triage log.

**Follow-up review:** false. No high or medium entry was patched (patched: 8 low rows in 6 entries).

**Founder-level decisions taken (no human in the loop).** Scale from the width with a fixed worst case of 80 pipe units (not the game's unknowable worst Uke); a Uke beyond it shrinks that Uke only. Both lines `ink` 1.1 px as DESIGN's text says (the mockup draws the goods line slate 2 px). Overdue box apart at the far upstream end of the pipe. Node centred. Wrapped labels keep their side. Stock label weight 700 at caption size, as drawn. «Lager 0» when neither stock nor backlog; both bars and labels when both are held. Screen-reader overdue clause «av dem N uten kjent uke» and the SVG title as draft copy [ASSUMPTION]. Band at most 28 rem wide on laptop. Epic 5's `ChainDiagram` not reused (a settings diagram of all four Roles, not one Seat's state). The scale product test runs on the layout model for all 120 Uke x Role states, with a browser test holding the width estimate to the real font, instead of rendering 240 pages (fast-test rule). Visual check by screenshots at 320, 360, 1440 px and 320 px with 200 % text in this run; the orchestrator runs its own. Implementation ran in the orchestrating agent's context (caller's runbook).

**Verification.**
- Backend: 2695 passed (87 s), ruff clean.
- Frontend: typecheck, Vitest 544 passed, `check:copy`, `lint:colours`, build (local and compose image).
- Playwright full `--workers=2`: 357 passed (6.2 min) before the review patches; after them `chain-band.spec.ts` and `graph-over-table.spec.ts` 29 passed. New tests about 0.6–1.2 s each (axe), no fixed sleeps.
- No migration.

**Residual risks.** At 320 px the downstream end label always wraps under the band (right-aligned); at 200 % text most labels wrap. Very large stock or backlog makes the band tall (true scale, no clipping). The typed-order box and «+ N» come with 6.11. Draft copy awaits the founder (#31).
