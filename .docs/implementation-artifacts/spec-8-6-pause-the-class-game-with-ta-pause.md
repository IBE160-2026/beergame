---
title: 'Story 8.6: Pause the Class game with «Ta pause»'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '5fe60c59c8210282bb88e78006478db07efdb353'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-8-context.md'
warnings: [oversized]
deferred: []
---

<intent-contract>

## Intent

**Problem:** A Class game group that agrees to stop for now has no way to stop the Inactivity limit from handing an absent Student's Seat to an AI player, and the Oversikt has no `paused` status (Story 7.1 left it for Epic 8). Story 8.5's review also left two UI defects: the Varselbånd's «KI-spiller satt inn for …» line outlives the band's next game, and Spillstyring keeps a Seat marked as pressed after a failed request.

**Approach:** Migration 0056 gives `games` the Pause columns and `game_summaries` the pause state. A new `games.commands.pause(game, *, actor)` writes them; a Student's `place_order` clears them; `rules.game_status` returns `paused` and `rules.can_take_over` refuses the automatic Takeover while paused. `POST /api/me/games/{game_id}/pause` exposes it; Spill and Hjem show «Ta pause» with the in-place Pausevalg and the pause lines; the Oversikt gets the «Pause» group, «herav n pauset» and drops paused games from the Varselbånd.

## Boundaries & Constraints

**Always:**
- Migration `0056_game_pause.py`: `games.paused_at timestamptz NULL`, `paused_by uuid NULL`, `resume_at timestamptz NULL` (empty until 8.7), `pause_ended_at timestamptz NULL`, `pause_ended_by uuid NULL` (the last Pause's end, for «Pausen er over»), check `paused_by IS NULL OR paused_at IS NOT NULL` and `resume_at IS NULL OR paused_at IS NOT NULL`; `game_summaries.paused_at`, `paused_by`; the status check gains `paused`. No backfill: no Game can be paused before 0056 (recorded in the module docstring and the 7.1 backfill test stays as it is).
- Only `games.commands` writes the columns, under the Game row lock, in one transaction with `_commit_change`. `pause(game_id, *, actor)`: refusals 404 `game_not_found`; 409 `pause_not_allowed` (policy `pause` false), `game_not_running` (not started), `game_finished`, `seat_not_yours` (the actor is not the Student of any Seat's latest occupancy row), `already_paused` with `fields.acted_by = {kind: "student"|"staff", user_id}` and `fields.acted_at` = `paused_at` (Story 8.5 shape; kind `staff` only once 8.7 lets staff pause). Writes `paused_at` = the transaction's database clock, `paused_by` = actor, clears `pause_ended_*`; leaves `lifecycle` and every due time unchanged. Audit `game.paused` (FR-3/spine: Pause by a person). Events: registry `games.pause: {game, session, user}`; `user:<id>` for every Student holding a Seat.
- `place_order` with `decided_by = student` on a paused Game sets `paused_at`, `paused_by`, `resume_at` to NULL and `pause_ended_at` = now, `pause_ended_by` = the ordering Student's user id (the Seat's occupant in force), in the same transaction, and tells every seated Student (`user:<id>`). `view_week` never ends a Pause (open-assumptions: opening a Guided Week is not an Order).
- `rules.game_status`: a `running`/`playing_out` Game with `paused_at` set is `paused` (before the waiting rule). `rules.can_take_over`: the `system` actor gets `game_paused` while paused; `staff` is not limited. The sweep's finder skips paused Games through that same check; `ops.sweep.TAKEOVER_RACES` adds `game_paused`. Due times are never moved; the Play deadline is untouched.
- `overview.recompute` stores `paused_at`/`paused_by` (ids only); a paused Game has empty `waiting_for`. `pause` joins the 7.1 recomputation test and `test_registry`.
- Student views: `TableStatus`/`TableStatusOut` and `StudentGameOut` gain `can_pause: bool` (Class game running, policy `pause`, not paused, the viewer holds a Seat now as a Student) and `pause: {state: "paused"|"ended", name: str|null, mine: bool} | null` — `paused` while paused (name of `paused_by`); `ended` when `pause_ended_at` is at or after the open Week's `opened_at` (name of `pause_ended_by`); else null. Names through the existing Student name resolver.
- Staff views: `OverviewGameOut` gains `paused_at` and `paused_by` (name via `classes.actor_names`); `OverviewCountsOut` gains `paused`, and `running` counts paused games too («15 pågår (herav 2 pauset)»). The Varselbånd and `next_change_at` consider only `waiting` games (paused drop out at once). Wall filter `running` also matches `paused` (backend `_matches` and frontend `filterGroups`).
- UI: «Ta pause» secondary `Button` under Setestatus on Spill and Hjem, ≥ 44 px, full width below 1024 px. The Pausevalg opens in place: the two epic lines, primary «Ta pause uten avtalt tid», link-styled «Avbryt»; focus moves to the primary on open; «Avbryt» returns focus to «Ta pause». Success: the pause line shows. `already_paused`: the form closes and the pause line (read again) shows. Other refusals: inline `ActionError` in the form. The pause line sits above Setestatus in a polite live region: «Pause, satt av Sara.», «Pause, satt av deg.», «Pausen er over. Sara har bestilt.», «Pausen er over. Du har bestilt.»; nothing about Uker.
- Oversikt: group «Pause» between Venter and Pågår (wall, list, table order); row line «Pause siden ma. 14:10, satt av Sara.» (Europe/Oslo); wall/table status word «Pause». Spillinnsikt status word «Pause»; Spillstyring still shows its per-Seat actions on a paused game.
- 8.5 follow-ups: the Varselbånd's result line survives the move the press itself causes and clears on the band's next change of game (or of its absence); Spillstyring forgets a Seat's pressed mark when its request fails for any reason but `takeover_exists`, so the row then follows the api.
- Copy in `nb.ts`; strings not verbatim in the epic/EXPERIENCE are `[ASSUMPTION]`. Regenerate `openapi.json`/`schema.ts`.

**Never:** no agreed time, `resume`, `set_agreed_time` or staff Pause controls (8.7); no peer «Sett inn KI-spiller» (8.8); no change to `turn_times` inputs; no Pause in a Lecturer's test Game or simulation; no change to the demo Class; no waiting on real time in tests; no comparison of DB time with host time.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Pause | running Class game, Student holds a Seat | `paused_at`/`paused_by` set, lifecycle same, status `paused`, version +1, audit row | — |
| Second pause | already paused by Sara | nothing written | 409 `already_paused`, `acted_by {student, Sara}`, `acted_at` |
| Sweep while paused | Seat past `takeover_due_at` | finder finds none; command refuses `game_paused`; due times unchanged | race, logged as skipped |
| Order ends it | paused, another Student orders | Pause columns NULL, `pause_ended_*` set, line «Pausen er over. Jonas har bestilt.»; overdue Seat taken at next sweep | — |
| Guided view | paused, Student opens Guided Week | still paused | — |
| Not seated | Student whose Seat was taken over, or never held one | — | 409 `seat_not_yours` |
| Not started / finished | lifecycle not running | `can_pause` false | 409 `game_not_running` / `game_finished` |
| Test Game | `lecturer_test` purpose | `can_pause` false | 409 `pause_not_allowed` |

</intent-contract>

## Code Map

- `backend/migrations/versions/0056_game_pause.py` (new) after `0055_seat_reclaims.py`; 0051/0053 for summary-column style.
- `backend/app/modules/games/models.py:82-120` `games`, `:341-367` `game_summaries` -- columns, checks.
- `backend/app/modules/games/schemas.py:39` `GameStatus` (+`PAUSED`), `:578-623` `TableSeat`/`TableStatus` (+`can_pause`, `pause`).
- `backend/app/modules/games/rules.py:45-110` -- `can_take_over` (`game_paused`), `game_status` (`paused`).
- `backend/app/modules/games/commands.py` -- `_commit_change` 246; `_place` 1185 (clear on student Order); `place_order` 1360 (tell seated Students); `takeover` 1700 / `request_reclaim` 1855 as the model; `_acted` 1842; `seated_students`; `__all__`.
- `backend/app/modules/games/repo.py` -- `lock_game` 49 returns the row (new columns come with it); add `set_pause`, `end_pause`; `upsert_summary` 1078; `due_takeover_turns` 642.
- `backend/app/modules/games/overview.py` -- `recompute` adds `paused_at`, `paused_by`.
- `backend/app/modules/games/views.py:296` `table_status` -- `can_pause`, `pause`; `_open_turns` 372 (opened_at of the open Week).
- `backend/app/modules/games/service.py:644-729` -- `ClassGameSummary.paused_at/paused_by`; `due_takeovers` 181 (unchanged: uses `can_take_over`).
- `backend/app/modules/ops/sweep.py:117` -- `TAKEOVER_RACES` + `game_paused`.
- `backend/app/platform/events/registry.py` -- `games.pause`.
- `backend/app/modules/sessions/{service.py _game_out 1301/student_play_of 1458/reclaim_own_seat 1590 (pattern), schemas.py TableStatusOut 520/StudentGameOut 482/OverviewGameOut/OverviewCountsOut 837/WallStatus 1054, overview.py class_overview 67/_next_due 128/_alert 141/_game_out 263/_matches 518, routes.py (reclaim route pattern)}`.
- `frontend/src/modules/games/{api.ts (pauseGame), pause-view.tsx (new: PauseLine, PauseControl), play-page.tsx:371-410, student-hjem.tsx:229-233, overview.ts (groupsOf, headline, STATUS_WORD, GROUP_STATUS, statusCounts, wallGroups, pauseText), overview-page.tsx GameRow 419, overview-band.tsx, spillstyring.tsx 166-199, insight-page.tsx status word}`, `frontend/src/modules/sessions/dates.ts` (weekday + time), `frontend/src/copy/nb.ts` (homes.student, overview.groups/counts, wall.status), `frontend/src/lib/api/{openapi.json,schema.ts}`.
- Tests: `backend/tests/games/test_takeover.py` (`class_game`, `due_of`), `test_game_summaries.py`, `test_registry.py`, `tests/sessions/test_reclaim_view.py` (api pattern); Vitest `seat-status.test.tsx`, `spillstyring.test.tsx`, `overview*.test.ts`; e2e `reclaim.spec.ts` (stub pattern), `overview.spec.ts`, `varselband.spec.ts`, `support/play.ts`.

## Tasks & Acceptance

**Execution:**
- `0056_game_pause.py`, `models.py`, `schemas.py` -- columns, checks, `GameStatus.PAUSED`.
- `rules.py`, `repo.py`, `commands.py`, `overview.py`, `registry.py`, `sweep.py` -- `pause`, clear on Order, status, Takeover refusal, summary, events.
- `views.py`, `games/schemas.py`, `games/service.py`, `sessions/{schemas,service,overview,routes}.py` -- student `can_pause`/`pause`, route `POST /api/me/games/{game_id}/pause` (returns `StudentGameOut`; 409 refusals with `fields`), staff `paused_at`/`paused_by`, counts, filter.
- `frontend/src/lib/api/*` -- regenerate. `frontend/src/...` -- Pausevalg, lines, Oversikt group and counts, band/Spillstyring fixes, copy.
- Backend tests `tests/games/test_pause.py` (matrix rows, events, audit, sweep, summary recomputation, `game_status`/`can_take_over` pure cases) and `tests/sessions/test_pause_view.py` (route, views for all four Students, ended line, Oversikt counts/alert/filter). Vitest: pause control states and lines, `groupsOf`/`headline`/`filterGroups` with paused, band line lifecycle, Spillstyring after a failed press. e2e `frontend/e2e/pause.spec.ts` (stubbed): Pausevalg focus/Avbryt, paused and ended lines on Spill and Hjem, axe and reflow at 320, 360, 1440; Oversikt «Pause» group placement and counts.

**Acceptance Criteria:**
- Given a Student in a running Class game that is not paused, when they open Spill or Hjem (ordered or not), then «Ta pause» shows under Setestatus; it is absent in a test Game, a finished game and a paused game.
- Given «Ta pause», when pressed, then the Pausevalg opens in place with no date/time field, the two lines, the primary «Ta pause uten avtalt tid» focused and «Avbryt», which returns focus to «Ta pause».
- Given a confirmed Pause, when any of the four Students opens Spill or Hjem, then «Pause, satt av Sara.» sits above Setestatus in a polite live region; after another Student's Order it reads «Pausen er over. Jonas har bestilt.».
- Given a paused game, when the Lecturer opens the Oversikt, then it is in «Pause 1» between Venter and Pågår with «Pause siden … , satt av Sara.», the headline reads «… pågår (herav 1 pauset)», and the Varselbånd does not name it.
- Given the Varselbånd's press result, when the band later moves to another game, then the result line is gone; given a failed Spillstyring press, then the row follows the api again.
- Given 320, 360 and 1440 px, when the Pausevalg, the paused and the ended states show, then no horizontal scroll and axe passes.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- Layers: blind hunter, edge-case hunter, verification gap, intent alignment (Sonnet, as the orchestrator asked). All four hand-backs dropped; findings read from `review-{blind,edge,verification,intent}-8-6.md` in the session scratchpad. The diff was taken against the baseline `5fe60c5`; the orchestrator's own commits on `epic-8` since then (sprint, log and runbook files) are not this change.
- verdicts: 39 findings — high 0, medium 1, low 31, false 7, maybe-false 0
- findings:
  - `[false]` `[reject]` blind-1: «Uten det har hver av dere sin vanlige ventetid …» promises a wait the code does not give after a Pause. The line is the epic's verbatim copy, and EXPERIENCE.md → Pausevalg → End says the clock kept running and a Seat whose limit has run is taken at once; the code does exactly that.
  - `[low]` `[reject]` blind-2: no audit row when a Pause ends. The end is a Student's Order, stored with its time in `seat_weeks`; the spine audits the person-triggered Pause itself, which `game.paused` records.
  - `[low]` `[reject]` blind-3: a Pause set in a Guided Week lasts until the next Student Order. open-assumptions.md decides that opening a Guided Week does not end it; the Week still completes by views, and the next Order ends it. The Lecturer's «Avslutt pausen» is Story 8.7.
  - `[low]` `[reject]` blind-4: `already_paused` calls a Student «staff» when their Seat was taken over meanwhile. Only the api field is affected, and only after a staff Takeover of the pauser's own Seat during the Pause; the web app names who paused from the view read again, never from `kind`.
  - `[low]` `[patch]` blind-5: a Game that finished under a Pause kept `paused_at`/`paused_by` in its summary. `overview.recompute` now stores them only while the status is `paused`.
  - `[low]` `[reject]` blind-6: `_pause_by` reads `playing_out` while `pause` refuses it. `playing_out` is Story 8.14's state, which clears the Pause; showing the line while it plays out does no harm.
  - `[low]` `[reject]` blind-7: a paused game's row hides whom it waits for. EXPERIENCE.md asks for since when and by whom; the status rule puts `paused` before `waiting`.
  - `[low]` `[reject]` blind-8: «Pause siden ma. 14:10» has no date. It is EXPERIENCE.md's own form (Spillinnsikt → Paused).
  - `[low]` `[patch]` blind-9: Hjem could stay stepped back when the game block unmounts with a form open. `GameBlock`'s effect now tells Hjem `false` on cleanup.
  - `[low]` `[patch]` blind-10: focus fell to the page when another Student's Pause closed an open Pausevalg. The closing now moves focus to the pause line.
  - `[low]` `[reject]` blind-11: frontend tests are server-rendered only. The project has no DOM test setup; the flows are in `e2e/pause.spec.ts` (focus, «Avbryt», confirm, both lines, Hjem's step-back).
  - `[low]` `[patch]` blind-12: no test that an AI player's Order leaves the Pause. Added `test_an_ai_players_order_does_not_end_the_pause` (a staff Takeover while paused). Concurrency and re-pause tests are rejected: the Game row lock is the same as every command's.
  - `[false]` `[reject]` blind-13: an unrelated log hunk in the change. It is the orchestrator's commit on the branch after the baseline, not this change; the 8.5 follow-ups are in the intent; the generated api files are left out by design.
  - `[low]` `[reject]` blind-14: no «Pause» Status filter. Paused games answer to «Pågår», as the headline counts them («pågår (herav n pauset)»).
  - `[low]` `[reject]` blind-15: no index for `paused_at IS NULL`, and the ended pair is not checked as a pair. The filter is on a join the sweep already makes; only `games.commands` writes the pair, always together.
  - `[low]` `[reject]` edge-1: as blind-4.
  - `[low]` `[reject]` edge-2: a staff Takeover of every Student Seat leaves a Pause no Student can end. Rare, and the game still plays (AI players order); the Lecturer's «Avslutt pausen» is Story 8.7. The finished case is patched with blind-5.
  - `[false]` `[reject]` edge-3: an overdue Student dodges the Takeover by pausing. FR-89 says no automatic Takeover while paused, whoever paused; the Student who presses is present and can order.
  - `[false]` `[reject]` edge-4: `paused_at` set with `paused_by` NULL hides the line. Unreachable: `pause` always writes both.
  - `[low]` `[reject]` edge-5: the ended line is hidden when the ending Order also opened the next Week, where the spec says «at or after». The Design Notes bound the line by the Week it ended in; the only fix would edit this spec.
  - `[low]` `[patch]` edge-6: as blind-9.
  - `[low]` `[reject]` edge-7: a refusal that also flips `can_pause` closes the form before its line is read. Only `game_finished`/`seat_not_yours` races do this, and the page then shows the game's new state.
  - `[low]` `[patch]` edge-8: after `already_paused` the focus move could give up before the read again drew the line, and the fallback error flashed. The form now closes after the read again, and `already_paused` shows no error.
  - `[low]` `[patch]` edge-9: a result set after the read again (someone came first) could find the band already moved, so the line outlived one more move. `onResult` now counts that move as the press's own.
  - `[low]` `[reject]` edge-10: a request that timed out after the server committed forgets the press, so no result line shows. The Seat's mark («KI satt inn av …») shows the outcome on the same page.
  - `[low]` `[patch]` edge-11: `takeover`'s docstring did not list `game_paused`. Added.
  - `[low]` `[reject]` edge-12: the spec's Tasks name a Vitest for the failed press. It is covered in Playwright (`spillstyring.spec.ts`); the only fix would edit the spec.
  - `[low]` `[patch]` verification-1: a paused game's wall row text was untested. `pause.test.tsx` asserts its `detail`, `shortDetail` and `rowName`.
  - `[low]` `[patch]` verification-2: Spillstyring on a paused game was untested. `pause.test.tsx` renders it for `paused`.
  - `[low]` `[patch]` verification-3: Hjem's step-back while the Pausevalg is open was untested. `pause.spec.ts` opens it on Hjem and counts one primary.
  - `[low]` `[reject]` verification-4: the band's effect is tested only through `afterBandMove`. A rendered test needs two live band moves; the pure rule and its wiring are small.
  - `[low]` `[reject]` verification-5: the sweep's `game_paused` race branch never runs in a test. The neighbouring race codes are untested the same way; the finder excludes paused games first.
  - `[medium]` `[patch]` verification-other-1: `test_migrations.HEAD` was still `0055`, so the migration test failed. Bumped to `0056`; the test passes.
  - `[false]` `[reject]` verification-other-2: the counts fixtures. The reviewer found no problem.
  - `[low]` `[patch]` intent-1: the "another game" reading of the band rule; the taken path consumed a move early. Patched with edge-9.
  - `[low]` `[reject]` intent-2: `takeover_exists` keeps its row. Its line names who came first (Story 8.5's AC); a refusal that put nothing in and named no one is forgotten.
  - `[false]` `[reject]` intent-3: scope beyond three columns. The ended pair is needed for «Pausen er over …» after a reload (Design Notes); the AC names the line.
  - `[false]` `[reject]` intent-4: «Pågår» takes paused games. The AC fixes «herav 2 pauset»; the filter follows the count.
  - `[low]` `[reject]` intent-5: the follow-ups are tested at a helper (band) and one mocked e2e (Spillstyring). As verification-4 and edge-12.

## Auto Run Result

Status: done

**Summary.** A Student of a running Class game can pause it with «Ta pause». Migration 0056 gives `games` the Pause columns (`paused_at`, `paused_by`, `resume_at`, empty until 8.7) and who ended the last Pause and when (`pause_ended_at`, `pause_ended_by`). It gives `game_summaries` `paused_at`/`paused_by`, and its status check `paused`. `games.commands.pause(game, *, actor)` writes the Pause under the Game row lock, with the audit row `game.paused`, `game`/`session` events and `user` events for every seated Student. It refuses `pause_not_allowed`, `game_not_running`, `game_finished` and `seat_not_yours`, and answers `already_paused` with Story 8.5's `acted_by`/`acted_at`. A Student's Order (`place_order`, `decided_by = student`) ends the Pause in its own transaction and tells every Student. A Guided-Week view does not end it (open-assumptions). `rules.game_status` says `paused`. `rules.can_take_over` refuses the `system` actor `game_paused`, and the sweep's finder also skips paused Games. Due times are never moved, so an overdue Seat is taken at the next sweep after the Order. Staff Takeover is not limited by a Pause.

`POST /api/me/games/{id}/pause` answers the game. Spill and Hjem get `can_pause` and `pause` (`paused`/`ended`, name, `mine`). On Spill and Hjem the pause line sits above Setestatus in a polite live region: «Pause, satt av Sara.», «Pause, satt av deg.», «Pausen er over. Jonas har bestilt.». It is filled after it is drawn, so it is read on load too. «Ta pause» sits under Setestatus and opens the Pausevalg in place: the two epic lines, the primary «Ta pause uten avtalt tid» (focused) and «Avbryt» (focus back). While the form is open, «Bekreft ordre» on Spill and the game's primary on Hjem step back to secondary.

The Oversikt groups paused games under «Pause» between Venter and Pågår, the longest paused first, with «Pause siden ma. 14:10, satt av Sara.». The headline reads «… pågår (herav n pauset)», and the «Pågår» filter takes paused games. The Varselbånd and `next_change_at` read only waiting games. Spillinnsikt reads «Pause» and keeps Spillstyring.

The 8.5 follow-ups: the band's result line now goes at the band's next move after the press's own move. Spillstyring forgets a press that put no AI player in and named no one, so its row then follows the api.

**Files changed**
- `backend/migrations/versions/0056_game_pause.py` (new), `backend/app/modules/games/models.py`: columns and checks.
- `backend/app/modules/games/{rules,commands,repo,overview,views,schemas,service}.py`: `is_paused`, the status, `game_paused`, `pause`, the end on a Student Order, the summary, `TablePause`/`can_pause`, `ClassGameSummary` pause fields, the finder filter.
- `backend/app/modules/ops/sweep.py` (`game_paused` race), `backend/app/platform/events/registry.py` (`games.pause`).
- `backend/app/modules/sessions/{schemas,service,overview,routes}.py`: `PauseOut`, `can_pause`/`pause` on `StudentGameOut` and `TableStatusOut`, the route, `paused_at`/`paused_by` on the Oversikt, `counts.paused`, the filter.
- `frontend/src/modules/games/pause-view.tsx` (new), `play-page.tsx`, `student-hjem.tsx`, `order-field.tsx` (`stepBack`), `overview.ts`/`overview-page.tsx` (group, lines, counts, filter), `overview-band.tsx`, `spillstyring.tsx`, `api.ts`; `frontend/src/modules/sessions/dates.ts` (`osloWeekdayTime`); `frontend/src/copy/nb.ts`; `frontend/src/lib/api/{openapi.json,schema.ts}` regenerated.
- Tests: `backend/tests/games/test_pause.py`, `tests/sessions/test_pause_view.py` (new); `test_registry.py`, `test_overview.py`, `test_migrations.py` (HEAD); Vitest `pause.test.tsx` (new) and fixture updates; e2e `pause.spec.ts` (new), `spillstyring.spec.ts` (failed press).
- `.docs/implementation-artifacts/epic-8-context.md`: recompiled (the spine had changed in 8.5).

**Review.** There were four Sonnet reviewers: blind hunter, edge case, verification gap and intent alignment. They returned 39 findings: 0 high, 1 medium, 31 low and 7 false.
- Patched (medium): `test_migrations.HEAD`.
- Patched (low): the stale pause fields on a finished game, Hjem's cleanup, focus when another Student's Pause closes the form, the `already_paused` flow, the band's move count on the taken path, the `takeover` docstring, and tests (AI Order keeps the Pause, the paused wall row, Spillstyring on a paused game, Hjem's step-back).
- Deferred: none.
- Rejected: the rest, each with its reason in the Review Triage Log.
- Follow-up review: not recommended (patched: high 0, medium 1, low 10 entries).

**Verification** (after the patches)
- Backend full suite `--maxprocesses=8`: 2953 passed, 4 skipped. ruff check and format are clean.
- Frontend: typecheck, Vitest (861 passed), `lint:colours`, `check:copy` and `next build` all pass.
- The stack was rebuilt after the last frontend change. Playwright `--workers=4` ran 182 tests over pause, spillstyring, overview, varselband, takeover, takeover-overview, reclaim, game-insight, live-updates, homes, student-home, seat-status, order-field, order-confirm, order-failures, week-table, week-advance, guided-week, game-card, cost-panel, chain-band, graph-over-table, week-transition and time-proposal. All passed, none on retry.
- axe and reflow pass at 320, 360 and 1440 px for the Pausevalg, the paused state (Spill and Hjem) and the ended state, and on the Oversikt with the «Pause» group.
- New tests over 1 s: `tests/sessions/test_pause_view.py::test_a_student_pauses_and_another_students_order_ends_it` (about 3.3 s: three Students through the api, Hjem, Spill, the Oversikt and two Weeks) and `test_only_a_student_of_the_game_may_pause_it` (about 1.2 s, a real short Class game).

**Decisions taken instead of the founder.**
- `pause_ended_at`/`pause_ended_by` beyond the epic's three columns, so «Pausen er over. Sara har bestilt.» survives a reload. The line shows until the next Week opens; an Order that also opens the next Week shows none.
- Only a Student who holds a Seat now may pause (a Student whose Seat was taken over may not). A Guided-Week view does not end a Pause, per open-assumptions.
- Staff «Sett inn KI-spiller» is not limited by a Pause, and Spillstyring stays on a paused game.
- A paused game counts in «pågår (herav n pauset)», and the «Pågår» filter takes it. It waits for no one on the Oversikt, and the band skips it.
- The audit row `game.paused` is written for a Student's Pause (spine: Pause by a person).
- Draft copy `[ASSUMPTION]`: «Pause, satt av deg.», «Pausen er over. Du har bestilt.», the unknown-name lines, the refusals, «Pause siden ma. 14:10, satt av Sara.» and «Pause» as the status word.
- The band's line goes at the band's second move after a press; Spillstyring keeps the row only for `takeover_exists`.
- Implemented in the builder's own context, as the orchestrator instructed.

**Residual risks.**
- With every Student Seat taken over by staff during a Pause, no Student can end it until 8.7's «Avslutt pausen» or 8.14's playout.
- The band effect and the Pausevalg's focus are covered by Playwright and pure helpers only; the project has no DOM unit tests.
- A visual check is left to the separate visual agent.

## Design Notes

`pause_ended_at`/`pause_ended_by` are two columns beyond the epic's three: «Pausen er over. Sara har bestilt.» must survive a reload and reach all four Students, and the open Week's `opened_at` bounds it, so it disappears when the next Week opens without a sweep. The Oversikt counts paused games as «pågår (herav n pauset)» (EXPERIENCE.md → Oversikt Live) while grouping them under «Pause» (EXPERIENCE.md → Grouping), so the `running` wall filter matches both. A paused game is not waiting: its `waiting_for` is empty and the band/`next_change_at` skip it; the stored due times stay, so after the Order ends the Pause the sweep takes an overdue Seat within the minute.

## Verification

**Commands:**
- `cd backend && uv run pytest -q tests/games/test_pause.py tests/sessions/test_pause_view.py tests/games/test_game_summaries.py tests/games/test_registry.py tests/games/test_takeover.py` -- pass
- `cd frontend && npx vitest run src/modules/games` -- pass
- Before commit: the full suites and the e2e specs named in the runbook.
