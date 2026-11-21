---
title: 'Story 9.5: Scrub the whole chain and see the amplification'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: 'b331cfc6cb1d90dce7bf015b1921a2c12c95e9aa'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-9-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** After the reveal the Student cannot see the whole chain: `steps/3` answers only its number, so the four Roles' Orders, inventory and backlog, the Order amplification and the first large Orders are never shown, and there is no way to spool through the Uker.

**Approach:** `GET /api/debriefs/{id}/steps/3` (behind `require_explanation`) answers `chain`: every Role, Fabrikk first, with each Uke's Order and the Week state it saw (Decision log `state_seen`), plus Forsterkning and the first Uke with an Order ≥ 10 read from the stored facts set (`games.service.fact_set` → `games.facts.get_or_create`), and the capacity of capped Roles while `FEATURE_CAPACITY` is on. The web app shows step 3 under step 2: heading «Hele kjeden: svingningene vokser oppstrøms og kommer senere», the Ukeskrubber (new shared `components/week-scrubber.tsx`), the four-Role Kjedebånd (new `variant="chain"` of the existing `ChainBand`) for the chosen Uke, then Ordrestolper (new shared `components/charts/order-bars.tsx`) over the Rolle × Uke table in one `GraphOverTable` region, with a polite live reading 300 ms after the last change.

## Boundaries & Constraints

**Always:**
- Numbers come from the api only: Forsterkning and first large Uke equal the stored facts set (Story 9.1); Order, inventory, backlog, På vei and Ordre inn per Role and Uke equal the Decision log rows' `order` / `state_seen`. `last_week` = facts `chain.weeks`; `large_order` = `analysis.facts.LARGE_ORDER`.
- `steps/3` keeps the 9.2/9.3 refusals (`debrief_not_open`, `debrief_held`, `forbidden`, `explanation_required`) with the envelope only. Step 2 unchanged; steps 4–5 answer only their number.
- Four-Role Kjedebånd: upstream left, «Produksjon» at the left end and «Kundene» at the right, own node with a 1.4 px `ink` border, stock bar up / backlog bar down on one scale for the whole game, Orders on the order line, På vei on the goods line, no names. Labels never overlap and fit from 320 px; the band is `aria-hidden` with a `<title>`; the live reading is its alternative.
- Ordrestolper: one row per Role, Fabrikk at the top, bars `order-history`, own Role `ink`, a `restordre` dot with «Uke n» at each Role's first large Order joined by a thin `restordre` diagonal, a dashed `ink` line at the chosen Uke, Forsterkning («7,6×», `figure-amplification`) at the right of each Role's row. Rolle × Uke numbers underneath in the same columns, every cell printing its number on a `flow-*` step (`ink` on 1–2, `paper` on 3–4), `th` scopes. Built in `components/charts` with a fixed width and an own-Role prop (unset for staff) so Spillinnsikt (Story 7.8) reuses it.
- Ukeskrubber: `role="slider"`, name «Velg uke», `aria-valuemin=1`, `aria-valuemax`=last Uke, `aria-valuetext` «Uke 15»; Left/Down −1, Right/Up +1, PageDown/PageUp ±4, Home/End; pointer drag optional; «Én uke tilbake» / «Én uke fram» buttons ≥ 44 px; «Uke 1» … «Uke N» at the ends; line «Kjeden i Uke 15. Dra i skrubberen for å spole.» Starts at the last Uke. No animation, so reduced motion shows the result at once.
- Live region (polite), 300 ms after the last change: «Uke 15. Fabrikk: restordre 3, ordre 22. Distributør: …», Fabrikk first; a Role with both stock and backlog (capacity) reads both.
- Capacity (flag on, Role capped): one line per capped Role «Fabrikk kan sende høyst 12 enheter per uke.»; nothing with the flag off.
- Copy in `nb.debrief.chain` (post-reveal section).

**Never:** no names of other Students; no number computed in the web app beyond the drawing's scale and the `flow-*` step choice; no rebuild of facts in `debrief`; no import of `modules/players` or `games` other than `games.service`; no step-pointer move (9.11); no Spillinnsikt page work (it does not exist yet: Stories 7.7/7.8 wire the shared components there).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Chain | `GET …/steps/3` with Explanation | 200 `{…, chain: {own_role, last_week, large_order: 10, roles:[{role, amplification, first_large_order_week, capacity, weeks:[{week, order, incoming_order, inventory, backlog, supply_line}]}]}}`, roles factory → retailer | — |
| No Explanation | none saved | 403 `explanation_required`, no `chain` | envelope only |
| Flat demand | demand never varied | `amplification` null; UI shows «–» for Forsterkning | — |
| No large Order | a Role never orders ≥ 10 | `first_large_order_week` null; no dot for that Role; diagonal joins the rest | — |
| Capacity off / uncapped | flag off or no cap | `capacity` null everywhere; no capacity line | — |
| Keys | Home / End / PageUp at Uke 34 of 36 | Uke 1 / 36 / 36 (clamped) | — |

</intent-contract>

## Code Map

- `backend/app/modules/debrief/{service.py step/_reveal, schemas.py DebriefStepOut, routes.py get_debrief_step, README.md}` -- add `_chain` for step 3.
- `backend/app/modules/games/{service.py, facts.py get_or_create}` -- expose `fact_set(game_id, seat)` through `games.service` (debrief may import only it, `tests/test_imports.py`).
- `backend/app/analysis/facts.py` -- `RoleFacts.amplification`, `first_large_order_week`, `LARGE_ORDER`, `ChainFacts.weeks`.
- `backend/app/engine/settings.py capacity_of`, `app/platform/config.py feature_capacity`.
- `backend/tests/debrief/test_explanation.py` -- module-scoped played Class game; step 2 test pattern to extend for step 3.
- `frontend/src/components/charts/{chain-band.tsx, chain-band-layout.ts}` -- the one-Seat band; add the chain variant (layout function in the same module).
- `frontend/src/components/graph-over-table.tsx` -- fields over week columns; Ordrestolper is a field, Rolle × Uke the body.
- `frontend/src/modules/debrief/{reveal-step.tsx (pattern), debrief-page.tsx, api.ts}`, `copy/nb.ts` `debrief`.
- `frontend/e2e/{debrief-reveal.spec.ts, support/reveal.ts}` -- stubbed-step e2e pattern with axe and scroll checks.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/games/service.py` -- `fact_set`, `StoredFactSet`.
- `backend/app/modules/debrief/{schemas,service,routes}.py`, `README.md` -- `ChainOut`, step 3.
- `backend/tests/debrief/test_explanation.py` -- step 3 numbers equal the Decision log and the stored facts set; gate; capacity null with no cap.
- `frontend/src/components/charts/{chain-band.tsx, chain-band-layout.ts, order-bars.tsx, charts.test.tsx, README.md}` -- chain variant layout (no overlaps, fits at 320), Ordrestolper, `flowStep`.
- `frontend/src/components/{week-scrubber.tsx, components.test.tsx}` -- slider keys, clamping, buttons.
- `frontend/src/modules/debrief/{chain-step.tsx, api.ts, debrief-page.tsx, debrief.test.ts}`, `copy/nb.ts`, regenerated `openapi.json` / `schema.ts` -- step 3 and the reading text.
- `frontend/e2e/debrief-chain.spec.ts` (+ `support/chain.ts`) -- stubbed step 3 at 320/360/1440 with axe, scroll region, columns aligned, keys, buttons, live reading, reduced motion; capacity line.

**Acceptance Criteria:**
- Given a saved Explanation, when the Debrief page shows, then step 3 shows under step 2 with the heading, the scrubber at the last Uke, the four-Role band and the Ordrestolper over the Rolle × Uke table; without one, step 3 is absent.
- Given the scrubber, when the Student presses a key or a step button, then the band, the dashed line and the line by the scrubber show the chosen Uke, and 300 ms later the live region reads the chain, Fabrikk first.
- Given 320, 360 and 1440 px, when step 3 shows, then the page does not scroll sideways, Ordrestolper and table scroll together inside their region with aligned columns, and axe passes.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
Layers run: blind hunter and edge-case hunter (sonnet), per the orchestrator's two-reviewer rule; verification-gap and intent-alignment skipped for the same reason. Both hand-backs failed; findings were read from `review-blind-9-5.md` and `review-edge-9-5.md` in the scratchpad.
- verdicts: 24 findings — high 0, medium 0, low 18, false 6, maybe-false 0
- findings:
  - `[low]` `[patch]` (blind 1) First-large markers keyed `text + x` collide when two Roles share the Uke. Keyed by row index now; test with three Roles in one Uke added.
  - `[low]` `[patch]` (blind 2) `debrief-explanation.spec.ts` left `steps/3` unstubbed, so the stubbed page fetched it from the stack and showed the chain's error block. Stubbed with `chain: null` (and `chain: null` added to its step-2 answer).
  - `[low]` `[patch]` (blind 3) The not-finished loop in `readers` swapped `steps/2` for `steps/3`. Both are listed now.
  - `[false]` `[reject]` (blind 4) Backend test gaps. `explanation_required` for steps 2–5 incl. 3 is asserted before the send; `amplification` None is the 9.1 facts' rule, passed through unchanged; a finished Game's log has every Role in every Uke (`DecisionLog._complete`), and its settings always exist.
  - `[false]` `[reject]` (blind 5) `KeyError` / order assumptions in `_chain`. The facts set is built from the same `settings.roles` (`facts._chain`), and `roles` is documented as customer's end first (`DecisionLog.roles`); old `state_seen` versions read as version 4 (`SeatState`).
  - `[false]` `[reject]` (blind 6) `last_week` vs logged Uker can differ. Same refutation: a complete log is the facts' precondition, and facts `weeks` is its length.
  - `[low]` `[patch]` (blind 7) `large_order` unused and «10» hard-coded in the key. `barsKey` takes the api's `large_order`.
  - `[false]` `[reject]` (blind 8) The fixed heading. The epic's AC gives this exact heading.
  - `[low]` `[reject]` (blind 9) Forsterkning not explained; «–» for no value. The term and «7,6×» are the spine's; a dash appears only when demand never varies (never in Classic). Copy review is Issue #31.
  - `[low]` `[reject]` (blind 10) Short bar rows. Four rows at 12 em match the mockup's proportions; the numbers under each bar carry the values. Visual check is a separate agent's.
  - `[low]` `[reject]` (blind 11) No loading state / empty state. Same as 9.4: one small read after a page already shown.
  - `[low]` `[reject]` (blind 12) Scroll-into-view couples to `GraphOverTable` markup; scrubber drag untested by unit. The e2e checks the scroll at phone widths and a press on the track; a refactor adds API to the shared component for no user gain.
  - `[low]` `[patch]` (blind 13) `flowStep` computed twice per cell. Computed once. (`const variant` is used; `_variant` is allowed by the typecheck; the reduced-motion test is the AC's check that nothing waits on motion.)
  - `[low]` `[patch]` (blind 14) README said «never rebuilt here» without the first-read build. Reworded: the first read builds and stores the set through `get_or_create`, whose unique insert settles a race.
  - `[false]` `[reject]` (blind 15) Generated `schema.ts`/`openapi.json` missing. They were left out of the review diff on purpose and are committed with the change.
  - `[false]` `[reject]` (edge 1) `ViewError` from `fact_set` gives a 500. Only for a missing pinned patterns version or an incomplete log; a finished Game has neither (same as 9.4's blind 6).
  - `[low]` `[patch]` (edge 2) Same as blind 1; same fix.
  - `[low]` `[patch]` (edge 3) Alt/Ctrl/Meta with an arrow key was swallowed by the slider. Modified keys pass through.
  - `[low]` `[patch]` (edge 4) A right-click on the track moved the handle. Only the main button (or touch/pen) starts a drag.
  - `[low]` `[patch]` (edge 5) A failed background refetch replaced the shown chain with the error. The error shows only when no chain was read.
  - `[low]` `[patch]` (edge 6) A small stock or backlog under a large game maximum drew under 1 px. Bars are at least 1 px.
  - `[low]` `[reject]` (edge 7) Gap labels may overlap at 3+ digits with 200 % text at 320 px. Needs a further arrangement search for a rare case; the comment now states the limit (edge 9).
  - `[low]` `[patch]` (edge 8) Same as blind 3; same fix.
  - `[low]` `[patch]` (edge 9, claim) The doc comment claimed «no two labels ever overlap». Corrected to node label blocks, with the gap-label limit stated.

## Design Notes

Decisions for the founder: Story 7.8 (Ordrestolper, Rolle × Uke table, Spillinnsikt) is still backlog in the other lane, so this story builds Ordrestolper and the Rolle × Uke rows in the shared chart module per 7.8's spec (own-Role prop, Forsterkning optional); the Spillinnsikt AC is left to 7.7/7.8, which reuse these components and read Forsterkning from the same facts. Forsterkning lives in a trailing column right of the week columns, so it stands at the right of each Role's row in the table that is the chart's alternative. Node labels name Roles only (no names, AD-14). Starting the scrubber at the last Uke shows the whole game's state; the mockup's «Uke 15» is an example.

## Verification

**Commands:**
- `uv run pytest -n0 tests/debrief tests/test_imports.py` -- pass
- full `uv run pytest`, `ruff check`, `ruff format --check` -- pass
- `npm run typecheck`, `npm test`, `npm run lint:colours`, `npm run check:copy`, `npm run build` -- pass
- Playwright `debrief-chain`, `debrief-reveal`, `debrief-explanation`, `homes`, play-screen specs -- pass

## Auto Run Result

Status: done

**Summary.** Debrief step 3 shows the whole chain. `GET /api/debriefs/{id}/steps/3` (behind the Explanation gate) answers `chain`: every Role, Fabrikk first, with each Uke's Order and the Week state it saw (Ordre inn, Lager, Restordre, På vei from `state_seen`), Forsterkning and the first Uke with an Order of 10 or more read from the stored facts set (`games.service.fact_set` over `games.facts.get_or_create`), `last_week`, `large_order`, and each Role's capacity while `FEATURE_CAPACITY` is on. The web app shows step 3 under step 2: the heading, «Kjeden i Uke N. Dra i skrubberen for å spole.» beside the new Ukeskrubber (slider with keys, 44 px step buttons, press/drag on the track, starting at the last Uke), the four-Role Kjedebånd (new `variant="chain"` of `ChainBand`, from «Produksjon» to «Kundene», own node in a 1.4 px `ink` border), then the new Ordrestolper over the Rolle × Uke numbers (`flow-*` steps) and a Forsterkning column in one Graf over tabell region, the scrubber's dashed line across the bars, Forsterkning as a line of text, and a polite reading of the chain 300 ms after the scrubber stops.

**Files.**
- `backend/app/modules/games/service.py`: `fact_set`, `StoredFactSet` for readers outside `games`.
- `backend/app/modules/debrief/{schemas,service,routes}.py`, `README.md`: `ChainOut`, step 3.
- `backend/tests/debrief/test_explanation.py`: step 3 against SQL and the stored facts, capacity on/off, refusals.
- `frontend/src/components/charts/{chain-band.tsx, chain-band-layout.ts (chainLayout), order-bars.tsx (new), charts.test.tsx, README.md}`.
- `frontend/src/components/{order-bars-table.tsx (new), week-scrubber.tsx (new), components.test.tsx}`.
- `frontend/src/modules/debrief/{chain-step.tsx (new), api.ts, debrief-page.tsx, debrief.test.ts}`, `copy/nb.ts` (`debrief.chain`), regenerated `openapi.json`/`schema.ts`.
- `frontend/e2e/{debrief-chain.spec.ts (new), support/chain.ts (new), debrief-reveal.spec.ts, debrief-explanation.spec.ts}` (the last two stub step 3).

**Deviations and decisions.** The builder implemented in its own context (orchestrator rule) and ran two review layers. Decisions for the founder (also in Design Notes): Story 7.8 is backlog, so Ordrestolper and the Rolle × Uke table are built here in the shared modules for 7.8 to reuse; the Spillinnsikt part of the AC is left to 7.7/7.8 (no Spillinnsikt page exists yet). Forsterkning stands in a trailing column at the right of each Role's row of the numbers, and again as one line of text. The scrubber starts at the last Uke. The band names Roles only and puts Orders over the order line and På vei over a box on the goods line, with a one-line key above the band; node labels move to staggered rows, then split «Restordre» from its number, when space runs out. `flow-*` steps are five equal parts of the game's largest Order (the lowest part unfilled). A capped Role reads «lager N, restordre M» and gets «Fabrikk kan sende høyst 12 enheter per uke.». Draft copy marked `[ASSUMPTION]` in `nb.debrief.chain`.

**Review.** 24 findings (high 0, medium 0, low 18, false 6): 13 rows patched (11 entries: marker keys, two e2e/test coverage fixes, `large_order` in the key, `flowStep` once, README wording, modifier keys, main pointer button only, keep the chain on a failed refetch, 1 px minimum bars, doc comment); nothing deferred; the rest rejected with reasons in the triage log. followup_review_recommended: false (no high or medium patched).

**Verification.**
- Full backend suite after the patches: 2880 passed, 4 skipped in 69 s; `ruff check`, `ruff format --check` clean. (An earlier full run had one failure in `tests/ai/test_effort.py` that passed alone and again in the next full run; not touched.)
- Frontend: typecheck, Vitest (55 files, 747 tests), `lint:colours`, `check:copy`, `next build` pass.
- Playwright on the rebuilt lane stack (8081): `debrief-chain`, `debrief-reveal`, `debrief-explanation`, `debrief-open`, `homes`, `game-end`, `student-home`, `order-confirm`, `week-advance`, `graph-over-table`, `chain-band`, `cost-panel`: 121 of 123 passed right after the rebuild; the two `week-advance` 2-second-budget tests failed while the stack warmed up and passed on rerun (play screens are untouched). Before the patches all 123 passed.
- Tests over 1 s: none new; `test_step_one_the_one_send_the_gate_and_the_readers` (about 3 s) also covers step 3 on the same played game.

**Residual risks.** Draft copy awaits review (Issue #31). Order or På vei numbers of three or more digits at 200 % text on a 320 px screen can reach a node in the band. The band's height can change between Uker when the node labels switch to staggered rows. Spillinnsikt (7.7/7.8, other lane) must reuse `OrderBarsTable` and `ChainBand variant="chain"` rather than build its own; if epic-7 builds 7.8 before this merges, the two lanes will have parallel components.
