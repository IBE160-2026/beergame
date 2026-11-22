---
title: 'Story 8.11: Mark a Class game as «I rommet» during a Lab hour'
type: 'feature'
created: '2026-11-22'
status: 'done'
baseline_revision: 'd90f556089fc37fc11c2fd15a748cdccc96ced36'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-8-context.md'
warnings: [oversized]
deferred:
  - summary: >-
      Finished-game and non-Takeover branches of «I rommet» are untested at the api.
    evidence: |-
      No test reads Spillinnsikt of a finished game for can_mark_in_room false and in_room none,
      runs the sweep's end_in_room on a Game that finished while marked, or marks a finished Game
      (409 game_finished). Low-risk branches (verification-gap layer, Story 8.11 review).
    location: >-
      backend/app/modules/games/insight.py (markable), backend/app/modules/games/commands.py (end_in_room, _check_in_room_game)
    severity: low
---

<intent-contract>

## Intent

**Problem:** A group sitting together in a Lab hour waits up to a day (the Inactivity limit) for one absent Student; FR-36's shorter in-room limit has no way in, and `turn_times` already takes an `in_room_limit` nobody passes.

**Approach:** Two new `games.commands` — `mark_in_room` and `end_in_room` — store the in-room limit, the Lab hour's end and its id on the Game (migration 0061) and recompute the open Week's due times with it; the sweep ends marks whose Lab hour has ended; a moved or removed Lab hour updates or ends its marks through `games.service`. Spillstyring offers «Marker som i rommet» (only during a Lab hour) and «Ikke i rommet lenger»; Students see the line above Setestatus with their own minutes; the wall row label carries «I rommet».

## Boundaries & Constraints

**Always:**
- Migration `0061_game_in_room.py`: `games.in_room_minutes smallint NULL`, `in_room_until timestamptz NULL`, `in_room_lab_hour_id uuid NULL`, `in_room_by uuid NULL`, `in_room_marked_at timestamptz NULL` (ids only, no FK); CHECK minutes/until/lab hour/marked_at set together or none; CHECK minutes 2..120. `game_summaries.in_room_until timestamptz NULL`. No backfill. `tests/test_migrations.py` HEAD → 0061.
- One limit source: `commands._in_room_limit(game)` → `timedelta(minutes=…)` when marked and the policy has inactivity Takeover, else None; passed as `TurnInputs.in_room_limit` in `_start_waits`, `_recompute_insert_times` and the recompute. `recompute_turn_times`' loop moves into `_recompute_due_times(session, game) -> bool`, shared by it and both new commands (same agreed-time rule, wait start never moves).
- `mark_in_room(game_id, minutes, *, actor: UUID | None, lab_hour_id, until, now)`: Game lock; 404 `game_not_found`; 409 `in_room_not_allowed` (policy has no inactivity Takeover), `game_finished`, `game_not_running` (not started); 422 `minutes_out_of_range` (not int 2..120); 409 `not_in_lab_hour` when `until <= now` (`now` is the caller's api clock, as Lab hours are). With a person `actor`, a marked Game answers 409 `already_in_room` with `fields {acted_by: {kind: staff, user_id: in_room_by}, acted_at: in_room_marked_at}`. With `actor=None` (a moved Lab hour) it only rewrites `in_room_until` of a Game marked for that Lab hour, else returns False. Writes the columns, recomputes, audit `game.marked_in_room` `{minutes, in_room_until}` for a person, `_commit_change`, `user:` per seated Student. Returns True.
- `end_in_room(game_id, *, actor: UUID | None, now: datetime | None = None, lab_hour_id: UUID | None = None) -> bool`: person: 409 `not_in_room` when unmarked; system: False when unmarked, when `now` is given and `in_room_until > now`, or when `lab_hour_id` is given and differs. Clears the columns, recomputes back to the Inactivity limit from the same wait start, audit `game.in_room_ended` for a person, commit and events. Runs on any lifecycle (a finished Game only loses its mark).
- Registry `COMMAND_TOPICS`: both `{game, session, user}`; both join `test_registry.py` runners and the Story 7.1 recomputation test. `overview.recompute` writes `in_room_until` (null unless marked and the Game runs).
- Sweep: `DueAction("games.end_in_room", …)` after `games.takeover`; finder `games.service.due_in_room_ends(now)` (marked Games with `in_room_until <= now`), act calls `end_in_room(actor=None, now=now)`.
- `games.service.lab_hour_moved(class_session_id, lab_hour_id, starts_at, ends_at, now)` and `lab_hour_removed(class_session_id, lab_hour_id)`: per marked Game of that Lab hour, end it (removed, or no longer on at `now`) or move its end. `sessions.service.change_lab_hour`/`remove_lab_hour` call them after their commit.
- `authz`: `games.in_room` = Lecturer / OWNER only.
- `sessions/overview.py`: `mark_in_room(user, game_id, minutes)` (as `pause_game`; reads `current_lab_hour(session, auth.utcnow())`, none → `InRoomRefused("not_in_lab_hour", 409)`), `end_in_room(user, game_id)`. `game_insight` gains `in_room: InsightInRoomOut {until, minutes} | None`, `can_mark_in_room` (Lecturer, game running/waiting/paused, policy allows) and `lab_hour_ends_at` (the Lab hour on now, api clock; None outside). `OverviewGameOut.in_room_until`.
- Routes: `POST /api/games/{id}/in-room` (`markInRoom`, body `InRoomIn {minutes: int}`) and `DELETE …/in-room` (`endInRoom`), both `authz.require("games.in_room")`, answer `GameInsightOut`; refusals with their codes. Api client via `npm run api:generate`.
- Students: `views.table_status(…, factor=None)` gains `in_room: TableInRoom {until, minutes}` while marked and running; `minutes = floor(in_room_minutes × own factor)` (factor from `sessions.service.time_factors` for the viewer, passed by `student_play_of`). `PlayOut.table_status.in_room`.
- Frontend: `modules/games/in-room.ts` (pure: minute check, button label, line texts) and `in-room-view.tsx`: `InRoomStyring` in Spillstyring after the Pause (secondary «Marker som i rommet»; outside a Lab hour `aria-disabled` with «Kan bare brukes i en Labtime.» as its description; form in place: «Ventetid i rommet» field default 10, the line «Studentene i spillet ser den kortere ventetiden. Den gjelder til Labtimen slutter kl. 16:00.», primary «Marker som i rommet, 10 min» and «Avbryt»; marked: «I rommet til 16:00. KI tar over etter 10 min uten ordre.» with secondary «Ikke i rommet lenger»; results «I rommet til 16:00.» / «Ikke i rommet lenger.» take focus; focus rules as `PauseStyring`). `InRoomLine` above Setestatus on Spill: polite live region «I rommet til kl. 16:00. En KI-spiller tar setet etter 10 min uten ordre.»; when the mark goes while the page is open, «Spillet er ikke i rommet lenger.» is announced (sr-only). Wall and table row label «Spill 3 · I rommet». Copy in `nb.ts` (`spillstyring.inRoom`, `homes.student.inRoom`), draft lines `[ASSUMPTION]`.

**Never:** no shortening below 2 min or the Student's factor (factor only extends); no mark outside a Lab hour or on a not-started/finished Game; no Assistant lecturer action; no Student sees another's minutes or factor; no change to the demo Class; no DB-vs-host time comparison in tests; no game per test.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected | Error |
|---|---|---|---|
| Mark in a Lab hour | running game, 10 min, Student B waited since t | B's due = t + 10 min; audit; summary `in_room_until` | — |
| Factor 2 | B has 2 × | due = t + 20 min; B's line «20 min», A's «10 min» | — |
| Out of range | 1 or 121 or 7.5 | nothing stored | 422 `minutes_out_of_range` |
| No Lab hour now | — | — | 409 `not_in_lab_hour` |
| Marked twice | already marked | — | 409 `already_in_room` + acted_by |
| Person ends | marked | due back to t + Inactivity limit | `not_in_room` when unmarked |
| Lab hour ends | sweep at until | mark cleared, times back | idempotent |
| Lab hour moved / removed | marked for it | until moved / mark ended | — |
| Assistant / Student / outsider | either route | — | 403 |

</intent-contract>

## Code Map

- `backend/app/modules/games/rules.py:180,242` -- `in_room_limit` already in `TurnInputs`/`_due_times`.
- `backend/app/modules/games/commands.py:1584` `_start_waits`, `:1627` `_time_factors`, `:1646` `_inactivity_limit`, `:2014-2170` pause/resume (pattern: lock, audit, `_commit_change`, `user:` events), `:2248` `recompute_turn_times` (loop to extract), `:2354` `_recompute_insert_times`, `:2399` `_paused_by` (fields shape).
- `backend/app/modules/games/{models.py:110-144 (games), :368 (game_summaries), repo.py (set_pause pattern ~:400, upsert_summary, due_agreed_times), overview.py:24 recompute, service.py:209 due_agreed_times / :700-760 ClassGameSummary, insight.py:124 GameInsight, views.py:299 table_status, schemas.py:631 TablePause/:651 TableStatus}`.
- `backend/app/platform/events/registry.py:44`; `backend/app/platform/authz.py:113,164`; `backend/app/modules/ops/sweep.py:213`.
- `backend/app/modules/sessions/{overview.py:400 game_insight, :580-660 staff Pause pattern, :297 _game_out; service.py:2133 change_lab_hour, :2179 remove_lab_hour, :2207 current_lab_hour, :593 time_factors, :1546 student_play_of; schemas.py (GameInsightOut, OverviewGameOut, TableStatusOut, PlayOut); routes.py:361-440 pause routes}`.
- Tests: `tests/games/test_registry.py` (RUNNERS, CLASS_SETUP_EVENTS, command set), `test_game_summaries.py`, `test_takeover.{class_game,due_of}`, `test_staff_pause.db_now`; `tests/sessions/test_staff_pause_view.py` (api pattern, `short_game`, `insight`, `home`, `email`), `test_lab_hours.py` (add helper), `tests/ops/` sweep tests.
- Frontend: `src/modules/games/{spillstyring.tsx, staff-pause.tsx (PauseResult), pause-view.tsx (PauseLine), play-page.tsx:414, overview.ts:332 wallGroups / :466 tableRows, api.ts}`, `src/components/text-field.tsx`, `src/copy/nb.ts:2514`; e2e `spillstyring.spec.ts`, `support/live-game.ts`, `classes.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0061_game_in_room.py`, `games/models.py`, `tests/test_migrations.py` -- columns.
- `games/repo.py`, `games/commands.py`, `games/overview.py`, `games/service.py`, `games/insight.py`, `games/views.py`, `games/schemas.py`, `platform/events/registry.py`, `ops/sweep.py` -- commands, recompute, summary, finder, Lab hour hooks, Student view.
- `platform/authz.py` -- `games.in_room`.
- `sessions/{overview,service,schemas,routes}.py` -- routes, insight fields, Lab hour hooks, Student minutes.
- `frontend/src/lib/api/{openapi.json,schema.ts}` -- regenerate.
- Frontend: `games/{api.ts, in-room.ts (+ Vitest), in-room-view.tsx, spillstyring.tsx, play-page.tsx, overview.ts}`, `copy/nb.ts`, fixtures.
- Tests: `tests/games/test_in_room.py` (commands: due times with/without factor, end restores, refusals, system end idempotent, moved/removed Lab hour, summary equality); registry runners; `tests/sessions/test_in_room_view.py` (routes, Lab hour gate, 403s, insight fields, Student minutes, sweep end); e2e `in-room.spec.ts` (mark, Student line, end, unavailable outside a Lab hour, axe + reflow 320/1440).

**Acceptance Criteria:**
- Given a running Class game and a Lab hour on now, when the Lecturer opens Spillinnsikt, then «Marker som i rommet» is active; with no Lab hour it is `aria-disabled` with «Kan bare brukes i en Labtime.»; an Assistant lecturer sees neither.
- Given the form, when it opens, then focus is on «Ventetid i rommet» (10), the line names the Lab hour's end and the primary reads «Marker som i rommet, 10 min»; 1 or 121 shows the error in the Ordrefelt pattern and the api answers 422 `minutes_out_of_range`; «Avbryt» returns focus to the opener.
- Given the Lecturer marks it, then «I rommet til 16:00.» has focus, the block reads «I rommet til 16:00. KI tar over etter 10 min uten ordre.» with «Ikke i rommet lenger», the wall row label carries «I rommet», and the Students' Spill shows «I rommet til kl. 16:00. En KI-spiller tar setet etter 10 min uten ordre.» above Setestatus, each with their own minutes.
- Given a Student who has not ordered 10 minutes after another ordered, when the sweep runs, then the automatic Takeover happens.
- Given «Ikke i rommet lenger» or the Lab hour's end passing the sweep, then the mark is gone, the due times are back on the Inactivity limit from the same wait start, and the Students' line goes with a polite announcement.

## Spec Change Log

## Review Triage Log

### 2026-11-22 — Review pass
- Layers: blind hunter (asked to weigh concurrency), edge-case hunter, verification gap and intent alignment, all on Sonnet as the orchestrator asked. All four hand-backs dropped, so the findings were read from `review-{blind,edge,verification,intent}-8-11.md` in the session scratchpad. The diff was taken against `HEAD` (the orchestrator committed on `epic-8` after the baseline) and leaves out the generated api client and `.docs`.
- verdicts: 51 findings — high 0, medium 0, low 39, false 12, maybe-false 0
- findings:
  - `[low]` `[reject]` blind-1: a Takeover can fire after the Lab hour ended when the sweep is down past both the due time and `in_room_until`. Needs a sweep outage; the due time was set inside the Lab hour, and reordering would break the intended «due before the end is still taken» rule (now tested).
  - `[low]` `[reject]` blind-2: a limit longer than what is left of the Lab hour never fires. The line names the end («I rommet til kl. 16:00»), and the mark ends with the Lab hour by design; a cap adds a rule the AC does not ask for.
  - `[low]` `[reject]` blind-3 / edge-6: marking with old wait starts makes long waits due at once. The AC recomputes «from the same clock start»; Design Notes record it as the room's choice not to wait.
  - `[low]` `[reject]` blind-4 / edge-8: a Lab hour removed between the read and the mark leaves an orphan mark until the old end. Needs two Lecturers acting within the same second; a lock-side re-check adds a cross-module read under the Game lock.
  - `[low]` `[reject]` blind-5 / edge-7 / verification-other-1: `lab_hour_changed` is unguarded after the Lab hour commits. Only `game_not_found` can be raised and Games are never deleted; a try/except per Game adds a branch for a state not shown reachable.
  - `[low]` `[reject]` blind-6: the button's availability goes stale while Spillinnsikt is open across a Lab hour boundary. Spillinnsikt is read again on every game event; a stale press answers `not_in_lab_hour` inline. A boundary timer adds machinery.
  - `[false]` `[reject]` blind-7 / edge-12: PLAYING_OUT disagreement. No path reaches PLAYING_OUT before Story 8.14, which the epic says clears the mark.
  - `[low]` `[reject]` blind-8: no «endre», and the 409 text drops who marked. The AC defines mark and end only; the refusal is the stable static line as in Story 8.7.
  - `[low]` `[reject]` blind-9: ending the mark can push an overdue, not-yet-swept Takeover to the long limit. That is the AC's «recomputes back … from the same clock start»; the sweep runs Takeover before its end (tested).
  - `[low]` `[reject]` blind-10 / edge-13: one more indexed `student_adjustments` read per play envelope. One small query; making it lazy adds a resolver parameter.
  - `[false]` `[reject]` blind-11: system ends write no audit row. Only a person's action is audited (FR-3, as `reach_agreed_time` and `announce_insert_time`); the AC asks the audit of `mark_in_room` by the Lecturer.
  - `[low]` `[reject]` blind-12: no concurrency tests. Every command runs under the Game row lock; the race outcomes are the sequential `already_in_room`/`not_in_room` refusals, which are tested.
  - `[low]` `[reject]` blind-13 / edge-9: back-to-back or overlapping Lab hours end the mark at the earliest Lab hour's end; the Lecturer marks again. Rare, and the AC ties the mark to «the Lab hour's end».
  - `[low]` `[reject]` blind-14: no index for the in-room finders. Like `due_agreed_times` (no index on `resume_at`), a small table read once a minute.
  - `[low]` `[patch]` blind-15 / verification-other-3: the `table_status` docstring lost «`factor`» (shell substitution). Restored. The two «ended» lines are for two readers (Lecturer and Student) on purpose.
  - `[low]` `[reject]` edge-1: an expired, not yet swept mark still shortens a new Week's waits for up to a minute. AD-9's one-minute resolution.
  - `[low]` `[reject]` edge-2: `already_in_room` for a mark that expired seconds ago and is not yet swept. One-minute window; the sweep clears it.
  - `[false]` `[reject]` edge-3: `end_in_room` with an unparseable actor and no guard clears unconditionally. No caller passes that: the route passes the Lecturer's id, the sweep `now`, the hook `lab_hour_id`.
  - `[false]` `[reject]` edge-4: a person call with `actor=None` silently returns False. The only person caller passes `user.id`.
  - `[false]` `[reject]` edge-5: a naive `now` raises TypeError. Both callers pass aware times (`auth.utcnow`, the sweep's UTC clock).
  - `[low]` `[reject]` edge-10: a Student whose Seat an AI player took still reads the line. The line is the game's state («I rommet til …») that all of the game's Students see (AC «all four»); a Reclaim brings the limit back to them.
  - `[false]` `[reject]` edge-11: float rounding below an integer. The offered factors are 1.5, 2 and 3, exact in binary with whole minutes (tested with 5 × 1.5 = 7).
  - `[low]` `[reject]` edge-14: the form reappears if another Lecturer marks and ends while it is open. Needs two Lecturers acting on one game while the form is open.
  - `[low]` `[reject]` edge-15: `"10"` as a string is accepted. Pydantic lax mode; harmless and the same as every other int body.
  - `[false]` `[reject]` edge-claim-1: the limit runs on past the end until the sweep. The spine bounds the sweep's resolution at one minute (AD-9).
  - `[low]` `[patch]` verification-1: the sweep's order (Takeover before the in-room end) was not pinned. `test_a_seat_due_before_the_lab_hours_end_is_taken_in_the_sweep_that_ends_the_mark` runs one sweep at the end and asserts both happen.
  - `[low]` `[patch]` verification-2: `_recompute_insert_times`' in-room input was untested. `test_a_pause_under_the_mark_keeps_the_in_room_insert_times` pauses with an agreed time, clears it and resumes under a mark.
  - `[low]` `[patch]` verification-3: the floor of the Student's minutes was not pinned. `test_the_students_own_minutes_are_rounded_down_and_never_shortened` covers 1.5 ×, 3 × and a factor below 1.
  - `[low]` `[patch]` verification-4: `tableRows`/`wallGroups` adoption of `rowLabel` was untested. `in-room.test.tsx` now asserts both labels.
  - `[low]` `[defer]` verification-5: finished-game and non-Takeover branches of `can_mark_in_room` and `end_in_room` are untested at the api. Low-risk branches; deferred as the layer filed it.
  - `[false]` `[reject]` verification-other-2: `policy.py` at the root is not this story's (an earlier agent's, left untracked on purpose).
  - `[low]` `[patch]` verification-other-4: a test comment said the next Week waits on the in-room limit but asserted nothing. Removed; `test_a_new_week_under_the_mark_waits_on_the_in_room_limit` covers `_start_waits`.
  - `[low]` `[patch]` intent-1: the AD-9 sweep list and the decision record were not updated. The spine's AD-9 list now names `games.end_in_room`, and the Deferred item has «Decided in Story 8.11». AD-2 already listed `end_in_room`.
  - `[false]` `[reject]` intent-2: the command signatures carry `lab_hour_id`, `until` and `now` beside the AC's `(game, minutes, actor)`. The AC's form is shorthand; the Lab hour comes from `sessions`, which `games` may not read.
  - `[false]` `[reject]` intent-3: «the system as actor» is `actor=None`. That is how every system command of `games` names the system (Story 8.5's `kind: system`).
  - `[low]` `[reject]` intent-4: the Student's minutes and the due time are computed in two places. Both read the same factor source; the shown minutes are floored on purpose and pinned by a test.
  - `[low]` `[reject]` intent-5: the e2e checks one Student's line, not all four. The api test checks three Students' envelopes and each one's own minutes; the screen is the same component.
  - `[false]` `[reject]` intent-6: the clock split. Lab hours are stored and judged on the api clock (Story 5.6), the sweep on its own; the stored end is the boundary (Design Notes).
  - `[low]` `[reject]` intent-7: the Student line is checked in e2e on Spill only, not Hjem. The AC names Spill only.
  - `[false]` `[reject]` intent-8: the generated client is absent from the diff. It was left out of the review diff on purpose and regenerated with `npm run api:generate`.
  - `[low]` `[reject]` intent-9: the 8.9 refactor (`_recompute_due_times`) is outside the story. It is the AC's «recomputes the open turns» shared with 8.9; the 8.9 tests still pass.
  - `[low]` `[reject]` intent-10: the 8.7 pause path changed. Passing the in-room limit there is the spine's «every command that changes an input recomputes» (AD-20); now tested.
  - `[low]` `[reject]` intent-11: the Lab hour hooks change Story 5.6's routes. The AC asks it («a Lab hour that is moved or removed updates or ends the marks»).
- Count: 15 blind, 15 edge-case plus 1 claim, 5 verification gaps plus 4 other, 11 intent divergences (the intent layer is descriptive; each divergence is a row). Findings with the same root cause share one row, named by every member (51 findings in 43 rows).
- Found after review, by the full suites: `test_game_insight.py::test_staff_read_every_week_of_every_role_as_stored` compares the Assistant's Spillinnsikt with the Lecturer's and now also differs by `can_mark_in_room` (fixed in the test); `e2e/staff-pause.spec.ts` met two `[data-pause-result]` lines because «I rommet» reused the Pause's result line (now its own `[data-in-room-result]`).

## Design Notes

Recorded decision (spine Deferred item, AD-2/AD-9): `end_in_room` is the one way a mark ends — by a person («Ikke i rommet lenger»), by the sweep's `games.end_in_room` at `in_room_until`, or by `games.service` when its Lab hour is removed or moved so it is no longer on; a moved end only rewrites `in_room_until` through `mark_in_room` with no person.

Marking recomputes from the stored wait start: a Seat waited for longer than the in-room limit is due at once and taken at the next sweep — the room decided not to wait. A Student's shown minutes are floored (never more than they have).

## Verification

**Commands:**
- `cd backend && uv run pytest -q tests/games/test_in_room.py tests/games/test_registry.py tests/games/test_game_summaries.py tests/sessions/test_in_room_view.py tests/test_migrations.py` -- pass
- `cd frontend && npx vitest run src/modules/games` -- pass

## Auto Run Result

Status: done

**Summary.** A Lecturer can mark a running Class game «I rommet» during a Lab hour of its Class session, with a shorter waiting time (2 to 120 whole minutes, default 10) until the Lab hour ends, and end it again. The Students read the line above Setestatus with their own minutes, and the Oversikt's wall row label carries «I rommet».

- **Store.** Migration 0061 adds the mark to `games` (`in_room_minutes`, `in_room_until`, `in_room_lab_hour_id`, `in_room_by`, `in_room_marked_at`; whole or absent, 2..120) and `game_summaries.in_room_until`.
- **Commands.**
  - `mark_in_room` writes the mark under the Game lock, recomputes the open Week's due and insert times from the stored wait starts with the in-room limit times each Student's factor, audits `game.marked_in_room`, and emits `game`, `session` and `user`.
  - `end_in_room` clears it and recomputes back to the Inactivity limit; a Lecturer's end is audited `game.in_room_ended`.
  - `_recompute_due_times` is shared with Story 8.9's `recompute_turn_times`; `_start_waits` and `_recompute_insert_times` read the in-room limit too.
  - Refusals: 422 `minutes_out_of_range`; 409 `not_in_lab_hour`, `already_in_room` (Story 8.5's `acted_by`/`acted_at`), `not_in_room`, `game_not_running`, `game_finished`, `in_room_not_allowed`.
- **Ending.** The sweep's new due action `games.end_in_room` (after `games.takeover`) ends a mark once `in_room_until` has passed. `games.service.lab_hour_changed`, called by `change_lab_hour`/`remove_lab_hour`, moves the end or ends the mark.
- **Api.** `POST`/`DELETE /api/games/{id}/in-room` under the Lecturer-only policy `games.in_room`. Spillinnsikt gains `in_room`, `can_mark_in_room` and `lab_hour_ends_at` (the Lab hour on now, api clock). The Oversikt gains `in_room_until`. The play envelope gains `table_status.in_room` with the reader's own whole minutes (floored).
- **Screens.**
  - Spillstyring: «Marker som i rommet» (unavailable with «Kan bare brukes i en Labtime.» outside a Lab hour). The form in place has «Ventetid i rommet», the line naming the end, «Marker som i rommet, 10 min» and «Avbryt». Marked, it reads «I rommet til 16:00. KI tar over etter 10 min uten ordre.» with «Ikke i rommet lenger». The result lines take focus.
  - Spill: «I rommet til kl. 16:00. En KI-spiller tar setet etter 10 min uten ordre.» in a polite live region; its end is read out.
  - Wall and table: «Spill 3 · I rommet».
- **Docs.** The spine's AD-9 sweep list names the in-room end, and its Deferred item records «Decided in Story 8.11».

**Files changed**
- Backend:
  - `migrations/versions/0061_game_in_room.py` (new) and `games/models.py`: the columns.
  - `games/{commands,repo,overview,service,insight,views,schemas}.py`: the commands, recompute, summary column, finder, Lab hour hook, insight and Student view fields.
  - `ops/sweep.py`: `games.end_in_room`.
  - `platform/{authz.py,events/registry.py}`: `games.in_room`; the two commands' topics.
  - `sessions/{overview,routes,schemas,service}.py`: the routes, the Spillinnsikt/Oversikt/play fields, the Lab hour hooks, the reader's factor.
- Frontend:
  - `modules/games/{in-room.ts,in-room-view.tsx}` (new): helpers, `InRoomStyring`, `InRoomLine`.
  - `games/{spillstyring.tsx,play-page.tsx,overview.ts,api.ts}`, `copy/nb.ts`.
  - `lib/api/{openapi.json,schema.ts}`: regenerated.
- Tests:
  - New: `tests/games/test_in_room.py`, `tests/sessions/test_in_room_view.py`, `src/modules/games/in-room.test.tsx`, `e2e/in-room.spec.ts`.
  - Updated: `test_registry.py` (two runners), `test_game_summaries.py` (recomputation), `test_migrations.py` (HEAD 0061), `test_game_insight.py` (`can_mark_in_room` differs for an Assistant); `can_mark_in_room` in six Vitest fixtures.
- Planning: `ARCHITECTURE-SPINE.md` (AD-9 list and the Story 8.11 decision).

**Review.** Four Sonnet reviewers returned 51 findings: high 0, medium 0, low 39, false 12.
- Patched (low): the `table_status` docstring; the AD-9 list and decision record; four tests (the sweep's order, the Pause path under a mark, the floor of the minutes, the wall/table labels); a misleading test comment.
- Deferred: finished-game and non-Takeover branches untested at the api (verification-5).
- Rejected: the rest, each with its reason in the Review Triage Log.
- Follow-up review: not recommended. Patched entries: high 0, medium 0, low 7.

**Verification** (after the patches)
- **Backend.** The full suite with `--maxprocesses=8` first ran 3054 passed, 1 failed: `test_game_insight.py::test_staff_read_every_week_of_every_role_as_stored`, a real consequence (the Assistant's Spillinnsikt now also differs by `can_mark_in_room`), fixed in the test. Rerun in full: 3055 passed. ruff check and format are clean on the touched files.
- **Frontend.** Typecheck, Vitest (74 files, 895 tests), `lint:colours`, `check:copy` and `next build` pass.
- **End to end.** After the last frontend change the stack was rebuilt. Playwright with `--workers=4` ran 139 tests in 24 specs: in-room, overview, varselband, spillstyring, pause, staff-pause, takeover, takeover-overview, live-updates, homes, student-home, game-insight, guided-week, order-confirm, order-failures, order-field, seat-status, week-advance, week-table, week-transition, peer-insert, class-session-lab-hours, start-games, tilrettelegging. All passed. The first run had one failure: `staff-pause.spec.ts` found two `[data-pause-result]` lines, a real consequence (the in-room block reused the Pause's result line). It now has its own `[data-in-room-result]`. No test failed once and passed on rerun.
- **Accessibility.** axe and reflow ran on Spillstyring's in-room form at 320 px and at 1440 px, and on the marked state at 320 px and at 1440 px.
- **Slow tests (over 1 s).**
  - `test_in_room_view.py::test_a_lecturer_marks_a_game_in_a_lab_hour_and_ends_it` takes 3.8 s: one short Class game through the api, the whole flow in one test.
  - `test_in_room_view.py::test_an_assistant_a_student_and_others_are_refused` takes 1.9 s.
  - `test_in_room.py::test_the_sweep_takes_over…` takes 1.2 s: two sweeps.
  - The registry test grew by two runners (about 10 s in total, was about 9 s).

**Decisions taken instead of the founder.**
- Marking recomputes from the stored wait starts (the AC's «same clock start»): a Seat already waited for longer than the in-room limit is taken at the next sweep.
- The Student's minutes are the in-room limit times their own factor, rounded down, never more than they have.
- A Lab hour is «on» by the api clock, the one Lab hours are stored on; the sweep ends a mark by its stored end.
- A moved Lab hour that is still on moves the mark's end; one moved so it is no longer on, or removed, ends it. Only a Lecturer's own presses are audited.
- One mark per game; a second mark is refused `already_in_room`, and changing the minutes is an end and a new mark.
- The Lecturer-only policy `games.in_room`; an Assistant lecturer sees neither the button nor the mark controls.
- The wall and table label read «Spill 3 · I rommet»; the end of a mark is read out to Students, not shown.
- Draft copy `[ASSUMPTION]`:
  - «Hele minutter, fra 2 til 120.» and «Skriv et helt antall minutter fra 2 til 120.»;
  - «Ikke i rommet lenger. Den vanlige ventetiden gjelder igjen.» and «Spillet er ikke i rommet lenger. Den vanlige ventetiden gjelder igjen.»;
  - the refusals and the failure.
- The orchestrator asked for the implementation in the builder's own context, so the skill's implementation subagent was not used.

**Residual risks.**
- An open Spillinnsikt does not read again by itself when a Lab hour starts or ends; a stale press answers `not_in_lab_hour`.
- A sweep outage past a Lab hour's end lets in-room due times act until the sweep runs.
- The visual check is left to the separate visual agent.
