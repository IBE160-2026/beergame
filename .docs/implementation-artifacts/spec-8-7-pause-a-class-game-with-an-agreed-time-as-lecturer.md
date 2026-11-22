---
title: 'Story 8.7: Pause a Class game with an agreed time as Lecturer'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '7eaa5e1350a4a88ce2b7a2bf5aa431d97dd901b0'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-8-context.md'
warnings: [oversized]
deferred: []
---

<intent-contract>

## Intent

**Problem:** Only a Student can pause a Class game (Story 8.6), always without a time. The Lecturer cannot pause a game, agree when the group continues, change that time or end a Pause, so a group's agreed return time cannot govern when an absent Seat may get an AI player (FR-89 extension, UX-DR52). Story 8.5's visual check also found the «Spillstyring» title in `headline` where DESIGN.md says `label`.

**Approach:** `games.commands` gains a staff `pause` with an optional `resume_at`, `set_agreed_time` and `resume`. Each recomputes `insert_allowed_at` of the open Week's turns through `rules.turn_times`. Three Lecturer-only routes expose them. Spillstyring and the Varselbånd get «Pause spillet» with the in-place pause form, and Spillinnsikt gets the paused state with «Endre avtalt tid» and «Avslutt pausen». The Students' pause line names the Lecturer and the agreed time. A sweep action announces the agreed time once it is reached.

## Boundaries & Constraints

**Always:**
- Migration `0057_pause_agreed_time_reached.py`: `games.agreed_time_reached_at timestamptz NULL`, check `agreed_time_reached_at IS NULL OR resume_at IS NOT NULL`. No backfill (no `resume_at` exists before 0057).
- `commands.pause(game_id, *, actor, staff=False, resume_at=None, latest=None)`: the Student path stays as in 8.6 (no time is ever taken from a Student). With `staff=True` the seat check is skipped. `resume_at`, when given, must lie in `now < resume_at <= latest`, where `latest` is the Play deadline read share-locked in the transaction and falls back to `PROPOSAL_HORIZON` when there is none. Otherwise it refuses 422 `time_out_of_range`, the code Story 6.19 uses. `already_paused` keeps 8.6's `acted_by` shape and gives `kind` `staff` when a staff member paused.
- `set_agreed_time(game_id, resume_at | None, *, actor, latest)`: 409 `not_paused`, `game_finished`, 422 `time_out_of_range`. It writes `resume_at` (None clears it) and clears `agreed_time_reached_at`. `resume(game_id, *, actor)`: 409 `not_paused`. It clears `paused_at`, `paused_by`, `resume_at` and `agreed_time_reached_at`, and sets `pause_ended_at` = now and `pause_ended_by` = actor. All refuse 404 `game_not_found`, 409 `pause_not_allowed` and `game_not_running`. Each runs under the Game row lock with `_commit_change`, `user:<id>` for every seated Student, and an audit row: `game.paused` (with `resume_at`), `game.pause_time_set` or `game.resumed`. Registry entries `games.set_agreed_time`, `games.resume` and `games.reach_agreed_time` are added (`game`, `session`, `user`). All three join the 7.1 recomputation test and `test_registry`.
- Insert times: the three commands set `insert_allowed_at` on each open-Week turn that a Student holds and that has not ordered. They use `rules.turn_times` with `clock_start` = the stored `wait_started_at`, the frozen limit and `agreed_time` = the Game's `resume_at`. `_due_times` gains: with an agreed time and no clock, the insert time is the agreed time (open-assumptions: the agreed time stands when no clock runs). `takeover_due_at` is never moved. On `resume`, an insert time already at or before now stays: a right that has arisen survives the end (EXPERIENCE.md → Pausevalg → End). `_start_waits` passes a turn's own stored `insert_allowed_at` as `agreed_time`, so an agreed time set in this Uke survives the first Order (open-assumptions: it stays the insert time for that Week). A Student's Order that ends the Pause leaves insert times as they are.
- Sweep: `games.reach_agreed_time` finds paused Games with `resume_at <= now` and `agreed_time_reached_at IS NULL`. The command sets the marker under the lock, bumps the version and emits the events. It never ends the Pause and never runs a Takeover. Races (`not_paused`, `agreed_time_not_reached`) are skipped quietly.
- Authz: a new policy `games.pause` with account role LECTURER and Class staff role OWNER. The routes are `POST /api/games/{id}/pause` `{resume_at: datetime | null}`, `PUT /api/games/{id}/pause/agreed-time` `{resume_at: datetime | null}` and `DELETE /api/games/{id}/pause`. Each answers `GameInsightOut`. Anyone else gets 403, one answer (FR-5). The Student route takes no body.
- Views: `GameInsightOut` gains `pause: {paused_at, by: str|null, mine: bool, resume_at} | null`, `can_pause: bool` (the reader is the game's Lecturer, the Game is running and its policy has Pause) and `play_deadline`. `ClassOverviewOut` gains `can_pause` (the reader holds `games.pause` in the Class) and `play_deadline`. `PauseOut`/`TablePause` gain `staff: bool` (set or ended by someone who is not a Student of the Game) and `resume_at`.
- Student lines (UX-DR62): «Pause til to. 19:00, satt av faglæreren.» whenever `resume_at` is set, «Pause, satt av faglæreren.» for a staff Pause without a time, and the 8.6 lines otherwise. When the Lecturer ends the Pause: «Pausen er over. Faglæreren har avsluttet den.» [ASSUMPTION].
- UI form (`staff-pause.tsx`, new): the legend «Når fortsetter spillet?», the Dato and Klokkeslett fields and the checkbox «Uten avtalt tid». The two epic lines. Primary «Ta pause til to. 19:00» (date and time valid), «Ta pause uten avtalt tid» (box ticked), else «Ta pause». «Avbryt» as a link. In change mode the form is prefilled and its primary reads «Lagre avtalt tid to. 19:00» / «Lagre uten avtalt tid» [ASSUMPTION]. Range error «Velg et tidspunkt mellom nå og Spillfristen, {dato}.» (`rangeError`) on blur and on press, in the Ordrefelt error pattern. The api's `time_out_of_range` shows the same text. Focus goes to the first field on open, and «Avbryt» returns it to the opener. The result line replaces the form and takes focus («Pause til to. 19:00 er satt.», «Spillet har pause.» [ASSUMPTION], «Pausen er avsluttet.» [ASSUMPTION]).
- Spillinnsikt: Spillstyring shows the paused line «Pause siden ma. 14:10, satt av Sara.» / «… satt av deg.» followed by « Avtalt tid to. 19:00.» [ASSUMPTION] when there is one, then the secondary «Endre avtalt tid» and «Avslutt pausen». A running, unpaused game shows the secondary «Pause spillet». Only one in-place form is open at a time. The block title is `text-label`. An Assistant lecturer sees only the per-Seat rows.
- Varselbånd: when `can_pause`, the secondary «Pause spillet» sits after «Sett inn KI-spiller». Its form opens under the band, and while it is open «Send Melding» shows as secondary. After a pause the band moves on, and the result line stands under it as Story 8.5's does.
- Copy goes in `nb.ts`, regenerate `openapi.json`/`schema.ts`.

**Never:** no time from a Student; no automatic end of a Pause; no Takeover from the sweep at the agreed time; no change to `takeover_due_at`, the Play deadline or Story 8.6's Student flow; no peer «Sett inn KI-spiller» (8.8); no Tilrettelegging input (8.9); no change to the demo Class; no real waiting or DB-vs-host time comparison in tests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Lecturer pauses with time | running, Jonas unordered with a clock | Pause by the Lecturer, `resume_at` set, Jonas's `insert_allowed_at` = `resume_at`, due unchanged | — |
| Time out of range | `resume_at` ≤ now or > Play deadline | nothing written | 422 `time_out_of_range` |
| Change time on Student pause | Sara paused | `resume_at` set, `paused_by` stays Sara, line «Pause til … , satt av faglæreren.» | — |
| Not paused | running | — | 409 `not_paused` for change/end |
| End | paused with time | Pause columns cleared, ended line, insert times back to due unless already passed | — |
| Agreed time reached | sweep at `now ≥ resume_at` | marker set, version +1, events; still paused; no Takeover | race skipped |
| Order after agreed time | Sara orders | Pause ends, Jonas keeps insert time = agreed time | — |
| Assistant / Student | calls staff routes | — | 403 `forbidden` |

</intent-contract>

## Code Map

- `backend/app/modules/games/commands.py` -- `pause` 1920 (extend), `_paused_by` 1969 (kind via `seated`), `_start_waits` 1536, `_inactivity_limit` 1570, `propose_time` 2088 (range rule, `PROPOSAL_HORIZON`, callable `latest`), `takeover` (audit pattern); `__all__`.
- `backend/app/modules/games/rules.py:219` `_due_times` -- agreed time without a clock.
- `backend/app/modules/games/repo.py:391` `set_pause`/`end_pause`; `set_wait_times` 529; `week_turns_with_occupant`; add `set_agreed_time`, `set_insert_allowed`, `mark_agreed_time_reached`, `due_agreed_times`.
- `backend/app/modules/games/models.py:111-120` -- column and check.
- `backend/app/modules/games/views.py:298-402` -- `TablePause` `staff`/`resume_at`; `_pause_by`. `schemas.py:617`.
- `backend/app/modules/games/service.py:181` -- finder pattern; `game_insight` (pause fields); `announce`.
- `backend/app/modules/ops/sweep.py:187` -- new DueAction after `games.takeover`.
- `backend/app/platform/authz.py:109,156` -- `games.pause`. `platform/events/registry.py:39`.
- `backend/app/modules/sessions/{overview.py take_over_seat 466 / game_insight 375 / class_overview, routes.py 323, schemas.py PauseOut 482 / GameInsightOut 1054 / ClassOverviewOut 924, service.py _pause_out 1379 / _play_deadline_of 1733}`.
- `frontend/src/modules/games/{spillstyring.tsx, overview-band.tsx, pause-view.tsx pauseText, time-proposal.ts checkProposal/rangeError/refusedRange, api.ts, insight-page.tsx}`, `frontend/src/modules/sessions/dates.ts osloWeekdayTime`, `frontend/src/copy/nb.ts` (`spillstyring`, `homes.student.pause`), `frontend/src/lib/api/*`.
- Tests: `backend/tests/games/test_pause.py`, `tests/sessions/test_pause_view.py`, `test_registry.py`, `test_game_summaries.py`, `test_migrations.py` HEAD; Vitest `pause.test.tsx`, `spillstyring.test.tsx`; e2e `pause.spec.ts`, `spillstyring.spec.ts`, `support/live-game.ts`.

## Tasks & Acceptance

**Execution:**
- Migration, `models.py`, `rules.py`, `repo.py`, `commands.py`, `service.py`, `sweep.py`, `registry.py`, `authz.py` -- commands, insert times, sweep action.
- `views.py`, `games/schemas.py`, `sessions/{schemas,service,overview,routes}.py` -- views and routes; regenerate the api client.
- `frontend/src/modules/games/staff-pause.tsx` (new), `spillstyring.tsx`, `overview-band.tsx`, `pause-view.tsx`, `api.ts`, `nb.ts` -- form, controls, lines, title class.
- Tests: `tests/games/test_staff_pause.py` (matrix, recompute, sweep, audit, `_due_times` pure cases), `tests/sessions/test_staff_pause_view.py` (routes, authz, insight/overview/student lines). Vitest `staff-pause.test.tsx` (labels, check, lines). e2e `staff-pause.spec.ts` (Spillstyring pause with a time, change, end; band form focus and one primary; the Student line; axe and reflow at 320, 360 and 1440).

**Acceptance Criteria:**
- Given a running, unpaused game on Spillinnsikt or in the Varselbånd, when the Lecturer presses «Pause spillet», then the form opens in place with focus in Dato, and «Avbryt» returns focus. Under the band, «Send Melding» is secondary while the form is open.
- Given a confirmed Pause with a time, when the Students open Spill or Hjem, then «Pause til to. 19:00, satt av faglæreren.» shows. Spillinnsikt shows «Pause til to. 19:00 er satt.» focused, then the paused line with «Endre avtalt tid» and «Avslutt pausen».
- Given an Assistant lecturer, then no pause controls show and the routes answer 403.
- Given 320, 360 and 1440 px, when the form and the paused state show, then there is no horizontal scroll and axe passes.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
- Layers: blind hunter, edge-case hunter, verification gap and intent alignment (Sonnet, as the orchestrator asked). All four hand-backs dropped; the findings were read from `review-{blind,edge,verification,intent}-8-7.md` in the session scratchpad. The diff was taken against the baseline `7eaa5e1`. The orchestrator's own commits on `epic-8` since then (sprint and log files) are not this change.
- verdicts: 42 findings — high 0, medium 3 (one root cause), low 33, false 6, maybe-false 0
- findings:
  - `[low]` `[reject]` blind-1: «staff» is decided by exclusion from the game's Students. `table_status` counts every Student who held or holds a Seat, so only a Student whose Seat history is gone reads as the Lecturer. `_paused_by`'s current-seat test is Story 8.6's (its blind-4, rejected there). Storing the kind needs a column.
  - `[low]` `[patch]` blind-2: a Student's 409 `already_paused` carried the Lecturer's user id. `pause_own_game` now drops `user_id` when `kind` is `staff`. Test `test_a_students_refusal_never_carries_the_lecturers_id`.
  - `[low]` `[reject]` blind-3: the line keeps «Pause til to. 19:00» after the time passed. The Pause goes on, and the line states the agreed time (EXPERIENCE.md → Paused). What changes at that moment is the right to insert, which is Story 8.8's row. The sweep's version bump is what makes that row appear without a reload.
  - `[false]` `[reject]` blind-4: the title change is unrelated. It is the intent's second item (DESIGN.md: `label`).
  - `[low]` `[reject]` blind-5: a `not_paused` refusal vanishes with the form. The form closes because the view read again shows the game unpaused; the Lecturer then sees «Pause spillet», which states the new state.
  - `[low]` `[reject]` blind-6: without a Spillfrist, a time past the 90-day horizon reads «etter nå». A locked Class session has a Spillfrist, so this is rare, and the fix adds a branch and copy.
  - `[low]` `[patch]` blind-7: the band's form could reopen when the band came back to its game. An effect now closes it for good when the band's game changes. The result line stays until the next press, as Story 8.5's does.
  - `[false]` `[reject]` blind-8: no `time_factor` is passed. No factor exists before Story 8.9, which passes it to `turn_times` for every caller.
  - `[false]` `[reject]` blind-9: the insert time can lie after the due time once the Pause ends. That is the rule: the agreed time is the insert time for the Uke (open-assumptions). Automatic Takeover runs on the FR-36 clock after the Pause (EXPERIENCE.md → Pausevalg → End).
  - `[low]` `[reject]` blind-10: «Avslutt pausen» has no consequence line. EXPERIENCE.md gives it none; a line would be new copy beyond the story.
  - `[low]` `[patch]` blind-11: a PUT with `{}` cleared the time. `StaffPauseIn.resume_at` is now required (null for «Uten avtalt tid»), and the test asserts 422.
  - `[low]` `[patch]` blind-12: the sweep could mark a Game that no longer runs. The finder and `reach_agreed_time` now need `lifecycle = running`, and the sweep test covers `playing_out`.
  - `[low]` `[patch]` blind-13: test gaps. Patched with verification-1, verification-2 and verification-4. The rest (a migration downgrade test, Vitest interaction tests) is rejected: migrations are tested at HEAD, and the project has no DOM test setup.
  - `[low]` `[reject]` blind-14: the fields are `readOnly`, not disabled, with «Uten avtalt tid». Read-only fields are announced as such and keep their focus (UX-DR8), and the typed time comes back when the box is cleared.
  - `[false]` `[reject]` blind-15: an unrelated `.logs` hunk. It comes from the orchestrator's commits after the baseline, not from this change.
  - `[low]` `[reject]` blind-16: test helper duplication (`db_now`, the fixture re-export). This follows the suite's existing pattern; moving it has no named harm.
  - `[medium]` `[patch]` edge-1: a Pause without a time (a Student's, or a Lecturer's) recomputed the insert times with no agreed time. That took away an agreed time kept after an earlier Pause ended. `pause` now recomputes only with an agreed time. The test asserts a Student's later Pause keeps it.
  - `[low]` `[reject]` edge-2: changing the time after it passed withdraws the arisen right. The Lecturer sets the time on purpose. Only the end of a Pause keeps a passed right (EXPERIENCE.md → End).
  - `[low]` `[reject]` edge-3: last writer wins between two Lecturers. Each command runs under the Game row lock, and the views read again. An If-Match would be new api surface.
  - `[low]` `[reject]` edge-4: a Week that opens during a Pause with an agreed time gives its turns no insert time. The agreed time is for the Uke it was set in (open-assumptions), and the Lecturer can set it again.
  - `[low]` `[patch]` edge-5: same as blind-12.
  - `[low]` `[reject]` edge-6: a Pause in `playing_out` cannot be ended. Story 8.14's playout clears the Pause.
  - `[low]` `[reject]` edge-7: same as blind-1.
  - `[low]` `[patch]` edge-8: same as blind-2.
  - `[low]` `[reject]` edge-9: same as blind-3.
  - `[low]` `[patch]` edge-10: re-sending the current time after it passed gave 422. The no-change check now comes before the range check, and a test covers it.
  - `[false]` `[reject]` edge-11: the sweep's clock differs from the database clock. The sweep judges every due time on its own `now`, as the Takeover does (Issue #63's injected clock).
  - `[low]` `[reject]` edge-12: authz is checked before the command's transaction. This is the same pattern as Story 8.5's Takeover; a revocation in that window is rare.
  - `[false]` `[reject]` edge-13: same as blind-8.
  - `[medium]` `[patch]` edge-14 (claim): same as edge-1.
  - `[low]` `[reject]` edge-15 (claim): same as edge-6.
  - `[low]` `[patch]` verification-1: no test of a Lecturer who is only an Assistant lecturer in this Class. The test now asserts 403 on all three routes and `can_pause` false on Spillinnsikt and the Oversikt.
  - `[low]` `[patch]` verification-2: «Endre avtalt tid» was never saved in a test. The e2e now saves a new time and then «Uten avtalt tid», and checks the Student's line follows each live.
  - `[low]` `[reject]` verification-3: the form's server-refusal branches are untested. They need route stubs or DOM tests. The client check gives the same range text, and the backend refusals are tested.
  - `[low]` `[patch]` verification-4: hiding the controls from an Assistant lecturer was not asserted next to Seat rows or in the band. `staff-pause.test.tsx` now asserts both.
  - `[low]` `[patch]` verification-5: `_due_times` with no limit and an agreed time was not pinned. A pure case was added.
  - `[medium]` `[patch]` verification-other-1: same as edge-1.
  - `[low]` `[reject]` verification-other-2: the Oversikt «Pause n» filter and «Venter ellers» from the 8.6 log. The intent names only Story 8.7 and the title fix.
  - `[low]` `[reject]` verification-other-3: same as blind-1.
  - `[low]` `[reject]` intent-1: the Spill page's line is not tested on its own. Spill and Hjem render the same `PauseLine` from the same `TablePause`/`_pause_out`.
  - `[low]` `[reject]` intent-2: same as verification-other-2.
  - `[low]` `[patch]` intent-3: the band without `canPause` had no UI test. Covered by verification-4.

## Design Notes

The marker column `agreed_time_reached_at` makes the sweep's announcement idempotent (AD-9) without ending the Pause. The insert time for a Seat with no running clock is the agreed time, so the first Order in the Uke that ends the Pause leaves it in place (`_start_waits` reads the turn's own stored insert time). Spillinnsikt's client-side range check uses the browser clock only as a hint; the api judges again under the lock (AD-10). Spillinnsikt has no `server_now`, because that would break its ETag.

## Verification

**Commands:**
- `cd backend && uv run pytest -q tests/games/test_staff_pause.py tests/sessions/test_staff_pause_view.py tests/games/test_pause.py tests/games/test_registry.py tests/games/test_game_summaries.py` -- pass
- `cd frontend && npx vitest run src/modules/games` -- pass
- Before the commit: the full suites and the e2e specs named in the runbook.

## Auto Run Result

Status: done

**Summary.** A Lecturer of the Class can now pause a running Class game, with an agreed time or without one, change that time, and end the Pause. `games.commands.pause` takes a staff actor and an optional `resume_at`, judged `now < resume_at ≤ Spillfrist` on the database clock. The Spillfrist is read share-locked in the same transaction, and anything else is refused 422 `time_out_of_range`. `set_agreed_time` sets, changes or clears the time, also on a Student's Pause. `resume` («Avslutt pausen») clears the Pause and names the Lecturer as who ended it. With an agreed time, each command recomputes `insert_allowed_at` for the open Uke's unordered Student Seats through `rules.turn_times`, and `takeover_due_at` never moves. The changes to the insert-time rules:
- `_due_times` lets the agreed time stand when no clock runs yet.
- `_start_waits` keeps it through the first Order.
- A Pause without a time leaves insert times alone.
- `resume` keeps an insert time already passed.

Migration 0057 adds `games.agreed_time_reached_at`. The new sweep action `games.reach_agreed_time` sets it once the agreed time passes, raises the version and emits the Game's events. It never ends the Pause and never takes a Seat. Each person's action writes an audit row: `game.paused` (with `resume_at`), `game.pause_time_set` or `game.resumed`.

The routes `POST /api/games/{id}/pause`, `PUT …/pause/agreed-time` and `DELETE …/pause` answer Spillinnsikt. They are held to the new `games.pause` policy: Lecturer account and Class owner only, so an Assistant lecturer, a Lecturer who is only an Assistant lecturer in the Class, and a Student all get 403. The read models gain these fields:
- Spillinnsikt: `pause` (since, by whom, `mine`, agreed time), `can_pause` and `play_deadline`.
- The Oversikt: `can_pause` and `play_deadline`.
- The Student's pause line: `staff` and `resume_at`.

A staff Pause never names anyone to the Students, and a Student's 409 drops the staff id.

In the UI, Spillstyring (title now `text-label`) gets «Pause spillet». It opens the form in place:
- «Når fortsetter spillet?» with «Dato» and «Klokkeslett», or «Uten avtalt tid».
- The two epic lines.
- The primary «Ta pause til to. 19:00» or «Ta pause uten avtalt tid», and «Avbryt».

On a paused game Spillstyring shows «Pause siden ma. 14:10, satt av Sara.» with « Avtalt tid to. 19:00.», then «Endre avtalt tid» (the same form, prefilled) and «Avslutt pausen». The Varselbånd gets the secondary «Pause spillet»; its form opens under the band, and «Send Melding» steps back to secondary while the form is open. Students read «Pause til to. 19:00, satt av faglæreren.», «Pause, satt av faglæreren.» or «Pausen er over. Faglæreren har avsluttet den.».

**Files changed**
- `backend/migrations/versions/0057_pause_agreed_time_reached.py` (new), `backend/app/modules/games/models.py`: the mark and its check.
- `backend/app/modules/games/commands.py`: staff `pause`, `set_agreed_time`, `resume`, `reach_agreed_time`, `_recompute_insert_times`, `_start_waits` keeps an agreed insert time.
- `backend/app/modules/games/{rules,repo,service,insight,views,schemas}.py`: the agreed time without a clock, the repo writes and the finder, the insight pause fields, `TablePause.staff`/`resume_at`.
- `backend/app/modules/ops/sweep.py`, `backend/app/platform/events/registry.py`, `backend/app/platform/authz.py`: the due action, three registry entries, the `games.pause` policy.
- `backend/app/modules/sessions/{schemas,overview,routes,service}.py`: `StaffPauseIn`, `InsightPauseOut`, the flags, the three routes and their service functions, the Student refusal without the staff id.
- `frontend/src/modules/games/staff-pause.tsx` (new), `spillstyring.tsx`, `overview-band.tsx`, `overview-page.tsx`, `pause-view.tsx`, `api.ts`; `frontend/src/copy/nb.ts`; `frontend/src/lib/api/{openapi.json,schema.ts}` regenerated.
- Tests: `backend/tests/games/test_staff_pause.py`, `backend/tests/sessions/test_staff_pause_view.py` (new); `test_registry.py`, `test_migrations.py` (HEAD 0057), `test_pause_view.py` and `test_game_insight.py` (new fields). Vitest `staff-pause.test.tsx` (new) and fixture updates. e2e `staff-pause.spec.ts` (new); `spillstyring.spec.ts` counts the per-Seat buttons only.

**Review.** Four Sonnet reviewers: blind hunter, edge case, verification gap and intent alignment. They returned 42 findings: 0 high, 3 medium (one root cause), 33 low and 6 false.
- Patched (medium): a Pause without a time no longer resets insert times.
- Patched (low): the Student's refusal without the staff id, the band form closing for good, `resume_at` required, the lifecycle guard on the sweep, the no-change check before the range check, and tests (Lecturer-as-assistant, «Endre avtalt tid» saved in e2e, the Assistant's hidden controls, `_due_times` without a limit).
- Deferred: none.
- Rejected: the rest, each with its reason in the Review Triage Log.
- Follow-up review: not recommended (patched entries: high 0, medium 1, low 9).

**Verification** (after the patches)
- Backend full suite `--maxprocesses=8`: 2975 passed. ruff check and format are clean.
- Frontend: typecheck, Vitest (869 passed), `lint:colours`, `check:copy` and `next build` all pass.
- The stack was rebuilt after the last frontend change. Playwright `--workers=4` ran 183 tests over staff-pause, pause, spillstyring, overview, varselband, takeover, takeover-overview, reclaim, game-insight, live-updates, homes, student-home, seat-status, order-field, order-confirm, order-failures, week-table, week-advance, guided-week, game-card, cost-panel, chain-band, graph-over-table, week-transition and time-proposal. 182 passed. `spillstyring.spec.ts`'s first test failed on its button count, because the Lecturer now also has «Pause spillet». It was fixed to count the per-Seat buttons and passed on the rerun; no test failed and then passed unchanged.
- axe and reflow pass:
  - the form at 1440 px, on Spillinnsikt and under the band;
  - the paused state at 1440 and 320 px;
  - the prefilled change form at 320 px;
  - the band form at 360 px.
- New tests over 1 s: `tests/sessions/test_staff_pause_view.py`, all five tests at 1.0–1.7 s each. Each runs one real short Class game (`short_game`) through the api. `test_registry.py::test_each_command_emits_exactly_its_registered_topics` grows by three runners: about 7.3 s alone, 42 s under the loaded full run.

**Decisions taken instead of the founder.**
- Migration 0057 adds a mark (`agreed_time_reached_at`), so the sweep announces the agreed time once (AD-9 idempotence) without ending the Pause.
- When no clock runs yet, the agreed time stands as the insert time, also with Tilrettelegging (open-assumptions). The first Order keeps it for that Uke.
- «Avslutt pausen» keeps an insert time already passed (EXPERIENCE.md → End). A changed time is recomputed freely. A Pause without a time leaves insert times as they are.
- A Lecturer's agreed time always reads «Pause til …, satt av faglæreren.», also on a Student's Pause (EXPERIENCE.md journey). Who is staff is judged by "not a Student of the game's Seat history".
- The Lecturer's end sets `pause_ended_by` to the Lecturer. Students read «Pausen er over. Faglæreren har avsluttet den.» [ASSUMPTION].
- «Uten avtalt tid» is a checkbox under the two fields, so focus opens in «Dato». It sets the fields read-only.
- The range check reuses `time_out_of_range` and Story 6.19's range text. Without a Spillfrist the limit is the 90-day horizon, with «Velg et tidspunkt etter nå.» [ASSUMPTION].
- Spillinnsikt's client check uses the browser clock as a hint only, so its ETag is not broken by a `server_now`. The api judges again.
- Draft copy `[ASSUMPTION]`: «Lagre avtalt tid …»/«Lagre uten avtalt tid», «Avtalt tid to. 19:00.», «Spillet har pause uten avtalt tid.», «Pausen er avsluttet.», «Spillet har allerede pause.», the refusal lines and the Students' ended line.
- Implemented in the builder's own context, as the orchestrator instructed.

**Residual risks.**
- After the agreed time passes, the Students' line still shows that time. The visible change (Sett inn KI-spiller) is Story 8.8's.
- A Week that opens during a Pause with an agreed time gives its turns no insert time until the Lecturer sets one again.
- The form's server-refusal paths (409 `already_paused`, 422) are covered only through the backend and the client-side check.
- A visual check is left to the separate visual agent.
