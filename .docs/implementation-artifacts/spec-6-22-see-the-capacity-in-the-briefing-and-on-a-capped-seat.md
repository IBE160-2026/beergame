---
title: 'Story 6.22: See the capacity in the briefing and on a capped Seat (cut list, behind FEATURE_CAPACITY)'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: 'e04e940de5ac2e1004d7b6a5620837cca87315fe'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-6-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-5-15-set-shipping-capacity.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** Story 5.15 lets a Lecturer cap what a Role ships per Week (`GameSettings.capacity`, frozen in the snapshot), but a Student is never told, and the play screen's week table shows only Netto lager, so a capped Seat holding stock and backlog at once cannot be read (FR-12, FR-23, FR-84).

**Approach:** `GameRulesOut` (the rules the briefing and the play page already read from `GET /api/me/games/{id}`) gains `capacity`: the snapshot's caps as `[{role, units}]`, filled only while `FEATURE_CAPACITY` is on (read at read time, as 6.21 does). The briefing adds a «Kapasitet» section when the list is non-empty. On the play screen a Seat whose Role is in that list gets the rows Lager and Restordre above Netto lager; the Kjedebånd already draws both bars and labels from `seat_state.inventory`/`backlog`, and gets a capped scale fixture.

## Boundaries & Constraints

**Always:**
- `GameRulesOut.capacity: list[RoleCapacityOut]` (`role`, `units`), in chain order (`settings.roles`, Detaljist first), `[]` when the flag is off or the snapshot sets none. Only the caps of the rules, never another Seat's numbers. `game_rules(row)` reads `get_settings().feature_capacity`.
- Briefing: a section «Kapasitet» after «Slik går en uke», only when the list is non-empty. One line per capped Role in chain order («Grossisten kan sende høyst 6 enheter per uke.»), or one line when all four share one cap («Hver rolle kan sende høyst 6 enheter per uke.»). Then «En rolle med kapasitet kan ha lager og restordre samtidig: enhetene ligger på lager mens ordrene venter.» When the Student's own Role is capped, also «Rollen din har kapasitet. Tabellen i spillet viser derfor Lager og Restordre hver for seg, over Netto lager.» Copy in `nb.games.briefing.capacity`, marked [ASSUMPTION]. Never a number of Weeks.
- Play screen: capped = own Role in `game.rules.capacity`. `WeekTable` with `capped` uses `CAPPED_ROWS` = `ROWS` with Lager and Restordre (not laptop-only) inserted before Netto lager, on phone and laptop. Cell values are `seat_state` / history fields as given; the web app computes nothing. `rules.capacity` missing (an older stand-in) reads as none.
- Kjedebånd: unchanged code; both bars, both labels («Lager 6», «Restordre 4») and the sentence already come from `inventory`/`backlog`. A new engine-held fixture `chain-band-capped.json` (the Classic fixture game's Orders with `capacity={"wholesaler": 6}`, all four Roles, every Uke) runs the 6.9 scale test at 288/328 px, 13/26 px text.
- With the flag off or no capacity, every screen of this epic is as before.

**Never:** No change to `seat_state`/`SeatState`, the engine, `RULES_VERSION`, golden traces, migrations, the LLM prompt or the Klasseøkt (Story 5.15). No change to «class-of-1994». No Debrief wording (Epic 9).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| No cap | snapshot capacity None, flag on | `rules.capacity == []`; briefing and table as before | — |
| Flag off | snapshot `{"wholesaler": 6}`, flag off | `rules.capacity == []`; nothing about capacity | — |
| One Role | `{"wholesaler": 6}`, flag on | `[{"role":"wholesaler","units":6}]`; briefing line for Grossisten; Grossist's table has Lager, Restordre over Netto lager; Detaljist's table as before | — |
| All alike | four Roles × 6 | four entries; briefing «Hver rolle …» line | — |
| Mixed | `{"retailer": 5, "factory": 9}` | two lines, Detaljisten then Fabrikken | — |

</intent-contract>

## Code Map

- `backend/app/modules/sessions/schemas.py:401` `GameRulesOut` -- add `RoleCapacityOut` and `capacity`.
- `backend/app/modules/sessions/service.py:1223` `game_rules` -- fill from snapshot (`settings.capacity_of`, `settings.roles`) behind `capacity_enabled()` (`:436`).
- `backend/tests/sessions/test_student_home.py:185,210,214` -- existing rules equality (add `"capacity": []`), `game_rules` unit test pattern; `CLASSIC_RULES` constant.
- `backend/tests/sessions/test_capacity.py` (Story 5.15) -- saving a capacity on a session (`save`, flag env).
- `backend/tests/games/test_play_fixture.py` -- `ORDERS`, `_game_until`, `chain_band_classic`, `BAND_FIELDS`; add capped settings parameter and `chain-band-capped.json`, plus `play-capped.json` (a wholesaler envelope in a Uke with inventory and backlog > 0).
- `frontend/src/lib/api/{openapi.json,schema.ts}` -- regenerate.
- `frontend/src/modules/games/briefing.ts`, `briefing-page.tsx`, `briefing.test.ts` -- `capacityLines(role, rules)`; section.
- `frontend/src/modules/games/week-table.ts:52` `ROWS` -- add `CAPPED_ROWS`, `isCapped(role, rules)`.
- `frontend/src/modules/games/week-table-view.tsx:256` -- `capped` prop; `play-page.tsx:323` passes it; `:165` skeleton unchanged.
- `frontend/src/copy/nb.ts:1433` -- `briefing.capacity`.
- `frontend/src/modules/games/chain-band.test.ts` -- capped scale test; `e2e/chain-band.spec.ts` / `e2e/briefing.spec.ts` / `e2e/support/play.ts` patterns.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/sessions/{schemas,service}.py` -- `capacity` in `GameRulesOut` behind the flag.
- `backend/tests/sessions/test_student_home.py` -- update equality; unit tests of `game_rules` (one Role, all, flag off, none); one api test: a session saved with `{"wholesaler": 6}`, locked, `GET /api/me/games/{id}` gives `rules.capacity` and nothing else new; flag off gives `[]`.
- `backend/tests/games/test_play_fixture.py` -- capped fixtures held to the engine.
- `frontend/src/lib/api/*` -- regenerate.
- `frontend/src/copy/nb.ts`, `briefing.ts`, `briefing-page.tsx`, `week-table.ts`, `week-table-view.tsx`, `play-page.tsx` -- UI.
- `frontend/src/modules/games/briefing.test.ts`, `week-table.test.tsx`, `chain-band.test.ts` -- lines, rows, capped scale test (both bars present in some Uker, no overflow/overlap).
- `frontend/e2e/briefing.spec.ts` -- capped briefing: section present with lines; absent without capacity; axe at 360 once.
- `frontend/e2e/chain-band.spec.ts` (or a new `capacity-play.spec.ts`) -- capped Grossist envelope at 320/360/1440: both bars and labels, sentence, rows Lager and Restordre above Netto lager, band fits, axe once per width.

**Acceptance Criteria:**
- Given the flag off or no capacity, when the briefing and play screen render, then nothing about capacity shows and `rules.capacity` is `[]`.
- Given `{"wholesaler": 6}` and the flag on, when a Grossist reads the briefing, then «Kapasitet» names Grossisten's 6 per uke, says stock and backlog can coexist, and that the table shows both rows.
- Given a capped Grossist with inventory and backlog > 0, when the play screen renders at 320, 360 and 1440 px, then the band draws the stock bar above and the backlog bar below with «Lager N» and «Restordre M», the sentence reads both, the table shows Lager and Restordre above Netto lager, and axe finds nothing.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- layers: the runbook allows two reviewers, so only the blind hunter and the edge-case hunter ran. The verification-gap and intent-alignment layers were skipped.
- verdicts: 18 findings — high 0, medium 0, low 15, false 3, maybe-false 0
- findings (blind):
  - `[false]` `[reject]` The flag cache would leak between tests. `tests/conftest.py::_fresh_settings` runs `reset_caches()`, which clears `get_settings`, before and after every test.
  - `[low]` `[reject]` With the flag switched off mid-game, the briefing and table hide a cap the frozen snapshot still plays. AC1 asks for exactly this (flag off, nothing about capacity). It is the same read-time rule as Story 6.21 and the residual Story 5.15 recorded.
  - `[low]` `[patch]` A cap of 1 read «høyst 1 enheter». Fixed: `unitsText` in `nb.ts` gives «1 enhet». Unit test added.
  - `[low]` `[reject]` The "every Role" check counts the copy's Role names, not the game's chain. `roles` is not editable (`EDITABLE_SETTINGS`), so every Class game has the four Classic Roles.
  - `[low]` `[reject]` The capped rows are not in the print variant or in Hjem's `MiniWeekTable`. The story names the play screen's week table of Story 6.6. The Spillkort has three fixed rows by design (DESIGN.md → Spillkort).
  - `[low]` `[reject]` The graph still draws Netto lager only. The story asks for the band and the table, and the graph tokens are DESIGN.md's.
  - `[low]` `[reject]` `isCapped` lives in `briefing.ts`. It reads `GameRules`, as the briefing helpers do. No lint rule fails (`tsc` and the build pass).
  - `[low]` `[reject]` The `?? []` fallback contradicts the required type. It keeps older stand-ins, and a payload cached across a deploy, from crashing the play page. It is cheap, and a unit test asserts it.
  - `[low]` `[reject]` `RoleCapacityOut.units` has no `ge=1`. The values come from `GameSettings`, which the engine validates to 1–100. This is an output model.
  - `[low]` `[reject]` The pre-lock path and a Role outside the chain are untested with capacity. The pre-lock path is the same code, already covered for the other rules. The engine's validator refuses a Role outside the chain.
  - `[low]` `[patch]` The uncapped e2e check asserted only that Lager is absent. Fixed: it asserts that Restordre is absent too.
  - `[low]` `[reject]` The copy is an unreviewed draft. `[ASSUMPTION]` is the project's marker for the founder's copy review (Issue #31). `check:copy` and the fixed copy back the "no Weeks" rule.
  - `[low]` `[patch]` The named imports in `briefing.test.ts` were out of order. Fixed. The hardcoded 120 in the capped test mirrors the Classic test.
- findings (edge case):
  - `[low]` `[reject]` With the flag off after the snapshot froze, the briefing and table hide the cap. Same as the second blind row (AC1).
  - `[low]` `[reject]` `capped` comes from the flag-gated rules, not from `seat_state`. Same root cause and decision. AC2 also forbids the web app from computing whether a Seat is capped.
  - `[low]` `[reject]` A chain of fewer than four Roles, all capped alike, would list each Role. Same as the fourth blind row: roles are not editable.
  - `[false]` `[reject]` `settings.roles` could be stored in an order that does not start with the Detaljist. `roles` is not editable, and the engine's default, which every snapshot holds, starts with the Detaljist.
  - `[false]` `[reject]` Hjem's `MiniWeekTable` lacks the capped rows. Same as the fifth blind row: the Spillkort's rows are fixed by design and lie outside this story's screens.

## Design Notes

Founder-level calls, taken here with no human in the loop:
- The capacities travel in `rules` (the game card), not in `seat_state`: they are rules of the game and the same for every Seat, and `seat_state` stays unchanged (no schema bump, LLM and Decision log untouched).
- The flag is read at read time, as in 6.21: switching it off hides the capacity in briefing and table even though the frozen cap is still played (Story 5.15's recorded residual).
- Briefing wording is draft [ASSUMPTION] and uses definite Role names; the «Kapasitet» section sits right after «Slik går en uke» because it qualifies «Det du har på lager, må du sende».
- Only the capped Seat's own table gets the extra rows; uncapped Seats keep Netto lager alone, as their stock and backlog are never both above 0.

## Verification

**Commands:**
- `cd backend && uv run pytest -n0 tests/sessions/test_student_home.py tests/games/test_play_fixture.py -q` -- pass
- `cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check .` -- pass
- `cd frontend && npx tsc --noEmit && npx vitest run && npm run check:copy && npm run build` -- pass
- `cd frontend && npx playwright test e2e/briefing.spec.ts e2e/chain-band.spec.ts e2e/week-table.spec.ts e2e/graph-over-table.spec.ts e2e/order-field.spec.ts` -- pass

## Auto Run Result

Status: done

**Summary.** Behind `FEATURE_CAPACITY`, a Student is told about a shipping capacity and sees both stock and backlog on a capped Seat (FR-12, FR-23, FR-84).
- **Api.** `GameRulesOut.capacity` (`[{role, units}]`, Detaljist first) comes from the snapshot. The flag is read on every request, as in Story 6.21. It is `[]` when the flag is off or nothing is capped. There is no `seat_state`, migration or engine change.
- **Briefing.** A «Kapasitet» section follows «Slik går en uke». It names each capped Role and its cap, in one line when all four Roles share one cap. It says that stock and backlog can stand together, and, for a capped Student, that the table shows both. The copy is draft [ASSUMPTION].
- **Play screen.** A capped Seat's week table has Lager and Restordre above Netto lager, on phone and laptop. The Kjedebånd already drew both bars and labels from `inventory` and `backlog`. Its scale test now also runs over a capped fixture.

**Files.**
- `backend/app/modules/sessions/{schemas,service}.py`: `RoleCapacityOut` and `GameRulesOut.capacity`, behind the flag.
- `backend/tests/sessions/test_student_home.py`: the rules now include `capacity`. Adds a `game_rules` capacity test and an api test.
- `backend/tests/games/test_play_fixture.py`: holds the two new fixtures to the engine.
- `frontend/src/modules/games/fixtures/{chain-band-capped,play-capped}.json` (new): the Classic fixture Orders with the Grossist capped at 6.
- `frontend/src/lib/api/{openapi.json,schema.ts}`: regenerated.
- `frontend/src/copy/nb.ts`: `briefing.capacity` and `unitsText`.
- `frontend/src/modules/games/{briefing.ts,briefing-page.tsx}`: `capacities`, `isCapped`, `capacityLines` and the section.
- `frontend/src/modules/games/{week-table.ts,week-table-view.tsx,play-page.tsx}`: `CAPPED_ROWS` and the `capped` prop.
- Tests: `briefing.test.ts`, `home.test.ts`, `week-table.test.tsx`, `chain-band.test.ts`, `e2e/briefing.spec.ts` and `e2e/chain-band.spec.ts`.

**Review.** 18 findings: low 15, false 3.
- Patched (low, 3):
  - «1 enhet»
  - the Restordre assertion in the uncapped e2e test
  - the import order
- Deferred: none.
- Rejected, with reasons in the triage log:
  - the flag is read live
  - the four Classic Roles
  - the Spillkort and the print variant
  - the graph
  - the fallback
  - the output model's range
  - the paths that run the same code
  - the draft copy
- Follow-up review: false. No high or medium finding was patched.

**Verification.**
- Backend: the full suite passed (2774 tests in 66.8 s). `ruff check` and `ruff format --check` are clean.
- Frontend:
  - `tsc` passed.
  - Vitest passed (713 tests).
  - `check:copy` passed.
  - The Next build passed, after the patches.
- Playwright:
  - After the patches, against a rebuilt frontend image, `briefing` and `chain-band` passed (28 tests).
  - Before the patches, these specs passed (110 tests): `week-table`, `graph-over-table`, `order-field`, `order-confirm`, `order-failures`, `week-transition`, `seat-status`, `guided-week`, `cost-panel`, `game-start`, `game-end`, `test-game`, `week-advance` and `game-card`.
- No new test runs over 1 s. There are no fixed sleeps.
- The builder looked at screenshots of the capped play screen and the briefing at 360 px. No independent visual reviewer was run; the orchestrator runs its own visual check.

**Residual risks.**
- If the flag goes off while a capped game runs, the cap is still played, but the briefing and the table no longer show it.
- The copy is a draft until the founder's copy review.

Visible screens changed: the briefing, and the play screen's week table. Both change only when the flag is on and the snapshot caps a Role.
