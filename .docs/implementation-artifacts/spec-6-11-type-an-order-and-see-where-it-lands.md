---
title: "Story 6.11: Type an Order and see where it lands"
type: 'feature'
created: '2026-11-20'
status: 'done'
baseline_revision: 'e6da17b394fea83bbd4ca754fc482f9ad007725c'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-6-context.md'
warnings: ['multiple-goals', 'oversized']
deferred:
  - summary: >-
      No test shows the typed text and its preview clear when the play envelope moves to a new Uke.
    evidence: |-
      play-page.tsx Running keys the typed text by game and Uke; every play e2e serves one fixed envelope and never advances the Uke, so dropping the key check would pass. Story 6.12 (send + drafts.ts) makes the advance after an own Order the main path: add an e2e there that types, swaps the play route to a later-Uke envelope, and asserts an empty field with no typed box, join line or typed cell.
    location: >-
      frontend/src/modules/games/play-page.tsx Running
    severity: low
---

<intent-contract>

## Intent

**Problem:** After the Guided Weeks the play screen has no way to type an Order, so a Student cannot see where a number would land before confirming (FR-24, UX-DR14, UX-DR17, UX-DR20, AD-10). Also the Guided Weeks' read-only Ordrefelt shows a text cursor, so it looks editable (Issue #128).

**Approach:** The Ordrefelt gains its editable states (empty, typed, invalid, out of range) with − / + segments and a «Bekreft ordre» button that does nothing yet. A valid typed value is previewed through one pure function in `frontend/src/lib/preview.ts` (from `seat_state.preview` only) into the week table (Din ordre at nå, Levering at the arrival Uke, a thin line between them) and the Kjedebånd (a new box with a 1.5 px `ink` border, «På vei 16 + 24», «Din ordre 24»). The read-only state gets `cursor: default`.

## Boundaries & Constraints

**Always:**
- Editable only when `turn.guided` is false and `turn.order` is null. Label «Din ordre for Uke {n}»; field `type="text" inputmode="numeric" pattern="[0-9]*"` with placeholder «Antall enheter»; help «Hele tall fra 0 til {maks}.» always shown and in `aria-describedby`; {maks} is `seat_state.max_order`.
- Empty: «Sist Uke bestilte du {n}.» from the last `history` row's `order` (none in Uke 1); button «Bekreft ordre» with `aria-disabled`, focusable; a press shows «Skriv et helt tall fra 0 til {maks}.».
- Valid = only digits and ≤ max (0 valid). Letters, decimals, minus, spaces → «Skriv et helt tall fra 0 til {maks}.»; > max → «{n} er mer enn {maks}. Skriv et helt tall fra 0 til {maks}.». Invalid shows the reason under the help line in `restordre` at once with a 1.4 px `restordre` border and `aria-invalid="true"`; the reason is announced through a `role="alert"` region only on blur or a button press, never per keystroke.
- − «Én færre», + «Én flere»: step 1, announce the new value politely; − unavailable when empty or 0, + gives 1 on empty and is unavailable at max; unavailable = `aria-disabled="true"`, keeps focus, press does nothing. Both unavailable while the text is not digits; − on a too-large value gives max.
- Valid value x: button primary «Bekreft ordre på x», the line «Kommer fram om lag Uke {arrival}. Kan ikke endres etter at du har bekreftet.» above it; a press does nothing (Story 6.12). Enter in the field moves focus to the button and sends nothing.
- Valid value x previews: Din ordre at nå is the `ink` block with x; the Levering cell of `preview.order_arrival_week` (if it is a column) shows x in a 1.5 px `ink` box, joined to Din ordre by a thin `ink` line; the Kjedebånd adds x as the last box on the pipe with a 1.5 px `ink` border, reads «Din ordre x» and «På vei {supply_line_base} + x», and its screen-reader sentence ends «På vei {base} pluss x». Posisjon, Netto lager, cost and Totalkostnad do not change.
- `preview.ts` is the only client arithmetic: it reads only `seat_state.preview` and the typed x, hard-codes no delay, and Vitest checks it against engine values for golden-trace games held by a backend fixture test.
- Field and button fill the width on phone; field at `order-input-height`, button at `control-height-phone`; every tap target ≥ 44 px. New copy is draft in `nb.ts` unless the spine gives it.

**Never:** No sending, `drafts.ts`, «Sender…»/confirmed/failed states (6.12–6.13); no «Alle rader og kostnad» link or screen; no Setestatus (6.14); no recommended or prefilled order (UX-DR78); no backend or api change; no `type="number"`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Empty | Uke 11, nothing typed | placeholder, «Sist Uke bestilte du 8.», «Bekreft ordre» aria-disabled, − aria-disabled | press → reason shown and announced |
| Valid | «24» | «Bekreft ordre på 24», «Kommer fram om lag Uke 15 …», table 24 at nå and Uke 15, band «På vei 16 + 24» | — |
| Zero | «0» | valid, «Bekreft ordre på 0», no band box | — |
| Letters / decimal / minus / space | «2a», «2,5», «-1», «2 4» | reason «Skriv et helt tall …», aria-invalid, no preview | announced on blur |
| Too large | «1000» (max 999) | «1000 er mer enn 999. Skriv …» | announced on blur |
| − / + | empty → + | 1; at 999 + aria-disabled; at 0 − aria-disabled | press at limit does nothing |
| Enter | Enter in field | focus on button, nothing sent | — |
| Guided Week | `turn.guided` | read-only field as 6.10 with `cursor: default` | — |

</intent-contract>

## Code Map

- `frontend/src/modules/games/order-field.tsx` -- Ordrefelt; today only the guided state (input classes need `cursor-default`); extend with editable states, controlled `text`/`onText` from `Running`.
- `frontend/src/modules/games/play-page.tsx:116` `Running` -- owns the typed text (reset per Uke), computes the preview once and passes it to `ChainBandView`, `WeekTable`, `OrderField`.
- `frontend/src/components/button.tsx` -- `Button` with `unavailable` (aria-disabled, ignores presses); `guardUnavailable` for the segments.
- `frontend/src/modules/games/week-table.ts:158` `cellFor(state,row,week,nowOrder)` -- add a typed preview: Din ordre at nå (`order-placed` look) and an `arrival-typed` cell at the arrival Uke; `week-table-view.tsx:164` `WeekTable` (props `nowOrder`), `WeekCell` :245.
- `frontend/src/components/graph-over-table.tsx` -- add an optional join line: measure two marked elements (`data-join="from"|"to"`) in the wrapper and draw a thin `ink` SVG line, re-measured when the join key changes.
- `frontend/src/components/charts/chain-band-layout.ts:146` `bandLayout` -- add optional `typed` quantity: one more box after the known ones (counted in the scale), returned separately; `chain-band.tsx` draws it with a 1.5 px `ink` stroke.
- `frontend/src/modules/games/chain-band.ts` `bandLabels`/`bandSentence` -- optional typed x for «Din ordre x», «På vei b + x», «… pluss x»; `chain-band-view.tsx` passes it.
- `frontend/src/lib/preview.ts` (new) -- `orderPreview(coefficients, x)` → `{ arrivalWeek, supplyLineBase, supplyLine, position }`; `parseOrder(text, max)` can live in `order-field` module (`order-input.ts`).
- `frontend/src/copy/nb.ts:1485` `games.play.order`, `table`, `band` -- new strings.
- `backend/tests/games/test_play_fixture.py` -- pattern for engine-held fixtures (`_game_until`, `build_seat_state`); golden traces in `backend/tests/engine/golden/*.json` (`settings`, `orders`).
- `frontend/e2e/guided-week.spec.ts` `openPlay` -- stub pattern for the new e2e; `e2e/support/classes.ts` `expectAccessible`.
- Read-only users of shared pieces: `src/modules/landing/seat-figure.tsx` and `src/app/print/graf-over-tabell/page.tsx` (WeekTable) must render unchanged.

## Tasks & Acceptance

**Execution:**
- `frontend/src/lib/preview.ts` + `preview.test.ts` -- the preview function; Vitest against `fixtures/preview-golden.json`: for each Seat-Week, the next Week's `supply_line + incoming_delivery` equals `supplyLine`, `position + incoming_order` equals `position`, and a slot of quantity x arrives at `arrivalWeek`.
- `backend/tests/games/test_play_fixture.py` -- `preview_golden()` from `classic-step-pass-through` and `delays-3-3-3-backlog` traces (per Role and Week: `preview`, the Order placed, next Week's `supply_line`, `incoming_delivery`, `position`, `incoming_order`, `supply_line_slots`); test the stored fixture equals it.
- `frontend/src/modules/games/order-input.ts` + test -- `parseOrder`, step rules.
- `frontend/src/modules/games/order-field.tsx` + test -- editable states, a11y wiring, `cursor-default` in read-only.
- `week-table.ts`, `week-table-view.tsx`, `graph-over-table.tsx` + tests -- typed cells and the join line.
- `chain-band-layout.ts`, `chain-band.tsx`, `chain-band.ts`, `chain-band-view.tsx` + tests -- typed box and labels.
- `play-page.tsx`, `nb.ts` -- wire state and copy.
- `frontend/e2e/order-field.spec.ts` (new) -- Uke 11 stub at 320/360/1440: empty, typed 24, invalid «2a», out of range; preview cells, line, band labels, button labels, Enter focus, −/+ limits, no request sent on press; axe; widths/heights; guided field `cursor: default` (extend `guided-week.spec.ts`).

**Acceptance Criteria:**
- Given Uke 11 with no Order, when the Student types 24, then Din ordre at nå and Levering at Uke 15 show 24 joined by a line, the Kjedebånd shows «Din ordre 24» and «På vei 16 + 24» with the new box, the button reads «Bekreft ordre på 24» under «Kommer fram om lag Uke 15. …», and Posisjon at nå is unchanged.
- Given the empty, typed, invalid and out-of-range states at 320, 360 and 1440 px, when axe runs, then there is no violation, field and button fill the width on phone, and every tap target is ≥ 44 px.
- Given a Guided Week, when the pointer is over the read-only field, then the cursor is `default`.

## Spec Change Log

## Review Triage Log

### 2026-11-20 — Review pass
- verdicts: 33 findings — high 0, medium 0, low 23, false 10, maybe-false 0
- findings:
  - `[false]` `[reject]` blind: «Kommer fram om lag Uke N» can name an Uke after the game's end — Students must play as if the business continues (FR-14); the engine's arrival week is the honest answer and the end is hidden.
  - `[low]` `[patch]` blind: `Editable` keeps `pressedEmpty`, the alert and the step announcement into the next Uke — `OrderField` now renders `<Editable key={week}>`.
  - `[low]` `[reject]` blind: the band sentence does not name the 24 as the own Order, and with overdue units reads «…uten kjent uke, pluss 24» — the AC fixes the ending «På vei 16 pluss 24»; the visible band and the table's text name it as Din ordre.
  - `[false]` `[reject]` blind: a typed 0 writes «Din ordre 0» and «På vei 16 + 0» with no box — 0 is a valid Order (AC); the labels state it, a 0-unit box has no width.
  - `[low]` `[reject]` blind: a large typed value rescales the band while typing — DESIGN.md: a Uke that needs more pipe is drawn smaller for that Uke only; true scale is the rule.
  - `[low]` `[reject]` blind: the table key does not describe the typed box — its sr text says «din ordre, ikke bekreftet»; extra key copy is founder copy work.
  - `[low]` `[reject]` blind: the join line is re-measured only on key change and resize, geometry tested at 360 px only — the ResizeObserver on the table catches font loads and layout changes; the line's presence is tested at all three widths.
  - `[low]` `[patch]` blind: no test of the play page wiring (first free Uke line, Uke reset) — `lastOrder(history)` moved to `order-input.ts` and tested, including the first free Uke (fixed Order 4); the Uke reset is deferred (see the verification-gap row).
  - `[low]` `[patch]` blind: the golden check would pass on any slot of the same quantity and Uke — it now also requires `stage: "ordered"`.
  - `[false]` `[reject]` blind: `supplyLine` and `position` are computed but unused — AD-10 puts the preview arithmetic in `preview.ts`, tested against golden traces, as the AC asks; Posisjon must not change while typing (EXPERIENCE.md), so it is not shown.
  - `[low]` `[reject]` blind: a placed non-guided Order shows read-only with no reason — reachable only after a switch to a rule-based player; its copy is the Confirmed state of Story 6.12.
  - `[false]` `[reject]` blind: a valid press does nothing — the AC says so («Story 6.12 gives the button its action»).
  - `[false]` `[reject]` blind: pasted values with spaces are rejected — the AC lists spaces as invalid.
  - `[false]` `[reject]` blind: the error is announced on every blur — the AC asks for the announcement when the Student leaves the field.
  - `[low]` `[reject]` blind: e2e matches «Bekreft» literally; the join line strokes `var(--color-ink)` — a token, not a literal; test literals are the spine's copy.
  - `[low]` `[patch]` edge: arrival past nå + 4 (3/3/3 delays) has no Levering cell and no line — the spec allows it («if it is a column»; the arrival line still names the Uke); a `cellFor` test now covers it (grouped with the verification-gap row).
  - `[low]` `[patch]` edge: `measureJoin` with no `to` element — same group; the guard already draws nothing, the new test covers the cells.
  - `[low]` `[reject]` edge: a typed 999 shrinks the shared scale — as the blind row on rescaling.
  - `[low]` `[patch]` edge: `Editable` state carries into the next Uke — same fix as the blind row (`key={week}`).
  - `[false]` `[reject]` edge: band shows «+ 0» with no box — as the blind row on 0.
  - `[low]` `[patch]` edge: the typed text is keyed by Uke only, so another game in the same Uke would inherit it — the state now holds the game id too.
  - `[low]` `[reject]` edge: the per-width e2e types «2,5», not «2a» — «2a» is covered by Vitest and the keyboard e2e; both are the same invalid state.
  - `[low]` `[defer]` verification-gap: no test shows the typed text clears when the Uke changes — filed disposition defer to Story 6.12, which makes the advance after an own Order the main path; recorded in `deferred`.
  - `[low]` `[patch]` verification-gap: no test for an arrival after the last column — `week-table.test.tsx` adds an arrival in Uke 17: nå shows the typed Order, no column holds `arrival-typed`.
  - `[low]` `[patch]` intent: Issue #128 could mean the insertion caret too — the read-only field now also has `caret-transparent`; e2e asserts a transparent `caret-color` and `cursor: default`.
  - `[false]` `[reject]` intent: the golden test checks sums nothing renders — the AC makes `preview.ts` the tested arithmetic; the rendered parts are pass-through fields checked in Playwright.
  - `[low]` `[patch]` intent: the first free Uke's «Sist Uke bestilte du 4.» is untested — `lastOrder` test above.
  - `[false]` `[reject]` intent: «Kostnad så langt» never appears — it is Story 6.16; the e2e holds Totalkostnad unchanged.
  - `[low]` `[reject]` intent: UX-DR78 checked only by an empty value — no surface has a source for a suggested number; the envelope carries none.
  - `[false]` `[reject]` intent: `max_order` API path not exercised — the stand-in envelope is held to the engine by `test_play_fixture.py`; `max_order` is an existing envelope field.
  - `[low]` `[patch]` intent: tap targets ≥ 44 px checked only on phone — the per-width e2e now measures the three field controls at 320, 360 and 1440 px.
  - `[low]` `[reject]` intent: `restordre` border colour checked only out of range — Vitest checks the class for every invalid input.
  - `[low]` `[reject]` intent: the placed read-only state is beyond the story's Given — it keeps a Seat with an Order (rule-based switch) from showing an editable field; no copy added.

## Design Notes

Founder-level calls taken here: the − segment on a too-large value gives max, and both segments are unavailable while the text holds a non-digit; «Sist Uke bestilte du n.» shows only while the field is empty; the polite step announcement is «{n} enheter» [ASSUMPTION]; screen readers read the typed cells as «24, din ordre, ikke bekreftet» [ASSUMPTION]; a placed non-guided Order (possible only through a switch to a rule-based player) shows the read-only field without the Veiledet uke line. The 6.10 orchestrator note put «the thin line» in 6.12; this story's AC asks for it with the typed value, so it is built here and 6.12 keeps it after confirming.

## Verification

**Commands:**
- `cd frontend && npx vitest run src/lib/preview.test.ts src/modules/games src/components` -- pass
- `cd backend && uv run pytest -n0 tests/games/test_play_fixture.py -q` -- pass
- `cd frontend && npx playwright test e2e/order-field.spec.ts e2e/guided-week.spec.ts --workers=2` -- pass
- full: backend pytest; frontend typecheck, Vitest, check:copy, build, Playwright `--workers=2` -- pass

## Auto Run Result

Status: done

**Summary.** After the Guided Weeks the Ordrefelt is editable: «Din ordre for Uke 11», a `type="text" inputmode="numeric" pattern="[0-9]*"` field with «Antall enheter», the help «Hele tall fra 0 til 999.» (from `seat_state.max_order`, in `aria-describedby`), «Sist Uke bestilte du 8.» while empty, the − / + segments «Én færre» / «Én flere» (`aria-disabled` at their limits, focus kept, steps announced politely), the reasons «Skriv et helt tall fra 0 til 999.» and «1 000 er mer enn 999. …» with a `restordre` border and `aria-invalid`, announced through `role="alert"` on leaving the field or pressing the button, and «Bekreft ordre» / «Bekreft ordre på 24» (no action yet) under «Kommer fram om lag Uke 15. Kan ikke endres etter at du har bekreftet.». Enter moves focus to the button. A valid value is previewed through `lib/preview.ts` (the only client arithmetic, held to two golden-trace games): Din ordre at nå as the `ink` block, the Levering cell of the arrival Uke in a 1.5 px `ink` box, a thin line between them, and in the Kjedebånd a new last box with a 1.5 px `ink` border, «Din ordre 24», «På vei 16 + 24» and the sentence ending «På vei 16 pluss 24». Posisjon, cost and Totalkostnad do not move. Issue #128: the read-only Guided field has `cursor: default` and no caret.

**Files.**
- `frontend/src/lib/preview.ts` (new), `preview.test.ts` (new); `backend/tests/games/test_play_fixture.py` + `frontend/src/modules/games/fixtures/preview-golden.json` (new) -- the preview and its engine-held check.
- `frontend/src/modules/games/order-input.ts` (new) -- parse, reasons, − / + rules, last Uke's Order.
- `frontend/src/modules/games/order-field.tsx`, `order-field.test.tsx` -- editable states; read-only without text cursor or caret.
- `frontend/src/modules/games/week-table.ts`, `week-table-view.tsx`, `week-table.test.tsx`; `frontend/src/components/graph-over-table.tsx` -- typed cells and the join line (`joinKey`).
- `frontend/src/components/charts/chain-band-layout.ts`, `chain-band.tsx`; `frontend/src/modules/games/chain-band.ts`, `chain-band-view.tsx`, `chain-band.test.ts` -- typed box and labels.
- `frontend/src/modules/games/play-page.tsx`, `frontend/src/copy/nb.ts` -- wiring and copy.
- `frontend/e2e/order-field.spec.ts` (new), `frontend/e2e/guided-week.spec.ts` -- states, preview, keyboard, axe at 320/360/1440; cursor and caret.

**Review.** One pass, four layers, 33 findings (high 0, medium 0, low 23, false 10). Patched (all low): `Editable` remounts per Uke; typed text keyed by game and Uke; `caret-transparent`; tests for the first free Uke line, an arrival past the last column, `stage: "ordered"`, and tap targets at all widths. Deferred: one (Uke-reset e2e, to Story 6.12). Rejections with reasons in the triage log.

**Follow-up review:** false. Patched entries: 0 high, 0 medium, 7 low.

**Founder-level decisions taken (no human in the loop).** − on a too-large value gives {maks}; − and + are both unavailable while the text holds a non-digit. «Sist Uke bestilte du n.» shows only while the field is empty. Draft copy [ASSUMPTION]: the step announcement «24 enheter»; the typed cells read «24, din ordre, ikke bekreftet»; with overdue units the band sentence ends «…uten kjent uke, pluss 24». The thin line from Din ordre to Levering is built here (the 6.11 AC asks for it; the 6.10 note had put it in 6.12). A typed 0 shows «Din ordre 0» and «På vei 16 + 0» with no box. An arrival past nå + 4 (longer delays) shows only at nå, with no line; the arrival sentence still names the Uke. The band keeps true scale, so a very large typed value shrinks the band in that Uke. A placed non-guided Order (only after a switch to a rule-based player) shows read-only with no line. The read-only field also drops the caret (`caret-transparent`), besides `cursor: default`. The 1.4 px borders render as whole device pixels at 1× (browser rounding); the e2e checks the colour. Implementation ran in the orchestrating agent's context (caller's runbook); reviewers were sub-agents.

**Verification.**
- Backend: 2705 passed (75.5 s); `test_play_fixture.py` 8 passed; ruff clean.
- Frontend: typecheck; Vitest 631 passed; `check:copy`; `lint:colours`; build (local and compose image).
- Playwright full `--workers=2`: 370 passed (6.5 min) before the review patches; after them the play specs (60) passed.
- Slow new tests: the per-width state test in `order-field.spec.ts` takes about 3.1 s at each of 320/360/1440 px (four axe runs per width, as the AC asks); the other new e2e tests are under 1 s. No fixed sleeps.
- No migration.

**Residual risks.** The Uke reset of the typed text is untested until Story 6.12 (deferred). Draft copy awaits the founder (#31). With longer delays the arrival has no table column.
