---
title: 'Story 8.2: An AI player takes over after the Inactivity limit'
type: 'feature'
created: '2026-11-21'
status: 'done'
baseline_revision: '271087f0a1feaa105820ebdb5411990837d49df7'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/.docs/implementation-artifacts/epic-8-context.md'
warnings: [oversized]
deferred: []
---

<intent-contract>

## Intent

**Problem:** Story 8.1 stores `takeover_due_at` on every waited-for Student turn, but nothing acts on it: an absent Student blocks the Class game forever, the occupancy history cannot say who triggered a change, and nobody is told when a Seat changes hands.

**Approach:** Add `games.rules.can_take_over` (the one eligibility check) and the command `games.commands.takeover(game, seat, actor="system", now)`; a new `ops.sweep` due action finds due turns and calls it, one per transaction. Migration 0054 adds nullable `seat_occupancy.actor_user_id`. The Setestatus rows, Spill and Hjem show the Takeover; an immediate `takeover_notice` mail tells the group.

## Boundaries & Constraints

**Always:** Only `games.commands` writes occupancy and turns (via `repo`), under the Game row lock, one transaction, version bump, `game`/`session`/`user` events, `_settle` after commit (AD-2). New occupant: `llm` when the frozen `SessionRuntime` has a model config, else `rule_based`; `rule_based` if the Seat ever had a `guard_switch` row or the budget is cost-limited (`_cost_limited`). Reason `takeover_inactivity`, `actor_user_id` NULL, `from_week` = open Week; `players.ensure_order` in the same transaction; an `llm` occupant mid-Week gets its turn's `ai_deadline_at` from `rules.turn_times` with `occupied_since`. Eligibility only through `can_take_over` (running Game, policy `inactivity_takeover`, Student-held Seat in the open Week, not `has_ordered`, `takeover_due_at` set and `<= now`). Sweep `now` is the sweep's clock; tests inject it (Issue #63). Ids only in rows, notices and logs. UI copy in `nb.ts`, mail in Jinja2; the requirement warning never holds a digit or «uke».

**Never:** No staff/peer Takeover, Reclaim, Pause, in-room, reminders or playout (8.3–8.14); no audit record for the system actor; no «Ta tilbake setet» button; no change to the demo Class; no browser-side due-time decision.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Due, free Week | Student B unordered, due passed | one row `takeover_inactivity` from this Week; AI orders; Week completes → advances once | none |
| Due, Guided Week | B never viewed Week 1 | row from Week 1; fixed Order kept; Week advances to 2 | none |
| Not due | sweep at due − 1 s | nothing | none |
| No Student ordered / excluded purpose | no due time, days pass | no row, no clock | none |
| Sweep twice / concurrent | two takeovers race | one row | second refused `409 seat_not_student_held`, sweep skips silently |
| Student orders first | Order committed, then takeover | Order stands | takeover refused `409 order_exists`, skipped |
| Student orders after | takeover committed, then Order | AI Order stands | `409 seat_not_yours` |
| LLM mode | snapshot with model config | occupant `llm`, `ai-orders` job, turn `ai_deadline_at` set | — |
| Guard-switched before / cost-limited | history has `guard_switch` / budget exhausted | occupant `rule_based` | — |

</intent-contract>

## Code Map

- `backend/app/modules/games/rules.py` -- add `can_take_over(game, turn, actor, now, *, guided) -> str | None` (refusal code or None) next to `has_ordered`/`turn_times`.
- `backend/app/modules/games/commands.py` -- add `takeover` modelled on `switch_to_rule_based` (1616-1661); reuse `_cost_limited` (833), `_ensure_order` (880), `_ai_order_budget` (888), `_commit_change` (243), `_settle` (979); `__all__`. Notices like `propose_time` (1773-1780).
- `backend/app/modules/games/repo.py` -- `due_takeover_turns(session, now)` (open Week of running Games, `takeover_due_at <= now`, joined with occupancy in force and game purpose/settings), `set_ai_deadline(turn_id, at)` (only while NULL), `guard_switched_seats(session, game_id)`, `last_students(session, game_id)` (each Seat's latest `student` row user id); `seat_occupancy` insert gains `actor_user_id`.
- `backend/app/modules/games/models.py:121-145` -- `actor_user_id` column + check constraint.
- `backend/migrations/versions/0054_seat_occupancy_actor.py` -- column + `ck_seat_occupancy_actor` (NULL for `initial`, `takeover_inactivity`, `guard_switch`, `cost_limit`, `playout`, `moved`).
- `backend/app/modules/games/service.py` -- `due_takeovers(now)` finder and `take_over_due(item, now)` act for the sweep (`ops` imports `games.service` only).
- `backend/app/modules/ops/sweep.py:112-151` -- `DueAction("games.takeover", …)`.
- `backend/app/platform/events/registry.py` -- `"games.takeover": {"game","session","user"}`.
- `backend/app/modules/games/views.py:296-353` + `schemas.py:578-611` -- `TableSeat.ordering_for` (name of the Student the AI took over from, takeover marks only) and `guard_switched`.
- `backend/app/modules/sessions/schemas.py:471-537`, `sessions/service.py:1374-1386` -- `TableSeatOut` fields; `StudentGameOut.obligatory`.
- `backend/app/modules/messaging/delivery.py` -- `TAKEOVER_NOTICE_KIND` immediate, context from `sessions.service.takeover_mail_context`.
- `backend/app/platform/email/templates/kinds/takeover_notice.{html,txt}.j2`, `_takeover_warning.j2`.
- `frontend/src/modules/games/seat-status.ts` -- holder/status words for takeover and guard switch; `frontend/src/modules/games/play-page.tsx` -- taken-over block replaces Ordrefelt, `seat_not_yours` checked before the stored-Order read (Issue #141); `student-hjem.tsx`, `home.ts` -- line and warning, no Spillkort/primary when taken over.
- `frontend/src/copy/nb.ts` (`homes.student`) -- `orderingFor`, `orderingForYou`, `takenOver`, `requirementWarning`.
- `frontend/scripts/check-copy.mjs` + `scripts.test.mjs` -- rule: `requirementWarning` strings and `_takeover_warning.j2` hold no digit or «uke».
- Tests: `backend/tests/games/helpers.py` patterns; `tests/games/test_registry.py` RUNNERS/CLASS_SETUP_EVENTS; `tests/games/test_game_summaries.py`; `tests/sessions/test_turn_clock.py` (`running`, `free_week`, `turns`).

## Tasks & Acceptance

**Execution:**
- `backend/migrations/versions/0054_seat_occupancy_actor.py`, `models.py` -- column + check -- AD-5 actor decision.
- `rules.py` -- `can_take_over` -- single eligibility check.
- `repo.py`, `commands.py` -- `takeover` command + writers -- FR-36, AD-2, AD-5.
- `service.py`, `ops/sweep.py`, `events/registry.py` -- due action, topics -- AD-9, AD-8.
- `views.py`, `schemas.py`, `sessions/*` -- seat fields, obligatory -- FR-34, UX-DR69.
- `messaging/delivery.py`, `sessions/service.py`, templates -- `takeover_notice` -- FR-36, AD-9.
- `frontend/...` -- rows, play screen, Hjem, copy, copy check; regenerate `openapi.json`/`schema.ts`.
- `ARCHITECTURE-SPINE.md:568` -- note the actor decision under the Deferred item.
- Tests: `backend/tests/games/test_takeover.py` (rules table, command, races, sweep clock, LLM/guard/cost, notices, Guided Week, idle days, excluded purpose); registry + summaries runners; api test of Setestatus/`obligatory`; Vitest for seat rows/home; `scripts.test.mjs`; e2e `frontend/e2e/takeover.spec.ts` (Student sees «KI-spiller har bestilt for deg.» on Spill and Hjem, other sees «bestiller for …»).

**Acceptance Criteria:**
- Given a Student-held unordered Seat whose `takeover_due_at` passed in a running Class game, when `ops.sweep.run(now)` runs with `now` ≤ due + 59 s, then exactly one occupancy row (`takeover_inactivity`, actor NULL, this Week) exists, the AI has ordered or its job is queued, the version rose, and `game`, `session`, `user` events were emitted.
- Given a Guided Week where one Student never opens Week 1, when the Takeover happens at the due time, then the Game advances to Week 2.
- Given a Takeover, when Students read Spill or Hjem, then the Seat row reads «KI-spiller» and «bestiller for <name>», the taken-over Student sees «KI-spiller har bestilt for deg.», and in an Obligatorisk session the requirement warning.
- Given a Takeover, when it commits, then each Student of the Game has one `takeover_notice` (dedupe `takeover_notice:<seat>:<week>:<user>`), delivered immediately with a template headed «ØL-spillet».
- Given the copy check, when the warning holds a digit or «uke», then it fails.

## Spec Change Log

## Review Triage Log

### 2026-11-21 — Review pass
- verdicts: 38 findings — high 0, medium 5, low 25, false 8, maybe-false 0
- findings:
  - `[medium]` `[patch]` blind-1: `taken_over` came from the latest row only, so a Play guard or cost-limit switch after a Takeover dropped «bestiller for» and gave the Student the Ordrefelt back — `repo.seat_histories` now tracks `taken_over` (a Takeover row after the Seat's last Student row) and `views.table_status` uses it; `test_a_later_guard_switch_keeps_the_seat_taken_over`.
  - `[low]` `[patch]` blind-2: the phone «Alle rader» link lived in the Ordrefelt's aside and vanished for a taken-over Seat — the play screen draws the same link under the note.
  - `[low]` `[patch]` blind-3: the warning exists in `nb.ts` and `_takeover_warning.j2` with no parity check — Vitest now compares the macro body with `requirementWarning`; spelled-out amounts stay outside the AC's rule (digit or «uke»).
  - `[false]` `[reject]` blind-4: an immediate mail to every Student at any hour — the AC requires `takeover_notice` for the Student and each other Student, `immediate`, also 22:00–07:00.
  - `[low]` `[reject]` blind-5: `seat_histories` reads the Game's whole occupancy history per read — a handful of rows per Seat in one indexed query; not worth a second query shape.
  - `[low]` `[reject]` blind-6: the finder's `ordered_at IS NULL OR viewed_at IS NULL` keeps ordered free-Week turns as candidates — `due_takeovers` filters them through `can_take_over` before the command; a few extra reads per minute only while a Week waits past its due time.
  - `[low]` `[patch]` blind-7: `occupied_since` used the transaction start (`repo.now`) — now `repo.clock_now`, after the lock (same as edge-8).
  - `[low]` `[patch]` blind-8: untested mail-context and Setestatus branches — the api test now drives the notices through the mail pipeline and the HTTP `409 seat_not_yours`; the archived/removed branches mirror the tested `time_proposal_mail_context` pattern and were left.
  - `[low]` `[patch]` blind-9: `TakenOverNote` was an `aria-live` region inserted already filled and repeated the Setestatus line — the note is no longer a live region; the Setestatus's polite line announces the Takeover.
  - `[false]` `[reject]` blind-10: «KI-spiller har bestilt for deg.» is a dead end — the spine's copy (UX-DR62); «Ta tilbake setet» is Story 8.4.
  - `[low]` `[patch]` blind-11: the actor was checked after the other refusals — `can_take_over` checks it first.
  - `[false]` `[reject]` blind-12: `actor_user_id` is speculative — the AC requires the column now, NULL for exactly the listed reasons.
  - `[false]` `[reject]` blind-13: sprint-status and Epic 7 log in the diff — orchestrator commits that landed on the branch after the baseline, not this change.
  - `[low]` `[patch]` blind-14: the mail fallback «bestiller nå for Fabrikk» reads like a person — now «for setet som Fabrikk»; `roles[role]` covers the four Roles (KeyError impossible); the dedupe key cannot collide because a Reclaim takes effect only in the next Week.
  - `[low]` `[reject]` blind-15: test construction (manual `_settle` swap, setup count, both-outcome race test) — follows `test_registry`'s existing pattern; the race test's two outcomes are the AC's.
  - `[medium]` `[patch]` blind-16: the sweep swallowed every 409 — only `can_take_over`'s race codes are skipped; any other refusal is raised and logged by the sweep (`TAKEOVER_RACES`); `test_the_sweep_skips_a_race_and_reports_any_other_refusal`.
  - `[medium]` `[patch]` edge-1: same root as blind-1; patched with it.
  - `[medium]` `[patch]` edge-2: a persistent 409 from inside `place_order` (snapshot, parameter set) would block the Game silently — same root as blind-16; patched with it.
  - `[low]` `[reject]` edge-3: `sweep.run` counts a skipped Seat — `run()` counts every action alike; changing it would change every other action's count.
  - `[low]` `[reject]` edge-4: finder over-fetch — as blind-6.
  - `[low]` `[patch]` edge-5: `games.takeover` ran after the finished-game replays — moved before `games.verify_finished` so slow replays never delay it.
  - `[low]` `[patch]` edge-7: the docstring promised an advance in a Guided Week — reworded: the Week advances when no other Student Seat is still unviewed.
  - `[false]` `[reject]` edge-6: dedupe key suppresses a second Takeover in one Week — the Seat is AI-held until a Reclaim, which applies from the next Week.
  - `[low]` `[patch]` edge-8: as blind-7.
  - `[low]` `[patch]` verification-1: the `seat_not_yours`-before-stored reorder was unpinned — e2e «an Order sent as the Seat is taken over is never confirmed…».
  - `[low]` `[patch]` verification-2: `useGuidedView`'s taken-over guard was unobserved — e2e «a Guided Uke of a Seat taken over is never reported as opened».
  - `[low]` `[patch]` verification-3: `guard_switched` never asserted true at the api — `test_a_seat_the_play_guard_switched_is_marked` asserts it.
  - `[medium]` `[patch]` verification-4: the delivery wiring and HTML part were never run — the api test drains the mail queue and asserts one mail each, the own one with the warning in HTML.
  - `[low]` `[patch]` verification-5: the sweep's skip was untested — covered by the new sweep test (blind-16).
  - `[low]` `[patch]` intent-3.1: the 409 after a Takeover was shown only at the command — the api test posts the Order and reads `409 seat_not_yours`.
  - `[low]` `[reject]` intent-3.2: night delivery not end to end — the mode is asserted `immediate`, and `test_an_immediate_notice_leaves_at_once_even_at_night` covers immediate kinds in the pipeline.
  - `[low]` `[reject]` intent-3.3: the e2e uses stand-in envelopes — the real envelope is asserted at the api; the browser half reads the same generated types; the runbook's e2e pattern.
  - `[false]` `[reject]` intent-3.4: «KI-spiller» everywhere Seats are shown — every view already renders an `ai` holder as «KI-spiller»; the Oversikt and Spillinnsikt are untouched.
  - `[low]` `[reject]` intent-3.5: the copy rule is keyed to one property and one file — the AC names exactly one place the warning is built; parity is now tested (blind-3).
  - `[low]` `[reject]` intent-3.6: the LLM job is not run — the `ai-orders` path is Story 2.x's, tested there; the Takeover's part (occupant, deadline) is tested.
  - `[low]` `[patch]` intent-3.7: `guard_switched` at the api — as verification-3.
  - `[false]` `[reject]` intent-3.8: Ordrefelt, Spillkort and guided view changes go beyond the story — they follow from «KI-spiller har bestilt for deg.» and the `409 seat_not_yours` AC.
  - `[false]` `[reject]` intent-3.9: scope edges — as blind-13.

## Design Notes

`actor_user_id` decision (AD-14/15): nullable id on `seat_occupancy`, set only for `takeover_staff`, `takeover_peer`, `reclaim` (later stories); a check constraint keeps it NULL for the rest. The sweep's refusals from `can_take_over` are expected race outcomes, so the act skips them quietly; any other refusal is raised for the sweep to log. `can_take_over` takes `actor` (`"system"` now) so 8.5/8.8 extend one function. The Play guard flag reads the history, not the latest row, so a switch outlasts a later Takeover.

## Verification

**Commands:**
- `cd backend && uv run pytest tests/games/test_takeover.py tests/games/test_registry.py tests/games/test_game_summaries.py -q` -- pass
- full backend `--maxprocesses=8`; `npm run typecheck`, `npm test`, `npm run lint:colours`, `npm run check:copy`, `npm run build`; Playwright `--workers=4` takeover, play-screen, homes, seat-status, live-updates.

## Auto Run Result

Status: done

**Summary.** An AI player now takes over the Seat of a Student who has not ordered by the stored `takeover_due_at`. The sweep's new `games.takeover` due action finds due turns (`games.service.due_takeovers`) and calls the new `games.commands.takeover(game, seat, actor="system", now)`, one Seat per transaction. The command checks the new `games.rules.can_take_over` under the Game row lock, appends one `takeover_inactivity` row from the open Week with no actor, has the AI player order through `players.ensure_order` in the same transaction (an LLM player gets its turn's AI deadline), bumps the version, emits `game`, `session` and `user`, and enqueues an immediate `takeover_notice` for each Student. The occupant is `llm` by the session's AI mode, `rule_based` after a Play guard switch or at the cost limit. Migration 0054 adds `seat_occupancy.actor_user_id` with a check constraint (the decision is noted in the spine's Deferred item). The Setestatus reads «KI-spiller  bestiller for Jonas»; the Student whose Seat it was sees «KI-spiller har bestilt for deg.» instead of the Ordrefelt and Spillkort, with the requirement warning in an Obligatorisk session; the copy check fails on a digit or «uke» in that warning in `nb.ts` and the mail macro.

**Files changed**
- `backend/migrations/versions/0054_seat_occupancy_actor.py`, `backend/app/modules/games/models.py`: the actor column and its check.
- `backend/app/modules/games/rules.py`: `can_take_over`, `TakeoverActor`.
- `backend/app/modules/games/commands.py`: `takeover`, `_takeover_occupant`, `_takeover_deadline`, `TAKEOVER_NOTICE`.
- `backend/app/modules/games/repo.py`: `set_ai_deadline`, `guard_switched`, `seat_histories`, `takeover_row`, `due_takeover_turns`.
- `backend/app/modules/games/service.py`: `due_takeovers`, `takeover_of`.
- `backend/app/modules/ops/sweep.py`: the `games.takeover` due action (before the finished-game checks).
- `backend/app/platform/events/registry.py`: `games.takeover` topics.
- `backend/app/modules/games/views.py`, `schemas.py`, `marks.py`, `sessions/schemas.py`, `sessions/service.py`: `taken_over`, `ordering_for`, `guard_switched` on each Seat; `obligatory` on the Student's game; `takeover_mail_context`.
- `backend/app/modules/messaging/delivery.py`, `backend/app/platform/email/templates/kinds/takeover_notice.*.j2`, `_takeover_warning.j2`: the immediate notice mail.
- `frontend/src/modules/games/seat-status.ts`, `seat-status-view.tsx`, `play-page.tsx`, `student-hjem.tsx`, `home.ts`, `frontend/src/copy/nb.ts`: rows, polite line, `TakenOverNote`, no Ordrefelt or Spillkort for a Seat taken over, `seat_not_yours` said before the stored Order is read (GitHub issue 141).
- `frontend/scripts/check-copy.mjs`: the warning rule.
- `frontend/src/lib/api/openapi.json`, `schema.ts`: regenerated.
- `.docs/planning-artifacts/architecture/.../ARCHITECTURE-SPINE.md`: the actor decision.
- Tests: `backend/tests/games/test_takeover.py` (new), `tests/sessions/test_takeover_view.py` (new), `tests/games/test_registry.py`, `test_game_summaries.py`, `tests/sessions/test_play.py`, `test_seat_status.py`, `tests/test_migrations.py`, `frontend/src/modules/games/seat-status.test.tsx`, `home.test.ts`, `frontend/scripts/scripts.test.mjs`, `frontend/e2e/takeover.spec.ts` (new).

**Review.** Four sonnet reviewers (blind, edge case, verification gap, intent alignment): 38 findings — 0 high, 5 medium, 25 low, 8 false.
- Patched: medium — Takeover state kept after a later guard/cost switch (blind-1, edge-1); only race refusals skipped by the sweep (blind-16, edge-2); mail pipeline tested end to end (verification-4). Low — phone «Alle rader» link, warning parity test, DB clock for `occupied_since`, note no longer a double live region, actor checked first, mail fallback wording, sweep order, docstring, and e2e/api tests for the 409, the `seat_not_yours` reorder, the guided-view guard and `guard_switched`.
- Deferred: none.
- Rejected: the rest, each with its reason in the Review Triage Log.

**Follow-up review recommended:** true. Three medium entries were patched (Takeover state after a later switch, sweep refusal handling, mail pipeline). Unverified risk: the whole path from the real sweep to a real browser on the local stack is not run in one test (the e2e uses stand-in envelopes; the api tests use an injected clock).

**Verification**
- Backend, full suite with `--maxprocesses=8`: 2907 passed. ruff check and format clean.
- Frontend: typecheck, Vitest (838 passed), `check:copy`, `lint:colours`, `next build` pass.
- Playwright `--workers=4` on a rebuilt stack: 94 passed, none retried (takeover, seat-status, order-failures, order-confirm, order-field, homes, student-home, game-card, live-updates, guided-week, week-advance). axe at 320 and 1440 px on the taken-over play screen.
- New tests over 1 s: `tests/sessions/test_takeover_view.py::test_the_absent_seat_is_taken_over_and_every_student_sees_it` (about 1.5 s call, plus 2.6 s fixture setup: it starts a real Class game and drains the mail queue). No test failed once and passed on rerun.

**Residual risks.** A notice names a User by foreign key; no User is ever deleted today, but a deleted one would fail the Takeover's transaction. An LLM turn whose Effort level is missing still gets no AI deadline (GitHub issue 141, item 1). The copy rule covers digits and «uke», not spelled-out counts. Draft copy (own row, removed Student, warning, mail) needs a copy review.
