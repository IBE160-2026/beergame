---
title: "Story 6.18: See the chain's Total cost when the game ends"
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: 'd05861fd9736c55aba7dc05de38f4aa73d3a77b2'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-6-context.md'
warnings: ['oversized']
deferred: []
---

<intent-contract>

## Intent

**Problem:** A finished Class game shows only «Spillet er ferdig.». Nothing records the Class game step, the finished-game check runs only for simulations, `games.policy` has no columns for the step or the pre-play gate, and there is no result endpoint, Kjedens regning or Kjedens kostnad over tid.

**Approach:**
- Backend: `games.commands.finish` records `progress` `class_game` for every Student in the occupancy history where the policy says so. An `ops.sweep` due action verifies finished Games that have no check yet. The policy gets two columns. A new `GET /api/me/games/{id}/result` returns the chain's cost per Role and per Uke once the game is finished.
- Frontend: the play route renders «Spillet er ferdig» from that endpoint. Two new shared components: `components/chain-bill.tsx` and `components/chain-cost-chart.tsx`.

## Boundaries & Constraints

**Always:**
- **Policy.** `GamePolicy` gains `records_class_game_step` and `pre_play_gate`. Both are on for `class` and off for `simulation`. `games.service.StudentGame` carries `pre_play_gate` (read from `games.purpose` through `policy`). `_game_out.briefing_first` and `start_own_game`'s `starting_task_required` apply only when it is on. No code compares a purpose.
- **finish.** In the caller's transaction, after `set_lifecycle`: when `records_class_game_step` is on and the Game has a Class session, call `progress.record_step(user_id, class_session_id, "class_game", at, within=session)` once for every distinct `user_id` in `repo.occupancy_history`. `at` is the database clock (`repo.clock_now`). The existing `place_order`/`view_week` events stay (`game`, `session`, `user` for Students holding Seats). `record_step` adds `user:`/`session:` for each Student it records. The registry keeps `games.finish: {game}`, and its comment notes the step's topics.
- **Sweep.** `DueAction("games.verify_finished", …)`. `find` returns up to 20 finished Game ids with no `game_checks` row, oldest first (new `repo.unchecked_finished_game_ids`). `act` calls `games.service.verify_finished(str(id))`. Each runs in its own transaction, and the end screen never waits for it.
- **Result endpoint.** `GET /api/me/games/{game_id}/result` goes through `_own_locked_game` (403 `forbidden` for every other id alike). It answers 409 `game_not_finished` unless the lifecycle is `finished`. The body is `GameResultOut`:
  - `roles`: Detaljist→Fabrikk (`retailer, wholesaler, distributor, factory`), each with `role`, `holding_cost`, `backorder_cost` and `total_cost` (money strings)
  - `chain`: the same three sums
  - `weeks`: Uke 1…last, each with the chain's cumulative `holding_cost`, `backorder_cost` and `total_cost`
  - no names, no demand, no settings and no week count other than the weeks list itself, which is allowed after the end
  - Built in `games.views.chain_result` from the stored opened states and Orders through `seat_detail` per Role (the engine's numbers). The backend adds the per-Role amounts together. The chain total equals `summaries`' `chain_cost`.
- **End screen.** It is shown on `/spill/{id}` when `status == "finished"`, whatever `briefing_first` says. Title «Spillet er ferdig», subtitle «Grossist, Spill 17» (`roleGame`). Then, in order:
  1. a note slot (`note?: ReactNode`, empty here, for Epic 8)
  2. «Kjedens totalkostnad» (label)
  3. the chain total in `text-figure-hero` («2 266,00 kr»)
  4. «Fire Roller, to kostnadsarter, hele spillet.»
  5. `ChainBill`
  6. `ChainCostChart`
  7. «Hvorfor ble den slik? Det finner dere ut i Debriefen, med alle fire Rollene.»
  8. the one primary button «Gå til Debrief», linking to `DEBRIEF_PATH`, a route constant in `identity/homes.ts` that is `HOME_PATH.home` until Epic 9
- **ChainBill.** A `<table>` with the columns Rolle (sr-only header), Lager, Restordre and Sum. There is one row per Role in api order, never sorted. Each row has a split bar under the Role name: `lager` then `restordre`, with the width the row's sum ÷ the largest Role sum. The bar is `aria-hidden`, and its numbers stand in the same row. The own row is in weight 600 with «Grossist (deg)». The «Kjeden» row is weight 700, sits in `tfoot` under an `axis` rule, and has no bar. An `extraRows?: ReactNode` slot sits in `tbody` after the Roles and stays empty here.
- **ChainCostChart.** Heading «Kjedens kostnad over tid». It reuses `charts/cost-area.tsx` with a new optional `endLabels` prop, which draws the final holding and backlog values as text at the right end, inside the plot, kept apart by at least one line. The Lenke-button «Vis som tabell» / «Vis som graf» swaps in place to a table: Uke / Lager / Restordre / Sum.
- **Data and copy.** `frontend/src/modules/games/result.ts` formats only (`formatNumber`, kroner and decimals). Bar ratios are display ratios. `useGameResult(id, enabled)` uses the key `["games","mine",id,"result"]`, so the `game:` topic refreshes it. Copy goes in `nb.ts`: the spine strings verbatim, and drafts marked [ASSUMPTION].
- **Hjem.** A finished game shows «Spillet er ferdig.» and the Lenke «Se kjedens totalkostnad» [ASSUMPTION] to `gamePath` (`GameAction`, not primary). Stegene marks Debrief as current through the recorded `class_game` step.

**Never:**
- chain data before the end
- names or demand in the result
- sorting, ranking, praise or celebration animation
- client arithmetic on game quantities
- a second primary button
- branching on purpose
- blocking the end screen on the check
- changes to «class-of-1994»
- fixed sleeps

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Last Order | `place_order` completes the last Week | lifecycle `finished`; `class_game` step for each Student ever in the occupancy history; events `game`, `session`, `user` | — |
| Student replaced earlier | occupancy history names a Student who no longer holds the Seat | that Student also gets the step | — |
| Simulation finishes | purpose `simulation` | no step recorded | — |
| Result while running | lifecycle `running` / `not_started` | 409 `game_not_finished` | no chain data |
| Result for other game | another Student's game, bad id | 403 `forbidden`, same body | — |
| Sweep | finished Game without check | one `game_checks` row; second sweep acts on none | failing item logged, sweep goes on |
| End screen live | open play page when the last Week runs | `game:` event refetches; «Spillet er ferdig» renders, focus not moved | result fetch failure → page-error with retry |

</intent-contract>

## Code Map

- `backend/app/modules/games/policy.py` -- `GamePolicy`, `POLICIES`; add the two columns.
- `backend/app/modules/games/commands.py:1566` `finish`. Its callers are `_step` (`:1085`, from `place_order`/`view_week`/`advance`). `_commit_change` (`:228`) emits `game`/`session`. `place_order` (`:1316`) emits `user` for current Students.
- `backend/app/modules/games/repo.py:532` `occupancy_history`, `:340` `now`/`clock_now`, `:587` `finished_game_ids` (the model for `unchecked_finished_game_ids`, a LEFT JOIN `game_checks`), `:134` `student_seats` (add `games.c.purpose`).
- `backend/app/modules/games/service.py:199` `StudentGame`, `:209` `student_game`. It re-exports from views and checks, so `chain_result` and `GameResult` are exported here too.
- `backend/app/modules/games/views.py:89–131` `_opened`, `stored_orders`, `seat_state`. `app/engine/view.py:226` `seat_detail` (history rows with running `total_*`, plus the now-week totals).
- `backend/app/modules/games/checks.py:49` `verify_finished`, which is idempotent and logs `game_check_failed`.
- `backend/app/modules/ops/sweep.py` `DUE_ACTIONS`.
- `backend/app/modules/progress/service.py` `record_step(within=)`.
- `backend/app/modules/sessions/service.py:1222` `_game_out`, `:1429` `start_own_game`, `:1322` `student_play_of` (the pattern for `student_result_of`). `routes.py:600–616` is the play route pattern. `schemas.py` holds `StudentGameOut`.
- `backend/app/platform/events/registry.py` -- the comment on `games.finish`.
- Tests: `tests/sessions/test_play.py` (`running`, `played_to`, `play`); `test_open_games.confirmed`; `tests/classes/test_invitation_counts.execute`; `tests/games/test_policy.py`; `tests/games/test_summary.py` (`classic_game`, chain cost); `tests/ops/test_sweep.py`.
- Frontend:
  - `frontend/src/modules/games/play-page.tsx:120,591` `NotRunning`
  - `api.ts` (`usePlay` pattern)
  - `cost-panel-view.tsx` (the CostArea, toggle and table pattern; `useSize`)
  - `components/charts/cost-area.tsx`
  - `game-action.tsx` (switch on `nextAction`), `home.ts:65` `nextAction`
  - `identity/homes.ts` (`HOME_PATH`, `gamePath`)
  - `copy/nb.ts:1512` `games.play`
  - `lib/number-format.ts` `formatNumber`
- E2e: `frontend/e2e/support/play.ts` (stub helpers), `support/live-game.ts` `liveClassGame` (add an option for `game_settings`), `e2e/cost-panel.spec.ts` (an axe and reflow pattern).

## Tasks & Acceptance

**Execution:**
- `backend/app/modules/games/policy.py` -- the two columns -- AD-13.
- `backend/app/modules/games/repo.py`, `service.py` -- `purpose` in `student_seats` and `StudentGame.pre_play_gate`; `unchecked_finished_game_ids`.
- `backend/app/modules/games/commands.py` -- record the steps in `finish`.
- `backend/app/modules/games/views.py`, `schemas.py` -- `chain_result(game_id) -> GameResult` (refuses `game_not_found` and `game_not_finished`).
- `backend/app/modules/ops/sweep.py` -- the due action.
- `backend/app/modules/sessions/service.py`, `schemas.py`, `routes.py` -- the gate via `pre_play_gate`; `student_result_of`, `GameResultOut` and the route `getMyGameResult`.
- `backend/tests/games/test_policy.py`, `backend/tests/sessions/test_game_end.py` (new; one shortened Class game shared by the tests, 6 Weeks with 1 Guided Week, set in `class_sessions.game_settings` before the lock), `backend/tests/ops/test_sweep.py` -- the matrix rows.
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerate.
- `frontend/src/components/charts/cost-area.tsx` (+ `charts.test.tsx`) -- `endLabels`.
- `frontend/src/components/chain-bill.tsx`, `chain-cost-chart.tsx` (+ `components.test.tsx`) -- the shared components.
- `frontend/src/modules/games/result.ts` (+ `result.test.ts`), `api.ts`, `game-end.tsx` (new), `play-page.tsx` -- the end screen.
- `frontend/src/modules/games/game-action.tsx`, `home.ts` -- the Hjem finished line and Lenke. `identity/homes.ts` -- `DEBRIEF_PATH`. `copy/nb.ts` -- the strings.
- `frontend/e2e/game-end.spec.ts` (new) and `support/live-game.ts` -- tests:
  - a stubbed finished game at 320, 360 and 1440 px: order of the parts, «(deg)» row, Kjeden row, one primary button, «Vis som tabell» in place, no page scroll, one axe check per width
  - one live test: 1 Student, `rule_based`, `weeks: 2`, `guided_weeks: 0`; the last Order shows «Spillet er ferdig» with the chain total without a reload, and Hjem then shows the finished line

**Acceptance Criteria:**
- Given the last Order, when it commits, then the game is finished in the same transaction, and every Student ever seated has the `class_game` step.
- Given a finished Class game, when the Student opens `/spill/{id}`, then the parts render in the spine's order with the chain total equal to the summary's chain cost.
- Given Kjedens regning, then the rows run Detaljist→Fabrikk with the own row «(deg)» and Kjeden under a rule, unsorted.
- Given 320, 360 and 1440 px, then there is no page scroll, one primary button and no axe violation.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- layers: blind hunter and edge-case hunter only (the orchestrator caps reviewers at two); verification-gap and intent-alignment skipped.
- verdicts: 25 findings — high 0, medium 2, low 18, false 5, maybe-false 0
- findings:
  - `[low]` `[reject]` blind: `advance` and `switch_to_rule_based` can complete the last Week, and then `record_step` emits `user`/`session`, which their registry rows do not list. In a Class game those commands already emit `session` through `_commit_change`, and the registry's footer says Lecturer-overview Games add it. The registry test runs them on simulations, where nothing is recorded. The `games.finish` comment now names the step's topics. Changing the runners is more than a direct correction.
  - `[medium]` `[patch]` blind: `class_game` went to every Student in the occupancy history, also one moved to another Game before the start. Fixed: `_record_class_game_step` keeps only Students whose `games.service.student_game` for the Class session is this Game.
  - `[low]` `[reject]` blind: a Game whose `verify_finished` keeps raising is retried every minute, and 20 such Games would block the rest. Only `rules_version_unsupported` can raise for a finished Game, and only for a version whose package is removed (`rules_versions_without_package` lists these). A failure marker adds state.
  - `[low]` `[reject]` blind: `assert isinstance` in `_verify_finished`. This is the sweep's existing adapter pattern (`_purge_rate_limit_windows`), and the item is always the `str` that `find` returns.
  - `[low]` `[patch]` blind: `RoleCost.role` was a plain `str`, so `result.ts` cast it. It is now the engine `Role` (the existing `Role` schema), and the cast is gone. Rejected part: the published schema name is `GameResult`, not `*Out`. That is naming only.
  - `[low]` `[patch]` blind: a `ViewError` other than `game_not_finished` from `chain_result` became a 500. A 404 now answers `None`, which is the uniform 403.
  - `[false]` `[reject]` blind: «Gå til Debrief» leads to Hjem. The story's AC asks for exactly this: one route constant to Hjem until Epic 9.
  - `[low]` `[patch]` blind: `GameEnd` hard-coded the ids `chain-total`/`chain-bill`. It now uses `useId`. `ChainBill` already takes its `titleId` from the caller.
  - `[low]` `[reject]` blind: `position: relative` on `<tr>` was uneven in older Safari. Current Chromium, Firefox and Safari position against the row, and the Playwright screenshots at 360 and 1440 px show the bars across the row.
  - `[medium]` `[patch]` blind: the end labels in `lager`/`restordre` on their own tints measured 4.07:1 and 3.98:1, below AA for 13 px text. Each label now has a `paper` halo (`paint-order: stroke`), so the series colour stands on white (5.5:1 and up).
  - `[false]` `[reject]` blind: `endPlaces` can push the holding label out of a small plot. The plot is always `CHART_LINES` (11) font sizes high, so `base − plotTop` is about 8.3 font sizes, well above the 2.4 the fallback needs.
  - `[low]` `[reject]` blind: `aria-expanded` on the chart/table toggle. It states the table's shown state correctly. Neither swap moves focus, as with «Kostnad så langt».
  - `[low]` `[reject]` blind: chart points use bare `Number()`, which a malformed value turns into NaN. The api's money fields are pydantic decimals and always decimal strings.
  - `[low]` `[patch]` blind: the new `finished`/`toResult` keys split the Spillkort doc comment from `card`. Moved above that comment.
  - `[low]` `[reject]` blind: fragile test checks. The fixture amounts are multiples of 0.50, so they are exact in floats. `games_db` empties Games per test, so `== 1` holds. The key check guards against names, demand and settings keys.
  - `[low]` `[reject]` blind: the `pre_play_gate=False` path has no test. No purpose seats Students with the gate off until Story 6.20, whose spec covers it.
  - `[low]` `[patch]` blind: `result-classic.json` had no trailing newline. Added. Rejected part: `__all__` order, which was not sorted before this change.
  - `[low]` `[patch]` edge: a Student moved before the start gets `class_game`. Same root and same fix as the blind row above.
  - `[low]` `[reject]` edge: registry drift for `advance`/`switch_to_rule_based`. Same as the blind row.
  - `[low]` `[reject]` edge: endless retries of a failing check. Same as the blind row.
  - `[false]` `[reject]` edge: a finished Game with no opened Weeks slices the wrong Orders. `commands.start` opens Week 1 in the transaction that starts the Game, and a Game finishes only by running its last opened Week.
  - `[low]` `[patch]` edge: a `game_not_found` from `chain_result` became a 500. Same fix as the blind row.
  - `[false]` `[reject]` edge: an unknown role string renders `undefined`. The roles come from `settings.roles` (the engine `Role`), and the schema now says so.
  - `[false]` `[reject]` edge: a small plot overlaps the end labels. Same refutation as the blind row.
  - `[low]` `[reject]` edge (claim): `tests/ops/test_sweep.py` is not touched. The due action's find, act and idempotency are tested in `tests/sessions/test_game_end.py`, on a real finished Class game. The failing-item path is the sweep's generic one, which `test_sweep.py` already tests.

## Design Notes

Founder-level calls, taken here with no human in the loop:
- «Se kjedens totalkostnad» is the Hjem Lenke (draft).
- The finished screen ignores `briefing_first`.
- The split bar's width is relative to the largest Role sum.
- The end labels read «Restordre 1 365,00» and «Lager 901,00», each in its band's colour, so the cost kind does not rest on colour alone.
- `nextAction` is unchanged. `GameAction` itself shows a finished game's line and Lenke, so the starting-task screen keeps «Til Hjem» for a finished game.
- `useSize` moved from `cost-panel-view.tsx` to `lib/box-size.ts`, so the shared `ChainCostChart` can measure itself.
- The live e2e test uses a 2-Week game.
- The sweep verifies at most 20 Games per minute.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/sessions/test_game_end.py tests/games/test_policy.py tests/ops/test_sweep.py tests/games/test_registry.py -q` -- pass
- `cd frontend && npx tsc --noEmit && npx vitest run src/modules/games src/components` -- pass
- `cd frontend && npx playwright test e2e/game-end.spec.ts e2e/student-home.spec.ts e2e/homes.spec.ts` -- pass

## Auto Run Result

Status: done

**Summary.** A finished Class game now ends on «Spillet er ferdig».
- **Backend.**
  - `games.policy` has two new columns. `records_class_game_step` and `pre_play_gate` are on for `class` and off for `simulation`. The pre-play gate of Stories 6.2/6.5 now reads `StudentGame.pre_play_gate`.
  - In the same transaction, `games.commands.finish` records `progress` `class_game` for every Student in the occupancy history whose Class game is this Game. A Student whose Seat an AI player took over is included. A Student moved away before the start is not.
  - The sweep's new due action `games.verify_finished` checks up to 20 unchecked finished Games per minute, one transaction each.
  - The new `GET /api/me/games/{id}/result` gives cost per Role (Detaljist→Fabrikk), the chain total and the chain's running cost per Uke, built from the engine's `seat_detail`. It answers 409 `game_not_finished` before the end and 403 for every other game.
- **Frontend.**
  - The play route shows, in order: «Spillet er ferdig», «Grossist, Spill 17», «Kjedens totalkostnad», «2 266,00 kr», «Fire Roller, to kostnadsarter, hele spillet.», Kjedens regning, Kjedens kostnad over tid with «Vis som tabell», the Debrief line, and the one primary «Gå til Debrief» (`DEBRIEF_PATH` leads to Hjem until Epic 9).
  - The screen has a slot for Epic 8's note.
  - Hjem shows «Spillet er ferdig.» with the Lenke «Se kjedens totalkostnad». Stegene moves on to Debrief.

**Files.**
- `backend/app/modules/games/policy.py` -- the two columns.
- `backend/app/modules/games/commands.py` -- `finish` records the step (`_record_class_game_step`).
- `backend/app/modules/games/repo.py`, `service.py` -- `purpose` in `student_seats`, `StudentGame.pre_play_gate`, `unchecked_finished_game_ids`, and the `chain_result`/`GameResult` exports.
- `backend/app/modules/games/views.py`, `schemas.py` -- `chain_result`, `GameResult`, `RoleCost`, `CostSum` and `ChainWeekCost`.
- `backend/app/modules/ops/sweep.py` -- the `games.verify_finished` due action, placed before the deadline reminders, which stay last.
- `backend/app/modules/sessions/service.py`, `schemas.py`, `routes.py` -- the gate via the policy, `student_result_of`, and `getMyGameResult`.
- `backend/app/platform/events/registry.py` -- the comment on `games.finish`.
- `backend/tests/sessions/test_game_end.py` (new), `tests/games/test_policy.py` -- new tests. `tests/test_imports.py` now allows `games` to import `progress.service` (AD-16).
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerated.
- `frontend/src/components/chain-bill.tsx` and `chain-cost-chart.tsx` (new, shared for Epic 9). `ChainBill` has the `extraRows` slot.
- `frontend/src/components/charts/cost-area.tsx` -- `endLabels` with a `paper` halo, and `endPlaces`.
- `frontend/src/lib/box-size.ts` (new) -- `useBoxSize`, moved out of `cost-panel-view.tsx`.
- `frontend/src/modules/games/result.ts`, `game-end.tsx` (new), `api.ts` (`useGameResult`), `play-page.tsx` and `game-action.tsx` -- the end screen and the Hjem finished line.
- `frontend/src/modules/identity/homes.ts` -- `DEBRIEF_PATH`.
- `frontend/src/copy/nb.ts` -- the new strings.
- Tests: `result.test.ts`, `charts.test.tsx`, `components.test.tsx`, `e2e/game-end.spec.ts` (new), and the `gameSettings` option of `e2e/support/live-game.ts`.

**Review.** Two layers (blind, edge case) reported 25 findings: high 0, medium 2, low 18, false 5.
- Patched (2 medium, 7 low):
  - only this Game's own Students get the step (medium)
  - a halo under the end labels for contrast (medium)
  - `RoleCost.role` is now `Role`
  - a 404 from `chain_result` becomes the uniform 403
  - `useId` in `GameEnd`
  - the copy comment order
  - the JSON newline
  - the moved-Student and 404 rows of the edge layer share the fixes above
- Deferred: none.
- Rejected: the rest, each with its reason in the triage log.

**Follow-up review:** false. Two medium entries were patched, both local and covered by the rerun tests.
- The moved-Student filter reuses `games.service.student_game`, the one way to find a Student's game.
- The halo is a presentation attribute.
- No high finding.

Patched by verdict: medium 2, low 7.

**Founder-level decisions taken (no human in the loop).**
- The Hjem copy for a finished game: «Spillet er ferdig.» and the Lenke «Se kjedens totalkostnad» [ASSUMPTION]. The Lenke is not a primary button.
- The end screen shows whatever `briefing_first` says.
- The split bar is drawn across the whole row. Its length is the Role's sum over the largest Role sum.
- The end labels read «Restordre 1 365,00» / «Lager 901,00» in the series colours, on a white halo.
- A Student moved to another Game before the start does not get this Game's `class_game` step.
- The sweep verifies at most 20 Games a minute.
- The live e2e test uses a 2-Uke game with 1 Student, set through the Class session's settings.
- Captions and SVG titles are drafts in `nb.ts`.

**Verification.**
- Backend: the full suite passed (2746 tests, 65 s). `ruff check` and `ruff format` are clean. No migration.
- Frontend: `tsc`, Vitest (687 passed), `check:copy`, the colour lint and the Next build (compose image) all passed.
- Playwright:
  - After the patches, `game-end`, `student-home`, `homes`, `game-card`, `game-start`, `cost-panel`, `order-confirm`, `week-advance`, `seat-status` and `live-updates` passed (84 tests).
  - Before the patches, the same set plus `starting-task`, `briefing`, `order-field`, `order-failures`, `week-table`, `week-transition`, `guided-week`, `chain-band` and `graph-over-table` passed (171 tests).
  - `game-end` ran twice more with `--repeat-each=2`, with no flake.
- New tests over 1 s:
  - `test_the_last_order_finishes_the_game_and_records_every_student_ever_seated` takes about 1.5 s.
  - `test_the_result_is_the_chain_per_role_and_week_only_once_finished_and_checked_later` takes about 1.9 s.
  - Each sets up a 6-Uke Class game; that setup is about 2.5 s, the same as `test_play.py`'s.
  - The e2e live test takes about 3–5 s.
  - No fixed sleeps.

**Residual risks.**
- No test moves a Student to another Game and then finishes both Games. The filter rests on `student_game`, which Story 6.1's tests cover.
- When `advance` or `switch_to_rule_based` completes the last Week of a Class game, it emits `user` and `session` through the step. Their registry rows list `game` only, as they did for `session` before this change.
- A Game whose check keeps raising is tried again every minute.

Visible screens changed: the play route of a finished game («Spillet er ferdig»), and Hjem's line for a finished game.
