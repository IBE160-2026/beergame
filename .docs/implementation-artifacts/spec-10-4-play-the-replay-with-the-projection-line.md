---
title: 'Story 10.4: Play the Replay with the projection line'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: 'ae5efdf2e6dbecfd109a6fff3fe9b5a3d310425d'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-10-context.md'
  - '{project-root}/.docs/implementation-artifacts/spec-10-3-start-the-replay-after-passing-the-debrief-quiz.md'
warnings: ['oversized']
deferred:
  - summary: >-
      A finished Replay shows the Class game's «Spillet er ferdig» with its Debrief explanation and
      «Gå til Debrief», although a Replay has no Debrief.
    evidence: |-
      `GameEnd` (frontend/src/modules/games/game-end.tsx) branches only on `test_game` and
      `debrief === "held"`; the play page shows it for any finished game. A Replay played to its
      last Week reaches it in 10.4. Story 10.5 owns the Replay's end («Replay er ferdig»,
      Totalkostnad, «Gå til gjennomgangen») and must give the Replay its own end screen
      (blind 11, edge 1 and 8).
    location: >-
      frontend/src/modules/games/game-end.tsx
    severity: medium
---

<intent-contract>

## Intent

**Problem:** A started Replay cannot be played: `games.service.own_game` answers None for a Game without a number that no Lecturer plays, so `/api/me/games/{id}`, `/play`, `/weeks/{w}/order` refuse it, Hjem shows only its Setene, and the play screen has no projection line.

**Approach:** Let `own_game` return the Student's Replay (theirs while they hold its Seat, as a test Game is), mark it `replay` in `StudentGameOut` and put `projection` (from `games.policy`) in the play envelope. The Epic 6 play screen then plays it unchanged, and draws the dashed projection with its sentence when the envelope says so, from display arithmetic in `lib/preview.ts`. Hjem and Stegene lead to it with «Fortsett Replay, Uke 9.».

## Boundaries & Constraints

**Always:** Orders only through `games.commands.place_order` (the existing `place_own_order`). The play screen components are reused from `modules/games` and `components/charts`; nothing of them is copied into `modules/replay`. Projection = `preview.position_base + order − horizon × incoming_order`, horizon = `preview.order_arrival_week − week` (fields already in `SeatState`; no new field is needed), the typed Order counted while valid (the placed or Guided Order once there), 0 otherwise. The line runs from (nå, Netto lager) to (nå + horizon, projection), dashed `projection` stroke, hollow dot at its end, `aria-hidden` like every graph row; the sentence is visible text under the table and is its alternative. The projection is drawn only when `PlayOut.projection` is true (policy column), never from the purpose. A Replay's rules (briefing, `rules`) are its own Game settings, not the Class session's. UI copy in `nb.ts`; draft lines recorded in `open-assumptions.md`.

**Never:** no finish screen or `replay` step (10.5), no close at the Test deadline (10.6); no change to the engine's numbers or the `SeatState` schema version; the axis never goes past nå + 4; no Time proposal, Starting task or Debrief for a Replay; no game per test.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Open own Replay | Student holds its Seat, session locked, Class listed | `GET /api/me/games/{id}` 200, `replay: true`, `number: null`, `briefing_first: false`, `rules` = Replay's settings, `debrief: null`; `/play` 200 with `projection: true` | — |
| Class game envelope | any Class game | `projection: false`; no line, no sentence | — |
| Order in a Replay | valid Order in open Week | 204; rule-based AI players order, the next Week opens; Hjem's Replay `week` follows | refusals as Epic 6 (`order_exists`, …) |
| Another User | other Student, Lecturer | 403 `forbidden` on every route | FR-5 |
| Time proposal / Starting task on a Replay | Student posts | 403 as for a test Game | — |
| Horizon 4 (Classic) | Posisjon 3, typed 24, incoming 8 | «Den stiplede linja viser netto lager om fire uker: 3 + 24 − 4 × 8 = −5 hvis ordre inn holder seg. Ikke garantert.», dot at nå + 4 | — |
| Shorter delays | horizon 2 | «… om to uker: …», dot at nå + 2 | — |
| Longer delays | horizon 5 or 6 | sentence names the horizon; the same straight line is drawn up to nå + 4 (axis edge), no dot past the axis | — |
| Nothing typed | empty or invalid field | sentence without the Order term: «… 3 − 4 × 8 = −29 hvis du ikke bestiller og ordre inn holder seg. Ikke garantert.» | — |

</intent-contract>

## Code Map

- `backend/app/modules/games/service.py:264 StudentGame`, `:437 own_game` -- add `replay`/`projection` fields; a non-numbered, not-staff Game is the Student's while `repo.held_role` names them.
- `backend/app/modules/sessions/service.py:1746 _game_out`, `:1836 _own_locked_game`, `:1861 _own_test_game` (pattern for own settings as rules), `:1899 student_play_of`, `:2076 propose_own_time`, `:2111 accept_own_time`, `:2180 own_game_session` -- Replay branch; refusals like `test_game`.
- `backend/app/modules/sessions/schemas.py:525 StudentGameOut`, `PlayOut` -- `replay: bool = False`, `projection: bool = False`.
- `backend/app/engine/view.py:217 OrderPreview` -- read-only: `order_arrival_week`, `position_base`; `players/llm.py:157` already reads the lead time the same way.
- `backend/tests/games/test_play_fixture.py` -- engine fixtures for the frontend (pattern `preview_golden`); add `projection-golden.json` and `play-replay-short.json`.
- `backend/tests/replay/test_start.py` -- setup pattern (`confirmed`, `sweep.run(START + MINUTE)`, `passed`, `start`).
- `frontend/src/lib/preview.ts` (+ `preview.test.ts`) -- `orderProjection`.
- `frontend/src/components/charts/net-graph.tsx` -- `projection` prop exists (`Projection`), add no-dot end; `netScale` takes `projection`.
- `frontend/src/modules/games/week-table-view.tsx graphFields/WeekTable` -- `projection` prop: points in the net field, sentence in the footer.
- `frontend/src/modules/games/play-page.tsx Running/Topplinje/BackLinks`, `home.ts gameTitle/stepItems`, `copy/nb.ts games.play`, `homes.student.replay`.
- `frontend/src/modules/replay/replay-block.tsx` -- «Fortsett Replay, Uke 9» link; start pushes to the play screen.
- `frontend/e2e/graph-over-table.spec.ts`, `replay-start.spec.ts`, `support/graph.ts` -- stub patterns.

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/games/service.py` -- `StudentGame.replay`, `.projection`; `own_game` branch.
- `backend/app/modules/sessions/{service,schemas}.py` -- `_own_locked_game` admits a Replay under the Class checks; `_game_out` with the Game's own settings as rules, no Debrief, `replay`; `PlayOut.projection` from the found game; time proposal and Starting task refuse a Replay.
- `backend/tests/replay/test_play.py` (new) -- one session: open, envelope `projection`, a Class game's `false`, orders advance Weeks with AI rows, Hjem week, other Users 403, proposal/Starting task 403.
- `backend/tests/games/test_play_fixture.py` -- projection golden (Classic, 3/3/3, 1/1/1 traces; value from `seat_detail`'s slots) and a short-delay Replay envelope.
- `frontend/src/lib/preview.ts` + `preview.test.ts` -- `orderProjection(state, order)` held to the golden file.
- `frontend/src/components/charts/net-graph.tsx`, `modules/games/week-table-view.tsx`, `play-page.tsx`, `home.ts`, `copy/nb.ts` -- draw line and sentence; Replay titles («Grossist, Replay»).
- `frontend/src/modules/replay/{replay-block.tsx,replay.ts,replay.test.ts}` + `games/home.ts stepItems` -- «Fortsett Replay, Uke 9» on Hjem (primary when no game action is), Stegene note «Fortsett Replay, Uke 9.» (the block's button above it is the way there; a second inline Lenke in Stegene would miss the 44 px tap target at 320 px).
- `frontend/e2e/replay-play.spec.ts` (new) -- stubbed Replay vs Class envelope at 320/360/1440 with axe; short delays dot column; Hjem/Stegene resume line.
- api client regenerated; `open-assumptions.md` draft copy.

**Acceptance Criteria:**
- Given a running Replay, when the Student opens `/spill/{id}`, then the Epic 6 play screen shows with Topplinje «Grossist, Replay», and an Order sent there is stored by `place_order`.
- Given envelopes of a Class game and a Replay, when Graf over tabell renders, then only the Replay has `[data-mark=projection]` and the sentence; the dot stands at the centre of column nå + horizon.
- Given the projection, when the Student types 24, then the sentence and the dot update without a request.
- Given Hjem with a running Replay in Uke 9, then the Replay block offers «Fortsett Replay, Uke 9» to `/spill/{id}` and Stegene's Replay step reads «Fortsett Replay, Uke 9.».
- Given the Replay screen at 320, 360 and 1440 px, then axe passes and the sentence wraps inside the page.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
Four layers (sonnet; the story widens who reaches the play routes, so it counts as risky): blind hunter, edge-case hunter, verification gap, intent alignment. Every hand-back failed; findings were read from `review-{blind,edge,verification,intent}-10-4.md` in the scratchpad.
- verdicts: 37 findings — high 0, medium 3, low 14, false 20, maybe-false 0
- findings:
  - `[false]` `[reject]` (blind 1) a placed non-guided Order is not counted — `preview` is `{...orderPreview(state.preview, placed), confirmed}` once `turn.order` is set, so `preview.order` is the placed Order.
  - `[low]` `[reject]` (blind 2) an invalid typed value makes the sentence say «hvis du ikke bestiller» — true of what the line counts; the Ordrefelt states the invalid value itself; a third sentence form adds copy and a state for a passing keystroke.
  - `[low]` `[reject]` (blind 3) `own_game` takes any number-less, not-staff Game as a Replay — the policy table is the rule (AD-13, no purpose compares); `replay` is the only such purpose with a Class session; a future one gets its own row and review.
  - `[false]` `[reject]` (blind 4) the commit inside `_own_locked_game` changes callers' transactions — the same pattern as `_own_test_game`; callers only read after it, in a new transaction; the row copy keeps the Class session's dates, which are the Replay's too.
  - `[false]` `[reject]` (blind 5) the straight line implies Netto lager values in between — UX-DR19 draws a dashed straight line to the value, not a trajectory; the clipped part is the same line.
  - `[false]` `[reject]` (blind 6) the golden assumes full shipment — that is the projection's stated assumption («hvis ordre inn holder seg … Ikke garantert»).
  - `[low]` `[reject]` (blind 7) `projection(weeks, …, horizon, …)` passes the horizon twice — both come from one `Projection` in the one caller; no divergence in use.
  - `[false]` `[reject]` (blind 8) `replayResume` and `resume` near-duplicates — two strings on purpose (sentence with full stop, button without), recorded in open-assumptions.
  - `[low]` `[reject]` (blind 9) the e2e expected sentence uses the code under test — the strings are pinned by hand in `projection.test.tsx` (the spine's sentence); the e2e checks the wiring.
  - `[false]` `[reject]` (blind 10) the redirect in `replay-start.spec.ts` races unmocked requests — the play page's reads answer 403 (the demo Student holds no such Game) and the test only checks the URL, then leaves; it passed.
  - `[medium]` `[defer]` (blind 11) a finished Replay shows «Gå til Debrief» — Story 10.5's end screen; deferred in frontmatter.
  - `[low]` `[reject]` (blind 12) a started Replay can be played after the Testfrist — Story 10.6 closes it at the deadline; outside this story.
  - `[low]` `[reject]` (blind 13) no Lecturer refusal test — `own_game` needs a held Seat and `authz.own_seat`, which staff never get in a Replay; classmates are tested.
  - `[low]` `[patch]` (blind 14) the repeated Order accepted two codes — now asserts 409 `order_exists`.
  - `[false]` `[reject]` (blind 15) `ResumeAction` duplicates markup; an «already started» refusal leaves Hjem stale — `NavAction` is private to `game-action.tsx` and the markup is two lines; an existing Replay answers 200, so the success path navigates.
  - `[low]` `[reject]` (blind 16) the axis rescales while typing — the domain must hold the dot to draw it; damping adds state for a keystroke-long effect.
  - `[medium]` `[defer]` (edge 1) = blind 11.
  - `[low]` `[reject]` (edge 2) the briefing at `/spill/{replay}/regler` reads «Testspill» — no link leads there any more (BackLinks); reachable only by typing the URL.
  - `[false]` `[reject]` (edge 3) a Guided Week without a placed Order — the fixed Order is placed when the Week opens (`turn.order`), so `nowOrder` is set; invalid input = blind 2.
  - `[false]` `[reject]` (edge 4) `horizon <= 0` in the found branch — delays are at least 1 each (`Delay`, ge=1), so the horizon is at least 2.
  - `[low]` `[reject]` (edge 5) = blind 3.
  - `[false]` `[reject]` (edge 6) `start_own_game` can start a stored Replay — it calls the same `games.commands.start` that `replay.start`'s recovery calls; the outcome is identical.
  - `[false]` `[reject]` (edge 7) stale reads after the commit — no caller holds ORM state across it; the `ready` path reads anew (`progress.steps_of`, `_game_out`).
  - `[medium]` `[defer]` (edge 8) = blind 11.
  - `[low]` `[reject]` (edge 9) = edge 2.
  - `[low]` `[patch]` (verification 1) the Replay's rules were checked on delays only — the test now compares delays, Guided Weeks and rates with the Replay's settings and asserts 0 Guided Weeks against the Class card's 4.
  - `[low]` `[patch]` (verification 2) the axis domain holding the projection was untested — `projection.test.tsx` asserts `netScale`'s domain spans the end value and its y stays inside the field.
  - `[low]` `[patch]` (verification 3) the accept route's Replay refusal was untested — the test now posts an accept and expects 403.
  - `[false]` `[reject]` (intent 1) the Playwright tests stub the api — descriptive; the flag is pinned over the real api in `tests/replay/test_play.py`, the drawing in the browser (as 10.3).
  - `[false]` `[reject]` (intent 2) resume and Stegene from stubs — descriptive; the real week on Hjem is in pytest.
  - `[false]` `[reject]` (intent 3) start-then-play stubbed — descriptive.
  - `[false]` `[reject]` (intent 4) no timing test for NFR-1/NFR-2 — descriptive; rule-based players order in the same request (the test reads Uke 2 right after the 204), LLM waits are Epic 2's budget.
  - `[false]` `[reject]` (intent 5) shared components gained props — descriptive; nothing is copied into `modules/replay`.
  - `[false]` `[reject]` (intent 6) hidden information asserted only through `FORBIDDEN` — descriptive; the envelope is the Class game's own builder.
  - `[false]` `[reject]` (intent 7) horizon derived, no new field — recorded decision (Design Notes).
  - `[false]` `[reject]` (intent 8) horizon past nå + 4 — recorded decision.
  - `[false]` `[reject]` (intent 9) «Start Replay» now opens the play screen — recorded decision.

## Design Notes

The horizon is the Order's lead time, already in `SeatState.preview` (`order_arrival_week − week`); adding a field would bump `SeatState` to version 5 with an upgrade path for every stored `state_seen`, for a number the envelope already carries. Golden values come from `engine.seat_detail` by another route than the client's: Netto lager + every supply-line slot due by nå + horizon + overdue + Order − horizon × incoming order.

Stegene's Replay step reads «Fortsett Replay, Uke 9.» without a Lenke of its own: the Replay block's «Fortsett Replay, Uke 9» stands just above it, and an inline step Lenke fails the 44 px tap-target check at 320 px.

A horizon past nå + 4 (delays up to 3 each) keeps the axis at nå + 4: the same straight line is clipped at the last column, with no dot, and the sentence still states the value.

## Verification

**Commands:**
- `uv run pytest tests/replay tests/games/test_play_fixture.py tests/sessions/test_play.py -q` -- pass
- `npm run typecheck && npx vitest run src/lib src/modules/games src/modules/replay src/components/charts` -- pass
- full gate per runbook before commit

## Auto Run Result

Status: done

**Summary.** A started Replay is now played on the Epic 6 play routes and screen. `games.service.own_game` gives a Game of the Class session without a number that no Lecturer plays (the policy, never the purpose) to the Student while they hold its Seat, as `StudentGame(replay=True, projection=policy.projection)`. `sessions` admits it under the Class game's checks, states the Replay's own drawn settings as its `rules`, gives it no Debrief, refuses the time proposal, its acceptance and the Starting task (403 as for a test Game), and adds `StudentGameOut.replay` and `PlayOut.projection`. Orders go through the existing `place_own_order` → `games.commands.place_order`. On the play screen, an envelope with `projection` draws the dashed `projection` line from Netto lager at nå to its value at nå + horizon with a hollow dot, and the sentence «Den stiplede linja viser netto lager om fire uker: 3 + 24 − 4 × 8 = −5 hvis ordre inn holder seg. Ikke garantert.» under the table, filled with the Seat's numbers and updated as the Order is typed. `orderProjection` in `lib/preview.ts` is display arithmetic on `seat_state` (`position_base`, `incoming_order`, horizon = `order_arrival_week − week`). The Topplinje reads «Grossist, Replay», and the only way out is «Til Hjem». Hjem's Replay block has «Fortsett Replay, Uke 9» (primary when no game action is), Stegene says «Fortsett Replay, Uke 9.», and «Start Replay» opens the play screen.

**Files.** Backend: `modules/games/service.py` (`StudentGame.replay/projection`, `own_game`), `modules/sessions/{service,schemas}.py`, `modules/replay/README.md`. Tests: `tests/replay/test_play.py` (new), `tests/games/test_play_fixture.py` (projection golden over the 4/6/2-horizon traces, and a 1/1/1 Replay envelope), `tests/sessions/test_play.py` (`projection` false for a Class game). Frontend: `lib/preview.ts` (+ test against `fixtures/projection-golden.json`), `components/charts/net-graph.tsx` (`week` on projection points, `projectionClipped`, `data-weeks`), `modules/games/week-table-view.tsx` (`projectionPoints`, `ProjectionSentence`, `projection` prop), `play-page.tsx`, `game-end.tsx`, `home.ts` (`gameTitle`/`roleGameText` for the Replay, Stegene note), `student-hjem.tsx`, `modules/replay/{replay-block.tsx,replay.ts}`, `copy/nb.ts`, regenerated `lib/api/{openapi.json,schema.ts}`, fixtures `projection-golden.json`, `play-replay-short.json`; tests `projection.test.tsx` (new), `charts.test.tsx`, `home.test.ts`, `replay.test.ts`; e2e `replay-play.spec.ts` (new), `replay-start.spec.ts`. Docs: `open-assumptions.md`, refreshed `epic-10-context.md` (planning docs were newer than it).

**Decisions the founder would otherwise take.** (1) The delay horizon is read from the existing `preview.order_arrival_week − week` (the Order's lead time); no `SeatState` field or version bump. (2) With nothing (or nothing valid) typed, the projection counts the Order as 0 and its sentence says «hvis du ikke bestiller og ordre inn holder seg» (draft). (3) A horizon past nå + 4 (delays of 3) keeps the axis at nå + 4: the same straight line is drawn to the last column without a dot, and the sentence gives the value at nå + horizon. (4) The line starts at Netto lager at nå. (5) The sentence stands under the table with a short dashed rule before it, in `ink-secondary`. (6) «Start Replay» opens the play screen at once. (7) Hjem's «Fortsett Replay, Uke 9» is the primary when no game action is; the button drops the spine's full stop, Stegene keeps it. (8) Stegene's Replay step is no second link (an inline step link fails the 44 px tap target at 320 px; the block's button is just above). (9) The Replay play screen has no «Regler før første ordre» link (the briefing is the Class game's, about playing together) and reads «Grossist, Replay». (10) A Replay has no time proposal, Starting task or Debrief (403 like a test Game). (11) Implementation done in this context (runbook); four review layers, since the story widens who reaches the play routes.

**Review.** 37 findings (four sonnet layers): 4 patched (all low: exact `order_exists` code, the Replay's full rules against the Class game's, the axis domain holding the projection, the accept-route refusal), 1 deferred (medium, Story 10.5: a finished Replay shows the Class game's end screen with «Gå til Debrief»), the rest rejected with reasons in the triage log. `followup_review_recommended: false`: no medium or high entry was patched.

**Verification.** Full backend suite `--maxprocesses=8` on fresh test databases (`…/olspillet_m`): 3141 passed, 4 skipped (116.6 s), after the last backend change. ruff check and format clean. Frontend typecheck, Vitest 1022 passed, `lint:colours`, `check:copy`, and `next build` (in the image) passed. Stack rebuilt after the last frontend change. Playwright `--workers=4` on replay-play, replay-start, student-home, homes, graph-over-table, week-table, order-field, order-confirm, order-failures, chain-band, seat-status, guided-week, cost-panel, week-advance, week-transition, live-updates, game-start, game-end, game-card, briefing, test-game, time-proposal: 193 passed, none flaky (an earlier run before the Stegene fix failed the 320 px tap-target check twice, which led to decision 8). axe at 320, 360 and 1440 px in `replay-play.spec.ts`. New test over 1 s: `tests/replay/test_play.py::test_the_replay_plays_on_the_play_routes_with_the_projection` (about 2.1 s, one session through the whole chain).

**Residual risks.** A finished Replay shows the Class game's end screen until Story 10.5. A started Replay can still be played after the Testfrist until Story 10.6 closes it. The projection's sentence is draft copy.
