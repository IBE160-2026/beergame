---
title: 'Story 8.8: Put an AI player in an absent Seat as a Student'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: 'a658811b681769e2459dd5b5949a388d92c7cbcb'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-8-context.md'
warnings: [oversized]
deferred: []
---

<intent-contract>

## Intent

**Problem:** Once an absent Seat's insert time (`seat_turns.insert_allowed_at`, Stories 8.1 and 8.7) has passed, the other Students of the game cannot put an AI player in it. While a Pause runs, no automatic Takeover happens, so the group stays stuck. The Setestatus row also never says when that right arises (FR-89, FR-37, UX-DR27).

**Approach:** `games.commands.takeover` gains a `peer` actor that `rules.can_take_over` judges by the Seat's insert time. A new Student route lets a Student who holds another Seat in the game use it. `table_status` tells each Student, per Seat, the insert time before it passes, whether the control is available, and who put the AI player in. A sweep action announces once that an insert time has passed, so the control appears without a reload. The Setestatus row shows the before line, or the consequence and «Sett inn KI-spiller for Jonas», and after a press the result or conflict line.

## Boundaries & Constraints

**Always:**
- Rules: `TakeoverActor` becomes `system | staff | peer`. `can_take_over(..., peer_seated=False)`: for `peer`, after the lifecycle and policy checks, `peer_seated` False gives `seat_not_yours`. Then the same Seat checks as now (`takeover_exists` / `seat_not_student_held`). A Pause is no condition for `peer`, and `has_ordered` gives `order_exists`. An `insert_allowed_at` that is missing or later than `now` gives `insert_not_allowed_yet`. `system` and `staff` behave as before.
- Command: `takeover(game_id, seat, actor="peer", actor_user_id=student)`. `peer_seated` is true when the actor holds, as a Student, a Seat of this Game other than the target in the latest occupancy rows (`seats_with_occupant`). It takes the database clock and writes reason `takeover_peer`, with the Student in `actor_user_id`. It writes the audit row `seat.taken_over` with the Student as actor, and runs `ensure_order`, the notices, the events and `_settle` exactly as for staff. No new 409 shapes: `takeover_exists` keeps `fields.acted_by`.
- Route `POST /api/me/games/{game_id}/seats/{role}/takeover` (operation `insertAiPlayer`), policy `games.play_own`, through `_own_locked_game` (403 for any other game, FR-5). It answers `StudentGameOut`. Refusals answer 409 with the code. `fields` pass through `_student_fields`, so a staff id never reaches a Student. There is no body: no route or parameter lets a Student set or shorten an insert time.
- View (`views.table_status`), per Seat. Each field is judged against the database clock, read once in the view:
  - `insert_at`: the stored `insert_allowed_at`. It is set only for another Student's Seat that a Student holds, has not ordered, and whose insert time lies after now, while the game is paused or the insert time is agreed. Otherwise it is None.
  - `insert_agreed`: `insert_allowed_at` is set and differs from `takeover_due_at` (the Lecturer's agreed time governs this Seat).
  - `can_insert`: the viewer holds another Seat now, and `can_take_over(game, turn, "peer", now, guided, seat=row, peer_seated=True)` is None.
  - `inserted_by`: for a Seat `taken_over` whose latest row is `takeover_peer`, the name now of the Student who pressed; otherwise None.
  The fields are mapped into `TableSeatOut` with defaults. The api client is regenerated.
- Sweep: migration `0058_seat_turns_insert_announced.py` adds `seat_turns.insert_announced_at timestamptz NULL` (no backfill). Finder `repo.due_insert_times(now)`: turns of the open Week of running Games with `insert_allowed_at <= now` and no mark. The command `announce_insert_time(game_id, seat_id, *, now)` runs under the Game lock. It always sets the mark. Only while the Seat is still Student-held, has not ordered and the Game runs does it also bump the version and emit `game`, `session` and `user` for every seated Student (registry `games.announce_insert_time`). `set_insert_allowed` clears the mark. The DueAction goes after `games.takeover`.
- Peer Takeover in a Guided Week: the Seat is taken from this Week, and the Week advances under Story 8.2's rule (already in `takeover`).
- UI (`GameSeatStatus` gains `gameId`; Spill and Hjem pass it):
  - Before line under the row: «Avtalt tid to. 19:00. Etter det kan dere sette inn en KI-spiller.» when `insert_agreed`, else «Etter on. 10:00 kan dere sette inn en KI-spiller.» (`osloWeekdayTime(insert_at)`). It never says why.
  - When `can_insert`: the caption consequence `spillstyring.thisWeek(name)` directly above the secondary «Sett inn KI-spiller for Jonas». The button is full width below 1024 px, at least 44 px, with no dialog.
  - Success: the response is set as the game, the play view and Hjem read again, and focus moves to the row's text («Fabrikk KI-spiller bestiller for Jonas», `tabindex="-1"`).
  - On 409 `takeover_exists`: read again, then the row shows `taken(inserted_by)`, «Faglæreren har allerede satt inn en KI-spiller.» [ASSUMPTION] for staff, or `takenBySystem`, and that line takes focus. Other refusals show inline and the button stays active.
  - The polite announcement is unchanged (the Takeover line already exists).
- Copy in `nb.ts` (`homes.student.insert`), reusing `spillstyring.thisWeek/takeover/taken/takenBySystem`.

**Never:** no change to automatic or staff Takeover rules, `takeover_due_at`, the Pause, the Play deadline or the demo Class. No Student time input, and no reason a Seat's time differs. No name in errors or logs (ids only). No DB-vs-host time comparison and no real waiting in tests.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Peer insert | paused, Jonas unordered, insert passed, Sara seated | row `takeover_peer`, actor Sara, Jonas's Order ensured, audit, notices | — |
| Too early | insert in the future or none | nothing written | 409 `insert_not_allowed_yet` |
| Not seated / own Seat | actor holds no other Seat | nothing written | 409 `seat_not_yours` |
| Ordered | Jonas has ordered | — | 409 `order_exists` |
| Race | two Students press | one row; second gets acted_by student + id | 409 `takeover_exists` |
| Order ends Pause | insert passed, Sara orders | insert time kept, `can_insert` still true for others | — |
| Sweep crossing | insert ≤ now, unmarked | mark set, version +1, events; a second run does nothing | race skipped |
| Outsider | not in the game | — | 403 `forbidden` |

</intent-contract>

## Code Map

- `backend/app/modules/games/rules.py:42-95` -- `TakeoverActor`, `can_take_over` (extend with `peer`, `peer_seated`).
- `backend/app/modules/games/commands.py:1730` `takeover` (reason/audit by actor; `_ACTED_BY_KIND` already maps `TAKEOVER_PEER`→student); `reach_agreed_time` 2091 (pattern for `announce_insert_time`); `_recompute_insert_times` 2157; `seated_students`; `__all__`.
- `backend/app/modules/games/repo.py:463` `set_insert_allowed` (clear mark), `due_agreed_times` 447 (finder pattern), `open_week` 511, `seats_with_occupant` (has `actor_user_id`, `reason`).
- `backend/app/modules/games/models.py` `seat_turns` -- new column. `backend/migrations/versions/0058_…` new; `tests/test_migrations.py:90` HEAD.
- `backend/app/modules/games/views.py:298` `table_status` (new per-Seat fields; viewer `seated`); `schemas.py:581` `TableSeat`.
- `backend/app/modules/games/service.py` -- `due_insert_times` re-export for the sweep (as `due_agreed_times`).
- `backend/app/modules/ops/sweep.py:153-202` -- DueAction.
- `backend/app/platform/events/registry.py:44` -- `games.announce_insert_time`.
- `backend/app/modules/sessions/{schemas.py TableSeatOut 381, service.py _seats_out 1393 / reclaim_own_seat 1609 pattern / _student_fields 1662, routes.py reclaim_my_seat 1010 pattern}`.
- Frontend: `src/modules/games/{seat-status.ts seatRows, seat-status-view.tsx GameSeatStatus, reclaim-view.tsx (focus pattern), spillstyring.tsx actedKind/takenText, api.ts reclaimSeat pattern, play-page.tsx:416,725, student-hjem.tsx:248}`, `src/components/seat-status.tsx` (row `detail`/`action` slots; focusable row text), `src/copy/nb.ts:396`, `src/modules/sessions/dates.ts osloWeekdayTime`, `src/lib/api/*`.
- Tests: `backend/tests/games/test_takeover.py` (`class_game`, `due_of`, `takeovers`), `test_staff_pause.py` (`db_now`, `insert_of`), `test_registry.py` RUNNERS, `test_game_summaries.check`; `tests/sessions/test_pause_view.py` (`three_students_in_uke_2`, `call`, `home`, `play`); e2e `takeover.spec.ts` + `support/play.ts` (stub pattern).

## Tasks & Acceptance

**Execution:**
- Migration 0058, `models.py`, `rules.py`, `repo.py`, `commands.py`, `service.py`, `sweep.py`, `registry.py` -- peer actor, mark, sweep action.
- `views.py`, `games/schemas.py`, `sessions/{schemas,service,routes}.py` -- fields, route; regenerate `openapi.json`/`schema.ts`.
- `frontend/src/modules/games/peer-insert.tsx` (new: before line, control, result), `seat-status.ts`, `seat-status-view.tsx`, `components/seat-status.tsx`, `api.ts`, `play-page.tsx`, `student-hjem.tsx`, `nb.ts`.
- Tests: `tests/games/test_peer_insert.py` (pure rule cases; matrix on commands; sweep mark/idempotence; registry runner; summary check), `tests/sessions/test_peer_insert_view.py` (one short game: before fields, can_insert, route press, conflict, outsider 403, staff id dropped). Vitest `peer-insert.test.tsx` (lines and visibility). e2e `peer-insert.spec.ts` (stubbed envelopes: before lines, control, press → row focused, conflict line focused, axe and reflow at 320, 360 and 1440).

**Acceptance Criteria:**
- Given an absent Seat while paused with an insert time ahead, when another Student opens Spill or Hjem, then its row reads the before line with that Seat's own time and no reason.
- Given `can_insert`, when the Student presses «Sett inn KI-spiller for Jonas», then no dialog shows, the row becomes «Fabrikk KI-spiller bestiller for Jonas» with focus on it, and the absent Student gets «KI-spiller har bestilt for deg.» and «Ta tilbake setet».
- Given a second Student pressed first, when the press returns 409, then the button is gone and focus is on «Sara har allerede satt inn en KI-spiller.».
- Given 320, 360 and 1440 px, then the before, available and done states have no horizontal scroll and pass axe.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
- Layers: blind hunter, edge-case hunter, verification gap and intent alignment, all on Sonnet as the orchestrator asked. All four hand-backs dropped, so the findings were read from `review-{blind,edge,verification,intent}-8-8.md` in the session scratchpad. The diff was taken against the baseline `a658811` and leaves out the generated api client and `.docs`. The orchestrator's later commits on `epic-8` (sprint and log files) are not part of this change.
- verdicts: 32 findings — high 0, medium 2 (one root cause), low 21, false 9, maybe-false 0
- findings:
  - `[low]` `[reject]` blind-1: the finder reads unannounced past-Week rows. The query is limited to the open Week of running Games. The scan grows only with one class's turns, as `due_takeovers` does. An index adds a migration for no named harm at this scale.
  - `[false]` `[reject]` blind-2: "agreed" is wrong when `takeover_due_at` is NULL. Without a clock, an insert time exists only because of an agreed time (`_due_times`), so `insert != due` is correctly agreed. An agreed time equal to the due time to the microsecond is not a real case.
  - `[medium]` `[patch]` blind-3: the press state (`done`, `taken`) was never cleared. After a Reclaim, the "Sara har allerede …" line stayed and the control was hidden. A press is now kept only while the Seat is taken over; it is forgotten once a Student holds the Seat again (`Pressed.seen`).
  - `[false]` `[reject]` blind-4: a 409 without `acted_by` shows nothing. `actedKind` returns `system` for any `takeover_exists` without a valid kind, and `invalidateQueries` does not reject on a failed refetch.
  - `[low]` `[patch]` blind-5: the button could be pressed again before the view read again. The control now goes as soon as a press is done or refused with `takeover_exists`.
  - `[low]` `[reject]` blind-6: there is no polite line when the control appears, and `focus:outline-none` is used. The Takeover line is already announced, and the focus style follows the Reclaim and Spillstyring result lines. A new live line is new copy beyond the story.
  - `[low]` `[reject]` blind-7: k absent Seats give k sweep commits. At most three Seats per game, once per insert time.
  - `[low]` `[reject]` blind-8: the refusal copy is thin. It is draft copy `[ASSUMPTION]`, and the controls are shown only when the api allows them, so the refusals are rare.
  - `[false]` `[reject]` blind-9: a 404 becomes 403. `role` is a `Role` enum and every Game has all four Seats, so `seat_not_found` cannot happen. 422 for a bad enum is FastAPI's, as on the Reclaim route.
  - `[low]` `[patch]` blind-10: the `takeover` docstring did not name `takeover_peer`. Corrected.
  - `[low]` `[patch]` blind-11: the finder test's name claimed more than it tested. Renamed `test_the_finder_skips_a_game_that_no_longer_runs`, and its last `UPDATE` was removed. The other test-style points (fixture re-exports, `nth(1)`) follow the suite's patterns.
  - `[low]` `[reject]` blind-12: listed coverage gaps. A peer insert in an unpaused game is covered (`test_the_right_survives_the_order_that_ends_the_pause`). The rest is inherited (audit label, notice mail) or follows the rules already tested.
  - `[false]` `[reject]` blind-13: the change set is incomplete. The api client is regenerated and was left out of the review diff on purpose. The spec exists, and the 8.7 log hunk is the orchestrator's commit.
  - `[medium]` `[patch]` edge-1: same as blind-3.
  - `[low]` `[reject]` edge-2: the sweep's clock against the database clock. The sweep judges every due time on its own `now`, as the Takeover and 8.7's `reach_agreed_time` do (Issue #63). The play screen also reads again at `next_change_at`.
  - `[low]` `[reject]` edge-3: A and B insert for each other at once. The loser no longer holds a Seat, gets `seat_not_yours`, and sees «Ta tilbake setet» on their own row. The outcome is coherent.
  - `[low]` `[reject]` edge-4: a peer's AI player is switched by the Play guard before a second press. That needs a guard switch within seconds of the press, and the refusal is still a 409 with the control gone.
  - `[low]` `[reject]` edge-5: a Student whose own Seat has a staff Takeover queued from the next Week cannot insert. That Seat is no longer theirs to play from; this is rare and follows "holds another Seat".
  - `[low]` `[reject]` edge-6: a peer insert that completes a paused Week leaves the Pause set. It is the same behaviour as a staff Takeover (8.5/8.6). Only a Student's Order ends a Pause (FR-89), and a test now asserts that the Pause goes on.
  - `[false]` `[reject]` edge-7 (claim): `set_wait_times` moves an announced insert time. It writes only while `wait_started_at` is unset, and with no factor before Story 8.9 the value stays the agreed time.
  - `[low]` `[reject]` edge-8: a retry after a lost response names the presser themselves. This is rare, and the line is still true.
  - `[low]` `[patch]` edge-9: no test of a press racing the absent Student's Order. Added `test_a_press_and_the_absent_students_order_end_one_way`, which shows one outcome either way.
  - `[low]` `[patch]` verification-1: the staff id was not checked as dropped on the Student route. The view test now has a staff Takeover first, and the 409 carries `{"kind": "staff", "user_id": None}`.
  - `[low]` `[patch]` verification-2: the UI path for other refusals was untested. Added an e2e test: a 409 `insert_not_allowed_yet` shows inline, the button stays enabled, and no result line appears.
  - `[low]` `[patch]` verification-3: the sweep's quiet mark for a Seat already taken over was untested. The main command test now asserts that it marks without a version bump.
  - `[low]` `[patch]` verification-other: the Pause state after a peer Takeover was not asserted. It is now (it goes on).
  - `[low]` `[reject]` intent-1: Hjem has no browser test. Hjem renders the same `GameSeatStatus`, and the api test reads the fields on Hjem.
  - `[low]` `[reject]` intent-2: the sweep event reaching the browser is not tested end to end. The event-to-read-again path is `live-updates.spec.ts`'s, and the sweep's emission is tested with `listening`.
  - `[false]` `[reject]` intent-3: the Oversikt mark for `takeover_peer` is not new work. It was built in Story 8.5 (`mark_by`, `markedBy`) and reads `actor_user_id`, which this story sets.
  - `[false]` `[reject]` intent-4: the changed version count in `test_staff_pause` is a defect. It is the intended second announcement: the agreed time is also each waiting Seat's insert time.
  - `[false]` `[reject]` intent-5: the 8.7 log hunk is not part of this change (orchestrator commit).
  - `[false]` `[reject]` intent-6: the generated api types are regenerated in the tree and were left out of the review diff.

## Design Notes

`insert_agreed` is read from stored times only (insert ≠ due), so the view tells "agreed time" from "own limit" without saying why one Seat is later (UX-DR27). With Tilrettelegging and a later own limit the insert equals the due time and the row reads «Etter …». The mark column makes the sweep's announcement idempotent (AD-9), as 8.7's `agreed_time_reached_at` does. The play screen already reads again at `next_change_at`, which includes insert times; the sweep's events serve Hjem and any open view.

## Verification

**Commands:**
- `cd backend && uv run pytest -q tests/games/test_peer_insert.py tests/sessions/test_peer_insert_view.py tests/games/test_takeover.py tests/games/test_registry.py` -- pass
- `cd frontend && npx vitest run src/modules/games` -- pass
- Before the commit: the full suites and the e2e specs named in the runbook.

## Auto Run Result

Status: done

**Summary.** A Student can now put an AI player in another Student's absent Seat once that Seat's insert time has passed, whether or not the game is paused.

- **Rule.** `rules.can_take_over` gains the `peer` actor:
  - The Student must hold another Seat of the Game (else `seat_not_yours`).
  - The Seat must be Student-held and must not have ordered (else `order_exists`).
  - Its stored `insert_allowed_at` must lie at or before now (else `insert_not_allowed_yet`).
  - A Takeover already done or queued gives `takeover_exists` with `acted_by`.
- **Command.** `commands.takeover(actor="peer")` writes the occupancy row with reason `takeover_peer` and the Student in `actor_user_id`. It also writes:
  - an audit row `seat.taken_over`;
  - the AI player's Order, in the same transaction;
  - Story 8.2's notices and events.
  In a Guided Week, the Week advances.
- **Route.** `POST /api/me/games/{id}/seats/{role}/takeover` uses `games.play_own`, takes no body, and works only on the Student's own game. It answers the game as it now stands. A refusal never carries a staff id.
- **View.** `table_status` gives each Seat four fields:
  - `insert_at`: the Seat's own insert time ahead, only while paused or agreed;
  - `insert_agreed`;
  - `can_insert`: the one rule (AD-10);
  - `inserted_by`.
- **Sweep.** Migration 0058 adds `seat_turns.insert_announced_at`. The sweep action `games.announce_insert_time` marks a passed insert time once. While the Seat still waits, it also emits the Game's events, so the control appears without a reload.
- **Screens.** On Spill and Hjem, another Student's row reads «Avtalt tid to. 19:00. Etter det kan dere sette inn en KI-spiller.» or «Etter on. 10:00 kan dere sette inn en KI-spiller.». Once the insert time has passed, it shows the consequence above the secondary «Sett inn KI-spiller for Jonas».
  - After a press, the row («KI-spiller bestiller for Jonas») takes focus.
  - When someone came first, «Sara har allerede satt inn en KI-spiller.» takes focus.

**Files changed**
- Backend:
  - `backend/migrations/versions/0058_seat_turns_insert_announced.py` (new) and `backend/app/modules/games/models.py`: the mark.
  - `rules.py`: the `peer` actor.
  - `commands.py`: the peer Takeover and `announce_insert_time`.
  - `repo.py`: the finder, and the mark cleared on `set_insert_allowed`.
  - `service.py`: the finder wrapper.
  - `views.py` and `schemas.py`: `_insert_state` and the new fields.
  - `backend/app/modules/ops/sweep.py` and `backend/app/platform/events/registry.py`: the due action and its registry entry.
  - `backend/app/modules/sessions/{routes,service,schemas}.py`: the route, `insert_ai_player`, `InsertRefused` and the fields.
- Frontend:
  - `frontend/src/modules/games/peer-insert.tsx` (new): the before line, the control and the focused line.
  - `seat-status-view.tsx`: `GameSeatStatus` takes `gameId` and keeps the press state.
  - `components/seat-status.tsx`: focusable row text.
  - `api.ts`, `play-page.tsx`, `student-hjem.tsx` and `copy/nb.ts`.
  - `lib/api/{openapi.json,schema.ts}`: regenerated.
- Tests:
  - New: `backend/tests/games/test_peer_insert.py` and `backend/tests/sessions/test_peer_insert_view.py`.
  - Updated: `test_registry.py` (a runner), `test_migrations.py` (HEAD 0058), `test_staff_pause.py` (the sweep now also announces insert times), `test_play.py` and `test_seat_status.py` (the new keys).
  - Vitest: `peer-insert.test.tsx` (new), with fixtures updated in `home.test.ts` and `seat-status.test.tsx`.
  - e2e: `peer-insert.spec.ts` (new).

**Review.** Four Sonnet reviewers returned 32 findings: high 0, medium 2 (one root cause), low 21, false 9.
- Patched (medium): the press state is cleared after a Reclaim.
- Patched (low):
  - no second press before the view is read again;
  - the docstring and a test name;
  - new tests for a press racing an Order, for the staff id being dropped on the Student route, for the inline refusal (e2e), for the quiet sweep mark, and for the Pause going on.
- Deferred: none.
- Rejected: the rest, each with its reason in the Review Triage Log.
- Follow-up review: not recommended. Patched entries: high 0, medium 1, low 8.

**Verification** (after the patches)
- **Backend.** The full suite with `--maxprocesses=8` passed: 2996 tests. ruff check and format are clean.
  - Before that, two runs failed because the shared Postgres container crashed and went into recovery (`server process exited with exit code 2`). After it recovered, the suite was run again.
  - Before the patches, `test_seat_status.py::test_the_first_students_order_starts_the_wait_for_the_seats_that_have_not_ordered` failed on its exact key set. It was updated for the new fields; it was not a flake.
- **Frontend.** Typecheck, Vitest (873 passed), `lint:colours`, `check:copy` and `next build` all pass.
  - One Vitest run reported one failed test while the backend suite was loading the machine. The output did not name the test. The next two full runs passed.
- **End to end.** The stack was rebuilt after the last frontend change. Playwright with `--workers=4` ran 178 tests, and all passed on the first run. The specs were chain-band, cost-panel, game-card, graph-over-table, guided-week, homes, live-updates, order-confirm, order-failures, order-field, pause, peer-insert, reclaim, seat-status, spillstyring, staff-pause, student-home, takeover, takeover-overview, time-proposal, week-advance, week-table and week-transition.
- **Accessibility.** axe ran at 1440 px for the before, available and done states, and at 320 and 360 px for the available state. The other states got a reflow and tap-target check.
- **Slow tests (over 1 s).**
  - `tests/sessions/test_peer_insert_view.py::test_students_put_an_ai_player_in_an_absent_seat` takes 3.3 s. It plays one short Class game through the api and covers the whole story.
  - Every new test in `tests/games/test_peer_insert.py` stays under 1 s (0.4–0.9 s).
  - `test_registry.py::test_each_command_emits_exactly_its_registered_topics` gains one runner and takes 8.4 s under the full run.

**Decisions taken instead of the founder.**
- A Student without another Seat of the game, or pressing on their own Seat, is refused `seat_not_yours`. This reuses an existing code; the epic names only `insert_not_allowed_yet`.
- The line before the insert time shows only while the game is paused or the time is the Lecturer's agreed time. "Agreed" is read from stored times: the insert time differs from the Takeover due time. Outside those cases the automatic Takeover comes at that same moment, so no line is shown (EXPERIENCE.md → Sett inn KI-spiller → Shown).
- With Tilrettelegging and a later own limit, the row reads «Etter …» with the Seat's own time, never «Avtalt tid …». That way it never says why one Seat's time is later.
- Migration 0058 adds a per-turn mark so the sweep announces a passed insert time once (AD-9). A Lecturer's new insert time clears the mark.
- A peer Takeover that completes a paused Week leaves the Pause in force, as a staff Takeover does. Only a Student's Order ends a Pause.
- Draft copy `[ASSUMPTION]`: «Faglæreren har allerede satt inn en KI-spiller.», the refusal lines and the failure line.
- The orchestrator asked for the implementation to be done in the builder's own context, so the skill's implementation subagent was not used.

**Residual risks.**
- The sweep marks a passed insert time on its own clock. If the host clock runs ahead of the database clock, Hjem may show the control only at the next event. The play screen reads again at `next_change_at`.
- Hjem's control and the path from the sweep to the browser are covered by api tests and the shared component, not by a browser test of their own.
- The visual check is left to the separate visual agent.
