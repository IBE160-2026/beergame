---
title: "Story 6.17: See on Hjem whether the game waits for me"
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '06a20231eaeb01e05aebab925bd22d62743c9011'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-6-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** While the Class game runs, Hjem shows only «Spill 17 · Du er Grossist», the Setestatus and the «Gå til Uke n» action below the Seats. It has no Spillkort: nothing says whether the game waits for this Student, and there is no mini graph, three-row table or Totalkostnad. The home endpoint carries no `seat_state`, so Hjem cannot show the numbers.

**Approach:** `StudentGameOut` (the Hjem and own-game payload) gains `seat_state` and the own `turn`, filled from the same read models as the play envelope while the game runs. A shared `GameCard` shell is added in `frontend/src/components/game-card.tsx`; it takes the title as its variant. Hjem fills it with a `MiniWeekTable`, which is Graf over tabell at mini scale. The card stands between the game heading and Setene, as in `04-student-hjem.png`.

## Boundaries & Constraints

**Always:**
- Backend: `StudentGameOut` gains `seat_state: SeatState | None` and `turn: PlayTurnOut | None`. Both are set only while `status == "running"`, from `games_service.seat_state(game, role, week)` and `open_turn`, the play endpoint's sources. People still come from `table_status`. Regenerate `openapi.json` and `schema.ts`.
- Card state comes from the api alone (`home.ts`): **waits for you** when the game runs, `seat_state` is present and the own Seat's `ordered` is `false`; **waiting for others** when it runs and the own Seat has ordered. Otherwise there is no card, and Hjem keeps today's actions («Les reglene», «Start spillet», the not-ready line).
- `GameCard` (DESIGN.md → Spillkort): a `paper` card with a 1 px `axis` border and `rounded-sm`. The heading row has the title (h4, `label` weight 600) and «Uke 11» right-aligned in the same heading row's line. Then the figure slot, then «Totalkostnad 68,00 kr» (`body`) and the action slot on one row that wraps. A sr-only summary sentence follows. The shell holds no game rule. Callers pass `title`, `week`, `figure`, `total`, `summary` and `action`, so Epic 13 can pass «Oppfølgingsspill» with no copy.
- Waits for you: the title is «Spillet venter på deg» and the action is the one primary button «Gå til Uke 11» (the page's one primary, UX-DR8).
- Waiting for others: the title is the draft «Du har bestilt» [ASSUMPTION] in `nb.ts`. There is no primary button; «Gå til Uke 11» stays as a Lenke.
- `MiniWeekTable` (in `week-table-view.tsx`) reuses `GraphOverTable`. It shows nå − 7 … nå + 4 at every width, never further right than nå + 4. It has one Netto lager field, drawn by `NetGraph` with `mini`: no Posisjon line, markers or direct labels, so it adds no new marks. The rows are Uke, Netto lager and Din ordre, using `cellFor`. Din ordre at nå shows the own `turn.order` as placed when there is one, else the dashed empty cell. There is no key line. The region is named «Graf og tabell, Spill 17» [ASSUMPTION]. The graph rows stay `aria-hidden`.
- Screen-reader alternative: the card's text, plus the sr-only «Netto lager −13 i Uke 11.» [ASSUMPTION form of the spine's sentence].
- Totalkostnad is `formatNumber(seat_state.total_cost, { kroner: true })`.
- The card sits inside `GameCard` of `student-hjem.tsx`: game heading → drawn line → Spillkort → Setene → rules Lenke. For non-running states, `GameAction` keeps its place.
- Live: the existing `game:<id>` and `user:<id>` → `enrolledSessionsKey` invalidation refreshes the card. Focus never moves.
- Phone bleed: inside the card the region does not bleed past the card's padding (a `bleed={false}` option on `GraphOverTable`).

**Never:** a week count, a share played, or axis columns beyond nå + 4; a reference or suggested Order; client arithmetic on game quantities; a second primary button on Hjem; a copy of the play screen's table code; changes to «class-of-1994»; fixed sleeps in tests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Waits for you, Uke 11 | own Seat `ordered: false` | «Spillet venter på deg», «Uke 11», mini graph, rows Uke/Netto lager/Din ordre over Uke 4–15, «Totalkostnad 82,00 kr», primary «Gå til Uke 11» | — |
| Waiting for others | own Seat `ordered: true`, `turn.order: 24` | «Du har bestilt», no primary button, Lenke «Gå til Uke 11», Din ordre at nå reads 24 | — |
| Uke 1 | no history | columns Uke 1–5 only; graph draws one point | — |
| Guided Week, not viewed | `ordered: false`, `turn.order` set | waits-for-you card; nå shows the fixed Order | — |
| Not running | `ready` / `not_ready` / `finished` | no card; `seat_state` and `turn` are null | — |
| Older stub without `seat_state` | field missing | no card; today's action stays | — |

</intent-contract>

## Code Map

- `backend/app/modules/sessions/schemas.py:391` `StudentGameOut`, `:427` `PlayTurnOut` (move it above `StudentGameOut`).
- `backend/app/modules/sessions/service.py:1222` `_game_out`: add the reads. `:1302` `student_play_of` is the reference for the same sources.
- `backend/tests/sessions/test_student_home.py` (`home`, `klass`) and `tests/sessions/test_play.py` (`running`, `played_to`) hold the fixtures to reuse. `test_student_home.py:76/180` compares own-game and Hjem payloads, which stays true.
- `frontend/src/components/graph-over-table.tsx:332`: the bleed wrapper.
- `frontend/src/components/charts/net-graph.tsx`: add the `mini` prop. `netScale` reads only net values when mini.
- `frontend/src/modules/games/week-table-view.tsx`: `graphFields` and `WeekCell` are the reuse points for `MiniWeekTable`. `week-table.ts`: `weekColumns` and `cellFor`.
- `frontend/src/modules/games/home.ts`: `nextAction` and `toWeekText`. Add `cardState`, and keep primary selection in `student-hjem.tsx:74`.
- `frontend/src/modules/games/game-action.tsx`: `NavAction` (primary or Lenke).
- `frontend/src/copy/nb.ts:349` `homes.student`: add `card`.
- `frontend/e2e/student-home.spec.ts` (`withSession`, `VIEWPORTS`, `textAtLeast13px`), `e2e/seat-status.spec.ts:162` (Hjem stub; add `seat_state`), `e2e/support/play.ts` (fixture `play-week-11.json`), `e2e/support/live-game.ts` (`liveClassGame`, `orderByApi`).

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/sessions/schemas.py`, `service.py`: the two fields. Add a test in `tests/sessions/test_student_home.py`: while running, the Hjem `seat_state` and `turn` equal the play envelope's. Before the start, both are null.
- Regenerate `frontend/src/lib/api/openapi.json` and `schema.ts`.
- `frontend/src/components/charts/net-graph.tsx`: `mini`. Test in `charts.test.tsx`: no position marks or labels.
- `frontend/src/components/graph-over-table.tsx`: `bleed`.
- `frontend/src/components/game-card.tsx` (new): the shell. Test in `components.test.tsx`.
- `frontend/src/modules/games/week-table-view.tsx`: `MiniWeekTable`.
- `frontend/src/modules/games/home.ts` (+ `home.test.ts`): `cardState`, `netSentence`.
- `frontend/src/modules/games/student-hjem.tsx`: the card wiring and the primary selection.
- `frontend/src/copy/nb.ts`: `homes.student.card` strings.
- `frontend/e2e/game-card.spec.ts` (new): stubbed Hjem in both states at 320, 360 and 1440 px. It checks the title, «Uke 11», the three rows and their columns, Totalkostnad, at most one primary button, the sr sentence, the aria-hidden graph, no page scroll, axe and text ≥ 13 px. One live test on the real stack (`liveClassGame`, 2 Students, `rule_based`): the other Student's Order and the Week advance reach the card within 2 s, and focus is kept.
- `frontend/e2e/seat-status.spec.ts`: give the Hjem stub `seat_state` and `turn`.

**Acceptance Criteria:**
- Given a running game that waits for the Student, when Hjem opens, then the Spillkort reads «Spillet venter på deg» and «Uke n». It holds a mini graph over Uke / Netto lager / Din ordre (nå − 7 … nå + 4), the Totalkostnad, and the one primary «Gå til Uke n» above Setene.
- Given the Student has ordered, then the card's title is «Du har bestilt», and Hjem has no primary button.
- Given a screen reader, then the graph is hidden and «Netto lager −13 i Uke 11.» is read in the card.
- Given another Seat orders or the Week advances, then the card and Setestatus update within 2 s without reload and focus stays put.
- Given 320, 360 and 1440 px, then there is no page scroll, at most one primary button and no axe violation.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- layers: blind hunter and edge-case hunter only (the orchestrator caps reviewers at two); verification-gap and intent-alignment skipped.
- verdicts: 17 findings — high 0, medium 0, low 13, false 4, maybe-false 0
- findings:
  - `[low]` `[reject]` blind: `table_status`, `play_status` and `seat_state`/`open_turn` are separate reads, so an advance between them can give a title for one Uke and numbers for the next. The play envelope reads the same way. The advance that causes the mix emits `game:<id>`, so Hjem reads again at once. A single snapshot read would add a transaction mode the read models do not have.
  - `[false]` `[reject]` blind: an unviewed Veiledet uke shows «Du har bestilt». `TableSeatOut.ordered` counts the Student's view in a Guided Week (Story 6.14, `schemas.py` docstring), so an unviewed Guided Week reads `ordered: false`, and the card is «Spillet venter på deg».
  - `[low]` `[patch]` blind: the backend test did not pin `seat_state.week == week`. Added to `test_hjem_carries_the_envelopes_own_seat_and_turn_while_running`.
  - `[low]` `[reject]` blind: every Hjem fetch now makes two more reads and carries the whole history. Hjem reads only on a change event, not on a timer. AD-3 asks for the play envelope's sources. A Classic game's history is at most 36 rows.
  - `[low]` `[patch]` blind: the `GameCard` docstring placed the sr-only summary last. The docstring now matches the markup.
  - `[low]` `[reject]` blind: `GameCard` hardcodes `<h4>`. Its only use and Epic 13's «Oppfølgingsspill» sit at the same depth on Hjem. A `level` prop would be unused surface.
  - `[low]` `[reject]` blind: `netLabel` and `positionLabel` are still required in mini mode. The props are documented as unused there. A union type would only change the API shape.
  - `[low]` `[patch]` blind: the mini-graph test's comment was misleading. Fixed. The path count runs on a fixed test series, so it is not data-dependent.
  - `[low]` `[patch]` blind: `MiniWeekTable` mapped `phone: true` onto columns already flagged `phone`. The map is removed and a comment says why no column hides.
  - `[low]` `[patch]` blind: `PlayCard` used `seat_state!`. The parent now passes the narrowed `state`.
  - `[false]` `[reject]` blind: the live e2e test assumes the AI players have ordered within 2 s. `commands._open_week` calls `players.ensure_order` in the transaction that opens the Week, and a `rule_based` occupant orders there and then. The AI Orders are stored before the Week is visible.
  - `[low]` `[reject]` blind: the stub's id pattern only covers fewer than 10 games, and there is no test of two cards that both wait. The spec uses two games. The primary choice is the existing `primaryGame` rule of Story 6.5, which this change only narrows.
  - `[low]` `[patch]` blind: nothing showed that `GameAction` is gone when the card shows. The e2e test now counts exactly one «Gå til Uke 11» per card. `cardState`'s unit test covers a running game with the briefing first.
  - `[low]` `[reject]` edge: the Uke can advance between the `table_status` and `seat_state` reads. Same root cause and same reason as the first row.
  - `[low]` `[reject]` edge: an Order can land between `table_status` and `open_turn`, so «venter på deg» shows with the Order at nå. This is transient, and the Order's own `game:<id>` event makes Hjem read again.
  - `[false]` `[reject]` edge: `open_turn` can raise for a running game and break all of Hjem. `commands.start` sets `running` and opens Week 1 with one turn per Seat in one transaction, and every advance does the same. A running game always has a turn for its open Week.
  - `[false]` `[reject]` edge (claim): the parity test is in `test_play.py`, not `test_student_home.py` as the spec's task says. `test_play.py` imports its fixtures from `test_student_home.py`, so the reverse would be a circular import. The test checks the claim. Its location is recorded under Auto Run Result.

## Design Notes

Founder-level calls taken here: the waiting title «Du har bestilt» (draft); «Gå til Uke n» stays as a Lenke while waiting for others; the mini graph omits Posisjon and direct labels, as drawn in the mockup; the card's window is the phone window at every width (the card is `max-w-md`); the card stands above Setene. The orchestrator's note (Issue #123) says mockup 04 puts the action below Setene. The mockup in fact draws «Gå til Uke 11» inside the card, above Setene, and the code now has it below. The story's AC and the mockup win: the action moves into the card, above Setene.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/sessions/test_student_home.py tests/sessions/test_play.py -q` -- pass
- `cd frontend && npx tsc --noEmit && npx vitest run src/modules/games src/components` -- pass
- `cd frontend && npx playwright test e2e/game-card.spec.ts e2e/student-home.spec.ts e2e/homes.spec.ts e2e/seat-status.spec.ts` -- pass

## Auto Run Result

Status: done

**Summary.** Hjem shows a Spillkort while the Class game runs. The api's Hjem and own-game payload (`StudentGameOut`) gains `seat_state` and the own `turn`. They are read through `games.views` in the open Week, as the play envelope reads them, and are null unless the game runs.

The card's title says whether the game waits for the Student:
- «Spillet venter på deg» has the page's one primary button «Gå til Uke n».
- The draft «Du har bestilt» has «Gå til Uke n» as a Lenke only, and Hjem then has no primary button.

The heading carries «Uke n». Inside the card stand:
- a mini Graf over tabell over nå − 7 … nå + 4: the Netto lager line, its fills, the dot and «Nå» over the rows Uke, Netto lager and Din ordre, with the own Order at nå once placed
- «Totalkostnad 82,00 kr»
- a sr-only «Netto lager −20 i Uke 11.»

The card stands above Setene, as in `04-student-hjem.png`. While the briefing still comes first, or the game is not running, Hjem is unchanged.

**Files.**
- `backend/app/modules/sessions/schemas.py`, `service.py` -- the two fields; `_own_week`, now shared with the play envelope.
- `backend/tests/sessions/test_play.py` -- Hjem equals the envelope while running; the fields are null when ready or finished. It is placed here, not in `test_student_home.py`, to avoid a circular import.
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerated.
- `frontend/src/components/game-card.tsx` (new) -- the shared Spillkort shell; its title is the variant (Epic 13).
- `frontend/src/components/charts/net-graph.tsx` -- `mini`.
- `frontend/src/components/graph-over-table.tsx` -- `bleed`.
- `frontend/src/modules/games/week-table-view.tsx` -- `MiniWeekTable`.
- `frontend/src/modules/games/home.ts` -- `cardState`, `netSentence`.
- `frontend/src/modules/games/student-hjem.tsx` -- `PlayCard`; the primary choice skips a game the Student has ordered in.
- `frontend/src/copy/nb.ts` -- `homes.student.card`, `graph.netMiniSvg`, `netMiniAxisSvg`.
- Tests: `charts.test.tsx`, `components.test.tsx`, `home.test.ts`, `week-table.test.tsx`, `e2e/game-card.spec.ts` (new), and `e2e/seat-status.spec.ts` (its stub gets the new fields).

**Review.** Two layers (blind, edge case) reported 17 findings: high 0, medium 0, low 13, false 4.
- Patched (6 low): the week invariant in the backend test, the GameCard docstring, the misleading test comment, the no-op column map, the narrowed `state` prop, and the e2e count of «Gå til Uke n» links.
- Deferred: none.
- Rejected: the rest, each with its reason in the triage log.

**Follow-up review:** false. Only low findings were patched.

**Founder-level decisions taken (no human in the loop).**
- The title while waiting for others is the draft «Du har bestilt» [ASSUMPTION].
- While waiting for others, «Gå til Uke n» stays as a Lenke.
- The mini graph has no Posisjon line, markers or direct labels, as drawn. Its axis ticks show (6.5 em high).
- The card shows the phone window nå − 7 … nå + 4 at every width.
- The card is hidden while the briefing still comes first.
- The region name «Graf og tabell, Spill 17», the SVG titles and the sr sentence form are drafts.
- The card holds the action above Setene. The orchestrator's brief (Issue #123) said mockup 04 puts the action below Setene. The mockup draws it inside the card, above Setene, and the story's AC agrees, so the AC and the mockup were followed. Before this change, the code had it below Setene.

**Verification.**
- Backend: the full suite passed (2743 tests, 68 s); ruff check and format are clean. No migration.
- Frontend: `tsc`, Vitest (678 passed), `check:copy`, the colour lint and the Next build (compose image) all passed.
- Playwright:
  - `game-card`, `student-home`, `homes`, `seat-status`, `game-start` and `graph-over-table` passed after the patches (72 tests).
  - Before the patches, every play-screen spec, `landing`, `briefing` and `week-advance` passed (120 tests).
- New tests over 1 s:
  - The stubbed `game-card` tests take about 1–2 s alone (two cards, axe), and up to 6 s under a parallel run.
  - The live test takes about 13 s: two Invitations, a lock and three Orders.
  - `test_hjem_carries_the_envelopes_own_seat_and_turn_while_running` takes about 11 s, because it plays to Uke 6 like its neighbours.
  - No fixed sleeps.

**Residual risks.**
- At 320–360 px the 12 columns do not all fit in the card. The table scrolls inside its region, which opens at nå, as review R2-M3 foresaw.
- A Week that advances between the payload's separate reads can mix the title and the numbers for a moment, until the advance's own event reads Hjem again.

Visible screens changed: Hjem (Student) while the Class game runs.
