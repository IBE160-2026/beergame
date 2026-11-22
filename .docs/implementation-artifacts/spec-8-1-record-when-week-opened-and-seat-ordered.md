---
title: 'Story 8.1: Record when each Week opened and when each Seat ordered'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '21065b6138924d67e6e1b2ba5932afba51968daf'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/.docs/implementation-artifacts/epic-8-context.md'
warnings: [oversized]
deferred:
  - summary: >-
      The Oversikt next_change_at uses the game-level minimum takeover_due_at and drops a game once that minimum passes, even if another waited-for Seat is due later.
    evidence: |-
      In Story 8.1 all waited-for Seats of a game share one wait start and one limit, so their due times are equal. Once Tilrettelegging (8.9) or mid-Week seating gives Seats different due times, store per-Seat due times in waiting_for (or let _next_due see every due time ahead) so the Oversikt reads again at the next one.
    location: >-
      backend/app/modules/sessions/overview.py:_next_due
    severity: medium (unverified)
---

<intent-contract>

## Intent

**Problem:** The game keeps `opened_at`, `ordered_at`, `viewed_at` and `wait_started_at` per Seat turn, but no Takeover or insert due time exists, `turn_times` lacks the FR-36 inputs, the Decision log does not copy the wait times, the overview and play envelope do not point `next_change_at` at a Takeover clock, and Spillinnsikt does not show when a Week opened and when the Order came.

**Approach:** Migration 0053 adds `takeover_due_at` and `insert_allowed_at` to `seat_turns` (and the wait times to `seat_weeks`, plus the nearest `takeover_due_at` to `game_summaries`). `games.rules.turn_times` gains the Inactivity limit, per-Student factor, agreed Pause time and in-room limit inputs; `games.commands._start_waits` stores both due times on Student-held, not-ordered turns of a Game whose policy has inactivity Takeover. Views carry the stored times; Spillinnsikt gets three columns.

## Boundaries & Constraints

**Always:** Only `games.commands` (via `games.repo`) writes the timing columns; only `rules.turn_times` computes them (AD-20). "Has ordered" stays `rules.has_ordered` (Guided Week: `viewed_at`). Due times only on Student-held turns, only after the clock start, only when `policy(purpose).inactivity_takeover` and the snapshot's `inactivity_limit_hours` is set. `seat_weeks` stays write-once. Ids only, no names in rows. UI copy in `nb.ts`; times shown in Europe/Oslo.

**Never:** No Takeover, sweep, Pause, adjustment or in-room behaviour (Stories 8.2–8.11). No browser-side wait/due derivation. No change to the demo Class. No trigger that freezes the two new columns (later stories recompute them).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Free Week, first Student orders | Class game, limit 24 h, other Student Seat unordered | its `wait_started_at` = T, `takeover_due_at` = `insert_allowed_at` = T + 24 h; AI Seats unordered get only `wait_started_at` | none |
| Guided Week, first Student views | same, Guided Week | same three times set on the unviewed Student Seat by `view_week` | none |
| No Student ordered yet | Week just opened | all three empty | none |
| Excluded purpose | lecturer test / simulation Game | `opened_at`, `ordered_at` recorded, no due time | none |
| Later Student orders | their turn already has times | `seat_weeks` row copies `wait_started_at`, `takeover_due_at`, `insert_allowed_at` | none |
| turn_times inputs | factor 1.5; in-room 10 min; agreed time earlier/later than due | due = start + limit×factor (in-room limit replaces limit); insert = agreed if set, but never before due when factor > 1; else due | factor below 1 treated as 1 |

</intent-contract>

## Code Map

- `backend/app/modules/games/rules.py:60-127` -- `TurnGame/TurnSeat/TurnInputs/TurnTimes/turn_times`: extend inputs and outputs.
- `backend/app/modules/games/commands.py:1480-1501` -- `_start_waits`: the only place the clock starts (from `_place` line 1249-1250 for Student Orders and `view_week` line 1460); add due times. `_place` 1217-1246 builds the `seat_weeks` row: copy the new times.
- `backend/app/modules/games/repo.py:484-490` -- `set_wait_started_at` → write wait and due times together, only while unset; new `turn_clock(session, game_id)` read for Spillinnsikt.
- `backend/app/modules/games/models.py:161-246, 298-321` -- `seat_turns`, `seat_weeks`, `game_summaries` columns.
- `backend/migrations/versions/0048_seat_turns_wait_started_at.py` -- pattern for 0053.
- `backend/app/modules/games/schemas.py:126-147` -- `SessionRuntime.inactivity_limit_hours` (frozen at lock, Story 5.11).
- `backend/app/modules/games/policy.py` -- `inactivity_takeover` flag (False for SIMULATION, LECTURER_TEST).
- `backend/app/modules/games/overview.py` -- `recompute`: add nearest `takeover_due_at` of `waiting_for`.
- `backend/app/modules/games/service.py:565-600` -- `ClassGameSummary`/`class_overview`: carry `takeover_due_at`.
- `backend/app/modules/sessions/overview.py:84-116` -- overview `next_change_at`: Start date before start, else nearest future `takeover_due_at`.
- `backend/app/modules/games/views.py:295-341` -- `table_status.due_times`: add stored `takeover_due_at`/`insert_allowed_at` of unordered turns (play envelope `next_change_at`, `sessions/service.py:1475-1478`).
- `backend/app/modules/games/insight.py` + `sessions/overview.py:289-362` + `sessions/schemas.py:947` -- `InsightWeek(Out)` gains `opened_at`, `ordered_at` (Guided Week Student Seat: `viewed_at`).
- `frontend/src/modules/games/insight.ts`, `insight-page.tsx`, `frontend/src/copy/nb.ts` (`insight.columns`) -- three new columns; reuse `waitDuration` (`seat-status.ts:20`) and the audit-style Oslo formatter.
- `frontend/src/lib/api/openapi.json`, `schema.ts` -- regenerate (`uv run python -m app.openapi ...`, `npm run api:generate`).
- Tests: `backend/tests/games/test_turn_times.py`, `tests/games/test_view_week.py`, `tests/sessions/test_game_insight.py`, `tests/sessions/test_overview.py`, `frontend/src/modules/games/insight.test.ts`, `frontend/e2e/game-insight.spec.ts`.

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0053_seat_turns_due_times.py` -- add the columns -- schema.
- `backend/app/modules/games/models.py` -- mirror columns -- metadata.
- `backend/app/modules/games/rules.py` -- extend `turn_times` -- one computation.
- `backend/app/modules/games/repo.py`, `commands.py` -- store due times in `_start_waits`, copy into `seat_weeks` -- FR-35/36.
- `backend/app/modules/games/overview.py`, `service.py`, `sessions/overview.py`, `views.py` -- `next_change_at` from stored due times -- AD-8.
- `backend/app/modules/games/insight.py`, `sessions/schemas.py`, `sessions/overview.py` -- opened/ordered per Week -- FR-35.
- `frontend/...` -- columns «Uke åpnet», «Bestilt», «Tid brukt» -- FR-35.
- Tests: table-driven `turn_times` tests; api tests for free and Guided Week due times, excluded purpose, `seat_weeks` copy, no other writer (source scan), overview/envelope `next_change_at`, insight times; Vitest for row formatting; e2e insight columns.

**Acceptance Criteria:**
- Given a Class game Week where one Student has ordered (free Week) or viewed (Guided Week), when the command commits, then every other unordered Student-held turn has `wait_started_at`, `takeover_due_at` and `insert_allowed_at` = start + Inactivity limit, and the AI turns have no due times.
- Given a lecturer-test Game, when Students order, then no due time is ever set.
- Given a Student orders after the clock started, when `place_order` commits, then their `seat_weeks` row holds the turn's three wait times.
- Given a waiting Class game, when the Oversikt and the play envelope are read, then `next_change_at` is the nearest stored due time after `server_now`.
- Given Spillinnsikt, when staff read a Game, then each Week row shows when the Week opened, when the Order came and the time between, in Europe/Oslo time.
- Given the source tree, when the guard test scans it, then only `games/repo.py` writes `seat_turns` and only `games/commands.py` calls its time writers.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- verdicts: 42 findings — high 0, medium 3, low 14, false 23, maybe-false 2
- findings:
  - `[maybe-false]` `[defer]` blind-1: Oversikt `_next_due` drops a game whose stored minimum due time has passed although another waited-for Seat is still ahead — in 8.1 every waited-for Seat of a game shares one wait start and one limit, so the due times in a game are equal; it becomes real with Tilrettelegging (8.9). Deferred (medium, unverified).
  - `[false]` `[reject]` blind-2: 0051 backfill SQL not extended — 0051 is a historic revision that never runs again; 0053 now fills the column for waits that existed (blind-3 patch), and the test states why 0051 rows carry none.
  - `[medium]` `[patch]` blind-3: games waiting at deploy never get due times — fixed: 0053 `BACKFILL` sets them from `wait_started_at` plus the frozen limit on open Student-held turns of running Class games and refreshes the waiting summaries; tested in `test_turn_clock.py` by clearing and re-running it.
  - `[false]` `[reject]` blind-4: `set_wait_times` guard blocks later recomputation — later stories add their own writer (`recompute_turn_times`, 8.9); this writer is the clock start only.
  - `[false]` `[reject]` blind-5: `_ordered_at` returns a too-early time in a Guided Week — the Guided Order is placed at opening (or in the view's own transaction for old Games), so `viewed_at` is the later moment; None while unviewed is the intended "has not ordered".
  - `[low]` `[reject]` blind-6: `due_times` duplicates and past entries — `next_change_at` takes the first entry after `server_now`; duplicates are harmless. The occupant part is edge-6.
  - `[false]` `[reject]` blind-7: speculative `turn_times` inputs — the story's AC requires the function to take the per-Student adjustment, agreed time and in-room limit now.
  - `[false]` `[reject]` blind-8: `hours == 0` gives an immediate due time — `class_sessions` has a check constraint `inactivity_limit_hours >= 20`; the None paths are now unit-tested (verification-3).
  - `[low]` `[reject]` blind-9: frontend: no year, month list from the invitations copy, empty «Tid brukt» cell, near-zero AI durations, wider table — Class games last weeks within one term; the table already scrolls in its own region (e2e at 320 px); not worth extra complexity.
  - `[low]` `[reject]` blind-10: test hygiene (cross-module fixtures, regex scan) — the repo's established test pattern; the scan is the AC's "api test asserts that no other code writes these columns".
  - `[false]` `[reject]` blind-11: required-nullable insight fields break older clients — api and web app deploy together; the schema is regenerated and CI diffs it.
  - `[false]` `[reject]` blind-12: no changelog for the new fields — docstrings and the regenerated OpenAPI are the project's contract.
  - `[medium]` `[patch]` edge-1: Student turn with a wait start but no due time — same root as blind-3; patched by the 0053 backfill.
  - `[medium]` `[patch]` edge-2: in-flight Class games at deploy — same root as blind-3; patched by the 0053 backfill.
  - `[false]` `[reject]` edge-3: Guided-Week `seat_weeks` rows carry no wait times — the Order is placed at opening, before any clock; the AC copies the times as they stand at `place_order`, and Spillinnsikt reads `seat_turns` for the view moment.
  - `[false]` `[reject]` edge-4: backfill historic `seat_weeks` — the table is write-once (a trigger refuses UPDATE, AD-15).
  - `[maybe-false]` `[defer]` edge-5: mixed past/future due times in one game — same root as blind-1; deferred with it.
  - `[low]` `[patch]` edge-6: a stale Takeover due time after a Student Seat goes to an AI player mid-Week feeds the envelope — fixed: `views._due_times_of` reads FR-36 due times of Student-held turns only (`overview.recompute` already filtered).
  - `[low]` `[reject]` edge-7: `occupied_since` not passed in `_start_waits` — no Student can take a Seat mid-Week yet (Reclaim is queued to the next Week, 8.4); `turn_times` supports it when 8.2/8.4 pass it.
  - `[false]` `[reject]` edge-8: zero or negative limit — the database check constraint keeps it at 20 h or more.
  - `[false]` `[reject]` edge-9: `clockText` throws on an invalid string — the api only serves `AwareDatetime` values.
  - `[false]` `[reject]` edge-10: a negative interval is hidden — `viewed_at` and `ordered_at` are written after `opened_at` on the same database clock.
  - `[low]` `[reject]` edge-11 (claim): the Oversikt ignores `insert_allowed_at` — equal to `takeover_due_at` until 8.7; the Oversikt shows Takeover, not insert rights.
  - `[false]` `[reject]` edge-12 (claim): Guided-Week `seat_weeks` nulls — as edge-3.
  - `[false]` `[reject]` edge-13 (claim): stored summaries diverge from recompute — as blind-2; the 0053 docstring is rewritten.
  - `[low]` `[patch]` verification-1: no test of a passed due time on the Oversikt — added to `test_the_overview_reads_again_at_the_nearest_takeover_due_time` (`next_change_at` is None once the stored due time has passed).
  - `[low]` `[patch]` verification-2: the unviewed Guided-Week Student has no insight test — added `test_in_an_open_guided_week_a_student_who_has_not_opened_it_has_not_ordered`.
  - `[low]` `[patch]` verification-3: the policy gate of `_inactivity_limit` is not pinned — added `test_only_a_game_whose_policy_has_inactivity_takeover_gets_a_limit`.
  - `[false]` `[reject]` verification-4: Guided `seat_weeks` nulls unverified — as edge-3.
  - `[low]` `[reject]` verification-5: stale due time after a switch untested — the code path is removed by edge-6; recompute's filter is covered by `test_game_summaries`.
  - `[low]` `[reject]` verification-6: migration columns not asserted — `command.check` compares the models with the revisions and the walk runs 0053 up and down.
  - `[false]` `[reject]` intent-1: reading R3 with R4 — descriptive; it matches the story.
  - `[false]` `[reject]` intent-2: the browser computes «Tid brukt» — a difference of two stored times shown as text, not a wait or a due time (AD-20 concerns those).
  - `[false]` `[reject]` intent-3: Guided Week «Bestilt» is `viewed_at` — what the AC defines as "has ordered".
  - `[false]` `[reject]` intent-4: envelope and Oversikt `next_change_at` cover different sets — the Oversikt has no per-Seat insert action; equal in 8.1.
  - `[false]` `[reject]` intent-5: weakened backfill check — as blind-2.
  - `[false]` `[reject]` intent-6: no test of the Week opening — `test_the_first_order_sets_the_due_times_of_the_students_who_have_not` asserts one turn per Seat with `opened_at` for the opened Week.
  - `[false]` `[reject]` intent-7: Hjem, Varselbånd and play screen unchanged — the AC constrains them to stored times, which they already show; the envelope and Oversikt values are api-tested.
  - `[low]` `[reject]` intent-8: the e2e checks the format, not the value — Vitest pins the formatting of exact values; the api test pins the values.
  - `[low]` `[reject]` intent-9: Guided «Bestilt» differs from `seat_weeks.ordered_at` — intended by the AC (opening counts as ordering); documented in the insight docstrings.
  - `[false]` `[reject]` intent-10: the migration only bumps HEAD — as verification-6.
  - `[low]` `[reject]` verification-other: a Guided `logged()` case missing — as edge-3; behaviour is "as stands at placement".

## Design Notes

`insert_allowed_at` equals `takeover_due_at` until Story 8.7 brings an agreed time; the function already implements FR-89's rule (agreed time wins, but a Student with Tilrettelegging is never given an insert time before their own extended limit). The in-room limit replaces the Inactivity limit and the factor multiplies whichever applies; Stories 8.9/8.11 may refine. `game_summaries.takeover_due_at` is stored now because the overview's `next_change_at` must come from the read model (AD-25); Story 8.3 builds its band choice on it.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/games/test_turn_times.py tests/games/test_view_week.py tests/sessions/test_game_insight.py tests/sessions/test_overview.py -q` -- pass
- full suite with `--maxprocesses=8`; `npm run typecheck`, `npm test`, `npm run lint:colours`, `npm run build`; Playwright `--workers=4` for game-insight, overview, varselband, live-updates, play-screen specs and homes.

## Auto Run Result

Status: done

**Summary.** The game now keeps its own FR-36 clock. Migration 0053 adds `seat_turns.takeover_due_at` and `insert_allowed_at`, copies the wait start and both due times into the write-once `seat_weeks` row, and adds the nearest `takeover_due_at` to `game_summaries`. A backfill gives games already waiting at deploy their due times. `games.rules.turn_times` takes the Inactivity limit, the per-Student factor, the agreed Pause time and the in-room limit. The last three stay empty until Stories 8.9, 8.7 and 8.11. `games.commands._start_waits` stores both due times on Student-held turns that have not ordered, in free and Guided Weeks, only when `games.policy` has inactivity Takeover. The play envelope and the Oversikt set `next_change_at` to the nearest stored due time. Spillinnsikt shows «Uke åpnet», «Bestilt» and «Tid brukt» in Europe/Oslo time; in a Guided Week «Bestilt» is the time the Student opened the Week.

**Files changed**
- `backend/migrations/versions/0053_seat_turns_due_times.py`: new columns and the in-flight backfill.
- `backend/app/modules/games/models.py`: the same columns in the metadata.
- `backend/app/modules/games/rules.py`: FR-36 inputs and outputs of `turn_times` (`_due_times`).
- `backend/app/modules/games/commands.py`: `_start_waits` stores the due times, `_inactivity_limit` applies the policy gate, and `_place` copies the times into `seat_weeks`.
- `backend/app/modules/games/repo.py`: `set_wait_times` (replaces `set_wait_started_at`) and `turn_clock`.
- `backend/app/modules/games/overview.py`, `service.py`: `game_summaries.takeover_due_at`.
- `backend/app/modules/games/views.py`: the envelope's due times include the Takeover and insert times of Student-held turns.
- `backend/app/modules/sessions/overview.py`, `schemas.py`: Oversikt `next_change_at` (`_next_due`) and the insight `opened_at`/`ordered_at`.
- `backend/app/modules/games/insight.py`: the per-Week opened and ordered times.
- `frontend/src/modules/games/insight.ts`, `insight-page.tsx`, `frontend/src/copy/nb.ts`: three new table columns and their copy (marked [ASSUMPTION]).
- `frontend/src/lib/api/openapi.json`, `schema.ts`: regenerated.
- Tests: `backend/tests/sessions/test_turn_clock.py` (new), `tests/games/test_turn_times.py`, `tests/sessions/test_game_insight.py`, `tests/sessions/test_seat_status.py`, `tests/games/test_game_summaries.py`, `tests/test_migrations.py`, `frontend/src/modules/games/insight.test.ts`, `frontend/e2e/game-insight.spec.ts`.

**Review.** Four sonnet reviewers ran: blind, edge case, verification gap and intent alignment. They reported 42 findings: 3 medium, 14 low, 23 false and 2 maybe-false.
- Patched:
  - the in-flight backfill, one medium entry (blind-3, edge-1, edge-2);
  - Takeover due times limited to Student-held turns in the envelope (low);
  - three test gaps (low): a passed due time on the Oversikt, an unviewed Guided Week in Spillinnsikt, and the policy gate.
- Deferred: the game-level minimum in `_next_due`, which matters once Seats in one game get different due times (8.9).
- Rejected: everything else, each with its reason in the Review Triage Log.

**Follow-up review recommended:** false. One medium entry and five low entries were patched; none was high.

**Verification**
- Backend, full suite with `--maxprocesses=8`: 2880 passed. ruff check and format are clean.
- Frontend: typecheck, Vitest (830 passed), `lint:colours`, `check:copy` and `next build` all pass.
- Playwright with `--workers=4` on a rebuilt stack: 73 passed and none was retried. The run covered game-insight, overview, varselband, live-updates, homes, seat-status, guided-week, week-advance, order-confirm and student-home. axe ran at 1440 and 320 px on Spillinnsikt.
- New tests over 1 s: `test_turn_clock.py::test_the_first_order_sets_the_due_times_of_the_students_who_have_not` takes about 3.6 s. It plays the Guided Weeks, as its sibling in `test_seat_status.py` does.

**Residual risks.** Story 8.3 builds on `game_summaries.takeover_due_at`. Guided-Week `seat_weeks` rows carry no wait times because their Order is placed at opening. Spillinnsikt reads `seat_turns` for those Weeks. The draft column copy needs a later copy review.
