---
title: "Story 6.8: See the Landing's Demodata Seat as a graph over its table"
type: 'feature'
created: '2026-11-20'
status: 'done'
baseline_revision: 'a7c6857c2ee8637840e50cc1bba23f64b5c64497'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-6-context.md'
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Landing (Story 3.13) shows its Demodata Seat as a bare HTML week table (`modules/landing/seat-table.tsx`, invented numbers in `demo-seat.ts`). A visitor does not see the graph over the table that Students play on (UX-DR70, mockup `01-landing.png`).

**Approach:** The Landing renders the play screen's own `WeekTable` (Story 6.7: `GraphOverTable` + `components/charts`) over a Demodata `SeatState` of the Grossist in Uke 4, a Veiledet uke. That state is the engine's own (`frontend/src/modules/landing/demo-seat.json`, held to `wholesaler_in_week(4)` by the backend fixture test), so the figure needs no second chart and no hand-made numbers. Two small options on `WeekTable`: the Order already placed at nå (a Veiledet uke's fixed Order, shown as the number, not the empty dashed cell), and the table's accessible name.

## Boundaries & Constraints

**Always:**
- One chart implementation: the Landing imports `WeekTable` (no new SVG, scale or field code). The play screen's rendering is unchanged when the new options are absent.
- Demodata only: `demo-seat.json` holds `seat_state` and `guided_order` (the engine's `guided_order(GameSettings())`), nothing from `table_status` (no names, no other Seat). The backend test pins both to the engine.
- Figure: caption «Ett sete, Grossist, Uke 4. Veiledet uke.» above (names the table), Graf over tabell with columns Uke 1 … 8 (nå + 4, `future-tint`, «Nå» line), Din ordre at Uke 4 = «4» bold; under it «Studenten ser bare sine egne tall. Tidsaksen slutter fire uker etter nå.» and «Demodata» (`caption`, `ink-muted`), then the existing «Lagerkurvene …» line.
- Hidden information (UX-DR71): no week count, no column past nå + 4, no customers, no other Seat; `npm run check:copy` passes on the `landing` section.
- On laptop the week columns are wider than the play screen's (the figure has eight columns, not thirty), via an option on `WeekTable`; marks still measured from `th[scope=col]`.
- The 6.7 alignment/label/readability checks move to `frontend/e2e/support/graph.ts` and are used by both `graph-over-table.spec.ts` and `landing.spec.ts`.

**Never:** No Kjedebånd or «Kostnad så langt» panel (6.9/6.16), no order-to-arrival line or preview of the Uke 8 arrival (6.11), no Ordrefelt; no api call from the Landing; no change to `sprint-status.yaml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Landing, phone 320/360 | engine Grossist Uke 4 | Uke 1–8, lines 1–4, «Lager 12», «Posisjon 24», bars 1–4, arrivals 4 in Uke 5–7 framed, Din ordre 4 at Uke 4; no page scroll | — |
| Landing, 1440 px | same | same columns, wider; Sendt/På vei rows shown | — |
| Play screen | `nowOrder` absent | Din ordre at nå stays the empty dashed cell | — |

</intent-contract>

## Code Map

- `frontend/src/modules/landing/{landing-page.tsx,seat-table.tsx,demo-seat.ts,demo-seat.test.ts}` -- 3.13's Landing; `SeatTable`/`DEMO_ROWS` are replaced by the Demodata `SeatState` through `WeekTable`.
- `frontend/src/modules/games/week-table-view.tsx:161` `WeekTable({state, fixed})` -- add `nowOrder?`, `labelledBy?`, `wide?`; `WEEK_COL` :36 column width.
- `frontend/src/modules/games/week-table.ts:155` `cellFor` -- nå's `order` row returns `order-empty`; take the placed Order when given.
- `frontend/src/components/graph-over-table.tsx:257` -- the `<table>`; pass `aria-labelledby`.
- `backend/tests/games/test_play_fixture.py` -- `wholesaler_in_week`; add the Landing fixture check (+ `guided_order`).
- `frontend/src/copy/nb.ts:147` `landing.seat` -- `ownNumbers` gets the mockup's time-axis sentence; `week`/`yourOrder` go if unused.
- `frontend/e2e/graph-over-table.spec.ts:65-149` `alignment`, `labelProblems`, `textReadable` -- move to `e2e/support/graph.ts`.
- `frontend/e2e/landing.spec.ts:57` -- rewrite the Seat assertions for the new figure.

## Tasks & Acceptance

**Execution:**
- `backend/tests/games/test_play_fixture.py` -- test that `frontend/src/modules/landing/demo-seat.json` equals `{"seat_state": wholesaler_in_week(4), "guided_order": guided_order(GameSettings())}`; generate the file from it.
- `frontend/src/modules/games/week-table.ts` (+ test) -- `cellFor(state,row,week,nowOrder?)`: nå's order is `plain` when `nowOrder` is given.
- `frontend/src/modules/games/week-table-view.tsx` -- options `nowOrder`, `labelledBy`, `wide`.
- `frontend/src/components/graph-over-table.tsx` -- `labelledBy` → table `aria-labelledby`.
- `frontend/src/modules/landing/*` -- `demo-seat.ts` exports the typed Demodata; delete `seat-table.tsx`; new `seat-figure.tsx`; content-rule tests on the JSON.
- `frontend/src/copy/nb.ts` -- landing copy.
- `frontend/e2e/support/graph.ts`, `graph-over-table.spec.ts`, `landing.spec.ts` -- shared checks; Landing figure at 320/360/1440 (+400 % zoom kept for axe/scroll).

**Acceptance Criteria:**
- Given the Landing at 320, 360 and 1440 px, when it renders, then every Netto lager vertex, Posisjon marker and cost bar is within 1 px of its `th[scope=col]` centre, the now-line at Uke 4's right edge, lines drawn for Uke 1–4 only, no label overlap, no text < 13 px, no clipped cell, no page-level horizontal scroll and no axe violation.
- Given the Landing, then the table named «Ett sete, Grossist, Uke 4. Veiledet uke.» has column headers Uke 1–8 and Din ordre «4» at Uke 4, every chart SVG is inside `aria-hidden`, «Demodata» shows in `ink-muted`, and no text names another Role's Seat or a customer.
- Given the play screen, then 6.7's e2e checks still pass with the shared helpers.
- Given Vitest, then `cellFor` with and without `nowOrder` and the Demodata content rules (Uke 4, Grossist, no rising Ordre inn, orders 4, stock ≥ 0) pass.

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 32 findings — high 0, medium 0, low 22, false 10, maybe-false 0
- findings:
  - `[low]` `[reject]` blind: Din ordre «4» at nå is not counted in Posisjon/På vei and has no Uke 8 arrival. The nå column shows the start-of-Week state, as the play screen does; the arrival of the Order typed at nå is 6.11's preview (spec Never). A visitor reads the same table a Student does.
  - `[low]` `[patch]` blind: nå's placed Order is styled like any past cell; new props untested beyond `cellFor`. New cell kind `order-placed` drawn bold; unit test and e2e (`font-weight` 700) added. (Grouped with the two edge rows on bold.)
  - `[low]` `[patch]` blind: the note and «Demodata» are a plain `<p>`, not tied to the figure. Now the figure's `<figcaption>`. (Grouped with edge.)
  - `[low]` `[patch]` blind: `demo-seat.ts` says «no Week beyond nå in the data» while the data holds arrivals in Uke 5–7. Comment corrected (no played Week beyond nå; arrivals never past nå + 4, as the test checks). (Grouped with edge claim.)
  - `[low]` `[reject]` blind: `as SeatState` cast on the JSON import. A JSON import types `role` as `string`, so `satisfies` cannot hold; the shape is pinned by the backend test against the engine and `SeatState`, as the play-week fixtures are.
  - `[low]` `[reject]` blind: no regeneration command for the fixture. Same as the existing play-week fixtures; the failing test prints the difference and `landing_demo_seat()` is the generator.
  - `[false]` `[reject]` blind: the Python test may lack imports. `json`, `Path`, `GameSettings`, `guided_order`, `SeatState` are imported at the top; the test ran and passed.
  - `[low]` `[patch]` blind: nothing asserts Uke 4 is still a Veiledet uke. Added `assert 4 <= GameSettings().guided_weeks`.
  - `[low]` `[reject]` blind: «fire uker» repeats the nå + 4 constant. The horizon is a spine rule (UX-DR71), not a tunable; the copy is draft for the founder.
  - `[low]` `[patch]` blind: the hidden-information check read `innerText` only. Now `textContent` of `main` (screen-reader text and SVG titles included).
  - `[low]` `[patch]` blind: the Landing e2e lost its row checks. Row headers asserted per layout (Sendt/På vei on laptop only). (Grouped with verification-gap other finding.)
  - `[low]` `[reject]` blind: the Landing gains the focusable «Graf og tabell» region. It is the shared component's keyboard scroll (NFR-6); axe passes; one tab stop.
  - `[false]` `[reject]` blind: removed copy keys may still be used. Typecheck passes over `src` and `e2e`; nothing references them.
  - `[low]` `[reject]` blind: `alignment()` gives `worst = -Infinity` with no marks. Both specs assert the Uker drawn, so an empty graph fails.
  - `[low]` `[patch]` edge: nå's Order not bold. Same fix as above.
  - `[low]` `[patch]` edge: note not a figcaption. Same fix as above.
  - `[low]` `[reject]` edge: unchecked cast. As the blind row.
  - `[low]` `[reject]` edge: fixed `CAPTION_ID` duplicates with a second figure. The Landing renders one; `useId` would make the server component a client one for an unreachable case.
  - `[low]` `[patch]` edge (claim): spec says «4» bold, code not. Same fix as above.
  - `[low]` `[patch]` edge (claim): «no Week beyond nå» comment. Same fix as above.
  - `[false]` `[reject]` edge (claim): `preview.order_arrival_week` 8 ships in the JSON. It is not rendered; the Never is about display, and the field is part of the engine's `seat_state` the test pins.
  - `[false]` `[reject]` intent A2: the 3.13 table's rows changed. The story's own user line («the same graph over a table that Students play on») selects the play screen's table; recorded as a founder-level call.
  - `[false]` `[reject]` intent B1: the data is no longer 3.13's fixture. Its numbers are the same (4/4/12/12, Order 4); they now come from the engine.
  - `[low]` `[patch]` intent C2: no test for week counts on the Landing. The e2e now fails on «uker spilt» or «N uker» anywhere in `main`.
  - `[false]` `[reject]` intent: «4» at nå reads as a recommended Order. It is the fixed Order the game places in a Veiledet uke (EXPERIENCE.md: «The landing shows this state»); no reference Order is involved.
  - `[false]` `[reject]` intent: copy and caption semantics beyond the story. The time-axis sentence is the mockup's own; the caption change keeps the table named by it (e2e locates the table by that name).
  - `[false]` `[reject]` intent: `wide` makes the figure geometrically different. Same component and marks; the AC's alignment check passes.
  - `[false]` `[reject]` intent: the extra 400 % zoom viewport. Not a defect; it was already in 3.13's test.
  - `[false]` `[reject]` intent: shared play-screen code only tested via `cellFor`. The full play-screen e2e (6.6/6.7 specs) ran with the props absent and passed.
  - `[low]` `[patch]` verification-gap: `wide` untested. 1440 px asserts a week column ≥ 5 em.
  - `[low]` `[patch]` verification-gap other: Landing row labels unchecked. Same fix as the blind row (row headers per layout).
  - `[low]` `[patch]` verification-gap other: bold unchecked. Same fix as the bold row (e2e `font-weight` 700).

## Design Notes

Founder-level calls taken: engine-pinned Demodata replaces 3.13's invented numbers (they agree: 4/4/12/12, plus Posisjon 24 and Kost 6); the Landing shows the play table's rows (adds Posisjon, Kost, laptop-only Sendt/På vei) because "the same graph over a table that Students play on" wins over 3.13's five rows; columns to nå + 4 as the play screen; the time-axis sentence from the mockup restored; wider laptop columns on the Landing.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/games/test_play_fixture.py -q` -- pass
- `cd frontend && npx vitest run src/modules/landing src/modules/games src/components` -- pass
- `cd frontend && npx playwright test e2e/landing.spec.ts e2e/graph-over-table.spec.ts --workers=2` -- pass
- full: backend pytest; frontend typecheck, Vitest, check:copy, build, Playwright `--workers=2` -- pass

## Auto Run Result

Status: done

**Summary.** The Landing's Seat figure is now the play screen's own Graf over tabell: `SeatFigure` renders `WeekTable` (Story 6.7's `GraphOverTable` and `components/charts`, no chart code of its own) over a Demodata Grossist in Uke 4, a Veiledet uke. The data is the engine's own state (`frontend/src/modules/landing/demo-seat.json`, only `seat_state` and the guided Order, pinned to `wholesaler_in_week(4)` and `guided_order` by the backend fixture test); its numbers equal 3.13's invented ones (4/4/12/12, Order 4). The figure shows Uke 1–8 (nå + 4, `future-tint`, «Nå» line), the Netto lager/Posisjon graph («Lager 12», «Posisjon 24»), Kost per uke, the known arrivals in Uke 5–7, and Din ordre «4» bold at Uke 4; the caption «Ett sete, Grossist, Uke 4. Veiledet uke.» names the table; the figcaption reads «Studenten ser bare sine egne tall. Tidsaksen slutter fire uker etter nå.» and «Demodata». `WeekTable` gained three options (`nowOrder`, `labelledBy`, `wide`); the play screen passes none and is unchanged.

**Files.**
- `backend/tests/games/test_play_fixture.py` -- pins the Landing's Demodata to the engine (and Uke 4 to the Guided Weeks).
- `frontend/src/modules/landing/demo-seat.json` (new), `demo-seat.ts`, `demo-seat.test.ts` -- engine Demodata and its content rules.
- `frontend/src/modules/landing/seat-figure.tsx` (new), `landing-page.tsx`; `seat-table.tsx` deleted -- the figure.
- `frontend/src/modules/games/week-table.ts` (+ test), `week-table-view.tsx` -- `order-placed` cell, `nowOrder`/`labelledBy`/`wide`.
- `frontend/src/components/graph-over-table.tsx` -- `labelledBy` on the table.
- `frontend/src/copy/nb.ts` -- note with the time-axis sentence [ASSUMPTION]; unused `week`/`yourOrder` removed.
- `frontend/e2e/support/graph.ts` (new), `graph-over-table.spec.ts`, `landing.spec.ts` -- 6.7's checks shared; Landing figure checks.

**Review.** One pass, four layers, 32 findings (high 0, medium 0, low 22, false 10). Patched (all low): nå's placed Order bold (`order-placed`), note as `<figcaption>`, content-rule comment, Uke 4 guided assertion, `textContent`-based hidden-information check plus a week-count check, row headers per layout, 1440 px column width ≥ 5 em. Deferred: none. Rejections with reasons in the triage log.

**Follow-up review:** false. No high or medium entry was patched (patched: 10 low rows in 8 entries).

**Founder-level decisions taken (no human in the loop).** The Landing shows the play screen's table (adds Posisjon, Kost, laptop-only Sendt/På vei; columns to nå + 4) rather than 3.13's five rows to Uke 4, read from the story's «the same graph over a table that Students play on»; engine-pinned Demodata instead of hand-written numbers; Din ordre at nå shows the guided Order 4 in bold (not the empty dashed cell); no Uke 8 arrival preview (6.11); the mockup's sentence «Tidsaksen slutter fire uker etter nå.» restored as draft copy [ASSUMPTION]; week columns widened to 5 em from 1024 px on the Landing only; caption as a labelled `<p>` and the note as `<figcaption>`. The visual check of the change was done by screenshots at 360 and 1440 px in this run; the orchestrator runs its own. Implementation ran in the orchestrating agent's context (caller's runbook).

**Verification.**
- Backend: 2694 passed (81 s), ruff clean.
- Frontend: typecheck, Vitest 525 passed, `check:copy`, build (local and compose image).
- Playwright full `--workers=2`: 349 passed before the review patches; after them 348 passed and 1 timed out (`admin-invite.spec.ts` mail test, `locator.fill` timeout under load, unrelated), which passed on rerun (8/8). Landing tests ≈ 1.1–1.2 s each (axe + graph checks), no fixed sleeps.
- No migration.

**Residual risks.** At 320 px the eight phone columns are narrow and the three framed arrivals sit close together (as on the play screen). The figure has no Kjedebånd or «Kostnad så langt» panel yet (6.9, 6.16). Draft copy awaits the founder (#31).
